# SkyGuard AI — Data Specification

## 1. Scope & Data Model Overview
This document defines the data schemas, validation boundaries, 14 mandatory data principles, anomaly taxonomy, and spatial calculation rules for SkyGuard AI.

---

## 2. Mandatory Data Principles
1. **Raw observations are immutable**: Never overwrite, modify, or truncate raw incoming sensor records.
2. **Never silently overwrite original sensor data**: Corrections, imputations, and flag updates are stored in separate dedicated tables/collections.
3. **Validation results stored separately**: Quality control flags, step tests, and model outputs exist in parallel with raw readings.
4. **Suspicious $\neq$ Faulty**: Flagged observations must undergo spatial neighbor corroboration before flagging as hardware fault.
5. **Extreme $\neq$ Anomalous**: Extreme values matching valid synoptic meteorology (e.g., tropical storms) must not be flagged as broken hardware.
6. **Genuine weather events remain possible**: The system must explicitly permit rate-of-change exceptions when neighboring stations exhibit similar atmospheric dynamics.
7. **`UNCERTAIN` classification support**: When sensor output is ambiguous and lacks conclusive corroboration, label as `UNCERTAIN` rather than false certainty.
8. **ML anomaly scores are not probabilities**: Raw distance/reconstruction loss outputs must be presented as normalized anomaly scores, not uncalibrated probabilities.
9. **Confidence has a documented definition**: Confidence metric ($0.0 - 1.0$) reflects rule consensus, model certainty, and spatial agreement index.
10. **Synthetic anomaly injection support**: Pipeline must support injecting controlled anomalies into baseline historical series for evaluation.
11. **Ground-truth label isolation**: Injected evaluation labels must never leak into feature extraction or model inference.
12. **Reproducible data preprocessing**: All normalization, imputation, and scaling pipelines must be deterministic and serializable.
13. **Model traceability**: Every quality assessment record must link to the specific model version and feature pipeline version used.
14. **Geographic proximity based on coordinates**: Spatial neighbor calculations must use geodetic distance (Haversine/Vincenty on Latitude, Longitude, Elevation), never state or district boundaries.

---

## 3. Core Data Schemas

### 3.1. Normalized `WeatherObservation`
The central normalized data contract produced by all data adapters and parsers:

| Field Name | Type | Unit | Nullable | Description |
|---|---|---|---|---|
| `station_id` | `string` | — | No | Unique identifier for the Automatic Weather Station (e.g., `"42182099999"`) |
| `station_name` | `string` | — | Yes | Descriptive station name (e.g., `"SAFDARJUNG, IN"`) |
| `timestamp` | `datetime (UTC)` | ISO-8601 | No | Observation recording timestamp in timezone-aware UTC |
| `temperature` / `temperature_c` | `float` | °C | Yes | Ambient air temperature (physical bounds: $-50.0$ to $+60.0$) |
| `dew_point_c` | `float` | °C | Yes | Dew point temperature (physical bounds: $-80.0$ to $+60.0$) |
| `pressure` / `sea_level_pressure_hpa` | `float` | hPa | Yes | Sea-Level barometric pressure ($500.0$ to $1080.0$) |
| `station_pressure_hpa` | `float` | hPa | Yes | Atmospheric surface station pressure ($300.0$ to $1080.0$) |
| `humidity` / `relative_humidity_pct` | `float` | % | Yes | Relative humidity ($0.0$ to $100.0$) |
| `relative_humidity_source` | `string` | — | Yes | Derivation indicator (e.g., `"derived_from_temperature_and_dew_point"`) |
| `latitude` | `float` | Decimal degrees | No | Geodetic latitude ($-90.0$ to $+90.0$) |
| `longitude` | `float` | Decimal degrees | No | Geodetic longitude ($-180.0$ to $+180.0$) |
| `elevation` / `elevation_m` | `float` | Meters | Yes | Station elevation above sea level |
| `source` | `ObservationSource (Enum)` | — | No | Origin source: `NOAA_ISD`, `HISTORICAL_CSV`, `METEOSTAT`, `OPEN_METEO`, `SIMULATOR`, `WEATHER_API`, `MQTT` |
| `report_type` | `string` | — | Yes | Observational report format (e.g., `"FM-12"`, `"FM-15"`, `"METAR"`) |
| `raw_quality_flags` | `dict[str, Any]` | — | No | Preserved source quality codes (e.g. `{"TMP_QC": "1", "DEW_QC": "1", "SLP_QC": "1"}`) |
| `data_quality_status` | `QualityStatus (Enum)` | — | No | Normalized quality state: `VALID`, `SUSPECT`, `ERROR`, `MISSING`, `UNKNOWN` |
| `native_resolution_minutes` | `float` | Minutes | Yes | Estimated native station reporting interval |
| `is_synthetic` | `bool` | — | No | Flag indicating simulated/interpolated observation (`False` for native physical telemetry) |
| `ingestion_timestamp` | `datetime (UTC)` | ISO-8601 | No | Server timestamp when the record entered the SkyGuard pipeline |
| `metadata` | `dict[str, Any]` | — | No | Additional sensor telemetry (WND, battery voltage, signal strength) |

### 3.2. Station Metadata (`StationMetadata`)
| Field Name | Type | Description |
|---|---|---|
| `station_id` | `string` | Unique station identifier |
| `name` | `string` | Human-readable location / station name |
| `latitude` | `float` | Geodetic latitude |
| `longitude` | `float` | Geodetic longitude |
| `elevation` | `float` | Elevation in meters |
| `state` | `string` | State / administrative region (informative only) |
| `sampling_interval_seconds` | `int` | Expected reporting cadence (default: 300s / 5min) |
| `status` | `string` | `"ACTIVE"`, `"MAINTENANCE"`, `"DECOMMISSIONED"` |
| `installed_sensors` | `list[str]` | List of active sensors (e.g., `["TEMP", "PRES", "RH"]`) |

---

## 4. Anomaly Taxonomy (15 Operational Categories)
The architecture reserves the following 15 distinct anomaly classifications:

1. `NORMAL`: Reading conforms to physical bounds, temporal rates, and spatial neighbor consensus.
2. `SPIKE`: Transient single-point extreme impulse deviating from local rolling window.
3. `SMALL_SPIKE`: Low-amplitude impulse ($1.5 - 3\sigma$) detectable via residual filtering.
4. `DRIFT`: Progressive linear or monotonic deviation from true atmospheric baseline over hours/days.
5. `OFFSET`: Sudden persistent step-function jump in baseline value.
6. `FROZEN_SENSOR`: Consecutive invariant readings (zero variance) despite changing atmospheric conditions.
7. `INTERMITTENT_SENSOR`: Alternating valid and frozen/dropout signals over short windows.
8. `MISSING_DATA`: Expected observation packet not received within configurable timeout window.
9. `COMMUNICATION_ERROR`: Checksum failure, parity error, or corrupted payload formatting.
10. `DUPLICATE_DATA`: Redundant packet with identical timestamp and station identifier.
11. `OUT_OF_ORDER_DATA`: Delayed packet arriving with a timestamp older than current watermark.
12. `MULTIVARIATE_INCONSISTENCY`: Physical contradiction between parameters (e.g., RH = 99% with large dew-point spread).
13. `POSSIBLE_GENUINE_EVENT`: Extreme rate-of-change or extreme value corroborated by physical meteorology or spatial neighbors.
14. `UNCERTAIN`: Ambiguous anomaly signal lacking definitive statistical or spatial confirmation.
15. `MULTI_FAULT`: Multiple simultaneous faults (e.g., temperature drift + frozen humidity sensor).

---

## 5. Physical Validation Boundaries (Quality Control QC-0)

```yaml
validation_bounds:
  temperature:
    min_physical: -50.0  # °C
    max_physical: 60.0   # °C
    max_step_5min: 5.0   # Maximum plausible rate of change per 5-min
  pressure:
    min_physical: 500.0  # hPa
    max_physical: 1080.0 # hPa
    max_step_5min: 4.0   # Maximum plausible barometric rate of change per 5-min
  humidity:
    min_physical: 0.0    # %
    max_physical: 100.0  # %
    max_step_5min: 15.0  # Maximum plausible RH rate of change per 5-min
```

---

## 6. Spatial Proximity Calculation
To determine spatial consistency between Station $A (\phi_1, \lambda_1)$ and Station $B (\phi_2, \lambda_2)$:
- **Geodesic Distance Formula (Haversine)**:
  $$d = 2R \arcsin \left(\sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)}\right)$$
  Where $R = 6371.0 \text{ km}$.
- **Elevation Adjustment**:
  Barometric pressure readings are normalized to Mean Sea Level (MSL) using the barometric formula before spatial inter-station comparison:
  $$P_{\text{MSL}} = P \cdot \left(1 - \frac{0.0065 \cdot h}{T + 0.0065 \cdot h + 273.15}\right)^{-5.257}$$
- **State Boundaries**: Explicitly ignored in spatial consistency computations. Only physical distance and elevation delta are considered.

---

## 7. Dataset Selection Status
*Status: TBD — requires historical dataset selection during Phase 1.*
Supported historical ingestion formats will include standard IMD/WMO AWS CSV structures, NetCDF, and JSON telemetry archives.
