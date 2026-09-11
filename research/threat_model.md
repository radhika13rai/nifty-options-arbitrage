# THREAT MODEL & ATTACK SURFACE ANALYSIS

**Author:** Agent 4 — Security & Risk Lead  
**Date:** 2026-09-11

---

## STRIDE THREAT MATRIX

1. **Spoofing:** Fake tick data injection over unencrypted WebSockets.
   * *Countermeasure:* Mandatory TLS (WSS) and signature verification.
2. **Tampering:** Modifying risk limits in configuration memory.
   * *Countermeasure:* Immutable Pydantic Settings with read-only runtime properties.
3. **Repudiation:** Denying that an order was issued.
   * *Countermeasure:* SQLite Write-Ahead Logging (WAL) with nanosecond timestamps.
4. **Information Disclosure:** Exposing trading logs to public endpoints.
   * *Countermeasure:* FastAPI endpoints bound strictly to internal authenticated networks.
5. **Denial of Service:** Flooding API with simulated orders.
   * *Countermeasure:* Token-bucket rate limiting at 2 OPS.
6. **Elevation of Privilege:** Enabling live trading without human approval.
   * *Countermeasure:* Hardcoded compile-time `LIVE_TRADING = DISABLED` flag.
