"""Historical feature and metrics extractor for Sensor Health & Degradation Monitoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence
import numpy as np
import pandas as pd

from ml.decision.schema import (
    DecisionReasonCode,
    DecisionSeverity,
    HybridDecision,
    HybridDecisionType,
)


@dataclass
class AnomalyStats:
    """Aggregated anomaly frequency and severity statistics."""
    total_observations: int = 0
    anomaly_count: int = 0
    genuine_event_count: int = 0
    severity_weighted_anomalies: float = 0.0
    anomaly_rate_per_100: float = 0.0
    max_consecutive_anomalies: int = 0
    is_repeated: bool = False
    is_persistent: bool = False


@dataclass
class DataQualityStats:
    """Aggregated data ingestion and schema quality statistics."""
    missing_fields_count: int = 0
    duplicate_count: int = 0
    out_of_order_count: int = 0
    malformed_count: int = 0
    total_dq_defects: int = 0
    dq_defect_rate: float = 0.0


@dataclass
class CommunicationStats:
    """Aggregated telemetry link and latency statistics."""
    total_gap_minutes: float = 0.0
    gap_episodes_count: int = 0
    max_gap_minutes: float = 0.0


@dataclass
class TemporalStabilityStats:
    """Aggregated flatline and persistence statistics."""
    max_flatline_steps: int = 0
    total_flatline_minutes: float = 0.0
    flatline_episodes_count: int = 0
    stuck_sensor_flag: bool = False


@dataclass
class DriftStats:
    """Aggregated baseline deviation and drift trajectory statistics."""
    drift_magnitude: float = 0.0
    drift_persistence_fraction: float = 0.0
    drift_trend_slope: float = 0.0
    has_significant_drift: bool = False


@dataclass
class SpatialConsistencyStats:
    """Aggregated multi-station spatial agreement statistics."""
    spatial_isolation_count: int = 0
    spatial_agreement_count: int = 0
    regional_event_count: int = 0
    isolation_rate: float = 0.0


class HealthFeatureExtractor:
    """Extracts historical degradation signals from observations and hybrid decision streams."""

    def __init__(
        self,
        severity_penalties: Optional[Dict[str, float]] = None,
        nominal_sampling_interval_min: float = 5.0,
    ) -> None:
        self.severity_penalties = severity_penalties or {
            "INFO": 0.0,
            "LOW": 0.25,
            "MEDIUM": 0.60,
            "HIGH": 1.00,
            "CRITICAL": 2.00,
        }
        self.nominal_interval = nominal_sampling_interval_min

    def extract_anomaly_stats(
        self,
        decisions: Sequence[HybridDecision],
        recency_weights: Optional[np.ndarray] = None,
        target_param: Optional[str] = None,
    ) -> AnomalyStats:
        """Extract frequency and severity-weighted anomaly metrics."""
        total = len(decisions)
        if total == 0:
            return AnomalyStats()

        weights = recency_weights if recency_weights is not None else np.ones(total)

        anom_count = 0
        genuine_count = 0
        weighted_sum = 0.0
        consecutive = 0
        max_consecutive = 0

        for i, dec in enumerate(decisions):
            # Check if this decision is relevant to target_param (if filtered)
            if target_param and dec.recommended_correction and dec.recommended_correction.target_variable:
                if dec.recommended_correction.target_variable != target_param:
                    continue

            # PROTECT REGIONAL EVENTS: Genuine events do NOT count as sensor anomalies
            if dec.decision == HybridDecisionType.POSSIBLE_GENUINE_EVENT:
                genuine_count += 1
                consecutive = 0
                continue

            if dec.decision in (
                HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
                HybridDecisionType.PROBABLE_DATA_QUALITY_ISSUE,
            ):
                anom_count += 1
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
                
                sev_key = dec.severity.value if hasattr(dec.severity, "value") else str(dec.severity)
                penalty = self.severity_penalties.get(sev_key, 1.0)
                weighted_sum += float(weights[i] * penalty)
            else:
                consecutive = 0

        rate = (anom_count / total) * 100.0 if total > 0 else 0.0
        is_repeated = anom_count >= 3
        is_persistent = max_consecutive >= 4

        return AnomalyStats(
            total_observations=total,
            anomaly_count=anom_count,
            genuine_event_count=genuine_count,
            severity_weighted_anomalies=round(weighted_sum, 3),
            anomaly_rate_per_100=round(rate, 2),
            max_consecutive_anomalies=max_consecutive,
            is_repeated=is_repeated,
            is_persistent=is_persistent,
        )

    def extract_data_quality_stats(
        self,
        decisions: Sequence[HybridDecision],
        recency_weights: Optional[np.ndarray] = None,
    ) -> DataQualityStats:
        """Extract data quality, missingness, and schema corruption metrics."""
        total = len(decisions)
        if total == 0:
            return DataQualityStats()

        weights = recency_weights if recency_weights is not None else np.ones(total)

        missing_fields = 0
        duplicates = 0
        out_of_order = 0
        malformed = 0
        defects_weighted = 0.0

        for i, dec in enumerate(decisions):
            dq = dec.evidence.data_quality
            has_defect = False

            if dq.missing_fields:
                missing_fields += len(dq.missing_fields)
                has_defect = True
            if dq.is_duplicate:
                duplicates += 1
                has_defect = True
            if dq.is_out_of_order:
                out_of_order += 1
                has_defect = True
            if dq.quality_status in ("REJECTED", "CORRUPTED"):
                malformed += 1
                has_defect = True

            if has_defect:
                defects_weighted += float(weights[i])

        rate = (defects_weighted / total) if total > 0 else 0.0

        return DataQualityStats(
            missing_fields_count=missing_fields,
            duplicate_count=duplicates,
            out_of_order_count=out_of_order,
            malformed_count=malformed,
            total_dq_defects=int(missing_fields + duplicates + out_of_order + malformed),
            dq_defect_rate=round(rate, 3),
        )

    def extract_communication_stats(
        self,
        decisions: Sequence[HybridDecision],
    ) -> CommunicationStats:
        """Extract communication gaps and telemetry outages."""
        total_gap = 0.0
        gap_episodes = 0
        max_gap = 0.0

        for dec in decisions:
            dq = dec.evidence.data_quality
            gap = dq.communication_gap_minutes
            if gap is not None and gap > (self.nominal_interval * 2.0):
                total_gap += gap
                gap_episodes += 1
                max_gap = max(max_gap, gap)

        return CommunicationStats(
            total_gap_minutes=round(total_gap, 1),
            gap_episodes_count=gap_episodes,
            max_gap_minutes=round(max_gap, 1),
        )

    def extract_temporal_stability_stats(
        self,
        decisions: Sequence[HybridDecision],
    ) -> TemporalStabilityStats:
        """Extract flatline, stuck sensor, and variance metrics."""
        max_steps = 0
        total_flatline = 0.0
        episodes = 0

        for dec in decisions:
            temp_ev = dec.evidence.temporal
            if temp_ev.is_flatline or temp_ev.consecutive_unchanged_count >= 6:
                episodes += 1
                total_flatline += temp_ev.flatline_duration_minutes
                max_steps = max(max_steps, temp_ev.consecutive_unchanged_count)

        return TemporalStabilityStats(
            max_flatline_steps=max_steps,
            total_flatline_minutes=round(total_flatline, 1),
            flatline_episodes_count=episodes,
            stuck_sensor_flag=max_steps >= 12 or total_flatline >= 60.0,
        )

    def extract_drift_stats(
        self,
        decisions: Sequence[HybridDecision],
        target_param: str = "temperature_c",
    ) -> DriftStats:
        """Extract progressive drift indicators from spatial/baseline deltas."""
        deltas: List[float] = []

        for dec in decisions:
            spat = dec.evidence.spatial
            # Target minus neighbor mean is a robust drift indicator
            if spat.temp_target_minus_mean is not None and target_param == "temperature_c":
                deltas.append(spat.temp_target_minus_mean)
            elif dec.evidence.temporal.baseline_deviation_zscore is not None:
                deltas.append(dec.evidence.temporal.baseline_deviation_zscore)

        if not deltas:
            return DriftStats()

        arr = np.array(deltas)
        magnitude = float(np.mean(np.abs(arr)))
        
        # Persistence: fraction of steps where deviation has the same sign and magnitude >= 1.5
        same_sign_pos = np.sum(arr >= 1.5) / len(arr)
        same_sign_neg = np.sum(arr <= -1.5) / len(arr)
        persistence = float(max(same_sign_pos, same_sign_neg))

        # Trend slope
        if len(arr) >= 5:
            x = np.arange(len(arr))
            slope = float(np.polyfit(x, arr, 1)[0])
        else:
            slope = 0.0

        has_drift = persistence >= 0.40 and magnitude >= 2.0

        return DriftStats(
            drift_magnitude=round(magnitude, 3),
            drift_persistence_fraction=round(persistence, 3),
            drift_trend_slope=round(slope, 4),
            has_significant_drift=has_drift,
        )

    def extract_spatial_consistency_stats(
        self,
        decisions: Sequence[HybridDecision],
    ) -> SpatialConsistencyStats:
        """Extract multi-station spatial agreement and isolated disagreement counts."""
        isolation_count = 0
        agreement_count = 0
        regional_events = 0
        total = len(decisions)

        for dec in decisions:
            spat = dec.evidence.spatial
            cat = spat.context_category.value if hasattr(spat.context_category, "value") else str(spat.context_category)

            if cat == "LOCAL_ONLY":
                isolation_count += 1
            elif cat in ("REGIONAL_PATTERN", "LOCAL_CLUSTER"):
                agreement_count += 1
                if cat == "REGIONAL_PATTERN":
                    regional_events += 1

        rate = (isolation_count / total) if total > 0 else 0.0

        return SpatialConsistencyStats(
            spatial_isolation_count=isolation_count,
            spatial_agreement_count=agreement_count,
            regional_event_count=regional_events,
            isolation_rate=round(rate, 3),
        )
