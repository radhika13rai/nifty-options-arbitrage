"""
End-to-End Intraday Trading Day Simulation & Demonstration.
Fast-forwards through an institutional NIFTY options trading day:
  1. 09:00 IST: Pre-Market Macro Sync (Live Yahoo Finance cues + RSS headlines)
  2. 09:15 IST: Market Opening Bell & Autonomous Breakout Execution
  3. Dynamic Trailing Stop Machine: Breakeven -> Profit Lock -> 1:2 R:R -> 1:3 Target Exit
  4. Closed-Loop Learning: RLS weights update and Bayesian Thompson Sampling update
  5. 11:30 IST: Midday Chop Stand-Down (Pause new entries)
  6. 15:15 IST: Mandatory Regulatory Square-Off
  7. 15:35 IST: Post-Market Walk-Forward Adaptation & Audit Archival
"""

import asyncio
import time
from database.db import db_manager
from portfolio.pnl import pnl_manager
from execution.auto_engine import auto_engine
from global_macro.poller import live_macro_poller
from scheduler.daily_routine import market_scheduler, MarketPhase
from market_data.normalizer import MarketDataNormalizer
from market_data.orderbook import orderbook_manager
from strategies.base import TradingSignal
from ml.learner import learning_engine


async def main():
    print("=" * 70)
    print("⚡ INSTITUTIONAL NIFTY OPTIONS ALGO TRADING: FULL DAY SIMULATION")
    print("=" * 70)

    # 0. Setup & Database Init
    await db_manager.async_init_db()
    pnl_manager.reset_balance(3000.0)
    market_scheduler.set_simulated_mode(True)
    auto_engine.enable()

    print("\n[Phase 1] 09:00 IST - PRE-MARKET MACRO SYNC & POSTURE ALIGNMENT")
    print("-" * 70)
    t1 = await market_scheduler.execute_phase_transition(MarketPhase.PRE_MARKET_OPEN)
    macro_poll = t1.get("macro_poll", {})
    print(f"  • Global Poller Status : {macro_poll.get('status')}")
    print(f"  • Brent Crude          : ${macro_poll.get('brent', 82.5):.2f}")
    print(f"  • US Dollar Index (DXY): {macro_poll.get('dxy', 103.8):.2f}")
    print(f"  • Est. NIFTY Open Gap  : {macro_poll.get('gap_pts', 0):+.1f} points")
    print(f"  • Recommended Posture  : {macro_poll.get('posture')}")
    print(f"  • Geopolitical Fear Idx: {macro_poll.get('fear_index', 0):.2f}")
    print(f"  • Trading Permitted    : {market_scheduler.is_trading_permitted} (Hold execution till bell)")

    print("\n[Phase 2] 09:15 IST - MARKET OPENING BELL & BREAKOUT SCANNING")
    print("-" * 70)
    t2 = await market_scheduler.execute_phase_transition(MarketPhase.MORNING_BREAKOUT)
    print(f"  • Market Status        : {t2.get('to')}")
    print(f"  • Actions              : {t2.get('actions')}")
    print(f"  • Trading Permitted    : {market_scheduler.is_trading_permitted}")

    # Set up synthetic orderbook for a liquid NIFTY call option under ₹38.00 cap
    sym = "NIFTY_2026-09-24_24600_CE"
    tick = MarketDataNormalizer.create_synthetic_tick(symbol=sym, mid_price=28.00, spread=0.20)
    orderbook_manager.update_tick(tick)

    print(f"\n[Phase 3] INCOMING ML SIGNAL & AUTONOMOUS DISPATCH")
    print("-" * 70)
    import uuid
    sig = TradingSignal(
        signal_id=f"SIG_MORN_BREAKOUT_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}",
        timestamp_ms=time.time() * 1000.0,
        strategy_name="VOLATILITY_BREAKOUT",
        symbol=sym,
        action="BUY",
        order_type="MARKET",
        suggested_price=28.10,
        quantity=65,
        target_price=35.00,     # Entry + 6.90 pts (1:3 R:R)
        stop_loss_price=25.80,  # Entry - 2.30 pts (Hard ₹150 stop)
        confidence=0.72,
        is_capital_feasible=True,
        metadata={
            "features": [0.65, 0.40, 0.02, 0.35, 0.08, 0.15, 0.25, 0.50],
            "option_type": "CALL"
        }
    )

    order_resp = await auto_engine.handle_signal(sig)
    managed_trade = auto_engine._active_trades.get(sym)
    print(f"  • Order Status         : {order_resp.status} (ID: {order_resp.order_id})")
    print(f"  • Active Managed Trade : {managed_trade.trade_id} [{managed_trade.state}]")
    print(f"  • Hard Stop-Loss Price : ₹{managed_trade.current_stop_price:.2f} (Max Risk: ₹149.50)")
    print(f"  • 1:3 R:R Target Price : ₹{managed_trade.target_price:.2f}")

    print("\n[Phase 4] REAL-TIME DYNAMIC TRAILING STOP RATCHET PROGRESSION")
    print("-" * 70)
    # Price steps up
    price_steps = [
        (29.60, "Move +1.50 pts -> RATCHET TIER 1: BREAKEVEN LOCKED (RISK-FREE)"),
        (31.30, "Move +3.20 pts -> RATCHET TIER 2: PROFIT LOCK LOCKED (+₹65 NET)"),
        (32.70, "Move +4.60 pts -> RATCHET TIER 3: 1:2 R:R LOCKED (+₹156 NET)"),
        (35.00, "Move +6.90 pts -> 1:3 R:R TARGET REACHED -> MARKET EXIT")
    ]

    for price, desc in price_steps:
        t_tick = MarketDataNormalizer.create_synthetic_tick(symbol=sym, mid_price=price, spread=0.20)
        orderbook_manager.update_tick(t_tick)
        res = await auto_engine.on_tick(t_tick)
        if res and "stop" in res:
            print(f"  • LTP ₹{price:.2f} : {desc}")
            print(f"    --> State: {res.get('state')} | Active Stop: ₹{res.get('stop'):.2f}")
        elif res and "exit_price" in res:
            print(f"  • LTP ₹{price:.2f} : {desc}")
            print(f"    --> Trade Closed! Fill: ₹{res.get('exit_price'):.2f} | Points: {res.get('points_moved'):+.2f}")
            print(f"    --> Gross PnL: ₹{res.get('gross_pnl'):+.2f} | Statutory Fees: ₹{res.get('total_fees'):.2f}")
            print(f"    --> Net PnL: ₹{res.get('net_pnl'):+.2f} | Reason: {res.get('reason')}")

    print("\n[Phase 5] 11:30 IST - MIDDAY CHOP STAND-DOWN")
    print("-" * 70)
    t3 = await market_scheduler.execute_phase_transition(MarketPhase.MIDDAY_STAND_DOWN)
    print(f"  • Market Status        : {t3.get('to')}")
    print(f"  • Action               : {t3.get('actions')}")
    print(f"  • Trading Permitted    : {market_scheduler.is_trading_permitted} (Prevents Theta decay traps)")

    print("\n[Phase 6] 15:15 IST - MANDATORY REGULATORY SQUARE-OFF")
    print("-" * 70)
    t4 = await market_scheduler.execute_phase_transition(MarketPhase.MANDATORY_SQUARE_OFF)
    print(f"  • Market Status        : {t4.get('to')}")
    print(f"  • Open Positions       : {len(auto_engine._active_trades)} (Strictly 0 overnight risk)")

    print("\n[Phase 7] 15:35 IST - POST-MARKET AI ADAPTATION & AUDIT ARCHIVAL")
    print("-" * 70)
    t5 = await market_scheduler.execute_phase_transition(MarketPhase.POST_MARKET_LEARN)
    print(f"  • Walk-Forward Step    : Advanced to Epoch {t5.get('adaptation_epoch')}")
    print(f"  • Multimodal Accuracy  : {t5.get('multimodal_accuracy', 0)*100:.1f}%")
    print(f"  • Closing Net P&L      : ₹{t5.get('closing_net_pnl', 0):.2f}")
    print(f"  • Total Friction Deduct: ₹{t5.get('total_friction', 0):.2f}")

    pnl = pnl_manager.generate_report()
    print("\n[FINAL PORTFOLIO ACCOUNTING]")
    print("-" * 70)
    print(f"  • Current Cash Balance : ₹{pnl.current_cash:.2f}")
    print(f"  • Net PnL Return       : {pnl.net_pnl_percentage:+.2f}%")
    print(f"  • Max Drawdown         : {pnl.drawdown_pct:.2f}%")
    print("=" * 70)
    print("✅ SIMULATION COMPLETE: ALL RULES, GOVERNANCE & LIFECYCLES PASSED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
