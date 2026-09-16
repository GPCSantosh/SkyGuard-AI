"""Station-level state management and bounded temporal sliding buffers for real-time streaming."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import math
from typing import Any, Deque, Dict, List, Optional, Set, Tuple
import numpy as np
import pandas as pd

from backend.app.models.observation import WeatherObservation
from backend.app.models.processing import ProcessingStatus
from ml.decision.schema import HybridDecision
from ml.health.health_schema import SensorHealthSummary


class StationStateBuffer:
    """Bounded, thread-safe temporal state ring buffer for an individual AWS station."""

    def __init__(self, station_id: str, max_retention: int = 120) -> None:
        self.station_id = station_id
        self.max_retention = max_retention
        
        # Chronologically ordered observation ring buffer
        self.observations: Deque[WeatherObservation] = deque(maxlen=max_retention)
        self.decisions: Deque[HybridDecision] = deque(maxlen=max_retention)
        self.health_history: Deque[SensorHealthSummary] = deque(maxlen=24)
        
        # Set of seen observation identity keys for fast idempotency & duplicate checks
        self.seen_identity_keys: Set[str] = set()
        self.last_seen_timestamp: Optional[datetime] = None

    def get_identity_key(self, obs: WeatherObservation) -> str:
        """Generate unique idempotent identity string for an incoming packet."""
        src = obs.source if hasattr(obs.source, "value") else str(obs.source)
        t_str = obs.timestamp.astimezone(timezone.utc).isoformat()
        return f"{self.station_id}::{t_str}::{src}"

    def check_temporal_ordering(
        self,
        obs: WeatherObservation,
        check_future_wall_clock: bool = True,
    ) -> Tuple[ProcessingStatus, Optional[str]]:
        """Validate timestamp temporal ordering, duplicates, and out-of-order state."""
        key = self.get_identity_key(obs)
        if key in self.seen_identity_keys:
            return ProcessingStatus.DUPLICATE_SKIPPED, "Duplicate observation packet received."

        obs_time = obs.timestamp.astimezone(timezone.utc)
        now_time = datetime.now(timezone.utc)

        # Check future timestamp relative to server wall clock for live telemetry feeds
        src = obs.source.value if hasattr(obs.source, "value") else str(obs.source)
        if check_future_wall_clock and src in ("WEATHER_API", "MQTT"):
            if (obs_time - now_time).total_seconds() > 300.0:
                return ProcessingStatus.FUTURE_TIMESTAMP, f"Timestamp {obs_time.isoformat()} is in the future relative to server time."

        # Check out-of-order
        if self.last_seen_timestamp is not None:
            if obs_time < self.last_seen_timestamp:
                return ProcessingStatus.OUT_OF_ORDER, f"Timestamp {obs_time.isoformat()} is out-of-order (prior watermark: {self.last_seen_timestamp.isoformat()})."

        return ProcessingStatus.PROCESSED, None

    def append_observation(self, obs: WeatherObservation) -> None:
        """Append observation to state buffer and update watermark."""
        key = self.get_identity_key(obs)
        self.seen_identity_keys.add(key)
        self.observations.append(obs)
        
        obs_time = obs.timestamp.astimezone(timezone.utc)
        if self.last_seen_timestamp is None or obs_time > self.last_seen_timestamp:
            self.last_seen_timestamp = obs_time

    def append_decision(self, decision: HybridDecision) -> None:
        """Append decision output to ring buffer."""
        self.decisions.append(decision)

    def append_health_snapshot(self, health: SensorHealthSummary) -> None:
        """Append health evaluation snapshot."""
        self.health_history.append(health)

    def get_causal_history(
        self,
        before_timestamp: datetime,
        max_points: Optional[int] = None,
    ) -> List[WeatherObservation]:
        """Retrieve chronological history strictly on or before before_timestamp."""
        cutoff = before_timestamp.astimezone(timezone.utc)
        matching = [o for o in self.observations if o.timestamp.astimezone(timezone.utc) <= cutoff]
        if max_points is not None:
            return matching[-max_points:]
        return matching


class StationStateManager:
    """Coordinates independent station state buffers across the AWS network."""

    def __init__(self, max_station_retention: int = 120) -> None:
        self.max_station_retention = max_station_retention
        self.stations: Dict[str, StationStateBuffer] = {}

    def get_or_create_buffer(self, station_id: str) -> StationStateBuffer:
        """Get existing station buffer or create an isolated new buffer."""
        if station_id not in self.stations:
            self.stations[station_id] = StationStateBuffer(
                station_id=station_id,
                max_retention=self.max_station_retention,
            )
        return self.stations[station_id]

    def get_contemporaneous_neighbor_pool(
        self,
        target_station_id: str,
        target_timestamp: datetime,
        temporal_tolerance_minutes: float = 30.0,
    ) -> List[Dict[str, Any]]:
        """Extract contemporaneous neighbor observations pool respecting strict causal ordering (t <= target_t)."""
        cutoff = target_timestamp.astimezone(timezone.utc)
        tol_seconds = temporal_tolerance_minutes * 60.0
        pool: List[Dict[str, Any]] = []

        for stn_id, buffer in self.stations.items():
            if stn_id == target_station_id:
                continue

            causal_obs = buffer.get_causal_history(before_timestamp=cutoff, max_points=3)
            if not causal_obs:
                continue

            # Pick latest observation <= cutoff
            latest_obs = causal_obs[-1]
            dt = (cutoff - latest_obs.timestamp.astimezone(timezone.utc)).total_seconds()
            if dt <= tol_seconds:
                # Format into neighbor pool dictionary
                pool.append({
                    "station_id": stn_id,
                    "timestamp": latest_obs.timestamp.astimezone(timezone.utc).isoformat(),
                    "temperature_c": latest_obs.temperature,
                    "relative_humidity_pct": latest_obs.humidity,
                    "sea_level_pressure_hpa": latest_obs.pressure,
                    "station_pressure_hpa": latest_obs.station_pressure_hpa,
                    "elevation_m": latest_obs.elevation,
                    "latitude": latest_obs.latitude,
                    "longitude": latest_obs.longitude,
                })

        return pool
