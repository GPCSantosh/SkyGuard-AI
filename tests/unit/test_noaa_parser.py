"""Unit tests for NOAA ISD parser, composite field parsing, QC mapping, and RH derivation."""

from datetime import datetime, timezone
import pytest
from backend.app.ingestion.noaa_parser import NOAAParser, NOAAParserConfig
from backend.app.models.observation import ObservationSource, QualityStatus


@pytest.fixture
def parser():
    return NOAAParser()


def test_parse_scaled_field(parser):
    """Verify NOAA composite field parsing (+0108,1 -> 10.8, QC=1)."""
    # Standard valid field
    val, qc = parser._parse_scaled_field("+0108,1", scale=10.0)
    assert val == 10.8
    assert qc == "1"

    # Negative value
    val, qc = parser._parse_scaled_field("-0052,1", scale=10.0)
    assert val == -5.2
    assert qc == "1"

    # Pressure field (scale=10)
    val, qc = parser._parse_scaled_field("10189,1", scale=10.0)
    assert val == 1018.9
    assert qc == "1"

    # Missing value markers
    val, qc = parser._parse_scaled_field("+9999,9", scale=10.0)
    assert val is None
    assert qc == "9"

    val, qc = parser._parse_scaled_field("99999,9", scale=10.0)
    assert val is None
    assert qc == "9"

    val, qc = parser._parse_scaled_field("", scale=10.0)
    assert val is None
    assert qc == "9"

    val, qc = parser._parse_scaled_field(None, scale=10.0)
    assert val is None
    assert qc == "9"


def test_parse_csv_content_valid_row(parser):
    """Verify complete parsing of a valid NOAA ISD CSV row."""
    csv_text = (
        '"STATION","DATE","SOURCE","LATITUDE","LONGITUDE","ELEVATION","NAME","REPORT_TYPE","CALL_SIGN","QUALITY_CONTROL","WND","CIG","VIS","TMP","DEW","SLP"\n'
        '"42182099999","2024-01-01T00:00:00","4","28.584511","77.205783","214.88","SAFDARJUNG, IN","FM-12","99999","V020","200,1,N,0021,1","99999,9,9,N","000500,1,9,9","+0108,1","+0100,1","10189,1"\n'
    )
    observations = parser.parse_csv_content(csv_text)
    assert len(observations) == 1
    obs = observations[0]

    assert obs.station_id == "42182099999"
    assert obs.station_name == "SAFDARJUNG, IN"
    assert obs.timestamp == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert obs.latitude == pytest.approx(28.584511)
    assert obs.longitude == pytest.approx(77.205783)
    assert obs.elevation == 214.88
    assert obs.temperature == 10.8
    assert obs.dew_point_c == 10.0
    assert obs.pressure == 1018.9
    assert obs.humidity is not None
    assert pytest.approx(obs.humidity, abs=0.5) == 94.8
    assert obs.relative_humidity_source == "derived_from_temperature_and_dew_point"
    assert obs.source == ObservationSource.NOAA_ISD
    assert obs.report_type == "FM-12"
    assert obs.data_quality_status == QualityStatus.VALID
    assert obs.raw_quality_flags["TMP_QC"] == "1"
    assert obs.raw_quality_flags["DEW_QC"] == "1"
    assert obs.raw_quality_flags["SLP_QC"] == "1"
    assert obs.is_synthetic is False


def test_parse_missing_fields(parser):
    """Verify that NOAA missing fields (+9999,9) produce None without throwing errors."""
    csv_text = (
        '"STATION","DATE","SOURCE","LATITUDE","LONGITUDE","ELEVATION","NAME","REPORT_TYPE","QUALITY_CONTROL","TMP","DEW","SLP"\n'
        '"42182099999","2024-01-01T06:00:00","4","28.58","77.20","214.8","SAFDARJUNG, IN","FM-12","V020","+9999,9","+9999,9","99999,9"\n'
    )
    observations = parser.parse_csv_content(csv_text)
    assert len(observations) == 1
    obs = observations[0]

    assert obs.temperature is None
    assert obs.dew_point_c is None
    assert obs.pressure is None
    assert obs.humidity is None
    assert obs.relative_humidity_source is None
    assert obs.data_quality_status == QualityStatus.MISSING


def test_parse_qc_error_and_suspect(parser):
    """Verify QC flag interpretation when data is suspect (QC=2) or erroneous (QC=3)."""
    # Suspect temperature (QC=2)
    csv_suspect = (
        '"STATION","DATE","LATITUDE","LONGITUDE","TMP","DEW","SLP"\n'
        '"42182099999","2024-01-01T06:00:00","28.58","77.20","+0250,2","+0150,1","10150,1"\n'
    )
    obs_suspect = parser.parse_csv_content(csv_suspect)[0]
    assert obs_suspect.temperature == 25.0
    assert obs_suspect.raw_quality_flags["TMP_QC"] == "2"
    assert obs_suspect.data_quality_status == QualityStatus.SUSPECT

    # Erroneous dew point (QC=3)
    csv_error = (
        '"STATION","DATE","LATITUDE","LONGITUDE","TMP","DEW","SLP"\n'
        '"42182099999","2024-01-01T06:00:00","28.58","77.20","+0250,1","+0150,3","10150,1"\n'
    )
    obs_error = parser.parse_csv_content(csv_error)[0]
    assert obs_error.data_quality_status == QualityStatus.ERROR


def test_station_pressure_parsing(parser):
    """Verify station pressure extraction from MA1 field."""
    csv_ma1 = (
        '"STATION","DATE","LATITUDE","LONGITUDE","TMP","DEW","SLP","MA1"\n'
        '"42182099999","2024-01-01T00:00:00","28.58","77.20","+0108,1","+0100,1","10189,1","09890,1,10189,1"\n'
    )
    obs = parser.parse_csv_content(csv_ma1)[0]
    assert obs.pressure == 1018.9  # SLP
    assert obs.station_pressure_hpa == 989.0  # Station pressure from MA1
    assert obs.raw_quality_flags["STP_QC"] == "1"


def test_report_type_filtering():
    """Verify parser can filter for specific report types."""
    csv_mixed = (
        '"STATION","DATE","LATITUDE","LONGITUDE","TMP","DEW","SLP","REPORT_TYPE"\n'
        '"42182099999","2024-01-01T00:00:00","28.58","77.20","+0108,1","+0100,1","10189,1","FM-12"\n'
        '"42182099999","2024-01-01T00:30:00","28.58","77.20","+0109,1","+0101,1","10190,1","FM-15"\n'
        '"42182099999","2024-01-01T01:00:00","28.58","77.20","+0110,1","+0102,1","10191,1","METAR"\n'
    )
    config = NOAAParserConfig(filter_report_types=["FM-15", "METAR"])
    filtered_parser = NOAAParser(config=config)
    observations = filtered_parser.parse_csv_content(csv_mixed)

    assert len(observations) == 2
    assert {obs.report_type for obs in observations} == {"FM-15", "METAR"}
