# SkyGuard AI — Hybrid Decision Engine Specification & Benchmark Report

## 1. Executive Summary & Purpose
The **SkyGuard Hybrid Decision Engine** synthesizes multi-subsystem evidence without numerical score flattening or ad-hoc probability mislabeling:
$$\text{Hybrid Decision} = \text{Data Quality} \oplus \text{Physical Planetary Bounds} \oplus \text{Temporal Dynamics} \oplus \text{Multivariate Physics} \oplus \text{ML Anomaly Score} \oplus \text{Spatial/Synoptic Context}$$

The engine interprets candidate anomalies, cleanly separating:
1. `NORMAL`: Meteorologically consistent, temporally coherent, corroborated background observations.
2. `POSSIBLE_GENUINE_EVENT`: Steep atmospheric dynamics (e.g. squall lines, microbursts, heatwaves) corroborated across the regional station network.
3. `PROBABLE_SENSOR_ANOMALY`: Hardware glitches, transducer freezing, calibration drift, or unphysical outliers isolated to a single station.
4. `PROBABLE_DATA_QUALITY_ISSUE`: Telemetry gaps, dropped packets, schema rejections, duplicate timestamps, or out-of-order packets.
5. `UNCERTAIN`: Conflicting or insufficient evidence (e.g. high statistical residual on an isolated station with no active neighbors).

---

## 2. Standardized Evidence Package (`ObservationEvidence`)
Evidence from each subsystem is preserved in its original units and classified into standardized **Evidence States**:
- `SUPPORTS`: Directly corroborates the anomaly/defect hypothesis.
- `CONTRADICTS`: Rebuts or provides alternative physical explanation (e.g., regional consensus rules out local hardware fault).
- `NEUTRAL`: Normal baseline; neither supports nor contradicts.
- `UNAVAILABLE`: Missing or sparse telemetry.

### 2.1. Subsystem Evidence Structure
- **Data Quality**: Ingestion status (`VALID`, `REJECTED`, `GAP`, `DUPLICATE`), missing required fields, communication gap duration, duplicate flag, out-of-order flag.
- **ML Anomaly**: Raw model score, continuous normalized anomaly score $[0, 1]$ (not mislabeled as probability), binary validation threshold flag, model architecture identifier.
- **Temporal Dynamics**: Parameter rate of change ($\Delta X / \text{min}$), consecutive unchanged count, flatline duration (minutes), sliding-window Z-score residual.
- **Multivariate Physics**: Dew point spread consistency ($T - T_d \ge 0$), August-Roche-Magnus thermodynamic consistency, joint standardized divergence norm.
- **Spatial/Synoptic Context (Phase 4)**: Active neighbor counts, context category (`LOCAL_ONLY`, `LOCAL_CLUSTER`, `REGIONAL_PATTERN`, `INSUFFICIENT_CONTEXT`), neighbor consensus ratios, IDW expected value delta.

---

## 3. Decision Rule Hierarchy & Arbitration Gates

```mermaid
flowchart TD
    Start[Incoming ObservationEvidence] --> G1{Gate 1: Data Quality Defect?}
    G1 -- Yes (Gap, Duplicate, Missing) --> DQ[PROBABLE_DATA_QUALITY_ISSUE]
    G1 -- No (Valid Telemetry) --> G2{Gate 2: Physical Boundary Breach?}
    
    G2 -- Yes (Temp > 60°C, RH > 100%) --> Phys[PROBABLE_SENSOR_ANOMALY (CRITICAL)]
    G2 -- No --> G3{Gate 3: Stuck Flatline Sensor?}
    
    G3 -- Yes (>= 6 steps unchanged) --> Flat[PROBABLE_SENSOR_ANOMALY (HIGH/MED)]
    G3 -- No --> G4{Gate 4: Multivariate Inconsistency?}
    
    G4 -- Yes (Thermodynamic Contradiction) --> Multi[PROBABLE_SENSOR_ANOMALY (MEDIUM)]
    G4 -- No --> G5{Gate 5: Anomaly Signal Present?}
    
    G5 -- Yes --> G5_Spat{Spatial Context Evaluation}
    G5_Spat -- REGIONAL_PATTERN (Mixed Excess) --> Mixed[PROBABLE_SENSOR_ANOMALY (HIGH)]
    G5_Spat -- REGIONAL_PATTERN (Corroborated) --> Genuine[POSSIBLE_GENUINE_EVENT (LOW/INFO)]
    G5_Spat -- LOCAL_CLUSTER --> Cluster[POSSIBLE_GENUINE_EVENT (LOW)]
    G5_Spat -- LOCAL_ONLY --> Local[PROBABLE_SENSOR_ANOMALY (HIGH/MED)]
    G5_Spat -- INSUFFICIENT_CONTEXT --> Unc[UNCERTAIN (MEDIUM)]
    
    G5 -- No (Nominal Telemetry) --> Norm[NORMAL (INFO)]
```

---

## 4. Reason Codes & Severity Taxonomy

### 4.1. Stable Reason Codes
- `NOMINAL_OBSERVATION`: All parameters within expected bounds and network consensus.
- `DATA_GAP`: Telemetry gap exceeding normal sampling interval.
- `DUPLICATE_TIMESTAMP`: Duplicate record received.
- `MISSING_REQUIRED_VARIABLES`: Primary meteorological parameters omitted.
- `OUT_OF_RANGE_PHYSICAL`: Parameter exceeds planetary thermodynamic limits.
- `PERSISTENT_VALUE`: Sensor output stuck constant during dynamic atmospheric periods.
- `RAPID_RATE_OF_CHANGE`: Step rate of change exceeds physical thresholds.
- `MULTIVARIATE_DEVIATION`: Joint physical relationships violated.
- `ML_HIGH_ANOMALY_SCORE`: Statistical model output exceeds high anomaly threshold.
- `LOCAL_SPATIAL_ISOLATION`: Single station deviates while surrounding network is stable.
- `REGIONAL_SPATIAL_AGREEMENT`: Adjacent AWS stations corroborate atmospheric transition.
- `MIXED_REGIONAL_EVENT_WITH_LOCAL_EXCESS`: Genuine regional event present, but target exhibits unphysical excess.
- `INSUFFICIENT_SPATIAL_CONTEXT`: Spatial coverage insufficient to confirm or refute anomaly.
- `CONFLICTING_EVIDENCE`: Subsystems provide contradictory evidence signals.

### 4.2. Operational Severity Levels
- `INFO`: Normal observations and corroborated regional weather events.
- `LOW`: Minor rate departures, single missing packets, or localized meso-scale clusters.
- `MEDIUM`: Moderate ML anomalies, persistent values, or unresolved uncertainty.
- `HIGH`: Confirmed local sensor spikes, severe drift, or mixed regional/fault events.
- `CRITICAL`: Physical limit breaches or prolonged telemetry outages ($> 180\text{ min}$).

---

## 5. Quantitative Scenario Evaluation Results

| Scenario ID | Test Description | Expected Decision | Hybrid Decision Output | Assigned Severity | Reason Codes Triggered | Status |
|---|---|---|---|---|---|---|
| **Scenario A** | Pristine Background Weather | `NORMAL` | `NORMAL` | `INFO` | `NOMINAL_OBSERVATION` | **EXACT MATCH** |
| **Scenario B** | Local Single-Station Spike | `PROBABLE_SENSOR_ANOMALY` | `PROBABLE_SENSOR_ANOMALY` | `HIGH` | `ML_HIGH_ANOMALY_SCORE`, `LOCAL_SPATIAL_ISOLATION` | **EXACT MATCH** |
| **Scenario C** | Regional Weather Front (Squall) | `POSSIBLE_GENUINE_EVENT` | `POSSIBLE_GENUINE_EVENT` | `LOW` | `ML_MODERATE_ANOMALY_SCORE`, `REGIONAL_SPATIAL_AGREEMENT`, `RAPID_RATE_OF_CHANGE` | **EXACT MATCH** |
| **Scenario D** | Mixed Regional Event + Sensor Spike | `PROBABLE_SENSOR_ANOMALY` | `PROBABLE_SENSOR_ANOMALY` | `HIGH` | `ML_HIGH_ANOMALY_SCORE`, `MIXED_REGIONAL_EVENT_WITH_LOCAL_EXCESS`, `REGIONAL_SPATIAL_AGREEMENT` | **EXACT MATCH** |
| **Scenario E** | Telemetry Communication Gap | `PROBABLE_DATA_QUALITY_ISSUE` | `PROBABLE_DATA_QUALITY_ISSUE` | `HIGH` | `MISSING_REQUIRED_VARIABLES`, `DATA_GAP` | **EXACT MATCH** |
| **Scenario F** | Frozen Sensor Flatline | `PROBABLE_SENSOR_ANOMALY` | `PROBABLE_SENSOR_ANOMALY` | `MEDIUM` | `PERSISTENT_VALUE` | **EXACT MATCH** |
| **Scenario G** | Slow Progressive Sensor Drift | `PROBABLE_SENSOR_ANOMALY` | `PROBABLE_SENSOR_ANOMALY` | `MEDIUM` | `ML_MODERATE_ANOMALY_SCORE`, `LOCAL_SPATIAL_ISOLATION` | **EXACT MATCH** |
| **Scenario H** | Conflicting / Isolated Station | `UNCERTAIN` | `UNCERTAIN` | `MEDIUM` | `ML_MODERATE_ANOMALY_SCORE`, `INSUFFICIENT_SPATIAL_CONTEXT`, `CONFLICTING_EVIDENCE` | **EXACT MATCH** |

---

## 6. Scientific Language & Operational Guidance
The engine produces structured human-readable explanations and standard operating actions:
- **No Absolute Proof Claims**: The engine avoids claiming "proof" or "certainty", instead outputting transparent evidence indicating probability and support.
- **Recommended SOPs**:
  - `NORMAL` $\rightarrow$ "No action required. Telemetry is meteorologically consistent."
  - `POSSIBLE_GENUINE_EVENT` $\rightarrow$ "Corroborated by regional network. Compare adjacent station observations and monitor atmospheric event progression."
  - `PROBABLE_SENSOR_ANOMALY` $\rightarrow$ "Inspect sensor hardware and wiring. Validate against portable reference instrument or redundant sensor."
  - `PROBABLE_DATA_QUALITY_ISSUE` $\rightarrow$ "Check communication telemetry link, data logger encoding, and ingestion pipeline queue."
  - `UNCERTAIN` $\rightarrow$ "Collect additional observation cycles and review manual field logs before executing corrective maintenance."
