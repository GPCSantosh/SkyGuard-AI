# SkyGuard AI — Sensor Health & Degradation Monitoring Specification (Phase 6B)

## 1. Executive Summary & Purpose
The **Sensor Health & Degradation Monitoring Subsystem** (`ml/health/`) aggregates historical observation evidence and upstream hybrid decisions over configurable time windows ($24\text{h}, 7\text{d}, 30\text{d}$) to evaluate the progressive operational reliability of Automatic Weather Stations (AWS) and individual sensor channels.

### Prime Directive & Scientific Principle
> **CRITICAL SCIENTIFIC DISTINCTION:**
> - The **Sensor Health Index** is a **0–100 empirical reliability indicator** reflecting observed historical performance.
> - It is **NOT** a guaranteed failure predictor or a probability of hardware failure.
> - We **NEVER** claim: *"Sensor has an 80% chance of failing tomorrow."*
> - We state: *"Sensor Health Index: 80.0/100 (GOOD, trend: stable). Observed reliability indicators remain favorable."*

---

## 2. Health Index Formulation & Dimensional Decomposition

The overall Sensor Health Index $H_{\text{overall}} \in [0.0, 100.0]$ is a weighted composite of **5 distinct sub-domain reliability indicators**:

$$H_{\text{overall}} = w_{\text{anom}} H_{\text{anom}} + w_{\text{dq}} H_{\text{dq}} + w_{\text{comm}} H_{\text{comm}} + w_{\text{temp}} H_{\text{temporal}} + w_{\text{spat}} H_{\text{spatial}}$$

### 2.1. Configurable Component Dimensions

| Component | Weight ($w_i$) | Focus & Penalty Metrics | Mathematical Basis |
|---|---|---|---|
| **Anomaly Health ($H_{\text{anom}}$)** | `0.30` | Severity-weighted frequency of single-station faults (`PROBABLE_SENSOR_ANOMALY`). | $100 \times \left(1 - \min\left(1.0, \frac{\sum w_t \cdot \text{sev\_penalty}}{0.12 \cdot N}\right)\right)$. **Protects `POSSIBLE_GENUINE_EVENT` from penalty.** |
| **Data Quality Health ($H_{\text{dq}}$)** | `0.20` | Missing fields, payload parsing rejections, duplicate timestamps, out-of-order packets. | $100 \times \left(1 - \min\left(1.0, \frac{\text{Defect Rate}}{0.15}\right)\right)$. |
| **Communication Health ($H_{\text{comm}}$)** | `0.15` | Telemetry link outages and communication gap duration. | $100 \times \left(1 - \min\left(1.0, \frac{\text{Total Gap Minutes}}{0.15 \times \text{Window Minutes}}\right)\right)$. |
| **Temporal Stability Health ($H_{\text{temp}}$)** | `0.20` | Frozen sensor flatlines, stuck transducers, variance collapse. | $100 \times \left(1 - \min\left(1.0, \frac{\text{Flatline Minutes}}{0.10 \times \text{Window Minutes}}\right)\right)$. |
| **Spatial Consistency Health ($H_{\text{spat}}$)** | `0.15` | Uncorroborated single-station departures (`LOCAL_ONLY`) and progressive baseline drift. | $100 \times \left(1 - \min\left(1.0, \frac{\text{Isolation Rate}}{0.15} + \text{Drift Penalty}\right)\right)$. |

---

## 3. Recency Weighting & Multi-Window Analysis

### 3.1. Exponential Recency Decay
Recent telemetry faults have a larger operational impact than distant past events:
$$w_t = \exp\left(-\lambda \cdot \frac{t_{\text{current}} - t}{T_{\text{window}}}\right)$$
where $\lambda = 1.5$ (configurable). Weights are normalized such that $\overline{w}_t = 1.0$.

### 3.2. Supported Time Windows
- **`24h` (Daily Window)**: Captures immediate diurnal performance and recent transient disruptions.
- **`7d` (Weekly Window)**: Identifies emerging calibration drift and repeated intermittent faults.
- **`30d` (Monthly Window)**: Baseline long-term transducer degradation monitoring.

---

## 4. Health Status Bands & Trend Trajectory

### 4.1. Configurable Status Bands

| Score Range | Status Band | Operational Interpretation |
|---|---|---|
| **90.0 – 100.0** | `HEALTHY` | Optimal observed reliability. All channels operating within tolerances. |
| **75.0 – 89.9** | `GOOD` | Favorable performance with minor isolated departures. |
| **50.0 – 74.9** | `ATTENTION` | Moderate reliability degradation; increased monitoring recommended. |
| **25.0 – 49.9** | `DEGRADED` | Significant multi-channel faults, drift, or telemetry gaps; inspection required. |
| **0.0 – 24.9** | `CRITICAL` | Severe transducer failure, persistent flatlines, or prolonged telemetry collapse. |
| *N < N_min* | `INSUFFICIENT_HISTORY` | Less than minimum observations ($N_{\text{min}}=12$). Low-data mode active. |

### 4.2. Trend Calculation
$$\Delta H = H_{\text{current}} - H_{\text{previous}}$$
- $\Delta H \ge +3.0$: `IMPROVING` (Triggers `RECENT_RECOVERY_OBSERVED`)
- $-3.0 < \Delta H < +3.0$: `STABLE`
- $\Delta H \le -3.0$: `DEGRADING`

---

## 5. Maintenance Recommendations (SOP Guidance)

| Maintenance Level | Trigger Criteria | Standard Operating Procedure |
|---|---|---|
| `NO_ACTION` | $H \ge 75.0$ and Trend $\neq$ `DEGRADING` and no individual degraded channels. | No maintenance required. Observed reliability indicators remain favorable. |
| `MONITOR` | $50.0 \le H < 75.0$ or Trend == `DEGRADING`. | Increase monitoring cadence across telemetry and spatial channels. |
| `INSPECT` | $25.0 \le H < 50.0$, or persistent flatline/anomaly, or any individual channel in `DEGRADED`/`CRITICAL`. | Schedule sensor inspection and field calibration check during next routine window. |
| `PRIORITY_INSPECTION` | $H < 25.0$ or ($H < 50.0$ and Trend == `DEGRADING`). | Priority on-site intervention required. Severe physical or hardware degradation detected. |

---

## 6. Parameter-Level Channel Isolation

Health is calculated at the **station level** and broken down across individual sensor channels:
- `temperature_c`
- `relative_humidity`
- `sea_level_pressure_hpa`

**Benefit**: If a humidity transducer fails or drifts while temperature and barometric pressure remain stable, the system isolates the defect to `relative_humidity` ($H_{\text{RH}} = 20.0$, `CRITICAL`) without declaring the entire multi-sensor station offline.

---

## 7. Synthetic Scenario Benchmark Results

The subsystem has been verified against 8 canonical operational profiles:

| Scenario | Operational Condition | Expected Health Band | Health Engine Output | Status |
|---|---|---|---|---|
| **Scenario A** | Pristine Background Weather | `HEALTHY` ($\ge 90.0$) | `100.0` (`HEALTHY`, `NO_ACTION`) | **EXACT MATCH** |
| **Scenario B** | Repeated Single-Station Spikes | `ATTENTION` / `DEGRADED` ($< 75.0$) | `70.0` (`ATTENTION`, `INSPECT`) | **EXACT MATCH** |
| **Scenario C** | Progressive Baseline Drift | Reduced Spatial Health ($< 85.0$) | `83.2` (`GOOD`, `INCREASING_DRIFT`) | **EXACT MATCH** |
| **Scenario D** | Stuck Sensor Flatline | Degraded Temporal Health ($< 60.0$) | `50.0` (`ATTENTION`, `INSPECT`) | **EXACT MATCH** |
| **Scenario E** | Communication Gaps | Degraded Comm Health ($< 60.0$) | `Comm: 0.0`, `Overall: 85.0` (`COMMUNICATION_INSTABILITY`) | **EXACT MATCH** |
| **Scenario F** | Mixed Multi-Fault Breakdown | `DEGRADED` / `CRITICAL` ($< 50.0$) | `35.0` (`DEGRADED`, `PRIORITY_INSPECTION`) | **EXACT MATCH** |
| **Scenario G** | Temporary Glitch $\rightarrow$ Recovery | `IMPROVING` Trend ($\Delta H > 0$) | `Delta: +30.0` (`IMPROVING`) | **EXACT MATCH** |
| **Scenario H** | **Regional Squall (Protection)** | **`HEALTHY` ($\ge 90.0$)** | **`100.0` (`HEALTHY`, `NO_ACTION`)** | **EXACT MATCH** |

> [!IMPORTANT]
> **Scenario H Protection**: When a synoptic front or convective squall impacts the network, the engine recognizes `POSSIBLE_GENUINE_EVENT` and applies **0 penalty**, preventing regional storms from creating false sensor degradation alerts.
