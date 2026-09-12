"""
Unit tests for Adversarial Stress Testing & Downside Invariant Verification.
Tests:
  1. Consecutive loss streak triggering automatic Model Drift Guard rollback
  2. Capital floor breach triggering latching Emergency Kill Switch
  3. Pre-trade risk gate hard-rejecting all orders while kill switch is engaged
  4. Cryptographic token security (invalid password fails, CONFIRM_RESET succeeds)
  5. SQLite risk event logging and audit trails
"""

import pytest
from risk.kill_switch import kill_switch
from simulation.stress_test import AdversarialStressTester


@pytest.fixture(autouse=True)
def clean_system_state():
    """Ensures clean kill switch and risk state before and after each test."""
    kill_switch.reset("CONFIRM_RESET")
    yield
    kill_switch.reset("CONFIRM_RESET")


@pytest.mark.anyio
async def test_full_adversarial_stress_suite():
    """Runs the 4-phase stress suite and verifies 100% invariant compliance."""
    tester = AdversarialStressTester(initial_capital=3000.0, capital_floor=2000.0)
    report = await tester.run_adversarial_suite(verbose=False)

    assert report.all_invariants_held is True
    assert report.phase1_drift_rollback_verified is True
    assert report.phase2_kill_switch_engaged_verified is True
    assert report.phase3_order_blocking_verified is True
    assert report.phase4_token_recovery_verified is True
    assert report.rollback_count >= 1
    assert report.consecutive_losses_observed == 0  # Reset after rollback
    assert report.risk_events_recorded >= 1
    assert report.audit_events_recorded >= 1


@pytest.mark.anyio
async def test_kill_switch_tamper_proofing():
    """Verify that kill switch cannot be reset with arbitrary tokens."""
    kill_switch.engage("Tamper test breach", "TEST_RUNNER")
    assert kill_switch.is_engaged is True

    # Invalid tokens must raise ValueError
    for invalid in ["password", "admin", "1234", "confirm_reset", "RESET"]:
        with pytest.raises(ValueError):
            kill_switch.reset(invalid)
        assert kill_switch.is_engaged is True

    # Valid token unlocks
    kill_switch.reset("CONFIRM_RESET")
    assert kill_switch.is_engaged is False
