"""
Empirical Volatility Skew & Surface Modeling Engine for NIFTY Index Options.
Replaces naive flat-IV assumptions with institutional parametric skew modeling:
  - Quadratic Log-Moneyness Skew: σ(K) = σ_atm + term_damping * [β_1 * ln(K/S) + β_2 * (ln(K/S))²]
  - Captures the pronounced NSE NIFTY downside Put skew (crash protection demand).
  - Term structure scaling: Skew steepens near weekly expiry and flattens out-of-month.
  - Calibration from real-time orderbook snapshots via ordinary least squares (OLS).
"""

import math
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Any
from config import config
from analytics.greeks import calculate_implied_volatility, normalize_option_type


@dataclass(frozen=True)
class VolatilitySurfacePoint:
    strike: float
    spot: float
    moneyness_ratio: float  # K / S
    log_moneyness: float    # ln(K / S)
    days_to_expiry: float
    implied_volatility: float
    iv_pct: float


class VolatilitySurface:
    """
    Parametric Volatility Surface and Skew Generator for NIFTY Options.
    Reflects the structural realities of Indian equity derivatives:
    - Downside Put Skew: β1 < 0 (OTM Puts trade at higher IV).
    - Smile Convexity: β2 > 0 (Extreme OTM wings trade at volatility premium).
    """

    def __init__(
        self,
        base_atm_iv: float = 0.155,       # 15.5% typical NIFTY ATM IV
        skew_slope: float = -0.35,        # Negative slope (downside crash risk premium)
        smile_curvature: float = 0.50,     # Wing convexity
        reference_days: float = 7.0,      # 7-day weekly benchmark
        min_iv: float = 0.08,             # 8.0% minimum realistic IV
        max_iv: float = 0.85              # 85.0% maximum extreme shock IV
    ):
        self.base_atm_iv = base_atm_iv
        self.skew_slope = skew_slope
        self.smile_curvature = smile_curvature
        self.reference_days = reference_days
        self.min_iv = min_iv
        self.max_iv = max_iv

    def get_implied_volatility(
        self,
        strike: float,
        spot: float,
        days_to_expiry: float,
        atm_iv_override: Optional[float] = None
    ) -> float:
        """
        Calculates the strike-specific Implied Volatility for a given strike and expiry.
        Uses quadratic log-moneyness expansion scaled by term structure.
        """
        if spot <= 0 or strike <= 0:
            return self.base_atm_iv

        atm_iv = atm_iv_override if atm_iv_override is not None else self.base_atm_iv
        log_moneyness = math.log(strike / spot)

        # Term structure damping: Near-expiry (0-4 days) exhibits steeper skew;
        # monthly (30+ days) exhibits flatter, smoother smile.
        t_days = max(0.5, days_to_expiry)
        term_factor = math.pow(self.reference_days / t_days, 0.25)
        term_factor = max(0.65, min(1.80, term_factor))

        # Quadratic skew formula: σ(k) = σ_atm + term * (β1 * k + β2 * k²)
        skew_adjustment = term_factor * (
            self.skew_slope * log_moneyness +
            self.smile_curvature * (log_moneyness ** 2)
        )

        iv = atm_iv + skew_adjustment
        return round(max(self.min_iv, min(self.max_iv, iv)), 6)

    def generate_skew_curve(
        self,
        spot: float,
        days_to_expiry: float = 4.0,
        num_strikes: int = 12,
        strike_interval: int = config.market.strike_interval,
        atm_iv_override: Optional[float] = None
    ) -> List[VolatilitySurfacePoint]:
        """
        Generates a discrete skew curve of VolatilitySurfacePoint instances
        across strikes centered around ATM.
        """
        atm_strike = round(spot / strike_interval) * strike_interval
        points: List[VolatilitySurfacePoint] = []

        for i in range(-num_strikes, num_strikes + 1):
            k = float(atm_strike + (i * strike_interval))
            iv = self.get_implied_volatility(
                strike=k,
                spot=spot,
                days_to_expiry=days_to_expiry,
                atm_iv_override=atm_iv_override
            )
            m_ratio = round(k / spot, 4)
            log_m = round(math.log(k / spot), 4)

            points.append(VolatilitySurfacePoint(
                strike=k,
                spot=round(spot, 2),
                moneyness_ratio=m_ratio,
                log_moneyness=log_m,
                days_to_expiry=round(days_to_expiry, 2),
                implied_volatility=iv,
                iv_pct=round(iv * 100.0, 2)
            ))

        return points

    def calibrate_from_market_chain(
        self,
        chain_quotes: List[Dict[str, Any]],
        spot: float,
        days_to_expiry: float,
        risk_free_rate: float = config.market.risk_free_rate
    ) -> Dict[str, Any]:
        """
        Calibrates parametric skew coefficients (β0, β1, β2) from a list of market quotes
        using Ordinary Least Squares (OLS) regression on solved IVs.
        Each quote should have: {"strike": float, "option_type": "CE"|"PE", "market_price": float}
        """
        t_years = max(0.001, days_to_expiry / 365.0)
        xs: List[float] = []
        ys: List[float] = []

        for q in chain_quotes:
            k = float(q.get("strike", 0))
            price = float(q.get("market_price", 0))
            ot = q.get("option_type", "CE")

            if k <= 0 or price <= 0:
                continue

            solved_iv = calculate_implied_volatility(
                market_price=price,
                spot=spot,
                strike=k,
                time_to_expiry_years=t_years,
                risk_free_rate=risk_free_rate,
                option_type=ot
            )
            if solved_iv is not None and self.min_iv <= solved_iv <= self.max_iv:
                m = math.log(k / spot)
                xs.append(m)
                ys.append(solved_iv)

        if len(xs) < 4:
            # Insufficient points for robust regression; retain priors
            return {
                "status": "INSUFFICIENT_DATA",
                "sample_points": len(xs),
                "atm_iv": self.base_atm_iv,
                "skew_slope": self.skew_slope,
                "smile_curvature": self.smile_curvature
            }

        # Fit quadratic polynomial using scaled log-moneyness u = 100 * x for numerical conditioning
        us = [x * 100.0 for x in xs]
        n = len(us)
        s_u = sum(us)
        s_u2 = sum(u * u for u in us)
        s_u3 = sum(u * u * u for u in us)
        s_u4 = sum(u * u * u * u for u in us)

        s_y = sum(ys)
        s_uy = sum(u * y for u, y in zip(us, ys))
        s_u2y = sum(u * u * y for u, y in zip(us, ys))

        # Solve 3x3 linear system A * [a, b', c']^T = B using Cramer's rule
        A = [
            [float(n), s_u, s_u2],
            [s_u, s_u2, s_u3],
            [s_u2, s_u3, s_u4]
        ]
        B = [s_y, s_uy, s_u2y]

        def det3(m):
            return (
                m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) -
                m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) +
                m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
            )

        det_A = det3(A)
        if abs(det_A) < 1e-4:
            return {"status": "SINGULAR_MATRIX", "sample_points": n}

        # Matrices with column replacements
        A0 = [[B[i], A[i][1], A[i][2]] for i in range(3)]
        A1 = [[A[i][0], B[i], A[i][2]] for i in range(3)]
        A2 = [[A[i][0], A[i][1], B[i]] for i in range(3)]

        fitted_atm = det3(A0) / det_A
        fitted_slope = (det3(A1) / det_A) * 100.0          # Unscale b = b' * 100
        fitted_curvature = (det3(A2) / det_A) * 10000.0    # Unscale c = c' * 10000

        # Safety bounds for financial stability
        self.base_atm_iv = round(max(0.08, min(0.60, fitted_atm)), 4)
        self.skew_slope = round(max(-2.50, min(0.50, fitted_slope)), 4)
        self.smile_curvature = round(max(0.05, min(250.0, fitted_curvature)), 4)

        return {
            "status": "CALIBRATED",
            "sample_points": n,
            "calibrated_atm_iv": self.base_atm_iv,
            "calibrated_slope": self.skew_slope,
            "calibrated_curvature": self.smile_curvature
        }

    def get_surface_grid(
        self,
        spot: float,
        expiry_days_list: Optional[List[float]] = None,
        num_strikes: int = 8
    ) -> Dict[str, Any]:
        """
        Generates a 2D matrix of implied volatilities across strikes and expiries
        suitable for 3D surface rendering.
        """
        if expiry_days_list is None:
            expiry_days_list = [1.0, 4.0, 7.0, 14.0, 30.0]

        grid: Dict[str, Any] = {
            "spot": spot,
            "expiries": expiry_days_list,
            "strikes": [],
            "matrix": []
        }

        atm_strike = round(spot / config.market.strike_interval) * config.market.strike_interval
        strikes = [float(atm_strike + i * config.market.strike_interval) for i in range(-num_strikes, num_strikes + 1)]
        grid["strikes"] = strikes

        for d in expiry_days_list:
            row = []
            for k in strikes:
                iv = self.get_implied_volatility(strike=k, spot=spot, days_to_expiry=d)
                row.append(round(iv * 100.0, 2))
            grid["matrix"].append(row)

        return grid


volatility_surface = VolatilitySurface()
