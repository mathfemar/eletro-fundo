"""
db_setup.py — Cria as tabelas de preços caso não existam.

Chamado no lifespan da API para garantir que o schema existe antes de qualquer request.
"""

import logging
from app.services.db_connection import execute

logger = logging.getLogger("app.services.precos.db_setup")


def create_tables() -> None:
    """Cria as tabelas e índices de preços se ainda não existirem."""

    # ── FAT_PRICING_LIVE ─────────────────────────────────────────────────────
    # Estado atual do preço de cada ativo. Sempre 1 linha por ID_ATIVO (UPSERT).
    execute("""
        CREATE TABLE IF NOT EXISTS FAT_PRICING_LIVE (
            ID_ATIVO                INTEGER PRIMARY KEY,
            VL_PRECO_ATUAL          REAL    NOT NULL,
            VL_PRECO_ABERTURA       REAL,
            VL_PRECO_MAX            REAL,
            VL_PRECO_MIN            REAL,
            VL_VOLUME_DIA           REAL,
            VL_VAR_DIA              REAL,
            VL_VAR_DIA_PCT          REAL,
            VL_PRECO_FECHAMENTO_ANT REAL,
            DT_REFERENCIA           DATE,
            DT_HORA_CAPTURA         DATETIME NOT NULL DEFAULT (datetime('now', '-3 hours')),
            CD_FONTE                TEXT     DEFAULT 'yfinance',
            FOREIGN KEY (ID_ATIVO) REFERENCES DIM_ATIVO(ID_ATIVO)
        )
    """)

    execute("""
        CREATE INDEX IF NOT EXISTS idx_live_dt_captura
            ON FAT_PRICING_LIVE(DT_REFERENCIA)
    """)

    # ── FAT_PRICING_LIVE_HIST ───────────────────────────────────────────────
    # Histórico intradiário dos snapshots live (append-only).
    execute("""
        CREATE TABLE IF NOT EXISTS FAT_PRICING_LIVE_HIST (
            ID_LIVE_HIST            INTEGER PRIMARY KEY AUTOINCREMENT,
            ID_ATIVO                INTEGER NOT NULL,
            VL_PRECO_ATUAL          REAL    NOT NULL,
            VL_PRECO_ABERTURA       REAL,
            VL_PRECO_MAX            REAL,
            VL_PRECO_MIN            REAL,
            VL_VOLUME_DIA           REAL,
            VL_VAR_DIA              REAL,
            VL_VAR_DIA_PCT          REAL,
            VL_PRECO_FECHAMENTO_ANT REAL,
            DT_REFERENCIA           DATE,
            DT_HORA_CAPTURA         DATETIME NOT NULL,
            CD_FONTE                TEXT     DEFAULT 'yfinance',
            FOREIGN KEY (ID_ATIVO) REFERENCES DIM_ATIVO(ID_ATIVO)
        )
    """)

    execute("""
        CREATE INDEX IF NOT EXISTS idx_live_hist_ativo_captura
            ON FAT_PRICING_LIVE_HIST(ID_ATIVO, DT_HORA_CAPTURA)
    """)

    execute("""
        CREATE INDEX IF NOT EXISTS idx_live_hist_captura
            ON FAT_PRICING_LIVE_HIST(DT_HORA_CAPTURA)
    """)

    # ── FAT_ATIVO_PRECO ───────────────────────────────────────────────────────
    # Série histórica OHLCV diária. Append-only — nunca sobrescreve.
    # VL_FECHAMENTO_AJ = Adj Close (ajustado por splits/dividendos) → use para retornos.
    execute("""
        CREATE TABLE IF NOT EXISTS FAT_ATIVO_PRECO (
            ID_PRECO         INTEGER PRIMARY KEY AUTOINCREMENT,
            ID_ATIVO         INTEGER NOT NULL,
            DT_REFERENCIA    DATE    NOT NULL,
            VL_ABERTURA      REAL,
            VL_MAXIMA        REAL,
            VL_MINIMA        REAL,
            VL_FECHAMENTO    REAL,
            VL_FECHAMENTO_AJ REAL,
            VL_VOLUME        REAL,
            CD_MOEDA         TEXT    DEFAULT 'BRL',
            CD_FONTE         TEXT    DEFAULT 'yfinance',
            DT_CARGA         DATETIME DEFAULT (datetime('now', '-3 hours')),
            FOREIGN KEY (ID_ATIVO) REFERENCES DIM_ATIVO(ID_ATIVO)
        )
    """)

    execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_fap_ativo_dt
            ON FAT_ATIVO_PRECO(ID_ATIVO, DT_REFERENCIA)
    """)

    execute("""
        CREATE INDEX IF NOT EXISTS idx_fap_dt
            ON FAT_ATIVO_PRECO(DT_REFERENCIA)
    """)

    logger.info("✓ Tabelas FAT_PRICING_LIVE, FAT_PRICING_LIVE_HIST e FAT_ATIVO_PRECO verificadas/criadas.")
