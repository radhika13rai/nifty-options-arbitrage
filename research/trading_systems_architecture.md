# TRADING SYSTEMS & EXECUTION ARCHITECTURE SPECIFICATION

**Author:** Agent 3 — Trading Systems & Execution Lead  
**Date:** 2026-09-11  
**Architecture Paradigm:** Clean Architecture, Dependency Inversion, Broker-Agnostic, Fail-Closed

---

## 1. CORE ARCHITECTURAL DIAGRAM

```
                       [ NSE / BROKER WEBSOCKET FEED ]
                                      |
                                      v
                       [ MarketDataConsumer (Async) ]
                                      |
                       [ MarketDataNormalizer & Orderbook ]
                         (Timestamp: Receipt, Normalized)
                                      |
              +-----------------------+-----------------------+
              |                                               |
              v                                               v
     [ Real-Time Strategy Engine ]                 [ Stale Data Guard ]
     - Volatility Breakout (OTM)                   - Threshold: 1,500ms
     - Mispricing Monitor (Parity/Spread)          - Halts if breached
              |                                               |
              v                                               v
     [ Candidate Signal ] -----------------------> [ Pre-Trade Risk Engine ]
                                                   - Max Loss per Trade: ₹150
                                                   - Max Daily Loss: ₹300
                                                   - Capital Limit: ₹3,000
                                                   - Rate Throttling: 2 OPS
                                                              |
                                                              v (RISK APPROVED)
                                                   [ Execution Router ]
                                                              |
                                        +---------------------+---------------------+
                                        |                                           |
                                        v                                           v
                              [ PaperBroker (ACTIVE) ]                 [ LiveBroker (PERMANENTLY ]
                              - Orderbook Depth Queue Check             [ DISABLED / GATED IN V1) ]
                              - Spread Crossing Penalty                             |
                              - Realistic Slippage & Fees                           X (NO ACCESS)
                                        |
                                        v
                            [ SQLite / Postgres Repository ]
                            - Immutable Audit Journal
                            - Positions & Trade Log
                                        |
                                        v
                            [ FastAPI WebSocket / REST ]
                                        |
                   +--------------------+--------------------+
                   |                                         |
                   v                                         v
         [ Android Phone 1: Main HUD ]             [ Android Phone 2: Health Monitor ]
```

---

## 2. BROKER ABSTRACTION CONTRACTS (INTERFACES)

The strategy and execution pipelines must NEVER directly couple to Dhan, Zerodha, or any specific vendor. All interactions are governed by strict abstract base classes in Python:

1. `MarketDataProvider`: Abstract async generator yielding normalized tick objects.
2. `InstrumentProvider`: Master lookup for strike intervals, expiry calendar, and token IDs.
3. `ExecutionProvider`: Dual-stage execution contract (`place_order`, `cancel_order`, `get_order_status`).
4. `PaperExecutionProvider`: Concrete simulation engine executing against virtual orderbook depth.
5. `RiskProvider`: Strict pre-trade validation gate verifying margin, rate limits, and drawdown.

---

## 3. FAIL-CLOSED ARCHITECTURAL INVARIANTS

1. **Stale Data Invariant:** If `now() - last_tick_timestamp > 1500ms`, trading state immediately locks to `TRADING_HALTED`. No new positions are permitted.
2. **Loss Cap Invariant:** If cumulative daily loss exceeds ₹300.00 (10% of starting capital), system triggers emergency kill-switch and liquidates open paper inventory.
3. **No Hidden Live Path:** `live_broker_disabled.py` explicitly raises `NotImplementedError("Live execution is strictly disabled in V1.")` if invoked by any subsystem.

**CONFIDENCE LEVEL: CONFIRMED.**
