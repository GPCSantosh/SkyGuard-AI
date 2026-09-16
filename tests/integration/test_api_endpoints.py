"""Integration tests for FastAPI REST API endpoints using direct handler execution."""

from datetime import datetime, timezone
import pytest

from backend.app.api.v1.deps import get_engine, get_replay_engine, get_repository
from backend.app.api.v1.endpoints.anomalies import get_anomaly_detail, get_anomaly_explanation, list_anomalies
from backend.app.api.v1.endpoints.observations import process_observation_batch, process_single_observation
from backend.app.api.v1.endpoints.replay import get_replay_status, step_replay_simulation
from backend.app.api.v1.endpoints.stations import (
    get_station,
    get_station_health,
    get_station_history,
    get_station_latest,
    list_stations,
)
from backend.app.api.v1.endpoints.system import get_system_health
from backend.app.models.observation import ObservationSource, QualityStatus, WeatherObservation


@pytest.mark.anyio
async def test_root_and_system_health_endpoint():
    repo = get_repository()
    health_status = await get_system_health(repo=repo)
    assert health_status.status == "HEALTHY"
    assert health_status.database_status == "CONNECTED"
    assert health_status.uptime_seconds >= 0.0


@pytest.mark.anyio
async def test_stations_endpoints():
    repo = get_repository()
    stations_list = await list_stations(repo=repo)
    assert len(stations_list) > 0
    first_stn_id = stations_list[0]["station_id"]

    stn = await get_station(station_id=first_stn_id, repo=repo)
    assert stn["station_id"] == first_stn_id
    assert "name" in stn

    latest = await get_station_latest(station_id=first_stn_id, repo=repo)
    assert latest.station_id == first_stn_id


@pytest.mark.anyio
async def test_process_observation_endpoint():
    engine = get_engine()
    obs = WeatherObservation(
        station_id="42182099999",
        timestamp=datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc),
        latitude=28.585,
        longitude=77.206,
        temperature=25.0,
        humidity=50.0,
        pressure=1013.25,
        source=ObservationSource.SIMULATOR,
        data_quality_status=QualityStatus.VALID,
    )

    res = await process_single_observation(observation=obs, engine=engine)
    assert res.status.value == "PROCESSED"
    assert res.hybrid_decision is not None
    assert res.hybrid_decision.decision.value == "NORMAL"
    assert res.latency.total_pipeline_latency_ms > 0.0


@pytest.mark.anyio
async def test_station_history_and_latest_endpoints():
    engine = get_engine()
    repo = get_repository()
    
    obs = WeatherObservation(
        station_id="42182099999",
        timestamp=datetime(2026, 9, 17, 12, 5, 0, tzinfo=timezone.utc),
        latitude=28.585,
        longitude=77.206,
        temperature=26.5,
        humidity=55.0,
        pressure=1012.8,
        source=ObservationSource.SIMULATOR,
        data_quality_status=QualityStatus.VALID,
    )
    await process_single_observation(observation=obs, engine=engine)

    latest = await get_station_latest(station_id="42182099999", repo=repo)
    assert latest.latest_temperature_c == 26.5

    hist_resp = await get_station_history(station_id="42182099999", limit=10, offset=0, repo=repo)
    assert len(hist_resp.items) >= 1
    assert hist_resp.pagination.total_count >= 1


@pytest.mark.anyio
async def test_anomalies_and_explanation_endpoints():
    engine = get_engine()
    repo = get_repository()

    # Ingest a severe unphysical spike to trigger anomaly
    spike_obs = WeatherObservation(
        station_id="42182099999",
        timestamp=datetime(2026, 9, 17, 12, 10, 0, tzinfo=timezone.utc),
        latitude=28.585,
        longitude=77.206,
        temperature=58.0,  # Extreme localized heat spike (nominal was 26.5)
        humidity=10.0,
        pressure=1013.25,
        source=ObservationSource.SIMULATOR,
        data_quality_status=QualityStatus.VALID,
    )
    res_proc = await process_single_observation(observation=spike_obs, engine=engine)
    event_id = res_proc.event_id
    assert event_id is not None

    # Query anomalies list
    anom_list = await list_anomalies(station_id="42182099999", limit=50, offset=0, repo=repo)
    assert anom_list.pagination.total_count >= 1

    # Query specific anomaly detail
    detail = await get_anomaly_detail(event_id=event_id, repo=repo)
    assert detail.event_id == event_id

    # Query explanation
    exp = await get_anomaly_explanation(event_id=event_id, repo=repo)
    assert exp.summary != ""
    assert exp.evidence_hierarchy is not None


@pytest.mark.anyio
async def test_replay_endpoints():
    replay = get_replay_engine()
    status_dict = await get_replay_status(replay=replay)
    assert "is_running" in status_dict
    assert "total_queued_observations" in status_dict
