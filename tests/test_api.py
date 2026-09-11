"""
Tests for REST API Endpoints & Health Checks.
"""

from starlette.testclient import TestClient
from api.app import app


def test_health_endpoint():
    """Verify /health endpoint returns correct mode and invariants."""
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "HEALTHY"
        assert data["execution_mode"] == "PAPER_TRADING"
        assert data["live_trading_enabled"] is False
        assert data["lot_size"] == 65


def test_status_endpoint():
    """Verify /api/status endpoint returns financial and operational metrics."""
    with TestClient(app) as client:
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "kill_switch" in data
        assert "capital" in data
        assert "pnl" in data
        assert data["lot_size"] == 65


def test_arbitrage_scanner_endpoint():
    """Verify /api/arbitrage/opportunities endpoint tags capital feasibility."""
    with TestClient(app) as client:
        resp = client.get("/api/arbitrage/opportunities")
        assert resp.status_code == 200
        data = resp.json()
        assert "opportunities" in data
        assert "capital_infeasible_count" in data


def test_kill_switch_api():
    """Verify manual kill switch engagement and reset via API."""
    with TestClient(app) as client:
        # Engage
        res1 = client.post("/api/kill-switch", json={"action": "engage", "reason": "API Unit Test"})
        assert res1.status_code == 200
        assert res1.json()["status"]["is_engaged"] is True

        # Reset with wrong token should fail
        res2 = client.post("/api/kill-switch", json={"action": "reset", "token": "WRONG_TOKEN"})
        assert res2.status_code == 400

        # Reset with correct token should succeed
        res3 = client.post("/api/kill-switch", json={"action": "reset", "token": "CONFIRM_RESET"})
        assert res3.status_code == 200
        assert res3.json()["status"]["is_engaged"] is False


def test_ml_endpoints():
    """Verify /api/ml/status and /api/ml/retrain endpoints."""
    with TestClient(app) as client:
        # Check status
        resp = client.get("/api/ml/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "regime" in data
        assert "confidence_score" in data
        assert "expected_win_rate" in data
        assert data["statutory_hurdle_inr"] == 52.02

        # Trigger retrain step
        retrain = client.post("/api/ml/retrain")
        assert retrain.status_code == 200
        r_data = retrain.json()
        assert r_data["success"] is True
        assert "epoch" in r_data
