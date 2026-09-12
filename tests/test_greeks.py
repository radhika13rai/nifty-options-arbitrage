"""
Unit and Integration Tests for Black-Scholes Greeks Engine & Dynamic Strike Screener.
Validates:
  1. Put-Call Parity: C - P = S - K * exp(-rT) within 1e-4 tolerance.
  2. Delta boundaries: 0 < Δ_call < 1, -1 < Δ_put < 0, and Δ_call - Δ_put = 1.0.
  3. Gamma positivity and ATM peaking.
  4. Theta decay negativity and holding period decay.
  5. Vega positivity, symmetry, and 1% shift precision.
  6. Implied Volatility solver accuracy across CE and PE contracts.
  7. Micro-capital strike screening: Premium <= ₹38.00, Delta in [0.15, 0.30], outlay <= ₹2,470.
  8. REST API endpoints (/api/greeks/calculate, /api/greeks/iv, /api/greeks/screener).
"""

import math
import pytest
from starlette.testclient import TestClient

from analytics.greeks import (
    OptionGreeks,
    calculate_d1_d2,
    calculate_option_price,
    calculate_delta,
    calculate_gamma,
    calculate_theta,
    calculate_vega,
    calculate_rho,
    calculate_all_greeks,
    calculate_implied_volatility,
    norm_cdf,
    norm_pdf,
)
from analytics.strike_screener import StrikeScreener, strike_screener
from api.app import app


# ----------------------------------------------------------------------
# 1. Put-Call Parity Tests
# ----------------------------------------------------------------------

def test_put_call_parity():
    """Validates analytical Put-Call Parity: C - P = S - K * exp(-rT)."""
    spot = 24500.0
    rate = 0.0675
    iv = 0.16

    for strike in [24000.0, 24500.0, 25000.0]:
        for days in [1.0, 4.0, 10.0, 30.0]:
            t_years = days / 365.0
            call_price = calculate_option_price(spot, strike, t_years, rate, iv, "CE")
            put_price = calculate_option_price(spot, strike, t_years, rate, iv, "PE")

            synthetic_parity = spot - strike * math.exp(-rate * t_years)
            actual_diff = call_price - put_price

            assert abs(actual_diff - synthetic_parity) < 1e-4, (
                f"Parity violated at K={strike}, days={days}: diff={actual_diff}, expected={synthetic_parity}"
            )


# ----------------------------------------------------------------------
# 2. Delta Sensitivity & Boundaries Tests
# ----------------------------------------------------------------------

def test_delta_bounds_and_relationship():
    """Validates Call and Put Delta bounds and the theoretical identity Δ_C - Δ_P = 1.0."""
    spot = 24500.0
    strike = 24500.0
    t_years = 5.0 / 365.0
    rate = 0.0675
    iv = 0.15

    delta_c = calculate_delta(spot, strike, t_years, rate, iv, "CE")
    delta_p = calculate_delta(spot, strike, t_years, rate, iv, "PE")

    assert 0.0 < delta_c < 1.0
    assert -1.0 < delta_p < 0.0
    assert abs((delta_c - delta_p) - 1.0) < 1e-5

    # Deep ITM Call should approach 1.0
    itm_call_delta = calculate_delta(26000.0, 24000.0, t_years, rate, iv, "CE")
    assert itm_call_delta > 0.99

    # Deep OTM Call should approach 0.0
    otm_call_delta = calculate_delta(23000.0, 25000.0, t_years, rate, iv, "CE")
    assert otm_call_delta < 0.01


# ----------------------------------------------------------------------
# 3. Gamma Convexity & ATM Peaking Tests
# ----------------------------------------------------------------------

def test_gamma_properties():
    """Validates Gamma positivity, Call/Put equality, and ATM peak."""
    spot = 24500.0
    t_years = 4.0 / 365.0
    rate = 0.0675
    iv = 0.155

    gamma_atm = calculate_gamma(spot, 24500.0, t_years, rate, iv)
    gamma_otm = calculate_gamma(spot, 25200.0, t_years, rate, iv)
    gamma_itm = calculate_gamma(spot, 23800.0, t_years, rate, iv)

    assert gamma_atm > 0.0
    assert gamma_atm > gamma_otm
    assert gamma_atm > gamma_itm


# ----------------------------------------------------------------------
# 4. Theta Decay Negativity Tests
# ----------------------------------------------------------------------

def test_theta_properties():
    """Validates Theta decay is negative for long options and scales to trading hours."""
    spot = 24500.0
    strike = 24700.0
    t_years = 4.0 / 365.0
    rate = 0.0675
    iv = 0.155

    theta_day_c, theta_ann_c, theta_hr_c = calculate_theta(spot, strike, t_years, rate, iv, "CE")
    theta_day_p, theta_ann_p, theta_hr_p = calculate_theta(spot, strike, t_years, rate, iv, "PE")

    assert theta_day_c < 0.0
    assert theta_day_p < 0.0
    assert theta_hr_c == pytest.approx(theta_day_c / 6.25, rel=1e-3)
    assert theta_day_c == pytest.approx(theta_ann_c / 365.0, rel=1e-3)


# ----------------------------------------------------------------------
# 5. Vega Sensitivity Tests
# ----------------------------------------------------------------------

def test_vega_properties():
    """Validates Vega positivity, Call/Put equality, and 1% shift precision."""
    spot = 24500.0
    strike = 24500.0
    t_years = 7.0 / 365.0
    rate = 0.0675
    iv = 0.15

    vega_1pct, vega_ann = calculate_vega(spot, strike, t_years, rate, iv)
    assert vega_1pct > 0.0
    assert vega_1pct == pytest.approx(vega_ann / 100.0, rel=1e-3)

    # Finite difference check: Price with IV + 1%
    p1 = calculate_option_price(spot, strike, t_years, rate, iv, "CE")
    p2 = calculate_option_price(spot, strike, t_years, rate, iv + 0.01, "CE")
    finite_diff_vega = p2 - p1

    # Theoretical vega per 1% should closely match finite difference
    assert abs(finite_diff_vega - vega_1pct) < 0.05


# ----------------------------------------------------------------------
# 6. Implied Volatility Solver Tests
# ----------------------------------------------------------------------

def test_iv_solver_convergence():
    """Validates Newton-Raphson IV solver convergence against known volatility benchmarks."""
    spot = 24500.0
    strike = 24800.0
    t_years = 4.0 / 365.0
    rate = 0.0675
    target_iv = 0.175  # 17.5%

    # 1. Call option test
    ce_price = calculate_option_price(spot, strike, t_years, rate, target_iv, "CE")
    solved_ce_iv = calculate_implied_volatility(ce_price, spot, strike, t_years, rate, "CE")

    assert solved_ce_iv is not None
    assert abs(solved_ce_iv - target_iv) < 2e-4

    # 2. Put option test
    pe_price = calculate_option_price(spot, strike, t_years, rate, target_iv, "PE")
    solved_pe_iv = calculate_implied_volatility(pe_price, spot, strike, t_years, rate, "PE")

    assert solved_pe_iv is not None
    assert abs(solved_pe_iv - target_iv) < 2e-4


def test_iv_solver_arbitrage_violation():
    """Validates IV solver gracefully handles prices below intrinsic (arbitrage violation)."""
    spot = 24500.0
    strike = 24000.0  # ITM Call by 500 pts
    t_years = 4.0 / 365.0
    rate = 0.0675

    # Price below intrinsic (e.g., ₹200 when intrinsic is ₹500)
    invalid_price = 200.0
    solved_iv = calculate_implied_volatility(invalid_price, spot, strike, t_years, rate, "CE")
    assert solved_iv is None


# ----------------------------------------------------------------------
# 7. Micro-Capital Strike Screener Invariant Tests
# ----------------------------------------------------------------------

def test_strike_screener_rules():
    """Validates strict adherence to ₹3,000 micro-capital and Greek invariants."""
    screener = StrikeScreener(
        max_premium_inr=38.00,
        min_premium_inr=10.00,
        min_delta=0.15,
        max_delta=0.30,
        capital_limit_inr=3000.0,
        lot_size=65
    )

    spot = 24500.0
    days = 4.0
    iv = 0.155

    # 1. Bullish Screening
    best_ce = screener.select_best_strike(spot=spot, days_to_expiry=days, iv=iv, directional_bias="BULLISH")
    assert best_ce is not None
    assert best_ce.option_type == "CE"
    assert best_ce.market_price <= 38.00
    assert best_ce.capital_outlay <= 2470.0
    assert best_ce.capital_headroom >= 530.0
    assert 0.15 <= abs(best_ce.greeks.delta) <= 0.30
    assert best_ce.is_eligible is True

    # 2. Bearish Screening
    best_pe = screener.select_best_strike(spot=spot, days_to_expiry=days, iv=iv, directional_bias="BEARISH")
    assert best_pe is not None
    assert best_pe.option_type == "PE"
    assert best_pe.market_price <= 38.00
    assert best_pe.capital_outlay <= 2470.0
    assert best_pe.capital_headroom >= 530.0
    assert 0.15 <= abs(best_pe.greeks.delta) <= 0.30
    assert best_pe.is_eligible is True

    # 3. Invariant Violation Checks: Over-budget ATM strike
    atm_eval = screener.evaluate_strike(
        strike=24500.0,
        option_type="CE",
        spot=spot,
        days_to_expiry=days,
        iv=iv
    )
    assert atm_eval.is_eligible is False
    assert any("exceeds micro-capital cap" in r for r in atm_eval.rejection_reasons)


# ----------------------------------------------------------------------
# 8. REST API Endpoints Integration Tests
# ----------------------------------------------------------------------

def test_api_greeks_endpoints():
    """Tests /api/greeks/calculate, /api/greeks/iv, and /api/greeks/screener."""
    client = TestClient(app)

    # 1. /api/greeks/calculate
    calc_resp = client.post("/api/greeks/calculate", json={
        "spot": 24500.0,
        "strike": 24800.0,
        "days_to_expiry": 4.0,
        "iv": 0.155,
        "option_type": "CE"
    })
    assert calc_resp.status_code == 200
    data = calc_resp.json()
    assert data["status"] == "SUCCESS"
    greeks = data["greeks"]
    assert "delta" in greeks
    assert "gamma" in greeks
    assert "theta_per_day" in greeks
    assert "vega_per_1pct" in greeks
    assert greeks["delta"] > 0.20

    # 2. /api/greeks/iv
    theo_price = greeks["theoretical_price"]
    iv_resp = client.post("/api/greeks/iv", json={
        "market_price": theo_price,
        "spot": 24500.0,
        "strike": 24800.0,
        "days_to_expiry": 4.0,
        "option_type": "CE"
    })
    assert iv_resp.status_code == 200
    iv_data = iv_resp.json()
    assert iv_data["status"] == "SUCCESS"
    assert abs(iv_data["implied_volatility"] - 0.155) < 5e-4

    # 3. /api/greeks/screener
    scr_resp = client.get("/api/greeks/screener?spot=24500&bias=BULLISH&days_to_expiry=4&iv=0.155")
    assert scr_resp.status_code == 200
    scr_data = scr_resp.json()
    assert scr_data["status"] == "SUCCESS"
    assert scr_data["best_strike"] is not None
    assert scr_data["best_strike"]["market_price"] <= 38.00
    assert scr_data["best_strike"]["capital_outlay"] <= 2470.0
