"""
Unit Tests for Automated Model Drift & Overfitting Guard (Paper V2).
Validates Out-of-Sample (OOS) drift detection, consecutive loss streaks,
and automatic rollback to verified conservative baseline weights.
"""

import pytest
from ml.drift_guard import ModelDriftGuard
from ml.learner import learning_engine


@pytest.fixture
def fresh_guard():
    guard = ModelDriftGuard(
        window_size=20,
        baseline_win_rate=0.65,
        baseline_sharpe=2.0,
        min_trades_for_eval=5,
        max_consecutive_losses=3
    )
    guard.reset()
    learning_engine.reset()
    return guard


def test_healthy_performance_no_drift(fresh_guard):
    # 5 consecutive winning trades
    for _ in range(5):
        fresh_guard.record_trade(net_pnl=380.0, gross_pnl=430.0, points_moved=6.6)

    status = fresh_guard.check_drift()
    assert status.is_drift_detected is False
    assert status.rolling_win_rate == 1.0
    assert status.consecutive_losses == 0
    assert status.total_trades_analyzed == 5


def test_win_rate_collapse_triggers_drift(fresh_guard):
    # 1 win, then 5 losses
    fresh_guard.record_trade(net_pnl=100.0, gross_pnl=150.0, points_moved=2.3)
    for _ in range(5):
        fresh_guard.record_trade(net_pnl=-190.0, gross_pnl=-140.0, points_moved=-2.1)

    status = fresh_guard.check_drift()
    assert status.is_drift_detected is True
    assert status.rolling_win_rate <= 0.20
    assert any("below 40.0%" in r for r in status.drift_reasons)


def test_consecutive_loss_streak_triggers_alert(fresh_guard):
    # 3 consecutive losses
    fresh_guard.record_trade(net_pnl=-150.0, gross_pnl=-100.0, points_moved=-1.5)
    fresh_guard.record_trade(net_pnl=-150.0, gross_pnl=-100.0, points_moved=-1.5)
    assert fresh_guard.consecutive_losses == 2
    assert fresh_guard.check_drift().is_drift_detected is False

    fresh_guard.record_trade(net_pnl=-150.0, gross_pnl=-100.0, points_moved=-1.5)
    assert fresh_guard.consecutive_losses == 3
    status = fresh_guard.check_drift()
    assert status.is_drift_detected is True
    assert any("Loss streak alert" in r for r in status.drift_reasons)


@pytest.mark.anyio
async def test_evaluate_and_enforce_executes_rollback(fresh_guard):
    # Modify weights artificially
    learning_engine.rls.w = [99.0, -99.0, 50.0, -50.0, 10.0, 10.0, 10.0, 10.0]
    
    # Induce 3 consecutive losses
    for _ in range(3):
        fresh_guard.record_trade(net_pnl=-150.0, gross_pnl=-100.0, points_moved=-1.5)

    status = await fresh_guard.evaluate_and_enforce()
    assert status.is_drift_detected is True
    assert status.rollback_triggered is True

    # Check that weights were rolled back to conservative defaults
    assert learning_engine.rls.w[0] == 1.8
    assert learning_engine.rls.w[1] == 1.2
    assert fresh_guard.rollback_count == 1
