"""
pricing_live_service.py — Atualiza e consulta preços ao vivo em FAT_PRICING_LIVE.

Fluxo:
    DIM_ATIVO + DIM_ATIVO_MAPPING (CD_YF)
        → yfinance Ticker.fast_info (captura paralela via ThreadPoolExecutor)
            → INSERT OR REPLACE em FAT_PRICING_LIVE (1 linha por ativo)
"""

import math
import logging
import time
from datetime import datetime, date, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError

FUTURE_TIMEOUT_S = 15   # segundos máximos por ticker antes de desistir

from app.services.db_connection import query, execute_many

logger = logging.getLogger("app.services.precos.live")


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


BATCH_SIZE = 50   # linhas por INSERT batch

_UPSERT_SQL = """
    INSERT OR REPLACE INTO FAT_PRICING_LIVE (
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


def _fetch_fast_info(ativo: dict) -> dict | None:
    """
    Busca fast_info de um único ticker via yfinance.
    Retorna dict com os dados prontos para INSERT, ou None em caso de erro.
    """
    # Import lazy para evitar circular e garantir que configure_yfinance
    # já foi chamado antes desta function ser despachada pela thread.
    import yfinance as yf

    cd_yf = ativo["CD_YF"]
    try:
        ticker = yf.Ticker(cd_yf)
        # Força timeout via session do requests caso curl_cffi não respeite
        fi = ticker.fast_info
        # Acessa last_price explicitamente para forçar a requisição agora
        _ = fi.last_price

        preco_atual = _safe(fi.last_price)
        if preco_atual is None:
            logger.warning("[SKIP] %s — last_price indisponível", cd_yf)
            return None

        prev_close = _safe(fi.previous_close) or _safe(
            getattr(fi, "regular_market_previous_close", None)
        )
        var_dia = (preco_atual - prev_close) if prev_close else None
        var_dia_pct = (var_dia / prev_close) if (prev_close and var_dia is not None) else None

        dt_ref = date.today().isoformat()
        dt_captura = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        return {
            "id_ativo":      ativo["ID_ATIVO"],
            "preco_atual":   preco_atual,
            "abertura":      _safe(getattr(fi, "open", None)),
            "max":           _safe(getattr(fi, "day_high", None)),
            "min":           _safe(getattr(fi, "day_low", None)),
            "volume":        _safe(getattr(fi, "last_volume", None)),
            "var_dia":       _safe(var_dia),
            "var_dia_pct":   _safe(var_dia_pct),
            "prev_close":    prev_close,
            "dt_ref":        dt_ref,
            "dt_captura":    dt_captura,
        }

    except Exception as exc:
        logger.error("[ERRO] %s: %s", cd_yf, exc)
        return None


# ─── Service ─────────────────────────────────────────────────────────────────

class PricingLiveService:
    """
    Gerencia a tabela FAT_PRICING_LIVE.

    atualizar_todos() — captura paralela + batch UPSERT
    get_live()        — leitura do snapshot atual no banco
    """

    def atualizar_todos(self, max_workers: int = 5, delay_s: float = 0.2) -> dict:
        """
        Busca preços ao vivo para todos os ativos mapeados e faz UPSERT.

        Args:
            max_workers: threads paralelas para chamadas ao Yahoo Finance.
            delay_s:     pausa entre capturas por thread (respeita rate limit).

        Returns:
            Resumo: {"ok", "erro", "total", "dt_captura"}
        """
        from app.services.YFinanceConfig import configure_yfinance_for_corporate_proxy
        configure_yfinance_for_corporate_proxy()

        ativos = _get_ativos_mapeados()
        if not ativos:
            return {"ok": 0, "erro": 0, "total": 0, "msg": "Nenhum ativo com CD_YF mapeado"}

        ok = 0
        erros = 0
        rows: list[tuple] = []
        total_inseridos = 0

        def _flush(batch: list[tuple]) -> None:
            """Persiste um lote no banco e limpa a lista."""
            nonlocal total_inseridos
            if batch:
                execute_many(_UPSERT_SQL, batch)
                total_inseridos += len(batch)
                logger.info("  ⤵ %d UPSERTs gravados (total acumulado: %d)", len(batch), total_inseridos)
                batch.clear()

        logger.info("Iniciando captura live para %d ativos (workers=%d)…", len(ativos), max_workers)

        try:
            # Captura paralela — cada thread busca um ativo
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {pool.submit(_fetch_fast_info, a): a for a in ativos}
                for future in as_completed(futures):
                    ativo_ref = futures[future]
                    try:
                        result = future.result(timeout=FUTURE_TIMEOUT_S)
                    except FutureTimeoutError:
                        logger.warning("[TIMEOUT] %s — excedeu %ds", ativo_ref.get("CD_YF"), FUTURE_TIMEOUT_S)
                        erros += 1
                        continue
                    except Exception as exc:
                        logger.error("[ERRO] %s — %s", ativo_ref.get("CD_YF"), exc)
                        erros += 1
                        continue

                    if result:
                        rows.append((
                            result["id_ativo"],
                            result["preco_atual"],
                            result["abertura"],
                            result["max"],
                            result["min"],
                            result["volume"],
                            result["var_dia"],
                            result["var_dia_pct"],
                            result["prev_close"],
                            result["dt_ref"],
                            result["dt_captura"],
                        ))
                        ok += 1
                        if len(rows) >= BATCH_SIZE:
                            _flush(rows)
                    else:
                        erros += 1
                    time.sleep(delay_s)
        except KeyboardInterrupt:
            logger.warning("⚠ Captura interrompida pelo usuário — salvando %d resultados parciais…", len(rows))
        finally:
            _flush(rows)  # garante que o tail sempre vai ao banco

        dt_captura = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        logger.info("Live update concluído: %d OK | %d erros | %d gravados", ok, erros, total_inseridos)
        return {"ok": ok, "erro": erros, "total": len(ativos), "gravados": total_inseridos, "dt_captura": dt_captura}

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
