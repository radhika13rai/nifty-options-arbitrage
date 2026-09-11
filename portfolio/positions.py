"""
Portfolio Position Tracking Module.
Tracks active long/short option inventory, calculates real-time Mark-to-Market (MTM)
and accurate fee-adjusted realized/unrealized P&L.
"""

from dataclasses import dataclass
import time
from typing import Literal, Optional


@dataclass
class Position:
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: int
    average_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_costs: float = 0.0
    is_open: bool = True
    updated_at: float = 0.0

    def update_mtm(self, current_price: float) -> None:
        """Mark-to-Market valuation."""
        self.current_price = current_price
        if self.is_open:
            if self.side == "BUY":
                self.unrealized_pnl = round((current_price - self.average_price) * self.quantity, 2)
            else:
                self.unrealized_pnl = round((self.average_price - current_price) * self.quantity, 2)
        else:
            self.unrealized_pnl = 0.0
        self.updated_at = time.time()


class PositionTracker:
    """Maintains portfolio positions state."""

    def __init__(self):
        self._positions: dict[str, Position] = {}

    def reset(self) -> None:
        """Clears all open and historical positions."""
        self._positions.clear()

    def apply_fill(
        self,
        symbol: str,
        side: Literal["BUY", "SELL"],
        price: float,
        quantity: int,
        order_costs: float
    ) -> Position:
        """Updates portfolio state following an order execution."""
        pos = self._positions.get(symbol)
        now = time.time()

        if not pos or not pos.is_open:
            # New opening position
            new_pos = Position(
                symbol=symbol,
                side=side,
                quantity=quantity,
                average_price=price,
                current_price=price,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                total_costs=order_costs,
                is_open=True,
                updated_at=now
            )
            self._positions[symbol] = new_pos
            return new_pos

        # Existing position: check if closing or adding
        if pos.side == side:
            # Adding to position
            new_qty = pos.quantity + quantity
            total_spend = (pos.average_price * pos.quantity) + (price * quantity)
            pos.average_price = round(total_spend / new_qty, 2)
            pos.quantity = new_qty
            pos.total_costs += order_costs
            pos.update_mtm(price)
            return pos
        else:
            # Closing / flattening position
            close_qty = min(pos.quantity, quantity)
            if pos.side == "BUY":
                trade_realized = round((price - pos.average_price) * close_qty, 2)
            else:
                trade_realized = round((pos.average_price - price) * close_qty, 2)

            pos.realized_pnl += trade_realized
            pos.total_costs += order_costs
            remaining_qty = pos.quantity - close_qty

            if remaining_qty == 0:
                pos.quantity = 0
                pos.is_open = False
                pos.unrealized_pnl = 0.0
            else:
                pos.quantity = remaining_qty
                pos.update_mtm(price)

            return pos

    def mark_to_market(self, symbol: str, current_price: float) -> Optional[Position]:
        pos = self._positions.get(symbol)
        if pos and pos.is_open:
            pos.update_mtm(current_price)
            return pos
        return None

    def get_open_positions(self) -> list[Position]:
        return [p for p in self._positions.values() if p.is_open]

    def get_all_positions(self) -> list[Position]:
        return list(self._positions.values())


position_tracker = PositionTracker()
