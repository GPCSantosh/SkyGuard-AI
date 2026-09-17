"""Live Source Observability & Control Endpoints."""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.v1.deps import get_live_poller
from backend.app.ingestion.live_poller import LiveSourcePoller

router = APIRouter(prefix="/live", tags=["Live Source Operations"])


@router.get("/source-health")
async def get_live_source_health(
    poller: LiveSourcePoller = Depends(get_live_poller),
) -> Dict[str, Any]:
    """Get operational health, request metrics, and per-station freshness of the live upstream API."""
    return poller.get_status_summary()


@router.get("/status")
async def get_live_status(
    poller: LiveSourcePoller = Depends(get_live_poller),
) -> Dict[str, Any]:
    """Get high-level status indicator (LIVE | DEGRADED | STALE | DISCONNECTED)."""
    summary = poller.get_status_summary()
    return {
        "status": summary["status"],
        "provider": summary["provider"],
        "is_polling": summary["is_polling"],
        "stations_configured": summary["stations_configured"],
        "last_poll_cycle_start": summary["metrics"]["last_poll_cycle_start"],
    }


@router.post("/poll-now")
async def trigger_immediate_poll(
    poller: LiveSourcePoller = Depends(get_live_poller),
) -> Dict[str, Any]:
    """Trigger an immediate synchronous poll cycle across all configured stations."""
    results = await poller.poll_cycle_once()
    ingested = sum(1 for r in results if r is not None)
    return {
        "status": "success",
        "stations_polled": len(results),
        "observations_ingested": ingested,
        "poll_duration_ms": poller.metrics.get("last_poll_cycle_duration_ms"),
    }
