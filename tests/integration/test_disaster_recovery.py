"""Disaster Recovery, Backup/Restore Verification, and Database Failure Resilience Tests for SkyGuard AI."""

from datetime import datetime, timezone
import os
from pathlib import Path
import pytest
from sqlalchemy import create_engine, func, select, text

from backend.app.core.database import DatabaseRepository
from backend.app.core.engine import RealTimeProcessingEngine
from backend.app.db.migrations import init_db_schema
from backend.app.db.models import (
    AnomalyEventModel,
    CorrectionRecommendationModel,
    ExplanationModel,
    OutageEpisodeModel,
    RawSourcePayloadModel,
    SensorHealthSnapshotModel,
    SourceHealthTransitionModel,
    StationModel,
    WeatherObservationModel,
)
from backend.app.db.session import DatabaseSessionManager
from backend.app.ingestion.source_health import ErrorCategory, OutageEpisode, SourceHealthState, SourceHealthTransition
from backend.app.models.observation import ObservationSource, QualityStatus, WeatherObservation
from backend.app.models.processing import AnomalyEventRecord, ProcessingStatus
from deploy.backup_restore import DisasterRecoveryManager
from ml.decision.schema import DecisionSeverity, HybridDecisionType
from ml.explainability.schema import AuditMetadata, ContributionDirection, EvidenceHierarchy, ExplanationSummary, FeatureContribution
from ml.imputation.schema import (
    CorrectionAuditMetadata,
    CorrectionRecommendation,
    EstimationMethod,
    RecommendationStatus,
    UncertaintyEstimate,
)
from ml.spatial.topology import SpatialNetworkTopology, StationNode


def populate_test_database(session_mgr: DatabaseSessionManager) -> SpatialNetworkTopology:
    """Populate database across all 9 persistent domain models."""
    init_db_schema(session_mgr.engine)
    topo = SpatialNetworkTopology()
    topo.add_station(StationNode(station_id="42182099999", name="SAFDARJUNG", latitude=28.585, longitude=77.206, elevation_m=216.0))
    topo.add_station(StationNode(station_id="42181099999", name="PALAM", latitude=28.567, longitude=77.117, elevation_m=237.0))
    repo = DatabaseRepository(topology=topo, session_manager=session_mgr)

    # 1. Observations and raw payloads (2 records)
    obs1 = WeatherObservation(
        station_id="42182099999",
        timestamp=datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc),
        latitude=28.585,
        longitude=77.206,
        temperature=28.5,
        humidity=62.0,
        pressure=1012.0,
    )
    obs2 = WeatherObservation(
        station_id="42181099999",
        timestamp=datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc),
        latitude=28.567,
        longitude=77.117,
        temperature=29.0,
        humidity=60.0,
        pressure=1011.8,
    )
    repo.save_observation(obs1, raw_payload='{"latitude": 28.585, "current": {"temperature_2m": 28.5}}', headers_metadata={"Content-Type": "application/json"})
    repo.save_observation(obs2)

    # 3. Anomaly Event & 4. Explanation
    event = AnomalyEventRecord(
        event_id="ANOM-20260917-42182099999-001",
        station_id="42182099999",
        timestamp="2026-09-17T10:00:00Z",
        decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        severity="HIGH",
        explanation_summary="High temperature spike uncorroborated by neighbors.",
    )
    expl = ExplanationSummary(
        station_id="42182099999",
        timestamp="2026-09-17T10:00:00Z",
        decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        severity=DecisionSeverity.HIGH,
        summary="Spatial discordance of +5.5C relative to Palam AWS.",
        feature_contributions=[
            FeatureContribution(
                feature_name="temperature_c_delta",
                feature_value=5.5,
                contribution=0.95,
                direction=ContributionDirection.INCREASES_ANOMALY,
                rank=1,
            )
        ],
        evidence_hierarchy=EvidenceHierarchy(
            direct_evidence={"observed_temp": 48.5},
            operational_interpretation="High spike confirmed anomalous by IDW.",
        ),
        recommended_investigation_steps=["Inspect station thermistor calibration"],
        audit_metadata=AuditMetadata(
            input_station_id="42182099999",
            input_timestamp="2026-09-17T10:00:00Z",
            model_version="v0.1.0_baseline",
        ),
    )
    repo.save_anomaly_event(event, explanation=expl)

    # 5. Source Health Transition & 6. Outage Episode
    t_start = datetime(2026, 9, 17, 9, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 9, 17, 9, 15, 0, tzinfo=timezone.utc)
    trans = SourceHealthTransition(
        from_state=SourceHealthState.HEALTHY,
        to_state=SourceHealthState.DEGRADED,
        reason="HTTP timeout",
        trigger_category=ErrorCategory.TIMEOUT,
        timestamp=t_start,
        metadata={"provider": "open_meteo"},
    )
    episode = OutageEpisode(
        episode_id="OUTAGE-20260917-001",
        started_at=t_start,
        resolved_at=t_end,
        source="open_meteo",
        affected_stations=["42182099999", "42181099999"],
        initial_state=SourceHealthState.DEGRADED,
        current_state=SourceHealthState.HEALTHY,
        duration_seconds=900.0,
        failure_categories=["TIMEOUT"],
        observation_loss_estimate=6,
        is_ongoing=False,
    )
    repo.save_source_transition(trans, source="open_meteo")
    repo.save_outage_episode(episode)

    # 7. Correction Recommendation
    corr = CorrectionRecommendation(
        observation_id="OBS-42182099999-20260917-001",
        station_id="42182099999",
        timestamp="2026-09-17T10:00:00Z",
        target_variable="temperature_c",
        observed_value=48.5,
        recommended_value=28.5,
        status=RecommendationStatus.REVIEW_RECOMMENDED,
        method=EstimationMethod.SPATIAL_IDW_CONSENSUS,
        decision_type="PROBABLE_SENSOR_ANOMALY",
        uncertainty=UncertaintyEstimate(estimate_range=(27.5, 29.5), standard_error=0.5, absolute_deviation=20.0),
        operator_summary="Recommended spatial consensus estimate of 28.5C derived from neighboring AWS nodes.",
    )
    repo.save_correction(corr)
    return topo


def test_disaster_recovery_backup_and_restore_cycle(tmp_path):
    """Test full cycle: populate DB -> create verified backup -> restore into clean DB -> verify parity."""
    # Step 1: Create and populate source database
    src_db_file = tmp_path / "source_primary.db"
    src_session_mgr = DatabaseSessionManager(f"sqlite:///{src_db_file}")
    populate_test_database(src_session_mgr)

    dr_manager = DisasterRecoveryManager(database_url=f"sqlite:///{src_db_file}")
    pre_backup_counts = dr_manager.get_table_counts(src_session_mgr.engine)
    assert pre_backup_counts["stations"] >= 2
    assert pre_backup_counts["observations"] >= 2
    assert pre_backup_counts["anomaly_events"] >= 1
    assert pre_backup_counts["anomaly_explanations"] >= 1
    assert pre_backup_counts["raw_source_payloads"] >= 1
    assert pre_backup_counts["source_health_transitions"] >= 1
    assert pre_backup_counts["outage_episodes"] >= 1
    assert pre_backup_counts["correction_recommendations"] >= 1

    # Step 2: Create Backup
    backup_dir = tmp_path / "backups"
    backup_artifact = dr_manager.create_backup(backup_dir)
    assert backup_artifact.exists()
    assert (backup_artifact / "backup_metadata.json").exists()
    assert (backup_artifact / "database_snapshot.db").exists()

    # Step 3: Verify Backup Checksum and Metadata
    is_valid, verify_msg, meta = dr_manager.verify_backup(backup_artifact)
    assert is_valid is True
    assert meta["total_records"] == sum(pre_backup_counts.values())

    # Step 4: Restore Backup into a completely clean target database
    target_db_file = tmp_path / "restored_target.db"
    target_db_url = f"sqlite:///{target_db_file}"
    restore_ok, restore_msg, post_restore_counts = dr_manager.restore_backup(backup_artifact, target_db_url=target_db_url)
    assert restore_ok is True

    # Step 5: Validate 100% Record Count Parity across all 9 domain tables
    for table_name, count in pre_backup_counts.items():
        assert post_restore_counts[table_name] == count, (
            f"Record parity failed for table '{table_name}': expected {count}, restored {post_restore_counts[table_name]}"
        )

    # Step 6: Verify Application Engine Compatibility Against Restored Database
    target_session_mgr = DatabaseSessionManager(target_db_url)
    topo = SpatialNetworkTopology()
    topo.add_station(StationNode(station_id="42182099999", name="SAFDARJUNG", latitude=28.585, longitude=77.206, elevation_m=216.0))
    restored_repo = DatabaseRepository(topology=topo, session_manager=target_session_mgr)
    restored_engine = RealTimeProcessingEngine(repository=restored_repo)

    # Verify query of restored historical observation
    hist, total = restored_repo.get_station_history("42182099999", limit=10, offset=0)
    assert total >= 1
    assert hist[0].temperature == 28.5

    # Verify ingestion of new observation into restored database
    new_obs = WeatherObservation(
        station_id="42182099999",
        timestamp=datetime(2026, 9, 17, 10, 5, 0, tzinfo=timezone.utc),
        latitude=28.585,
        longitude=77.206,
        temperature=28.7,
        humidity=61.0,
        pressure=1012.1,
    )
    ingested_record = restored_engine.process_observation(new_obs)
    assert ingested_record.status == ProcessingStatus.PROCESSED
    assert restored_repo.persistence_degraded is False


def test_database_failure_resilience_and_graceful_recovery(tmp_path):
    """Verify system survives database connection drop, continues memory pipeline, and recovers on reconnect."""
    db_file = tmp_path / "resilient.db"
    session_mgr = DatabaseSessionManager(f"sqlite:///{db_file}")
    init_db_schema(session_mgr.engine)
    topo = SpatialNetworkTopology()
    topo.add_station(StationNode(station_id="RESIL_001", name="Resilience Test", latitude=28.6, longitude=77.2, elevation_m=200.0))
    repo = DatabaseRepository(topology=topo, session_manager=session_mgr)
    engine = RealTimeProcessingEngine(repository=repo)

    # 1. Normal nominal ingestion
    obs1 = WeatherObservation(
        station_id="RESIL_001",
        timestamp=datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc),
        latitude=28.6,
        longitude=77.2,
        temperature=25.0,
        humidity=50.0,
        pressure=1013.25,
    )
    rec1 = engine.process_observation(obs1)
    assert rec1.status == ProcessingStatus.PROCESSED
    assert repo.persistence_degraded is False

    # 2. Simulate database failure by forcing invalid session / disposal
    class FailingSessionManager:
        def session(self):
            raise RuntimeError("Database network link severed (simulated outage)")
        @property
        def engine(self):
            return session_mgr.engine

    repo.session_manager = FailingSessionManager()

    # 3. Processing observation during outage does NOT crash the engine
    obs2 = WeatherObservation(
        station_id="RESIL_001",
        timestamp=datetime(2026, 9, 17, 12, 5, 0, tzinfo=timezone.utc),
        latitude=28.6,
        longitude=77.2,
        temperature=25.2,
        humidity=50.5,
        pressure=1013.20,
    )
    rec2 = engine.process_observation(obs2)
    assert rec2 is not None
    assert rec2.status == ProcessingStatus.PROCESSED
    assert repo.persistence_degraded is True
    # In-memory streaming state remains intact
    assert any(k.startswith("RESIL_001") for k in repo.observations.keys())

    # 4. Restore database connection and verify recovery
    repo.session_manager = session_mgr
    obs3 = WeatherObservation(
        station_id="RESIL_001",
        timestamp=datetime(2026, 9, 17, 12, 10, 0, tzinfo=timezone.utc),
        latitude=28.6,
        longitude=77.2,
        temperature=25.4,
        humidity=51.0,
        pressure=1013.15,
    )
    rec3 = engine.process_observation(obs3)
    assert rec3.status == ProcessingStatus.PROCESSED
    assert repo.persistence_degraded is False
