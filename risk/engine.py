"""
Pre-Trade Risk Engine.
Validates all proposed orders against 7 rigorous risk boundaries before permitting routing.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
from config import config
from risk.limits import risk_limits, RiskLimits
from risk.kill_switch import kill_switch
from risk.stale_data_guard import stale_data_guard
from market_data.orderbook import orderbook_manager
from costs.transaction_costs import cost_engine


@dataclass(frozen=True)
class PreTradeOrderRequest:
    symbol: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT"]
    price: float
    quantity: int
    stop_loss_price: Optional[float] = None
    target_price: Optional[float] = None


@dataclass(frozen=True)
class RiskCheckResult:
    passed: bool
    violations: list[str] = field(default_factory=list)
    reason: str = "PASS"
    approved_quantity: int = 0
    estimated_total_cost: float = 0.0


class PreTradeRiskEngine:
    """Rigorous pre-trade validation gate ensuring strict risk adherence."""

    def __init__(self, limits: RiskLimits = risk_limits):
        self.limits = limits

    def validate_order(
        self,
        order: PreTradeOrderRequest,
        current_cash_inr: float,
        daily_realized_loss_inr: float
    ) -> RiskCheckResult:
        """
        Executes sequential risk verification checklist:
        1. Kill switch state
        2. Daily loss ceiling breach (₹300)
        3. Capital floor threshold (₹2,000)
        4. Lot size compliance (must be multiple of 65, max 1 lot)
        5. Market data freshness (< 1500ms)
        6. Outlay & statutory cost sufficiency
        7. Max loss per trade limit (₹150)
        """
        violations = []

        # 1. Kill switch check
        if kill_switch.is_engaged:
            return RiskCheckResult(
                passed=False,
                violations=["KILL_SWITCH_ENGAGED"],
                reason=f"Rejected: Emergency kill switch is active ({kill_switch.get_status().reason})"
            )

        # 2. Daily loss ceiling
        if daily_realized_loss_inr >= self.limits.max_daily_loss_inr:
            kill_switch.engage(f"Daily loss limit breached (₹{daily_realized_loss_inr:.2f} >= ₹{self.limits.max_daily_loss_inr:.2f})", "RISK_BREACH")
            return RiskCheckResult(
                passed=False,
                violations=["DAILY_LOSS_LIMIT_EXCEEDED"],
                reason=f"Rejected: Daily loss ₹{daily_realized_loss_inr:.2f} reached ceiling of ₹{self.limits.max_daily_loss_inr:.2f}"
            )

        # 3. Capital floor check
        if current_cash_inr < self.limits.capital_floor_inr:
            return RiskCheckResult(
                passed=False,
                violations=["CAPITAL_BELOW_FLOOR"],
                reason=f"Rejected: Current cash ₹{current_cash_inr:.2f} is below emergency floor ₹{self.limits.capital_floor_inr:.2f}"
            )

        # 4. Lot size and quantity check
        if order.quantity % self.limits.lot_size != 0:
            violations.append(f"Quantity {order.quantity} is not a multiple of lot size {self.limits.lot_size}")
        
        max_allowed_qty = self.limits.max_lots * self.limits.lot_size
        if order.quantity > max_allowed_qty:
            violations.append(f"Quantity {order.quantity} exceeds max allowed {max_allowed_qty} (1 lot of {self.limits.lot_size})")

        # 5. Market data freshness check
        snapshot = orderbook_manager.get_snapshot(order.symbol)
        if snapshot:
            staleness = stale_data_guard.check_orderbook(snapshot)
            if not staleness.is_fresh:
                violations.append(f"Stale quote data: {staleness.reason}")
        else:
            violations.append("No active orderbook snapshot found for symbol")

        # 6. Cost and cash sufficiency
        breakdown = cost_engine.calculate_order_costs(order.side, order.price, order.quantity)
        total_required_outflow = breakdown.turnover + breakdown.total_costs
        if order.side == "BUY" and total_required_outflow > current_cash_inr:
            violations.append(
                f"Insufficient capital: Required ₹{total_required_outflow:.2f} (premium ₹{breakdown.turnover:.2f} + fees ₹{breakdown.total_costs:.2f}), available cash ₹{current_cash_inr:.2f}"
            )

        # 7. Max trade loss exposure check (if stop loss is provided)
        if order.side == "BUY" and order.stop_loss_price is not None:
            max_points_loss = order.price - order.stop_loss_price
            if max_points_loss > 0:
                potential_trade_loss = (max_points_loss * order.quantity) + (breakdown.total_costs * 2)  # round trip fees
                if potential_trade_loss > self.limits.max_trade_loss_inr:
                    violations.append(
                        f"Trade risk ₹{potential_trade_loss:.2f} exceeds max allowed ₹{self.limits.max_trade_loss_inr:.2f} per trade"
                    )

        if violations:
            return RiskCheckResult(
                passed=False,
                violations=violations,
                reason="; ".join(violations),
                estimated_total_cost=breakdown.total_costs
            )

        return RiskCheckResult(
            passed=True,
            violations=[],
            reason="PASS",
            approved_quantity=order.quantity,
            estimated_total_cost=breakdown.total_costs
        )


risk_engine = PreTradeRiskEngine()
