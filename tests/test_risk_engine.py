"""
Tests for Pre-Trade Risk Engine & Risk Invariants.
"""

from risk.engine import PreTradeRiskEngine, PreTradeOrderRequest
from risk.limits import RiskLimits
from risk.kill_switch import kill_switch
from market_data.orderbook import orderbook_manager
from market_data.normalizer import MarketDataNormalizer


def test_reject_wrong_lot_size():
    """Verify order is rejected if quantity is not a multiple of 65."""
    engine = PreTradeRiskEngine()
    req = PreTradeOrderRequest(
        symbol="NIFTY_TEST_CE",
        side="BUY",
        order_type="MARKET",
        price=20.0,
        quantity=50  # Invalid lot size (must be 65)
    )
    res = engine.validate_order(req, current_cash_inr=3000.0, daily_realized_loss_inr=0.0)
    assert res.passed is False
    assert any("multiple of lot size 65" in v for v in res.violations)


def test_reject_more_than_one_lot():
    """Verify max position size of 1 lot (65 units) is enforced."""
    engine = PreTradeRiskEngine()
    req = PreTradeOrderRequest(
        symbol="NIFTY_TEST_CE",
        side="BUY",
        order_type="MARKET",
        price=20.0,
        quantity=130  # 2 lots
    )
    res = engine.validate_order(req, current_cash_inr=3000.0, daily_realized_loss_inr=0.0)
    assert res.passed is False
    assert any("exceeds max allowed" in v for v in res.violations)


def test_reject_daily_loss_breach():
    """Verify orders are rejected when daily loss ceiling (₹300) is reached."""
    engine = PreTradeRiskEngine()
    req = PreTradeOrderRequest(
        symbol="NIFTY_TEST_CE",
        side="BUY",
        order_type="MARKET",
        price=20.0,
        quantity=65
    )
    res = engine.validate_order(req, current_cash_inr=2700.0, daily_realized_loss_inr=310.0)
    assert res.passed is False
    assert any("DAILY_LOSS_LIMIT_EXCEEDED" in v for v in res.violations)
    # Reset kill switch after test
    kill_switch.reset("CONFIRM_RESET")


def test_reject_when_capital_below_floor():
    """Verify orders are blocked if cash is below emergency floor (₹2,000)."""
    engine = PreTradeRiskEngine()
    req = PreTradeOrderRequest(
        symbol="NIFTY_TEST_CE",
        side="BUY",
        order_type="MARKET",
        price=20.0,
        quantity=65
    )
    res = engine.validate_order(req, current_cash_inr=1900.0, daily_realized_loss_inr=0.0)
    assert res.passed is False
    assert any("CAPITAL_BELOW_FLOOR" in v for v in res.violations)


def test_reject_when_kill_switch_engaged():
    """Verify all orders are rejected when kill switch is engaged."""
    kill_switch.engage("Manual test engage", "TEST")
    engine = PreTradeRiskEngine()
    req = PreTradeOrderRequest(
        symbol="NIFTY_TEST_CE",
        side="BUY",
        order_type="MARKET",
        price=20.0,
        quantity=65
    )
    res = engine.validate_order(req, current_cash_inr=3000.0, daily_realized_loss_inr=0.0)
    assert res.passed is False
    assert any("KILL_SWITCH_ENGAGED" in v for v in res.violations)
    kill_switch.reset("CONFIRM_RESET")
