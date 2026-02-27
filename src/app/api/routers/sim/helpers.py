"""
sim/helpers.py — Utilitários de data/hora, entidade e câmbio do simulador.
"""

import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.services.db_connection import managed_connection, query, query_scalar

logger = logging.getLogger("app.api.simulador")
TZ_BR = ZoneInfo("America/Sao_Paulo")


# ── Helpers de data/hora ─────────────────────────────────────────────────────

def _now_sp() -> datetime:
    return datetime.now(TZ_BR)


def _now_sp_str() -> str:
    return _now_sp().strftime("%Y-%m-%d %H:%M:%S")


def _iso_date_sp(value: Optional[datetime] = None) -> str:
    return (value or _now_sp()).date().isoformat()


# ── Helpers de entidade ──────────────────────────────────────────────────────

def _get_or_create_legacy_entities() -> tuple[int, int]:
    titular_id = query_scalar("SELECT ID_TITULAR FROM DIM_TITULAR WHERE NM_TITULAR = 'LEGADO' LIMIT 1")
    corretora_id = query_scalar("SELECT ID_CORRETORA FROM DIM_CORRETORA WHERE NM_CORRETORA = 'LEGADO' LIMIT 1")
    now_sp = _now_sp_str()

    with managed_connection() as conn:
        if not titular_id:
            cur = conn.execute(
                """
                INSERT INTO DIM_TITULAR (NM_TITULAR, NR_DOCUMENTO, ST_ATIVO, DT_CRIACAO, DT_ATUALIZACAO)
                VALUES ('LEGADO', NULL, 1, ?, ?)
                """,
                (now_sp, now_sp),
            )
            titular_id = cur.lastrowid

        if not corretora_id:
            cur = conn.execute(
                """
                INSERT INTO DIM_CORRETORA (NM_CORRETORA, CD_CORRETORA, ST_ATIVO, DT_CRIACAO, DT_ATUALIZACAO)
                VALUES ('LEGADO', 'LEGADO', 1, ?, ?)
                """,
                (now_sp, now_sp),
            )
            corretora_id = cur.lastrowid

    return int(titular_id), int(corretora_id)


def _entity_exists(table: str, id_col: str, value: int) -> bool:
    return bool(query_scalar(f"SELECT COUNT(*) FROM {table} WHERE {id_col} = ?", params=(value,)))


def _list_active_fundo_ids() -> list[int]:
    df = query("SELECT ID_FUNDO FROM DIM_FUNDO WHERE COALESCE(ST_ATIVO, 1) = 1 ORDER BY ID_FUNDO")
    if df.empty:
        return []
    return [int(v) for v in df["ID_FUNDO"].tolist()]


# ── Helpers de moeda / câmbio ────────────────────────────────────────────────

def _normalize_currency(value: Optional[str]) -> str:
    cur = (value or "BRL").strip().upper()
    return cur or "BRL"


def _fx_pair_code(currency: str) -> str:
    return f"{currency}BRL"


def _resolve_fx_asset_ids(currencies: set[str]) -> dict[str, int]:
    normalized = {_normalize_currency(c) for c in currencies if _normalize_currency(c) != "BRL"}
    if not normalized:
        return {}

    pair_codes = [_fx_pair_code(c) for c in normalized]
    placeholders = ",".join(["?"] * len(pair_codes))
    df = query(
        f"""
        SELECT ID_ATIVO, UPPER(TRIM(CD_ATIVO)) AS CD_ATIVO
        FROM DIM_ATIVO
        WHERE UPPER(TRIM(CD_ATIVO)) IN ({placeholders})
        """,
        params=tuple(pair_codes),
    )

    mapping: dict[str, int] = {}
    for row in df.to_dict("records"):
        cd = str(row["CD_ATIVO"]).upper().strip()
        if not cd.endswith("BRL"):
            continue
        currency = cd[:-3]
        if currency and currency not in mapping:
            mapping[currency] = int(row["ID_ATIVO"])
    return mapping


def _get_fx_rate(
    currency: str,
    dt_ref: Optional[str],
    fx_asset_ids: dict[str, int],
    cache: dict[tuple[str, Optional[str]], float],
) -> float:
    cur = _normalize_currency(currency)
    key = (cur, dt_ref)
    if key in cache:
        return cache[key]

    if cur == "BRL":
        cache[key] = 1.0
        return 1.0

    fx_asset_id = fx_asset_ids.get(cur)
    if fx_asset_id is None:
        logger.warning("Par cambial não cadastrado para moeda=%s (esperado: %s)", cur, _fx_pair_code(cur))
        cache[key] = 1.0
        return 1.0

    if dt_ref:
        fx_hist = query_scalar(
            """
            SELECT COALESCE(f.VL_FECHAMENTO_AJ, f.VL_FECHAMENTO)
            FROM FAT_ATIVO_PRECO f
            WHERE f.ID_ATIVO = ?
              AND f.DT_REFERENCIA <= ?
            ORDER BY f.DT_REFERENCIA DESC
            LIMIT 1
            """,
            params=(fx_asset_id, dt_ref),
        )
        if fx_hist is not None:
            cache[key] = float(fx_hist)
            return cache[key]

    fx_live = query_scalar(
        """
        SELECT fl.VL_PRECO_ATUAL
        FROM FAT_PRICING_LIVE fl
        WHERE fl.ID_ATIVO = ?
        LIMIT 1
        """,
        params=(fx_asset_id,),
    )
    if fx_live is not None:
        cache[key] = float(fx_live)
        return cache[key]

    fx_latest_hist = query_scalar(
        """
        SELECT COALESCE(f.VL_FECHAMENTO_AJ, f.VL_FECHAMENTO)
        FROM FAT_ATIVO_PRECO f
        WHERE f.ID_ATIVO = ?
        ORDER BY f.DT_REFERENCIA DESC
        LIMIT 1
        """,
        params=(fx_asset_id,),
    )
    if fx_latest_hist is not None:
        cache[key] = float(fx_latest_hist)
        return cache[key]

    logger.warning("FX sem preço para moeda=%s (ID_ATIVO=%s). Assumindo 1.0", cur, fx_asset_id)
    cache[key] = 1.0
    return 1.0


# ── Validação de trade ───────────────────────────────────────────────────────

def _normalize_trade_payload(payload) -> tuple[str, str, str]:
    """Valida e normaliza payload de trade. Retorna (side, dt_hora_exec, dt_trade)."""
    side = payload.SIDE.strip().upper()
    if side not in {"BUY", "SELL"}:
        raise HTTPException(status_code=422, detail="SIDE inválido. Use BUY ou SELL")

    if payload.QTD <= 0 or payload.PU <= 0:
        raise HTTPException(status_code=422, detail="QTD e PU devem ser maiores que zero")

    exists_portfolio = query_scalar(
        "SELECT COUNT(*) FROM DIM_CARTEIRA WHERE ID_CARTEIRA = ?",
        params=(payload.ID_PORTFOLIO,),
    )
    if not exists_portfolio:
        raise HTTPException(status_code=404, detail=f"Portfolio {payload.ID_PORTFOLIO} não encontrado")

    exists_ativo = query_scalar(
        "SELECT COUNT(*) FROM DIM_ATIVO WHERE ID_ATIVO = ?",
        params=(payload.ID_ATIVO,),
    )
    if not exists_ativo:
        raise HTTPException(status_code=404, detail=f"Ativo {payload.ID_ATIVO} não encontrado")

    dt_hora_exec = payload.DT_HORA_EXEC or f"{payload.DT_TRADE} 00:00:00"
    dt_trade = dt_hora_exec[:10]
    return side, dt_hora_exec, dt_trade
