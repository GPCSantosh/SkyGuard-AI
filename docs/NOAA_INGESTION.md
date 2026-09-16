# SkyGuard AI — NOAA ISD Historical Ingestion Specification (Phase 1B)

**Document Version:** 1.0.0  
**Phase:** Phase 1B (NOAA ISD Ingestion, Normalization & Profiling)  
**Status:** Implemented & Verified  

---

## 1. Overview & Architecture

The NOAA Ingestion Pipeline ingests raw historical Automatic Weather Station (AWS) and synoptic weather observations from NOAA NCEI's Integrated Surface Database (ISD) / Global Hourly dataset into the canonical, immutable `WeatherObservation` schema of SkyGuard AI.

```
+-----------------------------------------------------------------------------------+
|                           NOAA NCEI ISD Data Source                               |
|   (Local 'data/raw/*.csv' or Remote 'https://www.ncei.noaa.gov/data/global-hourly')|
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+───────────────────────────────────────────────────────────────────────────────────+
|               NOAAParser (backend/app/ingestion/noaa_parser.py)                   |
|  - Multi-part composite field splitting (e.g. "+0108,1" -> 10.8°C, QC="1")       |
|  - Scaling factors (/10.0 for TMP, DEW, SLP)                                      |
|  - Quality control flag interpretation & normalization                            |
|  - WMO August-Roche-Magnus Relative Humidity derivation                           |
|  - Separation of Sea-Level Pressure (SLP) and Station Pressure (P_stn)           |
|  - Timezone-aware UTC normalization and ISO8601 formatting                        |
+───────────────────────────────────────────────────────────────────────────────────+
                                         │
                                         ▼
+───────────────────────────────────────────────────────────────────────────────────+
|              DatasetProfiler (backend/app/ingestion/profiler.py)                  |
|  - Cadence calculation (median, min, max, mode, regularity index)                 |
|  - Missingness profiling per variable                                             |
|  - Duplicate and out-of-order timestamp detection                                 |
|  - Summary statistical metrics (min, mean, max, median, std, IQR)                 |
|  - Markdown profile report & JSON export                                          |
+───────────────────────────────────────────────────────────────────────────────────+
                                         │
                                         ▼
+───────────────────────────────────────────────────────────────────────────────────+
|               Normalized Processed Store ('data/processed/')                      |
|  - data/processed/{STATION}_{YEAR}_normalized.csv                                 |
|  - data/processed/{STATION}_{YEAR}_normalized.jsonl                               |
|  - data/processed/{STATION}_{YEAR}_profile.json                                   |
+───────────────────────────────────────────────────────────────────────────────────+
```

---

## 2. Field Mapping & Unit Conversions

| NOAA Raw Column | Meaning | Raw Format Example | Processing / Conversion | Normalized Field in `WeatherObservation` | Unit |
|---|---|---|---|---|---|
| `STATION` | USAF-WBAN Station Identifier | `"42182099999"` | Direct string strip | `station_id` | String |
| `NAME` | Station Name & Country | `"SAFDARJUNG, IN"` | Direct string strip | `station_name` | String |
| `DATE` | Observation Timestamp | `"2024-01-01T00:00:00"` | Converted to UTC timezone-aware datetime | `timestamp` | UTC Datetime |
| `LATITUDE` | Station Latitude | `"28.584511"` | Decimal float | `latitude` | Decimal degrees |
| `LONGITUDE` | Station Longitude | `"77.205783"` | Decimal float | `longitude` | Decimal degrees |
| `ELEVATION` | Station Elevation | `"214.88"` | Decimal float (Missing: `-999.9` $\rightarrow$ `None`) | `elevation_m` / `elevation` | Meters |
| `TMP` | Air Temperature & QC | `"+0108,1"` | Scaled by $10.0$ ($+108 / 10 = 10.8$). Missing: `+9999,9` $\rightarrow$ `None` | `temperature_c` / `temperature` | $^\circ\text{C}$ |
| `DEW` | Dew Point Temperature & QC | `"+0100,1"` | Scaled by $10.0$ ($+100 / 10 = 10.0$). Missing: `+9999,9` $\rightarrow$ `None` | `dew_point_c` | $^\circ\text{C}$ |
| `SLP` | Sea-Level Barometric Pressure | `"10189,1"` | Scaled by $10.0$ ($10189 / 10 = 1018.9$). Missing: `99999,9` $\rightarrow$ `None` | `sea_level_pressure_hpa` / `pressure` | $\text{hPa}$ |
| `MA1` / `STP` | Station Atmospheric Pressure | `"09890,1,10189,1"` | Extracted from `MA1[0]` or `STP`, scaled by $10.0$. Missing $\rightarrow$ `None` | `station_pressure_hpa` | $\text{hPa}$ |
| *Derived* | Relative Humidity | Computed from `TMP` & `DEW` | August-Roche-Magnus formula | `relative_humidity_pct` / `humidity` | $\%$ |
| *Derived* | RH Derivation Provenance | `"derived_from_temperature_and_dew_point"` | Preserves calculation provenance | `relative_humidity_source` | String |
| `REPORT_TYPE` | Observational Report Type | `"FM-12"`, `"METAR"` | Preserved string | `report_type` | String |
| `QUALITY_CONTROL` | Record-level QC Version | `"V020"` | Preserved in flags | `raw_quality_flags["RECORD_QC"]` | String |

---

## 3. Relative Humidity Derivation (August-Roche-Magnus)

In accordance with WMO and Alduchov & Eskridge (1996) meteorological standards:
$$e_s(T) = 6.1078 \times \exp\left(\frac{17.625 \cdot T}{243.04 + T}\right)$$
$$e(T_d) = 6.1078 \times \exp\left(\frac{17.625 \cdot T_d}{243.04 + T_d}\right)$$
$$RH = 100.0 \times \frac{e(T_d)}{e_s(T)} = 100.0 \times \exp\left(\frac{17.625 \cdot T_d}{243.04 + T_d} - \frac{17.625 \cdot T}{243.04 + T}\right)$$

### Rules:
1. If either $T$ or $T_d$ is missing (`None`), $RH$ evaluates strictly to `None`.
2. Clamping: If $T_d > T$ (sensor calibration drift or supersaturation), $RH$ is clamped to $100.0\%$ under default ingestion rules.
3. Metadata attribution: `relative_humidity_source = "derived_from_temperature_and_dew_point"`.

---

## 4. Quality Control (QC) Code Interpretation

| NOAA QC Flag Code | NOAA Definition | SkyGuard `QualityStatus` | Handling Rule |
|---|---|---|---|
| `1` | Passed all quality control checks | `VALID` | Fully valid observation |
| `2` | Suspect observation | `SUSPECT` | Retained for anomaly analysis |
| `3` | Erroneous observation | `ERROR` | Retained for fault detection |
| `4` | Passed gross limits check | `VALID` | Validated gross limits |
| `5` | Passed all QC and time series check | `VALID` | Verified against continuity |
| `6` | Suspect on time series check | `SUSPECT` | Continuity anomaly candidate |
| `7` | Erroneous on time series check | `ERROR` | Continuity failure candidate |
| `9` | Passed gross check or missing | `MISSING` (if null) / `UNKNOWN` | Flagged as unverified or missing |

---

## 5. CLI Usage & Pipeline Commands

### Ingest a Local Sample File:
```bash
python scripts/ingest_noaa.py --input-file data/external/sample_noaa_isd_42182099999.csv --output-dir data/processed
```

### Download and Ingest Station Telemetry by Station ID and Year:
```bash
python scripts/ingest_noaa.py --station 42182099999 --year 2024 --download-if-missing
```

### Dry-Run Profiling (Without Saving Files):
```bash
python scripts/ingest_noaa.py --input-file data/raw/42182099999_2024.csv --profile-only
```

---

## 6. Real-World Sample Profile Output (New Delhi Safdarjung, 2024)

```markdown
# Dataset Profile: Station 42182099999 (SAFDARJUNG, IN)
- **Total Observations:** 50
- **Time Coverage (UTC):** 2024-01-01T00:00:00+00:00 to 2024-01-07T06:00:00+00:00 (6.2 days)
- **Location:** Lat 28.5845°, Lon 77.2058°, Elev 214.88m
- **Cadence (minutes):** Median=180.0, Min=30.0, Max=540.0, Mode=180.0 (Regular: True)
- **Timestamp Issues:** Duplicates=1, Out-of-order=0

## Meteorological Variables Summary
| Parameter | Valid Count | Missing % | Min | Mean | Max | Median | Std |
|---|---|---|---|---|---|---|---|
| Temperature (°C) | 50 | 0.0% | 8.0 | 11.3 | 16.8 | 10.6 | 2.1 |
| Dew Point (°C) | 50 | 0.0% | 6.8 | 8.8 | 11.9 | 8.7 | 1.3 |
| SLP Pressure (hPa) | 48 | 4.0% | 1016.0 | 1018.9 | 1023.2 | 1019.0 | 1.5 |
| Station Pressure (hPa) | 2 | 96.0% | 1021.0 | 1021.5 | 1022.0 | 1021.5 | 0.5 |
| Relative Humidity (%) | 50 | 0.0% | 55.0 | 85.6 | 100.0 | 89.5 | 11.0 |

## Quality Control Distribution
| Quality Status | Count | Percentage |
|---|---|---|
| VALID | 50 | 100.0% |
```
