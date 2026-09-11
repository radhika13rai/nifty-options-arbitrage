"""
Put-Call Parity Arbitrage Scanner & Capital Feasibility Analyzer.
Detects theoretical synthetic parity mispricings: C - P = S - K * exp(-rT).
Explicitly proves and flags CAPITAL_INFEASIBLE under ₹3,000 retail capital constraint.
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


class PutCallParityArbitrageScanner(BaseStrategy):
    """
    Monitors European Put-Call Parity on NIFTY index options.
    Evaluates real synthetic forward arbitrage opportunities against 4-leg statutory friction.
    """

    def __init__(
        self,
        name: str = "PUT_CALL_PARITY_ARBITRAGE",
        min_discrepancy_pts: float = 2.0  # Minimum mispricing points after accounting for 4-leg friction
    ):
        super().__init__(name)
        self.min_discrepancy_pts = min_discrepancy_pts
        self.r = config.market.risk_free_rate
        self.lot_size = config.market.nifty_lot_size
        self.t_years = 7.0 / 365.0  # Default 7 days to weekly expiry

    def on_tick(self, tick: MarketTick) -> list[TradingSignal]:
        return []

    def scan_strike(
        self,
        strike: float,
        ce_symbol: str,
        pe_symbol: str,
        spot_price: float
    ) -> list[TradingSignal]:
        """
        Scans CE and PE pair at strike K for Put-Call Parity deviation:
        Parity relation: Synthetic Forward = C - P + K * exp(-r*T) vs Actual Spot S.
        Deviation = (C - P) - (S - K * exp(-r*T)).
        """
        ce_snap = orderbook_manager.get_snapshot(ce_symbol)
        pe_snap = orderbook_manager.get_snapshot(pe_symbol)

        if not ce_snap or not pe_snap:
            return []

        # Discount factor
        df = math.exp(-self.r * self.t_years)
        discounted_strike = strike * df

        # Theoretical Put-Call difference based on spot
        theoretical_diff = spot_price - discounted_strike

        signals = []

        # -------------------------------------------------------------
        # Case A: Call Overpriced relative to Put -> Reversal Arbitrage
        # Sell Call (at Bid), Buy Put (at Ask), Buy Spot / Future (at Ask)
        # -------------------------------------------------------------
        actual_diff_sell_c = ce_snap.best_bid - pe_snap.best_ask
        mispricing_reversal = actual_diff_sell_c - theoretical_diff

        # 4-leg round trip transaction friction for arbitrage:
        # Brokerage (4 x ₹20 = ₹80) + STT + Turnover + GST + Stamp Duty ~= ~₹180 - ₹240
        # On 65 lot size: friction hurdle is approx 3.0 to 3.5 index points.
        net_edge_reversal = mispricing_reversal - 3.2

        if net_edge_reversal > self.min_discrepancy_pts:
            # Reversal opportunity found!
            # BUT: Selling Call requires SPAN + Exposure Margin of ~₹1,35,000!
            # With ₹3,000 account capital, this is 100% CAPITAL_INFEASIBLE.
            sig = TradingSignal(
                signal_id=str(uuid.uuid4())[:8],
                timestamp_ms=time.time() * 1000.0,
                strategy_name=self.name,
                symbol=f"{ce_symbol}+{pe_symbol}",
                action="SELL",  # Short synthetic forward
                order_type="LIMIT",
                suggested_price=mispricing_reversal,
                quantity=self.lot_size,
                confidence=0.88,
                is_capital_feasible=False,
                infeasibility_reason=(
                    f"CAPITAL_INFEASIBLE: Multi-leg reversal requires selling naked call {ce_symbol}. "
                    f"NSE SPAN + Exposure margin requirement is ~₹1,38,000 per lot (65 units), "
                    f"exceeding available capital (₹{config.initial_capital_inr:,.2f}) by 46x."
                ),
                metadata={
                    "type": "REVERSAL_ARBITRAGE",
                    "strike": strike,
                    "spot_price": spot_price,
                    "gross_mispricing_pts": round(mispricing_reversal, 2),
                    "estimated_net_profit_pts": round(net_edge_reversal, 2),
                    "estimated_net_profit_inr": round(net_edge_reversal * self.lot_size, 2),
                    "span_margin_required_inr": 138000.0,
                    "friction_pts": 3.2
                }
            )
            signals.append(sig)

        # -------------------------------------------------------------
        # Case B: Call Underpriced relative to Put -> Conversion Arbitrage
        # Buy Call (at Ask), Sell Put (at Bid), Sell Spot / Future (at Bid)
        # -------------------------------------------------------------
        actual_diff_buy_c = ce_snap.best_ask - pe_snap.best_bid
        mispricing_conversion = theoretical_diff - actual_diff_buy_c
        net_edge_conversion = mispricing_conversion - 3.2

        if net_edge_conversion > self.min_discrepancy_pts:
            # Conversion opportunity found!
            # BUT: Selling Put requires SPAN margin of ~₹1,45,000!
            sig = TradingSignal(
                signal_id=str(uuid.uuid4())[:8],
                timestamp_ms=time.time() * 1000.0,
                strategy_name=self.name,
                symbol=f"{ce_symbol}+{pe_symbol}",
                action="BUY",  # Long synthetic forward
                order_type="LIMIT",
                suggested_price=mispricing_conversion,
                quantity=self.lot_size,
                confidence=0.88,
                is_capital_feasible=False,
                infeasibility_reason=(
                    f"CAPITAL_INFEASIBLE: Multi-leg conversion requires shorting put {pe_symbol} and futures. "
                    f"NSE SPAN margin requirement is ~₹1,45,000 per lot (65 units), "
                    f"exceeding available capital (₹{config.initial_capital_inr:,.2f}) by 48x."
                ),
                metadata={
                    "type": "CONVERSION_ARBITRAGE",
                    "strike": strike,
                    "spot_price": spot_price,
                    "gross_mispricing_pts": round(mispricing_conversion, 2),
                    "estimated_net_profit_pts": round(net_edge_conversion, 2),
                    "estimated_net_profit_inr": round(net_edge_conversion * self.lot_size, 2),
                    "span_margin_required_inr": 145000.0,
                    "friction_pts": 3.2
                }
            )
            signals.append(sig)

        return signals

    def on_orderbook(self, snapshot: OrderbookSnapshot) -> list[TradingSignal]:
        # Pairwise scanning is triggered explicitly or on spot update
        return []


put_call_parity_scanner = PutCallParityArbitrageScanner()
