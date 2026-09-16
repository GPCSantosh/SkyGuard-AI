"""Dataset Profiler for meteorological telemetry archives in SkyGuard AI.

Analyzes collections of WeatherObservation records to generate comprehensive
data quality profiles, cadence diagnostics, and summary statistics.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from backend.app.ingestion.noaa_parser import NOAAParser
from backend.app.models.observation import WeatherObservation


class VariableStats(BaseModel):
    """Statistical summary for a single meteorological variable."""
    model_config = ConfigDict(frozen=True)

    count_valid: int
    missing_pct: float
    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    median: Optional[float] = None
    q25: Optional[float] = None
    q75: Optional[float] = None


class DatasetProfile(BaseModel):
    """Comprehensive data quality and profiling metrics for a weather dataset."""
    model_config = ConfigDict(frozen=True)

    station_id: str
    station_name: Optional[str] = None
    total_records: int
    
    # Time Range Diagnostics
    start_time_utc: Optional[str] = None
    end_time_utc: Optional[str] = None
    total_duration_days: float = 0.0

    # Geospatial Coordinates
    latitude: float
    longitude: float
    elevation_m: Optional[float] = None

    # Temporal Diagnostics
    duplicate_timestamp_count: int = 0
    out_of_order_count: int = 0
    median_interval_minutes: Optional[float] = None
    min_interval_minutes: Optional[float] = None
    max_interval_minutes: Optional[float] = None
    common_interval_minutes: Optional[float] = None
    is_regular_cadence: bool = False

    # Provenance & Quality Breakdowns
    report_type_counts: Dict[str, int] = Field(default_factory=dict)
    quality_status_counts: Dict[str, int] = Field(default_factory=dict)

    # Meteorological Variable Summaries
    temperature_stats: VariableStats
    dew_point_stats: VariableStats
    sea_level_pressure_stats: VariableStats
    station_pressure_stats: VariableStats
    relative_humidity_stats: VariableStats

    def summary_markdown(self) -> str:
        """Format the profile as a clean Markdown summary table."""
        lines = [
            f"# Dataset Profile: Station {self.station_id} ({self.station_name or 'N/A'})",
            f"- **Total Observations:** {self.total_records:,}",
            f"- **Time Coverage (UTC):** {self.start_time_utc or 'N/A'} to {self.end_time_utc or 'N/A'} ({self.total_duration_days:.1f} days)",
            f"- **Location:** Lat {self.latitude:.4f}°, Lon {self.longitude:.4f}°, Elev {self.elevation_m}m",
            f"- **Cadence (minutes):** Median={self.median_interval_minutes}, Min={self.min_interval_minutes}, Max={self.max_interval_minutes}, Mode={self.common_interval_minutes} (Regular: {self.is_regular_cadence})",
            f"- **Timestamp Issues:** Duplicates={self.duplicate_timestamp_count}, Out-of-order={self.out_of_order_count}",
            "",
            "## Meteorological Variables Summary",
            "| Parameter | Valid Count | Missing % | Min | Mean | Max | Median | Std |",
            "|---|---|---|---|---|---|---|---|",
        ]

        def _row(name: str, s: VariableStats) -> str:
            min_str = f"{s.min:.1f}" if s.min is not None else "N/A"
            mean_str = f"{s.mean:.1f}" if s.mean is not None else "N/A"
            max_str = f"{s.max:.1f}" if s.max is not None else "N/A"
            med_str = f"{s.median:.1f}" if s.median is not None else "N/A"
            std_str = f"{s.std:.1f}" if s.std is not None else "N/A"
            return f"| {name} | {s.count_valid:,} | {s.missing_pct:.1f}% | {min_str} | {mean_str} | {max_str} | {med_str} | {std_str} |"

        lines.append(_row("Temperature (°C)", self.temperature_stats))
        lines.append(_row("Dew Point (°C)", self.dew_point_stats))
        lines.append(_row("SLP Pressure (hPa)", self.sea_level_pressure_stats))
        lines.append(_row("Station Pressure (hPa)", self.station_pressure_stats))
        lines.append(_row("Relative Humidity (%)", self.relative_humidity_stats))

        lines.extend([
            "",
            "## Quality Control Distribution",
            "| Quality Status | Count | Percentage |",
            "|---|---|---|",
        ])
        for status, count in self.quality_status_counts.items():
            pct = (count / self.total_records * 100.0) if self.total_records > 0 else 0.0
            lines.append(f"| {status} | {count:,} | {pct:.1f}% |")

        return "\n".join(lines)


class DatasetProfiler:
    """Calculates dataset quality profiles from WeatherObservation collections."""

    @staticmethod
    def _compute_variable_stats(values: List[Optional[float]], total_records: int) -> VariableStats:
        """Compute summary statistics for a float parameter series."""
        valid_vals = [v for v in values if v is not None and not np.isnan(v)]
        count_valid = len(valid_vals)
        missing_pct = ((total_records - count_valid) / total_records * 100.0) if total_records > 0 else 100.0

        if not valid_vals:
            return VariableStats(count_valid=0, missing_pct=missing_pct)

        arr = np.array(valid_vals, dtype=float)
        return VariableStats(
            count_valid=count_valid,
            missing_pct=round(missing_pct, 2),
            min=round(float(np.min(arr)), 2),
            max=round(float(np.max(arr)), 2),
            mean=round(float(np.mean(arr)), 2),
            std=round(float(np.std(arr)), 2),
            median=round(float(np.median(arr)), 2),
            q25=round(float(np.percentile(arr, 25)), 2),
            q75=round(float(np.percentile(arr, 75)), 2),
        )

    @classmethod
    def profile_observations(
        cls,
        observations: List[WeatherObservation],
        station_id: Optional[str] = None,
        station_name: Optional[str] = None,
    ) -> DatasetProfile:
        """Generate a complete DatasetProfile from a list of WeatherObservation objects."""
        total = len(observations)
        if total == 0:
            return DatasetProfile(
                station_id=station_id or "EMPTY",
                station_name=station_name,
                total_records=0,
                latitude=0.0,
                longitude=0.0,
                temperature_stats=VariableStats(count_valid=0, missing_pct=100.0),
                dew_point_stats=VariableStats(count_valid=0, missing_pct=100.0),
                sea_level_pressure_stats=VariableStats(count_valid=0, missing_pct=100.0),
                station_pressure_stats=VariableStats(count_valid=0, missing_pct=100.0),
                relative_humidity_stats=VariableStats(count_valid=0, missing_pct=100.0),
            )

        # Basic metadata
        st_id = station_id or observations[0].station_id
        st_name = station_name or observations[0].station_name
        lat = observations[0].latitude
        lon = observations[0].longitude
        elev = observations[0].elevation

        # Timestamps analysis
        timestamps = [obs.timestamp for obs in observations]
        start_time = min(timestamps).isoformat()
        end_time = max(timestamps).isoformat()
        duration_days = (max(timestamps) - min(timestamps)).total_seconds() / 86400.0

        # Duplicate and out-of-order detection
        seen_timestamps = set()
        duplicate_count = 0
        out_of_order_count = 0
        last_dt = None

        for dt in timestamps:
            if dt in seen_timestamps:
                duplicate_count += 1
            seen_timestamps.add(dt)

            if last_dt is not None and dt < last_dt:
                out_of_order_count += 1
            last_dt = dt

        # Cadence intervals (computed on sorted distinct timestamps)
        sorted_unique_dts = sorted(list(seen_timestamps))
        intervals_min: List[float] = []
        for i in range(1, len(sorted_unique_dts)):
            diff_min = (sorted_unique_dts[i] - sorted_unique_dts[i - 1]).total_seconds() / 60.0
            if diff_min > 0:
                intervals_min.append(diff_min)

        if intervals_min:
            med_interval = round(float(np.median(intervals_min)), 1)
            min_interval = round(float(np.min(intervals_min)), 1)
            max_interval = round(float(np.max(intervals_min)), 1)
            mode_counts = Counter(intervals_min).most_common(1)
            mode_interval = round(float(mode_counts[0][0]), 1) if mode_counts else med_interval
            # Regular if 90%+ of intervals are within 1 minute of mode
            is_regular = (
                sum(1 for x in intervals_min if abs(x - mode_interval) <= 1.0) / len(intervals_min)
            ) >= 0.90
        else:
            med_interval, min_interval, max_interval, mode_interval = None, None, None, None
            is_regular = False

        # Report Types & QC Distribution
        report_types = Counter(obs.report_type or "UNKNOWN" for obs in observations)
        qc_statuses = Counter(
            str(obs.data_quality_status.value if hasattr(obs.data_quality_status, "value") else obs.data_quality_status)
            for obs in observations
        )

        # Variable Summaries
        temp_stats = cls._compute_variable_stats([obs.temperature for obs in observations], total)
        dew_stats = cls._compute_variable_stats([obs.dew_point_c for obs in observations], total)
        slp_stats = cls._compute_variable_stats([obs.pressure for obs in observations], total)
        stn_pres_stats = cls._compute_variable_stats(
            [obs.station_pressure_hpa for obs in observations], total
        )
        rh_stats = cls._compute_variable_stats([obs.humidity for obs in observations], total)

        return DatasetProfile(
            station_id=st_id,
            station_name=st_name,
            total_records=total,
            start_time_utc=start_time,
            end_time_utc=end_time,
            total_duration_days=round(duration_days, 2),
            latitude=lat,
            longitude=lon,
            elevation_m=elev,
            duplicate_timestamp_count=duplicate_count,
            out_of_order_count=out_of_order_count,
            median_interval_minutes=med_interval,
            min_interval_minutes=min_interval,
            max_interval_minutes=max_interval,
            common_interval_minutes=mode_interval,
            is_regular_cadence=is_regular,
            report_type_counts=dict(report_types),
            quality_status_counts=dict(qc_statuses),
            temperature_stats=temp_stats,
            dew_point_stats=dew_stats,
            sea_level_pressure_stats=slp_stats,
            station_pressure_stats=stn_pres_stats,
            relative_humidity_stats=rh_stats,
        )

    @classmethod
    def profile_file(cls, file_path: Union[str, Path]) -> DatasetProfile:
        """Parse and profile a NOAA ISD CSV file directly."""
        parser = NOAAParser()
        observations = parser.parse_file(file_path)
        return cls.profile_observations(observations)
