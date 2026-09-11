# UNRESOLVED REGULATORY & TECHNICAL QUESTIONS

**Author:** Agent 1 — Regulatory & Compliance Lead  
**Audit Date:** 2026-09-11

---

1. **Question:** What is the precise broker-level turn-around time for allocating unique Algo IDs to individual retail custom algorithms under the April 2026 SEBI rollout?
   * **Status:** REQUIRES BROKER DIRECT CLARIFICATION.
   * **Impact on V1:** Zero impact on Paper Trading; mandatory before Stage C.

2. **Question:** Does DhanHQ require periodic annual re-certification of retail algorithmic order logic?
   * **Status:** UNKNOWN / BROKER POLICY CONTINGENT.
   * **Mitigation:** Maintain full modular separation of strategy rules.

3. **Question:** Will NSE introduce sub-millisecond throttle penalties for retail client-direct API accounts exceeding 10 queries/second?
   * **Status:** LIKELY.
   * **Mitigation:** Rate-limiter is enforced at 2 OPS on the client side.

**CONFIDENCE LEVEL: CONFIRMED.**
