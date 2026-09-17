"""Data lifecycle and configurable retention policy management for SkyGuard AI."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from sqlalchemy import delete
from sqlalchemy.orm import Session

from backend.app.core.config import StorageSettings, get_settings
from backend.app.core.logging import get_logger
from backend.app.db.models import (
    AnomalyEventModel,
    CorrectionRecommendationModel,
    ExplanationModel,
    OutageEpisodeModel,
    RawSourcePayloadModel,
    SensorHealthSnapshotModel,
    SourceHealthTransitionModel,
    WeatherObservationModel,
)

logger = get_logger("db_retention")


class RetentionPolicyManager:
    """Applies retention rules non-destructively based on explicit configuration."""

    def __init__(self, settings: Optional[StorageSettings] = None) -> None:
        self.settings = settings or get_settings().storage

    def prune_expired_records(self, session: Session, now_utc: Optional[datetime] = None) -> Dict[str, int]:
        """Prune records older than configured retention days.
        
        CRITICAL: Negative or zero values indicate indefinite retention (no records pruned).
        """
        now = now_utc or datetime.now(timezone.utc)
        pruned_counts: Dict[str, int] = {
            "observations": 0,
            "raw_payloads": 0,
            "anomalies": 0,
            "sensor_health": 0,
            "source_transitions": 0,
            "outage_episodes": 0,
            "corrections": 0,
        }

        # 1. Weather Observations
        if self.settings.observation_retention_days > 0:
            cutoff = now - timedelta(days=self.settings.observation_retention_days)
            stmt = delete(WeatherObservationModel).where(WeatherObservationModel.observation_timestamp < cutoff)
            res = session.execute(stmt)
            pruned_counts["observations"] = res.rowcount or 0

        # 2. Raw Source Payloads
        if self.settings.raw_payload_retention_days > 0:
            cutoff = now - timedelta(days=self.settings.raw_payload_retention_days)
            stmt = delete(RawSourcePayloadModel).where(RawSourcePayloadModel.retrieval_timestamp < cutoff)
            res = session.execute(stmt)
            pruned_counts["raw_payloads"] = res.rowcount or 0

        # 3. Anomalies & Explanations
        if self.settings.anomaly_retention_days > 0:
            cutoff = now - timedelta(days=self.settings.anomaly_retention_days)
            # Find matching event_ids to clean explanations
            stmt_exp = delete(ExplanationModel).where(ExplanationModel.timestamp < cutoff)
            session.execute(stmt_exp)
            stmt = delete(AnomalyEventModel).where(AnomalyEventModel.timestamp < cutoff)
            res = session.execute(stmt)
            pruned_counts["anomalies"] = res.rowcount or 0

        # 4. Sensor Health Snapshots
        if self.settings.sensor_health_retention_days > 0:
            cutoff = now - timedelta(days=self.settings.sensor_health_retention_days)
            stmt = delete(SensorHealthSnapshotModel).where(SensorHealthSnapshotModel.timestamp < cutoff)
            res = session.execute(stmt)
            pruned_counts["sensor_health"] = res.rowcount or 0

        # 5. Source Health Transitions
        if self.settings.source_health_retention_days > 0:
            cutoff = now - timedelta(days=self.settings.source_health_retention_days)
            stmt = delete(SourceHealthTransitionModel).where(SourceHealthTransitionModel.transition_timestamp < cutoff)
            res = session.execute(stmt)
            pruned_counts["source_transitions"] = res.rowcount or 0

        # 6. Outage Episodes (only closed episodes)
        if self.settings.outage_episode_retention_days > 0:
            cutoff = now - timedelta(days=self.settings.outage_episode_retention_days)
            stmt = delete(OutageEpisodeModel).where(
                OutageEpisodeModel.resolved_at.is_not(None),
                OutageEpisodeModel.resolved_at < cutoff,
            )
            res = session.execute(stmt)
            pruned_counts["outage_episodes"] = res.rowcount or 0

        # 7. Correction Recommendations
        if self.settings.correction_retention_days > 0:
            cutoff = now - timedelta(days=self.settings.correction_retention_days)
            stmt = delete(CorrectionRecommendationModel).where(CorrectionRecommendationModel.timestamp < cutoff)
            res = session.execute(stmt)
            pruned_counts["corrections"] = res.rowcount or 0

        total_pruned = sum(pruned_counts.values())
        if total_pruned > 0:
            logger.info("Retention prune completed: %s", pruned_counts)

        return pruned_counts
