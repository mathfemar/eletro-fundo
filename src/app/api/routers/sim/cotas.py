"""
sim/cotas.py — Cálculo de NAV / cotas, retorno e posição de cotistas.

Método de cotas (padrão fundos abertos):
  - Emissão/queima de cotas: qt_cotas += fluxo / cota_D-1
  - Precificação: cota = PL_real / qt_cotas
  - Retorno: retorno_dia = cota[D] / cota[D-1] − 1 (imune a fluxos)
"""

import logging
from typing import Optional

from app.services.db_connection import managed_connection, query, query_scalar

from app.api.routers.sim.helpers import _now_sp_str

logger = logging.getLogger("app.api.simulador")


def recompute_fundo_cotas_sync(fundo_id: int) -> dict:
    """Recalcula a série completa de cotas do fundo.

    Fonte de verdade: FAT_FUNDO_PNL_FECHAMENTO.VL_VALOR_MERCADO_TOTAL
    (= posições MtM + caixa líquido)
    """
    # ── 1. Primeiro capital: marco zero do fundo ─────────────────────────
    dt_primeiro_capital = query_scalar(
        "SELECT MIN(DT_REFERENCIA) FROM FAT_FUNDO_FLUXO_CAPITAL WHERE ID_FUNDO = ?",
        params=(fundo_id,),
    )
    if not dt_primeiro_capital:
        with managed_connection() as conn:
            conn.execute("DELETE FROM FAT_FUNDO_COTA_DIARIA WHERE ID_FUNDO = ?", (fundo_id,))
        return {"ID_FUNDO": fundo_id, "QT_DIAS": 0}

    with managed_connection() as conn:
        conn.execute(
            "DELETE FROM FAT_FUNDO_COTA_DIARIA WHERE ID_FUNDO = ? AND DT_REFERENCIA < ?",
            (fundo_id, dt_primeiro_capital),
        )

    # ── 2. Carrega fechamentos (PL real) e fluxos ────────────────────────
    fechamento_df = query(
        """
        SELECT DT_REFERENCIA, DT_HORA_CAPTURA,
               COALESCE(VL_VALOR_MERCADO_TOTAL, 0) AS VL_PL
        FROM FAT_FUNDO_PNL_FECHAMENTO
        WHERE ID_FUNDO = ? AND DT_REFERENCIA >= ?
        ORDER BY DT_REFERENCIA
        """,
        params=(fundo_id, dt_primeiro_capital),
    )

    fluxo_df = query(
        """
        SELECT DT_REFERENCIA,
               SUM(CASE WHEN TP_FLUXO = 'APORTE' THEN VL_FLUXO ELSE -VL_FLUXO END) AS VL_FLUXO_LIQ
        FROM FAT_FUNDO_FLUXO_CAPITAL
        WHERE ID_FUNDO = ? AND DT_REFERENCIA >= ?
        GROUP BY DT_REFERENCIA
        """,
        params=(fundo_id, dt_primeiro_capital),
    )

    fechamento_records = fechamento_df.to_dict("records")
    fluxo_records = fluxo_df.to_dict("records")

    if not fechamento_records and not fluxo_records:
        return {"ID_FUNDO": fundo_id, "QT_DIAS": 0}

    fechamento_map: dict[str, dict] = {
        str(row["DT_REFERENCIA"]): {
            "VL_PL": float(row["VL_PL"] or 0.0),
            "DT_HORA_CAPTURA": row["DT_HORA_CAPTURA"],
        }
        for row in fechamento_records
    }
    fluxo_map = {
        str(row["DT_REFERENCIA"]): float(row["VL_FLUXO_LIQ"] or 0.0)
        for row in fluxo_records
    }

    datas = sorted(set(fechamento_map.keys()) | set(fluxo_map.keys()))
    if not datas:
        return {"ID_FUNDO": fundo_id, "QT_DIAS": 0}

    # ── 3. Cota base do seed ─────────────────────────────────────────────
    cota_inicial_db = query_scalar(
        """
        SELECT VL_COTA FROM FAT_FUNDO_COTA_DIARIA
        WHERE ID_FUNDO = ? AND CD_METODO LIKE '%seed%'
        ORDER BY DT_REFERENCIA ASC LIMIT 1
        """,
        params=(fundo_id,),
    )
    cota_base = float(cota_inicial_db or 1.0)
    if abs(cota_base) <= 1e-12:
        cota_base = 1.0

    qt_cotas = 0.0
    cota_prev = cota_base

    # ── 4. Loop: calcula cota para cada dia ──────────────────────────────
    with managed_connection() as conn:
        dt_carga = _now_sp_str()
        for dt_ref in datas:
            fechamento = fechamento_map.get(dt_ref)
            fluxo_liq = float(fluxo_map.get(dt_ref, 0.0))

            # Emitir/queimar cotas ANTES de precificar (cota D-1)
            if abs(fluxo_liq) > 1e-12 and abs(cota_prev) > 1e-12:
                qt_cotas += fluxo_liq / cota_prev

            # Precificação
            if fechamento is not None:
                pl_real = float(fechamento["VL_PL"] or 0.0)
                cota = pl_real / qt_cotas if abs(qt_cotas) > 1e-12 else 0.0
                vl_pl_dia = pl_real
            else:
                cota = cota_prev
                vl_pl_dia = cota * qt_cotas

            dt_hora_fechamento = (
                (fechamento or {}).get("DT_HORA_CAPTURA")
                or f"{dt_ref} 19:00:00"
            )

            conn.execute(
                """
                INSERT INTO FAT_FUNDO_COTA_DIARIA (
                    ID_FUNDO, DT_REFERENCIA, VL_COTA, QT_COTAS, VL_PL,
                    DT_HORA_FECHAMENTO, CD_METODO, FL_REPROCESSADO, DT_CARGA
                ) VALUES (?, ?, ?, ?, ?, ?, 'nav_com_fluxos_emit_burn', 0, ?)
                ON CONFLICT(ID_FUNDO, DT_REFERENCIA) DO UPDATE SET
                    VL_COTA = excluded.VL_COTA,
                    QT_COTAS = excluded.QT_COTAS,
                    VL_PL = excluded.VL_PL,
                    DT_HORA_FECHAMENTO = excluded.DT_HORA_FECHAMENTO,
                    CD_METODO = excluded.CD_METODO,
                    FL_REPROCESSADO = 1,
                    DT_CARGA = datetime('now', '-3 hours')
                """,
                (fundo_id, dt_ref, cota, qt_cotas, vl_pl_dia, dt_hora_fechamento, dt_carga),
            )

            cota_prev = cota if abs(cota) > 1e-12 else cota_prev

    result = {
        "ID_FUNDO": fundo_id,
        "QT_DIAS": len(datas),
        "QT_COTAS": qt_cotas,
        "VL_COTA_BASE": cota_base,
        "DT_BASE_COTAS": datas[0],
        "VL_COTA_ULTIMA": cota_prev,
    }
    recompute_cotistas_posicao_diaria_sync(fundo_id=fundo_id)
    return result


# ── Posição de cotistas ──────────────────────────────────────────────────────

def _compute_cotistas_posicao_snapshot(fundo_id: int, dt_base: str) -> tuple[list[dict], float]:
    """Calcula posição de cada cotista num dia, baseado nos fluxos e cota D-1."""
    cota_ref = query_scalar(
        "SELECT VL_COTA FROM FAT_FUNDO_COTA_DIARIA WHERE ID_FUNDO = ? AND DT_REFERENCIA = ? LIMIT 1",
        params=(fundo_id, dt_base),
    )
    if cota_ref is None:
        cota_ref = query_scalar(
            """
            SELECT VL_COTA FROM FAT_FUNDO_COTA_DIARIA
            WHERE ID_FUNDO = ? AND DT_REFERENCIA <= ?
            ORDER BY DT_REFERENCIA DESC LIMIT 1
            """,
            params=(fundo_id, dt_base),
        )
    cota_atual = float(cota_ref or 0.0)
    if cota_ref is None:
        return [], cota_atual

    flows_df = query(
        """
        SELECT ffc.ID_TITULAR, dt.NM_TITULAR, ffc.DT_REFERENCIA, ffc.TP_FLUXO, ffc.VL_FLUXO
        FROM FAT_FUNDO_FLUXO_CAPITAL ffc
        LEFT JOIN DIM_TITULAR dt ON dt.ID_TITULAR = ffc.ID_TITULAR
        WHERE ffc.ID_FUNDO = ? AND ffc.ID_TITULAR IS NOT NULL AND ffc.DT_REFERENCIA <= ?
        ORDER BY ffc.DT_REFERENCIA ASC, ffc.ID_FLUXO ASC
        """,
        params=(fundo_id, dt_base),
    )

    cota_hist_df = query(
        "SELECT DT_REFERENCIA, VL_COTA FROM FAT_FUNDO_COTA_DIARIA WHERE ID_FUNDO = ? AND DT_REFERENCIA <= ? ORDER BY DT_REFERENCIA ASC",
        params=(fundo_id, dt_base),
    )
    cota_hist = [(str(r["DT_REFERENCIA"]), float(r["VL_COTA"] or 0.0)) for r in cota_hist_df.to_dict("records")]

    def _cota_no_dia_anterior(dt_ref: str) -> float:
        last = None
        for d, c in cota_hist:
            if d < dt_ref:
                last = c
            else:
                break
        return last if (last is not None and abs(last) > 1e-12) else 1.0

    saldo: dict[int, dict] = {}
    for row in flows_df.to_dict("records"):
        titular_id = int(row["ID_TITULAR"])
        item = saldo.setdefault(
            titular_id,
            {
                "ID_FUNDO": fundo_id,
                "ID_TITULAR": titular_id,
                "NM_TITULAR": row.get("NM_TITULAR") or f"Titular {titular_id}",
                "VL_APORTADO_BRUTO": 0.0,
                "VL_RESGATADO_BRUTO": 0.0,
                "VL_INVERTIDO_LIQ": 0.0,
                "QT_COTAS": 0.0,
                "DT_REFERENCIA": dt_base,
            },
        )

        dt_flow = str(row["DT_REFERENCIA"])
        tp = str(row["TP_FLUXO"]).upper()
        vl = float(row["VL_FLUXO"] or 0.0)
        cota_flow = _cota_no_dia_anterior(dt_flow)
        delta_vl = vl if tp == "APORTE" else -vl
        delta_qt = delta_vl / cota_flow if abs(cota_flow) > 1e-12 else 0.0

        if tp == "APORTE":
            item["VL_APORTADO_BRUTO"] += vl
        else:
            item["VL_RESGATADO_BRUTO"] += vl

        item["VL_INVERTIDO_LIQ"] += delta_vl
        item["QT_COTAS"] += delta_qt

    items: list[dict] = []
    for rec in saldo.values():
        vl_pl_cotista = rec["QT_COTAS"] * cota_atual
        vl_pnl = vl_pl_cotista - rec["VL_INVERTIDO_LIQ"]
        items.append({
            **rec,
            "VL_COTA": cota_atual,
            "VL_PL_COTISTA": vl_pl_cotista,
            "VL_PNL_COTISTA": vl_pnl,
        })

    items.sort(key=lambda x: x["NM_TITULAR"])
    return items, cota_atual


def recompute_cotistas_posicao_diaria_sync(fundo_id: int, dt_referencia: Optional[str] = None) -> dict:
    """Recalcula e persiste posição diária de todos os cotistas."""
    if dt_referencia:
        datas = [dt_referencia]
    else:
        cota_dates_df = query(
            "SELECT DT_REFERENCIA FROM FAT_FUNDO_COTA_DIARIA WHERE ID_FUNDO = ? ORDER BY DT_REFERENCIA",
            params=(fundo_id,),
        )
        datas = [str(r["DT_REFERENCIA"]) for r in cota_dates_df.to_dict("records")]

    total_rows = 0
    with managed_connection() as conn:
        for dt_base in datas:
            items, _ = _compute_cotistas_posicao_snapshot(fundo_id=fundo_id, dt_base=dt_base)
            conn.execute(
                "DELETE FROM FAT_COTISTA_POSICAO_DIARIA WHERE ID_FUNDO = ? AND DT_REFERENCIA = ?",
                (fundo_id, dt_base),
            )
            for item in items:
                conn.execute(
                    """
                    INSERT INTO FAT_COTISTA_POSICAO_DIARIA (
                        ID_FUNDO, ID_TITULAR, DT_REFERENCIA, NM_TITULAR,
                        VL_COTA, VL_APORTADO_BRUTO, VL_RESGATADO_BRUTO,
                        VL_INVERTIDO_LIQ, QT_COTAS, VL_PL_COTISTA, VL_PNL_COTISTA, DT_CARGA
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fundo_id,
                        int(item["ID_TITULAR"]),
                        dt_base,
                        item.get("NM_TITULAR"),
                        float(item.get("VL_COTA") or 0.0),
                        float(item.get("VL_APORTADO_BRUTO") or 0.0),
                        float(item.get("VL_RESGATADO_BRUTO") or 0.0),
                        float(item.get("VL_INVERTIDO_LIQ") or 0.0),
                        float(item.get("QT_COTAS") or 0.0),
                        float(item.get("VL_PL_COTISTA") or 0.0),
                        float(item.get("VL_PNL_COTISTA") or 0.0),
                        _now_sp_str(),
                    ),
                )
                total_rows += 1

    return {"ID_FUNDO": fundo_id, "QT_DIAS": len(datas), "QT_ROWS": total_rows}


# ── Série de retorno ─────────────────────────────────────────────────────────

def compute_retorno_serie_sync(
    fundo_id: int,
    dt_inicio: Optional[str] = None,
    dt_fim: Optional[str] = None,
) -> dict:
    """Série de retorno diário + acumulado baseada na cota (imune a fluxos)."""
    filtros = ["ID_FUNDO = ?"]
    params: list = [fundo_id]
    if dt_inicio:
        filtros.append("DT_REFERENCIA >= ?")
        params.append(dt_inicio)
    if dt_fim:
        filtros.append("DT_REFERENCIA <= ?")
        params.append(dt_fim)

    where = " AND ".join(filtros)
    df = query(
        f"SELECT DT_REFERENCIA, VL_COTA FROM FAT_FUNDO_COTA_DIARIA WHERE {where} ORDER BY DT_REFERENCIA",
        params=tuple(params),
    )

    records = df.to_dict("records")
    if not records:
        return {"items": [], "total": 0}

    cota_inicial_seed = query_scalar(
        """
        SELECT VL_COTA FROM FAT_FUNDO_COTA_DIARIA
        WHERE ID_FUNDO = ? AND CD_METODO LIKE '%seed%'
        ORDER BY DT_REFERENCIA ASC LIMIT 1
        """,
        params=(fundo_id,),
    )
    cota_base = float(cota_inicial_seed or 1.0)
    if abs(cota_base) <= 1e-12:
        cota_base = 1.0

    items: list[dict] = []
    cota_anterior = cota_base

    for row in records:
        cota = float(row["VL_COTA"] or 0.0)
        retorno_dia = (cota / cota_anterior - 1) if abs(cota_anterior) > 1e-12 else 0.0
        retorno_acum = (cota / cota_base - 1) if abs(cota_base) > 1e-12 else 0.0
        items.append({
            "DT_REFERENCIA": row["DT_REFERENCIA"],
            "VL_COTA": cota,
            "RETORNO_DIA_PCT": round(retorno_dia * 100, 6),
            "RETORNO_ACUM_PCT": round(retorno_acum * 100, 6),
        })
        cota_anterior = cota if abs(cota) > 1e-12 else cota_anterior

    return {"items": items, "total": len(items)}
