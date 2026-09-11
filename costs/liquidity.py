"""
Liquidity & Market Depth Health Scorer for Options Contracts.
Ensures algorithm only trades contracts with sufficient depth to avoid predatory fills.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class LiquidityMetrics:
    symbol: str
    best_bid: float
    best_ask: float
    bid_ask_spread: float
    spread_pct: float
    bid_depth_volume: int
    ask_depth_volume: int
    health_status: Literal["HIGHLY_LIQUID", "MODERATE", "THIN", "ILLIQUID"]
    is_tradable: bool


class LiquidityScorer:
    """Evaluates options orderbook health before permitting order execution."""

    def __init__(self, max_spread_pct: float = 8.0, min_depth_volume: int = 130):
        # 130 units = 2 lots of 65
        self.max_spread_pct = max_spread_pct
        self.min_depth_volume = min_depth_volume

    def evaluate(
        self,
        symbol: str,
        best_bid: float,
        best_ask: float,
        bid_depth_volume: int,
        ask_depth_volume: int
    ) -> LiquidityMetrics:
        """Analyzes spread and depth."""
        if best_bid <= 0 or best_ask <= 0:
            return LiquidityMetrics(
                symbol=symbol,
                best_bid=best_bid,
                best_ask=best_ask,
                bid_ask_spread=0.0,
                spread_pct=100.0,
                bid_depth_volume=bid_depth_volume,
                ask_depth_volume=ask_depth_volume,
                health_status="ILLIQUID",
                is_tradable=False
            )

        spread = round(best_ask - best_bid, 2)
        mid_price = (best_ask + best_bid) / 2.0
        spread_pct = round((spread / mid_price) * 100, 2) if mid_price > 0 else 100.0
        total_depth = bid_depth_volume + ask_depth_volume

        if spread_pct <= 2.5 and total_depth >= self.min_depth_volume * 4:
            status: Literal["HIGHLY_LIQUID", "MODERATE", "THIN", "ILLIQUID"] = "HIGHLY_LIQUID"
            tradable = True
        elif spread_pct <= self.max_spread_pct and total_depth >= self.min_depth_volume:
            status = "MODERATE"
            tradable = True
        elif spread_pct <= 15.0:
            status = "THIN"
            tradable = False
        else:
            status = "ILLIQUID"
            tradable = False

        return LiquidityMetrics(
            symbol=symbol,
            best_bid=best_bid,
            best_ask=best_ask,
            bid_ask_spread=spread,
            spread_pct=spread_pct,
            bid_depth_volume=bid_depth_volume,
            ask_depth_volume=ask_depth_volume,
            health_status=status,
            is_tradable=tradable
        )


liquidity_scorer = LiquidityScorer()
