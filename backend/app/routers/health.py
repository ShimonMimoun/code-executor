"""Health check routes."""

from fastapi import APIRouter

from app.config import settings
from app.models import HealthResponse
from app.services.queue import execution_queue
from app.services.sandbox import sandbox_manager

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health():
    redis_ok = await execution_queue.is_healthy()
    docker_ok = sandbox_manager.is_healthy()

    return HealthResponse(
        status="healthy" if (redis_ok and docker_ok) else "degraded",
        version=settings.app_version,
        redis="connected" if redis_ok else "disconnected",
        docker="connected" if docker_ok else "disconnected",
    )


@router.get("/ready", summary="Readiness probe")
async def readiness():
    redis_ok = await execution_queue.is_healthy()
    docker_ok = sandbox_manager.is_healthy()

    if not redis_ok or not docker_ok:
        return {
            "ready": False,
            "redis": "connected" if redis_ok else "disconnected",
            "docker": "connected" if docker_ok else "disconnected",
        }
    return {"ready": True}
