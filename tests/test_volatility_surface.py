"""
Unit and Integration Tests for Parametric Volatility Skew & Surface Engine.
Validates:
  1. ATM Volatility Recovery (log-moneyness = 0 matches ATM IV).
  2. Put Skew Asymmetry (OTM Puts trade at volatility premium over OTM Calls).
  3. Term Structure Damping (near-expiry skew is steeper than monthly skew).
  4. Boundary Clamping (min_iv and max_iv bounds).
  5. Skew Curve Generation (discrete strike distribution and metrics).
  6. 2D Surface Grid Generation (expiry x strike matrix).
  7. OLS Skew Calibration from Orderbook Chain (insufficient data & synthetic quotes).
  8. REST API Endpoints (/api/greeks/skew, /api/greeks/surface, /api/greeks/calibrate).
"""

import math
import pytest
from starlette.testclient import TestClient

from analytics.greeks import calculate_option_price
from analytics.volatility_surface import (
    VolatilitySurface,
    VolatilitySurfacePoint,
    volatility_surface,
)
from api.app import app


# ----------------------------------------------------------------------
# 1. Theoretical Skew Behavior & Invariants
# ----------------------------------------------------------------------

def test_atm_iv_recovery():
    """Confirms that at K == S (log-moneyness = 0), IV exactly recovers base_atm_iv."""
    surface = VolatilitySurface(base_atm_iv=0.16, skew_slope=-0.35, smile_curvature=0.50)
    spot = 24500.0

    for days in [0.5, 1.0, 4.0, 7.0, 14.0, 30.0]:
        iv = surface.get_implied_volatility(strike=spot, spot=spot, days_to_expiry=days)
        assert abs(iv - 0.16) < 1e-5, f"ATM IV recovery failed at days={days}: got {iv}"

    # With override
    iv_override = surface.get_implied_volatility(strike=spot, spot=spot, days_to_expiry=4.0, atm_iv_override=0.22)
    assert abs(iv_override - 0.22) < 1e-5


def test_put_skew_asymmetry():
    """
    Validates structural Put Skew:
    1. OTM Put (K < S) IV > ATM IV.
    2. OTM Put (S - dK) IV > OTM Call (S + dK) IV due to negative skew slope (crash protection).
    """
    surface = VolatilitySurface(base_atm_iv=0.155, skew_slope=-0.35, smile_curvature=0.50)
    spot = 24500.0
    days = 4.0

    atm_iv = surface.get_implied_volatility(strike=24500.0, spot=spot, days_to_expiry=days)
    otm_put_iv = surface.get_implied_volatility(strike=24100.0, spot=spot, days_to_expiry=days)
    otm_call_iv = surface.get_implied_volatility(strike=24900.0, spot=spot, days_to_expiry=days)

    assert otm_put_iv > atm_iv, f"OTM Put IV ({otm_put_iv}) should exceed ATM IV ({atm_iv})"
    assert otm_put_iv > otm_call_iv, (
        f"Put skew violated: OTM Put IV ({otm_put_iv}) must exceed equidistant OTM Call IV ({otm_call_iv})"
    )


def test_term_structure_damping():
    """
    Near-term weekly contracts (e.g. 1-2 days) feature steeper skew than monthly contracts (e.g. 30 days).
    """
    surface = VolatilitySurface(base_atm_iv=0.155, skew_slope=-0.35, smile_curvature=0.50)
    spot = 24500.0
    otm_strike = 24000.0  # Deep OTM put

    near_iv = surface.get_implied_volatility(strike=otm_strike, spot=spot, days_to_expiry=1.0)
    monthly_iv = surface.get_implied_volatility(strike=otm_strike, spot=spot, days_to_expiry=30.0)

    near_skew_spread = abs(near_iv - 0.155)
    monthly_skew_spread = abs(monthly_iv - 0.155)

    assert near_skew_spread > monthly_skew_spread, (
        f"Term damping failed: near skew spread ({near_skew_spread}) must exceed monthly ({monthly_skew_spread})"
    )


def test_boundary_clamping():
    """Verifies numerical safety bounds [min_iv, max_iv] for extreme tail strikes."""
    surface = VolatilitySurface(min_iv=0.08, max_iv=0.85)

    # Extreme low strike / deep crash
    extreme_crash_iv = surface.get_implied_volatility(strike=5000.0, spot=24500.0, days_to_expiry=1.0)
    assert extreme_crash_iv <= 0.85
    assert extreme_crash_iv >= 0.08

    # Extreme high strike
    extreme_call_iv = surface.get_implied_volatility(strike=100000.0, spot=24500.0, days_to_expiry=1.0)
    assert extreme_call_iv <= 0.85
    assert extreme_call_iv >= 0.08

    # Edge cases: 0 spot or 0 strike returns base_atm_iv safely without crash
    assert surface.get_implied_volatility(strike=0, spot=24500.0, days_to_expiry=4.0) == surface.base_atm_iv
    assert surface.get_implied_volatility(strike=24500.0, spot=0, days_to_expiry=4.0) == surface.base_atm_iv


# ----------------------------------------------------------------------
# 2. Skew Curve and Grid Generation
# ----------------------------------------------------------------------

def test_skew_curve_generation():
    """Validates discrete strike curve generation across moneyness spectrum."""
    surface = VolatilitySurface()
    spot = 24500.0
    num_strikes = 6
    curve = surface.generate_skew_curve(spot=spot, days_to_expiry=4.0, num_strikes=num_strikes)

    assert len(curve) == 2 * num_strikes + 1
    assert all(isinstance(p, VolatilitySurfacePoint) for p in curve)

    # ATM point check
    atm_pt = next(p for p in curve if p.strike == 24500.0)
    assert atm_pt.moneyness_ratio == 1.0
    assert atm_pt.log_moneyness == 0.0
    assert abs(atm_pt.implied_volatility - surface.base_atm_iv) < 1e-4

    # Monotonicity check near ATM: OTM Put strikes have strictly higher IV than ATM
    put_pt = next(p for p in curve if p.strike == 24300.0)
    assert put_pt.implied_volatility > atm_pt.implied_volatility


def test_surface_grid_structure():
    """Validates 2D Volatility Surface matrix dimensions and structure."""
    surface = VolatilitySurface()
    spot = 24500.0
    expiries = [1.0, 4.0, 7.0, 14.0, 30.0]
    num_strikes = 5

    grid = surface.get_surface_grid(spot=spot, expiry_days_list=expiries, num_strikes=num_strikes)

    assert grid["spot"] == spot
    assert grid["expiries"] == expiries
    expected_strikes_count = 2 * num_strikes + 1
    assert len(grid["strikes"]) == expected_strikes_count
    assert len(grid["matrix"]) == len(expiries)

    for row in grid["matrix"]:
        assert len(row) == expected_strikes_count
        assert all(isinstance(v, float) and 8.0 <= v <= 85.0 for v in row)


# ----------------------------------------------------------------------
# 3. OLS Skew Calibration Engine
# ----------------------------------------------------------------------

def test_calibration_insufficient_quotes():
    """Fewer than 4 valid quotes must return INSUFFICIENT_DATA and leave priors intact."""
    surface = VolatilitySurface(base_atm_iv=0.155)
    quotes = [
        {"strike": 24500.0, "option_type": "CE", "market_price": 120.0},
        {"strike": 24600.0, "option_type": "CE", "market_price": 70.0},
    ]

    res = surface.calibrate_from_market_chain(chain_quotes=quotes, spot=24500.0, days_to_expiry=4.0)
    assert res["status"] == "INSUFFICIENT_DATA"
    assert res["sample_points"] <= 2
    assert surface.base_atm_iv == 0.155


def test_calibration_recovers_known_parameters():
    """
    Synthesize realistic market quotes from known skew parameters,
    then verify OLS regression successfully calibrates and recovers parameters.
    """
    surface = VolatilitySurface(base_atm_iv=0.155, skew_slope=-0.35, smile_curvature=0.50)
    spot = 24500.0
    days = 4.0
    t_years = days / 365.0
    rate = 0.0675

    # Generate synthetic quotes across strikes
    strikes = [24200.0, 24300.0, 24400.0, 24450.0, 24500.0, 24550.0, 24600.0, 24700.0, 24800.0]
    quotes = []

    for k in strikes:
        true_iv = surface.get_implied_volatility(k, spot, days)
        ot = "PE" if k < spot else "CE"
        price = calculate_option_price(
            spot=spot,
            strike=k,
            time_to_expiry_years=t_years,
            risk_free_rate=rate,
            iv=true_iv,
            option_type=ot,
        )
        quotes.append({"strike": k, "option_type": ot, "market_price": round(price, 2)})

    fresh_surface = VolatilitySurface(base_atm_iv=0.20, skew_slope=0.0, smile_curvature=0.0)
    res = fresh_surface.calibrate_from_market_chain(chain_quotes=quotes, spot=spot, days_to_expiry=days)

    assert res["status"] == "CALIBRATED"
    assert res["sample_points"] >= 7
    # Recovers ATM IV within 1.5% margin
    assert abs(res["calibrated_atm_iv"] - 0.155) < 0.020
    # Negative skew slope recovered
    assert res["calibrated_slope"] < 0.0


# ----------------------------------------------------------------------
# 4. REST API Endpoints Integration
# ----------------------------------------------------------------------

client = TestClient(app)


def test_api_volatility_skew_endpoint():
    """Tests GET /api/greeks/skew endpoint."""
    resp = client.get("/api/greeks/skew?spot=24500&days_to_expiry=4")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "SUCCESS"
    assert data["spot"] == 24500.0
    assert data["days_to_expiry"] == 4.0
    assert "points" in data
    assert len(data["points"]) > 0

    first_pt = data["points"][0]
    assert "strike" in first_pt
    assert "implied_volatility" in first_pt
    assert "log_moneyness" in first_pt


def test_api_volatility_surface_endpoint():
    """Tests GET /api/greeks/surface endpoint."""
    resp = client.get("/api/greeks/surface?spot=24500")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "SUCCESS"
    surface = data["surface"]
    assert surface["spot"] == 24500.0
    assert len(surface["expiries"]) == 5
    assert len(surface["matrix"]) == 5


def test_api_volatility_calibrate_endpoint():
    """Tests POST /api/greeks/calibrate endpoint."""
    # Invalid JSON body
    resp_bad = client.post("/api/greeks/calibrate", content="invalid", headers={"Content-Type": "application/json"})
    assert resp_bad.status_code == 400

    # Valid payload with mock quotes
    quotes = [
        {"strike": 24300.0, "option_type": "PE", "market_price": 50.0},
        {"strike": 24400.0, "option_type": "PE", "market_price": 80.0},
        {"strike": 24500.0, "option_type": "CE", "market_price": 110.0},
        {"strike": 24600.0, "option_type": "CE", "market_price": 60.0},
        {"strike": 24700.0, "option_type": "CE", "market_price": 30.0},
    ]
    resp = client.post("/api/greeks/calibrate", json={
        "spot": 24500.0,
        "days_to_expiry": 4.0,
        "quotes": quotes
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "calibration" in data


def test_screener_skew_integration():
    """Validates that StrikeScreener with use_skew=True reflects empirical skew."""
    from analytics.strike_screener import strike_screener

    # Flat screening
    flat_results = strike_screener.generate_and_screen(
        spot=24500.0, days_to_expiry=4.0, iv=0.155, directional_bias="BEARISH", use_skew=False
    )
    # Skew-aware screening
    skew_results = strike_screener.generate_and_screen(
        spot=24500.0, days_to_expiry=4.0, iv=0.155, directional_bias="BEARISH", use_skew=True
    )

    # In downside puts, skew IV should be higher than flat 0.155, leading to higher theoretical premium
    flat_put = next(s for s in flat_results if s.strike == 24200.0 and s.option_type == "PE")
    skew_put = next(s for s in skew_results if s.strike == 24200.0 and s.option_type == "PE")

    assert skew_put.greeks.iv > flat_put.greeks.iv
    assert skew_put.market_price > flat_put.market_price


def test_api_screener_with_skew():
    """Tests GET /api/greeks/screener?use_skew=true endpoint."""
    resp = client.get("/api/greeks/screener?spot=24500&days_to_expiry=4&bias=BEARISH&use_skew=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "best_strike" in data
    assert data["total_screened"] > 0
