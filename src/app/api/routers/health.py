import time
import logging
from fastapi import APIRouter
from app.api.models.common import APIResponse

logger = logging.getLogger("app.api.health")
_start_time = time.time()

router = APIRouter(tags=["System"])


@router.get("/", response_model=APIResponse)
async def root():
    return APIResponse(data={"app": "Fundinho API", "docs": "/docs", "health": "/health"})


@router.get("/health", response_model=APIResponse)
async def health_check():
    return APIResponse(data={
        "status": "healthy",
        "uptime_seconds": round(time.time() - _start_time, 1),
    })
