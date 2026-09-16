"""High-level model evaluation harness across stations, taxonomies, and severities."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from ml.evaluation.metrics import (
    EvaluationMetricsBundle,
    EventMetrics,
    ObservationMetrics,
    compute_event_metrics,
    compute_observation_metrics,
)
from ml.models.base import BaseAnomalyModel


class ModelEvaluator:
    """Evaluates anomaly detection models across stations, anomaly categories, and severity tiers."""

    def __init__(
        self,
        timestamp_col: str = "timestamp",
        station_id_col: str = "station_id",
    ) -> None:
        self.timestamp_col = timestamp_col
        self.station_id_col = station_id_col

    def evaluate(
        self,
        model: BaseAnomalyModel,
        test_df: pd.DataFrame,
        ground_truth_df: Optional[pd.DataFrame] = None,
    ) -> EvaluationMetricsBundle:
        """Run complete multi-dimensional evaluation."""
        if test_df.empty:
            raise ValueError("Evaluation test_df cannot be empty.")

        # Compute predictions
        scores = model.score_samples(test_df)
        preds = (scores >= model.calibrated_threshold).astype(int)

        eval_df = test_df.copy().reset_index(drop=True)
        eval_df["anomaly_score"] = scores
        eval_df["is_anomaly"] = preds
        eval_df[self.timestamp_col] = pd.to_datetime(eval_df[self.timestamp_col], utc=True)
        eval_df[self.station_id_col] = eval_df[self.station_id_col].astype(str)

        # Build ground truth binary target vector aligned with eval_df
        y_true = np.zeros(len(eval_df), dtype=int)
        if ground_truth_df is not None and not ground_truth_df.empty:
            fault_gt = ground_truth_df[ground_truth_df.get("is_fault", True) == True]
            gt_tuples = set(zip(
                fault_gt[self.station_id_col].astype(str),
                pd.to_datetime(fault_gt[self.timestamp_col], utc=True),
            ))
            for i in range(len(eval_df)):
                row_stn = eval_df.iloc[i][self.station_id_col]
                row_ts = eval_df.iloc[i][self.timestamp_col]
                if (row_stn, row_ts) in gt_tuples:
                    y_true[i] = 1

        eval_df["y_true"] = y_true

        # 1. Overall Observation & Event Metrics
        obs_metrics = compute_observation_metrics(y_true, preds, anomaly_scores=scores)
        event_metrics = compute_event_metrics(
            eval_df=eval_df,
            pred_col="is_anomaly",
            ground_truth_df=ground_truth_df,
            timestamp_col=self.timestamp_col,
            station_id_col=self.station_id_col,
        )

        # 2. Station-level Metrics
        station_metrics: Dict[str, Dict[str, Any]] = {}
        for s_id, s_group in eval_df.groupby(self.station_id_col):
            s_y_true = s_group["y_true"].values
            s_preds = s_group["is_anomaly"].values
            s_obs_m = compute_observation_metrics(s_y_true, s_preds)

            has_gt_stn = (
                ground_truth_df is not None
                and not ground_truth_df.empty
                and self.station_id_col in ground_truth_df.columns
            )
            s_gt = ground_truth_df[ground_truth_df[self.station_id_col].astype(str) == str(s_id)] if has_gt_stn else None
            s_ev_m = compute_event_metrics(s_group, pred_col="is_anomaly", ground_truth_df=s_gt,
                                           timestamp_col=self.timestamp_col, station_id_col=self.station_id_col)
            station_metrics[str(s_id)] = {
                "observations": len(s_group),
                "injected_events": s_ev_m.total_injected_events,
                "detected_events": s_ev_m.detected_events,
                "missed_events": s_ev_m.missed_events,
                "event_recall": s_ev_m.event_recall,
                "false_positives": s_obs_m.false_positives,
                "precision": s_obs_m.precision,
                "recall": s_obs_m.recall,
                "f1_score": s_obs_m.f1_score,
            }

        # 3. Anomaly Taxonomy Breakdown
        taxonomy_metrics: Dict[str, Dict[str, Any]] = {}
        if ground_truth_df is not None and not ground_truth_df.empty and "anomaly_type" in ground_truth_df.columns:
            for anom_type, t_group in ground_truth_df.groupby("anomaly_type"):
                unique_events = t_group["anomaly_id"].unique()
                detected_cnt = 0
                for a_id in unique_events:
                    rows = t_group[t_group["anomaly_id"] == a_id]
                    stn = str(rows.iloc[0][self.station_id_col])
                    ts_list = pd.to_datetime(rows[self.timestamp_col], utc=True).tolist()
                    match = eval_df[
                        (eval_df[self.station_id_col].astype(str) == stn)
                        & (eval_df[self.timestamp_col].isin(ts_list))
                        & (eval_df["is_anomaly"] == 1)
                    ]
                    if not match.empty:
                        detected_cnt += 1

                tot_events = len(unique_events)
                t_recall = detected_cnt / tot_events if tot_events > 0 else 0.0
                taxonomy_metrics[str(anom_type)] = {
                    "injected_events": tot_events,
                    "detected_events": detected_cnt,
                    "missed_events": tot_events - detected_cnt,
                    "event_recall": round(t_recall, 4),
                }

        # 4. Severity Tier Breakdown
        severity_metrics: Dict[str, Dict[str, Any]] = {"subtle": {}, "moderate": {}, "obvious": {}}
        if ground_truth_df is not None and not ground_truth_df.empty:
            fault_records = ground_truth_df[ground_truth_df.get("is_fault", True) == True].copy()
            for idx, r in fault_records.iterrows():
                orig = r.get("original_value")
                mod = r.get("modified_value")
                delta = abs(mod - orig) if orig is not None and mod is not None else 3.0

                if delta <= 2.0 or r.get("anomaly_type") == "SMALL_SPIKE":
                    tier = "subtle"
                elif delta <= 5.0:
                    tier = "moderate"
                else:
                    tier = "obvious"
                fault_records.at[idx, "_tier"] = tier

            for tier_name in ["subtle", "moderate", "obvious"]:
                tier_rows = fault_records[fault_records.get("_tier") == tier_name]
                if not tier_rows.empty:
                    u_events = tier_rows["anomaly_id"].unique()
                    det = 0
                    for a_id in u_events:
                        a_rows = tier_rows[tier_rows["anomaly_id"] == a_id]
                        stn = str(a_rows.iloc[0][self.station_id_col])
                        ts = pd.to_datetime(a_rows[self.timestamp_col], utc=True).tolist()
                        match = eval_df[(eval_df[self.station_id_col].astype(str) == stn) & (eval_df[self.timestamp_col].isin(ts)) & (eval_df["is_anomaly"] == 1)]
                        if not match.empty:
                            det += 1
                    tot = len(u_events)
                    severity_metrics[tier_name] = {
                        "events": tot,
                        "detected": det,
                        "recall": round(det / tot if tot > 0 else 0.0, 4),
                    }

        # 5. Genuine Weather Event Analysis (False Positive Check)
        genuine_event_summary: Dict[str, Any] = {}
        if ground_truth_df is not None and not ground_truth_df.empty and "anomaly_type" in ground_truth_df.columns:
            if "POSSIBLE_GENUINE_EVENT" in ground_truth_df["anomaly_type"].values:
                gen_rows = ground_truth_df[ground_truth_df["anomaly_type"] == "POSSIBLE_GENUINE_EVENT"]
                gen_ts = pd.to_datetime(gen_rows[self.timestamp_col], utc=True).tolist()
                gen_eval = eval_df[eval_df[self.timestamp_col].isin(gen_ts)]
            if not gen_eval.empty:
                flagged_count = int(np.sum(gen_eval["is_anomaly"] == 1))
                mean_score = float(np.mean(gen_eval["anomaly_score"]))
                genuine_event_summary = {
                    "evaluated_records": len(gen_eval),
                    "flagged_as_anomaly": flagged_count,
                    "false_alarm_rate": round(flagged_count / len(gen_eval), 4),
                    "mean_anomaly_score": round(mean_score, 4),
                    "calibrated_threshold": model.calibrated_threshold,
                    "interpretation": "Baseline unsupervised models flag extreme genuine events unless spatial context is checked.",
                }

        return EvaluationMetricsBundle(
            model_id=model.model_id,
            observation_metrics=obs_metrics,
            event_metrics=event_metrics,
            station_metrics=station_metrics,
            taxonomy_metrics=taxonomy_metrics,
            severity_metrics=severity_metrics,
            genuine_event_summary=genuine_event_summary,
        )
