# SkyGuard AI — Frontend (Meteorological Operations Center)

The SkyGuard AI frontend is a high-density, real-time monitoring interface for Automatic Weather Station networks.

## Architecture
- **Framework**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS + shadcn/ui design tokens adhering to `docs/UI_DESIGN_SYSTEM.md`
- **Charts**: Recharts (Synchronized multi-axis time series, raw vs. imputed comparison, spatial neighbor consistency)
- **Data Fetching**: TanStack Query

## Visual Language
Follows the **Meteorological Operations Center / Weather Mission Control** aesthetic:
- Deep-slate / dark-navy neutral background (`#0B0F17`, `#111827`)
- Strict semantic color mapping (Cyan/Sky for Temperature, Violet for Pressure, Emerald for Humidity, Amber for Warning, Red for Critical Anomaly, Indigo for Genuine Weather Events)
- Monospace formatting for coordinates, timestamps, and sensor telemetry.
