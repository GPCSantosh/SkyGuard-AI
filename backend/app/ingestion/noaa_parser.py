"""NOAA NCEI Integrated Surface Database (ISD) CSV Parser and Transformer for SkyGuard AI.

Parses raw NOAA Global Hourly / ISD CSV archives into normalized canonical
WeatherObservation records while preserving all raw QC codes and provenance metadata.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from backend.app.core.meteorology import calculate_relative_humidity
from backend.app.models.observation import (
    ObservationSource,
    QualityStatus,
    WeatherObservation,
)

# NOAA ISD QC Flag mapping to SkyGuard QualityStatus
NOAA_QC_MAP: Dict[str, QualityStatus] = {
    "0": QualityStatus.VALID,
    "1": QualityStatus.VALID,     # Passed all quality control checks
    "2": QualityStatus.SUSPECT,   # Suspect
    "3": QualityStatus.ERROR,     # Erroneous
    "4": QualityStatus.VALID,     # Passed gross limits check
    "5": QualityStatus.VALID,     # Passed all QC and time series check
    "6": QualityStatus.SUSPECT,   # Suspect on time series
    "7": QualityStatus.ERROR,     # Erroneous on time series
    "9": QualityStatus.UNKNOWN,   # Passed gross check / unverified or missing
}


class NOAAParserConfig:
    """Configuration options for NOAA ISD ingestion parsing."""

    def __init__(
        self,
        filter_report_types: Optional[List[str]] = None,
        derive_rh: bool = True,
        clamp_rh: bool = True,
        strict_physical_bounds: bool = False,
        default_station_id: Optional[str] = None,
        default_station_name: Optional[str] = None,
    ) -> None:
        self.filter_report_types = filter_report_types
        self.derive_rh = derive_rh
        self.clamp_rh = clamp_rh
        self.strict_physical_bounds = strict_physical_bounds
        self.default_station_id = default_station_id
        self.default_station_name = default_station_name


class NOAAParser:
    """Parser and transformer for NOAA NCEI Global Hourly / ISD CSV data."""

    def __init__(self, config: Optional[NOAAParserConfig] = None) -> None:
        self.config = config or NOAAParserConfig()

    @staticmethod
    def _parse_scaled_field(
        raw_val: Any,
        scale: float = 10.0,
        missing_markers: Tuple[str, ...] = ("9999", "+9999", "-9999", "99999", "+99999", "999.9", "9999.9"),
    ) -> Tuple[Optional[float], str]:
        """Parse a NOAA composite field such as '+0108,1' into (value, qc_flag)."""
        if raw_val is None or pd.isna(raw_val):
            return None, "9"

        str_val = str(raw_val).strip().strip('"')
        if not str_val:
            return None, "9"

        if "," in str_val:
            parts = str_val.split(",")
            val_part = parts[0].strip()
            qc_part = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "9"
        else:
            val_part = str_val
            qc_part = "9"

        if val_part in missing_markers or not val_part:
            return None, qc_part

        try:
            numeric_val = float(val_part)
            # Check for standard NOAA missing sentinels (9999, +9999 for temp/dew, 99999 for SLP)
            if numeric_val in (9999.0, -9999.0, 99999.0, 999.9, 9999.9):
                return None, qc_part
            scaled = numeric_val / scale
            return round(scaled, 2), qc_part
        except (ValueError, TypeError):
            return None, "3"  # Mark parsing error

    @staticmethod
    def _parse_station_pressure(row: pd.Series) -> Tuple[Optional[float], Optional[str]]:
        """Extract station pressure from MA1 or STP fields if present."""
        # 1. Check MA1 field: format 'stn_pres*10,qc,slp*10,qc'
        if "MA1" in row and pd.notna(row["MA1"]):
            val_str = str(row["MA1"]).strip().strip('"')
            parts = val_str.split(",")
            if len(parts) >= 2 and parts[0] not in ("99999", "+99999", "9999.9", ""):
                try:
                    p_stn = float(parts[0]) / 10.0
                    qc = parts[1] if len(parts) > 1 else "9"
                    if 300.0 <= p_stn <= 1080.0:
                        return round(p_stn, 2), qc
                except (ValueError, TypeError):
                    pass

        # 2. Check direct STP field if available
        if "STP" in row and pd.notna(row["STP"]):
            val, qc = NOAAParser._parse_scaled_field(row["STP"], scale=10.0)
            if val is not None and 300.0 <= val <= 1080.0:
                return val, qc

        return None, None

    def parse_file(self, file_path: Union[str, Path]) -> List[WeatherObservation]:
        """Read and parse a NOAA ISD CSV file into WeatherObservation objects."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"NOAA data file not found: {path}")

        # Check for empty file
        if path.stat().st_size == 0:
            return []

        # Read CSV, treating all columns as strings initially for robust composite parsing
        df = pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)
        return self.parse_dataframe(df, source_name=f"NOAA_ISD_{path.name}")

    def parse_csv_content(
        self,
        csv_content: Union[str, bytes],
        source_name: str = "NOAA_ISD",
    ) -> List[WeatherObservation]:
        """Parse raw CSV text or bytes into WeatherObservation objects."""
        if isinstance(csv_content, bytes):
            buffer = io.BytesIO(csv_content)
        else:
            buffer = io.StringIO(csv_content)

        if len(csv_content) == 0:
            return []

        df = pd.read_csv(buffer, dtype=str, keep_default_na=False, low_memory=False)
        return self.parse_dataframe(df, source_name=source_name)

    def parse_dataframe(
        self,
        df: pd.DataFrame,
        source_name: str = "NOAA_ISD",
    ) -> List[WeatherObservation]:
        """Transform a pandas DataFrame of NOAA records into WeatherObservation objects."""
        if df.empty:
            return []

        # Validate mandatory NOAA columns
        required_cols = ["DATE"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required NOAA ISD columns: {missing}")

        # Filter by report type if configured
        if self.config.filter_report_types and "REPORT_TYPE" in df.columns:
            df = df[df["REPORT_TYPE"].isin(self.config.filter_report_types)]

        observations: List[WeatherObservation] = []

        for _, row in df.iterrows():
            obs = self._parse_single_row(row, source_name=source_name)
            if obs is not None:
                observations.append(obs)

        # Estimate and assign native resolution across the series
        if len(observations) >= 2:
            self._assign_native_resolution(observations)

        return observations

    def _parse_single_row(
        self,
        row: pd.Series,
        source_name: str,
    ) -> Optional[WeatherObservation]:
        """Parse one row of NOAA ISD DataFrame into a WeatherObservation."""
        # 1. Parse Timestamp
        raw_date = row.get("DATE", "")
        if not raw_date or str(raw_date).strip() == "":
            return None

        clean_date_str = str(raw_date).strip().strip('"')
        try:
            # Handle ISO format variants
            if "T" in clean_date_str:
                timestamp_str = clean_date_str
            else:
                timestamp_str = clean_date_str.replace(" ", "T")
        except Exception:
            return None

        # 2. Station Identification & Metadata
        raw_station = str(row.get("STATION", "")).strip().strip('"')
        station_id = raw_station or self.config.default_station_id or "UNKNOWN_STATION"
        station_name = (
            str(row.get("NAME", "")).strip().strip('"')
            or self.config.default_station_name
        )
        report_type = str(row.get("REPORT_TYPE", "")).strip().strip('"') or None

        # 3. Geospatial Coordinates
        try:
            latitude = float(str(row.get("LATITUDE", "0")).strip().strip('"'))
            longitude = float(str(row.get("LONGITUDE", "0")).strip().strip('"'))
        except (ValueError, TypeError):
            latitude, longitude = 0.0, 0.0

        try:
            elev_str = str(row.get("ELEVATION", "")).strip().strip('"')
            elevation = float(elev_str) if elev_str and elev_str != "-999.9" else None
        except (ValueError, TypeError):
            elevation = None

        # 4. Parse Meteorological Variables
        temp_c, qc_temp = self._parse_scaled_field(row.get("TMP"))
        dew_c, qc_dew = self._parse_scaled_field(row.get("DEW"))
        slp_hpa, qc_slp = self._parse_scaled_field(row.get("SLP"))
        stn_pres_hpa, qc_stn = self._parse_station_pressure(row)

        # 5. Derive Relative Humidity
        rh_pct: Optional[float] = None
        rh_source: Optional[str] = None
        if self.config.derive_rh and temp_c is not None and dew_c is not None:
            rh_pct = calculate_relative_humidity(
                temperature_c=temp_c,
                dew_point_c=dew_c,
                clamp=self.config.clamp_rh,
            )
            if rh_pct is not None:
                rh_source = "derived_from_temperature_and_dew_point"

        # 6. Interpret Raw Quality Flags
        raw_qc_flags: Dict[str, Any] = {
            "TMP_QC": qc_temp,
            "DEW_QC": qc_dew,
            "SLP_QC": qc_slp,
        }
        if qc_stn:
            raw_qc_flags["STP_QC"] = qc_stn
        if "QUALITY_CONTROL" in row and pd.notna(row["QUALITY_CONTROL"]):
            raw_qc_flags["RECORD_QC"] = str(row["QUALITY_CONTROL"]).strip().strip('"')

        # Determine Overall Quality Status
        qc_statuses = [
            NOAA_QC_MAP.get(qc_temp, QualityStatus.UNKNOWN) if temp_c is not None else None,
            NOAA_QC_MAP.get(qc_dew, QualityStatus.UNKNOWN) if dew_c is not None else None,
            NOAA_QC_MAP.get(qc_slp, QualityStatus.UNKNOWN) if slp_hpa is not None else None,
        ]
        active_statuses = [s for s in qc_statuses if s is not None]

        if not active_statuses:
            overall_quality = QualityStatus.MISSING
        elif any(s == QualityStatus.ERROR for s in active_statuses):
            overall_quality = QualityStatus.ERROR
        elif any(s == QualityStatus.SUSPECT for s in active_statuses):
            overall_quality = QualityStatus.SUSPECT
        elif all(s == QualityStatus.VALID for s in active_statuses):
            overall_quality = QualityStatus.VALID
        else:
            overall_quality = QualityStatus.UNKNOWN

        # 7. Construct Immutable WeatherObservation Instance
        try:
            obs = WeatherObservation(
                station_id=station_id,
                station_name=station_name if station_name else None,
                timestamp=timestamp_str,
                latitude=latitude,
                longitude=longitude,
                elevation=elevation,
                temperature=temp_c,
                dew_point_c=dew_c,
                pressure=slp_hpa,
                station_pressure_hpa=stn_pres_hpa,
                humidity=rh_pct,
                relative_humidity_source=rh_source,
                source=ObservationSource.NOAA_ISD,
                report_type=report_type,
                raw_quality_flags=raw_qc_flags,
                data_quality_status=overall_quality,
                is_synthetic=False,
                metadata={
                    "parser": "SkyGuard_NOAAParser_v1.0",
                    "wnd": str(row.get("WND", "")).strip().strip('"') if "WND" in row else None,
                },
            )
            return obs
        except Exception:
            # If strict physical bounds failed or row is corrupt, return None or re-raise
            if self.config.strict_physical_bounds:
                raise
            return None

    @staticmethod
    def _assign_native_resolution(observations: List[WeatherObservation]) -> None:
        """Calculate and assign median sampling resolution (minutes) across sorted observations."""
        if len(observations) < 2:
            return

        # Extract timestamps and compute diffs
        timestamps = [obs.timestamp for obs in observations]
        diffs_sec = [
            (timestamps[i] - timestamps[i - 1]).total_seconds()
            for i in range(1, len(timestamps))
        ]
        # Filter negative or zero diffs (duplicates/out-of-order)
        positive_diffs = [d for d in diffs_sec if d > 0]
        if not positive_diffs:
            return

        median_min = float(np.median(positive_diffs) / 60.0)
        # Note: WeatherObservation is frozen; we can store this at dataset profiling level
        # or recreate instances if needed. We populate metadata during profiling.
