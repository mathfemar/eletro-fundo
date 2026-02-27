"""
sim/caixa.py — Cálculo de caixa e validação de capital para trades.
"""

import logging
from typing import Optional

from fastapi import HTTPException

from app.services.db_connection import query, query_scalar

logger = logging.getLogger("app.api.simulador")


def _saldo_carteira_caixa(id_fundo: int, id_carteira: int, dt_limite: Optional[str] = None) -> float:
    """Saldo de caixa de uma carteira específica (apenas movimentos de caixa, sem trades)."""
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
    """Caixa líquido total do fundo = movimentos (net) + impacto de trades.

    Movimentos: APORTE_INICIAL, ALOCACAO_ENTRADA, APORTE_COTISTA → +
                Todo o resto → −
                (ALOCACAO_SAIDA + ALOCACAO_ENTRADA se cancelam no nível fundo)

    Trades: SELL → devolve caixa (+), BUY → consome caixa (−)
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
    """Valida que a carteira tem capital para a operação (BUY).

    Rejeita operações em carteiras CAIXA.
    Para BUY: verifica saldo de caixa (movimentos + trades) ≥ valor da ordem.
    """
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
            detail="Carteira sem vínculo de fundo. Vincule a carteira a um fundo antes de registrar operações.",
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
