"""
Real-Time Black-Scholes-Merton Analytical Greeks Engine & Numerical IV Solver.
Implements pure-Python, zero-dependency options sensitivity modeling:
  - Delta (Δ): Directional sensitivity [0, 1] for CE, [-1, 0] for PE.
  - Gamma (Γ): Convexity curvature of Delta (peaks At-The-Money).
  - Theta (Θ): Deterministic time decay (points/day, points/hour, and INR/lot/day).
  - Vega (ν): Volatility sensitivity (points per 1% IV shift and INR/lot).
  - Rho (ρ): Interest rate sensitivity (points per 1% rate shift).
  - Implied Volatility (IV): Robust Newton-Raphson solver with bisection fallback.
"""

import math
from dataclasses import dataclass, asdict
from typing import Literal, Optional, Tuple
from config import config

OptionType = Literal["CE", "PE", "CALL", "PUT"]
TRADING_HOURS_PER_DAY = 6.25  # 09:15 to 15:30 IST on NSE


def norm_cdf(x: float) -> float:
    """
    Cumulative Standard Normal Distribution function Φ(x).
    Uses math.erf for high numerical precision without external C/Fortran libraries.
    """
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_pdf(x: float) -> float:
    """Standard Normal Probability Density Function φ(x)."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def normalize_option_type(option_type: str) -> str:
    """Normalizes option type string to standard 'CE' or 'PE'."""
    ot = str(option_type).strip().upper()
    if ot in ("CE", "CALL", "C"):
        return "CE"
    if ot in ("PE", "PUT", "P"):
        return "PE"
    raise ValueError(f"Invalid option type '{option_type}'. Must be 'CE' or 'PE'.")


def calculate_d1_d2(
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    risk_free_rate: float,
    iv: float
) -> Tuple[float, float]:
    """
    Calculates Black-Scholes d1 and d2 parameters.
    d1 = [ln(S / K) + (r + 0.5 * σ^2) * T] / (σ * sqrt(T))
    d2 = d1 - σ * sqrt(T)
    """
    if spot <= 0.0 or strike <= 0.0:
        raise ValueError(f"Spot ({spot}) and strike ({strike}) must be strictly positive.")
    if time_to_expiry_years <= 0.0 or iv <= 0.0:
        raise ValueError("time_to_expiry_years and iv must be strictly positive to compute d1/d2.")

    sqrt_t = math.sqrt(time_to_expiry_years)
    numerator = math.log(spot / strike) + (risk_free_rate + 0.5 * iv * iv) * time_to_expiry_years
    denominator = iv * sqrt_t
    d1 = numerator / denominator
    d2 = d1 - iv * sqrt_t
    return d1, d2


def calculate_option_price(
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    risk_free_rate: float,
    iv: float,
    option_type: str
) -> float:
    """
    Computes theoretical European option price via Black-Scholes-Merton model.
    Handles expiry (T <= 0) and zero-volatility edge cases safely.
    """
    ot = normalize_option_type(option_type)
    if spot <= 0.0 or strike <= 0.0:
        return 0.0

    # At or past expiry: intrinsic value
    if time_to_expiry_years <= 0.0:
        if ot == "CE":
            return max(0.0, spot - strike)
        return max(0.0, strike - spot)

    # Extreme low volatility: discounted intrinsic value
    if iv <= 1e-7:
        df = math.exp(-risk_free_rate * time_to_expiry_years)
        if ot == "CE":
            return max(0.0, spot - strike * df)
        return max(0.0, strike * df - spot)

    d1, d2 = calculate_d1_d2(spot, strike, time_to_expiry_years, risk_free_rate, iv)
    df = math.exp(-risk_free_rate * time_to_expiry_years)

    if ot == "CE":
        price = spot * norm_cdf(d1) - strike * df * norm_cdf(d2)
    else:
        price = strike * df * norm_cdf(-d2) - spot * norm_cdf(-d1)

    return max(0.0, price)


def calculate_delta(
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    risk_free_rate: float,
    iv: float,
    option_type: str
) -> float:
    """
    Calculates Delta (Δ = ∂V/∂S).
    CE Delta ∈ [0.0, 1.0]
    PE Delta ∈ [-1.0, 0.0]
    """
    ot = normalize_option_type(option_type)
    if spot <= 0.0 or strike <= 0.0:
        return 0.0

    if time_to_expiry_years <= 0.0:
        if ot == "CE":
            return 1.0 if spot > strike else (0.5 if spot == strike else 0.0)
        return -1.0 if spot < strike else (-0.5 if spot == strike else 0.0)

    if iv <= 1e-7:
        df = math.exp(-risk_free_rate * time_to_expiry_years)
        discounted_strike = strike * df
        if ot == "CE":
            return 1.0 if spot > discounted_strike else 0.0
        return -1.0 if spot < discounted_strike else 0.0

    d1, _ = calculate_d1_d2(spot, strike, time_to_expiry_years, risk_free_rate, iv)
    if ot == "CE":
        return norm_cdf(d1)
    return norm_cdf(d1) - 1.0


def calculate_gamma(
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    risk_free_rate: float,
    iv: float
) -> float:
    """
    Calculates Gamma (Γ = ∂²V/∂S²).
    Convexity curvature; identical for both Calls and Puts. Always >= 0.
    """
    if spot <= 0.0 or strike <= 0.0 or time_to_expiry_years <= 0.0 or iv <= 1e-7:
        return 0.0

    d1, _ = calculate_d1_d2(spot, strike, time_to_expiry_years, risk_free_rate, iv)
    denominator = spot * iv * math.sqrt(time_to_expiry_years)
    if denominator <= 0.0:
        return 0.0

    return norm_pdf(d1) / denominator


def calculate_theta(
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    risk_free_rate: float,
    iv: float,
    option_type: str
) -> Tuple[float, float, float]:
    """
    Calculates Theta (time decay).
    Returns (theta_per_day, theta_annual, theta_per_hour).
    Convention: Negative for long options (reflecting erosion in value).
    """
    ot = normalize_option_type(option_type)
    if spot <= 0.0 or strike <= 0.0 or time_to_expiry_years <= 0.0 or iv <= 1e-7:
        return 0.0, 0.0, 0.0

    d1, d2 = calculate_d1_d2(spot, strike, time_to_expiry_years, risk_free_rate, iv)
    sqrt_t = math.sqrt(time_to_expiry_years)
    df = math.exp(-risk_free_rate * time_to_expiry_years)

    term1 = -(spot * norm_pdf(d1) * iv) / (2.0 * sqrt_t)

    if ot == "CE":
        theta_annual = term1 - risk_free_rate * strike * df * norm_cdf(d2)
    else:
        theta_annual = term1 + risk_free_rate * strike * df * norm_cdf(-d2)

    theta_per_day = theta_annual / 365.0
    theta_per_hour = theta_per_day / TRADING_HOURS_PER_DAY
    return theta_per_day, theta_annual, theta_per_hour


def calculate_vega(
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    risk_free_rate: float,
    iv: float
) -> Tuple[float, float]:
    """
    Calculates Vega (∂V/∂σ).
    Identical for Calls and Puts. Always >= 0.
    Returns (vega_per_1pct, vega_annual).
    vega_per_1pct is price sensitivity per 1% absolute IV shift (0.01).
    """
    if spot <= 0.0 or strike <= 0.0 or time_to_expiry_years <= 0.0 or iv <= 1e-7:
        return 0.0, 0.0

    d1, _ = calculate_d1_d2(spot, strike, time_to_expiry_years, risk_free_rate, iv)
    vega_annual = spot * math.sqrt(time_to_expiry_years) * norm_pdf(d1)
    vega_per_1pct = vega_annual / 100.0
    return vega_per_1pct, vega_annual


def calculate_rho(
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    risk_free_rate: float,
    iv: float,
    option_type: str
) -> Tuple[float, float]:
    """
    Calculates Rho (∂V/∂r).
    Returns (rho_per_1pct, rho_annual).
    Points per 1% interest rate change.
    """
    ot = normalize_option_type(option_type)
    if spot <= 0.0 or strike <= 0.0 or time_to_expiry_years <= 0.0 or iv <= 1e-7:
        return 0.0, 0.0

    _, d2 = calculate_d1_d2(spot, strike, time_to_expiry_years, risk_free_rate, iv)
    df = math.exp(-risk_free_rate * time_to_expiry_years)

    if ot == "CE":
        rho_annual = strike * time_to_expiry_years * df * norm_cdf(d2)
    else:
        rho_annual = -strike * time_to_expiry_years * df * norm_cdf(-d2)

    rho_per_1pct = rho_annual / 100.0
    return rho_per_1pct, rho_annual


def calculate_implied_volatility(
    market_price: float,
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    risk_free_rate: float = config.market.risk_free_rate,
    option_type: str = "CE",
    tolerance: float = 1e-4,
    max_iterations: int = 60
) -> Optional[float]:
    """
    Solves for Implied Volatility (IV) given market price using Newton-Raphson
    with guaranteed bisection fallback.
    
    Returns:
        Annualized IV as a decimal (e.g. 0.165 for 16.5%), or None if no arbitrage-free
        solution exists.
    """
    if market_price <= 0.0 or spot <= 0.0 or strike <= 0.0 or time_to_expiry_years <= 0.0:
        return None

    ot = normalize_option_type(option_type)
    df = math.exp(-risk_free_rate * time_to_expiry_years)

    # Check lower no-arbitrage boundary (discounted intrinsic)
    if ot == "CE":
        intrinsic = max(0.0, spot - strike * df)
        upper_bound_price = spot
    else:
        intrinsic = max(0.0, strike * df - spot)
        upper_bound_price = strike * df

    if market_price < intrinsic - 1e-3 or market_price > upper_bound_price:
        return None

    # Initial volatility estimate using Brenner-Subrahmanyam approximation
    try:
        bs_approx = math.sqrt(2.0 * math.pi / time_to_expiry_years) * (market_price / spot)
        current_sigma = max(0.05, min(1.50, bs_approx))
    except Exception:
        current_sigma = 0.20

    # 1. Newton-Raphson Iteration
    for _ in range(max_iterations // 2):
        price = calculate_option_price(spot, strike, time_to_expiry_years, risk_free_rate, current_sigma, ot)
        diff = price - market_price

        if abs(diff) < tolerance:
            return round(current_sigma, 6)

        _, vega_annual = calculate_vega(spot, strike, time_to_expiry_years, risk_free_rate, current_sigma)

        if vega_annual > 1e-6:
            step = diff / vega_annual
            next_sigma = current_sigma - step
            if 0.005 <= next_sigma <= 4.0 and abs(step) < 0.5:
                current_sigma = next_sigma
                continue
        break

    # 2. Bisection Fallback (Guaranteed global convergence if root is bracketed)
    sigma_low = 0.001
    sigma_high = 5.0

    f_low = calculate_option_price(spot, strike, time_to_expiry_years, risk_free_rate, sigma_low, ot) - market_price
    f_high = calculate_option_price(spot, strike, time_to_expiry_years, risk_free_rate, sigma_high, ot) - market_price

    if f_low * f_high > 0:
        if abs(f_low) < 0.05:
            return round(sigma_low, 6)
        if abs(f_high) < 0.05:
            return round(sigma_high, 6)
        return None

    sigma_mid = current_sigma
    for _ in range(max_iterations):
        sigma_mid = 0.5 * (sigma_low + sigma_high)
        f_mid = calculate_option_price(spot, strike, time_to_expiry_years, risk_free_rate, sigma_mid, ot) - market_price

        if abs(f_mid) < tolerance or abs(sigma_high - sigma_low) < 1e-5:
            return round(sigma_mid, 6)

        if f_low * f_mid <= 0.0:
            sigma_high = sigma_mid
            f_high = f_mid
        else:
            sigma_low = sigma_mid
            f_low = f_mid

    return round(sigma_mid, 6)


@dataclass(frozen=True)
class OptionGreeks:
    """Comprehensive Black-Scholes Greeks and theoretical pricing payload."""
    spot: float
    strike: float
    time_to_expiry_days: float
    time_to_expiry_years: float
    risk_free_rate: float
    option_type: str  # 'CE' or 'PE'
    iv: float
    theoretical_price: float
    intrinsic_value: float
    time_value: float
    delta: float
    gamma: float
    theta_per_day: float
    theta_per_hour: float
    theta_annual: float
    theta_per_lot_inr: float
    vega_per_1pct: float
    vega_annual: float
    vega_per_lot_inr: float
    rho_per_1pct: float

    def to_dict(self) -> dict:
        """Converts Greeks dataclass to serializable dictionary."""
        return asdict(self)


def calculate_all_greeks(
    spot: float,
    strike: float,
    days_to_expiry: float,
    iv: float,
    option_type: str = "CE",
    risk_free_rate: float = config.market.risk_free_rate,
    lot_size: int = config.market.nifty_lot_size
) -> OptionGreeks:
    """
    Computes all Black-Scholes Greeks, theoretical price, intrinsic, and time value
    for a given contract with lot-level P&L exposure.
    """
    ot = normalize_option_type(option_type)
    t_years = max(0.0, days_to_expiry / 365.0)

    price = calculate_option_price(spot, strike, t_years, risk_free_rate, iv, ot)
    if ot == "CE":
        intrinsic = max(0.0, spot - strike)
    else:
        intrinsic = max(0.0, strike - spot)
    time_val = max(0.0, price - intrinsic)

    delta = calculate_delta(spot, strike, t_years, risk_free_rate, iv, ot)
    gamma = calculate_gamma(spot, strike, t_years, risk_free_rate, iv)
    theta_day, theta_ann, theta_hour = calculate_theta(spot, strike, t_years, risk_free_rate, iv, ot)
    vega_1pct, vega_ann = calculate_vega(spot, strike, t_years, risk_free_rate, iv)
    rho_1pct, _ = calculate_rho(spot, strike, t_years, risk_free_rate, iv, ot)

    theta_lot = theta_day * lot_size
    vega_lot = vega_1pct * lot_size

    return OptionGreeks(
        spot=round(spot, 2),
        strike=round(strike, 2),
        time_to_expiry_days=round(days_to_expiry, 4),
        time_to_expiry_years=round(t_years, 6),
        risk_free_rate=round(risk_free_rate, 4),
        option_type=ot,
        iv=round(iv, 4),
        theoretical_price=round(price, 2),
        intrinsic_value=round(intrinsic, 2),
        time_value=round(time_val, 2),
        delta=round(delta, 4),
        gamma=round(gamma, 6),
        theta_per_day=round(theta_day, 4),
        theta_per_hour=round(theta_hour, 4),
        theta_annual=round(theta_ann, 2),
        theta_per_lot_inr=round(theta_lot, 2),
        vega_per_1pct=round(vega_1pct, 4),
        vega_annual=round(vega_ann, 2),
        vega_per_lot_inr=round(vega_lot, 2),
        rho_per_1pct=round(rho_1pct, 4)
    )
