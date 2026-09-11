# EXCHANGE TEST ENVIRONMENT & SIMULATION FACILITIES

**Author:** Agent 1 — Regulatory & Compliance Lead  
**Date:** 2026-09-11

---

## 1. NSE TEST MARKET FACILITY (TMF)

* **Purpose:** NSE provides the Test Market Facility (TMF) and Saturday Mock Trading Sessions for registered brokers and empanelled software vendors.
* **Access Barrier for Retail:** Direct retail investor access to live TMF sockets is generally restricted to broker internal testing. Retail developers do not have direct leased-line access to NSE TMF.
* **Broker Simulation:** DhanHQ currently provides a sandbox environment with mock tick generation.
* **V1 Solution:** To ensure complete mathematical independence and reproducible verification, the project implements a **Local High-Precision Market Replay & Paper Engine** that consumes real historical tick-by-tick / minute options data and simulates orderbook queue physics.

**CONFIDENCE LEVEL: CONFIRMED.**
