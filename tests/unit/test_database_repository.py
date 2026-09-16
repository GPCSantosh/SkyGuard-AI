"""Unit tests for DatabaseRepository persistence, queries, and pagination."""

from datetime import datetime, timezone
import pytest

from backend.app.core.database import DatabaseRepository
from backend.app.models.observation import ObservationSource, QualityStatus, WeatherObservation
from backend.app.models.processing import AnomalyEventRecord
from ml.decision.schema import HybridDecisionType
from ml.spatial.topology import SpatialNetworkTopology, StationNode


@pytest.fixture
def repo():
    topo = SpatialNetworkTopology()
    topo.add_station(StationNode(station_id="STN_001", name="Station 1", latitude=28.6, longitude=77.2, elevation_m=200.0))
    return DatabaseRepository(topology=topo)


def test_observation_persistence_and_latest(repo):
    obs1 = WeatherObservation(
        station_id="STN_001",
        timestamp=datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc),
        latitude=28.6,
        longitude=77.2,
        temperature=25.0,
        humidity=50.0,
        pressure=1013.25,
    )
    obs2 = WeatherObservation(
        station_id="STN_001",
        timestamp=datetime(2026, 9, 17, 12, 5, 0, tzinfo=timezone.utc),
        latitude=28.6,
        longitude=77.2,
        temperature=26.0,
        humidity=52.0,
        pressure=1013.0,
    )

    is_new1 = repo.save_observation(obs1)
    is_new2 = repo.save_observation(obs2)
    assert is_new1 is True
    assert is_new2 is True

    # Check latest snapshot
    latest = repo.get_station_latest("STN_001")
    assert latest is not None
    assert latest.latest_temperature_c == 26.0
    assert latest.latest_humidity_pct == 52.0


def test_station_history_filtering_and_pagination(repo):
    for i in range(10):
        obs = WeatherObservation(
            station_id="STN_001",
            timestamp=datetime(2026, 9, 17, 12, i, 0, tzinfo=timezone.utc),
            latitude=28.6,
            longitude=77.2,
            temperature=20.0 + i,
            humidity=50.0,
            pressure=1013.25,
        )
        repo.save_observation(obs)

    # Paginate: limit 3, offset 2
    items, total = repo.get_station_history("STN_001", limit=3, offset=2)
    assert total == 10
    assert len(items) == 3
    assert items[0].temperature == 22.0
    assert items[-1].temperature == 24.0


def test_anomaly_event_persistence_and_filtering(repo):
    event1 = AnomalyEventRecord(
        event_id="ANOM-20260917-STN001-0001",
        station_id="STN_001",
        timestamp="2026-09-17T12:00:00Z",
        decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        severity="HIGH",
        explanation_summary="High temperature spike detected.",
    )
    event2 = AnomalyEventRecord(
        event_id="ANOM-20260917-STN001-0002",
        station_id="STN_001",
        timestamp="2026-09-17T12:30:00Z",
        decision=HybridDecisionType.UNCERTAIN,
        severity="MEDIUM",
        explanation_summary="Uncertain reading with sparse context.",
    )

    repo.save_anomaly_event(event1)
    repo.save_anomaly_event(event2)

    # Filter by severity HIGH
    anoms, total = repo.get_anomalies(severity="HIGH")
    assert total == 1
    assert anoms[0].event_id == "ANOM-20260917-STN001-0001"

    # Query single by ID
    single = repo.get_anomaly_by_id("ANOM-20260917-STN001-0002")
    assert single is not None
    assert single.decision == HybridDecisionType.UNCERTAIN
