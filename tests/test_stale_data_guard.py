"""
Tests for Market Data Freshness & Stale Data Guard (1500ms Threshold).
"""

import time
from risk.stale_data_guard import StaleDataGuard
from market_data.normalizer import MarketTick


def test_fresh_market_tick():
    """Verify that newly generated ticks are recognized as fresh."""
    guard = StaleDataGuard(timeout_ms=1500)
    tick = MarketTick(
        symbol="NIFTY_TEST_CE",
        timestamp_ms=time.time() * 1000.0,  # Just generated
        ltp=25.0,
        volume=1000,
        best_bid=24.9,
        best_ask=25.1,
        bid_size=65,
        ask_size=65
    )
    res = guard.check_tick(tick)
    assert res.is_fresh is True
    assert res.age_ms < 100.0


def test_stale_market_tick():
    """Verify that ticks older than 1500ms are marked stale."""
    guard = StaleDataGuard(timeout_ms=1500)
    old_timestamp = (time.time() - 2.5) * 1000.0  # 2.5 seconds ago

    tick = MarketTick(
        symbol="NIFTY_TEST_CE",
        timestamp_ms=old_timestamp,
        ltp=25.0,
        volume=1000,
        best_bid=24.9,
        best_ask=25.1,
        bid_size=65,
        ask_size=65
    )
    res = guard.check_tick(tick)
    assert res.is_fresh is False
    assert res.age_ms >= 2000.0
    assert "stale" in res.reason.lower()
