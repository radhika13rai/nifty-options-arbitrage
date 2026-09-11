"""
Tests for High-Fidelity Paper Trading Execution Engine.
"""

import asyncio
from execution.paper_broker import paper_broker
from broker.interface import BrokerOrderRequest
from market_data.orderbook import orderbook_manager
from market_data.normalizer import MarketDataNormalizer
from portfolio.pnl import pnl_manager
from database.db import db_manager


def test_paper_buy_execution_and_fees():
    """Verify paper BUY order fills at Ask price and deducts correct fees."""
    async def _run():
        # Ensure database is initialized
        await db_manager.async_init_db()

        # Reset balance
        pnl_manager.reset_balance(3000.0)

        # Seed fresh orderbook
        symbol = "NIFTY_TEST_CE_EXEC"
        tick = MarketDataNormalizer.create_synthetic_tick(
            symbol=symbol,
            mid_price=20.0,
            spread=0.20
        )
        orderbook_manager.update_tick(tick)

        # Place BUY order for 1 lot (65 units)
        req = BrokerOrderRequest(
            symbol=symbol,
            side="BUY",
            order_type="MARKET",
            quantity=65,
            price=20.10
        )

        resp = await paper_broker.place_order(req)
        assert resp.status == "FILLED"
        assert resp.filled_quantity == 65
        assert resp.fill_price >= tick.best_ask
        assert resp.total_charges_inr > 20.0  # Brokerage + GST + exchange fees

        # Cash must be reduced by outlay + fees
        expected_outlay = round(resp.fill_price * 65, 2)
        expected_cash = round(3000.0 - expected_outlay - resp.total_charges_inr, 2)
        assert pnl_manager.current_cash == expected_cash

    asyncio.run(_run())


def test_paper_sell_execution():
    """Verify paper SELL order fills at Bid price and accounts for STT."""
    async def _run():
        symbol = "NIFTY_TEST_PE_EXEC"
        tick = MarketDataNormalizer.create_synthetic_tick(
            symbol=symbol,
            mid_price=30.0,
            spread=0.40
        )
        orderbook_manager.update_tick(tick)

        req = BrokerOrderRequest(
            symbol=symbol,
            side="SELL",
            order_type="MARKET",
            quantity=65,
            price=29.80
        )

        resp = await paper_broker.place_order(req)
        assert resp.status == "FILLED"
        assert resp.fill_price <= tick.best_bid
        # Sell side has STT included
        assert resp.total_charges_inr > 25.0

    asyncio.run(_run())
