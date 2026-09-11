"""
Unit tests for the Institutional Microstructure Slippage & Queue Priority Engine.
Tests:
  1. FIFO queue priority and Level-1 matching
  2. Multi-level depth walking with VWAP fill pricing
  3. Liquidity exhaustion penalties for outsized orders
  4. Fast-market adverse selection drag dynamics
  5. Passive limit order queue wait and fill probability modeling
  6. Synthetic fallback execution when L2 depth is absent
  7. Empirical calibration telemetry recording and reset behavior
"""

import pytest
from costs.slippage import SlippageModel, QueuePosition, SlippageEstimate


@pytest.fixture
def slippage_engine():
    """Provides a fresh isolated slippage model instance for each test."""
    return SlippageModel(
        default_slippage_points=0.15,
        queue_priority_default=0.60,
        adverse_selection_factor=0.10,
        exhaustion_penalty_points=1.50
    )


def test_level_1_clean_fill_within_depth(slippage_engine):
    """Orders smaller than available depth at Level 1 fill at Best Ask without adverse drag."""
    # 500 contracts at Level 1, 60% queue priority = 300 ahead, 200 available
    ask_depth = [
        {"price": 28.50, "size": 500},
        {"price": 28.60, "size": 400},
        {"price": 28.70, "size": 300},
    ]
    
    # Buy 65 contracts (1 lot)
    res = slippage_engine.calculate_buy_fill(
        best_ask=28.50,
        quantity=65,
        ask_depth=ask_depth,
        is_fast_market=False
    )
    
    assert isinstance(res, SlippageEstimate)
    assert res.simulated_fill_price == 28.50
    assert res.slippage_points == 0.0
    assert res.fill_ratio == 1.0
    assert res.adverse_selection_drag_pts == 0.0
    
    # Check QueuePosition
    q = res.queue_position
    assert isinstance(q, QueuePosition)
    assert q.price_level == 28.50
    assert q.total_depth_at_level == 500
    assert q.queue_ahead_qty == 300  # 60% of 500
    assert q.our_quantity == 65
    assert q.fill_probability == 1.0
    assert q.estimated_wait_ms == 750.0  # 300 * 2.5ms


def test_multi_level_depth_walking(slippage_engine):
    """When order size exceeds available L1 depth, it walks into Level 2 with VWAP pricing."""
    # Level 1: 100 size. Queue ahead (60%) = 60. Available at L1 = 40.
    # Level 2: 200 size @ 30.10.
    ask_depth = [
        {"price": 30.00, "size": 100},
        {"price": 30.10, "size": 200},
        {"price": 30.20, "size": 200},
    ]
    
    # Order quantity = 100 contracts:
    # Fills 40 @ 30.00 = 1200.0
    # Fills 60 @ 30.10 = 1806.0
    # Total cost = 3006.0 / 100 = 30.06 base fill
    # Walked past L1 -> adverse selection drag applies:
    # 30.00 * 0.002 * 0.10 = 0.006 -> 0.01 pts drag
    # Final fill = 30.06 + 0.01 = 30.07
    res = slippage_engine.calculate_buy_fill(
        best_ask=30.00,
        quantity=100,
        ask_depth=ask_depth,
        is_fast_market=False
    )
    
    assert res.simulated_fill_price == 30.07
    assert res.slippage_points == 0.07
    assert res.adverse_selection_drag_pts == 0.01
    assert res.fill_ratio == 1.0


def test_sell_order_multi_level_walking(slippage_engine):
    """Sell market orders hitting bids walk bid depth downwards."""
    # Level 1: 100 size @ 25.00. Available = 40.
    # Level 2: 100 size @ 24.90.
    bid_depth = [
        {"price": 25.00, "size": 100},
        {"price": 24.90, "size": 100},
    ]
    
    # Sell 80 contracts:
    # 40 @ 25.00 = 1000.0
    # 40 @ 24.90 = 996.0
    # Total proceeds = 1996.0 / 80 = 24.95 base fill
    # Walked past L1 -> adverse selection drag: 25.00 * 0.002 * 0.10 = 0.005 -> 0.01 pts
    # Final fill = 24.95 - 0.01 = 24.94
    res = slippage_engine.calculate_sell_fill(
        best_bid=25.00,
        quantity=80,
        bid_depth=bid_depth,
        is_fast_market=False
    )
    
    assert res.simulated_fill_price == 24.94
    assert res.slippage_points == 0.06
    assert res.fill_ratio == 1.0


def test_depth_exhaustion_penalty(slippage_engine):
    """Orders that fully deplete all available depth incur the exhaustion penalty on excess."""
    # Total available: L1 has 40 available, L2 has 50 available = 90 total
    ask_depth = [
        {"price": 20.00, "size": 100},
        {"price": 20.20, "size": 50},
    ]
    
    # Request 150 contracts (60 contracts beyond book capacity)
    # L1: 40 @ 20.00 = 800
    # L2: 50 @ 20.20 = 1010
    # Excess 60 @ (20.20 + 1.50 exhaustion penalty = 21.70) = 1302
    # Total = 3112 / 150 = 20.7466 -> base 20.75
    res = slippage_engine.calculate_buy_fill(
        best_ask=20.00,
        quantity=150,
        ask_depth=ask_depth,
        is_fast_market=False
    )
    
    assert res.simulated_fill_price > 20.50
    assert res.slippage_points >= 0.74


def test_fast_market_adverse_selection_expansion(slippage_engine):
    """Fast market conditions trigger heightened adverse selection drag even on small orders."""
    ask_depth = [{"price": 40.00, "size": 1000}]
    
    normal_res = slippage_engine.calculate_buy_fill(
        best_ask=40.00,
        quantity=65,
        ask_depth=ask_depth,
        is_fast_market=False
    )
    
    fast_res = slippage_engine.calculate_buy_fill(
        best_ask=40.00,
        quantity=65,
        ask_depth=ask_depth,
        is_fast_market=True
    )
    
    # Fast market adds: 40.00 * 0.005 * 0.10 = 0.02 pts drag
    assert normal_res.simulated_fill_price == 40.00
    assert fast_res.simulated_fill_price == 40.02
    assert fast_res.adverse_selection_drag_pts == 0.02
    assert fast_res.slippage_points > normal_res.slippage_points


def test_fallback_without_depth(slippage_engine):
    """When orderbook depth is unavailable, models default spread-crossing slippage."""
    # BUY fallback
    buy_res = slippage_engine.calculate_buy_fill(
        best_ask=35.00,
        quantity=65,
        ask_depth=None,
        is_fast_market=False
    )
    assert buy_res.simulated_fill_price == 35.15  # 35.00 + 0.15 default slippage
    assert buy_res.slippage_points == 0.15
    assert buy_res.slippage_inr == round(0.15 * 65, 2)
    
    # SELL fallback
    sell_res = slippage_engine.calculate_sell_fill(
        best_bid=35.00,
        quantity=65,
        bid_depth=None,
        is_fast_market=False
    )
    assert sell_res.simulated_fill_price == 34.85  # 35.00 - 0.15 default slippage
    assert sell_res.slippage_points == 0.15


def test_passive_limit_order_execution(slippage_engine):
    """Passive limit orders suffer zero spread-crossing slippage but track queue wait."""
    depth_levels = [
        {"price": 25.00, "size": 200},
        {"price": 24.90, "size": 300},
    ]
    
    # Post limit buy at 25.00 with high incoming volume -> filled
    res_high_vol = slippage_engine.calculate_passive_limit_fill(
        side="BUY",
        limit_price=25.00,
        quantity=65,
        depth_levels=depth_levels,
        incoming_volume=1000
    )
    
    assert res_high_vol.execution_type == "PASSIVE_LIMIT"
    assert res_high_vol.simulated_fill_price == 25.00
    assert res_high_vol.slippage_points == 0.0
    assert res_high_vol.fill_ratio == 1.0
    assert res_high_vol.queue_position.queue_ahead_qty == 120  # 60% of 200
    assert res_high_vol.queue_position.fill_probability == 1.0
    assert res_high_vol.queue_position.estimated_wait_ms == 1800.0  # 120 * 15ms


def test_telemetry_calibration_and_reset(slippage_engine):
    """Telemetry records empirical fills, tracks statistics, and resets cleanly."""
    assert slippage_engine.get_telemetry()["total_fills_analyzed"] == 0
    
    # Execute 3 fills
    slippage_engine.calculate_buy_fill(best_ask=20.00, quantity=65, ask_depth=None)
    slippage_engine.calculate_buy_fill(best_ask=25.00, quantity=65, ask_depth=None)
    slippage_engine.calculate_sell_fill(best_bid=30.00, quantity=65, bid_depth=None)
    
    tel = slippage_engine.get_telemetry()
    assert tel["total_fills_analyzed"] == 3
    assert tel["avg_slippage_points"] == 0.15
    assert tel["avg_slippage_inr"] == round(0.15 * 65, 2)
    assert "default_queue_priority" in tel
    
    # Reset
    slippage_engine.reset()
    tel_after = slippage_engine.get_telemetry()
    assert tel_after["total_fills_analyzed"] == 0
