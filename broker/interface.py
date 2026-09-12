"""
Abstract Broker Interface Definition.
Defines standard broker contract for order routing, positions, and account telemetry.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass(frozen=True)
class BrokerOrderRequest:
    symbol: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT"]
    quantity: int
    price: float = 0.0
    client_order_id: str = ""
    stop_loss_price: Optional[float] = None
    target_price: Optional[float] = None


@dataclass(frozen=True)
class BrokerOrderResponse:
    order_id: str
    client_order_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    status: Literal["SUBMITTED", "FILLED", "REJECTED", "CANCELLED"]
    fill_price: float
    filled_quantity: int
    total_charges_inr: float
    rejection_reason: Optional[str] = None


@dataclass(frozen=True)
class BrokerFunds:
    available_cash: float
    used_margin: float
    total_balance: float


class AbstractBrokerClient(ABC):
    """Universal broker adapter interface."""

    @abstractmethod
    async def connect(self) -> bool:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def place_order(self, request: BrokerOrderRequest) -> BrokerOrderResponse:
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        pass

    @abstractmethod
    async def get_positions(self) -> list[dict]:
        pass

    @abstractmethod
    async def get_funds(self) -> BrokerFunds:
        pass
