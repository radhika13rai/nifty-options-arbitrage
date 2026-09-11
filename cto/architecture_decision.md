# CTO ARCHITECTURE DECISION

**Author:** Chief Technology Officer (CTO)  
**Date:** 2026-09-11

---

1. **Decoupled Python Backend (Clean Architecture):**
   - Core runtime: Python 3.12+ with FastAPI, asyncio, and Pydantic v2.
   - Broker Abstraction: Strict interface separation (`MarketDataProvider`, `ExecutionProvider`).
   - Execution Provider: `PaperBroker` active by default; `LiveBrokerDisabled` raises `NotImplementedError`.

2. **Persistent Audit Logging:**
   - SQLite with WAL (Write-Ahead Logging) mode enabled for zero-latency write durability.
   - Comprehensive trade journals recording: signal timestamp, order timestamp, fill timestamp, slippage, brokerage, and statutory taxes.

3. **Android Client Dashboard:**
   - High-performance, dark-mode technical HUD accessible via local network browser.
   - Phone 1: Main Trading HUD (Positions, P&L, Signals, Equity Curve).
   - Phone 2: System Health & Opportunity Monitor (Latency, Heartbeats, Orderbook Depth, Kill-Switch).
