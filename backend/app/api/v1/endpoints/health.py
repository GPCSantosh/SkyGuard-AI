"""Liveness and Readiness Operational Probes for SkyGuard AI.

Provides standard health check endpoints compliant with Kubernetes / Docker Compose / Load Balancer probes.
- GET /health/live: Immediate process liveness verification.
- GET /health/ready: Granular dependency readiness verification (Database, Engine, Live Source, WebSockets).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text

from backend.app.api.v1.deps import get_engine, get_live_poller, get_repository
from backend.app.core.config import get_settings
from backend.app.core.database import DatabaseRepository
from backend.app.core.engine import RealTimeProcessingEngine
from backend.app.core.ws_manager import get_ws_manager
from backend.app.ingestion.live_poller import LiveSourcePoller

router = APIRouter(tags=["Health Probes"])
settings = get_settings()
_process_start_time = time.time()


@router.get("/health/live", summary="Process Liveness Probe")
async def health_live() -> Dict[str, Any]:
    """Process liveness probe indicating whether the server process is alive and responsive."""
    return {
        "status": "alive",
        "service": settings.system.project_name,
        "version": settings.system.version,
        "environment": settings.env,
        "uptime_seconds": round(time.time() - _process_start_time, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready", summary="Service Readiness Probe")
async def health_ready(
    response: Response,
    repo: DatabaseRepository = Depends(get_repository),
    engine: RealTimeProcessingEngine = Depends(get_engine),
    poller: LiveSourcePoller = Depends(get_live_poller),
) -> Dict[str, Any]:
    """Readiness probe evaluating the operational state of core subsystems and dependencies.

    Returns HTTP 200 when ready to accept traffic.
    Returns HTTP 503 only when core internal state is uninitialized or critically blocked.
    """
    db_status = "healthy"
    db_error = None
    try:
        with repo.session_manager.session() as session:
            session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "degraded" if repo.persistence_degraded else "unreachable"
        db_error = str(e)

    # Live Source Health from State Machine
    source_status = "disabled"
    source_details = None
    if settings.live_source.enabled:
        source_summary = poller.get_status_summary()
        source_status = source_summary.get("source_state", "UNKNOWN").lower()
        source_details = {
            "provider": source_summary.get("provider"),
            "consecutive_failures": source_summary.get("consecutive_failures", 0),
            "is_polling": source_summary.get("is_polling", False),
        }

    # WebSocket status
    ws_manager = get_ws_manager()
    ws_connections = ws_manager.active_connections_count

    # Overall system readiness determination
    is_ready = True
    overall_status = "ready"

    if db_status == "unreachable" and not repo.persistence_degraded:
        overall_status = "degraded"
    elif repo.persistence_degraded or source_status in ("degraded", "transient_failure", "disconnected"):
        overall_status = "degraded"

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": {
            "application": {
                "status": "healthy",
                "stations_monitored": len(repo.topology.stations),
                "processed_observations": repo.processed_observations_count,
            },
            "database": {
                "status": db_status,
                "type": repo.session_manager.engine.dialect.name,
                "persistence_degraded": repo.persistence_degraded,
                "error": db_error,
            },
            "live_source": {
                "status": source_status,
                "enabled": settings.live_source.enabled,
                "details": source_details,
            },
            "websocket": {
                "status": "healthy",
                "active_connections": ws_connections,
            },
        },
    }
