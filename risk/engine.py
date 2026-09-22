"""
Pre-Trade Risk Engine & Risk Kernel Interface.
Single authoritative risk management gate ensuring strict risk and capital floor adherence.
"""

from risk.kernel import (
    RiskKernel,
    risk_kernel,
    PreTradeOrderRequest,
    RiskCheckResult,
    CapitalReservationResult,
)
from risk.limits import risk_limits, RiskLimits
from risk.kill_switch import kill_switch
from risk.stale_data_guard import stale_data_guard

# Alias PreTradeRiskEngine directly to RiskKernel to ensure unified single-authority risk policy
PreTradeRiskEngine = RiskKernel
risk_engine = risk_kernel

__all__ = [
    "PreTradeOrderRequest",
    "RiskCheckResult",
    "CapitalReservationResult",
    "PreTradeRiskEngine",
    "RiskKernel",
    "risk_engine",
    "risk_kernel",
    "risk_limits",
    "RiskLimits",
    "kill_switch",
    "stale_data_guard",
]
