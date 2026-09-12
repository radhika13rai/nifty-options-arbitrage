"""
Realistic Paper Trading Execution Broker.
Simulates real Indian options market execution:
- Fills BUY orders at Best Ask (with slippage)
- Fills SELL orders at Best Bid (with slippage)
- Deducts all statutory charges (Brokerage ₹20, STT 0.1%, Exchange 0.05%, GST 18%, Stamp Duty 0.003%, SEBI)
- Rejects orders violating pre-trade risk checks
- Persists all orders and trades to SQLite WAL database
"""

import logging
import time
import uuid
from typing import Optional
from config import config
from broker.interface import AbstractBrokerClient, BrokerOrderRequest, BrokerOrderResponse, BrokerFunds
from market_data.orderbook import orderbook_manager
from costs.transaction_costs import cost_engine
from costs.slippage import slippage_model
from risk.engine import risk_engine, PreTradeOrderRequest
from risk.kill_switch import kill_switch
from portfolio.positions import position_tracker
from portfolio.pnl import pnl_manager
from database.db import db_manager

logger = logging.getLogger("PaperBroker")


class PaperBroker(AbstractBrokerClient):
    """Production-fidelity paper trading engine for NIFTY options."""

    def __init__(self, initial_cash: float = config.initial_capital_inr):
        self.initial_cash = initial_cash
        self.is_connected = True

    async def connect(self) -> bool:
        self.is_connected = True
        logger.info("PaperBroker initialized with virtual cash ₹%.2f", pnl_manager.current_cash)
        return True

    async def disconnect(self) -> None:
        self.is_connected = False

    async def place_order(self, request: BrokerOrderRequest) -> BrokerOrderResponse:
        """
        Processes order through pre-trade risk pipeline, orderbook depth walking,
        and statutory cost deduction.
        """
        client_oid = request.client_order_id or str(uuid.uuid4())[:8]
        order_id = f"PAP_{int(time.time()*1000)}_{client_oid}"

        # 1. Fetch current orderbook snapshot
        snapshot = orderbook_manager.get_snapshot(request.symbol)
        if not snapshot:
            reason = f"REJECTED: No orderbook snapshot for {request.symbol}"
            await db_manager.record_order(
                order_id=order_id,
                client_order_id=client_oid,
                symbol=request.symbol,
                side=request.side,
                order_type=request.order_type,
                quantity=request.quantity,
                requested_price=request.price,
                fill_price=None,
                status="REJECTED",
                rejection_reason=reason
            )
            return BrokerOrderResponse(
                order_id=order_id,
                client_order_id=client_oid,
                symbol=request.symbol,
                side=request.side,
                status="REJECTED",
                fill_price=0.0,
                filled_quantity=0,
                total_charges_inr=0.0,
                rejection_reason=reason
            )

        # 2. Determine realistic fill price using slippage model
        if request.side == "BUY":
            slippage_res = slippage_model.calculate_buy_fill(
                best_ask=snapshot.best_ask,
                quantity=request.quantity,
                ask_depth=[{"price": d.price, "size": d.size} for d in snapshot.asks] if snapshot.asks else None
            )
            simulated_fill_price = slippage_res.simulated_fill_price
        else:
            slippage_res = slippage_model.calculate_sell_fill(
                best_bid=snapshot.best_bid,
                quantity=request.quantity,
                bid_depth=[{"price": d.price, "size": d.size} for d in snapshot.bids] if snapshot.bids else None
            )
            simulated_fill_price = slippage_res.simulated_fill_price

        # 3. Pre-trade Risk Check Gate & Atomic Portfolio Mutation
        rejection_reason = None
        cost_breakdown = None

        with kill_switch.atomic_execution_gate():
            if kill_switch.is_engaged:
                rejection_reason = f"Rejected: Emergency kill switch is active ({kill_switch.get_status().reason})"
            else:
                pnl_report = pnl_manager.generate_report()
                daily_loss = max(0.0, -pnl_report.gross_realized_pnl + pnl_report.total_friction_inr)

                effective_stop = request.stop_loss_price
                if request.side == "BUY":
                    if effective_stop is None or round(simulated_fill_price - effective_stop, 2) > 2.30:
                        effective_stop = round(max(0.05, simulated_fill_price - 2.30), 2)

                risk_req = PreTradeOrderRequest(
                    symbol=request.symbol,
                    side=request.side,
                    order_type=request.order_type,
                    price=simulated_fill_price,
                    quantity=request.quantity,
                    stop_loss_price=effective_stop,
                    target_price=request.target_price
                )
                risk_result = risk_engine.validate_order(
                    order=risk_req,
                    current_cash_inr=pnl_manager.current_cash,
                    daily_realized_loss_inr=daily_loss
                )

                if not risk_result.passed:
                    rejection_reason = risk_result.reason
                elif kill_switch.is_engaged:
                    rejection_reason = f"Rejected: Emergency kill switch is active ({kill_switch.get_status().reason})"
                else:
                    # 4. Calculate exact statutory costs
                    cost_breakdown = cost_engine.calculate_order_costs(
                        side=request.side,
                        price=simulated_fill_price,
                        quantity=request.quantity
                    )

                    # 5. Apply fill to portfolio & cash atomically
                    pnl_manager.adjust_cash(cost_breakdown.net_cash_flow, cost_breakdown.total_costs)
                    position_tracker.apply_fill(
                        symbol=request.symbol,
                        side=request.side,
                        price=simulated_fill_price,
                        quantity=request.quantity,
                        order_costs=cost_breakdown.total_costs
                    )

        if rejection_reason is not None:
            logger.warning(f"Order {order_id} blocked: {rejection_reason}")
            await db_manager.record_risk_event(
                event_type="ORDER_BLOCKED",
                reason=rejection_reason,
                blocked_payload={"order_id": order_id, "symbol": request.symbol, "side": request.side, "quantity": request.quantity}
            )
            await db_manager.record_order(
                order_id=order_id,
                client_order_id=client_oid,
                symbol=request.symbol,
                side=request.side,
                order_type=request.order_type,
                quantity=request.quantity,
                requested_price=request.price,
                fill_price=None,
                status="REJECTED",
                rejection_reason=rejection_reason
            )
            return BrokerOrderResponse(
                order_id=order_id,
                client_order_id=client_oid,
                symbol=request.symbol,
                side=request.side,
                status="REJECTED",
                fill_price=0.0,
                filled_quantity=0,
                total_charges_inr=0.0,
                rejection_reason=rejection_reason
            )

        # 6. Persist order and trade into SQLite database
        trade_id = f"TRD_{int(time.time()*1000)}_{str(uuid.uuid4())[:4]}"
        await db_manager.record_order(
            order_id=order_id,
            client_order_id=client_oid,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            requested_price=request.price,
            fill_price=simulated_fill_price,
            status="FILLED",
            total_costs=cost_breakdown.total_costs
        )
        await db_manager.record_trade(
            trade_id=trade_id,
            order_id=order_id,
            symbol=request.symbol,
            side=request.side,
            price=simulated_fill_price,
            quantity=request.quantity,
            turnover=cost_breakdown.turnover,
            brokerage=cost_breakdown.brokerage,
            stt=cost_breakdown.stt,
            exchange_charges=cost_breakdown.exchange_charges,
            gst=cost_breakdown.gst,
            stamp_duty=cost_breakdown.stamp_duty,
            sebi_charges=cost_breakdown.sebi_charges,
            total_costs=cost_breakdown.total_costs,
            net_cash_flow=cost_breakdown.net_cash_flow
        )
        await db_manager.record_audit_log(
            event_type="ORDER_FILLED",
            severity="INFO",
            component="PaperBroker",
            details=f"Filled {request.side} {request.quantity}x {request.symbol} @ ₹{simulated_fill_price} (Fee: ₹{cost_breakdown.total_costs})"
        )

        logger.info(
            f"Paper Order FILLED: {request.side} {request.quantity} {request.symbol} @ ₹{simulated_fill_price:.2f} | "
            f"Charges: ₹{cost_breakdown.total_costs:.2f} | Remaining Cash: ₹{pnl_manager.current_cash:.2f}"
        )

        return BrokerOrderResponse(
            order_id=order_id,
            client_order_id=client_oid,
            symbol=request.symbol,
            side=request.side,
            status="FILLED",
            fill_price=simulated_fill_price,
            filled_quantity=request.quantity,
            total_charges_inr=cost_breakdown.total_costs
        )

    async def cancel_order(self, order_id: str) -> bool:
        return True

    async def get_positions(self) -> list[dict]:
        return [
            {
                "symbol": p.symbol,
                "side": p.side,
                "quantity": p.quantity,
                "average_price": p.average_price,
                "current_price": p.current_price,
                "unrealized_pnl": p.unrealized_pnl,
                "realized_pnl": p.realized_pnl,
                "total_costs": p.total_costs
            }
            for p in position_tracker.get_open_positions()
        ]

    async def get_funds(self) -> BrokerFunds:
        pnl = pnl_manager.generate_report()
        return BrokerFunds(
            available_cash=pnl.current_cash,
            used_margin=pnl.invested_capital,
            total_balance=pnl.total_portfolio_value
        )


paper_broker = PaperBroker()
