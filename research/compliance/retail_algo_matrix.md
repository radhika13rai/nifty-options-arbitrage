# RETAIL ALGO REGULATORY & TECHNICAL MATRIX

**Author:** Agent 1 — Regulatory & Compliance Lead  
**Date:** 2026-09-11

---

## 1. CLASSIFICATION MATRIX

| Criteria | V1 Paper Trading (Current) | Tech-Savvy Retail API (Stage C) | Commercial Algo Vendor (Prohibited) |
| :--- | :--- | :--- | :--- |
| **Legal Classification** | Private Educational Research | Retail Algorithmic Client | Algo Software Vendor / Fintech |
| **SEBI Registration Needed?** | **NO** | **NO** (Client executes own funds) | **YES** (SEBI RA / IA / Broker Partner) |
| **Exchange Algo ID Required?** | **NO** | **YES** (Assigned via Broker) | **YES** (Formal Exchange Empanelment) |
| **Capital Source** | Simulated Virtual (₹3,000) | Personal Broker Account | Third-party client funds |
| **Order Route** | Internal Python Memory Simulator | Broker API -> Exchange RMS | Multi-client OMS / Tripartite Gateway |
| **Static IP Required?** | **NO** | **YES** (Broker Whitelisted) | **YES** (Leased Line / Broker Co-location) |
| **Audit Log Mandate** | Internal SQLite audit trail | 5-Year Broker Audit Trail | Comprehensive Statutory SEBI Audit |

---

## 2. GO / NO-GO COMPLIANCE CRITERIA

1. **Rule 1.1:** If any code connects to broker order endpoint without human approval -> **HALT SYSTEM**.
2. **Rule 1.2:** If multiple user accounts are detected -> **HALT SYSTEM**.
3. **Rule 1.3:** If marketing, signal broadcasting, or profit promises are detected -> **HALT SYSTEM**.

**CONFIDENCE LEVEL: CONFIRMED.**
