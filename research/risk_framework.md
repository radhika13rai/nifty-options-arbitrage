# QUANTITATIVE RISK MANAGEMENT FRAMEWORK

**Author:** Agent 4 — Security & Risk Lead  
**Date:** 2026-09-11

---

## 1. PRE-TRADE RISK CONTROL PARAMETERS

| Metric | Threshold | Action on Breach |
| :--- | :--- | :--- |
| **Max Capital Exposure** | ₹3,000.00 | Reject order; flag `MARGIN_EXCEEDED` |
| **Max Position Size** | 1 Lot (65 Qty) | Reject order; flag `MAX_LOT_REACHED` |
| **Max Loss Per Trade** | ₹150.00 (5% of cap) | Immediate market exit / Stop-loss hit |
| **Max Daily Cumulative Loss** | ₹300.00 (10% of cap) | Lock system for remainder of trading day |
| **Max Orders Per Second** | 2 Orders / sec | Throttle queue with 500ms delay |
| **Stale Data Threshold** | 1,500 milliseconds | Reject all entries; cancel active quotes |
| **Bid-Ask Spread Filter** | > 1.50 points | Reject entry; flag `EXCESSIVE_SPREAD` |
| **Min Depth Requirement** | < 100 Qty on Top-3 | Reject entry; flag `INSUFFICIENT_LIQUIDITY` |

---

## 2. EMERGENCY KILL-SWITCH PROTOCOL
* **Trigger Conditions:**
  1. Manual user override button on dashboard.
  2. Broker WebSocket disconnection lasting > 3.0 seconds.
  3. Cumulative daily drawdown reaching ₹300.00.
  4. Memory corruption or database integrity fault.
* **Execution Behavior:**
  1. Instantly transition system state to `KILL_SWITCH_ACTIVE`.
  2. Cancel all outstanding pending paper orders.
  3. Liquidate any open inventory at current best opposite quote.
  4. Halt all evaluation loops.
