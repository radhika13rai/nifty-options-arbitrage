"""
Order Management System (OMS) Coordinator.
Orchestrates signal ingestion, execution routing, and state tracking.
"""

import logging
from typing import Optional
from broker.interface import BrokerOrderRequest, BrokerOrderResponse
from execution.paper_broker import paper_broker
from risk.engine import risk_engine, PreTradeOrderRequest
from risk.kill_switch import kill_switch
from portfolio.pnl import pnl_manager
from database.db import db_manager
from strategies.base import TradingSignal

logger = logging.getLogger("OMS")


class OrderManager:
    """
    Order Management System (OMS) Coordinator.
    Mandatory architectural boundary between Signal Generation and Execution Adapters.
    Enforces Pre-Trade Risk Engine validation before any broker adapter is invoked.
    """

    def __init__(self, broker=paper_broker):
        self.broker = broker

    async def execute_signal(self, signal: TradingSignal) -> Optional[BrokerOrderResponse]:
        """
        Validates signal feasibility, enforces stop loss invariants, executes pre-trade
        risk gate, and routes only approved orders to execution.
        """
        if not signal.is_capital_feasible:
            logger.info(
                f"Signal {signal.signal_id} on {signal.symbol} rejected: {signal.infeasibility_reason}"
            )
            return None

        if kill_switch.is_engaged:
            logger.warning(
                f"Signal {signal.signal_id} on {signal.symbol} rejected: Kill switch active ({kill_switch.get_status().reason})"
            )
            return None

        # Determine effective stop loss ensuring mandatory ₹150 loss enforcement
        effective_stop = signal.stop_loss_price
        if effective_stop is None and signal.action == "BUY":
            # Default to maximum permissible stop loss under ₹150 cap (~2.30 points)
            effective_stop = round(max(0.05, signal.suggested_price - 2.30), 2)

        # Mandatory OMS Pre-Trade Risk Validation Boundary
        pnl_report = pnl_manager.generate_report()
        daily_loss = max(0.0, -pnl_report.gross_realized_pnl + pnl_report.total_friction_inr)
        
        risk_req = PreTradeOrderRequest(
            symbol=signal.symbol,
            side=signal.action,
            order_type=signal.order_type,
            price=signal.suggested_price,
            quantity=signal.quantity,
            stop_loss_price=effective_stop,
            target_price=signal.target_price
        )

        risk_result = risk_engine.validate_order(
            order=risk_req,
            current_cash_inr=pnl_manager.current_cash,
            daily_realized_loss_inr=daily_loss
        )

        if not risk_result.passed:
            logger.warning(
                f"Signal {signal.signal_id} rejected at OMS Risk Gate: {risk_result.reason}"
            )
            await db_manager.record_risk_event(
                event_type="OMS_RISK_REJECTION",
                reason=risk_result.reason,
                blocked_payload={
                    "signal_id": signal.signal_id,
                    "symbol": signal.symbol,
                    "side": signal.action,
                    "price": signal.suggested_price,
                    "quantity": signal.quantity,
                    "stop_loss_price": effective_stop
                }
            )
            return None

        req = BrokerOrderRequest(
            symbol=signal.symbol,
            side=signal.action,
            order_type=signal.order_type,
            quantity=signal.quantity,
            price=signal.suggested_price,
            client_order_id=signal.signal_id,
            stop_loss_price=effective_stop,
            target_price=signal.target_price
        )

        return await self.broker.place_order(req)


order_manager = OrderManager()
