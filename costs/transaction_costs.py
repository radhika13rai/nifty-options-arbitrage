"""
Indian Securities & Derivatives Transaction Cost Engine (2026 Statutory Schedule).
Calculates exact brokerage, STT, exchange charges, GST, stamp duty, and SEBI turnover fees
for NIFTY options trading.
"""

from dataclasses import dataclass
from typing import Literal
from config import config


@dataclass(frozen=True)
class OrderCostBreakdown:
    """Detailed fee breakdown for an individual executed order leg."""
    side: Literal["BUY", "SELL"]
    price: float
    quantity: int
    turnover: float
    brokerage: float
    stt: float
    exchange_charges: float
    gst: float
    stamp_duty: float
    sebi_charges: float
    total_costs: float
    net_cash_flow: float  # Outflow for BUY (-), Inflow for SELL (+) after statutory deductions


@dataclass(frozen=True)
class RoundTripCostBreakdown:
    """Comprehensive statutory cost breakdown across a complete round-trip trade."""
    entry_order: OrderCostBreakdown
    exit_order: OrderCostBreakdown
    gross_pnl: float
    total_friction: float
    net_pnl: float
    breakeven_exit_price: float
    points_hurdle: float
    friction_drag_pct: float


class TransactionCostEngine:
    """Statutory cost calculator for Indian equity derivatives (Options)."""

    def __init__(self, schedule=config.costs):
        self.schedule = schedule

    def calculate_order_costs(
        self,
        side: Literal["BUY", "SELL"],
        price: float,
        quantity: int
    ) -> OrderCostBreakdown:
        """
        Calculate statutory taxes and brokerage for a single order leg.
        
        Args:
            side: 'BUY' or 'SELL'
            price: Option premium per unit (INR)
            quantity: Total units (multiple of lot size, e.g., 65)
        """
        turnover = round(price * quantity, 2)
        
        # 1. Brokerage: flat ₹20 per executed order
        brokerage = self.schedule.brokerage_per_order
        
        # 2. STT: 0.1% on premium (SELL side only for options)
        stt = round(turnover * self.schedule.stt_rate_sell, 2) if side == "SELL" else 0.0
        
        # 3. Exchange Transaction Charges: 0.05% of premium turnover (NSE)
        exchange_charges = round(turnover * self.schedule.exchange_turnover_rate, 2)
        
        # 4. SEBI Turnover Fee: ₹10 per crore (0.0001% of turnover)
        sebi_charges = round(turnover * self.schedule.sebi_turnover_rate, 2)
        
        # 5. GST: 18% on (Brokerage + Exchange Charges + SEBI Charges)
        gst = round((brokerage + exchange_charges + sebi_charges) * self.schedule.gst_rate, 2)
        
        # 6. Stamp Duty: 0.003% on premium (BUY side only)
        stamp_duty = round(turnover * self.schedule.stamp_duty_rate_buy, 2) if side == "BUY" else 0.0
        
        # Total statutory and broker friction
        total_costs = round(brokerage + stt + exchange_charges + gst + stamp_duty + sebi_charges, 2)
        
        if side == "BUY":
            # Cash required = Premium outlay + all charges
            net_cash_flow = -(turnover + total_costs)
        else:
            # Cash received = Premium inflow - all charges
            net_cash_flow = turnover - total_costs
            
        return OrderCostBreakdown(
            side=side,
            price=price,
            quantity=quantity,
            turnover=turnover,
            brokerage=brokerage,
            stt=stt,
            exchange_charges=exchange_charges,
            gst=gst,
            stamp_duty=stamp_duty,
            sebi_charges=sebi_charges,
            total_costs=total_costs,
            net_cash_flow=net_cash_flow
        )

    def calculate_round_trip(
        self,
        entry_side: Literal["BUY", "SELL"],
        entry_price: float,
        exit_price: float,
        quantity: int
    ) -> RoundTripCostBreakdown:
        """
        Calculates exact gross vs net P&L and friction drag for a full round-trip trade.
        """
        exit_side: Literal["BUY", "SELL"] = "SELL" if entry_side == "BUY" else "BUY"
        
        entry = self.calculate_order_costs(entry_side, entry_price, quantity)
        exit_leg = self.calculate_order_costs(exit_side, exit_price, quantity)
        
        if entry_side == "BUY":
            gross_pnl = round((exit_price - entry_price) * quantity, 2)
        else:
            gross_pnl = round((entry_price - exit_price) * quantity, 2)
            
        total_friction = round(entry.total_costs + exit_leg.total_costs, 2)
        net_pnl = round(gross_pnl - total_friction, 2)
        
        # Required exit price to achieve exactly 0 net PnL
        # For BUY: (exit_price - entry_price) * quantity = total_friction
        # exit_price = entry_price + (total_friction / quantity)
        points_hurdle = round(total_friction / quantity, 2)
        if entry_side == "BUY":
            breakeven_exit_price = round(entry_price + points_hurdle, 2)
            outlay = entry.turnover
        else:
            breakeven_exit_price = round(entry_price - points_hurdle, 2)
            outlay = exit_leg.turnover
            
        friction_drag_pct = round((total_friction / outlay) * 100, 2) if outlay > 0 else 0.0
        
        return RoundTripCostBreakdown(
            entry_order=entry,
            exit_order=exit_leg,
            gross_pnl=gross_pnl,
            total_friction=total_friction,
            net_pnl=net_pnl,
            breakeven_exit_price=breakeven_exit_price,
            points_hurdle=points_hurdle,
            friction_drag_pct=friction_drag_pct
        )


cost_engine = TransactionCostEngine()
