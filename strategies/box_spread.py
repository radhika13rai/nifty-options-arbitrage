"""
Box Spread 4-Leg Arbitrage Scanner & Margin Infeasibility Analyzer.
Box Spread = Bull Call Spread + Bear Put Spread across strikes K1 and K2.
Mathematical invariant: Value = (K2 - K1) * exp(-rT).
Evaluates execution feasibility against retail capital of ₹3,000.
"""

import math
import time
import uuid
from typing import Optional
from config import config
from market_data.normalizer import MarketTick
from market_data.orderbook import OrderbookSnapshot, orderbook_manager
from strategies.base import BaseStrategy, TradingSignal
from costs.transaction_costs import cost_engine


class BoxSpreadArbitrageScanner(BaseStrategy):
    """
    Scans for 4-leg box spread arbitrage across strikes K1 < K2:
    - Long Call(K1)
    - Short Call(K2)
    - Long Put(K2)
    - Short Put(K1)
    Theoretical payoff at expiry is exactly K2 - K1 risk-free.
    """

    def __init__(
        self,
        name: str = "BOX_SPREAD_ARBITRAGE",
        min_net_profit_pts: float = 3.0
    ):
        super().__init__(name)
        self.min_net_profit_pts = min_net_profit_pts
        self.r = config.market.risk_free_rate
        self.lot_size = config.market.nifty_lot_size
        self.t_years = 7.0 / 365.0

    def on_tick(self, tick: MarketTick) -> list[TradingSignal]:
        return []

    def on_orderbook(self, snapshot: OrderbookSnapshot) -> list[TradingSignal]:
        return []

    def scan_box(
        self,
        k1: float,
        k2: float,
        c1_sym: str,
        c2_sym: str,
        p1_sym: str,
        p2_sym: str
    ) -> Optional[TradingSignal]:
        """
        Calculates cost to enter Long Box:
        Cost = Ask(C1) - Bid(C2) + Ask(P2) - Bid(P1).
        Payoff = (K2 - K1) * exp(-r*T).
        """
        c1 = orderbook_manager.get_snapshot(c1_sym)
        c2 = orderbook_manager.get_snapshot(c2_sym)
        p1 = orderbook_manager.get_snapshot(p1_sym)
        p2 = orderbook_manager.get_snapshot(p2_sym)

        if not all([c1, c2, p1, p2]):
            return None

        # Box debit cost to buy
        debit_cost = (c1.best_ask - c2.best_bid) + (p2.best_ask - p1.best_bid)
        nominal_payoff = k2 - k1
        discounted_payoff = nominal_payoff * math.exp(-self.r * self.t_years)

        gross_profit_pts = discounted_payoff - debit_cost
        
        # 4-leg statutory friction dynamically calculated via CostEngine
        c1_cost = cost_engine.calculate_order_costs("BUY", c1.best_ask, self.lot_size)
        c2_cost = cost_engine.calculate_order_costs("SELL", c2.best_bid, self.lot_size)
        p1_cost = cost_engine.calculate_order_costs("SELL", p1.best_bid, self.lot_size)
        p2_cost = cost_engine.calculate_order_costs("BUY", p2.best_ask, self.lot_size)
        total_friction = c1_cost.total_costs + c2_cost.total_costs + p1_cost.total_costs + p2_cost.total_costs
        friction_pts = round(total_friction / self.lot_size, 2)

        net_profit_pts = gross_profit_pts - friction_pts

        if net_profit_pts > self.min_net_profit_pts:
            # Theoretical Box arbitrage exists!
            # Required SPAN margin for short call + short put legs in India:
            # Even with spread benefit, margin is ~₹65,000 to ₹90,000 per lot (65 units).
            return TradingSignal(
                signal_id=str(uuid.uuid4())[:8],
                timestamp_ms=time.time() * 1000.0,
                strategy_name=self.name,
                symbol=f"BOX_{k1}_{k2}",
                action="BUY",
                order_type="LIMIT",
                suggested_price=round(debit_cost, 2),
                quantity=self.lot_size,
                confidence=0.92,
                is_capital_feasible=False,
                infeasibility_reason=(
                    f"CAPITAL_INFEASIBLE: 4-leg box spread across {k1}/{k2} requires maintaining simultaneous short option positions. "
                    f"NSE portfolio margin requirement is ~₹75,000 per lot (65 units), "
                    f"far exceeding retail capital limit of ₹{config.initial_capital_inr:,.2f}."
                ),
                metadata={
                    "k1": k1,
                    "k2": k2,
                    "debit_cost": round(debit_cost, 2),
                    "discounted_payoff": round(discounted_payoff, 2),
                    "gross_profit_pts": round(gross_profit_pts, 2),
                    "net_profit_pts": round(net_profit_pts, 2),
                    "estimated_net_profit_inr": round(net_profit_pts * self.lot_size, 2),
                    "margin_required_inr": 75000.0
                }
            )

        return None


box_spread_scanner = BoxSpreadArbitrageScanner()
