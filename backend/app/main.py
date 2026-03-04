"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import execute, health
from app.services.queue import execution_queue
from app.services.sandbox import sandbox_manager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("🚀 Starting %s v%s", settings.app_name, settings.app_version)

    # Connect to Redis (with in-memory fallback)
    await execution_queue.connect()

    # Initialize Docker (with local subprocess fallback)
    sandbox_manager._init_docker()

    if sandbox_manager._docker_available:
        if sandbox_manager.ensure_sandbox_image():
            logger.info("✅ Sandbox image '%s' is available", settings.sandbox_image)
        else:
            logger.warning("⚠️  Sandbox image not found — build it with: docker build -t %s sandbox/", settings.sandbox_image)

    yield

    # Shutdown
    logger.info("Shutting down...")
    sandbox_manager.cleanup()
    sandbox_manager.close()
    await execution_queue.disconnect()
    logger.info("👋 Goodbye!")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Secure code execution platform for AI agents. "
        "Execute arbitrary code in isolated Docker sandbox containers."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(execute.router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
