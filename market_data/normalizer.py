"""
Market Data Normalizer & Tick Validation Module.
Normalizes heterogeneous broker feeds (Dhan, Kite, NSE mock) into a unified high-performance schema.
"""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class DepthLevel:
    price: float
    size: int
    orders: int = 1


@dataclass
class MarketTick:
    """Standardized normalized market quote tick."""
    symbol: str
    timestamp_ms: float  # Unix timestamp in milliseconds
    ltp: float  # Last Traded Price
    volume: int
    best_bid: float
    best_ask: float
    bid_size: int
    ask_size: int
    open_interest: int = 0
    bids: list[DepthLevel] = field(default_factory=list)
    asks: list[DepthLevel] = field(default_factory=list)

    @property
    def mid_price(self) -> float:
        if self.best_bid > 0 and self.best_ask > 0:
            return round((self.best_bid + self.best_ask) / 2.0, 2)
        return self.ltp

    @property
    def spread(self) -> float:
        return round(max(0.0, self.best_ask - self.best_bid), 2)

    @property
    def age_ms(self) -> float:
        """Calculates age of tick relative to current system time."""
        current_time_ms = time.time() * 1000.0
        return max(0.0, current_time_ms - self.timestamp_ms)

    def is_valid(self) -> bool:
        """Validates that market quote is not corrupted or inverted."""
        if self.ltp < 0 or self.best_bid < 0 or self.best_ask < 0:
            return False
        # Crossed market check (bid > ask is an anomalous condition)
        if self.best_bid > 0 and self.best_ask > 0 and self.best_bid > self.best_ask:
            return False
        return True


class MarketDataNormalizer:
    """Parses raw inbound payloads into validated MarketTick instances."""

    @staticmethod
    def normalize_dhan_tick(raw_data: dict) -> Optional[MarketTick]:
        """Parses DhanHQ v2 WebSocket / REST quote format."""
        try:
            symbol = raw_data.get("security_id") or raw_data.get("symbol", "")
            ltp = float(raw_data.get("LTP", raw_data.get("last_price", 0.0)))
            timestamp_ms = float(raw_data.get("exchange_timestamp", time.time() * 1000))
            
            depth = raw_data.get("depth", {})
            buy_depth = depth.get("buy", [])
            sell_depth = depth.get("sell", [])
            
            best_bid = float(buy_depth[0].get("price", ltp)) if buy_depth else ltp
            bid_size = int(buy_depth[0].get("quantity", 0)) if buy_depth else 0
            best_ask = float(sell_depth[0].get("price", ltp)) if sell_depth else ltp
            ask_size = int(sell_depth[0].get("quantity", 0)) if sell_depth else 0

            bids = [
                DepthLevel(price=float(d.get("price", 0)), size=int(d.get("quantity", 0)), orders=int(d.get("orders", 1)))
                for d in buy_depth[:5]
            ]
            asks = [
                DepthLevel(price=float(d.get("price", 0)), size=int(d.get("quantity", 0)), orders=int(d.get("orders", 1)))
                for d in sell_depth[:5]
            ]

            tick = MarketTick(
                symbol=str(symbol),
                timestamp_ms=timestamp_ms,
                ltp=ltp,
                volume=int(raw_data.get("volume", 0)),
                best_bid=best_bid,
                best_ask=best_ask,
                bid_size=bid_size,
                ask_size=ask_size,
                open_interest=int(raw_data.get("oi", 0)),
                bids=bids,
                asks=asks
            )
            return tick if tick.is_valid() else None
        except Exception:
            return None

    @staticmethod
    def create_synthetic_tick(
        symbol: str,
        mid_price: float,
        spread: float = 0.20,
        volume: int = 5000,
        bid_qty: int = 650,
        ask_qty: int = 650
    ) -> MarketTick:
        """Creates a realistic Level-2 synthetic tick for simulations."""
        half_spread = spread / 2.0
        best_bid = round(max(0.05, mid_price - half_spread), 2)
        best_ask = round(best_bid + spread, 2)
        now_ms = time.time() * 1000.0

        bids = [
            DepthLevel(price=round(best_bid - (i * 0.10), 2), size=int(bid_qty * (1 - i * 0.15)), orders=i + 1)
            for i in range(5)
        ]
        asks = [
            DepthLevel(price=round(best_ask + (i * 0.10), 2), size=int(ask_qty * (1 - i * 0.15)), orders=i + 1)
            for i in range(5)
        ]

        return MarketTick(
            symbol=symbol,
            timestamp_ms=now_ms,
            ltp=round(mid_price, 2),
            volume=volume,
            best_bid=best_bid,
            best_ask=best_ask,
            bid_size=bid_qty,
            ask_size=ask_qty,
            bids=bids,
            asks=asks
        )
