"""
Market Alert & Volatility Shock Defense Engine.
Monitors breaking news alerts and macroeconomic spikes (e.g. Brent Crude > 2%, VIX surges),
broadcasting high-priority market alerts and enforcing temporary trading stand-down windows.
"""

import time
import uuid
import logging
from dataclasses import dataclass
from typing import Literal, Optional

AlertSeverity = Literal["INFO", "WARNING", "CRITICAL_SHOCK"]

logger = logging.getLogger("MarketAlertEngine")


@dataclass(frozen=True)
class MarketAlert:
    alert_id: str
    timestamp_ms: float
    severity: AlertSeverity
    event_type: str
    headline: str
    action_recommended: str
    cooldown_until_ms: float
    source: str


class AlertEngine:
    """
    Alert Engine orchestrating high-priority market warnings and capital protection.
    Enforces a mandatory 15-minute stand-down when CRITICAL_SHOCK events are triggered.
    """

    def __init__(self, shock_cooldown_minutes: float = 15.0):
        self.shock_cooldown_ms = shock_cooldown_minutes * 60.0 * 1000.0
        self._alerts: list[MarketAlert] = []
        self._shock_stand_down_until_ms: float = 0.0
        self._last_shock_reason: Optional[str] = None

    def trigger_alert(
        self,
        severity: AlertSeverity,
        event_type: str,
        headline: str,
        action_recommended: str = "MONITOR",
        source: str = "MarketIntelligence"
    ) -> MarketAlert:
        now_ms = time.time() * 1000.0
        alert_id = f"ALT_{int(now_ms)}_{str(uuid.uuid4())[:4]}"
        
        cooldown_until = 0.0
        if severity == "CRITICAL_SHOCK":
            cooldown_until = now_ms + self.shock_cooldown_ms
            self._shock_stand_down_until_ms = max(self._shock_stand_down_until_ms, cooldown_until)
            self._last_shock_reason = f"{event_type}: {headline}"
            logger.warning(
                f"ALERT ENGINE: CRITICAL SHOCK DETECTED -> Engaging 15-minute Entry Stand-Down until "
                f"{time.strftime('%H:%M:%S', time.localtime(cooldown_until/1000.0))}. Reason: {headline}"
            )
        else:
            logger.info(f"ALERT ENGINE: [{severity}] {event_type}: {headline}")

        alert = MarketAlert(
            alert_id=alert_id,
            timestamp_ms=now_ms,
            severity=severity,
            event_type=event_type,
            headline=headline,
            action_recommended=action_recommended,
            cooldown_until_ms=cooldown_until,
            source=source
        )

        self._alerts.insert(0, alert)
        if len(self._alerts) > 100:
            self._alerts.pop()

        return alert

    def is_shock_stand_down_active(self, current_time_ms: Optional[float] = None) -> bool:
        """Returns True if the system is currently in a defensive shock cooldown window."""
        now_ms = current_time_ms or (time.time() * 1000.0)
        return now_ms < self._shock_stand_down_until_ms

    def get_remaining_stand_down_sec(self, current_time_ms: Optional[float] = None) -> float:
        now_ms = current_time_ms or (time.time() * 1000.0)
        remaining_ms = max(0.0, self._shock_stand_down_until_ms - now_ms)
        return round(remaining_ms / 1000.0, 1)

    def get_last_shock_reason(self) -> Optional[str]:
        if self.is_shock_stand_down_active():
            return self._last_shock_reason
        return None

    def get_recent_alerts(self, limit: int = 20) -> list[dict]:
        return [
            {
                "alert_id": a.alert_id,
                "timestamp_ms": a.timestamp_ms,
                "severity": a.severity,
                "event_type": a.event_type,
                "headline": a.headline,
                "action_recommended": a.action_recommended,
                "cooldown_until_ms": a.cooldown_until_ms,
                "source": a.source
            }
            for a in self._alerts[:limit]
        ]

    def clear(self) -> None:
        self._alerts.clear()
        self._shock_stand_down_until_ms = 0.0
        self._last_shock_reason = None


alert_engine = AlertEngine()
