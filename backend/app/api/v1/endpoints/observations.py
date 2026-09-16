"""Real-time observation ingestion and processing endpoints."""

from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, status

from backend.app.api.v1.deps import get_engine
from backend.app.core.engine import RealTimeProcessingEngine
from backend.app.models.observation import WeatherObservation
from backend.app.models.processing import ProcessingResult

router = APIRouter(prefix="/observations", tags=["Observations & Ingestion"])


@router.post("/process", response_model=ProcessingResult, status_code=status.HTTP_200_OK)
async def process_single_observation(
    observation: WeatherObservation,
    engine: RealTimeProcessingEngine = Depends(get_engine),
):
    """Ingest and process a single WeatherObservation through the full analytical intelligence pipeline."""
    return engine.process_observation(observation)


@router.post("/batch", response_model=List[ProcessingResult], status_code=status.HTTP_200_OK)
async def process_observation_batch(
    observations: List[WeatherObservation],
    engine: RealTimeProcessingEngine = Depends(get_engine),
):
    """Process a sequential batch of WeatherObservations."""
    results = []
    for obs in observations:
        res = engine.process_observation(obs)
        results.append(res)
    return results
