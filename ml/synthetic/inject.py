"""CLI entry point for running reproducible synthetic anomaly injection experiments.

Usage:
    python -m ml.synthetic.inject \
        --input data/processed/42182099999_2024_normalized.csv \
        --output-dir data/experiments/injected \
        --seed 42 \
        --config configs/anomalies.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import pandas as pd

from ml.synthetic.engine import SyntheticAnomalyEngine
from ml.synthetic.schema import AnomalyInjectionConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SkyGuard AI — Synthetic Anomaly Injection & Evaluation Engine"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to clean processed baseline CSV file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/experiments/injected",
        help="Directory to save modified observations and isolated ground truth tables",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed (default: 42)",
    )
    parser.add_argument(
        "--experiment-id",
        type=str,
        default=None,
        help="Optional experiment identifier",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/anomalies.yaml",
        help="Path to anomaly configuration YAML",
    )
    parser.add_argument(
        "--num-per-type",
        type=int,
        default=2,
        help="Number of anomalies to inject per category (default: 2)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    if not input_path.is_file():
        print(f"[ERROR] Input file not found: {input_path}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 75)
    print("SkyGuard AI — Synthetic Anomaly Injection Experiment")
    print(f"[*] Input File:      {input_path}")
    print(f"[*] Random Seed:     {args.seed}")
    print(f"[*] Configuration:   {args.config}")
    print("=" * 75)

    df_clean = pd.read_csv(input_path)
    print(f"[+] Loaded baseline dataset: {len(df_clean):,} observations.")

    cfg = AnomalyInjectionConfig(
        seed=args.seed,
        experiment_id=args.experiment_id or f"EXP_SEED_{args.seed}",
        num_anomalies_per_type=args.num_per_type,
        config_file_path=args.config,
    )

    engine = SyntheticAnomalyEngine(config=cfg)
    result = engine.run_injection(df_clean)

    # Save outputs
    base_name = input_path.stem
    exp_prefix = f"{base_name}_{result.experiment_id}"

    mod_csv_path = output_dir / f"{exp_prefix}_injected.csv"
    gt_csv_path = output_dir / f"{exp_prefix}_ground_truth.csv"

    result.modified_df.to_csv(mod_csv_path, index=False)
    result.ground_truth_df.to_csv(gt_csv_path, index=False)

    print(f"\n[+] Injected observations saved:  {mod_csv_path} ({len(result.modified_df):,} rows)")
    print(f"[+] Isolated ground truth saved:   {gt_csv_path} ({len(result.ground_truth_df):,} labels)")
    print("\n" + result.summary())
    print("\n[SUCCESS] Anomaly injection experiment complete.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
