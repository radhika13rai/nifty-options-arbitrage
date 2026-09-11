"""
Continuous Live Market Data Streamer & Health Watchdog (Paper V2).
Ingests live or simulated L2 orderbook feeds, validates tick freshness (< 1,500ms),
manages active strike subscriptions, and routes ticks to the autonomous execution engine.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from config import config
from market_data.normalizer import MarketDataNormalizer, MarketTick
from market_data.orderbook import orderbook_manager
from market_data.replay import replay_engine
from risk.stale_data_guard import stale_data_guard

logger = logging.getLogger("LiveMarketDataStreamer")


@dataclass(frozen=True)
class StreamHealthTelemetry:
    is_connected: bool
    mode: str
    total_ticks_received: int
    last_tick_time_ms: float
    stale_ticks_dropped: int
    reconnect_count: int
    subscribed_symbols: list[str]
    latency_ms: float


class LiveMarketDataStreamer:
    """
    Production-grade streaming coordinator for NIFTY options market data.
    Provides sub-millisecond dispatching, fail-closed staleness checks,
    and automatic reconnection.
    """

    def __init__(self):
        self.is_running: bool = False
        self.mode: str = "SIMULATED_REPLAY"
        self._task: Optional[asyncio.Task] = None
        self._subscribers: list[Callable[[MarketTick], None]] = []
        self._subscribed_symbols: set[str] = set()
        self._total_ticks: int = 0
        self._stale_ticks: int = 0
        self._last_tick_time_ms: float = 0.0
        self._reconnect_count: int = 0
        self._has_live_credentials = bool(config.dhan_client_id and config.dhan_access_token)

    def subscribe_symbol(self, symbol: str) -> None:
        """Adds instrument to active watch list."""
        self._subscribed_symbols.add(symbol)
        logger.debug(f"LiveMarketDataStreamer: Subscribed to {symbol}")

    def add_tick_listener(self, callback: Callable[[MarketTick], None]) -> None:
        """Registers listener for normalized market ticks."""
        self._subscribers.append(callback)

    def dispatch_tick(self, tick: MarketTick) -> None:
        """
        Validates freshness and routes tick to orderbook and registered subscribers.
        """
        now_ms = time.time() * 1000.0
        self._total_ticks += 1
        self._last_tick_time_ms = now_ms

        # Staleness check
        staleness = stale_data_guard.check_tick(tick)
        if not staleness.is_fresh:
            self._stale_ticks += 1
            logger.warning(f"LiveMarketDataStreamer: Dropping stale tick on {tick.symbol} ({staleness.age_ms:.1f}ms latency)")
            return

        # Update orderbook snapshot
        orderbook_manager.update_tick(tick)

        # Notify downstream consumers
        for cb in self._subscribers:
            try:
                cb(tick)
            except Exception as e:
                logger.error(f"LiveMarketDataStreamer: Error in tick subscriber: {e}")

    async def start(self) -> None:
        """Starts continuous ingestion loop."""
        if self.is_running:
            return

        self.is_running = True
        self.mode = "LIVE_DHAN_WEBSOCKET" if self._has_live_credentials else "SIMULATED_REPLAY"
        logger.info(f"Starting LiveMarketDataStreamer in mode: {self.mode}")

        if self._has_live_credentials:
            self._task = asyncio.create_task(self._run_live_websocket())
        else:
            self._task = asyncio.create_task(self._run_simulated_stream())

    async def stop(self) -> None:
        """Gracefully halts data ingestion."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("LiveMarketDataStreamer stopped.")

    async def _run_simulated_stream(self) -> None:
        """Replays realistic multi-strike options tick batches continuously."""
        try:
            async for tick_batch in replay_engine.stream_ticks(interval_sec=0.15):
                if not self.is_running:
                    break
                for tick in tick_batch:
                    self.dispatch_tick(tick)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"LiveMarketDataStreamer: Simulation feed error: {e}")

    async def _run_live_websocket(self) -> None:
        """DhanHQ read-only WebSocket client with automatic exponential backoff."""
        import websockets
        ws_url = f"wss://api-feed.dhan.co?version=2&token={config.dhan_access_token}&clientId={config.dhan_client_id}&authType=2"
        backoff = 1.0

        while self.is_running:
            try:
                async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("LiveMarketDataStreamer: Connected to DhanHQ Live Market Feed.")
                    backoff = 1.0

                    while self.is_running:
                        msg = await ws.recv()
                        if isinstance(msg, bytes):
                            continue
                        data = json.loads(msg)
                        tick = MarketDataNormalizer.normalize_dhan_tick(data)
                        if tick:
                            self.dispatch_tick(tick)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._reconnect_count += 1
                logger.warning(f"LiveMarketDataStreamer: Connection dropped ({e}). Reconnecting in {backoff:.1f}s...")
                await asyncio.sleep(backoff)
                backoff = min(30.0, backoff * 1.5)

    def get_health(self) -> StreamHealthTelemetry:
        """Returns instantaneous streaming telemetry and health metrics."""
        now_ms = time.time() * 1000.0
        latency = (now_ms - self._last_tick_time_ms) if self._last_tick_time_ms > 0 else 0.0
        return StreamHealthTelemetry(
            is_connected=self.is_running and (latency < 3000.0 or self._total_ticks == 0),
            mode=self.mode,
            total_ticks_received=self._total_ticks,
            last_tick_time_ms=self._last_tick_time_ms,
            stale_ticks_dropped=self._stale_ticks,
            reconnect_count=self._reconnect_count,
            subscribed_symbols=sorted(list(self._subscribed_symbols)),
            latency_ms=round(latency, 1)
        )

    def reset(self) -> None:
        """Resets telemetry counters."""
        self._total_ticks = 0
        self._stale_ticks = 0
        self._last_tick_time_ms = 0.0
        self._reconnect_count = 0


market_streamer = LiveMarketDataStreamer()
