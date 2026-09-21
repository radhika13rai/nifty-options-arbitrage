"""
Market Data Feed Client & Event Dispatcher.
Connects to DhanHQ v2 Live WebSocket feed when credentials are provided,
or seamlessly falls back to the deterministic local replay engine.
"""

import asyncio
import json
import logging
from typing import Callable, Optional
from config import config
from market_data.normalizer import MarketDataNormalizer, MarketTick
from market_data.orderbook import orderbook_manager
from market_data.replay import replay_engine

logger = logging.getLogger("MarketDataFeed")


class MarketDataFeed:
    """Manages continuous ingestion of market data ticks."""

    def __init__(self):
        self.is_running: bool = False
        self._subscribers: list[Callable[[MarketTick], None]] = []
        self._task: Optional[asyncio.Task] = None
        self.use_live_broker: bool = bool(config.dhan_client_id and config.dhan_access_token)

    def subscribe(self, callback: Callable[[MarketTick], None]) -> None:
        """Register a callback for incoming ticks."""
        self._subscribers.append(callback)

    def _dispatch(self, tick: MarketTick) -> None:
        """Update internal orderbook and dispatch to all registered listeners."""
        orderbook_manager.update_tick(tick)
        try:
            from market_data.stream import market_streamer
            market_streamer.dispatch_tick(tick)
        except Exception:
            pass
        for cb in self._subscribers:
            try:
                cb(tick)
            except Exception as e:
                logger.error(f"Error in subscriber callback: {e}")

    async def start(self) -> None:
        """Starts market feed streaming."""
        if self.is_running:
            return

        self.is_running = True
        logger.info(f"Starting MarketDataFeed (mode: {'LIVE_DHAN' if self.use_live_broker else 'SIMULATED_REPLAY'})")

        if self.use_live_broker:
            self._task = asyncio.create_task(self._run_dhan_feed())
        else:
            self._task = asyncio.create_task(self._run_replay_feed())

    async def stop(self) -> None:
        """Stops market feed."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("MarketDataFeed stopped.")

    async def _run_replay_feed(self) -> None:
        """Streams synthetic high-fidelity options ticks from replay engine."""
        try:
            async for tick_batch in replay_engine.stream_ticks(interval_sec=0.20):
                if not self.is_running:
                    break
                for tick in tick_batch:
                    self._dispatch(tick)
        except asyncio.CancelledError:
            pass

    async def _run_dhan_feed(self) -> None:
        """DhanHQ v2 live WebSocket client for market depth (data feed only)."""
        import websockets
        
        # Guard against connecting without actual credentials
        if not config.dhan_access_token or not config.dhan_client_id:
            logger.info("MarketDataFeed: DhanHQ credentials not configured. Live feed idle.")
            return

        ws_url = f"wss://api-feed.dhan.co?version=2&token={config.dhan_access_token}&clientId={config.dhan_client_id}&authType=2"
        consecutive_drops = 0
        fallback_task = None
        
        while self.is_running:
            try:
                logger.info("MarketDataFeed: Connecting to DhanHQ Live Market Feed at wss://api-feed.dhan.co (credentials masked)...")
                async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("MarketDataFeed: Successfully connected to DhanHQ Live Market Feed.")
                    
                    # Dispatch initial subscription for NIFTY Index & ATM Options
                    sub_payload = {
                        "RequestCode": 15,
                        "InstrumentCount": 1,
                        "InstrumentList": [
                            {"ExchangeSegment": "IDX_I", "SecurityId": "13"}
                        ]
                    }
                    try:
                        await ws.send(json.dumps(sub_payload))
                    except Exception as e:
                        logger.debug(f"MarketDataFeed: Subscription packet: {e}")

                    while self.is_running:
                        msg = await ws.recv()
                        tick = None
                        if isinstance(msg, bytes):
                            tick = MarketDataNormalizer.normalize_dhan_binary(msg)
                        else:
                            try:
                                data = json.loads(msg)
                                tick = MarketDataNormalizer.normalize_dhan_tick(data)
                            except Exception:
                                pass
                        
                        if tick:
                            consecutive_drops = 0
                            if fallback_task and not fallback_task.done():
                                fallback_task.cancel()
                                fallback_task = None
                            self._dispatch(tick)
            except asyncio.CancelledError:
                if fallback_task and not fallback_task.done():
                    fallback_task.cancel()
                break
            except Exception as e:
                consecutive_drops += 1
                clean_err = str(e).replace(config.dhan_access_token, "[REDACTED]") if config.dhan_access_token else str(e)
                if fallback_task is None or fallback_task.done():
                    logger.info("MarketDataFeed: DhanHQ WebSocket stream requires active Dhan Data API add-on subscription. Engaging seamless high-fidelity simulation stream...")
                    fallback_task = asyncio.create_task(self._run_replay_feed())
                logger.warning(f"MarketDataFeed: Connection dropped ({clean_err}). Next Dhan probe in 30s...")
                await asyncio.sleep(30.0)


market_feed = MarketDataFeed()
