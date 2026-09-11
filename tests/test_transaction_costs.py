"""
Tests for Indian Securities & Derivatives Statutory Cost Engine (2026 Schedule).
"""

from costs.transaction_costs import cost_engine


def test_buy_order_costs():
    """
    BUY 1 lot of NIFTY @ ₹30.00:
    Turnover = 30 * 65 = ₹1,950.00
    Brokerage = ₹20.00
    STT = 0 (Buy side options)
    Exchange charges = 0.05% of 1950 = round(0.975, 2) = ₹0.97
    SEBI charges = 0.0001% of 1950 = ₹0.00
    GST = 18% of (20 + 0.97) = round(3.7746, 2) = ₹3.77
    Stamp Duty = 0.003% of 1950 = round(0.0585, 2) = ₹0.06
    Total costs = 20 + 0.97 + 3.77 + 0.06 = ₹24.80
    """
    breakdown = cost_engine.calculate_order_costs("BUY", 30.0, 65)
    assert breakdown.turnover == 1950.0
    assert breakdown.brokerage == 20.0
    assert breakdown.stt == 0.0
    assert breakdown.exchange_charges == 0.97
    assert breakdown.stamp_duty == 0.06
    assert breakdown.gst == 3.77
    assert breakdown.total_costs == 24.80
    assert breakdown.net_cash_flow == -(1950.0 + 24.80)


def test_sell_order_costs():
    """
    SELL 1 lot of NIFTY @ ₹35.00:
    Turnover = 35 * 65 = ₹2,275.00
    Brokerage = ₹20.00
    STT = 0.1% of 2275 = round(2.275, 2) = ₹2.27 (Sell side options)
    Exchange charges = 0.05% of 2275 = round(1.1375, 2) = ₹1.14
    GST = 18% of (20 + 1.14) = round(3.8052, 2) = ₹3.81
    Stamp duty = 0 (Sell side)
    Total costs = 20 + 2.27 + 1.14 + 3.81 = ₹27.22
    """
    breakdown = cost_engine.calculate_order_costs("SELL", 35.0, 65)
    assert breakdown.turnover == 2275.0
    assert breakdown.brokerage == 20.0
    assert breakdown.stt == 2.27
    assert breakdown.exchange_charges == 1.14
    assert breakdown.stamp_duty == 0.0
    assert breakdown.gst == 3.81
    assert breakdown.total_costs == 27.22


def test_round_trip_breakeven():
    """
    Round trip: BUY @ ₹30.00, SELL @ ₹35.00 (65 units):
    Gross PnL = (35 - 30) * 65 = ₹325.00
    Total friction = 24.80 + 27.22 = ₹52.02
    Net PnL = 325 - 52.02 = ₹272.98
    Breakeven hurdle in points = round(52.02 / 65, 2) = 0.80 points
    """
    rt = cost_engine.calculate_round_trip("BUY", 30.0, 35.0, 65)
    assert rt.gross_pnl == 325.0
    assert rt.total_friction == 52.02
    assert rt.net_pnl == 272.98
    assert rt.points_hurdle == 0.80
    assert rt.breakeven_exit_price == 30.80
