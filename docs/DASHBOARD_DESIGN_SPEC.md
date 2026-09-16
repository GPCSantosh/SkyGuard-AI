# SkyGuard AI — Dashboard Design Specification
# Meteorological Operations Center

**Version**: 1.0  
**Status**: Design Phase — No Frontend Code  
**Scope**: UX Architecture, Page Layouts, Component System, Design System

---

## Table of Contents

1. [Information Architecture](#1-information-architecture)
2. [Page Layouts](#2-page-layouts)
3. [Component System](#3-component-system)
4. [Design System](#4-design-system)
5. [Responsive Behavior](#5-responsive-behavior)
6. [Accessibility](#6-accessibility)
7. [Visual Hierarchy](#7-visual-hierarchy)
8. [Interaction Patterns](#8-interaction-patterns)
9. [Data Visualization Rules](#9-data-visualization-rules)
10. [Dashboard Anti-Slop Rules](#10-dashboard-anti-slop-rules)

---

## 1. Information Architecture

### 1.1. Navigation Model

**Layout**: Fixed left sidebar + top status bar + main content area.

```
┌──────────────────────────────────────────────────────────────────────┐
│  TOP BAR: SkyGuard AI  |  Network Health  |  Active Alerts  |  Time │
├───────────┬──────────────────────────────────────────────────────────┤
│           │                                                          │
│  SIDEBAR  │                   MAIN CONTENT AREA                     │
│  (fixed)  │                                                          │
│           │                                                          │
│  Nav      │                                                          │
│  Links    │                                                          │
│           │                                                          │
│  Station  │                                                          │
│  List     │                                                          │
│           │                                                          │
└───────────┴──────────────────────────────────────────────────────────┘
```

**Sidebar width**: 220px (collapsed: 48px icon-only)  
**Top bar height**: 40px  
**Content area**: Fluid, max-width 1600px centered

### 1.2. Sidebar Navigation

```
┌─────────────────────┐
│ ◈ SkyGuard AI       │  ← Product mark. No decorative logo glyph.
├─────────────────────┤
│ ● Network Overview  │  ← Primary landing page
│   Live Monitoring   │
│   Station Details   │
│   Anomaly Invest.   │
│   Sensor Health     │
│   Correction Review │
│   Historical Anal.  │
│   System Status     │
├─────────────────────┤
│ STATIONS            │  ← Section label (muted, uppercase, 10px)
│  AWS_001 ● HEALTHY  │  ← Per-station status pill
│  AWS_007 ▲ WARN     │
│  AWS_014 ✕ CRITICAL │
│  AWS_019 — OFFLINE  │
│  ... (scrollable)   │
└─────────────────────┘
```

- Station list in sidebar is always visible. Sorted by severity descending.
- Active nav item has a 2px left border accent in the page's semantic color.
- No accordion. No tooltips on every icon. Labels always visible unless fully collapsed.

### 1.3. Top Status Bar

```
SkyGuard AI          Network: 18/20 OPERATIONAL    ▲ 3 ALERTS    14:23:07 UTC
```

- Left: product name + current page breadcrumb.
- Center: live network health summary (stations operational / total).
- Right: active alert count badge + UTC clock (monospace).
- Bar color shifts to amber if ≥ 1 HIGH alert, red if ≥ 1 CRITICAL alert.

### 1.4. Page Hierarchy

```
Network Overview
└── Station Details (drill-down via map or station list)
    ├── Anomaly Investigation (drill-down from anomaly event)
    ├── Sensor Health (drill-down from health score)
    └── Correction Review (drill-down from correction recommendation)

Live Monitoring
└── Station Details (click row)

Historical Analysis
└── Station Details (cross-link)

System Status
└── (no drill-down, terminal page)
```

---

## 2. Page Layouts

### 2.1. Network Overview

**Purpose**: Answer in ≤ 5 seconds — how many stations, which need attention, where are the anomalies?

**Layout**:

```
┌──── TOP ROW: Network Status Strip ───────────────────────────────────┐
│  20 Stations  |  16 Nominal  |  2 Warning  |  1 Critical  |  1 Offline │
│  Data Age: Last update 48s ago                                        │
└──────────────────────────────────────────────────────────────────────┘

┌──── LEFT (55%) ──────────────────────┬─── RIGHT (45%) ───────────────┐
│                                      │                               │
│  NETWORK MAP                         │  ACTIVE ALERTS                │
│  (Geospatial AWS network)            │  ─────────────────────────    │
│                                      │  ✕ AWS_014  CRITICAL          │
│  [India region map with station      │    PROBABLE_SENSOR_ANOMALY    │
│   dots, severity-colored rings,      │    Temperature spike 52.1°C   │
│   neighbor connection lines for      │    2 min ago  →               │
│   active anomaly context]            │  ─────────────────────────    │
│                                      │  ▲ AWS_007  HIGH              │
│                                      │    LOCAL_SPATIAL_ISOLATION    │
│                                      │    Pressure -12.3 hPa dev.    │
│                                      │    7 min ago  →               │
│                                      │  ─────────────────────────    │
│                                      │  ▲ AWS_019  OFFLINE           │
│                                      │    Telemetry gap: 34 min      │
│                                      │    Last seen 14:07:22 UTC  →  │
│                                      │                               │
│                                      │  REGIONAL CONTEXT             │
│                                      │  ─────────────────────────    │
│                                      │  NW Cluster: NORMAL (6 stn.)  │
│                                      │  S Cluster: 1 WARN (4 stn.)   │
│                                      │  E Cluster: NOMINAL (5 stn.)  │
│                                      │  Peninsular: NOMINAL (5 stn.) │
│                                      │                               │
└──────────────────────────────────────┴───────────────────────────────┘

┌──── BOTTOM: Station Status Table ────────────────────────────────────┐
│ Station  | Status   | Temp(°C) | RH(%) | P(hPa)  | Health | Updated  │
│ AWS_001  | ● NORMAL | 28.4     | 62    | 1013.2  | 97     | 12s ago  │
│ AWS_007  | ▲ HIGH   | 31.1     | 71    | 1001.4  | 74     | 7m ago   │
│ AWS_014  | ✕ CRIT.  | 52.1*    | 44    | 1015.1  | 43     | 2m ago   │
│ AWS_019  | — OFFL.  | —        | —     | —       | 61     | 34m ago  │
│ ...                                                                   │
└──────────────────────────────────────────────────────────────────────┘
```

**Network Status Strip** (top):
- NOT 12 KPI cards. A single compact horizontal strip with 5 data fields.
- Color fills the strip edge (green → amber → red) based on worst active severity.
- `Data Age` shows seconds since last observation received by the backend.

**Network Map** (left panel):
- Station dots sized by severity (larger = worse, not decorative).
- Color: Green (Normal), Amber (Warning), Red (Critical), Gray (Offline).
- Thin gray lines between neighbors active during anomaly investigation.
- Clicking a dot opens Station Details.

**Active Alerts** (right panel):
- Plain list. No large cards. Each entry: station ID + severity badge + decision label + primary metric deviation + age + arrow link.
- Sorted by severity then recency.
- Empty state: "No active alerts. Network nominal."

**Station Status Table** (bottom):
- All 20 stations. Sortable. Anomalous cell values highlighted with background tint only.
- Asterisk (*) on anomalous cell value. Row gets 2px left-border accent, not full-row color fill.
- Clicking a row navigates to Station Details.

---

### 2.2. Live Monitoring

**Purpose**: Real-time operations view. Identify degrading situations as they develop.

**Layout**:

```
┌──── FILTER BAR ──────────────────────────────────────────────────────┐
│ All Stations ▼   |   Status: All ▼   |   Parameter: All ▼   |  ↺ Live │
└──────────────────────────────────────────────────────────────────────┘

┌──── LIVE TELEMETRY TABLE ────────────────────────────────────────────┐
│ Station | Anomaly  | T (°C) | RH (%) | P (hPa) | Health | QC  | Age  │
│ ─────── | ──────── | ────── | ────── | ─────── | ────── | ─── | ──── │
│ AWS_001 | NORMAL   | 28.4   |  62    | 1013.2  |  97    | ●   | 12s  │
│ AWS_003 | NORMAL   | 29.1   |  58    | 1014.0  |  94    | ●   | 18s  │
│ AWS_007 | ▲ HIGH   | 31.1*  |  71    | 1001.4* |  74    | ○   | 7m   │
│ AWS_014 | ✕ CRIT.  | 52.1*  |  44    | 1015.1  |  43    | ✕   | 2m   │
│ AWS_019 | — OFFL.  | —      |  —     | —       |  61    | —   | 34m  │
│ ...                                                                   │
└──────────────────────────────────────────────────────────────────────┘

┌──── SPARKLINE STRIP (flagged stations only) ─────────────────────────┐
│  AWS_007: T [30-min mini chart] | RH trend | P trend                 │
│  AWS_014: T [30-min mini chart] | RH trend | P trend                 │
└──────────────────────────────────────────────────────────────────────┘
```

**Live Telemetry Table**:
- `QC` column: ● Pass, ○ Warning, ✕ Fail/Missing, — Offline.
- `Age` column: amber > 5 min, red > 15 min.
- Asterisk (*) on flagged cell value. 2px left-border accent on anomalous rows only.

**Sparkline Strip**:
- Visible only for flagged stations (not all 20).
- 30-minute mini time-series. No axis labels. Tooltip on hover.
- Click to expand to Station Details.

---

### 2.3. Station Details

**Purpose**: Complete operational profile of one AWS station.

**Layout**:

```
┌──── STATION HEADER ──────────────────────────────────────────────────┐
│  AWS_007  Jaipur, Rajasthan   27.1767°N  75.7500°E  el. 431m        │
│  Status: ▲ WARNING | Health: 74 GOOD | Last Update: 14:16:43 UTC    │
└──────────────────────────────────────────────────────────────────────┘

┌──── LEFT (65%) ──────────────────────────┬── RIGHT (35%) ────────────┐
│  CURRENT READINGS                        │  STATION INFO             │
│  Temperature     31.1°C   ▲ Anomaly      │  Station ID: AWS_007      │
│  Relative Hum.   71 %     ● Normal       │  Network: IMDAWS          │
│  Sea-Level P.    1001.4   ▲ -11.8 hPa   │  Hardware: Vaisala WXT530 │
│                  deviation from nbrs     │  Elevation: 431 m         │
│                                          │  Commissioned: 2023-04-10 │
│  TIME-SERIES CHARTS                      │                           │
│  [T chart — 24h, raw + imputed dashed]   │  NEIGHBORS                │
│  [RH chart — 24h, synced cursor]         │  AWS_002  18.4km  ● OK    │
│  [P chart — 24h, synced cursor]          │  AWS_011  24.1km  ● OK    │
│                                          │  AWS_018  31.0km  ● OK    │
│  ANOMALY TIMELINE                        │                           │
│  [Horizontal swimlane — color bands      │  DECISION HISTORY         │
│   for each episode type]                 │  14:16:43  WARN HIGH      │
│                                          │  14:11:37  WARN HIGH      │
│  HEALTH TREND                            │  14:06:22  NORMAL         │
│  [Health score area chart — 30 days]     │  13:58:44  NORMAL         │
└──────────────────────────────────────────┴───────────────────────────┘
```

**Station Header**: Station ID + human location + geodetic coordinates (monospace) + elevation on one line. Status + health + timestamp on second line. No giant title.

**Time-Series Charts**: Three synchronized charts (T, RH, P). Solid raw line. Dashed imputed line. Faint anomaly episode bands. Synchronized crosshair. Window selector: 6h / 24h / 7d / 30d.

**Anomaly Timeline**: Horizontal swimlane. Click a band → Anomaly Investigation.

**Decision History**: Compact scrollable list. Click a row → Anomaly Investigation.

---

### 2.4. Anomaly Investigation

**Purpose**: Flagship screen. Complete traceable evidence record for one anomaly decision.

**Layout**:

```
┌──── DECISION BANNER ─────────────────────────────────────────────────┐
│  PROBABLE_SENSOR_ANOMALY                      Severity: HIGH          │
│  AWS_007  Jaipur, Rajasthan  |  14:16:43 UTC  |  Duration: 14 min   │
│  Engine: hybrid_v1.0.0  |  Model: isolation_forest_v1  |  TREE_SHAP  │
└──────────────────────────────────────────────────────────────────────┘

┌──── OBSERVED vs EXPECTED ────────────────────────────────────────────┐
│ Parameter   | Observed | Neighbor Median | Deviation  | Status       │
│ Temperature | 31.1 °C  | 28.3 °C         | +2.8 °C    | ▲ ANOMALY   │
│ Humidity    | 71 %     | 68 %            | +3 %       | ● NORMAL     │
│ Pressure    | 1001.4   | 1013.2          | -11.8 hPa  | ✕ ANOMALY   │
└──────────────────────────────────────────────────────────────────────┘

┌──── LEFT (60%) ──────────────────────────┬── RIGHT (40%) ────────────┐
│  EVIDENCE PANEL                          │  SPATIAL CONTEXT          │
│                                          │  [Mini map: target +      │
│  [Tier 1] Direct Evidence                │   neighbors with values]  │
│    Observed: 31.1°C @ 14:16:43 UTC       │                           │
│    QC Status: VALID  |  Gap: 0s          │  Target:  AWS_007 31.1°C  │
│                                          │  AWS_002: 28.1°C (18km)   │
│  [Tier 2] ML Model Evidence              │  AWS_011: 27.9°C (24km)   │
│    Anomaly Score: 0.81  Threshold: 0.58  │  AWS_018: 28.8°C (31km)   │
│    Method: TREE_SHAP                     │                           │
│                                          │  Consensus: LOCAL_ONLY    │
│    Feature Contributions:                │  3/3 neighbors disagree   │
│    temp_rate_of_change    ████▓▓▓░       │                           │
│    temp_zscore_1h         █████░░░       │  EPISODE TIMELINE         │
│    pressure_delta_nbr     ███▓▓░░░       │  Onset:   14:02:43 UTC    │
│    humidity_consistency   ██▓░░░░░       │  Peak:    14:09:17 UTC    │
│    temp_diurnal_residual  ██░░░░░░       │  Current: 14:16:43 UTC    │
│    (direction labels per bar)            │  Duration: 14 min active  │
│                                          │                           │
│  [Tier 3] Contextual Evidence            │  RECOMMENDED ACTION       │
│    Rate of Change: +1.8°C/min            │  Inspect sensor hardware  │
│    Flatline count: 0                     │  and wiring. Validate     │
│    Spatial isolation: LOCAL_ONLY         │  against portable ref.    │
│    Neighbor agreement: 0/3 agree         │  instrument or redundant  │
│    Thermodynamic: PASS                   │  sensor.                  │
│                                          │                           │
│  [Tier 4] Operational Interpretation     │  CORRECTION               │
│    PROBABLE_SENSOR_ANOMALY               │  Candidate: 28.4 °C       │
│    Reason: LOCAL_SPATIAL_ISOLATION,      │  Method: SPATIAL_IDW      │
│            ML_HIGH_ANOMALY_SCORE         │  Uncertainty: ±0.6°C      │
│                                          │  Quality: HIGH            │
│    Operator Summary:                     │  Status: REVIEW_REQUIRED  │
│    "SHAP identifies temperature rate     │  [Accept] [Reject] [Flag] │
│     of change as the leading model       │                           │
│     feature contribution. The station   │  ⚠ Source obs. immutable. │
│     is isolated from all 3 neighbors."  │                           │
│                                          │                           │
│  AUDIT TRAIL                             │                           │
│  model_version:    isolation_forest_v1   │                           │
│  feature_version:  v1.0.0               │                           │
│  engine_version:   hybrid_v1.0.0         │                           │
│  method:           TREE_SHAP             │                           │
│  generated_at:     2026-09-17T08:46:43Z  │                           │
└──────────────────────────────────────────┴───────────────────────────┘
```

**Decision Banner**: Full-width. Color-coded left border by severity. Decision + severity + station + timestamp + episode duration on rows 1–2. Version metadata (engine, model, explanation method) on row 3, muted. Always visible.

**Observed vs Expected**: Compact three-row table — all parameters. Neighbor median derived from causal spatial comparator. Never fabricated.

**Evidence Panel** (left, scrollable):
- Four tiers rendered in sequence. All tiers visible simultaneously (no accordion hiding).
- SHAP bar chart: horizontal bars sorted by magnitude. Direction labels per bar. No false probability language. No "proves fault" language.
- Audit trail at the bottom. Monospace. Always present.

**Spatial Context** (right):
- Mini static map. Neighbor dots labeled with station ID + current parameter reading.
- Consensus classification text below map.

**Episode Timeline** (right):
- Onset → Peak → Recovery (or "Active") with UTC timestamps and duration.

**Correction** (right):
- Only rendered when status is not `NO_CORRECTION_RECOMMENDED`.
- Immutability warning is non-dismissable.

---

### 2.5. Sensor Health

**Purpose**: Degradation monitoring across stations and individual sensor channels.

**Layout**:

```
┌──── NETWORK HEALTH SUMMARY STRIP ────────────────────────────────────┐
│ Network Avg: 81.4 GOOD  |  5 HEALTHY  |  9 GOOD  |  4 ATTENTION  |  │
│ 1 DEGRADED  |  1 CRITICAL  |  Time Window: 7d ▼                     │
└──────────────────────────────────────────────────────────────────────┘

┌──── STATION HEALTH TABLE ────────────────────────────────────────────┐
│ Station  | Overall | Anomaly | Data Q. | Comm.  | Temporal | Spatial │
│ AWS_001  | 97 ●    | 99      | 100     | 100    | 96       | 95      │
│ AWS_007  | 74 ○    | 68      | 90      | 100    | 72       | 58      │
│ AWS_014  | 43 ✕    | 31      | 80      | 88     | 22       | 44      │
│ ...                                                                   │
└──────────────────────────────────────────────────────────────────────┘

┌──── SELECTED STATION DETAIL ─────────────────────────────────────────┐
│  AWS_014  |  Health: 43 DEGRADED  |  Trend: ▼ DEGRADING             │
│  Maintenance Recommendation: PRIORITY_INSPECTION                     │
│                                                                      │
│  Component Breakdown:                                                │
│  Anomaly Health:       31  ████░░░░░░░░░░░░░░░░░░░░                 │
│  Data Quality Health: 80  █████████████░░░░░░░░░░                   │
│  Comm. Health:        88  ██████████████░░░░░░░░                    │
│  Temporal Stability:  22  ████░░░░░░░░░░░░░░░░░░                    │
│  Spatial Consistency: 44  ███████░░░░░░░░░░░░░                      │
│                                                                      │
│  Parameter Channel Health:                                           │
│  Temperature (°C):      38  DEGRADED   ↓ Trending worse             │
│  Relative Humidity (%): 85  GOOD       → Stable                     │
│  Pressure (hPa):        72  ATTENTION  ↓ Trending worse             │
│                                                                      │
│  Health Trend (30-day):                                              │
│  [Area chart — health score over 30 days. Status band               │
│   background tints: green 90–100, amber 75–89, etc.]                │
│                                                                      │
│  NOTE: Health Index is an empirical reliability indicator. It is    │
│  NOT a failure probability or percentage chance of hardware failure. │
└──────────────────────────────────────────────────────────────────────┘
```

**Network Health Summary Strip**: Single row. Band counts. Time window selector. No per-component KPI cards.

**Station Health Table**: All stations. Six numeric columns. Cell color matches status band. Clicking a row expands the detail panel.

**Component Breakdown**: Horizontal bar per component. Color + score + status band label.

**Parameter Channel Health**: Three rows (T, RH, P). Explicitly separated from component health — different scoring subsystem.

**Health Trend Chart**: Area chart. 0–100 Y-axis. Background zone tints per status band.

**Scientific disclaimer**: Always visible. Required by SENSOR_HEALTH.md principle. Not collapsible.

---

### 2.6. Correction / Data Quality Review

**Purpose**: Transparent human oversight of correction recommendations. Never silently replacing source data.

**Layout**:

```
┌──── FILTER BAR ──────────────────────────────────────────────────────┐
│ Station: All ▼  | Status: REVIEW_REQUIRED ▼  | Parameter: All ▼     │
│ Date Range: Last 7 days ▼   | Sort: Newest first ▼                  │
└──────────────────────────────────────────────────────────────────────┘

┌──── REVIEW QUEUE TABLE ──────────────────────────────────────────────┐
│ Station | Time (UTC)  | Param | Observed | Recommended | Status | Act│
│ AWS_014 | 14:16:43    | T(°C) | 52.1     | 28.4 ±0.6   | ● REQ  | … │
│ AWS_007 | 13:47:22    | P(hPa)| 1001.4   | 1012.9 ±1.1 | ○ CAND | … │
│ AWS_003 | 10:22:11    | RH(%) | —        | 64.2 ±4.1   | ☰ IMP  | … │
│ ...                                                                   │
└──────────────────────────────────────────────────────────────────────┘

┌──── SELECTED RECORD DETAIL ──────────────────────────────────────────┐
│  AWS_014  |  Temperature  |  14:16:43 UTC  |  REVIEW_REQUIRED        │
│                                                                      │
│  Values:                                                             │
│    Source Observation (IMMUTABLE):  52.1°C                           │
│    Recommended Estimate:            28.4°C  ±0.6°C (95% CI)         │
│    Method:         SPATIAL_IDW_CONSENSUS                             │
│    Method Quality: HIGH                                              │
│    Certainty Index: 0.87                                             │
│    Supporting Neighbors: 3 (AWS_002, AWS_011, AWS_018)               │
│                                                                      │
│  Evidence Chain:                                                     │
│    Upstream Decision:  PROBABLE_SENSOR_ANOMALY (HIGH)                │
│    Reason Codes:  ML_HIGH_ANOMALY_SCORE, LOCAL_SPATIAL_ISOLATION     │
│    Spatial consensus:  3/3 neighbors agree within ±2.0°C            │
│    ML Anomaly Score:   0.81 (threshold 0.58)                         │
│    Sensor Health:      43 DEGRADED                                   │
│    Thermodynamic:      PASS (all physical constraints met)           │
│                                                                      │
│  Operator Actions:                                                   │
│    [✓ Accept]  [✕ Reject]  [⚑ Flag for Senior Review]               │
│    Operator Note (optional): _________________________               │
│                                                                      │
│  ⚠ Accepting records the recommendation in the audit log.           │
│    Source observations (52.1°C) are never modified.                  │
└──────────────────────────────────────────────────────────────────────┘
```

**Status column codes**: ● REVIEW_REQUIRED, ○ CORRECTION_CANDIDATE, ☰ IMPUTED, ✓ ACCEPTED, ✕ REJECTED.

**Immutability warning**: Non-dismissable. Always visible when a record is selected.

---

### 2.7. Historical Analysis

**Purpose**: Time-windowed retrospective analysis of observation history and anomaly distribution.

**Layout**:

```
┌──── CONTROLS ────────────────────────────────────────────────────────┐
│ Station: AWS_007 ▼  | Parameter: Temperature ▼  |  [date] to [date] │
│ Overlay: Imputed ☑  Neighbor Median ☑  Anomaly Bands ☑             │
└──────────────────────────────────────────────────────────────────────┘

┌──── PRIMARY TIME-SERIES ─────────────────────────────────────────────┐
│  [Full-width chart — selected parameter. Brush/zoom on X-axis.]      │
│  Raw (solid) | Imputed (dashed) | Neighbor median (dotted gray)      │
│  Anomaly episode bands as background shading                         │
└──────────────────────────────────────────────────────────────────────┘

┌──── SECONDARY CHARTS (2-col) ────────────────────────────────────────┐
│  [Other two parameters, synced cursor, reduced height]               │
│  Left: RH chart         |   Right: Pressure chart                   │
└──────────────────────────────────────────────────────────────────────┘

┌──── ANOMALY SUMMARY TABLE ───────────────────────────────────────────┐
│ Time (UTC)  | Decision              | Severity | Duration | → View   │
│ 14:16:43    | PROBABLE_SENSOR_ANOM. | HIGH     | 14 min   | →        │
│ 11:33:22    | NORMAL                | INFO     | —        | →        │
└──────────────────────────────────────────────────────────────────────┘
```

**Primary Chart**: Full-width, minimum 300px height. Brush control at bottom. Anomaly bands color-coded by decision type. Secondary charts: 160px height each, synchronized cursor.

---

### 2.8. System Status

**Purpose**: Backend health, model status, pipeline diagnostics.

**Layout**:

```
┌──── SYSTEM HEALTH BANNER ────────────────────────────────────────────┐
│  Status: ● OPERATIONAL   |  Uptime: 14d 06:43:22  |  API: v1        │
└──────────────────────────────────────────────────────────────────────┘

┌──── COMPONENT STATUS TABLE ──────────────────────────────────────────┐
│ Component                    | Status      | Details                 │
│ FastAPI Backend              | ● OK        | v0.115.0                │
│ Observation Repository       | ● OK        | 20 stations, 48,291 rec │
│ ML Engine (Isolation Forest) | ● OK        | isolation_forest_v1     │
│ Hybrid Decision Engine       | ● OK        | hybrid_v1.0.0           │
│ Explainability Engine        | ● OK        | TREE_SHAP active        │
│ Sensor Health Engine         | ● OK        | Last run 14:20:00 UTC   │
│ Correction Engine            | ● OK        | 12 pending review       │
│ Spatial Context Engine       | ● OK        | 20 active stations      │
└──────────────────────────────────────────────────────────────────────┘

┌──── LATENCY METRICS ─────────────────────────────────────────────────┐
│ Pipeline Stage               | P50 (ms) | P95 (ms) | SLA Target      │
│ Total Pipeline               | 0.21 ms  | 5.89 ms  | <15 ms ● OK    │
│ Feature Extraction           | 0.08 ms  | 1.12 ms  | —               │
│ ML Inference                 | 0.04 ms  | 0.88 ms  | —               │
│ Spatial Context              | 0.03 ms  | 1.44 ms  | —               │
│ SHAP Explanation             | 0.06 ms  | 2.45 ms  | —               │
└──────────────────────────────────────────────────────────────────────┘

┌──── REPLAY STATUS ───────────────────────────────────────────────────┐
│ Replay Mode: IDLE  |  Queue: 0 packets  |  [Step] [Reset]           │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component System

All components are reusable, parameterized, and page-agnostic. No page-specific duplicates.

### 3.1. `StationStatus`

**Props**: `station_id`, `status` (NORMAL / WARNING / CRITICAL / OFFLINE), `decision`, `severity`  
**Sizes**: `sm` (sidebar), `md` (table row), `lg` (station header)

```
● AWS_007  ▲ HIGH  PROBABLE_SENSOR_ANOMALY
```

### 3.2. `SeverityBadge`

**Props**: `severity` (INFO / LOW / MEDIUM / HIGH / CRITICAL)  
**Renders**: Color-coded badge. `rounded` (4px). Never `rounded-full`.

```
▲ HIGH    ✕ CRITICAL    ● INFO
```

### 3.3. `MetricTable`

**Props**: `rows[]` = `{parameter, value, unit, state, deviation?}`  
**Renders**: Compact three-row table (T, RH, P). State icons inline. Deviation shown when anomaly active. No separate per-parameter KPI cards.

### 3.4. `WeatherTrendChart`

**Props**: `data[]`, `parameter`, `unit`, `window`, `showImputed`, `showNeighborMedian`, `syncId`  
**Renders**: Line chart with:
- Solid line = raw sensor reading (always present)
- Dashed line = imputed/recommended (when `showImputed`)
- Dotted gray = neighbor median (when `showNeighborMedian`)
- Faint background anomaly bands (8% opacity)
- Synchronized crosshair via `syncId`

### 3.5. `AnomalyTimeline`

**Props**: `episodes[]`, `window`, `selectedEpisodeId?`  
**Renders**: Horizontal swimlane. One track. Color-coded bands per episode type. Clickable. No animation.

### 3.6. `EvidencePanel`

**Props**: `explanation` (ExplanationSummary)  
**Renders**: Four-tier evidence display in sequence. All tiers visible simultaneously (no accordion).  
SHAP bar chart within this panel: horizontal bars sorted by magnitude, direction labels, no false probability language, no causation claims.

### 3.7. `NeighborComparison`

**Props**: `target`, `neighbors[]`, `parameter`, `deviation`  
**Renders**: Mini static map or list. Target value vs. neighbor values with distance labels. Consensus classification text.

### 3.8. `HealthScore`

**Props**: `score`, `status_band`, `trend`, `window`  
**Renders**: Numeric score (28px, weight 600) + status band label + trend arrow + time window label.  
**NOT** a circular gauge or radial chart.

```
74  GOOD  ↓ DEGRADING  (7d)
```

### 3.9. `HealthTrend`

**Props**: `history[]` (date + score), `window`  
**Renders**: Area chart. 0–100 Y-axis. Background zone tints per status band. No animation.

### 3.10. `AlertList`

**Props**: `alerts[]`, `maxVisible?`, `onSelect`  
**Renders**: Vertical list. Each row: `SeverityBadge` + station ID + decision + primary metric + age.  
**Empty state**: "No active alerts. Network nominal."  
**No card container per alert. Plain list items with subtle dividers.**

### 3.11. `NetworkMap`

**Props**: `stations[]` (with coordinates, status, severity), `highlightedStations?`, `neighborLinks?`  
**Renders**: Map (Leaflet or similar). Station dots colored by status. Severity reflected in dot size when anomaly active. Neighbor link lines when anomaly context is displayed. Non-decorative.

### 3.12. `DataFreshnessIndicator`

**Props**: `lastUpdateSeconds`, `expectedIntervalSeconds`  
**Renders**: Inline age text with color coding. Green (<1 interval), amber (1–3 intervals), red (>3 intervals).

```
Updated 12s ago   |   ▲ 7m ago (stale)   |   — 34m ago (offline)
```

### 3.13. `SystemStatus`

**Props**: `components[]` (name + status + detail)  
**Renders**: Table. ● OK / ▲ WARN / ✕ ERROR per component. No decorative icons.

### 3.14. `DecisionBanner`

**Props**: `decision`, `severity`, `station_id`, `timestamp`, `duration?`, `model_version`, `engine_version`, `explanation_method`  
**Renders**: Full-width horizontal banner. Color-coded left border by severity. Version metadata always shown, muted. Not collapsible.

---

## 4. Design System

### 4.1. Color Palette

**Foundation (Dark Theme)**

| Token                | Hex       | Usage                                         |
|----------------------|-----------|-----------------------------------------------|
| `--canvas`           | `#0B0F17` | Application background                        |
| `--surface-1`        | `#111827` | Primary panel / page background               |
| `--surface-2`        | `#1A2234` | Elevated card / secondary panel               |
| `--surface-hover`    | `#232D42` | Hover states on interactive elements          |
| `--border-subtle`    | `#2D3748` | Panel borders, table row dividers             |
| `--border-emphasis`  | `#3D4F6B` | Active borders, focus rings                   |
| `--text-primary`     | `#F8FAFC` | Primary content text                          |
| `--text-secondary`   | `#94A3B8` | Labels, captions, secondary metadata          |
| `--text-muted`       | `#64748B` | Timestamps, disabled text, axis labels        |

**Semantic Operational Colors**

| Semantic Role         | Hex       | Token                | Usage                                              |
|-----------------------|-----------|----------------------|----------------------------------------------------|
| Normal / Healthy      | `#10B981` | `--color-normal`     | Healthy station, nominal observation               |
| Atmospheric / Weather | `#38BDF8` | `--color-weather`    | Temperature charts, weather data lines             |
| Humidity              | `#34D399` | `--color-humidity`   | RH charts, moisture indicators                     |
| Pressure              | `#818CF8` | `--color-pressure`   | Pressure charts (muted indigo, not decorative purple)|
| Warning               | `#F59E0B` | `--color-warning`    | Suspicious observations, MEDIUM severity           |
| Critical              | `#EF4444` | `--color-critical`   | Sensor anomalies, CRITICAL severity                |
| Genuine Event         | `#6366F1` | `--color-genuine`    | POSSIBLE_GENUINE_EVENT classification              |
| Uncertain             | `#A3A3A3` | `--color-uncertain`  | UNCERTAIN classification, pending review           |
| Offline / Missing     | `#475569` | `--color-offline`    | Disconnected stations, missing telemetry           |

**Color Usage Rules**:
- Color is used only for semantic communication. Never for decoration.
- Background tints use 8–12% opacity of the semantic color.
- `--color-pressure` (muted indigo) is reserved for barometric data only.

### 4.2. Typography

**Primary Typeface**: `Inter` (Google Fonts)  
**Monospace Typeface**: `JetBrains Mono` (station IDs, coordinates, timestamps, sensor values)

| Level               | Size  | Weight | Line Height | Letter Spacing | Usage                                |
|---------------------|-------|--------|-------------|----------------|--------------------------------------|
| Display / Stat Value| 28px  | 600    | 1.1         | -0.02em        | Health score, single key metric      |
| H1 Page Title       | 18px  | 600    | 1.2         | -0.01em        | Page header (one per page)           |
| H2 Section Title    | 14px  | 600    | 1.3         | 0              | Panel and section headings           |
| H3 Subsection       | 13px  | 600    | 1.3         | 0              | Table headers, sub-panel titles      |
| Body Regular        | 13px  | 400    | 1.45        | 0              | Narrative text, operator summaries   |
| Body Small          | 12px  | 500    | 1.35        | +0.01em        | Table cells, chart axis ticks        |
| Label / Uppercase   | 10px  | 600    | 1.2         | +0.08em        | Section labels ("STATIONS")          |
| Mono / Telemetry    | 11px  | 400    | 1.2         | 0              | Timestamps, coordinates, IDs, values |

**Rules**:
- H1 titles must not consume significant vertical space. Never a centered giant heading.
- Station IDs use monospace. Human location names use sans-serif.
- Operator summary text: 13px body regular, line-height 1.45 for readability.

### 4.3. Spacing Scale

4px base grid. All spacing is a multiple of 4px.

| Token     | Value | Usage                                  |
|-----------|-------|----------------------------------------|
| `space-1` | 4px   | Icon-to-label gap, compact row padding |
| `space-2` | 8px   | Component internal gaps                |
| `space-3` | 12px  | Card internal padding                  |
| `space-4` | 16px  | Panel padding, section gap             |
| `space-6` | 24px  | Section separation                     |
| `space-8` | 32px  | Major layout divisions                 |

Panel padding: 12–16px. Table cell padding: 8px horizontal, 6px vertical. No excessive whitespace.

### 4.4. Border Radius

| Context                   | Radius |
|---------------------------|--------|
| Structural panels / cards | 4px    |
| Table cells               | 0px    |
| Buttons                   | 4px    |
| Status badges             | 4px (never `rounded-full`) |
| Input fields              | 4px    |

**Never use**: `rounded-2xl`, `rounded-3xl`, or pill/capsule shapes on structural elements.

### 4.5. Table Style

- Background: `--surface-1`
- Header background: `--surface-2`
- Header text: 12px, weight 600, uppercase, `--text-muted`
- Row dividers: 1px solid `--border-subtle`
- Row hover: background `--surface-hover`
- Selected row: 2px left border in semantic color, `--surface-hover` background
- Cell padding: `8px 12px`
- Anomalous cell: 8% opacity background tint in semantic color — not whole-row fill
- Numeric values: monospace font

### 4.6. Chart Style

- Background: `--surface-1`
- Grid lines: 1px solid `#1F2937`, `dasharray="3 3"`, 15% opacity
- Axis line: `--border-subtle`
- Axis tick labels: 11px, `--text-muted`, monospace for values
- Raw reading line: 1.5px solid, semantic color
- Imputed line: 1.5px dashed, 70% opacity of semantic color
- Neighbor median: 1px dotted, `--text-muted`
- Anomaly band fill: 8% opacity of severity color
- Tooltip: `--surface-2` background, 1px border `--border-emphasis`, 8px padding, 4px radius
- No chart titles inside SVG. No drop shadows on chart elements. No smooth/spline interpolation.

### 4.7. Badge Style

```
CRITICAL → bg: #450A0A   text: #FCA5A5  border: 1px #7F1D1D
HIGH     → bg: #431407   text: #FDBA74  border: 1px #7C2D12
MEDIUM   → bg: #451A03   text: #FDE68A  border: 1px #78350F
LOW      → bg: #0C1A28   text: #7DD3FC  border: 1px #164E63
INFO     → bg: #0F172A   text: #94A3B8  border: 1px #334155
```

Status dots: `#10B981` Normal, `#F59E0B` Warning, `#EF4444` Critical, `#475569` Offline.

### 4.8. Alert Style

- List items, not cards.
- No shadow. Border radius: 4px.
- Left border 3px in severity color.
- Padding: 8px 12px.
- Never modal or blocking for non-critical operational alerts.

### 4.9. Navigation and Sidebar

- Expanded: 220px. Collapsed: 48px icon-only.
- Background: `--surface-1` with right border `--border-subtle`.
- Nav item height: 36px. Padding: 0 12px.
- Active item: 2px left border `--color-weather`, background `--surface-2`.
- Section labels: 10px, uppercase, weight 600, `--text-muted`.

### 4.10. Header

- Height: 40px. Background: `--surface-1`, 1px bottom border `--border-subtle`.
- Alert badge: amber styling (`#451A03` bg, `#FDE68A` text, `#78350F` border).
- UTC clock: monospace, `--text-secondary`.

### 4.11. Empty States

- Same background as surrounding panel. No decorative illustrations.
- Message is context-specific: *"No telemetry records received for AWS_012 in the selected 24h window."*
- Never: "No data found."

### 4.12. Loading States

- Skeleton shimmer: CSS background-position animation.
- Base: `--surface-2`. Shimmer highlight: `#1F2D40`.
- Show skeleton after 150ms delay (avoid flicker on fast loads).
- Charts: gray rectangle matching chart dimensions. No spinner inside chart.

### 4.13. Error States

- Inline error message below failed component: `⚠ Failed to load station data. [Retry]`
- Retry: text button, no primary styling.
- Critical connectivity loss: sticky top bar in `--color-critical` background.
- Always show last cached data if available. Never a blank crash screen.

### 4.14. Offline State

- Sticky bar below app header: "Live telemetry stream disconnected. Viewing cached observations as of [timestamp]."
- Background: `#451A03`. Text: `#FDE68A`. 1px bottom border `#78350F`.
- All map station dots switch to offline color. All `DataFreshnessIndicator` instances show stale age.

---

## 5. Responsive Behavior

### 5.1. Breakpoints

| Breakpoint | Width  | Behavior                                                      |
|------------|--------|---------------------------------------------------------------|
| `sm`       | 640px  | Sidebar collapses to icon-only. Single column content.        |
| `md`       | 768px  | Sidebar icons + badge. Summary-level tables.                  |
| `lg`       | 1024px | Full sidebar. Two-column page layouts.                        |
| `xl`       | 1280px | Map + alerts split. All panels visible.                       |
| `2xl`      | 1536px | Wider chart areas. More table columns.                        |

### 5.2. Critical Data — Never Disappears

Must remain visible at all breakpoints:
- Station status (Normal / Warning / Critical / Offline)
- Active alert list
- Observed values for flagged parameters
- Anomaly decision classification
- Last update timestamp

### 5.3. Collapsible on Narrow Screens

May collapse or hide on `md` and below:
- Neighbor comparison details (collapse to count only)
- Secondary parameter charts (stack vertically, reduce height)
- Evidence tier 3–4 (collapse to summary line + expand control)
- SHAP bar chart (replace with ranked text list)
- Audit trail (collapse to accordion)

### 5.4. Chart Responsive Rules

- Minimum chart height: 120px. Never truncate or clip data.
- On `md`: stacked single-column layout.
- On `sm`: sparkline with full expand option.
- Tooltip usable on touch (tap replaces hover).

### 5.5. Table Responsive Rules

- On `md`: hide lower-priority columns. Show column selection control.
- On `sm`: convert tables to card list with primary fields only.
- Never hide: station ID, status, current T, anomaly state, last update time.

---

## 6. Accessibility

### 6.1. Color Contrast

- WCAG 2.1 AA minimum: 4.5:1 body text, 3:1 large text and UI components.
- Status dots supplemented by text labels — never color-only communication.
- Chart lines supplemented by distinct line styles (solid / dashed / dotted) — never color-only differentiation.

### 6.2. Keyboard Navigation

- All interactive elements reachable via Tab.
- Tab order matches visual reading order.
- Focus rings: 2px solid `#38BDF8`, 2px offset. Never removed.
- Modal dialogs: trap focus, Esc to close.

### 6.3. ARIA Labels and Roles

- Sidebar: `<nav aria-label="Main navigation">`.
- Status badges: `aria-label="Status: Critical"`.
- Charts: `<figure>` with `<figcaption>`. ARIA live region for real-time updates.
- Alert list: `role="log"`, `aria-live="polite"`.
- Tables: `<table>` with `<thead>`, `<th scope="col">`, `<caption>`.

### 6.4. Reduced Motion

- All transitions respect `prefers-reduced-motion`. Skeleton shimmer disabled. Chart transitions removed.
- No auto-playing animations at rest state.

### 6.5. Font Sizes

- All font sizes in `rem` or `em`. No `px`-only definitions.
- Layout functional at 150% browser zoom.

---

## 7. Visual Hierarchy

### 7.1. Hierarchy Principles

1. **Decision state** is the highest visual priority. Status color appears first, largest.
2. **Observed values** are second priority. Monospace, prominent.
3. **Metadata** (timestamps, coordinates, versions) is de-emphasized: smaller, muted color.
4. **Version/audit information** always present but visually recessed.

### 7.2. Page-Level Hierarchy

```
Page Title (18px, weight 600)
  → Section Title (14px, weight 600)
    → Panel Content (13px, weight 400)
      → Metadata / Muted (11px, weight 400, --text-muted)
```

### 7.3. Color as Hierarchy Signal

- Red / Critical draws the eye first (highest urgency).
- Amber / Warning draws second.
- Green / Normal is visually quiet — normal is the expected state, not a celebration.
- Muted gray items (metadata, timestamps) do not compete with operational data.

### 7.4. Density

Dense by default. Compact padding. This is an operations center, not a marketing page. Whitespace is used between sections (24–32px), not within panels.

---

## 8. Interaction Patterns

### 8.1. Drill-Down

Every anomaly, station status, and health score is clickable to a detail view:

- Network Overview map dot → Station Details
- Alert list item → Anomaly Investigation
- Station Details anomaly band → Anomaly Investigation
- Anomaly Investigation correction section → Correction Review
- Station Details health score → Sensor Health

Breadcrumb in top bar shows navigation context.

### 8.2. Data Freshness and Polling

- Network Overview, Live Monitoring: poll every 15 seconds.
- Station Details: poll every 30 seconds.
- System Status: poll every 60 seconds.
- On failure: offline state banner after 2 consecutive failures.

Implementation: **TanStack Query** with `refetchInterval`.

### 8.3. Time Window Selection

- Segmented control: `6h | 24h | 7d | 30d`.
- Window persists in URL query parameter (e.g. `?window=7d`).
- Changing window triggers fetch and re-renders charts without full page reload.

### 8.4. Table Sorting

- All tables sortable by column header click.
- Default: severity descending (worst first).
- Sort state persists in URL parameter.

### 8.5. Chart Interaction

- Cursor hover: synchronized vertical crosshair across all charts on the same page.
- Tooltip shows all parameter values at the hovered timestamp.
- Historical Analysis: brush selection updates anomaly summary table below.

### 8.6. Correction Actions

- Accept / Reject / Flag: single click.
- Confirmation: inline text, 3-second auto-dismiss. Not a modal.
- Accepted: ✓ badge. Rejected: ✕ badge.
- Operator note: optional, no blocking validation.

### 8.7. Loading / Empty / Error Transitions

- Loading skeleton: appears after 150ms delay to avoid flicker.
- Empty states: show immediately on empty API response.
- Error: inline message + retry button. Immediate re-fetch on retry.

---

## 9. Data Visualization Rules

### 9.1. Chart Type Selection

| Data Type                        | Correct Chart                        | Prohibited                    |
|----------------------------------|--------------------------------------|-------------------------------|
| Parameter value over time        | Line chart (WeatherTrendChart)       | Bar chart (primary view)      |
| Health score over time           | Area chart (HealthTrend)             | Radial gauge, donut           |
| SHAP feature contributions       | Horizontal bar chart (ranked)        | Pie chart, bubble chart       |
| Component health breakdown       | Horizontal bar per component         | Radar / spider chart          |
| Station status distribution      | Status strip (band counts)           | Donut / pie chart             |
| Station geographic distribution  | Map (NetworkMap)                     | Abstract node diagram         |
| Anomaly episode timeline         | Horizontal swimlane (AnomalyTimeline)| Calendar heatmap              |

### 9.2. Dual-Signal Representation

Charts always render both signals when imputed data is available:
- Solid line = raw immutable sensor reading (always present, never hidden or replaced)
- Dashed line = imputed / recommended value (clearly distinguished)

### 9.3. Anomaly Annotation

- Episodes shown as background bands, 8% opacity of severity color.
- Bands must not obscure the data line.
- Band label shown only on hover. No permanent floating labels.

### 9.4. Axes Rules

- Y-axis always shows units in the label. E.g. "Temperature (°C)", "Pressure (hPa)".
- X-axis always shows UTC timestamps. Format: `HH:mm UTC` (within 24h), `MM-DD HH:mm` (multi-day).
- Y-axis scale is data-driven. No artificial zero-baseline unless physically meaningful.
- Never truncate Y-axis to exaggerate small variations.

### 9.5. Multi-Parameter Synchronization

- T, RH, P charts on the same page share a `syncId`.
- Hover on any chart shows crosshair on all three.
- Time window selector applies to all three simultaneously.

### 9.6. SHAP Visualization Rules

- Horizontal bars sorted by magnitude (highest first).
- Direction label adjacent to each bar: "increases anomaly" or "decreases anomaly".
- No colors implying "good" or "bad" — use neutral direction colors only.
- No language claiming SHAP bars prove fault causation (only model contribution).
- Feature names in readable form: `temp_rate_of_change` → "Temperature Rate of Change".

### 9.7. Health Score Visualization

- Primary display: plain numeric score + status band label. 28px, weight 600.
- Trend: arrow (↑ IMPROVING, → STABLE, ↓ DEGRADING).
- Historical trend: HealthTrend area chart with background status band zones.
- No radial gauge. No circular progress rings. No animated fill.
- Scientific disclaimer visible on Sensor Health page.

---

## 10. Dashboard Anti-Slop Rules

### 10.1. Structural Anti-Patterns — Prohibited

| Prohibited Pattern                                   | Reason                                                     |
|------------------------------------------------------|------------------------------------------------------------|
| Purple gradient hero section                         | Decorative, no semantic meaning                            |
| Giant centered page title (>24px on dashboard)       | Wastes vertical space; operators need data, not branding   |
| 12 identical KPI cards in a grid                     | Cards without hierarchy; status strip or table is superior |
| Excessive rounded cards (`rounded-2xl` or more)      | Consumer SaaS aesthetic, not operations center             |
| Random drop shadows on all cards                     | Visual noise, no semantic purpose                          |
| Glassmorphism backgrounds on functional panels       | Reduces readability, purely decorative                     |
| Decorative background blurs or glows                 | Reduces contrast, impairs readability                      |
| Giant whitespace sections between panels             | Reduces information density                                |

### 10.2. Data and Chart Anti-Patterns — Prohibited

| Prohibited Pattern                                   | Reason                                                     |
|------------------------------------------------------|------------------------------------------------------------|
| Decorative charts with no actionable information     | Every chart must answer a specific operational question    |
| Donut / pie charts for status distribution           | Status strip or table is more precise and faster to read   |
| Radial gauge for health score                        | Plain numeric is faster; radial is arbitrary encoding      |
| Radar / spider charts for component breakdown        | Misleading with non-uniform axes; bar chart is clearer     |
| Animated number counters on page load                | Distracting, no informational value                        |
| Chart animation reset on every 15-second poll        | Visual disruption during normal operations                 |
| Smooth/spline interpolation on meteorological data   | Masks actual data shape; use linear interpolation          |

### 10.3. Alert and Status Anti-Patterns — Prohibited

| Prohibited Pattern                                   | Reason                                                     |
|------------------------------------------------------|------------------------------------------------------------|
| Modal popup for every new anomaly                    | Blocks operations workflow; use alert list / status bar    |
| Sound alerts without user preference control         | Invasive, inaccessible                                     |
| Blinking or pulsing status indicators (CSS animation)| Distracting; a static colored dot is sufficient            |
| Color-only status communication                      | Inaccessible; must pair color with text label              |

### 10.4. Content Anti-Patterns — Prohibited

| Prohibited Pattern                                   | Reason                                                     |
|------------------------------------------------------|------------------------------------------------------------|
| AI-themed decorative imagery (brain, neural net)     | Unprofessional in operational context                      |
| "AI-powered" marketing text in the UI                | Evidence chain explains the system; text is redundant      |
| Probability statements from ML anomaly scores        | Not calibrated; use "anomaly score" language only          |
| "Corrected value is true" language                   | Scientifically incorrect; use "recommended estimate"       |
| Certainty claims on UNCERTAIN decisions              | Must declare the conflicting or sparse evidence explicitly  |
| Generic empty state messages ("No data found")       | Must be specific to context and station                    |
| Version metadata hidden or collapsed by default      | Audit information must always be visible on investigation  |

### 10.5. Animation Anti-Patterns — Prohibited

| Prohibited Pattern                                   | Reason                                                     |
|------------------------------------------------------|------------------------------------------------------------|
| Page transition animations                           | Adds latency perception; inappropriate for data UI         |
| Chart line draw animation on load                    | Distracting; operator needs data immediately               |
| Card hover scale transforms (`scale-105`)            | Consumer aesthetic, not operations center                  |
| Loading spinner inside chart area                    | Skeleton shimmer is less disruptive                        |
| Floating particle / aurora background effects        | Purely decorative; incompatible with visual language       |

---

## Appendix A: API Endpoint Reference (Frontend Consumption)

| Page                  | Primary API Endpoints                                                          |
|-----------------------|--------------------------------------------------------------------------------|
| Network Overview      | `GET /api/v1/stations`, `GET /api/v1/anomalies?limit=20`                      |
| Live Monitoring       | `GET /api/v1/stations/{id}/latest` (all stations, polled)                      |
| Station Details       | `GET /api/v1/stations/{id}`, `/latest`, `/history`, `/health`                 |
| Anomaly Investigation | `GET /api/v1/anomalies/{event_id}`, `/anomalies/{event_id}/explanation`        |
| Sensor Health         | `GET /api/v1/stations/{id}/health` (all stations)                              |
| Correction Review     | *(Correction JSONL data — future dedicated API endpoint)*                      |
| Historical Analysis   | `GET /api/v1/stations/{id}/history?start_time=&end_time=&limit=1000`          |
| System Status         | `GET /api/v1/system/health`, `GET /api/v1/replay/status`                      |

---

## Appendix B: Component × Page Matrix

| Component              | Net. Overview | Live Mon. | Station Det. | Anomaly Inv. | Sensor Health | Correction | Historical | System |
|------------------------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| StationStatus          |  ✓  |  ✓  |  ✓  |  ✓  |  ✓  |     |     |    |
| SeverityBadge          |  ✓  |  ✓  |  ✓  |  ✓  |     |  ✓  |  ✓  |    |
| MetricTable            |  ✓  |  ✓  |  ✓  |  ✓  |     |     |     |    |
| WeatherTrendChart      |     |  ✓  |  ✓  |     |     |     |  ✓  |    |
| AnomalyTimeline        |     |     |  ✓  |  ✓  |     |     |  ✓  |    |
| EvidencePanel          |     |     |     |  ✓  |     |  ✓  |     |    |
| NeighborComparison     |     |     |  ✓  |  ✓  |     |     |     |    |
| HealthScore            |  ✓  |  ✓  |  ✓  |     |  ✓  |     |     |    |
| HealthTrend            |     |     |  ✓  |     |  ✓  |     |     |    |
| AlertList              |  ✓  |     |     |     |     |     |     |    |
| NetworkMap             |  ✓  |     |     |  ✓  |     |     |     |    |
| DataFreshnessIndicator |  ✓  |  ✓  |  ✓  |     |     |     |     |    |
| SystemStatus           |     |     |     |     |     |     |     |  ✓  |
| DecisionBanner         |     |     |     |  ✓  |     |     |     |    |

---

*End of SkyGuard AI Dashboard Design Specification v1.0*
