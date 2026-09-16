"""Unit tests for DatasetProfiler diagnostics, statistics, and cadence metrics."""

from datetime import datetime, timezone
import pytest
from backend.app.ingestion.profiler import DatasetProfiler
from backend.app.models.observation import (
    ObservationSource,
    QualityStatus,
    WeatherObservation,
)


def create_sample_observations():
    """Create a controlled series of 5 observations with known properties."""
    obs_list = [
        WeatherObservation(
            station_id="42182099999",
            station_name="Safdarjung",
            timestamp="2024-01-01T00:00:00Z",
            latitude=28.58,
            longitude=77.20,
            elevation=214.8,
            temperature=10.0,
            dew_point_c=5.0,
            pressure=1015.0,
            humidity=71.2,
            data_quality_status=QualityStatus.VALID,
        ),
        WeatherObservation(
            station_id="42182099999",
            station_name="Safdarjung",
            timestamp="2024-01-01T00:30:00Z",
            latitude=28.58,
            longitude=77.20,
            elevation=214.8,
            temperature=11.0,
            dew_point_c=5.5,
            pressure=1015.2,
            humidity=68.5,
            data_quality_status=QualityStatus.VALID,
        ),
        WeatherObservation(
            station_id="42182099999",
            station_name="Safdarjung",
            timestamp="2024-01-01T01:00:00Z",
            latitude=28.58,
            longitude=77.20,
            elevation=214.8,
            temperature=12.0,
            dew_point_c=None,  # Missing dew point
            pressure=1014.8,
            humidity=None,      # Missing RH
            data_quality_status=QualityStatus.VALID,
        ),
        WeatherObservation(
            station_id="42182099999",
            station_name="Safdarjung",
            timestamp="2024-01-01T01:30:00Z",
            latitude=28.58,
            longitude=77.20,
            elevation=214.8,
            temperature=13.0,
            dew_point_c=6.0,
            pressure=1014.5,
            humidity=62.3,
            data_quality_status=QualityStatus.SUSPECT,
        ),
        # Duplicate timestamp
        WeatherObservation(
            station_id="42182099999",
            station_name="Safdarjung",
            timestamp="2024-01-01T01:30:00Z",
            latitude=28.58,
            longitude=77.20,
            elevation=214.8,
            temperature=13.5,
            dew_point_c=6.0,
            pressure=1014.5,
            humidity=60.8,
            data_quality_status=QualityStatus.VALID,
        ),
    ]
    return obs_list


def test_profiler_basic_metrics():
    """Verify record count, missingness, and variable summary stats."""
    obs_list = create_sample_observations()
    profile = DatasetProfiler.profile_observations(obs_list)

    assert profile.station_id == "42182099999"
    assert profile.total_records == 5
    assert profile.duplicate_timestamp_count == 1
    assert profile.temperature_stats.count_valid == 5
    assert profile.temperature_stats.missing_pct == 0.0
    assert profile.temperature_stats.min == 10.0
    assert profile.temperature_stats.max == 13.5
    assert profile.dew_point_stats.count_valid == 4
    assert profile.dew_point_stats.missing_pct == 20.0
    assert profile.relative_humidity_stats.count_valid == 4
    assert profile.relative_humidity_stats.missing_pct == 20.0


def test_profiler_cadence_calculation():
    """Verify median and mode sampling interval calculations."""
    obs_list = create_sample_observations()
    profile = DatasetProfiler.profile_observations(obs_list)

    assert profile.median_interval_minutes == 30.0
    assert profile.common_interval_minutes == 30.0
    assert profile.is_regular_cadence is True


def test_profiler_markdown_summary():
    """Verify markdown summary generation."""
    obs_list = create_sample_observations()
    profile = DatasetProfiler.profile_observations(obs_list)
    md = profile.summary_markdown()

    assert "Dataset Profile: Station 42182099999" in md
    assert "**Total Observations:** 5" in md
    assert "Temperature" in md
    assert "VALID" in md


def test_profiler_empty_dataset():
    """Verify profiling on empty dataset returns clean defaults."""
    profile = DatasetProfiler.profile_observations([])
    assert profile.total_records == 0
    assert profile.temperature_stats.missing_pct == 100.0
