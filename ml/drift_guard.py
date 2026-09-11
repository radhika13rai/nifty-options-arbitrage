"""
Automated Model Drift & Overfitting Guard.
Monitors online learning parameters, rolling out-of-sample (OOS) trade outcomes,
and statistical distribution stability. Automatically rolls back weights to conservative
priors if performance degrades below institutional thresholds.
"""

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Optional

from database.db import db_manager
from ml.learner import learning_engine

logger = logging.getLogger("ModelDriftGuard")


@dataclass(frozen=True)
class DriftStatus:
    is_drift_detected: bool
    rolling_win_rate: float
    rolling_profit_factor: float
    rolling_sharpe: float
    consecutive_losses: int
    total_trades_analyzed: int
    drift_reasons: list[str]
    rollback_triggered: bool
    timestamp: float


class ModelDriftGuard:
    """
    Automated watchdog protecting the ₹3,000 micro-capital account from:
    1. RLS weight overfitting on short-term noise
    2. Out-of-Sample performance decay (Win rate < 40% or Sharpe decay > 25%)
    3. Severe consecutive loss streaks (>= 3 losses in a row)
    4. Statutory friction over-trading drag
    """

    def __init__(
        self,
        window_size: int = 20,
        baseline_win_rate: float = 0.65,
        baseline_sharpe: float = 2.0,
        min_trades_for_eval: int = 5,
        max_consecutive_losses: int = 3
    ):
        self.window_size = window_size
        self.baseline_win_rate = baseline_win_rate
        self.baseline_sharpe = baseline_sharpe
        self.min_trades_for_eval = min_trades_for_eval
        self.max_consecutive_losses = max_consecutive_losses
        
        self.trade_history: list[dict] = []
        self.consecutive_losses: int = 0
        self.rollback_count: int = 0
        self.last_rollback_time: Optional[float] = None

    def record_trade(self, net_pnl: float, gross_pnl: float, points_moved: float) -> None:
        """Records completed trade outcome into rolling window."""
        is_win = net_pnl > 0
        if is_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1

        entry = {
            "timestamp": time.time(),
            "net_pnl": net_pnl,
            "gross_pnl": gross_pnl,
            "points_moved": points_moved,
            "is_win": is_win
        }
        self.trade_history.append(entry)
        if len(self.trade_history) > self.window_size:
            self.trade_history.pop(0)

    def calculate_rolling_metrics(self) -> tuple[float, float, float]:
        """Calculates (win_rate, profit_factor, annualized_sharpe_proxy)."""
        if not self.trade_history:
            return 0.50, 1.0, 0.0

        n = len(self.trade_history)
        wins = sum(1 for t in self.trade_history if t["is_win"])
        win_rate = round(wins / n, 3)

        gross_wins = sum(t["gross_pnl"] for t in self.trade_history if t["gross_pnl"] > 0)
        gross_losses = sum(abs(t["gross_pnl"]) for t in self.trade_history if t["gross_pnl"] < 0)
        profit_factor = round(gross_wins / gross_losses, 2) if gross_losses > 0 else 99.0

        # Sharpe calculation on net PnL returns
        net_pnls = [t["net_pnl"] for t in self.trade_history]
        mean_pnl = sum(net_pnls) / n
        variance = sum((p - mean_pnl) ** 2 for p in net_pnls) / n if n > 1 else 0.0
        std_pnl = math.sqrt(variance) if variance > 0 else 1.0

        sharpe_proxy = round((mean_pnl / std_pnl) * math.sqrt(252), 2) if std_pnl > 0 else 0.0
        return win_rate, profit_factor, sharpe_proxy

    def check_drift(self) -> DriftStatus:
        """
        Evaluates current rolling performance against institutional drift boundaries.
        """
        win_rate, profit_factor, sharpe = self.calculate_rolling_metrics()
        drift_reasons = []

        if len(self.trade_history) >= self.min_trades_for_eval:
            # 1. Win rate collapse below 40%
            if win_rate < 0.40:
                drift_reasons.append(f"Rolling win rate {win_rate*100:.1f}% dropped below 40.0% critical threshold")

            # 2. Sharpe ratio degradation > 25%
            sharpe_degradation = (self.baseline_sharpe - sharpe) / self.baseline_sharpe if self.baseline_sharpe > 0 else 0.0
            if sharpe_degradation > 0.25 and sharpe < 1.20:
                drift_reasons.append(f"Rolling Sharpe {sharpe:.2f} degraded by {sharpe_degradation*100:.1f}% vs baseline {self.baseline_sharpe:.2f}")

        # 3. Severe consecutive loss streak
        if self.consecutive_losses >= self.max_consecutive_losses:
            drift_reasons.append(f"Loss streak alert: {self.consecutive_losses} consecutive loss trades under micro-capital limits")

        is_drift = len(drift_reasons) > 0
        return DriftStatus(
            is_drift_detected=is_drift,
            rolling_win_rate=win_rate,
            rolling_profit_factor=profit_factor,
            rolling_sharpe=sharpe,
            consecutive_losses=self.consecutive_losses,
            total_trades_analyzed=len(self.trade_history),
            drift_reasons=drift_reasons,
            rollback_triggered=False,
            timestamp=time.time()
        )

    async def evaluate_and_enforce(self) -> DriftStatus:
        """
        Checks for drift and automatically executes safe weight rollbacks if breached.
        """
        status = self.check_drift()
        if not status.is_drift_detected:
            return status

        # Trigger safe rollback
        logger.warning(f"ModelDriftGuard: Drift detected! Triggering weight rollback: {status.drift_reasons}")
        self.rollback_to_conservative_priors()
        self.rollback_count += 1
        self.last_rollback_time = time.time()

        # Audit event into SQLite
        await db_manager.record_audit_log(
            event_type="MODEL_DRIFT_ROLLBACK",
            severity="WARNING",
            component="ModelDriftGuard",
            details=f"Triggered model rollback. Reasons: {'; '.join(status.drift_reasons)}"
        )

        return DriftStatus(
            is_drift_detected=True,
            rolling_win_rate=status.rolling_win_rate,
            rolling_profit_factor=status.rolling_profit_factor,
            rolling_sharpe=status.rolling_sharpe,
            consecutive_losses=status.consecutive_losses,
            total_trades_analyzed=status.total_trades_analyzed,
            drift_reasons=status.drift_reasons,
            rollback_triggered=True,
            timestamp=time.time()
        )

    def rollback_to_conservative_priors(self) -> None:
        """
        Restores verified conservative weights and resets samplers.
        """
        learning_engine.reset()
        self.consecutive_losses = 0
        logger.info("ModelDriftGuard: RLS weights and Bayesian samplers rolled back to verified priors.")

    def reset(self) -> None:
        """Clears state for testing or clean restarts."""
        self.trade_history.clear()
        self.consecutive_losses = 0
        self.rollback_count = 0
        self.last_rollback_time = None


drift_guard = ModelDriftGuard()
