"""Integration tests for Unified Data Source Control Plane and RunContext API."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.run_context import DataSourceType, RunMode


@pytest.fixture
def client():
    return TestClient(app)


def test_get_active_run_context(client):
    """Verify GET /api/v1/runtime/context returns canonical RunContext."""
    response = client.get("/api/v1/runtime/context")
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert "source_type" in data
    assert "mode" in data
    assert "status" in data


def test_list_providers(client):
    """Verify GET /api/v1/runtime/providers lists all data source providers."""
    response = client.get("/api/v1/runtime/providers")
    assert response.status_code == 200
    providers = response.json()
    assert len(providers) >= 4
    provider_types = [p["source_type"] for p in providers]
    assert "SYNTHETIC_VALIDATION" in provider_types
    assert "HISTORICAL_CSV" in provider_types
    assert "OPEN_METEO" in provider_types
    assert "IMD_AWS" in provider_types


def test_source_selection_flow(client):
    """Verify POST /api/v1/runtime/source/select switches data source and generates fresh run_id."""
    payload = {
        "source_type": "OPEN_METEO",
        "mode": "LIVE_MONITORING"
    }
    response = client.post("/api/v1/runtime/source/select", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["source_type"] == "OPEN_METEO"
    assert data["mode"] == "LIVE_MONITORING"
    assert data["run_id"].startswith("RUN-")


def test_unconfigured_source_rejection(client):
    """Verify attempting to select an unconfigured source like IMD AWS is rejected with 400."""
    payload = {
        "source_type": "IMD_AWS",
        "mode": "LIVE_MONITORING"
    }
    response = client.post("/api/v1/runtime/source/select", json=payload)
    assert response.status_code == 400
    assert "COMING SOON" in response.json()["detail"]


def test_run_controls(client):
    """Verify starting, pausing, and resetting run status."""
    res_start = client.post("/api/v1/runtime/run/start")
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "RUNNING"

    res_pause = client.post("/api/v1/runtime/run/pause")
    assert res_pause.status_code == 200
    assert res_pause.json()["status"] == "PAUSED"

    res_reset = client.post("/api/v1/runtime/run/reset")
    assert res_reset.status_code == 200
    assert res_reset.json()["status"] == "IDLE"


def test_run_history_audit(client):
    """Verify GET /api/v1/runtime/history returns audit log."""
    response = client.get("/api/v1/runtime/history")
    assert response.status_code == 200
    history = response.json()
    assert isinstance(history, list)
    assert len(history) >= 1
