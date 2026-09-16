# SkyGuard AI — API Specification (FastAPI / REST)

## 1. Overview & Principles
The SkyGuard AI backend exposes a high-performance RESTful streaming API built with **FastAPI**. All requests and responses are strictly validated via Pydantic v2 schemas and conform to uniform pagination and error conventions.

- **Base URL Prefix**: `/api/v1`
- **Content Type**: `application/json`
- **OpenAPI / Swagger UI**: Available at `/docs` or `/redoc`
- **Architecture**: Sub-10ms synchronous processing pipeline with non-destructive in-memory repository persistence.

---

## 2. API Endpoints

### 2.1. Real-Time Processing Endpoints (`/observations`)

#### `POST /api/v1/observations/process`
Process a single telemetry packet synchronously through the analytical pipeline.
- **Request Body**: `WeatherObservation`
- **Response**: `ProcessingResult` (contains `HybridDecision`, `SensorHealthSummary`, `ExplanationSummary`, `CorrectionRecommendation`, and `ProcessingLatencyBreakdown`).

#### `POST /api/v1/observations/batch`
Process a sequence of observations in causal order.
- **Request Body**: `list[WeatherObservation]`
- **Response**: `list[ProcessingResult]`

---

### 2.2. Stations & Telemetry Endpoints (`/stations`)

#### `GET /api/v1/stations`
Retrieve all monitored AWS stations with geodetic coordinates and operational status.
- **Response**: `list[dict]`

#### `GET /api/v1/stations/{station_id}`
Retrieve station metadata and coordinate details.

#### `GET /api/v1/stations/{station_id}/latest`
Retrieve the latest cached snapshot and weather parameters for a specific station.
- **Response**: `LiveStationSnapshot`

#### `GET /api/v1/stations/{station_id}/history`
Retrieve chronological observation history with optional timestamp filtering and pagination.
- **Query Params**: `start_time`, `end_time`, `limit` (1..1000), `offset` (0..)
- **Response**: `PaginatedResponse[WeatherObservation]`

#### `GET /api/v1/stations/{station_id}/health`
Retrieve the latest rolling sensor health index, sub-dimension scores, and maintenance SOP action.
- **Response**: `SensorHealthSummary`

---

### 2.3. Anomalies & Explainability Endpoints (`/anomalies`)

#### `GET /api/v1/anomalies`
Query detected anomaly events across stations with multi-criteria filtering and pagination.
- **Query Params**: `station_id`, `decision`, `severity`, `start_time`, `end_time`, `limit`, `offset`
- **Response**: `PaginatedResponse[AnomalyEventRecord]`

#### `GET /api/v1/anomalies/{event_id}`
Retrieve comprehensive details for a specific anomaly event record.
- **Response**: `AnomalyEventRecord`

#### `GET /api/v1/anomalies/{event_id}/explanation`
Retrieve full SHAP / rule-based feature contributions and natural language operator summary.
- **Response**: `ExplanationSummary`

---

### 2.4. System Diagnostics Endpoints (`/system`)

#### `GET /api/v1/system/health`
Retrieve end-to-end health status of the backend, repository, ML models, and latency metrics.
- **Response**: `SystemHealthStatus`

---

### 2.5. Streaming Replay Endpoints (`/replay`)

#### `GET /api/v1/replay/status`
Inspect current status of the streaming replay simulator.

#### `POST /api/v1/replay/step`
Execute a synchronous simulation step forward across queued historical observations.
- **Query Params**: `steps` (default: 1)
- **Response**: `list[ProcessingResult]`
