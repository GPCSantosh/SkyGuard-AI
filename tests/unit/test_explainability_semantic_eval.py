"""Unit tests for explanation semantic evaluation across synthetic anomaly types."""

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
from ml.explainability.evaluator import ExplanationSemanticEvaluator
from ml.explainability.schema import FeatureContribution
from ml.spatial.schema import SpatialContextCategory


@pytest.fixture
def engine() -> ExplainabilityEngine:
    return ExplainabilityEngine()


@pytest.fixture
def evaluator() -> ExplanationSemanticEvaluator:
    return ExplanationSemanticEvaluator()


def test_semantic_eval_spike(engine: ExplainabilityEngine, evaluator: ExplanationSemanticEvaluator):
    """Test semantic evaluation for single-station temperature spike."""
    ev = ObservationEvidence(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.92, ml_is_anomaly=True),
        temporal=TemporalEvidence(temp_rate_per_min=1.8, is_rate_abnormal=True),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.LOCAL_ONLY, valid_neighbor_count=4, temp_target_minus_mean=6.5),
    )
    dec = HybridDecision(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        severity=DecisionSeverity.HIGH,
        reason_codes=[DecisionReasonCode.LOCAL_SPATIAL_ISOLATION, DecisionReasonCode.RAPID_RATE_OF_CHANGE],
        recommended_action="Inspect sensor.",
        explanation=DecisionExplanation(summary="Sensor anomaly indicated."),
        evidence=ev,
    )

    exp = engine.explain(dec, target_variable="temperature_c", target_value=32.0)
    res = evaluator.evaluate_explanation_semantics(exp, "SPIKE")
    assert res["passed"] is True
    assert len(res["matched_keywords"]) > 0


def test_semantic_eval_frozen_sensor(engine: ExplainabilityEngine, evaluator: ExplanationSemanticEvaluator):
    """Test semantic evaluation for frozen / stuck sensor flatline."""
    ev = ObservationEvidence(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        temporal=TemporalEvidence(consecutive_unchanged_count=8, flatline_duration_minutes=40.0, is_flatline=True),
    )
    dec = HybridDecision(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        severity=DecisionSeverity.MEDIUM,
        reason_codes=[DecisionReasonCode.PERSISTENT_VALUE],
        recommended_action="Inspect sensor transducer.",
        explanation=DecisionExplanation(summary="Sensor persistence check failed."),
        evidence=ev,
    )

    exp = engine.explain(dec)
    res = evaluator.evaluate_explanation_semantics(exp, "FROZEN_SENSOR")
    assert res["passed"] is True
    assert "unchanged" in res["matched_keywords"] or "persist" in res["matched_keywords"]


def test_semantic_eval_regional_event(engine: ExplainabilityEngine, evaluator: ExplanationSemanticEvaluator):
    """Test semantic evaluation for regional weather front."""
    ev = ObservationEvidence(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        spatial=SpatialEvidence(context_category=SpatialContextCategory.REGIONAL_PATTERN, valid_neighbor_count=5),
        temporal=TemporalEvidence(is_rate_abnormal=True),
    )
    dec = HybridDecision(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        decision=HybridDecisionType.POSSIBLE_GENUINE_EVENT,
        severity=DecisionSeverity.LOW,
        reason_codes=[DecisionReasonCode.REGIONAL_SPATIAL_AGREEMENT, DecisionReasonCode.RAPID_RATE_OF_CHANGE],
        recommended_action="Monitor regional front.",
        explanation=DecisionExplanation(summary="Corroborated by regional AWS network."),
        evidence=ev,
    )

    exp = engine.explain(dec)
    res = evaluator.evaluate_explanation_semantics(exp, "REGIONAL_EVENT")
    assert res["passed"] is True
    assert "regional" in res["matched_keywords"] or "stations" in res["matched_keywords"]


def test_semantic_eval_data_gap(engine: ExplainabilityEngine, evaluator: ExplanationSemanticEvaluator):
    """Test semantic evaluation for data telemetry gap."""
    ev = ObservationEvidence(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        data_quality=DataQualityEvidence(
            quality_status="GAP",
            communication_gap_minutes=60.0,
            missing_fields=["temperature_c"],
        ),
    )
    dec = HybridDecision(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        decision=HybridDecisionType.PROBABLE_DATA_QUALITY_ISSUE,
        severity=DecisionSeverity.HIGH,
        reason_codes=[DecisionReasonCode.DATA_GAP, DecisionReasonCode.MISSING_REQUIRED_VARIABLES],
        recommended_action="Check telemetry queue.",
        explanation=DecisionExplanation(summary="Telemetry gap detected."),
        evidence=ev,
    )

    exp = engine.explain(dec)
    res = evaluator.evaluate_explanation_semantics(exp, "DATA_GAP")
    assert res["passed"] is True


def test_semantic_eval_batch(engine: ExplainabilityEngine, evaluator: ExplanationSemanticEvaluator):
    """Test batch semantic evaluation over mixed synthetic cases."""
    # Build a suite of explanations
    exp1 = engine.explain(HybridDecision(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        severity=DecisionSeverity.HIGH,
        reason_codes=[DecisionReasonCode.LOCAL_SPATIAL_ISOLATION, DecisionReasonCode.RAPID_RATE_OF_CHANGE],
        recommended_action="Inspect sensor.",
        explanation=DecisionExplanation(summary="Sensor anomaly."),
        evidence=ObservationEvidence(
            station_id="AWS_001",
            timestamp="2026-09-17T12:00:00Z",
            temporal=TemporalEvidence(temp_rate_per_min=2.0, is_rate_abnormal=True),
            spatial=SpatialEvidence(context_category=SpatialContextCategory.LOCAL_ONLY, valid_neighbor_count=3),
        ),
    ))

    exp2 = engine.explain(HybridDecision(
        station_id="AWS_002",
        timestamp="2026-09-17T12:00:00Z",
        decision=HybridDecisionType.POSSIBLE_GENUINE_EVENT,
        severity=DecisionSeverity.LOW,
        reason_codes=[DecisionReasonCode.REGIONAL_SPATIAL_AGREEMENT],
        recommended_action="Monitor event.",
        explanation=DecisionExplanation(summary="Regional event."),
        evidence=ObservationEvidence(
            station_id="AWS_002",
            timestamp="2026-09-17T12:00:00Z",
            spatial=SpatialEvidence(context_category=SpatialContextCategory.REGIONAL_PATTERN, valid_neighbor_count=4),
        ),
    ))

    batch = [
        (exp1, "SPIKE"),
        (exp2, "REGIONAL_EVENT"),
    ]

    batch_res = evaluator.evaluate_batch(batch)
    assert batch_res["total_evaluated"] == 2
    assert batch_res["passed_count"] == 2
    assert batch_res["all_passed"] is True
    assert batch_res["pass_rate"] == 1.0
