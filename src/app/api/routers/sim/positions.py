"""
sim/positions.py — Motor de posições, mark-to-market e posição diária.
"""

import logging
import math
from typing import Optional

from app.services.db_connection import managed_connection, query

from app.api.routers.sim.helpers import (
    _normalize_currency,
    _resolve_fx_asset_ids,
    _get_fx_rate,
    _now_sp_str,
    _iso_date_sp,
)

logger = logging.getLogger("app.api.simulador")


def _build_positions_response(
    trades_records: list[dict],
    owner_key: str,
    owner_id: int,
    dt_mark_to_market: Optional[str] = None,
) -> dict:
    """Calcula posição consolidada a partir de trades.

    Para cada ativo:
    - Preço médio ponderado (weighted avg cost)
    - PnL Realizado na venda/cobertura
    - PnL Aberto = (preço_atual − PM) × qtd
    - Valor de Mercado = qtd × preço_atual
    """
    if dt_mark_to_market:
        prices_df = query(
            """
            SELECT
                da.ID_ATIVO,
                da.CD_ATIVO,
                da.MOEDA,
                da.PRECO_ONLINE,
                (
                    SELECT COALESCE(f.VL_FECHAMENTO_AJ, f.VL_FECHAMENTO)
                    FROM FAT_ATIVO_PRECO f
                    WHERE f.ID_ATIVO = da.ID_ATIVO
                      AND f.DT_REFERENCIA <= ?
                    ORDER BY f.DT_REFERENCIA DESC
                    LIMIT 1
                ) AS PRECO_ATUAL
            FROM DIM_ATIVO da
            """,
            params=(dt_mark_to_market,),
        )
    else:
        prices_df = query(
            """
            WITH last_hist AS (
                SELECT f.ID_ATIVO, f.VL_FECHAMENTO_AJ, f.VL_FECHAMENTO
                FROM FAT_ATIVO_PRECO f
                JOIN (
                    SELECT ID_ATIVO, MAX(DT_REFERENCIA) AS DT_REF_MAX
                    FROM FAT_ATIVO_PRECO
                    GROUP BY ID_ATIVO
                ) m ON m.ID_ATIVO = f.ID_ATIVO AND m.DT_REF_MAX = f.DT_REFERENCIA
            )
            SELECT
                da.ID_ATIVO,
                da.CD_ATIVO,
                da.MOEDA,
                da.PRECO_ONLINE,
                COALESCE(fl.VL_PRECO_ATUAL, lh.VL_FECHAMENTO_AJ, lh.VL_FECHAMENTO) AS PRECO_ATUAL
            FROM DIM_ATIVO da
            LEFT JOIN FAT_PRICING_LIVE fl ON fl.ID_ATIVO = da.ID_ATIVO
            LEFT JOIN last_hist lh ON lh.ID_ATIVO = da.ID_ATIVO
            """
        )

    price_map = {
        int(r["ID_ATIVO"]): {
            "PRECO_ATUAL": r["PRECO_ATUAL"],
            "MOEDA": r["MOEDA"],
            "PRECO_ONLINE": r.get("PRECO_ONLINE"),
        }
        for r in prices_df.to_dict("records")
    }

    state: dict[int, dict] = {}
    fx_cache: dict[tuple[str, Optional[str]], float] = {}
    currencies = {
        _normalize_currency(row.get("MOEDA"))
        for row in trades_records
        if _normalize_currency(row.get("MOEDA")) != "BRL"
    }
    fx_asset_ids = _resolve_fx_asset_ids(currencies)

    def _sign(value: float) -> int:
        return 1 if value > 0 else (-1 if value < 0 else 0)

    for tr in trades_records:
        id_ativo = int(tr["ID_ATIVO"])
        rec = state.setdefault(id_ativo, {
            owner_key: owner_id,
            "ID_ATIVO": id_ativo,
            "CD_ATIVO": tr["CD_ATIVO"],
            "MOEDA": _normalize_currency(tr.get("MOEDA")),
            "QTD_LIQ": 0.0,
            "PRECO_MEDIO": None,
            "PNL_REALIZADO": 0.0,
            "CUSTO_TOTAL": 0.0,
        })

        qty = float(tr["QTD"])
        dt_trade = str(tr["DT_HORA_EXEC"])[:10]
        fx_trade = _get_fx_rate(rec["MOEDA"], dt_trade, fx_asset_ids, fx_cache)
        pu = float(tr["PU"]) * fx_trade
        custo = float(tr["CUSTO"] or 0) * fx_trade
        side = str(tr["SIDE"]).upper()

        trade_qty = qty if side in ("BUY", "COVER") else -qty
        old_qty = float(rec["QTD_LIQ"])
        old_avg = rec["PRECO_MEDIO"]

        rec["CUSTO_TOTAL"] += custo
        rec["PNL_REALIZADO"] -= custo

        # Abertura ou adição à mesma direção
        if old_qty == 0 or _sign(old_qty) == _sign(trade_qty):
            base = abs(old_qty)
            add = abs(trade_qty)
            new_qty = old_qty + trade_qty
            new_avg = pu if base == 0 else ((base * float(old_avg)) + (add * pu)) / (base + add)
            rec["QTD_LIQ"] = new_qty
            rec["PRECO_MEDIO"] = None if new_qty == 0 else new_avg
            continue

        # Redução / encerramento / virada (flip)
        close_qty = min(abs(old_qty), abs(trade_qty))
        if old_qty > 0 and trade_qty < 0:
            rec["PNL_REALIZADO"] += (pu - float(old_avg)) * close_qty
        elif old_qty < 0 and trade_qty > 0:
            rec["PNL_REALIZADO"] += (float(old_avg) - pu) * close_qty

        residual = abs(trade_qty) - close_qty
        if residual <= 1e-12:
            new_qty = old_qty + trade_qty
            rec["QTD_LIQ"] = new_qty
            rec["PRECO_MEDIO"] = None if abs(new_qty) <= 1e-12 else old_avg
        else:
            new_qty = residual if trade_qty > 0 else -residual
            rec["QTD_LIQ"] = new_qty
            rec["PRECO_MEDIO"] = pu

    # ── Mark-to-market ───────────────────────────────────────────────────
    items: list[dict] = []

    for id_ativo, rec in state.items():
        qtd = float(rec["QTD_LIQ"])
        if abs(qtd) <= 1e-12:
            continue

        px_info = price_map.get(id_ativo, {})
        preco_atual_local = px_info.get("PRECO_ATUAL")

        fx_atual = _get_fx_rate(rec["MOEDA"], dt_mark_to_market, fx_asset_ids, fx_cache)
        pm = rec["PRECO_MEDIO"]

        preco_online = px_info.get("PRECO_ONLINE")
        has_market_price = (
            preco_atual_local is not None
            and not (isinstance(preco_atual_local, float) and math.isnan(preco_atual_local))
        )

        # Alertas sobre precificação
        alertas: list[str] = []
        if not preco_online or preco_online != 1:
            alertas.append("Ativo sem 'Preço Online' ativado — preço pode estar desatualizado.")
        if not has_market_price:
            alertas.append("Sem preço de mercado disponível — usando Preço Médio como referência.")

        if has_market_price:
            # Preço de mercado em moeda local → converter para BRL
            preco_atual = float(preco_atual_local) * fx_atual
        elif pm is not None:
            # Fallback: PM já está em BRL — usar diretamente, sem re-converter
            preco_atual = float(pm)
        else:
            preco_atual = None

        valor_mercado = (qtd * float(preco_atual)) if preco_atual is not None else 0.0
        pnl_aberto = ((float(preco_atual) - float(pm)) * qtd) if (preco_atual is not None and pm is not None) else 0.0
        pnl_total = float(pnl_aberto) + float(rec["PNL_REALIZADO"])

        items.append({
            owner_key: rec[owner_key],
            "ID_ATIVO": rec["ID_ATIVO"],
            "CD_ATIVO": rec["CD_ATIVO"],
            "MOEDA": rec["MOEDA"],
            "FX_ATUAL": fx_atual,
            "QTD_LIQ": qtd,
            "PRECO_MEDIO": pm,
            "PRECO_ATUAL": preco_atual,
            "PRECO_ONLINE": bool(preco_online and preco_online == 1),
            "SEM_PRECO_MERCADO": not has_market_price,
            "ALERTAS": alertas if alertas else None,
            "CUSTO_TOTAL": rec["CUSTO_TOTAL"],
            "VALOR_MERCADO": valor_mercado,
            "PNL_REALIZADO": rec["PNL_REALIZADO"],
            "PNL_ABERTO": pnl_aberto,
            "PNL_TOTAL": pnl_total,
        })

    items.sort(key=lambda r: r["CD_ATIVO"])
    vm_total = float(sum((r.get("VALOR_MERCADO") or 0.0) for r in items))
    pl_aberto_total = float(sum((r.get("PNL_ABERTO") or 0.0) for r in items))
    pl_real_total = float(sum((r.get("PNL_REALIZADO") or 0.0) for r in items))

    return {
        "items": items,
        "total": len(items),
        "resumo": {
            "VALOR_MERCADO_TOTAL": vm_total,
            "PNL_ABERTO_TOTAL": pl_aberto_total,
            "PNL_REALIZADO_TOTAL": pl_real_total,
            "PNL_TOTAL": pl_aberto_total + pl_real_total,
        },
    }


# ── Posições de fundo (agrega carteiras) ────────────────────────────────────

def _get_fundo_positions_payload_sync(fundo_id: int, dt_ref: Optional[str] = None) -> dict:
    """Posição consolidada do fundo (todas as carteiras vinculadas)."""
    sql = """
        WITH carteira_fundo AS (
            SELECT DISTINCT rfc.ID_CARTEIRA
            FROM RL_FUNDO_CARTEIRA rfc
            WHERE rfc.ID_FUNDO = ?
              AND (rfc.ST_ATIVO = 1 OR rfc.DT_FIM IS NULL)
        )
        SELECT
            t.ID_ATIVO,
            da.CD_ATIVO,
            da.MOEDA,
            COALESCE(t.DT_HORA_EXEC, t.DT_TRADE || ' 00:00:00') AS DT_HORA_EXEC,
            t.SIDE,
            t.QTD,
            t.PU,
            COALESCE(t.CUSTO, 0) AS CUSTO
        FROM FAT_CARTEIRA_TRADE t
        JOIN carteira_fundo cf ON cf.ID_CARTEIRA = t.ID_CARTEIRA
        JOIN DIM_ATIVO da ON da.ID_ATIVO = t.ID_ATIVO
    """
    params: list = [fundo_id]
    if dt_ref:
        sql += " WHERE substr(COALESCE(t.DT_HORA_EXEC, t.DT_TRADE || ' 00:00:00'), 1, 10) <= ? "
        params.append(dt_ref)
    sql += " ORDER BY DT_HORA_EXEC ASC, t.ID_TRADE ASC "

    trades_df = query(sql, params=tuple(params))
    return _build_positions_response(
        trades_records=trades_df.to_dict("records"),
        owner_key="ID_FUNDO",
        owner_id=fundo_id,
        dt_mark_to_market=dt_ref,
    )


# ── Posição diária de carteira ───────────────────────────────────────────────

def recompute_carteira_posicao_diaria_sync(portfolio_id: int, dt_ref: Optional[str] = None) -> dict:
    """Recalcula e persiste posição diária de uma carteira."""
    dt_base = dt_ref or _iso_date_sp()
    trades_df = query(
        """
        SELECT
            t.ID_ATIVO,
            da.CD_ATIVO,
            da.MOEDA,
            COALESCE(t.DT_HORA_EXEC, t.DT_TRADE || ' 00:00:00') AS DT_HORA_EXEC,
            t.SIDE,
            t.QTD,
            t.PU,
            COALESCE(t.CUSTO, 0) AS CUSTO
        FROM FAT_CARTEIRA_TRADE t
        JOIN DIM_ATIVO da ON da.ID_ATIVO = t.ID_ATIVO
        WHERE t.ID_CARTEIRA = ?
          AND substr(COALESCE(t.DT_HORA_EXEC, t.DT_TRADE || ' 00:00:00'), 1, 10) <= ?
        ORDER BY DT_HORA_EXEC ASC, t.ID_TRADE ASC
        """,
        params=(portfolio_id, dt_base),
    )

    payload = _build_positions_response(
        trades_records=trades_df.to_dict("records"),
        owner_key="ID_PORTFOLIO",
        owner_id=portfolio_id,
        dt_mark_to_market=dt_base,
    )
    items = payload.get("items", [])

    with managed_connection() as conn:
        conn.execute(
            "DELETE FROM FAT_CARTEIRA_POSICAO_DIARIA WHERE ID_CARTEIRA = ? AND DT_REFERENCIA = ?",
            (portfolio_id, dt_base),
        )
        for item in items:
            conn.execute(
                """
                INSERT INTO FAT_CARTEIRA_POSICAO_DIARIA (
                    ID_CARTEIRA, DT_REFERENCIA, ID_ATIVO, CD_ATIVO, MOEDA,
                    FX_ATUAL, QTD_LIQ, PRECO_MEDIO, PRECO_ATUAL, CUSTO_TOTAL,
                    VALOR_MERCADO, PNL_REALIZADO, PNL_ABERTO, PNL_TOTAL, DT_CARGA
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    portfolio_id,
                    dt_base,
                    int(item["ID_ATIVO"]),
                    item["CD_ATIVO"],
                    item.get("MOEDA"),
                    float(item.get("FX_ATUAL") or 1.0),
                    float(item.get("QTD_LIQ") or 0.0),
                    item.get("PRECO_MEDIO"),
                    item.get("PRECO_ATUAL"),
                    item.get("CUSTO_TOTAL"),
                    item.get("VALOR_MERCADO"),
                    item.get("PNL_REALIZADO"),
                    item.get("PNL_ABERTO"),
                    item.get("PNL_TOTAL"),
                    _now_sp_str(),
                ),
            )

    return {
        "ID_PORTFOLIO": portfolio_id,
        "DT_REFERENCIA": dt_base,
        "TOTAL_ATIVOS": len(items),
        "RESUMO": payload.get("resumo", {}),
    }
