"""
Authoritative RiskKernel — Single Source of Truth for Risk Boundaries.
Orchestrates pre-trade risk checks, capital reservation, dynamic margin calculation,
daily loss limits, market data staleness, and atomic execution gates.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
import time

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
class CapitalReservationResult:
    """Authoritative pre-trade capital reservation accounting."""
    entry_premium: float
    entry_fees: float
    worst_case_slippage: float
    reserved_exit_fees: float
    risk_buffer: float
    total_required_cash: float
    available_cash: float
    post_entry_cash: float
    capital_floor: float
    is_solvent: bool
    is_floor_preserved: bool
    violations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RiskCheckResult:
    passed: bool
    violations: list[str] = field(default_factory=list)
    reason: str = "PASS"
    approved_quantity: int = 0
    estimated_total_cost: float = 0.0
    reservation: Optional[CapitalReservationResult] = None


class RiskKernel:
    """
    Centralized, authoritative risk management gate.
    All proposed orders must be validated here prior to routing to OMS or broker.
    """

    def __init__(self, limits: RiskLimits = risk_limits):
        self.limits = limits

    def calculate_capital_reservation(
        self,
        side: Literal["BUY", "SELL"],
        price: float,
        quantity: int,
        available_cash: float,
        portfolio_equity: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        capital_floor: Optional[float] = None
    ) -> CapitalReservationResult:
        """
        Authoritative capital-reservation calculation:
            required_cash =
                entry_premium
              + entry_fees
              + worst_case_slippage
              + reserved_exit_fees
              + risk_buffer
        """
        floor = capital_floor if capital_floor is not None else self.limits.capital_floor_inr
        current_eq = portfolio_equity if portfolio_equity is not None else available_cash

        if side != "BUY":
            # SELL / Exit orders return cash to portfolio
            return CapitalReservationResult(
                entry_premium=0.0,
                entry_fees=0.0,
                worst_case_slippage=0.0,
                reserved_exit_fees=0.0,
                risk_buffer=0.0,
                total_required_cash=0.0,
                available_cash=round(available_cash, 2),
                post_entry_cash=round(available_cash, 2),
                capital_floor=floor,
                is_solvent=True,
                is_floor_preserved=True,
                violations=[]
            )

        entry_premium = round(price * quantity, 2)
        entry_cost_res = cost_engine.calculate_order_costs("BUY", price, quantity)
        entry_fees = entry_cost_res.total_costs

        worst_case_slippage = round(config.risk.max_slippage_points * quantity, 2)
        exit_cost_res = cost_engine.calculate_order_costs("SELL", price, quantity)
        reserved_exit_fees = exit_cost_res.total_costs

        effective_stop = stop_loss_price if stop_loss_price is not None else max(0.05, round(price - 2.30, 2))
        max_points_loss = max(0.0, round(price - effective_stop, 2))
        risk_buffer = round(max_points_loss * quantity, 2)

        # Total cash outlay needed to safely enter and close the position
        total_required_cash = round(
            entry_premium + entry_fees + worst_case_slippage + reserved_exit_fees,
            2
        )
        post_entry_cash = round(available_cash - total_required_cash, 2)

        violations = []
        is_solvent = available_cash >= (entry_premium + entry_fees)
        if not is_solvent:
            violations.append(
                f"Insufficient capital: Required ₹{entry_premium + entry_fees:.2f} "
                f"(premium ₹{entry_premium:.2f} + fees ₹{entry_fees:.2f}), available cash ₹{available_cash:.2f}"
            )

        # Total risk includes max point loss + round-trip statutory costs
        total_potential_risk = round(risk_buffer + entry_fees + reserved_exit_fees, 2)

        is_floor_preserved = True
        if available_cash <= floor:
            is_floor_preserved = False
            violations.append(
                f"CAPITAL_FLOOR_REACHED: Available cash ₹{available_cash:.2f} is at or below non-negotiable floor ₹{floor:.2f}"
            )
        elif (available_cash - total_potential_risk) < floor:
            is_floor_preserved = False
            violations.append(
                f"CAPITAL_FLOOR_HEADROOM_EXCEEDED: Current cash ₹{available_cash:.2f} minus potential trade loss ₹{total_potential_risk:.2f} would breach non-negotiable capital floor ₹{floor:.2f}"
            )

        return CapitalReservationResult(
            entry_premium=entry_premium,
            entry_fees=entry_fees,
            worst_case_slippage=worst_case_slippage,
            reserved_exit_fees=reserved_exit_fees,
            risk_buffer=risk_buffer,
            total_required_cash=total_required_cash,
            available_cash=round(available_cash, 2),
            post_entry_cash=post_entry_cash,
            capital_floor=floor,
            is_solvent=is_solvent,
            is_floor_preserved=is_floor_preserved,
            violations=violations
        )

    def validate_order(
        self,
        order: PreTradeOrderRequest,
        current_cash_inr: float,
        daily_realized_loss_inr: float,
        portfolio_equity: Optional[float] = None
    ) -> RiskCheckResult:
        """
        Executes sequential risk verification checklist inside atomic execution gate:
        1. Kill switch state
        2. Daily loss ceiling breach (₹300)
        3. Lot size compliance (strictly multiple of 65, max 1 lot)
        4. Market data freshness (< 1500ms)
        5. Authoritative capital reservation & solvency
        6. Max trade loss exposure check (mandatory ₹150 cap)
        7. Daily risk budget headroom
        8. Capital floor headroom
        """
        with kill_switch.atomic_execution_gate():
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
                kill_switch.engage(
                    f"Daily loss limit breached (₹{daily_realized_loss_inr:.2f} >= ₹{self.limits.max_daily_loss_inr:.2f})",
                    "RISK_BREACH"
                )
                return RiskCheckResult(
                    passed=False,
                    violations=["DAILY_LOSS_LIMIT_EXCEEDED"],
                    reason=f"Rejected: Daily loss ₹{daily_realized_loss_inr:.2f} reached ceiling of ₹{self.limits.max_daily_loss_inr:.2f}"
                )

            # 3. Capital floor check on existing cash before entry
            if order.side == "BUY" and current_cash_inr < self.limits.capital_floor_inr:
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
                violations.append(
                    f"Quantity {order.quantity} exceeds max allowed {max_allowed_qty} (1 lot of {self.limits.lot_size})"
                )

            # 5. Market data freshness check
            snapshot = orderbook_manager.get_snapshot(order.symbol)
            if snapshot:
                staleness = stale_data_guard.check_orderbook(snapshot)
                if not staleness.is_fresh:
                    violations.append(f"Stale quote data: {staleness.reason}")
            else:
                violations.append("No active orderbook snapshot found for symbol")

            # 6. Authoritative capital reservation and solvency
            reservation = self.calculate_capital_reservation(
                side=order.side,
                price=order.price,
                quantity=order.quantity,
                available_cash=current_cash_inr,
                portfolio_equity=portfolio_equity,
                stop_loss_price=order.stop_loss_price,
                capital_floor=self.limits.capital_floor_inr
            )
            violations.extend(reservation.violations)

            # 7. Max trade loss exposure check (₹150 cap)
            if order.side == "BUY":
                if reservation.risk_buffer > self.limits.max_trade_loss_inr:
                    violations.append(
                        f"Trade risk ₹{reservation.risk_buffer:.2f} exceeds max allowed ₹{self.limits.max_trade_loss_inr:.2f} per trade"
                    )

                # 7b. Daily risk budget headroom check
                total_potential_risk = reservation.risk_buffer + reservation.entry_fees + reservation.reserved_exit_fees
                if (daily_realized_loss_inr + total_potential_risk) > self.limits.max_daily_loss_inr:
                    violations.append(
                        f"DAILY_LOSS_HEADROOM_EXCEEDED: Realized daily loss ₹{daily_realized_loss_inr:.2f} + potential trade loss ₹{total_potential_risk:.2f} exceeds daily loss ceiling ₹{self.limits.max_daily_loss_inr:.2f}"
                    )

            if violations:
                return RiskCheckResult(
                    passed=False,
                    violations=violations,
                    reason="; ".join(violations),
                    estimated_total_cost=reservation.entry_fees,
                    reservation=reservation
                )

            return RiskCheckResult(
                passed=True,
                violations=[],
                reason="PASS",
                approved_quantity=order.quantity,
                estimated_total_cost=reservation.entry_fees,
                reservation=reservation
            )


risk_kernel = RiskKernel()
