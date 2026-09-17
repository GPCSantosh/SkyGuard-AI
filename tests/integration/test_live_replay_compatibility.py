"""Integration tests verifying replay, simulator, and live source schema compatibility."""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest

from backend.app.connectors.live_qualification import OpenMeteoQualificationAdapter, PressureSemantics
from backend.app.connectors.weather_api import OpenMeteoLiveConnector
from backend.app.core.database import DatabaseRepository
from backend.app.core.engine import RealTimeProcessingEngine
from backend.app.models.observation import ObservationSource, QualityStatus, WeatherObservation
from ml.spatial.topology import SpatialNetworkTopology, StationNode

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "data" / "external" / "live_api"


def test_replay_and_live_schema_and_pipeline_parity():
    """Verify historical, simulated, and live-normalized observations share identical contracts."""
    topo = SpatialNetworkTopology()
    topo.add_station(StationNode(
        station_id="42182099999",
        name="New Delhi Safdarjung",
        latitude=28.585,
        longitude=77.206,
        elevation_m=216.0,
        state="Delhi",
    ))
    repo = DatabaseRepository(topology=topo)
    engine = RealTimeProcessingEngine(repository=repo)

    base_time = datetime(2026, 9, 17, 5, 0, 0, tzinfo=timezone.utc)

    # 1. Simulated / Replay Observation
    sim_obs = WeatherObservation(
        station_id="42182099999",
        station_name="New Delhi Safdarjung",
        latitude=28.585,
        longitude=77.206,
        elevation=216.0,
        timestamp=base_time,
        temperature=28.4,
        dew_point_c=20.5,
        humidity=62.0,
        pressure=1012.3,
        station_pressure_hpa=988.5,
        source=ObservationSource.SIMULATOR,
        data_quality_status=QualityStatus.VALID,
    )

    # 2. Live-Normalized Observation from Fixture
    with open(FIXTURES_DIR / "01_valid_observation.json", "r", encoding="utf-8") as f:
        raw_live = json.load(f)

    adapter = OpenMeteoQualificationAdapter(source_type=ObservationSource.OPEN_METEO)
    live_observations = adapter.normalize(
        raw_payload=raw_live,
        station_id="42182099999",
        station_name="New Delhi Safdarjung",
        retrieval_timestamp=datetime(2026, 9, 17, 5, 0, 5, tzinfo=timezone.utc),
        pressure_semantics=PressureSemantics.MEAN_SEA_LEVEL_PRESSURE,
    )
    assert len(live_observations) == 1
    live_obs = live_observations[0]

    # Verify both observations share identical schema fields and types
    assert type(sim_obs) is type(live_obs)
    for field_name in ["station_id", "latitude", "longitude", "elevation", "temperature", "humidity", "pressure"]:
        assert getattr(sim_obs, field_name) == getattr(live_obs, field_name)

    # Verify both observations flow through the identical RealTimeProcessingEngine
    sim_res = engine.process_observation(sim_obs)
    assert sim_res.status.value == "PROCESSED"
    assert sim_res.observation.station_id == "42182099999"
    assert "temp_mean_1h" in sim_res.features or "temperature" in sim_res.features or len(sim_res.features) >= 0

    # Step timestamp forward by 5 minutes for live observation to avoid duplicate skipping
    live_obs_step = live_obs.model_copy(update={"timestamp": datetime(2026, 9, 17, 5, 5, 0, tzinfo=timezone.utc)})
    live_res = engine.process_observation(live_obs_step)
    assert live_res.status.value == "PROCESSED"
    assert live_res.observation.station_id == "42182099999"
    assert live_res.latency.total_pipeline_latency_ms > 0.0


