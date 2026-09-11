"""
DhanHQ v2 Broker Integration Adapter.
Provides market data quotes and telemetry.
CRITICAL SAFETY INVARIANT: Order placement is compiled with a fail-closed hard stop.
"""

import logging
from typing import Optional
from config import config
from broker.interface import AbstractBrokerClient, BrokerOrderRequest, BrokerOrderResponse, BrokerFunds

logger = logging.getLogger("DhanClient")


class DhanBrokerClient(AbstractBrokerClient):
    """
    Adapter for DhanHQ API v2.
    NOTE: DhanHQ requires Static IP whitelisting with 7-day modification lock for order APIs.
    In V1, all execution requests are strictly intercepted and blocked by compliance mandate.
    """

    def __init__(
        self,
        client_id: str = config.dhan_client_id,
        access_token: str = config.dhan_access_token
    ):
        self.client_id = client_id
        self.access_token = access_token
        self.is_connected = False

    async def connect(self) -> bool:
        if not self.client_id or not self.access_token:
            logger.info("Dhan credentials not provided; operating in offline simulation mode.")
            return False
        self.is_connected = True
        logger.info(f"Dhan client initialized for Client ID: {self.client_id[:4]}***")
        return True

    async def disconnect(self) -> None:
        self.is_connected = False
        logger.info("Dhan client disconnected.")

    async def place_order(self, request: BrokerOrderRequest) -> BrokerOrderResponse:
        """
        FAIL-CLOSED COMPLIANCE LOCK.
        Live order placement is strictly prohibited in V1.
        """
        logger.critical(
            f"ILLEGAL ATTEMPT to place live order on DhanHQ! Symbol: {request.symbol}, Side: {request.side}. "
            f"V1 is locked to PAPER_TRADING only."
        )
        raise RuntimeError(
            "COMPLIANCE_VIOLATION: Live order placement via DhanHQ is permanently disabled in V1. "
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
