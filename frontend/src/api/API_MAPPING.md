# SkyGuard AI — Frontend to Backend API Mapping Document

This document records the exact contract between frontend API client functions and the authoritative FastAPI backend endpoints specified in `openapi.json` and `API_SPEC.md`.

---

## 1. Primary REST Endpoint Mappings

| Frontend Function | HTTP Method | Backend Path | Request Schema / Params | Response Schema | Used By Page(s) |
|---|---|---|---|---|---|
| `stationsApi.getStations` | `GET` | `/api/v1/stations` | None | `Array<Station>` | Network Overview, Live Monitoring, Sensor Health, Sidebar |
| `stationsApi.getStation` | `GET` | `/api/v1/stations/{station_id}` | `station_id: string` (path) | `Station` | Station Details, Anomaly Investigation |
| `stationsApi.getStationLatest` | `GET` | `/api/v1/stations/{station_id}/latest` | `station_id: string` (path) | `LiveStationSnapshot` | Station Details, Live Monitoring |
| `stationsApi.getStationHistory` | `GET` | `/api/v1/stations/{station_id}/history` | `station_id`, `start_time?`, `end_time?`, `limit?`, `offset?` | `PaginatedResponse<WeatherObservation>` | Station Details, Historical Analysis |
| `anomaliesApi.getAnomalies` | `GET` | `/api/v1/anomalies` | `station_id?`, `decision?`, `severity?`, `limit?` | `PaginatedResponse<AnomalyEventRecord>` | Network Overview, Live Monitoring, Historical Analysis |
| `anomaliesApi.getAnomaly` | `GET` | `/api/v1/anomalies/{event_id}` | `event_id: string` (path) | `AnomalyEventRecord` | Anomaly Investigation |
| `anomaliesApi.getAnomalyExplanation` | `GET` | `/api/v1/anomalies/{event_id}/explanation` | `event_id: string` (path) | `ExplanationSummary` | Anomaly Investigation |
| `healthApi.getStationHealth` | `GET` | `/api/v1/stations/{station_id}/health` | `station_id: string` (path) | `SensorHealthSummary` | Station Details, Sensor Health |
| `healthApi.getAllStationsHealth` | `GET` | `/api/v1/stations/{station_id}/health` (batch) | None | `Array<SensorHealthSummary>` | Sensor Health, Sidebar |
| `correctionsApi.getCorrections` | `GET` | `/api/v1/corrections` | `station_id?`, `status?`, `target_variable?`, `limit?` | `PaginatedResponse<CorrectionRecommendation>` | Correction Review, Anomaly Investigation |
| `correctionsApi.getCorrection` | `GET` | `/api/v1/corrections/{observation_id}` | `observation_id: string` (path) | `CorrectionRecommendation` | Correction Review |
| `correctionsApi.reviewCorrection` | `POST` | `/api/v1/corrections/{observation_id}/review` | `action: 'ACCEPT' \| 'REJECT' \| 'FLAG'`, `note?` | `{ status: string, message: string }` | Correction Review |
| `systemApi.getSystemHealth` | `GET` | `/api/v1/system/health` | None | `SystemHealthStatus` | System Status, TopBar |
| `systemApi.getLiveStatus` | `GET` | `/api/v1/live/status` | None | `{ status, operational_mode, active_source }` | TopBar, System Status |
| `systemApi.triggerImmediatePoll` | `POST` | `/api/v1/live/poll-now` | None | `{ status, stations_polled }` | Live Monitoring, TopBar |
| `replayApi.getReplayStatus` | `GET` | `/api/v1/replay/status` | None | `ReplayStatus` | System Status, TopBar Demo Controller |
| `replayApi.stepReplay` | `POST` | `/api/v1/replay/step?count={n}` | `count: number` (query) | `ReplayStatus` | System Status, TopBar Demo Controller |
| `replayApi.resetReplay` | `POST` | `/api/v1/replay/reset` | None | `ReplayStatus` | System Status, TopBar Demo Controller |

---

## 2. WebSocket Streaming Contract

| Stream Endpoint | Protocol | Inbound Events Handled | Cache Group Invalidation |
|---|---|---|---|
| `ws://{host}/ws/stream` or `/api/v1/ws/stream` | RFC 6455 UTF-8 JSON Envelope (`schema_version: "1.0"`) | `observation.updated`<br>`anomaly.created`<br>`health.updated`<br>`correction.created`<br>`station.status_changed`<br>`system.status_changed` | `['stations']`<br>`['anomalies']`<br>`['corrections']`<br>`['system']`<br>`['replay']` |

---

## 3. Switching Between Mock and Production Backend

To point this frontend at your running FastAPI backend:

1. Open `.env` (or copy `.env.example` to `.env.local`):
   ```env
   VITE_API_BASE_URL=http://localhost:8000/api/v1
   VITE_WS_URL=ws://localhost:8000/ws/stream
   VITE_USE_MOCK_DATA=false
   ```
2. Restart the Vite dev server (`npm run dev`).
3. The API client will dispatch real HTTP and WebSocket calls to the FastAPI backend without altering any React page components or TanStack Query hooks.
