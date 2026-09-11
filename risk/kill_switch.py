"""
Emergency Kill Switch & Fail-Safe System.
Enables immediate, latching cessation of all order routing and trading activities.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("KillSwitch")


@dataclass(frozen=True)
class KillSwitchStatus:
    is_engaged: bool
    engaged_at: Optional[float]
    reason: str
    triggered_by: str  # "MANUAL", "RISK_BREACH", "BROKER_DISCONNECT", "STALE_DATA"


class KillSwitch:
    """Thread-safe latching kill switch."""

    def __init__(self):
        self._is_engaged: bool = False
        self._engaged_at: Optional[float] = None
        self._reason: str = "NORMAL_OPERATION"
        self._triggered_by: str = "NONE"

    @property
    def is_engaged(self) -> bool:
        return self._is_engaged

    def engage(self, reason: str, triggered_by: str = "MANUAL") -> KillSwitchStatus:
        """Immediately locks the system into safe halt mode."""
        self._is_engaged = True
        self._engaged_at = time.time()
        self._reason = reason
        self._triggered_by = triggered_by
        logger.critical(f"EMERGENCY KILL SWITCH ENGAGED! Reason: {reason} (Source: {triggered_by})")
        return self.get_status()

    def reset(self, reset_token: str = "CONFIRM_RESET") -> KillSwitchStatus:
        """Requires explicit confirmation string to disengage."""
        if reset_token != "CONFIRM_RESET":
            raise ValueError("Invalid reset token. Must be 'CONFIRM_RESET'.")
        self._is_engaged = False
        self._engaged_at = None
        self._reason = "RESET_TO_NORMAL"
        self._triggered_by = "OPERATOR"
        logger.warning("Kill switch manually disengaged by operator.")
        return self.get_status()

    def get_status(self) -> KillSwitchStatus:
        return KillSwitchStatus(
            is_engaged=self._is_engaged,
            engaged_at=self._engaged_at,
            reason=self._reason,
            triggered_by=self._triggered_by
        )


kill_switch = KillSwitch()
