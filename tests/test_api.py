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


def test_global_macro_endpoints():
    """Verify /api/global-macro/status and /api/global-macro/scenario endpoints."""
    with TestClient(app) as client:
        # 1. Check status
        resp = client.get("/api/global-macro/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "macro" in data
        assert "fusion" in data
        assert "global_bias" in data["fusion"]
        assert "geopolitical_fear_index" in data["fusion"]
        assert "headlines" in data

        # 2. Trigger world scenario simulation
        sc_resp = client.post(
            "/api/global-macro/scenario",
            json={"scenario": "MIDDLE_EAST_WAR_CRISIS"}
        )
        assert sc_resp.status_code == 200
        sc_data = sc_resp.json()
        assert sc_data["success"] is True
        assert sc_data["global_bias"] in ["STRONG_BEARISH", "MODERATE_BEARISH"]
        assert sc_data["geopolitical_fear_index"] >= 0.70

        # 3. Test dataset endpoint
        ds_resp = client.get("/api/global-macro/dataset")
        assert ds_resp.status_code == 200
        ds_data = ds_resp.json()
        assert ds_data["count"] >= 10
        assert len(ds_data["samples"]) >= 10

        # 4. Test multimodal weight training endpoint
        tr_resp = client.post("/api/global-macro/train")
        assert tr_resp.status_code == 200
        tr_data = tr_resp.json()
        assert tr_data["success"] is True
        assert tr_data["directional_accuracy"] >= 0.75
        assert len(tr_data["macro_weights"]) == 5
        assert len(tr_data["news_weights"]) == 8

        # Reset to neutral
        client.post("/api/global-macro/scenario", json={"scenario": "NEUTRAL"})


def test_auto_trade_and_scheduler_endpoints():
    """Verify auto-trade, macro poller, and scheduler REST endpoints."""
    from global_macro.poller import live_macro_poller
    live_macro_poller.enable_mock_mode(True)

    with TestClient(app) as client:
        # 1. Auto-trade endpoints
        at_resp = client.get("/api/auto-trade/status")
        assert at_resp.status_code == 200
        at_data = at_resp.json()
        assert "is_enabled" in at_data
        assert "active_trades" in at_data

        t_resp = client.post("/api/auto-trade/toggle", json={"enabled": False})
        assert t_resp.status_code == 200
        assert t_resp.json()["is_enabled"] is False

        # 2. Live macro poller endpoints
        p_resp = client.post("/api/global-macro/poll")
        assert p_resp.status_code == 200
        p_data = p_resp.json()
        assert p_data["status"] == "SUCCESS"

        st_resp = client.get("/api/global-macro/poller-status")
        assert st_resp.status_code == 200
        assert st_resp.json()["poll_count"] >= 1

        # 3. Scheduler endpoints
        sch_resp = client.get("/api/scheduler/status")
        assert sch_resp.status_code == 200
        sch_data = sch_resp.json()
        assert "current_phase" in sch_data
        assert "is_trading_permitted" in sch_data

        adv_resp = client.post("/api/scheduler/advance", json={"phase": "MORNING_BREAKOUT"})
        assert adv_resp.status_code == 200
        adv_data = adv_resp.json()
        assert adv_data["success"] is True
        assert adv_data["status"]["current_phase"] == "MORNING_BREAKOUT"
        assert adv_data["status"]["is_trading_permitted"] is True
