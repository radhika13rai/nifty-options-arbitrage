"""
Tests for ₹3,000 Retail Capital Feasibility Proofs.
Verifies that multi-leg arbitrage strategies are flagged CAPITAL_INFEASIBLE,
while single-leg low-premium OTM strategies are permitted.
"""

from config import config
from strategies.put_call_parity import put_call_parity_scanner
from strategies.box_spread import box_spread_scanner
from strategies.volatility_breakout import VolatilityBreakoutStrategy
from market_data.orderbook import orderbook_manager
from market_data.normalizer import MarketDataNormalizer
from portfolio.margin import margin_calculator


def test_put_call_parity_flags_capital_infeasible():
    """Verify that Put-Call Parity arbitrage signals are marked CAPITAL_INFEASIBLE."""
    # Setup test orderbooks with an artificial mispricing
    ce_sym = "NIFTY_2026-09-24_24500_CE"
    pe_sym = "NIFTY_2026-09-24_24500_PE"

    ce_tick = MarketDataNormalizer.create_synthetic_tick(ce_sym, mid_price=120.0)
    pe_tick = MarketDataNormalizer.create_synthetic_tick(pe_sym, mid_price=40.0)
    orderbook_manager.update_tick(ce_tick)
    orderbook_manager.update_tick(pe_tick)

    # Spot price 24,500
    signals = put_call_parity_scanner.scan_strike(24500, ce_sym, pe_sym, 24500.0)

    for sig in signals:
        # Every multi-leg arbitrage signal MUST be flagged as not capital feasible
        assert sig.is_capital_feasible is False
        assert "CAPITAL_INFEASIBLE" in sig.infeasibility_reason
        assert "margin" in sig.infeasibility_reason.lower()


def test_box_spread_flags_capital_infeasible():
    """Verify that 4-leg box spreads are marked CAPITAL_INFEASIBLE."""
    c1 = "NIFTY_2026-09-24_24400_CE"
    c2 = "NIFTY_2026-09-24_24500_CE"
    p1 = "NIFTY_2026-09-24_24400_PE"
    p2 = "NIFTY_2026-09-24_24500_PE"

    for sym, price in [(c1, 150.0), (c2, 80.0), (p1, 40.0), (p2, 100.0)]:
        tick = MarketDataNormalizer.create_synthetic_tick(sym, mid_price=price)
        orderbook_manager.update_tick(tick)

    box_sig = box_spread_scanner.scan_box(24400, 24500, c1, c2, p1, p2)
    if box_sig:
        assert box_sig.is_capital_feasible is False
        assert "CAPITAL_INFEASIBLE" in box_sig.infeasibility_reason


def test_margin_calculator_short_vs_long():
    """Verify margin calculations accurately reflect exchange requirements."""
    # Long option at ₹30 premium
    long_margin = margin_calculator.evaluate_option_buy(30.0, 65)
    assert long_margin.is_feasible is True
    assert long_margin.required_capital_inr < 3000.0

    # Naked short option requires SPAN margin of ~₹1,40,000
    short_margin = margin_calculator.evaluate_option_sell(24500.0, 65)
    assert short_margin.is_feasible is False
    assert short_margin.required_capital_inr >= 100000.0
    assert short_margin.shortfall_inr > 90000.0


def test_volatility_breakout_within_capital_limit():
    """Verify single-leg OTM volatility breakout fits within ₹3,000 capital."""
    strat = VolatilityBreakoutStrategy()
    assert strat.max_premium * 65 < 3000.0  # 38 * 65 = ₹2,470 < ₹3,000
