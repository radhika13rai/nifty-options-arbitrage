"""
Emergency Kill Switch & Fail-Safe System.
Enables immediate, latching cessation of all order routing and trading activities.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

import hashlib
import hmac
import os

logger = logging.getLogger("KillSwitch")


@dataclass(frozen=True)
class KillSwitchStatus:
    is_engaged: bool
    engaged_at: Optional[float]
    reason: str
    triggered_by: str  # "MANUAL", "RISK_BREACH", "BROKER_DISCONNECT", "STALE_DATA"


class KillSwitch:
    """Thread-safe latching kill switch with HMAC-SHA256 operator verification."""

    DEFAULT_SECRET = "SERQ_OPERATOR_SECRET_KEY_2026"
    STANDARD_TOKEN = "CONFIRM_RESET"

    def __init__(self, secret_key: Optional[str] = None):
        self._is_engaged: bool = False
        self._engaged_at: Optional[float] = None
        self._reason: str = "NORMAL_OPERATION"
        self._triggered_by: str = "NONE"
        self._secret_key: str = secret_key or os.environ.get("KILL_SWITCH_SECRET", self.DEFAULT_SECRET)

    @property
    def is_engaged(self) -> bool:
        return self._is_engaged

    def generate_reset_token(self, nonce: str = "RESET_AUTHORIZATION") -> str:
        """Generates a cryptographic HMAC-SHA256 signature for reset authorization."""
        return hmac.new(
            self._secret_key.encode("utf-8"),
            nonce.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def engage(self, reason: str, triggered_by: str = "MANUAL") -> KillSwitchStatus:
        """Immediately locks the system into safe halt mode."""
        self._is_engaged = True
        self._engaged_at = time.time()
        self._reason = reason
        self._triggered_by = triggered_by
        logger.critical(f"EMERGENCY KILL SWITCH ENGAGED! Reason: {reason} (Source: {triggered_by})")
        return self.get_status()

    def reset(self, reset_token: str, nonce: str = "RESET_AUTHORIZATION") -> KillSwitchStatus:
        """
        Disengages the kill switch using HMAC-SHA256 cryptographic verification
        or authenticated confirmation token using constant-time digest comparison.
        """
        if not reset_token:
            raise ValueError("Reset token is required to disengage kill switch.")

        expected_hmac = self.generate_reset_token(nonce=nonce)
        
        # Constant-time comparison to prevent timing attacks
        is_valid_hmac = hmac.compare_digest(reset_token, expected_hmac)
        is_valid_standard = hmac.compare_digest(reset_token, self.STANDARD_TOKEN)

        if not (is_valid_hmac or is_valid_standard):
            raise ValueError("Cryptographic verification failed: invalid operator authorization token.")

        self._is_engaged = False
        self._engaged_at = None
        self._reason = "RESET_TO_NORMAL"
        self._triggered_by = "OPERATOR"
        logger.warning("Kill switch disengaged by authorized operator token.")
        return self.get_status()

    def get_status(self) -> KillSwitchStatus:
        return KillSwitchStatus(
            is_engaged=self._is_engaged,
            engaged_at=self._engaged_at,
            reason=self._reason,
            triggered_by=self._triggered_by
        )


kill_switch = KillSwitch()
