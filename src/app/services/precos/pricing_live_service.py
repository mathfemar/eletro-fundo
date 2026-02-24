"""
pricing_live_service.py — Atualiza e consulta preços ao vivo em FAT_PRICING_LIVE.

Fluxo:
    DIM_ATIVO + DIM_ATIVO_MAPPING (CD_YF)
        → yfinance.download() em batches (minimiza requests ao Yahoo Finance)
            → INSERT OR REPLACE em FAT_PRICING_LIVE (1 linha por ativo)
"""

import math
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from app.services.db_connection import query, execute_many

logger = logging.getLogger("app.services.precos.live")
TZ_BR = ZoneInfo("America/Sao_Paulo")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _safe(val, decimais: int = 2) -> float | None:
    """Converte NaN/None para None e arredonda para N casas decimais."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else round(f, decimais)
    except (TypeError, ValueError):
        return None


def _now_br() -> datetime:
    """Retorna data/hora atual no fuso de São Paulo."""
    return datetime.now(TZ_BR)


BATCH_SIZE = 50    # linhas por INSERT batch
DOWNLOAD_CHUNK = 200  # tickers por chamada yf.download()

_UPSERT_SQL = """
    INSERT OR REPLACE INTO FAT_PRICING_LIVE (
        ID_ATIVO, VL_PRECO_ATUAL, VL_PRECO_ABERTURA,
        VL_PRECO_MAX, VL_PRECO_MIN, VL_VOLUME_DIA,
        VL_VAR_DIA, VL_VAR_DIA_PCT, VL_PRECO_FECHAMENTO_ANT,
        DT_REFERENCIA, DT_HORA_CAPTURA, CD_FONTE
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'yfinance')
"""

_INSERT_HIST_SQL = """
    INSERT INTO FAT_PRICING_LIVE_HIST (
        ID_ATIVO, VL_PRECO_ATUAL, VL_PRECO_ABERTURA,
        VL_PRECO_MAX, VL_PRECO_MIN, VL_VOLUME_DIA,
        VL_VAR_DIA, VL_VAR_DIA_PCT, VL_PRECO_FECHAMENTO_ANT,
        DT_REFERENCIA, DT_HORA_CAPTURA, CD_FONTE
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'yfinance')
"""


def _get_ativos_mapeados() -> list[dict]:
    """Retorna todos os ativos com PRECO_ONLINE=1 e ticker YF disponível."""
    df = query("""
        SELECT
            da.ID_ATIVO,
            da.CD_ATIVO,
            dam.CD_YF
        FROM DIM_ATIVO da
        JOIN DIM_ATIVO_MAPPING dam ON dam.Id_Ativo = da.ID_ATIVO
        WHERE dam.CD_YF IS NOT NULL
          AND TRIM(dam.CD_YF) != ''
          AND da.PRECO_ONLINE = 1
    """)
    return df.to_dict("records")


def _normalize_sub(sub: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nomes de colunas e remove timezone do índice."""
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


def _fallback_fast_info(ativo: dict) -> dict | None:
    """Fallback por ticker quando yf.download falha para um ativo específico."""
    import yfinance as yf

    cd_yf = ativo["CD_YF"]
    try:
        fi = yf.Ticker(cd_yf).fast_info
        preco_atual = _safe(getattr(fi, "last_price", None))
        if preco_atual is None:
            return None

        prev_close = _safe(getattr(fi, "previous_close", None))
        var_dia = round(preco_atual - prev_close, 4) if prev_close else None
        var_dia_pct = round(var_dia / prev_close, 6) if (prev_close and var_dia is not None) else None

        now_br = _now_br()
        return {
            "id_ativo":    ativo["ID_ATIVO"],
            "preco_atual": preco_atual,
            "abertura":    _safe(getattr(fi, "open", None)),
            "max":         _safe(getattr(fi, "day_high", None)),
            "min":         _safe(getattr(fi, "day_low", None)),
            "volume":      _safe(getattr(fi, "last_volume", None)),
            "var_dia":     var_dia,
            "var_dia_pct": var_dia_pct,
            "prev_close":  prev_close,
            "dt_ref":      now_br.date().isoformat(),
            "dt_captura":  now_br.strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as exc:
        logger.warning("[FALLBACK FAST_INFO] %s falhou: %s", cd_yf, exc)
        return None


def _fetch_batch_live(ativos: list[dict]) -> list[dict]:
    """
    Busca preços ao vivo para múltiplos tickers em uma única chamada yf.download().
    Usa period='2d' para obter também o fechamento anterior (var_dia).
    Retorna lista de dicts prontos para INSERT.
    """
    import yfinance as yf

    if not ativos:
        return []

    cd_yf_map = {a["CD_YF"]: a for a in ativos}
    cd_yf_list = list(cd_yf_map.keys())
    now_br = _now_br()
    dt_captura = now_br.strftime("%Y-%m-%d %H:%M:%S")
    dt_ref_captura = now_br.date().isoformat()

    try:
        df = yf.download(
            tickers=cd_yf_list,
            period="2d",
            interval="1d",
            auto_adjust=False,
            actions=False,
            group_by="ticker",
            progress=False,
            threads=False,
        )
    except Exception as exc:
        logger.error("[BATCH LIVE] Erro no download: %s", exc)
        return []

    if df is None or df.empty:
        return []

    results = []
    single = len(cd_yf_list) == 1

    for cd_yf, ativo in cd_yf_map.items():
        try:
            if single:
                sub = _normalize_sub(df)
            else:
                sub = _extract_ticker_frame(df, cd_yf)
                if sub is None:
                    fb = _fallback_fast_info(ativo)
                    if fb:
                        results.append(fb)
                    else:
                        logger.warning("[BATCH LIVE] %s — não encontrado no resultado", cd_yf)
                    continue

            sub = sub.dropna(subset=["Close"])
            if sub.empty:
                fb = _fallback_fast_info(ativo)
                if fb:
                    results.append(fb)
                else:
                    logger.warning("[BATCH LIVE] %s — sem dados Close", cd_yf)
                continue

            last = sub.iloc[-1]
            prev = sub.iloc[-2] if len(sub) >= 2 else None

            preco_atual = _safe(last.get("Close"))
            if preco_atual is None:
                continue

            prev_close = _safe(prev.get("Close")) if prev is not None else None
            abertura   = _safe(last.get("Open"))
            max_       = _safe(last.get("High"))
            min_       = _safe(last.get("Low"))
            volume     = _safe(last.get("Volume"))

            var_dia     = round(preco_atual - prev_close, 4) if prev_close else None
            var_dia_pct = round(var_dia / prev_close, 6) if (prev_close and var_dia is not None) else None

            results.append({
                "id_ativo":    ativo["ID_ATIVO"],
                "preco_atual": preco_atual,
                "abertura":    abertura,
                "max":         max_,
                "min":         min_,
                "volume":      volume,
                "var_dia":     var_dia,
                "var_dia_pct": var_dia_pct,
                "prev_close":  prev_close,
                "dt_ref":      dt_ref_captura,
                "dt_captura":  dt_captura,
            })

        except Exception as exc:
            logger.error("[BATCH LIVE] %s: %s", cd_yf, exc)

    return results


# ─── Service ─────────────────────────────────────────────────────────────────

class PricingLiveService:
    """
    Gerencia a tabela FAT_PRICING_LIVE.

    atualizar_todos() — captura em batch + UPSERT
    get_live()        — leitura do snapshot atual no banco
    """

    def atualizar_todos(self, chunk_size: int = DOWNLOAD_CHUNK) -> dict:
        """
        Busca preços ao vivo para todos os ativos mapeados e faz UPSERT.
        Usa yf.download() em batches para minimizar o número de requests ao Yahoo Finance.

        Args:
            chunk_size: quantidade de tickers por chamada yf.download().

        Returns:
            Resumo: {"ok", "erro", "total", "gravados", "dt_captura"}
        """
        from app.services.YFinanceConfig import configure_yfinance_for_corporate_proxy
        configure_yfinance_for_corporate_proxy()

        ativos = _get_ativos_mapeados()
        if not ativos:
            return {"ok": 0, "erro": 0, "total": 0, "msg": "Nenhum ativo com CD_YF mapeado"}

        ok = 0
        erros = 0
        all_rows: list[tuple] = []

        logger.info("Iniciando captura live para %d ativos em chunks de %d…", len(ativos), chunk_size)

        for i in range(0, len(ativos), chunk_size):
            chunk = ativos[i : i + chunk_size]
            logger.info("  chunk %d–%d…", i + 1, i + len(chunk))

            results = _fetch_batch_live(chunk)
            erros += len(chunk) - len(results)

            for r in results:
                all_rows.append((
                    r["id_ativo"],
                    r["preco_atual"],
                    r["abertura"],
                    r["max"],
                    r["min"],
                    r["volume"],
                    r["var_dia"],
                    r["var_dia_pct"],
                    r["prev_close"],
                    r["dt_ref"],
                    r["dt_captura"],
                ))
                ok += 1

            # Pausa entre chunks para não sobrecarregar a API
            if i + chunk_size < len(ativos):
                time.sleep(1.0)

        gravados = 0
        if all_rows:
            gravados = execute_many(_UPSERT_SQL, all_rows)
            execute_many(_INSERT_HIST_SQL, all_rows)

        dt_captura = _now_br().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("Live update concluído: %d OK | %d erros | %d gravados", ok, erros, gravados)
        return {"ok": ok, "erro": erros, "total": len(ativos), "gravados": gravados, "dt_captura": dt_captura}

    def get_live(self) -> list[dict]:
        """Retorna o snapshot atual de todos os ativos da FAT_PRICING_LIVE."""
        df = query("""
            SELECT
                da.CD_ATIVO,
                dam.CD_YF,
                fl.VL_PRECO_ATUAL,
                fl.VL_PRECO_ABERTURA,
                fl.VL_PRECO_MAX,
                fl.VL_PRECO_MIN,
                fl.VL_VOLUME_DIA,
                fl.VL_VAR_DIA,
                fl.VL_VAR_DIA_PCT,
                fl.VL_PRECO_FECHAMENTO_ANT,
                fl.DT_REFERENCIA,
                fl.DT_HORA_CAPTURA
            FROM FAT_PRICING_LIVE fl
            JOIN DIM_ATIVO           da  ON da.ID_ATIVO  = fl.ID_ATIVO
            LEFT JOIN DIM_ATIVO_MAPPING dam ON dam.Id_Ativo = fl.ID_ATIVO
            ORDER BY da.CD_ATIVO
        """)
        return df.to_dict("records")

    def get_live_ativo(self, cd_ativo: str) -> dict | None:
        """Retorna o preço live de um único ativo pelo CD_ATIVO."""
        df = query("""
            SELECT
                da.CD_ATIVO,
                dam.CD_YF,
                fl.VL_PRECO_ATUAL,
                fl.VL_VAR_DIA_PCT,
                fl.VL_PRECO_FECHAMENTO_ANT,
                fl.DT_REFERENCIA,
                fl.DT_HORA_CAPTURA
            FROM FAT_PRICING_LIVE fl
            JOIN DIM_ATIVO           da  ON da.ID_ATIVO  = fl.ID_ATIVO
            LEFT JOIN DIM_ATIVO_MAPPING dam ON dam.Id_Ativo = fl.ID_ATIVO
            WHERE da.CD_ATIVO = ?
        """, params=(cd_ativo,))
        records = df.to_dict("records")
        return records[0] if records else None

    def get_live_serie_ativo(self, cd_ativo: str, horas: int = 24) -> list[dict]:
        """Retorna série intradiária de snapshots live de um ativo nas últimas N horas."""
        horas = max(1, min(horas, 168))
        df = query("""
            SELECT
                da.CD_ATIVO,
                dam.CD_YF,
                h.VL_PRECO_ATUAL,
                h.VL_PRECO_ABERTURA,
                h.VL_PRECO_MAX,
                h.VL_PRECO_MIN,
                h.VL_VOLUME_DIA,
                h.VL_VAR_DIA,
                h.VL_VAR_DIA_PCT,
                h.VL_PRECO_FECHAMENTO_ANT,
                h.DT_REFERENCIA,
                h.DT_HORA_CAPTURA
            FROM FAT_PRICING_LIVE_HIST h
            JOIN DIM_ATIVO da ON da.ID_ATIVO = h.ID_ATIVO
            LEFT JOIN DIM_ATIVO_MAPPING dam ON dam.Id_Ativo = h.ID_ATIVO
            WHERE da.CD_ATIVO = ?
              AND h.DT_HORA_CAPTURA >= datetime('now', '-3 hours', ?)
            ORDER BY h.DT_HORA_CAPTURA ASC
        """, params=(cd_ativo, f"-{horas} hours"))
        return df.to_dict("records")
