"""Comprehensive edge case unit tests for anomaly detection models and evaluation pipelines."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.evaluation.evaluator import ModelEvaluator
from ml.models.baselines import FixedThresholdDetector, RollingZScoreDetector
from ml.models.isolation_forest import IsolationForestDetector


def test_edge_case_1_very_small_training_dataset() -> None:
    df_tiny = pd.DataFrame({
        "temperature_c": [20.0, 21.0, 22.0],
        "relative_humidity_pct": [50.0, 51.0, 52.0],
        "sea_level_pressure_hpa": [1013.0, 1013.1, 1013.2],
    })
    model = IsolationForestDetector(feature_list=["temperature_c", "relative_humidity_pct"], n_estimators=10)
    model.fit(df_tiny)
    assert model.is_fitted is True
    scores = model.score_samples(df_tiny)
    assert len(scores) == 3


def test_edge_case_3_all_features_constant() -> None:
    df_const = pd.DataFrame({
        "temperature_c": [25.0] * 20,
        "relative_humidity_pct": [50.0] * 20,
        "sea_level_pressure_hpa": [1013.0] * 20,
    })
    model = IsolationForestDetector(feature_list=["temperature_c", "relative_humidity_pct"])
    model.fit(df_const)
    scores = model.score_samples(df_const)
    assert len(scores) == 20
    assert not np.any(np.isnan(scores))


def test_edge_case_4_5_6_missing_nans_and_inf_features() -> None:
    df_clean = pd.DataFrame({
        "temperature_c": [20.0, 22.0, 24.0, 26.0, 28.0],
        "relative_humidity_pct": [50.0, 52.0, 54.0, 56.0, 58.0],
        "sea_level_pressure_hpa": [1013.0, 1013.0, 1013.0, 1013.0, 1013.0],
    })
    model = IsolationForestDetector(feature_list=["temperature_c", "relative_humidity_pct", "extra_missing_feature"])
    model.fit(df_clean)

    # Test with NaNs and Infs
    df_corrupt = pd.DataFrame({
        "temperature_c": [20.0, np.nan, np.inf, -np.inf, 28.0],
        "relative_humidity_pct": [50.0, np.nan, 55.0, 60.0, np.nan],
    })
    scores = model.score_samples(df_corrupt)
    assert len(scores) == 5
    assert not np.any(np.isnan(scores))
    assert not np.any(np.isinf(scores))


def test_edge_case_15_test_period_no_anomalies() -> None:
    test_df = pd.DataFrame({
        "station_id": ["STN_01"] * 10,
        "timestamp": pd.date_range("2024-01-01", periods=10, freq="1h", tz="UTC"),
        "temperature_c": [20.0] * 10,
        "relative_humidity_pct": [50.0] * 10,
        "sea_level_pressure_hpa": [1013.0] * 10,
    })
    model = FixedThresholdDetector()
    evaluator = ModelEvaluator()
    # Empty ground truth -> 0 anomalies
    res = evaluator.evaluate(model, test_df, ground_truth_df=pd.DataFrame())
    assert res.observation_metrics.total_observations == 10
    assert res.observation_metrics.true_positives == 0
    assert res.observation_metrics.false_positives == 0
    assert res.event_metrics.total_injected_events == 0


def test_edge_case_16_test_period_only_anomalies() -> None:
    timestamps = pd.date_range("2024-01-01", periods=5, freq="1h", tz="UTC")
    test_df = pd.DataFrame({
        "station_id": ["STN_01"] * 5,
        "timestamp": timestamps,
        "temperature_c": [80.0] * 5,  # All out of bounds (> 60)
        "relative_humidity_pct": [50.0] * 5,
        "sea_level_pressure_hpa": [1013.0] * 5,
    })
    gt_df = pd.DataFrame([
        {"anomaly_id": f"A{i}", "station_id": "STN_01", "timestamp": timestamps[i], "injection_start": timestamps[i], "is_fault": True}
        for i in range(5)
    ])
    model = FixedThresholdDetector()
    evaluator = ModelEvaluator()
    res = evaluator.evaluate(model, test_df, ground_truth_df=gt_df)
    assert res.observation_metrics.total_observations == 5
    assert res.observation_metrics.true_positives == 5
    assert res.observation_metrics.recall == 1.0


def test_edge_case_17_18_threshold_extremes() -> None:
    test_df = pd.DataFrame({
        "station_id": ["STN_01"] * 5,
        "timestamp": pd.date_range("2024-01-01", periods=5, freq="1h", tz="UTC"),
        "temperature_c": [20.0, 22.0, 24.0, 26.0, 28.0],
        "relative_humidity_pct": [50.0, 52.0, 54.0, 56.0, 58.0],
        "sea_level_pressure_hpa": [1013.0] * 5,
    })
    model = IsolationForestDetector(feature_list=["temperature_c", "relative_humidity_pct"])
    model.fit(test_df)

    # Threshold 1.1 -> produces zero detections
    model.calibrated_threshold = 1.1
    preds_zero = model.predict(test_df)
    assert np.all(preds_zero == 0)

    # Threshold -0.1 -> produces all detections
    model.calibrated_threshold = -0.1
    preds_all = model.predict(test_df)
    assert np.all(preds_all == 1)
