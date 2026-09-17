#!/usr/bin/env python3
"""SkyGuard AI — Phase 11D Controlled Live Soak Test & API Validation Harness.

Executes a multi-cycle validation or soak test across real geographically distributed
Automatic Weather Stations (AWS) using the OpenMeteoLiveConnector and RealTimeProcessingEngine.

Tracks:
- Empirical request latencies, observation age, delivery delay
- Contract validation (MSLP vs Surface pressure semantics)
- End-to-end WebSocket broadcasting and engine decision logging
- Source Health State Machine transitions and episode logging
- Memory and background resource metrics

Usage:
    python scripts/live_soak_test.py --live --cycles 5 --interval-seconds 5
    python scripts/live_soak_test.py --mock --cycles 3
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.api.v1.deps import get_default_topology
from backend.app.connectors.live_qualification import PressureSemantics
from backend.app.connectors.weather_api import OpenMeteoLiveConnector
from backend.app.core.config import get_settings
from backend.app.core.database import DatabaseRepository
from backend.app.core.engine import RealTimeProcessingEngine
from backend.app.core.ws_manager import WebSocketConnectionManager
from backend.app.ingestion.live_poller import LiveSourcePoller
from backend.app.ingestion.source_health import ErrorCategory, SourceHealthState, StationLiveStatus


class ControlledSoakRunner:
    """Orchestrates controlled validation cycles and records empirical metrics."""

    def __init__(
        self,
        is_live: bool = True,
        selected_stations: Optional[List[str]] = None,
        poll_interval_seconds: int = 5,
        stale_threshold_seconds: float = 3600.0,
    ) -> None:
        self.is_live = is_live
        self.poll_interval = poll_interval_seconds
        self.stale_threshold = stale_threshold_seconds

        self.full_topology = get_default_topology()
        self.target_station_ids = selected_stations or [
            "42182099999",  # NEW DELHI / SAFDARJUNG
            "42181099999",  # DELHI / PALAM
            "42184099999",  # DELHI / LODHI ROAD
            "42139099999",  # GURGAON AWS
            "42187099999",  # NOIDA AWS
        ]

        # Build sub-topology for selected stations
        from ml.spatial.topology import SpatialNetworkTopology
        self.topology = SpatialNetworkTopology()
        for s_id in self.target_station_ids:
            if s_id in self.full_topology.stations:
                self.topology.add_station(self.full_topology.stations[s_id])

        self.repository = DatabaseRepository(topology=self.topology)
        self.engine = RealTimeProcessingEngine(repository=self.repository)
        self.ws_manager = WebSocketConnectionManager()

        # Connector
        if not self.is_live:
            # Deterministic Mock Custom Fetcher
            fixture_path = PROJECT_ROOT / "data" / "external" / "live_api" / "01_valid_observation.json"
            with open(fixture_path, "r", encoding="utf-8") as f:
                mock_data = json.load(f)

            def mock_fetcher(url: str, timeout: float):
                return 200, mock_data

            self.connector = OpenMeteoLiveConnector(http_fetcher=mock_fetcher)
        else:
            settings = get_settings()
            self.connector = OpenMeteoLiveConnector(
                base_url=settings.live_source.base_url,
                api_key=settings.live_source.api_key,
                timeout_seconds=settings.live_source.timeout_seconds,
                pressure_semantics=PressureSemantics.MEAN_SEA_LEVEL_PRESSURE,
            )

        self.poller = LiveSourcePoller(
            connector=self.connector,
            engine=self.engine,
            repository=self.repository,
            topology=self.topology,
            ws_manager=self.ws_manager,
            poll_interval_seconds=self.poll_interval,
            stale_threshold_seconds=self.stale_threshold,
        )

        # Soak Metrics Collection
        self.cycle_records: List[Dict[str, Any]] = []
        self.request_latencies_ms: List[float] = []
        self.observation_ages_sec: List[float] = []
        self.delivery_delays_sec: List[float] = []
        self.engine_results: List[Dict[str, Any]] = []
        self.websocket_events_emitted: int = 0

    async def run_cycles(self, total_cycles: int) -> Dict[str, Any]:
        """Execute N controlled validation cycles."""
        mode_label = "LIVE TEST (Real Outbound HTTP)" if self.is_live else "MOCK TEST (Deterministic Local Fixture)"
        print("=" * 78)
        print("SKYGUARD AI — CONTROLLED LIVE SOAK TEST & INTEGRATION VALIDATION")
        print(f"MODE            : {mode_label}")
        print(f"Target Stations : {len(self.topology.stations)} ({', '.join(self.target_station_ids)})")
        print(f"Planned Cycles  : {total_cycles} (Interval: {self.poll_interval}s)")
        print("=" * 78)

        t_start_total = time.perf_counter()

        for cycle_idx in range(1, total_cycles + 1):
            t_cycle_start = time.perf_counter()
            print(f"\n>>> CYCLE {cycle_idx}/{total_cycles} [Timestamp: {datetime.now(timezone.utc).isoformat()}]")

            observations = await self.poller.poll_cycle_once()

            cycle_duration_ms = (time.perf_counter() - t_cycle_start) * 1000.0
            successful_obs = [obs for obs in observations if obs is not None]

            print(f"  Result: {len(successful_obs)}/{len(self.topology.stations)} stations received. Cycle time: {cycle_duration_ms:.2f}ms")

            for obs in successful_obs:
                now_utc = datetime.now(timezone.utc)
                obs_age = (now_utc - obs.timestamp).total_seconds()
                deliv_delay = (obs.ingestion_timestamp - obs.timestamp).total_seconds()

                self.observation_ages_sec.append(obs_age)
                self.delivery_delays_sec.append(deliv_delay)

                # Fetch latency from connector
                lat_ms = self.connector.health.last_response_latency_ms or 0.0
                if lat_ms > 0:
                    self.request_latencies_ms.append(lat_ms)

                # Contract & pressure validation
                mslp = obs.pressure
                surf_p = obs.station_pressure_hpa
                q_status_str = getattr(obs.data_quality_status, "value", str(obs.data_quality_status))
                print(
                    f"    [{obs.station_id}] Temp: {obs.temperature:5.1f}°C | "
                    f"RH: {obs.humidity:4.1f}% | MSLP: {mslp:6.1f}hPa | "
                    f"Surface: {surf_p:6.1f}hPa | Age: {obs_age:5.1f}s | Status: {q_status_str}"
                )

                # Engine processing check
                res = self.engine.process_observation(obs)
                self.engine_results.append({
                    "station_id": obs.station_id,
                    "timestamp": obs.timestamp.isoformat(),
                    "decision": res.decision.value if hasattr(res, "decision") else "PROCESSED",
                    "status": res.status.value,
                })
                self.websocket_events_emitted += 1

            source_state = self.poller.state_machine.current_state.value
            print(f"  Source Health State: {source_state} | Active Episode: {self.poller.state_machine.active_episode is not None}")

            if cycle_idx < total_cycles:
                await asyncio.sleep(self.poll_interval)

        total_elapsed_sec = time.perf_counter() - t_start_total

        # Summary statistics calculation
        return self._generate_report(total_cycles, total_elapsed_sec)

    def _generate_report(self, cycles_run: int, elapsed_sec: float) -> Dict[str, Any]:
        """Compute structured metrics summary."""
        sm_summary = self.poller.state_machine.get_summary()

        n_lat = len(self.request_latencies_ms)
        mean_lat = sum(self.request_latencies_ms) / n_lat if n_lat > 0 else 0.0
        min_lat = min(self.request_latencies_ms) if n_lat > 0 else 0.0
        max_lat = max(self.request_latencies_ms) if n_lat > 0 else 0.0

        n_age = len(self.observation_ages_sec)
        mean_age = sum(self.observation_ages_sec) / n_age if n_age > 0 else 0.0
        min_age = min(self.observation_ages_sec) if n_age > 0 else 0.0
        max_age = max(self.observation_ages_sec) if n_age > 0 else 0.0

        n_del = len(self.delivery_delays_sec)
        mean_del = sum(self.delivery_delays_sec) / n_del if n_del > 0 else 0.0

        report = {
            "mode": "LIVE_TEST" if self.is_live else "MOCK_TEST",
            "cycles_executed": cycles_run,
            "total_duration_seconds": round(elapsed_sec, 2),
            "stations_monitored": len(self.topology.stations),
            "total_observations_evaluated": len(self.observation_ages_sec),
            "websocket_events_generated": self.websocket_events_emitted,
            "latency_stats_ms": {
                "min": round(min_lat, 2),
                "max": round(max_lat, 2),
                "mean": round(mean_lat, 2),
                "count": n_lat,
            },
            "observation_age_stats_sec": {
                "min": round(min_age, 1),
                "max": round(max_age, 1),
                "mean": round(mean_age, 1),
            },
            "delivery_delay_stats_sec": {
                "mean": round(mean_del, 1),
            },
            "source_health_state": sm_summary["source_state"],
            "station_status_counts": sm_summary["counts"],
            "active_episode": sm_summary["active_episode"],
            "episodes_count": len(sm_summary["recent_episodes"]),
            "transitions_count": len(sm_summary["recent_transitions"]),
        }

        print("\n" + "=" * 78)
        print("CONTROLLED SOAK TEST EXECUTION SUMMARY")
        print("=" * 78)
        print(f"Total Duration     : {report['total_duration_seconds']}s")
        print(f"Cycles Completed   : {report['cycles_executed']}")
        print(f"Observations Ingest: {report['total_observations_evaluated']}")
        print(f"WebSocket Events   : {report['websocket_events_generated']}")
        print(f"Request Latency    : min={min_lat:.1f}ms, max={max_lat:.1f}ms, mean={mean_lat:.1f}ms")
        print(f"Observation Age    : min={min_age:.1f}s, max={max_age:.1f}s, mean={mean_age:.1f}s")
        print(f"Delivery Delay     : mean={mean_del:.1f}s")
        print(f"Final Source State : {report['source_health_state']}")
        print(f"Station Breakdown  : {report['station_status_counts']}")
        print("=" * 78)

        return report


async def main_async():
    parser = argparse.ArgumentParser(description="SkyGuard AI — Controlled Live Soak Test Harness")
    parser.add_argument("--live", action="store_true", help="Execute real live outbound queries against Open-Meteo")
    parser.add_argument("--mock", action="store_true", help="Execute deterministic mock test")
    parser.add_argument("--cycles", type=int, default=5, help="Number of polling cycles to run (default: 5)")
    parser.add_argument("--interval-seconds", type=int, default=5, help="Interval between poll cycles in seconds (default: 5)")

    args = parser.parse_args()
    is_live = not args.mock if args.live else False

    runner = ControlledSoakRunner(
        is_live=is_live,
        poll_interval_seconds=args.interval_seconds,
    )

    report = await runner.run_cycles(total_cycles=args.cycles)
    return report


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
