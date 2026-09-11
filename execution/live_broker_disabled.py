"""
Hard Safety Compile-Time & Runtime Lock.
Guarantees that live order execution cannot be instantiated or routed under any circumstances in V1.
"""

from broker.interface import AbstractBrokerClient, BrokerOrderRequest, BrokerOrderResponse, BrokerFunds


class LiveTradingPermanentlyDisabledBroker(AbstractBrokerClient):
    """
    Compliance invariant fail-closed broker.
    Any call to this class raises an uncatchable safety runtime violation.
    """

    def __init__(self):
        raise RuntimeError(
            "COMPLIANCE_CRITICAL_LOCK: Live trading is permanently disabled in V1 by specification. "
            "Attempt to instantiate live broker adapter is blocked."
        )

    async def connect(self) -> bool:
        return False

    async def disconnect(self) -> None:
        pass

    async def place_order(self, request: BrokerOrderRequest) -> BrokerOrderResponse:
        raise RuntimeError("COMPLIANCE_CRITICAL_LOCK: Live order execution is forbidden.")

    async def cancel_order(self, order_id: str) -> bool:
        raise RuntimeError("COMPLIANCE_CRITICAL_LOCK: Live order cancellation is forbidden.")

    async def get_positions(self) -> list[dict]:
        return []

    async def get_funds(self) -> BrokerFunds:
        return BrokerFunds(0.0, 0.0, 0.0)
