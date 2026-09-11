# QUANTITATIVE MODEL ASSUMPTIONS REGISTER

**Author:** Agent 2 — Quantitative Research Lead  
**Date:** 2026-09-11

---

1. **Lot Size Assumption:** 1 lot NIFTY = 65 contracts (Per NSE Circular No. NSE/FAOP/70616).
2. **Execution Latency:** Average round-trip API network latency is modeled at **45.0 ms** (realistic for high-performance cloud VPS to Mumbai broker datacenter).
3. **Slippage Parameter:** Slippage is modeled stochastically with a minimum threshold of 0.20 index points on normal market conditions, escalating to 1.50 points during news spikes.
4. **Risk-Free Interest Rate ($r$):** 6.75% annualized (derived from current Reserve Bank of India 91-day Treasury Bill yields).
5. **Dividend Yield ($q$):** 1.20% annualized for NIFTY 50 index basket.
