"""
Unit Tests for Continuous Live Market Data Streamer (Paper V2).
Validates tick ingestion, freshness filtering, listener dispatch, and lifecycle.
"""

import asyncio
import time
import pytest
from market_data.stream import LiveMarketDataStreamer
from market_data.normalizer import MarketDataNormalizer


@pytest.fixture
def streamer():
    s = LiveMarketDataStreamer()
    s.reset()
    return s


def test_streamer_initialization(streamer):
    assert streamer.is_running is False
    assert streamer._total_ticks == 0
    assert streamer._stale_ticks == 0


def test_dispatch_fresh_tick_reaches_listener(streamer):
    received = []

    def on_tick(tick):
        received.append(tick)

    streamer.add_tick_listener(on_tick)
    sym = "NIFTY_2026-09-24_24600_CE"
    streamer.subscribe_symbol(sym)

    tick = MarketDataNormalizer.create_synthetic_tick(symbol=sym, mid_price=28.0, spread=0.20)
    streamer.dispatch_tick(tick)

    assert len(received) == 1
    assert received[0].symbol == sym
    assert streamer.get_health().total_ticks_received == 1
    assert streamer.get_health().stale_ticks_dropped == 0


def test_stale_tick_dropped_by_guard(streamer):
    received = []
    streamer.add_tick_listener(lambda t: received.append(t))

    sym = "NIFTY_2026-09-24_24600_CE"
    import dataclasses
    tick = MarketDataNormalizer.create_synthetic_tick(symbol=sym, mid_price=28.0, spread=0.20)
    stale_tick = dataclasses.replace(tick, timestamp_ms=(time.time() - 5.0) * 1000.0)

    streamer.dispatch_tick(stale_tick)

    # Must NOT reach listener
    assert len(received) == 0
    assert streamer.get_health().stale_ticks_dropped == 1


@pytest.mark.anyio
async def test_streamer_lifecycle():
    s = LiveMarketDataStreamer()
    s._has_live_credentials = False
    received = []
    s.add_tick_listener(lambda t: received.append(t))

    await s.start()
    assert s.is_running is True

    # Allow stream to ingest several ticks
    await asyncio.sleep(0.5)

    await s.stop()
    assert s.is_running is False
    assert len(received) > 0
