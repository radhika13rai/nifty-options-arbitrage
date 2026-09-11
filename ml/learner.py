"""
Adaptive Self-Learning Optimizer & Machine Learning Engine.
Implements Recursive Least Squares (RLS), Bayesian Thompson Sampling,
and Tax-Aware Net P&L Optimization in pure Python.
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import Literal, Optional
from costs.transaction_costs import cost_engine
from config import config

MarketRegime = Literal["TRENDING_BULL", "TRENDING_BEAR", "CHOPPY_CONSOLIDATION", "HIGH_VOL_SHOCK"]


class RecursiveLeastSquares:
    """Online linear learning model with exponential forgetting factor lambda."""

    def __init__(self, dim: int = 8, lam: float = 0.98, delta: float = 10.0):
        self.dim = dim
        self.lam = lam  # Forgetting factor
        # Weight vector
        self.w: list[float] = [0.0] * dim
        # Inverse covariance matrix P initialized to delta * Identity
        self.P: list[list[float]] = [
            [delta if i == j else 0.0 for j in range(dim)]
            for i in range(dim)
        ]
        self.steps: int = 0

    def predict(self, x: list[float]) -> float:
        """Computes dot product w^T * x."""
        return sum(self.w[i] * x[i] for i in range(min(len(x), self.dim)))

    def update(self, x: list[float], y: float) -> float:
        """Online Recursive Least Squares update step."""
        d = self.dim
        # 1. P * x vector
        Px = [sum(self.P[i][j] * x[j] for j in range(d)) for i in range(d)]
        # 2. x^T * P * x scalar
        xPx = sum(x[i] * Px[i] for i in range(d))
        # 3. Denominator
        denom = self.lam + xPx
        if abs(denom) < 1e-9:
            return 0.0

        # 4. Kalman gain vector k = Px / denom
        k = [Px[i] / denom for i in range(d)]

        # 5. Prediction error e = y - w^T * x
        pred = self.predict(x)
        err = y - pred

        # 6. Weight update w = w + k * err
        for i in range(d):
            self.w[i] += k[i] * err

        # 7. Covariance update P = (P - k * Px^T) / lam
        for i in range(d):
            for j in range(d):
                self.P[i][j] = (self.P[i][j] - k[i] * Px[j]) / self.lam

        self.steps += 1
        return err


class BayesianThompsonSampler:
    """Tracks probability of trade success using a Beta-Binomial conjugate prior."""

    def __init__(self, alpha_prior: float = 3.0, beta_prior: float = 3.0):
        self.alpha = alpha_prior
        self.beta = beta_prior
        self.total_updates = 0

    def update(self, is_winning_trade: bool) -> None:
        """Updates posterior distribution after observing a trade outcome."""
        if is_winning_trade:
            self.alpha += 1.0
        else:
            self.beta += 1.0
        self.total_updates += 1

    @property
    def expected_win_rate(self) -> float:
        """Mean of the Beta distribution."""
        return round(self.alpha / (self.alpha + self.beta), 3)

    def sample_win_rate(self) -> float:
        """Draws a Thompson sample from Beta(alpha, beta) using standard normal approx."""
        # Beta mean and variance
        mean = self.alpha / (self.alpha + self.beta)
        var = (self.alpha * self.beta) / (((self.alpha + self.beta) ** 2) * (self.alpha + self.beta + 1.0))
        std = math.sqrt(var)
        # Sample with clipping
        sample = random.gauss(mean, std)
        return min(0.99, max(0.01, sample))


@dataclass
class LearningMetrics:
    epoch: int
    regime: MarketRegime
    confidence_score: float
    expected_win_rate: float
    rls_steps: int
    sample_win_rate: float
    statutory_hurdle_inr: float
    last_update_time: float


class AdaptiveLearningEngine:
    """Master self-learning coordinator. Trains continuously on Net Realized P&L."""

    def __init__(self, lot_size: int = config.market.nifty_lot_size):
        self.lot_size = lot_size
        self.rls = RecursiveLeastSquares(dim=8, lam=0.98)
        self.call_sampler = BayesianThompsonSampler(alpha_prior=4.0, beta_prior=3.0)
        self.put_sampler = BayesianThompsonSampler(alpha_prior=4.0, beta_prior=3.0)
        self.epoch: int = 1
        self.current_regime: MarketRegime = "TRENDING_BULL"
        self.statutory_hurdle_inr: float = 52.02  # Standard 1 lot round-trip tax
        self.last_adaptation_time: float = time.time()
        self._init_warm_weights()

    def _init_warm_weights(self):
        """Initializes RLS with sane quantitative priors."""
        # Features: [imbalance, micro_delta, spread_pct, vwap_stretch, ema_slope, rsi, atr, vol_rank]
        # Strong imbalance and positive EMA slope are rewarded
        self.rls.w = [1.8, 1.2, -2.5, 0.9, 1.5, 0.6, 0.4, 0.5]

    def classify_regime(self, spot_ema_slope: float, spot_atr: float) -> MarketRegime:
        """Classifies the market volatility regime."""
        if spot_atr > 60.0:
            self.current_regime = "HIGH_VOL_SHOCK"
        elif abs(spot_ema_slope) > 0.0015:
            self.current_regime = "TRENDING_BULL" if spot_ema_slope > 0 else "TRENDING_BEAR"
        else:
            self.current_regime = "CHOPPY_CONSOLIDATION"
        return self.current_regime

    def evaluate_opportunity(
        self,
        features: list[float],
        option_type: Literal["CE", "PE"],
        premium: float
    ) -> tuple[bool, float, str]:
        """
        Evaluates trade probability. Returns (should_trade, confidence, reason).
        Directly optimizes Net Profit after Indian statutory fees!
        """
        # 1. Regime filter: Avoid buying options in choppy markets (theta decay trap)
        if self.current_regime == "CHOPPY_CONSOLIDATION":
            return False, 0.30, "Regime is CHOPPY: Long options paused to avoid theta decay"

        # 2. Predicted points move from RLS model
        predicted_points = self.rls.predict(features)
        
        # Invert for PE if needed
        if option_type == "PE":
            predicted_points = -predicted_points

        # 3. Calculate expected Gross and Net PnL on 1 lot (65 units)
        expected_gross_pnl = predicted_points * self.lot_size
        
        # Calculate real statutory taxes
        expected_exit_price = max(0.05, premium + predicted_points)
        rt_costs = cost_engine.calculate_round_trip("BUY", premium, expected_exit_price, self.lot_size)
        expected_net_pnl = expected_gross_pnl - rt_costs.total_friction

        # 4. Bayesian win rate check
        sampler = self.call_sampler if option_type == "CE" else self.put_sampler
        exp_prob = sampler.expected_win_rate

        # 5. Core Decision Rule:
        # Expected move must beat statutory friction (net PnL >= ₹60) AND expected win rate >= 55%
        if expected_net_pnl >= 60.0 and exp_prob >= 0.55:
            confidence = min(0.95, round(exp_prob * 0.7 + (expected_net_pnl / 300.0) * 0.3, 2))
            return True, confidence, f"AI Conviction: Expected Net +₹{expected_net_pnl:.1f} (beats ₹{rt_costs.total_friction:.1f} fee hurdle)"
        
        return False, round(exp_prob, 2), f"Sub-hurdle: Expected Net ₹{expected_net_pnl:.1f} does not justify ₹{rt_costs.total_friction:.1f} tax drag"

    def learn_from_trade(
        self,
        features: list[float],
        option_type: Literal["CE", "PE"],
        actual_points_moved: float,
        actual_net_pnl: float
    ) -> None:
        """
        Post-trade learning step. Updates RLS weights and Bayesian samplers.
        """
        target_y = actual_points_moved if option_type == "CE" else -actual_points_moved
        
        # Online RLS update
        self.rls.update(features, target_y)

        # Bayesian update (True if Net PnL was positive after all taxes)
        is_winner = actual_net_pnl > 0
        if option_type == "CE":
            self.call_sampler.update(is_winner)
        else:
            self.put_sampler.update(is_winner)

        self.last_adaptation_time = time.time()

    def run_daily_adaptation_step(self, historical_trades: list[dict]) -> LearningMetrics:
        """Simulates end-of-day walk-forward optimization over session trades."""
        self.epoch += 1
        for t in historical_trades:
            feats = t.get("features", [0.0] * 8)
            opt_type = t.get("option_type", "CE")
            pts = t.get("points_moved", 0.0)
            net_pnl = t.get("net_pnl", 0.0)
            self.learn_from_trade(feats, opt_type, pts, net_pnl)

        return self.get_metrics()

    def get_metrics(self) -> LearningMetrics:
        avg_win_rate = (self.call_sampler.expected_win_rate + self.put_sampler.expected_win_rate) / 2.0
        return LearningMetrics(
            epoch=self.epoch,
            regime=self.current_regime,
            confidence_score=round(avg_win_rate, 2),
            expected_win_rate=avg_win_rate,
            rls_steps=self.rls.steps,
            sample_win_rate=self.call_sampler.sample_win_rate(),
            statutory_hurdle_inr=self.statutory_hurdle_inr,
            last_update_time=self.last_adaptation_time
        )


learning_engine = AdaptiveLearningEngine()
