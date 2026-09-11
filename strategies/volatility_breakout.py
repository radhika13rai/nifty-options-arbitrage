"""
Single-Leg OTM Volatility Breakout Research Strategy.
Designed specifically for the ₹3,000 retail capital constraint.
Trades single-leg low-premium OTM options (< ₹40) with tight ₹150 risk cap
and statutory friction hurdle calculations.
"""

import time
import uuid
from typing import Optional
from config import config
from market_data.normalizer import MarketTick
from market_data.orderbook import OrderbookSnapshot
from strategies.base import BaseStrategy, TradingSignal
from costs.transaction_costs import cost_engine


class VolatilityBreakoutStrategy(BaseStrategy):
    """
    Capital-feasible breakout strategy for 1 lot (65 units) of NIFTY options.
    Monitors short-term momentum and orderbook depth imbalance to capture rapid volatility expansions.
    """

    def __init__(
        self,
        name: str = "VOLATILITY_BREAKOUT_OTM",
        max_premium: float = 38.0,  # Max premium so 65 * 38 = ₹2,470 < ₹3,000
        min_premium: float = 12.0,  # Lower bound to avoid ultra-low delta decay traps
        stop_loss_points: float = 1.6,  # 1.6 pts * 65 = ₹104 loss + ₹45 fees = ₹149 <= ₹150 cap
        target_risk_reward: float = 2.5  # Target = 1.6 * 2.5 = 4.0 pts gain (₹260 gross - ₹45 fees = ₹215 net)
    ):
        super().__init__(name)
        self.max_premium = max_premium
        self.min_premium = min_premium
        self.stop_loss_points = stop_loss_points
        self.target_risk_reward = target_risk_reward
        self.lot_size = config.market.nifty_lot_size
        self._last_prices: dict[str, float] = {}

    def on_tick(self, tick: MarketTick) -> list[TradingSignal]:
        # Track price history
        self._last_prices[tick.symbol] = tick.ltp
        return []

    def on_orderbook(self, snapshot: OrderbookSnapshot) -> list[TradingSignal]:
        """
        Evaluates orderbook state. Triggers when:
        1. Premium is within [min_premium, max_premium]
        2. Strong orderbook imbalance (|imbalance| > 0.40) indicating directional pressure
        3. Spread is tight (<= 0.50 points)
        """
        if not self.is_active or snapshot.symbol == "NIFTY_SPOT":
            return []

        ask = snapshot.best_ask
        bid = snapshot.best_bid

        # Check capital feasibility: Outlay must fit comfortably within ₹3,000
        outlay = ask * self.lot_size
        if ask > self.max_premium or ask < self.min_premium:
            return []

        # Check spread tightness to minimize immediate crossing friction
        if snapshot.spread > 0.60:
            return []

        signals = []

        # High positive imbalance + micro-price above mid => aggressive buy pressure
        if snapshot.imbalance >= 0.40 and snapshot.micro_price > snapshot.mid_price:
            stop_loss = round(max(0.05, ask - self.stop_loss_points), 2)
            target = round(ask + (self.stop_loss_points * self.target_risk_reward), 2)
            
            # Double check trade risk against ₹150 hard ceiling
            expected_loss_pts = ask - stop_loss
            friction_est = cost_engine.calculate_order_costs("BUY", ask, self.lot_size).total_costs * 2
            total_risk = (expected_loss_pts * self.lot_size) + friction_est

            if total_risk <= config.risk.max_trade_loss_inr:
                sig = TradingSignal(
                    signal_id=str(uuid.uuid4())[:8],
                    timestamp_ms=time.time() * 1000.0,
                    strategy_name=self.name,
                    symbol=snapshot.symbol,
                    action="BUY",
                    order_type="MARKET",
                    suggested_price=ask,
                    quantity=self.lot_size,
                    stop_loss_price=stop_loss,
                    target_price=target,
                    confidence=min(0.95, 0.60 + abs(snapshot.imbalance) * 0.35),
                    is_capital_feasible=True,
                    infeasibility_reason=None,
                    metadata={
                        "outlay_inr": round(outlay, 2),
                        "imbalance": snapshot.imbalance,
                        "spread": snapshot.spread,
                        "total_risk_inr": round(total_risk, 2),
                        "hurdle_pts": round(friction_est / self.lot_size, 2)
                    }
                )
                signals.append(sig)

        return signals
