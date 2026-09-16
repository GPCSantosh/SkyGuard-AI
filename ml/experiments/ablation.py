"""Feature ablation study runner comparing feature subsets A, B, C, and D."""

from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from ml.evaluation.evaluator import ModelEvaluator
from ml.evaluation.splitting import ChronologicalSplitter
from ml.features.pipeline import FeaturePipeline
from ml.features.registry import (
    FEATURE_SET_A_RAW_TEMPORAL,
    FEATURE_SET_B_TEMPORAL_ROLLING,
    FEATURE_SET_C_MULTIVARIATE,
    FEATURE_SET_D_SPATIAL,
)
from ml.models.isolation_forest import IsolationForestDetector
from ml.synthetic.engine import SyntheticAnomalyEngine
from ml.synthetic.schema import AnomalyInjectionConfig


def run_ablation_study(
    data_path: Union[str, Path],
    seed: int = 42,
    output_dir: Union[str, Path] = "experiments/reports",
) -> Dict[str, Any]:
    """Execute feature ablation across Sets A, B, C, and D."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df_raw = pd.read_csv(data_path)
    pipeline = FeaturePipeline()
    df_feat = pipeline.transform(df_raw)

    splitter = ChronologicalSplitter()
    split_res = splitter.split_by_ratio(df_feat)

    # Injections
    inj_val = SyntheticAnomalyEngine(AnomalyInjectionConfig(seed=seed, num_anomalies_per_type=1))
    val_res = inj_val.run_injection(split_res.val_df)

    inj_test = SyntheticAnomalyEngine(AnomalyInjectionConfig(seed=seed + 100, num_anomalies_per_type=2))
    test_res = inj_test.run_injection(split_res.test_df)

    y_val = np.zeros(len(val_res.modified_df), dtype=int)
    if not val_res.ground_truth_df.empty:
        fault_gt = val_res.ground_truth_df[val_res.ground_truth_df.get("is_fault", True) == True]
        val_tuples = set(zip(
            fault_gt["station_id"].astype(str),
            pd.to_datetime(fault_gt["timestamp"], utc=True)
        ))
        val_mod = val_res.modified_df.reset_index(drop=True)
        for i in range(len(val_mod)):
            stn = str(val_mod.iloc[i]["station_id"])
            t = pd.to_datetime(val_mod.iloc[i]["timestamp"], utc=True)
            if (stn, t) in val_tuples:
                y_val[i] = 1

    ablation_sets = {
        "Set_A_Raw_Temporal": FEATURE_SET_A_RAW_TEMPORAL,
        "Set_B_Temporal_Rolling": FEATURE_SET_B_TEMPORAL_ROLLING,
        "Set_C_Multivariate": FEATURE_SET_C_MULTIVARIATE,
        "Set_D_Spatial": FEATURE_SET_D_SPATIAL,
    }

    evaluator = ModelEvaluator()
    ablation_results: Dict[str, Any] = {}

    for set_name, f_list in ablation_sets.items():
        avail_features = [f for f in f_list if f in df_feat.columns]
        model = IsolationForestDetector(
            feature_list=avail_features,
            n_estimators=100,
            contamination=0.01,
            random_state=seed,
            model_id=f"iforest_ablation_{set_name.lower()}",
        )
        model.fit(split_res.train_df)
        model.calibrate_threshold(val_res.modified_df, y_val, target_metric="f1")

        eval_bundle = evaluator.evaluate(model, test_res.modified_df, test_res.ground_truth_df)
        obs_m = eval_bundle.observation_metrics
        ev_m = eval_bundle.event_metrics

        ablation_results[set_name] = {
            "num_features": len(avail_features),
            "precision": obs_m.precision,
            "recall": obs_m.recall,
            "f1_score": obs_m.f1_score,
            "false_positive_rate": obs_m.false_positive_rate,
            "event_recall": ev_m.event_recall,
            "mean_latency_minutes": ev_m.mean_detection_latency_minutes,
            "calibrated_threshold": model.calibrated_threshold,
        }

    report_file = out_dir / "ablation_study_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(ablation_results, f, indent=2)

    return ablation_results
