# SkyGuard AI — UI Design System Specification

## 1. Visual Identity & Aesthetic Direction
**Theme:** **Meteorological Operations Center / Weather Mission Control / Enterprise Observability**

### 1.1. Core Principles
- **Technical & Information-Dense**: Prioritize high data density, readable typography, clear visual hierarchy, and fast scanning over decorative whitespace.
- **Calm & Restrained**: Dark-slate / deep-navy neutral foundation. Color is used strictly for semantic communication (alerts, state transitions, meteorological bands).
- **Zero Decorative Fluff**:
  - NO purple gradient washes or random AI glowing effects.
  - NO excessive glassmorphism or blurry card layers.
  - NO decorative 3D robot or cloud illustrations.
  - NO card grids where an information-dense table or synchronized time-series chart is the natural medium.
- **Accessibility & Contrast**: Strict compliance with WCAG 2.1 AA contrast requirements across all chart legends, telemetry pills, and table cells.

---

## 2. Color Palette & Semantic Tokens

### 2.1. Base Foundation Colors (Dark Theme Default)
- **Canvas / App Background**: `#0B0F17` (Deep Space Navy)
- **Panel / Surface 1**: `#111827` (Charcoal Slate)
- **Surface 2 / Card Background**: `#1A2234` (Elevated Panel Slate)
- **Surface Hover / Highlight**: `#232D42`
- **Border Neutral**: `#2D3748` (Subtle Gridlines & Card Borders)
- **Text Primary**: `#F8FAFC` (Slate 50)
- **Text Secondary**: `#94A3B8` (Slate 400)
- **Text Muted / Timestamp**: `#64748B` (Slate 500)

### 2.2. Semantic Operational Colors
| Semantic Meaning | Hex Code | Purpose / Usage |
|---|---|---|
| **Neutral / Infrastructure** | `#64748B` / `#94A3B8` | Normal metadata, axes, inactive sensors, hardware specs |
| **Atmospheric / Weather** | `#38BDF8` (Sky Blue) | Temperature line charts, precipitation bars, station badges |
| **Barometric Pressure** | `#A78BFA` (Muted Violet) | Pressure time-series charts, isobar lines |
| **Relative Humidity** | `#34D399` (Emerald Mint) | Humidity area charts, moisture gradients |
| **Healthy / Nominal** | `#10B981` (Emerald 500) | Station operational, QC passed, health score 85–100 |
| **Warning / Suspicious** | `#F59E0B` (Amber 500) | Suspicious observation, low-amplitude anomaly, health 60–84 |
| **Critical Anomaly** | `#EF4444` (Red 500) | Confirmed spike, severe drift, sensor failure, health < 60 |
| **Genuine Weather Event** | `#6366F1` (Indigo 500) | Verified extreme meteorological event |
| **Uncertain / Review** | `#EC4899` (Fuchsia 500) | Ambiguous observation pending operator review |
| **Offline / Missing** | `#475569` (Slate 600) | Dropped telemetry, sensor disconnected |

---

## 3. Typography Hierarchy
- **Primary Typeface**: `Inter`, `Roboto`, or `IBM Plex Sans` (System sans fallback).
- **Monospace Typeface (Telemetry & Coordinates)**: `JetBrains Mono` or `Fira Code` (strictly for timestamps, lat/long, sensor IDs, numeric readings, and hex values).

| Level | Size | Weight | Line Height | Tracking | Usage |
|---|---|---|---|---|---|
| Display / Stat Value | 28px (1.75rem) | 600 (SemiBold) | 1.1 | -0.02em | KPI cards, Health Index score |
| Header 1 | 20px (1.25rem) | 600 (SemiBold) | 1.2 | -0.01em | Screen titles, Station Header |
| Header 2 | 16px (1.0rem) | 600 (SemiBold) | 1.3 | 0 | Card section titles, Table headers |
| Body Regular | 14px (0.875rem) | 400 (Regular) | 1.4 | 0 | General narrative, metadata labels |
| Body Small / Data | 12px (0.75rem) | 500 (Medium) | 1.3 | +0.01em | Table cell data, Chart axis ticks |
| Mono Code / Coordinates | 11px (0.6875rem) | 400 (Mono) | 1.2 | 0 | Lat/Lon, Raw UTC timestamps, Hash IDs |

---

## 4. Layout, Spacing & Breakpoints

### Spacing Scale
- Compact 4px grid: `4px`, `8px`, `12px`, `16px`, `24px`, `32px`.
- Card padding: `12px` to `16px` max (tight, high-density).
- Component gap: `8px` to `12px`.
- Border radius: Subdued `4px` or `6px` (`rounded` or `rounded-md`). Never pill-shaped or bubbly `rounded-2xl` on structural panels.

### Responsive Breakpoints
- `sm`: 640px (Mobile view — collapsed sidebar, single column stack)
- `md`: 768px (Tablet view — station selector + summary)
- `lg`: 1024px (Standard Operations Console — sidebar + multi-chart layout)
- `xl`: 1280px (Wide Mission Control — full network spatial map + synchronized multi-parameter charts + live anomaly stream)
- `2xl`: 1536px (Multi-monitor NOC display)

---

## 5. Chart & Visualization Guidelines (Recharts / Canvas)
- **Synchronized Cursor Scrubbing**: Hovering over one parameter (e.g. Temperature) synchronizes the vertical crosshair across Pressure and Humidity charts simultaneously.
- **Dual Visual Representation (Raw vs. Imputed)**:
  - Raw sensor reading: Solid line with scatter dots on anomalous points.
  - Imputed/Estimated reading: High-contrast dashed line showing the model-recommended value.
  - Injected / Ground Truth: Shaded background band demarcating the exact anomaly window.
- **Chart Background**: `#111827` with faint grid lines (`#1F2937`, 1px stroke, `dasharray="3 3"`).
- **Zero Chart Clutter**: No heavy drop shadows on chart lines. Use subtle area fills with 10% opacity.

---

## 6. Component Patterns & States

### 6.1. Station Health Badge
- Health Score $\ge 85$: Green background pill (`bg-emerald-950 text-emerald-300 border border-emerald-800`).
- Health Score $60-84$: Amber background pill (`bg-amber-950 text-amber-300 border border-amber-800`).
- Health Score $< 60$: Red background pill (`bg-red-950 text-red-300 border border-red-800`).

### 6.2. Interactive States
- **Loading State**: Subtle skeleton shimmer with matching slate backgrounds (`#1E293B`).
- **Empty State**: Technical wireframe box with explanatory message: *"No telemetry records received for station AWS_012 in the selected 24h window."*
- **Error State**: Non-blocking toast notification + inline retry button; never a blank crash screen.
- **Offline Banner**: Sticky top status strip when backend connection is disrupted: *"Live telemetry stream disconnected. Viewing cached observations."*
