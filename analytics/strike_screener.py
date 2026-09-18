"""
Dynamic Strike Screener for Micro-Capital Single-Leg NIFTY Options.
Enforces institutional risk invariants under the ₹3,000 capital ceiling:
  1. Micro-Capital Budget: Premium <= ₹38.00 (Outlay <= ₹2,470 for 65 units, >= ₹530 headroom).
  2. Target Delta Corridor: 0.15 <= |Δ| <= 0.30 (Sweet spot ~0.22 for convex breakout acceleration).
  3. Theta Bleed Ceiling: Configurable hourly or daily decay limits to protect against intraday erosion.
  4. Liquidity & Spread Filter: Spread <= 1.00 pt (or <= 3.5% of premium).
  5. Directional Alignment: Bullish -> CE, Bearish -> PE.
"""

import math
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Literal
from config import config
from analytics.greeks import (
    OptionGreeks,
    calculate_all_greeks,
    calculate_option_price,
    normalize_option_type,
)

DirectionalBias = Literal["BULLISH", "BEARISH", "NEUTRAL"]


@dataclass(frozen=True)
class ScreenedStrike:
    """Detailed screening assessment of an option strike."""
    symbol: str
    strike: float
    option_type: str  # "CE" or "PE"
    expiry: str
    days_to_expiry: float
    market_price: float
    lot_size: int
    capital_outlay: float
    capital_headroom: float
    greeks: OptionGreeks
    bid: float
    ask: float
    spread: float
    spread_pct: float
    gamma_theta_ratio: float  # Gamma convexity vs Theta decay efficiency (Γ * 1000 / |Θ|)
    quality_score: float  # 0.0 to 100.0
    is_eligible: bool
    rejection_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Converts screened strike to serializable dictionary."""
        d = asdict(self)
        d["greeks"] = self.greeks.to_dict()
        return d


class StrikeScreener:
    """
    Screens NIFTY options chain to select optimal single-leg strikes
    adhering strictly to micro-capital and Greek sensitivity rules.
    """

    def __init__(
        self,
        max_premium_inr: float = 38.00,
        min_premium_inr: float = 10.00,
        min_delta: float = 0.15,
        max_delta: float = 0.30,
        target_delta: float = 0.225,
        max_theta_day: Optional[float] = 30.0,
        max_theta_hour: Optional[float] = None,
        max_spread_pts: float = 1.00,
        max_spread_pct: float = 3.50,
        capital_limit_inr: float = config.initial_capital_inr,
        lot_size: int = config.market.nifty_lot_size,
    ):
        self.max_premium_inr = max_premium_inr
        self.min_premium_inr = min_premium_inr
        self.min_delta = min_delta
        self.max_delta = max_delta
        self.target_delta = target_delta
        self.max_theta_day = max_theta_day
        self.max_theta_hour = max_theta_hour
        self.max_spread_pts = max_spread_pts
        self.max_spread_pct = max_spread_pct
        self.capital_limit_inr = capital_limit_inr
        self.lot_size = lot_size

    def evaluate_strike(
        self,
        strike: float,
        option_type: str,
        spot: float,
        days_to_expiry: float,
        iv: float,
        market_price: Optional[float] = None,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
        expiry: str = "2026-09-24",
        symbol: Optional[str] = None
    ) -> ScreenedStrike:
        """Evaluates a single strike against all risk and Greek invariants."""
        ot = normalize_option_type(option_type)

        # 1. Compute theoretical Greeks
        greeks = calculate_all_greeks(
            spot=spot,
            strike=strike,
            days_to_expiry=days_to_expiry,
            iv=iv,
            option_type=ot,
            lot_size=self.lot_size
        )

        # Price determination
        theo_price = greeks.theoretical_price
        if market_price is None:
            market_price = max(0.05, round(theo_price, 2))

        if bid is None or ask is None:
            half_spread = 0.10
            bid = max(0.05, round(market_price - half_spread, 2))
            ask = round(market_price + half_spread, 2)

        spread = round(ask - bid, 2)
        spread_pct = round((spread / market_price) * 100.0, 2) if market_price > 0 else 0.0

        if symbol is None:
            symbol = f"NIFTY_{expiry}_{int(strike)}_{ot}"

        capital_outlay = round(market_price * self.lot_size, 2)
        capital_headroom = round(self.capital_limit_inr - capital_outlay, 2)

        rejection_reasons: List[str] = []

        # Invariant 1: Capital ceiling (Premium <= ₹38.00 and Total Outlay <= Available Capital)
        if market_price > self.max_premium_inr:
            rejection_reasons.append(
                f"Premium ₹{market_price:.2f} exceeds micro-capital cap ₹{self.max_premium_inr:.2f}"
            )
        if capital_outlay > self.capital_limit_inr:
            rejection_reasons.append(
                f"Capital outlay ₹{capital_outlay:.2f} exceeds ₹{self.capital_limit_inr:.2f}"
            )

        # Invariant 2: Deep OTM lottery floor (Premium >= ₹10.00)
        if market_price < self.min_premium_inr:
            rejection_reasons.append(
                f"Premium ₹{market_price:.2f} is below deep-OTM decay floor ₹{self.min_premium_inr:.2f}"
            )

        # Invariant 3: Target Delta corridor (0.15 <= |Δ| <= 0.30)
        abs_delta = abs(greeks.delta)
        if abs_delta < self.min_delta:
            rejection_reasons.append(
                f"Delta {abs_delta:.3f} below minimum efficiency corridor {self.min_delta:.2f}"
            )
        elif abs_delta > self.max_delta:
            rejection_reasons.append(
                f"Delta {abs_delta:.3f} exceeds maximum efficiency corridor {self.max_delta:.2f}"
            )

        # Invariant 4: Theta bleed ceiling (daily or hourly)
        abs_theta_day = abs(greeks.theta_per_day)
        if self.max_theta_day is not None and abs_theta_day > self.max_theta_day:
            rejection_reasons.append(
                f"Theta decay {abs_theta_day:.2f} pts/day exceeds limit {self.max_theta_day:.2f} pts/day"
            )
        abs_theta_hour = abs(greeks.theta_per_hour)
        if self.max_theta_hour is not None and abs_theta_hour > self.max_theta_hour:
            rejection_reasons.append(
                f"Hourly theta {abs_theta_hour:.2f} pts/hr exceeds limit {self.max_theta_hour:.2f} pts/hr"
            )

        # Invariant 5: Bid-ask spread sanity
        if spread > self.max_spread_pts and spread_pct > self.max_spread_pct:
            rejection_reasons.append(
                f"Spread {spread:.2f} pts ({spread_pct:.1f}%) exceeds liquidity threshold"
            )

        is_eligible = len(rejection_reasons) == 0

        # Compute Gamma / Theta convexity efficiency
        gamma_theta_ratio = round((greeks.gamma * 1000.0) / max(0.20, abs_theta_day), 4)

        # Compute Institutional Quality Score (0 to 100)
        quality_score = 0.0
        if is_eligible:
            # 1. Delta sweet spot score (up to 35 pts)
            delta_diff = abs(abs_delta - self.target_delta)
            delta_score = max(0.0, 1.0 - (delta_diff / 0.075)) * 35.0

            # 2. Theta efficiency score: Delta gain per unit of daily Theta loss (up to 25 pts)
            theta_ratio = abs_delta / max(0.20, abs_theta_day)
            theta_score = min(25.0, theta_ratio * 125.0)

            # 3. Gamma convexity acceleration: Gamma per unit of Theta decay (up to 15 pts)
            gamma_score = min(15.0, gamma_theta_ratio * 30.0)

            # 4. Capital preservation score: Headroom buffer (up to 15 pts)
            affordability_score = (
                max(0.0, (self.max_premium_inr - market_price) / (self.max_premium_inr - self.min_premium_inr))
            ) * 15.0

            # 5. Spread tightness score (up to 10 pts)
            spread_score = max(0.0, 1.0 - (spread / self.max_spread_pts)) * 10.0

            quality_score = round(delta_score + theta_score + gamma_score + affordability_score + spread_score, 2)
        else:
            delta_diff = abs(abs_delta - self.target_delta)
            quality_score = max(0.0, round((1.0 - min(1.0, delta_diff / 0.20)) * 20.0, 2))

        return ScreenedStrike(
            symbol=symbol,
            strike=round(strike, 2),
            option_type=ot,
            expiry=expiry,
            days_to_expiry=round(days_to_expiry, 4),
            market_price=round(market_price, 2),
            lot_size=self.lot_size,
            capital_outlay=capital_outlay,
            capital_headroom=capital_headroom,
            greeks=greeks,
            bid=round(bid, 2),
            ask=round(ask, 2),
            spread=spread,
            spread_pct=spread_pct,
            gamma_theta_ratio=gamma_theta_ratio,
            quality_score=quality_score,
            is_eligible=is_eligible,
            rejection_reasons=rejection_reasons
        )

    def generate_and_screen(
        self,
        spot: float,
        days_to_expiry: float = 4.0,
        iv: float = 0.155,
        directional_bias: DirectionalBias = "BULLISH",
        num_strikes: int = 15,
        strike_interval: int = config.market.strike_interval,
        expiry: str = "2026-09-24",
        use_skew: bool = False
    ) -> List[ScreenedStrike]:
        """
        Generates and evaluates a full option chain around the spot price.
        Returns all evaluated strikes sorted by eligibility first, then quality_score descending.
        When use_skew=True, evaluates each strike using parametric volatility surface skew.
        """
        bias = directional_bias.upper()
        if bias in ("BULLISH", "LONG", "BUY_CE"):
            target_types = ["CE"]
        elif bias in ("BEARISH", "SHORT", "BUY_PE"):
            target_types = ["PE"]
        else:
            target_types = ["CE", "PE"]

        atm_strike = round(spot / strike_interval) * strike_interval
        evaluated: List[ScreenedStrike] = []

        for i in range(-num_strikes, num_strikes + 1):
            k = atm_strike + (i * strike_interval)
            strike_iv = iv
            if use_skew:
                from analytics.volatility_surface import volatility_surface
                strike_iv = volatility_surface.get_implied_volatility(
                    strike=float(k),
                    spot=spot,
                    days_to_expiry=days_to_expiry,
                    atm_iv_override=iv
                )
            for ot in target_types:
                sc = self.evaluate_strike(
                    strike=float(k),
                    option_type=ot,
                    spot=spot,
                    days_to_expiry=days_to_expiry,
                    iv=strike_iv,
                    expiry=expiry
                )
                evaluated.append(sc)

        evaluated.sort(key=lambda s: (s.is_eligible, s.quality_score), reverse=True)
        return evaluated

    def select_best_strike(
        self,
        spot: float,
        days_to_expiry: float = 4.0,
        iv: float = 0.155,
        directional_bias: DirectionalBias = "BULLISH",
        expiry: str = "2026-09-24",
        use_skew: bool = False
    ) -> Optional[ScreenedStrike]:
        """
        Selects the single highest-scoring eligible strike matching directional posture.
        Returns None if no strike satisfies the micro-capital and Greek constraints.
        """
        screened = self.generate_and_screen(
            spot=spot,
            days_to_expiry=days_to_expiry,
            iv=iv,
            directional_bias=directional_bias,
            expiry=expiry,
            use_skew=use_skew
        )
        eligible = [s for s in screened if s.is_eligible]
        if eligible:
            return eligible[0]
        return None


strike_screener = StrikeScreener()
