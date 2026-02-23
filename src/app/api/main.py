import time
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import date, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.config import get_settings
from app.api.routers import health, precos, ativos

logger = logging.getLogger("app.api")
_start_time = time.time()

LIVE_INTERVAL_S = 30 * 60  # 30 minutos


async def _scheduler_live():
    """Background loop: atualiza preços live a cada 30 minutos."""
    logger.info("⏱ Scheduler de preços live iniciado (intervalo: %ds)", LIVE_INTERVAL_S)
    while True:
        try:
            from app.services.precos.pricing_live_service import PricingLiveService
            result = await asyncio.get_event_loop().run_in_executor(
                None, PricingLiveService().atualizar_todos,
            )
            logger.info("⏱ Live update: %s", result)
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Fundinho API starting...")
    # Garante que as tabelas de preços existem antes dos primeiros requests
    from app.services.precos.db_setup import create_tables
    create_tables()

    # Inicia tarefas em background
    live_task = asyncio.create_task(_scheduler_live())
    backfill_task = asyncio.create_task(_backfill_historico())

    yield

    # Cleanup
    live_task.cancel()
    backfill_task.cancel()
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
