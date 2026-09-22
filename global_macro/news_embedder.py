"""
Financial & Geopolitical News Embedding Engine.
Converts unstructured news headlines into quantitative semantic embeddings,
evaluating conflict intensity, energy shocks, and monetary policy sentiment in pure Python.
"""

import math
import re
import time
from dataclasses import dataclass, field
from typing import Literal

NewsCategory = Literal["GEOPOLITICS", "CRUDE_ENERGY", "CENTRAL_BANK", "TRADE_TARIFFS", "DOMESTIC_INDIA"]


@dataclass(frozen=True)
class NewsItem:
    """Represents a single news wire headline."""
    headline: str
    source: str
    timestamp_ms: float
    category: NewsCategory = "GEOPOLITICS"


@dataclass(frozen=True)
class NewsEmbedding:
    """Semantic quantitative embedding derived from financial news text."""
    headline: str
    directional_sentiment: float         # [-1.0, +1.0]: Bearish to Bullish
    geopolitical_conflict_intensity: float # [0.0, 1.0]: Peace to War/Crisis
    energy_shock_score: float             # [-1.0, +1.0]: Oil surplus to Oil shortage/spike
    monetary_hawkish_score: float         # [-1.0, +1.0]: Rate cuts/dovish to Rate hikes/hawkish
    dense_vector: list[float]             # 8-dimensional normalized text embedding vector


class FinancialNewsEmbedder:
    """Tokenizes and transforms financial headlines into dense semantic vectors."""

    def __init__(self):
        # Domain-specific financial & geopolitical semantic dictionaries with calibrated weights
        self._conflict_terms = {
            "war": 0.95, "missile": 0.90, "strike": 0.85, "attack": 0.85, "escalat": 0.80,
            "bomb": 0.90, "invasion": 0.95, "tanks": 0.75, "drone": 0.70, "retaliat": 0.80,
            "conflict": 0.75, "military": 0.65, "threat": 0.60, "sanction": 0.65, "embargo": 0.80,
            "hostage": 0.75, "casualt": 0.85, "shipping": 0.50, "red sea": 0.80, "hormuz": 0.85
        }
        self._deescalation_terms = {
            "ceasefire": -0.90, "peace": -0.85, "truce": -0.90, "treaty": -0.80, "de-escalat": -0.85,
            "agreement": -0.60, "diplomac": -0.65, "resolved": -0.70, "withdraw": -0.75
        }
        self._bearish_terms = {
            "crash": -0.90, "plunge": -0.85, "slump": -0.75, "fall": -0.50, "selloff": -0.70,
            "loss": -0.60, "recession": -0.85, "deficit": -0.55, "downgrade": -0.70, "default": -0.90
        }
        self._bullish_terms = {
            "surge": 0.85, "rally": 0.80, "jump": 0.70, "gain": 0.60, "record": 0.70,
            "growth": 0.65, "upgrade": 0.75, "stimulus": 0.80, "boom": 0.85, "optimism": 0.60
        }
        self._energy_shock_terms = {
            "crude spike": 0.90, "oil jump": 0.85, "opec cut": 0.80, "supply disrupt": 0.85,
            "refinery attack": 0.95, "crude drops": -0.80, "oil slide": -0.80, "glut": -0.70
        }
        self._monetary_terms = {
            "rate hike": 0.85, "hawkish": 0.80, "inflation surge": 0.75, "tightening": 0.70,
            "rate cut": -0.85, "dovish": -0.80, "easing": -0.75, "liquidity injection": -0.70
        }

    def _clean_tokens(self, text: str) -> list[str]:
        cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", text.lower())
        return cleaned.split()

    def embed_headline(self, item: NewsItem) -> NewsEmbedding:
        """Converts a headline into an 8-dimensional semantic embedding."""
        tokens = self._clean_tokens(item.headline)
        joined_text = " ".join(tokens)

        # 1. Conflict Intensity [0.0, 1.0]
        conflict_scores = []
        for term, weight in self._conflict_terms.items():
            if term in joined_text:
                conflict_scores.append(weight)
        for term, weight in self._deescalation_terms.items():
            if term in joined_text:
                conflict_scores.append(weight)

        conflict_raw = sum(conflict_scores) if conflict_scores else 0.0
        conflict_intensity = max(0.0, min(1.0, round(conflict_raw, 2)))

        # 2. Directional Sentiment [-1.0, +1.0]
        sentiment_scores = []
        for term, weight in self._bearish_terms.items():
            if term in joined_text:
                sentiment_scores.append(weight)
        for term, weight in self._bullish_terms.items():
            if term in joined_text:
                sentiment_scores.append(weight)
        # De-escalation and peace provide strong positive relief sentiment
        for term, weight in self._deescalation_terms.items():
            if term in joined_text:
                sentiment_scores.append(abs(weight) * 0.85)

        # If conflict is high, it heavily biases sentiment bearish for Indian equities
        if conflict_intensity > 0.40:
            sentiment_scores.append(-conflict_intensity * 0.8)

        sentiment_val = sum(sentiment_scores) / (len(sentiment_scores) + 1e-6) if sentiment_scores else 0.0
        directional_sentiment = max(-1.0, min(1.0, round(sentiment_val, 2)))

        # 3. Energy Shock [-1.0, +1.0]
        energy_scores = [w for t, w in self._energy_shock_terms.items() if t in joined_text]
        energy_score = max(-1.0, min(1.0, round(sum(energy_scores), 2))) if energy_scores else 0.0

        # 4. Monetary Hawkishness [-1.0, +1.0]
        monetary_scores = [w for t, w in self._monetary_terms.items() if t in joined_text]
        monetary_score = max(-1.0, min(1.0, round(sum(monetary_scores), 2))) if monetary_scores else 0.0

        # 8-dimensional dense vector:
        # [directional_sentiment, conflict_intensity, energy_shock, monetary_score,
        #  sentiment_magnitude, conflict_binary, headline_length_norm, urgency_factor]
        urgency = round(max(abs(directional_sentiment), conflict_intensity), 2)
        dense_vector = [
            directional_sentiment,
            conflict_intensity,
            energy_score,
            monetary_score,
            round(abs(directional_sentiment), 2),
            1.0 if conflict_intensity >= 0.50 else 0.0,
            round(min(1.0, len(tokens) / 20.0), 2),
            urgency
        ]

        return NewsEmbedding(
            headline=item.headline,
            directional_sentiment=directional_sentiment,
            geopolitical_conflict_intensity=conflict_intensity,
            energy_shock_score=energy_score,
            monetary_hawkish_score=monetary_score,
            dense_vector=dense_vector
        )

    def embed(self, text_or_item) -> NewsEmbedding:
        """Convenience method that embeds either a headline string or NewsItem object."""
        if isinstance(text_or_item, str):
            item = NewsItem(
                headline=text_or_item,
                source="HISTORICAL_DATASET",
                timestamp_ms=time.time() * 1000.0,
                category="GEOPOLITICS"
            )
            return self.embed_headline(item)
        return self.embed_headline(text_or_item)

    def aggregate_embeddings(self, embeddings: list[NewsEmbedding]) -> list[float]:
        """Averages and weights recent news embeddings into a single 8-D vector."""
        if not embeddings:
            return [0.0] * 8

        # Weighted average with highest weight given to highest urgency
        total_weight = 0.0
        acc = [0.0] * 8

        for emb in embeddings:
            # Urgency acts as sample weight
            w = 1.0 + emb.dense_vector[7] * 2.0
            for i in range(8):
                acc[i] += emb.dense_vector[i] * w
            total_weight += w

        return [round(acc[i] / total_weight, 4) for i in range(8)]


news_embedder = FinancialNewsEmbedder()
# Quant accuracy alias: explicitly denotes feature encoding architecture
FinancialNewsFeatureEncoder = FinancialNewsEmbedder
news_feature_encoder = news_embedder
