# SkyGuard AI

> **Intelligent Anomaly Detection and Data Quality Assurance System for Automatic Weather Stations (AWS)**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Architecture: Hybrid QC](https://img.shields.io/badge/Architecture-Physics%20Rules%20%2B%20ML-indigo.svg)](docs/ARCHITECTURE.md)

---

## 1. Overview
**SkyGuard AI** is a meteorological observability and data quality control platform designed for Automatic Weather Station (AWS) networks across India.

Operating in remote, rugged environments, automated weather stations frequently experience sensor spikes, drift, frozen values, communication loss, and sudden offsets. Crucially, conventional thresholding algorithms often mislabel genuine extreme weather events (such as squalls or severe convective storms) as sensor faults.

SkyGuard AI solves this via a **Hybrid Intelligence Architecture**:
$$\text{Quality Decision} = \text{Meteorological Physics Rules} \oplus \text{Unsupervised ML Models} \oplus \text{Geodesic Spatial Neighbor Context}$$

### Primary Weather Parameters (Foundation Scope)
1. **Temperature (°C)**: Physical bounds $[-50.0, +60.0]^\circ\text{C}$
2. **Atmospheric Pressure (hPa)**: Physical bounds $[500.0, 1080.0]\text{ hPa}$
3. **Relative Humidity (%)**: Physical bounds $[0.0, 100.0]\%$

---

## 2. Core Architectural Principles
- **Raw Observations are Immutable**: Original sensor readings are permanently preserved without silent overwriting.
- **Separate Quality & Imputation Storage**: Model corrections and flags are stored independently with full derivation metadata.
- **Geodesic Spatial Proximity**: Station neighbor correlations use coordinate distance (Haversine/Vincenty), not administrative or state borders.
- **15-Category Operational Taxonomy**: Precise diagnostic classification (`NORMAL`, `SPIKE`, `DRIFT`, `FROZEN_SENSOR`, `POSSIBLE_GENUINE_EVENT`, `UNCERTAIN`, etc.).
- **Controlled Synthetic Evaluation**: Models are benchmarked by injecting controlled faults into clean historical series with isolated ground truth.
- **Configurable Cadence**: Default cadence is **5 minutes** ($300\text{s}$), fully configurable via YAML and environment variables.

---

## 3. Repository Structure

```
skyguard-ai/
├── backend/                  # FastAPI backend service
│   ├── app/
│   │   ├── api/              # REST endpoint routes
│   │   ├── connectors/       # Modular data source adapters (CSV, SIM, API, MQTT)
│   │   ├── core/             # Configuration, constants, logging
│   │   ├── models/           # Pydantic v2 domain schemas (WeatherObservation, Anomaly, Station)
│   │   └── main.py           # FastAPI application entrypoint
│   └── tests/                # Backend-specific test suite
│
├── frontend/                 # React + TypeScript + Tailwind frontend
│   ├── src/
│   │   └── types/            # Synchronized TypeScript domain types
│   ├── package.json
│   └── tsconfig.json
│
├── ml/                       # Machine learning & statistical pipelines
│   ├── features/             # Temporal, spatial, and multivariate feature extractors
│   ├── pipelines/            # Anomaly scoring models (Isolation Forest, LOF)
│   ├── synthetic/            # Synthetic fault injection engine
│   └── evaluation/           # Benchmark scorers and evaluation metrics
│
├── configs/                  # Externalized system & meteorological configurations
│   ├── default.yaml          # System defaults & pipeline windows
│   ├── thresholds.yaml       # Physical boundaries & step limits
│   └── stations.yaml         # Sample 20-station network topology across India
│
├── data/                     # Data stores
│   ├── raw/                  # Immutable raw historical telemetry (CSV, JSON)
│   ├── processed/            # Cleaned, normalized datasets
│   └── external/             # Digital Elevation Models (DEM) & spatial maps
│
├── models/registry/          # Serialized model artifacts (.joblib) & manifests
├── notebooks/                # Exploratory data analysis & prototype research
├── scripts/                  # Management, migration, and benchmarking scripts
├── docs/                     # Comprehensive engineering & architectural specifications
│   ├── PROJECT_SPEC.md       # Scope, parameters, requirements
│   ├── ARCHITECTURE.md       # 17-section architecture specification + Mermaid diagrams
│   ├── DATA_SPEC.md          # 14 data principles, schemas, taxonomy
│   ├── ML_SPEC.md            # ML strategy, feature pipelines, synthetic injection
│   ├── API_SPEC.md           # REST API specification & schemas
│   ├── UI_DESIGN_SYSTEM.md   # Meteorological Operations Center design system
│   ├── TEST_PLAN.md          # Multi-tier testing strategy
│   ├── EVALUATION_PLAN.md    # Synthetic evaluation & metrics plan
│   ├── DECISIONS.md          # Architecture Decision Records (ADR-001 to ADR-006)
│   └── ENGINEERING_RULES.md  # Standards & coding guidelines
│
├── tests/                    # Project-wide automated test suite
│   ├── unit/                 # Unit tests (schemas, configs, imports, connectors)
│   ├── integration/          # Ingestion & pipeline integration tests
│   └── fixtures/             # Mock observation payloads & sample records
│
├── AGENTS.md                 # Agent engineering rules and prime directives
├── .env.example              # Environment variables template
├── .gitignore                # Git exclusions
├── pyproject.toml            # Python packaging & tool configurations
└── requirements.txt          # Python dependencies
```

---

## 4. Getting Started

### Prerequisites
- Python 3.10 or higher
- Node.js 18+ (for frontend development)

### 1. Python Environment Setup
```bash
# Clone the repository
git clone https://github.com/your-org/skyguard-ai.git
cd sih_project

# Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
# Copy example configuration
cp .env.example .env

# Verify default settings in configs/default.yaml
```

### 3. Running Automated Tests
```bash
pytest -v
```

### 4. Running the Backend API Locally
```bash
uvicorn backend.app.main:app --reload --port 8000
```
- API Documentation (Swagger UI): `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/api/v1/health`

---

## 5. Development Guidelines
> **IMPORTANT:** Before implementing features in any phase, developers and agents must read the relevant documentation in [`docs/`](docs/) and follow [`AGENTS.md`](AGENTS.md).
