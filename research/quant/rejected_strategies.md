# REJECTED STRATEGIES REGISTER

**Author:** Agent 2 — Quantitative Research Lead  
**Date:** 2026-09-11

---

### Strategy: Pure Put-Call Parity Arbitrage
* **Rejection Reason 1:** `CAPITAL_INFEASIBLE`. Requires writing naked options and futures positioning requiring exchange SPAN margin of ₹1.4 Lakh to ₹1.8 Lakh.
* **Rejection Reason 2:** `LATENCY_UNCOMPETITIVE`. Co-located institutional algos consume parity dislocations in sub-millisecond windows. A retail API with 30ms latency will suffer 100% adverse selection.

### Strategy: Box Spread Arbitrage
* **Rejection Reason 1:** `CAPITAL_INFEASIBLE`. Requires 4 simultaneous legs, requiring > ₹1.5 Lakh margin.
* **Rejection Reason 2:** `EXECUTION_FAILURE_RISK`. Executing 4 distinct option legs sequentially across retail APIs guarantees "legging risk" where 2 legs fill and the other 2 legs miss, resulting in catastrophic unhedged exposure.
