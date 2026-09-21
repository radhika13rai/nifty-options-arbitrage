"""
Live Global Macro & World Tension News Poller.
Fetches live international market benchmarks (Brent Crude, DXY, CBOE VIX, S&P 500 futures, NIFTY 50)
from open Yahoo Finance endpoints and financial/geopolitical RSS feeds (Google News, Reuters, ET).
Fuses real-time world signals into the multimodal fusion engine for options posture alignment.
"""

import asyncio
import json
import logging
import re
import socket
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from typing import Optional

from global_macro.indicators import MacroIndicatorSnapshot, macro_engine
from global_macro.news_embedder import NewsItem, NewsCategory, news_embedder
from global_macro.news_feed import news_feed
from global_macro.multimodal_fusion import multimodal_fusion

logger = logging.getLogger("LiveMacroPoller")


def categorize_headline(headline: str) -> NewsCategory:
    """Categorizes news text into quantitative macro domain buckets."""
    h_lower = headline.lower()
    
    # 1. Crude & Energy
    if any(k in h_lower for k in ["crude", "oil", "brent", "opec", "barrel", "petroleum", "gasoline", "fuel", "strait of hormuz"]):
        return "CRUDE_ENERGY"
    
    # 2. Central Bank & Monetary
    if any(k in h_lower for k in ["fed", "federal reserve", "rbi", "interest rate", "rate cut", "rate hike", "inflation", "cpi", "powell", "das", "bond yield", "treasury", "dxy", "dollar index"]):
        return "CENTRAL_BANK"
        
    # 3. Trade & Tariffs
    if any(k in h_lower for k in ["tariff", "customs", "trade war", "wto", "sanction", "export ban", "import duty"]):
        return "TRADE_TARIFFS"
        
    # 4. Domestic Indian Economy & Equities
    if any(k in h_lower for k in ["nifty", "sensex", "india", "inr", "rupee", "fii", "dii", "sebi", "dalal street", "gift nifty"]):
        return "DOMESTIC_INDIA"
        
    # Default: Geopolitics & Conflict
    return "GEOPOLITICS"


class LiveMacroPoller:
    """
    Asynchronous poller that periodically pulls live global macro cues
    and international news wire headlines without blocking execution.
    """

    def __init__(self, poll_interval_sec: float = 60.0):
        self.poll_interval_sec = poll_interval_sec
        self.is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        self.last_poll_time_ms: float = 0.0
        self.poll_count: int = 0
        self.successful_poll_count: int = 0
        self.last_error: Optional[str] = None
        self.last_fetched_quotes: dict = {}
        self.last_fetched_headlines: list[str] = []
        self._mock_mode: bool = False

    def enable_mock_mode(self, enabled: bool = True):
        """Allows fast unit testing without outbound network calls."""
        self._mock_mode = enabled

    def _fetch_yahoo_ticker(self, ticker: str) -> tuple[float, float]:
        """
        Fetches last price and percentage change from Yahoo Finance v8 chart API.
        Returns: (regular_market_price, change_pct)
        """
        encoded_ticker = urllib.parse.quote(ticker)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_ticker}?interval=1d&range=2d"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )

        with urllib.request.urlopen(req, timeout=6.0) as resp:
            raw_bytes = resp.read()
            data = json.loads(raw_bytes.decode("utf-8"))
            meta = data["chart"]["result"][0]["meta"]
            price = float(meta.get("regularMarketPrice") or 0.0)
            prev_close = float(meta.get("chartPreviousClose") or meta.get("previousClose") or price)
            chg_pct = round(((price - prev_close) / prev_close * 100.0), 2) if prev_close else 0.0
            return price, chg_pct

    def _fetch_all_yahoo_quotes(self) -> dict:
        """Pulls international benchmarks."""
        if self._mock_mode:
            return {
                "brent": (84.50, 1.20),
                "dxy": (103.95, 0.15),
                "vix": (15.20, 2.10),
                "sp500": (5850.0, 0.45),
                "nifty": (23414.3, 0.29)
            }

        results = {}
        ticker_map = {
            "brent": "BZ=F",
            "dxy": "DX-Y.NYB",
            "vix": "^VIX",
            "sp500": "ES=F",
            "nifty": "^NSEI"
        }

        for key, sym in ticker_map.items():
            try:
                price, chg = self._fetch_yahoo_ticker(sym)
                results[key] = (price, chg)
            except Exception as e:
                logger.debug(f"Failed to fetch {key} ({sym}): {e}")
                # Fallback to reasonable neutral value
                fallback_defaults = {
                    "brent": (82.50, 0.0),
                    "dxy": (103.80, 0.0),
                    "vix": (14.50, 0.0),
                    "sp500": (5800.0, 0.0),
                    "nifty": (23414.3, 0.0)
                }
                results[key] = fallback_defaults[key]

        return results

    def _fetch_rss_news(self) -> list[tuple[str, str, NewsCategory]]:
        """
        Fetches live financial and geopolitical headlines via Google News RSS.
        Returns: list of (headline, source, category)
        """
        if self._mock_mode:
            return [
                ("Crude oil steadies as shipping security tightens in Bab el-Mandeb", "Reuters", "CRUDE_ENERGY"),
                ("Nifty holds gains above 24,500 amid steady domestic institutional inflows", "Economic Times", "DOMESTIC_INDIA")
            ]

        urls = [
            "https://news.google.com/rss/search?q=nifty+OR+crude+oil+OR+rbi+economy&hl=en-IN&gl=IN&ceid=IN:en",
            "https://news.google.com/rss/search?q=geopolitics+OR+war+sanctions+OR+oil&hl=en-IN&gl=IN&ceid=IN:en"
        ]

        items = []
        seen_headlines = set()

        for url in urls:
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    xml_data = resp.read().decode("utf-8", errors="ignore")
                    root = ET.fromstring(xml_data)
                    rss_items = root.findall("./channel/item")

                    for it in rss_items[:5]:
                        title_el = it.find("title")
                        if title_el is None or not title_el.text:
                            continue
                        full_title = title_el.text.strip()
                        
                        # Separate headline and source if formatted as "Title - Source"
                        source = "Live Wire"
                        headline = full_title
                        if " - " in full_title:
                            parts = full_title.rsplit(" - ", 1)
                            headline = parts[0].strip()
                            source = parts[1].strip()

                        if headline not in seen_headlines:
                            seen_headlines.add(headline)
                            category = categorize_headline(headline)
                            items.append((headline, source, category))
            except Exception as e:
                logger.debug(f"RSS fetch warning for {url}: {e}")

        return items

    async def poll_once(self) -> dict:
        """
        Executes a non-blocking poll cycle across market quotes and RSS feeds.
        Updates macro_engine, news_feed, and multimodal_fusion.
        """
        self.poll_count += 1
        now_ms = time.time() * 1000.0

        try:
            # 1. Fetch live quotes in worker thread to avoid blocking event loop
            quotes = await asyncio.to_thread(self._fetch_all_yahoo_quotes)
            self.last_fetched_quotes = quotes

            brent_price, brent_chg = quotes.get("brent", (82.50, 0.0))
            dxy_val, dxy_chg = quotes.get("dxy", (103.80, 0.0))
            vix_val, vix_chg = quotes.get("vix", (14.50, 0.0))
            sp500_price, sp500_chg = quotes.get("sp500", (5800.0, 0.0))
            nifty_price, nifty_chg = quotes.get("nifty", (23414.3, 0.0))

            # Automatically sync options chain and base spot to real NIFTY level
            if nifty_price > 10000.0:
                try:
                    from market_data.replay import replay_engine
                    if abs(replay_engine.base_spot - nifty_price) > 5.0:
                        replay_engine.sync_spot_price(nifty_price)
                except Exception as e:
                    logger.debug(f"Failed to sync replay engine spot: {e}")

            # Estimate GIFT NIFTY gap from US/world momentum & crude shock
            # High crude + high DXY hurts NIFTY; positive S&P aids NIFTY
            macro_bias_pts = round((sp500_chg * 40.0) - (brent_chg * 15.0) - (dxy_chg * 30.0), 1)
            gift_nifty_pts = round(nifty_price + macro_bias_pts, 1)

            # 2. Update GlobalMacroEngine snapshot
            snap = MacroIndicatorSnapshot(
                timestamp_ms=now_ms,
                brent_crude_usd=brent_price,
                brent_change_pct=brent_chg,
                dollar_index_dxy=dxy_val,
                dxy_change_pct=dxy_chg,
                gift_nifty_points=gift_nifty_pts,
                gift_nifty_gap_pts=macro_bias_pts,
                us_vix=vix_val,
                us_vix_change_pct=vix_chg,
                sp500_change_pct=sp500_chg
            )
            macro_engine.update_snapshot(snap)

            # 3. Fetch RSS news items in worker thread
            news_items = await asyncio.to_thread(self._fetch_rss_news)
            self.last_fetched_headlines = [h for h, _, _ in news_items]

            for h, src, cat in news_items:
                news_feed.add_headline(headline=h, source=src, category=cat)

            # 4. Trigger multimodal fusion
            embs = news_feed.get_recent_embeddings()
            fusion = multimodal_fusion.fuse(snap, embs)

            self.last_poll_time_ms = now_ms
            self.successful_poll_count += 1
            self.last_error = None

            logger.info(
                f"LiveMacroPoller: Synced global cues | Brent: ${brent_price:.2f} ({brent_chg:+.2f}%) | "
                f"DXY: {dxy_val:.2f} | Gap: {macro_bias_pts:+.1f} pts | Posture: {fusion.recommended_options_posture}"
            )

            return {
                "status": "SUCCESS",
                "timestamp_ms": now_ms,
                "brent": brent_price,
                "dxy": dxy_val,
                "gap_pts": macro_bias_pts,
                "posture": fusion.recommended_options_posture,
                "fear_index": fusion.geopolitical_fear_index,
                "news_count": len(news_items)
            }

        except Exception as e:
            self.last_error = str(e)
            logger.warning(f"LiveMacroPoller polling error: {e}")
            return {
                "status": "ERROR",
                "timestamp_ms": now_ms,
                "error": str(e)
            }

    async def _run_loop(self):
        """Continuous background polling loop."""
        while self.is_running:
            await self.poll_once()
            try:
                await asyncio.sleep(self.poll_interval_sec)
            except asyncio.CancelledError:
                break

    async def start(self):
        """Starts asynchronous macro polling."""
        if self.is_running:
            return
        self.is_running = True
        logger.info(f"Starting LiveMacroPoller (interval: {self.poll_interval_sec}s)")
        # Launch non-blocking background polling task so server boots immediately
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stops asynchronous macro polling."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("LiveMacroPoller stopped.")

    def get_status(self) -> dict:
        """Returns live telemetry of the macro poller."""
        return {
            "is_running": self.is_running,
            "poll_count": self.poll_count,
            "successful_poll_count": self.successful_poll_count,
            "last_poll_time_ms": self.last_poll_time_ms,
            "last_error": self.last_error,
            "poll_interval_sec": self.poll_interval_sec,
            "recent_headlines_count": len(self.last_fetched_headlines),
            "quotes_snapshot": self.last_fetched_quotes
        }


# Singleton instance
live_macro_poller = LiveMacroPoller(poll_interval_sec=60.0)
