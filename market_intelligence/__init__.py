"""
Market Intelligence Package.
Provides news deduplication, entity classification, temporal decay,
breaking shock alert generation, and macro shock detection.
"""

from market_intelligence.deduplicator import news_deduplicator, NewsDeduplicator
from market_intelligence.classifier import news_classifier, NewsClassifier, ClassifiedHeadline
from market_intelligence.alert_engine import alert_engine, AlertEngine, MarketAlert
from market_intelligence.engine import market_intelligence, MarketIntelligenceEngine, IntelligenceSnapshot

__all__ = [
    "news_deduplicator",
    "NewsDeduplicator",
    "news_classifier",
    "NewsClassifier",
    "ClassifiedHeadline",
    "alert_engine",
    "AlertEngine",
    "MarketAlert",
    "market_intelligence",
    "MarketIntelligenceEngine",
    "IntelligenceSnapshot",
]
