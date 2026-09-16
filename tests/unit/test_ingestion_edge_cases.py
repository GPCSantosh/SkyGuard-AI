"""Comprehensive edge case and fault-tolerance unit tests for NOAA ingestion pipeline."""

from datetime import datetime, timezone
import pytest
from backend.app.ingestion.noaa_parser import NOAAParser
from backend.app.ingestion.profiler import DatasetProfiler
from backend.app.models.observation import QualityStatus


@pytest.fixture
def parser():
    return NOAAParser()


def test_edge_case_temperature_null(parser):
    """Edge Case 1: Temperature is missing (+9999,9), Dew Point and SLP are present."""
    csv_text = (
        '"STATION","DATE","LATITUDE","LONGITUDE","TMP","DEW","SLP"\n'
        '"42182099999","2024-01-01T00:00:00","28.58","77.20","+9999,9","+0100,1","10189,1"\n'
    )
    obs = parser.parse_csv_content(csv_text)[0]
    assert obs.temperature is None
    assert obs.dew_point_c == 10.0
    assert obs.pressure == 1018.9
    assert obs.humidity is None  # RH cannot be derived without temperature


def test_edge_case_dew_point_null(parser):
    """Edge Case 2: Dew Point is missing (+9999,9), Temperature and SLP are present."""
    csv_text = (
        '"STATION","DATE","LATITUDE","LONGITUDE","TMP","DEW","SLP"\n'
        '"42182099999","2024-01-01T00:00:00","28.58","77.20","+0250,1","+9999,9","10189,1"\n'
    )
    obs = parser.parse_csv_content(csv_text)[0]
    assert obs.temperature == 25.0
    assert obs.dew_point_c is None
    assert obs.humidity is None  # RH cannot be derived without dew point


def test_edge_case_temp_equals_dew_point(parser):
    """Edge Case 3: Temperature == Dew Point -> 100.0% Relative Humidity."""
    csv_text = (
        '"STATION","DATE","LATITUDE","LONGITUDE","TMP","DEW","SLP"\n'
        '"42182099999","2024-01-01T00:00:00","28.58","77.20","+0150,1","+0150,1","10189,1"\n'
    )
    obs = parser.parse_csv_content(csv_text)[0]
    assert obs.temperature == 15.0
    assert obs.dew_point_c == 15.0
    assert obs.humidity == 100.0


def test_edge_case_dew_point_greater_than_temp(parser):
    """Edge Case 4 & 5: Dew Point > Temperature (Sensor Inversion / Supersaturation)."""
    csv_text = (
        '"STATION","DATE","LATITUDE","LONGITUDE","TMP","DEW","SLP"\n'
        '"42182099999","2024-01-01T00:00:00","28.58","77.20","+0200,1","+0205,1","10189,1"\n'
    )
    obs = parser.parse_csv_content(csv_text)[0]
    assert obs.temperature == 20.0
    assert obs.dew_point_c == 20.5
    # Clamped to 100% per scientific guidelines
    assert obs.humidity == 100.0


def test_edge_case_pressure_unavailable(parser):
    """Edge Case 7: Pressure is completely unavailable (99999,9)."""
    csv_text = (
        '"STATION","DATE","LATITUDE","LONGITUDE","TMP","DEW","SLP"\n'
        '"42182099999","2024-01-01T00:00:00","28.58","77.20","+0200,1","+0150,1","99999,9"\n'
    )
    obs = parser.parse_csv_content(csv_text)[0]
    assert obs.pressure is None
    assert obs.station_pressure_hpa is None
    assert obs.temperature == 20.0
    assert obs.dew_point_c == 15.0


def test_edge_case_duplicate_timestamps_and_out_of_order(parser):
    """Edge Cases 8 & 17: Duplicate timestamps and non-chronological order."""
    csv_text = (
        '"STATION","DATE","LATITUDE","LONGITUDE","TMP","DEW","SLP"\n'
        '"42182099999","2024-01-01T02:00:00","28.58","77.20","+0150,1","+0100,1","10180,1"\n'
        '"42182099999","2024-01-01T01:00:00","28.58","77.20","+0140,1","+0100,1","10182,1"\n'
        '"42182099999","2024-01-01T01:00:00","28.58","77.20","+0142,1","+0100,1","10182,1"\n'
    )
    observations = parser.parse_csv_content(csv_text)
    assert len(observations) == 3

    profile = DatasetProfiler.profile_observations(observations)
    assert profile.duplicate_timestamp_count == 1
    assert profile.out_of_order_count == 1


def test_edge_case_multiple_report_types_same_timestamp(parser):
    """Edge Case 9: Coincident timestamps with differing report types (FM-12 and METAR)."""
    csv_text = (
        '"STATION","DATE","LATITUDE","LONGITUDE","TMP","DEW","SLP","REPORT_TYPE"\n'
        '"42182099999","2024-01-01T00:00:00","28.58","77.20","+0108,1","+0100,1","10189,1","FM-12"\n'
        '"42182099999","2024-01-01T00:00:00","28.58","77.20","+0109,1","+0100,1","10189,1","METAR"\n'
    )
    observations = parser.parse_csv_content(csv_text)
    assert len(observations) == 2
    assert observations[0].report_type == "FM-12"
    assert observations[1].report_type == "METAR"


def test_edge_case_corrupted_row(parser):
    """Edge Case 12: Corrupted row with malformed fields is safely handled."""
    csv_text = (
        '"STATION","DATE","LATITUDE","LONGITUDE","TMP","DEW","SLP"\n'
        '"42182099999","2024-01-01T00:00:00","28.58","77.20","+0108,1","+0100,1","10189,1"\n'
        '"42182099999","CORRUPTED_DATE","BAD_LAT","BAD_LON","BAD_TMP","BAD_DEW","BAD_SLP"\n'
        '"42182099999","2024-01-01T01:00:00","28.58","77.20","+0115,1","+0100,1","10185,1"\n'
    )
    observations = parser.parse_csv_content(csv_text)
    # The corrupted date is rejected, valid rows are preserved
    assert len(observations) == 2
    assert observations[0].temperature == 10.8
    assert observations[1].temperature == 11.5


def test_edge_case_empty_and_headers_only(parser):
    """Edge Cases 13 & 14: Empty file and header-only CSV."""
    assert parser.parse_csv_content("") == []

    headers_only = '"STATION","DATE","LATITUDE","LONGITUDE","TMP","DEW","SLP"\n'
    assert parser.parse_csv_content(headers_only) == []


def test_edge_case_extra_unknown_columns(parser):
    """Edge Case 19: Extra unexpected columns in CSV are tolerated without error."""
    csv_text = (
        '"STATION","DATE","LATITUDE","LONGITUDE","TMP","DEW","SLP","EXTRA_COL_A","EXTRA_COL_B"\n'
        '"42182099999","2024-01-01T00:00:00","28.58","77.20","+0108,1","+0100,1","10189,1","FOO","BAR"\n'
    )
    observations = parser.parse_csv_content(csv_text)
    assert len(observations) == 1
    assert observations[0].temperature == 10.8


def test_edge_case_missing_required_columns(parser):
    """Edge Case 18: Missing mandatory DATE column raises ValueError."""
    csv_text = (
        '"STATION","LATITUDE","LONGITUDE","TMP","DEW","SLP"\n'
        '"42182099999","28.58","77.20","+0108,1","+0100,1","10189,1"\n'
    )
    with pytest.raises(ValueError) as exc:
        parser.parse_csv_content(csv_text)
    assert "Missing required NOAA ISD columns" in str(exc.value)
