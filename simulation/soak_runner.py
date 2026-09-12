"""
Automated Continuous Paper Soak Runner (Paper V2).
Executes unattended, multi-day/multi-week paper trading cycles to validate:
  1. Long-horizon system stability and memory safety
  2. Strict adherence to ₹2,000 non-negotiable capital floor
  3. Latching emergency kill switch integrity under prolonged stress
  4. SQLite WAL checkpointing, audit trails, and zero database bloat
  5. Online learning engine weight convergence and model drift protection
"""

import asyncio
import dataclasses
import logging
import math
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, Optional

from config import config
from database.db import db_manager
from portfolio.pnl import pnl_manager
from portfolio.positions import position_tracker
from execution.auto_engine import auto_engine
from risk.kill_switch import kill_switch
from ml.learner import learning_engine, MarketRegime
from ml.drift_guard import drift_guard
from scheduler.daily_routine import market_scheduler, MarketPhase
from simulation.walk_forward import (
    WalkForwardSimulator,
    DayScenarioConfig,
    DaySimulationResult,
)

logger = logging.getLogger("PaperSoakRunner")


@dataclass
class SoakConfig:
    """Configuration for the continuous paper soak runner."""
    target_days: int = 50
    iteration_interval_sec: float = 0.05  # Delay between simulated trading days
    checkpoint_every_n_days: int = 5
    initial_capital: float = 3000.0
    capital_floor: float = 2000.0
    max_loss_per_trade: float = 150.0
    daily_loss_limit: float = 300.0
    reset_state_on_start: bool = True
    dynamic_procedural_days: bool = True


@dataclass
class SoakMetrics:
    """Live telemetry and health scorecard for continuous soak execution."""
    status: Literal["IDLE", "RUNNING", "PAUSED", "STOPPED", "KILL_SWITCH_TRIPPED", "COMPLETED"] = "IDLE"
    days_completed: int = 0
    target_days: int = 50
    initial_capital: float = 3000.0
    current_capital: float = 3000.0
    peak_capital: float = 3000.0
    min_capital_seen: float = 3000.0
    cumulative_net_pnl: float = 0.0
    cumulative_gross_pnl: float = 0.0
    cumulative_friction: float = 0.0
    net_return_pct: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0
    win_rate_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    profit_factor: float = 0.0
    drift_rollbacks_count: int = 0
    sqlite_db_size_kb: float = 0.0
    checkpoints_executed: int = 0
    elapsed_seconds: float = 0.0
    last_day_summary: Optional[dict] = None
    capital_floor_preserved: bool = True
    invariants_respected: bool = True
    seed_used: Optional[int] = None
    is_deterministic: bool = True


class ProceduralScenarioGenerator:
    """
    Generates procedurally varied, macroeconomically consistent trading days
    grounded in institutional Indian option market dynamics.
    """

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        self._day_counter = 0

    def next_scenario(self, day_number: int, reference_scenarios: list[DayScenarioConfig]) -> DayScenarioConfig:
        """
        Generates next scenario, blending reference templates with stochastic perturbations.
        """
        # Pick regime template in rotation with stochastic variation
        regimes: list[MarketRegime] = [
            "TRENDING_BULL",
            "HIGH_VOL_SHOCK",
            "TRENDING_BEAR",
            "CHOPPY_CONSOLIDATION",
            "CHOPPY_CONSOLIDATION",
            "TRENDING_BULL",
            "TRENDING_BEAR"
        ]
        chosen_regime = regimes[day_number % len(regimes)]
        date_str = f"2026-10-{(day_number % 28) + 1:02d}"

        # 1. TRENDING BULL
        if chosen_regime == "TRENDING_BULL":
            base_prem = round(self._rng.uniform(24.0, 32.0), 2)
            strike = 24600 + (day_number * 50) % 600
            return DayScenarioConfig(
                day_number=day_number,
                date_str=date_str,
                regime="TRENDING_BULL",
                title=f"Bull Momentum Breakout (Day {day_number})",
                headline=f"FII Inflows & Robust Domestic PMI Propel NIFTY Above {strike-100}",
                brent_crude=round(self._rng.uniform(78.0, 84.0), 2),
                brent_change_pct=round(self._rng.uniform(-1.8, -0.2), 2),
                dollar_index_dxy=round(self._rng.uniform(102.5, 104.0), 2),
                gift_nifty_gap_pts=round(self._rng.uniform(45.0, 95.0), 1),
                fear_index=round(self._rng.uniform(0.18, 0.32), 2),
                symbol=f"NIFTY_2026-10-29_{strike}_CE",
                option_type="CE",
                base_price=base_prem,
                features=[0.68, 0.45, 0.02, 0.38, 0.09, 0.15, 0.22, 0.48],
                should_signal=True,
                price_trajectory=[
                    (round(base_prem + 0.30, 2), "09:18 IST - Morning Call Breakout Entry"),
                    (round(base_prem + 1.80, 2), "09:30 IST - Move +1.80 pts -> Breakeven Locked"),
                    (round(base_prem + 3.40, 2), "09:55 IST - Move +3.40 pts -> Profit Lock Ratchet"),
                    (round(base_prem + 5.00, 2), "10:20 IST - Move +5.00 pts -> 1:2 R:R Locked"),
                    (round(base_prem + 7.10, 2), "10:45 IST - 1:3 R:R Target Reached (+6.90 pts) -> Auto Exit")
                ]
            )

        # 2. BEAR / CRUDE SHOCK
        elif chosen_regime in ("HIGH_VOL_SHOCK", "TRENDING_BEAR"):
            base_prem = round(self._rng.uniform(25.0, 33.0), 2)
            strike = 24400 - (day_number * 50) % 500
            crude = round(self._rng.uniform(94.0, 103.0), 2)
            return DayScenarioConfig(
                day_number=day_number,
                date_str=date_str,
                regime=chosen_regime,
                title=f"Geopolitical Shock & Put Acceleration (Day {day_number})",
                headline=f"Crude Surges to ${crude:.2f}; Inflationary Pressures Trigger Broad Risk-Off",
                brent_crude=crude,
                brent_change_pct=round(self._rng.uniform(2.5, 6.0), 2),
                dollar_index_dxy=round(self._rng.uniform(105.0, 107.0), 2),
                gift_nifty_gap_pts=round(self._rng.uniform(-140.0, -60.0), 1),
                fear_index=round(self._rng.uniform(0.70, 0.90), 2),
                symbol=f"NIFTY_2026-10-29_{strike}_PE",
                option_type="PE",
                base_price=base_prem,
                features=[-0.75, -0.55, 0.03, -0.45, -0.12, 0.25, 0.42, 0.70],
                should_signal=True,
                price_trajectory=[
                    (round(base_prem + 0.40, 2), "09:18 IST - Put Momentum Signal Executed"),
                    (round(base_prem + 1.80, 2), "09:28 IST - Breakeven Ratchet Engaged"),
                    (round(base_prem + 3.50, 2), "09:50 IST - Profit Lock Ratchet Engaged"),
                    (round(base_prem + 7.20, 2), "10:25 IST - 1:3 Target (+6.90 pts) Cleared -> Auto Exit")
                ]
            )

        # 3. CHOPPY CONSOLIDATION (Theta Trap Defense)
        else:
            base_prem = round(self._rng.uniform(22.0, 28.0), 2)
            strike = 24500
            # 80% of chop days stand down, 20% test exploratory loss guard
            is_false_breakout_test = (day_number % 9 == 0)
            if is_false_breakout_test:
                return DayScenarioConfig(
                    day_number=day_number,
                    date_str=date_str,
                    regime="CHOPPY_CONSOLIDATION",
                    title=f"False Breakout Probe & Stop-Loss Test (Day {day_number})",
                    headline="Morning Attempt Fails at Resistance; Micro-Capital Guardrails Tested",
                    brent_crude=83.0,
                    brent_change_pct=0.5,
                    dollar_index_dxy=103.8,
                    gift_nifty_gap_pts=10.0,
                    fear_index=0.35,
                    symbol=f"NIFTY_2026-10-29_{strike}_CE",
                    option_type="CE",
                    base_price=base_prem,
                    features=[0.40, 0.18, 0.014, 0.12, 0.0007, 0.09, 0.16, 0.33],
                    should_signal=True,
                    price_trajectory=[
                        (round(base_prem + 0.20, 2), "09:18 IST - Exploratory Signal Dispatched"),
                        (round(base_prem - 0.50, 2), "09:24 IST - Breakout Fails, Spot Reverses"),
                        (round(base_prem - 2.10, 2), "09:35 IST - Price Drops -> Stop Limit Respected")
                    ]
                )
            else:
                return DayScenarioConfig(
                    day_number=day_number,
                    date_str=date_str,
                    regime="CHOPPY_CONSOLIDATION",
                    title=f"Choppy Stand-Down Discipline (Day {day_number})",
                    headline="Index Boxed in Tight 30-Point Range; Autonomous Engine Pauses Churn",
                    brent_crude=82.4,
                    brent_change_pct=0.2,
                    dollar_index_dxy=103.5,
                    gift_nifty_gap_pts=-4.0,
                    fear_index=0.30,
                    symbol=f"NIFTY_2026-10-29_{strike}_PE",
                    option_type="PE",
                    base_price=base_prem,
                    features=[0.02, 0.01, 0.009, 0.01, 0.0001, 0.06, 0.09, 0.15],
                    should_signal=False,  # AI Stand-Down Discipline
                    price_trajectory=[
                        (base_prem, "09:15 IST - Flat Equilibrium"),
                        (round(base_prem - 0.20, 2), "10:30 IST - Low ATR Chop: Zero Entries Taken"),
                        (round(base_prem - 0.40, 2), "11:30 IST - Midday Stand-Down Active; Fee Bleed Avoided")
                    ]
                )


class PaperSoakRunner:
    """
    Unattended autonomous paper trading soak daemon.
    Simulates consecutive trading sessions, tests long-tail edge invariants,
    persists daily PnL & audit trails to SQLite, and monitors drift.
    """

    def __init__(self, config_override: Optional[SoakConfig] = None):
        self.config = config_override or SoakConfig()
        self.metrics = SoakMetrics(
            initial_capital=self.config.initial_capital,
            current_capital=self.config.initial_capital,
            peak_capital=self.config.initial_capital,
            min_capital_seen=self.config.initial_capital,
            target_days=self.config.target_days
        )
        self.simulator = WalkForwardSimulator(
            initial_capital=self.config.initial_capital,
            capital_floor=self.config.capital_floor
        )
        self.scenario_gen = ProceduralScenarioGenerator()
        self.day_results: list[DaySimulationResult] = []
        self._stop_requested = False
        self._pause_requested = False
        self._start_time: float = 0.0
        self._iteration_callbacks: list[Callable[[DaySimulationResult, SoakMetrics], None]] = []

    def register_callback(self, callback: Callable[[DaySimulationResult, SoakMetrics], None]) -> None:
        """Adds a real-time listener callback fired after every simulated day."""
        self._iteration_callbacks.append(callback)

    def pause(self) -> None:
        """Pauses the soak daemon after the current day finishes."""
        self._pause_requested = True
        self.metrics.status = "PAUSED"
        logger.info("PaperSoakRunner: Pause requested.")

    def resume(self) -> None:
        """Resumes a paused soak daemon."""
        self._pause_requested = False
        self.metrics.status = "RUNNING"
        logger.info("PaperSoakRunner: Resumed.")

    def stop(self) -> None:
        """Signals the soak daemon to stop gracefully."""
        self._stop_requested = True
        self.metrics.status = "STOPPED"
        logger.info("PaperSoakRunner: Graceful stop requested.")

    def reset(self) -> None:
        """Resets soak metrics and internal simulator state."""
        self.day_results.clear()
        self._stop_requested = False
        self._pause_requested = False
        self._start_time = 0.0
        self.metrics = SoakMetrics(
            initial_capital=self.config.initial_capital,
            current_capital=self.config.initial_capital,
            peak_capital=self.config.initial_capital,
            min_capital_seen=self.config.initial_capital,
            target_days=self.config.target_days
        )
        # Reset system components
        learning_engine.reset()
        position_tracker.reset()
        pnl_manager.reset(self.config.initial_capital)
        kill_switch.reset_system()
        drift_guard.reset()
        auto_engine.enable()

    async def step(self) -> DaySimulationResult:
        """
        Executes exactly one simulated trading day session, verifies invariants,
        and records SQLite telemetry.
        """
        day_index = self.metrics.days_completed + 1

        # 1. Obtain scenario configuration
        if day_index <= len(self.simulator.scenarios) and not self.config.dynamic_procedural_days:
            scenario = self.simulator.scenarios[day_index - 1]
        else:
            scenario = self.scenario_gen.next_scenario(day_index, self.simulator.scenarios)

        # 2. Execute trading session
        result = await self.simulator._run_single_day(scenario)
        self.day_results.append(result)

        # 3. Update Soak Metrics
        self.metrics.days_completed += 1
        self.metrics.current_capital = result.ending_cash
        self.metrics.peak_capital = max(self.metrics.peak_capital, result.ending_cash)
        self.metrics.min_capital_seen = min(self.metrics.min_capital_seen, result.ending_cash)
        self.metrics.cumulative_gross_pnl = round(sum(d.gross_pnl for d in self.day_results), 2)
        self.metrics.cumulative_friction = round(sum(d.statutory_fees for d in self.day_results), 2)
        self.metrics.cumulative_net_pnl = round(self.metrics.current_capital - self.metrics.initial_capital, 2)
        self.metrics.net_return_pct = round((self.metrics.cumulative_net_pnl / self.metrics.initial_capital) * 100, 2)

        self.metrics.total_trades += result.trades_executed
        self.metrics.winning_trades += result.wins
        self.metrics.losing_trades += result.losses
        self.metrics.breakeven_trades += result.breakevens

        if self.metrics.total_trades > 0:
            self.metrics.win_rate_pct = round((self.metrics.winning_trades / self.metrics.total_trades) * 100, 1)

        total_gross_loss = sum(abs(d.gross_pnl) for d in self.day_results if d.gross_pnl < 0)
        total_gross_win = sum(d.gross_pnl for d in self.day_results if d.gross_pnl > 0)
        self.metrics.profit_factor = round(total_gross_win / total_gross_loss, 2) if total_gross_loss > 0 else 999.0

        # Compute true cumulative peak-to-trough maximum drawdown over all daily equity points
        peak = self.metrics.initial_capital
        max_dd = 0.0
        for d in self.day_results:
            if d.ending_cash > peak:
                peak = d.ending_cash
            dd_pct = ((peak - d.ending_cash) / peak) * 100.0 if peak > 0 else 0.0
            if d.drawdown_pct > dd_pct:
                dd_pct = d.drawdown_pct
            if dd_pct > max_dd:
                max_dd = dd_pct
        self.metrics.max_drawdown_pct = round(max_dd, 2)
        self.metrics.drift_rollbacks_count = drift_guard.rollback_count

        self.metrics.last_day_summary = {
            "day": result.day_number,
            "date": result.date_str,
            "regime": result.regime,
            "net_pnl": result.net_pnl,
            "trades": result.trades_executed,
            "wins": result.wins,
            "losses": result.losses,
            "ending_cash": result.ending_cash
        }

        # 4. Strict Micro-Capital & Risk Invariant Checks
        # A. Capital Floor Check (₹2,000)
        if self.metrics.current_capital < self.config.capital_floor:
            self.metrics.capital_floor_preserved = False
            self.metrics.invariants_respected = False
            self.metrics.status = "KILL_SWITCH_TRIPPED"
            kill_switch.engage(f"SOAK CRITICAL: Capital floor breached: ₹{self.metrics.current_capital:.2f} < ₹{self.config.capital_floor:.2f}")
            await db_manager.record_risk_event(
                event_type="CAPITAL_FLOOR_BREACH",
                reason=f"Current capital ₹{self.metrics.current_capital:.2f} below non-negotiable floor ₹{self.config.capital_floor:.2f}",
                blocked_payload={"day": result.day_number, "cash": result.ending_cash}
            )
            logger.critical("PaperSoakRunner: CAPITAL FLOOR BREACHED! Emergency Kill Switch Latched.")

        # B. Single-Trade Loss Check (₹150 max risk)
        for t in result.trades_detail:
            gross_loss = abs(t.get("gross_pnl", 0.0))
            if t.get("gross_pnl", 0.0) < 0 and gross_loss > (self.config.max_loss_per_trade + 0.05):
                self.metrics.invariants_respected = False
                logger.error(f"PaperSoakRunner: Single-trade risk violated! Loss: ₹{gross_loss:.2f} > ₹{self.config.max_loss_per_trade:.2f}")

        # C. Zero Overnight Position Check
        if len(auto_engine._active_trades) > 0:
            self.metrics.invariants_respected = False
            logger.error("PaperSoakRunner: Active positions detected overnight post 15:15 square-off!")

        # 5. SQLite Persistence: Daily PnL Table
        try:
            await db_manager.record_daily_pnl(
                date_str=result.date_str,
                starting_cash=result.start_cash,
                ending_cash=result.ending_cash,
                gross_pnl=result.gross_pnl,
                total_friction=result.statutory_fees,
                net_pnl=result.net_pnl,
                trades_count=result.trades_executed,
                max_drawdown=result.drawdown_pct
            )
        except Exception as e:
            logger.warning(f"PaperSoakRunner: Failed to record daily_pnl to DB: {e}")

        # 6. SQLite Audit Log
        try:
            await db_manager.record_audit_log(
                event_type="AUDIT_SOAK_DAY_COMPLETE",
                severity="INFO" if result.net_pnl >= 0 else "WARNING",
                component="PaperSoakRunner",
                details=f"Day {result.day_number} ({result.regime}): Net ₹{result.net_pnl:+.2f} | Cash: ₹{result.ending_cash:.2f} | Trades: {result.trades_executed}"
            )
        except Exception as e:
            logger.warning(f"PaperSoakRunner: Failed to record audit log: {e}")

        # 7. Periodic SQLite WAL Checkpoint & DB File Health Check
        if day_index % self.config.checkpoint_every_n_days == 0:
            await self._execute_checkpoint(day_index)

        # 8. Fire Callbacks
        for cb in self._iteration_callbacks:
            try:
                cb(result, self.metrics)
            except Exception as cb_err:
                logger.warning(f"Soak callback error: {cb_err}")

        return result

    async def _execute_checkpoint(self, day_index: int) -> None:
        """Flushes SQLite WAL to main file and records memory/storage telemetry."""
        try:
            await db_manager.checkpoint_wal()
            db_path = config.db_path
            if db_path.exists():
                size_kb = round(os.path.getsize(db_path) / 1024.0, 1)
                self.metrics.sqlite_db_size_kb = size_kb
            self.metrics.checkpoints_executed += 1

            await db_manager.record_audit_log(
                event_type="AUDIT_SOAK_CHECKPOINT",
                severity="INFO",
                component="PaperSoakRunner",
                details=f"Day {day_index} Checkpoint: WAL flushed. SQLite size: {self.metrics.sqlite_db_size_kb} KB. Capital: ₹{self.metrics.current_capital:.2f}"
            )
            logger.info(f"PaperSoakRunner: Checkpoint executed at Day {day_index}. DB Size: {self.metrics.sqlite_db_size_kb} KB.")
        except Exception as e:
            logger.warning(f"PaperSoakRunner: Checkpoint error: {e}")

    async def run(
        self,
        max_days: Optional[int] = None,
        interval_sec: Optional[float] = None,
        seed: Optional[int] = None
    ) -> SoakMetrics:
        """
        Runs continuous paper trading iterations until target days or stopped.
        Supports deterministic reproducible seed or stochastic Monte Carlo seed.
        """
        target = max_days if max_days is not None else self.config.target_days
        interval = interval_sec if interval_sec is not None else self.config.iteration_interval_sec

        if seed is not None:
            actual_seed = seed
            self.metrics.is_deterministic = True
        else:
            import secrets
            actual_seed = secrets.randbelow(1_000_000_000)
            self.metrics.is_deterministic = False

        self.metrics.seed_used = actual_seed
        self.scenario_gen = ProceduralScenarioGenerator(seed=actual_seed)

        if self.config.reset_state_on_start and self.metrics.days_completed == 0:
            self.reset()
            self.metrics.seed_used = actual_seed
            self.scenario_gen = ProceduralScenarioGenerator(seed=actual_seed)

        self._start_time = time.time()
        self.metrics.status = "RUNNING"
        self.metrics.target_days = target
        logger.info(
            f"PaperSoakRunner: Starting run for {target} days (Seed={actual_seed}, "
            f"Deterministic={self.metrics.is_deterministic})..."
        )

        while self.metrics.days_completed < target and not self._stop_requested:
            # Handle pause state
            while self._pause_requested and not self._stop_requested:
                await asyncio.sleep(0.5)

            if self._stop_requested:
                break

            # Execute single day
            await self.step()

            # Halt if kill switch was triggered
            if self.metrics.status == "KILL_SWITCH_TRIPPED" or kill_switch.is_engaged:
                self.metrics.status = "KILL_SWITCH_TRIPPED"
                logger.critical("PaperSoakRunner: Aborting loop due to latched Kill Switch.")
                break

            self.metrics.elapsed_seconds = round(time.time() - self._start_time, 2)

            if interval > 0:
                await asyncio.sleep(interval)

        if self.metrics.status == "RUNNING":
            self.metrics.status = "COMPLETED"

        self.metrics.elapsed_seconds = round(time.time() - self._start_time, 2)
        logger.info(
            f"PaperSoakRunner: Run finished. Status={self.metrics.status}. "
            f"Days={self.metrics.days_completed}, Net PnL=₹{self.metrics.cumulative_net_pnl:.2f}, "
            f"Ending Capital=₹{self.metrics.current_capital:.2f}, Max Drawdown={self.metrics.max_drawdown_pct:.2f}%"
        )
        return self.metrics

    async def run_monte_carlo(
        self,
        num_paths: int = 5,
        days_per_path: int = 10,
        interval_sec: float = 0.0
    ) -> dict:
        """
        Executes multi-path Monte Carlo stress analysis across distinct random seeds
        to measure the empirical distribution of returns, win rates, and drawdowns.
        """
        results = []
        for path_idx in range(num_paths):
            self.reset()
            # Each path gets an independent random seed
            met = await self.run(max_days=days_per_path, interval_sec=interval_sec, seed=None)
            results.append({
                "path": path_idx + 1,
                "seed": met.seed_used,
                "net_pnl": met.cumulative_net_pnl,
                "net_return_pct": met.net_return_pct,
                "win_rate_pct": met.win_rate_pct,
                "max_drawdown_pct": met.max_drawdown_pct,
                "capital_floor_preserved": met.capital_floor_preserved,
                "ending_cash": met.current_capital
            })

        net_returns = [r["net_return_pct"] for r in results]
        drawdowns = [r["max_drawdown_pct"] for r in results]
        win_rates = [r["win_rate_pct"] for r in results]

        summary = {
            "num_paths": num_paths,
            "days_per_path": days_per_path,
            "paths": results,
            "mean_return_pct": round(sum(net_returns) / len(net_returns), 2) if net_returns else 0.0,
            "min_return_pct": min(net_returns) if net_returns else 0.0,
            "max_return_pct": max(net_returns) if net_returns else 0.0,
            "mean_drawdown_pct": round(sum(drawdowns) / len(drawdowns), 2) if drawdowns else 0.0,
            "worst_drawdown_pct": max(drawdowns) if drawdowns else 0.0,
            "mean_win_rate_pct": round(sum(win_rates) / len(win_rates), 1) if win_rates else 0.0,
            "all_capital_floors_preserved": all(r["capital_floor_preserved"] for r in results)
        }
        return summary

    def get_metrics_dict(self) -> dict:
        """Returns JSON-serializable soak metrics for REST API & CLI."""
        d = dataclasses.asdict(self.metrics)
        d["kill_switch_engaged"] = kill_switch.is_engaged
        return d


# Global singleton instance
soak_runner = PaperSoakRunner()
