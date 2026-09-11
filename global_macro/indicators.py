"""
Global Macro Indicators & Leading Market Cues Engine.
Tracks GIFT NIFTY, Brent Crude, US Dollar Index (DXY), and CBOE VIX
to quantify international economic and geopolitical pressure on NIFTY 50.
"""

import time
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MacroIndicatorSnapshot:
    """Standardized snapshot of leading global market variables."""
    timestamp_ms: float
    brent_crude_usd: float       # Oil price ($/barrel)
    brent_change_pct: float      # % change today
    dollar_index_dxy: float      # DXY index value
    dxy_change_pct: float        # % change today
    gift_nifty_points: float     # GIFT NIFTY level
    gift_nifty_gap_pts: float    # Estimated morning gap on NIFTY 50
    us_vix: float                # CBOE Volatility index
    us_vix_change_pct: float     # % change today
    sp500_change_pct: float      # US market % change

    def to_dense_vector(self) -> list[float]:
        """
        Returns normalized 5-dimensional numerical embedding vector:
        [brent_norm, dxy_norm, gift_gap_norm, us_vix_norm, sp500_norm]
        """
        # Normalizing around typical standard deviations
        return [
            round(self.brent_change_pct / 3.0, 4),        # +/- 3% is 1 std
            round(self.dxy_change_pct / 0.5, 4),          # +/- 0.5% is 1 std
            round(self.gift_nifty_gap_pts / 100.0, 4),    # +/- 100 pts is 1 std
            round(self.us_vix_change_pct / 10.0, 4),      # +/- 10% is 1 std
            round(self.sp500_change_pct / 1.5, 4)         # +/- 1.5% is 1 std
        ]


class GlobalMacroEngine:
    """Coordinates ingestion, normalization, and simulation of world market cues."""

    def __init__(self):
        self._current_snapshot: MacroIndicatorSnapshot = self._create_baseline_snapshot()

    def _create_baseline_snapshot(self) -> MacroIndicatorSnapshot:
        return MacroIndicatorSnapshot(
            timestamp_ms=time.time() * 1000.0,
            brent_crude_usd=82.50,
            brent_change_pct=0.20,
            dollar_index_dxy=103.80,
            dxy_change_pct=0.05,
            gift_nifty_points=24510.0,
            gift_nifty_gap_pts=10.0,
            us_vix=14.50,
            us_vix_change_pct=0.80,
            sp500_change_pct=0.15
        )

    def get_snapshot(self) -> MacroIndicatorSnapshot:
        return self._current_snapshot

    def update_snapshot(self, snapshot: MacroIndicatorSnapshot) -> None:
        self._current_snapshot = snapshot

    def apply_scenario(self, scenario_name: str) -> MacroIndicatorSnapshot:
        """
        Applies pre-configured world macro scenarios for backtesting and simulation.
        """
        now = time.time() * 1000.0
        if scenario_name == "MIDDLE_EAST_WAR_CRISIS":
            # Severe geopolitical shock: Crude spikes, Gift Nifty gaps down, fear surges
            snap = MacroIndicatorSnapshot(
                timestamp_ms=now,
                brent_crude_usd=89.20,
                brent_change_pct=4.80,
                dollar_index_dxy=105.10,
                dxy_change_pct=0.85,
                gift_nifty_points=24320.0,
                gift_nifty_gap_pts=-180.0,
                us_vix=21.40,
                us_vix_change_pct=22.50,
                sp500_change_pct=-1.85
            )
        elif scenario_name == "GLOBAL_DEESCALATION_RELIEF":
            # De-escalation / Ceasefire: Crude plummets, Gift Nifty rallies, VIX crushes
            snap = MacroIndicatorSnapshot(
                timestamp_ms=now,
                brent_crude_usd=78.10,
                brent_change_pct=-3.60,
                dollar_index_dxy=102.90,
                dxy_change_pct=-0.65,
                gift_nifty_points=24660.0,
                gift_nifty_gap_pts=160.0,
                us_vix=12.80,
                us_vix_change_pct=-14.20,
                sp500_change_pct=1.40
            )
        elif scenario_name == "US_FED_HAWKISH_SURPRISE":
            # Fed signals higher interest rates: Dollar surges, emerging markets sell off
            snap = MacroIndicatorSnapshot(
                timestamp_ms=now,
                brent_crude_usd=81.00,
                brent_change_pct=-1.20,
                dollar_index_dxy=105.60,
                dxy_change_pct=1.10,
                gift_nifty_points=24390.0,
                gift_nifty_gap_pts=-110.0,
                us_vix=17.20,
                us_vix_change_pct=11.00,
                sp500_change_pct=-1.50
            )
        else:  # NEUTRAL
            snap = self._create_baseline_snapshot()

        self._current_snapshot = snap
        return snap


macro_engine = GlobalMacroEngine()
