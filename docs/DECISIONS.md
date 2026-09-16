# SkyGuard AI — Architecture Decision Records (ADRs)

## Record Summary

| ADR # | Title | Status | Date |
|---|---|---|---|
| ADR-001 | Initial Observation Interval (5 Minutes, Configurable) | Accepted | 2026-09-16 |
| ADR-002 | Historical Datasets First, Live API Later | Accepted | 2026-09-16 |
| ADR-003 | Synthetic Anomaly Injection for Controlled Evaluation | Accepted | 2026-09-16 |
| ADR-004 | Detection + Recommended Correction (Immutable Raw Data) | Accepted | 2026-09-16 |
| ADR-005 | React & TypeScript Frontend with Operations Center Visuals | Accepted | 2026-09-16 |
| ADR-006 | Geodesic Spatial Proximity over Administrative Boundaries | Accepted | 2026-09-16 |

---

## ADR-001: Initial Observation Interval Configured to 5 Minutes
- **Status:** Accepted
- **Context:** Automatic Weather Stations report at varying cadences (1 min, 5 min, 10 min, 15 min, 60 min). We need a standard default sampling rate for baseline pipeline development.
- **Decision:** Set default sampling interval to **5 minutes** while ensuring all sliding windows, step thresholds, and rate calculations are parametrically derived from configuration rather than hard-coded.
- **Consequences:** Provides an optimal balance between temporal resolution for spike/rate detection and computational/storage footprint. Any station reporting at 1 min or 15 min can be accommodated via config updates.

---

## ADR-002: Historical Datasets First, Live API Later
- **Status:** Accepted
- **Context:** Connecting live external weather APIs early introduces network flakiness, rate limits, uncalibrated sensor errors, and lack of reproducible ground truth during ML development.
- **Decision:** Build and validate the core data adapter, QC pipeline, feature extraction, and ML models on historical AWS datasets before implementing live API connectors.
- **Consequences:** Enables rapid, deterministic, and offline development. Connectors are abstracted via `BaseConnector` to ensure dropping in a live API connector in Phase 4 requires zero changes to core ML or backend logic.

---

## ADR-003: Synthetic Anomaly Injection for Controlled Evaluation
- **Status:** Accepted
- **Context:** Real-world weather station logs contain rare, unreliably annotated anomalies. Evaluating models solely on unverified historical logs makes quantitative F1 and Recall benchmarking impossible.
- **Decision:** Implement a synthetic fault injection framework that introduces controlled anomalies (spikes, drift, frozen values, multivariate corruptions) into clean historical series with isolated ground truth.
- **Consequences:** Enables precise, automated metric computation (Precision, Recall, F1, Detection Latency) and regression testing across model iterations.

---

## ADR-004: Detection + Recommended Correction Rather Than Silent Overwrite
- **Status:** Accepted
- **Context:** In meteorological operations, raw sensor observations represent legal and scientific records. Modifying or replacing raw data in place destroys audit trails.
- **Decision:** Raw observations are strictly immutable. When an anomaly is detected, the system stores the quality classification and a recommended imputed/corrected value in a separate table/collection.
- **Consequences:** Guarantees 100% data provenance, auditability, and the ability to re-run updated models over pristine historical raw data.

---

## ADR-005: React / TypeScript Frontend with Meteorological Ops Center Aesthetic
- **Status:** Accepted
- **Context:** The monitoring interface must serve operations engineers, meteorologists, and hackathon judges who require high information density, multi-chart synchronization, and clear status indicators.
- **Decision:** Use React, TypeScript, Tailwind CSS, shadcn/ui tokens, and Recharts with a dark "Meteorological Operations Center / Enterprise Observability" design system. Avoid generic SaaS templates, excessive animations, and decorative AI gradients.
- **Consequences:** Ensures a credible, professional, high-performance interface suited for mission-critical monitoring.

---

## ADR-006: Geodesic Spatial Proximity Rather Than State Membership
- **Status:** Accepted
- **Context:** Weather does not stop at state or district borders. Two stations in different states 15 km apart share weather dynamics, whereas two stations in the same state 600 km apart may have entirely different microclimates.
- **Decision:** Calculate spatial neighborhood matrices and spatial consistency checks using geodetic distance (Haversine/Vincenty on Latitude, Longitude, Elevation), completely ignoring political/state boundaries.
- **Consequences:** Maximizes physical meteorological validity in spatial consistency validation.
