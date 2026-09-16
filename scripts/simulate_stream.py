"""CLI script to generate 5-minute synthetic simulation streams from historical series.

Usage:
    python scripts/simulate_stream.py \
        --input data/processed/42182099999_2024_normalized.csv \
        --output data/experiments/simulations/42182099999_2024_5min_sim.csv \
        --cadence 5.0
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.synthetic.stream_simulator import StreamSimulator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SkyGuard AI — 5-Minute Synthetic Stream Simulation"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to input observations CSV",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/experiments/simulations",
        help="Output CSV file path or directory",
    )
    parser.add_argument(
        "--cadence",
        type=float,
        default=5.0,
        help="Target simulation cadence in minutes (default: 5.0)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for micro-turbulence noise",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"[ERROR] Input file not found: {input_path}", file=sys.stderr)
        return 1

    out_p = Path(args.output)
    if out_p.is_dir() or not out_p.suffix:
        out_p.mkdir(parents=True, exist_ok=True)
        output_file = out_p / f"{input_path.stem}_5min_sim.csv"
    else:
        out_p.parent.mkdir(parents=True, exist_ok=True)
        output_file = out_p

    print("=" * 75)
    print("SkyGuard AI — 5-Minute High-Cadence Stream Simulator")
    print(f"[*] Input File:      {input_path}")
    print(f"[*] Output File:     {output_file}")
    print(f"[*] Target Cadence:  {args.cadence} minutes")
    print("=" * 75)

    df_in = pd.read_csv(input_path)
    simulator = StreamSimulator(
        target_cadence_minutes=args.cadence,
        add_micro_turbulence=True,
        seed=args.seed,
    )

    sim_df = simulator.simulate_stream(df_in)
    sim_df.to_csv(output_file, index=False)

    print(f"[+] Simulation completed successfully!")
    print(f"[+] Input rows:  {len(df_in):,}")
    print(f"[+] Output rows: {len(sim_df):,} (5-minute resolution)")
    print(f"[+] Synthetic Provenance Flag: is_synthetic={sim_df['is_synthetic'].all()}")
    print(f"[+] Saved to: {output_file}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
