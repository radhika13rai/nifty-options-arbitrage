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
    kill_switch.reset_system()


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
    kill_switch.reset_system()


def test_kill_switch_hmac_cryptographic_verification():
    """Verify HMAC-SHA256 token verification and invalid token rejection."""
    import pytest
    kill_switch.engage("Testing HMAC reset", "TEST")
    assert kill_switch.is_engaged is True
    
    # 1. Invalid token raises ValueError without leaking expected string
    with pytest.raises(ValueError, match="Cryptographic verification failed"):
        kill_switch.reset("FORGED_TOKEN_12345")
    assert kill_switch.is_engaged is True
    
    # 2. Valid HMAC token disengages
    valid_hmac = kill_switch.generate_reset_token()
    kill_switch.reset(valid_hmac)
    assert kill_switch.is_engaged is False


def test_reject_daily_loss_headroom_exceeded():
    """Verify new orders are rejected if remaining daily loss budget cannot absorb the potential trade risk."""
    engine = PreTradeRiskEngine()
    req = PreTradeOrderRequest(
        symbol="NIFTY_TEST_CE",
        side="BUY",
        order_type="MARKET",
        price=20.0,
        quantity=65,
        stop_loss_price=17.70  # ₹149.50 risk
    )
    # With daily realized loss of ₹200.00, adding ₹149.50 + fees would exceed ₹300.00 ceiling
    res = engine.validate_order(req, current_cash_inr=2800.0, daily_realized_loss_inr=200.0)
    assert res.passed is False
    assert any("DAILY_LOSS_HEADROOM_EXCEEDED" in v for v in res.violations)


def test_reject_capital_floor_headroom_exceeded():
    """Verify new orders are rejected if potential trade loss would breach non-negotiable ₹2,000 floor."""
    engine = PreTradeRiskEngine()
    req = PreTradeOrderRequest(
        symbol="NIFTY_TEST_CE",
        side="BUY",
        order_type="MARKET",
        price=20.0,
        quantity=65,
        stop_loss_price=17.70  # ₹149.50 risk + ~₹52 fees = ~₹201.50 total potential loss
    )
    # 1. Reject if cash is already at or below floor
    res_at_floor = engine.validate_order(req, current_cash_inr=2000.0, daily_realized_loss_inr=0.0)
    assert res_at_floor.passed is False
    assert any("CAPITAL_FLOOR_REACHED" in v for v in res_at_floor.violations)

    # 2. Reject if cash is ₹2,100 (potential loss would leave ₹1,898.50, breaching ₹2,000 floor)
    res_headroom = engine.validate_order(req, current_cash_inr=2100.0, daily_realized_loss_inr=0.0)
    assert res_headroom.passed is False
    assert any("CAPITAL_FLOOR_HEADROOM_EXCEEDED" in v for v in res_headroom.violations)


