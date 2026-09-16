"""Multi-seed stability experiment harness evaluating model variance across random seeds."""

from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from typing import Any, Dict, List, Sequence, Union
import numpy as np
import pandas as pd

from ml.evaluation.evaluator import ModelEvaluator
from ml.evaluation.splitting import ChronologicalSplitter
from ml.features.pipeline import FeaturePipeline
from ml.features.registry import BASELINE_FEATURE_SET
from ml.models.isolation_forest import IsolationForestDetector
from ml.synthetic.engine import SyntheticAnomalyEngine
from ml.synthetic.schema import AnomalyInjectionConfig


def run_multi_seed_stability(
    data_path: Union[str, Path],
    seeds: Sequence[int] = (42, 123, 2026),
    output_dir: Union[str, Path] = "experiments/reports",
) -> Dict[str, Any]:
    """Execute model training and evaluation over multiple random seeds to measure metric stability."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df_raw = pd.read_csv(data_path)
    pipeline = FeaturePipeline()
    df_feat = pipeline.transform(df_raw)

    splitter = ChronologicalSplitter()
    split_res = splitter.split_by_ratio(df_feat)

    seed_runs: Dict[str, Dict[str, Any]] = {}
    f1_list: List[float] = []
    prec_list: List[float] = []
    rec_list: List[float] = []
    ev_rec_list: List[float] = []
    fpr_list: List[float] = []

    evaluator = ModelEvaluator()

    for seed in seeds:
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

        avail_features = [f for f in BASELINE_FEATURE_SET if f in df_feat.columns]
        model = IsolationForestDetector(
            feature_list=avail_features,
            n_estimators=100,
            contamination=0.01,
            random_state=seed,
            model_id=f"iforest_stability_s{seed}",
        )
        model.fit(split_res.train_df)
        model.calibrate_threshold(val_res.modified_df, y_val, target_metric="f1")

        eval_bundle = evaluator.evaluate(model, test_res.modified_df, test_res.ground_truth_df)
        obs_m = eval_bundle.observation_metrics
        ev_m = eval_bundle.event_metrics

        f1_list.append(obs_m.f1_score)
        prec_list.append(obs_m.precision)
        rec_list.append(obs_m.recall)
        ev_rec_list.append(ev_m.event_recall)
        fpr_list.append(obs_m.false_positive_rate)

        seed_runs[f"seed_{seed}"] = {
            "precision": obs_m.precision,
            "recall": obs_m.recall,
            "f1_score": obs_m.f1_score,
            "false_positive_rate": obs_m.false_positive_rate,
            "event_recall": ev_m.event_recall,
            "calibrated_threshold": model.calibrated_threshold,
        }

    summary = {
        "seeds_evaluated": list(seeds),
        "f1_score": {"mean": round(float(np.mean(f1_list)), 4), "std": round(float(np.std(f1_list)), 4)},
        "precision": {"mean": round(float(np.mean(prec_list)), 4), "std": round(float(np.std(prec_list)), 4)},
        "recall": {"mean": round(float(np.mean(rec_list)), 4), "std": round(float(np.std(rec_list)), 4)},
        "event_recall": {"mean": round(float(np.mean(ev_rec_list)), 4), "std": round(float(np.std(ev_rec_list)), 4)},
        "false_positive_rate": {"mean": round(float(np.mean(fpr_list)), 4), "std": round(float(np.std(fpr_list)), 4)},
        "individual_runs": seed_runs,
    }

    report_file = out_dir / "multi_seed_stability_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary
