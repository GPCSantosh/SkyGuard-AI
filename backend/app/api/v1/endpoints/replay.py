"""Stream replay simulation control endpoints."""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.v1.deps import get_engine, get_replay_engine
from backend.app.core.engine import RealTimeProcessingEngine
from backend.app.core.replay import StreamReplayEngine

router = APIRouter(prefix="/replay", tags=["Replay Simulator"])


@router.get("/status")
async def get_replay_status(
    replay: StreamReplayEngine = Depends(get_replay_engine),
) -> Dict[str, Any]:
    """Get current status of the stream replay simulator."""
    return {
        "is_running": replay.is_running,
        "total_queued_observations": len(replay.observations),
        "emitted_count": replay.emitted_count,
        "speed_multiplier": replay.speed_multiplier,
        "registered_injected_anomalies_count": len(replay.injected_anomalies),
    }


@router.post("/step")
async def step_replay_simulation(
    count: int = 1,
    replay: StreamReplayEngine = Depends(get_replay_engine),
    engine: RealTimeProcessingEngine = Depends(get_engine),
) -> Dict[str, Any]:
    """Step the replay simulation forward by N observations."""
    if not replay.observations:
        raise HTTPException(status_code=400, detail="No historical observations loaded in replay engine.")

    results = replay.run_synchronous_simulation(engine=engine, max_steps=count)
    return {
        "steps_executed": len(results),
        "total_emitted": replay.emitted_count,
        "results_summary": [
            {
                "station_id": r.observation.station_id,
                "timestamp": r.observation.timestamp.isoformat(),
                "status": r.status.value,
                "decision": r.hybrid_decision.decision.value if r.hybrid_decision else None,
                "event_id": r.event_id,
            }
            for r in results
        ],
    }
