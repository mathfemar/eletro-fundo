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
    DT_INICIO: str = Field(default_factory=lambda: date.today().isoformat())
    VL_PL_INICIAL: float = Field(default=0.0, ge=0)
    VL_COTA_INICIAL: float = Field(default=1.0, gt=0)


class FundoSetupCotistaInput(BaseModel):
    ID_TITULAR: int
    VL_APORTE: float = Field(gt=0)


class FundoSetupInput(BaseModel):
    NM_FUNDO: str = Field(min_length=1, max_length=120)
    DS_ESTRATEGIA: Optional[str] = None
    BENCHMARK: Optional[str] = None
    MOEDA_BASE: str = "BRL"
    ST_ATIVO: int = 1
    DT_INICIO: str = Field(default_factory=lambda: date.today().isoformat())
    VL_COTA_INICIAL: float = Field(default=1.0, gt=0)
    COTISTAS_INICIAIS: list[FundoSetupCotistaInput]


class FundoCarteiraInput(BaseModel):
    ID_TITULAR: int
    NM_CARTEIRA: str = Field(min_length=1, max_length=120)
    ID_CORRETORA: Optional[int] = None
    CONTA_REF: Optional[str] = None
    MOEDA_BASE: str = "BRL"
    DT_INICIO: str = Field(default_factory=lambda: date.today().isoformat())


class FundoAlocacaoInput(BaseModel):
    ID_CARTEIRA_ORIGEM: int
    ID_CARTEIRA_DESTINO: int
    VL_ALOCACAO: float = Field(gt=0)
    DT_MOVIMENTO: str = Field(default_factory=lambda: date.today().isoformat())
    DS_OBSERVACAO: Optional[str] = None


def _assert_portfolio_has_capital_for_trade(
    portfolio_id: int,
    dt_trade: str,
    side: str,
    qtd: float,
    pu: float,
    custo: float = 0.0,
    exclude_trade_id: Optional[int] = None,
) -> None:
    carteira_row = query(
        """
        SELECT NM_CARTEIRA, CONTA_REF
        FROM DIM_CARTEIRA
        WHERE ID_CARTEIRA = ?
        LIMIT 1
        """,
        params=(portfolio_id,),
    )
    if carteira_row.empty:
        raise HTTPException(status_code=404, detail=f"Carteira {portfolio_id} não encontrada")

    carteira = carteira_row.to_dict("records")[0]
    nm_carteira = str(carteira.get("NM_CARTEIRA") or "").upper()
    conta_ref = str(carteira.get("CONTA_REF") or "").upper()
    if conta_ref == "CAIXA" or nm_carteira.startswith("CAIXA -"):
        raise HTTPException(
            status_code=409,
            detail=(
                "Carteira CAIXA não permite operações BUY/SELL. "
                "Use a página de Carteiras e Alocação para distribuir caixa para carteiras de estratégia."
            ),
        )

    fundo_id = query_scalar(
        """
        SELECT rfc.ID_FUNDO
        FROM RL_FUNDO_CARTEIRA rfc
        WHERE rfc.ID_CARTEIRA = ?
        ORDER BY COALESCE(rfc.DT_FIM, '9999-12-31') DESC, rfc.DT_INICIO DESC
        LIMIT 1
        """,
        params=(portfolio_id,),
    )

    if fundo_id is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Carteira sem vínculo de fundo. Vincule a carteira a um fundo antes de registrar operações."
            ),
        )

    fluxo_liq = query_scalar(
        """
        SELECT COALESCE(SUM(CASE WHEN TP_FLUXO = 'APORTE' THEN VL_FLUXO ELSE -VL_FLUXO END), 0)
        FROM FAT_FUNDO_FLUXO_CAPITAL
        WHERE ID_FUNDO = ?
          AND DT_REFERENCIA <= ?
        """,
        params=(int(fundo_id), dt_trade),
    )

    pl_seed = query_scalar(
        """
        SELECT COALESCE(MAX(VL_PL), 0)
        FROM FAT_FUNDO_COTA_DIARIA
        WHERE ID_FUNDO = ?
          AND DT_REFERENCIA <= ?
        """,
        params=(int(fundo_id), dt_trade),
    )

    fluxo_liq = float(fluxo_liq or 0.0)
    pl_seed = float(pl_seed or 0.0)
    if fluxo_liq <= 0 and pl_seed <= 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Fundo {int(fundo_id)} sem capital líquido até {dt_trade}. "
                "Registre aporte inicial (ou PL inicial no cadastro do fundo) antes de lançar operações."
            ),
        )

    side_norm = str(side).upper()
    if side_norm == "BUY":
        sql_trade_cash = """
            SELECT COALESCE(
                SUM(
                    CASE
                        WHEN SIDE = 'SELL' THEN (QTD * PU) - COALESCE(CUSTO, 0)
                        WHEN SIDE = 'BUY' THEN -((QTD * PU) + COALESCE(CUSTO, 0))
                        ELSE 0
                    END
                ),
                0
            )
            FROM FAT_CARTEIRA_TRADE
            WHERE ID_CARTEIRA = ?
              AND DT_TRADE <= ?
        """
        params: list = [portfolio_id, dt_trade]
        if exclude_trade_id is not None:
            sql_trade_cash += " AND ID_TRADE <> ?"
            params.append(exclude_trade_id)

        saldo_mov = _saldo_carteira_caixa(int(fundo_id), portfolio_id, dt_trade)
        saldo_trades = float(query_scalar(sql_trade_cash, params=tuple(params)) or 0.0)
        saldo_disponivel = saldo_mov + saldo_trades
        valor_ordem = (float(qtd) * float(pu)) + float(custo or 0.0)

        if valor_ordem > saldo_disponivel + 1e-9:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Caixa insuficiente na carteira {portfolio_id} para BUY em {dt_trade}. "
                    f"Disponível={saldo_disponivel:.2f}; Necessário={valor_ordem:.2f}."
                ),
            )


def _saldo_carteira_caixa(id_fundo: int, id_carteira: int, dt_limite: Optional[str] = None) -> float:
    sql = """
        SELECT
            COALESCE(
                SUM(
                    CASE
                        WHEN TP_MOVIMENTO IN ('APORTE_INICIAL', 'ALOCACAO_ENTRADA', 'APORTE_COTISTA') THEN VL_MOVIMENTO
                        ELSE -VL_MOVIMENTO
                    END
                ),
                0
            )
        FROM FAT_CARTEIRA_MOVIMENTO_CAIXA
        WHERE ID_FUNDO = ?
          AND ID_CARTEIRA = ?
    """
    params: list = [id_fundo, id_carteira]
    if dt_limite:
        sql += " AND DT_MOVIMENTO <= ? "
        params.append(dt_limite)

    return float(query_scalar(sql, params=tuple(params)) or 0.0)


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
    SIDE: str = Field(description="BUY | SELL")
    QTD: float
    PU: float
    CUSTO: float = 0.0
    OBSERVACAO: Optional[str] = None


class FundoFluxoInput(BaseModel):
    ID_FUNDO: int
    ID_TITULAR: Optional[int] = None
    DT_REFERENCIA: str = Field(default_factory=lambda: date.today().isoformat())
    TP_FLUXO: str = Field(description="APORTE | RESGATE")
    VL_FLUXO: float = Field(gt=0)
    OBSERVACAO: Optional[str] = None


class AtivoLiquidezInput(BaseModel):
    ID_ATIVO: int
    NR_DIAS_LIQUIDEZ: int = Field(default=0, ge=0)
    DS_REGRA: Optional[str] = None
    ST_ATIVO: int = 1


class RFTituloInput(BaseModel):
    CD_TITULO: str = Field(min_length=1, max_length=80)
    NM_TITULO: Optional[str] = None
    ID_ATIVO: Optional[int] = None
    DT_VENCIMENTO: str
    DT_RESGATE: Optional[str] = None
    VL_TAXA_CONTRATADA: Optional[float] = None
    ST_ATIVO: int = 1


class ResgateSolicitacaoInput(BaseModel):
    ID_FUNDO: int
    ID_TITULAR: Optional[int] = None
    DT_SOLICITACAO: str = Field(default_factory=lambda: date.today().isoformat())
    VL_RESGATE: float = Field(gt=0)
    DS_OBSERVACAO: Optional[str] = None


class ResgatePlanoItemInput(BaseModel):
    ID_ATIVO: int
    VL_LIQUIDAR: float = Field(gt=0)
    NR_DIAS_LIQUIDEZ: Optional[int] = Field(default=None, ge=0)
    DS_OBSERVACAO: Optional[str] = None


class ResgatePlanoInput(BaseModel):
    ID_SOLICITACAO: int
    CD_METODO: str = "MANUAL_GESTOR"
    DS_JUSTIFICATIVA: Optional[str] = None
    ST_STATUS: str = "RASCUNHO"
    items: list[ResgatePlanoItemInput]


class ResgateExecucaoInput(BaseModel):
    DT_REFERENCIA: str = Field(default_factory=lambda: date.today().isoformat())
    VL_EXECUTADO: Optional[float] = Field(default=None, gt=0)
    DS_OBSERVACAO: Optional[str] = None


class ResgateOverrideInput(BaseModel):
    DT_REFERENCIA: str = Field(default_factory=lambda: date.today().isoformat())
    DS_JUSTIFICATIVA: str = Field(min_length=5)
    VL_EVENTO: float = 0.0


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

            pl_inicial = float(payload.VL_PL_INICIAL or 0.0)
            cota_inicial = float(payload.VL_COTA_INICIAL or 1.0)
            if pl_inicial > 0:
                dt_ref = payload.DT_INICIO
                dt_hora_seed = f"{dt_ref} 00:00:00"
                qt_cotas_seed = pl_inicial / cota_inicial if abs(cota_inicial) > 1e-12 else pl_inicial

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
                    ) VALUES (?, ?, ?, ?, 0, 0, 0, 'seed_cadastro_fundo', 0, ?)
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
                        new_id,
                        dt_ref,
                        dt_hora_seed,
                        pl_inicial,
                        now_sp,
                    ),
                )

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
                    ) VALUES (?, ?, ?, ?, ?, ?, 'seed_cadastro_fundo', 0, ?)
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
                        new_id,
                        dt_ref,
                        cota_inicial,
                        qt_cotas_seed,
                        pl_inicial,
                        dt_hora_seed,
                        now_sp,
                    ),
                )

        return APIResponse(data={"ID_FUNDO": new_id})
    except Exception as exc:
        logger.exception("Erro em POST /sim/fundos")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/fundos/{fundo_id}", response_model=APIResponse)
async def excluir_fundo(fundo_id: int):
    exists_fundo = query_scalar(
        "SELECT COUNT(*) FROM DIM_FUNDO WHERE ID_FUNDO = ?",
        params=(fundo_id,),
    )
    if not exists_fundo:
        raise HTTPException(status_code=404, detail=f"Fundo {fundo_id} não encontrado")

    links_count = query_scalar(
        "SELECT COUNT(*) FROM RL_FUNDO_CARTEIRA WHERE ID_FUNDO = ?",
        params=(fundo_id,),
    )
    if links_count and int(links_count) > 0:
        raise HTTPException(
            status_code=409,
            detail="Fundo possui carteiras vinculadas. Remova os vínculos/exclua as carteiras antes de excluir o fundo.",
        )

    try:
        with managed_connection() as conn:
            conn.execute("DELETE FROM FAT_FUNDO_RESGATE_EVENTO WHERE ID_FUNDO = ?", (fundo_id,))
            conn.execute(
                """
                DELETE FROM FAT_FUNDO_RESGATE_ITEM
                WHERE ID_PLANO IN (
                    SELECT p.ID_PLANO
                    FROM FAT_FUNDO_RESGATE_PLANO p
                    JOIN FAT_FUNDO_RESGATE_SOLICITACAO s
                      ON s.ID_SOLICITACAO = p.ID_SOLICITACAO
                    WHERE s.ID_FUNDO = ?
                )
                """,
                (fundo_id,),
            )
            conn.execute(
                """
                DELETE FROM FAT_FUNDO_RESGATE_PLANO
                WHERE ID_SOLICITACAO IN (
                    SELECT ID_SOLICITACAO
                    FROM FAT_FUNDO_RESGATE_SOLICITACAO
                    WHERE ID_FUNDO = ?
                )
                """,
                (fundo_id,),
            )
            conn.execute("DELETE FROM FAT_FUNDO_RESGATE_SOLICITACAO WHERE ID_FUNDO = ?", (fundo_id,))
            conn.execute("DELETE FROM FAT_COTISTA_POSICAO_DIARIA WHERE ID_FUNDO = ?", (fundo_id,))
            conn.execute("DELETE FROM FAT_CARTEIRA_MOVIMENTO_CAIXA WHERE ID_FUNDO = ?", (fundo_id,))
            conn.execute("DELETE FROM FAT_FUNDO_FLUXO_CAPITAL WHERE ID_FUNDO = ?", (fundo_id,))
            conn.execute("DELETE FROM FAT_FUNDO_COTA_DIARIA WHERE ID_FUNDO = ?", (fundo_id,))
            conn.execute("DELETE FROM FAT_FUNDO_PNL_FECHAMENTO WHERE ID_FUNDO = ?", (fundo_id,))
            conn.execute("DELETE FROM FAT_FUNDO_PNL_LIVE WHERE ID_FUNDO = ?", (fundo_id,))
            conn.execute("DELETE FROM DIM_FUNDO WHERE ID_FUNDO = ?", (fundo_id,))

        return APIResponse(data={"deleted": True, "ID_FUNDO": fundo_id})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em DELETE /sim/fundos/{fundo_id}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fundos/fluxos", response_model=APIResponse, status_code=201)
async def criar_fluxo_fundo(payload: FundoFluxoInput):
    tp_fluxo = payload.TP_FLUXO.strip().upper()
    if tp_fluxo not in {"APORTE", "RESGATE"}:
        raise HTTPException(status_code=422, detail="TP_FLUXO inválido. Use APORTE ou RESGATE")

    exists_fundo = query_scalar(
        "SELECT COUNT(*) FROM DIM_FUNDO WHERE ID_FUNDO = ?",
        params=(payload.ID_FUNDO,),
    )
    if not exists_fundo:
        raise HTTPException(status_code=404, detail=f"Fundo {payload.ID_FUNDO} não encontrado")

    if payload.ID_TITULAR is not None:
        exists_titular = query_scalar(
            "SELECT COUNT(*) FROM DIM_TITULAR WHERE ID_TITULAR = ?",
            params=(payload.ID_TITULAR,),
        )
        if not exists_titular:
            raise HTTPException(status_code=404, detail=f"Titular {payload.ID_TITULAR} não encontrado")

    try:
        with managed_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO FAT_FUNDO_FLUXO_CAPITAL (
                    ID_FUNDO,
                    ID_TITULAR,
                    DT_REFERENCIA,
                    TP_FLUXO,
                    VL_FLUXO,
                    OBSERVACAO,
                    DT_CARGA
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.ID_FUNDO,
                    payload.ID_TITULAR,
                    payload.DT_REFERENCIA,
                    tp_fluxo,
                    float(payload.VL_FLUXO),
                    payload.OBSERVACAO,
                    _now_sp_str(),
                ),
            )
            fluxo_id = cur.lastrowid

        cota_info = recompute_fundo_cotas_sync(payload.ID_FUNDO)
        return APIResponse(data={"ID_FLUXO": fluxo_id, "ID_FUNDO": payload.ID_FUNDO, "COTA": cota_info})
    except Exception as exc:
        logger.exception("Erro em POST /sim/fundos/fluxos")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fundos/{fundo_id}/recalcular-cotas", response_model=APIResponse)
async def recalcular_cotas_fundo(fundo_id: int):
    exists_fundo = query_scalar(
        "SELECT COUNT(*) FROM DIM_FUNDO WHERE ID_FUNDO = ?",
        params=(fundo_id,),
    )
    if not exists_fundo:
        raise HTTPException(status_code=404, detail=f"Fundo {fundo_id} não encontrado")

    try:
        data = recompute_fundo_cotas_sync(fundo_id)
        return APIResponse(data=data)
    except Exception as exc:
        logger.exception("Erro em POST /sim/fundos/{fundo_id}/recalcular-cotas")
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


@router.get("/cotistas", response_model=APIResponse)
async def listar_cotistas():
    return await listar_titulares()


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


@router.post("/cotistas", response_model=APIResponse, status_code=201)
async def criar_cotista(payload: TitularInput):
    return await criar_titular(payload)


@router.post("/fundos/setup", response_model=APIResponse, status_code=201)
async def setup_fundo(payload: FundoSetupInput):
    try:
        cotistas = payload.COTISTAS_INICIAIS or []
        if not cotistas:
            raise HTTPException(status_code=422, detail="Informe ao menos 1 cotista inicial")

        ids = [int(item.ID_TITULAR) for item in cotistas]
        if len(ids) != len(set(ids)):
            raise HTTPException(status_code=422, detail="Cotistas iniciais duplicados")

        for titular_id in ids:
            if not _entity_exists("DIM_TITULAR", "ID_TITULAR", titular_id):
                raise HTTPException(status_code=404, detail=f"Cotista/Titular {titular_id} não encontrado")

        vl_pl_inicial = sum(float(item.VL_APORTE) for item in cotistas)
        if vl_pl_inicial <= 0:
            raise HTTPException(status_code=422, detail="PL inicial deve ser maior que zero")

        now_sp = _now_sp_str()
        dt_ref = payload.DT_INICIO
        dt_hora_seed = f"{dt_ref} 00:00:00"
        cota_inicial = float(payload.VL_COTA_INICIAL)
        qt_cotas_seed = vl_pl_inicial / cota_inicial if abs(cota_inicial) > 1e-12 else vl_pl_inicial

        titular_legado, corretora_legado = _get_or_create_legacy_entities()
        titular_caixa = int(ids[0]) if ids else int(titular_legado)

        with managed_connection() as conn:
            cur_fundo = conn.execute(
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
            fundo_id = int(cur_fundo.lastrowid)

            cur_carteira_caixa = conn.execute(
                """
                INSERT INTO DIM_CARTEIRA
                    (ID_TITULAR, ID_CORRETORA, NM_CARTEIRA, CONTA_REF, MOEDA_BASE, ST_ATIVO, DT_CRIACAO, DT_ATUALIZACAO)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    titular_caixa,
                    corretora_legado,
                    f"CAIXA - {payload.NM_FUNDO.strip()}",
                    "CAIXA",
                    payload.MOEDA_BASE,
                    now_sp,
                    now_sp,
                ),
            )
            carteira_caixa_id = int(cur_carteira_caixa.lastrowid)

            conn.execute(
                """
                INSERT INTO RL_FUNDO_CARTEIRA
                    (ID_FUNDO, ID_CARTEIRA, DT_INICIO, DT_FIM, ST_ATIVO, DT_CRIACAO, DT_ATUALIZACAO)
                VALUES (?, ?, ?, NULL, 1, ?, ?)
                """,
                (
                    fundo_id,
                    carteira_caixa_id,
                    dt_ref,
                    now_sp,
                    now_sp,
                ),
            )

            for item in cotistas:
                conn.execute(
                    """
                    INSERT INTO FAT_FUNDO_FLUXO_CAPITAL (
                        ID_FUNDO,
                        ID_TITULAR,
                        DT_REFERENCIA,
                        TP_FLUXO,
                        VL_FLUXO,
                        OBSERVACAO,
                        DT_CARGA
                    ) VALUES (?, ?, ?, 'APORTE', ?, 'SEED_INICIAL_SETUP', ?)
                    """,
                    (
                        fundo_id,
                        int(item.ID_TITULAR),
                        dt_ref,
                        float(item.VL_APORTE),
                        now_sp,
                    ),
                )

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
                ) VALUES (?, ?, ?, ?, 0, 0, 0, 'seed_setup_fundo', 0, ?)
                """,
                (
                    fundo_id,
                    dt_ref,
                    dt_hora_seed,
                    vl_pl_inicial,
                    now_sp,
                ),
            )

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
                ) VALUES (?, ?, ?, ?, ?, ?, 'seed_setup_fundo', 0, ?)
                """,
                (
                    fundo_id,
                    dt_ref,
                    cota_inicial,
                    qt_cotas_seed,
                    vl_pl_inicial,
                    dt_hora_seed,
                    now_sp,
                ),
            )

            conn.execute(
                """
                INSERT INTO FAT_CARTEIRA_MOVIMENTO_CAIXA (
                    ID_FUNDO,
                    ID_CARTEIRA,
                    ID_CARTEIRA_REF,
                    DT_MOVIMENTO,
                    TP_MOVIMENTO,
                    VL_MOVIMENTO,
                    DS_OBSERVACAO,
                    DT_CARGA
                ) VALUES (?, ?, NULL, ?, 'APORTE_INICIAL', ?, 'SEED_SETUP_FUNDO', ?)
                """,
                (
                    fundo_id,
                    carteira_caixa_id,
                    dt_ref,
                    vl_pl_inicial,
                    now_sp,
                ),
            )

        return APIResponse(
            data={
                "ID_FUNDO": fundo_id,
                "ID_CARTEIRA_CAIXA": carteira_caixa_id,
                "VL_PL_INICIAL": vl_pl_inicial,
                "VL_COTA_INICIAL": cota_inicial,
                "QT_COTAS_INICIAL": qt_cotas_seed,
                "QT_COTISTAS": len(cotistas),
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em POST /sim/fundos/setup")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/fundos/{fundo_id}/carteiras", response_model=APIResponse)
async def listar_carteiras_fundo(fundo_id: int):
    try:
        exists_fundo = query_scalar(
            "SELECT COUNT(*) FROM DIM_FUNDO WHERE ID_FUNDO = ?",
            params=(fundo_id,),
        )
        if not exists_fundo:
            raise HTTPException(status_code=404, detail=f"Fundo {fundo_id} não encontrado")

        df = query(
            """
            SELECT
                dc.ID_CARTEIRA,
                dc.NM_CARTEIRA,
                dc.ID_TITULAR,
                dt.NM_TITULAR,
                dc.ID_CORRETORA,
                dcor.NM_CORRETORA,
                dc.CONTA_REF,
                dc.MOEDA_BASE,
                rfc.DT_INICIO,
                rfc.DT_FIM,
                rfc.ST_ATIVO
            FROM RL_FUNDO_CARTEIRA rfc
            JOIN DIM_CARTEIRA dc ON dc.ID_CARTEIRA = rfc.ID_CARTEIRA
            LEFT JOIN DIM_TITULAR dt ON dt.ID_TITULAR = dc.ID_TITULAR
            LEFT JOIN DIM_CORRETORA dcor ON dcor.ID_CORRETORA = dc.ID_CORRETORA
            WHERE rfc.ID_FUNDO = ?
              AND (rfc.ST_ATIVO = 1 OR rfc.DT_FIM IS NULL)
            ORDER BY dc.ID_CARTEIRA DESC
            """,
            params=(fundo_id,),
        )
        items = df.to_dict("records")
        for item in items:
            item["VL_SALDO_CAIXA"] = _saldo_carteira_caixa(fundo_id, int(item["ID_CARTEIRA"]))

        return APIResponse(data={"items": items, "total": len(items)})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em GET /sim/fundos/{fundo_id}/carteiras")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fundos/{fundo_id}/carteiras", response_model=APIResponse, status_code=201)
async def criar_carteira_fundo(fundo_id: int, payload: FundoCarteiraInput):
    try:
        exists_fundo = query_scalar(
            "SELECT COUNT(*) FROM DIM_FUNDO WHERE ID_FUNDO = ?",
            params=(fundo_id,),
        )
        if not exists_fundo:
            raise HTTPException(status_code=404, detail=f"Fundo {fundo_id} não encontrado")

        exists_cotista = query_scalar(
            """
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT ffc.ID_TITULAR
                FROM FAT_FUNDO_FLUXO_CAPITAL ffc
                WHERE ffc.ID_FUNDO = ?
                  AND ffc.ID_TITULAR IS NOT NULL

                UNION

                SELECT DISTINCT dc.ID_TITULAR
                FROM RL_FUNDO_CARTEIRA rfc
                JOIN DIM_CARTEIRA dc ON dc.ID_CARTEIRA = rfc.ID_CARTEIRA
                WHERE rfc.ID_FUNDO = ?
            ) base_cotistas
            WHERE ID_TITULAR = ?
            """,
            params=(fundo_id, fundo_id, payload.ID_TITULAR),
        )
        if not exists_cotista:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Titular {payload.ID_TITULAR} não é cotista deste fundo. "
                    "Selecione um titular da lista de cotistas do fundo."
                ),
            )

        if payload.ID_CORRETORA is not None:
            exists_corretora = _entity_exists("DIM_CORRETORA", "ID_CORRETORA", payload.ID_CORRETORA)
            if not exists_corretora:
                raise HTTPException(status_code=404, detail=f"Corretora {payload.ID_CORRETORA} não encontrada")
            corretora_id = int(payload.ID_CORRETORA)
        else:
            _, corretora_legado = _get_or_create_legacy_entities()
            corretora_id = int(corretora_legado)

        now_sp = _now_sp_str()
        with managed_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO DIM_CARTEIRA
                    (ID_TITULAR, ID_CORRETORA, NM_CARTEIRA, CONTA_REF, MOEDA_BASE, ST_ATIVO, DT_CRIACAO, DT_ATUALIZACAO)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    payload.ID_TITULAR,
                    corretora_id,
                    payload.NM_CARTEIRA.strip(),
                    payload.CONTA_REF,
                    payload.MOEDA_BASE,
                    now_sp,
                    now_sp,
                ),
            )
            carteira_id = int(cur.lastrowid)

            conn.execute(
                """
                INSERT INTO RL_FUNDO_CARTEIRA
                    (ID_FUNDO, ID_CARTEIRA, DT_INICIO, DT_FIM, ST_ATIVO, DT_CRIACAO, DT_ATUALIZACAO)
                VALUES (?, ?, ?, NULL, 1, ?, ?)
                """,
                (
                    fundo_id,
                    carteira_id,
                    payload.DT_INICIO,
                    now_sp,
                    now_sp,
                ),
            )

        return APIResponse(data={"ID_FUNDO": fundo_id, "ID_CARTEIRA": carteira_id})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em POST /sim/fundos/{fundo_id}/carteiras")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fundos/{fundo_id}/alocacoes", response_model=APIResponse, status_code=201)
async def alocar_caixa_fundo(fundo_id: int, payload: FundoAlocacaoInput):
    try:
        if payload.ID_CARTEIRA_ORIGEM == payload.ID_CARTEIRA_DESTINO:
            raise HTTPException(status_code=422, detail="Origem e destino devem ser carteiras diferentes")

        for carteira_id in (payload.ID_CARTEIRA_ORIGEM, payload.ID_CARTEIRA_DESTINO):
            count = query_scalar(
                """
                SELECT COUNT(*)
                FROM RL_FUNDO_CARTEIRA
                WHERE ID_FUNDO = ?
                  AND ID_CARTEIRA = ?
                  AND (ST_ATIVO = 1 OR DT_FIM IS NULL)
                """,
                params=(fundo_id, carteira_id),
            )
            if not count:
                raise HTTPException(status_code=404, detail=f"Carteira {carteira_id} não vinculada ao fundo {fundo_id}")

        saldo_origem = _saldo_carteira_caixa(fundo_id, payload.ID_CARTEIRA_ORIGEM, payload.DT_MOVIMENTO)
        if saldo_origem + 1e-9 < float(payload.VL_ALOCACAO):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Saldo insuficiente na carteira origem. Saldo={saldo_origem:.2f}, "
                    f"Alocação={float(payload.VL_ALOCACAO):.2f}"
                ),
            )

        now_sp = _now_sp_str()
        with managed_connection() as conn:
            conn.execute(
                """
                INSERT INTO FAT_CARTEIRA_MOVIMENTO_CAIXA (
                    ID_FUNDO,
                    ID_CARTEIRA,
                    ID_CARTEIRA_REF,
                    DT_MOVIMENTO,
                    TP_MOVIMENTO,
                    VL_MOVIMENTO,
                    DS_OBSERVACAO,
                    DT_CARGA
                ) VALUES (?, ?, ?, ?, 'ALOCACAO_SAIDA', ?, ?, ?)
                """,
                (
                    fundo_id,
                    payload.ID_CARTEIRA_ORIGEM,
                    payload.ID_CARTEIRA_DESTINO,
                    payload.DT_MOVIMENTO,
                    float(payload.VL_ALOCACAO),
                    payload.DS_OBSERVACAO,
                    now_sp,
                ),
            )

            conn.execute(
                """
                INSERT INTO FAT_CARTEIRA_MOVIMENTO_CAIXA (
                    ID_FUNDO,
                    ID_CARTEIRA,
                    ID_CARTEIRA_REF,
                    DT_MOVIMENTO,
                    TP_MOVIMENTO,
                    VL_MOVIMENTO,
                    DS_OBSERVACAO,
                    DT_CARGA
                ) VALUES (?, ?, ?, ?, 'ALOCACAO_ENTRADA', ?, ?, ?)
                """,
                (
                    fundo_id,
                    payload.ID_CARTEIRA_DESTINO,
                    payload.ID_CARTEIRA_ORIGEM,
                    payload.DT_MOVIMENTO,
                    float(payload.VL_ALOCACAO),
                    payload.DS_OBSERVACAO,
                    now_sp,
                ),
            )

        return APIResponse(
            data={
                "ID_FUNDO": fundo_id,
                "ID_CARTEIRA_ORIGEM": payload.ID_CARTEIRA_ORIGEM,
                "ID_CARTEIRA_DESTINO": payload.ID_CARTEIRA_DESTINO,
                "VL_ALOCACAO": float(payload.VL_ALOCACAO),
                "VL_SALDO_ORIGEM_APOS": _saldo_carteira_caixa(fundo_id, payload.ID_CARTEIRA_ORIGEM),
                "VL_SALDO_DESTINO_APOS": _saldo_carteira_caixa(fundo_id, payload.ID_CARTEIRA_DESTINO),
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em POST /sim/fundos/{fundo_id}/alocacoes")
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
    portfolio_df = query(
        """
        SELECT
            dc.ID_CARTEIRA,
            dc.NM_CARTEIRA,
            dc.CONTA_REF,
            rfc.ID_FUNDO
        FROM DIM_CARTEIRA dc
        LEFT JOIN RL_FUNDO_CARTEIRA rfc ON rfc.ID_CARTEIRA = dc.ID_CARTEIRA
        WHERE dc.ID_CARTEIRA = ?
        ORDER BY COALESCE(rfc.DT_FIM, '9999-12-31') DESC, rfc.DT_INICIO DESC
        LIMIT 1
        """,
        params=(portfolio_id,),
    )
    if portfolio_df.empty:
        raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} não encontrado")

    portfolio = portfolio_df.to_dict("records")[0]
    fundo_id = portfolio.get("ID_FUNDO")

    trade_count = int(
        query_scalar(
            "SELECT COUNT(*) FROM FAT_CARTEIRA_TRADE WHERE ID_CARTEIRA = ?",
            params=(portfolio_id,),
        )
        or 0
    )
    if trade_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Carteira possui {trade_count} operação(ões). "
                "Exclua as operações (ou zere/liquide posições) antes de excluir a carteira."
            ),
        )

    saldo_caixa = _saldo_carteira_caixa(int(fundo_id), portfolio_id) if fundo_id is not None else 0.0
    if abs(float(saldo_caixa)) > 1e-9:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Carteira com saldo de caixa diferente de zero ({saldo_caixa:.2f}). "
                "Transfira/alocar o caixa para outra carteira antes de excluir."
            ),
        )

    try:
        with managed_connection() as conn:
            conn.execute("DELETE FROM FAT_CARTEIRA_TRADE WHERE ID_CARTEIRA = ?", (portfolio_id,))
            conn.execute("DELETE FROM FAT_CARTEIRA_POSICAO_DIARIA WHERE ID_CARTEIRA = ?", (portfolio_id,))
            conn.execute(
                "DELETE FROM FAT_CARTEIRA_MOVIMENTO_CAIXA WHERE ID_CARTEIRA = ? OR ID_CARTEIRA_REF = ?",
                (portfolio_id, portfolio_id),
            )
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
    _assert_portfolio_has_capital_for_trade(
        portfolio_id=payload.ID_PORTFOLIO,
        dt_trade=dt_trade,
        side=side,
        qtd=float(payload.QTD),
        pu=float(payload.PU),
        custo=float(payload.CUSTO or 0.0),
    )

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

        recompute_carteira_posicao_diaria_sync(payload.ID_PORTFOLIO, dt_trade)

        return APIResponse(data={"ID_TRADE": new_id})
    except Exception as exc:
        logger.exception("Erro em POST /sim/trades")
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/trades/{trade_id}", response_model=APIResponse)
async def atualizar_trade(trade_id: int, payload: TradeInput):
    """Atualiza uma operação manual no simulador."""
    side, dt_hora_exec, dt_trade = _normalize_trade_payload(payload)

    prev_trade_df = query(
        "SELECT ID_CARTEIRA, DT_TRADE FROM FAT_CARTEIRA_TRADE WHERE ID_TRADE = ? LIMIT 1",
        params=(trade_id,),
    )
    if prev_trade_df.empty:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} não encontrada")

    prev_trade = prev_trade_df.to_dict("records")[0]
    prev_portfolio_id = int(prev_trade["ID_CARTEIRA"])
    prev_dt_trade = str(prev_trade["DT_TRADE"])

    _assert_portfolio_has_capital_for_trade(
        portfolio_id=payload.ID_PORTFOLIO,
        dt_trade=dt_trade,
        side=side,
        qtd=float(payload.QTD),
        pu=float(payload.PU),
        custo=float(payload.CUSTO or 0.0),
        exclude_trade_id=trade_id,
    )

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

        recompute_carteira_posicao_diaria_sync(prev_portfolio_id, prev_dt_trade)
        recompute_carteira_posicao_diaria_sync(payload.ID_PORTFOLIO, dt_trade)

        return APIResponse(data={"ID_TRADE": trade_id})
    except Exception as exc:
        logger.exception("Erro em PUT /sim/trades/{trade_id}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/trades/{trade_id}", response_model=APIResponse)
async def excluir_trade(trade_id: int):
    """Exclui uma operação manual no simulador."""
    try:
        prev_trade_df = query(
            "SELECT ID_CARTEIRA, DT_TRADE FROM FAT_CARTEIRA_TRADE WHERE ID_TRADE = ? LIMIT 1",
            params=(trade_id,),
        )
        with managed_connection() as conn:
            cur = conn.execute(
                "DELETE FROM FAT_CARTEIRA_TRADE WHERE ID_TRADE = ?",
                (trade_id,),
            )

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Trade {trade_id} não encontrada")

        if not prev_trade_df.empty:
            rec = prev_trade_df.to_dict("records")[0]
            recompute_carteira_posicao_diaria_sync(int(rec["ID_CARTEIRA"]), str(rec["DT_TRADE"]))

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


def recompute_carteira_posicao_diaria_sync(portfolio_id: int, dt_ref: Optional[str] = None) -> dict:
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
                    ID_CARTEIRA,
                    DT_REFERENCIA,
                    ID_ATIVO,
                    CD_ATIVO,
                    MOEDA,
                    FX_ATUAL,
                    QTD_LIQ,
                    PRECO_MEDIO,
                    PRECO_ATUAL,
                    CUSTO_TOTAL,
                    VALOR_MERCADO,
                    PNL_REALIZADO,
                    PNL_ABERTO,
                    PNL_TOTAL,
                    DT_CARGA
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


@router.get("/carteiras/posicao/serie", response_model=APIResponse)
async def get_carteira_posicao_serie(
    portfolio_id: int = Query(..., description="ID da carteira"),
    dt_inicio: Optional[str] = Query(None),
    dt_fim: Optional[str] = Query(None),
):
    try:
        filtros = ["ID_CARTEIRA = ?"]
        params: list = [portfolio_id]
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
                ID_CARTEIRA AS ID_PORTFOLIO,
                DT_REFERENCIA,
                ID_ATIVO,
                CD_ATIVO,
                MOEDA,
                FX_ATUAL,
                QTD_LIQ,
                PRECO_MEDIO,
                PRECO_ATUAL,
                CUSTO_TOTAL,
                VALOR_MERCADO,
                PNL_REALIZADO,
                PNL_ABERTO,
                PNL_TOTAL,
                DT_CARGA
            FROM FAT_CARTEIRA_POSICAO_DIARIA
            WHERE {where}
            ORDER BY DT_REFERENCIA ASC, ID_ATIVO ASC
            """,
            params=tuple(params),
        )
        items = df.to_dict("records")
        return APIResponse(data={"items": items, "total": len(items)})
    except Exception as exc:
        logger.exception("Erro em GET /sim/carteiras/posicao/serie")
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
    fechamento_df = query(
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

    fluxo_df = query(
        """
        SELECT
            DT_REFERENCIA,
            SUM(CASE WHEN TP_FLUXO = 'APORTE' THEN VL_FLUXO ELSE -VL_FLUXO END) AS VL_FLUXO_LIQ
        FROM FAT_FUNDO_FLUXO_CAPITAL
        WHERE ID_FUNDO = ?
          AND COALESCE(OBSERVACAO, '') <> 'SEED_INICIAL_SETUP'
        GROUP BY DT_REFERENCIA
        """,
        params=(fundo_id,),
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

    dt_primeiro = datas[0]
    pl_primeiro_fechamento = float((fechamento_map.get(dt_primeiro) or {}).get("VL_PL") or 0.0)
    pl_primeira_abertura = query_scalar(
        """
        SELECT COALESCE(VL_VALOR_MERCADO_TOTAL, 0)
        FROM FAT_FUNDO_PNL_LIVE
        WHERE ID_FUNDO = ?
          AND DT_REFERENCIA = ?
        ORDER BY DT_HORA_CAPTURA ASC
        LIMIT 1
        """,
        params=(fundo_id, dt_primeiro),
    )

    pl_base_cotas = float(pl_primeira_abertura or 0.0)
    if abs(pl_base_cotas) <= 1e-12:
        pl_base_cotas = pl_primeiro_fechamento
    if abs(pl_base_cotas) <= 1e-12:
        pl_base_cotas = 1.0

    qt_cotas_atual = pl_base_cotas
    cota_prev = pl_base_cotas / qt_cotas_atual if abs(qt_cotas_atual) > 1e-12 else 1.0
    pl_economico_atual = pl_base_cotas
    pl_fechamento_anterior: Optional[float] = None

    with managed_connection() as conn:
        dt_carga = _now_sp_str()
        for dt_ref in datas:
            fechamento = fechamento_map.get(dt_ref)
            fluxo_liq = float(fluxo_map.get(dt_ref, 0.0))

            if fechamento is not None:
                pl_fech = float(fechamento["VL_PL"] or 0.0)
                if pl_fechamento_anterior is None:
                    pl_economico_atual = pl_fech
                else:
                    pl_economico_atual += pl_fech - pl_fechamento_anterior
                pl_fechamento_anterior = pl_fech

            if abs(fluxo_liq) > 1e-12 and abs(cota_prev) > 1e-12:
                qt_cotas_atual += fluxo_liq / cota_prev
                pl_economico_atual += fluxo_liq

            cota = pl_economico_atual / qt_cotas_atual if abs(qt_cotas_atual) > 1e-12 else 0.0
            dt_hora_fechamento = (
                (fechamento or {}).get("DT_HORA_CAPTURA")
                or f"{dt_ref} 19:00:00"
            )

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
                (
                    fundo_id,
                    dt_ref,
                    cota,
                    qt_cotas_atual,
                    pl_economico_atual,
                    dt_hora_fechamento,
                    dt_carga,
                ),
            )

            cota_prev = cota if abs(cota) > 1e-12 else cota_prev

    result = {
        "ID_FUNDO": fundo_id,
        "QT_DIAS": len(datas),
        "QT_COTAS": qt_cotas_atual,
        "VL_PL_BASE_COTAS": pl_base_cotas,
        "DT_BASE_COTAS": dt_primeiro,
        "VL_COTA_ULTIMA": cota_prev,
    }
    recompute_cotistas_posicao_diaria_sync(fundo_id=fundo_id)
    return result


def _compute_cotistas_posicao_snapshot(fundo_id: int, dt_base: str) -> tuple[list[dict], float]:
    cota_ref = query_scalar(
        """
        SELECT VL_COTA
        FROM FAT_FUNDO_COTA_DIARIA
        WHERE ID_FUNDO = ? AND DT_REFERENCIA = ?
        LIMIT 1
        """,
        params=(fundo_id, dt_base),
    )
    if cota_ref is None:
        cota_ref = query_scalar(
            """
            SELECT VL_COTA
            FROM FAT_FUNDO_COTA_DIARIA
            WHERE ID_FUNDO = ? AND DT_REFERENCIA <= ?
            ORDER BY DT_REFERENCIA DESC
            LIMIT 1
            """,
            params=(fundo_id, dt_base),
        )
    cota_atual = float(cota_ref or 0.0)
    if cota_ref is None:
        return [], cota_atual

    flows_df = query(
        """
        SELECT
            ffc.ID_TITULAR,
            dt.NM_TITULAR,
            ffc.DT_REFERENCIA,
            ffc.TP_FLUXO,
            ffc.VL_FLUXO
        FROM FAT_FUNDO_FLUXO_CAPITAL ffc
        LEFT JOIN DIM_TITULAR dt ON dt.ID_TITULAR = ffc.ID_TITULAR
        WHERE ffc.ID_FUNDO = ?
          AND ffc.ID_TITULAR IS NOT NULL
          AND ffc.DT_REFERENCIA <= ?
        ORDER BY ffc.DT_REFERENCIA ASC, ffc.ID_FLUXO ASC
        """,
        params=(fundo_id, dt_base),
    )

    cota_hist_df = query(
        """
        SELECT DT_REFERENCIA, VL_COTA
        FROM FAT_FUNDO_COTA_DIARIA
        WHERE ID_FUNDO = ?
          AND DT_REFERENCIA <= ?
        ORDER BY DT_REFERENCIA ASC
        """,
        params=(fundo_id, dt_base),
    )
    cota_hist = [(str(r["DT_REFERENCIA"]), float(r["VL_COTA"] or 0.0)) for r in cota_hist_df.to_dict("records")]

    def _cota_no_dia(dt_ref: str) -> float:
        last = None
        for d, c in cota_hist:
            if d <= dt_ref:
                last = c
            else:
                break
        if last is None or abs(last) <= 1e-12:
            return 1.0
        return last

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
        cota_flow = _cota_no_dia(dt_flow)
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
        items.append(
            {
                **rec,
                "VL_COTA": cota_atual,
                "VL_PL_COTISTA": vl_pl_cotista,
                "VL_PNL_COTISTA": vl_pnl,
            }
        )

    items.sort(key=lambda x: x["NM_TITULAR"])
    return items, cota_atual


def recompute_cotistas_posicao_diaria_sync(fundo_id: int, dt_referencia: Optional[str] = None) -> dict:
    if dt_referencia:
        datas = [dt_referencia]
    else:
        cota_dates_df = query(
            """
            SELECT DT_REFERENCIA
            FROM FAT_FUNDO_COTA_DIARIA
            WHERE ID_FUNDO = ?
            ORDER BY DT_REFERENCIA
            """,
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
                        ID_FUNDO,
                        ID_TITULAR,
                        DT_REFERENCIA,
                        NM_TITULAR,
                        VL_COTA,
                        VL_APORTADO_BRUTO,
                        VL_RESGATADO_BRUTO,
                        VL_INVERTIDO_LIQ,
                        QT_COTAS,
                        VL_PL_COTISTA,
                        VL_PNL_COTISTA,
                        DT_CARGA
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


@router.get("/fundos/retorno", response_model=APIResponse)
async def serie_retorno_fundo(
    fundo_id: int = Query(..., description="ID do fundo"),
    dt_inicio: Optional[str] = Query(None),
    dt_fim: Optional[str] = Query(None),
):
    """Série de retorno do fundo baseada na cota (imune a aportes/resgates)."""
    try:
        data = compute_retorno_serie_sync(fundo_id, dt_inicio, dt_fim)
        return APIResponse(data=data)
    except Exception as exc:
        logger.exception("Erro em GET /sim/fundos/retorno")
        raise HTTPException(status_code=500, detail=str(exc))


def compute_retorno_serie_sync(
    fundo_id: int,
    dt_inicio: Optional[str] = None,
    dt_fim: Optional[str] = None,
) -> dict:
    """Lê FAT_FUNDO_COTA_DIARIA e calcula retorno diário + acumulado."""
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
        SELECT DT_REFERENCIA, VL_COTA
        FROM FAT_FUNDO_COTA_DIARIA
        WHERE {where}
        ORDER BY DT_REFERENCIA
        """,
        params=tuple(params),
    )

    records = df.to_dict("records")
    if not records:
        return {"items": [], "total": 0}

    cota_base = float(records[0]["VL_COTA"] or 0.0)
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


@router.get("/fundos/fluxos", response_model=APIResponse)
async def listar_fluxos_fundo(
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
                ID_FLUXO,
                ID_FUNDO,
                ffc.ID_TITULAR,
                dt.NM_TITULAR,
                DT_REFERENCIA,
                TP_FLUXO,
                VL_FLUXO,
                ffc.OBSERVACAO,
                ffc.DT_CARGA
            FROM FAT_FUNDO_FLUXO_CAPITAL ffc
            LEFT JOIN DIM_TITULAR dt ON dt.ID_TITULAR = ffc.ID_TITULAR
            WHERE {where}
            ORDER BY DT_REFERENCIA ASC, ID_FLUXO ASC
            """,
            params=tuple(params),
        )
        items = df.to_dict("records")
        return APIResponse(data={"items": items, "total": len(items)})
    except Exception as exc:
        logger.exception("Erro em GET /sim/fundos/fluxos")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/fundos/dashboard", response_model=APIResponse)
async def dashboard_fundo_consolidado(
    fundo_id: int = Query(..., description="ID do fundo"),
    dt_inicio: Optional[str] = Query(None),
    dt_fim: Optional[str] = Query(None),
    dt_referencia: Optional[str] = Query(None, description="Data para posição de cotistas (default: dt_fim)"),
):
    try:
        exists_fundo = query_scalar(
            "SELECT COUNT(*) FROM DIM_FUNDO WHERE ID_FUNDO = ?",
            params=(fundo_id,),
        )
        if not exists_fundo:
            raise HTTPException(status_code=404, detail=f"Fundo {fundo_id} não encontrado")

        filtros = ["ID_FUNDO = ?"]
        params_base: list = [fundo_id]
        if dt_inicio:
            filtros.append("DT_REFERENCIA >= ?")
            params_base.append(dt_inicio)
        if dt_fim:
            filtros.append("DT_REFERENCIA <= ?")
            params_base.append(dt_fim)
        where = " AND ".join(filtros)

        pnl_df = query(
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
            params=tuple(params_base),
        )
        pnl_items = pnl_df.to_dict("records")

        cota_df = query(
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
            params=tuple(params_base),
        )
        cota_items = cota_df.to_dict("records")

        fluxos_df = query(
            f"""
            SELECT
                ID_FLUXO,
                ID_FUNDO,
                ffc.ID_TITULAR,
                dt.NM_TITULAR,
                DT_REFERENCIA,
                TP_FLUXO,
                VL_FLUXO,
                ffc.OBSERVACAO,
                ffc.DT_CARGA
            FROM FAT_FUNDO_FLUXO_CAPITAL ffc
            LEFT JOIN DIM_TITULAR dt ON dt.ID_TITULAR = ffc.ID_TITULAR
            WHERE {where}
            ORDER BY DT_REFERENCIA ASC, ID_FLUXO ASC
            """,
            params=tuple(params_base),
        )
        fluxos_items = fluxos_df.to_dict("records")

        dt_base = dt_referencia or dt_fim
        if not dt_base:
            dt_last = query_scalar(
                """
                SELECT DT_REFERENCIA
                FROM FAT_FUNDO_COTA_DIARIA
                WHERE ID_FUNDO = ?
                ORDER BY DT_REFERENCIA DESC
                LIMIT 1
                """,
                params=(fundo_id,),
            )
            dt_base = str(dt_last) if dt_last else None

        cotistas_items: list[dict] = []
        vl_cota_ref = None
        if dt_base:
            cotistas_df = query(
                """
                SELECT
                    ID_FUNDO,
                    ID_TITULAR,
                    DT_REFERENCIA,
                    NM_TITULAR,
                    VL_COTA,
                    VL_APORTADO_BRUTO,
                    VL_RESGATADO_BRUTO,
                    VL_INVERTIDO_LIQ,
                    QT_COTAS,
                    VL_PL_COTISTA,
                    VL_PNL_COTISTA
                FROM FAT_COTISTA_POSICAO_DIARIA
                WHERE ID_FUNDO = ?
                  AND DT_REFERENCIA = ?
                ORDER BY NM_TITULAR
                """,
                params=(fundo_id, dt_base),
            )
            if cotistas_df.empty:
                recompute_cotistas_posicao_diaria_sync(fundo_id=fundo_id, dt_referencia=dt_base)
                cotistas_df = query(
                    """
                    SELECT
                        ID_FUNDO,
                        ID_TITULAR,
                        DT_REFERENCIA,
                        NM_TITULAR,
                        VL_COTA,
                        VL_APORTADO_BRUTO,
                        VL_RESGATADO_BRUTO,
                        VL_INVERTIDO_LIQ,
                        QT_COTAS,
                        VL_PL_COTISTA,
                        VL_PNL_COTISTA
                    FROM FAT_COTISTA_POSICAO_DIARIA
                    WHERE ID_FUNDO = ?
                      AND DT_REFERENCIA = ?
                    ORDER BY NM_TITULAR
                    """,
                    params=(fundo_id, dt_base),
                )
            cotistas_items = cotistas_df.to_dict("records")
            vl_cota_ref = float(cotistas_items[0]["VL_COTA"]) if cotistas_items else None

        last_pnl = pnl_items[-1] if pnl_items else None
        last_cota = cota_items[-1] if cota_items else None

        return APIResponse(
            data={
                "ID_FUNDO": fundo_id,
                "periodo": {"DT_INICIO": dt_inicio, "DT_FIM": dt_fim},
                "resumo": {
                    "ULTIMA_DATA_PNL": last_pnl.get("DT_REFERENCIA") if last_pnl else None,
                    "ULTIMA_DATA_COTA": last_cota.get("DT_REFERENCIA") if last_cota else None,
                    "VL_PL_ULTIMO": float(last_pnl.get("VL_VALOR_MERCADO_TOTAL") or 0.0) if last_pnl else 0.0,
                    "VL_PNL_ULTIMO": float(last_pnl.get("VL_PNL_TOTAL") or 0.0) if last_pnl else 0.0,
                    "VL_COTA_ULTIMA": float(last_cota.get("VL_COTA") or 0.0) if last_cota else 0.0,
                },
                "pnl_fechamento": {"items": pnl_items, "total": len(pnl_items)},
                "cotas": {"items": cota_items, "total": len(cota_items)},
                "fluxos": {"items": fluxos_items, "total": len(fluxos_items)},
                "cotistas_posicao": {
                    "items": cotistas_items,
                    "total": len(cotistas_items),
                    "DT_REFERENCIA": dt_base,
                    "VL_COTA": vl_cota_ref,
                },
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em GET /sim/fundos/dashboard")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/ativos/liquidez", response_model=APIResponse)
async def listar_ativos_liquidez():
    try:
        df = query(
            """
            SELECT
                da.ID_ATIVO,
                da.CD_ATIVO,
                COALESCE(sal.NR_DIAS_LIQUIDEZ, 0) AS NR_DIAS_LIQUIDEZ,
                sal.DS_REGRA,
                COALESCE(sal.ST_ATIVO, 1) AS ST_ATIVO,
                sal.DT_ATUALIZACAO
            FROM DIM_ATIVO da
            LEFT JOIN SIM_ATIVO_LIQUIDEZ sal ON sal.ID_ATIVO = da.ID_ATIVO
            ORDER BY da.CD_ATIVO
            """
        )
        items = df.to_dict("records")
        return APIResponse(data={"items": items, "total": len(items)})
    except Exception as exc:
        logger.exception("Erro em GET /sim/ativos/liquidez")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/ativos/liquidez", response_model=APIResponse, status_code=201)
async def upsert_ativo_liquidez(payload: AtivoLiquidezInput):
    try:
        exists_ativo = query_scalar(
            "SELECT COUNT(*) FROM DIM_ATIVO WHERE ID_ATIVO = ?",
            params=(payload.ID_ATIVO,),
        )
        if not exists_ativo:
            raise HTTPException(status_code=404, detail=f"Ativo {payload.ID_ATIVO} não encontrado")

        with managed_connection() as conn:
            now_sp = _now_sp_str()
            conn.execute(
                """
                INSERT INTO SIM_ATIVO_LIQUIDEZ (
                    ID_ATIVO,
                    NR_DIAS_LIQUIDEZ,
                    DS_REGRA,
                    ST_ATIVO,
                    DT_CRIACAO,
                    DT_ATUALIZACAO
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(ID_ATIVO) DO UPDATE SET
                    NR_DIAS_LIQUIDEZ = excluded.NR_DIAS_LIQUIDEZ,
                    DS_REGRA = excluded.DS_REGRA,
                    ST_ATIVO = excluded.ST_ATIVO,
                    DT_ATUALIZACAO = datetime('now', '-3 hours')
                """,
                (
                    payload.ID_ATIVO,
                    int(payload.NR_DIAS_LIQUIDEZ),
                    payload.DS_REGRA,
                    int(payload.ST_ATIVO),
                    now_sp,
                    now_sp,
                ),
            )
        return APIResponse(data={"ID_ATIVO": payload.ID_ATIVO})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em POST /sim/ativos/liquidez")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/rf/titulos", response_model=APIResponse)
async def listar_rf_titulos(st_ativo: Optional[int] = Query(None)):
    try:
        filtros: list[str] = []
        params: list = []
        if st_ativo is not None:
            filtros.append("rf.ST_ATIVO = ?")
            params.append(int(st_ativo))

        where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""
        df = query(
            f"""
            SELECT
                rf.ID_TITULO,
                rf.CD_TITULO,
                rf.NM_TITULO,
                rf.ID_ATIVO,
                da.CD_ATIVO,
                rf.DT_VENCIMENTO,
                rf.DT_RESGATE,
                COALESCE(rf.DT_RESGATE, rf.DT_VENCIMENTO) AS DT_LIQUIDEZ,
                rf.VL_TAXA_CONTRATADA,
                rf.ST_ATIVO,
                rf.DT_CRIACAO,
                rf.DT_ATUALIZACAO
            FROM SIM_RF_TITULO rf
            LEFT JOIN DIM_ATIVO da ON da.ID_ATIVO = rf.ID_ATIVO
            {where_clause}
            ORDER BY COALESCE(rf.DT_RESGATE, rf.DT_VENCIMENTO), rf.CD_TITULO
            """,
            params=tuple(params),
        )
        items = df.to_dict("records")
        return APIResponse(data={"items": items, "total": len(items)})
    except Exception as exc:
        logger.exception("Erro em GET /sim/rf/titulos")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/rf/titulos", response_model=APIResponse, status_code=201)
async def criar_rf_titulo(payload: RFTituloInput):
    try:
        cd_titulo = payload.CD_TITULO.strip().upper()
        if not cd_titulo:
            raise HTTPException(status_code=422, detail="CD_TITULO é obrigatório")

        dt_venc = date.fromisoformat(payload.DT_VENCIMENTO)
        dt_resgate = date.fromisoformat(payload.DT_RESGATE) if payload.DT_RESGATE else None
        if dt_resgate and dt_resgate > dt_venc:
            raise HTTPException(status_code=422, detail="DT_RESGATE não pode ser maior que DT_VENCIMENTO")

        if payload.ID_ATIVO is not None:
            exists_ativo = query_scalar(
                "SELECT COUNT(*) FROM DIM_ATIVO WHERE ID_ATIVO = ?",
                params=(int(payload.ID_ATIVO),),
            )
            if not exists_ativo:
                raise HTTPException(status_code=404, detail=f"Ativo {payload.ID_ATIVO} não encontrado")

        exists_cd = query_scalar(
            "SELECT COUNT(*) FROM SIM_RF_TITULO WHERE UPPER(CD_TITULO) = ?",
            params=(cd_titulo,),
        )
        if int(exists_cd or 0) > 0:
            raise HTTPException(status_code=409, detail=f"Título RF {cd_titulo} já cadastrado")

        with managed_connection() as conn:
            now_sp = _now_sp_str()
            cur = conn.execute(
                """
                INSERT INTO SIM_RF_TITULO (
                    CD_TITULO,
                    NM_TITULO,
                    ID_ATIVO,
                    DT_VENCIMENTO,
                    DT_RESGATE,
                    VL_TAXA_CONTRATADA,
                    ST_ATIVO,
                    DT_CRIACAO,
                    DT_ATUALIZACAO
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cd_titulo,
                    payload.NM_TITULO,
                    payload.ID_ATIVO,
                    dt_venc.isoformat(),
                    dt_resgate.isoformat() if dt_resgate else None,
                    payload.VL_TAXA_CONTRATADA,
                    int(payload.ST_ATIVO),
                    now_sp,
                    now_sp,
                ),
            )

        return APIResponse(data={"ID_TITULO": cur.lastrowid})
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Data inválida: {exc}")
    except Exception as exc:
        logger.exception("Erro em POST /sim/rf/titulos")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/fundos/liquidez/opcoes", response_model=APIResponse)
async def opcoes_liquidez_fundo(
    fundo_id: int = Query(..., description="ID do fundo"),
):
    try:
        exists_fundo = query_scalar(
            "SELECT COUNT(*) FROM DIM_FUNDO WHERE ID_FUNDO = ?",
            params=(fundo_id,),
        )
        if not exists_fundo:
            raise HTTPException(status_code=404, detail=f"Fundo {fundo_id} não encontrado")

        payload = _get_fundo_positions_payload_sync(fundo_id=fundo_id)
        items = payload.get("items", [])
        if not items:
            return APIResponse(data={"items": [], "total": 0})

        ids_ativos = [int(item["ID_ATIVO"]) for item in items]
        placeholders = ",".join(["?"] * len(ids_ativos))
        liquidez_df = query(
            f"""
            SELECT ID_ATIVO, COALESCE(NR_DIAS_LIQUIDEZ, 0) AS NR_DIAS_LIQUIDEZ, DS_REGRA
            FROM SIM_ATIVO_LIQUIDEZ
            WHERE ID_ATIVO IN ({placeholders})
            """,
            params=tuple(ids_ativos),
        )
        liquidez_map = {
            int(r["ID_ATIVO"]): {
                "NR_DIAS_LIQUIDEZ": int(r["NR_DIAS_LIQUIDEZ"] or 0),
                "DS_REGRA": r.get("DS_REGRA"),
            }
            for r in liquidez_df.to_dict("records")
        }

        out = []
        for item in items:
            ativo_id = int(item["ID_ATIVO"])
            liq = liquidez_map.get(ativo_id, {"NR_DIAS_LIQUIDEZ": 0, "DS_REGRA": None})
            out.append(
                {
                    "ID_ATIVO": ativo_id,
                    "CD_ATIVO": item.get("CD_ATIVO"),
                    "VALOR_MERCADO": float(item.get("VALOR_MERCADO") or 0.0),
                    "QTD_LIQ": float(item.get("QTD_LIQ") or 0.0),
                    "NR_DIAS_LIQUIDEZ": int(liq["NR_DIAS_LIQUIDEZ"]),
                    "DS_REGRA": liq["DS_REGRA"],
                }
            )

        out.sort(key=lambda x: (x["NR_DIAS_LIQUIDEZ"], x["CD_ATIVO"] or ""))
        return APIResponse(data={"items": out, "total": len(out)})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em GET /sim/fundos/liquidez/opcoes")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fundos/resgates/solicitacoes", response_model=APIResponse, status_code=201)
async def criar_solicitacao_resgate(payload: ResgateSolicitacaoInput):
    try:
        exists_fundo = query_scalar(
            "SELECT COUNT(*) FROM DIM_FUNDO WHERE ID_FUNDO = ?",
            params=(payload.ID_FUNDO,),
        )
        if not exists_fundo:
            raise HTTPException(status_code=404, detail=f"Fundo {payload.ID_FUNDO} não encontrado")

        if payload.ID_TITULAR is not None:
            exists_titular = query_scalar(
                "SELECT COUNT(*) FROM DIM_TITULAR WHERE ID_TITULAR = ?",
                params=(payload.ID_TITULAR,),
            )
            if not exists_titular:
                raise HTTPException(status_code=404, detail=f"Titular {payload.ID_TITULAR} não encontrado")

        with managed_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO FAT_FUNDO_RESGATE_SOLICITACAO (
                    ID_FUNDO,
                    ID_TITULAR,
                    DT_SOLICITACAO,
                    VL_RESGATE,
                    ST_STATUS,
                    DS_OBSERVACAO,
                    DT_CARGA
                ) VALUES (?, ?, ?, ?, 'ABERTA', ?, ?)
                """,
                (
                    payload.ID_FUNDO,
                    payload.ID_TITULAR,
                    payload.DT_SOLICITACAO,
                    float(payload.VL_RESGATE),
                    payload.DS_OBSERVACAO,
                    _now_sp_str(),
                ),
            )
            solicitacao_id = cur.lastrowid

        return APIResponse(data={"ID_SOLICITACAO": solicitacao_id, "ID_FUNDO": payload.ID_FUNDO})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em POST /sim/fundos/resgates/solicitacoes")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/fundos/resgates/solicitacoes", response_model=APIResponse)
async def listar_solicitacoes_resgate(
    fundo_id: int = Query(..., description="ID do fundo"),
    st_status: Optional[str] = Query(None),
):
    try:
        filtros = ["frs.ID_FUNDO = ?"]
        params: list = [fundo_id]
        if st_status:
            filtros.append("frs.ST_STATUS = ?")
            params.append(st_status)
        where = " AND ".join(filtros)

        df = query(
            f"""
            SELECT
                frs.ID_SOLICITACAO,
                frs.ID_FUNDO,
                frs.ID_TITULAR,
                dt.NM_TITULAR,
                frs.DT_SOLICITACAO,
                frs.VL_RESGATE,
                frs.ST_STATUS,
                frs.DS_OBSERVACAO,
                frs.DT_CARGA
            FROM FAT_FUNDO_RESGATE_SOLICITACAO frs
            LEFT JOIN DIM_TITULAR dt ON dt.ID_TITULAR = frs.ID_TITULAR
            WHERE {where}
            ORDER BY frs.DT_SOLICITACAO DESC, frs.ID_SOLICITACAO DESC
            """,
            params=tuple(params),
        )
        items = df.to_dict("records")
        return APIResponse(data={"items": items, "total": len(items)})
    except Exception as exc:
        logger.exception("Erro em GET /sim/fundos/resgates/solicitacoes")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fundos/resgates/planos", response_model=APIResponse, status_code=201)
async def criar_plano_resgate(payload: ResgatePlanoInput):
    try:
        solic_df = query(
            """
            SELECT ID_SOLICITACAO, ID_FUNDO, DT_SOLICITACAO, VL_RESGATE, ST_STATUS
            FROM FAT_FUNDO_RESGATE_SOLICITACAO
            WHERE ID_SOLICITACAO = ?
            LIMIT 1
            """,
            params=(payload.ID_SOLICITACAO,),
        )
        if solic_df.empty:
            raise HTTPException(status_code=404, detail=f"Solicitação {payload.ID_SOLICITACAO} não encontrada")

        solic = solic_df.to_dict("records")[0]
        if str(solic.get("ST_STATUS") or "").upper() == "CANCELADA":
            raise HTTPException(status_code=409, detail="Solicitação cancelada não pode receber plano")

        if not payload.items:
            raise HTTPException(status_code=422, detail="Plano precisa de ao menos 1 item de liquidação")

        ids_ativos = [int(i.ID_ATIVO) for i in payload.items]
        placeholders = ",".join(["?"] * len(ids_ativos))
        ativos_df = query(
            f"""
            SELECT ID_ATIVO, CD_ATIVO
            FROM DIM_ATIVO
            WHERE ID_ATIVO IN ({placeholders})
            """,
            params=tuple(ids_ativos),
        )
        ativos_map = {int(r["ID_ATIVO"]): str(r["CD_ATIVO"]) for r in ativos_df.to_dict("records")}
        for ativo_id in ids_ativos:
            if ativo_id not in ativos_map:
                raise HTTPException(status_code=404, detail=f"Ativo {ativo_id} não encontrado")

        liquidez_df = query(
            f"""
            SELECT ID_ATIVO, COALESCE(NR_DIAS_LIQUIDEZ, 0) AS NR_DIAS_LIQUIDEZ
            FROM SIM_ATIVO_LIQUIDEZ
            WHERE ID_ATIVO IN ({placeholders})
            """,
            params=tuple(ids_ativos),
        )
        liq_map = {int(r["ID_ATIVO"]): int(r["NR_DIAS_LIQUIDEZ"] or 0) for r in liquidez_df.to_dict("records")}

        dt_solic = date.fromisoformat(str(solic["DT_SOLICITACAO"]))
        vl_solic = float(solic["VL_RESGATE"] or 0.0)
        vl_total_plano = sum(float(item.VL_LIQUIDAR) for item in payload.items)

        max_rev = query_scalar(
            "SELECT COALESCE(MAX(NR_REVISAO), 0) FROM FAT_FUNDO_RESGATE_PLANO WHERE ID_SOLICITACAO = ?",
            params=(payload.ID_SOLICITACAO,),
        )
        nova_revisao = int(max_rev or 0) + 1

        with managed_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO FAT_FUNDO_RESGATE_PLANO (
                    ID_SOLICITACAO,
                    NR_REVISAO,
                    CD_METODO,
                    ST_STATUS,
                    DS_JUSTIFICATIVA,
                    DT_CARGA
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.ID_SOLICITACAO,
                    nova_revisao,
                    (payload.CD_METODO or "MANUAL_GESTOR").upper(),
                    (payload.ST_STATUS or "RASCUNHO").upper(),
                    payload.DS_JUSTIFICATIVA,
                    _now_sp_str(),
                ),
            )
            plano_id = cur.lastrowid

            for item in payload.items:
                dias = int(item.NR_DIAS_LIQUIDEZ) if item.NR_DIAS_LIQUIDEZ is not None else int(liq_map.get(item.ID_ATIVO, 0))
                dt_prev = (dt_solic + timedelta(days=max(dias, 0))).isoformat()
                conn.execute(
                    """
                    INSERT INTO FAT_FUNDO_RESGATE_ITEM (
                        ID_PLANO,
                        ID_ATIVO,
                        VL_LIQUIDAR,
                        NR_DIAS_LIQUIDEZ,
                        DT_LIQUIDEZ_PREVISTA,
                        DS_OBSERVACAO,
                        DT_CARGA
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plano_id,
                        int(item.ID_ATIVO),
                        float(item.VL_LIQUIDAR),
                        dias,
                        dt_prev,
                        item.DS_OBSERVACAO,
                        _now_sp_str(),
                    ),
                )

            novo_status = "PLANEJADA" if vl_total_plano >= vl_solic else "PARCIAL"
            conn.execute(
                """
                UPDATE FAT_FUNDO_RESGATE_SOLICITACAO
                SET ST_STATUS = ?
                WHERE ID_SOLICITACAO = ?
                """,
                (novo_status, payload.ID_SOLICITACAO),
            )

        return APIResponse(
            data={
                "ID_PLANO": plano_id,
                "ID_SOLICITACAO": payload.ID_SOLICITACAO,
                "NR_REVISAO": nova_revisao,
                "VL_TOTAL_PLANO": vl_total_plano,
                "VL_RESGATE_SOLICITADO": vl_solic,
                "ST_STATUS_SOLICITACAO": "PLANEJADA" if vl_total_plano >= vl_solic else "PARCIAL",
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em POST /sim/fundos/resgates/planos")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/fundos/resgates/planos", response_model=APIResponse)
async def listar_planos_resgate(
    solicitacao_id: int = Query(..., description="ID da solicitação"),
):
    try:
        planos_df = query(
            """
            SELECT
                frp.ID_PLANO,
                frp.ID_SOLICITACAO,
                frp.NR_REVISAO,
                frp.CD_METODO,
                frp.ST_STATUS,
                frp.DS_JUSTIFICATIVA,
                frp.DT_CARGA
            FROM FAT_FUNDO_RESGATE_PLANO frp
            WHERE frp.ID_SOLICITACAO = ?
            ORDER BY frp.NR_REVISAO DESC, frp.ID_PLANO DESC
            """,
            params=(solicitacao_id,),
        )
        planos = planos_df.to_dict("records")

        if not planos:
            return APIResponse(data={"items": [], "total": 0})

        plano_ids = [int(p["ID_PLANO"]) for p in planos]
        placeholders = ",".join(["?"] * len(plano_ids))
        items_df = query(
            f"""
            SELECT
                fri.ID_ITEM,
                fri.ID_PLANO,
                fri.ID_ATIVO,
                da.CD_ATIVO,
                fri.VL_LIQUIDAR,
                fri.NR_DIAS_LIQUIDEZ,
                fri.DT_LIQUIDEZ_PREVISTA,
                fri.DS_OBSERVACAO,
                fri.DT_CARGA
            FROM FAT_FUNDO_RESGATE_ITEM fri
            JOIN DIM_ATIVO da ON da.ID_ATIVO = fri.ID_ATIVO
            WHERE fri.ID_PLANO IN ({placeholders})
            ORDER BY fri.ID_ITEM
            """,
            params=tuple(plano_ids),
        )

        items_by_plano: dict[int, list] = {}
        for row in items_df.to_dict("records"):
            items_by_plano.setdefault(int(row["ID_PLANO"]), []).append(row)

        eventos_df = query(
            f"""
            SELECT
                ID_PLANO,
                SUM(CASE WHEN TP_EVENTO IN ('EXEC_PARCIAL', 'EXEC_TOTAL') THEN COALESCE(VL_EVENTO, 0) ELSE 0 END) AS VL_TOTAL_EXECUTADO
            FROM FAT_FUNDO_RESGATE_EVENTO
            WHERE ID_PLANO IN ({placeholders})
            GROUP BY ID_PLANO
            """,
            params=tuple(plano_ids),
        )
        executado_by_plano = {
            int(r["ID_PLANO"]): float(r["VL_TOTAL_EXECUTADO"] or 0.0)
            for r in eventos_df.to_dict("records")
        }

        out = []
        for plano in planos:
            pid = int(plano["ID_PLANO"])
            rows = items_by_plano.get(pid, [])
            plano["VL_TOTAL_PLANEJADO"] = sum(float(r.get("VL_LIQUIDAR") or 0.0) for r in rows)
            plano["VL_TOTAL_EXECUTADO"] = executado_by_plano.get(pid, 0.0)
            plano["items"] = rows
            out.append(plano)

        return APIResponse(data={"items": out, "total": len(out)})
    except Exception as exc:
        logger.exception("Erro em GET /sim/fundos/resgates/planos")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/fundos/resgates/planos/{plano_id}/eventos", response_model=APIResponse)
async def listar_eventos_plano_resgate(plano_id: int):
    try:
        exists = query_scalar(
            "SELECT COUNT(*) FROM FAT_FUNDO_RESGATE_PLANO WHERE ID_PLANO = ?",
            params=(plano_id,),
        )
        if not exists:
            raise HTTPException(status_code=404, detail=f"Plano {plano_id} não encontrado")

        df = query(
            """
            SELECT
                ID_EVENTO,
                ID_FUNDO,
                ID_SOLICITACAO,
                ID_PLANO,
                DT_REFERENCIA,
                TP_EVENTO,
                VL_EVENTO,
                DS_JUSTIFICATIVA,
                DS_OBSERVACAO,
                DT_CARGA
            FROM FAT_FUNDO_RESGATE_EVENTO
            WHERE ID_PLANO = ?
            ORDER BY DT_REFERENCIA ASC, ID_EVENTO ASC
            """,
            params=(plano_id,),
        )
        items = df.to_dict("records")
        return APIResponse(data={"items": items, "total": len(items)})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em GET /sim/fundos/resgates/planos/{plano_id}/eventos")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fundos/resgates/planos/{plano_id}/executar", response_model=APIResponse)
async def executar_plano_resgate(plano_id: int, payload: ResgateExecucaoInput):
    try:
        plano_df = query(
            """
            SELECT
                p.ID_PLANO,
                p.ID_SOLICITACAO,
                p.ST_STATUS AS ST_STATUS_PLANO,
                s.ID_FUNDO,
                s.ID_TITULAR,
                s.VL_RESGATE,
                s.ST_STATUS AS ST_STATUS_SOLICITACAO
            FROM FAT_FUNDO_RESGATE_PLANO p
            JOIN FAT_FUNDO_RESGATE_SOLICITACAO s ON s.ID_SOLICITACAO = p.ID_SOLICITACAO
            WHERE p.ID_PLANO = ?
            LIMIT 1
            """,
            params=(plano_id,),
        )
        if plano_df.empty:
            raise HTTPException(status_code=404, detail=f"Plano {plano_id} não encontrado")

        rec = plano_df.to_dict("records")[0]
        if str(rec.get("ST_STATUS_SOLICITACAO") or "").upper() == "CANCELADA":
            raise HTTPException(status_code=409, detail="Solicitação cancelada não pode ser executada")

        id_solic = int(rec["ID_SOLICITACAO"])
        id_fundo = int(rec["ID_FUNDO"])
        id_titular = rec.get("ID_TITULAR")
        vl_solic = float(rec.get("VL_RESGATE") or 0.0)

        vl_exec_total = float(
            query_scalar(
                """
                SELECT COALESCE(SUM(VL_EVENTO), 0)
                FROM FAT_FUNDO_RESGATE_EVENTO
                WHERE ID_PLANO = ?
                  AND TP_EVENTO IN ('EXEC_PARCIAL','EXEC_TOTAL')
                """,
                params=(plano_id,),
            )
            or 0.0
        )

        saldo_exec = max(vl_solic - vl_exec_total, 0.0)
        if saldo_exec <= 1e-9:
            raise HTTPException(status_code=409, detail="Plano já executado integralmente")

        vl_exec = float(payload.VL_EXECUTADO) if payload.VL_EXECUTADO is not None else saldo_exec
        if vl_exec <= 0:
            raise HTTPException(status_code=422, detail="VL_EXECUTADO deve ser maior que zero")
        if vl_exec - saldo_exec > 1e-9:
            raise HTTPException(status_code=409, detail=f"Execução acima do saldo pendente ({saldo_exec:.2f})")

        tp_evento = "EXEC_TOTAL" if abs(vl_exec - saldo_exec) <= 1e-9 else "EXEC_PARCIAL"
        st_solic = "LIQUIDADA" if tp_evento == "EXEC_TOTAL" else "PARCIAL"
        st_plano = "EXECUTADO" if tp_evento == "EXEC_TOTAL" else "APROVADO"

        with managed_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO FAT_FUNDO_RESGATE_EVENTO (
                    ID_FUNDO,
                    ID_SOLICITACAO,
                    ID_PLANO,
                    DT_REFERENCIA,
                    TP_EVENTO,
                    VL_EVENTO,
                    DS_JUSTIFICATIVA,
                    DS_OBSERVACAO,
                    DT_CARGA
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    id_fundo,
                    id_solic,
                    plano_id,
                    payload.DT_REFERENCIA,
                    tp_evento,
                    vl_exec,
                    payload.DS_OBSERVACAO,
                    _now_sp_str(),
                ),
            )
            evento_id = int(cur.lastrowid)

            conn.execute(
                """
                INSERT INTO FAT_FUNDO_FLUXO_CAPITAL (
                    ID_FUNDO,
                    ID_TITULAR,
                    DT_REFERENCIA,
                    TP_FLUXO,
                    VL_FLUXO,
                    OBSERVACAO,
                    DT_CARGA
                ) VALUES (?, ?, ?, 'RESGATE', ?, ?, ?)
                """,
                (
                    id_fundo,
                    id_titular,
                    payload.DT_REFERENCIA,
                    vl_exec,
                    f"Execução de plano #{plano_id}",
                    _now_sp_str(),
                ),
            )

            conn.execute(
                "UPDATE FAT_FUNDO_RESGATE_SOLICITACAO SET ST_STATUS = ? WHERE ID_SOLICITACAO = ?",
                (st_solic, id_solic),
            )
            conn.execute(
                "UPDATE FAT_FUNDO_RESGATE_PLANO SET ST_STATUS = ? WHERE ID_PLANO = ?",
                (st_plano, plano_id),
            )

        cota_info = recompute_fundo_cotas_sync(id_fundo)
        return APIResponse(
            data={
                "ID_EVENTO": evento_id,
                "ID_PLANO": plano_id,
                "ID_SOLICITACAO": id_solic,
                "TP_EVENTO": tp_evento,
                "VL_EXECUTADO": vl_exec,
                "VL_SALDO_RESGATE": max(saldo_exec - vl_exec, 0.0),
                "ST_STATUS_SOLICITACAO": st_solic,
                "ST_STATUS_PLANO": st_plano,
                "COTA": cota_info,
            }
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em POST /sim/fundos/resgates/planos/{plano_id}/executar")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/fundos/resgates/planos/{plano_id}/override-mtm", response_model=APIResponse)
async def registrar_override_mtm_resgate(plano_id: int, payload: ResgateOverrideInput):
    try:
        plano_df = query(
            """
            SELECT
                p.ID_PLANO,
                p.ID_SOLICITACAO,
                s.ID_FUNDO
            FROM FAT_FUNDO_RESGATE_PLANO p
            JOIN FAT_FUNDO_RESGATE_SOLICITACAO s ON s.ID_SOLICITACAO = p.ID_SOLICITACAO
            WHERE p.ID_PLANO = ?
            LIMIT 1
            """,
            params=(plano_id,),
        )
        if plano_df.empty:
            raise HTTPException(status_code=404, detail=f"Plano {plano_id} não encontrado")

        rec = plano_df.to_dict("records")[0]
        id_solic = int(rec["ID_SOLICITACAO"])
        id_fundo = int(rec["ID_FUNDO"])

        with managed_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO FAT_FUNDO_RESGATE_EVENTO (
                    ID_FUNDO,
                    ID_SOLICITACAO,
                    ID_PLANO,
                    DT_REFERENCIA,
                    TP_EVENTO,
                    VL_EVENTO,
                    DS_JUSTIFICATIVA,
                    DS_OBSERVACAO,
                    DT_CARGA
                ) VALUES (?, ?, ?, ?, 'OVERRIDE_MTM', ?, ?, NULL, ?)
                """,
                (
                    id_fundo,
                    id_solic,
                    plano_id,
                    payload.DT_REFERENCIA,
                    float(payload.VL_EVENTO or 0.0),
                    payload.DS_JUSTIFICATIVA.strip(),
                    _now_sp_str(),
                ),
            )
            evento_id = int(cur.lastrowid)

        return APIResponse(data={"ID_EVENTO": evento_id, "ID_PLANO": plano_id, "TP_EVENTO": "OVERRIDE_MTM"})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em POST /sim/fundos/resgates/planos/{plano_id}/override-mtm")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/fundos/cotistas/posicao", response_model=APIResponse)
async def posicao_cotistas_fundo(
    fundo_id: int = Query(..., description="ID do fundo"),
    dt_referencia: Optional[str] = Query(None, description="Data base YYYY-MM-DD (default: última cota)"),
):
    try:
        exists_fundo = query_scalar(
            "SELECT COUNT(*) FROM DIM_FUNDO WHERE ID_FUNDO = ?",
            params=(fundo_id,),
        )
        if not exists_fundo:
            raise HTTPException(status_code=404, detail=f"Fundo {fundo_id} não encontrado")

        if dt_referencia:
            dt_base = dt_referencia
        else:
            row = query(
                """
                SELECT DT_REFERENCIA
                FROM FAT_FUNDO_COTA_DIARIA
                WHERE ID_FUNDO = ?
                ORDER BY DT_REFERENCIA DESC
                LIMIT 1
                """,
                params=(fundo_id,),
            )
            if row.empty:
                return APIResponse(data={"items": [], "total": 0, "DT_REFERENCIA": None, "VL_COTA": None})
            dt_base = str(row.to_dict("records")[0]["DT_REFERENCIA"])

        items_df = query(
            """
            SELECT
                ID_FUNDO,
                ID_TITULAR,
                DT_REFERENCIA,
                NM_TITULAR,
                VL_COTA,
                VL_APORTADO_BRUTO,
                VL_RESGATADO_BRUTO,
                VL_INVERTIDO_LIQ,
                QT_COTAS,
                VL_PL_COTISTA,
                VL_PNL_COTISTA
            FROM FAT_COTISTA_POSICAO_DIARIA
            WHERE ID_FUNDO = ?
              AND DT_REFERENCIA = ?
            ORDER BY NM_TITULAR
            """,
            params=(fundo_id, dt_base),
        )

        if items_df.empty:
            recompute_cotistas_posicao_diaria_sync(fundo_id=fundo_id, dt_referencia=dt_base)
            items_df = query(
                """
                SELECT
                    ID_FUNDO,
                    ID_TITULAR,
                    DT_REFERENCIA,
                    NM_TITULAR,
                    VL_COTA,
                    VL_APORTADO_BRUTO,
                    VL_RESGATADO_BRUTO,
                    VL_INVERTIDO_LIQ,
                    QT_COTAS,
                    VL_PL_COTISTA,
                    VL_PNL_COTISTA
                FROM FAT_COTISTA_POSICAO_DIARIA
                WHERE ID_FUNDO = ?
                  AND DT_REFERENCIA = ?
                ORDER BY NM_TITULAR
                """,
                params=(fundo_id, dt_base),
            )

        items = items_df.to_dict("records")
        vl_cota = float(items[0]["VL_COTA"]) if items else None
        return APIResponse(data={"items": items, "total": len(items), "DT_REFERENCIA": dt_base, "VL_COTA": vl_cota})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em GET /sim/fundos/cotistas/posicao")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/fundos/cotistas/posicao/serie", response_model=APIResponse)
async def posicao_cotistas_fundo_serie(
    fundo_id: int = Query(..., description="ID do fundo"),
    dt_inicio: Optional[str] = Query(None, description="Data inicial YYYY-MM-DD"),
    dt_fim: Optional[str] = Query(None, description="Data final YYYY-MM-DD"),
):
    try:
        exists_fundo = query_scalar(
            "SELECT COUNT(*) FROM DIM_FUNDO WHERE ID_FUNDO = ?",
            params=(fundo_id,),
        )
        if not exists_fundo:
            raise HTTPException(status_code=404, detail=f"Fundo {fundo_id} não encontrado")

        where = ["ID_FUNDO = ?"]
        params: list = [fundo_id]
        if dt_inicio:
            where.append("DT_REFERENCIA >= ?")
            params.append(dt_inicio)
        if dt_fim:
            where.append("DT_REFERENCIA <= ?")
            params.append(dt_fim)

        where_clause = " AND ".join(where)
        count = query_scalar(f"SELECT COUNT(*) FROM FAT_COTISTA_POSICAO_DIARIA WHERE {where_clause}", params=tuple(params))
        if int(count or 0) == 0:
            recompute_cotistas_posicao_diaria_sync(fundo_id=fundo_id)

        serie_df = query(
            f"""
            SELECT
                ID_FUNDO,
                ID_TITULAR,
                NM_TITULAR,
                DT_REFERENCIA,
                VL_COTA,
                VL_APORTADO_BRUTO,
                VL_RESGATADO_BRUTO,
                VL_INVERTIDO_LIQ,
                QT_COTAS,
                VL_PL_COTISTA,
                VL_PNL_COTISTA
            FROM FAT_COTISTA_POSICAO_DIARIA
            WHERE {where_clause}
            ORDER BY NM_TITULAR, DT_REFERENCIA
            """,
            params=tuple(params),
        )

        return APIResponse(data={"items": serie_df.to_dict("records"), "total": len(serie_df)})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em GET /sim/fundos/cotistas/posicao/serie")
        raise HTTPException(status_code=500, detail=str(exc))
