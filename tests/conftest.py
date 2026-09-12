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
    """Resets database and kill switch before each test execution."""
    db_manager.init_db()
    if kill_switch.is_engaged:
        kill_switch.reset_system()
    pnl_manager.reset_balance(config.initial_capital_inr)
    yield
    if kill_switch.is_engaged:
        kill_switch.reset_system()
