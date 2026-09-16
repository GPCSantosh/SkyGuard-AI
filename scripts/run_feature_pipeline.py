"""CLI script to run the SkyGuard AI Feature Engineering Pipeline over processed datasets.

Usage:
    python scripts/run_feature_pipeline.py \
        --input data/processed/42182099999_2024_normalized.csv \
        --output data/processed/42182099999_2024_features.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import pandas as pd
import yaml

# Ensure repository root is on Python search path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.features.pipeline import FeaturePipeline, FeaturePipelineConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SkyGuard AI — Feature Engineering Pipeline Execution"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to input normalized CSV observations file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to output CSV feature dataset",
    )
    parser.add_argument(
        "--stations-config",
        type=str,
        default="configs/stations.yaml",
        help="Path to stations configuration file (for spatial coordinates)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"[ERROR] Input file not found: {input_path}", file=sys.stderr)
        return 1

    output_path = (
        Path(args.output)
        if args.output
        else input_path.parent / f"{input_path.stem.replace('_normalized', '')}_features.csv"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 75)
    print("SkyGuard AI — Feature Engineering Pipeline")
    print(f"[*] Input:  {input_path}")
    print(f"[*] Output: {output_path}")
    print("=" * 75)

    df_in = pd.read_csv(input_path)
    print(f"[+] Loaded {len(df_in):,} raw/normalized records.")

    # Load station metadata for spatial context
    station_meta = {}
    stations_cfg_path = Path(args.stations_config)
    if stations_cfg_path.is_file():
        with open(stations_cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            for s in cfg.get("stations", []):
                station_meta[str(s["station_id"])] = {
                    "latitude": float(s["latitude"]),
                    "longitude": float(s["longitude"]),
                    "elevation_m": float(s.get("elevation", 0.0)),
                    "name": s.get("name", "AWS Station"),
                }

    pipeline = FeaturePipeline(
        config=FeaturePipelineConfig(),
        station_metadata=station_meta,
    )

    df_features = pipeline.transform(df_in)
    feature_cols = pipeline.get_feature_columns(df_features)

    df_features.to_csv(output_path, index=False)
    print(f"[+] Generated features successfully!")
    print(f"[+] Output rows: {len(df_features):,}")
    print(f"[+] Total columns: {len(df_features.columns)} ({len(feature_cols)} ML features)")
    print(f"[+] Saved to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
