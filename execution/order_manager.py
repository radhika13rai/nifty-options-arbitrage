"""
Order Management System (OMS) Coordinator.
Orchestrates signal ingestion, execution routing, and state tracking.
"""

import logging
from typing import Optional
from broker.interface import BrokerOrderRequest, BrokerOrderResponse
from execution.paper_broker import paper_broker
from strategies.base import TradingSignal

logger = logging.getLogger("OMS")


class OrderManager:
    """Manages the full lifecycle of orders from signal creation to settlement."""

    def __init__(self, broker=paper_broker):
        self.broker = broker

    async def execute_signal(self, signal: TradingSignal) -> Optional[BrokerOrderResponse]:
        """Validates capital feasibility before routing signal to execution."""
        if not signal.is_capital_feasible:
            logger.info(
                f"Signal {signal.signal_id} on {signal.symbol} rejected: {signal.infeasibility_reason}"
            )
            return None

        req = BrokerOrderRequest(
            symbol=signal.symbol,
            side=signal.action,
            order_type=signal.order_type,
            quantity=signal.quantity,
            price=signal.suggested_price,
            client_order_id=signal.signal_id
        )

        return await self.broker.place_order(req)


order_manager = OrderManager()
