# SkyGuard AI — Historical Weather Dataset Research & Qualification (Phase 1A)

**Document Version:** 1.0.0  
**Phase:** Phase 1A (Data Discovery & Dataset Qualification)  
**Author:** SkyGuard AI Engineering Team  
**Status:** Completed & Verified  

---

## 1. Executive Summary

Phase 1A qualifies and compares candidate historical meteorological datasets to establish the data foundation for SkyGuard AI's Automatic Weather Station (AWS) anomaly detection platform. 

SkyGuard AI requires three core meteorological variables:
1. **Temperature ($T$, $^\circ\text{C}$)**
2. **Atmospheric Pressure ($P$, $\text{hPa}$)** — distinguishing Station Pressure vs. Sea-Level Pressure
3. **Relative Humidity ($RH$, $\%$ )** — directly observed or derived from Temperature and Dew Point

We evaluated candidate datasets across provenance, temporal resolution (evaluating the target 5-minute design against available resolutions), geographical station coverage across India ($\ge 20$ stations with exact coordinates and elevation), missingness characteristics, and programmatic access reliability.

### Key Recommendations:
- **Primary Candidate:** **NOAA NCEI Integrated Surface Database (ISD) / Global Hourly**  
  *Rationale:* Authentic, high-integrity station observations from real meteorological instruments with 545 historical and 410+ active stations across India. Provides exact WMO quality flags, 30-minute to 3-hourly resolution, and public-domain, unauthenticated programmatic access.
- **Secondary Backup Candidate:** **Meteostat Hourly Aggregated Observations**  
  *Rationale:* Standardized, pre-processed hourly station time series derived from ISD and national agencies with pre-calculated Relative Humidity and Sea-Level Pressure.
- **Reanalysis Reference Benchmark:** **Open-Meteo Historical Archive (ECMWF ERA5)**  
  *Rationale:* Continuous 1-hour model reanalysis providing a complete baseline with both station pressure and sea-level pressure, ideal for spatial reference validation, though explicitly distinguished from raw hardware observations.

---

## 2. Candidate Datasets Investigated

We investigated four primary candidate data sources:

| Candidate | Provider / Source | Provenance Category | Access Mechanism |
|---|---|---|---|
| **Candidate 1: NOAA NCEI ISD / Global Hourly** | NOAA National Centers for Environmental Information (US) | **A. Real Station Observations** (GTS SYNOP FM-12 / METAR) | Direct HTTPS CSV / S3 Open Data / ISD-Lite |
| **Candidate 2: Meteostat Hourly** | Meteostat Open Data Project | **B. Aggregated Station Observations** | Bulk Gzip CSV / Python Library (`meteostat`) |
| **Candidate 3: Open-Meteo Historical API** | Open-Meteo / ECMWF | **C. Reanalysis & Numerical Weather Models** (ERA5 / ERA5-Land) | REST API (JSON / CSV) |
| **Candidate 4: IMD AWS Portal / MOSDAC** | India Meteorological Department (IMD) / ISRO | **A. Real Station Observations** (Indian National AWS Network) | Web Portal / MOSDAC HDF5 (Restricted/Auth) |

---

## 3. Dataset Comparison Table

> **Note on Evaluation Methodology:** Per project engineering rules, datasets are evaluated using qualitative, evidence-based criteria. Arbitrary numerical scoring has been intentionally avoided to preserve scientific rigor.

| Evaluation Criterion | Candidate 1: NOAA NCEI ISD / Global Hourly | Candidate 2: Meteostat Hourly | Candidate 3: Open-Meteo (ERA5 Reanalysis) | Candidate 4: IMD AWS / MOSDAC Portal |
|---|---|---|---|---|
| **India Coverage** | Extensive (545 total stations, 410+ active post-2024) | High (~150+ major Indian stations) | Universal (any lat/lon coordinate on 0.1° grid) | National (Hundreds of AWS/ARG stations across India) |
| **Verified Indian Stations** | 23 major stations tested and verified across all climatic zones | ~20+ major metropolitan & airport stations | All Indian territory | Variable availability depending on portal state |
| **Air Temperature ($T$)** | Direct sensor observation (`TMP`), 0.1°C resolution with QC flag | Direct standardized observation (`temp`, °C) | Reanalysis 2m temperature (`temperature_2m`, °C) | Direct sensor observation (°C) |
| **Pressure ($P$)** | Sea-Level Pressure (`SLP`) core; Station Pressure (`MA1`) on select stations | Sea-Level Pressure (`pres`, hPa) | Both Surface Station Pressure (`surface_pressure`) and MSLP (`pressure_msl`) | Station Pressure and MSLP reported |
| **Relative Humidity ($RH$)** | Derived via Magnus equation from `TMP` and `DEW` (dew point) | Direct pre-calculated (`rhum`, %) | Direct reanalysis (`relative_humidity_2m`, %) | Direct sensor observation (%) |
| **Temporal Resolution** | 30 minutes (Airport METAR AWS) to 3 hours (Synoptic SYNOP) | 1 hour (Standardized) | 1 hour (Continuous) | 15 minutes to 1 hour |
| **Coordinates & Elevation** | Latitude, Longitude, Elevation (m) in every record and station index | Latitude, Longitude, Elevation (m) via station metadata | Exact latitude, longitude, and elevation from DEM | Station name, latitude, longitude, elevation |
| **Historical Coverage** | 1970–present (Decades of continuous records) | 1970–present | 1940–present | Intermittent archive (1–5 years public) |
| **Observational Provenance** | **True Station Observations** (Hardware sensors, WMO telemetry) | **Aggregated Observations** (Cleaned from ISD/DWD) | **Model Reanalysis** (Assimilated physical model) | **True Station Observations** (IMD AWS hardware) |
| **Missingness Characteristics** | Real-world missingness (sensor dropouts, reporting gaps, maintenance) | Minimal gaps (interpolated or masked as NaN) | 0% missingness (synthetic continuity by design) | Frequent station outages and transmission gaps |
| **Programmatic Access Ease** | High: Direct HTTPS CSV downloads by year and station ID | High: Gzipped CSV dumps and Python API | High: Open REST API with JSON/CSV output | Low: Dynamic session cookies, web scraping barriers |
| **Licensing** | Public Domain (US Gov / NOAA Open Data Policy) | Open Data (CC-BY-NC 4.0 for non-commercial) | Open Data (CC BY 4.0) | Restricted / Government portal terms of use |
| **Spatial Anomaly Suitability** | High: True local spatial correlations and microclimate variations | High: Standardized timestamps for cross-station comparison | Moderate: Spatially smooth (lacks local sensor variance) | High: Dense Indian network |
| **Temporal Anomaly Suitability** | High for $\ge 30$-min dynamics; requires simulation for 5-min spikes | Moderate for hourly dynamics; lacks sub-hourly micro-spikes | Low for sensor faults (model data is inherently smooth) | High: 15-minute captures rapid weather shifts |
| **Synthetic Injection Suitability** | Excellent: Authentic baseline noise, diurnal cycles, and physical realism | Excellent: Clean baseline ready for anomaly injection | Good: Predictable baseline, but lacks physical sensor noise | High: Authentic telemetry |
| **Overall Recommendation** | **PRIMARY RECOMMENDED DATASET** | **BACKUP CANDIDATE (Standardized)** | **SUPPLEMENTAL BENCHMARK (Reanalysis)** | **FUTURE REAL-TIME INTEGRATION TARGET** |

---

## 4. Detailed Candidate Assessment

### Candidate 1: NOAA NCEI Integrated Surface Database (ISD) / Global Hourly
- **Provider:** National Oceanic and Atmospheric Administration (NOAA) / National Centers for Environmental Information (NCEI).
- **Provenance:** Genuine observational data reported via the World Meteorological Organization (WMO) Global Telecommunication System (GTS). Comprises manual synoptic observations (FM-12 SYNOP) and automated airport weather stations (METAR/SPECI).
- **India Verification:** Programmatically verified 23 active stations across all Indian climate zones:
  - *North / Subtropical:* New Delhi Safdarjung (`42182099999`), New Delhi IGI Airport (`42181099999`), Amritsar (`42071099999`), Patiala (`42101099999`).
  - *West / Coastal & Arid:* Mumbai Santacruz (`43003099999`), Mumbai Colaba (`43057099999`), Ahmedabad (`42647099999`), Jodhpur (`42339099999`).
  - *South / Peninsula & Islands:* Bengaluru HAL (`43295099999`), Chennai (`43279099999`), Thiruvananthapuram (`43371099999`), Goa Dabolim (`43192099999`), Minicoy (`43369099999`), Port Blair (`43346099999`).
  - *Central & Deccan:* Nagpur (`42867099999`), Hyderabad Begumpet (`43128099999`), Pune (`43063099999`), Indore (`42754099999`).
  - *East & Northeast:* Kolkata Dum Dum (`42809099999`), Guwahati (`42410099999`), Dibrugarh (`42314099999`), Allahabad (`42475099999`).
  - *Himalayan / High Altitude:* Srinagar (`42027099999`, elevation 1,587m).
- **Sampling Volume (2024 Actuals):**
  - Major airport automated stations: **18,000 to 19,635 records/year** per station (~30-minute sampling interval).
  - Synoptic stations: **2,700 to 2,888 records/year** per station (~3-hourly synoptic interval).
- **Quality Control:** Every record includes explicit NOAA QC codes (`1` = Passed quality check, `2` = Suspect, `3` = Erroneous, `9` = Passed gross check).

### Candidate 2: Meteostat Hourly
- **Provider:** Meteostat Open Source Data Project.
- **Provenance:** Aggregated station observations compiled and normalized from NOAA ISD, Deutscher Wetterdienst (DWD), Environment and Climate Change Canada (ECCC), and others.
- **Characteristics:** Provides standardized 1-hour records. Dew point and temperature are converted into relative humidity (`rhum`) beforehand. Pressure is normalized to sea level (`pres`).
- **Limitation:** Bulk gzip HTTP endpoints may throttle direct continuous automated scrapers without rate limits; licensing is CC-BY-NC 4.0.

### Candidate 3: Open-Meteo Historical Weather API (ERA5 Reanalysis)
- **Provider:** Open-Meteo / European Centre for Medium-Range Weather Forecasts (ECMWF).
- **Provenance:** Reanalysis model (ERA5 / ERA5-Land). Gridded numerical integration combining physical weather simulation equations with historical observation assimilation.
- **Strengths:** Zero missing values, seamless 1-hour continuous resolution, separates surface station pressure (`surface_pressure`) from sea-level pressure (`pressure_msl`).
- **Critical Limitation for Anomaly Detection:** Lacks real hardware anomalies, digitization artifacts, frozen sensor glitches, and calibration drift. Using pure reanalysis as the primary training set would misrepresent real AWS telemetry behavior.

### Candidate 4: IMD AWS Portal (aws.imd.gov.in / MOSDAC)
- **Provider:** India Meteorological Department (IMD) / Ministry of Earth Sciences.
- **Provenance:** Primary ground-truth Indian Automatic Weather Stations.
- **Strengths:** True 15-minute Indian AWS telemetry.
- **Limitations:** Lacks an open, stable REST API for historical multi-year bulk extraction without institutional credentials; web interface enforces dynamic session tokens and periodic maintenance downtime. Ideal as a future real-time ingest connector target, but high friction for offline historical baseline benchmarking.

---

## 5. Temporal Resolution Analysis & The 5-Minute Design Tradeoff

SkyGuard AI's operational specification targets a **5-minute observation interval**. Real-world historical station archives offer different temporal characteristics:

```
+-------------------------------------------------------------------------------+
| NOAA METAR AWS (30-min)    | [t0] ---------- [t30] ---------- [t60]           |
| Meteostat Hourly (60-min)  | [t0] --------------------------- [t60]           |
| SkyGuard Target (5-min)    | [t0]-[t5]-[t10]-[t15]-[t20]-[t25]-[t30] ...      |
+-------------------------------------------------------------------------------+
```

### Consequences of Candidate Resolutions:

1. **30-Minute Observations (NOAA METAR AWS):**
   - *Strengths:* Captures diurnal cycles, frontal passages, rapid pressure drops during thunderstorms, and genuine sensor variance.
   - *Limitations:* Cannot capture high-frequency single 5-minute transient sensor spikes (e.g., a momentary ADC glitch lasting 1–3 minutes) without interpolation.
   - *Strategy:* Use genuine 30-minute data as anchor points, with physically consistent spline or meteorological interpolation down to 5-minute steps when micro-frequency testing is required.

2. **1-Hour Observations (Meteostat / Synoptic / Reanalysis):**
   - *Strengths:* Excellent for long-term drift detection, baseline calibration, and macro-scale spatial anomaly detection.
   - *Limitations:* Over-smooths rapid convective storm onset and sudden wind squall temperature drops.

3. **5-Minute Operational Simulation Strategy for SkyGuard AI:**
   - **Baseline Generation:** Ingest verified 30-minute / hourly observational data.
   - **Configurable Ingestion Engine:** The ingestion connector accepts timestamps at native resolution (30-min / 60-min) OR configurable 5-minute simulated intervals.
   - **Synthetic Anomaly Injection:** Injecting anomalies (spikes, drift, stuck values) can be applied directly at the native observation timestamps or upon 5-minute sub-sampled series.
   - **Scientific Rule:** The system will **never label interpolated hourly data as native 5-minute observations**; metadata will clearly state `resolution_minutes: 30` or `is_synthetic_subsampled: true`.

---

## 6. Meteorological Variable Availability & Relative Humidity Derivation

### 6.1 Temperature ($T$)
- Available across all candidates in degrees Celsius ($^\circ\text{C}$).
- NOAA ISD provides tenths of a degree Celsius (`TMP = +0108` $\rightarrow 10.8^\circ\text{C}$) accompanied by a quality flag (`1`).

### 6.2 Atmospheric Pressure ($P$): Station vs. Sea-Level Pressure
- **Sea-Level Pressure ($P_{\text{SLP}}$):** Atmospheric pressure reduced to mean sea level. Standard across all synoptic stations (`SLP` in NOAA ISD, `pres` in Meteostat).
- **Station Pressure ($P_{\text{stn}}$):** True local barometric pressure measured at the sensor barometer elevation ($z$).
- **Relationship & Conversion:**
  Where station elevation $z$ is known, $P_{\text{stn}}$ and $P_{\text{SLP}}$ relate via the barometric hypsometric formula:
  $$P_{\text{stn}} = P_{\text{SLP}} \cdot \left(1 - \frac{L \cdot z}{T_0}\right)^{\frac{g \cdot M}{R_0 \cdot L}}$$
  *(where $L = 0.0065\text{ K/m}$ is standard lapse rate, $g = 9.80665\text{ m/s}^2$, $T_0 = 288.15\text{ K}$, $R_0 = 8.31447\text{ J/(mol}\cdot\text{K)}$).*
- **Design Rule:** SkyGuard AI stores both raw observed pressure and sea-level normalized pressure to enable valid spatial comparisons between stations at different elevations (e.g., Srinagar at 1,587m vs. Mumbai at 14m).

### 6.3 Relative Humidity ($RH$) Derivation Analysis
In NOAA ISD, relative humidity is not directly stored as a core field; instead, **Air Temperature ($T$)** and **Dew Point Temperature ($T_d$)** are directly measured and recorded with high accuracy.

#### Scientific Derivation Equation (August-Roche-Magnus Formula)
Saturation vapor pressure $e_s(T)$ and actual vapor pressure $e(T_d)$ are computed using the WMO-standard Magnus approximation:
$$e_s(T) = c \cdot \exp\left(\frac{a \cdot T}{b + T}\right)$$
$$e(T_d) = c \cdot \exp\left(\frac{a \cdot T_d}{b + T_d}\right)$$
$$\text{Relative Humidity } RH = 100 \times \frac{e(T_d)}{e_s(T)} = 100 \times \exp\left(\frac{a \cdot T_d}{b + T_d} - \frac{a \cdot T}{b + T}\right)$$

Where constants (Alduchov & Eskridge, 1996 / WMO guidelines):
- $a = 17.625$
- $b = 243.04^\circ\text{C}$
- $c = 6.1078\text{ hPa}$

#### Error & Uncertainty Assessment:
- The Magnus formulation introduces an approximation error of $<\pm 0.1\%$ over the operational meteorological range $-40^\circ\text{C} \le T \le 50^\circ\text{C}$.
- Because $T$ and $T_d$ in NOAA ISD are measured with $0.1^\circ\text{C}$ precision, the resulting $RH$ uncertainty is bounded within $\pm 0.6\%$, which is well within the typical hardware sensor tolerance ($\pm 2\%\text{ to }\pm 3\%$) of physical capacitive humidity sensors.
- **Scientific Conclusion:** Deriving $RH$ from validated $T$ and $T_d$ is scientifically sound, rigorous, and standard practice in observational climatology.

---

## 7. Spatial Network Analysis (India Coverage)

To support geodesic distance-based spatial anomaly detection (comparing neighboring stations without relying on arbitrary administrative boundaries), at least 20 geographically distributed stations are required.

### Verified 23-Station Indian Network:

```
                          [Srinagar (1587m)]
                                 |
                     [Amritsar] [Patiala]
                                 |
                 [Jodhpur]   [New Delhi (Safdarjung & Palam)]
                     |           |
            [Ahmedabad]      [Indore]      [Allahabad]   [Guwahati] [Dibrugarh]
                 |               |               |              |
         [Mumbai (Col/San)]  [Nagpur]       [Kolkata]
                 |               |
               [Goa]        [Hyderabad]
                 |               |
            [Bengaluru]      [Chennai]
                 |
        [Thiruvananthapuram]
                 |
        [Minicoy (Island)]                   [Port Blair (Andaman)]
```

### Spatial Characteristics:
1. **Latitude Span:** $8.30^\circ\text{N}$ (Minicoy) to $34.08^\circ\text{N}$ (Srinagar)
2. **Longitude Span:** $72.63^\circ\text{E}$ (Ahmedabad) to $95.02^\circ\text{E}$ (Dibrugarh)
3. **Elevation Span:** $2\text{m}$ (Minicoy) to $1,587\text{m}$ (Srinagar)
4. **Climatic Zones Represented:**
   - *High Altitude / Montane Alpine:* Srinagar
   - *Hot Semi-Arid / Desert:* Jodhpur, Ahmedabad
   - *Composite / Gangetic Plains:* New Delhi, Patiala, Allahabad, Amritsar
   - *Humid Subtropical / Northeast Hills:* Guwahati, Dibrugarh
   - *Tropical Wet & Dry / Coastal:* Mumbai, Chennai, Goa, Kolkata, Thiruvananthapuram
   - *Tropical Semi-Arid / Deccan Plateau:* Bengaluru, Hyderabad, Nagpur, Indore
   - *Island Maritime:* Minicoy (Lakshadweep), Port Blair (Andaman & Nicobar)

---

## 8. Data Inspection Findings & Artifacts

Lightweight sample datasets were downloaded and inspected in `data/external/`:
1. `data/external/sample_noaa_isd_42182099999.csv` (50 rows, New Delhi Safdarjung, 2024)
2. `data/external/sample_open_meteo_delhi.csv` (50 rows, Delhi Reanalysis, 2024)

### Inspection Summary:
- **NOAA ISD Schema:** 34 columns including `DATE`, `STATION`, `LATITUDE`, `LONGITUDE`, `ELEVATION`, `NAME`, `REPORT_TYPE`, `QUALITY_CONTROL`, `WND`, `TMP`, `DEW`, `SLP`. Missing values are cleanly encoded as `+9999` or empty commas.
- **Open-Meteo Schema:** Clean tabular 8 columns (`time`, `temperature_2m`, `relative_humidity_2m`, `surface_pressure`, `pressure_msl`, `dew_point_2m`, `precipitation`, `wind_speed_10m`).

---

## 9. Licensing & Compliance Notes

1. **NOAA NCEI ISD:** Unrestricted Public Domain (US Federal Government open data, NOAA Open Data Dissemination policy). Commercial and academic use permitted without royalty or authentication.
2. **Meteostat:** Open Data (Creative Commons Attribution-NonCommercial 4.0 International - CC BY-NC 4.0). Suitable for research, academic, and hackathon prototype projects.
3. **Open-Meteo / ECMWF ERA5:** Creative Commons Attribution 4.0 International (CC BY 4.0). Free for research with attribution.

---

## 10. Risks & Unknowns

| Risk / Unknown | Impact | Mitigation Strategy |
|---|---|---|
| **Varying Reporting Frequency** | Stations have mixed sampling rates (30-min airport vs. 3-hr synoptic). | Implement robust timestamp indexing in ingestion pipeline; support irregular time intervals in feature calculation. |
| **Missing Observations** | Real AWS telemetry experiences transmission dropouts (2–5% missingness). | Track missingness explicitly (`is_missing` flag); implement quality metrics before anomaly evaluation. |
| **Elevation Pressure Discrepancy** | High-altitude stations (e.g. Srinagar) have lower raw pressure (~830 hPa) than sea-level stations (~1013 hPa). | Always normalize spatial neighbors using Sea-Level Pressure ($P_{\text{SLP}}$) or elevation-adjusted barometric formulas. |

---

## 11. Final Recommendations

### Primary Recommendation: **NOAA NCEI ISD / Global Hourly**
- **Why:** Real physical observations with genuine sensor noise and authentic weather extremes. Free, unauthenticated HTTPS access, 23+ Indian stations across all climate zones, and full WMO quality control flags.

### Secondary Backup Recommendation: **Meteostat Hourly (or Open-Meteo for Reanalysis Reference)**
- **Why:** Pre-formatted hourly records with direct $RH$ values, enabling rapid verification and testing if raw NOAA CSV parsing needs a secondary validation cross-check.

---

## 12. Exact Source URLs

1. **NOAA NCEI ISD Station Master History:**  
   `https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv`
2. **NOAA NCEI Global Hourly CSV Access (Pattern):**  
   `https://www.ncei.noaa.gov/data/global-hourly/access/{YEAR}/{STATION_ID}.csv`  
   *Example (Delhi Safdarjung 2024):* `https://www.ncei.noaa.gov/data/global-hourly/access/2024/42182099999.csv`  
   *Example (Mumbai Santacruz 2024):* `https://www.ncei.noaa.gov/data/global-hourly/access/2024/43003099999.csv`
3. **NOAA ISD Format Documentation:**  
   `https://www.ncei.noaa.gov/data/global-hourly/doc/isd-format-document.pdf`
4. **Meteostat Bulk Data Archive:**  
   `https://bulk.meteostat.net/v2/hourly/{STATION_ID}.csv.gz`
5. **Open-Meteo Historical Weather API:**  
   `https://archive-api.open-meteo.com/v1/archive`
6. **IMD AWS Web Portal:**  
   `http://aws.imd.gov.in/`
7. **ISRO MOSDAC Portal:**  
   `https://www.mosdac.gov.in/`

---

## 13. Recommended Next Action for Project Owner

With Phase 1A complete and candidate datasets qualified, the project owner can approve:
1. **Selection of Primary Dataset:** Confirm **NOAA NCEI Global Hourly (ISD)** as the primary historical baseline and **Meteostat / Open-Meteo** as secondary references.
2. **Phase 1B Authorization:** Proceed to **Phase 1B (Ingestion Engine Implementation & Connector Refinement)** to build the dedicated NOAA ISD ingestion parser and synthetic 5-minute sampling adapter.
