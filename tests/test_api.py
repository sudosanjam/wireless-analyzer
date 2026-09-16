"""
Unit tests for FastAPI REST endpoints and web responses.
"""

from fastapi.testclient import TestClient
from application.config.settings import load_config
from application.web.server import SignalObserverServer


def test_api_endpoints(tmp_path):
    test_db = tmp_path / "test_api.db"
    config = load_config(overrides={
        "scanners": {"mock_mode": True, "scan_interval_seconds": 1.0},
        "storage": {"database_path": str(test_db)},
    })
    server = SignalObserverServer(config)
    client = TestClient(server.app)

    # 1. Main index template
    resp = client.get("/")
    assert resp.status_code == 200
    assert "SIGNAL // OBSERVER" in resp.text
    assert "radar-canvas" in resp.text

    # 2. Session API
    resp = client.get("/api/session")
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["status"] == "RUNNING"

    # 3. Contacts API
    resp = client.get("/api/contacts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # 4. Analytics API
    resp = client.get("/api/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert "rssi_stats" in data

    # 5. Diagnostics API
    resp = client.get("/api/diagnostics")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "table" in data

    # 6. Exports API
    resp = client.get("/api/export/csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]

    resp = client.get("/api/export/json")
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]

    resp = client.get("/api/export/debrief")
    assert resp.status_code == 200
    assert "text/markdown" in resp.headers["content-type"]
    assert "ENVIRONMENTAL SIGNAL OBSERVATION DEBRIEF" in resp.text
