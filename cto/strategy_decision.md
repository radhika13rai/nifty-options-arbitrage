# CTO STRATEGY SELECTION & QUANTITATIVE MANDATE

**Author:** Chief Technology Officer (CTO)  
**Date:** 2026-09-11

---

1. **Approved for V1 Implementation:**
   - **Strategy 01: Intraday Volatility Breakout (OTM Long):** Buys low-premium NIFTY options (< ₹40 premium, cost < ₹2,600) upon confirmed 15-minute range expansion and volume surge. Target >= 1:2.5 risk-to-reward. Max risk: ₹150 per trade.
   - **Strategy 02: Real-Time Mispricing Monitor (Theoretical Parity Tracker):** Tracks theoretical put-call parity dislocations and displays them on the dashboard as a research benchmark, flagging them as `CAPITAL_INFEASIBLE` for execution.

2. **Rejected from V1 Implementation:**
   - Box Spreads, Synthetic Futures, and Conversions/Reversals (Requires > ₹1.2 Lakh capital).
