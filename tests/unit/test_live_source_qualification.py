"""Unit tests for Phase 11A Live AWS / Weather API Source Qualification."""

import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from pydantic import ValidationError

from backend.app.connectors.live_qualification import (
    LiveSourceHealthStatus,
    LiveSourceQualificationGate,
    OpenMeteoQualificationAdapter,
    PressureSemantics,
)
from backend.app.core.config import AppSettings, LiveSourceSettings, get_settings
from backend.app.models.observation import (
    ObservationSource,
    QualityStatus,
    WeatherObservation,
)


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "data" / "external" / "live_api"


def load_fixture(filename: str):
    """Load JSON test fixture safely."""
    path = FIXTURES_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_01_valid_observation_normalization():
    """Verify 01: Valid Open-Meteo payload normalizes into canonical WeatherObservation."""
    raw = load_fixture("01_valid_observation.json")
    adapter = OpenMeteoQualificationAdapter()
    
    retrieval_time = datetime(2026, 9, 17, 5, 0, 5, tzinfo=timezone.utc)
    observations = adapter.normalize(
        raw_payload=raw,
        station_id="AWS_DELHI_001",
        station_name="New Delhi Safdarjung AWS",
        retrieval_timestamp=retrieval_time,
        pressure_semantics=PressureSemantics.MEAN_SEA_LEVEL_PRESSURE
    )

    assert len(observations) == 1
    obs = observations[0]
    assert obs.station_id == "AWS_DELHI_001"
    assert obs.station_name == "New Delhi Safdarjung AWS"
    assert obs.latitude == 28.585
    assert obs.longitude == 77.206
    assert obs.elevation == 216.0
    assert obs.timestamp == datetime(2026, 9, 17, 5, 0, 0, tzinfo=timezone.utc)
    assert obs.ingestion_timestamp == retrieval_time
    assert obs.temperature == 28.4
    assert obs.humidity == 62.0
    assert obs.pressure == 1012.3  # MSLP
    assert obs.station_pressure_hpa == 988.5
    assert obs.dew_point_c == 20.5
    assert obs.source == ObservationSource.OPEN_METEO
    assert obs.data_quality_status == QualityStatus.VALID

    # Verify non-core parameters are preserved in metadata and NOT in core feature set
    assert "source_supplementary" in obs.metadata
    assert obs.metadata["source_supplementary"]["wind_speed_10m"] == 12.4
    assert obs.metadata["source_supplementary"]["precipitation"] == 0.0

    # Evaluate Quality Gate
    gate_result = LiveSourceQualificationGate.evaluate(
        obs,
        pressure_semantics=PressureSemantics.MEAN_SEA_LEVEL_PRESSURE,
        expected_station_id="AWS_DELHI_001"
    )
    assert gate_result.is_qualified is True
    assert len(gate_result.reasons) == 0


def test_02_missing_temperature_handling():
    """Verify 02: Missing temperature is preserved as None and flagged SUSPECT."""
    raw = load_fixture("02_missing_temperature.json")
    adapter = OpenMeteoQualificationAdapter()
    obs = adapter.normalize(raw, station_id="AWS_DELHI_001")[0]

    assert obs.temperature is None
    assert obs.humidity == 62.0
    assert obs.pressure == 1012.3
    assert obs.data_quality_status == QualityStatus.SUSPECT


def test_03_missing_rh_handling():
    """Verify 03: Missing RH is preserved as None and flagged SUSPECT."""
    raw = load_fixture("03_missing_rh.json")
    adapter = OpenMeteoQualificationAdapter()
    obs = adapter.normalize(raw, station_id="AWS_DELHI_001")[0]

    assert obs.temperature == 28.4
    assert obs.humidity is None
    assert obs.pressure == 1012.3
    assert obs.data_quality_status == QualityStatus.SUSPECT


def test_04_missing_pressure_handling():
    """Verify 04: Missing pressure is preserved as None and flagged SUSPECT."""
    raw = load_fixture("04_missing_pressure.json")
    adapter = OpenMeteoQualificationAdapter()
    obs = adapter.normalize(raw, station_id="AWS_DELHI_001")[0]

    assert obs.temperature == 28.4
    assert obs.humidity == 62.0
    assert obs.pressure is None
    assert obs.data_quality_status == QualityStatus.SUSPECT


def test_05_invalid_rh_bounds_rejection():
    """Verify 05: RH > 100% is strictly rejected by physical limits validation."""
    raw = load_fixture("05_invalid_rh.json")
    adapter = OpenMeteoQualificationAdapter()
    with pytest.raises(ValidationError) as exc_info:
        adapter.normalize(raw, station_id="AWS_DELHI_001")
    assert "Relative humidity 145.0% exceeds physical limits" in str(exc_info.value)


def test_06_invalid_pressure_bounds_rejection():
    """Verify 06: Pressure > 1100 hPa is strictly rejected by physical limits validation."""
    raw = load_fixture("06_invalid_pressure.json")
    adapter = OpenMeteoQualificationAdapter()
    with pytest.raises(ValidationError) as exc_info:
        adapter.normalize(raw, station_id="AWS_DELHI_001")
    assert "Pressure 1500.0 hPa exceeds physical limits" in str(exc_info.value)


def test_07_malformed_timestamp_error():
    """Verify 07: Unparseable timestamp string raises ValueError."""
    raw = load_fixture("07_malformed_timestamp.json")
    adapter = OpenMeteoQualificationAdapter()
    with pytest.raises(ValueError):
        adapter.normalize(raw, station_id="AWS_DELHI_001")


def test_08_timezone_ambiguity_utc_enforcement():
    """Verify 08: Timestamp without explicit offset is safely interpreted as UTC."""
    raw = load_fixture("08_timezone_ambiguity.json")
    adapter = OpenMeteoQualificationAdapter()
    obs = adapter.normalize(raw, station_id="AWS_DELHI_001")[0]

    assert obs.timestamp.tzinfo is not None
    assert obs.timestamp == datetime(2026, 9, 17, 5, 0, 0, tzinfo=timezone.utc)


def test_09_duplicate_observation_contract():
    """Verify 09: Adapter idempotently parses repeated payloads with identical timestamps."""
    raw = load_fixture("09_duplicate_observation.json")
    adapter = OpenMeteoQualificationAdapter()
    obs1 = adapter.normalize(raw, station_id="AWS_DELHI_001")[0]
    obs2 = adapter.normalize(raw, station_id="AWS_DELHI_001")[0]

    assert obs1.timestamp == obs2.timestamp
    assert obs1.station_id == obs2.station_id
    assert obs1.temperature == obs2.temperature


def test_10_delayed_observation_latency_tracking():
    """Verify 10: Delayed observation preserves genuine observation timestamp distinct from ingestion timestamp."""
    raw = load_fixture("10_delayed_observation.json")
    adapter = OpenMeteoQualificationAdapter()
    retrieval_time = datetime(2026, 9, 17, 9, 0, 0, tzinfo=timezone.utc)
    obs = adapter.normalize(raw, station_id="AWS_DELHI_001", retrieval_timestamp=retrieval_time)[0]

    # Observation time remains 05:00 UTC (4 hours old)
    assert obs.timestamp == datetime(2026, 9, 17, 5, 0, 0, tzinfo=timezone.utc)
    # Ingestion time is 09:00 UTC
    assert obs.ingestion_timestamp == retrieval_time
    delta_hours = (obs.ingestion_timestamp - obs.timestamp).total_seconds() / 3600.0
    assert delta_hours == 4.0


def test_11_out_of_order_observation_series():
    """Verify 11: Multi-step hourly payload parses all entries without silent re-sorting."""
    raw = load_fixture("11_out_of_order_observation.json")
    adapter = OpenMeteoQualificationAdapter()
    observations = adapter.normalize(raw, station_id="AWS_DELHI_001")

    assert len(observations) == 3
    assert observations[0].timestamp == datetime(2026, 9, 17, 5, 0, 0, tzinfo=timezone.utc)
    assert observations[1].timestamp == datetime(2026, 9, 17, 3, 0, 0, tzinfo=timezone.utc)
    assert observations[2].timestamp == datetime(2026, 9, 17, 4, 0, 0, tzinfo=timezone.utc)


def test_12_unknown_station_identity_gate():
    """Verify 12: Quality gate catches and flags unexpected or unregistered station IDs."""
    raw = load_fixture("12_unknown_station.json")
    adapter = OpenMeteoQualificationAdapter()
    obs = adapter.normalize(raw, station_id="UNKNOWN_UNREGISTERED_STN_999")[0]

    gate_result = LiveSourceQualificationGate.evaluate(
        obs,
        expected_station_id="AWS_DELHI_001"
    )
    assert gate_result.is_qualified is False
    assert "station_identity_valid" in gate_result.checks
    assert gate_result.checks["station_identity_valid"] is False
    assert any("Station ID mismatch" in r for r in gate_result.reasons)


def test_13_unknown_pressure_semantics_rejection():
    """Verify 13: Unspecified pressure semantics fail qualification gate."""
    raw = load_fixture("13_unknown_pressure_semantics.json")
    adapter = OpenMeteoQualificationAdapter()
    
    # When pressure semantics are explicitly unknown, adapter must not populate MSLP
    obs = adapter.normalize(
        raw,
        station_id="AWS_DELHI_001",
        pressure_semantics=PressureSemantics.UNSPECIFIED_OR_UNKNOWN
    )[0]

    assert obs.pressure is None  # MSLP not populated
    gate_result = LiveSourceQualificationGate.evaluate(
        obs,
        pressure_semantics=PressureSemantics.UNSPECIFIED_OR_UNKNOWN
    )
    assert gate_result.is_qualified is False
    assert gate_result.checks["pressure_semantics_confirmed"] is False
    assert any("Pressure semantics unconfirmed" in r for r in gate_result.reasons)


def test_14_api_error_response_health_tracking():
    """Verify 14: Upstream HTTP 500 error updates LiveSourceHealthStatus correctly."""
    raw = load_fixture("14_api_error_response.json")
    health = LiveSourceHealthStatus(provider="open_meteo")

    assert health.is_reachable is True
    assert health.consecutive_failures == 0

    health.record_failure(error_msg=raw["reason"])
    assert health.consecutive_failures == 1
    assert health.last_error_message == "Internal Server Error: model backend timed out"

    # 3 consecutive failures marks source unreachable
    health.record_failure(error_msg=raw["reason"])
    health.record_failure(error_msg=raw["reason"])
    assert health.consecutive_failures == 3
    assert health.is_reachable is False


def test_15_rate_limit_response_health_tracking():
    """Verify 15: HTTP 429 rate limit payload is recorded with remaining quota."""
    raw = load_fixture("15_rate_limit_response.json")
    health = LiveSourceHealthStatus(provider="open_meteo")

    health.rate_limit_remaining = 0
    health.rate_limit_reset_seconds = 3600
    health.record_failure(error_msg=raw["reason"])

    assert health.rate_limit_remaining == 0
    assert health.last_error_message == "Hourly API request limit exceeded (10,000 calls / day reached)"


def test_16_authentication_failure_handling():
    """Verify 16: HTTP 401/403 invalid token updates auth status without logging secrets."""
    raw = load_fixture("16_authentication_failure.json")
    health = LiveSourceHealthStatus(provider="open_meteo_enterprise")

    health.record_failure(error_msg=raw["reason"], auth_failed=True)
    assert health.authentication_status == "INVALID_CREDENTIALS"
    assert "[REDACTED]" in health.last_error_message


def test_17_malformed_json_handling():
    """Verify 17: Truncated JSON increments malformed_response_count in health state."""
    raw_text = (FIXTURES_DIR / "17_malformed_json.json").read_text(encoding="utf-8")
    health = LiveSourceHealthStatus(provider="open_meteo")

    try:
        json.loads(raw_text)
        pytest.fail("Should have failed JSON decoding")
    except json.JSONDecodeError as e:
        health.record_failure(error_msg=f"JSON decode failed: {str(e)}", is_malformed=True)

    assert health.malformed_response_count == 1
    assert health.consecutive_failures == 1


def test_18_provider_field_missing_validation():
    """Verify 18: Payload missing coordinate fields raises clear ValueError."""
    raw = load_fixture("18_provider_field_missing.json")
    adapter = OpenMeteoQualificationAdapter()
    with pytest.raises(ValueError) as exc_info:
        adapter.normalize(raw, station_id="AWS_DELHI_001")
    assert "missing required latitude/longitude coordinates" in str(exc_info.value)


def test_19_unit_mismatch_kelvin_rejection():
    """Verify 19: Unconverted Kelvin temperature (301.55) is rejected by physical bounds."""
    raw = load_fixture("19_unit_mismatch.json")
    adapter = OpenMeteoQualificationAdapter()
    with pytest.raises(ValidationError) as exc_info:
        adapter.normalize(raw, station_id="AWS_DELHI_001")
    assert "Temperature 301.55°C exceeds physical limits" in str(exc_info.value)


def test_20_stale_observation_detection():
    """Verify 20: Stale observation is detected via elapsed timestamp delta."""
    raw = load_fixture("20_stale_observation.json")
    adapter = OpenMeteoQualificationAdapter()
    retrieval_time = datetime(2026, 9, 17, 8, 0, 0, tzinfo=timezone.utc)
    obs = adapter.normalize(raw, station_id="AWS_DELHI_001", retrieval_timestamp=retrieval_time)[0]

    health = LiveSourceHealthStatus(provider="open_meteo")
    elapsed_seconds = (retrieval_time - obs.timestamp).total_seconds()
    health.stale_feed_duration_seconds = elapsed_seconds

    assert health.stale_feed_duration_seconds == 10800.0  # 3 hours


def test_live_source_settings_and_environment():
    """Verify live source configuration schemas and default values."""
    settings = get_settings()
    assert isinstance(settings.live_source, LiveSourceSettings)
    assert settings.live_source.enabled is False
    assert settings.live_source.provider == "open_meteo"
    assert settings.live_source.base_url == "https://api.open-meteo.com/v1"
    assert settings.live_source.pressure_product_type == "msl"
    assert settings.live_source.retry_limit == 3
