"""Unit tests for Phase 12B deployment endpoints, health probes, security gating, and logging."""

import logging
import os
import pytest
from fastapi import HTTPException, Response

from backend.app.api.v1.endpoints.health import health_live, health_ready
from backend.app.api.v1.endpoints.live import trigger_immediate_poll, verify_operational_access
from backend.app.core.config import get_settings
from backend.app.core.database import DatabaseRepository
from backend.app.core.engine import RealTimeProcessingEngine
from backend.app.core.logging import JsonLogFormatter, SensitiveDataFilter, setup_logging
from backend.app.db.session import DatabaseSessionManager
from backend.app.ingestion.live_poller import LiveSourcePoller
from backend.app.main import app
from ml.spatial.topology import SpatialNetworkTopology, StationNode


@pytest.fixture
def test_repo(tmp_path):
    db_file = tmp_path / "test_deploy.db"
    session_mgr = DatabaseSessionManager(f"sqlite:///{db_file}")
    topo = SpatialNetworkTopology()
    topo.add_station(StationNode(station_id="STN_001", name="Station 1", latitude=28.6, longitude=77.2, elevation_m=200.0))
    return DatabaseRepository(topology=topo, session_manager=session_mgr)


@pytest.mark.anyio
async def test_health_live_endpoint():
    """Verify GET /health/live returns process liveness metadata."""
    data = await health_live()
    assert data["status"] == "alive"
    assert data["service"] == "SkyGuard AI"
    assert "version" in data
    assert "uptime_seconds" in data
    assert "timestamp" in data


@pytest.mark.anyio
async def test_health_ready_endpoint(test_repo):
    """Verify GET /health/ready evaluates all core dependencies."""
    from unittest.mock import MagicMock
    engine = RealTimeProcessingEngine(repository=test_repo)
    mock_poller = MagicMock()
    mock_poller.get_status_summary.return_value = {
        "source_state": "HEALTHY",
        "provider": "open_meteo",
        "consecutive_failures": 0,
        "is_polling": True,
    }
    
    resp = Response()
    data = await health_ready(response=resp, repo=test_repo, engine=engine, poller=mock_poller)
    assert data["status"] in ("ready", "degraded")
    assert "dependencies" in data
    deps = data["dependencies"]
    assert "application" in deps
    assert "database" in deps
    assert "live_source" in deps
    assert "websocket" in deps
    assert deps["application"]["status"] == "healthy"
    assert deps["database"]["status"] == "healthy"


def test_poll_now_security_in_development(monkeypatch):
    """Verify verify_operational_access permits calls in development mode without credentials."""
    monkeypatch.setenv("SKYGUARD_ENV", "development")
    assert verify_operational_access(x_operational_key=None, authorization=None) is True


def test_poll_now_security_in_production(monkeypatch):
    """Verify verify_operational_access enforces operational authentication in production mode."""
    monkeypatch.setenv("SKYGUARD_ENV", "production")
    monkeypatch.setenv("SKYGUARD_OPERATIONAL_API_KEY", "prod-secret-key-12345")
    monkeypatch.setenv("SKYGUARD_ENABLE_PUBLIC_POLL_TRIGGER", "false")

    # 1. Anonymous request -> 401 Unauthorized
    with pytest.raises(HTTPException) as exc_anon:
        verify_operational_access(x_operational_key=None, authorization=None)
    assert exc_anon.value.status_code == 401

    # 2. Invalid key -> 401 Unauthorized
    with pytest.raises(HTTPException) as exc_bad:
        verify_operational_access(x_operational_key="wrong-key", authorization=None)
    assert exc_bad.value.status_code == 401

    # 3. Valid key via X-Operational-Key -> True
    assert verify_operational_access(x_operational_key="prod-secret-key-12345", authorization=None) is True

    # 4. Valid key via Bearer token -> True
    assert verify_operational_access(x_operational_key=None, authorization="Bearer prod-secret-key-12345") is True


def test_sensitive_data_log_filtering():
    """Verify SensitiveDataFilter redacts passwords, tokens, and credentials from log messages."""
    filter_inst = SensitiveDataFilter()
    
    # Test record with password in message
    record1 = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="Connecting with postgresql://user:my_secret_pw@localhost:5432/db and api_key=abc12345xyz",
        args=(), exc_info=None
    )
    filter_inst.filter(record1)
    assert "my_secret_pw" not in record1.msg
    assert "abc12345xyz" not in record1.msg
    assert "[REDACTED]" in record1.msg

    # Test record with Bearer token
    record2 = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="Authorization header provided: Bearer secret_jwt_token_9999",
        args=(), exc_info=None
    )
    filter_inst.filter(record2)
    assert "secret_jwt_token_9999" not in record2.msg
    assert "Bearer [REDACTED]" in record2.msg


def test_json_log_formatter():
    """Verify JsonLogFormatter produces valid structured JSON log line."""
    import json
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="test.service", level=logging.WARNING, pathname="test.py", lineno=42,
        msg="Test warning event occurred", args=(), exc_info=None
    )
    record.station_id = "STN_001"
    formatted = formatter.format(record)
    
    parsed = json.loads(formatted)
    assert parsed["level"] == "WARNING"
    assert parsed["service"] == "skyguard-backend"
    assert parsed["message"] == "Test warning event occurred"
    assert parsed["station_id"] == "STN_001"
    assert "timestamp" in parsed

