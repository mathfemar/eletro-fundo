"""
db_connection.py — Conexão com o banco SQLite do Fundinho

Uso básico:
    from app.services.db_connection import query, execute, get_connection

    # Query com f-string (retorna DataFrame)
    tabela = "cotacoes"
    ticker = "PETR4.SA"
    df = query(f"SELECT * FROM {tabela} WHERE ticker = '{ticker}'")

    # Query parametrizada (mais segura para inputs externos)
    df = query("SELECT * FROM cotacoes WHERE ticker = ?", params=("PETR4.SA",))

    # Execute sem retorno (INSERT, CREATE TABLE, etc.)
    execute(f"DELETE FROM {tabela} WHERE ticker = '{ticker}'")
"""

import sqlite3
import os
import logging
from contextlib import contextmanager
from typing import Any, Optional

import pandas as pd

# ─── Configuração ────────────────────────────────────────────────────────────

# Resolve o caminho do banco em relação à raiz do projeto (três níveis acima de app/services/)
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))          # services/
_ROOT_DIR = os.path.abspath(os.path.join(_SRC_DIR, "..", "..", ".."))  # raiz

DB_PATH = os.getenv("DATABASE_PATH", os.path.join(_ROOT_DIR, "database", "main_db"))

_logger = logging.getLogger("app.db")


# ─── Conexão ─────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Retorna uma conexão SQLite com row_factory e WAL habilitados."""
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def managed_connection():
    """Context manager com commit/rollback automático."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─── Query → DataFrame ───────────────────────────────────────────────────────

def query(sql: str, params: Optional[tuple] = None) -> pd.DataFrame:
    """
    Executa uma SELECT e retorna um DataFrame.

    Aceita f-strings e queries parametrizadas (? placeholders).

    Exemplos:
        tabela = "cotacoes"
        df = query(f"SELECT * FROM {tabela} ORDER BY data DESC LIMIT 30")
        df = query("SELECT * FROM cotacoes WHERE ticker = ?", params=("PETR4.SA",))
        df = query(f"SELECT * FROM {tabela} WHERE ticker = ?", params=("PETR4.SA",))
    """
    with managed_connection() as conn:
        if params:
            return pd.read_sql(sql, conn, params=params)
        return pd.read_sql(sql, conn)


def query_one(sql: str, params: Optional[tuple] = None) -> Optional[dict]:
    """Retorna apenas a primeira linha como dict, ou None."""
    with managed_connection() as conn:
        cursor = conn.execute(sql, params or ())
        row = cursor.fetchone()
        return dict(row) if row else None


def query_scalar(sql: str, params: Optional[tuple] = None) -> Any:
    """Retorna apenas o primeiro valor (útil para COUNT, MAX, SUM)."""
    with managed_connection() as conn:
        cursor = conn.execute(sql, params or ())
        row = cursor.fetchone()
        return row[0] if row else None


# ─── Execute (sem retorno) ────────────────────────────────────────────────────

def execute(sql: str, params: Optional[tuple] = None) -> int:
    """
    Executa INSERT, UPDATE, DELETE, CREATE TABLE, etc.
    Retorna rowcount.

    Exemplos:
        tabela = "cotacoes"
        execute(f"DELETE FROM {tabela} WHERE ticker = 'PETR4.SA'")
        execute("INSERT INTO cotacoes (ticker, data, fechamento) VALUES (?,?,?)",
                params=("PETR4.SA", "2025-01-02", 38.50))
    """
    with managed_connection() as conn:
        cursor = conn.execute(sql, params or ())
        return cursor.rowcount


def execute_many(sql: str, data: list[tuple]) -> int:
    """Batch insert/update. Retorna rowcount total."""
    with managed_connection() as conn:
        cursor = conn.executemany(sql, data)
        return cursor.rowcount


# ─── Helpers de DataFrame ─────────────────────────────────────────────────────

def df_to_db(df: pd.DataFrame, table: str, if_exists: str = "append") -> int:
    """
    Salva um DataFrame inteiro no banco.

    Args:
        if_exists: 'append' (padrão), 'replace' ou 'fail'
    """
    with managed_connection() as conn:
        rows = df.to_sql(table, conn, if_exists=if_exists, index=True)
        return rows or 0


# ─── Utilitários ──────────────────────────────────────────────────────────────

def table_exists(table: str) -> bool:
    """Verifica se uma tabela existe no banco."""
    result = query_scalar(
        f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{table}'"
    )
    return bool(result)


def list_tables() -> list[str]:
    """Retorna lista com os nomes de todas as tabelas do banco."""
    df = query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return df["name"].tolist() if not df.empty else []


def table_info(table: str) -> pd.DataFrame:
    """Retorna informações das colunas de uma tabela."""
    return query(f"PRAGMA table_info({table})")
