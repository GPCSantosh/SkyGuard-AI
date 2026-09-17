"""Unit tests for SkyGuard AI WebSocket event envelope and payload schemas."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from backend.app.models.events import (
    AnomalyCreatedPayload,
    AnomalyUpdatedPayload,
    CorrectionCreatedPayload,
    EventType,
    HealthUpdatedPayload,
    ObservationUpdatedPayload,
    StationStatusChangedPayload,
    SystemStatusChangedPayload,
    WebSocketEnvelope,
)


def test_envelope_creation_valid():
    """Verify standard WebSocketEnvelope construction and serialization."""
    obs_payload = ObservationUpdatedPayload(
        station_id="42182099999",
        station_name="NEW DELHI / SAFDARJUNG",
        timestamp="2026-09-17T00:00:00Z",
        temperature=28.5,
        humidity=65.0,
        pressure=1013.25,
        dew_point_c=21.0,
        data_quality_status="VALID",
        freshness_seconds=0,
    )

    envelope = WebSocketEnvelope.create(
        event_id="EVT-001",
        event_type=EventType.OBSERVATION_UPDATED,
        station_id="42182099999",
        timestamp="2026-09-17T00:00:00Z",
        payload=obs_payload,
    )

    assert envelope.event_id == "EVT-001"
    assert envelope.event_type == EventType.OBSERVATION_UPDATED
    assert envelope.station_id == "42182099999"
    assert envelope.schema_version == "1.0"
    assert envelope.payload["temperature"] == 28.5

    json_str = envelope.model_dump_json()
    assert "EVT-001" in json_str
    assert "observation.updated" in json_str


def test_anomaly_created_payload_schema():
    """Verify anomaly.created payload structure."""
    payload = AnomalyCreatedPayload(
        event_id="ANOM-20260917-820999-0001",
        station_id="42182099999",
        station_name="NEW DELHI / SAFDARJUNG",
        timestamp="2026-09-17T01:15:00Z",
        decision="PROBABLE_SENSOR_ANOMALY",
        severity="HIGH",
        summary="Unphysical temperature spike detected (+15°C delta).",
        reason_codes=["ISOLATION_FOREST_ANOMALY", "RATE_OF_CHANGE_EXCEEDED"],
        observed_values={"temperature_c": 45.0, "humidity": 30.0},
        recommended_values={"temperature_c": 30.0},
    )

    envelope = WebSocketEnvelope.create(
        event_id=payload.event_id,
        event_type=EventType.ANOMALY_CREATED,
        station_id=payload.station_id,
        payload=payload,
    )

    assert envelope.event_type == EventType.ANOMALY_CREATED
    assert envelope.payload["decision"] == "PROBABLE_SENSOR_ANOMALY"
    assert len(envelope.payload["reason_codes"]) == 2


def test_health_updated_payload_schema():
    """Verify health.updated payload structure."""
    payload = HealthUpdatedPayload(
        station_id="42182099999",
        timestamp="2026-09-17T02:00:00Z",
        health_index=88.5,
        health_status="HEALTHY",
        health_trend="STABLE",
        maintenance_recommendation="NO_ACTION",
        parameter_health={"temperature_c": 92.0, "humidity": 85.0},
        component_scores={"anomaly_health": 90.0, "spatial_consistency_health": 87.0},
    )

    envelope = WebSocketEnvelope.create(
        event_id="HLT-001",
        event_type=EventType.HEALTH_UPDATED,
        station_id="42182099999",
        payload=payload,
    )

    assert envelope.payload["health_index"] == 88.5
    assert envelope.payload["parameter_health"]["temperature_c"] == 92.0


def test_system_status_changed_payload():
    """Verify system.status_changed payload with nullable station_id."""
    payload = SystemStatusChangedPayload(
        component="websocket_stream",
        status="ONLINE",
        timestamp="2026-09-17T03:00:00Z",
        details={"active_clients": 5},
    )

    envelope = WebSocketEnvelope.create(
        event_id="SYS-001",
        event_type=EventType.SYSTEM_STATUS_CHANGED,
        station_id=None,
        payload=payload,
    )

    assert envelope.station_id is None
    assert envelope.payload["component"] == "websocket_stream"


def test_invalid_event_type_raises():
    """Verify that an invalid event_type string is rejected by Pydantic."""
    with pytest.raises(ValidationError):
        WebSocketEnvelope(
            event_id="ERR-01",
            event_type="invalid.type",  # Not a valid EventType enum
            timestamp="2026-09-17T00:00:00Z",
            payload={},
            schema_version="1.0",
        )
