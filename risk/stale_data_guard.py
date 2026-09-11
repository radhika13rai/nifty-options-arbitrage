"""
Stale Data Guard Module.
Monitors the age of inbound market ticks and halts execution if data exceeds latency thresholds.
"""

import time
from dataclasses import dataclass
from typing import Optional
from config import config
from market_data.normalizer import MarketTick
from market_data.orderbook import OrderbookSnapshot


@dataclass(frozen=True)
class StalenessCheckResult:
    symbol: str
    age_ms: float
    is_fresh: bool
    threshold_ms: float
    reason: str


class StaleDataGuard:
    """Detects and flags stale quote data to prevent toxic execution on lagging books."""

    def __init__(self, timeout_ms: int = config.risk.stale_quote_timeout_ms):
        self.timeout_ms = timeout_ms

    def check_tick(self, tick: Optional[MarketTick]) -> StalenessCheckResult:
        if not tick:
            return StalenessCheckResult(
                symbol="UNKNOWN",
                age_ms=float("inf"),
                is_fresh=False,
                threshold_ms=self.timeout_ms,
                reason="No market tick data available"
            )

        now_ms = time.time() * 1000.0
        age_ms = max(0.0, now_ms - tick.timestamp_ms)
        is_fresh = age_ms <= self.timeout_ms
        reason = "Data is fresh" if is_fresh else f"Market data stale: age {age_ms:.1f}ms exceeds threshold {self.timeout_ms}ms"

        return StalenessCheckResult(
            symbol=tick.symbol,
            age_ms=age_ms,
            is_fresh=is_fresh,
            threshold_ms=self.timeout_ms,
            reason=reason
        )

    def check_orderbook(self, snapshot: Optional[OrderbookSnapshot]) -> StalenessCheckResult:
        if not snapshot:
            return StalenessCheckResult(
                symbol="UNKNOWN",
                age_ms=float("inf"),
                is_fresh=False,
                threshold_ms=self.timeout_ms,
                reason="No orderbook snapshot available"
            )

        is_fresh = snapshot.age_ms <= self.timeout_ms
        reason = "Orderbook is fresh" if is_fresh else f"Orderbook stale: age {snapshot.age_ms:.1f}ms exceeds threshold {self.timeout_ms}ms"

        return StalenessCheckResult(
            symbol=snapshot.symbol,
            age_ms=snapshot.age_ms,
            is_fresh=is_fresh,
            threshold_ms=self.timeout_ms,
            reason=reason
        )


stale_data_guard = StaleDataGuard()
