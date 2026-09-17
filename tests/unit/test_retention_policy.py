"""Unit tests verifying configurable data retention and non-destructive pruning rules."""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.app.core.config import StorageSettings
from backend.app.db.models import (
    AnomalyEventModel,
    Base,
    CorrectionRecommendationModel,
    ExplanationModel,
    OutageEpisodeModel,
    RawSourcePayloadModel,
    SensorHealthSnapshotModel,
    SourceHealthTransitionModel,
    WeatherObservationModel,
)
from backend.app.db.retention import RetentionPolicyManager


@pytest.fixture
def seeded_retention_session():
    """Create in-memory SQLite database populated with historical and recent records."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    session = Session(engine)

    now = datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc)
    old_time = now - timedelta(days=45)  # 45 days old
    recent_time = now - timedelta(days=2)  # 2 days old

    # 1. Observations
    obs_old = WeatherObservationModel(
        observation_id="obs_old",
        station_id="42182099999",
        observation_timestamp=old_time,
        ingestion_timestamp=old_time,
        temperature_c=20.0,
        latitude=28.585,
        longitude=77.206,
        source="NOAA_ISD",
        data_quality_status="VALID",
        raw_quality_flags={},
        metadata_json={},
    )
    obs_recent = WeatherObservationModel(
        observation_id="obs_recent",
        station_id="42182099999",
        observation_timestamp=recent_time,
        ingestion_timestamp=recent_time,
        temperature_c=25.0,
        latitude=28.585,
        longitude=77.206,
        source="NOAA_ISD",
        data_quality_status="VALID",
        raw_quality_flags={},
        metadata_json={},
    )
    session.add_all([obs_old, obs_recent])

    # 2. Anomalies & Explanations
    anom_old = AnomalyEventModel(
        event_id="ANOM_OLD",
        station_id="42182099999",
        timestamp=old_time,
        decision="PROBABLE_SENSOR_ANOMALY",
        severity="HIGH",
        reason_codes=[],
        observed_values={},
        recommended_values={},
    )
    exp_old = ExplanationModel(
        event_id="ANOM_OLD",
        station_id="42182099999",
        timestamp=old_time,
        feature_attributions={},
        spatial_evidence={},
        temporal_evidence={},
        multivariate_evidence={},
        evidence_hierarchy={},
        recommended_sop_steps=[],
    )
    anom_recent = AnomalyEventModel(
        event_id="ANOM_RECENT",
        station_id="42182099999",
        timestamp=recent_time,
        decision="PROBABLE_SENSOR_ANOMALY",
        severity="MEDIUM",
        reason_codes=[],
        observed_values={},
        recommended_values={},
    )
    session.add_all([anom_old, exp_old, anom_recent])

    # 3. Outage Episodes
    ep_old = OutageEpisodeModel(
        episode_id="ep_old",
        source="open_meteo",
        started_at=old_time,
        resolved_at=old_time + timedelta(hours=1),
        initial_state="DEGRADED",
        current_state="HEALTHY",
        duration_seconds=3600.0,
        affected_stations=[],
        failure_categories=[],
        is_ongoing=False,
    )
    ep_recent = OutageEpisodeModel(
        episode_id="ep_recent",
        source="open_meteo",
        started_at=recent_time,
        resolved_at=recent_time + timedelta(hours=1),
        initial_state="DEGRADED",
        current_state="HEALTHY",
        duration_seconds=3600.0,
        affected_stations=[],
        failure_categories=[],
        is_ongoing=False,
    )
    session.add_all([ep_old, ep_recent])

    session.commit()
    yield session, now
    session.close()
    engine.dispose()


def test_default_retention_preserves_all_records(seeded_retention_session):
    """Default -1 retention configuration must be completely non-destructive."""
    session, now = seeded_retention_session
    default_settings = StorageSettings(
        observation_retention_days=-1,
        anomaly_retention_days=-1,
        outage_episode_retention_days=-1,
    )
    manager = RetentionPolicyManager(settings=default_settings)
    pruned = manager.prune_expired_records(session, now_utc=now)
    session.commit()

    assert sum(pruned.values()) == 0

    obs_count = session.execute(select(func.count(WeatherObservationModel.id))).scalar_one()
    anom_count = session.execute(select(func.count(AnomalyEventModel.id))).scalar_one()
    ep_count = session.execute(select(func.count(OutageEpisodeModel.id))).scalar_one()

    assert obs_count == 2
    assert anom_count == 2
    assert ep_count == 2


def test_explicit_retention_pruning(seeded_retention_session):
    """Configured 30-day retention prunes 45-day records while preserving 2-day records."""
    session, now = seeded_retention_session
    custom_settings = StorageSettings(
        observation_retention_days=30,
        anomaly_retention_days=30,
        outage_episode_retention_days=30,
    )
    manager = RetentionPolicyManager(settings=custom_settings)
    pruned = manager.prune_expired_records(session, now_utc=now)
    session.commit()

    assert pruned["observations"] == 1
    assert pruned["anomalies"] == 1
    assert pruned["outage_episodes"] == 1

    # Verify only recent records remain
    remaining_obs = session.execute(select(WeatherObservationModel)).scalars().all()
    assert len(remaining_obs) == 1
    assert remaining_obs[0].observation_id == "obs_recent"

    remaining_anom = session.execute(select(AnomalyEventModel)).scalars().all()
    assert len(remaining_anom) == 1
    assert remaining_anom[0].event_id == "ANOM_RECENT"

    # Corresponding explanation for old anomaly should be cleaned
    remaining_exp = session.execute(select(ExplanationModel)).scalars().all()
    assert len(remaining_exp) == 0
