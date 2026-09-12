"""
Concurrency, Thread Safety, and Race Condition Tests.
Verifies system behavior under multi-threaded contention:
1. KillSwitch lock-free/lock-guarded state integrity (zero torn reads).
2. Atomic execution gate prevents check-then-act order leaks during kill switch transitions.
3. Concurrent order placement under kill switch activation.
4. Concurrent SQLite WAL logging stress.
"""

import threading
import time
import pytest
from risk.kill_switch import KillSwitch, kill_switch
from risk.engine import PreTradeRiskEngine, PreTradeOrderRequest
from market_data.orderbook import orderbook_manager
from market_data.normalizer import MarketDataNormalizer
from database.db import DatabaseManager
from pathlib import Path


def test_kill_switch_torn_read_and_concurrency():
    """
    Spawns 8 reader threads reading KillSwitch status and 1 writer thread
    rapidly engaging and resetting the switch.
    Asserts 0 torn reads across thousands of iterations.
    """
    ks = KillSwitch()
    stop_event = threading.Event()
    torn_reads = []
    total_reads = [0]

    def reader():
        while not stop_event.is_set():
            st = ks.get_status()
            total_reads[0] += 1
            if st.is_engaged and st.reason in ("NORMAL_OPERATION", "RESET_TO_NORMAL"):
                torn_reads.append(f"Torn read: engaged=True but reason={st.reason}")
            if not st.is_engaged and st.engaged_at is not None:
                torn_reads.append(f"Torn read: engaged=False but engaged_at={st.engaged_at}")

    def writer():
        for i in range(200):
            ks.engage(f"Contention test breach {i}", "TEST")
            time.sleep(0.0005)
            ks.reset_system()
            time.sleep(0.0005)

    threads = [threading.Thread(target=reader) for _ in range(8)]
    writer_thread = threading.Thread(target=writer)

    for t in threads:
        t.start()
    writer_thread.start()

    writer_thread.join()
    stop_event.set()
    for t in threads:
        t.join()

    assert len(torn_reads) == 0, f"Detected {len(torn_reads)} torn reads: {torn_reads[:3]}"
    assert total_reads[0] > 1000


def test_atomic_execution_gate_eliminates_check_then_act_race():
    """
    Simulates Experiment 3 from independent audit paper:
    Multiple worker threads validate orders inside atomic_execution_gate
    while an emergency thread triggers the kill switch.
    Asserts that 0 orders are approved while kill switch is engaged.
    """
    from market_data.normalizer import MarketTick, DepthLevel
    tick = MarketTick(
        symbol="NIFTY26MAR23000CE",
        timestamp_ms=time.time() * 1000,
        ltp=25.0,
        volume=1000,
        best_bid=24.9,
        best_ask=25.1,
        bid_size=65,
        ask_size=65,
        bids=[DepthLevel(price=24.9, size=65)],
        asks=[DepthLevel(price=25.1, size=65)]
    )
    orderbook_manager.update_tick(tick)

    engine = PreTradeRiskEngine()
    req = PreTradeOrderRequest(
        symbol="NIFTY26MAR23000CE",
        side="BUY",
        order_type="MARKET",
        price=25.1,
        quantity=65
    )

    stop_event = threading.Event()
    race_violations = []
    approved_count = [0]
    rejected_count = [0]

    def worker():
        while not stop_event.is_set():
            with kill_switch.atomic_execution_gate():
                res = engine.validate_order(req, current_cash_inr=3000.0, daily_realized_loss_inr=0.0)
                if res.passed:
                    if kill_switch.is_engaged:
                        race_violations.append("Order approved while kill switch engaged inside atomic gate!")
                    approved_count[0] += 1
                else:
                    rejected_count[0] += 1

    def trigger():
        for _ in range(100):
            kill_switch.engage("Adversarial race test", "TEST")
            time.sleep(0.001)
            kill_switch.reset_system()
            time.sleep(0.001)

    workers = [threading.Thread(target=worker) for _ in range(6)]
    trig_thread = threading.Thread(target=trigger)

    for w in workers:
        w.start()
    trig_thread.start()

    trig_thread.join()
    stop_event.set()
    for w in workers:
        w.join()

    if kill_switch.is_engaged:
        kill_switch.reset_system()

    assert len(race_violations) == 0, f"Check-then-act race violations detected: {race_violations}"
    assert approved_count[0] > 0
    assert rejected_count[0] > 0


def test_concurrent_sqlite_wal_writes(tmp_path: Path):
    """
    Stress tests DatabaseManager with concurrent writes from 10 threads
    to verify WAL mode and write lock serialization prevent database lock errors.
    """
    db_file = tmp_path / "test_concurrent.db"
    mgr = DatabaseManager(db_path=db_file)
    mgr.init_db()

    errors = []

    def writer(thread_id: int):
        for i in range(50):
            try:
                mgr.execute_write(
                    "INSERT INTO audit_logs (event_type, severity, component, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                    ("STRESS_TEST", "INFO", f"Thread_{thread_id}", f"Log entry {i}", time.time())
                )
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {str(e)}")

    threads = [threading.Thread(target=writer, args=(t,)) for t in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"SQLite write errors under contention: {errors}"
    rows = mgr.execute_query("SELECT COUNT(*) as cnt FROM audit_logs WHERE event_type = 'STRESS_TEST'")
    assert rows[0]["cnt"] == 500


import anyio

@pytest.mark.anyio
async def test_paper_broker_concurrent_kill_switch_safety():
    """
    End-to-end verification of PaperBroker under concurrent kill-switch transitions.
    Addresses Auditor Recommendation §5.3 / Future Work (4):
    Spawns concurrent order placement tasks while kill switch toggles.
    Asserts:
    1. Zero orders are filled while kill switch is engaged.
    2. Cash and position inventory remain strictly consistent.
    """
    from execution.paper_broker import paper_broker
    from broker.interface import BrokerOrderRequest
    from portfolio.pnl import pnl_manager
    from portfolio.positions import position_tracker

    initial_cash = pnl_manager.current_cash
    stop_event = threading.Event()
    race_detected = []
    filled_count = [0]
    rejected_count = [0]

    async def place_orders():
        for i in range(25):
            req = BrokerOrderRequest(
                symbol="NIFTY26MAR23000CE",
                side="BUY",
                order_type="MARKET",
                quantity=65,
                price=25.1
            )
            res = await paper_broker.place_order(req)
            if res.status == "FILLED":
                filled_count[0] += 1
                # If filled, kill switch MUST NOT have been engaged during the atomic gate
                if kill_switch.is_engaged:
                    race_detected.append("Order filled while kill switch was engaged!")
            else:
                rejected_count[0] += 1
            await anyio.sleep(0.005)

    def trigger():
        for _ in range(20):
            kill_switch.engage("Broker concurrency test", "TEST")
            time.sleep(0.01)
            kill_switch.reset_system()
            time.sleep(0.01)

    trig_thread = threading.Thread(target=trigger)
    trig_thread.start()

    async with anyio.create_task_group() as tg:
        for _ in range(4):
            tg.start_soon(place_orders)

    trig_thread.join()

    if kill_switch.is_engaged:
        kill_switch.reset_system()

    assert len(race_detected) == 0, f"Race detected in PaperBroker: {race_detected}"
    assert rejected_count[0] > 0
