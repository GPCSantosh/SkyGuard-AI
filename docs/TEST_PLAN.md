# SkyGuard AI — Test Plan

## 1. Test Strategy Overview
Testing in SkyGuard AI follows a strict multi-tier verification hierarchy:
1. **Unit Tests**: Schema validation, boundary range checks, timestamp parsing, connector interfaces, and mathematical utilities.
2. **Integration Tests**: Ingestion pipeline flow, database CRUD, configuration loading, and API endpoint contracts.
3. **Property & Invariance Tests**: Verifying that raw observations are never mutated under any transformation or imputation pipeline.
4. **Synthetic Fault Benchmarking**: Evaluation tests comparing ML anomaly predictions against known injected ground-truth faults.

---

## 2. Test Execution Matrix

| Test Suite | Location | Purpose | Execution Cadence |
|---|---|---|---|
| **Phase 0 Baseline Tests** | `tests/unit/`, `backend/tests/` | Pydantic model validation, config loading, import integrity | Pre-commit & CI |
| **Data QC Rule Tests** | `tests/unit/qc/` | Physical limits, rate-of-change thresholds, step tests | Phase 1+ |
| **Connector Tests** | `tests/integration/connectors/` | CSV parsing, mock API polling, stream deserialization | Phase 1+ |
| **ML Inference Tests** | `tests/unit/ml/` | Pipeline transformations, isolation forest inference, SHAP outputs | Phase 2+ |
| **API Integration Tests** | `tests/integration/api/` | FastAPI endpoint requests, response codes, error handling | Phase 3+ |
| **Synthetic Benchmark** | `tests/evaluation/` | Precision, Recall, F1, latency benchmark across 15 fault categories | Phase 2+ |

---

## 3. Phase 0 Test Suite (Current Baseline)
In this foundation phase, tests verify:
- **`test_imports.py`**: Clean import of all core backend and ML module namespaces without syntax or dependency errors.
- **`test_config.py`**: Default settings loading, YAML configuration parsing, environment variable overrides, and 5-minute default sampling rate verification.
- **`test_observation_schema.py`**:
  - Valid `WeatherObservation` instantiation.
  - Rejection of out-of-bounds physical measurements ($T = 95^\circ\text{C}$, $RH = 120\%$, $P = 400\text{ hPa}$).
  - Rejection of missing required fields (`station_id`, `timestamp`, `latitude`, `longitude`).
  - Correct parsing of various ISO-8601 UTC timestamp formats.
  - Immutability / serialization round-trip verification.
- **`test_connectors_interface.py`**: Verification of `BaseConnector` abstract contract and compliance of concrete connector placeholders.

---

## 4. Phase 1B Test Suite (NOAA ISD Ingestion, QC & Meteorology)
In this phase, tests verify:
- **`test_meteorology.py`**:
  - August-Roche-Magnus Relative Humidity derivation across standard, hot-humid, arid desert, cold fog, and sub-zero winter scenarios.
  - Clamping behavior when dew point exceeds air temperature.
  - Sea-level to station pressure reduction and inverse hypsometric conversions.
  - Multivariate physical consistency checks between $T$, $T_d$, and reported $RH$.
- **`test_noaa_parser.py`**:
  - Composite field splitting and scaling (`+0108,1` $\rightarrow 10.8^\circ\text{C}$, QC=`1`).
  - Correct parsing of `TMP`, `DEW`, `SLP`, `STP`, `MA1`, `WND`.
  - Quality control flag interpretation (`1` $\rightarrow$ `VALID`, `2` $\rightarrow$ `SUSPECT`, `3` $\rightarrow$ `ERROR`, `9` $\rightarrow$ `UNKNOWN`/`MISSING`).
  - Report type filtering (`FM-12`, `FM-15`, `METAR`).
- **`test_profiler.py`**:
  - Calculation of summary statistics (min, mean, max, median, std, IQR).
  - Missingness percentage computation per variable.
  - Duplicate timestamp and out-of-order sequence detection.
  - Cadence estimation (median, min, max, mode, regularity flag).
  - Markdown and JSON profile export.
- **`test_noaa_connector.py`**:
  - `NOAAISDConnector` lifecycle, local caching, and record streaming.
- **`test_ingestion_edge_cases.py`**:
  - 17 distinct edge cases: missing $T$, missing $T_d$, $T == T_d$, $T_d > T$, missing pressure, duplicate timestamps, multi-report coincident timestamps, corrupted rows, empty files, headers-only files, and unexpected columns.

---

## 6. Phase 3 Test Suite (Baseline Models & Anti-Leakage Framework)
In this phase, tests verify:
- **`test_leakage.py`**: Mandatory anti-leakage verification ensuring strict chronological split ordering (no overlap, train before val, val before test), zero future data leakage during feature generation and imputer fitting, and zero contamination of synthetic ground truth into model features.
- **`test_models_baselines.py`**: Fixed Threshold and Rolling Z-Score detector initialization, score normalization in $[0, 1]$, threshold calibration on validation sets, and edge case resilience (constant series, NaNs).
- **`test_isolation_forest.py`**: Isolation Forest detector training on clean data, continuous normalized anomaly scoring, validation threshold calibration, missing/Inf value sanitization, and model/metadata serialization round-trip (`.joblib` + `_metadata.json`).
- **`test_evaluation_metrics.py`**: Observation-level metrics (Precision, Recall, F1, FPR, FNR, PR-AUC, ROC-AUC) and Event-level metrics (Episode Recall, Latency in steps/minutes, False Alarms per station-day).
- **`test_feature_registry.py`**: Feature Registry registration, retrieval by category (`RAW`, `TEMPORAL`, `ROLLING`, `CHANGE`, `PERSISTENCE`, `DEVIATION`, `MULTIVARIATE`, `SPATIAL`), named feature sets (Sets A, B, C, D), and validation.
- **`test_phase3_edge_cases.py`**: 18 specialized edge cases (empty dataframes, missing columns, single-row data, all-NaN/Inf feature inputs, zero variance, extreme unobserved values, negative values, leap-year timestamps, out-of-order timestamps, duplicate timestamps).

---

## 7. Phase 4 Test Suite (Spatial & Synoptic Context Engine)
Phase 4 tests verify:
- **`test_spatial_topology.py`**: Exact geodesic Haversine distance, initial compass bearing (forward azimuth $0^\circ-360^\circ$), elevation differences, YAML network graph parsing, and JSON serialization round-trip.
- **`test_spatial_engine.py`**: Temporal alignment within configurable window, stale data exclusion, barometric sea-level pressure normalization, statistical consensus metrics (mean, median, std, min, max, z-score, similarity ratios), IDW distance weighting, and cross-variable multi-sensor coherence.
- **`test_spatial_scenarios.py`**: Multi-station scenario validation covering Local Sensor Anomaly (A -> `LOCAL_ONLY`), Regional Weather Event (B -> `REGIONAL_PATTERN`), Mixed Regional Event + Sensor Fault (C -> Target Departure isolated), and Isolated Station Outage (D -> `INSUFFICIENT_CONTEXT`).
- **`test_spatial_edge_cases.py`**: Zero configured neighbors, single neighbor, missing neighbor values, duplicate station coordinates, extreme inter-station distances, all-identical neighbor readings (zero variance), and robust outlier neighbor resilience.

---

## 8. Phase 5 Test Suite (Hybrid Decision Engine)
Phase 5 tests verify:
- **`test_hybrid_evidence.py`**: Pydantic schema validation of unflattened evidence domains (`DataQualityEvidence`, `SingleStationMLEvidence`, `TemporalEvidence`, `MultivariateEvidence`, `SpatialSynopticEvidence`, `ObservationEvidence`, `HybridDecision`), evidence states (`SUPPORTS`, `CONTRADICTS`, `NEUTRAL`, `UNAVAILABLE`), and decision severities.
- **`test_hybrid_decision_engine.py`**: Comprehensive gate-by-gate rule evaluation verifying:
  - Gate 1: Priority of telemetry and missingness data quality failures (`PROBABLE_DATA_QUALITY_ISSUE`).
  - Gate 2: Planetary physical limit boundary violations (`PROBABLE_SENSOR_ANOMALY`).
  - Gate 3: Persistent sensor flatlining across diurnal cycles (`PROBABLE_SENSOR_ANOMALY`).
  - Gate 4: Thermodynamic physical constraint violations ($T_d > T$, $RH=100\%$ with diverging vapor pressure).
  - Gate 5: Spatial-ML synergy (coherent genuine regional events vs. locally isolated hardware spikes/drifts).
  - Gate 6: Uncertainty arbitration under sparse/offline neighbor topologies (`UNCERTAIN`).
  - Gate 7: Nominal dynamic fallback (`NORMAL`).
- **`test_hybrid_scenarios.py`**: End-to-end operational verification across canonical Scenarios A through H with exact reason code and SOP action validation.
- **`test_hybrid_edge_cases.py`**: 15 boundary and edge conditions including zero anomaly scores, extreme out-of-scale scores, contradictory spatial vs temporal signals, all-neighbors-missing scenarios, zero-variance networks, and missing optional evidence domains.

---

## 9. Test Commands
```bash
# Run full unit test suite (Phases 0, 1, 2, 3, 4, 5)
pytest -v tests/unit/

# Run specific Phase 5 Hybrid Decision Engine tests
pytest -v tests/unit/test_hybrid_evidence.py tests/unit/test_hybrid_decision_engine.py tests/unit/test_hybrid_scenarios.py tests/unit/test_hybrid_edge_cases.py

# Run specific Phase 4 spatial context tests
pytest -v tests/unit/test_spatial_topology.py tests/unit/test_spatial_engine.py tests/unit/test_spatial_scenarios.py tests/unit/test_spatial_edge_cases.py

# Run specific Phase 3 baseline & anti-leakage tests
pytest -v tests/unit/test_leakage.py tests/unit/test_isolation_forest.py tests/unit/test_models_baselines.py tests/unit/test_evaluation_metrics.py tests/unit/test_feature_registry.py tests/unit/test_phase3_edge_cases.py
```
