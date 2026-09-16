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

## 4. Test Commands
```bash
# Run full unit test suite
pytest -v tests/unit/

# Run with coverage report
pytest -v --cov=backend/app --cov-report=term-missing tests/
```
