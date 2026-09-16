"""Unit tests for Imputation and Correction Schemas and Immutability."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from ml.imputation.schema import (
    CorrectionAuditMetadata,
    CorrectionRecommendation,
    EstimationMethod,
    ImputationRecord,
    ImputationStatus,
    MethodQuality,
    MultivariateCorrectionBundle,
    RecommendationStatus,
    UncertaintyEstimate,
)


def test_uncertainty_estimate_schema():
    unc = UncertaintyEstimate(
        estimate_range=(25.1, 28.3),
        standard_error=0.81,
        absolute_deviation=1.5,
        supporting_neighbor_count=3,
        method_quality=MethodQuality.HIGH,
        confidence_index=0.85,
        notes=["Test uncertainty note."],
    )
    assert unc.estimate_range == (25.1, 28.3)
    assert unc.method_quality == MethodQuality.HIGH
    assert unc.supporting_neighbor_count == 3
    assert unc.confidence_index == 0.85
    assert len(unc.notes) == 1

    # Immutability check
    with pytest.raises(ValidationError):
        unc.confidence_index = 0.99  # type: ignore


def test_imputation_record_schema():
    rec = ImputationRecord(
        station_id="STN_001",
        timestamp="2026-09-17T00:00:00+00:00",
        target_variable="temperature_c",
        original_value=None,
        imputed_value=24.5,
        status=ImputationStatus.IMPUTED,
        method=EstimationMethod.CAUSAL_TEMPORAL_INTERPOLATION,
        reason="Causal interpolation from preceding 3 steps.",
        gap_duration_minutes=15.0,
        consecutive_missing_steps=3,
        is_causal=True,
    )
    assert rec.station_id == "STN_001"
    assert rec.status == ImputationStatus.IMPUTED
    assert rec.imputed_value == 24.5
    assert rec.gap_duration_minutes == 15.0
    assert rec.is_causal is True

    # Immutability
    with pytest.raises(ValidationError):
        rec.imputed_value = 25.0  # type: ignore


def test_correction_recommendation_schema():
    rec = CorrectionRecommendation(
        observation_id="hash12345",
        station_id="STN_002",
        timestamp="2026-09-17T00:05:00+00:00",
        target_variable="temperature_c",
        observed_value=55.0,
        recommended_value=28.4,
        status=RecommendationStatus.CORRECTION_CANDIDATE,
        method=EstimationMethod.COMBINED_TEMPORAL_SPATIAL,
        decision_type="PROBABLE_SENSOR_ANOMALY",
        reason_codes=["LOCAL_SPATIAL_ISOLATION", "RAPID_RATE_OF_CHANGE"],
        supporting_evidence=["Spatial IDW consensus estimate."],
        operator_summary="Recommended estimate 28.4°C based on neighbor consensus.",
        station_health_score=45.0,
        station_health_band="DEGRADED",
    )
    assert rec.observed_value == 55.0
    assert rec.recommended_value == 28.4
    assert rec.status == RecommendationStatus.CORRECTION_CANDIDATE
    assert rec.station_health_score == 45.0

    # Immutability
    with pytest.raises(ValidationError):
        rec.recommended_value = 30.0  # type: ignore


def test_multivariate_bundle_schema():
    rec_t = CorrectionRecommendation(
        observation_id="t1",
        station_id="STN_001",
        timestamp="2026-09-17T00:00:00+00:00",
        target_variable="temperature_c",
        observed_value=55.0,
        recommended_value=28.0,
        status=RecommendationStatus.CORRECTION_CANDIDATE,
        method=EstimationMethod.SPATIAL_IDW_CONSENSUS,
        decision_type="PROBABLE_SENSOR_ANOMALY",
        operator_summary="Temperature candidate.",
    )
    bundle = MultivariateCorrectionBundle(
        station_id="STN_001",
        timestamp="2026-09-17T00:00:00+00:00",
        recommendations={"temperature_c": rec_t},
        is_jointly_consistent=True,
    )
    assert bundle.is_jointly_consistent is True
    assert "temperature_c" in bundle.recommendations
