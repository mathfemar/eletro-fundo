import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.config import get_settings
from app.api.routers import health, precos

logger = logging.getLogger("app.api")
_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Fundinho API starting...")
    # Garante que as tabelas de preços existem antes dos primeiros requests
    from app.services.precos.db_setup import create_tables
    create_tables()
    yield
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
