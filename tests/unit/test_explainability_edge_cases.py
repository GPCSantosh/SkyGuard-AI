"""Unit tests for explainability engine edge cases, determinism, and auditability."""

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
    MLAnomalyEvidence,
    MultivariateEvidence,
    ObservationEvidence,
    SpatialEvidence,
    TemporalEvidence,
)
from ml.explainability.engine import ExplainabilityEngine
from ml.models.isolation_forest import IsolationForestDetector
from ml.spatial.schema import SpatialContextCategory


@pytest.fixture
def trained_engine() -> ExplainabilityEngine:
    """Fixture providing an ExplainabilityEngine with a trained Isolation Forest."""
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        "temperature_c": np.random.normal(20.0, 2.0, n),
        "relative_humidity": np.random.normal(50.0, 5.0, n),
    })
    model = IsolationForestDetector(n_estimators=20, random_state=42).fit(df)
    return ExplainabilityEngine(model=model)


def test_determinism_and_auditability(trained_engine: ExplainabilityEngine):
    """Test that identical inputs produce identical explanations and complete audit metadata."""
    ev = ObservationEvidence(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.85, ml_is_anomaly=True),
        temporal=TemporalEvidence(temp_rate_per_min=1.5, is_rate_abnormal=True),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.LOCAL_ONLY, valid_neighbor_count=3),
    )
    dec = HybridDecision(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        severity=DecisionSeverity.HIGH,
        reason_codes=[DecisionReasonCode.LOCAL_SPATIAL_ISOLATION, DecisionReasonCode.RAPID_RATE_OF_CHANGE],
        recommended_action="Inspect sensor.",
        explanation=DecisionExplanation(summary="Sensor anomaly."),
        evidence=ev,
    )

    feat_vec = {"temperature_c": 35.0, "relative_humidity": 50.0}

    # Generate twice
    exp1 = trained_engine.explain(dec, feature_vector=feat_vec)
    exp2 = trained_engine.explain(dec, feature_vector=feat_vec)

    # Determinism
    assert exp1.summary == exp2.summary
    assert len(exp1.feature_contributions) == len(exp2.feature_contributions)
    for c1, c2 in zip(exp1.feature_contributions, exp2.feature_contributions):
        assert c1.feature_name == c2.feature_name
        assert c1.contribution == c2.contribution
        assert c1.direction == c2.direction

    # Auditability
    assert exp1.audit_metadata.input_station_id == "AWS_001"
    assert exp1.audit_metadata.input_timestamp == "2026-09-17T12:00:00Z"
    assert exp1.audit_metadata.model_version == "isolation_forest_v1"
    assert exp1.audit_metadata.explanation_method == "TREE_SHAP"
    assert exp1.audit_metadata.generated_at is not None


def test_edge_case_nan_and_constant_features(trained_engine: ExplainabilityEngine):
    """Test engine handles NaN features, constant features, and missing fields safely."""
    ev = ObservationEvidence(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.9),
    )
    dec = HybridDecision(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        severity=DecisionSeverity.HIGH,
        reason_codes=[DecisionReasonCode.ML_HIGH_ANOMALY_SCORE],
        recommended_action="Inspect.",
        explanation=DecisionExplanation(summary="ML anomaly."),
        evidence=ev,
    )

    feat_vec = {"temperature_c": np.nan, "relative_humidity": 0.0}
    exp = trained_engine.explain(dec, feature_vector=feat_vec)
    assert isinstance(exp.feature_contributions, list)
    assert len(exp.feature_contributions) == 2


def test_edge_case_stale_and_zero_neighbors(trained_engine: ExplainabilityEngine):
    """Test engine handles 0 neighbors, 1 neighbor, and stale neighbors."""
    ev = ObservationEvidence(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        spatial=SpatialEvidence(context_category=SpatialContextCategory.INSUFFICIENT_CONTEXT, valid_neighbor_count=0),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.7),
    )
    dec = HybridDecision(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        decision=HybridDecisionType.UNCERTAIN,
        severity=DecisionSeverity.MEDIUM,
        reason_codes=[DecisionReasonCode.INSUFFICIENT_SPATIAL_CONTEXT, DecisionReasonCode.CONFLICTING_EVIDENCE],
        recommended_action="Collect observations.",
        explanation=DecisionExplanation(summary="Uncertain."),
        evidence=ev,
    )

    exp = trained_engine.explain(
        dec,
        neighbor_data={},
        target_variable="temperature_c",
        target_value=25.0,
    )

    assert exp.neighbor_comparison is not None
    assert exp.neighbor_comparison.total_valid_neighbors == 0
    assert exp.neighbor_comparison.temporal_alignment_status == "NO_NEIGHBORS"
    assert "spatial neighborhood telemetry is insufficient" in exp.summary
