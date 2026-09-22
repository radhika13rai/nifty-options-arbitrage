"""
Master Market Intelligence Engine (MIE).
Orchestrates live wire news ingestion, content deduplication, entity classification,
temporal decay weighting, and emergency shock alerts for options trading risk.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from market_intelligence.deduplicator import news_deduplicator, NewsDeduplicator
from market_intelligence.classifier import news_classifier, NewsClassifier, ClassifiedHeadline
from market_intelligence.alert_engine import alert_engine, AlertEngine, MarketAlert

logger = logging.getLogger("MarketIntelligenceEngine")


@dataclass(frozen=True)
class IntelligenceSnapshot:
    timestamp_ms: float
    news_sentiment_score: float  # Range: [-1.0, +1.0], weighted by temporal decay
    geopolitical_tension_index: float  # Range: [0.0, 1.0]
    is_shock_stand_down_active: bool
    stand_down_remaining_sec: float
    stand_down_reason: Optional[str]
    total_processed_headlines: int
    active_alerts_count: int
    recent_headlines: list[dict]


class MarketIntelligenceEngine:
    """
    Central intelligence coordinator. Aggregates multi-source news streams,
    detects breaking market-moving shocks, and computes unified macro features.
    """

    def __init__(
        self,
        deduplicator: Optional[NewsDeduplicator] = None,
        classifier: Optional[NewsClassifier] = None,
        alerts: Optional[AlertEngine] = None
    ):
        self.deduplicator = deduplicator or news_deduplicator
        self.classifier = classifier or news_classifier
        self.alerts = alerts or alert_engine
        self._classified_items: list[ClassifiedHeadline] = []
        self.max_cached_items: int = 100
        self._init_baseline()

    def _init_baseline(self):
        """Seeds initial calm baseline headlines."""
        baseline = [
            ("Asian markets steady as investors evaluate global macroeconomic cues", "Reuters", "DOMESTIC_MACRO"),
            ("Brent crude trades near $82 as supply routes remain orderly", "Bloomberg", "CRUDE_ENERGY"),
            ("RBI Governor emphasizes domestic economic resilience and stable liquidity", "PTI", "CENTRAL_BANK_RBI"),
            ("Indian manufacturing and services PMI print healthy expansion figures", "Economic Times", "DOMESTIC_MACRO")
        ]
        now_ms = time.time() * 1000.0
        for h, src, _ in baseline:
            self.process_incoming_headline(h, src, now_ms)

    def process_incoming_headline(
        self,
        raw_headline: str,
        source: str = "Live Wire",
        timestamp_ms: Optional[float] = None
    ) -> Optional[ClassifiedHeadline]:
        """
        Processes a raw news wire headline through deduplication, classification,
        and alert evaluation. Returns ClassifiedHeadline if novel, or None if duplicate.
        """
        now_ms = timestamp_ms or (time.time() * 1000.0)
        
        # 1. Deduplication Gate
        fingerprint = self.deduplicator.register(raw_headline, now_ms)
        if not fingerprint:
            # Duplicate or syndicated rehash -> Drop silently
            return None

        # 2. Classification & Temporal Decay
        classified = self.classifier.classify(raw_headline, source, now_ms)
        self._classified_items.insert(0, classified)
        if len(self._classified_items) > self.max_cached_items:
            self._classified_items.pop()

        # 3. Breaking Shock Alert Dispatch
        if classified.is_shock_trigger or classified.urgency == "CRITICAL_SHOCK":
            self.alerts.trigger_alert(
                severity="CRITICAL_SHOCK",
                event_type="BREAKING_NEWS_SHOCK",
                headline=raw_headline,
                action_recommended="PAUSE_ENTRIES_15M",
                source=source
            )
        elif classified.urgency == "ELEVATED":
            self.alerts.trigger_alert(
                severity="WARNING",
                event_type="ELEVATED_MACRO_EVENT",
                headline=raw_headline,
                action_recommended="MONITOR_IMPLIED_VOLATILITY",
                source=source
            )

        return classified

    def get_snapshot(self) -> IntelligenceSnapshot:
        """Computes instantaneous market intelligence metrics."""
        now_ms = time.time() * 1000.0
        
        # Compute time-weighted average sentiment across unique recent items
        if self._classified_items:
            # Recompute temporal weights to reflect true elapsed time
            total_weight = 0.0
            weighted_sentiment_sum = 0.0
            conflict_scores = []

            for item in self._classified_items[:20]:
                decay = self.classifier.compute_temporal_decay(item.timestamp_ms, now_ms)
                eff_weight = decay * item.relevance_score
                total_weight += eff_weight
                weighted_sentiment_sum += (item.raw_sentiment * eff_weight)
                
                if item.category == "GEOPOLITICS":
                    conflict_scores.append(max(0.0, -item.raw_sentiment) * decay)
                elif item.category == "CRUDE_ENERGY" and item.raw_sentiment < 0:
                    conflict_scores.append(abs(item.raw_sentiment) * decay)

            net_sentiment = round(weighted_sentiment_sum / total_weight, 3) if total_weight > 0 else 0.0
            tension_idx = round(min(1.0, sum(conflict_scores) / max(1, len(conflict_scores)) * 1.5), 3) if conflict_scores else 0.15
        else:
            net_sentiment = 0.0
            tension_idx = 0.10

        stand_down_active = self.alerts.is_shock_stand_down_active(now_ms)
        remaining_sec = self.alerts.get_remaining_stand_down_sec(now_ms)
        stand_down_reason = self.alerts.get_last_shock_reason()

        recent_dicts = [
            {
                "headline": it.headline,
                "source": it.source,
                "category": it.category,
                "urgency": it.urgency,
                "relevance": it.relevance_score,
                "sentiment": it.raw_sentiment,
                "decayed_sentiment": round(it.raw_sentiment * self.classifier.compute_temporal_decay(it.timestamp_ms, now_ms), 3),
                "timestamp_ms": it.timestamp_ms
            }
            for it in self._classified_items[:15]
        ]

        return IntelligenceSnapshot(
            timestamp_ms=now_ms,
            news_sentiment_score=net_sentiment,
            geopolitical_tension_index=tension_idx,
            is_shock_stand_down_active=stand_down_active,
            stand_down_remaining_sec=remaining_sec,
            stand_down_reason=stand_down_reason,
            total_processed_headlines=len(self._classified_items),
            active_alerts_count=len(self.alerts.get_recent_alerts(10)),
            recent_headlines=recent_dicts
        )

    def evaluate_macro_shock(self, brent_pct_chg: float, vix_val: float, vix_pct_chg: float) -> None:
        """Monitors live quantitative macro indicators for sudden market shocks."""
        now_ms = time.time() * 1000.0
        # Brent Crude sharp spike > 2.2% or VIX surge > 6% indicates macro volatility expansion
        if brent_pct_chg >= 2.2:
            self.alerts.trigger_alert(
                severity="CRITICAL_SHOCK",
                event_type="CRUDE_PRICE_SPIKE",
                headline=f"Brent Crude spiked +{brent_pct_chg:.2f}% intraday — Inflation and trade deficit risk elevated",
                action_recommended="PAUSE_ENTRIES_15M",
                source="MacroBenchmark"
            )
        elif vix_pct_chg >= 6.5 or vix_val >= 22.0:
            self.alerts.trigger_alert(
                severity="CRITICAL_SHOCK",
                event_type="VOLATILITY_EXPANSION_SHOCK",
                headline=f"Volatility surge: VIX at {vix_val:.1f} (+{vix_pct_chg:.1f}%) — High risk of gap risk and adverse selection",
                action_recommended="PAUSE_ENTRIES_15M",
                source="MacroBenchmark"
            )


market_intelligence = MarketIntelligenceEngine()
