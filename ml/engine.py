"""
Adaptive ML Strategy Adapter.
Connects the self-learning ML engine to the unified trading strategy interface.
Enforces the ₹3,000 retail capital constraint and single-leg low-premium OTM rules.
"""

import time
import uuid
from typing import Optional
from config import config
from market_data.normalizer import MarketTick
from market_data.orderbook import OrderbookSnapshot
from strategies.base import BaseStrategy, TradingSignal
from ml.features import feature_extractor
from ml.learner import learning_engine
from costs.transaction_costs import cost_engine
from global_macro.multimodal_fusion import multimodal_fusion
from global_macro.indicators import macro_engine
from global_macro.news_feed import news_feed


class AdaptiveMLStrategy(BaseStrategy):
    """
    Self-learning, adaptive trading strategy for NIFTY options.
    Generates signals dynamically based on continuous online RLS weights
    and Bayesian Thompson sampling.
    """

    def __init__(
        self,
        name: str = "ADAPTIVE_SELF_LEARNING_ML",
        max_premium: float = 38.0,  # ₹38.00 * 65 = ₹2,470 < ₹3,000
        min_premium: float = 12.0
    ):
        super().__init__(name)
        self.max_premium = max_premium
        self.min_premium = min_premium
        self.lot_size = config.market.nifty_lot_size
        self.learner = learning_engine

    def on_tick(self, tick: MarketTick) -> list[TradingSignal]:
        # Track spot updates to classify market regime
        if tick.symbol == "NIFTY_SPOT":
            tracker = feature_extractor.get_or_create_tracker("NIFTY_SPOT")
            tracker.update(tick.ltp, tick.volume, tick.timestamp_ms)
            if tracker.ema9 and tracker.ema21:
                slope = (tracker.ema9 - tracker.ema21) / tracker.ema21
                self.learner.classify_regime(slope, tracker.atr)
        return []

    def on_orderbook(self, snapshot: OrderbookSnapshot) -> list[TradingSignal]:
        if not self.is_active or snapshot.symbol == "NIFTY_SPOT":
            return []

        ask = snapshot.best_ask
        bid = snapshot.best_bid

        # Check capital feasibility for ₹3,000 account
        if ask > self.max_premium or ask < self.min_premium:
            return []

        # Filter out wide spread illiquidity
        if snapshot.spread > 0.60:
            return []

        # Extract normalized quantitative features
        feat_vec = feature_extractor.extract_features(snapshot)
        features = feat_vec.to_list()

        option_type = "CE" if snapshot.symbol.endswith("_CE") else "PE"

        # Ask ML learner to evaluate opportunity
        should_trade, confidence, reason = self.learner.evaluate_opportunity(
            features=features,
            option_type=option_type,
            premium=ask
        )

        if not should_trade:
            return []

        # Check Global Macro & News Intelligence Fusion
        macro_snap = macro_engine.get_snapshot()
        news_embs = news_feed.get_recent_embeddings()
        global_res = multimodal_fusion.fuse(macro_snap, news_embs)

        # 1. Macro Bias Directional Filter:
        # Suppress buying Call options when global tensions are high and macro is bearish
        if global_res.global_bias in ["STRONG_BEARISH", "MODERATE_BEARISH"] and option_type == "CE":
            return []
        
        # Suppress buying Put options when global macro is strongly bullish
        if global_res.global_bias in ["STRONG_BULLISH", "MODERATE_BULLISH"] and option_type == "PE":
            return []

        # Boost confidence when local breakout is confirmed by global macro alignment
        if global_res.recommended_options_posture == "FAVOR_PUT_BREAKOUT" and option_type == "PE":
            confidence = min(0.98, round(confidence + 0.12, 2))
            reason += f" | Global Alignment: {global_res.synthesis_reason}"
        elif global_res.recommended_options_posture == "FAVOR_CALL_BREAKOUT" and option_type == "CE":
            confidence = min(0.98, round(confidence + 0.12, 2))
            reason += f" | Global Alignment: {global_res.synthesis_reason}"

        # Calculate strict ₹150 risk cap
        # Friction ~ ₹45
        # Max points loss = (150 - 45) / 65 = ~1.6 points
        stop_loss_points = 1.6
        stop_loss_price = round(max(0.05, ask - stop_loss_points), 2)
        target_price = round(ask + (stop_loss_points * 2.5), 2)

        sig = TradingSignal(
            signal_id=str(uuid.uuid4())[:8],
            timestamp_ms=time.time() * 1000.0,
            strategy_name=self.name,
            symbol=snapshot.symbol,
            action="BUY",
            order_type="MARKET",
            suggested_price=ask,
            quantity=self.lot_size,
            stop_loss_price=stop_loss_price,
            target_price=target_price,
            confidence=confidence,
            is_capital_feasible=True,
            infeasibility_reason=None,
            metadata={
                "ai_reason": reason,
                "regime": self.learner.current_regime,
                "confidence": confidence,
                "epoch": self.learner.epoch,
                "outlay_inr": round(ask * self.lot_size, 2),
                "features": list(features),
                "option_type": option_type
            }
        )

        return [sig]


adaptive_ml_strategy = AdaptiveMLStrategy()
