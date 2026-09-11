"""
Risk Limits & Pre-Trade Constraints Module.
Implements the strict risk limits defined for the ₹3,000 capital research experiment.
"""

from dataclasses import dataclass
from config import config


@dataclass(frozen=True)
class RiskLimits:
    """Immutable pre-trade risk parameter thresholds."""
    max_trade_loss_inr: float = config.risk.max_trade_loss_inr  # ₹150 max loss per trade
    max_daily_loss_inr: float = config.risk.max_daily_loss_inr  # ₹300 max loss per day
    max_lots: int = config.risk.max_lots  # 1 lot (65 units)
    capital_floor_inr: float = config.risk.capital_floor_inr  # Halt trading below ₹2,000
    stale_timeout_ms: int = config.risk.stale_quote_timeout_ms  # 1500ms max tick age
    lot_size: int = config.market.nifty_lot_size  # 65 units


risk_limits = RiskLimits()
