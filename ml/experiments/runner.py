"""Main experiment runner executing baseline training, calibration, and evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
import yaml

from ml.evaluation.evaluator import ModelEvaluator
from ml.evaluation.splitting import ChronologicalSplitter
from ml.features.pipeline import FeaturePipeline
from ml.features.registry import BASELINE_FEATURE_SET
from ml.models.baselines import FixedThresholdDetector, RollingZScoreDetector
from ml.models.isolation_forest import IsolationForestDetector
from ml.synthetic.engine import SyntheticAnomalyEngine
from ml.synthetic.schema import AnomalyInjectionConfig


def run_full_experiment(
    data_path: Union[str, Path],
    output_dir: Union[str, Path] = "experiments",
    seed: int = 42,
    contamination: float = 0.01,
) -> Dict[str, Any]:
    """Execute complete end-to-end baseline modeling, injection, calibration, and evaluation."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    models_dir = Path("models/registry")
    models_dir.mkdir(parents=True, exist_ok=True)

    df_raw = pd.read_csv(data_path)
    print(f"[+] Loaded baseline dataset: {len(df_raw):,} rows from {data_path}")

    # 1. Feature Engineering
    pipeline = FeaturePipeline()
    df_feat = pipeline.transform(df_raw)
    print(f"[+] Computed feature matrix: {df_feat.shape[1]} total columns.")

    # 2. Chronological Splitting (60% Train, 20% Val, 20% Test)
    splitter = ChronologicalSplitter(train_ratio=0.6, val_ratio=0.2, test_ratio=0.2)
    split_res = splitter.split_by_ratio(df_feat)
    print(f"\n{split_res.summary()}\n")

    # 3. Clean Training Data (Normal baseline only)
    train_df = split_res.train_df.copy()

    # 4. Synthetic Injection on Validation and Test Sets
    inj_cfg_val = AnomalyInjectionConfig(seed=seed, experiment_id=f"VAL_SEED_{seed}", num_anomalies_per_type=1)
    inj_engine_val = SyntheticAnomalyEngine(config=inj_cfg_val)
    val_inj_res = inj_engine_val.run_injection(split_res.val_df)

    inj_cfg_test = AnomalyInjectionConfig(seed=seed + 100, experiment_id=f"TEST_SEED_{seed}", num_anomalies_per_type=2)
    inj_engine_test = SyntheticAnomalyEngine(config=inj_cfg_test)
    test_inj_res = inj_engine_test.run_injection(split_res.test_df)

    print(f"[+] Validation Anomaly Events: {len(val_inj_res.ground_truth_df):,}")
    print(f"[+] Test Anomaly Events:       {len(test_inj_res.ground_truth_df):,}")

    # 5. Model Training & Threshold Calibration
    # A. Fixed Threshold
    m_fixed = FixedThresholdDetector(model_id=f"fixed_threshold_s{seed}")
    m_fixed.fit(train_df)

    # B. Rolling Z-Score
    m_zscore = RollingZScoreDetector(z_threshold=3.0, model_id=f"rolling_zscore_s{seed}")
    m_zscore.fit(train_df)

    # C. Isolation Forest
    m_iforest = IsolationForestDetector(
        feature_list=BASELINE_FEATURE_SET,
        n_estimators=100,
        contamination=contamination,
        random_state=seed,
        model_id=f"isolation_forest_s{seed}",
    )
    m_iforest.fit(train_df)

    # Calibrate on validation set (station-aware ground truth matching)
    y_val = np.zeros(len(val_inj_res.modified_df), dtype=int)
    if not val_inj_res.ground_truth_df.empty:
        fault_gt = val_inj_res.ground_truth_df[val_inj_res.ground_truth_df.get("is_fault", True) == True]
        val_tuples = set(zip(
            fault_gt["station_id"].astype(str),
            pd.to_datetime(fault_gt["timestamp"], utc=True)
        ))
        val_mod = val_inj_res.modified_df.reset_index(drop=True)
        for i in range(len(val_mod)):
            stn = str(val_mod.iloc[i]["station_id"])
            t = pd.to_datetime(val_mod.iloc[i]["timestamp"], utc=True)
            if (stn, t) in val_tuples:
                y_val[i] = 1

    thresh_z = m_zscore.calibrate_threshold(val_inj_res.modified_df, y_val, target_metric="f1")
    thresh_if = m_iforest.calibrate_threshold(val_inj_res.modified_df, y_val, target_metric="f1")
    print(f"[+] Calibrated Thresholds -> Rolling Z-Score: {thresh_z:.4f}, Isolation Forest: {thresh_if:.4f}")

    # Save model artifact
    m_iforest.save(models_dir)
    print(f"[+] Serialized Isolation Forest artifact to: {models_dir}")

    # 6. Normal-Weather False Positive Evaluation (Clean uncorrupted test partition)
    evaluator = ModelEvaluator()
    res_clean_normal = evaluator.evaluate(m_iforest, split_res.test_df, ground_truth_df=None)
    clean_obs_count = len(split_res.test_df)
    clean_fp = int(np.sum(res_clean_normal.observation_metrics.false_positives))
    clean_fpr = res_clean_normal.observation_metrics.false_positive_rate
    clean_fa_rate = res_clean_normal.event_metrics.false_alarms_per_station_day

    # 7. Evaluation on Corrupted Test Set
    res_fixed = evaluator.evaluate(m_fixed, test_inj_res.modified_df, test_inj_res.ground_truth_df)
    res_zscore = evaluator.evaluate(m_zscore, test_inj_res.modified_df, test_inj_res.ground_truth_df)
    res_iforest = evaluator.evaluate(m_iforest, test_inj_res.modified_df, test_inj_res.ground_truth_df)

    # Event accounting details
    gt_df = test_inj_res.ground_truth_df
    total_events = gt_df["anomaly_id"].nunique() if not gt_df.empty else 0
    total_affected_obs = len(gt_df) if not gt_df.empty else 0
    
    # Check for timestamp collisions across different anomaly IDs
    overlapping_events_count = 0
    if not gt_df.empty:
        ts_station_counts = gt_df.groupby(["station_id", "timestamp"])["anomaly_id"].nunique()
        overlapping_events_count = int(np.sum(ts_station_counts > 1))

    # Export metrics JSON
    summary_report = {
        "dataset_split": {
            "train_rows": len(split_res.train_df),
            "val_rows": len(split_res.val_df),
            "test_rows": len(split_res.test_df),
            "train_dates": [str(split_res.train_start), str(split_res.train_end)],
            "val_dates": [str(split_res.val_start), str(split_res.val_end)],
            "test_dates": [str(split_res.test_start), str(split_res.test_end)],
            "stations_evaluated": list(df_raw["station_id"].astype(str).unique()),
        },
        "event_accounting": {
            "total_injected_events": total_events,
            "total_affected_observations": total_affected_obs,
            "mean_observations_per_event": round(total_affected_obs / total_events, 2) if total_events > 0 else 0,
            "overlapping_event_timestamps": overlapping_events_count,
        },
        "normal_weather_false_alarms": {
            "clean_test_observations": clean_obs_count,
            "false_positives": clean_fp,
            "false_positive_rate": clean_fpr,
            "false_alarms_per_station_day": clean_fa_rate,
        },
        "models": {
            "FixedThreshold": res_fixed.model_dump(),
            "RollingZScore": res_zscore.model_dump(),
            "IsolationForest": res_iforest.model_dump(),
        }
    }

    report_path = out_dir / f"baseline_experiment_report_s{seed}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    print(f"[+] Exported experiment report to: {report_path}")
    return summary_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SkyGuard AI — Phase 3 Experiment Harness")
    parser.add_argument("--data", type=str, default="data/processed/benchmark_multistation_2024.csv")
    parser.add_argument("--output-dir", type=str, default="experiments/reports")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    run_full_experiment(args.data, output_dir=args.output_dir, seed=args.seed)

