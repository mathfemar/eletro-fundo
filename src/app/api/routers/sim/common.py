"""
sim/common.py — Helpers, Pydantic models e utilitários compartilhados do simulador.
"""

import logging
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.api.models.common import APIResponse
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


# ── Pydantic Models ──────────────────────────────────────────────────────────

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


# ── Motor de posições ────────────────────────────────────────────────────────

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
    import math

    for id_ativo, rec in state.items():
        qtd = float(rec["QTD_LIQ"])
        if abs(qtd) <= 1e-12:
            continue

        px_info = price_map.get(id_ativo, {})
        preco_atual_local = px_info.get("PRECO_ATUAL")
        
        # Se não há preço no banco, o Pandas retorna NaN ou None.
        # Fallback para o preço médio para a posição não zerar o PL.
        if preco_atual_local is None or (isinstance(preco_atual_local, float) and math.isnan(preco_atual_local)):
            preco_atual_local = rec["PRECO_MEDIO"]

        fx_atual = _get_fx_rate(rec["MOEDA"], dt_mark_to_market, fx_asset_ids, fx_cache)
        preco_atual = (float(preco_atual_local) * fx_atual) if preco_atual_local is not None else None
        
        pm = rec["PRECO_MEDIO"]
        
        # Se ainda assim não tiver preço atual (não deveria ocorrer com o fallback), assume valor de mercado = custo
        if preco_atual is None and pm is not None:
            preco_atual = float(pm) * fx_atual

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


# ── Helpers de caixa ─────────────────────────────────────────────────────────

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


def _get_fundo_caixa_total_sync(fundo_id: int, dt_ref: Optional[str] = None) -> float:
    """Calcula o caixa líquido total de um fundo (movimentos + impacto de trades).

    Caixa = Entradas (aportes, alocações) - Saídas
           + SELL trades (devolvem caixa)
           - BUY trades (consomem caixa)
    """
    # 1) Saldo de movimentos de caixa
    sql_mov = """
        SELECT COALESCE(
            SUM(
                CASE
                    WHEN TP_MOVIMENTO IN ('APORTE_INICIAL', 'ALOCACAO_ENTRADA', 'APORTE_COTISTA')
                        THEN VL_MOVIMENTO
                    ELSE -VL_MOVIMENTO
                END
            ), 0
        )
        FROM FAT_CARTEIRA_MOVIMENTO_CAIXA
        WHERE ID_FUNDO = ?
    """
    params_mov: list = [fundo_id]
    if dt_ref:
        sql_mov += " AND DT_MOVIMENTO <= ? "
        params_mov.append(dt_ref)
    saldo_mov = float(query_scalar(sql_mov, params=tuple(params_mov)) or 0.0)

    # 2) Impacto de trades sobre o caixa
    sql_trade = """
        WITH carteira_fundo AS (
            SELECT DISTINCT rfc.ID_CARTEIRA
            FROM RL_FUNDO_CARTEIRA rfc
            WHERE rfc.ID_FUNDO = ?
              AND (rfc.ST_ATIVO = 1 OR rfc.DT_FIM IS NULL)
        )
        SELECT COALESCE(
            SUM(
                CASE
                    WHEN t.SIDE = 'SELL' THEN (t.QTD * t.PU) - COALESCE(t.CUSTO, 0)
                    WHEN t.SIDE = 'BUY'  THEN -((t.QTD * t.PU) + COALESCE(t.CUSTO, 0))
                    ELSE 0
                END
            ), 0
        )
        FROM FAT_CARTEIRA_TRADE t
        JOIN carteira_fundo cf ON cf.ID_CARTEIRA = t.ID_CARTEIRA
    """
    params_trade: list = [fundo_id]
    if dt_ref:
        sql_trade += " WHERE substr(COALESCE(t.DT_HORA_EXEC, t.DT_TRADE || ' 00:00:00'), 1, 10) <= ? "
        params_trade.append(dt_ref)
    saldo_trades = float(query_scalar(sql_trade, params=tuple(params_trade)) or 0.0)

    return saldo_mov + saldo_trades


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


# ── Helpers de posições de fundo ─────────────────────────────────────────────

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
