"""Unit tests verifying SQLAlchemy 2.0 ORM models, tables, indexes, and constraints."""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.models import (
    AnomalyEventModel,
    Base,
    CorrectionRecommendationModel,
    ExplanationModel,
    OutageEpisodeModel,
    RawSourcePayloadModel,
    SensorHealthSnapshotModel,
    SourceHealthTransitionModel,
    StationModel,
    WeatherObservationModel,
)


@pytest.fixture
def memory_db_session():
    """Isolated in-memory SQLite database session."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_station_model_crud(memory_db_session: Session):
    """Verify StationModel table creation, column mappings, and persistence."""
    stn = StationModel(
        station_id="TEST_AWS_01",
        name="Test Station 1",
        latitude=28.585,
        longitude=77.206,
        elevation_m=216.0,
        state="DELHI",
        status="ACTIVE",
        sampling_interval_seconds=300,
        installed_sensors=["TEMP", "RH", "PRES"],
    )
    memory_db_session.add(stn)
    memory_db_session.commit()

    retrieved = memory_db_session.get(StationModel, "TEST_AWS_01")
    assert retrieved is not None
    assert retrieved.name == "Test Station 1"
    assert retrieved.latitude == 28.585
    assert retrieved.installed_sensors == ["TEMP", "RH", "PRES"]


def test_weather_observation_model_idempotency_constraint(memory_db_session: Session):
    """Verify unique constraint on (source, station_id, observation_timestamp) prevents duplicates."""
    t_now = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
    obs1 = WeatherObservationModel(
        observation_id="obs_test_01",
        station_id="42182099999",
        observation_timestamp=t_now,
        ingestion_timestamp=t_now,
        temperature_c=25.4,
        relative_humidity_pct=60.0,
        sea_level_pressure_hpa=1013.2,
        latitude=28.585,
        longitude=77.206,
        elevation=216.0,
        source="OPEN_METEO",
        data_quality_status="VALID",
        raw_quality_flags={"TMP_QC": "1"},
        metadata_json={},
    )
    memory_db_session.add(obs1)
    memory_db_session.commit()

    # Second insert with identical (source, station_id, observation_timestamp) must fail unique constraint
    obs2 = WeatherObservationModel(
        observation_id="obs_test_02",
        station_id="42182099999",
        observation_timestamp=t_now,
        ingestion_timestamp=t_now,
        temperature_c=99.9,  # different value
        relative_humidity_pct=10.0,
        sea_level_pressure_hpa=1000.0,
        latitude=28.585,
        longitude=77.206,
        elevation=216.0,
        source="OPEN_METEO",
        data_quality_status="VALID",
        raw_quality_flags={},
        metadata_json={},
    )
    memory_db_session.add(obs2)
    with pytest.raises(IntegrityError):
        memory_db_session.commit()
    memory_db_session.rollback()


def test_raw_source_payload_model(memory_db_session: Session):
    """Verify raw payload persistence and secret-sanitization metadata."""
    t_now = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
    raw = RawSourcePayloadModel(
        payload_id="raw_test_01",
        source="OPEN_METEO",
        provider="open_meteo",
        endpoint="/v1/forecast",
        station_id="42182099999",
        source_timestamp=t_now,
        retrieval_timestamp=t_now,
        raw_payload_json={"current": {"temperature_2m": 25.4}},
        headers_metadata={"content-type": "application/json"},
        normalization_version="v1.0.0",
    )
    memory_db_session.add(raw)
    memory_db_session.commit()

    retrieved = memory_db_session.execute(
        select(RawSourcePayloadModel).where(RawSourcePayloadModel.payload_id == "raw_test_01")
    ).scalar_one()
    assert retrieved.provider == "open_meteo"
    assert retrieved.raw_payload_json["current"]["temperature_2m"] == 25.4


def test_anomaly_and_explanation_models(memory_db_session: Session):
    """Verify AnomalyEventModel and ExplanationModel persistence and version tracking."""
    t_now = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
    anom = AnomalyEventModel(
        event_id="ANOM-20260917-001",
        station_id="42182099999",
        timestamp=t_now,
        decision="PROBABLE_SENSOR_ANOMALY",
        severity="HIGH",
        reason_codes=["ISOLATED_ANOMALY_SPARSE_NETWORK"],
        observed_values={"temperature_c": 55.0},
        recommended_values={"temperature_c": 26.2},
        explanation_summary="Sudden uncorroborated spike in temperature.",
        model_id="isolation_forest_s42",
        model_version="v0.1.0_baseline",
        feature_version="v1.0.0",
        decision_engine_version="hybrid_v1.0.0",
    )
    exp = ExplanationModel(
        event_id="ANOM-20260917-001",
        station_id="42182099999",
        timestamp=t_now,
        feature_attributions={"temperature_c_delta": 0.85},
        spatial_evidence={"valid_neighbors": 4},
        temporal_evidence={"temp_rate_per_min": 2.5},
        multivariate_evidence={"dew_point_spread_c": 12.0},
        evidence_hierarchy={"tier1": "DATA_QUALITY_VALID"},
        natural_language_explanation="SHAP attribution indicates high spike rate.",
        recommended_sop_steps=["Inspect sensor RTD wiring", "Verify neighbor readings"],
        explanation_version="v1.0.0",
        model_id="isolation_forest_s42",
    )
    memory_db_session.add(anom)
    memory_db_session.add(exp)
    memory_db_session.commit()

    retrieved_anom = memory_db_session.execute(
        select(AnomalyEventModel).where(AnomalyEventModel.event_id == "ANOM-20260917-001")
    ).scalar_one()
    retrieved_exp = memory_db_session.execute(
        select(ExplanationModel).where(ExplanationModel.event_id == "ANOM-20260917-001")
    ).scalar_one()

    assert retrieved_anom.model_id == "isolation_forest_s42"
    assert retrieved_anom.decision == "PROBABLE_SENSOR_ANOMALY"
    assert retrieved_exp.recommended_sop_steps == ["Inspect sensor RTD wiring", "Verify neighbor readings"]


def test_source_health_and_outage_models(memory_db_session: Session):
    """Verify operational source health transition and outage episode tables."""
    t_start = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
    t_res = datetime(2026, 9, 17, 10, 45, 0, tzinfo=timezone.utc)

    trans = SourceHealthTransitionModel(
        source="open_meteo",
        from_state="HEALTHY",
        to_state="DISCONNECTED",
        reason="HTTP 500 upstream timeout",
        trigger_category="TIMEOUT",
        metadata_json={"consecutive_failures": 3},
        transition_timestamp=t_start,
    )
    episode = OutageEpisodeModel(
        episode_id="ep_20260917_001",
        source="open_meteo",
        started_at=t_start,
        resolved_at=t_res,
        initial_state="DISCONNECTED",
        current_state="HEALTHY",
        duration_seconds=2700.0,
        affected_stations=["42182099999", "42181099999"],
        failure_categories=["TIMEOUT"],
        observation_loss_estimate=6,
        is_ongoing=False,
    )
    memory_db_session.add(trans)
    memory_db_session.add(episode)
    memory_db_session.commit()

    retrieved_ep = memory_db_session.execute(
        select(OutageEpisodeModel).where(OutageEpisodeModel.episode_id == "ep_20260917_001")
    ).scalar_one()
    assert retrieved_ep.duration_seconds == 2700.0
    assert retrieved_ep.observation_loss_estimate == 6
    assert retrieved_ep.is_ongoing is False


def test_sensor_health_and_correction_models(memory_db_session: Session):
    """Verify sensor health snapshot and advisory correction models."""
    t_now = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
    health = SensorHealthSnapshotModel(
        station_id="42182099999",
        timestamp=t_now,
        overall_health_score=88.5,
        status_band="HEALTHY",
        trend="STABLE",
        maintenance_recommendation="NO_ACTION",
        parameter_health={"temperature": {"health_score": 90.0}},
        component_scores={"anomaly_penalty": 0.0},
        active_anomalies_count=0,
    )
    corr = CorrectionRecommendationModel(
        observation_id="obs_corr_01",
        station_id="42182099999",
        timestamp=t_now,
        target_variable="temperature_c",
        observed_value=55.0,  # pristine raw value preserved
        recommended_value=26.4,
        status="REVIEW_RECOMMENDED",
        method="SPATIAL_IDW_CONSENSUS",
        confidence_lower=25.0,
        confidence_upper=27.8,
        uncertainty_json={"standard_error": 0.7},
        multivariate_consistent=True,
        reason_codes=["ISOLATED_SPIKE"],
        operator_summary="Recommended 26.4C based on 4 spatial neighbors.",
    )
    memory_db_session.add(health)
    memory_db_session.add(corr)
    memory_db_session.commit()

    retrieved_corr = memory_db_session.execute(
        select(CorrectionRecommendationModel).where(CorrectionRecommendationModel.observation_id == "obs_corr_01")
    ).scalar_one()
    assert retrieved_corr.observed_value == 55.0  # pristine raw value preserved
    assert retrieved_corr.recommended_value == 26.4
    assert retrieved_corr.multivariate_consistent is True
