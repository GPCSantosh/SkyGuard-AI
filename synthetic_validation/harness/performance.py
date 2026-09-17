"""Performance and Latency Profiler for Synthetic Validation Harness.

Measures controlled local latency distributions (P50, P95, P99) and processing throughput
across 1-station, 8-station, and 20-station network scales.
"""

from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any, Dict, List
import numpy as np

from backend.app.core.database import DatabaseRepository
from backend.app.core.engine import RealTimeProcessingEngine
from backend.app.core.ws_manager import WebSocketConnectionManager
from backend.app.db.session import DatabaseSessionManager
from ml.spatial.topology import SpatialNetworkTopology, StationNode
from synthetic_validation.harness.network_generator import (
    DEFAULT_SYNTHETIC_STATIONS,
    SyntheticNetworkGenerator,
)


class SyntheticPerformanceProfiler:
    """Profiles multi-scale processing latency and throughput under controlled load."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed

    def profile_network_scale(self, num_stations: int = 20, cycles: int = 12) -> Dict[str, Any]:
        """Profile pipeline performance for a specific station network scale."""
        configs = DEFAULT_SYNTHETIC_STATIONS[:num_stations]
        generator = SyntheticNetworkGenerator(station_configs=configs, seed=self.seed)
        topology = generator.create_topology()

        session_mgr = DatabaseSessionManager("sqlite:///:memory:")
        repo = DatabaseRepository(topology=topology, session_manager=session_mgr)
        ws_mgr = WebSocketConnectionManager()
        engine = RealTimeProcessingEngine(repository=repo, ws_manager=ws_mgr)

        # Generate test observation stream
        t_gen_start = time.perf_counter()
        observations = generator.generate_baseline_observations(
            duration_hours=(cycles * 5) / 60.0,
            interval_minutes=5,
        )
        gen_time_ms = (time.perf_counter() - t_gen_start) * 1000.0

        total_obs = len(observations)
        latencies_ms: List[float] = []

        t_process_start = time.perf_counter()
        for obs in observations:
            t0 = time.perf_counter()
            res = engine.process_observation(obs)
            lat = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(lat)

        total_duration_s = max(1e-5, time.perf_counter() - t_process_start)
        throughput_obs_sec = total_obs / total_duration_s

        p50 = float(np.percentile(latencies_ms, 50))
        p95 = float(np.percentile(latencies_ms, 95))
        p99 = float(np.percentile(latencies_ms, 99))
        mean_lat = float(np.mean(latencies_ms))

        return {
            "scale_stations": num_stations,
            "total_cycles": cycles,
            "total_observations": total_obs,
            "generation_time_ms": round(gen_time_ms, 2),
            "throughput_obs_per_sec": round(throughput_obs_sec, 2),
            "latency_p50_ms": round(p50, 2),
            "latency_p95_ms": round(p95, 2),
            "latency_p99_ms": round(p99, 2),
            "latency_mean_ms": round(mean_lat, 2),
            "label": "LOCAL SYNTHETIC VALIDATION",
        }

    def run_multi_scale_benchmark(self) -> Dict[str, Any]:
        """Run standard benchmark across 1, 8, and 20 stations."""
        scales = [1, 8, 20]
        results = {}
        for s in scales:
            results[f"{s}_station"] = self.profile_network_scale(num_stations=s, cycles=12)
        return results
