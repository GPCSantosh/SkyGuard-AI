# SkyGuard AI — API Specification (FastAPI / REST)

## 1. Overview & Principles
The SkyGuard AI backend exposes a RESTful API built with **FastAPI**. All requests and responses are strictly validated via Pydantic v2 schemas.

- **Base URL Prefix**: `/api/v1`
- **Content Type**: `application/json`
- **Error Format**: Uniform RFC 7807 problem details structure.
- **Authentication**: Bearer Token / API Key (Configurable; disabled in local development mode).

---

## 2. API Endpoints

### 2.1. Ingestion Endpoints
#### `POST /api/v1/ingest/observation`
Ingest a single normalized weather observation record.
- **Request Body**: `WeatherObservation`
- **Responses**:
  - `201 Created`: Observation accepted and queued for QC/analysis.
  - `422 Unprocessable Entity`: Schema or range validation error.

#### `POST /api/v1/ingest/batch`
Ingest a batch of weather observation records.
- **Request Body**: `list[WeatherObservation]`
- **Responses**:
  - `200 OK`: Returns batch summary (`accepted_count`, `rejected_count`, `errors`).

---

### 2.2. Station & Network Endpoints
#### `GET /api/v1/stations`
Retrieve list of registered weather stations with latest status.
- **Query Params**: `status` (optional), `state` (optional), `limit` (default: 100).
- **Response**: `list[StationMetadataResponse]`

#### `GET /api/v1/stations/{station_id}`
Retrieve station metadata, installed sensors, and geographic coordinates.

#### `GET /api/v1/stations/{station_id}/neighbors`
Retrieve spatial neighbor stations ordered by geodetic distance.
- **Query Params**: `radius_km` (default: 150), `max_neighbors` (default: 5).

---

### 2.3. Telemetry & Observation Endpoints
#### `GET /api/v1/stations/{station_id}/observations`
Retrieve historical observations (raw + quality flags + model-imputed values).
- **Query Params**:
  - `start_time` (ISO-8601 UTC)
  - `end_time` (ISO-8601 UTC)
  - `include_imputed` (boolean, default: true)
  - `parameter` (`temperature` | `pressure` | `humidity` | `all`)
- **Response**: Time-series array of multi-parameter readings.

---

### 2.4. Anomalies & Quality Diagnostics Endpoints
#### `GET /api/v1/anomalies`
Query system-wide detected anomalies across the network.
- **Query Params**:
  - `severity` (`LOW` | `MEDIUM` | `HIGH` | `CRITICAL`)
  - `category` (15-category taxonomy enum)
  - `station_id` (optional)
  - `start_time`, `end_time`
- **Response**: Paginated list of anomaly events with root-cause and confidence.

#### `GET /api/v1/anomalies/{anomaly_id}/explain`
Retrieve local feature attribution and SHAP explanation for a specific anomaly event.

---

### 2.5. Sensor Health & Operations Endpoints
#### `GET /api/v1/stations/{station_id}/health`
Retrieve current sensor health index (0–100 scale), uptime, drift metrics, and failure probabilities.

#### `GET /api/v1/network/summary`
Retrieve high-level network operational overview (Total active stations, healthy vs degraded count, active critical anomalies, network data completeness %).

---

## 3. Standard Response & Error Schemas

### Standard Success Wrapper
```json
{
  "status": "success",
  "data": {},
  "timestamp": "2026-09-16T22:30:00Z"
}
```

### Standard Error Schema
```json
{
  "status": "error",
  "error_code": "INVALID_MEASUREMENT_RANGE",
  "message": "Temperature reading 95.0°C exceeds physical maximum threshold of 60.0°C.",
  "details": {
    "parameter": "temperature",
    "value": 95.0,
    "valid_range": [-50.0, 60.0]
  },
  "timestamp": "2026-09-16T22:30:00Z"
}
```
