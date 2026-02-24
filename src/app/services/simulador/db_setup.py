"""
db_setup.py — Cria tabelas do simulador de fundos (Sprint 1).
"""

import logging
from app.services.db_connection import execute, query_scalar

logger = logging.getLogger("app.services.simulador.db_setup")


def create_tables() -> None:
    """Cria as tabelas e índices do simulador se ainda não existirem."""

    execute("""
        CREATE TABLE IF NOT EXISTS SIM_PORTFOLIO (
            ID_PORTFOLIO  INTEGER PRIMARY KEY AUTOINCREMENT,
            NM_PORTFOLIO  TEXT NOT NULL,
            DT_INICIO     DATE NOT NULL,
            BENCHMARK     TEXT,
            MOEDA_BASE    TEXT DEFAULT 'BRL',
            ST_ATIVO      INTEGER DEFAULT 1,
            DT_CRIACAO    DATETIME DEFAULT (datetime('now', '-3 hours')),
            DT_ATUALIZACAO DATETIME DEFAULT (datetime('now', '-3 hours'))
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS SIM_TRADE (
            ID_TRADE      INTEGER PRIMARY KEY AUTOINCREMENT,
            ID_PORTFOLIO  INTEGER NOT NULL,
            ID_ATIVO      INTEGER NOT NULL,
            DT_HORA_EXEC  DATETIME NOT NULL,
            DT_TRADE      DATE NOT NULL,
            SIDE          TEXT NOT NULL CHECK (SIDE IN ('BUY','SELL','SHORT','COVER')),
            QTD           REAL NOT NULL,
            PU            REAL NOT NULL,
            CUSTO         REAL DEFAULT 0,
            OBSERVACAO    TEXT,
            CD_FONTE      TEXT DEFAULT 'manual',
            DT_CARGA      DATETIME DEFAULT (datetime('now', '-3 hours')),
            FOREIGN KEY (ID_PORTFOLIO) REFERENCES SIM_PORTFOLIO(ID_PORTFOLIO),
            FOREIGN KEY (ID_ATIVO) REFERENCES DIM_ATIVO(ID_ATIVO)
        )
    """)

    execute("""
        CREATE INDEX IF NOT EXISTS idx_sim_trade_portfolio_dt
            ON SIM_TRADE(ID_PORTFOLIO, DT_HORA_EXEC)
    """)

    execute("""
        CREATE INDEX IF NOT EXISTS idx_sim_trade_ativo
            ON SIM_TRADE(ID_ATIVO)
    """)

    # Migração leve para bases já existentes (quando tabela foi criada sem DT_HORA_EXEC)
    try:
        execute("ALTER TABLE SIM_TRADE ADD COLUMN DT_HORA_EXEC DATETIME")
        execute("UPDATE SIM_TRADE SET DT_HORA_EXEC = COALESCE(DT_HORA_EXEC, DT_TRADE || ' 00:00:00')")
    except Exception:
        # Coluna já existe (ou tabela ainda não criada) — pode ignorar.
        pass

    # ── Nova modelagem dimensional ──────────────────────────────────────────
    execute("""
        CREATE TABLE IF NOT EXISTS DIM_FUNDO (
            ID_FUNDO             INTEGER PRIMARY KEY AUTOINCREMENT,
            NM_FUNDO             TEXT NOT NULL,
            DS_ESTRATEGIA        TEXT,
            BENCHMARK            TEXT,
            MOEDA_BASE           TEXT DEFAULT 'BRL',
            ST_ATIVO             INTEGER DEFAULT 1,
            NR_LEGACY_PORTFOLIO  INTEGER UNIQUE,
            DT_CRIACAO           DATETIME DEFAULT (datetime('now', '-3 hours')),
            DT_ATUALIZACAO       DATETIME DEFAULT (datetime('now', '-3 hours'))
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS DIM_TITULAR (
            ID_TITULAR      INTEGER PRIMARY KEY AUTOINCREMENT,
            NM_TITULAR      TEXT NOT NULL UNIQUE,
            NR_DOCUMENTO    TEXT,
            ST_ATIVO        INTEGER DEFAULT 1,
            DT_CRIACAO      DATETIME DEFAULT (datetime('now', '-3 hours')),
            DT_ATUALIZACAO  DATETIME DEFAULT (datetime('now', '-3 hours'))
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS DIM_CORRETORA (
            ID_CORRETORA    INTEGER PRIMARY KEY AUTOINCREMENT,
            NM_CORRETORA    TEXT NOT NULL UNIQUE,
            CD_CORRETORA    TEXT,
            ST_ATIVO        INTEGER DEFAULT 1,
            DT_CRIACAO      DATETIME DEFAULT (datetime('now', '-3 hours')),
            DT_ATUALIZACAO  DATETIME DEFAULT (datetime('now', '-3 hours'))
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS DIM_CARTEIRA (
            ID_CARTEIRA           INTEGER PRIMARY KEY AUTOINCREMENT,
            ID_TITULAR            INTEGER NOT NULL,
            ID_CORRETORA          INTEGER NOT NULL,
            NM_CARTEIRA           TEXT NOT NULL,
            CONTA_REF             TEXT,
            MOEDA_BASE            TEXT DEFAULT 'BRL',
            ST_ATIVO              INTEGER DEFAULT 1,
            NR_LEGACY_PORTFOLIO   INTEGER UNIQUE,
            DT_CRIACAO            DATETIME DEFAULT (datetime('now', '-3 hours')),
            DT_ATUALIZACAO        DATETIME DEFAULT (datetime('now', '-3 hours')),
            FOREIGN KEY (ID_TITULAR) REFERENCES DIM_TITULAR(ID_TITULAR),
            FOREIGN KEY (ID_CORRETORA) REFERENCES DIM_CORRETORA(ID_CORRETORA)
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS RL_FUNDO_CARTEIRA (
            ID_FUNDO        INTEGER NOT NULL,
            ID_CARTEIRA     INTEGER NOT NULL,
            DT_INICIO       DATE NOT NULL,
            DT_FIM          DATE,
            ST_ATIVO        INTEGER DEFAULT 1,
            DT_CRIACAO      DATETIME DEFAULT (datetime('now', '-3 hours')),
            DT_ATUALIZACAO  DATETIME DEFAULT (datetime('now', '-3 hours')),
            PRIMARY KEY (ID_FUNDO, ID_CARTEIRA, DT_INICIO),
            FOREIGN KEY (ID_FUNDO) REFERENCES DIM_FUNDO(ID_FUNDO),
            FOREIGN KEY (ID_CARTEIRA) REFERENCES DIM_CARTEIRA(ID_CARTEIRA)
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS FAT_CARTEIRA_TRADE (
            ID_TRADE            INTEGER PRIMARY KEY AUTOINCREMENT,
            ID_CARTEIRA         INTEGER NOT NULL,
            ID_ATIVO            INTEGER NOT NULL,
            DT_HORA_EXEC        DATETIME NOT NULL,
            DT_TRADE            DATE NOT NULL,
            SIDE                TEXT NOT NULL CHECK (SIDE IN ('BUY','SELL','SHORT','COVER')),
            QTD                 REAL NOT NULL,
            PU                  REAL NOT NULL,
            CUSTO               REAL DEFAULT 0,
            OBSERVACAO          TEXT,
            CD_FONTE            TEXT DEFAULT 'manual',
            NR_LEGACY_TRADE     INTEGER UNIQUE,
            DT_CARGA            DATETIME DEFAULT (datetime('now', '-3 hours')),
            FOREIGN KEY (ID_CARTEIRA) REFERENCES DIM_CARTEIRA(ID_CARTEIRA),
            FOREIGN KEY (ID_ATIVO) REFERENCES DIM_ATIVO(ID_ATIVO)
        )
    """)

    execute("""
        CREATE INDEX IF NOT EXISTS idx_dim_carteira_titular_corretora
            ON DIM_CARTEIRA(ID_TITULAR, ID_CORRETORA)
    """)

    execute("""
        CREATE INDEX IF NOT EXISTS idx_rl_fundo_carteira_fundo
            ON RL_FUNDO_CARTEIRA(ID_FUNDO, ST_ATIVO)
    """)

    execute("""
        CREATE INDEX IF NOT EXISTS idx_fat_carteira_trade_carteira_dt
            ON FAT_CARTEIRA_TRADE(ID_CARTEIRA, DT_HORA_EXEC)
    """)

    execute("""
        CREATE INDEX IF NOT EXISTS idx_fat_carteira_trade_ativo
            ON FAT_CARTEIRA_TRADE(ID_ATIVO)
    """)

    # ── PnL live e fechamento diário de fundo ──────────────────────────────
    execute("""
        CREATE TABLE IF NOT EXISTS FAT_FUNDO_PNL_LIVE (
            ID_PNL_LIVE            INTEGER PRIMARY KEY AUTOINCREMENT,
            ID_FUNDO               INTEGER NOT NULL,
            DT_REFERENCIA          DATE NOT NULL,
            DT_HORA_CAPTURA        DATETIME NOT NULL,
            VL_VALOR_MERCADO_TOTAL REAL DEFAULT 0,
            VL_PNL_ABERTO_TOTAL    REAL DEFAULT 0,
            VL_PNL_REALIZADO_TOTAL REAL DEFAULT 0,
            VL_PNL_TOTAL           REAL DEFAULT 0,
            CD_FONTE               TEXT DEFAULT 'simulador',
            FL_REPROCESSADO        INTEGER DEFAULT 0,
            DT_CARGA               DATETIME DEFAULT (datetime('now', '-3 hours')),
            FOREIGN KEY (ID_FUNDO) REFERENCES DIM_FUNDO(ID_FUNDO)
        )
    """)

    execute("""
        CREATE INDEX IF NOT EXISTS idx_fundo_pnl_live_fundo_dt
            ON FAT_FUNDO_PNL_LIVE(ID_FUNDO, DT_REFERENCIA, DT_HORA_CAPTURA)
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS FAT_FUNDO_PNL_FECHAMENTO (
            ID_FUNDO               INTEGER NOT NULL,
            DT_REFERENCIA          DATE NOT NULL,
            DT_HORA_CAPTURA        DATETIME NOT NULL,
            VL_VALOR_MERCADO_TOTAL REAL DEFAULT 0,
            VL_PNL_ABERTO_TOTAL    REAL DEFAULT 0,
            VL_PNL_REALIZADO_TOTAL REAL DEFAULT 0,
            VL_PNL_TOTAL           REAL DEFAULT 0,
            CD_METODO              TEXT DEFAULT 'snapshot_ultimo_dia',
            FL_REPROCESSADO        INTEGER DEFAULT 0,
            DT_CARGA               DATETIME DEFAULT (datetime('now', '-3 hours')),
            PRIMARY KEY (ID_FUNDO, DT_REFERENCIA),
            FOREIGN KEY (ID_FUNDO) REFERENCES DIM_FUNDO(ID_FUNDO)
        )
    """)

    execute("""
        CREATE INDEX IF NOT EXISTS idx_fundo_pnl_fechamento_dt
            ON FAT_FUNDO_PNL_FECHAMENTO(DT_REFERENCIA)
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS FAT_FUNDO_COTA_DIARIA (
            ID_FUNDO            INTEGER NOT NULL,
            DT_REFERENCIA       DATE NOT NULL,
            VL_COTA             REAL NOT NULL,
            QT_COTAS            REAL NOT NULL,
            VL_PL               REAL NOT NULL,
            DT_HORA_FECHAMENTO  DATETIME,
            CD_METODO           TEXT DEFAULT 'pl_sobre_cotas_constantes',
            FL_REPROCESSADO     INTEGER DEFAULT 0,
            DT_CARGA            DATETIME DEFAULT (datetime('now', '-3 hours')),
            PRIMARY KEY (ID_FUNDO, DT_REFERENCIA),
            FOREIGN KEY (ID_FUNDO) REFERENCES DIM_FUNDO(ID_FUNDO)
        )
    """)

    execute("""
        CREATE INDEX IF NOT EXISTS idx_fundo_cota_diaria_dt
            ON FAT_FUNDO_COTA_DIARIA(DT_REFERENCIA)
    """)

    execute("""
        CREATE VIEW IF NOT EXISTS VW_FUNDO_PNL_LIVE_ULTIMO_DIA AS
        WITH max_cap AS (
            SELECT
                ID_FUNDO,
                DT_REFERENCIA,
                MAX(DT_HORA_CAPTURA) AS DT_HORA_CAPTURA
            FROM FAT_FUNDO_PNL_LIVE
            GROUP BY ID_FUNDO, DT_REFERENCIA
        )
        SELECT
            l.ID_FUNDO,
            l.DT_REFERENCIA,
            l.DT_HORA_CAPTURA,
            l.VL_VALOR_MERCADO_TOTAL,
            l.VL_PNL_ABERTO_TOTAL,
            l.VL_PNL_REALIZADO_TOTAL,
            l.VL_PNL_TOTAL,
            l.CD_FONTE,
            l.FL_REPROCESSADO,
            l.DT_CARGA
        FROM FAT_FUNDO_PNL_LIVE l
        JOIN max_cap m
          ON m.ID_FUNDO = l.ID_FUNDO
         AND m.DT_REFERENCIA = l.DT_REFERENCIA
         AND m.DT_HORA_CAPTURA = l.DT_HORA_CAPTURA
    """)

    # ── Migração inicial SIM_* -> DIM/RL/FAT (idempotente) ─────────────────
    execute("""
        INSERT OR IGNORE INTO DIM_TITULAR (NM_TITULAR, NR_DOCUMENTO, ST_ATIVO, DT_CRIACAO, DT_ATUALIZACAO)
        VALUES ('LEGADO', NULL, 1, datetime('now', '-3 hours'), datetime('now', '-3 hours'))
    """)

    execute("""
        INSERT OR IGNORE INTO DIM_CORRETORA (NM_CORRETORA, CD_CORRETORA, ST_ATIVO, DT_CRIACAO, DT_ATUALIZACAO)
        VALUES ('LEGADO', 'LEGADO', 1, datetime('now', '-3 hours'), datetime('now', '-3 hours'))
    """)

    legacy_titular_id = query_scalar(
        "SELECT ID_TITULAR FROM DIM_TITULAR WHERE NM_TITULAR = 'LEGADO' LIMIT 1"
    )
    legacy_corretora_id = query_scalar(
        "SELECT ID_CORRETORA FROM DIM_CORRETORA WHERE NM_CORRETORA = 'LEGADO' LIMIT 1"
    )

    if legacy_titular_id and legacy_corretora_id:
        execute(
            """
            INSERT OR IGNORE INTO DIM_FUNDO
                (NM_FUNDO, DS_ESTRATEGIA, BENCHMARK, MOEDA_BASE, ST_ATIVO, NR_LEGACY_PORTFOLIO, DT_CRIACAO, DT_ATUALIZACAO)
            SELECT
                sp.NM_PORTFOLIO,
                'Migrado de SIM_PORTFOLIO',
                sp.BENCHMARK,
                COALESCE(sp.MOEDA_BASE, 'BRL'),
                COALESCE(sp.ST_ATIVO, 1),
                sp.ID_PORTFOLIO,
                datetime('now', '-3 hours'),
                datetime('now', '-3 hours')
            FROM SIM_PORTFOLIO sp
            WHERE NOT EXISTS (
                SELECT 1
                FROM DIM_FUNDO df
                WHERE df.NR_LEGACY_PORTFOLIO = sp.ID_PORTFOLIO
            )
            """
        )

        execute(
            """
            INSERT OR IGNORE INTO DIM_CARTEIRA
                (ID_TITULAR, ID_CORRETORA, NM_CARTEIRA, CONTA_REF, MOEDA_BASE, ST_ATIVO, NR_LEGACY_PORTFOLIO, DT_CRIACAO, DT_ATUALIZACAO)
            SELECT
                ?,
                ?,
                sp.NM_PORTFOLIO,
                NULL,
                COALESCE(sp.MOEDA_BASE, 'BRL'),
                COALESCE(sp.ST_ATIVO, 1),
                sp.ID_PORTFOLIO,
                datetime('now', '-3 hours'),
                datetime('now', '-3 hours')
            FROM SIM_PORTFOLIO sp
            WHERE NOT EXISTS (
                SELECT 1
                FROM DIM_CARTEIRA dc
                WHERE dc.NR_LEGACY_PORTFOLIO = sp.ID_PORTFOLIO
            )
            """,
            params=(legacy_titular_id, legacy_corretora_id),
        )

        execute(
            """
            INSERT OR IGNORE INTO RL_FUNDO_CARTEIRA
                (ID_FUNDO, ID_CARTEIRA, DT_INICIO, DT_FIM, ST_ATIVO, DT_CRIACAO, DT_ATUALIZACAO)
            SELECT
                df.ID_FUNDO,
                dc.ID_CARTEIRA,
                sp.DT_INICIO,
                NULL,
                1,
                datetime('now', '-3 hours'),
                datetime('now', '-3 hours')
            FROM SIM_PORTFOLIO sp
            JOIN DIM_FUNDO df
              ON df.NR_LEGACY_PORTFOLIO = sp.ID_PORTFOLIO
            JOIN DIM_CARTEIRA dc
              ON dc.NR_LEGACY_PORTFOLIO = sp.ID_PORTFOLIO
            WHERE NOT EXISTS (
                SELECT 1
                FROM RL_FUNDO_CARTEIRA rfc
                WHERE rfc.ID_FUNDO = df.ID_FUNDO
                  AND rfc.ID_CARTEIRA = dc.ID_CARTEIRA
                  AND rfc.DT_INICIO = sp.DT_INICIO
            )
            """
        )

        execute(
            """
            INSERT OR IGNORE INTO FAT_CARTEIRA_TRADE
                (ID_CARTEIRA, ID_ATIVO, DT_HORA_EXEC, DT_TRADE, SIDE, QTD, PU, CUSTO, OBSERVACAO, CD_FONTE, NR_LEGACY_TRADE, DT_CARGA)
            SELECT
                dc.ID_CARTEIRA,
                st.ID_ATIVO,
                COALESCE(st.DT_HORA_EXEC, st.DT_TRADE || ' 00:00:00'),
                st.DT_TRADE,
                st.SIDE,
                st.QTD,
                st.PU,
                COALESCE(st.CUSTO, 0),
                st.OBSERVACAO,
                COALESCE(st.CD_FONTE, 'manual'),
                st.ID_TRADE,
                                COALESCE(st.DT_CARGA, datetime('now', '-3 hours'))
            FROM SIM_TRADE st
            JOIN DIM_CARTEIRA dc
              ON dc.NR_LEGACY_PORTFOLIO = st.ID_PORTFOLIO
            WHERE NOT EXISTS (
                SELECT 1
                FROM FAT_CARTEIRA_TRADE fct
                WHERE fct.NR_LEGACY_TRADE = st.ID_TRADE
            )
            """
        )

    logger.info(
        "✓ Schema simulador pronto: legado (SIM_*) + dimensional (DIM_FUNDO, DIM_TITULAR, DIM_CORRETORA, DIM_CARTEIRA, RL_FUNDO_CARTEIRA, FAT_CARTEIRA_TRADE)."
    )
