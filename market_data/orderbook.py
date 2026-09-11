"""
In-Memory Orderbook & Microstructure State Manager.
Maintains continuous Level-2 orderbook state, calculates micro-price and imbalance,
and tracks tick staleness.
"""

import time
from dataclasses import dataclass
from typing import Optional
from market_data.normalizer import MarketTick, DepthLevel


@dataclass(frozen=True)
class OrderbookSnapshot:
    symbol: str
    timestamp_ms: float
    age_ms: float
    best_bid: float
    best_ask: float
    mid_price: float
    micro_price: float
    spread: float
    imbalance: float  # Range: [-1.0, 1.0]. Positive means buy pressure.
    total_bid_volume: int
    total_ask_volume: int
    bids: list[DepthLevel]
    asks: list[DepthLevel]


class Orderbook:
    """Manages real-time orderbook state for a specific instrument."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.latest_tick: Optional[MarketTick] = None
        self.last_update_ms: float = 0.0

    def update(self, tick: MarketTick) -> None:
        """Applies inbound normalized market tick."""
        if tick.symbol != self.symbol:
            raise ValueError(f"Symbol mismatch: expected {self.symbol}, got {tick.symbol}")
        self.latest_tick = tick
        self.last_update_ms = time.time() * 1000.0

    def get_snapshot(self) -> Optional[OrderbookSnapshot]:
        """Returns instantaneous snapshot of the orderbook with micro-price metrics."""
        if not self.latest_tick:
            return None

        tick = self.latest_tick
        now_ms = time.time() * 1000.0
        age_ms = max(0.0, now_ms - self.last_update_ms)

        best_bid = tick.best_bid
        best_ask = tick.best_ask
        mid_price = tick.mid_price
        spread = tick.spread

        # Calculate depth volumes
        tot_bid_vol = sum(d.size for d in tick.bids) if tick.bids else tick.bid_size
        tot_ask_vol = sum(d.size for d in tick.asks) if tick.asks else tick.ask_size

        # Micro-price: Volume-weighted mid price
        total_vol = tot_bid_vol + tot_ask_vol
        if total_vol > 0 and best_bid > 0 and best_ask > 0:
            micro_price = round(((best_ask * tot_bid_vol) + (best_bid * tot_ask_vol)) / total_vol, 2)
            imbalance = round((tot_bid_vol - tot_ask_vol) / total_vol, 3)
        else:
            micro_price = mid_price
            imbalance = 0.0

        return OrderbookSnapshot(
            symbol=self.symbol,
            timestamp_ms=self.last_update_ms,
            age_ms=age_ms,
            best_bid=best_bid,
            best_ask=best_ask,
            mid_price=mid_price,
            micro_price=micro_price,
            spread=spread,
            imbalance=imbalance,
            total_bid_volume=tot_bid_vol,
            total_ask_volume=tot_ask_vol,
            bids=tick.bids,
            asks=tick.asks
        )


class OrderbookManager:
    """Manages active orderbooks across all subscribed symbols."""

    def __init__(self):
        self._books: dict[str, Orderbook] = {}

    def get_or_create(self, symbol: str) -> Orderbook:
        if symbol not in self._books:
            self._books[symbol] = Orderbook(symbol)
        return self._books[symbol]

    def update_tick(self, tick: MarketTick) -> None:
        book = self.get_or_create(tick.symbol)
        book.update(tick)

    def get_snapshot(self, symbol: str) -> Optional[OrderbookSnapshot]:
        book = self._books.get(symbol)
        return book.get_snapshot() if book else None

    def get_all_snapshots(self) -> dict[str, OrderbookSnapshot]:
        snapshots = {}
        for sym, book in self._books.items():
            snap = book.get_snapshot()
            if snap:
                snapshots[sym] = snap
        return snapshots


orderbook_manager = OrderbookManager()
