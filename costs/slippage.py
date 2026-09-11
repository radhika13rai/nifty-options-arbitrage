"""
Microstructure Slippage, Market Impact & Orderbook Queue Engine (Paper V2).
Models institutional execution dynamics for NIFTY options:
  1. Price-Time (FIFO) queue priority tracking at each price level
  2. Orderbook depth walking with partial fills and depth exhaustion penalties
  3. Dynamic adverse selection drag during fast breakout regimes
  4. Passive limit vs. aggressive market order fill probability modeling
  5. Empirical calibration telemetry tracking effective-to-quoted spread ratios
"""

import math
import time
from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass(frozen=True)
class QueuePosition:
    """Represents FIFO placement inside a limit order book level."""
    price_level: float
    total_depth_at_level: int
    queue_ahead_qty: int
    our_quantity: int
    fill_probability: float
    estimated_wait_ms: float


@dataclass(frozen=True)
class SlippageEstimate:
    """Comprehensive execution cost and slippage report."""
    expected_price: float
    simulated_fill_price: float
    slippage_points: float
    slippage_inr: float
    fill_ratio: float  # 1.0 if fully filled within depth
    execution_type: Literal["AGGRESSIVE_MARKET", "PASSIVE_LIMIT"] = "AGGRESSIVE_MARKET"
    queue_position: Optional[QueuePosition] = None
    adverse_selection_drag_pts: float = 0.0
    effective_spread_pts: float = 0.0


@dataclass
class SlippageCalibrationPoint:
    timestamp: float
    side: str
    quantity: int
    quoted_price: float
    fill_price: float
    slippage_points: float
    effective_spread: float


class SlippageModel:
    """
    Advanced microstructure fill simulator modeling real Indian options execution.
    Never assumes mid-price fills or zero queue latency.
    """

    def __init__(
        self,
        default_slippage_points: float = 0.15,
        queue_priority_default: float = 0.60,
        adverse_selection_factor: float = 0.10,
        exhaustion_penalty_points: float = 1.50
    ):
        self.default_slippage_points = default_slippage_points
        self.queue_priority_default = queue_priority_default  # 60% of depth ahead in FIFO queue
        self.adverse_selection_factor = adverse_selection_factor
        self.exhaustion_penalty_points = exhaustion_penalty_points
        self.calibration_history: list[SlippageCalibrationPoint] = []
        self._max_history = 100

    def calculate_buy_fill(
        self,
        best_ask: float,
        quantity: int,
        ask_depth: Optional[list[dict]] = None,
        queue_priority: Optional[float] = None,
        is_fast_market: bool = False
    ) -> SlippageEstimate:
        """
        Determines realistic fill price for a BUY market order taking liquidity.
        Walks the book accounting for FIFO queue priority and adverse selection.
        """
        queue_factor = queue_priority if queue_priority is not None else self.queue_priority_default
        
        # Fallback if no L2 depth provided
        if not ask_depth:
            spread_crossing = self.default_slippage_points
            adverse_drag = 0.20 if is_fast_market else 0.0
            simulated_fill = round(best_ask + spread_crossing + adverse_drag, 2)
            slippage_pts = round(simulated_fill - best_ask, 2)
            
            self._record_calibration("BUY", quantity, best_ask, simulated_fill, slippage_pts, slippage_pts * 2)
            return SlippageEstimate(
                expected_price=best_ask,
                simulated_fill_price=simulated_fill,
                slippage_points=slippage_pts,
                slippage_inr=round(slippage_pts * quantity, 2),
                fill_ratio=1.0,
                execution_type="AGGRESSIVE_MARKET",
                adverse_selection_drag_pts=adverse_drag,
                effective_spread_pts=round(spread_crossing * 2, 2)
            )

        # 1. Level 1 Queue Position Modeling
        level_1 = ask_depth[0]
        level_1_price = level_1.get("price", best_ask)
        level_1_size = level_1.get("size", 100)

        # FIFO queue priority: competitors ahead of us
        queue_ahead = int(math.ceil(level_1_size * queue_factor))
        available_at_l1 = max(0, level_1_size - queue_ahead)

        # 2. Walk depth levels
        remaining_qty = quantity
        total_cost = 0.0

        # Fill available portion at Level 1
        fill_l1 = min(remaining_qty, available_at_l1)
        total_cost += fill_l1 * level_1_price
        remaining_qty -= fill_l1
        walked_past_l1 = remaining_qty > 0

        # If remaining, walk deeper levels
        if remaining_qty > 0 and len(ask_depth) > 1:
            for level in ask_depth[1:]:
                price = level.get("price", level_1_price)
                size = level.get("size", 0)
                fill_qty = min(remaining_qty, size)
                total_cost += fill_qty * price
                remaining_qty -= fill_qty
                if remaining_qty <= 0:
                    break

        # If depth is still exhausted, penalize unfulfilled portion
        if remaining_qty > 0:
            last_price = ask_depth[-1].get("price", best_ask) if ask_depth else best_ask
            penalized_price = last_price + self.exhaustion_penalty_points
            total_cost += remaining_qty * penalized_price

        # 3. Adverse Selection Drag
        base_fill = total_cost / quantity if quantity > 0 else best_ask
        if is_fast_market:
            adverse_drag = round(level_1_price * 0.005 * self.adverse_selection_factor, 2)
        elif walked_past_l1:
            adverse_drag = round(level_1_price * 0.002 * self.adverse_selection_factor, 2)
        else:
            adverse_drag = 0.0
        final_fill = round(base_fill + adverse_drag, 2)
        slippage_pts = round(max(0.0, final_fill - best_ask), 2)

        # Fill ratio
        filled_portion = quantity - remaining_qty
        fill_ratio = 1.0 if remaining_qty <= 0 else round(filled_portion / quantity, 2)

        q_pos = QueuePosition(
            price_level=level_1_price,
            total_depth_at_level=level_1_size,
            queue_ahead_qty=queue_ahead,
            our_quantity=quantity,
            fill_probability=1.0 if remaining_qty <= 0 else fill_ratio,
            estimated_wait_ms=round(queue_ahead * 2.5, 1)  # ~2.5ms per contract processing
        )

        self._record_calibration("BUY", quantity, best_ask, final_fill, slippage_pts, slippage_pts * 2)

        return SlippageEstimate(
            expected_price=best_ask,
            simulated_fill_price=final_fill,
            slippage_points=slippage_pts,
            slippage_inr=round(slippage_pts * quantity, 2),
            fill_ratio=fill_ratio,
            execution_type="AGGRESSIVE_MARKET",
            queue_position=q_pos,
            adverse_selection_drag_pts=adverse_drag,
            effective_spread_pts=round(slippage_pts * 2, 2)
        )

    def calculate_sell_fill(
        self,
        best_bid: float,
        quantity: int,
        bid_depth: Optional[list[dict]] = None,
        queue_priority: Optional[float] = None,
        is_fast_market: bool = False
    ) -> SlippageEstimate:
        """
        Determines realistic fill price for a SELL market order hitting bids.
        Walks bid depth accounting for FIFO queue priority and adverse selection.
        """
        queue_factor = queue_priority if queue_priority is not None else self.queue_priority_default

        if not bid_depth:
            spread_crossing = self.default_slippage_points
            adverse_drag = 0.20 if is_fast_market else 0.0
            simulated_fill = round(max(0.05, best_bid - spread_crossing - adverse_drag), 2)
            slippage_pts = round(best_bid - simulated_fill, 2)

            self._record_calibration("SELL", quantity, best_bid, simulated_fill, slippage_pts, slippage_pts * 2)
            return SlippageEstimate(
                expected_price=best_bid,
                simulated_fill_price=simulated_fill,
                slippage_points=slippage_pts,
                slippage_inr=round(slippage_pts * quantity, 2),
                fill_ratio=1.0,
                execution_type="AGGRESSIVE_MARKET",
                adverse_selection_drag_pts=adverse_drag,
                effective_spread_pts=round(spread_crossing * 2, 2)
            )

        # 1. Level 1 Queue Position Modeling
        level_1 = bid_depth[0]
        level_1_price = level_1.get("price", best_bid)
        level_1_size = level_1.get("size", 100)

        queue_ahead = int(math.ceil(level_1_size * queue_factor))
        available_at_l1 = max(0, level_1_size - queue_ahead)

        # 2. Walk bid depth levels
        remaining_qty = quantity
        total_proceeds = 0.0

        fill_l1 = min(remaining_qty, available_at_l1)
        total_proceeds += fill_l1 * level_1_price
        remaining_qty -= fill_l1
        walked_past_l1 = remaining_qty > 0

        if remaining_qty > 0 and len(bid_depth) > 1:
            for level in bid_depth[1:]:
                price = level.get("price", level_1_price)
                size = level.get("size", 0)
                fill_qty = min(remaining_qty, size)
                total_proceeds += fill_qty * price
                remaining_qty -= fill_qty
                if remaining_qty <= 0:
                    break

        if remaining_qty > 0:
            last_price = bid_depth[-1].get("price", best_bid) if bid_depth else best_bid
            penalized_price = max(0.05, last_price - self.exhaustion_penalty_points)
            total_proceeds += remaining_qty * penalized_price

        # 3. Adverse Selection Drag
        base_fill = total_proceeds / quantity if quantity > 0 else best_bid
        if is_fast_market:
            adverse_drag = round(level_1_price * 0.005 * self.adverse_selection_factor, 2)
        elif walked_past_l1:
            adverse_drag = round(level_1_price * 0.002 * self.adverse_selection_factor, 2)
        else:
            adverse_drag = 0.0
        final_fill = round(max(0.05, base_fill - adverse_drag), 2)
        slippage_pts = round(max(0.0, best_bid - final_fill), 2)

        filled_portion = quantity - remaining_qty
        fill_ratio = 1.0 if remaining_qty <= 0 else round(filled_portion / quantity, 2)

        q_pos = QueuePosition(
            price_level=level_1_price,
            total_depth_at_level=level_1_size,
            queue_ahead_qty=queue_ahead,
            our_quantity=quantity,
            fill_probability=1.0 if remaining_qty <= 0 else fill_ratio,
            estimated_wait_ms=round(queue_ahead * 2.5, 1)
        )

        self._record_calibration("SELL", quantity, best_bid, final_fill, slippage_pts, slippage_pts * 2)

        return SlippageEstimate(
            expected_price=best_bid,
            simulated_fill_price=final_fill,
            slippage_points=slippage_pts,
            slippage_inr=round(slippage_pts * quantity, 2),
            fill_ratio=fill_ratio,
            execution_type="AGGRESSIVE_MARKET",
            queue_position=q_pos,
            adverse_selection_drag_pts=adverse_drag,
            effective_spread_pts=round(slippage_pts * 2, 2)
        )

    def calculate_passive_limit_fill(
        self,
        side: Literal["BUY", "SELL"],
        limit_price: float,
        quantity: int,
        depth_levels: list[dict],
        incoming_volume: int = 500
    ) -> SlippageEstimate:
        """
        Simulates passive execution for limit orders resting in the book.
        Zero spread-crossing slippage, but subject to queue wait and fill probability.
        """
        # Find depth at limit price
        level_match = next((d for d in depth_levels if abs(d.get("price", 0.0) - limit_price) < 0.05), None)
        total_depth = level_match.get("size", 100) if level_match else 50

        queue_ahead = int(total_depth * self.queue_priority_default)
        fill_prob = min(1.0, max(0.05, incoming_volume / (queue_ahead + quantity + 1e-6)))

        is_filled = fill_prob >= 0.50
        fill_ratio = 1.0 if is_filled else round(fill_prob, 2)

        q_pos = QueuePosition(
            price_level=limit_price,
            total_depth_at_level=total_depth,
            queue_ahead_qty=queue_ahead,
            our_quantity=quantity,
            fill_probability=round(fill_prob, 2),
            estimated_wait_ms=round(queue_ahead * 15.0, 1)  # Resting orders wait longer
        )

        return SlippageEstimate(
            expected_price=limit_price,
            simulated_fill_price=limit_price,  # Limit orders fill at limit or better
            slippage_points=0.0,
            slippage_inr=0.0,
            fill_ratio=fill_ratio,
            execution_type="PASSIVE_LIMIT",
            queue_position=q_pos,
            adverse_selection_drag_pts=0.0,
            effective_spread_pts=0.0
        )

    def _record_calibration(
        self,
        side: str,
        quantity: int,
        quoted: float,
        filled: float,
        slippage: float,
        eff_spread: float
    ) -> None:
        """Maintains rolling queue and slippage calibration telemetry."""
        pt = SlippageCalibrationPoint(
            timestamp=time.time(),
            side=side,
            quantity=quantity,
            quoted_price=quoted,
            fill_price=filled,
            slippage_points=slippage,
            effective_spread=eff_spread
        )
        self.calibration_history.append(pt)
        if len(self.calibration_history) > self._max_history:
            self.calibration_history.pop(0)

    def get_telemetry(self) -> dict:
        """Returns empirical queue and slippage telemetry."""
        if not self.calibration_history:
            return {
                "total_fills_analyzed": 0,
                "avg_slippage_points": self.default_slippage_points,
                "avg_slippage_inr": round(self.default_slippage_points * 65, 2),
                "effective_spread_ratio": 1.0,
                "default_queue_priority": f"{self.queue_priority_default * 100:.0f}%"
            }

        n = len(self.calibration_history)
        avg_pts = sum(p.slippage_points for p in self.calibration_history) / n
        avg_spread = sum(p.effective_spread for p in self.calibration_history) / n
        total_inr = sum(p.slippage_points * p.quantity for p in self.calibration_history)

        return {
            "total_fills_analyzed": n,
            "avg_slippage_points": round(avg_pts, 3),
            "avg_slippage_inr": round(total_inr / n, 2),
            "avg_effective_spread": round(avg_spread, 3),
            "default_queue_priority": f"{self.queue_priority_default * 100:.0f}%"
        }

    def reset(self) -> None:
        """Resets calibration history."""
        self.calibration_history.clear()


slippage_model = SlippageModel()
