"""Integration tests verifying end-to-end production persistence lifecycle scenarios for SkyGuard AI.

Scenarios verified:
1. Backend Restart Recovery (surviving process/repository restart)
2. Duplicate Retry Idempotency (tolerating network/polling retries)
3. Source Outage Persistence (persisting state machine transitions and episodes)
4. Correction Immutability (raw observation remains pristine, correction separate)
5. Historical Reproducibility (model, feature, and engine version traceability)
6. Database Failure Resilience (graceful degradation without pipeline crash)
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
import pytest
from sqlalchemy import create_engine, func, select

from backend.app.core.database import DatabaseRepository
from backend.app.core.engine import RealTimeProcessingEngine
from backend.app.db.models import (
    AnomalyEventModel,
    Base,
    CorrectionRecommendationModel,
    OutageEpisodeModel,
    SourceHealthTransitionModel,
    WeatherObservationModel,
)
from backend.app.db.session import DatabaseSessionManager
from backend.app.ingestion.source_health import ErrorCategory, SourceHealthState, SourceHealthStateMachine
from backend.app.models.observation import ObservationSource, QualityStatus, WeatherObservation
from backend.app.models.processing import AnomalyEventRecord, ProcessingStatus
from ml.decision.schema import HybridDecisionType
from ml.explainability.schema import ExplanationSummary
from ml.imputation.schema import (
    CorrectionAuditMetadata,
    CorrectionRecommendation,
    EstimationMethod,
    RecommendationStatus,
    UncertaintyEstimate,
)

from ml.spatial.topology import SpatialNetworkTopology, StationNode


def get_test_topology() -> SpatialNetworkTopology:
    """Create a standard 3-station test topology."""
    topo = SpatialNetworkTopology()
    topo.add_station(StationNode(
        station_id="42182099999",
        name="NEW DELHI / SAFDARJUNG",
        latitude=28.585,
        longitude=77.206,
        elevation_m=216.0,
        state="DELHI",
    ))
    topo.add_station(StationNode(
        station_id="42181099999",
        name="DELHI / PALAM",
        latitude=28.567,
        longitude=77.117,
        elevation_m=237.0,
        state="DELHI",
    ))
    return topo


@pytest.fixture
def temp_db_file():
    """Create a temporary SQLite file database path with safe teardown."""
    tmp_path = Path(tempfile.gettempdir()) / f"skyguard_test_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.db"
    db_url = f"sqlite:///{tmp_path.as_posix()}"
    yield db_url
    # Cleanup file if exists
    for suffix in ["", "-wal", "-shm"]:
        p = Path(f"{tmp_path}{suffix}")
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass



def test_backend_restart_recovery_scenario(temp_db_file: str):
    """Integration Scenario 1: Telemetry and anomalies survive complete backend restart."""
    topo = get_test_topology()
    session_mgr1 = DatabaseSessionManager(database_url=temp_db_file)
    repo1 = DatabaseRepository(topology=topo, session_manager=session_mgr1)
    engine1 = RealTimeProcessingEngine(repository=repo1)

    t_obs = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
    obs = WeatherObservation(
        station_id="42182099999",
        station_name="NEW DELHI / SAFDARJUNG",
        timestamp=t_obs,
        temperature=48.5,  # extreme spike
        humidity=35.0,
        pressure=1010.2,
        latitude=28.585,
        longitude=77.206,
        elevation=216.0,
        source=ObservationSource.OPEN_METEO,
        data_quality_status=QualityStatus.VALID,
        ingestion_timestamp=t_obs,
    )

    # 1. Ingest observation into Engine 1
    result1 = engine1.process_observation(obs)
    assert result1.status == ProcessingStatus.PROCESSED

    # 2. Simulate Backend / Repository Process Termination
    session_mgr1.close()
    del repo1
    del engine1
    del session_mgr1

    # 3. Reconnect fresh Backend / Repository to existing Database
    session_mgr2 = DatabaseSessionManager(database_url=temp_db_file)
    repo2 = DatabaseRepository(topology=topo, session_manager=session_mgr2)

    # 4. Verify data was persisted and recovered
    history, total = repo2.get_station_history("42182099999")
    assert total == 1
    assert len(history) == 1
    assert history[0].station_id == "42182099999"
    assert history[0].temperature == 48.5
    assert history[0].source == "OPEN_METEO"

    # Verify latest snapshot query survives restart
    latest = repo2.get_station_latest("42182099999")
    assert latest is not None
    assert latest.latest_temperature_c == 48.5
    assert latest.last_seen_timestamp == t_obs.isoformat()

    session_mgr2.close()


def test_duplicate_retry_idempotency_scenario(temp_db_file: str):
    """Integration Scenario 2: Network / polling retry does not create duplicate DB rows."""
    topo = get_test_topology()
    session_mgr = DatabaseSessionManager(database_url=temp_db_file)
    repo = DatabaseRepository(topology=topo, session_manager=session_mgr)
    engine = RealTimeProcessingEngine(repository=repo)

    t_obs = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
    obs = WeatherObservation(
        station_id="42182099999",
        timestamp=t_obs,
        temperature=25.0,
        humidity=60.0,
        pressure=1013.25,
        latitude=28.585,
        longitude=77.206,
        source=ObservationSource.OPEN_METEO,
        ingestion_timestamp=t_obs,
    )

    # Initial Ingestion
    res1 = engine.process_observation(obs)
    assert res1.status == ProcessingStatus.PROCESSED

    # Simulated Retry of Same Observation
    res2 = engine.process_observation(obs)
    assert res2.status == ProcessingStatus.DUPLICATE_SKIPPED

    # Verify database contains exactly 1 record
    with session_mgr.session() as session:
        count = session.execute(
            select(func.count(WeatherObservationModel.id))
            .where(WeatherObservationModel.station_id == "42182099999")
        ).scalar_one()
        assert count == 1

    session_mgr.close()


def test_source_outage_persistence_scenario(temp_db_file: str):
    """Integration Scenario 3: Source health transitions and outage episodes are durably persisted."""
    topo = get_test_topology()
    session_mgr = DatabaseSessionManager(database_url=temp_db_file)
    repo = DatabaseRepository(topology=topo, session_manager=session_mgr)

    sm = SourceHealthStateMachine(
        provider="open_meteo",
        outage_consecutive_failures=2,
        recovery_required_successes=2,
        expected_cadence_seconds=900.0,
        repository=repo,
    )

    t1 = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 17, 10, 15, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 9, 17, 10, 30, 0, tzinfo=timezone.utc)
    t4 = datetime(2026, 9, 17, 10, 45, 0, tzinfo=timezone.utc)

    # Failure 1 -> DEGRADED
    sm.record_poll_cycle_failure(
        category=ErrorCategory.TIMEOUT,
        error_message="HTTP Timeout 1",
        timestamp=t1,
    )
    assert sm.current_state == SourceHealthState.DEGRADED

    # Failure 2 -> DISCONNECTED (Outage threshold reached)
    sm.record_poll_cycle_failure(
        category=ErrorCategory.HTTP_5XX,
        error_message="HTTP 502 Bad Gateway",
        timestamp=t2,
    )
    assert sm.current_state == SourceHealthState.DISCONNECTED

    # Recovery Success 1 -> DEGRADED (Warm-up)
    station_success = {
        "42182099999": {"success": True, "observation_timestamp": t3, "temperature": 25.0},
    }
    sm.record_poll_cycle_success(latency_ms=120.0, station_results=station_success, timestamp=t3)
    assert sm.current_state == SourceHealthState.DEGRADED

    # Recovery Success 2 -> HEALTHY (Resolved)
    sm.record_poll_cycle_success(latency_ms=115.0, station_results=station_success, timestamp=t4)
    assert sm.current_state == SourceHealthState.HEALTHY

    # Verify transitions persisted in DB
    with session_mgr.session() as session:
        transitions = session.execute(
            select(SourceHealthTransitionModel).order_by(SourceHealthTransitionModel.transition_timestamp.asc())
        ).scalars().all()
        assert len(transitions) >= 3

        # Verify outage episode persisted with calculated duration and loss estimate
        episodes = session.execute(select(OutageEpisodeModel)).scalars().all()
        assert len(episodes) == 1
        ep = episodes[0]
        assert ep.initial_state == "DEGRADED"
        assert ep.current_state == "HEALTHY"
        assert ep.is_ongoing is False
        assert ep.resolved_at is not None
        assert ep.duration_seconds == 2700.0  # 10:00 to 10:45 = 45 min = 2700s

    session_mgr.close()


def test_correction_immutability_scenario(temp_db_file: str):
    """Integration Scenario 4: Raw observations remain 100% immutable when corrections are generated."""
    topo = get_test_topology()
    session_mgr = DatabaseSessionManager(database_url=temp_db_file)
    repo = DatabaseRepository(topology=topo, session_manager=session_mgr)

    t_obs = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
    raw_obs = WeatherObservation(
        station_id="42182099999",
        timestamp=t_obs,
        temperature=58.2,  # raw corrupted spike
        humidity=40.0,
        pressure=1012.0,
        latitude=28.585,
        longitude=77.206,
        source=ObservationSource.OPEN_METEO,
        ingestion_timestamp=t_obs,
    )
    repo.save_observation(raw_obs)

    # Save advisory correction recommendation
    corr = CorrectionRecommendation(
        observation_id="obs_test_corr_01",
        station_id="42182099999",
        timestamp=t_obs.isoformat(),
        target_variable="temperature_c",
        observed_value=58.2,
        recommended_value=27.1,
        decision_type=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        status=RecommendationStatus.REVIEW_RECOMMENDED,
        method=EstimationMethod.SPATIAL_IDW_CONSENSUS,
        uncertainty=UncertaintyEstimate(estimate_range=(25.5, 28.7), standard_error=0.8),
        multivariate_consistent=True,
        reason_codes=["SPATIAL_DISCORDANCE"],
        operator_summary="Recommended 27.1C based on 3 neighbor consensus.",
        audit_metadata=CorrectionAuditMetadata(),
    )
    repo.save_correction(corr)



    # Verify in DB: raw observation has NOT been mutated
    with session_mgr.session() as session:
        obs_row = session.execute(
            select(WeatherObservationModel).where(WeatherObservationModel.station_id == "42182099999")
        ).scalar_one()
        assert obs_row.temperature_c == 58.2  # pristine raw value unaltered

        corr_row = session.execute(
            select(CorrectionRecommendationModel).where(CorrectionRecommendationModel.observation_id == "obs_test_corr_01")
        ).scalar_one()
        assert corr_row.observed_value == 58.2
        assert corr_row.recommended_value == 27.1
        assert corr_row.status == "REVIEW_RECOMMENDED"

    session_mgr.close()


def test_historical_reproducibility_scenario(temp_db_file: str):
    """Integration Scenario 5: Historical anomaly results preserve full model and engine provenance."""
    topo = get_test_topology()
    session_mgr = DatabaseSessionManager(database_url=temp_db_file)
    repo = DatabaseRepository(topology=topo, session_manager=session_mgr)

    t_obs = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
    ev = AnomalyEventRecord(
        event_id="ANOM-20260917-0099",
        station_id="42182099999",
        timestamp=t_obs.isoformat(),
        decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        severity="HIGH",
        reason_codes=["ISOLATED_ANOMALY_SPARSE_NETWORK"],
        observed_values={"temperature_c": 52.0},
        recommended_values={"temperature_c": 25.0},
        explanation_summary="High temperature rate spike.",
    )
    from ml.decision.schema import DecisionSeverity
    from ml.explainability.schema import AuditMetadata, ContributionDirection, EvidenceHierarchy, FeatureContribution

    exp = ExplanationSummary(
        station_id="42182099999",
        timestamp=t_obs.isoformat(),
        decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        severity=DecisionSeverity.HIGH,
        summary="High temperature rate spike.",
        feature_contributions=[
            FeatureContribution(
                feature_name="temperature_c_delta",
                feature_value=5.0,
                contribution=0.92,
                direction=ContributionDirection.INCREASES_ANOMALY,
                rank=1,
            )
        ],
        evidence_hierarchy=EvidenceHierarchy(
            direct_evidence={"observed_temp": 52.0},
            operational_interpretation="Probable sensor anomaly due to rate spike.",
        ),
        recommended_investigation_steps=["Inspect thermocouple"],
        audit_metadata=AuditMetadata(
            input_station_id="42182099999",
            input_timestamp=t_obs.isoformat(),
            model_version="isolation_forest_v1",
        ),
    )
    provenance = {
        "model_id": "isolation_forest_s42",
        "model_version": "v0.1.0_baseline",
        "feature_version": "v1.0.0",
        "decision_engine_version": "hybrid_v1.0.0",
        "explanation_version": "v1.0.0",
    }

    repo.save_anomaly_event(ev, explanation=exp, provenance=provenance)


    # Verify query returns complete provenance
    retrieved_ev = repo.get_anomaly_by_id("ANOM-20260917-0099")
    retrieved_exp = repo.get_anomaly_explanation("ANOM-20260917-0099")

    assert retrieved_ev is not None
    assert retrieved_exp is not None
    assert retrieved_exp.feature_contributions[0].contribution == 0.92


    with session_mgr.session() as session:
        db_anom = session.execute(
            select(AnomalyEventModel).where(AnomalyEventModel.event_id == "ANOM-20260917-0099")
        ).scalar_one()
        assert db_anom.model_id == "isolation_forest_s42"
        assert db_anom.model_version == "v0.1.0_baseline"
        assert db_anom.feature_version == "v1.0.0"
        assert db_anom.decision_engine_version == "hybrid_v1.0.0"

    session_mgr.close()


def test_database_failure_resilience_scenario():
    """Integration Scenario 6: Database unavailability does not corrupt pipeline or crash execution."""
    topo = get_test_topology()
    # Provide an invalid database URL to simulate DB refusal/failure
    failing_session_mgr = DatabaseSessionManager(database_url="sqlite:////non_existent_folder_xyz_123/unwritable.db")
    repo = DatabaseRepository(topology=topo, session_manager=failing_session_mgr, auto_init_db=False)
    engine = RealTimeProcessingEngine(repository=repo)

    t_obs = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
    obs = WeatherObservation(
        station_id="42182099999",
        timestamp=t_obs,
        temperature=24.5,
        humidity=55.0,
        pressure=1013.0,
        latitude=28.585,
        longitude=77.206,
        source=ObservationSource.OPEN_METEO,
        ingestion_timestamp=t_obs,
    )

    # Engine must process successfully in degraded memory mode without unhandled crash
    result = engine.process_observation(obs)
    assert result.status == ProcessingStatus.PROCESSED
    assert result.observation.temperature == 24.5

    # System health should report database status as DEGRADED or DISCONNECTED
    sys_health = repo.get_system_health()
    assert sys_health.database_status in ("DEGRADED", "DISCONNECTED")
    assert repo.persistence_degraded is True
