"""Dependency injection providers for FastAPI endpoints."""

from __future__ import annotations

import math
from typing import Optional
from backend.app.core.database import DatabaseRepository
from backend.app.core.engine import RealTimeProcessingEngine
from backend.app.core.replay import StreamReplayEngine
from ml.spatial.topology import SpatialNetworkTopology, StationNode


# Global singleton instances for local backend execution
_repository: Optional[DatabaseRepository] = None
_engine: Optional[RealTimeProcessingEngine] = None
_replay_engine: Optional[StreamReplayEngine] = None


def get_default_topology() -> SpatialNetworkTopology:
    """Initialize standard default spatial topology with baseline AWS stations."""
    topo = SpatialNetworkTopology()
    # Add representative AWS stations across India
    default_stations = [
        ("42182099999", "NEW DELHI / SAFDARJUNG", 28.585, 77.206, 216.0, "DELHI"),
        ("42181099999", "DELHI / PALAM", 28.567, 77.117, 237.0, "DELHI"),
        ("42184099999", "DELHI / LODHI ROAD", 28.583, 77.217, 211.0, "DELHI"),
        ("42139099999", "GURGAON AWS", 28.459, 77.026, 220.0, "HARYANA"),
        ("42187099999", "NOIDA AWS", 28.535, 77.391, 200.0, "UTTAR PRADESH"),
        ("42165099999", "MEERUT AWS", 28.984, 77.706, 222.0, "UTTAR PRADESH"),
        ("42111099999", "ROHTAK AWS", 28.895, 76.606, 220.0, "HARYANA"),
        ("42314099999", "ALWAR AWS", 27.553, 76.634, 270.0, "RAJASTHAN"),
    ]
    for s_id, name, lat, lon, elev, state in default_stations:
        topo.add_station(StationNode(
            station_id=s_id,
            name=name,
            latitude=lat,
            longitude=lon,
            elevation_m=elev,
            state=state,
        ))
    return topo


def get_repository() -> DatabaseRepository:
    """Get or create singleton DatabaseRepository."""
    global _repository
    if _repository is None:
        topo = get_default_topology()
        _repository = DatabaseRepository(topology=topo)
    return _repository


def get_engine() -> RealTimeProcessingEngine:
    """Get or create singleton RealTimeProcessingEngine."""
    global _engine
    if _engine is None:
        repo = get_repository()
        _engine = RealTimeProcessingEngine(repository=repo)
    return _engine


def get_replay_engine() -> StreamReplayEngine:
    """Get or create singleton StreamReplayEngine."""
    global _replay_engine
    if _replay_engine is None:
        _replay_engine = StreamReplayEngine()
        # Seed replay engine with multi-station chronological observations
        import pandas as pd
        topo = get_default_topology()
        records = []
        base_time = pd.Timestamp("2026-09-17 00:00:00", tz="UTC")
        for step in range(30):
            t = base_time + pd.Timedelta(minutes=5 * step)
            for idx, (s_id, node) in enumerate(topo.stations.items()):
                # Baseline smooth diurnal cycle
                t_val = 25.0 + 5.0 * math.sin(step / 6.0) + (idx * 0.4)
                h_val = 60.0 - 10.0 * math.sin(step / 6.0) - (idx * 0.2)
                p_val = 1013.25 - (node.elevation_m / 8.0)
                records.append({
                    "station_id": s_id,
                    "timestamp": t.isoformat(),
                    "latitude": node.latitude,
                    "longitude": node.longitude,
                    "elevation": node.elevation_m,
                    "temperature_c": t_val,
                    "relative_humidity_pct": h_val,
                    "sea_level_pressure_hpa": p_val,
                })
        df = pd.DataFrame(records)
        _replay_engine.load_from_dataframe(df)

        # Inject a couple of realistic anomalies for demonstration
        if records:
            _replay_engine.register_injected_anomaly(
                station_id="42182099999",
                timestamp=(base_time + pd.Timedelta(minutes=15)).isoformat(),
                anomaly_type="SPIKE",
                corrupted_values={"temperature": 52.0},
            )
            _replay_engine.register_injected_anomaly(
                station_id="42181099999",
                timestamp=(base_time + pd.Timedelta(minutes=25)).isoformat(),
                anomaly_type="FROZEN_SENSOR",
                corrupted_values={"humidity": 5.0},
            )
    return _replay_engine
