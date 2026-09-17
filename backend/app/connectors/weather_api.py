"""Open-Meteo & External Weather REST API Live Connector for SkyGuard AI.

Implements Phase 11B production live telemetry ingestion conforming to
the canonical WeatherObservation contract using standard library HTTP transport.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import math
import time
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union
import urllib.error
import urllib.parse
import urllib.request

from backend.app.connectors.base import BaseConnector
from backend.app.connectors.live_qualification import (
    LiveSourceHealthStatus,
    LiveSourceQualificationGate,
    OpenMeteoQualificationAdapter,
    PressureSemantics,
)
from backend.app.core.config import LiveSourceSettings, get_settings
from backend.app.core.logging import get_logger
from backend.app.models.observation import (
    ObservationSource,
    QualityStatus,
    WeatherObservation,
)

logger = get_logger("live_connector")


class OpenMeteoLiveConnector(BaseConnector):
    """Production live connector for querying Open-Meteo WMO surface weather feeds."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        retry_limit: Optional[int] = None,
        retry_backoff_base_seconds: Optional[float] = None,
        pressure_semantics: PressureSemantics = PressureSemantics.MEAN_SEA_LEVEL_PRESSURE,
        config: Optional[Dict[str, Any]] = None,
        http_fetcher: Optional[Callable[[str, float], Tuple[int, Dict[str, Any]]]] = None,
    ) -> None:
        super().__init__(config=config)
        app_settings = get_settings()
        live_cfg = app_settings.live_source

        resolved_url = base_url or api_base_url or live_cfg.base_url or "https://api.open-meteo.com/v1"
        self.base_url = resolved_url.rstrip("/")
        self.api_base_url = self.base_url
        self.api_key = api_key or live_cfg.api_key
        self.timeout_seconds = timeout_seconds or live_cfg.timeout_seconds
        self.retry_limit = retry_limit if retry_limit is not None else live_cfg.retry_limit
        self.retry_backoff_base_seconds = retry_backoff_base_seconds if retry_backoff_base_seconds is not None else live_cfg.retry_backoff_base_seconds
        self.pressure_semantics = pressure_semantics


        self.adapter = OpenMeteoQualificationAdapter(source_type=ObservationSource.OPEN_METEO)
        self.health = LiveSourceHealthStatus(
            provider=live_cfg.provider or "open_meteo",
            authentication_status="AUTHENTICATED" if self.api_key else "UNAUTHENTICATED_OPEN",
        )

        self._custom_fetcher = http_fetcher
        self.is_connected = False

    def connect(self) -> None:
        """Initialize connection status."""
        self.is_connected = True
        logger.info("OpenMeteoLiveConnector connected to %s", self.base_url)

    def disconnect(self) -> None:
        """Release connector resources."""
        self.is_connected = False
        logger.info("OpenMeteoLiveConnector disconnected.")

    def _sanitize_url_for_logging(self, url: str) -> str:
        """Strip API keys and credentials from logged URLs."""
        if "apikey=" in url or "api_key=" in url:
            import re
            return re.sub(r'(apikey|api_key)=[^&]+', r'\1=[REDACTED]', url)
        return url

    def build_query_params(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Construct standard query parameters for Open-Meteo current surface observations."""
        params: Dict[str, Any] = {
            "latitude": round(float(latitude), 4),
            "longitude": round(float(longitude), 4),
            "current": "temperature_2m,relative_humidity_2m,pressure_msl,surface_pressure,dew_point_2m,wind_speed_10m,precipitation",
            "timezone": "UTC",
        }
        if self.api_key:
            params["apikey"] = self.api_key
        return params

    def _execute_http_get(self, url: str, timeout: float) -> Tuple[int, Dict[str, Any]]:
        """Perform a low-level HTTP GET and return (status_code, parsed_json)."""
        if self._custom_fetcher is not None:
            return self._custom_fetcher(url, timeout)

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "SkyGuard-AI/1.0 (Meteorological Quality Platform)",
                "Accept": "application/json",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status_code = response.getcode()
                body = response.read().decode("utf-8")
                try:
                    data = json.loads(body)
                    return status_code, data
                except json.JSONDecodeError as jde:
                    raise ValueError(f"Malformed JSON: {str(jde)}") from jde
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_body)
            except Exception:
                err_json = {"error": True, "reason": err_body or he.reason}
            return he.code, err_json

    def fetch_station_observation(
        self,
        station_id: str,
        latitude: float,
        longitude: float,
        elevation: Optional[float] = None,
        station_name: Optional[str] = None,
    ) -> Optional[WeatherObservation]:
        """Synchronously fetch, normalize, and qualify an observation for a given station."""
        if not self.is_connected:
            self.connect()

        params = self.build_query_params(latitude, longitude)
        query_str = urllib.parse.urlencode(params)
        url = f"{self.base_url}/forecast?{query_str}"
        safe_url = self._sanitize_url_for_logging(url)

        retrieval_ts = datetime.now(timezone.utc)
        t_start = time.perf_counter()

        last_exception: Optional[Exception] = None
        for attempt in range(self.retry_limit + 1):
            try:
                status_code, data = self._execute_http_get(url, timeout=self.timeout_seconds)
                latency_ms = (time.perf_counter() - t_start) * 1000.0

                # 1. Handle HTTP Status Codes
                if status_code == 200:
                    try:
                        observations = self.adapter.normalize(
                            raw_payload=data,
                            station_id=station_id,
                            station_name=station_name,
                            retrieval_timestamp=retrieval_ts,
                            pressure_semantics=self.pressure_semantics,
                        )
                    except Exception as norm_err:
                        self.health.record_failure(
                            error_msg=f"Normalization failed for {station_id}: {str(norm_err)}",
                            is_malformed=True,
                            timestamp=retrieval_ts,
                        )
                        return None

                    if not observations:
                        self.health.record_failure(
                            error_msg=f"Empty observation list returned for {station_id}",
                            timestamp=retrieval_ts,
                        )
                        return None

                    obs = observations[0]
                    if obs.elevation is None and elevation is not None:
                        obs = obs.model_copy(update={"elevation": elevation})

                    # Evaluate Quality Gate
                    gate_res = LiveSourceQualificationGate.evaluate(
                        obs=obs,
                        pressure_semantics=self.pressure_semantics,
                        expected_station_id=station_id,
                    )
                    if not gate_res.is_qualified:
                        reasons_str = "; ".join(gate_res.reasons)
                        logger.warning("Observation for station %s failed qualification gate: %s", station_id, reasons_str)
                        self.health.record_failure(
                            error_msg=f"Quality gate rejected observation: {reasons_str}",
                            timestamp=retrieval_ts,
                        )
                        return None

                    self.health.record_success(latency_ms=latency_ms, timestamp=retrieval_ts)
                    return obs

                elif status_code in (401, 403):
                    self.health.record_failure(
                        error_msg=f"Authentication failed (HTTP {status_code}) for {safe_url}",
                        auth_failed=True,
                        timestamp=retrieval_ts,
                    )
                    logger.error("Live source authentication error (HTTP %d) on %s", status_code, safe_url)
                    return None  # Permanent error, do not retry

                elif status_code == 429:
                    self.health.rate_limit_remaining = 0
                    self.health.record_failure(
                        error_msg=f"Rate limit exceeded (HTTP 429) on {safe_url}",
                        timestamp=retrieval_ts,
                    )
                    logger.warning("Live source rate limit hit (HTTP 429) on %s", safe_url)
                    return None

                else:
                    err_msg = f"HTTP {status_code} from {safe_url}"
                    if attempt < self.retry_limit:
                        backoff = self.retry_backoff_base_seconds * (2 ** attempt)
                        logger.warning("Attempt %d/%d failed with %s; retrying in %.2fs", attempt + 1, self.retry_limit + 1, err_msg, backoff)
                        time.sleep(backoff)
                        continue
                    else:
                        self.health.record_failure(error_msg=err_msg, timestamp=retrieval_ts)
                        return None

            except TimeoutError as te:
                last_exception = te
                if attempt < self.retry_limit:
                    backoff = self.retry_backoff_base_seconds * (2 ** attempt)
                    logger.warning("Timeout fetching %s (attempt %d/%d); retrying in %.2fs", station_id, attempt + 1, self.retry_limit + 1, backoff)
                    time.sleep(backoff)
                else:
                    self.health.record_failure(
                        error_msg=f"Request timeout for {station_id} after {self.retry_limit + 1} attempts",
                        timestamp=retrieval_ts,
                    )
                    return None

            except Exception as e:
                last_exception = e
                is_malformed = "Malformed JSON" in str(e)
                if is_malformed:
                    self.health.record_failure(
                        error_msg=f"Malformed JSON from {safe_url}: {str(e)}",
                        is_malformed=True,
                        timestamp=retrieval_ts,
                    )
                    return None

                if attempt < self.retry_limit:
                    backoff = self.retry_backoff_base_seconds * (2 ** attempt)
                    logger.warning("Network error fetching %s (%s); retrying in %.2fs", station_id, str(e), backoff)
                    time.sleep(backoff)
                else:
                    self.health.record_failure(
                        error_msg=f"Network exception for {station_id}: {str(e)}",
                        timestamp=retrieval_ts,
                    )
                    return None

        if last_exception:
            self.health.record_failure(
                error_msg=f"Exhausted retries for {station_id}: {str(last_exception)}",
                timestamp=retrieval_ts,
            )
        return None

    async def async_fetch_station_observation(
        self,
        station_id: str,
        latitude: float,
        longitude: float,
        elevation: Optional[float] = None,
        station_name: Optional[str] = None,
    ) -> Optional[WeatherObservation]:
        """Asynchronously fetch, normalize, and qualify an observation in an executor thread."""
        return await asyncio.to_thread(
            self.fetch_station_observation,
            station_id=station_id,
            latitude=latitude,
            longitude=longitude,
            elevation=elevation,
            station_name=station_name,
        )

    def fetch_observations(self) -> Generator[WeatherObservation, None, None]:
        """Poll default configured stations synchronously and yield normalized observations."""
        from ml.spatial.topology import SpatialNetworkTopology
        from backend.app.api.v1.deps import get_default_topology

        topo = get_default_topology()
        for station_id, node in topo.stations.items():
            obs = self.fetch_station_observation(
                station_id=station_id,
                latitude=node.latitude,
                longitude=node.longitude,
                elevation=node.elevation_m,
                station_name=node.name,
            )
            if obs is not None:
                yield obs


# Backward-compatible alias
WeatherAPIConnector = OpenMeteoLiveConnector
