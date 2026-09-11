"""
Mock Broker Client for Testing & Local Development.
"""

from broker.interface import AbstractBrokerClient, BrokerOrderRequest, BrokerOrderResponse, BrokerFunds
from config import config


class MockBrokerClient(AbstractBrokerClient):
    """Simple in-memory broker client for deterministic testing."""

    def __init__(self, initial_cash: float = config.initial_capital_inr):
        self.cash = initial_cash
        self.orders = []

    async def connect(self) -> bool:
        return True

    async def disconnect(self) -> None:
        pass

    async def place_order(self, request: BrokerOrderRequest) -> BrokerOrderResponse:
        resp = BrokerOrderResponse(
            order_id=f"MOCK_{len(self.orders)+1}",
            client_order_id=request.client_order_id,
            symbol=request.symbol,
            side=request.side,
            status="FILLED",
            fill_price=request.price if request.price > 0 else 25.0,
            filled_quantity=request.quantity,
            total_charges_inr=23.60
        )
        self.orders.append(resp)
        return resp

    async def cancel_order(self, order_id: str) -> bool:
        return True

    async def get_positions(self) -> list[dict]:
        return []

    async def get_funds(self) -> BrokerFunds:
        return BrokerFunds(
            available_cash=self.cash,
            used_margin=0.0,
            total_balance=self.cash
        )
