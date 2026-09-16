"""Unit tests for observation-level, event-level, and latency evaluation metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.evaluation.evaluator import ModelEvaluator
from ml.evaluation.metrics import compute_event_metrics, compute_observation_metrics
from ml.models.baselines import FixedThresholdDetector


def test_compute_observation_metrics_perfect_and_imperfect() -> None:
    # Perfect predictions
    y_true = np.array([0, 0, 1, 1, 0, 1])
    y_pred = np.array([0, 0, 1, 1, 0, 1])
    m = compute_observation_metrics(y_true, y_pred)
    assert m.precision == 1.0
    assert m.recall == 1.0
    assert m.f1_score == 1.0
    assert m.false_positive_rate == 0.0

    # 1 FP and 1 FN
    y_true2 = np.array([0, 0, 1, 1])
    y_pred2 = np.array([0, 1, 1, 0])
    m2 = compute_observation_metrics(y_true2, y_pred2)
    assert m2.true_positives == 1
    assert m2.false_positives == 1
    assert m2.false_negatives == 1
    assert m2.precision == 0.5
    assert m2.recall == 0.5


def test_compute_event_metrics_and_latency() -> None:
    # 2 Events: Event 1 detected on step 2 (latency = 10 mins); Event 2 missed
    timestamps = pd.date_range("2024-01-01 00:00:00", periods=10, freq="5min", tz="UTC")
    eval_df = pd.DataFrame({
        "station_id": ["STN_A"] * 10,
        "timestamp": timestamps,
        "is_anomaly": [0, 0, 1, 0, 0, 0, 0, 0, 0, 0],  # Alert at row 2 (00:10)
    })

    # Ground truth
    gt_df = pd.DataFrame([
        # Event 1 (00:00 to 00:15)
        {"anomaly_id": "EV1", "station_id": "STN_A", "timestamp": timestamps[0], "injection_start": timestamps[0], "is_fault": True},
        {"anomaly_id": "EV1", "station_id": "STN_A", "timestamp": timestamps[1], "injection_start": timestamps[0], "is_fault": True},
        {"anomaly_id": "EV1", "station_id": "STN_A", "timestamp": timestamps[2], "injection_start": timestamps[0], "is_fault": True},
        # Event 2 (00:30 to 00:40) - missed
        {"anomaly_id": "EV2", "station_id": "STN_A", "timestamp": timestamps[6], "injection_start": timestamps[6], "is_fault": True},
        {"anomaly_id": "EV2", "station_id": "STN_A", "timestamp": timestamps[7], "injection_start": timestamps[6], "is_fault": True},
    ])

    ev_m = compute_event_metrics(eval_df, ground_truth_df=gt_df)
    assert ev_m.total_injected_events == 2
    assert ev_m.detected_events == 1
    assert ev_m.missed_events == 1
    assert ev_m.event_recall == 0.5
    assert ev_m.mean_detection_latency_minutes == 10.0
