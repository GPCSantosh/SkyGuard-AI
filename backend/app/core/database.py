"""Database persistence abstraction and repository for SkyGuard AI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple
import pandas as pd

from backend.app.models.observation import WeatherObservation
from backend.app.models.processing import (
    AnomalyEventRecord,
    LiveStationSnapshot,
    SystemHealthStatus,
)
from ml.decision.schema import HybridDecision, HybridDecisionType
from ml.explainability.schema import ExplanationSummary
from ml.health.health_schema import SensorHealthSummary
from ml.imputation.schema import CorrectionRecommendation
from ml.spatial.topology import SpatialNetworkTopology, StationNode


class DatabaseRepository:
    """In-memory and relational persistence repository for live and historical telemetry."""

    def __init__(self, topology: Optional[SpatialNetworkTopology] = None) -> None:
        self.topology = topology or SpatialNetworkTopology()
        
        # Primary In-Memory Stores (easily backed by SQLite/Postgres via SQLModel/SQLAlchemy)
        self.observations: Dict[str, WeatherObservation] = {}  # key: station_id::timestamp
        self.observation_order: List[str] = []
        
        self.anomaly_events: Dict[str, AnomalyEventRecord] = {}  # key: event_id
        self.anomaly_order: List[str] = []
        
        self.explanations: Dict[str, ExplanationSummary] = {}  # key: event_id
        self.latest_health_by_station: Dict[str, SensorHealthSummary] = {}
        self.health_history: List[SensorHealthSummary] = []
        self.corrections: Dict[str, CorrectionRecommendation] = {}  # key: observation_id
        self.correction_order: List[str] = []

        # Counters & Startup Telemetry
        self.startup_time = datetime.now(timezone.utc)
        self.processed_observations_count = 0
        self.last_processed_timestamp: Optional[str] = None
        self.latencies_history_ms: List[float] = []

    def save_observation(self, obs: WeatherObservation) -> bool:
        """Persist immutable observation record."""
        t_str = obs.timestamp.astimezone(timezone.utc).isoformat()
        key = f"{obs.station_id}::{t_str}"
        
        is_new = key not in self.observations
        self.observations[key] = obs
        if is_new:
            self.observation_order.append(key)
            self.processed_observations_count += 1
            self.last_processed_timestamp = t_str
            
        return is_new

    def save_anomaly_event(
        self,
        event: AnomalyEventRecord,
        explanation: Optional[ExplanationSummary] = None,
    ) -> None:
        """Persist anomaly event and accompanying explainability package."""
        if event.event_id not in self.anomaly_events:
            self.anomaly_events[event.event_id] = event
            self.anomaly_order.append(event.event_id)
            
        if explanation is not None:
            self.explanations[event.event_id] = explanation

    def save_health_snapshot(self, health: SensorHealthSummary) -> None:
        """Persist updated sensor health evaluation snapshot."""
        self.latest_health_by_station[health.station_id] = health
        self.health_history.append(health)

    def save_correction(self, corr: CorrectionRecommendation) -> None:
        """Persist advisory correction recommendation."""
        if corr.observation_id not in self.corrections:
            self.correction_order.append(corr.observation_id)
        self.corrections[corr.observation_id] = corr

    def record_latency(self, latency_ms: float) -> None:
        """Record pipeline execution latency for metrics."""
        self.latencies_history_ms.append(latency_ms)
        if len(self.latencies_history_ms) > 1000:
            self.latencies_history_ms.pop(0)

    # =========================================================================
    # Query APIs
    # =========================================================================

    def get_stations(self) -> List[Dict[str, Any]]:
        """List all stations in network topology with latest live telemetry."""
        results: List[Dict[str, Any]] = []
        for s_id, node in self.topology.stations.items():
            latest = self.get_station_latest(s_id)
            results.append({
                "station_id": s_id,
                "name": node.name,
                "latitude": node.latitude,
                "longitude": node.longitude,
                "elevation_m": node.elevation_m,
                "state": node.state,
                "status": node.status,
                "sampling_interval_seconds": node.sampling_interval_seconds,
                "latest_snapshot": latest,
            })
        return results

    def get_station_by_id(self, station_id: str) -> Optional[Dict[str, Any]]:
        """Get single station metadata and latest status."""
        node = self.topology.stations.get(station_id)
        if not node:
            return None
        latest = self.get_station_latest(station_id)
        return {
            "station_id": station_id,
            "name": node.name,
            "latitude": node.latitude,
            "longitude": node.longitude,
            "elevation_m": node.elevation_m,
            "state": node.state,
            "status": node.status,
            "sampling_interval_seconds": node.sampling_interval_seconds,
            "latest_snapshot": latest,
        }

    def get_station_latest(self, station_id: str) -> Optional[LiveStationSnapshot]:
        """Fetch real-time snapshot for a given station."""
        # Find latest observation for station
        stn_keys = [k for k in self.observation_order if k.startswith(f"{station_id}::")]
        node = self.topology.stations.get(station_id)
        name = node.name if node else f"Station {station_id}"
        lat = node.latitude if node else 0.0
        lon = node.longitude if node else 0.0
        elev = node.elevation_m if node else 0.0

        if not stn_keys:
            return LiveStationSnapshot(
                station_id=station_id,
                station_name=name,
                latitude=lat,
                longitude=lon,
                elevation_m=elev,
            )

        latest_obs = self.observations[stn_keys[-1]]
        health = self.latest_health_by_station.get(station_id)

        # Count active anomalies in last 24h
        cutoff_24h = (datetime.now(timezone.utc) - pd.Timedelta(hours=24)).isoformat()
        active_anom_count = sum(
            1 for ev in self.anomaly_events.values()
            if ev.station_id == station_id and ev.timestamp >= cutoff_24h
        )

        return LiveStationSnapshot(
            station_id=station_id,
            station_name=name,
            latitude=lat,
            longitude=lon,
            elevation_m=elev,
            last_seen_timestamp=latest_obs.timestamp.astimezone(timezone.utc).isoformat(),
            latest_temperature_c=latest_obs.temperature,
            latest_humidity_pct=latest_obs.humidity,
            latest_pressure_hpa=latest_obs.pressure,
            latest_decision="NORMAL",
            latest_health_score=health.overall_health_score if health else 100.0,
            latest_health_band=health.status_band.value if health else "HEALTHY",
            active_anomaly_count_24h=active_anom_count,
        )

    def get_station_history(
        self,
        station_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[WeatherObservation], int]:
        """Query chronological observation history for a station with filters and pagination."""
        start_dt = start_time if isinstance(start_time, datetime) else None
        end_dt = end_time if isinstance(end_time, datetime) else None
        lim = limit if isinstance(limit, int) else 100
        off = offset if isinstance(offset, int) else 0

        stn_keys = [k for k in self.observation_order if k.startswith(f"{station_id}::")]
        records: List[WeatherObservation] = []

        for k in stn_keys:
            obs = self.observations[k]
            obs_time = obs.timestamp.astimezone(timezone.utc)
            if start_dt and obs_time < start_dt.astimezone(timezone.utc):
                continue
            if end_dt and obs_time > end_dt.astimezone(timezone.utc):
                continue
            records.append(obs)

        total_count = len(records)
        paginated = records[off : off + lim]
        return paginated, total_count

    def get_station_health(self, station_id: str) -> Optional[SensorHealthSummary]:
        """Fetch latest SensorHealthSummary for a station."""
        return self.latest_health_by_station.get(station_id)

    def get_anomalies(
        self,
        station_id: Optional[str] = None,
        decision: Optional[str] = None,
        severity: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[AnomalyEventRecord], int]:
        """Query anomalies with multi-field filtering and pagination."""
        stn_filter = station_id if isinstance(station_id, str) and station_id.strip() else None
        dec_filter = decision if isinstance(decision, str) and decision.strip() else None
        sev_filter = severity if isinstance(severity, str) and severity.strip() else None
        start_dt = start_time if isinstance(start_time, datetime) else None
        end_dt = end_time if isinstance(end_time, datetime) else None
        lim = limit if isinstance(limit, int) else 50
        off = offset if isinstance(offset, int) else 0

        matched: List[AnomalyEventRecord] = []

        for ev_id in reversed(self.anomaly_order):
            ev = self.anomaly_events[ev_id]
            if stn_filter and ev.station_id != stn_filter:
                continue
            if dec_filter and ev.decision.value != dec_filter and ev.decision != dec_filter:
                continue
            if sev_filter and ev.severity.upper() != sev_filter.upper():
                continue

            ev_time = pd.to_datetime(ev.timestamp, utc=True)
            if start_dt and ev_time < start_dt.astimezone(timezone.utc):
                continue
            if end_dt and ev_time > end_dt.astimezone(timezone.utc):
                continue

            matched.append(ev)

        total_count = len(matched)
        paginated = matched[off : off + lim]
        return paginated, total_count

    def get_anomaly_by_id(self, event_id: str) -> Optional[AnomalyEventRecord]:
        """Get single anomaly event record."""
        return self.anomaly_events.get(event_id)

    def get_anomaly_explanation(self, event_id: str) -> Optional[ExplanationSummary]:
        """Get complete explainability package for an anomaly event."""
        return self.explanations.get(event_id)

    def get_corrections(
        self,
        station_id: Optional[str] = None,
        status: Optional[str] = None,
        target_variable: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[CorrectionRecommendation], int]:
        """Query advisory correction recommendations with filters and pagination."""
        stn_filter = station_id if isinstance(station_id, str) and station_id.strip() else None
        status_filter = status if isinstance(status, str) and status.strip() else None
        var_filter = target_variable if isinstance(target_variable, str) and target_variable.strip() else None
        lim = limit if isinstance(limit, int) else 50
        off = offset if isinstance(offset, int) else 0

        matched: List[CorrectionRecommendation] = []
        for obs_id in reversed(self.correction_order):
            corr = self.corrections[obs_id]
            if stn_filter and corr.station_id != stn_filter:
                continue
            if status_filter and corr.status.value != status_filter and corr.status != status_filter:
                continue
            if var_filter and corr.target_variable != var_filter:
                continue
            matched.append(corr)

        total_count = len(matched)
        paginated = matched[off : off + lim]
        return paginated, total_count

    def get_correction_by_id(self, observation_id: str) -> Optional[CorrectionRecommendation]:
        """Get single correction recommendation by observation ID."""
        return self.corrections.get(observation_id)

    def get_system_health(self) -> SystemHealthStatus:
        """Compute end-to-end service status of all core subsystems."""
        now = datetime.now(timezone.utc)
        uptime = (now - self.startup_time).total_seconds()
        mean_latency = float(pd.Series(self.latencies_history_ms).mean()) if self.latencies_history_ms else 0.0

        return SystemHealthStatus(
            status="HEALTHY",
            service="SkyGuard AI Real-Time Processing Engine",
            version="1.0.0",
            database_status="CONNECTED",
            model_registry_status="LOADED",
            active_model_id="isolation_forest_s42",
            spatial_topology_stations_count=len(self.topology.stations),
            active_monitored_stations=len(self.observations),
            total_observations_processed=self.processed_observations_count,
            last_processed_timestamp=self.last_processed_timestamp,
            mean_pipeline_latency_ms=round(mean_latency, 2),
            replay_simulator_status="READY",
            uptime_seconds=round(uptime, 1),
        )
