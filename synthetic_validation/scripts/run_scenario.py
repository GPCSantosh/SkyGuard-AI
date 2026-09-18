"""CLI script to run a single synthetic validation scenario by ID."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Ensure repository root is in sys.path
root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from synthetic_validation.harness.runner import SyntheticValidationRunner
from synthetic_validation.scenarios.definitions import get_scenario_by_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a single SkyGuard synthetic validation scenario.")
    parser.add_argument("--scenario", "-s", type=str, default="SV02", help="Scenario ID (e.g., SV01, SV02, ..., SV24)")
    args = parser.parse_args()

    scenario_id = args.scenario.upper().strip()
    scenario = get_scenario_by_id(scenario_id)
    if not scenario:
        print(f"[ERROR] Scenario {scenario_id} not found in scenario registry.")
        return 1

    print("=" * 72)
    print(f" RUNNING SYNTHETIC VALIDATION SCENARIO: {scenario.scenario_id} - {scenario.name} ")
    print("=" * 72)
    print(f" Category:         {scenario.category.value}")
    print(f" Target Stations:  {', '.join(scenario.target_stations)}")
    print(f" Anomaly Type:     {scenario.anomaly_type}")
    print(f" Expected Action:  {scenario.expected_decision}")
    print("-" * 72)

    runner = SyntheticValidationRunner(seed=42)
    result = runner.run_single_scenario(scenario_id)

    print(f" Status:           [{result.status}]")
    print(f" Processed Obs:    {result.total_observations_processed}")
    print(f" Actual Decision:  {result.actual_decision}")
    print(f" Health Before:    {result.health_score_before:.1f}%")
    print(f" Health After:     {result.health_score_after:.1f}% ({result.health_impact_observed})")
    print(f" Correction Gen:   {result.correction_generated}")
    print(f" Explainability:   {result.explainability_verified}")
    print(f" Persistence:      {result.persistence_verified}")
    print(f" WebSocket Events: {result.websocket_events_dispatched}")
    print(f" Mean Latency:     {result.mean_latency_ms:.2f} ms")
    print(f" P95 Latency:      {result.p95_latency_ms:.2f} ms")

    if result.status != "PASS":
        print("-" * 72)
        print(f"[FAILURE DETAILS] {result.error_message}")
        print("=" * 72)
        return 1

    print("=" * 72)
    print(f" SCENARIO {scenario_id} PASSED ALL VALIDATION ASSERTIONS ")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
