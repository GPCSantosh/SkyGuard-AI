"""Unit tests for WeatherObservation Pydantic model validation, rejection, and parsing."""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from backend.app.models.observation import (
    ObservationSource,
    WeatherObservation,
)


def test_valid_observation_creation():
    """Verify standard valid observation instantiation."""
    obs = WeatherObservation(
        station_id="AWS_IND_DL_001",
        timestamp="2026-09-16T12:00:00Z",
        temperature=32.5,
        pressure=1010.5,
        humidity=65.0,
        latitude=28.5847,
        longitude=77.2060,
        elevation=216.0,
        source=ObservationSource.HISTORICAL_CSV,
        metadata={"qc_flag": 0},
    )

    assert obs.station_id == "AWS_IND_DL_001"
    assert obs.temperature == 32.5
    assert obs.pressure == 1010.5
    assert obs.humidity == 65.0
    assert obs.latitude == 28.5847
    assert obs.longitude == 77.2060
    assert obs.elevation == 216.0
    assert obs.source == "HISTORICAL_CSV"
    assert obs.timestamp.tzinfo is not None


def test_timestamp_parsing_variations():
    """Verify various ISO 8601 UTC timestamp formats parse correctly."""
    t1 = WeatherObservation(
        station_id="AWS_01",
        timestamp="2026-09-16T12:00:00Z",
        latitude=20.0,
        longitude=75.0,
    )
    assert t1.timestamp == datetime(2026, 9, 16, 12, 0, 0, tzinfo=timezone.utc)

    t2 = WeatherObservation(
        station_id="AWS_01",
        timestamp="2026-09-16T12:00:00+00:00",
        latitude=20.0,
        longitude=75.0,
    )
    assert t2.timestamp == datetime(2026, 9, 16, 12, 0, 0, tzinfo=timezone.utc)

    dt_obj = datetime(2026, 9, 16, 12, 0, 0, tzinfo=timezone.utc)
    t3 = WeatherObservation(
        station_id="AWS_01",
        timestamp=dt_obj,
        latitude=20.0,
        longitude=75.0,
    )
    assert t3.timestamp == dt_obj


def test_rejection_missing_required_fields():
    """Verify validation error when required fields are missing."""
    # Missing station_id
    with pytest.raises(ValidationError) as exc:
        WeatherObservation(
            timestamp="2026-09-16T12:00:00Z",
            latitude=28.5847,
            longitude=77.2060,
        )
    assert "station_id" in str(exc.value)

    # Missing timestamp
    with pytest.raises(ValidationError) as exc:
        WeatherObservation(
            station_id="AWS_01",
            latitude=28.5847,
            longitude=77.2060,
        )
    assert "timestamp" in str(exc.value)

    # Missing coordinates
    with pytest.raises(ValidationError) as exc:
        WeatherObservation(
            station_id="AWS_01",
            timestamp="2026-09-16T12:00:00Z",
        )
    assert "latitude" in str(exc.value)


def test_rejection_out_of_bounds_temperature():
    """Verify rejection of temperatures outside [-50, 60]°C."""
    # Too high (95°C)
    with pytest.raises(ValidationError) as exc:
        WeatherObservation(
            station_id="AWS_01",
            timestamp="2026-09-16T12:00:00Z",
            temperature=95.0,
            latitude=20.0,
            longitude=75.0,
        )
    assert "Temperature 95.0°C exceeds physical limits" in str(exc.value)

    # Too low (-65°C)
    with pytest.raises(ValidationError) as exc:
        WeatherObservation(
            station_id="AWS_01",
            timestamp="2026-09-16T12:00:00Z",
            temperature=-65.0,
            latitude=20.0,
            longitude=75.0,
        )
    assert "Temperature -65.0°C exceeds physical limits" in str(exc.value)


def test_rejection_out_of_bounds_pressure():
    """Verify rejection of pressures outside [500, 1080] hPa."""
    # Too low (450 hPa)
    with pytest.raises(ValidationError) as exc:
        WeatherObservation(
            station_id="AWS_01",
            timestamp="2026-09-16T12:00:00Z",
            pressure=450.0,
            latitude=20.0,
            longitude=75.0,
        )
    assert "Pressure 450.0 hPa exceeds physical limits" in str(exc.value)

    # Too high (1150 hPa)
    with pytest.raises(ValidationError) as exc:
        WeatherObservation(
            station_id="AWS_01",
            timestamp="2026-09-16T12:00:00Z",
            pressure=1150.0,
            latitude=20.0,
            longitude=75.0,
        )
    assert "Pressure 1150.0 hPa exceeds physical limits" in str(exc.value)


def test_rejection_out_of_bounds_humidity():
    """Verify rejection of humidity outside [0, 100]%."""
    # Negative humidity
    with pytest.raises(ValidationError) as exc:
        WeatherObservation(
            station_id="AWS_01",
            timestamp="2026-09-16T12:00:00Z",
            humidity=-5.0,
            latitude=20.0,
            longitude=75.0,
        )
    assert "Relative humidity -5.0% exceeds physical limits" in str(exc.value)

    # Humidity > 100%
    with pytest.raises(ValidationError) as exc:
        WeatherObservation(
            station_id="AWS_01",
            timestamp="2026-09-16T12:00:00Z",
            humidity=105.0,
            latitude=20.0,
            longitude=75.0,
        )
    assert "Relative humidity 105.0% exceeds physical limits" in str(exc.value)


def test_rejection_out_of_bounds_coordinates():
    """Verify invalid geodetic coordinates are rejected."""
    # Latitude > 90
    with pytest.raises(ValidationError):
        WeatherObservation(
            station_id="AWS_01",
            timestamp="2026-09-16T12:00:00Z",
            latitude=95.0,
            longitude=75.0,
        )

    # Longitude > 180
    with pytest.raises(ValidationError):
        WeatherObservation(
            station_id="AWS_01",
            timestamp="2026-09-16T12:00:00Z",
            latitude=20.0,
            longitude=195.0,
        )


def test_immutability():
    """Verify that WeatherObservation instances cannot be mutated in place."""
    obs = WeatherObservation(
        station_id="AWS_01",
        timestamp="2026-09-16T12:00:00Z",
        temperature=25.0,
        latitude=20.0,
        longitude=75.0,
    )
    with pytest.raises(ValidationError):
        obs.temperature = 30.0  # type: ignore


def test_fixtures_json_parsing():
    """Verify sample JSON fixture records load cleanly through WeatherObservation."""
    fixture_path = Path("tests/fixtures/sample_observations.json")
    assert fixture_path.is_file()

    with open(fixture_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    assert len(records) >= 3
    observations = [WeatherObservation(**r) for r in records]
    assert len(observations) == len(records)
    assert observations[0].station_id == "AWS_IND_DL_001"
    assert observations[1].station_id == "AWS_IND_MH_001"
    assert observations[2].station_id == "AWS_IND_KA_001"
