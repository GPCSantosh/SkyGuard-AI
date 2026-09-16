"""Unit tests for reason code mapping, evidence hierarchy, and human explanation synthesis."""

from ml.decision.schema import (
    DataQualityEvidence,
    DecisionExplanation,
    DecisionReasonCode,
    DecisionSeverity,
    EvidenceState,
    HybridDecision,
    HybridDecisionType,
    MLAnomalyEvidence,
    MultivariateEvidence,
    ObservationEvidence,
    SpatialEvidence,
    TemporalEvidence,
)
from ml.explainability.schema import (
    ContributionDirection,
    FeatureContribution,
    NeighborComparison,
)
from ml.explainability.synthesizer import ExplanationSynthesizer
from ml.spatial.schema import SpatialContextCategory


def test_evidence_hierarchy_4_tier_separation():
    """Test that direct, model, contextual, and operational evidence are strictly categorized."""
    synthesizer = ExplanationSynthesizer()

    ev = ObservationEvidence(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.88, ml_is_anomaly=True),
        temporal=TemporalEvidence(temp_rate_per_min=1.2, is_rate_abnormal=True),
        multivariate=MultivariateEvidence(),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.LOCAL_ONLY, valid_neighbor_count=3),
    )

    decision = HybridDecision(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        severity=DecisionSeverity.HIGH,
        reason_codes=[DecisionReasonCode.LOCAL_SPATIAL_ISOLATION, DecisionReasonCode.ML_HIGH_ANOMALY_SCORE],
        recommended_action="Inspect sensor hardware.",
        explanation=DecisionExplanation(summary="Sensor anomaly indicated."),
        evidence=ev,
    )

    contributions = [
        FeatureContribution(
            feature_name="temperature_rate_of_change",
            feature_value=1.2,
            contribution=0.25,
            direction=ContributionDirection.INCREASES_ANOMALY,
            rank=1,
        )
    ]

    hierarchy = synthesizer.build_evidence_hierarchy(decision, contributions)

    # 1. Direct evidence
    assert hierarchy.direct_evidence["station_id"] == "AWS_001"
    assert hierarchy.direct_evidence["timestamp"] == "2026-09-17T12:00:00Z"

    # 2. Model evidence
    assert hierarchy.model_evidence["normalized_anomaly_score"] == 0.88
    assert "temperature_rate_of_change" in hierarchy.model_evidence["top_feature_attributions"][0]
    assert "SHAP identifies the model features" in hierarchy.model_evidence["attribution_note"]

    # 3. Contextual evidence
    assert hierarchy.contextual_evidence["spatial_category"] == "LOCAL_ONLY"
    assert hierarchy.contextual_evidence["spatial_neighbors_active"] == 3
    assert hierarchy.contextual_evidence["temporal_rate_abnormal_flag"] is True

    # 4. Operational interpretation
    assert hierarchy.operational_interpretation == "probable sensor anomaly"


def test_genuine_event_scientific_phrasing():
    """Test that POSSIBLE_GENUINE_EVENT uses cautious regional phrasing and does not claim proof."""
    synthesizer = ExplanationSynthesizer()

    ev = ObservationEvidence(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        spatial=SpatialEvidence(context_category=SpatialContextCategory.REGIONAL_PATTERN, valid_neighbor_count=5),
        temporal=TemporalEvidence(is_rate_abnormal=True),
    )

    decision = HybridDecision(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        decision=HybridDecisionType.POSSIBLE_GENUINE_EVENT,
        severity=DecisionSeverity.LOW,
        reason_codes=[DecisionReasonCode.REGIONAL_SPATIAL_AGREEMENT, DecisionReasonCode.RAPID_RATE_OF_CHANGE],
        recommended_action="Compare regional observations.",
        explanation=DecisionExplanation(summary="Corroborated regional event."),
        evidence=ev,
    )

    summary = synthesizer.synthesize_summary(decision, [])
    assert "consistent with a regional event" in summary
    assert "definitely genuine" not in summary.lower()
    assert "proves" not in summary.lower()


def test_uncertain_explanation_clarity():
    """Test that UNCERTAIN explanations explicitly state why evidence is conflicting or sparse."""
    synthesizer = ExplanationSynthesizer()

    # Case A: Insufficient spatial context
    ev_sparse = ObservationEvidence(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.72),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.INSUFFICIENT_CONTEXT, valid_neighbor_count=0),
    )
    dec_sparse = HybridDecision(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        decision=HybridDecisionType.UNCERTAIN,
        severity=DecisionSeverity.MEDIUM,
        reason_codes=[DecisionReasonCode.INSUFFICIENT_SPATIAL_CONTEXT, DecisionReasonCode.CONFLICTING_EVIDENCE],
        recommended_action="Collect additional observations.",
        explanation=DecisionExplanation(summary="Uncertain evaluation."),
        evidence=ev_sparse,
    )
    summary_sparse = synthesizer.synthesize_summary(dec_sparse, [])
    assert "spatial neighborhood telemetry is insufficient" in summary_sparse

    # Case B: Conflicting evidence
    ev_conflict = ObservationEvidence(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.68),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.REGIONAL_PATTERN, valid_neighbor_count=4),
    )
    dec_conflict = HybridDecision(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        decision=HybridDecisionType.UNCERTAIN,
        severity=DecisionSeverity.LOW,
        reason_codes=[DecisionReasonCode.CONFLICTING_EVIDENCE],
        recommended_action="Review field logs.",
        explanation=DecisionExplanation(summary="Conflicting evidence."),
        evidence=ev_conflict,
    )
    summary_conflict = synthesizer.synthesize_summary(dec_conflict, [])
    assert "Conflicting evidence" in summary_conflict


def test_data_quality_investigation_steps():
    """Test that data quality issues recommend pipeline verification rather than sensor replacement."""
    synthesizer = ExplanationSynthesizer()

    ev_dq = ObservationEvidence(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        data_quality=DataQualityEvidence(
            quality_status="GAP",
            missing_fields=["temperature_c", "relative_humidity"],
            communication_gap_minutes=45.0,
        ),
    )
    dec_dq = HybridDecision(
        station_id="AWS_001",
        timestamp="2026-09-17T12:00:00Z",
        decision=HybridDecisionType.PROBABLE_DATA_QUALITY_ISSUE,
        severity=DecisionSeverity.HIGH,
        reason_codes=[DecisionReasonCode.DATA_GAP, DecisionReasonCode.MISSING_REQUIRED_VARIABLES],
        recommended_action="Check telemetry link.",
        explanation=DecisionExplanation(summary="Telemetry ingestion failure."),
        evidence=ev_dq,
    )

    steps = synthesizer.generate_investigation_steps(dec_dq)
    steps_text = " ".join(steps).lower()
    assert "telemetry link" in steps_text or "buffer queue" in steps_text
    assert "pipeline health" in steps_text
