"""
Test Suite for Multi-Day Historical Walk-Forward Simulation (Paper V2).
Validates execution across 3 market regimes, dynamic trailing ratchet stops,
statutory friction deduction, capital floor preservation, and model adaptation.
"""

import os
import pytest
from pathlib import Path
from simulation.walk_forward import WalkForwardSimulator, DayScenarioConfig
from ml.learner import learning_engine
from portfolio.positions import position_tracker
from portfolio.pnl import pnl_manager
from execution.auto_engine import auto_engine
from risk.kill_switch import kill_switch


@pytest.fixture(autouse=True)
def reset_engine_state():
    kill_switch.reset("CONFIRM_RESET")
    learning_engine.reset()
    position_tracker.reset()
    auto_engine._active_trades.clear()
    auto_engine._trade_history.clear()
    auto_engine.enable()
    pnl_manager.reset_balance(3000.0)
    yield


@pytest.mark.anyio
async def test_simulation_initialization():
    sim = WalkForwardSimulator(initial_capital=3000.0, capital_floor=2000.0)
    assert sim.initial_capital == 3000.0
    assert sim.capital_floor == 2000.0
    assert len(sim.scenarios) == 10


@pytest.mark.anyio
async def test_3day_mini_walk_forward_execution():
    sim = WalkForwardSimulator(initial_capital=3000.0, capital_floor=2000.0)
    summary = await sim.run_simulation(num_days=3)

    assert summary.total_trades >= 2
    assert summary.ending_capital > summary.initial_capital
    assert summary.total_statutory_friction > 0.0
    assert summary.capital_floor_preserved is True
    assert summary.zero_overnight_positions is True
    assert summary.max_loss_per_trade_respected is True
    assert summary.single_lot_size_respected is True


@pytest.mark.anyio
async def test_bull_breakout_regime():
    sim = WalkForwardSimulator(initial_capital=3000.0, capital_floor=2000.0)
    # Day 1 is TRENDING_BULL
    day1_scenario = sim.scenarios[0]
    assert day1_scenario.regime == "TRENDING_BULL"
    assert day1_scenario.option_type == "CE"

    res = await sim._run_single_day(day1_scenario)
    assert res.trades_executed == 1
    assert res.net_pnl > 0.0
    assert res.statutory_fees > 45.0  # Proper statutory fee deducted


@pytest.mark.anyio
async def test_geopolitical_crude_shock_bear_regime():
    sim = WalkForwardSimulator(initial_capital=3000.0, capital_floor=2000.0)
    # Day 4 is HIGH_VOL_SHOCK
    day4_scenario = sim.scenarios[3]
    assert day4_scenario.regime == "HIGH_VOL_SHOCK"
    assert day4_scenario.option_type == "PE"

    res = await sim._run_single_day(day4_scenario)
    assert res.trades_executed == 1
    assert res.net_pnl > 0.0
    assert res.statutory_fees > 45.0


@pytest.mark.anyio
async def test_choppy_stand_down_discipline():
    sim = WalkForwardSimulator(initial_capital=3000.0, capital_floor=2000.0)
    # Day 7 is CHOPPY_CONSOLIDATION with should_signal=False
    day7_scenario = sim.scenarios[6]
    assert day7_scenario.regime == "CHOPPY_CONSOLIDATION"
    assert day7_scenario.should_signal is False

    res = await sim._run_single_day(day7_scenario)
    assert res.trades_executed == 0
    assert res.statutory_fees == 0.0
    assert res.net_pnl == 0.0  # Zero fee bleed!


@pytest.mark.anyio
async def test_hard_stop_loss_cap():
    sim = WalkForwardSimulator(initial_capital=3000.0, capital_floor=2000.0)
    # Day 9 is false breakout test
    day9_scenario = sim.scenarios[8]
    assert day9_scenario.day_number == 9

    res = await sim._run_single_day(day9_scenario)
    assert res.trades_executed == 1
    assert res.losses == 1
    # Gross loss must not exceed 150 INR
    assert res.gross_pnl >= -150.05
    assert abs(res.gross_pnl) <= 150.05


@pytest.mark.anyio
async def test_full_10day_simulation_and_report_generation(tmp_path):
    sim = WalkForwardSimulator(initial_capital=3000.0, capital_floor=2000.0)
    summary = await sim.run_simulation(num_days=10)

    assert len(summary.daily_results) == 10
    assert summary.capital_floor_preserved is True
    assert summary.zero_overnight_positions is True
    assert summary.max_loss_per_trade_respected is True
    assert summary.single_lot_size_respected is True
    assert summary.models_adapted is True
    assert summary.ending_capital > summary.initial_capital
    assert summary.win_rate_pct >= 55.0

    report_path = tmp_path / "test_walk_forward_report.md"
    generated_path = sim.generate_markdown_report(summary, filepath=str(report_path))
    assert Path(generated_path).exists()

    content = Path(generated_path).read_text(encoding="utf-8")
    assert "# Institutional Walk-Forward Backtesting" in content
    assert "Master Performance Scorecard" in content
    assert "Capital Floor Integrity" in content
    assert "PASS" in content
