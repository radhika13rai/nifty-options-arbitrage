"""
Microstructure Slippage & Market Impact Engine.
Models realistic fill pricing for market orders taking liquidity from the orderbook.
Never assumes mid-price fills or zero-latency executions.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SlippageEstimate:
    expected_price: float
    simulated_fill_price: float
    slippage_points: float
    slippage_inr: float
    fill_ratio: float  # 1.0 if fully filled within depth


class SlippageModel:
    """Computes conservative execution slippage against orderbook depth."""

    def __init__(self, default_slippage_points: float = 0.5):
        self.default_slippage_points = default_slippage_points

    def calculate_buy_fill(
        self,
        best_ask: float,
        quantity: int,
        ask_depth: Optional[list[dict]] = None
    ) -> SlippageEstimate:
        """
        Determines realistic fill price for a BUY market order.
        If orderbook depth is provided, walks the book. Otherwise applies conservative spread crossing.
        """
        if not ask_depth:
            simulated_fill = best_ask + self.default_slippage_points
            slippage_pts = simulated_fill - best_ask
            return SlippageEstimate(
                expected_price=best_ask,
                simulated_fill_price=round(simulated_fill, 2),
                slippage_points=round(slippage_pts, 2),
                slippage_inr=round(slippage_pts * quantity, 2),
                fill_ratio=1.0
            )

        remaining_qty = quantity
        total_cost = 0.0

        for level in ask_depth:
            price = level.get("price", best_ask)
            size = level.get("size", 0)
            fill_qty = min(remaining_qty, size)
            total_cost += fill_qty * price
            remaining_qty -= fill_qty
            if remaining_qty <= 0:
                break

        if remaining_qty > 0:
            # Depth exhausted: penalize unfulfilled portion with high slippage
            last_price = ask_depth[-1].get("price", best_ask) if ask_depth else best_ask
            penalized_price = last_price + 2.0
            total_cost += remaining_qty * penalized_price

        vwap_fill = total_cost / quantity if quantity > 0 else best_ask
        slippage_pts = max(0.0, vwap_fill - best_ask)

        return SlippageEstimate(
            expected_price=best_ask,
            simulated_fill_price=round(vwap_fill, 2),
            slippage_points=round(slippage_pts, 2),
            slippage_inr=round(slippage_pts * quantity, 2),
            fill_ratio=1.0 if remaining_qty <= 0 else round((quantity - remaining_qty) / quantity, 2)
        )

    def calculate_sell_fill(
        self,
        best_bid: float,
        quantity: int,
        bid_depth: Optional[list[dict]] = None
    ) -> SlippageEstimate:
        """
        Determines realistic fill price for a SELL market order.
        If orderbook depth is provided, walks the bid depth.
        """
        if not bid_depth:
            simulated_fill = max(0.05, best_bid - self.default_slippage_points)
            slippage_pts = best_bid - simulated_fill
            return SlippageEstimate(
                expected_price=best_bid,
                simulated_fill_price=round(simulated_fill, 2),
                slippage_points=round(slippage_pts, 2),
                slippage_inr=round(slippage_pts * quantity, 2),
                fill_ratio=1.0
            )

        remaining_qty = quantity
        total_proceeds = 0.0

        for level in bid_depth:
            price = level.get("price", best_bid)
            size = level.get("size", 0)
            fill_qty = min(remaining_qty, size)
            total_proceeds += fill_qty * price
            remaining_qty -= fill_qty
            if remaining_qty <= 0:
                break

        if remaining_qty > 0:
            last_price = bid_depth[-1].get("price", best_bid) if bid_depth else best_bid
            penalized_price = max(0.05, last_price - 2.0)
            total_proceeds += remaining_qty * penalized_price

        vwap_fill = total_proceeds / quantity if quantity > 0 else best_bid
        slippage_pts = max(0.0, best_bid - vwap_fill)

        return SlippageEstimate(
            expected_price=best_bid,
            simulated_fill_price=round(vwap_fill, 2),
            slippage_points=round(slippage_pts, 2),
            slippage_inr=round(slippage_pts * quantity, 2),
            fill_ratio=1.0 if remaining_qty <= 0 else round((quantity - remaining_qty) / quantity, 2)
        )


slippage_model = SlippageModel()
