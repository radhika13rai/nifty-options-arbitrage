"""
Market-Hours Routine & Institutional Intraday Lifecycle Scheduler.
Manages strict chronological market phases according to Indian Standard Time (IST):
  - 09:00 IST: Pre-Market Posture & Overnight Macro Intake
  - 09:15 IST: Market Opening Bell & Breakout Scanning Activation
  - 11:30 IST: Midday Stand-Down (Choppy Consolidation & Theta Trap Pause)
  - 13:30 IST: Afternoon Session & European Open Momentum Window
  - 15:15 IST: Mandatory Regulatory Intraday Square-Off (Zero Overnight Risk)
  - 15:35 IST: Post-Market Walk-Forward AI Adaptation & Audit Archival
Supports both live real-time wall-clock tracking and simulated fast-forward progression.
"""

import asyncio
import datetime
import logging
import time
from enum import Enum
from typing import Optional

from database import db_manager
from execution.auto_engine import auto_engine
from global_macro.poller import live_macro_poller
from global_macro.trainer import macro_trainer
from ml.engine import learning_engine
from portfolio.pnl import pnl_manager

logger = logging.getLogger("DailyScheduler")


class MarketPhase(str, Enum):
    PRE_MARKET_OPEN = "PRE_MARKET_OPEN"         # 09:00 - 09:15 IST
    MORNING_BREAKOUT = "MORNING_BREAKOUT"       # 09:15 - 11:30 IST
    MIDDAY_STAND_DOWN = "MIDDAY_STAND_DOWN"     # 11:30 - 13:30 IST
    AFTERNOON_SESSION = "AFTERNOON_SESSION"     # 13:30 - 15:15 IST
    MANDATORY_SQUARE_OFF = "MANDATORY_SQUARE_OFF" # 15:15 - 15:30 IST
    POST_MARKET_LEARN = "POST_MARKET_LEARN"     # 15:35+ IST
    MARKET_CLOSED = "MARKET_CLOSED"             # Off-hours & Weekends


class MarketRoutineScheduler:
    """
    Orchestrates automated daily transitions across institutional market phases.
    Ensures that zero positions are carried overnight, risk models adapt daily,
    and micro-capital is protected from midday option theta burn.
    """

    def __init__(self):
        self.current_phase: MarketPhase = MarketPhase.MARKET_CLOSED
        self.is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._simulated_mode: bool = False
        self.phase_history: list[dict] = []
        self.last_transition_time_ms: float = 0.0

    @property
    def is_trading_permitted(self) -> bool:
        """Trading is only active during high-conviction breakout sessions."""
        return self.current_phase in (MarketPhase.MORNING_BREAKOUT, MarketPhase.AFTERNOON_SESSION)

    def get_ist_now(self) -> datetime.datetime:
        """Current time in Indian Standard Time (UTC+5:30)."""
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        ist_offset = datetime.timedelta(hours=5, minutes=30)
        return utc_now + ist_offset

    def determine_current_phase(self, ist_dt: Optional[datetime.datetime] = None) -> MarketPhase:
        """Determines market phase based on IST clock time."""
        if ist_dt is None:
            ist_dt = self.get_ist_now()

        # Weekend check (5 = Saturday, 6 = Sunday)
        if ist_dt.weekday() >= 5:
            return MarketPhase.MARKET_CLOSED

        t = ist_dt.time()
        
        # 09:00:00 to 09:14:59
        if datetime.time(9, 0) <= t < datetime.time(9, 15):
            return MarketPhase.PRE_MARKET_OPEN
        # 09:15:00 to 11:29:59
        elif datetime.time(9, 15) <= t < datetime.time(11, 30):
            return MarketPhase.MORNING_BREAKOUT
        # 11:30:00 to 13:29:59
        elif datetime.time(11, 30) <= t < datetime.time(13, 30):
            return MarketPhase.MIDDAY_STAND_DOWN
        # 13:30:00 to 15:14:59
        elif datetime.time(13, 30) <= t < datetime.time(15, 15):
            return MarketPhase.AFTERNOON_SESSION
        # 15:15:00 to 15:29:59
        elif datetime.time(15, 15) <= t < datetime.time(15, 30):
            return MarketPhase.MANDATORY_SQUARE_OFF
        # 15:35:00 to 16:30:00
        elif datetime.time(15, 35) <= t < datetime.time(16, 30):
            return MarketPhase.POST_MARKET_LEARN
        else:
            return MarketPhase.MARKET_CLOSED

    async def execute_phase_transition(self, target_phase: MarketPhase) -> dict:
        """
        Executes the institutional action corresponding to the phase.
        """
        old_phase = self.current_phase
        self.current_phase = target_phase
        now_ms = time.time() * 1000.0
        self.last_transition_time_ms = now_ms

        logger.info(f"MarketRoutineScheduler: Transitioning {old_phase.value} -> {target_phase.value}")
        action_summary = {"from": old_phase.value, "to": target_phase.value, "actions": []}

        # 1. PRE_MARKET_OPEN (09:00 IST)
        if target_phase == MarketPhase.PRE_MARKET_OPEN:
            action_summary["actions"].append("POLL_MACRO_AND_RSS")
            poll_res = await live_macro_poller.poll_once()
            action_summary["macro_poll"] = poll_res
            auto_engine.disable()  # Hold execution until 09:15 bell

            await db_manager.record_audit_log(
                event_type="SCHEDULE_PRE_MARKET",
                severity="INFO",
                component="MarketScheduler",
                details=f"Pre-market routine executed. Macro gap: {poll_res.get('gap_pts', 0)} pts."
            )

        # 2. MORNING_BREAKOUT (09:15 IST)
        elif target_phase == MarketPhase.MORNING_BREAKOUT:
            action_summary["actions"].append("ENABLE_AUTO_EXECUTION")
            auto_engine.enable()

            await db_manager.record_audit_log(
                event_type="SCHEDULE_MARKET_OPEN",
                severity="INFO",
                component="MarketScheduler",
                details="09:15 IST Market Opening Bell. Morning breakout scanning enabled."
            )

        # 3. MIDDAY_STAND_DOWN (11:30 IST)
        elif target_phase == MarketPhase.MIDDAY_STAND_DOWN:
            action_summary["actions"].append("STAND_DOWN_PAUSE_NEW_ENTRIES")
            # Stand down: disable new breakout entries to prevent theta churn
            auto_engine.disable()

            await db_manager.record_audit_log(
                event_type="SCHEDULE_MIDDAY_STAND_DOWN",
                severity="INFO",
                component="MarketScheduler",
                details="11:30 IST Lunch chop stand-down. Paused new entry signals."
            )

        # 4. AFTERNOON_SESSION (13:30 IST)
        elif target_phase == MarketPhase.AFTERNOON_SESSION:
            action_summary["actions"].append("RESUME_AFTERNOON_ENTRIES")
            auto_engine.enable()

            await db_manager.record_audit_log(
                event_type="SCHEDULE_AFTERNOON_OPEN",
                severity="INFO",
                component="MarketScheduler",
                details="13:30 IST European Open session. Resumed breakout execution."
            )

        # 5. MANDATORY_SQUARE_OFF (15:15 IST)
        elif target_phase == MarketPhase.MANDATORY_SQUARE_OFF:
            action_summary["actions"].append("EXECUTE_1515_SQUARE_OFF")
            auto_engine.disable()
            sq_results = await auto_engine.mandatory_intraday_square_off()
            action_summary["squared_off_trades"] = sq_results

            await db_manager.record_audit_log(
                event_type="SCHEDULE_MANDATORY_SQUARE_OFF",
                severity="WARNING",
                component="MarketScheduler",
                details=f"15:15 IST Regulatory Square-Off: Liquidated {len(sq_results)} open positions."
            )

        # 6. POST_MARKET_LEARN (15:35 IST)
        elif target_phase == MarketPhase.POST_MARKET_LEARN:
            action_summary["actions"].append("RUN_WALK_FORWARD_ADAPTATION")
            auto_engine.disable()
            
            # 1. Walk-forward epoch progression (trades are learned in real-time on exit)
            adapt_metrics = learning_engine.run_daily_adaptation_step([])
            action_summary["adaptation_epoch"] = adapt_metrics.epoch

            # 2. Retrain multimodal weights on macro historical set
            train_res = macro_trainer.train_on_dataset()
            action_summary["multimodal_accuracy"] = train_res.directional_accuracy

            # 3. PnL report
            pnl_report = pnl_manager.generate_report()
            action_summary["closing_net_pnl"] = pnl_report.net_pnl
            action_summary["total_friction"] = pnl_report.total_friction_inr

            await db_manager.record_audit_log(
                event_type="SCHEDULE_POST_MARKET_LEARN",
                severity="INFO",
                component="MarketScheduler",
                details=f"Post-market learning complete. Epoch: {adapt_metrics.epoch} | Net PnL: ₹{pnl_report.net_pnl:.2f}."
            )

        # 7. MARKET_CLOSED
        elif target_phase == MarketPhase.MARKET_CLOSED:
            action_summary["actions"].append("MARKET_CLOSED_REST")
            auto_engine.disable()

        self.phase_history.append({
            "phase": target_phase.value,
            "timestamp_ms": now_ms,
            "actions": action_summary["actions"]
        })
        if len(self.phase_history) > 20:
            self.phase_history.pop(0)

        return action_summary

    async def _scheduler_loop(self):
        """Continuous monitor that checks IST clock every 15 seconds."""
        while self.is_running:
            try:
                if not self._simulated_mode:
                    expected_phase = self.determine_current_phase()
                    if expected_phase != self.current_phase:
                        await self.execute_phase_transition(expected_phase)
                await asyncio.sleep(15.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(5.0)

    async def start(self):
        """Starts the routine scheduler."""
        if self.is_running:
            return
        self.is_running = True
        logger.info("Starting MarketRoutineScheduler...")
        # Determine initial phase immediately
        initial_phase = self.determine_current_phase()
        await self.execute_phase_transition(initial_phase)
        self._task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """Stops the routine scheduler."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("MarketRoutineScheduler stopped.")

    def set_simulated_mode(self, enabled: bool):
        """Enables manual or test-driven phase transitions."""
        self._simulated_mode = enabled

    def get_status(self) -> dict:
        """Returns live scheduler telemetry."""
        ist_now = self.get_ist_now()
        return {
            "current_phase": self.current_phase.value,
            "is_trading_permitted": self.is_trading_permitted,
            "ist_time": ist_now.strftime("%Y-%m-%d %H:%M:%S IST"),
            "is_running": self.is_running,
            "is_simulated_mode": self._simulated_mode,
            "phase_history": self.phase_history[-6:]
        }


# Singleton instance
market_scheduler = MarketRoutineScheduler()
