"""
db_connection.py — Conexão com o banco SQLite do Fundinho

Uso básico:
    from db_connection import query, execute, get_connection

    # Query com f-string (retorna DataFrame)
    tabela = "cotacoes"
    ticker = "PETR4.SA"
    df = query(f"SELECT * FROM {tabela} WHERE ticker = '{ticker}'")

    # Query parametrizada (mais segura para inputs externos)
    df = query("SELECT * FROM cotacoes WHERE ticker = ?", params=("PETR4.SA",))

    # Execute sem retorno (INSERT, CREATE TABLE, etc.)
    execute(f"DELETE FROM {tabela} WHERE ticker = '{ticker}'")

    # Acesso à conexão bruta (para uso avançado)
    with get_connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL")

Arquivo do banco: Fundinho/Fundinho.db (na raiz do projeto)
"""

import sqlite3
import os
import logging
from contextlib import contextmanager
from typing import Any, Optional

import pandas as pd

# ─── Configuração ────────────────────────────────────────────────────────────

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DATABASE_PATH", os.path.join(_BASE_DIR, "Fundinho"))

_logger = logging.getLogger("db_connection")


# ─── Conexão ─────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """
    Retorna uma conexão SQLite com row_factory e timeout configurados.

    Exemplo:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()

    Ou como context manager (fecha automaticamente):
        with get_connection() as conn:
            conn.execute("PRAGMA integrity_check")
    """
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row        # acesso por nome de coluna
    conn.execute("PRAGMA journal_mode=WAL")  # melhor concorrência
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def managed_connection():
    """
    Context manager que garante fechamento da conexão mesmo em caso de erro.

    Exemplo:
        with managed_connection() as conn:
            conn.execute("INSERT INTO ...")
    """
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

    Aceita tanto f-strings quanto queries parametrizadas (? placeholders).

    Args:
        sql:    Query SQL — pode ser f-string ou string com ?
        params: Tupla de parâmetros para ? placeholders (opcional)

    Returns:
        pd.DataFrame com os resultados (vazio se não houver linhas)

    Exemplos:
        # f-string (mais legível para queries fixas)
        tabela = "cotacoes"
        df = query(f"SELECT * FROM {tabela} ORDER BY data DESC LIMIT 30")

        # Parametrizado (use para valores vindos do usuário/externa)
        df = query("SELECT * FROM cotacoes WHERE ticker = ?", params=("PETR4.SA",))

        # Combinado
        tabela = "cotacoes"
        df = query(f"SELECT * FROM {tabela} WHERE ticker = ?", params=("PETR4.SA",))
    """
    with managed_connection() as conn:
        if params:
            return pd.read_sql(sql, conn, params=params)
        return pd.read_sql(sql, conn)


def query_one(sql: str, params: Optional[tuple] = None) -> Optional[dict]:
    """
    Executa uma SELECT e retorna apenas a primeira linha como dict.
    Retorna None se não houver resultados.

    Exemplo:
        row = query_one(f"SELECT * FROM cotacoes WHERE ticker = 'PETR4.SA' LIMIT 1")
        if row:
            print(row["fechamento"])
    """
    with managed_connection() as conn:
        cursor = conn.execute(sql, params or ())
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)


def query_scalar(sql: str, params: Optional[tuple] = None) -> Any:
    """
    Executa uma SELECT e retorna apenas o primeiro valor da primeira linha.
    Útil para COUNT, MAX, SUM, etc.

    Exemplo:
        total = query_scalar(f"SELECT COUNT(*) FROM cotacoes")
        ultima_data = query_scalar(f"SELECT MAX(data) FROM cotacoes WHERE ticker = 'PETR4.SA'")
    """
    with managed_connection() as conn:
        cursor = conn.execute(sql, params or ())
        row = cursor.fetchone()
        return row[0] if row else None


# ─── Execute (sem retorno) ────────────────────────────────────────────────────

def execute(sql: str, params: Optional[tuple] = None) -> int:
    """
    Executa um comando SQL sem retorno de dados (INSERT, UPDATE, DELETE, CREATE, etc.).

    Args:
        sql:    Comando SQL — pode ser f-string
        params: Tupla de parâmetros para ? placeholders (opcional)

    Returns:
        int: Número de linhas afetadas (rowcount)

    Exemplos:
        tabela = "cotacoes"

        # CREATE TABLE via f-string
        execute(f'''
            CREATE TABLE IF NOT EXISTS {tabela} (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker  TEXT NOT NULL,
                data    TEXT NOT NULL,
                fechamento REAL
            )
        ''')

        # DELETE
        execute(f"DELETE FROM {tabela} WHERE ticker = 'PETR4.SA'")

        # INSERT parametrizado
        execute(
            "INSERT INTO cotacoes (ticker, data, fechamento) VALUES (?, ?, ?)",
            params=("PETR4.SA", "2025-01-02", 38.50)
        )
    """
    with managed_connection() as conn:
        cursor = conn.execute(sql, params or ())
        return cursor.rowcount


def execute_many(sql: str, data: list[tuple]) -> int:
    """
    Executa o mesmo comando SQL para múltiplas linhas de uma vez (batch insert/update).

    Args:
        sql:  Comando com ? placeholders
        data: Lista de tuplas com os valores de cada linha

    Returns:
        int: Total de linhas afetadas

    Exemplo:
        rows = [("PETR4.SA", "2025-01-02", 38.50), ("VALE3.SA", "2025-01-02", 70.10)]
        execute_many("INSERT OR REPLACE INTO cotacoes (ticker, data, fechamento) VALUES (?,?,?)", rows)
    """
    with managed_connection() as conn:
        cursor = conn.executemany(sql, data)
        return cursor.rowcount


# ─── Helpers de DataFrame ─────────────────────────────────────────────────────

def df_to_db(df: pd.DataFrame, table: str, if_exists: str = "append") -> int:
    """
    Salva um DataFrame inteiro no banco. Wrapper conveniente sobre df.to_sql().

    Args:
        df:        DataFrame a salvar
        table:     Nome da tabela destino
        if_exists: 'append' (padrão), 'replace' ou 'fail'

    Returns:
        int: Número de linhas inseridas

    Exemplo:
        df_cotacoes = yf.download("PETR4.SA", period="1y")
        df_to_db(df_cotacoes, "cotacoes")
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
    """Retorna informações das colunas de uma tabela (nome, tipo, nullable, default)."""
    return query(f"PRAGMA table_info({table})")
