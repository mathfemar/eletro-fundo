"""
sim/pnl.py — Pipeline de PnL: captura live, fechamento diário, backfill e catch-up.

Fluxo:
  1. capture_pnl_live  → calcula PL (posições MtM + caixa) → grava FAT_FUNDO_PNL_LIVE
  2. close_pnl_day     → pega último live do dia → grava FAT_FUNDO_PNL_FECHAMENTO → recomputa cotas
  3. backfill           → roda close_pnl_day para range de datas  
  4. catchup            → preenche dias faltantes desde último fechamento
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from app.services.db_connection import managed_connection, query, query_scalar

from app.api.routers.sim.helpers import TZ_BR, _now_sp, _now_sp_str, _list_active_fundo_ids
from app.api.routers.sim.caixa import _get_fundo_caixa_total_sync
from app.api.routers.sim.positions import _get_fundo_positions_payload_sync
from app.api.routers.sim.cotas import recompute_fundo_cotas_sync

logger = logging.getLogger("app.api.simulador")


def capture_pnl_live_fundo_sync(
    fundo_id: int,
    dt_hora_captura: Optional[datetime] = None,
    fonte: str = "simulador",
) -> dict:
    """Captura snapshot de PnL live: posições MtM + caixa líquido → FAT_FUNDO_PNL_LIVE."""
    dt_cap = dt_hora_captura or _now_sp()
    dt_ref = dt_cap.date().isoformat()
    dt_carga = _now_sp_str()

    payload = _get_fundo_positions_payload_sync(fundo_id=fundo_id, dt_ref=dt_ref)
    resumo = payload.get("resumo", {})

    valor_mercado_posicoes = float(resumo.get("VALOR_MERCADO_TOTAL") or 0.0)
    caixa_liquido = _get_fundo_caixa_total_sync(fundo_id, dt_ref)
    pl_total_fundo = valor_mercado_posicoes + caixa_liquido

    with managed_connection() as conn:
        conn.execute(
            """
            INSERT INTO FAT_FUNDO_PNL_LIVE (
                ID_FUNDO, DT_REFERENCIA, DT_HORA_CAPTURA,
                VL_VALOR_MERCADO_TOTAL, VL_PNL_ABERTO_TOTAL,
                VL_PNL_REALIZADO_TOTAL, VL_PNL_TOTAL,
                CD_FONTE, FL_REPROCESSADO, DT_CARGA
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fundo_id,
                dt_ref,
                dt_cap.strftime("%Y-%m-%d %H:%M:%S"),
                pl_total_fundo,
                float(resumo.get("PNL_ABERTO_TOTAL") or 0.0),
                float(resumo.get("PNL_REALIZADO_TOTAL") or 0.0),
                float(resumo.get("PNL_TOTAL") or 0.0),
                fonte,
                0,
                dt_carga,
            ),
        )

    return {
        "ID_FUNDO": fundo_id,
        "DT_REFERENCIA": dt_ref,
        "DT_HORA_CAPTURA": dt_cap.strftime("%Y-%m-%d %H:%M:%S"),
        "RESUMO": resumo,
    }


def close_pnl_day_fundo_sync(
    fundo_id: int,
    dt_referencia: str,
    allow_recompute: bool = True,
    update_cota: bool = True,
) -> dict:
    """Fecha PnL do dia: pega último live → grava fechamento → recomputa cotas."""
    row = query_scalar(
        "SELECT COUNT(*) FROM VW_FUNDO_PNL_LIVE_ULTIMO_DIA WHERE ID_FUNDO = ? AND DT_REFERENCIA = ?",
        params=(fundo_id, dt_referencia),
    )

    if allow_recompute or not row:
        capture_time = datetime.fromisoformat(f"{dt_referencia} 19:00:00").replace(tzinfo=TZ_BR)
        capture_pnl_live_fundo_sync(
            fundo_id=fundo_id,
            dt_hora_captura=capture_time,
            fonte="reprocessamento_fechamento",
        )

    last_df = query(
        """
        SELECT ID_FUNDO, DT_REFERENCIA, DT_HORA_CAPTURA,
               VL_VALOR_MERCADO_TOTAL, VL_PNL_ABERTO_TOTAL,
               VL_PNL_REALIZADO_TOTAL, VL_PNL_TOTAL
        FROM VW_FUNDO_PNL_LIVE_ULTIMO_DIA
        WHERE ID_FUNDO = ? AND DT_REFERENCIA = ?
        LIMIT 1
        """,
        params=(fundo_id, dt_referencia),
    )

    if last_df.empty:
        raise ValueError(f"Sem snapshot live para fechar fundo={fundo_id} em {dt_referencia}")

    rec = last_df.to_dict("records")[0]
    dt_carga = _now_sp_str()
    with managed_connection() as conn:
        conn.execute(
            """
            INSERT INTO FAT_FUNDO_PNL_FECHAMENTO (
                ID_FUNDO, DT_REFERENCIA, DT_HORA_CAPTURA,
                VL_VALOR_MERCADO_TOTAL, VL_PNL_ABERTO_TOTAL,
                VL_PNL_REALIZADO_TOTAL, VL_PNL_TOTAL,
                CD_METODO, FL_REPROCESSADO, DT_CARGA
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'snapshot_ultimo_dia', 0, ?)
            ON CONFLICT(ID_FUNDO, DT_REFERENCIA) DO UPDATE SET
                DT_HORA_CAPTURA = excluded.DT_HORA_CAPTURA,
                VL_VALOR_MERCADO_TOTAL = excluded.VL_VALOR_MERCADO_TOTAL,
                VL_PNL_ABERTO_TOTAL = excluded.VL_PNL_ABERTO_TOTAL,
                VL_PNL_REALIZADO_TOTAL = excluded.VL_PNL_REALIZADO_TOTAL,
                VL_PNL_TOTAL = excluded.VL_PNL_TOTAL,
                CD_METODO = excluded.CD_METODO,
                FL_REPROCESSADO = 1,
                DT_CARGA = datetime('now', '-3 hours')
            """,
            (
                fundo_id,
                dt_referencia,
                rec["DT_HORA_CAPTURA"],
                float(rec["VL_VALOR_MERCADO_TOTAL"] or 0.0),
                float(rec["VL_PNL_ABERTO_TOTAL"] or 0.0),
                float(rec["VL_PNL_REALIZADO_TOTAL"] or 0.0),
                float(rec["VL_PNL_TOTAL"] or 0.0),
                dt_carga,
            ),
        )

    if update_cota:
        recompute_fundo_cotas_sync(fundo_id)

    return {
        "ID_FUNDO": fundo_id,
        "DT_REFERENCIA": dt_referencia,
        "VL_PNL_TOTAL": float(rec["VL_PNL_TOTAL"] or 0.0),
        "DT_HORA_CAPTURA": rec["DT_HORA_CAPTURA"],
    }


def backfill_pnl_fechamento_fundo_sync(fundo_id: int, dt_inicio: str, dt_fim: str) -> dict:
    """Executa close_pnl_day para cada dia do range, respeitando primeiro capital."""
    start = date.fromisoformat(dt_inicio)
    end = date.fromisoformat(dt_fim)
    if end < start:
        raise ValueError("dt_fim deve ser maior ou igual a dt_inicio")

    dt_primeiro_capital = query_scalar(
        "SELECT MIN(DT_REFERENCIA) FROM FAT_FUNDO_FLUXO_CAPITAL WHERE ID_FUNDO = ?",
        params=(fundo_id,),
    )
    if dt_primeiro_capital is None:
        raise ValueError(
            f"Fundo {fundo_id} não possui nenhum aporte/capital registrado. "
            "Registre o capital inicial antes de executar o backfill."
        )

    dt_capital = date.fromisoformat(str(dt_primeiro_capital))
    if start < dt_capital:
        start = dt_capital

    if start > end:
        raise ValueError(
            f"dt_inicio ({dt_inicio}) é anterior ao primeiro capital do fundo "
            f"({dt_capital}) e dt_fim ({dt_fim}) também — nada a processar."
        )

    registros = 0
    cursor = start
    while cursor <= end:
        close_pnl_day_fundo_sync(
            fundo_id=fundo_id,
            dt_referencia=cursor.isoformat(),
            allow_recompute=True,
            update_cota=False,
        )
        registros += 1
        cursor += timedelta(days=1)

    cota_info = recompute_fundo_cotas_sync(fundo_id)

    return {
        "ID_FUNDO": fundo_id,
        "DT_INICIO": start.isoformat(),
        "DT_FIM": dt_fim,
        "QT_DIAS": registros,
        "COTA": cota_info,
    }


def close_pnl_day_all_fundos_sync(dt_referencia: str) -> dict:
    """Fecha PnL de todos os fundos ativos para uma data."""
    fundo_ids = _list_active_fundo_ids()
    ok = 0
    erro = 0
    for fid in fundo_ids:
        try:
            close_pnl_day_fundo_sync(fundo_id=fid, dt_referencia=dt_referencia, allow_recompute=True)
            ok += 1
        except Exception:
            erro += 1
            logger.exception("Falha no fechamento diário do fundo %s em %s", fid, dt_referencia)
    return {"DT_REFERENCIA": dt_referencia, "QT_OK": ok, "QT_ERRO": erro}


def catchup_fechamento_all_fundos_sync() -> dict:
    """Preenche dias faltantes desde último fechamento até hoje."""
    last_dt = query_scalar("SELECT MAX(DT_REFERENCIA) FROM FAT_FUNDO_PNL_FECHAMENTO")
    today = _now_sp().date()

    start = date.fromisoformat(last_dt) + timedelta(days=1) if last_dt else today - timedelta(days=7)
    end = today
    if end < start:
        return {"DT_INICIO": start.isoformat(), "DT_FIM": end.isoformat(), "QT_DIAS": 0, "QT_OK": 0, "QT_ERRO": 0}

    qt_dias = 0
    ok = 0
    erro = 0
    cursor = start
    while cursor <= end:
        qt_dias += 1
        result = close_pnl_day_all_fundos_sync(cursor.isoformat())
        ok += int(result["QT_OK"])
        erro += int(result["QT_ERRO"])
        cursor += timedelta(days=1)

    return {
        "DT_INICIO": start.isoformat(),
        "DT_FIM": end.isoformat(),
        "QT_DIAS": qt_dias,
        "QT_OK": ok,
        "QT_ERRO": erro,
    }
