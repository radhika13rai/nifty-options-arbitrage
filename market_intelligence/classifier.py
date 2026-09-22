"""
Market Intelligence Relevance, Urgency & Temporal Decay Classifier.
Classifies financial news headlines for Indian equity derivatives impact,
measures directional sentiment, and computes exponential half-life decay.
"""

import math
import re
import time
from dataclasses import dataclass
from typing import Literal

DomainCategory = Literal[
    "CENTRAL_BANK_RBI",
    "CRUDE_ENERGY",
    "DOMESTIC_MACRO",
    "GEOPOLITICS",
    "MARKET_MICROSTRUCTURE"
]

UrgencyLevel = Literal["ROUTINE", "ELEVATED", "CRITICAL_SHOCK"]


@dataclass(frozen=True)
class ClassifiedHeadline:
    headline: str
    source: str
    timestamp_ms: float
    category: DomainCategory
    relevance_score: float  # Range: [0.0, 1.0]
    urgency: UrgencyLevel
    raw_sentiment: float  # Range: [-1.0, +1.0]
    decayed_sentiment: float  # Weighted by exponential half-life
    temporal_weight: float  # Range: [0.0, 1.0]
    is_shock_trigger: bool
    summary_reason: str


class NewsClassifier:
    """
    Quantitative domain and sentiment classifier tuned for Indian NIFTY/BankNIFTY options.
    Applies half-life decay of 45 minutes to model market absorption speed.
    """

    def __init__(self, half_life_minutes: float = 45.0):
        self.half_life_ms = half_life_minutes * 60.0 * 1000.0
        self.decay_lambda = math.log(2) / self.half_life_ms

        # Critical shock triggers (immediate market moving events)
        self._shock_phrases = [
            "missile strike", "war declared", "emergency rate hike", "emergency rate cut",
            "ceasefire signed", "surprise rate hike", "surprise rate cut", "strait of hormuz closed",
            "crude surges", "crude plunges", "market halt", "circuit breaker", "trading halted"
        ]

        # Domain keywords & weightings
        self._keywords = {
            "CENTRAL_BANK_RBI": [
                "rbi", "repo rate", "mpc", "shaktikanta", "interest rate", "rate hike",
                "rate cut", "inflation", "cpi", "wpi", "federal reserve", "fed", "powell",
                "fomc", "treasury yield", "bond yield", "liquidity deficit", "monetary policy"
            ],
            "CRUDE_ENERGY": [
                "crude", "brent", "wti", "oil", "opec", "barrel", "petroleum", "gasoline",
                "refinery", "strait of hormuz", "red sea", "tanker", "saudi aramco"
            ],
            "DOMESTIC_MACRO": [
                "gdp", "fiscal deficit", "gst collection", "fii", "dii", "inr", "rupee",
                "current account", "manufacturing pmi", "services pmi", "iip", "budget"
            ],
            "GEOPOLITICS": [
                "war", "military", "missile", "sanction", "ceasefire", "conflict",
                "middle east", "russia", "ukraine", "iran", "israel", "taiwan", "tariff"
            ],
            "MARKET_MICROSTRUCTURE": [
                "nifty", "banknifty", "sensex", "expiry", "option chain", "open interest",
                "sebi", "dalal street", "gift nifty", "f&o", "margin requirement"
            ]
        }

        # Directional polarities
        self._positive_words = {
            "rally", "surge", "gain", "peace", "ceasefire", "rate cut", "easing",
            "growth", "relief", "diplomatic", "breakthrough", "stimulus", "inflows",
            "buy", "bullish", "record high", "upgrade", "positive", "resilient"
        }
        self._negative_words = {
            "plunge", "crash", "slump", "war", "strike", "attack", "escalation",
            "rate hike", "inflation", "deficit", "sanction", "selloff", "outflows",
            "bearish", "downgrade", "crisis", "threat", "tightening", "fear", "drop"
        }

    def compute_temporal_decay(self, timestamp_ms: float, reference_time_ms: float) -> float:
        """Computes exponential decay weight e^(-lambda * dt)."""
        dt_ms = max(0.0, reference_time_ms - timestamp_ms)
        return round(math.exp(-self.decay_lambda * dt_ms), 4)

    def classify(self, headline: str, source: str = "Wire", timestamp_ms: float = 0.0) -> ClassifiedHeadline:
        now_ms = time.time() * 1000.0
        ts = timestamp_ms if timestamp_ms > 0 else now_ms
        h_lower = headline.lower()

        # 1. Determine Category by keyword frequency and relevance
        category_scores: dict[DomainCategory, float] = {}
        for cat, kws in self._keywords.items():
            matches = sum(1 for kw in kws if kw in h_lower)
            category_scores[cat] = matches  # type: ignore

        best_cat = max(category_scores.items(), key=lambda x: x[1])
        category: DomainCategory = best_cat[0] if best_cat[1] > 0 else "DOMESTIC_MACRO"

        # 2. Relevance Score to NIFTY [0.0 - 1.0]
        match_count = category_scores[category]
        has_direct_nifty = any(term in h_lower for term in ["nifty", "india", "rbi", "rupee", "dalal street", "inr"])
        base_relevance = 0.40 + min(0.40, match_count * 0.15)
        if has_direct_nifty:
            base_relevance = min(1.0, base_relevance + 0.20)
        relevance_score = round(base_relevance, 3)

        # 3. Urgency & Shock Detection
        is_shock = any(phrase in h_lower for phrase in self._shock_phrases)
        if is_shock:
            urgency: UrgencyLevel = "CRITICAL_SHOCK"
        elif match_count >= 2 or any(term in h_lower for term in ["breaking", "alert", "urgent", "surges", "plunges"]):
            urgency = "ELEVATED"
        else:
            urgency = "ROUTINE"

        # 4. Sentiment Analysis
        pos_hits = sum(1 for w in self._positive_words if w in h_lower)
        neg_hits = sum(1 for w in self._negative_words if w in h_lower)
        total_hits = pos_hits + neg_hits

        if total_hits > 0:
            raw_sentiment = round((pos_hits - neg_hits) / total_hits, 2)
        else:
            raw_sentiment = 0.0

        # Special context rules (e.g. "rate hike" is usually negative for equities)
        if "rate hike" in h_lower:
            raw_sentiment = min(raw_sentiment, -0.60)
        elif "rate cut" in h_lower:
            raw_sentiment = max(raw_sentiment, +0.60)

        # 5. Temporal Decay
        temporal_weight = self.compute_temporal_decay(ts, now_ms)
        decayed_sentiment = round(raw_sentiment * temporal_weight, 3)

        reason = f"{category} | Urgency={urgency} | Rel={relevance_score:.2f} | Sent={raw_sentiment:+.2f} (decayed={decayed_sentiment:+.2f})"

        return ClassifiedHeadline(
            headline=headline,
            source=source,
            timestamp_ms=ts,
            category=category,
            relevance_score=relevance_score,
            urgency=urgency,
            raw_sentiment=raw_sentiment,
            decayed_sentiment=decayed_sentiment,
            temporal_weight=temporal_weight,
            is_shock_trigger=is_shock,
            summary_reason=reason
        )


news_classifier = NewsClassifier()
