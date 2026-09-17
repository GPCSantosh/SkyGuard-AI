# SkyGuard AI — Hackathon Submission Checklist

> **Release Identifier:** `v1.0.0-hackathon`
> **Git Commit:** `phase-13c-release-frozen` (to be tagged at end of Phase 13C)
> **Parent Commit:** `ffba8e8` (phase-13b-demo-hardened)
> **Evaluation Version:** `1.0.0` (frozen at Phase 13A, `evaluation/final_results.json`)
> **Demo Dataset Version:** `1.0.0` (seed=42, 384 observations, `demo/replay/narrative_replay_dataset.csv`)
> **Model Version:** `isolation_forest_s42` (`models/registry/isolation_forest_s42_metadata.json`)

---

## 1. Project Overview

**SkyGuard AI** is a meteorological data quality and anomaly detection platform for Automatic Weather Station (AWS) networks. It solves the critical failure modes of classical quality control systems:

- **False alarms on genuine severe weather** — classical ML flags storms, squalls, and heatwaves as sensor faults
- **Missed subtle hardware degradation** — flat thresholds miss low-amplitude sensor drift and intermittent freezes
- **Operator blind spots** — no interpretable, evidence-backed explanations for field crews
- **Destructive correction** — traditional systems overwrite original sensor telemetry

SkyGuard AI implements a 7-gate hierarchical hybrid decision engine synthesizing ML scores, geodesic spatial consensus, multivariate physics, temporal dynamics, and longitudinal sensor health into 5 operational decision classes.

---

## 2. Architecture

```
LIVE SOURCE (Open-Meteo WMO)  ←→  LiveSourcePoller
                                          ↓
                          RealTimeProcessingEngine
                         ┌──────────────────────────┐
                         │  Feature Engineering      │
                         │  Isolation Forest ML      │
                         │  Spatial Geodesic IDW     │
                         │  Hybrid 7-Gate Arbiter    │
                         │  TreeSHAP Explainer       │
                         │  Sensor Health Engine     │
                         │  Imputation/Correction    │
                         └──────────────────────────┘
                                      ↓
             PostgreSQL / SQLite ← Persistence Layer
                                      ↓
                           WebSocket Broadcaster
                                      ↓
                           React Operations Dashboard
```

**Stack:** Python 3.13 + FastAPI + Pydantic v2 + scikit-learn + SHAP + SQLAlchemy + Alembic + PostgreSQL + React + TypeScript + Vite

---

## 3. Scientific Evidence

All benchmark metrics are measured on a frozen, chronologically partitioned evaluation dataset:

| Metric | Value | Evidence Type | Source | Limitation |
| :--- | :--- | :--- | :--- | :--- |
| Hybrid Pipeline F1 | **0.963** | BENCHMARK | `FINAL_EVALUATION_REPORT.md` §8 (Table 8 Aggregate) | Synthetic + scenario dataset |
| Network-Aggregate Precision | **0.952** | BENCHMARK | `FINAL_EVALUATION_REPORT.md` §8 (Table 8 Aggregate) | Synthetic + scenario dataset |
| Network-Aggregate Recall | **0.974** | BENCHMARK | `FINAL_EVALUATION_REPORT.md` §8 (Table 8 Aggregate) | Synthetic + scenario dataset |
| Clean-Period FPR | **0.00%** | BENCHMARK | `FINAL_EVALUATION_REPORT.md` §5 (Baselines Table) | Clean nominal weather test partition |
| Regional Event Protection | **100%** | BENCHMARK | `final_results.json` → `hybrid_decision_engine.summary` | Scenario-based; squalls + heatwaves only |
| Event Detection Latency | **0–60 min** | BENCHMARK | `FINAL_EVALUATION_REPORT.md` §7 (Table 7) | Class-dependent; frozen sensors take 60 min |
| Pipeline P95 Latency | **3.42 ms** | LOCAL PERFORMANCE | `FINAL_EVALUATION_REPORT.md` §17 (Pipeline Profiler) | Single-node local; not deployed infra |
| Throughput | **>550 obs/sec** | LOCAL PERFORMANCE | `FINAL_EVALUATION_REPORT.md` §17 | Single-node local |

### Anti-Leakage Guarantee
- Chronological train/val/test partition with strict causal window functions
- No future observations contaminate feature vectors
- Ground truth labels isolated from model feature vectors
- Verified: `VERIFIED_NO_LEAKAGE` status in `evaluation/final_results.json`

---

## 4. Live Validation Evidence

| Check | Status | Source |
| :--- | :--- | :--- |
| Open-Meteo WMO live API qualified | ✅ 100% Pass | `LIVE_VALIDATION_REPORT.md` |
| ISO-8601 UTC timestamp normalization | ✅ Pass | `LIVE_VALIDATION_REPORT.md` |
| State machine: HEALTHY→DEGRADED→OUTAGE→RECOVERY→HEALTHY | ✅ Pass | `final_results.json` |
| Source health isolated from sensor health | ✅ Pass | `final_results.json` |

> **Limitation:** Live validation uses Open-Meteo WMO surface feed as testbed. Not equivalent to direct IMD AWS hardware telemetry integration.

---

## 5. Demo Instructions

### Prerequisites
```bash
# Verify all systems
python demo/scripts/demo_health_check.py
```
Expected: `9/9 PASS`

### Option A: Live Mode
```bash
# Backend
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend && npm.cmd run dev
```
Navigate to `http://localhost:5173`. TopBar shows: 🟢 `LIVE MODE (OPEN-METEO)`

### Option B: Demo Replay Mode (Deterministic)
```bash
# Same startup as Live Mode
# In Dashboard → Network Overview tab:
# 1. Select a scenario from the dropdown
# 2. Click "Step 1 AWS" or "Step Cycle (8 AWS)"
# TopBar shows: 🔵 DEMO REPLAY MODE
```

### Scenario Sequence (8–12 min)
1. **Flagship Narrative** — full end-to-end normal → fault → genuine event → outage
2. **Isolated Hardware Spike** — isolated +18.5°C spike at New Delhi
3. **Regional Squall Event** — genuine squall protected across 4 stations
4. **Source Health Outage** — sensor health isolated from API outage

> **Safety:** Reset Demo resets only the replay pointer — no database mutations.

---

## 6. Known Limitations

> [!IMPORTANT]
> These limitations are **explicitly retained** and must not be concealed from judges.

1. **Synthetic fault reliance** — benchmark anomalies are substantially synthetic/scenario-based; limited labeled real-world AWS hardware fault data exists
2. **Spatial density constraint** — isolated stations (e.g., Srinagar at 1,587m with 0 active neighbors) produce `UNCERTAIN` outputs rather than definitive fault classification
3. **Live validation scope** — Open-Meteo validation is not equivalent to direct IMD AWS gateway integration
4. **Latency measurement context** — P95=3.42ms measured on single-node local execution; distributed deployment latency is not experimentally measured
5. **Uncalibrated ML scores** — Isolation Forest anomaly scores are decision-function values, not calibrated Bayesian probabilities
6. **RPO/RTO targets** — Disaster recovery RPO<1min and RTO<2min are design targets validated under local simulation, not under production distributed load

---

## 7. Reproducibility

```bash
# Freeze exact state
python scripts/run_final_evaluation.py --seed 42
# Produces: evaluation/final_results.json, evaluation/reproducibility_manifest.json

# Full test suite
pytest tests/

# Frontend build
cd frontend && npm.cmd run build

# Pre-demo health check
python demo/scripts/demo_health_check.py
```

### Frozen Artifact SHA-256 Hashes

| Artifact | SHA-256 |
| :--- | :--- |
| `evaluation/final_results.json` | `90c58ce5e2a3b219a110ef6fd26c68e56ec46e4c2e0dbdc3491e559c8fe61402` |
| `evaluation/reproducibility_manifest.json` | `6931f71128094a0cd29204180e62e93f2a849f2e721e82f3db2c3c6b36ab049d` |
| `demo/replay/narrative_replay_dataset.csv` | `fd26360a4663a8ad479aa00c6e2e48286b5880ecb9b6aa701b7b43aadc87f9dc` |
| `demo/replay/scenario_registry.json` | `60e5d7470c15919dfaa5c3aeffddc1064c90f3ba1721f30a0bda3a65e9849a9f` |
| `models/registry/isolation_forest_s42_weights.joblib` | `fd2994eebe2278bf28b43b896d289d13c6ac43fb1d93b883d22a6c48c2ed63a5` |
| `models/registry/isolation_forest_s42_metadata.json` | `cebe6f415a43d735ea0aca1a9d5f5efb335242b89e055ed29f9ff8fc0edf6b75` |

---

## 8. Security

| Check | Status |
| :--- | :--- |
| No secrets in Git history | ✅ Verified — no `.env` files tracked |
| No hardcoded credentials in source | ✅ Verified — `test_no_hardcoded_secrets_in_codebase` passes |
| PostgreSQL uses `expose` only (no public `ports`) | ✅ Verified — `docker-compose.yml` line 28 |
| `SKYGUARD_DEBUG=false` default in compose | ✅ Verified — `docker-compose.yml` line 72 |
| Rate-limiting and poll-now protection active | ✅ Verified — `RateLimitExceededError` guard in live poller |
| Frontend bundle contains no API keys | ✅ Verified — environment via Vite `VITE_*` at build time |
| `.env.example` provides placeholder template | ✅ Present — all real values excluded |

---

## 9. Recovery Procedures

### Live Source Unavailable
- TopBar displays: 🔴 `LIVE SOURCE UNAVAILABLE`
- Network Overview shows fallback banner with direct "Switch to Demo Replay Mode" action
- No data loss — replay mode activates from frozen dataset

### Demo Reset
- Click "Reset Demo" in Demo Controller panel
- Resets: `current_index → 0`, `emitted_count → 0`
- Preserved: All database records, frozen evaluation artifacts, production observation history

### Backend Restart
```bash
# Database state auto-rehydrated from SQLite/PostgreSQL on restart
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

---

## 10. Release Dimension Status

| Dimension | Status | Notes |
| :--- | :--- | :--- |
| Scientific evaluation | ✅ FROZEN | Phase 13A — `evaluation/final_results.json`, seed=42 |
| Operational validation | ✅ QUALIFIED | Open-Meteo live API; state machine verified |
| Deployment validation | ✅ HARDENED | Docker Compose + PostgreSQL + Alembic + disaster recovery |
| Security validation | ✅ CLEAN | No secrets in code/git/bundle/logs |
| Disaster recovery | ✅ TESTED | RPO<1min, RTO<2min (local simulation targets) |
| Demo reproducibility | ✅ DETERMINISTIC | seed=42; 4 scenarios; 9/9 health checks pass |
| Known limitations | ✅ DOCUMENTED | See §6 above — explicitly retained |

---

## 11. Git Provenance

```
Branch: main
Final tag: phase-13c-release-frozen

Phase tags (chronological):
  phase-0-foundation
  phase-1a-dataset-qualified
  phase-1b-ingestion-qc
  phase-2-feature-anomaly-framework
  phase-3-baseline-evaluation
  phase-4-spatial-context
  phase-5-hybrid-decision
  phase-5a-hybrid-benchmark
  phase-6a-explainability
  phase-6b-sensor-health
  phase-7-correction-imputation
  phase-8-realtime-engine
  phase-9b-dashboard
  phase-9c-ui-hardening
  phase-10-websocket-realtime
  phase-11a-live-source-qualified
  phase-11b-live-connector
  phase-11c-source-health
  phase-11d-live-validation
  phase-12a-persistence
  phase-12b-production-deployment
  phase-12c-production-hardening
  phase-13a-final-evaluation
  phase-13b-demo-hardened
  phase-13c-release-frozen  ← this release
```
