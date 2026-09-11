"""
Tests for Live Trading Safety Invariants.
Verifies that live order execution is impossible in V1.
"""

import asyncio
import pytest
from execution.live_broker_disabled import LiveTradingPermanentlyDisabledBroker
from broker.dhan.client import DhanBrokerClient
from broker.zerodha.client import ZerodhaBrokerClient
from broker.interface import BrokerOrderRequest


def test_disabled_broker_instantiation_raises():
    """Verify attempting to instantiate disabled live broker raises RuntimeError."""
    with pytest.raises(RuntimeError) as exc_info:
        LiveTradingPermanentlyDisabledBroker()
    assert "Live trading is permanently disabled in V1" in str(exc_info.value)


def test_dhan_broker_blocks_orders():
    """Verify Dhan client throws RuntimeError if place_order is invoked in V1."""
    async def _run():
        dhan = DhanBrokerClient("FAKE_CLIENT", "FAKE_TOKEN")
        req = BrokerOrderRequest(
            symbol="NIFTY_TEST_CE",
            side="BUY",
            order_type="MARKET",
            quantity=65
        )
        with pytest.raises(RuntimeError) as exc_info:
            await dhan.place_order(req)
        assert "Live order placement via DhanHQ is permanently disabled" in str(exc_info.value)

    asyncio.run(_run())


def test_zerodha_broker_blocks_orders():
    """Verify Zerodha client throws RuntimeError if place_order is invoked in V1."""
    async def _run():
        kite = ZerodhaBrokerClient()
        req = BrokerOrderRequest(
            symbol="NIFTY_TEST_CE",
            side="BUY",
            order_type="MARKET",
            quantity=65
        )
        with pytest.raises(RuntimeError) as exc_info:
            await kite.place_order(req)
        assert "Live order placement via Zerodha is permanently disabled" in str(exc_info.value)

    asyncio.run(_run())
