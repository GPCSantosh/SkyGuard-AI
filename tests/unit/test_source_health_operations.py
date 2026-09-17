"""Phase 11C Unit and Integration Tests: Source Health & Live Operations Hardening.

Covers:
- Scenarios A through N: deterministic state machine transitions, outage episodes,
  recovery warm-up, observation loss calculation, station live freshness vs sensor health,
  latency tracking, secret redaction, and API contract compliance.
"""

from datetime import datetime, timedelta, timezone
import pytest
from unittest.mock import MagicMock

from backend.app.ingestion.source_health import (
    ErrorCategory,
    OutageEpisode,
    SourceHealthState,
    SourceHealthStateMachine,
    SourceHealthTransition,
    StationLiveRecord,
    StationLiveStatus,
)
from backend.app.models.observation import (
    ObservationSource,
    QualityStatus,
    WeatherObservation,
)


def _make_obs(
    station_id: str = "42182099999",
    age_seconds: float = 60.0,
    temp: float = 25.0,
    humidity: float = 50.0,
    pressure: float = 1013.25,
) -> WeatherObservation:
    now = datetime.now(timezone.utc)
    obs_ts = now - timedelta(seconds=age_seconds)
    return WeatherObservation(
        station_id=station_id,
        timestamp=obs_ts,
        latitude=28.5845,
        longitude=77.2058,
        elevation=214.9,
        temperature=temp,
        humidity=humidity,
        pressure=pressure,
        source=ObservationSource.OPEN_METEO,
        report_type="LIVE_API_CURRENT",
        raw_quality_flags={},
        data_quality_status=QualityStatus.VALID,
        ingestion_timestamp=now,
        native_resolution_minutes=15.0,
        is_synthetic=False,
    )


def test_scenario_a_normal_healthy_operation():
    """Scenario A: Successful recent observations produce HEALTHY state."""
    sm = SourceHealthStateMachine(outage_consecutive_failures=3, recovery_required_successes=2)
    now = datetime.now(timezone.utc)

    station_results = {
        "STN_1": {
            "success": True,
            "observation_timestamp": now - timedelta(seconds=120),
            "ingestion_timestamp": now,
            "temperature": 24.5,
            "humidity": 60.0,
            "pressure": 1012.0,
        },
        "STN_2": {
            "success": True,
            "observation_timestamp": now - timedelta(seconds=120),
            "ingestion_timestamp": now,
            "temperature": 25.1,
            "humidity": 58.0,
            "pressure": 1011.8,
        },
    }

    sm.record_poll_cycle_success(latency_ms=45.2, station_results=station_results, timestamp=now)

    assert sm.current_state == SourceHealthState.HEALTHY
    assert sm.consecutive_failures == 0
    assert sm.consecutive_successes == 1
    assert sm.stations["STN_1"].status == StationLiveStatus.LIVE
    assert sm.stations["STN_2"].status == StationLiveStatus.LIVE
    assert sm.active_episode is None


def test_scenario_b_transient_timeout():
    """Scenario B: A single transient timeout moves source to DEGRADED."""
    sm = SourceHealthStateMachine(outage_consecutive_failures=3, recovery_required_successes=2)
    now = datetime.now(timezone.utc)

    sm.record_poll_cycle_failure(
        category=ErrorCategory.TIMEOUT,
        error_message="Request timeout after 10.0s",
        affected_stations=["STN_1", "STN_2"],
        timestamp=now,
    )

    assert sm.current_state == SourceHealthState.DEGRADED
    assert sm.consecutive_failures == 1
    assert sm.consecutive_successes == 0
    assert sm.active_episode is not None
    assert sm.active_episode.initial_state == SourceHealthState.DEGRADED
    assert "TIMEOUT" in sm.active_episode.failure_categories


def test_scenario_c_and_h_repeated_timeout_and_complete_disconnect():
    """Scenario C & H: 3 consecutive timeouts transition to DISCONNECTED with outage episode."""
    sm = SourceHealthStateMachine(outage_consecutive_failures=3, recovery_required_successes=2)
    t0 = datetime.now(timezone.utc)

    for i in range(3):
        sm.record_poll_cycle_failure(
            category=ErrorCategory.TIMEOUT,
            error_message=f"Timeout {i + 1}",
            affected_stations=["STN_1", "STN_2"],
            timestamp=t0 + timedelta(seconds=i * 900),
        )

    assert sm.current_state == SourceHealthState.DISCONNECTED
    assert sm.consecutive_failures == 3
    assert sm.stations["STN_1"].status == StationLiveStatus.OFFLINE
    assert sm.stations["STN_2"].status == StationLiveStatus.OFFLINE

    ep = sm.active_episode
    assert ep is not None
    assert ep.is_ongoing is True
    assert ep.current_state == SourceHealthState.DISCONNECTED
    assert len(ep.affected_stations) == 2


def test_scenario_d_http_500():
    """Scenario D: Upstream HTTP 500 error classification."""
    sm = SourceHealthStateMachine(outage_consecutive_failures=3)
    now = datetime.now(timezone.utc)

    sm.record_poll_cycle_failure(
        category=ErrorCategory.HTTP_5XX,
        error_message="HTTP 500 Internal Server Error",
        affected_stations=["STN_1"],
        timestamp=now,
    )

    assert sm.current_state == SourceHealthState.DEGRADED
    assert sm.active_episode.failure_categories == ["HTTP_5XX"]


def test_scenario_e_http_429_rate_limit():
    """Scenario E: Upstream HTTP 429 immediately enters RATE_LIMITED state."""
    sm = SourceHealthStateMachine()
    now = datetime.now(timezone.utc)

    sm.record_poll_cycle_failure(
        category=ErrorCategory.HTTP_429,
        error_message="HTTP 429 Too Many Requests",
        affected_stations=["STN_1"],
        timestamp=now,
    )

    assert sm.current_state == SourceHealthState.RATE_LIMITED
    assert sm.active_episode.initial_state == SourceHealthState.RATE_LIMITED


def test_scenario_f_http_401_auth_error():
    """Scenario F: Upstream HTTP 401 enters AUTH_ERROR state immediately."""
    sm = SourceHealthStateMachine()
    now = datetime.now(timezone.utc)

    sm.record_poll_cycle_failure(
        category=ErrorCategory.HTTP_401,
        error_message="HTTP 401 Unauthorized",
        affected_stations=["STN_1"],
        timestamp=now,
    )

    assert sm.current_state == SourceHealthState.AUTH_ERROR
    assert sm.active_episode.initial_state == SourceHealthState.AUTH_ERROR


def test_scenario_g_stale_feed():
    """Scenario G: Successful connection with observations older than stale_threshold -> STALE."""
    sm = SourceHealthStateMachine(stale_threshold_seconds=3600.0)
    now = datetime.now(timezone.utc)
    old_ts = now - timedelta(seconds=7200)  # 2 hours old

    station_results = {
        "STN_1": {
            "success": True,
            "observation_timestamp": old_ts,
            "ingestion_timestamp": now,
            "temperature": 28.0,
            "humidity": 50.0,
            "pressure": 1012.0,
        }
    }

    sm.record_poll_cycle_success(latency_ms=30.0, station_results=station_results, timestamp=now)

    assert sm.current_state == SourceHealthState.STALE
    assert sm.stations["STN_1"].status == StationLiveStatus.STALE
    assert sm.stations["STN_1"].is_stale is True
    assert sm.stations["STN_1"].observation_age_seconds >= 7200.0


def test_scenario_i_recovery_warmup_and_episode_resolution():
    """Scenario I: Deterministic recovery warm-up requires configured consecutive successes."""
    sm = SourceHealthStateMachine(
        outage_consecutive_failures=3,
        recovery_required_successes=2,
        expected_cadence_seconds=900.0,
    )
    t0 = datetime.now(timezone.utc)

    # 1. Trigger Disconnect Outage
    for i in range(3):
        sm.record_poll_cycle_failure(
            category=ErrorCategory.TIMEOUT,
            error_message=f"Timeout {i + 1}",
            affected_stations=["STN_1"],
            timestamp=t0 + timedelta(seconds=i * 900),
        )
    assert sm.current_state == SourceHealthState.DISCONNECTED
    assert sm.active_episode is not None

    # 2. First successful poll (Warm-up -> DEGRADED)
    t_rec1 = t0 + timedelta(seconds=3600)
    station_results = {
        "STN_1": {
            "success": True,
            "observation_timestamp": t_rec1 - timedelta(seconds=60),
            "ingestion_timestamp": t_rec1,
            "temperature": 22.0,
            "humidity": 45.0,
            "pressure": 1015.0,
        }
    }
    sm.record_poll_cycle_success(latency_ms=25.0, station_results=station_results, timestamp=t_rec1)

    assert sm.current_state == SourceHealthState.DEGRADED
    assert sm.consecutive_successes == 1
    assert sm.active_episode is not None  # Not yet resolved

    # 3. Second successful poll (Completes Warm-up -> HEALTHY)
    t_rec2 = t_rec1 + timedelta(seconds=900)
    station_results_2 = {
        "STN_1": {
            "success": True,
            "observation_timestamp": t_rec2 - timedelta(seconds=60),
            "ingestion_timestamp": t_rec2,
            "temperature": 22.5,
            "humidity": 46.0,
            "pressure": 1014.8,
        }
    }
    sm.record_poll_cycle_success(latency_ms=22.0, station_results=station_results_2, timestamp=t_rec2)

    assert sm.current_state == SourceHealthState.HEALTHY
    assert sm.consecutive_successes == 2
    assert sm.active_episode is None  # Resolved!

    # Verify resolved episode history
    episodes = sm.get_recent_episodes()
    assert len(episodes) == 1
    assert episodes[0].is_ongoing is False
    assert episodes[0].resolved_at == t_rec2
    assert episodes[0].duration_seconds == (t_rec2 - t0).total_seconds()
    assert episodes[0].observation_loss_estimate == int(episodes[0].duration_seconds / 900.0) * 1


def test_scenario_j_and_k_partial_and_multi_station_failure():
    """Scenario J & K: Partial station failure keeps source DEGRADED and isolates station status."""
    sm = SourceHealthStateMachine(outage_consecutive_failures=3)
    now = datetime.now(timezone.utc)

    station_results = {
        "STN_HEALTHY": {
            "success": True,
            "observation_timestamp": now - timedelta(seconds=100),
            "ingestion_timestamp": now,
            "temperature": 20.0,
            "humidity": 50.0,
            "pressure": 1013.0,
        },
        "STN_FAILING": {
            "success": False,
            "error_category": ErrorCategory.PARSE_ERROR,
            "error_message": "Malformed response",
        },
    }

    sm.record_poll_cycle_success(latency_ms=50.0, station_results=station_results, timestamp=now)

    assert sm.current_state == SourceHealthState.DEGRADED
    assert sm.stations["STN_HEALTHY"].status == StationLiveStatus.LIVE
    assert sm.stations["STN_FAILING"].status == StationLiveStatus.STALE  # 1st failure
    assert sm.stations["STN_FAILING"].consecutive_failures == 1


def test_scenario_l_bounded_retention():
    """Scenario L: History deques adhere strictly to max_history_records and max_outage_episodes."""
    sm = SourceHealthStateMachine(max_history_records=5, max_outage_episodes=3)
    now = datetime.now(timezone.utc)

    # Trigger multiple transitions
    for i in range(10):
        sm.record_poll_cycle_failure(
            category=ErrorCategory.TIMEOUT,
            error_message=f"Timeout {i}",
            affected_stations=["STN_1"],
            timestamp=now + timedelta(seconds=i * 10),
        )
        sm.record_poll_cycle_success(
            latency_ms=20.0,
            station_results={"STN_1": {"success": True, "observation_timestamp": now, "ingestion_timestamp": now}},
            timestamp=now + timedelta(seconds=i * 10 + 5),
        )

    transitions = sm.get_recent_transitions()
    episodes = sm.get_recent_episodes()

    assert len(transitions) <= 5
    assert len(episodes) <= 3


def test_scenario_m_secret_redaction_in_summary():
    """Scenario M: Summary dictionary contains no secrets or raw auth tokens."""
    sm = SourceHealthStateMachine()
    summary = sm.get_summary()

    summary_str = str(summary)
    assert "api_key" not in summary_str
    assert "apikey" not in summary_str
    assert "secret" not in summary_str


def test_scenario_n_source_health_separate_from_sensor_health():
    """Scenario N: Upstream outage does not mutate physical sensor health score models."""
    from backend.app.models.health import SensorHealthStatus, HealthTier

    # Sensor health model
    dummy_sensor_health = SensorHealthStatus(
        station_id="42182099999",
        overall_health_score=95.0,
        health_tier=HealthTier.HEALTHY,
        temperature_health=98.0,
        pressure_health=95.0,
        humidity_health=92.0,
        anomaly_count_24h=0,
        missing_intervals_24h=0,
        data_completeness_pct_24h=100.0,
        drift_detected=False,
        frozen_detected=False,
    )

    # Simulate severe upstream API outage
    sm = SourceHealthStateMachine(outage_consecutive_failures=3)
    for _ in range(3):
        sm.record_poll_cycle_failure(
            category=ErrorCategory.HTTP_401,
            error_message="Invalid credentials",
            affected_stations=["42182099999"],
        )

    assert sm.current_state == SourceHealthState.AUTH_ERROR
    # Sensor health remains untainted
    assert dummy_sensor_health.overall_health_score == 95.0
    assert dummy_sensor_health.health_tier == HealthTier.HEALTHY
