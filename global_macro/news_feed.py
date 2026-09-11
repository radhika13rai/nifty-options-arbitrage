"""
Global News Wire Feed & Scenario Manager.
Ingests live financial wire headlines and simulates realistic geopolitical scenarios.
"""

import time
from typing import Optional
from global_macro.news_embedder import NewsItem, NewsEmbedding, news_embedder


class GlobalNewsFeed:
    """Manages continuous ingestion, caching, and embedding of news wire headlines."""

    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self._news_items: list[NewsItem] = []
        self._cached_embeddings: list[NewsEmbedding] = []
        self._init_baseline_news()

    def _init_baseline_news(self):
        """Initializes default baseline global headlines."""
        baseline = [
            ("Asian markets steady as investors weigh central bank commentary", "Reuters", "CENTRAL_BANK"),
            ("Brent crude hovers around $82 as supply conditions remain stable", "Bloomberg", "CRUDE_ENERGY"),
            ("Indian manufacturing PMI shows resilient domestic demand", "Economic Times", "DOMESTIC_INDIA"),
            ("Global shipping routes operating without major delays", "PTI", "GEOPOLITICS")
        ]
        now = time.time() * 1000.0
        for h, src, cat in baseline:
            item = NewsItem(headline=h, source=src, timestamp_ms=now, category=cat)
            self._add_item(item)

    def _add_item(self, item: NewsItem) -> NewsEmbedding:
        emb = news_embedder.embed_headline(item)
        self._news_items.insert(0, item)
        self._cached_embeddings.insert(0, emb)
        if len(self._news_items) > self.max_history:
            self._news_items.pop()
            self._cached_embeddings.pop()
        return emb

    def add_headline(self, headline: str, source: str = "Live Wire", category: str = "GEOPOLITICS") -> NewsEmbedding:
        """Injects a new headline into the real-time news pipeline."""
        item = NewsItem(
            headline=headline,
            source=source,
            timestamp_ms=time.time() * 1000.0,
            category=category  # type: ignore
        )
        return self._add_item(item)

    def load_scenario(self, scenario_name: str) -> list[NewsEmbedding]:
        """Loads a synchronized batch of headlines representing a real-world geopolitical shock."""
        self._news_items.clear()
        self._cached_embeddings.clear()
        now = time.time() * 1000.0

        if scenario_name == "MIDDLE_EAST_WAR_CRISIS":
            headlines = [
                ("Breaking: Missile strikes reported on commercial tankers in Red Sea shipping corridor", "Reuters", "GEOPOLITICS"),
                ("Brent crude surges past $89 as Middle East military escalation threatens Strait of Hormuz", "Bloomberg", "CRUDE_ENERGY"),
                ("UN convenes emergency security council meeting amid widening regional war threats", "PTI", "GEOPOLITICS"),
                ("FIIs accelerate emerging market equity selloff as global risk-off intensifies", "Economic Times", "CENTRAL_BANK")
            ]
        elif scenario_name == "GLOBAL_DEESCALATION_RELIEF":
            headlines = [
                ("Diplomatic breakthrough: Regional ceasefire treaty signed; international sanctions eased", "Reuters", "GEOPOLITICS"),
                ("Crude oil plunges 3.6% as peace agreement restores safe passage in vital waterways", "Bloomberg", "CRUDE_ENERGY"),
                ("Global equity markets rally sharply in relief; safe-haven dollar demand softens", "PTI", "GEOPOLITICS"),
                ("Foreign institutional investors turn net buyers in Indian equities amid de-escalation", "Economic Times", "DOMESTIC_INDIA")
            ]
        elif scenario_name == "US_FED_HAWKISH_SURPRISE":
            headlines = [
                ("US Federal Reserve signals surprise interest rate hike as inflation pressures persist", "Reuters", "CENTRAL_BANK"),
                ("US Dollar Index (DXY) rallies to 4-month high against emerging market basket", "Bloomberg", "CENTRAL_BANK"),
                ("Bond yields spike globally; emerging market central banks prepare defense", "PTI", "CENTRAL_BANK"),
                ("NIFTY facing opening pressure as FII liquidity outflows accelerate", "Economic Times", "DOMESTIC_INDIA")
            ]
        else:  # NEUTRAL
            self._init_baseline_news()
            return self._cached_embeddings

        for h, src, cat in headlines:
            item = NewsItem(headline=h, source=src, timestamp_ms=now, category=cat)  # type: ignore
            self._add_item(item)

        return self._cached_embeddings

    def get_recent_embeddings(self, limit: int = 10) -> list[NewsEmbedding]:
        return self._cached_embeddings[:limit]

    def get_recent_items(self, limit: int = 10) -> list[dict]:
        return [
            {
                "headline": self._cached_embeddings[i].headline,
                "source": self._news_items[i].source,
                "category": self._news_items[i].category,
                "sentiment": self._cached_embeddings[i].directional_sentiment,
                "conflict_intensity": self._cached_embeddings[i].geopolitical_conflict_intensity,
                "timestamp_ms": self._news_items[i].timestamp_ms
            }
            for i in range(min(limit, len(self._cached_embeddings)))
        ]


news_feed = GlobalNewsFeed()
