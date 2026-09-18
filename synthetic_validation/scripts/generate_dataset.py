"""CLI script to generate synthetic baseline and injected validation datasets."""

from __future__ import annotations

import json
from pathlib import Path
import sys

# Ensure repository root is in sys.path
root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from synthetic_validation.harness.injector import SyntheticAnomalyInjector
from synthetic_validation.harness.network_generator import SyntheticNetworkGenerator


def main() -> int:
    print("=" * 72)
    print(" SKYGUARD AI - SYNTHETIC DATASET GENERATOR (SEED=42) ")
    print("=" * 72)

    datasets_dir = root / "synthetic_validation" / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)

    generator = SyntheticNetworkGenerator(seed=42)
    injector = SyntheticAnomalyInjector(seed=42)

    # 1. Generate Clean Baseline (20 stations, 24 hours @ 5-min intervals = 5,760 observations)
    print("Generating 24-hour clean baseline for 20 AWS stations...")
    baseline_obs = generator.generate_baseline_observations(
        duration_hours=24.0,
        interval_minutes=5,
    )
    baseline_df = generator.generate_baseline_dataframe(
        duration_hours=24.0,
        interval_minutes=5,
    )
    baseline_csv_path = datasets_dir / "clean_baseline_20stn_24h.csv"
    baseline_df.to_csv(baseline_csv_path, index=False)
    print(f" [OK] Baseline dataset saved: {baseline_csv_path} ({len(baseline_obs)} observations)")

    # 2. Inject Validation Scenarios & Create Ground Truth Registry
    print("Injecting 24 validation scenarios into synthetic network...")
    injected_obs, truth_registry = injector.inject_all_scenarios(baseline_obs)

    # Serialize injected dataset
    injected_records = []
    for o in injected_obs:
        injected_records.append({
            "station_id": o.station_id,
            "station_name": o.station_name,
            "latitude": o.latitude,
            "longitude": o.longitude,
            "elevation": o.elevation,
            "timestamp": o.timestamp.isoformat(),
            "temperature_c": o.temperature,
            "dew_point_c": o.dew_point_c,
            "relative_humidity_pct": o.humidity,
            "sea_level_pressure_hpa": o.pressure,
            "source": o.source,
            "data_quality_status": o.data_quality_status,
            "is_synthetic": True,
        })
    import pandas as pd
    injected_df = pd.DataFrame(injected_records)
    injected_csv_path = datasets_dir / "injected_validation_dataset.csv"
    injected_df.to_csv(injected_csv_path, index=False)
    print(f" [OK] Injected dataset saved: {injected_csv_path} ({len(injected_obs)} observations)")

    # Serialize isolated ground-truth event registry
    truth_json_path = datasets_dir / "synthetic_event_truth.json"
    with open(truth_json_path, "w", encoding="utf-8") as f:
        json.dump(truth_registry, f, indent=2)
    print(f" [OK] Ground-truth event registry saved: {truth_json_path} ({len(truth_registry)} event records)")

    print("=" * 72)
    print(" SYNTHETIC DATASET GENERATION COMPLETE ")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
