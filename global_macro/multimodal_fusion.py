"""
Multimodal Fusion Engine for Global Macro & News Intelligence.
Fuses dense textual embeddings (e_news) with continuous quantitative macro vectors (e_macro)
to produce a unified global market bias and option posture recommendation.
"""

import math
import time
from dataclasses import dataclass
from typing import Literal
from global_macro.indicators import MacroIndicatorSnapshot, macro_engine
from global_macro.news_embedder import NewsEmbedding, news_embedder

GlobalBias = Literal["STRONG_BEARISH", "MODERATE_BEARISH", "NEUTRAL", "MODERATE_BULLISH", "STRONG_BULLISH"]
OptionsPosture = Literal["FAVOR_PUT_BREAKOUT", "FAVOR_CALL_BREAKOUT", "DEFENSIVE_CASH", "HIGH_VOLATILITY_EXPANSION"]


@dataclass(frozen=True)
class MultimodalFusionResult:
    """Consolidated intelligence state fused from global news and macro indicators."""
    timestamp_ms: float
    global_bias: GlobalBias
    geopolitical_fear_index: float       # [0.0, 1.0]
    expected_nifty_gap_points: float     # Predicted opening gap (points)
    iv_expansion_probability: float      # [0.0, 1.0]
    recommended_options_posture: OptionsPosture
    confidence_score: float              # [0.0, 1.0]
    fused_embedding_vector: list[float]  # 13-dimensional joint embedding vector
    synthesis_reason: str


class MultimodalFusionEngine:
    """Fuses 8-D text news embeddings and 5-D quantitative macro vectors."""

    def __init__(self):
        # Learned linear fusion projection weights
        # Macro inputs: [brent_norm, dxy_norm, gift_gap_norm, us_vix_norm, sp500_norm]
        self._macro_weights = [-1.4, -1.2, 2.0, -1.5, 1.1]
        
        # News inputs: [dir_sent, conflict, energy, monetary, sent_mag, conf_bin, len_norm, urgency]
        self._news_weights = [1.8, -2.2, -1.1, -0.9, 0.4, -0.8, 0.1, -1.0]

    def set_weights(self, macro_weights: list[float], news_weights: list[float]) -> None:
        """Dynamically updates fusion weights after model training/adaptation."""
        if len(macro_weights) == 5:
            self._macro_weights = list(macro_weights)
        if len(news_weights) == 8:
            self._news_weights = list(news_weights)

    def get_weights(self) -> dict[str, list[float]]:
        """Returns currently active multimodal fusion weights."""
        return {
            "macro_weights": list(self._macro_weights),
            "news_weights": list(self._news_weights)
        }

    def fuse(
        self,
        macro_snap: MacroIndicatorSnapshot,
        news_embeddings: list[NewsEmbedding]
    ) -> MultimodalFusionResult:
        """
        Executes cross-modal fusion between news sentiment and quantitative indicators.
        """
        e_macro = macro_snap.to_dense_vector()  # 5 dims
        e_news = news_embedder.aggregate_embeddings(news_embeddings)  # 8 dims
        fused_vector = e_macro + e_news  # 13 dims

        # 1. Compute Macro Component Score
        macro_score = sum(e_macro[i] * self._macro_weights[i] for i in range(5))

        # 2. Compute News Component Score
        news_score = sum(e_news[i] * self._news_weights[i] for i in range(8))

        # 3. Fused Composite Score (Positive = Bullish, Negative = Bearish)
        # Weighted combination: Macro (60%) + News (40%)
        composite_score = (macro_score * 0.60) + (news_score * 0.40)

        # 4. Geopolitical Fear Index [0.0, 1.0]
        # Driven by conflict intensity in news + VIX spikes + crude surges
        conflict_intensity = e_news[1]
        vix_shock = max(0.0, e_macro[3])
        crude_shock = max(0.0, e_macro[0])
        fear_raw = (conflict_intensity * 0.50) + (vix_shock * 0.30) + (crude_shock * 0.20)
        fear_index = round(max(0.0, min(1.0, fear_raw)), 2)

        # 5. Expected NIFTY Opening Gap (Points)
        # Driven primarily by Gift Nifty gap, modified by overnight shock intensity
        base_gap = macro_snap.gift_nifty_gap_pts
        news_modifier = e_news[0] * 25.0  # Directional sentiment adjustment (+/- 25 pts)
        expected_gap = round(base_gap + news_modifier, 1)

        # 6. IV Expansion Probability
        iv_prob = round(max(0.05, min(0.95, 0.20 + (fear_index * 0.75))), 2)

        # 7. Categorize Global Bias
        if composite_score <= -1.8:
            bias: GlobalBias = "STRONG_BEARISH"
        elif composite_score <= -0.6:
            bias = "MODERATE_BEARISH"
        elif composite_score >= 1.8:
            bias = "STRONG_BULLISH"
        elif composite_score >= 0.6:
            bias = "MODERATE_BULLISH"
        else:
            bias = "NEUTRAL"

        # 8. Determine Recommended Options Posture
        if fear_index >= 0.70 or bias == "STRONG_BEARISH":
            posture: OptionsPosture = "FAVOR_PUT_BREAKOUT"
            reason = f"High geopolitical tension (Fear: {fear_index:.2f}) & crude pressure: Prioritizing single-leg OTM Puts."
        elif fear_index <= 0.25 and bias in ["STRONG_BULLISH", "MODERATE_BULLISH"]:
            posture = "FAVOR_CALL_BREAKOUT"
            reason = f"Bullish global macro tailwinds & de-escalation: Favoring momentum OTM Calls."
        elif fear_index >= 0.55 and abs(expected_gap) > 100:
            posture = "HIGH_VOLATILITY_EXPANSION"
            reason = f"Wide gap expected ({expected_gap:+.1f} pts) on global shock: High volatility expansion anticipated."
        else:
            posture = "DEFENSIVE_CASH"
            reason = f"Neutral global cues (Score: {composite_score:+.2f}): Standing down to preserve ₹3,000 capital from theta decay."

        confidence = round(min(0.95, 0.55 + abs(composite_score) * 0.15 + fear_index * 0.15), 2)

        return MultimodalFusionResult(
            timestamp_ms=time.time() * 1000.0,
            global_bias=bias,
            geopolitical_fear_index=fear_index,
            expected_nifty_gap_points=expected_gap,
            iv_expansion_probability=iv_prob,
            recommended_options_posture=posture,
            confidence_score=confidence,
            fused_embedding_vector=fused_vector,
            synthesis_reason=reason
        )


multimodal_fusion = MultimodalFusionEngine()
