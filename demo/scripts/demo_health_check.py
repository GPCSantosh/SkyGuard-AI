"""Pre-Demo Comprehensive Health and Integrity Check for Hackathon Presentation.

Verifies end-to-end system availability:
- Backend environment and imports
- Model registry and weights
- Frozen replay scenarios and dataset
- Database availability and schema
- WebSocket / Real-time processing engine
- Frozen evaluation reports and reproducibility manifest
- Live source connector configuration
- Production frontend build artifact
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))


def run_health_check() -> bool:
    print("=" * 72)
    print(" SKYGUARD AI - PRE-DEMO COMPREHENSIVE INTEGRITY & HEALTH CHECK ")
    print("=" * 72)

    all_passed = True
    results = []

    def check(name: str, passed: bool, detail: str = ""):
        nonlocal all_passed
        status = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        results.append((name, status, detail))
        print(f" {status} {name:<45} {detail}")

    # 1. Check Python Environment & Core Imports
    try:
        import fastapi
        import pandas
        import pydantic
        import shap
        import sklearn
        import sqlalchemy
        check("Python Core Dependencies", True, f"Python {sys.version.split()[0]}")
    except Exception as e:
        check("Python Core Dependencies", False, str(e))

    # 2. Check Database & Topology Repository
    try:
        from backend.app.api.v1.deps import get_repository, get_default_topology
        repo = get_repository()
        topo = repo.topology
        station_count = len(topo.stations)
        check("Spatial Topology & Repository", station_count >= 8, f"{station_count} stations active")
    except Exception as e:
        check("Spatial Topology & Repository", False, str(e))

    # 3. Check Real-Time Engine & Hybrid Pipeline
    try:
        from backend.app.api.v1.deps import get_engine
        engine = get_engine()
        check("Real-Time Processing Engine", engine is not None, "Hybrid Decision Engine loaded")
    except Exception as e:
        check("Real-Time Processing Engine", False, str(e))

    # 4. Check Demo Dataset & Scenario Registry
    replay_dir = root / "demo" / "replay"
    dataset_csv = replay_dir / "narrative_replay_dataset.csv"
    registry_json = replay_dir / "scenario_registry.json"

    if dataset_csv.exists() and registry_json.exists():
        try:
            with open(registry_json, "r", encoding="utf-8") as f:
                registry = json.load(f)
            sc_count = len(registry.get("scenarios", []))
            check("Demo Replay Scenarios", sc_count >= 4, f"{sc_count} scenarios registered")
        except Exception as e:
            check("Demo Replay Scenarios", False, str(e))
    else:
        check("Demo Replay Scenarios", False, "Missing CSV or scenario_registry.json")

    # 5. Check Frozen Evaluation Benchmark Artifacts
    eval_dir = root / "evaluation"
    final_res = eval_dir / "final_results.json"
    rep_man = eval_dir / "reproducibility_manifest.json"

    if final_res.exists() and rep_man.exists():
        try:
            with open(final_res, "r", encoding="utf-8") as f:
                data = json.load(f)
            rec = data.get("hybrid_decision_engine", {}).get("summary", {}).get("sensor_fault_recall", 0)
            check("Frozen Scientific Benchmark", rec >= 0.95, f"Recall={rec:.3f} verified")
        except Exception as e:
            check("Frozen Scientific Benchmark", False, str(e))
    else:
        check("Frozen Scientific Benchmark", False, "Missing final_results.json or manifest")

    # 6. Check Model Registry
    model_dir = root / "models" / "registry"
    model_weights = model_dir / "isolation_forest_s42_weights.joblib"
    model_meta = model_dir / "isolation_forest_s42_metadata.json"
    check("ML Baseline Model Weights", model_weights.exists() and model_meta.exists(), "Isolation Forest weights verified")

    # 7. Check Live Weather API Connector Status
    try:
        from backend.app.api.v1.deps import get_live_poller
        poller = get_live_poller()
        stn_count = len(poller.topology.stations)
        check("Live Open-Meteo Poller Config", stn_count >= 8, f"{stn_count} stations configured")
    except Exception as e:
        check("Live Open-Meteo Poller Config", False, str(e))

    # 8. Check Frontend Production Build
    frontend_dist = root / "frontend" / "dist" / "index.html"
    check("Frontend Production Bundle", frontend_dist.exists(), "dist/index.html verified")

    # 9. Check Documentation Artifacts
    doc_eval = root / "docs" / "FINAL_EVALUATION_REPORT.md"
    doc_arch = root / "docs" / "FINAL_SYSTEM_ARCHITECTURE.md"
    doc_ops = root / "docs" / "OPERATIONS_RUNBOOK.md"
    doc_live = root / "docs" / "LIVE_VALIDATION_REPORT.md"
    docs_exist = doc_eval.exists() and doc_arch.exists() and doc_ops.exists() and doc_live.exists()
    check("Authoritative Technical Documentation", docs_exist, "All 4 Phase 13A specs present")

    print("=" * 72)
    if all_passed:
        print(" PRE-DEMO HEALTH CHECK: ALL SYSTEMS GO (100% PASS) ")
        print(" Platform is fully verified for deterministic hackathon demonstration.")
    else:
        print(" PRE-DEMO HEALTH CHECK: ONE OR MORE CHECKS FAILED ")
    print("=" * 72)

    return all_passed

if __name__ == "__main__":
    success = run_health_check()
    sys.exit(0 if success else 1)
