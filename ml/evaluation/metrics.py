"""Observation-level, event-level, and latency evaluation metrics for SkyGuard AI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from sklearn.metrics import average_precision_score, roc_auc_score


class ObservationMetrics(BaseModel):
    """Observation-level classification metrics."""
    model_config = ConfigDict(frozen=True)

    total_observations: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    false_negative_rate: float
    pr_auc: Optional[float] = None
    roc_auc: Optional[float] = None


class EventMetrics(BaseModel):
    """Event-level episode detection metrics."""
    model_config = ConfigDict(frozen=True)

    total_injected_events: int
    detected_events: int
    missed_events: int
    event_recall: float
    mean_detection_latency_steps: float
    mean_detection_latency_minutes: float
    false_alarm_events: int
    false_alarms_per_station_day: float


class EvaluationMetricsBundle(BaseModel):
    """Unified container for all evaluation metrics."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    model_id: str
    observation_metrics: ObservationMetrics
    event_metrics: EventMetrics
    station_metrics: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    taxonomy_metrics: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    severity_metrics: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    genuine_event_summary: Dict[str, Any] = Field(default_factory=dict)


def compute_observation_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    anomaly_scores: Optional[np.ndarray] = None,
) -> ObservationMetrics:
    """Calculate observation-level classification metrics."""
    y_t = np.asarray(y_true, dtype=int)
    y_p = np.asarray(y_pred, dtype=int)

    tp = int(np.sum((y_p == 1) & (y_t == 1)))
    fp = int(np.sum((y_p == 1) & (y_t == 0)))
    tn = int(np.sum((y_p == 0) & (y_t == 0)))
    fn = int(np.sum((y_p == 0) & (y_t == 1)))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    pr_auc_val = None
    roc_auc_val = None
    if anomaly_scores is not None and len(np.unique(y_t)) > 1:
        try:
            pr_auc_val = float(average_precision_score(y_t, anomaly_scores))
            roc_auc_val = float(roc_auc_score(y_t, anomaly_scores))
        except Exception:
            pass

    return ObservationMetrics(
        total_observations=len(y_t),
        true_positives=tp,
        false_positives=fp,
        true_negatives=tn,
        false_negatives=fn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1_score=round(f1, 4),
        false_positive_rate=round(fpr, 4),
        false_negative_rate=round(fnr, 4),
        pr_auc=round(pr_auc_val, 4) if pr_auc_val is not None else None,
        roc_auc=round(roc_auc_val, 4) if roc_auc_val is not None else None,
    )


def compute_event_metrics(
    eval_df: pd.DataFrame,
    pred_col: str = "is_anomaly",
    ground_truth_df: Optional[pd.DataFrame] = None,
    timestamp_col: str = "timestamp",
    station_id_col: str = "station_id",
) -> EventMetrics:
    """Calculate event-level detection rates and latency."""
    if ground_truth_df is None or ground_truth_df.empty:
        return EventMetrics(
            total_injected_events=0,
            detected_events=0,
            missed_events=0,
            event_recall=0.0,
            mean_detection_latency_steps=0.0,
            mean_detection_latency_minutes=0.0,
            false_alarm_events=0,
            false_alarms_per_station_day=0.0,
        )

    # Filter fault ground truth events (is_fault=True)
    fault_gt = ground_truth_df[ground_truth_df.get("is_fault", True) == True]
    unique_event_ids = fault_gt["anomaly_id"].unique()
    total_events = len(unique_event_ids)

    detected_events_count = 0
    latencies_steps: List[int] = []
    latencies_mins: List[float] = []

    # Map timestamps to predictions with guaranteed string station_id matching
    eval_df_copy = eval_df.copy()
    eval_df_copy[timestamp_col] = pd.to_datetime(eval_df_copy[timestamp_col], utc=True)
    eval_df_copy[station_id_col] = eval_df_copy[station_id_col].astype(str)
    pred_map = eval_df_copy.set_index([station_id_col, timestamp_col])[pred_col].to_dict()

    for anom_id in unique_event_ids:
        anom_rows = fault_gt[fault_gt["anomaly_id"] == anom_id].sort_values(by="timestamp")
        stn = str(anom_rows.iloc[0][station_id_col])
        start_time = pd.to_datetime(anom_rows.iloc[0]["injection_start"], utc=True)

        is_detected = False
        first_detect_time = None
        step_idx = 0

        for _, row in anom_rows.iterrows():
            t = pd.to_datetime(row[timestamp_col], utc=True)
            pred = pred_map.get((stn, t), 0)
            if pred == 1:
                is_detected = True
                first_detect_time = t
                break
            step_idx += 1

        if is_detected:
            detected_events_count += 1
            latencies_steps.append(step_idx)
            latency_min = max(0.0, (first_detect_time - start_time).total_seconds() / 60.0)
            latencies_mins.append(latency_min)

    missed_events_count = total_events - detected_events_count
    event_recall = detected_events_count / total_events if total_events > 0 else 0.0

    mean_lat_steps = float(np.mean(latencies_steps)) if latencies_steps else 0.0
    mean_lat_mins = float(np.mean(latencies_mins)) if latencies_mins else 0.0

    # False alarm event calculation: count continuous spans of false alarms in clean periods
    clean_obs = eval_df_copy[~eval_df_copy[timestamp_col].isin(pd.to_datetime(fault_gt["timestamp"], utc=True))]
    false_alarm_events = 0
    if not clean_obs.empty and pred_col in clean_obs.columns:
        # Count rising edges of false alarms
        fa_preds = clean_obs[pred_col].values
        rising_edges = np.diff(np.pad(fa_preds, (1, 0), "constant")) == 1
        false_alarm_events = int(np.sum(rising_edges))

    # Calculate days observed
    t_min = eval_df_copy[timestamp_col].min()
    t_max = eval_df_copy[timestamp_col].max()
    days_span = max(1.0, (t_max - t_min).total_seconds() / 86400.0)
    station_count = max(1, eval_df_copy[station_id_col].nunique())
    fa_per_station_day = false_alarm_events / (station_count * days_span)

    return EventMetrics(
        total_injected_events=total_events,
        detected_events=detected_events_count,
        missed_events=missed_events_count,
        event_recall=round(event_recall, 4),
        mean_detection_latency_steps=round(mean_lat_steps, 2),
        mean_detection_latency_minutes=round(mean_lat_mins, 2),
        false_alarm_events=false_alarm_events,
        false_alarms_per_station_day=round(fa_per_station_day, 4),
    )
