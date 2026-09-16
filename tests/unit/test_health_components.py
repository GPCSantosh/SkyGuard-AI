"""Unit tests for health component extractions and history buffer."""

import numpy as np
import pandas as pd
import pytest

from ml.decision.schema import (
    DataQualityEvidence,
    DecisionExplanation,
    DecisionReasonCode,
    DecisionSeverity,
    HybridDecision,
    HybridDecisionType,
    ObservationEvidence,
    SpatialEvidence,
    TemporalEvidence,
)
from ml.health.health_features import HealthFeatureExtractor
from ml.health.health_history import HealthHistoryBuffer
from ml.spatial.schema import SpatialContextCategory


@pytest.fixture
def feature_extractor() -> HealthFeatureExtractor:
    return HealthFeatureExtractor()


def test_anomaly_stats_and_regional_protection(feature_extractor: HealthFeatureExtractor):
    """Test anomaly extraction and verify genuine regional events are protected from penalties."""
    # Create 10 decisions: 2 spikes, 3 genuine events, 5 normal
    decs: List[HybridDecision] = []
    base_t = pd.Timestamp("2026-09-17 00:00:00")

    for i in range(10):
        t_str = (base_t + pd.Timedelta(minutes=i * 5)).isoformat() + "Z"
        if i in (0, 1):
            # Spikes
            ev = ObservationEvidence(station_id="AWS_001", timestamp=t_str)
            dec = HybridDecision(
                station_id="AWS_001", timestamp=t_str, decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
                severity=DecisionSeverity.HIGH, reason_codes=[DecisionReasonCode.LOCAL_SPATIAL_ISOLATION],
                recommended_action="Inspect", explanation=DecisionExplanation(summary="Spike"), evidence=ev,
            )
        elif i in (2, 3, 4):
            # Regional Squall (POSSIBLE_GENUINE_EVENT) -> Must NOT be penalized!
            ev = ObservationEvidence(station_id="AWS_001", timestamp=t_str)
            dec = HybridDecision(
                station_id="AWS_001", timestamp=t_str, decision=HybridDecisionType.POSSIBLE_GENUINE_EVENT,
                severity=DecisionSeverity.LOW, reason_codes=[DecisionReasonCode.REGIONAL_SPATIAL_AGREEMENT],
                recommended_action="Monitor", explanation=DecisionExplanation(summary="Regional front"), evidence=ev,
            )
        else:
            # Normal
            ev = ObservationEvidence(station_id="AWS_001", timestamp=t_str)
            dec = HybridDecision(
                station_id="AWS_001", timestamp=t_str, decision=HybridDecisionType.NORMAL,
                severity=DecisionSeverity.INFO, reason_codes=[DecisionReasonCode.NOMINAL_OBSERVATION],
                recommended_action="None", explanation=DecisionExplanation(summary="Normal"), evidence=ev,
            )
        decs.append(dec)

    stats = feature_extractor.extract_anomaly_stats(decs)
    assert stats.total_observations == 10
    assert stats.anomaly_count == 2
    assert stats.genuine_event_count == 3
    # Only 2 anomalies contributed to severity sum
    assert stats.severity_weighted_anomalies == 2.0
    assert stats.anomaly_rate_per_100 == 20.0


def test_history_buffer_recency_weighting_and_slicing():
    """Test history buffer window slicing and exponential recency weights."""
    buffer = HealthHistoryBuffer(recency_lambda=2.0)
    base_t = pd.Timestamp("2026-09-17 00:00:00")

    # Add 24 hourly records
    for i in range(24):
        t_str = (base_t + pd.Timedelta(hours=i)).isoformat() + "Z"
        ev = ObservationEvidence(station_id="AWS_001", timestamp=t_str)
        dec = HybridDecision(
            station_id="AWS_001", timestamp=t_str, decision=HybridDecisionType.NORMAL,
            severity=DecisionSeverity.INFO, reason_codes=[DecisionReasonCode.NOMINAL_OBSERVATION],
            recommended_action="None", explanation=DecisionExplanation(summary="Normal"), evidence=ev,
        )
        buffer.add_decision(dec)

    # Query last 12 hours
    slice_decs, weights = buffer.get_window_decisions("AWS_001", custom_hours=12.0)
    assert len(slice_decs) == 13  # Includes boundary endpoints
    assert len(weights) == 13
    # Most recent record has higher weight than oldest in slice
    assert weights[-1] > weights[0]
    # Mean weight is normalized to 1.0
    assert np.isclose(np.mean(weights), 1.0)
