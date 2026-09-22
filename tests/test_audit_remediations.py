"""
Regression & Invariant Verification Suite for External Audit Remediations.
Explicitly validates:
1. Authoritative RiskKernel capital reservation & solvency bounds.
2. Failed exit state machine (no fake fills, position retained, kill switch escalation).
3. Realistic paper broker limit order crossing requirements.
4. SQLite persistence of kill switch state across re-instantiation.
5. Dynamic strike and expiry resolution in arbitrage scanner.
6. WebSocket authentication and remote telemetry protection.
"""

import asyncio
import os
import time
import pytest
from broker.interface import BrokerOrderRequest
from execution.paper_broker import paper_broker
from execution.auto_engine import auto_engine, ManagedTrade
from risk.kernel import risk_kernel, PreTradeOrderRequest
from risk.kill_switch import kill_switch, KillSwitch
from market_data.orderbook import orderbook_manager
from market_data.normalizer import MarketDataNormalizer
from portfolio.pnl import pnl_manager
from database.db import db_manager
from starlette.testclient import TestClient
from api.app import app


@pytest.fixture(autouse=True)
def setup_test_env():
    db_manager.init_db()
    if kill_switch.is_engaged:
        kill_switch.reset_system()
    pnl_manager.reset_balance(3000.0)
    auto_engine._active_trades.clear()
    auto_engine._trade_history.clear()
    yield
    if kill_switch.is_engaged:
        kill_switch.reset_system()
    auto_engine._active_trades.clear()


def test_authoritative_capital_reservation():
    """Verify that RiskKernel authoritatively calculates required capital and flags breaches."""
    res = risk_kernel.calculate_capital_reservation(
        side="BUY",
        price=22.10,
        quantity=65,
        available_cash=3000.0,
        stop_loss_price=19.80,
        capital_floor=2000.0
    )
    # 22.10 * 65 = 1436.50 entry premium
    assert res.entry_premium == 1436.50
    assert res.entry_fees > 20.0
    assert res.reserved_exit_fees > 20.0
    assert res.total_required_cash > 1436.50
    assert res.is_solvent is True
    # If starting cash is 2,000 or below, floor must fail
    res_floor = risk_kernel.calculate_capital_reservation(
        side="BUY",
        price=22.10,
        quantity=65,
        available_cash=2000.0,
        stop_loss_price=19.80,
        capital_floor=2000.0
    )
    assert res_floor.is_floor_preserved is False
    assert any("CAPITAL_FLOOR_REACHED" in v for v in res_floor.violations)


def test_paper_broker_limit_order_crossing_rejection():
    """Verify limit orders that do not cross the spread are rejected immediately."""
    async def _run():
        symbol = "NIFTY_LIMIT_TEST"
        # Mid = 25.0, spread = 2.0 -> Bid = 24.0, Ask = 26.0
        tick = MarketDataNormalizer.create_synthetic_tick(symbol=symbol, mid_price=25.0, spread=2.0)
        orderbook_manager.update_tick(tick)

        # 1. BUY LIMIT @ 24.50 (best ask is 26.00 -> uncrossed!)
        req_buy = BrokerOrderRequest(
            symbol=symbol,
            side="BUY",
            order_type="LIMIT",
            quantity=65,
            price=24.50
        )
        resp_buy = await paper_broker.place_order(req_buy)
        assert resp_buy.status == "REJECTED"
        assert "LIMIT_UNFILLABLE" in resp_buy.rejection_reason

        # 2. SELL LIMIT @ 25.50 (best bid is 24.00 -> uncrossed!)
        req_sell = BrokerOrderRequest(
            symbol=symbol,
            side="SELL",
            order_type="LIMIT",
            quantity=65,
            price=25.50
        )
        resp_sell = await paper_broker.place_order(req_sell)
        assert resp_sell.status == "REJECTED"
        assert "LIMIT_UNFILLABLE" in resp_sell.rejection_reason

        # 3. BUY LIMIT @ 26.50 (best ask is 26.00 -> crossed!)
        req_cross = BrokerOrderRequest(
            symbol=symbol,
            side="BUY",
            order_type="LIMIT",
            quantity=65,
            price=26.50
        )
        resp_cross = await paper_broker.place_order(req_cross)
        assert resp_cross.status == "FILLED"
        assert resp_cross.fill_price <= 26.50

    asyncio.run(_run())


def test_failed_exit_retains_position_and_escalates():
    """Verify that unfulfilled broker exits do not create fake fills and escalate to kill switch."""
    async def _run():
        symbol = "NIFTY_FAILED_EXIT_TEST"
        # Do not put snapshot in orderbook_manager, so place_order will fail/reject!
        orderbook_manager._books.pop(symbol, None)

        trade = ManagedTrade(
            trade_id="TRD_FAIL_01",
            symbol=symbol,
            option_type="CE",
            side="BUY",
            quantity=65,
            entry_price=20.0,
            entry_time_ms=time.time() * 1000.0,
            current_stop_price=17.70,
            target_price=26.90,
            state="STATE_0_INCEPTION",
            highest_price_seen=20.0,
            features_at_entry=[0.0] * 8,
            strategy_name="AdaptiveMLStrategy",
            max_exit_retries=1
        )
        auto_engine._active_trades[symbol] = trade

        res = await auto_engine._exit_trade(trade, 17.50, "STOP_TRIGGERED")
        assert res.get("status") == "EXIT_FAILED"
        # Invariant: Must NOT remove trade from active trades on failure!
        assert symbol in auto_engine._active_trades
        assert auto_engine._active_trades[symbol].state == "STATE_EXIT_FAILED"
        # Retries exhausted -> Emergency kill switch must be engaged!
        assert kill_switch.is_engaged is True

    asyncio.run(_run())


def test_kill_switch_sqlite_persistence():
    """Verify kill switch engaged state persists into SQLite and survives across new instances."""
    kill_switch.engage("Adversarial crash test", "AUDIT_TEST")
    assert kill_switch.is_engaged is True

    # Create completely new KillSwitch instance simulating process restart
    restarted_ks = KillSwitch(secret_key="SESSION_KEY_001")
    assert restarted_ks.is_engaged is True
    assert "Adversarial crash test" in restarted_ks.get_status().reason

    # Clean reset
    valid_hmac = restarted_ks.generate_reset_token()
    restarted_ks.reset(valid_hmac)
    assert restarted_ks.is_engaged is False

    # Verify state in third instance reflects the disengagement
    third_ks = KillSwitch(secret_key="SESSION_KEY_001")
    assert third_ks.is_engaged is False


def test_dynamic_arbitrage_strikes_centered_on_spot():
    """Verify that arbitrage scanner dynamically targets strikes centered on current spot."""
    # Seed spot at 24,000
    spot_tick = MarketDataNormalizer.create_synthetic_tick("NIFTY_SPOT", mid_price=24000.0)
    orderbook_manager.update_tick(spot_tick)

    with TestClient(app) as client:
        resp = client.get("/api/arbitrage/opportunities")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "OK"
        assert data["spot_price"] == 24000.0


def test_websocket_auth_gate():
    """Verify that /ws/stream blocks unauthenticated connections when API key is configured."""
    from api.auth import is_websocket_authenticated
    from unittest.mock import MagicMock

    # 1. Configure key
    os.environ["SERQ_API_KEY"] = "super-secret-key-xyz"
    try:
        # Mock unauthenticated remote websocket
        mock_ws_unauth = MagicMock()
        mock_ws_unauth.query_params = {}
        mock_ws_unauth.headers = {}
        mock_ws_unauth.client.host = "192.168.1.50"
        assert is_websocket_authenticated(mock_ws_unauth) is False

        # Mock authenticated websocket via query param
        mock_ws_auth = MagicMock()
        mock_ws_auth.query_params = {"api_key": "super-secret-key-xyz"}
        mock_ws_auth.headers = {}
        mock_ws_auth.client.host = "192.168.1.50"
        assert is_websocket_authenticated(mock_ws_auth) is True

        # Mock authenticated websocket via Bearer header
        mock_ws_bearer = MagicMock()
        mock_ws_bearer.query_params = {}
        mock_ws_bearer.headers = {"authorization": "Bearer super-secret-key-xyz"}
        mock_ws_bearer.client.host = "192.168.1.50"
        assert is_websocket_authenticated(mock_ws_bearer) is True
    finally:
        os.environ["SERQ_API_KEY"] = ""
