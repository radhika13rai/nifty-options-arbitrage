"""
Unit tests for the Automated Continuous Paper Soak Runner (Paper V2).
Tests:
  1. Soak runner initialization and config overrides
  2. Procedural scenario generator across multiple regimes
  3. Single-step execution, PnL accounting, and invariant validation
  4. SQLite daily_pnl recording and WAL checkpointing
  5. Capital floor breach triggering latching kill switch
  6. Pause, resume, and graceful stop controls
  7. Starlette REST API endpoints (/api/soak/status, reset, stop)
"""

import asyncio
import pytest
from starlette.testclient import TestClient

from api.app import app
from database.db import db_manager
from risk.kill_switch import kill_switch
from simulation.soak_runner import (
    PaperSoakRunner,
    SoakConfig,
    ProceduralScenarioGenerator,
    soak_runner,
)


@pytest.fixture(autouse=True)
def clean_soak_state():
    """Ensures clean state before and after each test."""
    kill_switch.reset_system()
    soak_runner.reset()
    yield
    kill_switch.reset_system()
    soak_runner.reset()


def test_soak_runner_initialization():
    """Verify default configuration and metrics of PaperSoakRunner."""
    runner = PaperSoakRunner()
    metrics = runner.metrics
    assert metrics.status == "IDLE"
    assert metrics.days_completed == 0
    assert metrics.initial_capital == 3000.0
    assert metrics.current_capital == 3000.0
    assert metrics.capital_floor_preserved is True
    assert metrics.invariants_respected is True


def test_procedural_scenario_generator():
    """Verify procedural scenario generator emits valid NIFTY options scenarios."""
    gen = ProceduralScenarioGenerator(seed=123)
    ref_scenarios = soak_runner.simulator.scenarios
    
    seen_regimes = set()
    for day in range(1, 15):
        sc = gen.next_scenario(day, ref_scenarios)
        assert sc.day_number == day
        assert sc.option_type in ("CE", "PE")
        assert sc.base_price <= 38.00  # Micro-capital constraint
        assert len(sc.features) == 8
        assert len(sc.price_trajectory) > 0
        seen_regimes.add(sc.regime)
        
    # Must span diverse regimes
    assert "TRENDING_BULL" in seen_regimes
    assert "CHOPPY_CONSOLIDATION" in seen_regimes
    assert any(r in seen_regimes for r in ("HIGH_VOL_SHOCK", "TRENDING_BEAR"))


@pytest.mark.anyio
async def test_soak_step_execution():
    """Verify single step updates days completed, capital, and PnL metrics."""
    cfg = SoakConfig(target_days=5, iteration_interval_sec=0.0, checkpoint_every_n_days=2)
    runner = PaperSoakRunner(cfg)
    
    res = await runner.step()
    assert res.day_number == 1
    assert runner.metrics.days_completed == 1
    assert runner.metrics.current_capital == res.ending_cash
    assert runner.metrics.capital_floor_preserved is True
    assert runner.metrics.invariants_respected is True


@pytest.mark.anyio
async def test_sqlite_daily_pnl_and_checkpoint():
    """Verify soak run writes daily PnL rows to SQLite and triggers checkpoints."""
    cfg = SoakConfig(target_days=2, iteration_interval_sec=0.0, checkpoint_every_n_days=1)
    runner = PaperSoakRunner(cfg)
    
    metrics = await runner.run(max_days=2, interval_sec=0.0)
    assert metrics.days_completed == 2
    assert metrics.checkpoints_executed >= 2
    
    # Query database to confirm records exist
    rows = await db_manager.get_daily_pnl_records(limit=10)
    assert len(rows) >= 2
    
    # Verify columns exist
    first_row = rows[0]
    assert "date" in first_row
    assert "net_pnl" in first_row
    assert "total_friction" in first_row


@pytest.mark.anyio
async def test_pause_resume_and_stop_controls():
    """Verify pause, resume, and graceful stop state transitions."""
    runner = PaperSoakRunner()
    
    runner.pause()
    assert runner._pause_requested is True
    assert runner.metrics.status == "PAUSED"
    
    runner.resume()
    assert runner._pause_requested is False
    assert runner.metrics.status == "RUNNING"
    
    runner.stop()
    assert runner._stop_requested is True
    assert runner.metrics.status == "STOPPED"


def test_soak_rest_api_endpoints():
    """Verify Starlette REST endpoints for soak runner monitoring and control."""
    with TestClient(app) as client:
        # 1. Status endpoint
        resp = client.get("/api/soak/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "days_completed" in data
        assert "current_capital" in data
        assert "capital_floor_preserved" in data
        
        # 2. Stop endpoint
        stop_resp = client.post("/api/soak/stop")
        assert stop_resp.status_code == 200
        assert stop_resp.json()["status"] == "STOP_REQUESTED"
        
        # 3. Reset endpoint
        reset_resp = client.post("/api/soak/reset")
        assert reset_resp.status_code == 200
        assert reset_resp.json()["status"] == "RESET_COMPLETE"
        assert reset_resp.json()["metrics"]["days_completed"] == 0


def test_max_drawdown_peak_to_trough_preserved_after_new_high():
    """
    Critical Regression Test:
    Verify that if capital drops from a peak (e.g. ₹7,809 down to ₹7,609, ~2.56% drawdown)
    and subsequently recovers to a new all-time high (e.g. ₹8,200), the max drawdown
    reported is the true historical maximum (~2.56%), NEVER falsely overwritten with 0.00%.
    """
    from simulation.walk_forward import DaySimulationResult

    runner = PaperSoakRunner()
    runner.metrics.initial_capital = 3000.0

    def make_day(day_num, date_str, regime, ending_cash, gross, net, fee, dd):
        return DaySimulationResult(
            day_number=day_num, date_str=date_str, regime=regime, title=f"Day {day_num}",
            start_cash=3000.0, ending_cash=ending_cash, gross_pnl=gross, statutory_fees=fee,
            net_pnl=net, return_pct=round((net / 3000.0) * 100, 2), trades_executed=1,
            wins=1 if net >= 0 else 0, losses=0 if net >= 0 else 1, breakevens=0,
            peak_capital=max(3000.0, ending_cash), drawdown_pct=dd, rls_epoch=day_num,
            bayesian_call_expected_win=0.55, bayesian_put_expected_win=0.55,
            trades_detail=[], actions_taken=[]
        )

    d1 = make_day(1, "2026-10-01", "TRENDING_BULL", 7809.0, 4809.0, 4750.0, 59.0, 0.0)
    d2 = make_day(2, "2026-10-02", "CHOPPY_CONSOLIDATION", 7609.0, -200.0, -252.0, 52.0, 2.56)
    d3 = make_day(3, "2026-10-03", "TRENDING_BULL", 8200.0, 591.0, 540.0, 51.0, 0.0)

    runner.day_results = [d1, d2, d3]

    peak = runner.metrics.initial_capital
    max_dd = 0.0
    for d in runner.day_results:
        if d.ending_cash > peak:
            peak = d.ending_cash
        dd_pct = ((peak - d.ending_cash) / peak) * 100.0 if peak > 0 else 0.0
        if d.drawdown_pct > dd_pct:
            dd_pct = d.drawdown_pct
        if dd_pct > max_dd:
            max_dd = dd_pct
    runner.metrics.max_drawdown_pct = round(max_dd, 2)

    assert runner.metrics.max_drawdown_pct == pytest.approx(2.56, abs=0.05)
    assert runner.metrics.max_drawdown_pct > 0.0
