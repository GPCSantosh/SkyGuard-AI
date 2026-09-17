"""WebSocket Streaming Endpoint for SkyGuard AI Operations Center."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.core.ws_manager import get_ws_manager
from backend.app.models.events import EventType, SystemStatusChangedPayload, WebSocketEnvelope

logger = logging.getLogger("skyguard.websocket.endpoint")
router = APIRouter(tags=["WebSocket Stream"])


@router.websocket("/ws/stream")
@router.websocket("/stream")
async def websocket_stream_endpoint(websocket: WebSocket) -> None:
    """High-performance WebSocket endpoint streaming real-time AWS observations, anomalies, and health."""
    ws_manager = get_ws_manager()
    await ws_manager.connect(websocket)

    # Transmit initial connection welcome / system status envelope
    welcome_envelope = WebSocketEnvelope.create(
        event_id=f"SYS-CONN-{uuid.uuid4().hex[:8]}",
        event_type=EventType.SYSTEM_STATUS_CHANGED,
        payload=SystemStatusChangedPayload(
            component="websocket_stream",
            status="CONNECTED",
            timestamp=datetime.now(timezone.utc).isoformat(),
            details={
                "transport": "websocket",
                "schema_version": "1.0",
                "active_clients": ws_manager.active_connections_count,
            },
        ),
    )
    await ws_manager.send_personal(websocket, welcome_envelope)

    try:
        while True:
            # Receive client messages / heartbeats
            data_text = await websocket.receive_text()
            try:
                msg_data = json.loads(data_text)
                event_type = msg_data.get("event_type")

                # Handle client ping heartbeat
                if event_type in ("heartbeat.ping", "ping"):
                    pong_envelope = WebSocketEnvelope.create(
                        event_id=f"PONG-{uuid.uuid4().hex[:8]}",
                        event_type=EventType.HEARTBEAT_PONG,
                        payload={
                            "client_timestamp": msg_data.get("timestamp"),
                            "server_timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    await ws_manager.send_personal(websocket, pong_envelope)
            except json.JSONDecodeError:
                logger.warning("Received invalid non-JSON payload over WebSocket from client.")
            except Exception as exc:
                logger.warning("Error processing client WebSocket message: %s", exc)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("Unexpected WebSocket connection exception: %s", exc)
        ws_manager.disconnect(websocket)
