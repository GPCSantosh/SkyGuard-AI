"""Unit tests for DatabaseRepository persistence, queries, and pagination."""

from datetime import datetime, timezone
import pytest

from backend.app.core.database import DatabaseRepository
from backend.app.db.session import DatabaseSessionManager
from backend.app.models.observation import ObservationSource, QualityStatus, WeatherObservation
from backend.app.models.processing import AnomalyEventRecord
from ml.decision.schema import HybridDecisionType
from ml.spatial.topology import SpatialNetworkTopology, StationNode


@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "test_repo.db"
    session_mgr = DatabaseSessionManager(f"sqlite:///{db_file}")
    topo = SpatialNetworkTopology()
    topo.add_station(StationNode(station_id="STN_001", name="Station 1", latitude=28.6, longitude=77.2, elevation_m=200.0))
    return DatabaseRepository(topology=topo, session_manager=session_mgr)


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


def test_system_health_active_stations_matches_topology_not_observations(tmp_path):
    """Regression guard: active_monitored_stations must equal configured network stations,
    NOT the number of observation records in the store.

    Previously len(self.observations) was used, which grew to 100+ records
    while only 1 physical station was configured. That caused the dashboard to
    display '100 active stations' instead of the correct network size.
    """
    db_file = tmp_path / "test_health.db"
    session_mgr = DatabaseSessionManager(f"sqlite:///{db_file}")
    topo = SpatialNetworkTopology()
    topo.add_station(
        StationNode(station_id="GUARD_001", name="Guard Station 1", latitude=28.6, longitude=77.2, elevation_m=200.0)
    )
    topo.add_station(
        StationNode(station_id="GUARD_002", name="Guard Station 2", latitude=28.7, longitude=77.3, elevation_m=210.0)
    )
    repo = DatabaseRepository(topology=topo, session_manager=session_mgr)

    # Persist 50 observation records from a single station — simulating a busy data stream
    for i in range(50):
        obs = WeatherObservation(
            station_id="GUARD_001",
            timestamp=datetime(2026, 9, 17, 0, i % 60, i % 30, tzinfo=timezone.utc),
            latitude=28.6,
            longitude=77.2,
            temperature=25.0 + i * 0.1,
            humidity=50.0,
            pressure=1013.25,
        )
        repo.save_observation(obs)

    health = repo.get_system_health()

    # CRITICAL: active_monitored_stations must reflect topology size (2), not observation dict size (50)
    assert health.active_monitored_stations == 2, (
        f"active_monitored_stations ({health.active_monitored_stations}) must equal the number of "
        f"configured topology stations (2), not the observation record count "
        f"({health.total_observations_processed}). "
        "Prevents misleading 'N active stations' dashboard display."
    )
    assert health.total_observations_processed == 50, (
        "total_observations_processed should count individual observation records, not stations."
    )
    # The spatial topology count and active monitored count must always agree
    assert health.spatial_topology_stations_count == health.active_monitored_stations, (
        "spatial_topology_stations_count and active_monitored_stations must always agree."
    )

