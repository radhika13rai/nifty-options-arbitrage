"""
Pytest Fixtures and Lifecycle Setup.
Ensures clean state for kill switch and SQLite database before each test.
"""

import pytest
from database.db import db_manager
from risk.kill_switch import kill_switch
from portfolio.pnl import pnl_manager
from config import config


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Resets database, kill switch, portfolio, and auto execution engine before each test execution."""
    db_manager.init_db()
    if kill_switch.is_engaged:
        kill_switch.reset_system()
    pnl_manager.reset_balance(config.initial_capital_inr)
    from portfolio.positions import position_tracker
    from execution.auto_engine import auto_engine
    position_tracker.reset()
    auto_engine._active_trades.clear()
    auto_engine._trade_history.clear()
    yield
    if kill_switch.is_engaged:
        kill_switch.reset_system()
    position_tracker.reset()
    auto_engine._active_trades.clear()

