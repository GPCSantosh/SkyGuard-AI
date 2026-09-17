"""Unit tests for RealTimeProcessingEngine, ML Model Fallback, and Latency Profiling."""

from datetime import datetime, timezone
import pytest

from backend.app.core.database import DatabaseRepository
from backend.app.core.engine import RealTimeProcessingEngine
from backend.app.db.session import DatabaseSessionManager
from backend.app.models.observation import ObservationSource, QualityStatus, WeatherObservation
from backend.app.models.processing import ProcessingStatus
from ml.spatial.topology import SpatialNetworkTopology, StationNode


@pytest.fixture
def test_engine():
    topo = SpatialNetworkTopology()
    topo.add_station(StationNode(station_id="STN_001", name="Station 1", latitude=28.6, longitude=77.2, elevation_m=200.0))
    topo.add_station(StationNode(station_id="STN_002", name="Station 2", latitude=28.58, longitude=77.23, elevation_m=205.0))
    session_manager = DatabaseSessionManager("sqlite:///:memory:")
    repo = DatabaseRepository(topology=topo, session_manager=session_manager)
    return RealTimeProcessingEngine(repository=repo)


def test_process_single_nominal_observation(test_engine):
    obs = WeatherObservation(
        station_id="STN_001",
        timestamp=datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc),
        latitude=28.6,
        longitude=77.2,
        temperature=25.0,
        humidity=50.0,
        pressure=1013.25,
        source=ObservationSource.SIMULATOR,
        data_quality_status=QualityStatus.VALID,
    )

    res = test_engine.process_observation(obs)
    assert res.status == ProcessingStatus.PROCESSED
    assert res.hybrid_decision is not None
    assert res.hybrid_decision.decision.value == "NORMAL"
    assert res.features is not None
    assert "temperature_c" in res.features
    assert res.latency.total_pipeline_latency_ms > 0.0
    assert res.latency.feature_latency_ms >= 0.0
    assert res.sensor_health is not None


def test_duplicate_observation_skipping(test_engine):
    obs = WeatherObservation(
        station_id="STN_001",
        timestamp=datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc),
        latitude=28.6,
        longitude=77.2,
        temperature=25.0,
        humidity=50.0,
        pressure=1013.25,
    )

    res1 = test_engine.process_observation(obs)
    assert res1.status == ProcessingStatus.PROCESSED

    # Second arrival of exact same observation
    res2 = test_engine.process_observation(obs)
    assert res2.status == ProcessingStatus.DUPLICATE_SKIPPED


def test_resilient_ml_model_failure_fallback(test_engine):
    # Simulate a failing/corrupted model object
    class FaultyModel:
        model_id = "faulty_model"
        calibrated_threshold = 0.5
        def score_samples(self, df):
            raise RuntimeError("Simulated ML inference GPU memory crash")

    test_engine.ml_model = FaultyModel()

    obs = WeatherObservation(
        station_id="STN_001",
        timestamp=datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc),
        latitude=28.6,
        longitude=77.2,
        temperature=25.0,
        humidity=50.0,
        pressure=1013.25,
    )

    # Engine must not crash, should catch error, flag ml_model_failed, and produce a valid result
    res = test_engine.process_observation(obs)
    assert res.status == ProcessingStatus.PROCESSED
    assert res.ml_model_failed is True
    assert res.hybrid_decision is not None
    assert res.hybrid_decision.decision.value == "NORMAL"


def test_anomaly_event_generation_and_id(test_engine):
    # 1. Establish normal baseline at STN_001 and neighbor STN_002
    obs_base_1 = WeatherObservation(
        station_id="STN_001",
        timestamp=datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc),
        latitude=28.6,
        longitude=77.2,
        temperature=25.0,
        humidity=50.0,
        pressure=1013.25,
    )
    test_engine.process_observation(obs_base_1)

    obs_n = WeatherObservation(
        station_id="STN_002",
        timestamp=datetime(2026, 9, 17, 12, 5, 0, tzinfo=timezone.utc),
        latitude=28.58,
        longitude=77.23,
        temperature=25.0,
        humidity=50.0,
        pressure=1013.25,
    )
    test_engine.process_observation(obs_n)

    # 2. Target station experiences an extreme +33°C jump in 5 minutes
    obs_target = WeatherObservation(
        station_id="STN_001",
        timestamp=datetime(2026, 9, 17, 12, 5, 0, tzinfo=timezone.utc),
        latitude=28.6,
        longitude=77.2,
        temperature=58.0,
        humidity=10.0,
        pressure=1013.25,
    )

    res = test_engine.process_observation(obs_target)
    assert res.event_id is not None
    assert res.event_id.startswith("ANOM-")
    assert res.hybrid_decision.decision.value in ("PROBABLE_SENSOR_ANOMALY", "PROBABLE_DATA_QUALITY_ISSUE", "UNCERTAIN")
    assert res.explanation is not None
    assert res.correction_recommendation is not None
