from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes_assets import router as assets_router
from .api.routes_funds import router as funds_router
from .api.routes_pricing import router as pricing_router
from .bootstrap import init_database
from .config import settings
from .services.scheduler import schedule_jobs, scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    schedule_jobs()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(assets_router)
app.include_router(pricing_router)
app.include_router(funds_router)


@app.get('/health')
def healthcheck() -> dict:
    return {'status': 'ok'}
