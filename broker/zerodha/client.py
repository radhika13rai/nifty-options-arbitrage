"""
Zerodha Kite Connect Adapter (Compliance Stub).
Maintains standard broker interface for future expansion while strictly disabling live orders in V1.
"""

import logging
from config import config
from broker.interface import AbstractBrokerClient, BrokerOrderRequest, BrokerOrderResponse, BrokerFunds

logger = logging.getLogger("ZerodhaClient")


class ZerodhaBrokerClient(AbstractBrokerClient):
    """Zerodha Kite Connect stub adapter."""

    async def connect(self) -> bool:
        logger.info("Zerodha Kite Connect adapter initialized (stub mode).")
        return True

    async def disconnect(self) -> None:
        pass

    async def place_order(self, request: BrokerOrderRequest) -> BrokerOrderResponse:
        raise RuntimeError(
            "COMPLIANCE_VIOLATION: Live order placement via Zerodha is permanently disabled in V1. "
            "System is strictly gated to Paper Trading."
        )

    async def cancel_order(self, order_id: str) -> bool:
        raise RuntimeError("COMPLIANCE_VIOLATION: Live order cancellation disabled in V1.")

    async def get_positions(self) -> list[dict]:
        return []

    async def get_funds(self) -> BrokerFunds:
        return BrokerFunds(
            available_cash=config.initial_capital_inr,
            used_margin=0.0,
            total_balance=config.initial_capital_inr
        )
