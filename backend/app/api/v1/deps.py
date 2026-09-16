"""Dependency injection providers for FastAPI endpoints."""

from __future__ import annotations

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
    return _replay_engine
