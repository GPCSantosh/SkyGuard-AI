"""Performance, Load, and Latency Benchmark for WebSocket Real-Time Streaming across 20 AWS Stations."""

from datetime import datetime, timezone
import time
import numpy as np
import pytest

from backend.app.core.database import DatabaseRepository
from backend.app.core.engine import RealTimeProcessingEngine
from backend.app.core.ws_manager import WebSocketConnectionManager
from backend.app.models.observation import ObservationSource, QualityStatus, WeatherObservation
from ml.spatial.topology import SpatialNetworkTopology, StationNode


@pytest.fixture
def network_20_stations():
    topo = SpatialNetworkTopology()
    for i in range(20):
        lat = 28.0 + (i // 5) * 0.4 + (i % 5) * 0.05
        lon = 76.5 + (i % 5) * 0.4
        s_id = f"AWS_STN_{i:03d}"
        topo.add_station(StationNode(
            station_id=s_id,
            name=f"Network AWS Station {i:03d}",
            latitude=lat,
            longitude=lon,
            elevation_m=200.0 + (i * 10),
        ))
    return topo


def test_20_station_websocket_throughput_and_latency(network_20_stations):
    """Verify WebSocket system stability, event throughput, latency SLA, and burst performance across 20 stations."""
    ws_manager = WebSocketConnectionManager()
    repo = DatabaseRepository(topology=network_20_stations)
    engine = RealTimeProcessingEngine(repository=repo, ws_manager=ws_manager)

    station_ids = list(network_20_stations.stations.keys())
    assert len(station_ids) == 20

    # Generate 12 cycles of 5-minute intervals = 240 observations
    observations = []
    base_ts = datetime(2026, 9, 17, 0, 0, 0, tzinfo=timezone.utc)

    for step in range(12):
        step_time = datetime.fromtimestamp(base_ts.timestamp() + step * 300, tz=timezone.utc)
        for idx, s_id in enumerate(station_ids):
            node = network_20_stations.stations[s_id]
            # Inject a spike at station 0, step 6
            is_spike = (idx == 0 and step == 6)
            temp = 55.0 if is_spike else (22.0 + 5.0 * np.sin(step * 0.2) + (idx % 3) * 0.5)

            obs = WeatherObservation(
                station_id=s_id,
                station_name=node.name,
                latitude=node.latitude,
                longitude=node.longitude,
                elevation=node.elevation_m,
                timestamp=step_time,
                temperature=round(float(temp), 2),
                dew_point_c=round(float(temp - 7.0), 2),
                humidity=60.0,
                pressure=1013.25,
                source=ObservationSource.SIMULATOR,
                data_quality_status=QualityStatus.VALID,
            )
            observations.append(obs)

    assert len(observations) == 240

    # Execute processing loop and measure performance
    t_start = time.perf_counter()
    pipeline_latencies_ms = []

    for obs in observations:
        res = engine.process_observation(obs)
        pipeline_latencies_ms.append(res.latency.total_pipeline_latency_ms)

    total_time_s = time.perf_counter() - t_start
    throughput = len(observations) / max(1e-5, total_time_s)

    # Profiling assertions
    p50 = float(np.percentile(pipeline_latencies_ms, 50))
    p95 = float(np.percentile(pipeline_latencies_ms, 95))
    p99 = float(np.percentile(pipeline_latencies_ms, 99))
    mean_lat = float(np.mean(pipeline_latencies_ms))

    assert mean_lat < 50.0
    assert p95 < 80.0
    assert throughput >= 30.0

    # Verify WebSocket metrics
    metrics = ws_manager.get_metrics()
    assert metrics["total_broadcasts"] >= 240  # Observation + Health + Anomaly events
    assert metrics["total_dropped_messages"] == 0

    # Burst test: 20 simultaneous observations
    burst_time = datetime.fromtimestamp(base_ts.timestamp() + 13 * 300, tz=timezone.utc)
    burst_obs = [
        WeatherObservation(
            station_id=s_id,
            timestamp=burst_time,
            latitude=network_20_stations.stations[s_id].latitude,
            longitude=network_20_stations.stations[s_id].longitude,
            temperature=28.0,
            humidity=55.0,
            pressure=1012.0,
        )
        for s_id in station_ids
    ]

    t_burst_start = time.perf_counter()
    burst_results = [engine.process_observation(o) for o in burst_obs]
    t_burst_total = time.perf_counter() - t_burst_start

    assert len(burst_results) == 20
    assert all(r.status.value == "PROCESSED" for r in burst_results)
    assert t_burst_total < 2.0
