"""CSV Schema Mapping Layer, Normalization and Dataset Preview Generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.observation import ObservationSource, QualityStatus, WeatherObservation

# Known standard column aliases mapping to canonical WeatherObservation fields
COLUMN_ALIASES: Dict[str, List[str]] = {
    "station_id": ["station_id", "station", "stn", "aws_id", "STATION"],
    "station_name": ["station_name", "name", "station_desc", "NAME"],
    "timestamp": ["timestamp", "time", "date", "date_time", "datetime", "DATE", "OBS_TIME"],
    "temperature": [
        "temperature", "temperature_c", "temp", "temp_c", "air_temp", "TMP",
        "temp_degree_c", "temperature_celsius"
    ],
    "dew_point_c": ["dew_point_c", "dew_point", "dewpoint", "dew_pt", "DEW"],
    "humidity": [
        "humidity", "relative_humidity", "relative_humidity_pct", "rh", "rhum",
        "rel_hum", "HUM"
    ],
    "pressure": [
        "pressure", "sea_level_pressure", "sea_level_pressure_hpa", "mslp", "slp",
        "barometer", "baro_pressure", "SLP"
    ],
    "station_pressure_hpa": ["station_pressure_hpa", "station_pressure", "stp", "STP"],
    "latitude": ["latitude", "lat", "LATITUDE", "y"],
    "longitude": ["longitude", "lon", "lng", "LONGITUDE", "x"],
    "elevation": ["elevation", "elevation_m", "elev", "ELEVATION", "z", "alt", "altitude"],
}

REQUIRED_CANONICAL_FIELDS = ["station_id", "timestamp", "temperature", "humidity", "pressure"]
OPTIONAL_CANONICAL_FIELDS = ["station_name", "dew_point_c", "station_pressure_hpa", "latitude", "longitude", "elevation"]


class ColumnMappingReview(BaseModel):
    """Result of column mapping auto-detection."""
    model_config = ConfigDict(frozen=True)

    detected_mapping: Dict[str, str]  # CSV column -> canonical field
    unmapped_columns: List[str]
    missing_required_fields: List[str]
    is_valid: bool
    warnings: List[str]


class CSVDatasetPreview(BaseModel):
    """Detailed summary preview of a CSV file prior to ingestion."""
    model_config = ConfigDict(frozen=True)

    file_name: str
    row_count: int
    station_count: int
    stations: List[str]
    start_time: Optional[str]
    end_time: Optional[str]
    detected_cadence_minutes: float
    missingness_pct: Dict[str, float]
    column_mapping: Dict[str, str]
    unmapped_columns: List[str]
    missing_required_fields: List[str]
    has_ground_truth: bool
    warnings: List[str]
    sample_rows: List[Dict[str, Any]]


class CSVNormalizer:
    """Normalizes raw DataFrame / CSV data into canonical WeatherObservation models."""

    @staticmethod
    def infer_column_mapping(df_columns: List[str]) -> ColumnMappingReview:
        """Infer canonical field mapping from input CSV column headers."""
        detected_mapping: Dict[str, str] = {}
        unmapped: List[str] = []
        found_canonical: set[str] = set()

        for col in df_columns:
            clean_col = col.strip()
            matched_canonical = None

            for canonical_field, aliases in COLUMN_ALIASES.items():
                if clean_col.lower() in [a.lower() for a in aliases] or clean_col == canonical_field:
                    matched_canonical = canonical_field
                    break

            if matched_canonical and matched_canonical not in found_canonical:
                detected_mapping[clean_col] = matched_canonical
                found_canonical.add(matched_canonical)
            else:
                unmapped.append(clean_col)

        missing_required = [f for f in REQUIRED_CANONICAL_FIELDS if f not in found_canonical]
        warnings: List[str] = []

        if missing_required:
            warnings.append(f"Missing required canonical fields: {', '.join(missing_required)}")

        if "latitude" not in found_canonical or "longitude" not in found_canonical:
            warnings.append("Geospatial coordinates (latitude/longitude) not detected; using default station lookup if available.")

        return ColumnMappingReview(
            detected_mapping=detected_mapping,
            unmapped_columns=unmapped,
            missing_required_fields=missing_required,
            is_valid=len(missing_required) == 0,
            warnings=warnings,
        )

    @classmethod
    def generate_preview(cls, file_path: Path | str, user_mapping: Optional[Dict[str, str]] = None) -> CSVDatasetPreview:
        """Parse CSV sample and generate comprehensive summary preview."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"CSV file not found: {path}")

        df = pd.read_csv(path)
        mapping_review = cls.infer_column_mapping(list(df.columns))
        active_mapping = user_mapping or mapping_review.detected_mapping

        # Rename mapped columns for internal summary calculation
        renamed_df = df.rename(columns=active_mapping)

        row_count = len(df)
        station_col = "station_id" if "station_id" in renamed_df.columns else None
        stations = sorted(list(renamed_df[station_col].dropna().unique().astype(str))) if station_col else ["UNKNOWN_STATION"]
        station_count = len(stations)

        # Time range & cadence detection
        start_time_str = None
        end_time_str = None
        cadence_min = 5.0

        if "timestamp" in renamed_df.columns:
            try:
                parsed_time = pd.to_datetime(renamed_df["timestamp"], utc=True, errors="coerce").dropna()
                if not parsed_time.empty:
                    start_time_str = parsed_time.min().isoformat()
                    end_time_str = parsed_time.max().isoformat()

                    # Estimate cadence from median diff per station
                    diffs = []
                    if station_col:
                        for _, stn_df in renamed_df.groupby(station_col):
                            stn_time = pd.to_datetime(stn_df["timestamp"], utc=True, errors="coerce").sort_values().dropna()
                            if len(stn_time) > 1:
                                diffs.extend(stn_time.diff().dt.total_seconds().dropna() / 60.0)
                    if diffs:
                        cadence_min = round(float(np.median([d for d in diffs if d > 0])), 1)
            except Exception:
                pass

        # Missingness calculation
        missingness: Dict[str, float] = {}
        for canonical in REQUIRED_CANONICAL_FIELDS + OPTIONAL_CANONICAL_FIELDS:
            if canonical in renamed_df.columns:
                null_pct = (renamed_df[canonical].isnull().sum() / max(1, row_count)) * 100.0
                missingness[canonical] = round(float(null_pct), 1)
            else:
                missingness[canonical] = 100.0

        # Check for ground truth label column
        has_gt = "ground_truth_anomaly" in df.columns or "is_anomaly" in df.columns or "anomaly_label" in df.columns

        sample_rows = df.head(5).to_dict(orient="records")

        return CSVDatasetPreview(
            file_name=path.name,
            row_count=row_count,
            station_count=station_count,
            stations=stations[:20],
            start_time=start_time_str,
            end_time=end_time_str,
            detected_cadence_minutes=cadence_min,
            missingness_pct=missingness,
            column_mapping=active_mapping,
            unmapped_columns=mapping_review.unmapped_columns,
            missing_required_fields=mapping_review.missing_required_fields,
            has_ground_truth=has_gt,
            warnings=mapping_review.warnings,
            sample_rows=sample_rows,
        )

    @classmethod
    def parse_to_observations(
        cls,
        file_path: Path | str,
        user_mapping: Optional[Dict[str, str]] = None,
        run_id: Optional[str] = None,
        source_type: str = "HISTORICAL_CSV",
        source_name: str = "Historical CSV",
        dataset_id: str = "custom_csv",
        dataset_version: str = "1.0.0",
    ) -> List[WeatherObservation]:
        """Convert CSV rows into normalized WeatherObservation objects with strict type conversion."""
        path = Path(file_path)
        df = pd.read_csv(path)
        mapping_review = cls.infer_column_mapping(list(df.columns))
        active_mapping = user_mapping or mapping_review.detected_mapping

        renamed_df = df.rename(columns=active_mapping)
        observations: List[WeatherObservation] = []

        for idx, row in renamed_df.iterrows():
            stn_id = str(row.get("station_id", f"AWS_CSV_{idx % 10 + 1:03d}")).strip()
            ts_val = row.get("timestamp")
            if pd.isna(ts_val):
                continue

            try:
                parsed_ts = pd.to_datetime(ts_val, utc=True).to_pydatetime()
            except Exception:
                continue

            # Extracted parameters with fallbacks
            temp = float(row["temperature"]) if "temperature" in row and not pd.isna(row["temperature"]) else None
            dew = float(row["dew_point_c"]) if "dew_point_c" in row and not pd.isna(row["dew_point_c"]) else None
            rh = float(row["humidity"]) if "humidity" in row and not pd.isna(row["humidity"]) else None
            slp = float(row["pressure"]) if "pressure" in row and not pd.isna(row["pressure"]) else None
            stp = float(row["station_pressure_hpa"]) if "station_pressure_hpa" in row and not pd.isna(row["station_pressure_hpa"]) else None
            lat = float(row["latitude"]) if "latitude" in row and not pd.isna(row["latitude"]) else 28.6139
            lon = float(row["longitude"]) if "longitude" in row and not pd.isna(row["longitude"]) else 77.2090
            elev = float(row["elevation"]) if "elevation" in row and not pd.isna(row["elevation"]) else 216.0
            stn_name = str(row.get("station_name", f"Station {stn_id}"))

            # Handle ground truth label if present
            meta: Dict[str, Any] = {}
            if "ground_truth_anomaly" in row and not pd.isna(row["ground_truth_anomaly"]):
                meta["ground_truth_anomaly"] = bool(row["ground_truth_anomaly"])
            elif "is_anomaly" in row and not pd.isna(row["is_anomaly"]):
                meta["ground_truth_anomaly"] = bool(row["is_anomaly"])

            obs = WeatherObservation(
                station_id=stn_id,
                station_name=stn_name,
                latitude=lat,
                longitude=lon,
                elevation=elev,
                timestamp=parsed_ts,
                temperature=temp,
                dew_point_c=dew,
                humidity=rh,
                pressure=slp,
                station_pressure_hpa=stp,
                source=ObservationSource.HISTORICAL_CSV,
                data_quality_status=QualityStatus.VALID if (temp is not None and rh is not None and slp is not None) else QualityStatus.SUSPECT,
                run_id=run_id,
                source_type=source_type,
                source_name=source_name,
                dataset_id=dataset_id,
                dataset_version=dataset_version,
                metadata=meta,
            )
            observations.append(obs)

        return observations
