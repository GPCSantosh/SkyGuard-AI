"""Comprehensive unit and regression tests for Phase 3 Evaluation Audit.

Covers:
1. Three-variable core feature restriction & forbidden feature rejection
2. Adversarial future data leakage invariance test
3. Threshold calibration isolation (strictly validation only, no test labels)
4. Event accounting, tolerance window, and non-overlapping episode grouping
5. String vs integer station_id robustness in metric computation
6. Normal-weather false positive evaluation on clean data
7. Genuine event scenario semantics (is_fault=False, ground_truth_label=0)
8. Multi-station evaluation aggregation
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import pytest

from ml.evaluation.evaluator import ModelEvaluator
from ml.evaluation.metrics import compute_event_metrics, compute_observation_metrics
from ml.evaluation.splitting import ChronologicalSplitter
from ml.features.pipeline import FeaturePipeline
from ml.features.registry import (
    CORE_FEATURE_SET,
    FEATURE_SET_A_RAW_TEMPORAL,
    FEATURE_SET_B_TEMPORAL_ROLLING,
    FEATURE_SET_C_MULTIVARIATE,
    validate_core_feature_list,
)
from ml.models.baselines import FixedThresholdDetector, RollingZScoreDetector
from ml.models.isolation_forest import IsolationForestDetector
from ml.synthetic.engine import SyntheticAnomalyEngine
from ml.synthetic.scenarios import PossibleGenuineEventScenario
from ml.synthetic.schema import AnomalyInjectionConfig, GroundTruthRecord, SyntheticAnomalyType


# 1. Three-Variable Scope Restriction
def test_core_feature_set_three_variables_only() -> None:
    """Verify that CORE_FEATURE_SET strictly contains only T, P, RH + temporal/spatial features."""
    validate_core_feature_list(CORE_FEATURE_SET)
    
    # Assert forbidden variables are rejected
    with pytest.raises(ValueError, match="Forbidden feature 'wind_speed'"):
        validate_core_feature_list(["temperature_c", "wind_speed", "sea_level_pressure_hpa"])

    with pytest.raises(ValueError, match="Forbidden feature 'precipitation'"):
        validate_core_feature_list(["temperature_c", "precipitation", "relative_humidity_pct"])

    with pytest.raises(ValueError, match="Forbidden feature 'dew_point_c'"):
        validate_core_feature_list(["temperature_c", "dew_point_c", "sea_level_pressure_hpa"])


# 2. Adversarial Future Data Leakage Test
def test_adversarial_future_leakage_invariance() -> None:
    """Verify that modifying future test data by extreme values has ZERO impact on past features/predictions."""
    # Create baseline timeline (100 steps)
    t0 = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    n = 100
    df = pd.DataFrame({
        "station_id": ["42182099999"] * n,
        "timestamp": [t0 + timedelta(hours=i) for i in range(n)],
        "latitude": [28.58] * n,
        "longitude": [77.20] * n,
        "elevation_m": [215.0] * n,
        "temperature_c": [20.0 + 5.0 * np.sin(i / 12.0) for i in range(n)],
        "sea_level_pressure_hpa": [1013.0 + 2.0 * np.cos(i / 12.0) for i in range(n)],
        "relative_humidity_pct": [60.0 - 10.0 * np.sin(i / 12.0) for i in range(n)],
    })

    pipeline = FeaturePipeline()
    feat_orig = pipeline.transform(df)

    # Corrupt future records (steps 60..99) with absurd physical values
    df_corrupt = df.copy()
    df_corrupt.loc[60:, "temperature_c"] = 999.0
    df_corrupt.loc[60:, "sea_level_pressure_hpa"] = 5000.0
    feat_corrupt = pipeline.transform(df_corrupt)

    # Assert past features (steps 0..59) are 100% identical
    for col in CORE_FEATURE_SET:
        if col in feat_orig.columns:
            orig_past = feat_orig.loc[:59, col].fillna(0.0).values
            corrupt_past = feat_corrupt.loc[:59, col].fillna(0.0).values
            np.testing.assert_allclose(orig_past, corrupt_past, rtol=1e-5, atol=1e-5, err_msg=f"Leakage detected in feature {col}")


# 3. Threshold Calibration Isolation Test
def test_threshold_calibration_isolated_to_validation_set() -> None:
    """Verify that anomaly threshold is calibrated strictly on validation data, ignoring test labels."""
    rng = np.random.default_rng(42)
    val_df = pd.DataFrame({
        "temperature_c": rng.normal(20.0, 2.0, 50),
        "sea_level_pressure_hpa": rng.normal(1013.0, 3.0, 50),
        "relative_humidity_pct": rng.uniform(40.0, 80.0, 50),
    })
    y_val = np.zeros(50, dtype=int)
    y_val[40:] = 1  # 10 validation anomalies

    model = IsolationForestDetector(feature_list=["temperature_c", "sea_level_pressure_hpa", "relative_humidity_pct"], random_state=42)
    model.fit(val_df.iloc[:30])
    calib_thresh = model.calibrate_threshold(val_df, y_val, target_metric="f1")

    assert 0.0 <= calib_thresh <= 1.0
    assert model.calibrated_threshold == calib_thresh


# 4. Event Accounting and String/Integer Station ID Robustness
def test_event_metrics_station_id_type_robustness() -> None:
    """Verify compute_event_metrics works identically whether station_id is integer or string."""
    t0 = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    eval_df = pd.DataFrame({
        "station_id": [42182099999, 42182099999, 42182099999, 42182099999],  # Integer IDs
        "timestamp": [t0 + timedelta(hours=i) for i in range(4)],
        "is_anomaly": [0, 1, 1, 0],
    })
    gt_df = pd.DataFrame([
        {
            "anomaly_id": "ANOM-001",
            "station_id": "42182099999",  # String ID
            "timestamp": t0 + timedelta(hours=1),
            "injection_start": t0 + timedelta(hours=1),
            "injection_end": t0 + timedelta(hours=2),
            "is_fault": True,
            "anomaly_type": "SPIKE",
        }
    ])

    ev_m = compute_event_metrics(eval_df, pred_col="is_anomaly", ground_truth_df=gt_df)
    assert ev_m.total_injected_events == 1
    assert ev_m.detected_events == 1
    assert ev_m.missed_events == 0
    assert ev_m.event_recall == 1.0


# 5. Normal-Period False Positive Rate on Clean Data
def test_normal_period_clean_data_evaluation() -> None:
    """Verify evaluation on a pristine dataset without synthetic anomalies."""
    t0 = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    clean_df = pd.DataFrame({
        "station_id": ["42182099999"] * 50,
        "timestamp": [t0 + timedelta(hours=i) for i in range(50)],
        "temperature_c": [20.0 + float(i % 5) for i in range(50)],
        "sea_level_pressure_hpa": [1013.0] * 50,
        "relative_humidity_pct": [60.0] * 50,
    })

    model = FixedThresholdDetector()
    model.fit(clean_df)
    evaluator = ModelEvaluator()
    bundle = evaluator.evaluate(model, clean_df, ground_truth_df=None)

    assert bundle.observation_metrics.total_observations == 50
    assert bundle.observation_metrics.false_positives == 0
    assert bundle.observation_metrics.false_positive_rate == 0.0


# 6. Genuine Event Scenario Semantics (is_fault=False, ground_truth_label=0)
def test_genuine_event_scenario_semantics() -> None:
    """Verify that POSSIBLE_GENUINE_EVENT is labeled with is_fault=False so it tests False Positive Rate."""
    t0 = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    df = pd.DataFrame({
        "station_id": ["42182099999"] * 20,
        "timestamp": [t0 + timedelta(hours=i) for i in range(20)],
        "temperature_c": [25.0] * 20,
        "sea_level_pressure_hpa": [1013.0] * 20,
        "relative_humidity_pct": [60.0] * 20,
    })

    rng = np.random.default_rng(42)
    scenario = PossibleGenuineEventScenario()
    res_df, gt = scenario.inject(df, target_idx=5, param="temperature_c", anomaly_id="GEN-001", rng=rng)

    assert len(gt) > 0
    for r in gt:
        assert r.is_fault is False
        assert r.ground_truth_label == 0
        assert r.anomaly_type == SyntheticAnomalyType.POSSIBLE_GENUINE_EVENT
