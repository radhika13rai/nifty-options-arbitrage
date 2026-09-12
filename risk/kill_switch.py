"""
Emergency Kill Switch & Fail-Safe System.
Enables immediate, latching cessation of all order routing and trading activities.
"""

import contextlib
import hashlib
import hmac
import logging
import os
import threading
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
    """Thread-safe latching kill switch with HMAC-SHA256 operator verification and atomic execution gate."""

    def __init__(self, secret_key: Optional[str] = None):
        self._lock = threading.RLock()
        self._execution_lock = threading.RLock()
        self._is_engaged: bool = False
        self._engaged_at: Optional[float] = None
        self._reason: str = "NORMAL_OPERATION"
        self._triggered_by: str = "NONE"

        # Load from parameter, environment, or generate secure random session secret
        env_secret = os.environ.get("KILL_SWITCH_SECRET")
        if secret_key:
            self._secret_key = secret_key
        elif env_secret:
            self._secret_key = env_secret
        else:
            # Ephemeral cryptographically strong secret unique to this process lifecycle
            import secrets
            self._secret_key = secrets.token_hex(32)
            logger.info("Initialized ephemeral cryptographic secret for session lifecycle.")

    @property
    def is_engaged(self) -> bool:
        with self._lock:
            return self._is_engaged

    @property
    def execution_lock(self) -> threading.RLock:
        return self._execution_lock

    @contextlib.contextmanager
    def atomic_execution_gate(self):
        """
        Context manager ensuring atomic validation and execution.
        Guarantees that no kill-switch state transition can occur
        between pre-execution risk validation and portfolio mutation.
        """
        with self._execution_lock:
            yield

    def generate_reset_token(self, nonce: str = "RESET_AUTHORIZATION") -> str:
        """Generates a cryptographic HMAC-SHA256 signature for reset authorization."""
        return hmac.new(
            self._secret_key.encode("utf-8"),
            nonce.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def engage(self, reason: str, triggered_by: str = "MANUAL") -> KillSwitchStatus:
        """Immediately locks the system into safe halt mode."""
        with self._execution_lock:
            with self._lock:
                self._is_engaged = True
                self._engaged_at = time.time()
                self._reason = reason
                self._triggered_by = triggered_by
        logger.critical(f"EMERGENCY KILL SWITCH ENGAGED! Reason: {reason} (Source: {triggered_by})")
        return self.get_status()

    def reset(self, reset_token: str, nonce: str = "RESET_AUTHORIZATION") -> KillSwitchStatus:
        """
        Disengages the kill switch strictly using HMAC-SHA256 cryptographic signature
        verification with constant-time digest comparison.
        """
        if not reset_token:
            raise ValueError("Cryptographic reset signature is required to disengage kill switch.")

        expected_hmac = self.generate_reset_token(nonce=nonce)
        
        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(reset_token, expected_hmac):
            raise ValueError("Cryptographic verification failed: invalid operator HMAC-SHA256 signature.")

        with self._execution_lock:
            with self._lock:
                self._is_engaged = False
                self._engaged_at = None
                self._reason = "RESET_TO_NORMAL"
                self._triggered_by = "OPERATOR"
        logger.warning("Kill switch disengaged by verified operator HMAC-SHA256 signature.")
        return self.get_status()

    def reset_system(self, nonce: str = "RESET_AUTHORIZATION") -> KillSwitchStatus:
        """Internal/trusted reset using the instance's active cryptographic key."""
        token = self.generate_reset_token(nonce=nonce)
        return self.reset(token, nonce=nonce)

    def get_status(self) -> KillSwitchStatus:
        with self._lock:
            return KillSwitchStatus(
                is_engaged=self._is_engaged,
                engaged_at=self._engaged_at,
                reason=self._reason,
                triggered_by=self._triggered_by
            )


kill_switch = KillSwitch()
