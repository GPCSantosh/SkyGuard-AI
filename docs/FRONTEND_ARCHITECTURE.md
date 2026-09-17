# SkyGuard AI — Frontend Architecture Specification

## 1. Overview
The SkyGuard AI Frontend is a high-density, mission-critical meteorological operations center and enterprise observability platform built for real-time Automated Weather Station (AWS) network telemetry, anomaly investigation, sensor reliability scoring, and human-in-the-loop advisory correction review.

---

## 2. Technology Stack & Frameworks

- **UI Framework**: React 18 with TypeScript in strict mode
- **Bundler & Dev Server**: Vite 5 with `@vitejs/plugin-react`
- **Client Routing**: React Router v6 with declarative nested layout routes
- **Server State & Caching**: TanStack Query (React Query v5) with automated query invalidation and configurable polling fallbacks
- **Data Visualization**: Recharts v2 with linear interpolation, zero artificial spline distortion, synchronized cursors (`syncId`), and missing-value gap preservation
- **Geospatial Mapping**: React-Leaflet & Leaflet with custom SVG status marker pins and OpenStreetMap tile layers styled for dark operations center consoles
- **Styling**: Tailwind CSS v3 with custom design system tokens (`--canvas`, `--surface-*`, `--border-*`, `--ops-*`) and JetBrains Mono monospace telemetry typography
- **Iconography**: Lucide React

---

## 3. Directory & Component Architecture

```
frontend/src/
├── api/                  # Centralized, type-safe API client functions
│   ├── client.ts         # Base fetch wrapper & ApiError handler
│   ├── stations.ts       # /stations, /stations/:id/history, /stations/:id/health
│   ├── anomalies.ts      # /anomalies, /anomalies/:id, /anomalies/:id/explanation
│   ├── health.ts         # Sensor health query functions
│   ├── corrections.ts    # /corrections, /corrections/:id
│   ├── system.ts         # /system/health, /replay/status
│   └── replay.ts         # /replay/step control functions
│
├── hooks/                # TanStack Query custom hooks
│   ├── useStations.ts    # Station metadata, history, and health hooks
│   ├── useAnomalies.ts   # Anomaly queue & explainability package hooks
│   ├── useHealth.ts      # Multi-component health trend hooks
│   ├── useCorrections.ts # Advisory correction recommendations query hooks
│   ├── useSystem.ts      # Subsystem health & replay step mutations
│   └── useRealtimeStream.ts # Real-time connection, heartbeat, and freshness state
│
├── layouts/              # Shell and navigational containers
│   ├── AppLayout.tsx     # Shell composing TopBar, Sidebar, and View Canvas
│   ├── TopBar.tsx        # 40px fixed bar with live UTC clock, alert count & freshness
│   └── Sidebar.tsx       # 220px/48px collapsible navigation with severity-sorted station list
│
├── components/           # 15 Reusable domain & state components
│   ├── StationStatus.tsx           # Status badge (ACTIVE, DEGRADED, OFFLINE)
│   ├── SeverityBadge.tsx           # Severity indicator (INFO, LOW, MEDIUM, HIGH, CRITICAL)
│   ├── DecisionBanner.tsx          # Flagship sticky decision banner with trigger codes & metadata
│   ├── DataFreshnessIndicator.tsx  # Live stream polling cadence & freshness badge
│   ├── MetricTable.tsx             # Dense sortable table with customizable columns
│   ├── WeatherTrendChart.tsx       # Recharts time series with syncId & empty state handling
│   ├── AnomalyTimeline.tsx         # Anomaly episode milestone reconstruction timeline
│   ├── EvidencePanel.tsx           # 4-tier structured operational evidence hierarchy
│   ├── ShapContributionPlot.tsx    # Horizontal SHAP feature attribution with directional impact
│   ├── NeighborComparison.tsx      # Geodesic spatial cross-validation table
│   ├── HealthScore.tsx             # Plain 0-100 Health Index with trend indicator
│   ├── HealthTrend.tsx             # 5-component breakdown and parameter status
│   ├── AlertList.tsx               # Active anomaly feed
│   ├── NetworkMap.tsx              # Leaflet GIS layer with severity markers & neighbor links
│   ├── SystemStatus.tsx            # Approved Component Status Table
│   └── StateFeedback.tsx           # LoadingSkeleton, ErrorState, EmptyState, DegradedModeBanner
│
├── utils/                # Pure formatting and data transformation helpers
│   └── formatters.ts     # Parameter-specific formatting (temperature, humidity, pressure, coords)
│
├── pages/                # 8 Primary Application Screens
│   ├── NetworkOverviewPage.tsx      # /network (Network Overview)
│   ├── LiveMonitoringPage.tsx       # /live (Live Telemetry & Attention Sparklines)
│   ├── StationDetailsPage.tsx       # /stations/:stationId (65/35 Synchronized Charts)
│   ├── AnomalyInvestigationPage.tsx # /anomalies/:eventId (Flagship Root-Cause Drilldown)
│   ├── SensorHealthPage.tsx         # /health (Sensor Reliability & Maintenance Matrix)
│   ├── CorrectionReviewPage.tsx     # /corrections (Advisory Human-in-the-Loop Review)
│   ├── HistoricalAnalysisPage.tsx   # /history (Full-Width Sequence & Event Log)
│   └── SystemStatusPage.tsx         # /system (Subsystem Observability & Replay Simulator)
│
├── types/                # Domain TypeScript contracts matching FastAPI schemas
│   ├── api.ts            # WeatherObservation, AnomalyRecord, ExplanationSummary, etc.
│   └── events.ts         # WebSocketEnvelope, EventType, payload contracts
│
├── App.tsx               # Client router & QueryClientProvider setup
├── main.tsx              # Application entry point
└── index.css             # Tailwind base, dark palette variables & Leaflet overrides
```

---

## 4. Application Routes

| Path | Screen Name | Key Operational Responsibility |
|---|---|---|
| `/network` | **Network Overview** | Network status strip, interactive GIS Leaflet station map, active anomaly stream, network telemetry matrix table. |
| `/live` | **Live Monitoring** | High-density sortable telemetry matrix, multi-criteria filtering (status, health, station search), sparkline strip for stations requiring attention. |
| `/stations/:stationId` | **Station Details** | 65/35 split view: 3 synchronized time-series charts (Temperature, Humidity, Pressure) with `syncId`, station coordinates, topographic neighbors, and reliability breakdown. |
| `/anomalies/:eventId` | **Anomaly Investigation** | Flagship root-cause screen: Decision Banner, Observed vs Expected cards, 4-tier Evidence Hierarchy, SHAP Model Contribution table, Spatial Cross-Validation, and Operator SOP Action list. |
| `/health` | **Sensor Health** | Network health rankings, 0-100 Sensor Health Index with disclaimer, 5-component breakdown (Anomaly, QC, Communication, Stability, Spatial), parameter health, and maintenance recommendations. |
| `/corrections` | **Correction Review** | Non-destructive review queue with immutable raw telemetry notice banner, advisory estimates, uncertainty bands, scientific rationale, and human-in-the-loop acknowledgement controls. |
| `/history` | **Historical Analysis** | Full-width main sequence chart with brush/zoom, synchronized humidity/pressure charts, station switcher, time window filters, and historical anomaly log. |
| `/system` | **System Status** | Subsystem status grid (Database, Model, Topology, Simulator, Latency), pipeline execution latency profile, and stream replay simulation stepping controls. |

---

## 5. Anti-Slop Design Principles Enforced

1. **Zero Decorative AI Fluff**: No glowing neon cards, no purple AI gradient washes, no 3D robot or cloud illustrations.
2. **Tables Over Cards**: Information-dense tables are used for station metrics, anomaly feeds, and feature contributions instead of oversized card grids.
3. **Plain Scoring**: Sensor Health is displayed as clean numbers (`80/100 HEALTHY ↓ STABLE`) rather than radial gauges or spider charts.
4. **Synchronized Linear Charts**: All time series use linear interpolation (no smooth spline distortion) and preserve missing value gaps without fabricating data points.
5. **Clear Semantics**: Red, amber, and emerald colors are reserved strictly for operational alerting and quality statuses.
