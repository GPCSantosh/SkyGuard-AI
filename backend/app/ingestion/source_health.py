"""Source Health State Machine and Operations Monitor for SkyGuard AI.

Implements Phase 11C operational observability, deterministic state transitions,
outage episode tracking, station freshness monitoring, and latency diagnostics.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Deque, Dict, List, Optional, Set
from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.logging import get_logger

logger = get_logger("source_health")


class SourceHealthState(str, Enum):
    """Deterministic states of the live upstream data source.
    
    CRITICAL DISTINCTION:
    - Source Health: upstream feed / API connectivity, auth, quota, and freshness.
    - Sensor Health: physical AWS hardware sensor performance & degradation.
    """
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    DISCONNECTED = "DISCONNECTED"
    RATE_LIMITED = "RATE_LIMITED"
    AUTH_ERROR = "AUTH_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"


class StationLiveStatus(str, Enum):
    """Operational freshness status of an individual Automatic Weather Station feed."""
    LIVE = "LIVE"
    STALE = "STALE"
    OFFLINE = "OFFLINE"


class ErrorCategory(str, Enum):
    """Classification of live telemetry ingestion errors."""
    NONE = "NONE"
    TIMEOUT = "TIMEOUT"
    HTTP_5XX = "HTTP_5XX"
    HTTP_429 = "HTTP_429"
    HTTP_401 = "HTTP_401"
    HTTP_403 = "HTTP_403"
    PARSE_ERROR = "PARSE_ERROR"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    NETWORK_ERROR = "NETWORK_ERROR"
    CONFIG_ERROR = "CONFIG_ERROR"


class SourceHealthTransition(BaseModel):
    """Record of a source health state transition."""
    model_config = ConfigDict(frozen=True)

    from_state: SourceHealthState
    to_state: SourceHealthState
    timestamp: datetime
    reason: str
    trigger_category: ErrorCategory = ErrorCategory.NONE
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OutageEpisode(BaseModel):
    """Operational episode representing a significant source interruption or degradation."""
    model_config = ConfigDict(populate_by_name=True)

    episode_id: str
    started_at: datetime
    resolved_at: Optional[datetime] = None
    source: str
    affected_stations: List[str] = Field(default_factory=list)
    initial_state: SourceHealthState
    current_state: SourceHealthState
    duration_seconds: float = 0.0
    failure_categories: List[str] = Field(default_factory=list)
    observation_loss_estimate: Optional[int] = None
    is_ongoing: bool = True

    def update_duration(self, current_time: Optional[datetime] = None) -> None:
        """Update elapsed duration in seconds."""
        end_time = self.resolved_at or current_time or datetime.now(timezone.utc)
        self.duration_seconds = max(0.0, (end_time - self.started_at).total_seconds())

    def calculate_loss_estimate(self, cadence_seconds: float) -> None:
        """Estimate observation loss based on outage duration and affected station count."""
        if cadence_seconds <= 0 or not self.affected_stations:
            self.observation_loss_estimate = None
            return
        cycles = math.floor(self.duration_seconds / cadence_seconds)
        self.observation_loss_estimate = max(0, int(cycles * len(self.affected_stations)))


class StationLiveRecord(BaseModel):
    """Per-station live telemetry ingestion status (isolated from physical sensor health)."""
    model_config = ConfigDict(populate_by_name=True)

    station_id: str
    status: StationLiveStatus = StationLiveStatus.OFFLINE
    last_observation_timestamp: Optional[datetime] = None
    last_ingestion_timestamp: Optional[datetime] = None
    observation_age_seconds: Optional[float] = None
    ingestion_latency_seconds: Optional[float] = None
    consecutive_failures: int = 0
    latest_successful_poll_utc: Optional[datetime] = None
    latest_error_category: ErrorCategory = ErrorCategory.NONE
    latest_error_message: Optional[str] = None
    is_stale: bool = False
    duplicate_count: int = 0
    rejected_observation_count: int = 0
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None


class SourceHealthStateMachine:
    """State machine managing source health, recovery detection, and outage episodes."""

    def __init__(
        self,
        provider: str = "open_meteo",
        outage_consecutive_failures: int = 3,
        recovery_required_successes: int = 2,
        stale_threshold_seconds: float = 3600.0,
        expected_cadence_seconds: float = 900.0,
        max_history_records: int = 50,
        max_outage_episodes: int = 20,
        repository: Optional[Any] = None,
    ) -> None:
        self.provider = provider
        self.outage_consecutive_failures = outage_consecutive_failures
        self.recovery_required_successes = recovery_required_successes
        self.stale_threshold_seconds = stale_threshold_seconds
        self.expected_cadence_seconds = expected_cadence_seconds
        self.max_history_records = max_history_records
        self.max_outage_episodes = max_outage_episodes
        self.repository = repository


        # Current state
        self._current_state: SourceHealthState = SourceHealthState.HEALTHY
        self._consecutive_failures: int = 0
        self._consecutive_successes: int = 0
        self._last_successful_poll_utc: Optional[datetime] = None
        self._last_poll_attempt_utc: Optional[datetime] = None
        self._last_request_latency_ms: Optional[float] = None

        # Episode & History management
        self._transitions: Deque[SourceHealthTransition] = deque(maxlen=max_history_records)
        self._episodes: Deque[OutageEpisode] = deque(maxlen=max_outage_episodes)
        self._active_episode: Optional[OutageEpisode] = None
        self._episode_counter: int = 0

        # Station Live Tracking
        self.stations: Dict[str, StationLiveRecord] = {}

        # Aggregate Metrics
        self.metrics: Dict[str, Any] = {
            "poll_attempts_total": 0,
            "successful_polls_total": 0,
            "failed_polls_total": 0,
            "stale_observations_total": 0,
            "rejected_observations_total": 0,
            "duplicate_observations_total": 0,
            "total_request_latency_ms": 0.0,
            "mean_request_latency_ms": 0.0,
        }

    @property
    def current_state(self) -> SourceHealthState:
        """Current operational source health state."""
        return self._current_state

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    @property
    def consecutive_successes(self) -> int:
        return self._consecutive_successes

    @property
    def last_successful_poll_utc(self) -> Optional[datetime]:
        return self._last_successful_poll_utc

    @property
    def active_episode(self) -> Optional[OutageEpisode]:
        if self._active_episode is not None:
            self._active_episode.update_duration()
            self._active_episode.calculate_loss_estimate(self.expected_cadence_seconds)
        return self._active_episode

    def get_recent_transitions(self) -> List[SourceHealthTransition]:
        """Return shallow list of recent transitions."""
        return list(self._transitions)

    def get_recent_episodes(self) -> List[OutageEpisode]:
        """Return list of recent outage episodes with updated durations."""
        now = datetime.now(timezone.utc)
        episodes_list = list(self._episodes)
        for ep in episodes_list:
            if ep.is_ongoing:
                ep.update_duration(now)
                ep.calculate_loss_estimate(self.expected_cadence_seconds)
        return episodes_list

    def _transition_to(
        self,
        new_state: SourceHealthState,
        reason: str,
        category: ErrorCategory = ErrorCategory.NONE,
        affected_stations: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Transition to a new state, manage outage episodes, and emit structured log."""
        ts = timestamp or datetime.now(timezone.utc)
        prev_state = self._current_state

        if prev_state == new_state:
            # Update active episode failure category if ongoing
            if self._active_episode and category != ErrorCategory.NONE:
                cat_val = category.value
                if cat_val not in self._active_episode.failure_categories:
                    self._active_episode.failure_categories.append(cat_val)
            return

        self._current_state = new_state
        rec = SourceHealthTransition(
            from_state=prev_state,
            to_state=new_state,
            timestamp=ts,
            reason=reason,
            trigger_category=category,
            metadata={"consecutive_failures": self._consecutive_failures, "consecutive_successes": self._consecutive_successes},
        )
        self._transitions.append(rec)
        if self.repository is not None and hasattr(self.repository, "save_source_transition"):
            try:
                self.repository.save_source_transition(rec, source=self.provider)
            except Exception as repo_err:
                logger.warning("Failed to persist source transition to repository: %s", str(repo_err))

        # Structured operational log
        logger.info(
            "source_health_transition source=%s previous=%s current=%s reason=%s timestamp=%s",
            self.provider,
            prev_state.value,
            new_state.value,
            reason,
            ts.isoformat(),
        )

        # Outage Episode lifecycle
        if new_state in (
            SourceHealthState.DEGRADED,
            SourceHealthState.DISCONNECTED,
            SourceHealthState.RATE_LIMITED,
            SourceHealthState.AUTH_ERROR,
            SourceHealthState.CONFIG_ERROR,
            SourceHealthState.STALE,
        ):
            if self._active_episode is None:
                self._episode_counter += 1
                ep_id = f"ep_{ts.strftime('%Y%m%d_%H%M%S')}_{self._episode_counter}"
                stations_list = affected_stations or list(self.stations.keys())
                self._active_episode = OutageEpisode(
                    episode_id=ep_id,
                    started_at=ts,
                    source=self.provider,
                    affected_stations=stations_list,
                    initial_state=new_state,
                    current_state=new_state,
                    failure_categories=[category.value] if category != ErrorCategory.NONE else [],
                    is_ongoing=True,
                )
                self._episodes.append(self._active_episode)
                if self.repository is not None and hasattr(self.repository, "save_outage_episode"):
                    try:
                        self.repository.save_outage_episode(self._active_episode)
                    except Exception as repo_err:
                        logger.warning("Failed to persist outage episode to repository: %s", str(repo_err))
            else:
                self._active_episode.current_state = new_state
                if category != ErrorCategory.NONE and category.value not in self._active_episode.failure_categories:
                    self._active_episode.failure_categories.append(category.value)
                if affected_stations:
                    merged = list(set(self._active_episode.affected_stations + affected_stations))
                    self._active_episode.affected_stations = merged
                if self.repository is not None and hasattr(self.repository, "save_outage_episode"):
                    try:
                        self.repository.save_outage_episode(self._active_episode)
                    except Exception as repo_err:
                        logger.warning("Failed to update outage episode in repository: %s", str(repo_err))

        elif new_state == SourceHealthState.HEALTHY:
            if self._active_episode is not None:
                self._active_episode.resolved_at = ts
                self._active_episode.current_state = SourceHealthState.HEALTHY
                self._active_episode.is_ongoing = False
                self._active_episode.update_duration(ts)
                self._active_episode.calculate_loss_estimate(self.expected_cadence_seconds)
                logger.info(
                    "outage_episode_resolved episode_id=%s source=%s duration=%.1fs loss_estimate=%s",
                    self._active_episode.episode_id,
                    self.provider,
                    self._active_episode.duration_seconds,
                    self._active_episode.observation_loss_estimate,
                )
                if self.repository is not None and hasattr(self.repository, "save_outage_episode"):
                    try:
                        self.repository.save_outage_episode(self._active_episode)
                    except Exception as repo_err:
                        logger.warning("Failed to persist resolved outage episode to repository: %s", str(repo_err))
                self._active_episode = None


    def record_poll_cycle_success(
        self,
        latency_ms: float,
        station_results: Dict[str, Dict[str, Any]],
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Evaluate source and station health after a completed multi-station poll cycle."""
        now = timestamp or datetime.now(timezone.utc)
        self._last_poll_attempt_utc = now
        self._last_request_latency_ms = round(latency_ms, 2)
        self.metrics["poll_attempts_total"] += 1
        self.metrics["successful_polls_total"] += 1
        self.metrics["total_request_latency_ms"] += latency_ms
        if self.metrics["successful_polls_total"] > 0:
            self.metrics["mean_request_latency_ms"] = round(
                self.metrics["total_request_latency_ms"] / self.metrics["successful_polls_total"], 2
            )

        self._consecutive_failures = 0
        self._consecutive_successes += 1
        self._last_successful_poll_utc = now

        # Update Station Live Records
        failed_stations: List[str] = []
        stale_stations: List[str] = []
        live_stations: List[str] = []

        for stn_id, data in station_results.items():
            rec = self.stations.setdefault(stn_id, StationLiveRecord(station_id=stn_id))
            success = data.get("success", False)
            if success:
                obs_ts = data.get("observation_timestamp")
                ing_ts = data.get("ingestion_timestamp") or now
                obs_age = (now - obs_ts).total_seconds() if obs_ts else 0.0
                ing_delay = (ing_ts - obs_ts).total_seconds() if obs_ts else 0.0
                is_stale = obs_age > self.stale_threshold_seconds

                rec.status = StationLiveStatus.STALE if is_stale else StationLiveStatus.LIVE
                rec.last_observation_timestamp = obs_ts
                rec.last_ingestion_timestamp = ing_ts
                rec.observation_age_seconds = round(obs_age, 1)
                rec.ingestion_latency_seconds = round(ing_delay, 1)
                rec.consecutive_failures = 0
                rec.latest_successful_poll_utc = now
                rec.latest_error_category = ErrorCategory.NONE
                rec.latest_error_message = None
                rec.is_stale = is_stale
                rec.temperature_c = data.get("temperature")
                rec.humidity_pct = data.get("humidity")
                rec.pressure_hpa = data.get("pressure")

                if data.get("is_duplicate"):
                    rec.duplicate_count += 1
                    self.metrics["duplicate_observations_total"] += 1
                if data.get("is_rejected"):
                    rec.rejected_observation_count += 1
                    self.metrics["rejected_observations_total"] += 1
                if is_stale:
                    self.metrics["stale_observations_total"] += 1
                    stale_stations.append(stn_id)
                else:
                    live_stations.append(stn_id)
            else:
                rec.consecutive_failures += 1
                rec.latest_error_category = data.get("error_category", ErrorCategory.NETWORK_ERROR)
                rec.latest_error_message = data.get("error_message")
                rec.status = StationLiveStatus.OFFLINE if rec.consecutive_failures >= self.outage_consecutive_failures else StationLiveStatus.STALE
                failed_stations.append(stn_id)

        # Deterministic State Machine Evaluation
        total_stations = len(station_results)
        if total_stations == 0:
            return

        if len(failed_stations) == total_stations:
            # Complete station failure despite HTTP success
            self._transition_to(
                SourceHealthState.DEGRADED,
                reason=f"All {total_stations} stations failed parsing or normalization",
                category=ErrorCategory.SCHEMA_VIOLATION,
                affected_stations=failed_stations,
                timestamp=now,
            )
        elif len(failed_stations) > 0:
            # Partial station failure
            self._transition_to(
                SourceHealthState.DEGRADED,
                reason=f"{len(failed_stations)} of {total_stations} stations failed ingestion",
                category=ErrorCategory.NETWORK_ERROR,
                affected_stations=failed_stations,
                timestamp=now,
            )
        elif len(stale_stations) == total_stations:
            # All observations stale
            self._transition_to(
                SourceHealthState.STALE,
                reason=f"All {total_stations} station observations exceed stale threshold ({self.stale_threshold_seconds}s)",
                category=ErrorCategory.NONE,
                affected_stations=stale_stations,
                timestamp=now,
            )
        elif len(stale_stations) > 0:
            # Mixed fresh and stale observations
            self._transition_to(
                SourceHealthState.DEGRADED,
                reason=f"{len(stale_stations)} of {total_stations} stations have stale observations",
                category=ErrorCategory.NONE,
                affected_stations=stale_stations,
                timestamp=now,
            )
        else:
            # All stations fresh & successful
            if self._current_state != SourceHealthState.HEALTHY:
                if self._consecutive_successes >= self.recovery_required_successes:
                    self._transition_to(
                        SourceHealthState.HEALTHY,
                        reason=f"Source recovered: {self._consecutive_successes} consecutive successful cycles",
                        category=ErrorCategory.NONE,
                        timestamp=now,
                    )
                else:
                    self._transition_to(
                        SourceHealthState.DEGRADED,
                        reason=f"Recovery warm-up ({self._consecutive_successes}/{self.recovery_required_successes} successes)",
                        category=ErrorCategory.NONE,
                        timestamp=now,
                    )

    def record_poll_cycle_failure(
        self,
        category: ErrorCategory,
        error_message: str,
        affected_stations: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Record an entire poll cycle failure and trigger deterministic state transitions."""
        now = timestamp or datetime.now(timezone.utc)
        self._last_poll_attempt_utc = now
        self.metrics["poll_attempts_total"] += 1
        self.metrics["failed_polls_total"] += 1
        self._consecutive_failures += 1
        self._consecutive_successes = 0

        aff = affected_stations or list(self.stations.keys())

        # Update station consecutive failures
        for stn_id in aff:
            rec = self.stations.setdefault(stn_id, StationLiveRecord(station_id=stn_id))
            rec.consecutive_failures += 1
            rec.latest_error_category = category
            rec.latest_error_message = error_message
            if rec.consecutive_failures >= self.outage_consecutive_failures:
                rec.status = StationLiveStatus.OFFLINE

        # Deterministic Source Health Transitions
        if category in (ErrorCategory.HTTP_401, ErrorCategory.HTTP_403):
            self._transition_to(
                SourceHealthState.AUTH_ERROR,
                reason=f"Authentication failure: {error_message}",
                category=category,
                affected_stations=aff,
                timestamp=now,
            )
        elif category == ErrorCategory.HTTP_429:
            self._transition_to(
                SourceHealthState.RATE_LIMITED,
                reason=f"Rate limit exceeded: {error_message}",
                category=category,
                affected_stations=aff,
                timestamp=now,
            )
        elif category == ErrorCategory.CONFIG_ERROR:
            self._transition_to(
                SourceHealthState.CONFIG_ERROR,
                reason=f"Configuration error: {error_message}",
                category=category,
                affected_stations=aff,
                timestamp=now,
            )
        elif self._consecutive_failures >= self.outage_consecutive_failures:
            self._transition_to(
                SourceHealthState.DISCONNECTED,
                reason=f"Outage threshold exceeded: {self._consecutive_failures} consecutive failures ({category.value})",
                category=category,
                affected_stations=aff,
                timestamp=now,
            )
        else:
            self._transition_to(
                SourceHealthState.DEGRADED,
                reason=f"Transient failure ({self._consecutive_failures}/{self.outage_consecutive_failures}): {error_message}",
                category=category,
                affected_stations=aff,
                timestamp=now,
            )

    def get_summary(self) -> Dict[str, Any]:
        """Return comprehensive secret-redacted operational summary."""
        now = datetime.now(timezone.utc)
        station_recs = {
            stn_id: rec.model_dump()
            for stn_id, rec in self.stations.items()
        }

        # Calculate counts
        total_stns = len(self.stations)
        live_count = sum(1 for r in self.stations.values() if r.status == StationLiveStatus.LIVE)
        stale_count = sum(1 for r in self.stations.values() if r.status == StationLiveStatus.STALE)
        offline_count = sum(1 for r in self.stations.values() if r.status == StationLiveStatus.OFFLINE)

        active_ep = self.active_episode

        return {
            "source_state": self._current_state.value,
            "provider": self.provider,
            "consecutive_failures": self._consecutive_failures,
            "consecutive_successes": self._consecutive_successes,
            "last_successful_poll_utc": self._last_successful_poll_utc.isoformat() if self._last_successful_poll_utc else None,
            "last_poll_attempt_utc": self._last_poll_attempt_utc.isoformat() if self._last_poll_attempt_utc else None,
            "last_request_latency_ms": self._last_request_latency_ms,
            "stale_threshold_seconds": self.stale_threshold_seconds,
            "recovery_required_successes": self.recovery_required_successes,
            "outage_consecutive_failures": self.outage_consecutive_failures,
            "counts": {
                "total_stations": total_stns,
                "live_stations": live_count,
                "stale_stations": stale_count,
                "offline_stations": offline_count,
            },
            "active_episode": active_ep.model_dump() if active_ep else None,
            "recent_episodes": [ep.model_dump() for ep in self.get_recent_episodes()],
            "recent_transitions": [t.model_dump() for t in self.get_recent_transitions()],
            "stations": station_recs,
            "metrics": self.metrics,
        }
