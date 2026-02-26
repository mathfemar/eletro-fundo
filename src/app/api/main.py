import time
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.config import get_settings
from app.api.routers import health, precos, ativos, simulador

logger = logging.getLogger("app.api")
_start_time = time.time()

LIVE_INTERVAL_S = 30 * 60  # 30 minutos
PNL_CLOSE_CHECK_INTERVAL_S = 5 * 60
TZ_BR = ZoneInfo("America/Sao_Paulo")


async def _scheduler_live():
    """Background loop: atualiza preços live a cada 30 minutos."""
    logger.info("⏱ Scheduler de preços live iniciado (intervalo: %ds)", LIVE_INTERVAL_S)
    while True:
        try:
            from app.services.precos.pricing_live_service import PricingLiveService
            result_precos = await asyncio.get_event_loop().run_in_executor(
                None, PricingLiveService().atualizar_todos,
            )

            from app.api.routers.simulador import (
                _list_active_fundo_ids,
                capture_pnl_live_fundo_sync,
                close_pnl_day_fundo_sync,
            )

            def _atualizar_fundos_sync() -> dict:
                itens = []
                today_iso = date.today().isoformat()
                for fid in _list_active_fundo_ids():
                    itens.append(capture_pnl_live_fundo_sync(fundo_id=fid, fonte="scheduler_yf"))
                    # Fecha dia provisoriamente e recomputa cota para manter retorno atualizado
                    try:
                        close_pnl_day_fundo_sync(
                            fundo_id=fid,
                            dt_referencia=today_iso,
                            allow_recompute=False,
                            update_cota=True,
                        )
                    except Exception as exc_close:
                        logger.warning("⏱ Falha no fechamento provisório do fundo %s: %s", fid, exc_close)
                return {"items": itens, "total": len(itens)}

            result_fundos = await asyncio.get_event_loop().run_in_executor(
                None,
                _atualizar_fundos_sync,
            )

            logger.info(
                "⏱ Live update concluído | preços=%s | fundos=%s",
                result_precos,
                {
                    "total": result_fundos.get("total", 0),
                    "ids": [item.get("ID_FUNDO") for item in result_fundos.get("items", [])],
                },
            )
        except asyncio.CancelledError:
            logger.info("⏱ Live scheduler cancelado")
            break
        except Exception as exc:
            logger.exception("⏱ Erro no scheduler live: %s", exc)
        await asyncio.sleep(LIVE_INTERVAL_S)


async def _backfill_historico():
    """Startup: garante 1 ano de histórico para ativos PRECO_ONLINE=1."""
    try:
        dt_inicio = (date.today() - timedelta(days=365)).isoformat()
        dt_fim = date.today().isoformat()
        logger.info("📊 Backfill histórico 1 ano: %s → %s", dt_inicio, dt_fim)

        from app.services.precos.historico_service import HistoricoService
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: HistoricoService().carregar_historico(
                dt_inicio=dt_inicio,
                dt_fim=dt_fim,
            ),
        )
        logger.info("📊 Backfill concluído: %s", result)
    except Exception as exc:
        logger.exception("📊 Erro no backfill histórico: %s", exc)


async def _catchup_pnl_fechamento():
    """Startup: reconcilia fechamentos de PnL de fundos em dias pendentes (horário Brasil)."""
    try:
        from app.api.routers.simulador import catchup_fechamento_all_fundos_sync

        logger.info("📈 Catch-up PnL fechamento (SP) iniciado")
        result = await asyncio.get_event_loop().run_in_executor(None, catchup_fechamento_all_fundos_sync)
        logger.info("📈 Catch-up PnL fechamento concluído: %s", result)
    except Exception as exc:
        logger.exception("📈 Erro no catch-up PnL fechamento: %s", exc)


async def _scheduler_pnl_fechamento():
    """Background loop: roda fechamento diário de PnL às 19h (America/Sao_Paulo)."""
    logger.info("⏱ Scheduler PnL fechamento iniciado (checagem: %ds)", PNL_CLOSE_CHECK_INTERVAL_S)
    ultimo_dia_executado: str | None = None

    while True:
        try:
            now_sp = datetime.now(TZ_BR)
            dt_ref = now_sp.date().isoformat()

            if now_sp.hour >= 19 and ultimo_dia_executado != dt_ref:
                from app.api.routers.simulador import close_pnl_day_all_fundos_sync

                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: close_pnl_day_all_fundos_sync(dt_ref),
                )
                logger.info("⏱ Fechamento PnL diário (SP) %s: %s", dt_ref, result)
                ultimo_dia_executado = dt_ref
        except asyncio.CancelledError:
            logger.info("⏱ Scheduler PnL fechamento cancelado")
            break
        except Exception as exc:
            logger.exception("⏱ Erro no scheduler PnL fechamento: %s", exc)

        await asyncio.sleep(PNL_CLOSE_CHECK_INTERVAL_S)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Fundinho API starting...")
    # Garante que as tabelas de preços existem antes dos primeiros requests
    from app.services.precos.db_setup import create_tables
    from app.services.simulador.db_setup import create_tables as create_sim_tables
    create_tables()
    create_sim_tables()

    # Inicia tarefas em background
    live_task = asyncio.create_task(_scheduler_live())
    backfill_task = asyncio.create_task(_backfill_historico())
    pnl_catchup_task = asyncio.create_task(_catchup_pnl_fechamento())
    pnl_close_task = asyncio.create_task(_scheduler_pnl_fechamento())

    yield

    # Cleanup
    live_task.cancel()
    backfill_task.cancel()
    pnl_catchup_task.cancel()
    pnl_close_task.cancel()
    logger.info("🛑 Fundinho API shutting down...")


settings = get_settings()

app = FastAPI(
    title="Fundinho API",
    description="REST API para análise de fundos de investimento via yfinance",
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(precos.router)
app.include_router(ativos.router)
app.include_router(simulador.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
