# SkyGuard AI — Spatial & Synoptic Context Specification & Benchmark Report

## 1. Executive Summary & Objective
Phase 3 single-station unsupervised baseline anomaly detectors demonstrated a core operational limitation: rare, genuine meteorological dynamics (squalls, heatwaves, frontal passages) exhibit extreme rates-of-change and statistical residual spikes that single-station models erroneously flag as sensor faults.

Phase 4 implements the **Spatial & Synoptic Context Engine**, answering:
> *"Do nearby weather stations show evidence of the same atmospheric transition, or is this observation locally isolated?"*

The engine outputs structured **Contextual Evidence** (`LOCAL_ONLY`, `LOCAL_CLUSTER`, `REGIONAL_PATTERN`, `INSUFFICIENT_CONTEXT`) along with statistical consensus metrics and distance weighting. It does **not** make final fault classifications or alter the raw observations.

---

## 2. Spatial Network Topology & Geodesic Model

### 2.1. Coordinate System & Distance Computation
Spatial proximity is calculated using the spherical **Haversine formula** on true geodetic coordinates $(\phi, \lambda)$, completely independent of political or administrative boundaries (ADR-006):
$$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)$$
$$d = 2 R_{\text{earth}} \cdot \text{atan2}\left(\sqrt{a}, \sqrt{1-a}\right)$$
where $R_{\text{earth}} = 6371.0088\text{ km}$.

### 2.2. Compass Bearing & Elevation Tracking
- **Initial Compass Bearing (Forward Azimuth)**:
  $$\theta = \text{atan2}\left(\sin(\Delta \lambda)\cos(\phi_2), \cos(\phi_1)\sin(\phi_2) - \sin(\phi_1)\cos(\phi_2)\cos(\Delta \lambda)\right) \pmod{360^\circ}$$
- **Elevation Difference**: $\Delta z = z_{\text{neighbor}} - z_{\text{target}}$ (meters).

---

## 3. Temporal Alignment & Causality Rules

### 3.1. Strict Forward-Time Exclusion (Causal Operation)
In real-time / operational mode:
$$t_{\text{neighbor}} \le t_{\text{target}}$$
Any observation where $t_{\text{neighbor}} > t_{\text{target}}$ is strictly excluded. Modifying future records produces zero change in historical context evaluations.

### 3.2. Temporal Window Tolerance & Stale Data
- Configurable tolerance window $W_{\text{temporal}}$ (default: $\pm 30\text{ minutes}$).
- Active neighbor candidate window: $[t_{\text{target}} - W_{\text{temporal}}, t_{\text{target}}]$.
- If $|t_{\text{neighbor}} - t_{\text{target}}| > W_{\text{temporal}}$, the observation is marked `STALE` and excluded from consensus statistics.

---

## 4. Core Parameters & Sea-Level Pressure Normalization
The spatial context engine operates exclusively on the core primary trio:
1. **Temperature (°C)** (`temperature_c`)
2. **Relative Humidity (%)** (`relative_humidity_pct`)
3. **Sea-Level Pressure (hPa)** (`sea_level_pressure_hpa`)

Raw station barometric pressure is normalized to Mean Sea Level (MSL) using the hypsometric equation before spatial comparison across stations with elevation differences:
$$P_{\text{slp}} = P_{\text{stn}} \cdot \exp\left(\frac{g_0 \cdot \Delta z}{R_d \cdot (T_K + \frac{L \cdot \Delta z}{2})}\right)$$

---

## 5. Statistical Consensus Metrics & Weighting

### 5.1. Distribution Statistics
For each parameter $X$ across active neighbors $\{X_1, X_2, \dots, X_k\}$:
- **Neighbor Mean**: $\mu_{\text{neighbor}} = \frac{1}{k} \sum X_i$
- **Neighbor Median**: $\text{med}_{\text{neighbor}} = \text{median}(\{X_i\})$
- **Sample Standard Deviation**: $\sigma_{\text{neighbor}} = \sqrt{\frac{1}{k-1} \sum (X_i - \mu_{\text{neighbor}})^2}$
- **Target Delta**: $\Delta_{\text{mean}} = X_{\text{target}} - \mu_{\text{neighbor}}$, $\Delta_{\text{median}} = X_{\text{target}} - \text{med}_{\text{neighbor}}$
- **Safe Standardized Z-Score**:
  $$Z_{\text{spatial}} = \frac{X_{\text{target}} - \mu_{\text{neighbor}}}{\max(\sigma_{\text{neighbor}}, \epsilon)}$$

### 5.2. Agreement Ratios
With parameter tolerance $\tau$ ($\pm 1.0^\circ\text{C}$ for T, $\pm 5.0\%$ for RH, $\pm 1.5\text{ hPa}$ for SLP):
- $\text{Frac}_{\text{similar}} = \frac{1}{k} \sum \mathbb{I}(|X_i - X_{\text{target}}| \le \tau)$
- $\text{Frac}_{\text{higher}} = \frac{1}{k} \sum \mathbb{I}(X_i > X_{\text{target}} + \tau)$
- $\text{Frac}_{\text{lower}} = \frac{1}{k} \sum \mathbb{I}(X_i < X_{\text{target}} - \tau)$

### 5.3. Directional Rate-of-Change Agreement
- Evaluates whether neighboring stations share the same physical tendency ($\Delta X / \Delta t$):
  $$\text{Agreement}_{\text{trend}} = \begin{cases} \text{Frac}_{\text{increasing}} - \text{Frac}_{\text{decreasing}} & \text{if } \Delta X_{\text{target}} > \tau_{\text{trend}} \\ \text{Frac}_{\text{decreasing}} - \text{Frac}_{\text{increasing}} & \text{if } \Delta X_{\text{target}} < -\tau_{\text{trend}} \\ \text{Frac}_{\text{stable}} - (\text{Frac}_{\text{increasing}} + \text{Frac}_{\text{decreasing}}) & \text{if } |\Delta X_{\text{target}}| \le \tau_{\text{trend}} \end{cases}$$

### 5.4. Inverse Distance Weighting (IDW)
$$w_i = \frac{1}{\max(d_i, 1.0)^p}, \quad W_i = \frac{w_i}{\sum w_j}, \quad \hat{X}_{\text{IDW}} = \sum_{i=1}^k W_i X_i$$

---

## 6. Spatial Context Categorization Taxonomy

| Category | Definition | Operational Interpretation |
|---|---|---|
| `REGIONAL_PATTERN` | $\ge 50\%$ active neighbors corroborate target value level OR agree on event-scale directional trend. | Atmospheric change is shared across the wider geographical network (e.g. synoptic front). |
| `LOCAL_CLUSTER` | Nearest neighbor ($\text{rank}=1$) corroborates departure, but distant stations differ. | Localized micro-climate or storm cell affecting immediate cluster. |
| `LOCAL_ONLY` | Target station exhibits significant departure from neighborhood without neighbor corroboration. | Observation is locally isolated; highly suspicious of sensor/hardware glitch. |
| `INSUFFICIENT_CONTEXT` | Active valid neighbors within spatial radius and temporal window $< k_{\text{min}}$. | Network coverage too sparse or telemetry dropped; cannot establish consensus. |

---

## 7. Experimental Evaluation & Benchmark Findings

### 7.1. Summary Matrix (8 Core Questions)

| Question / Experiment | Empirical Finding | Status |
|---|---|---|
| **Q1: Local Corruption Agreement** | Injected +6.0°C sensor spike produced $0.0\%$ similarity, $|Z|=31.54$, and $100\%$ `LOCAL_ONLY`. | **PASSED** |
| **Q2: Regional Event Agreement** | Injected frontal squall (-4.5°C, +20% RH, -3.5 hPa) produced $100\%$ similarity and $100\%$ `REGIONAL_PATTERN`. | **PASSED** |
| **Q3: Mixed Scenario Discrimination** | Target sensor fault (+7.0°C) atop regional event (+3.5°C) correctly isolated target deviation ($\Delta_{\text{mean}} = +7.06^\circ\text{C}$). | **PASSED** |
| **Q4: Temporal Tolerance Sensitivity** | Verified valid neighbor retention at 10m, 30m, 60m, 120m tolerances. | **PASSED** |
| **Q5: Distance Radius Sensitivity** | Quantified topological reach from 25 km (local) to 1500 km (sub-continental). | **PASSED** |
| **Q6: Distance Weighting (IDW)** | IDW expected value (22.03°C) vs arithmetic mean (22.09°C) provides smooth localized bias reduction. | **PASSED** |
| **Q7: Stale / Dropped Telemetry** | Stale records excluded from statistics without contaminating mean; missing values safely skipped. | **PASSED** |
| **Q8: Isolated Outage Handling** | Zero active neighbors deterministically yielded `INSUFFICIENT_CONTEXT`. | **PASSED** |
| **Causality & Leakage Proof** | Future corrupted records (t > T) yielded zero change in past context evaluations. | **PASSED** |

---

## 8. Limitations & Boundary Conditions
1. **Network Density Sensitivity**: In sparsely instrumented regions ($> 600\text{ km}$ station separation), micro-scale convective storms will naturally categorize as `INSUFFICIENT_CONTEXT` or `LOCAL_CLUSTER`.
2. **Elevation Inversions**: High-altitude stations in mountain terrain (e.g. Srinagar 1600m vs Delhi 214m) have persistent climatological offsets that require multi-station cluster baselining.
3. **Non-Calibrated Context**: Spatial evidence provides atmospheric consensus, not probabilistic ground-truth or hardware diagnostic confirmation.
