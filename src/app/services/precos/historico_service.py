"""
historico_service.py — Carrega série histórica OHLCV em FAT_ATIVO_PRECO.

Fluxo:
    DIM_ATIVO + DIM_ATIVO_MAPPING (CD_YF)
        → yfinance Ticker.history(auto_adjust=False)   ← retorna Open/High/Low/Close/Adj Close/Volume
            → INSERT OR IGNORE em FAT_ATIVO_PRECO      ← append-only, nunca sobrescreve

Incrementalidade:
    Antes de baixar, consulta MAX(DT_REFERENCIA) no banco por ativo.
    Se já existe histórico, baixa apenas D+1 até hoje (evita re-download total).
"""

import math
import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from app.services.db_connection import query, query_one, query_scalar, execute_many

logger = logging.getLogger("app.services.precos.historico")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _safe(val) -> float | None:
    """Converte NaN/None/inf para None (compatível com SQLite)."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def _ultima_data_carregada(id_ativo: int) -> Optional[str]:
    """Retorna a última DT_REFERENCIA carregada para o ativo, ou None se não há dados."""
    return query_scalar(
        "SELECT MAX(DT_REFERENCIA) FROM FAT_ATIVO_PRECO WHERE ID_ATIVO = ?",
        params=(id_ativo,),
    )


def _get_ativos_mapeados(ids_ativo: Optional[list[int]] = None) -> list[dict]:
    """
    Retorna todos os ativos com PRECO_ONLINE=1 e CD_YF mapeado.
    Se ids_ativo for fornecido, filtra apenas esses IDs.
    """
    sql = """
        SELECT
            da.ID_ATIVO,
            da.CD_ATIVO,
            dam.CD_YF
        FROM DIM_ATIVO da
        JOIN DIM_ATIVO_MAPPING dam ON dam.Id_Ativo = da.ID_ATIVO
        WHERE dam.CD_YF IS NOT NULL
          AND TRIM(dam.CD_YF) != ''
          AND da.PRECO_ONLINE = 1
    """
    df = query(sql)
    if ids_ativo:
        df = df[df["ID_ATIVO"].isin(ids_ativo)]
    return df.to_dict("records")


def _download_historico(cd_yf: str, dt_inicio: str, dt_fim: str) -> pd.DataFrame:
    """
    Baixa OHLCV histórico de um ticker via yfinance.

    Retorna DataFrame com colunas normalizadas:
        Open, High, Low, Close, AdjClose, Volume
    O índice é a data do pregão (tz removida).
    """
    import yfinance as yf

    ticker = yf.Ticker(cd_yf)

    # auto_adjust=False → retorna Close raw + Adj Close separados
    df = ticker.history(
        start=dt_inicio,
        end=dt_fim,
        auto_adjust=False,
        actions=False,   # ignora Dividends e Stock Splits (não precisamos aqui)
    )

    if df.empty:
        return df

    # Remove timezone do índice para compatibilidade com DATE do SQLite
    df.index = df.index.tz_localize(None).normalize()

    # Normaliza nomes de colunas para lidar com variações de versão do yfinance
    df.columns = [c.replace(" ", "") for c in df.columns]

    # Garante coluna AdjClose (pode vir como 'AdjClose' ou 'Adj Close' → já normalizado)
    if "AdjClose" not in df.columns and "Close" in df.columns:
        logger.warning("%s — coluna AdjClose ausente; usando Close como fallback", cd_yf)
        df["AdjClose"] = df["Close"]

    return df


# ─── Service ─────────────────────────────────────────────────────────────────

class HistoricoService:
    """
    Gerencia a tabela FAT_ATIVO_PRECO.

    carregar_historico() — download incremental + batch INSERT OR IGNORE
    get_historico()      — leitura da série histórica de um ativo
    resumo()             — contagem de registros por ativo
    """

    def carregar_historico(
        self,
        dt_inicio: Optional[str] = None,
        dt_fim:    Optional[str] = None,
        ids_ativo: Optional[list[int]] = None,
    ) -> dict:
        """
        Carrega série histórica OHLCV para os ativos mapeados.

        Args:
            dt_inicio: data de início no formato 'YYYY-MM-DD'.
                       Se None, usa a última data em banco + 1 dia (incremental).
                       Se não houver dados no banco, usa '2020-01-01' como default.
            dt_fim:    data fim no formato 'YYYY-MM-DD'. Default: hoje.
            ids_ativo: lista de ID_ATIVO para filtrar. Se None, processa todos.

        Returns:
            Resumo: {"ok", "sem_dados", "erro", "total", "linhas_inseridas"}
        """
        from app.services.YFinanceConfig import configure_yfinance_for_corporate_proxy
        configure_yfinance_for_corporate_proxy()

        dt_fim_final = dt_fim or date.today().isoformat()
        ativos = _get_ativos_mapeados(ids_ativo)

        if not ativos:
            return {"ok": 0, "sem_dados": 0, "erro": 0, "total": 0, "linhas_inseridas": 0,
                    "msg": "Nenhum ativo com CD_YF mapeado"}

        ok = 0
        sem_dados = 0
        erros = 0
        total_linhas = 0

        for ativo in ativos:
            id_ativo = ativo["ID_ATIVO"]
            cd_yf    = ativo["CD_YF"]

            # ── Determina data de início incremental ─────────────────────────
            if dt_inicio:
                dt_inicio_final = dt_inicio
            else:
                ultima = _ultima_data_carregada(id_ativo)
                if ultima:
                    # D+1 da última data carregada
                    dt_inicio_final = (
                        date.fromisoformat(ultima) + timedelta(days=1)
                    ).isoformat()
                else:
                    dt_inicio_final = "2020-01-01"

            # Nenhuma data para buscar
            if dt_inicio_final > dt_fim_final:
                logger.info("[UP-TO-DATE] %s — já atualizado até %s", cd_yf, dt_fim_final)
                sem_dados += 1
                continue

            try:
                df = _download_historico(cd_yf, dt_inicio_final, dt_fim_final)

                if df.empty:
                    logger.warning("[SEM DADOS] %s no período %s → %s", cd_yf, dt_inicio_final, dt_fim_final)
                    sem_dados += 1
                    continue

                # ── Monta lista de tuplas para INSERT OR IGNORE ──────────────
                rows: list[tuple] = []
                for dt_idx, row in df.iterrows():
                    dt_ref = dt_idx.strftime("%Y-%m-%d")
                    rows.append((
                        id_ativo,
                        dt_ref,
                        _safe(row.get("Open")),
                        _safe(row.get("High")),
                        _safe(row.get("Low")),
                        _safe(row.get("Close")),
                        _safe(row.get("AdjClose")),
                        _safe(row.get("Volume")),
                    ))

                if rows:
                    inseridos = execute_many(
                        """
                        INSERT OR IGNORE INTO FAT_ATIVO_PRECO (
                            ID_ATIVO, DT_REFERENCIA,
                            VL_ABERTURA, VL_MAXIMA, VL_MINIMA,
                            VL_FECHAMENTO, VL_FECHAMENTO_AJ, VL_VOLUME
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )
                    total_linhas += inseridos
                    logger.info(
                        "[OK] %s — %d registros inseridos (%s → %s)",
                        cd_yf, inseridos, dt_inicio_final, dt_fim_final,
                    )

                ok += 1

            except Exception as exc:
                logger.error("[ERRO] %s: %s", cd_yf, exc)
                erros += 1

        logger.info(
            "Carga histórica concluída: %d OK | %d sem dados | %d erros | %d linhas",
            ok, sem_dados, erros, total_linhas,
        )
        return {
            "ok": ok,
            "sem_dados": sem_dados,
            "erro": erros,
            "total": len(ativos),
            "linhas_inseridas": total_linhas,
        }

    # ── Auto-fetch on demand ──────────────────────────────────────────────────

    def ensure_range(self, cd_ativo: str, dt_inicio: str, dt_fim: str) -> None:
        """
        Garante que o ativo tenha dados históricos cobrindo [dt_inicio, dt_fim].
        Se a menor data no banco for posterior a dt_inicio, baixa o que falta.
        """
        from app.services.YFinanceConfig import configure_yfinance_for_corporate_proxy
        configure_yfinance_for_corporate_proxy()

        # Descobre ID_ATIVO + CD_YF
        row = query_one(
            """
            SELECT da.ID_ATIVO, dam.CD_YF
            FROM DIM_ATIVO da
            JOIN DIM_ATIVO_MAPPING dam ON dam.Id_Ativo = da.ID_ATIVO
            WHERE da.CD_ATIVO = ? AND dam.CD_YF IS NOT NULL
            """,
            params=(cd_ativo,),
        )
        if not row:
            logger.warning("[ensure_range] %s — sem mapeamento CD_YF", cd_ativo)
            return

        id_ativo = row["ID_ATIVO"]
        cd_yf    = row["CD_YF"]

        # Verifica menor data que já temos
        menor = query_scalar(
            "SELECT MIN(DT_REFERENCIA) FROM FAT_ATIVO_PRECO WHERE ID_ATIVO = ?",
            params=(id_ativo,),
        )

        if menor and menor <= dt_inicio:
            # Já temos dados suficientes para o início do range
            return

        # Precisa baixar dados de dt_inicio até (menor - 1 dia) ou dt_fim
        fetch_end = menor if menor else dt_fim
        logger.info("[ensure_range] %s — baixando %s → %s", cd_yf, dt_inicio, fetch_end)

        try:
            df = _download_historico(cd_yf, dt_inicio, fetch_end)
            if df.empty:
                logger.warning("[ensure_range] %s — sem dados no período", cd_yf)
                return

            rows: list[tuple] = []
            for dt_idx, r in df.iterrows():
                dt_ref = dt_idx.strftime("%Y-%m-%d")
                rows.append((
                    id_ativo, dt_ref,
                    _safe(r.get("Open")), _safe(r.get("High")),
                    _safe(r.get("Low")),  _safe(r.get("Close")),
                    _safe(r.get("AdjClose")), _safe(r.get("Volume")),
                ))
            if rows:
                inseridos = execute_many(
                    """
                    INSERT OR IGNORE INTO FAT_ATIVO_PRECO (
                        ID_ATIVO, DT_REFERENCIA,
                        VL_ABERTURA, VL_MAXIMA, VL_MINIMA,
                        VL_FECHAMENTO, VL_FECHAMENTO_AJ, VL_VOLUME
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                logger.info("[ensure_range] %s — %d registros inseridos", cd_yf, inseridos)
        except Exception as exc:
            logger.error("[ensure_range] %s: %s", cd_yf, exc)

    def get_historico(
        self,
        cd_ativo: str,
        dt_inicio: Optional[str] = None,
        dt_fim:    Optional[str] = None,
    ) -> list[dict]:
        """
        Retorna série histórica de preços de um ativo.

        Args:
            cd_ativo:  código do ativo (ex: 'PETR4')
            dt_inicio: filtro de data início 'YYYY-MM-DD'. Default: sem limite.
            dt_fim:    filtro de data fim 'YYYY-MM-DD'.    Default: sem limite.
        """
        filtros = ["da.CD_ATIVO = ?"]
        params:  list = [cd_ativo]

        if dt_inicio:
            filtros.append("fap.DT_REFERENCIA >= ?")
            params.append(dt_inicio)
        if dt_fim:
            filtros.append("fap.DT_REFERENCIA <= ?")
            params.append(dt_fim)

        where = " AND ".join(filtros)

        df = query(f"""
            SELECT
                da.CD_ATIVO,
                fap.DT_REFERENCIA,
                fap.VL_ABERTURA,
                fap.VL_MAXIMA,
                fap.VL_MINIMA,
                fap.VL_FECHAMENTO,
                fap.VL_FECHAMENTO_AJ,
                fap.VL_VOLUME,
                fap.CD_MOEDA,
                fap.DT_CARGA
            FROM FAT_ATIVO_PRECO fap
            JOIN DIM_ATIVO da ON da.ID_ATIVO = fap.ID_ATIVO
            WHERE {where}
            ORDER BY fap.DT_REFERENCIA
        """, params=tuple(params))

        return df.to_dict("records")

    def resumo(self) -> list[dict]:
        """Retorna contagem de registros históricos por ativo."""
        df = query("""
            SELECT
                da.CD_ATIVO,
                dam.CD_YF,
                COUNT(*)          AS QT_REGISTROS,
                MIN(DT_REFERENCIA) AS DT_INICIO,
                MAX(DT_REFERENCIA) AS DT_FIM
            FROM FAT_ATIVO_PRECO fap
            JOIN DIM_ATIVO           da  ON da.ID_ATIVO  = fap.ID_ATIVO
            LEFT JOIN DIM_ATIVO_MAPPING dam ON dam.Id_Ativo = fap.ID_ATIVO
            GROUP BY fap.ID_ATIVO
            ORDER BY da.CD_ATIVO
        """)
        return df.to_dict("records")
