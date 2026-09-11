# FAILURE MODES & EFFECTS ANALYSIS (FMEA)

**Author:** Agent 4 — Security & Risk Lead  
**Date:** 2026-09-11

---

| Failure Mode | Severity | Probability | Detection Mechanism | System Reaction |
| :--- | :---: | :---: | :--- | :--- |
| **Market Data Stale / Hang** | HIGH | Medium | Tick Heartbeat Monitor (>1.5s) | Transition to `TRADING_HALTED` |
| **Legging Risk (One Leg Fills)** | CRITICAL | High | Execution state mismatch | Instant market stop on filled leg |
| **Database Disk Full** | HIGH | Low | SQLite write exception | Stop order engine; log error |
| **Phone Dashboard Disconnect** | LOW | High | WebSocket ping-pong failure | Engine continues unattended; no impact |
| **Extreme Flash Crash** | HIGH | Low | Circuit limit validator | Freeze trading; log circuit event |
