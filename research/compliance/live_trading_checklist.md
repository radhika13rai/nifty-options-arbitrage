# LIVE TRADING PRE-FLIGHT COMPLIANCE CHECKLIST (STAGE C GATE)

**Author:** Agent 1 — Regulatory & Compliance Lead  
**Current Date:** 2026-09-11  
**Default System Status:** LIVE_TRADING = DISABLED (PAPER_TRADING ONLY)

---

All 18 compliance criteria below must be validated and signed off before any code may submit a live order:

- [ ] 1. Current SEBI Circular SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/0000013 compliance validated.
- [ ] 2. NSE Retail Algo Direct API implementation circular verified.
- [ ] 3. Broker (Dhan) Developer Agreement signed and in active standing.
- [ ] 4. Dedicated VPS with whitelisted Static Public IP deployed.
- [ ] 5. Primary and Secondary Static IP confirmed via `GET /v2/ip/getIP`.
- [ ] 6. OAuth 2.0 with TOTP 2FA daily session token pipeline verified.
- [ ] 7. Algo Identifier assigned and registered with Broker RMS.
- [ ] 8. Maximum Order-Per-Second (OPS) throttle hardcoded to <= 2 orders/sec.
- [ ] 9. Price band and Circuit Limit sanity checks integrated into pre-trade engine.
- [ ] 10. Maximum loss per day hard stop circuit-breaker verified.
- [ ] 11. Stale-data threshold guard set to <= 1500ms.
- [ ] 12. Local immutable audit logging to SQLite/Postgres verified.
- [ ] 13. System health watchdog and emergency kill-switch tested with simulated disconnection.
- [ ] 14. Comprehensive Paper-Trading evidence generated over >= 30 trading sessions.
- [ ] 15. Statistical positive net edge confirmed AFTER brokerage, STT, exchange, and slippage.
- [ ] 16. Security secrets scanner confirms zero plaintext API keys in repo or frontend.
- [ ] 17. Multi-agent adversarial review completed with zero open critical issues.
- [ ] 18. CTO explicit signed authorization token generated.

**CURRENT STATUS: FAILED / INCOMPLETE.** System remains strictly in `PAPER_TRADING` mode.
