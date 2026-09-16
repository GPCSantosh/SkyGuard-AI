"""FastAPI Application Entry Point for SkyGuard AI."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import router as api_v1_router
from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger, setup_logging

settings = get_settings()
setup_logging(log_level=settings.log_level)
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    logger.info(
        "Initializing %s (v%s) in [%s] mode",
        settings.system.project_name,
        settings.system.version,
        settings.env,
    )
    logger.info(
        "Observation Cadence: %ds (5-min default)",
        settings.observation_interval_seconds
    )
    yield
    logger.info("Shutting down SkyGuard AI backend service.")


app = FastAPI(
    title="SkyGuard AI — Meteorological Data Quality & Anomaly Detection API",
    description="REST API for Automatic Weather Station telemetry, quality control, and sensor health.",
    version=settings.system.version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Router
app.include_router(api_v1_router, prefix=settings.api_prefix)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint providing service metadata."""
    return {
        "service": settings.system.project_name,
        "version": settings.system.version,
        "status": "online",
        "docs_url": "/docs",
        "api_v1": settings.api_prefix,
    }
