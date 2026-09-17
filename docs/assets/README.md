# SkyGuard AI — Dashboard & Demo Screenshot Assets

This directory hosts high-resolution UI captures and visual artifacts for the SkyGuard AI documentation and root `README.md`.

## Recommended Asset Inventory

| Filename | Dimensions | Description / Primary UI View |
| :--- | :--- | :--- |
| `dashboard-overview.png` | 1920x1080 | **Network Overview**: Full GIS map, live station markers, network health matrix, and active anomaly alerts. |
| `live-monitoring.png` | 1920x1080 | **Live Monitoring**: Real-time multi-station observation feed with latency indicators and delivery status. |
| `station-details.png` | 1920x1080 | **Station Details**: Single-station parameter time-series, diurnal cycle overlay, and historical records. |
| `anomaly-investigation.png` | 1920x1080 | **Anomaly Investigation**: TreeSHAP waterfall feature contributions, spatial neighborhood comparison, and natural language summary. |
| `sensor-health.png` | 1920x1080 | **Sensor Health**: 5-channel longitudinal reliability indices (0–100), degradation trend curves, and SOP maintenance cards. |
| `correction-review.png` | 1920x1080 | **Correction Review**: Advisory non-destructive imputation overlay with confidence bounds and raw telemetry comparison. |
| `historical-analysis.png` | 1920x1080 | **Historical Analysis**: Long-term climatological anomaly distribution, seasonal trends, and QC rejection audits. |
| `system-status.png` | 1920x1080 | **System & Source Health**: Upstream provider state machine, database connectivity, and WebSocket stream health. |
| `demo-thumbnail.png` | 1280x720 | **Demo Presentation Thumbnail**: High-impact preview banner for the 8–12 minute hackathon walkthrough video. |

## Capturing UI Screenshots
1. Start the complete stack: `docker compose up -d` or run backend and frontend locally.
2. Load the demo replay scenario: `POST /api/v1/replay/load-scenario {"scenario_id": "flagship_narrative"}`.
3. Advance to key scenario steps (e.g. Step 8 for isolated spike, Step 28 for regional squall).
4. Save browser viewport captures into this directory with the exact filenames listed above.
