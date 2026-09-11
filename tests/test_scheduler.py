"""Unit tests for Market-Hours Scheduler & Intraday Routine."""
import asyncio
import datetime
import pytest
from scheduler.daily_routine import MarketRoutineScheduler, MarketPhase
from global_macro.poller import live_macro_poller


def test_ist_phase_clock_determination():
    sched = MarketRoutineScheduler()

    # Create weekday timestamps (Monday: 2026-09-14)
    # 09:05 IST
    dt_pre = datetime.datetime(2026, 9, 14, 9, 5, 0)
    assert sched.determine_current_phase(dt_pre) == MarketPhase.PRE_MARKET_OPEN

    # 10:15 IST
    dt_morning = datetime.datetime(2026, 9, 14, 10, 15, 0)
    assert sched.determine_current_phase(dt_morning) == MarketPhase.MORNING_BREAKOUT

    # 12:15 IST
    dt_lunch = datetime.datetime(2026, 9, 14, 12, 15, 0)
    assert sched.determine_current_phase(dt_lunch) == MarketPhase.MIDDAY_STAND_DOWN

    # 14:00 IST
    dt_afternoon = datetime.datetime(2026, 9, 14, 14, 0, 0)
    assert sched.determine_current_phase(dt_afternoon) == MarketPhase.AFTERNOON_SESSION

    # 15:20 IST
    dt_sq = datetime.datetime(2026, 9, 14, 15, 20, 0)
    assert sched.determine_current_phase(dt_sq) == MarketPhase.MANDATORY_SQUARE_OFF

    # 15:45 IST
    dt_post = datetime.datetime(2026, 9, 14, 15, 45, 0)
    assert sched.determine_current_phase(dt_post) == MarketPhase.POST_MARKET_LEARN

    # 20:00 IST (Off-hours)
    dt_night = datetime.datetime(2026, 9, 14, 20, 0, 0)
    assert sched.determine_current_phase(dt_night) == MarketPhase.MARKET_CLOSED

    # Saturday: 2026-09-19 10:00 IST
    dt_sat = datetime.datetime(2026, 9, 19, 10, 0, 0)
    assert sched.determine_current_phase(dt_sat) == MarketPhase.MARKET_CLOSED


def test_scheduler_lifecycle_transitions():
    async def _run():
        sched = MarketRoutineScheduler()
        sched.set_simulated_mode(True)
        live_macro_poller.enable_mock_mode(True)

        # 1. Transition to PRE_MARKET_OPEN
        t1 = await sched.execute_phase_transition(MarketPhase.PRE_MARKET_OPEN)
        assert t1["to"] == "PRE_MARKET_OPEN"
        assert "POLL_MACRO_AND_RSS" in t1["actions"]
        assert sched.is_trading_permitted is False

        # 2. Transition to MORNING_BREAKOUT
        t2 = await sched.execute_phase_transition(MarketPhase.MORNING_BREAKOUT)
        assert t2["to"] == "MORNING_BREAKOUT"
        assert "ENABLE_AUTO_EXECUTION" in t2["actions"]
        assert sched.is_trading_permitted is True

        # 3. Transition to MIDDAY_STAND_DOWN
        t3 = await sched.execute_phase_transition(MarketPhase.MIDDAY_STAND_DOWN)
        assert t3["to"] == "MIDDAY_STAND_DOWN"
        assert "STAND_DOWN_PAUSE_NEW_ENTRIES" in t3["actions"]
        assert sched.is_trading_permitted is False

        # 4. Transition to AFTERNOON_SESSION
        t4 = await sched.execute_phase_transition(MarketPhase.AFTERNOON_SESSION)
        assert t4["to"] == "AFTERNOON_SESSION"
        assert sched.is_trading_permitted is True

        # 5. Transition to MANDATORY_SQUARE_OFF
        t5 = await sched.execute_phase_transition(MarketPhase.MANDATORY_SQUARE_OFF)
        assert t5["to"] == "MANDATORY_SQUARE_OFF"
        assert "EXECUTE_1515_SQUARE_OFF" in t5["actions"]
        assert sched.is_trading_permitted is False

        # 6. Transition to POST_MARKET_LEARN
        t6 = await sched.execute_phase_transition(MarketPhase.POST_MARKET_LEARN)
        assert t6["to"] == "POST_MARKET_LEARN"
        assert "RUN_WALK_FORWARD_ADAPTATION" in t6["actions"]
        assert "adaptation_epoch" in t6

        # Verify status report
        status = sched.get_status()
        assert status["current_phase"] == "POST_MARKET_LEARN"
        assert "IST" in status["ist_time"]
        assert len(status["phase_history"]) >= 6

    asyncio.run(_run())
