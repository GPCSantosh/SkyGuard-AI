"""Integration tests for SkyGuard AI WebSocket stream endpoint and live processing."""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest

from backend.app.api.v1.deps import get_engine, get_replay_engine, get_repository
from backend.app.api.v1.endpoints.replay import step_replay_simulation
from backend.app.api.v1.endpoints.ws import websocket_stream_endpoint
from backend.app.core.ws_manager import get_ws_manager
from backend.app.models.events import EventType
from backend.app.models.observation import ObservationSource, QualityStatus, WeatherObservation


class FakeWebSocket:
    """Mock WebSocket client for testing streaming endpoints."""

    def __init__(self, incoming_messages=None):
        self.accepted = False
        self.sent_messages = []
        self._incoming = list(incoming_messages or [])

    async def accept(self):
        self.accepted = True

    async def send_text(self, text: str):
        self.sent_messages.append(text)

    async def receive_text(self) -> str:
        if self._incoming:
            return self._incoming.pop(0)
        # Raise standard disconnect when no more incoming frames
        from fastapi import WebSocketDisconnect
        raise WebSocketDisconnect(code=1000)


@pytest.mark.anyio
async def test_websocket_endpoint_welcome_and_ping_pong():
    """Verify endpoint accepts connection, transmits welcome envelope, and responds to heartbeat ping."""
    ping_payload = json.dumps({
        "event_type": "heartbeat.ping",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    fake_ws = FakeWebSocket(incoming_messages=[ping_payload])

    await websocket_stream_endpoint(fake_ws)

    assert fake_ws.accepted is True
    assert len(fake_ws.sent_messages) == 2

    # 1. First frame: Welcome / System status
    welcome_frame = json.loads(fake_ws.sent_messages[0])
    assert welcome_frame["event_type"] == EventType.SYSTEM_STATUS_CHANGED.value
    assert welcome_frame["schema_version"] == "1.0"
    assert welcome_frame["payload"]["status"] == "CONNECTED"

    # 2. Second frame: Heartbeat pong
    pong_frame = json.loads(fake_ws.sent_messages[1])
    assert pong_frame["event_type"] == EventType.HEARTBEAT_PONG.value
    assert pong_frame["schema_version"] == "1.0"
    assert "server_timestamp" in pong_frame["payload"]


@pytest.mark.anyio
async def test_websocket_stream_receives_observation_and_anomaly_events():
    """Verify that processing an observation publishes live WebSocket events to connected clients."""
    ws_manager = get_ws_manager()
    engine = get_engine()

    mock_client = AsyncMock()
    mock_client.sent_frames = []

    async def mock_send(text: str):
        mock_client.sent_frames.append(json.loads(text))

    mock_client.send_text.side_effect = mock_send
    await ws_manager.connect(mock_client)

    try:
        # Initial baseline observation
        base_obs = WeatherObservation(
            station_id="42182099999",
            station_name="NEW DELHI / SAFDARJUNG",
            latitude=28.585,
            longitude=77.206,
            elevation=216.0,
            timestamp=datetime(2026, 9, 17, 13, 0, 0, tzinfo=timezone.utc),
            temperature=25.0,
            humidity=50.0,
            pressure=1013.25,
            source=ObservationSource.SIMULATOR,
            data_quality_status=QualityStatus.VALID,
        )
        engine.process_observation(base_obs)

        # Extreme rapid heat spike 5 minutes later
        anom_obs = WeatherObservation(
            station_id="42182099999",
            station_name="NEW DELHI / SAFDARJUNG",
            latitude=28.585,
            longitude=77.206,
            elevation=216.0,
            timestamp=datetime(2026, 9, 17, 13, 5, 0, tzinfo=timezone.utc),
            temperature=58.5,  # extreme rate jump (+33.5°C in 5 min)
            humidity=10.0,
            pressure=1013.25,
            source=ObservationSource.SIMULATOR,
            data_quality_status=QualityStatus.VALID,
        )

        res = engine.process_observation(anom_obs)
        assert res.event_id is not None

        # Give async tasks a moment to deliver
        await asyncio.sleep(0.01)

        event_types = [f["event_type"] for f in mock_client.sent_frames]
        assert "observation.updated" in event_types
        assert "anomaly.created" in event_types
        assert "health.updated" in event_types

        # Verify anomaly event content
        anom_frame = next(
            f for f in mock_client.sent_frames
            if f["event_type"] == "anomaly.created" and f["event_id"] == res.event_id
        )
        assert anom_frame["event_id"] == res.event_id
        assert anom_frame["station_id"] == "42182099999"
        assert anom_frame["payload"]["decision"] in ("PROBABLE_SENSOR_ANOMALY", "UNCERTAIN")
    finally:
        ws_manager.disconnect(mock_client)


@pytest.mark.anyio
async def test_replay_stepping_publishes_websocket_events():
    """Verify that stepping the replay simulator publishes WebSocket events to connected clients."""
    ws_manager = get_ws_manager()
    engine = get_engine()
    replay = get_replay_engine()

    mock_client = AsyncMock()
    mock_client.sent_frames = []

    async def mock_send(text: str):
        mock_client.sent_frames.append(json.loads(text))

    mock_client.send_text.side_effect = mock_send
    await ws_manager.connect(mock_client)

    try:
        step_result = await step_replay_simulation(count=1, replay=replay, engine=engine)
        assert step_result["steps_executed"] >= 1

        await asyncio.sleep(0.01)
        event_types = [f["event_type"] for f in mock_client.sent_frames]
        assert "observation.updated" in event_types
    finally:
        ws_manager.disconnect(mock_client)
