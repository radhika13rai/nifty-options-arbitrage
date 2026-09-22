"""
Champion-Challenger (Shadow Model) Model Governance & Validation Engine.
Maintains the production Champion model while continuously training Challenger models
on reconciled historical episodes with strict out-of-sample promotion gates.
"""

import json
import logging
import math
import time
from dataclasses import dataclass, asdict
from typing import Optional

from database.db import db_manager

logger = logging.getLogger("ChampionChallenger")


@dataclass
class CandidateMetrics:
    total_samples: int
    win_rate: float
    net_profit_factor: float
    sharpe_ratio: float
    max_drawdown_pct: float
    net_pnl: float


@dataclass
class ModelCandidate:
    model_id: str
    weights: list[float]
    dim: int
    created_at: float
    trained_episodes_count: int
    metrics: CandidateMetrics


class ChampionChallengerEngine:
    """
    Automated model evaluation and promotion gate.
    Ensures that only empirically superior models with out-of-sample validation
    are allowed to guide live trading signals.
    """

    def __init__(self):
        self.dim = 16
        # Baseline 16-D weights: [8 Microstructure] + [4 Option Surface] + [4 Macro & News]
        self._baseline_weights: list[float] = [
            1.8, 1.2, -2.5, 0.9, 1.5, 0.6, 0.4, 0.5,    # 8 Microstructure
            -0.8, 1.1, -0.4, 0.9,                         # 4 Options Skew & Surface
            -1.2, -0.9, 1.4, -1.0                         # 4 Macro & News Intelligence
        ]
        
        self.champion: ModelCandidate = ModelCandidate(
            model_id="CHAMPION_BASELINE_V1",
            weights=list(self._baseline_weights),
            dim=self.dim,
            created_at=time.time(),
            trained_episodes_count=0,
            metrics=CandidateMetrics(
                total_samples=0,
                win_rate=0.60,
                net_profit_factor=1.50,
                sharpe_ratio=1.80,
                max_drawdown_pct=8.5,
                net_pnl=0.0
            )
        )
        self.challenger: Optional[ModelCandidate] = None
        self.promotion_history: list[dict] = []

    def score_features(self, features: list[float], model: Optional[ModelCandidate] = None) -> float:
        """Computes dot product w^T * x using specified model (default: Champion)."""
        candidate = model or self.champion
        w = candidate.weights
        n = min(len(features), len(w))
        return sum(w[i] * features[i] for i in range(n))

    def evaluate_dataset(self, episodes: list[dict], weights: list[float]) -> CandidateMetrics:
        """
        Evaluates a set of weights against reconciled historical episodes.
        Computes win rate, profit factor, Sharpe ratio, and peak-to-trough drawdown.
        """
        if not episodes:
            return CandidateMetrics(0, 0.50, 1.0, 0.0, 0.0, 0.0)

        wins = 0
        gross_wins = 0.0
        gross_losses = 0.0
        net_pnls: list[float] = []
        cumulative_pnl = 0.0
        peak_pnl = 0.0
        max_dd = 0.0

        for ep in episodes:
            feats = ep.get("features", [])
            if not feats and "features_json" in ep:
                feats = json.loads(ep["features_json"])

            opt_type = ep.get("option_type", "CE")
            actual_pts = ep.get("points_moved", 0.0)
            actual_net = ep.get("net_pnl", 0.0)

            # Dot product score
            pred = sum(weights[i] * feats[i] for i in range(min(len(weights), len(feats))))
            if opt_type == "PE":
                pred = -pred

            # Trade is taken if predicted points move justifies the statutory fee hurdle (> +0.9 pts)
            if pred >= 0.90:
                net_pnls.append(actual_net)
                cumulative_pnl += actual_net
                if cumulative_pnl > peak_pnl:
                    peak_pnl = cumulative_pnl
                dd = peak_pnl - cumulative_pnl
                if dd > max_dd:
                    max_dd = dd

                if actual_net > 0:
                    wins += 1
                    gross_wins += actual_net
                else:
                    gross_losses += abs(actual_net)

        total_trades = len(net_pnls)
        if total_trades == 0:
            return CandidateMetrics(0, 0.50, 1.0, 0.0, 0.0, 0.0)

        win_rate = round(wins / total_trades, 3)
        profit_factor = round(gross_wins / gross_losses, 2) if gross_losses > 0 else 99.0
        mean_pnl = sum(net_pnls) / total_trades
        variance = sum((p - mean_pnl) ** 2 for p in net_pnls) / total_trades if total_trades > 1 else 0.0
        std_pnl = math.sqrt(variance) if variance > 0 else 1.0
        sharpe = round((mean_pnl / std_pnl) * math.sqrt(252), 2) if std_pnl > 0 else 0.0
        dd_pct = round((max_dd / 3000.0) * 100.0, 2)

        return CandidateMetrics(
            total_samples=total_trades,
            win_rate=win_rate,
            net_profit_factor=profit_factor,
            sharpe_ratio=sharpe,
            max_drawdown_pct=dd_pct,
            net_pnl=round(sum(net_pnls), 2)
        )

    def train_challenger(self, episodes: list[dict], split_ratio: float = 0.70) -> Optional[ModelCandidate]:
        """
        Trains a Challenger model using 70% Train, 30% Holdout Out-of-Sample (OOS) validation.
        """
        if len(episodes) < 6:
            logger.info(f"ChampionChallenger: Insufficient episodes ({len(episodes)} < 6) to train Challenger.")
            return None

        # Sort chronologically by entry_time_ms
        sorted_eps = sorted(episodes, key=lambda x: x.get("entry_time_ms", 0))
        split_idx = max(3, int(len(sorted_eps) * split_ratio))
        train_set = sorted_eps[:split_idx]
        holdout_set = sorted_eps[split_idx:]

        # Train weights via online Recursive Least Squares on train_set
        w = list(self.champion.weights)
        lam = 0.98
        P = [[10.0 if i == j else 0.0 for j in range(self.dim)] for i in range(self.dim)]

        for ep in train_set:
            feats = ep.get("features", [])
            if not feats and "features_json" in ep:
                feats = json.loads(ep["features_json"])
            opt_type = ep.get("option_type", "CE")
            pts = ep.get("points_moved", 0.0)
            target = pts if opt_type == "CE" else -pts

            # Pad features to 16-D if shorter
            x = (feats + [0.0] * self.dim)[:self.dim]
            
            # RLS Step
            Px = [sum(P[i][j] * x[j] for j in range(self.dim)) for i in range(self.dim)]
            xPx = sum(x[i] * Px[i] for i in range(self.dim))
            denom = lam + xPx
            if abs(denom) > 1e-9:
                k = [Px[i] / denom for i in range(self.dim)]
                pred = sum(w[i] * x[i] for i in range(self.dim))
                err = target - pred
                for i in range(self.dim):
                    w[i] += k[i] * err
                for i in range(self.dim):
                    for j in range(self.dim):
                        P[i][j] = (P[i][j] - k[i] * Px[j]) / lam

        # Evaluate on Holdout Out-of-Sample set
        oos_metrics = self.evaluate_dataset(holdout_set, w)

        now_ms = time.time() * 1000.0
        challenger = ModelCandidate(
            model_id=f"CHALLENGER_{int(now_ms)}",
            weights=[round(val, 4) for val in w],
            dim=self.dim,
            created_at=time.time(),
            trained_episodes_count=len(train_set),
            metrics=oos_metrics
        )
        self.challenger = challenger
        logger.info(
            f"ChampionChallenger: Challenger trained on {len(train_set)} samples. "
            f"OOS Metrics: Win Rate={oos_metrics.win_rate:.1%}, Sharpe={oos_metrics.sharpe_ratio:.2f}, "
            f"Profit Factor={oos_metrics.net_profit_factor:.2f}, DD={oos_metrics.max_drawdown_pct:.1f}%"
        )
        return challenger

    def evaluate_and_promote(self) -> dict:
        """
        Strict institutional promotion gate:
        Challenger is promoted to Champion ONLY if:
        1. OOS Win Rate >= 55%
        2. OOS Profit Factor >= 1.25
        3. OOS Sharpe Ratio > Champion Sharpe + 0.15
        4. OOS Max Drawdown < 15.0%
        """
        if not self.challenger:
            return {"promoted": False, "reason": "NO_CHALLENGER_AVAILABLE"}

        champ_m = self.champion.metrics
        chall_m = self.challenger.metrics

        rejection_reasons = []
        if chall_m.win_rate < 0.55:
            rejection_reasons.append(f"Win Rate {chall_m.win_rate:.1%} < 55.0% hurdle")
        if chall_m.net_profit_factor < 1.25:
            rejection_reasons.append(f"Profit Factor {chall_m.net_profit_factor:.2f} < 1.25 hurdle")
        if chall_m.sharpe_ratio <= (champ_m.sharpe_ratio + 0.15):
            rejection_reasons.append(
                f"Sharpe {chall_m.sharpe_ratio:.2f} did not exceed Champion ({champ_m.sharpe_ratio:.2f}) + 0.15"
            )
        if chall_m.max_drawdown_pct >= 15.0:
            rejection_reasons.append(f"Max Drawdown {chall_m.max_drawdown_pct:.1f}% >= 15.0% limit")

        if rejection_reasons:
            reason_str = " | ".join(rejection_reasons)
            logger.info(f"ChampionChallenger: Challenger REJECTED. Reasons: {reason_str}")
            return {
                "promoted": False,
                "reason": reason_str,
                "champion": asdict(self.champion),
                "challenger": asdict(self.challenger)
            }

        # PROMOTE CHALLENGER TO CHAMPION
        prev_champ_id = self.champion.model_id
        self.champion = self.challenger
        self.challenger = None

        promo_record = {
            "timestamp": time.time(),
            "new_champion_id": self.champion.model_id,
            "previous_champion_id": prev_champ_id,
            "win_rate": chall_m.win_rate,
            "sharpe_ratio": chall_m.sharpe_ratio,
            "profit_factor": chall_m.net_profit_factor
        }
        self.promotion_history.append(promo_record)
        logger.info(f"ChampionChallenger: PROMOTION SUCCESSFUL! New Champion: {self.champion.model_id}")

        return {
            "promoted": True,
            "reason": "OOS_VALIDATION_SURPASSED",
            "champion": asdict(self.champion),
            "promotion_record": promo_record
        }

    def rollback_to_baseline(self, reason: str = "PERFORMANCE_DEGRADATION") -> None:
        """Rolls back the active model to conservative baseline priors."""
        logger.warning(f"ChampionChallenger: Executing ROLLBACK to baseline priors. Reason: {reason}")
        self.champion = ModelCandidate(
            model_id=f"CHAMPION_ROLLBACK_{int(time.time()*1000)}",
            weights=list(self._baseline_weights),
            dim=self.dim,
            created_at=time.time(),
            trained_episodes_count=0,
            metrics=CandidateMetrics(0, 0.60, 1.50, 1.80, 8.5, 0.0)
        )
        self.challenger = None


champion_challenger = ChampionChallengerEngine()
