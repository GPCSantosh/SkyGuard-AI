# SkyGuard AI — Project Specification

## 1. Project Identity & Purpose
- **Project Name:** SkyGuard AI
- **Domain:** Meteorological Observability & Automatic Weather Station (AWS) Quality Assurance
- **Mission:** Build an intelligent, real-time and historical anomaly detection, data quality control, and sensor health monitoring platform for Automatic Weather Station networks across India.

---

## 2. Core Meteorological Parameters (Scope: Primary Trio)
SkyGuard AI initially targets the three foundational surface weather parameters:
1. **Temperature (°C)**: Surface ambient temperature (typical physical range: -50.0°C to +60.0°C).
2. **Atmospheric Pressure (hPa)**: Station level / barometric pressure (typical physical range: 500.0 hPa to 1080.0 hPa).
3. **Relative Humidity (%)**: Ambient relative humidity (physical range: 0.0% to 100.0%).

*(Future extensions will support secondary parameters: Wind Speed, Wind Direction, Solar Radiation, Precipitation, and Soil Moisture).*

---

## 3. Operational Problem Statement
Automatic Weather Stations operate autonomously in remote, harsh environments. Sensor networks regularly experience:
- **Sensor Spikes:** Single or short-duration impulse errors due to electrical noise or sensor glitch.
- **Frozen / Stuck Values:** Sensor output remains constant despite dynamic atmospheric conditions.
- **Gradual Sensor Drift:** Slow progressive deviation caused by sensor degradation, dust, or calibration loss.
- **Sudden Offsets:** Instantaneous baseline shift following power cycle, maintenance error, or physical impact.
- **Missing / Delayed Observations:** Telemetry drops, network congestion, or hardware brownouts.
- **Corrupted / Out-of-Order Packets:** Data transmission encoding errors.
- **Multivariate Inconsistencies:** Physical contradictions (e.g., relative humidity > 95% during peak midday temperature with dry bulb / wet bulb discrepancies).
- **Distinguishing Genuine Extreme Weather from Faults:** Genuine meteorological phenomena (squall lines, microbursts, heatwaves, cyclone landfall) exhibit rapid rate-of-change and extreme magnitudes. Simple thresholding erroneously flags real weather as sensor failure.

---

## 4. System Objectives & Classification Target
The system must categorize incoming records into four high-level operational tiers:
1. **Normal Observations:** Meteorologically consistent, temporally coherent, spatially verified.
2. **Suspicious Observations:** Statistical anomalies requiring spatial confirmation or multi-sensor correlation.
3. **Likely Sensor / Data Anomalies:** Confirmed hardware, telemetry, or calibration failures with recommended non-destructive imputation.
4. **Uncertain or Genuine Extreme Events:** High rate-of-change verified across neighboring stations or consistent with meteorological dynamics.

---

## 5. Scope & Roadmap Boundaries

### Current Phase Scope (Phase 0: Foundation)
- Architecture, data models, schema definitions, and validation rules.
- Engineering rules, design system specifications, and ADRs.
- Abstract data connector interfaces (`HistoricalCSV`, `Simulator`, `WeatherAPI`, `MQTT`).
- Configurable settings (sampling interval default: 5 minutes).
- Test infrastructure and baseline schema validation tests.

### Future Scope (Phase 1 & Beyond)
- Historical AWS dataset ingestion & normalization.
- Feature engineering (temporal sliding windows, spatial neighbor delta, multivariate gradients).
- Synthetic anomaly injection engine for controlled benchmarking.
- Hybrid Anomaly Engine (Physics rule checks + Unsupervised/Semi-supervised ML + Spatial consistency).
- Root-cause classification taxonomy & SHAP-based explainability.
- Sensor Health Scoring Index (0–100 scale).
- High-density Meteorological Operations Center dashboard (React, TypeScript, Tailwind, Recharts).
- Live API and Edge/MQTT telemetry ingestion.

---

## 6. Assumptions & Constraints
- **Station Network Scale:** Target network of ~20+ stations distributed geographically across India. Multiple stations may reside in the same state; spatial checks must rely on geodetic distance (Haversine/Vincenty), not state labels.
- **Sampling Cadence:** Default baseline is **5 minutes**. System must remain interval-agnostic (configurable: 1 min to 60 min).
- **Dataset Selection:** TBD — historical dataset selection pending Phase 1.
- **Edge Devices (ESP32 / Microcontrollers):** Explicitly out of scope for current implementation phase.
- **Non-Destructive Storage:** Raw observations are strictly immutable. Model corrections are stored as distinct derived entities.
