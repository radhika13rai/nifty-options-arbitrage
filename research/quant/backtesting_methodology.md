# BACKTESTING METHODOLOGY & REALISM PROTOCOL

**Author:** Agent 2 — Quantitative Research Lead  
**Date:** 2026-09-11

---

## 1. PROTOCOL TO PREVENT BACKTEST ARTIFACTS

To ensure that backtest results are non-fictional and mathematically honest:

### Rule 1: Zero Look-Ahead Bias
Data bars must be ingested strictly via event-driven tick simulation. A candle/bar closing at $T$ is not visible to the strategy until $T + \Delta t_{\text{latency}}$.

### Rule 2: Realistic Fill Price vs. Signal Price
* When a strategy issues a `BUY` signal, the fill price is the **CURRENT BEST ASK** (never the LTP, never the bid, and never the mid-price).
* When a strategy issues a `SELL` signal, the fill price is the **CURRENT BEST BID**.
* An orderbook crossing penalty of at least 1 tick (0.05 pts) plus market impact is enforced.

### Rule 3: Liquidity & Lot Constraints
* Orders can only fill if the orderbook depth at the best quote is greater than or equal to the requested lot size (65 qty).
* If available depth is less than 65 qty, a partial fill or order rejection is logged.
