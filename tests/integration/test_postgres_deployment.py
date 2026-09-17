"""Integration tests for production deployment lifecycle, connection pool behavior, and migration execution."""

import asyncio
from datetime import datetime, timezone
import pytest
from sqlalchemy import text

from backend.app.core.database import DatabaseRepository
from backend.app.db.migrations import init_db_schema
from backend.app.db.models import WeatherObservationModel
from backend.app.db.session import DatabaseSessionManager
from backend.app.ingestion.live_poller import LiveSourcePoller
from backend.app.models.observation import WeatherObservation
from ml.spatial.topology import SpatialNetworkTopology, StationNode


@pytest.fixture
def isolated_db_mgr(tmp_path):
    """Create an isolated session manager."""
    db_file = tmp_path / "prod_test.db"
    return DatabaseSessionManager(f"sqlite:///{db_file}")


def test_production_pool_and_session_lifecycle(isolated_db_mgr):
    """Verify session manager correctly executes queries, checks health, and cleans up connections."""
    init_db_schema(isolated_db_mgr.engine)
    
    with isolated_db_mgr.session() as session:
        result = session.execute(text("SELECT 1 AS num")).scalar()
        assert result == 1

    health = isolated_db_mgr.check_health()
    assert health["status"] == "healthy"
    assert health["dialect"] == "sqlite"
    assert health["connected"] is True
    assert "metrics" in health
    assert health["metrics"]["writes_total"] >= 1


def test_clean_schema_initialization_and_table_presence(isolated_db_mgr):
    """Verify schema initialization creates all 9 production tables."""
    init_db_schema(isolated_db_mgr.engine)
    
    inspector_tables = isolated_db_mgr.engine.dialect.get_table_names(isolated_db_mgr.engine.connect())
    expected_tables = [
        "stations",
        "observations",
        "raw_source_payloads",
        "anomaly_events",
        "anomaly_explanations",
        "source_health_transitions",
        "outage_episodes",
        "sensor_health_snapshots",
        "correction_recommendations",
    ]
    for table in expected_tables:
        assert table in inspector_tables, f"Expected table '{table}' not found in database schema"


@pytest.mark.anyio
async def test_poller_graceful_shutdown_lifecycle(isolated_db_mgr):
    """Verify LiveSourcePoller starts and stops gracefully without leaking background tasks."""
    from unittest.mock import AsyncMock, MagicMock
    from backend.app.connectors.weather_api import OpenMeteoLiveConnector
    from backend.app.core.engine import RealTimeProcessingEngine

    topo = SpatialNetworkTopology()
    topo.add_station(StationNode(station_id="TEST_001", name="Test Station", latitude=28.6, longitude=77.2, elevation_m=200.0))
    repo = DatabaseRepository(topology=topo, session_manager=isolated_db_mgr)
    engine = RealTimeProcessingEngine(repository=repo)
    connector = OpenMeteoLiveConnector()

    poller = LiveSourcePoller(
        connector=connector,
        engine=engine,
        repository=repo,
        topology=topo,
        poll_interval_seconds=1,
    )

    # Mock connector fetch to avoid external network calls during unit test
    connector.fetch_latest_observation = AsyncMock(return_value=WeatherObservation(
        station_id="TEST_001",
        timestamp=datetime.now(timezone.utc),
        latitude=28.6,
        longitude=77.2,
        temperature=25.0,
        humidity=50.0,
        pressure=1013.25,
    ))

    # Start polling
    poller_task = await poller.start_polling()
    assert poller.is_polling is True
    assert poller._polling_task is not None

    # Let it run briefly
    await asyncio.sleep(0.05)

    # Stop polling gracefully
    await poller.stop_polling()
    assert poller.is_polling is False
    assert poller._polling_task is None

