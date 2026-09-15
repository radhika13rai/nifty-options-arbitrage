#!/usr/bin/env python3
"""
Autonomous NIFTY Options Trading Terminal Daemon.
Launches the continuous auto-trading engine, ingests real-time market ticks,
evaluates quantitative breakout signals, manages trailing ratchet stops,
and displays live execution telemetry.

Usage:
    python3 run_auto_trader.py
    python3 run_auto_trader.py --capital 3000 --duration 60
"""

import argparse
import asyncio
import logging
import signal
import sys
import time

from config import config
from database.db import db_manager
from portfolio.pnl import pnl_manager
from portfolio.positions import position_tracker
from risk.kill_switch import kill_switch
from execution.auto_engine import auto_engine
from market_data.websocket import market_feed
from market_data.orderbook import orderbook_manager
from strategies.volatility_breakout import VolatilityBreakoutStrategy
from ml.engine import adaptive_ml_strategy
from scheduler.daily_routine import market_scheduler, MarketPhase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AutoTrader")

vol_strategy = VolatilityBreakoutStrategy()


def handle_tick(tick):
    """Event handler invoked on every inbound market tick."""
    # 1. Update position MTM
    position_tracker.mark_to_market(tick.symbol, tick.ltp)

    # 2. Evaluate active positions against dynamic ratchet trailing stop
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(auto_engine.on_tick(tick))
    except RuntimeError:
        pass

    # 3. Generate trading signals if auto-trading is enabled
    if not auto_engine.is_auto_trading_enabled:
        return

    rule_sigs = vol_strategy.on_tick(tick) or []
    ml_sigs = adaptive_ml_strategy.on_tick(tick) or []
    signals = rule_sigs + ml_sigs

    if signals:
        for sig in signals:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(auto_engine.handle_signal(sig))
            except RuntimeError:
                pass


async def render_telemetry():
    """Prints live performance summary to stdout periodically."""
    while True:
        await asyncio.sleep(5.0)
        pnl = pnl_manager.generate_report()
        status = auto_engine.get_status()
        active = status.get("active_trades", [])
        
        print("\n" + "=" * 75)
        print(f"⚡ AUTO-TRADER TELEMETRY | Mode: {config.execution_mode} | Capital: ₹{pnl.current_cash:.2f}")
        print(f"   Realized P&L: ₹{pnl.net_pnl:+.2f} | Unrealized: ₹{pnl.gross_unrealized_pnl:+.2f} | Fees: ₹{pnl.total_friction_inr:.2f}")
        print(f"   Active Positions: {len(active)}/1 lot | Closed Trades: {status.get('trade_count', 0)}")
        
        if active:
            for t in active:
                pts = t.get("delta_pts", 0.0)
                print(f"   ► [{t.get('symbol')}] Entry: ₹{t.get('entry_price'):.2f} | Stop: ₹{t.get('stop_loss'):.2f} | Target: ₹{t.get('target'):.2f} | Move: {pts:+.2f} pts | State: {t.get('state')}")
        else:
            print("   ► Scanning orderbook for high-conviction breakout opportunities...")
        print("=" * 75)


async def main():
    parser = argparse.ArgumentParser(description="Autonomous Options Trading Terminal Daemon")
    parser.add_argument("--capital", type=float, default=3000.0, help="Starting capital (INR)")
    parser.add_argument("--duration", type=int, default=0, help="Run duration in seconds (0 = indefinite)")
    args = parser.parse_args()

    print("=" * 75)
    print("🚀 STARTING INSTITUTIONAL NIFTY OPTIONS AUTONOMOUS TRADING ENGINE")
    print(f"   Capital: ₹{args.capital:,.2f} | Max Lot: 1 (65 units) | Stop Cap: ₹150.00")
    print(f"   Execution Mode: {config.execution_mode} | Kill Switch: {kill_switch.is_engaged}")
    print("=" * 75)

    # 1. Initialize SQLite Database and PnL Account
    await db_manager.async_init_db()
    pnl_manager.reset_balance(args.capital)
    
    # 2. Enable Auto-Execution Engine
    auto_engine.enable()
    market_feed.subscribe(handle_tick)

    # 3. Start Market Feed & Routine Scheduler
    await market_scheduler.execute_phase_transition(MarketPhase.MORNING_BREAKOUT)
    await market_feed.start()

    telemetry_task = asyncio.create_task(render_telemetry())

    # 4. Graceful shutdown handler
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received. Stopping auto trader...")
        stop_event.set()

    for sig_name in ("SIGINT", "SIGTERM"):
        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(getattr(signal, sig_name), _signal_handler)
        except (NotImplementedError, AttributeError):
            pass

    try:
        if args.duration > 0:
            await asyncio.wait_for(stop_event.wait(), timeout=args.duration)
        else:
            await stop_event.wait()
    except asyncio.TimeoutError:
        logger.info(f"Target duration of {args.duration}s reached.")
    finally:
        telemetry_task.cancel()
        logger.info("Squaring off active positions post-run...")
        await auto_engine.mandatory_intraday_square_off()
        await market_feed.stop()
        
        rep = pnl_manager.generate_report()
        print("\n" + "=" * 75)
        print("🏁 AUTO-TRADER SESSION SUMMARY")
        print(f"   Starting Capital : ₹{rep.starting_cash:.2f}")
        print(f"   Ending Capital   : ₹{rep.current_cash:.2f}")
        print(f"   Net P&L Realized : ₹{rep.net_pnl:+.2f}")
        print(f"   Total Friction   : ₹{rep.total_friction_inr:.2f}")
        print(f"   Net Return Pct   : {rep.net_pnl_percentage:.1f}%")
        print("=" * 75)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSession stopped by user.")
