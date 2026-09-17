# SkyGuard AI — Synthetic End-to-End Validation Harness

## Overview

The **Synthetic End-to-End Validation Harness** is a deterministic, offline testing suite for SkyGuard AI. It generates a 20-station synthetic Automatic Weather Station (AWS) network, simulates physically plausible diurnal baselines across the primary meteorological trio (`temperature_c`, `relative_humidity_pct`, `sea_level_pressure_hpa`), injects 24 controlled fault/event scenarios, and routes observations through the complete production `RealTimeProcessingEngine` pipeline.

```
synthetic generator
    ↓
WeatherObservation (Immutable)
    ↓
QC / Physical Limit Validation
    ↓
RealTimeProcessingEngine
    ↓
Causal Feature Engineering
    ↓
Isolation Forest Anomaly Detection
    ↓
Multi-Gate Hybrid Decision Engine
    ↓
Explainability Engine (SHAP & Rules)
    ↓
Sensor Health Degradation / Protection
    ↓
Correction & Imputation Recommendation
    ↓
Database Repository Persistence
    ↓
WebSocket Connection Manager Broadcast
```

---

## Key Principles & Architectural Guarantees

1. **Isolation from Frozen Benchmark**: This harness is completely independent of the frozen Phase 13A Scientific Benchmark and demo datasets. It does not overwrite `evaluation/final_results.json`.
2. **Ground-Truth Separation**: Synthetic ground-truth metadata is saved to `synthetic_validation/datasets/synthetic_event_truth.json` and is never leaked into feature extraction or model inference.
3. **Raw Data Immutability**: All incoming `WeatherObservation` payloads are immutable (`frozen=True`). Correction recommendations are stored as advisory outputs without mutating raw observations.
4. **Isolated Test Database**: The harness executes against an isolated in-memory SQLite repository (`sqlite:///:memory:`) or dedicated test database URL, eliminating database contamination.
5. **No External Network Dependencies**: Zero external API calls to Open-Meteo, NOAA, or IMD. The simulation runs locally with deterministic seed `42`.

---

## Scenario Registry (SV01 to SV24)

| ID | Name | Category | Anomaly Type | Target Station(s) | Expected Hybrid Decision | Expected Sensor Health |
|:---|:---|:---|:---|:---|:---|:---|
| **SV01** | Clean Baseline | Baseline | `NONE` | All 20 AWS | `NORMAL` | Stable High (~100%) |
| **SV02** | Isolated Positive Spike | Temporal Fault | `SPIKE_POSITIVE` (+12°C) | `AWS_DEL_001` | `PROBABLE_SENSOR_ANOMALY` | Degrades |
| **SV03** | Isolated Negative Drop | Temporal Fault | `SPIKE_NEGATIVE` (-15°C) | `AWS_DEL_002` | `PROBABLE_SENSOR_ANOMALY` | Degrades |
| **SV04** | Persistent Step Change | Temporal Fault | `STEP_CHANGE` (+8°C) | `AWS_DEL_003` | `PROBABLE_SENSOR_ANOMALY` | Degrades |
| **SV05** | Slow Sensor Drift | Temporal Fault | `DRIFT` (+0.3°C/step) | `AWS_DEL_004` | `PROBABLE_SENSOR_ANOMALY` | Degrades |
| **SV06** | Flatline / Frozen Sensor | Temporal Fault | `FLATLINE` (18 steps) | `AWS_DEL_005` | `PROBABLE_SENSOR_ANOMALY` | Degrades (Persistence penalty) |
| **SV07** | High-Frequency Oscillation | Temporal Fault | `OSCILLATION` (±7.5°C) | `AWS_NCR_006` | `PROBABLE_SENSOR_ANOMALY` | Degrades |
| **SV08** | Rate-of-Change Violation | Temporal Fault | `RATE_OF_CHANGE_VIOLATION` | `AWS_NCR_007` | `PROBABLE_SENSOR_ANOMALY` | Degrades |
| **SV09** | Impossible Temperature | Physical Bound | `IMPOSSIBLE_TEMPERATURE` (75°C) | `AWS_NCR_008` | `PHYSICAL_LIMIT_EXCEEDED` | Degrades |
| **SV10** | Invalid Relative Humidity | Physical Bound | `INVALID_RH` (118%) | `AWS_NCR_009` | `PHYSICAL_LIMIT_EXCEEDED` | Degrades |
| **SV11** | Invalid Pressure Limit | Physical Bound | `INVALID_PRESSURE` (720 hPa) | `AWS_NCR_010` | `PHYSICAL_LIMIT_EXCEEDED` | Degrades |
| **SV12** | Missing Temperature Field | Data Quality | `MISSING_TEMPERATURE` | `AWS_REG_011` | `DATA_QUALITY_ISSUE` | Degrades |
| **SV13** | Missing RH Field | Data Quality | `MISSING_RH` | `AWS_REG_012` | `DATA_QUALITY_ISSUE` | Degrades |
| **SV14** | Missing Pressure Field | Data Quality | `MISSING_PRESSURE` | `AWS_REG_013` | `DATA_QUALITY_ISSUE` | Degrades |
| **SV15** | Duplicate Observation | Data Quality | `DUPLICATE_OBSERVATION` | `AWS_REG_014` | `NORMAL` (Idempotent) | Stable |
| **SV16** | Out-of-Order Observation | Data Quality | `OUT_OF_ORDER` (-30 min) | `AWS_REG_015` | `DATA_QUALITY_ISSUE` | Stable |
| **SV17** | Timestamp Gap | Data Quality | `TIMESTAMP_GAP` (45 min) | `AWS_REG_016` | `NORMAL` (Freshness recover) | Stable |
| **SV18** | Corrupted Timestamp | Data Quality | `CORRUPTED_TIMESTAMP` | `AWS_REG_017` | `INGESTION_REJECTED` | Stable |
| **SV19** | Multivariate Inconsistency | Multivariate | `MULTIVARIATE_INCONSISTENCY` | `AWS_REG_018` | `PROBABLE_SENSOR_ANOMALY` | Degrades |
| **SV20** | Spatial Outlier | Spatial Fault | `SPATIAL_OUTLIER` (+10.5°C) | `AWS_REG_019` | `PROBABLE_SENSOR_ANOMALY` | Degrades |
| **SV21** | Regional Squall / Cold Pool | Genuine Event | `REGIONAL_EVENT` (-8°C, +28% RH) | `AWS_DEL_001..005` | `POSSIBLE_GENUINE_EVENT` | **Protected (No fault penalty)** |
| **SV22** | Partial Station Outage | Outage | `PARTIAL_STATION_OUTAGE` | `AWS_REG_011..013` | `STALE` / Offline | Stable |
| **SV23** | Full Source Disconnection | Outage | `FULL_SOURCE_OUTAGE` | All 20 Stations | `DISCONNECTED` | Source Degraded, Sensor Stable |
| **SV24** | Recovery After Outage | Outage | `SOURCE_RECOVERY` | All 20 Stations | `NORMAL` | Recovering Monotonically |

---

## Directory Layout

```
synthetic_validation/
├── datasets/
│   ├── clean_baseline_20stn_24h.csv         # 5,760 baseline observations (20 stations, 288 steps)
│   ├── injected_validation_dataset.csv      # Complete synthetic dataset with injected scenarios
│   └── synthetic_event_truth.json           # Isolated ground-truth event registry
├── scenarios/
│   ├── definitions.py                       # Python scenario definitions & metadata
│   └── scenario_registry.json               # JSON scenario registry
├── harness/
│   ├── __init__.py
│   ├── network_generator.py                 # 20-station spatial topology & diurnal baseline generator
│   ├── injector.py                          # Deterministic anomaly injection engine
│   ├── runner.py                            # End-to-end execution runner
│   ├── assertions.py                        # Multi-dimensional automated assertion suite
│   ├── performance.py                       # Multi-scale latency & throughput profiler
│   └── ws_validator.py                      # Standalone WebSocket lifecycle & reconnect validator
├── reports/
│   ├── scenario_results.json                # Execution outcomes & performance metrics
│   └── SYNTHETIC_VALIDATION_REPORT.md       # Comprehensive markdown summary report
├── scripts/
│   ├── generate_dataset.py                  # Dataset & ground truth generator CLI
│   ├── run_scenario.py                      # Single scenario execution CLI (--scenario SV02)
│   ├── run_websocket_validation.py          # WebSocket lifecycle CLI
│   └── run_validation.py                    # Master test runner
└── README.md                                # Authoritative documentation
```

---

## Commands & Usage

### 1. Run Complete Validation Harness
```bash
python synthetic_validation/scripts/run_validation.py
```

### 2. Generate Synthetic Datasets
```bash
python synthetic_validation/scripts/generate_dataset.py
```

### 3. Run a Specific Scenario
```bash
python synthetic_validation/scripts/run_scenario.py --scenario SV02
python synthetic_validation/scripts/run_scenario.py --scenario SV21
```

### 4. Run WebSocket Lifecycle Validation
```bash
python synthetic_validation/scripts/run_websocket_validation.py
```

---

## Scope & Limitations

- **Local Synthetic Validation**: This test harness is designed to verify software correctness, multi-station edge cases, health reactions, and real-time processing under deterministic conditions.
- **Not Empirical Ground Truth**: Synthetic scenario pass rates must not be cited as empirical meteorological accuracy on real-world networks. Empirical benchmark metrics (Recall=0.949, Precision=0.978, F1=0.963) are established exclusively in `docs/FINAL_EVALUATION_REPORT.md` and `evaluation/final_results.json`.
