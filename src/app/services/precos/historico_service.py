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

DOWNLOAD_CHUNK = 100  # tickers por chamada yf.download()


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
                """
                SELECT MAX(DT_REFERENCIA)
                FROM FAT_ATIVO_PRECO
                WHERE ID_ATIVO = ?
                    AND (
                        VL_ABERTURA IS NOT NULL OR
                        VL_MAXIMA IS NOT NULL OR
                        VL_MINIMA IS NOT NULL OR
                        VL_FECHAMENTO IS NOT NULL OR
                        VL_FECHAMENTO_AJ IS NOT NULL
                    )
                """,
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


def _normalize_sub(sub: pd.DataFrame) -> pd.DataFrame:
    """Normaliza colunas e remove timezone do índice."""
    sub = sub.copy()
    sub.columns = [str(c).replace(" ", "") for c in sub.columns]
    if "AdjClose" not in sub.columns and "Close" in sub.columns:
        sub["AdjClose"] = sub["Close"]
    if sub.index.tz is not None:
        sub.index = sub.index.tz_convert(None)
    sub.index = sub.index.normalize()
    return sub.dropna(how="all")


def _extract_ticker_frame(df: pd.DataFrame, cd_yf: str) -> pd.DataFrame | None:
    """Extrai frame de um ticker aceitando MultiIndex [ticker, campo] ou [campo, ticker]."""
    if not isinstance(df.columns, pd.MultiIndex):
        return _normalize_sub(df)

    lvl0 = df.columns.get_level_values(0)
    lvl1 = df.columns.get_level_values(1)

    if cd_yf in lvl0:
        return _normalize_sub(df[cd_yf])

    if cd_yf in lvl1:
        swapped = df.swaplevel(0, 1, axis=1)
        return _normalize_sub(swapped[cd_yf])

    return None


def _download_historico_batch(cd_yf_list: list[str], dt_inicio: str, dt_fim: str) -> dict[str, pd.DataFrame]:
    """
    Baixa OHLCV histórico para múltiplos tickers em uma única chamada yf.download().
    Retorna dict {cd_yf: DataFrame} com colunas normalizadas.
    """
    import yfinance as yf

    if not cd_yf_list:
        return {}

    try:
        df = yf.download(
            tickers=cd_yf_list,
            start=dt_inicio,
            end=dt_fim,
            auto_adjust=False,
            actions=False,
            group_by="ticker",
            progress=False,
            threads=False,
        )
    except Exception as exc:
        logger.error("[BATCH HIST] Erro no download de %d tickers: %s", len(cd_yf_list), exc)
        return {}

    if df is None or df.empty:
        return {}

    result: dict[str, pd.DataFrame] = {}
    single = len(cd_yf_list) == 1

    if single:
        cd_yf = cd_yf_list[0]
        sub = _extract_ticker_frame(df, cd_yf)
        if sub is None:
            sub = _normalize_sub(df)
        if not sub.empty:
            result[cd_yf] = sub
    else:
        for cd_yf in cd_yf_list:
            try:
                sub = _extract_ticker_frame(df, cd_yf)
                if sub is None:
                    continue
                if not sub.empty:
                    result[cd_yf] = sub
            except Exception as exc:
                logger.warning("[BATCH HIST] Erro ao extrair %s: %s", cd_yf, exc)

    return result

def _download_historico(cd_yf: str, dt_inicio: str, dt_fim: str) -> pd.DataFrame:
    """Baixa OHLCV histórico de um único ticker (usado por ensure_range)."""
    result = _download_historico_batch([cd_yf], dt_inicio, dt_fim)
    return result.get(cd_yf, pd.DataFrame())

# ─── Service ─────────────────────────────────────────────────────────────────

class HistoricoService:
    """
    Gerencia a tabela FAT_ATIVO_PRECO.

    carregar_historico() — download em batch + batch INSERT OR IGNORE
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
        Usa yf.download() em batches de até DOWNLOAD_CHUNK tickers por chamada.

        Args:
            dt_inicio: data de início no formato 'YYYY-MM-DD'.
                       Se None, usa a última data em banco + 1 dia (incremental).
                       Se não houver dados no banco, usa '2020-01-01' como default.
            dt_fim:    data fim no formato 'YYYY-MM-DD'. Default: hoje.
            ids_ativo: lista de ID_ATIVO para filtrar. Se None, processa todos.

        Returns:
            Resumo: {"ok", "sem_dados", "erro", "total", "linhas_inseridas"}
        """
        import time
        from app.services.YFinanceConfig import configure_yfinance_for_corporate_proxy
        configure_yfinance_for_corporate_proxy()

        dt_fim_final = dt_fim or (date.today() + timedelta(days=1)).isoformat()
        ativos = _get_ativos_mapeados(ids_ativo)

        if not ativos:
            return {"ok": 0, "sem_dados": 0, "erro": 0, "total": 0, "linhas_inseridas": 0,
                    "msg": "Nenhum ativo com CD_YF mapeado"}

        # 1️⃣ Calcula dt_inicio efetivo por ativo e filtra os já atualizados
        pendentes: list[dict] = []
        sem_dados = 0

        for ativo in ativos:
            if dt_inicio:
                dt_inicio_final = dt_inicio
            else:
                ultima = _ultima_data_carregada(ativo["ID_ATIVO"])
                if ultima:
                    dt_inicio_final = (date.fromisoformat(ultima) + timedelta(days=1)).isoformat()
                else:
                    dt_inicio_final = "2020-01-01"

            if dt_inicio_final > dt_fim_final:
                logger.debug("[UP-TO-DATE] %s — já atualizado até %s", ativo["CD_YF"], dt_fim_final)
                sem_dados += 1
                continue

            pendentes.append({**ativo, "_dt_inicio": dt_inicio_final})

        ok = 0
        erros = 0
        total_linhas = 0

        # 2️⃣ Download em batches — agrupa por dt_inicio mínimo do chunk
        for i in range(0, len(pendentes), DOWNLOAD_CHUNK):
            chunk = pendentes[i : i + DOWNLOAD_CHUNK]
            cd_yf_list = [a["CD_YF"] for a in chunk]
            dt_chunk_inicio = min(a["_dt_inicio"] for a in chunk)

            logger.info(
                "[BATCH HIST] chunk %d–%d | %d tickers | %s → %s",
                i + 1, i + len(chunk), len(chunk), dt_chunk_inicio, dt_fim_final,
            )

            batch_result = _download_historico_batch(cd_yf_list, dt_chunk_inicio, dt_fim_final)

            for ativo in chunk:
                cd_yf = ativo["CD_YF"]
                id_ativo = ativo["ID_ATIVO"]
                dt_ativo_inicio = ativo["_dt_inicio"]

                df_ativo = batch_result.get(cd_yf)
                if df_ativo is None or df_ativo.empty:
                    logger.warning("[SEM DADOS] %s no período %s → %s", cd_yf, dt_chunk_inicio, dt_fim_final)
                    erros += 1
                    continue

                # Filtra apenas datas a partir do dt_inicio específico deste ativo
                df_ativo = df_ativo[df_ativo.index >= pd.Timestamp(dt_ativo_inicio)]
                if df_ativo.empty:
                    sem_dados += 1
                    continue

                rows: list[tuple] = []
                for dt_idx, row in df_ativo.iterrows():
                    dt_ref = dt_idx.strftime("%Y-%m-%d")
                    rows.append((
                        id_ativo, dt_ref,
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
                        INSERT INTO FAT_ATIVO_PRECO (
                            ID_ATIVO, DT_REFERENCIA,
                            VL_ABERTURA, VL_MAXIMA, VL_MINIMA,
                            VL_FECHAMENTO, VL_FECHAMENTO_AJ, VL_VOLUME,
                            DT_CARGA
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '-3 hours'))
                        ON CONFLICT(ID_ATIVO, DT_REFERENCIA) DO UPDATE SET
                            VL_ABERTURA = excluded.VL_ABERTURA,
                            VL_MAXIMA = excluded.VL_MAXIMA,
                            VL_MINIMA = excluded.VL_MINIMA,
                            VL_FECHAMENTO = excluded.VL_FECHAMENTO,
                            VL_FECHAMENTO_AJ = excluded.VL_FECHAMENTO_AJ,
                            VL_VOLUME = excluded.VL_VOLUME,
                            DT_CARGA = datetime('now', '-3 hours')
                        """,
                        rows,
                    )
                    total_linhas += inseridos
                    logger.info("[OK] %s — %d registros inseridos", cd_yf, inseridos)
                ok += 1

            # Pausa entre chunks
            if i + DOWNLOAD_CHUNK < len(pendentes):
                time.sleep(1.5)

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
                        """
                        SELECT MIN(DT_REFERENCIA)
                        FROM FAT_ATIVO_PRECO
                        WHERE ID_ATIVO = ?
                            AND (
                                VL_ABERTURA IS NOT NULL OR
                                VL_MAXIMA IS NOT NULL OR
                                VL_MINIMA IS NOT NULL OR
                                VL_FECHAMENTO IS NOT NULL OR
                                VL_FECHAMENTO_AJ IS NOT NULL
                            )
                        """,
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
                    INSERT INTO FAT_ATIVO_PRECO (
                        ID_ATIVO, DT_REFERENCIA,
                        VL_ABERTURA, VL_MAXIMA, VL_MINIMA,
                        VL_FECHAMENTO, VL_FECHAMENTO_AJ, VL_VOLUME,
                        DT_CARGA
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '-3 hours'))
                    ON CONFLICT(ID_ATIVO, DT_REFERENCIA) DO UPDATE SET
                        VL_ABERTURA = excluded.VL_ABERTURA,
                        VL_MAXIMA = excluded.VL_MAXIMA,
                        VL_MINIMA = excluded.VL_MINIMA,
                        VL_FECHAMENTO = excluded.VL_FECHAMENTO,
                        VL_FECHAMENTO_AJ = excluded.VL_FECHAMENTO_AJ,
                        VL_VOLUME = excluded.VL_VOLUME,
                        DT_CARGA = datetime('now', '-3 hours')
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
