"""
routers/simulador.py — Endpoints do simulador de carteiras (Sprint 1).

- Carteiras simuladas
- Operações (trades) manuais
- Posições consolidadas
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.models.common import APIResponse
from app.services.db_connection import managed_connection, query, query_scalar

logger = logging.getLogger("app.api.simulador")
router = APIRouter(prefix="/api/sim", tags=["Simulador"])
TZ_BR = ZoneInfo("America/Sao_Paulo")


def _now_sp() -> datetime:
    return datetime.now(TZ_BR)


def _now_sp_str() -> str:
    return _now_sp().strftime("%Y-%m-%d %H:%M:%S")


def _iso_date_sp(value: Optional[datetime] = None) -> str:
    return (value or _now_sp()).date().isoformat()


class PortfolioInput(BaseModel):
    NM_PORTFOLIO: str = Field(min_length=1, max_length=120)
    DT_INICIO: str = Field(default_factory=lambda: date.today().isoformat())
    BENCHMARK: Optional[str] = None
    MOEDA_BASE: str = "BRL"
    ST_ATIVO: int = 1
    ID_FUNDO: Optional[int] = None
    ID_TITULAR: Optional[int] = None
    ID_CORRETORA: Optional[int] = None
    CONTA_REF: Optional[str] = None


class FundoInput(BaseModel):
    NM_FUNDO: str = Field(min_length=1, max_length=120)
    DS_ESTRATEGIA: Optional[str] = None
    BENCHMARK: Optional[str] = None
    MOEDA_BASE: str = "BRL"
    ST_ATIVO: int = 1


class TitularInput(BaseModel):
    NM_TITULAR: str = Field(min_length=1, max_length=120)
    NR_DOCUMENTO: Optional[str] = None
    ST_ATIVO: int = 1


class CorretoraInput(BaseModel):
    NM_CORRETORA: str = Field(min_length=1, max_length=120)
    CD_CORRETORA: Optional[str] = None
    ST_ATIVO: int = 1


class TradeInput(BaseModel):
    ID_PORTFOLIO: int
    ID_ATIVO: int
    DT_HORA_EXEC: Optional[str] = None
    DT_TRADE: str = Field(default_factory=lambda: date.today().isoformat())
    SIDE: str = Field(description="BUY | SELL | SHORT | COVER")
    QTD: float
    PU: float
    CUSTO: float = 0.0
    OBSERVACAO: Optional[str] = None


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


def _normalize_trade_payload(payload: TradeInput) -> tuple[str, str, str]:
    side = payload.SIDE.strip().upper()
    if side not in {"BUY", "SELL", "SHORT", "COVER"}:
        raise HTTPException(status_code=422, detail="SIDE inválido. Use BUY, SELL, SHORT ou COVER")

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


def _build_positions_response(
    trades_records: list[dict],
    owner_key: str,
    owner_id: int,
    dt_mark_to_market: Optional[str] = None,
) -> dict:
    if dt_mark_to_market:
        prices_df = query(
            """
            SELECT
                da.ID_ATIVO,
                da.CD_ATIVO,
                da.MOEDA,
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

        if old_qty == 0 or _sign(old_qty) == _sign(trade_qty):
            base = abs(old_qty)
            add = abs(trade_qty)
            new_qty = old_qty + trade_qty
            new_avg = pu if base == 0 else ((base * float(old_avg)) + (add * pu)) / (base + add)
            rec["QTD_LIQ"] = new_qty
            rec["PRECO_MEDIO"] = None if new_qty == 0 else new_avg
            continue

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

    items: list[dict] = []
    for id_ativo, rec in state.items():
        qtd = float(rec["QTD_LIQ"])
        if abs(qtd) <= 1e-12:
            continue

        px_info = price_map.get(id_ativo, {})
        preco_atual_local = px_info.get("PRECO_ATUAL")
        fx_atual = _get_fx_rate(rec["MOEDA"], dt_mark_to_market, fx_asset_ids, fx_cache)
        preco_atual = (float(preco_atual_local) * fx_atual) if preco_atual_local is not None else None
        pm = rec["PRECO_MEDIO"]
        valor_mercado = (qtd * float(preco_atual)) if preco_atual is not None else None
        pnl_aberto = ((float(preco_atual) - float(pm)) * qtd) if (preco_atual is not None and pm is not None) else None
        pnl_total = (pnl_aberto if pnl_aberto is not None else 0.0) + float(rec["PNL_REALIZADO"])

        items.append({
            owner_key: rec[owner_key],
            "ID_ATIVO": rec["ID_ATIVO"],
            "CD_ATIVO": rec["CD_ATIVO"],
            "MOEDA": rec["MOEDA"],
            "FX_ATUAL": fx_atual,
            "QTD_LIQ": qtd,
            "PRECO_MEDIO": pm,
            "PRECO_ATUAL": preco_atual,
            "CUSTO_TOTAL": rec["CUSTO_TOTAL"],
            "VALOR_MERCADO": valor_mercado,
            "PNL_REALIZADO": rec["PNL_REALIZADO"],
            "PNL_ABERTO": pnl_aberto,
            "PNL_TOTAL": pnl_total,
        })

    items.sort(key=lambda r: r["CD_ATIVO"])
    pl_total = float(sum((r.get("PNL_ABERTO") or 0.0) for r in items))
    vm_total = float(sum((r.get("VALOR_MERCADO") or 0.0) for r in items))
    pl_real_total = float(sum((r.get("PNL_REALIZADO") or 0.0) for r in items))

    return {
        "items": items,
        "total": len(items),
        "resumo": {
            "VALOR_MERCADO_TOTAL": vm_total,
            "PNL_ABERTO_TOTAL": pl_total,
            "PNL_REALIZADO_TOTAL": pl_real_total,
            "PNL_TOTAL": pl_total + pl_real_total,
        },
    }


@router.get("/portfolios", response_model=APIResponse)
async def listar_portfolios():
    """Lista carteiras simuladas."""
    try:
        df = query("""
            WITH link AS (
                SELECT
                    rfc.ID_CARTEIRA,
                    rfc.ID_FUNDO,
                    rfc.DT_INICIO,
                    ROW_NUMBER() OVER (
                        PARTITION BY rfc.ID_CARTEIRA
                        ORDER BY rfc.DT_INICIO DESC
                    ) AS RN
                FROM RL_FUNDO_CARTEIRA rfc
                WHERE rfc.ST_ATIVO = 1 OR rfc.DT_FIM IS NULL
            )
            SELECT
                dc.ID_CARTEIRA AS ID_PORTFOLIO,
                dc.NM_CARTEIRA AS NM_PORTFOLIO,
                COALESCE(lk.DT_INICIO, substr(dc.DT_CRIACAO, 1, 10)) AS DT_INICIO,
                df.BENCHMARK,
                dc.MOEDA_BASE,
                dc.ST_ATIVO,
                                lk.ID_FUNDO,
                                df.NM_FUNDO,
                                dc.ID_TITULAR,
                                dt.NM_TITULAR,
                                dc.ID_CORRETORA,
                                dcor.NM_CORRETORA,
                                dc.CONTA_REF,
                dc.DT_CRIACAO,
                dc.DT_ATUALIZACAO
            FROM DIM_CARTEIRA dc
            LEFT JOIN link lk
              ON lk.ID_CARTEIRA = dc.ID_CARTEIRA
             AND lk.RN = 1
            LEFT JOIN DIM_FUNDO df
              ON df.ID_FUNDO = lk.ID_FUNDO
                        LEFT JOIN DIM_TITULAR dt
                            ON dt.ID_TITULAR = dc.ID_TITULAR
                        LEFT JOIN DIM_CORRETORA dcor
                            ON dcor.ID_CORRETORA = dc.ID_CORRETORA
            ORDER BY dc.ID_CARTEIRA DESC
        """)
        items = df.to_dict("records")
        return APIResponse(data={"items": items, "total": len(items)})
    except Exception as exc:
        logger.exception("Erro em GET /sim/portfolios")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/fundos", response_model=APIResponse)
async def listar_fundos():
    try:
        df = query(
            """
            SELECT
                ID_FUNDO,
                NM_FUNDO,
                DS_ESTRATEGIA,
                BENCHMARK,
                MOEDA_BASE,
                ST_ATIVO,
                DT_CRIACAO,
                DT_ATUALIZACAO
            FROM DIM_FUNDO
            ORDER BY ID_FUNDO DESC
            """
        )
        items = df.to_dict("records")
        return APIResponse(data={"items": items, "total": len(items)})
    except Exception as exc:
        logger.exception("Erro em GET /sim/fundos")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fundos", response_model=APIResponse, status_code=201)
async def criar_fundo(payload: FundoInput):
    try:
        now_sp = _now_sp_str()
        with managed_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO DIM_FUNDO
                    (NM_FUNDO, DS_ESTRATEGIA, BENCHMARK, MOEDA_BASE, ST_ATIVO, DT_CRIACAO, DT_ATUALIZACAO)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.NM_FUNDO.strip(),
                    payload.DS_ESTRATEGIA,
                    payload.BENCHMARK,
                    payload.MOEDA_BASE,
                    payload.ST_ATIVO,
                    now_sp,
                    now_sp,
                ),
            )
            new_id = cur.lastrowid

        return APIResponse(data={"ID_FUNDO": new_id})
    except Exception as exc:
        logger.exception("Erro em POST /sim/fundos")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/titulares", response_model=APIResponse)
async def listar_titulares():
    try:
        df = query(
            """
            SELECT
                ID_TITULAR,
                NM_TITULAR,
                NR_DOCUMENTO,
                ST_ATIVO,
                DT_CRIACAO,
                DT_ATUALIZACAO
            FROM DIM_TITULAR
            ORDER BY ID_TITULAR DESC
            """
        )
        items = df.to_dict("records")
        return APIResponse(data={"items": items, "total": len(items)})
    except Exception as exc:
        logger.exception("Erro em GET /sim/titulares")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/titulares", response_model=APIResponse, status_code=201)
async def criar_titular(payload: TitularInput):
    try:
        now_sp = _now_sp_str()
        with managed_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO DIM_TITULAR
                    (NM_TITULAR, NR_DOCUMENTO, ST_ATIVO, DT_CRIACAO, DT_ATUALIZACAO)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload.NM_TITULAR.strip(),
                    payload.NR_DOCUMENTO,
                    payload.ST_ATIVO,
                    now_sp,
                    now_sp,
                ),
            )
            new_id = cur.lastrowid

        return APIResponse(data={"ID_TITULAR": new_id})
    except Exception as exc:
        logger.exception("Erro em POST /sim/titulares")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/corretoras", response_model=APIResponse)
async def listar_corretoras():
    try:
        df = query(
            """
            SELECT
                ID_CORRETORA,
                NM_CORRETORA,
                CD_CORRETORA,
                ST_ATIVO,
                DT_CRIACAO,
                DT_ATUALIZACAO
            FROM DIM_CORRETORA
            ORDER BY ID_CORRETORA DESC
            """
        )
        items = df.to_dict("records")
        return APIResponse(data={"items": items, "total": len(items)})
    except Exception as exc:
        logger.exception("Erro em GET /sim/corretoras")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/corretoras", response_model=APIResponse, status_code=201)
async def criar_corretora(payload: CorretoraInput):
    try:
        now_sp = _now_sp_str()
        with managed_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO DIM_CORRETORA
                    (NM_CORRETORA, CD_CORRETORA, ST_ATIVO, DT_CRIACAO, DT_ATUALIZACAO)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload.NM_CORRETORA.strip(),
                    payload.CD_CORRETORA,
                    payload.ST_ATIVO,
                    now_sp,
                    now_sp,
                ),
            )
            new_id = cur.lastrowid

        return APIResponse(data={"ID_CORRETORA": new_id})
    except Exception as exc:
        logger.exception("Erro em POST /sim/corretoras")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/portfolios", response_model=APIResponse, status_code=201)
async def criar_portfolio(payload: PortfolioInput):
    """Cria uma nova carteira simulada."""
    try:
        titular_id, corretora_id = _get_or_create_legacy_entities()

        id_titular = payload.ID_TITULAR or titular_id
        id_corretora = payload.ID_CORRETORA or corretora_id

        if not _entity_exists("DIM_TITULAR", "ID_TITULAR", id_titular):
            raise HTTPException(status_code=404, detail=f"Titular {id_titular} não encontrado")
        if not _entity_exists("DIM_CORRETORA", "ID_CORRETORA", id_corretora):
            raise HTTPException(status_code=404, detail=f"Corretora {id_corretora} não encontrada")

        with managed_connection() as conn:
            now_sp = _now_sp_str()
            id_fundo = payload.ID_FUNDO
            if id_fundo:
                exists_fundo = conn.execute(
                    "SELECT COUNT(*) FROM DIM_FUNDO WHERE ID_FUNDO = ?",
                    (id_fundo,),
                ).fetchone()[0]
                if not exists_fundo:
                    raise HTTPException(status_code=404, detail=f"Fundo {id_fundo} não encontrado")
            else:
                cur_fundo = conn.execute(
                    """
                    INSERT INTO DIM_FUNDO
                        (NM_FUNDO, DS_ESTRATEGIA, BENCHMARK, MOEDA_BASE, ST_ATIVO, DT_CRIACAO, DT_ATUALIZACAO)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.NM_PORTFOLIO.strip(),
                        "Criado via API simulador",
                        payload.BENCHMARK,
                        payload.MOEDA_BASE,
                        payload.ST_ATIVO,
                        now_sp,
                        now_sp,
                    ),
                )
                id_fundo = cur_fundo.lastrowid

            cur_carteira = conn.execute(
                """
                INSERT INTO DIM_CARTEIRA
                    (ID_TITULAR, ID_CORRETORA, NM_CARTEIRA, CONTA_REF, MOEDA_BASE, ST_ATIVO, DT_CRIACAO, DT_ATUALIZACAO)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    id_titular,
                    id_corretora,
                    payload.NM_PORTFOLIO.strip(),
                    payload.CONTA_REF,
                    payload.MOEDA_BASE,
                    payload.ST_ATIVO,
                    now_sp,
                    now_sp,
                ),
            )
            new_id = cur_carteira.lastrowid

            conn.execute(
                """
                INSERT INTO RL_FUNDO_CARTEIRA
                    (ID_FUNDO, ID_CARTEIRA, DT_INICIO, DT_FIM, ST_ATIVO, DT_CRIACAO, DT_ATUALIZACAO)
                VALUES (?, ?, ?, NULL, 1, ?, ?)
                """,
                (
                    id_fundo,
                    new_id,
                    payload.DT_INICIO,
                    now_sp,
                    now_sp,
                ),
            )

        return APIResponse(data={"ID_PORTFOLIO": new_id})
    except Exception as exc:
        logger.exception("Erro em POST /sim/portfolios")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/portfolios/{portfolio_id}", response_model=APIResponse)
async def excluir_portfolio(portfolio_id: int):
    """Exclui carteira simulada e suas operações."""
    exists_portfolio = query_scalar(
        "SELECT COUNT(*) FROM DIM_CARTEIRA WHERE ID_CARTEIRA = ?",
        params=(portfolio_id,),
    )
    if not exists_portfolio:
        raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} não encontrado")

    try:
        with managed_connection() as conn:
            conn.execute("DELETE FROM FAT_CARTEIRA_TRADE WHERE ID_CARTEIRA = ?", (portfolio_id,))
            conn.execute("DELETE FROM RL_FUNDO_CARTEIRA WHERE ID_CARTEIRA = ?", (portfolio_id,))
            conn.execute("DELETE FROM DIM_CARTEIRA WHERE ID_CARTEIRA = ?", (portfolio_id,))

        return APIResponse(data={"deleted": True, "ID_PORTFOLIO": portfolio_id})
    except Exception as exc:
        logger.exception("Erro em DELETE /sim/portfolios/{portfolio_id}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/trades", response_model=APIResponse, status_code=201)
async def criar_trade(payload: TradeInput):
    """Registra uma operação manual no simulador."""
    side, dt_hora_exec, dt_trade = _normalize_trade_payload(payload)

    try:
        with managed_connection() as conn:
            now_sp = _now_sp_str()
            cur = conn.execute(
                """
                INSERT INTO FAT_CARTEIRA_TRADE
                    (ID_CARTEIRA, ID_ATIVO, DT_HORA_EXEC, DT_TRADE, SIDE, QTD, PU, CUSTO, OBSERVACAO, DT_CARGA)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.ID_PORTFOLIO,
                    payload.ID_ATIVO,
                    dt_hora_exec,
                    dt_trade,
                    side,
                    payload.QTD,
                    payload.PU,
                    payload.CUSTO,
                    payload.OBSERVACAO,
                    now_sp,
                ),
            )
            new_id = cur.lastrowid

        return APIResponse(data={"ID_TRADE": new_id})
    except Exception as exc:
        logger.exception("Erro em POST /sim/trades")
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/trades/{trade_id}", response_model=APIResponse)
async def atualizar_trade(trade_id: int, payload: TradeInput):
    """Atualiza uma operação manual no simulador."""
    side, dt_hora_exec, dt_trade = _normalize_trade_payload(payload)

    exists_trade = query_scalar(
        "SELECT COUNT(*) FROM FAT_CARTEIRA_TRADE WHERE ID_TRADE = ?",
        params=(trade_id,),
    )
    if not exists_trade:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} não encontrada")

    try:
        with managed_connection() as conn:
            conn.execute(
                """
                UPDATE FAT_CARTEIRA_TRADE
                SET
                    ID_CARTEIRA = ?,
                    ID_ATIVO = ?,
                    DT_HORA_EXEC = ?,
                    DT_TRADE = ?,
                    SIDE = ?,
                    QTD = ?,
                    PU = ?,
                    CUSTO = ?,
                    OBSERVACAO = ?
                WHERE ID_TRADE = ?
                """,
                (
                    payload.ID_PORTFOLIO,
                    payload.ID_ATIVO,
                    dt_hora_exec,
                    dt_trade,
                    side,
                    payload.QTD,
                    payload.PU,
                    payload.CUSTO,
                    payload.OBSERVACAO,
                    trade_id,
                ),
            )

        return APIResponse(data={"ID_TRADE": trade_id})
    except Exception as exc:
        logger.exception("Erro em PUT /sim/trades/{trade_id}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/trades/{trade_id}", response_model=APIResponse)
async def excluir_trade(trade_id: int):
    """Exclui uma operação manual no simulador."""
    try:
        with managed_connection() as conn:
            cur = conn.execute(
                "DELETE FROM FAT_CARTEIRA_TRADE WHERE ID_TRADE = ?",
                (trade_id,),
            )

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Trade {trade_id} não encontrada")

        return APIResponse(data={"deleted": True, "ID_TRADE": trade_id})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em DELETE /sim/trades/{trade_id}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/trades", response_model=APIResponse)
async def listar_trades(
    portfolio_id: int = Query(..., description="ID da carteira"),
    dt_inicio: Optional[str] = Query(None),
    dt_fim: Optional[str] = Query(None),
):
    """Lista operações da carteira no período."""
    try:
        if not isinstance(dt_inicio, str):
            dt_inicio = None
        if not isinstance(dt_fim, str):
            dt_fim = None

        filtros = ["t.ID_CARTEIRA = ?"]
        params: list = [portfolio_id]

        if dt_inicio:
            filtros.append("t.DT_TRADE >= ?")
            params.append(dt_inicio)
        if dt_fim:
            filtros.append("t.DT_TRADE <= ?")
            params.append(dt_fim)

        where = " AND ".join(filtros)

        df = query(f"""
            SELECT
                t.ID_TRADE,
                t.ID_CARTEIRA AS ID_PORTFOLIO,
                t.ID_ATIVO,
                da.CD_ATIVO,
                t.DT_HORA_EXEC,
                t.DT_TRADE,
                t.SIDE,
                t.QTD,
                t.PU,
                t.CUSTO,
                t.OBSERVACAO,
                t.DT_CARGA
            FROM FAT_CARTEIRA_TRADE t
            JOIN DIM_ATIVO da ON da.ID_ATIVO = t.ID_ATIVO
            WHERE {where}
            ORDER BY COALESCE(t.DT_HORA_EXEC, t.DT_TRADE || ' 00:00:00') DESC, t.ID_TRADE DESC
        """, params=tuple(params))

        items = df.to_dict("records")
        return APIResponse(data={"items": items, "total": len(items)})
    except Exception as exc:
        logger.exception("Erro em GET /sim/trades")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/positions", response_model=APIResponse)
async def get_positions(
    portfolio_id: int = Query(..., description="ID da carteira"),
):
    """Retorna posições consolidadas da carteira (MVP)."""
    try:
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
            ORDER BY DT_HORA_EXEC ASC, t.ID_TRADE ASC
            """,
            params=(portfolio_id,),
        )

        return APIResponse(
            data=_build_positions_response(
                trades_records=trades_df.to_dict("records"),
                owner_key="ID_PORTFOLIO",
                owner_id=portfolio_id,
            )
        )
    except Exception as exc:
        logger.exception("Erro em GET /sim/positions")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/fundos/positions", response_model=APIResponse)
async def get_positions_fundo(
    fundo_id: int = Query(..., description="ID do fundo"),
):
    """Retorna posições consolidadas por fundo (agregando carteiras vinculadas)."""
    try:
        trades_df = query(
            """
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
            ORDER BY DT_HORA_EXEC ASC, t.ID_TRADE ASC
            """,
            params=(fundo_id,),
        )

        return APIResponse(
            data=_build_positions_response(
                trades_records=trades_df.to_dict("records"),
                owner_key="ID_FUNDO",
                owner_id=fundo_id,
            )
        )
    except Exception as exc:
        logger.exception("Erro em GET /sim/fundos/positions")
        raise HTTPException(status_code=500, detail=str(exc))


def _list_active_fundo_ids() -> list[int]:
    df = query("SELECT ID_FUNDO FROM DIM_FUNDO WHERE COALESCE(ST_ATIVO, 1) = 1 ORDER BY ID_FUNDO")
    if df.empty:
        return []
    return [int(v) for v in df["ID_FUNDO"].tolist()]


def _get_fundo_positions_payload_sync(fundo_id: int, dt_ref: Optional[str] = None) -> dict:
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


def capture_pnl_live_fundo_sync(fundo_id: int, dt_hora_captura: Optional[datetime] = None, fonte: str = "simulador") -> dict:
    dt_cap = dt_hora_captura or _now_sp()
    dt_ref = dt_cap.date().isoformat()
    dt_carga = _now_sp_str()

    payload = _get_fundo_positions_payload_sync(fundo_id=fundo_id, dt_ref=dt_ref)
    resumo = payload.get("resumo", {})

    with managed_connection() as conn:
        conn.execute(
            """
            INSERT INTO FAT_FUNDO_PNL_LIVE (
                ID_FUNDO,
                DT_REFERENCIA,
                DT_HORA_CAPTURA,
                VL_VALOR_MERCADO_TOTAL,
                VL_PNL_ABERTO_TOTAL,
                VL_PNL_REALIZADO_TOTAL,
                VL_PNL_TOTAL,
                CD_FONTE,
                FL_REPROCESSADO,
                DT_CARGA
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fundo_id,
                dt_ref,
                dt_cap.strftime("%Y-%m-%d %H:%M:%S"),
                float(resumo.get("VALOR_MERCADO_TOTAL") or 0.0),
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


def recompute_fundo_cotas_sync(fundo_id: int) -> dict:
    df = query(
        """
        SELECT
            DT_REFERENCIA,
            DT_HORA_CAPTURA,
            COALESCE(VL_VALOR_MERCADO_TOTAL, 0) AS VL_PL
        FROM FAT_FUNDO_PNL_FECHAMENTO
        WHERE ID_FUNDO = ?
        ORDER BY DT_REFERENCIA
        """,
        params=(fundo_id,),
    )

    records = df.to_dict("records")
    if not records:
        return {"ID_FUNDO": fundo_id, "QT_DIAS": 0}

    pl0 = float(records[0]["VL_PL"] or 0.0)
    qt_cotas = pl0 if abs(pl0) > 1e-12 else 1.0

    with managed_connection() as conn:
        dt_carga = _now_sp_str()
        for rec in records:
            pl = float(rec["VL_PL"] or 0.0)
            cota = pl / qt_cotas if abs(qt_cotas) > 1e-12 else 0.0
            conn.execute(
                """
                INSERT INTO FAT_FUNDO_COTA_DIARIA (
                    ID_FUNDO,
                    DT_REFERENCIA,
                    VL_COTA,
                    QT_COTAS,
                    VL_PL,
                    DT_HORA_FECHAMENTO,
                    CD_METODO,
                    FL_REPROCESSADO,
                    DT_CARGA
                ) VALUES (?, ?, ?, ?, ?, ?, 'pl_sobre_cotas_constantes', 0, ?)
                ON CONFLICT(ID_FUNDO, DT_REFERENCIA) DO UPDATE SET
                    VL_COTA = excluded.VL_COTA,
                    QT_COTAS = excluded.QT_COTAS,
                    VL_PL = excluded.VL_PL,
                    DT_HORA_FECHAMENTO = excluded.DT_HORA_FECHAMENTO,
                    CD_METODO = excluded.CD_METODO,
                    FL_REPROCESSADO = 1,
                    DT_CARGA = datetime('now', '-3 hours')
                """,
                (
                    fundo_id,
                    rec["DT_REFERENCIA"],
                    cota,
                    qt_cotas,
                    pl,
                    rec["DT_HORA_CAPTURA"],
                    dt_carga,
                ),
            )

    return {
        "ID_FUNDO": fundo_id,
        "QT_DIAS": len(records),
        "QT_COTAS": qt_cotas,
        "VL_COTA_ULTIMA": float(records[-1]["VL_PL"] or 0.0) / qt_cotas if abs(qt_cotas) > 1e-12 else 0.0,
    }


def close_pnl_day_fundo_sync(
    fundo_id: int,
    dt_referencia: str,
    allow_recompute: bool = True,
    update_cota: bool = True,
) -> dict:
    row = query_scalar(
        """
        SELECT COUNT(*)
        FROM VW_FUNDO_PNL_LIVE_ULTIMO_DIA
        WHERE ID_FUNDO = ? AND DT_REFERENCIA = ?
        """,
        params=(fundo_id, dt_referencia),
    )

    if not row and allow_recompute:
        capture_time = datetime.fromisoformat(f"{dt_referencia} 19:00:00").replace(tzinfo=TZ_BR)
        capture_pnl_live_fundo_sync(
            fundo_id=fundo_id,
            dt_hora_captura=capture_time,
            fonte="reprocessamento_fechamento",
        )

    last_df = query(
        """
        SELECT
            ID_FUNDO,
            DT_REFERENCIA,
            DT_HORA_CAPTURA,
            VL_VALOR_MERCADO_TOTAL,
            VL_PNL_ABERTO_TOTAL,
            VL_PNL_REALIZADO_TOTAL,
            VL_PNL_TOTAL
        FROM VW_FUNDO_PNL_LIVE_ULTIMO_DIA
        WHERE ID_FUNDO = ?
          AND DT_REFERENCIA = ?
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
                ID_FUNDO,
                DT_REFERENCIA,
                DT_HORA_CAPTURA,
                VL_VALOR_MERCADO_TOTAL,
                VL_PNL_ABERTO_TOTAL,
                VL_PNL_REALIZADO_TOTAL,
                VL_PNL_TOTAL,
                CD_METODO,
                FL_REPROCESSADO,
                DT_CARGA
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
    start = date.fromisoformat(dt_inicio)
    end = date.fromisoformat(dt_fim)
    if end < start:
        raise ValueError("dt_fim deve ser maior ou igual a dt_inicio")

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
        "DT_INICIO": dt_inicio,
        "DT_FIM": dt_fim,
        "QT_DIAS": registros,
        "COTA": cota_info,
    }


def close_pnl_day_all_fundos_sync(dt_referencia: str) -> dict:
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


@router.post("/fundos/pnl/live/capture", response_model=APIResponse)
async def capture_pnl_live(
    fundo_id: Optional[int] = Query(None, description="ID do fundo. Omitir para todos"),
):
    try:
        if fundo_id:
            data = capture_pnl_live_fundo_sync(fundo_id=fundo_id)
            return APIResponse(data=data)

        itens = []
        for fid in _list_active_fundo_ids():
            itens.append(capture_pnl_live_fundo_sync(fundo_id=fid))
        return APIResponse(data={"items": itens, "total": len(itens), "dt_hora_sp": _now_sp().strftime("%Y-%m-%d %H:%M:%S")})
    except Exception as exc:
        logger.exception("Erro em POST /sim/fundos/pnl/live/capture")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fundos/pnl/fechamento", response_model=APIResponse)
async def fechar_pnl_dia(
    fundo_id: Optional[int] = Query(None, description="ID do fundo. Omitir para todos"),
    dt_referencia: Optional[str] = Query(None, description="Data YYYY-MM-DD. Default: hoje (SP)"),
):
    try:
        if not isinstance(dt_referencia, str):
            dt_referencia = None
        dt_ref = dt_referencia or _iso_date_sp()
        if fundo_id:
            data = close_pnl_day_fundo_sync(fundo_id=fundo_id, dt_referencia=dt_ref, allow_recompute=True)
            return APIResponse(data=data)

        return APIResponse(data=close_pnl_day_all_fundos_sync(dt_ref))
    except Exception as exc:
        logger.exception("Erro em POST /sim/fundos/pnl/fechamento")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fundos/pnl/backfill", response_model=APIResponse)
async def backfill_pnl_fechamento(
    fundo_id: int = Query(..., description="ID do fundo"),
    dt_inicio: str = Query(..., description="Data início YYYY-MM-DD"),
    dt_fim: str = Query(..., description="Data fim YYYY-MM-DD"),
):
    try:
        return APIResponse(data=backfill_pnl_fechamento_fundo_sync(fundo_id=fundo_id, dt_inicio=dt_inicio, dt_fim=dt_fim))
    except Exception as exc:
        logger.exception("Erro em POST /sim/fundos/pnl/backfill")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/fundos/pnl/fechamento/serie", response_model=APIResponse)
async def serie_pnl_fechamento(
    fundo_id: int = Query(..., description="ID do fundo"),
    dt_inicio: Optional[str] = Query(None),
    dt_fim: Optional[str] = Query(None),
):
    try:
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
            f"""
            SELECT
                ID_FUNDO,
                DT_REFERENCIA,
                DT_HORA_CAPTURA,
                VL_VALOR_MERCADO_TOTAL,
                VL_PNL_ABERTO_TOTAL,
                VL_PNL_REALIZADO_TOTAL,
                VL_PNL_TOTAL,
                CD_METODO,
                FL_REPROCESSADO,
                DT_CARGA
            FROM FAT_FUNDO_PNL_FECHAMENTO
            WHERE {where}
            ORDER BY DT_REFERENCIA
            """,
            params=tuple(params),
        )
        items = df.to_dict("records")
        return APIResponse(data={"items": items, "total": len(items)})
    except Exception as exc:
        logger.exception("Erro em GET /sim/fundos/pnl/fechamento/serie")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fundos/cotas/recalcular", response_model=APIResponse)
async def recalcular_cotas(
    fundo_id: int = Query(..., description="ID do fundo"),
):
    try:
        return APIResponse(data=recompute_fundo_cotas_sync(fundo_id=fundo_id))
    except Exception as exc:
        logger.exception("Erro em POST /sim/fundos/cotas/recalcular")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/fundos/cotas/serie", response_model=APIResponse)
async def serie_cotas(
    fundo_id: int = Query(..., description="ID do fundo"),
    dt_inicio: Optional[str] = Query(None),
    dt_fim: Optional[str] = Query(None),
):
    try:
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
            f"""
            SELECT
                ID_FUNDO,
                DT_REFERENCIA,
                VL_COTA,
                QT_COTAS,
                VL_PL,
                DT_HORA_FECHAMENTO,
                CD_METODO,
                FL_REPROCESSADO,
                DT_CARGA
            FROM FAT_FUNDO_COTA_DIARIA
            WHERE {where}
            ORDER BY DT_REFERENCIA
            """,
            params=tuple(params),
        )
        items = df.to_dict("records")
        return APIResponse(data={"items": items, "total": len(items)})
    except Exception as exc:
        logger.exception("Erro em GET /sim/fundos/cotas/serie")
        raise HTTPException(status_code=500, detail=str(exc))
