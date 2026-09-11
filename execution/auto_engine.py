"""
Autonomous Execution & Dynamic Trailing Stop Lifecycle Engine.
Orchestrates autonomous order dispatching, dynamic ratchet trailing stops (Breakeven, Profit Lock,
1:2 and 1:3 R:R tiers), time-stop expiration, and closed-loop reinforcement learning updates.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Literal, Optional

from broker.interface import BrokerOrderRequest, BrokerOrderResponse
from execution.paper_broker import paper_broker
from execution.order_manager import order_manager
from strategies.base import TradingSignal
from market_data.normalizer import MarketTick
from portfolio.positions import position_tracker
from costs.transaction_costs import cost_engine
from ml.learner import learning_engine
from ml.drift_guard import drift_guard
from database.db import db_manager

logger = logging.getLogger("AutoExecutionEngine")


@dataclass
class ManagedTrade:
    """Represents an active, autonomously managed options position."""
    trade_id: str
    symbol: str
    option_type: Literal["CE", "PE"]
    side: Literal["BUY"]
    quantity: int
    entry_price: float
    entry_time_ms: float
    current_stop_price: float
    target_price: float
    state: Literal[
        "STATE_0_INCEPTION",
        "STATE_1_BREAKEVEN",
        "STATE_2_PROFIT_LOCK",
        "STATE_3_RR_1_2",
        "STATE_4_EXITED"
    ]
    highest_price_seen: float
    features_at_entry: list[float]
    strategy_name: str
    last_update_time_ms: float = field(default_factory=lambda: time.time() * 1000.0)
    exit_reason: Optional[str] = None


class AutoExecutionEngine:
    """
    Autonomous position manager implementing the institutional Options Trader playbook:
    - Automatically executes approved ML breakout signals
    - Ratchets trailing stop loss to Breakeven (+0.80 pts) at +1.50 pts move (risk-free)
    - Locks in profits at +3.20 pts (+1.80 pts stop) and +4.60 pts (+3.20 pts stop)
    - Captures 1:3 R:R targets (+6.90 pts move)
    - Enforces 15-minute time stop and 15:15 IST mandatory square-off
    - Automatically feeds back realized Net P&L into Recursive Least Squares & Bayesian Samplers
    """

    def __init__(self):
        self.is_auto_trading_enabled: bool = True
        self._active_trades: dict[str, ManagedTrade] = {}
        self._trade_history: list[dict] = []

    def enable(self) -> None:
        """Enables automated execution and position management."""
        self.is_auto_trading_enabled = True
        logger.info("AutoExecutionEngine: Autonomous trading ENABLED")

    def disable(self) -> None:
        """Disables new automated entries (existing positions continue trailing)."""
        self.is_auto_trading_enabled = False
        logger.info("AutoExecutionEngine: Autonomous trading DISABLED")

    async def handle_signal(self, signal: TradingSignal) -> Optional[BrokerOrderResponse]:
        """
        Processes an incoming signal from the ML strategy.
        Under the ₹3,000 capital baseline, only 1 position (65 units) is allowed at any time.
        """
        if not self.is_auto_trading_enabled:
            return None

        if not signal.is_capital_feasible or signal.action != "BUY":
            return None

        # Capital Invariant: Max 1 lot active trade under ₹3,000 capital
        if len(self._active_trades) >= 1:
            logger.debug("AutoExecutionEngine: Signal ignored - already holding active position")
            return None

        # Check if already holding this symbol
        if signal.symbol in self._active_trades:
            return None

        logger.info(
            f"AutoExecutionEngine: Dispatching signal {signal.signal_id} on {signal.symbol} @ ₹{signal.suggested_price}"
        )

        resp = await order_manager.execute_signal(signal)
        if not resp or resp.status != "FILLED":
            return resp

        # Create ManagedTrade state machine
        fill_price = resp.fill_price
        opt_type = signal.metadata.get("option_type", "CE" if "_CE" in signal.symbol else "PE")
        feats = signal.metadata.get("features", [0.0] * 8)

        # Initial stop: -2.30 points (max risk ₹149.50 <= ₹150 limit)
        initial_stop = round(max(0.05, fill_price - 2.30), 2)
        # 1:3 R:R target: +6.90 points
        target_price = round(fill_price + 6.90, 2)

        managed_trade = ManagedTrade(
            trade_id=resp.order_id,
            symbol=signal.symbol,
            option_type=opt_type,
            side="BUY",
            quantity=signal.quantity,
            entry_price=fill_price,
            entry_time_ms=time.time() * 1000.0,
            current_stop_price=initial_stop,
            target_price=target_price,
            state="STATE_0_INCEPTION",
            highest_price_seen=fill_price,
            features_at_entry=feats,
            strategy_name=signal.strategy_name
        )

        self._active_trades[signal.symbol] = managed_trade
        logger.info(
            f"AutoExecutionEngine: Managed trade started for {signal.symbol}: "
            f"Entry=₹{fill_price:.2f}, Stop=₹{initial_stop:.2f}, Target=₹{target_price:.2f}"
        )
        return resp

    async def on_tick(self, tick: MarketTick) -> Optional[dict]:
        """
        Evaluates active positions tick-by-tick against the Ratchet Trailing Stop State Machine.
        """
        trade = self._active_trades.get(tick.symbol)
        if not trade:
            return None

        current_price = tick.ltp
        now_ms = time.time() * 1000.0
        trade.last_update_time_ms = now_ms
        trade.highest_price_seen = max(trade.highest_price_seen, current_price)

        delta_pts = round(current_price - trade.entry_price, 2)
        elapsed_sec = (now_ms - trade.entry_time_ms) / 1000.0

        # --- RULE 1: Stop-Loss Breach (Hard stop or ratcheted trailing stop) ---
        if current_price <= trade.current_stop_price:
            reason = f"STOP_TRIGGERED ({current_price:.2f} <= {trade.current_stop_price:.2f})"
            return await self._exit_trade(trade, current_price, reason)

        # --- RULE 2: Full 1:3 R:R Target Reached ---
        if current_price >= trade.target_price:
            reason = f"TARGET_1_3_REACHED (+{delta_pts:.2f} pts >= +6.90 pts)"
            return await self._exit_trade(trade, current_price, reason)

        # --- RULE 3: 15-Minute Time Stop (Mitigates Option Theta Decay) ---
        if elapsed_sec >= 900.0 and delta_pts < 1.50:  # 15 mins with no breakout
            reason = f"TIME_STOP_EXPIRED (15 mins elapsed, gain {delta_pts:.2f} < 1.50 pts)"
            return await self._exit_trade(trade, current_price, reason)

        # --- RULE 4: Dynamic Ratchet Trailing Progression ---
        # Tier 3: 1:2 R:R achieved (+4.60 pts move) -> Ratchet stop to entry + 3.20 pts (locks +₹156 net)
        if delta_pts >= 4.60 and trade.state != "STATE_3_RR_1_2":
            trade.state = "STATE_3_RR_1_2"
            new_stop = round(trade.entry_price + 3.20, 2)
            if new_stop > trade.current_stop_price:
                trade.current_stop_price = new_stop
                logger.info(f"AutoExecutionEngine: RATCHET TIER 3 (1:2 R:R) -> Stop raised to ₹{new_stop:.2f}")

        # Tier 2: Profit Lock achieved (+3.20 pts move) -> Ratchet stop to entry + 1.80 pts (locks +₹65 net)
        elif delta_pts >= 3.20 and trade.state not in ("STATE_2_PROFIT_LOCK", "STATE_3_RR_1_2"):
            trade.state = "STATE_2_PROFIT_LOCK"
            new_stop = round(trade.entry_price + 1.80, 2)
            if new_stop > trade.current_stop_price:
                trade.current_stop_price = new_stop
                logger.info(f"AutoExecutionEngine: RATCHET TIER 2 (Profit Lock) -> Stop raised to ₹{new_stop:.2f}")

        # Tier 1: Breakeven achieved (+1.50 pts move) -> Ratchet stop to entry + 0.80 pts (RISK FREE: covers ₹52 fee)
        elif delta_pts >= 1.50 and trade.state == "STATE_0_INCEPTION":
            trade.state = "STATE_1_BREAKEVEN"
            new_stop = round(trade.entry_price + 0.80, 2)
            if new_stop > trade.current_stop_price:
                trade.current_stop_price = new_stop
                logger.info(f"AutoExecutionEngine: RATCHET TIER 1 (Breakeven) -> Stop raised to ₹{new_stop:.2f} (RISK-FREE)")

        return {
            "symbol": trade.symbol,
            "state": trade.state,
            "ltp": current_price,
            "stop": trade.current_stop_price,
            "delta_pts": round(delta_pts, 2),
            "elapsed_sec": round(elapsed_sec, 1)
        }

    async def _exit_trade(self, trade: ManagedTrade, exit_price: float, reason: str) -> dict:
        """
        Executes marketable exit order, computes fee-adjusted net PnL,
        and feeds the realized trade outcome into the online learning engine.
        """
        logger.info(f"AutoExecutionEngine: Closing trade {trade.symbol} @ ₹{exit_price:.2f} | Reason: {reason}")
        trade.state = "STATE_4_EXITED"
        trade.exit_reason = reason

        exit_req = BrokerOrderRequest(
            symbol=trade.symbol,
            side="SELL",
            order_type="MARKET",
            quantity=trade.quantity,
            price=exit_price,
            client_order_id=f"EXT_{trade.trade_id[:6]}_{int(time.time()*1000)}_{str(uuid.uuid4())[:4]}"
        )

        resp = await paper_broker.place_order(exit_req)
        actual_fill_price = resp.fill_price if resp and resp.status == "FILLED" else exit_price

        # Calculate exact fee-adjusted Net P&L
        points_moved = round(actual_fill_price - trade.entry_price, 2)
        gross_pnl = round(points_moved * trade.quantity, 2)
        
        # Round trip costs
        rt_costs = cost_engine.calculate_round_trip(
            entry_side="BUY",
            entry_price=trade.entry_price,
            exit_price=actual_fill_price,
            quantity=trade.quantity
        )
        net_pnl = round(gross_pnl - rt_costs.total_friction, 2)

        # --- CLOSED-LOOP LEARNING FEEDBACK ---
        # Train RLS weights and Bayesian Beta-Binomial samplers on the real outcome
        learning_engine.learn_from_trade(
            features=trade.features_at_entry,
            option_type=trade.option_type,
            actual_points_moved=points_moved,
            actual_net_pnl=net_pnl
        )

        # Monitor Model Drift & Automatic Rollback Guard
        drift_guard.record_trade(
            net_pnl=net_pnl,
            gross_pnl=gross_pnl,
            points_moved=points_moved
        )
        await drift_guard.evaluate_and_enforce()

        # Audit log into SQLite
        await db_manager.record_audit_log(
            event_type="AUTO_TRADE_EXIT",
            severity="INFO" if net_pnl >= 0 else "WARNING",
            component="AutoExecutionEngine",
            details=f"Exit {trade.symbol} @ ₹{actual_fill_price:.2f} | Pts: {points_moved:+.2f} | Net: ₹{net_pnl:+.2f} | Reason: {reason}"
        )

        result_summary = {
            "symbol": trade.symbol,
            "entry_price": trade.entry_price,
            "exit_price": actual_fill_price,
            "points_moved": points_moved,
            "gross_pnl": gross_pnl,
            "total_fees": rt_costs.total_friction,
            "net_pnl": net_pnl,
            "reason": reason,
            "duration_sec": round((time.time() * 1000.0 - trade.entry_time_ms) / 1000.0, 1)
        }

        # Remove from active trades and archive
        self._active_trades.pop(trade.symbol, None)
        self._trade_history.append(result_summary)
        return result_summary

    async def mandatory_intraday_square_off(self) -> list[dict]:
        """Liquidates all active positions at market close (15:15 IST)."""
        results = []
        for symbol, trade in list(self._active_trades.items()):
            pos = position_tracker.mark_to_market(symbol, trade.entry_price)
            ltp = pos.current_price if pos else trade.entry_price
            res = await self._exit_trade(trade, ltp, "MANDATORY_INTRADAY_SQUARE_OFF_1515")
            results.append(res)
        return results

    def get_status(self) -> dict:
        """Returns live auto-execution telemetry."""
        trades_info = []
        now_ms = time.time() * 1000.0
        for sym, t in self._active_trades.items():
            pos = position_tracker.mark_to_market(sym, t.entry_price)
            current_price = pos.current_price if pos else t.entry_price
            delta_pts = round(current_price - t.entry_price, 2)
            trades_info.append({
                "trade_id": t.trade_id,
                "symbol": t.symbol,
                "option_type": t.option_type,
                "quantity": t.quantity,
                "entry_price": t.entry_price,
                "current_price": current_price,
                "stop_price": t.current_stop_price,
                "target_price": t.target_price,
                "state": t.state,
                "delta_pts": delta_pts,
                "elapsed_sec": round((now_ms - t.entry_time_ms) / 1000.0, 1)
            })

        return {
            "is_enabled": self.is_auto_trading_enabled,
            "active_trade_count": len(self._active_trades),
            "active_trades": trades_info,
            "total_executed_trades": len(self._trade_history),
            "recent_history": self._trade_history[-5:]
        }


auto_engine = AutoExecutionEngine()
