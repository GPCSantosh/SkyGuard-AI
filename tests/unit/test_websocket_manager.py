"""Unit tests for WebSocketConnectionManager."""

import asyncio
from unittest.mock import AsyncMock
import pytest

from backend.app.core.ws_manager import WebSocketConnectionManager
from backend.app.models.events import EventType, ObservationUpdatedPayload, WebSocketEnvelope


@pytest.mark.anyio
async def test_manager_connect_and_disconnect():
    """Verify registration and unregistration of WebSocket client."""
    manager = WebSocketConnectionManager()
    assert manager.active_connections_count == 0

    mock_ws = AsyncMock()
    await manager.connect(mock_ws)
    mock_ws.accept.assert_awaited_once()
    assert manager.active_connections_count == 1

    manager.disconnect(mock_ws)
    assert manager.active_connections_count == 0


@pytest.mark.anyio
async def test_manager_broadcast_multiple_clients():
    """Verify concurrent broadcast to multiple connected clients."""
    manager = WebSocketConnectionManager()
    mock_ws1 = AsyncMock()
    mock_ws2 = AsyncMock()

    await manager.connect(mock_ws1)
    await manager.connect(mock_ws2)
    assert manager.active_connections_count == 2

    envelope = WebSocketEnvelope.create(
        event_id="EVT-100",
        event_type=EventType.OBSERVATION_UPDATED,
        station_id="42182099999",
        payload=ObservationUpdatedPayload(
            station_id="42182099999",
            timestamp="2026-09-17T00:00:00Z",
            temperature=25.0,
            data_quality_status="VALID",
        ),
    )

    delivered = await manager.broadcast(envelope)
    assert delivered == 2
    mock_ws1.send_text.assert_awaited_once()
    mock_ws2.send_text.assert_awaited_once()

    metrics = manager.get_metrics()
    assert metrics["active_clients"] == 2
    assert metrics["total_broadcasts"] == 1
    assert metrics["total_dropped_messages"] == 0


@pytest.mark.anyio
async def test_manager_broadcast_handles_dropped_client():
    """Verify that a failing client is safely removed without blocking other clients."""
    manager = WebSocketConnectionManager()
    mock_ws_good = AsyncMock()
    mock_ws_bad = AsyncMock()
    mock_ws_bad.send_text.side_effect = RuntimeError("Connection dropped")

    await manager.connect(mock_ws_good)
    await manager.connect(mock_ws_bad)
    assert manager.active_connections_count == 2

    envelope = WebSocketEnvelope.create(
        event_id="EVT-101",
        event_type=EventType.OBSERVATION_UPDATED,
        station_id="42182099999",
        payload={"temperature": 25.0},
    )

    delivered = await manager.broadcast(envelope)
    assert delivered == 1
    # Bad client should have been cleaned up
    assert manager.active_connections_count == 1
    assert manager.total_dropped_count == 1
