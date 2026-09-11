"""
Margin Calculation & Retail Feasibility Analyzer.
Evaluates exchange SPAN margin and cash margin requirements for single-leg and multi-leg structures.
"""

from dataclasses import dataclass
from typing import Literal
from config import config


@dataclass(frozen=True)
class MarginRequirement:
    structure_name: str
    is_feasible: bool
    required_capital_inr: float
    available_capital_inr: float
    shortfall_inr: float
    margin_type: Literal["CASH_PREMIUM", "SPAN_EXPOSURE", "SPREAD_BENEFIT"]
    explanation: str


class MarginCalculator:
    """Calculates margin requirements according to NSE margin framework."""

    @staticmethod
    def evaluate_option_buy(premium: float, quantity: int = config.market.nifty_lot_size) -> MarginRequirement:
        """Long option only requires premium + upfront transaction costs."""
        outlay = premium * quantity
        required = outlay + 45.0  # approximate fee buffer
        available = config.initial_capital_inr
        is_feasible = required <= available
        shortfall = max(0.0, required - available)

        return MarginRequirement(
            structure_name="LONG_OPTION_SINGLE_LEG",
            is_feasible=is_feasible,
            required_capital_inr=round(required, 2),
            available_capital_inr=available,
            shortfall_inr=round(shortfall, 2),
            margin_type="CASH_PREMIUM",
            explanation="Long options require 100% upfront premium plus statutory transaction fees."
        )

    @staticmethod
    def evaluate_option_sell(strike: float, quantity: int = config.market.nifty_lot_size) -> MarginRequirement:
        """Short option requires full SPAN + Exposure margin."""
        # NSE NIFTY SPAN + Exposure is typically 10-12% of underlying contract value
        # At NIFTY 24,500, contract value = 24,500 * 65 = ₹15,92,500. Margin ~₹1,40,000
        required = 140000.0
        available = config.initial_capital_inr
        shortfall = required - available

        return MarginRequirement(
            structure_name="SHORT_OPTION_NAKED",
            is_feasible=False,
            required_capital_inr=required,
            available_capital_inr=available,
            shortfall_inr=shortfall,
            margin_type="SPAN_EXPOSURE",
            explanation="Shorting options requires exchange SPAN margin of ~₹1,40,000 per lot (65 units)."
        )

    @staticmethod
    def evaluate_arbitrage_multileg() -> MarginRequirement:
        """Multi-leg arbitrage (synthetic forward, conversion/reversal, box spread)."""
        required = 85000.0  # Even with spread hedge benefit
        available = config.initial_capital_inr
        shortfall = required - available

        return MarginRequirement(
            structure_name="MULTI_LEG_ARBITRAGE",
            is_feasible=False,
            required_capital_inr=required,
            available_capital_inr=available,
            shortfall_inr=shortfall,
            margin_type="SPREAD_BENEFIT",
            explanation="Multi-leg arbitrage contains short legs requiring hedged SPAN margin of ~₹85,000 minimum."
        )


margin_calculator = MarginCalculator()
