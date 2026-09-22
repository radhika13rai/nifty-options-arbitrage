"""
Tests for Autonomous Execution & Dynamic Trailing Stop Lifecycle Engine.
Verifies signal auto-dispatching, dynamic ratchet progression (Breakeven, Profit Lock,
1:2 R:R, 1:3 Target), time stops, and closed-loop learning feedback.
"""

import asyncio
import time
import uuid
import pytest
from execution.auto_engine import auto_engine, ManagedTrade
from strategies.base import TradingSignal
from market_data.normalizer import MarketDataNormalizer
from market_data.orderbook import orderbook_manager
from portfolio.pnl import pnl_manager
from database.db import db_manager
from ml.learner import learning_engine
from portfolio.positions import position_tracker


@pytest.fixture(autouse=True)
def setup_environment():
    """Initializes clean database and resets engine before each test."""
    db_manager.init_db()
    pnl_manager.reset_balance(3000.0)
    position_tracker.reset()
    auto_engine._active_trades.clear()
    auto_engine._trade_history.clear()
    auto_engine.enable()
    yield
    position_tracker.reset()
    auto_engine._active_trades.clear()



def test_auto_execution_signal_fill():
    """Verify that a valid ML signal automatically routes and registers a ManagedTrade."""
    async def _run():
        symbol = "NIFTY_2026-09-24_24600_CE"
        tick = MarketDataNormalizer.create_synthetic_tick(symbol=symbol, mid_price=22.0, spread=0.20)
        orderbook_manager.update_tick(tick)

        sig = TradingSignal(
            signal_id=f"SIG_{uuid.uuid4().hex[:8]}",
            timestamp_ms=time.time() * 1000.0,
            strategy_name="AdaptiveMLStrategy",
            symbol=symbol,
            action="BUY",
            order_type="MARKET",
            suggested_price=22.10,
            quantity=65,
            confidence=0.85,
            is_capital_feasible=True,
            metadata={"option_type": "CE", "features": [0.1] * 8}
        )

        resp = await auto_engine.handle_signal(sig)
        assert resp is not None
        assert resp.status == "FILLED"
        assert symbol in auto_engine._active_trades

        trade = auto_engine._active_trades[symbol]
        assert trade.state == "STATE_0_INCEPTION"
        assert trade.entry_price >= 22.10
        assert trade.current_stop_price == round(trade.entry_price - 2.30, 2)
        assert trade.target_price == round(trade.entry_price + 6.90, 2)

    asyncio.run(_run())


def test_dynamic_trailing_ratchet_breakeven():
    """Verify stop ratchets to Breakeven (+0.80 pts) when price moves +1.50 pts."""
    async def _run():
        symbol = "NIFTY_2026-09-24_24600_CE"
        trade = ManagedTrade(
            trade_id="TRD_01",
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
            strategy_name="AdaptiveMLStrategy"
        )
        auto_engine._active_trades[symbol] = trade

        # Tick at +1.60 pts gain (LTP = 21.60)
        tick = MarketDataNormalizer.create_synthetic_tick(symbol=symbol, mid_price=21.60)
        res = await auto_engine.on_tick(tick)

        assert res is not None
        assert trade.state == "STATE_1_BREAKEVEN"
        # Stop must be ratcheted to entry + 0.80 = 20.80 (risk-free)
        assert trade.current_stop_price == 20.80

    asyncio.run(_run())


def test_dynamic_trailing_ratchet_profit_lock_and_rr():
    """Verify stop progresses through Profit Lock (+1.80 pts) and 1:2 R:R (+3.20 pts)."""
    async def _run():
        symbol = "NIFTY_2026-09-24_24600_CE"
        trade = ManagedTrade(
            trade_id="TRD_02",
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
            strategy_name="AdaptiveMLStrategy"
        )
        auto_engine._active_trades[symbol] = trade

        # 1. Price advances +3.30 pts (LTP = 23.30) -> Tier 2 Profit Lock
        tick1 = MarketDataNormalizer.create_synthetic_tick(symbol=symbol, mid_price=23.30)
        await auto_engine.on_tick(tick1)
        assert trade.state == "STATE_2_PROFIT_LOCK"
        assert trade.current_stop_price == 21.80  # Entry + 1.80 pts

        # 2. Price advances +4.70 pts (LTP = 24.70) -> Tier 3 (1:2 R:R)
        tick2 = MarketDataNormalizer.create_synthetic_tick(symbol=symbol, mid_price=24.70)
        await auto_engine.on_tick(tick2)
        assert trade.state == "STATE_3_RR_1_2"
        assert trade.current_stop_price == 23.20  # Entry + 3.20 pts

    asyncio.run(_run())


def test_auto_exit_target_reached_and_feedback():
    """Verify full exit when 1:3 target is hit and feedback updates the learning engine."""
    async def _run():
        symbol = "NIFTY_2026-09-24_24600_CE"
        # Seed orderbook so paper_broker can fill sell exit
        tick_ob = MarketDataNormalizer.create_synthetic_tick(symbol=symbol, mid_price=27.0, spread=0.20)
        orderbook_manager.update_tick(tick_ob)

        initial_win_rate = learning_engine.call_sampler.expected_win_rate

        trade = ManagedTrade(
            trade_id="TRD_03",
            symbol=symbol,
            option_type="CE",
            side="BUY",
            quantity=65,
            entry_price=20.0,
            entry_time_ms=time.time() * 1000.0,
            current_stop_price=23.20,
            target_price=26.90,
            state="STATE_3_RR_1_2",
            highest_price_seen=25.0,
            features_at_entry=[0.1] * 8,
            strategy_name="AdaptiveMLStrategy"
        )
        auto_engine._active_trades[symbol] = trade
        position_tracker.apply_fill(symbol=symbol, side="BUY", price=20.0, quantity=65)

        # Price hits target (LTP = 27.00 >= 26.90)
        tick_target = MarketDataNormalizer.create_synthetic_tick(symbol=symbol, mid_price=27.00)
        res = await auto_engine.on_tick(tick_target)

        assert res is not None
        assert "TARGET_1_3_REACHED" in res["reason"]
        assert symbol not in auto_engine._active_trades
        assert len(auto_engine._trade_history) == 1

        # Check positive net PnL and learning feedback
        closed = auto_engine._trade_history[0]
        assert closed["net_pnl"] > 0
        # Call sampler alpha must have incremented
        assert learning_engine.call_sampler.alpha > 1.0

    asyncio.run(_run())


def test_stop_loss_breach_exit():
    """Verify automatic exit when price drops below active trailing stop."""
    async def _run():
        symbol = "NIFTY_2026-09-24_24600_CE"
        tick_ob = MarketDataNormalizer.create_synthetic_tick(symbol=symbol, mid_price=17.5, spread=0.20)
        orderbook_manager.update_tick(tick_ob)

        trade = ManagedTrade(
            trade_id="TRD_04",
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
            strategy_name="AdaptiveMLStrategy"
        )
        auto_engine._active_trades[symbol] = trade
        position_tracker.apply_fill(symbol=symbol, side="BUY", price=20.0, quantity=65)

        # Price drops below stop (LTP = 17.60 <= 17.70)
        tick_stop = MarketDataNormalizer.create_synthetic_tick(symbol=symbol, mid_price=17.60)
        res = await auto_engine.on_tick(tick_stop)

        assert res is not None
        assert "STOP_TRIGGERED" in res["reason"]
        assert symbol not in auto_engine._active_trades

    asyncio.run(_run())


def test_time_stop_expiration():
    """Verify automatic exit when position stagnates for 15 minutes without breakout."""
    async def _run():
        symbol = "NIFTY_2026-09-24_24600_CE"
        tick_ob = MarketDataNormalizer.create_synthetic_tick(symbol=symbol, mid_price=20.2, spread=0.20)
        orderbook_manager.update_tick(tick_ob)

        # Entry time 16 minutes in the past
        past_time = (time.time() - 960) * 1000.0

        trade = ManagedTrade(
            trade_id="TRD_05",
            symbol=symbol,
            option_type="CE",
            side="BUY",
            quantity=65,
            entry_price=20.0,
            entry_time_ms=past_time,
            current_stop_price=17.70,
            target_price=26.90,
            state="STATE_0_INCEPTION",
            highest_price_seen=20.3,
            features_at_entry=[0.0] * 8,
            strategy_name="AdaptiveMLStrategy"
        )
        auto_engine._active_trades[symbol] = trade
        position_tracker.apply_fill(symbol=symbol, side="BUY", price=20.0, quantity=65)

        # Tick at +0.20 pts gain (insufficient, < 1.50 pts)
        tick = MarketDataNormalizer.create_synthetic_tick(symbol=symbol, mid_price=20.20)
        res = await auto_engine.on_tick(tick)

        assert res is not None
        assert "TIME_STOP_EXPIRED" in res["reason"]
        assert symbol not in auto_engine._active_trades

    asyncio.run(_run())


def test_capital_single_position_lock():
    """Verify that only 1 position can be active under the ₹3,000 capital invariant."""
    async def _run():
        symbol1 = "NIFTY_2026-09-24_24600_CE"
        symbol2 = "NIFTY_2026-09-24_24400_PE"

        # Pre-populate active trade
        auto_engine._active_trades[symbol1] = ManagedTrade(
            trade_id="TRD_EXISTING",
            symbol=symbol1,
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
            strategy_name="AdaptiveMLStrategy"
        )
        position_tracker.apply_fill(symbol=symbol1, side="BUY", price=20.0, quantity=65)

        # Attempt to dispatch second signal
        sig2 = TradingSignal(
            signal_id=f"SIG_{uuid.uuid4().hex[:8]}",
            timestamp_ms=time.time() * 1000.0,
            strategy_name="AdaptiveMLStrategy",
            symbol=symbol2,
            action="BUY",
            order_type="MARKET",
            suggested_price=25.0,
            quantity=65,
            confidence=0.90,
            is_capital_feasible=True,
            metadata={"option_type": "PE", "features": [0.0] * 8}
        )

        resp = await auto_engine.handle_signal(sig2)
        assert resp is None  # Blocked!
        assert symbol2 not in auto_engine._active_trades

    asyncio.run(_run())


def test_dispatch_breakout_with_screener():
    """Verify autonomous entry via strike screener selects compliant contract and executes."""
    async def _run():
        resp = await auto_engine.dispatch_breakout_with_screener(
            spot=24500.0,
            directional_bias="BULLISH",
            days_to_expiry=4.0,
            iv=0.155
        )
        assert resp is not None
        assert resp.status == "FILLED"
        assert len(auto_engine._active_trades) == 1

        active_trade = list(auto_engine._active_trades.values())[0]
        assert active_trade.option_type == "CE"
        assert active_trade.entry_price <= 38.00
        assert active_trade.quantity == 65
        assert 0.15 <= abs(active_trade.entry_delta) <= 0.30

    asyncio.run(_run())


def test_gamma_acceleration_ratchet():
    """Verify trailing stop ratchets aggressively when Delta expands past 0.50."""
    async def _run():
        symbol = "NIFTY_2026-09-24_24900_CE"
        trade = ManagedTrade(
            trade_id="TRD_GAMMA_01",
            symbol=symbol,
            option_type="CE",
            side="BUY",
            quantity=65,
            entry_price=25.0,
            entry_time_ms=time.time() * 1000.0,
            current_stop_price=22.70,
            target_price=35.00,
            state="STATE_0_INCEPTION",
            highest_price_seen=25.0,
            features_at_entry=[0.0] * 8,
            strategy_name="DYNAMIC_GREEK_BREAKOUT",
            entry_delta=0.22,
            current_delta=0.22
        )
        auto_engine._active_trades[symbol] = trade

        # Huge breakout moves option from 25.0 to 32.0 (+7.0 pts)
        # Delta expands: 0.22 + (7.0 * 0.045) = 0.535 >= 0.50
        tick = MarketDataNormalizer.create_synthetic_tick(symbol=symbol, mid_price=32.0)
        res = await auto_engine.on_tick(tick)

        assert res is not None
        assert res["gamma_triggered"] is True
        assert res["current_delta"] >= 0.50
        assert trade.current_stop_price >= 28.50  # entry 25.0 + 3.50

    asyncio.run(_run())


def test_pre_trade_premium_cap_rejection():
    """Verify signals with premium > ₹38.00 are rejected upfront under micro-capital limits."""
    async def _run():
        symbol = "NIFTY_2026-09-24_24500_CE"
        sig_expensive = TradingSignal(
            signal_id=f"SIG_EXP_{uuid.uuid4().hex[:6]}",
            timestamp_ms=time.time() * 1000.0,
            strategy_name="AdaptiveMLStrategy",
            symbol=symbol,
            action="BUY",
            order_type="MARKET",
            suggested_price=75.0,  # Violates ₹38.00 cap!
            quantity=65,
            confidence=0.90,
            is_capital_feasible=True,
            metadata={"option_type": "CE"}
        )

        resp = await auto_engine.handle_signal(sig_expensive)
        assert resp is None  # Blocked!
        assert symbol not in auto_engine._active_trades

    asyncio.run(_run())

