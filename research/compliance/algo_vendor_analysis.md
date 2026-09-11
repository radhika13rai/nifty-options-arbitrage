# ALGO VENDOR & SOFTWARE DISTRIBUTION ANALYSIS

**Author:** Agent 1 — Regulatory & Compliance Lead  
**Date:** 2026-09-11

---

## 1. SCENARIO RISK MATRIX

| Scenario | Legal Status | Regulatory Requirements | Allowed in This Project? |
| :--- | :--- | :--- | :--- |
| **A. Personal Paper Research** | Completely Unrestricted | None | **YES (V1 Scope)** |
| **B. Personal Live Trading** | Permitted under Retail Rules | Broker API terms, Static IP, Personal funds | Future Stage C (After Gate) |
| **C. Distributing Open-Source Code** | Permitted with strict disclaimer | MIT/Apache License, No trade execution | YES (Code only, no services) |
| **D. Hosted Web SaaS / Bot** | **STRICTLY REGULATED** | Broker partnership, SEBI RA registration | **NO** |
| **E. Trading Signal Service** | **STRICTLY REGULATED** | SEBI Research Analyst registration | **NO** |
| **F. Executing for Third Parties** | **ILLEGAL** without PMS/Broker license | SEBI PMS / Broker license, Exchange empanelment | **NO** |
| **G. Multi-broker Account Aggregator** | **STRICTLY REGULATED** | Principal-agent broker agreement | **NO** |

---

## 2. BINDING POLICY FOR REPOSITORY
The `nifty-options-arbitrage` codebase is explicitly designed as an **internal research engine**. Any attempt to add multi-user authentication, billing, signal distribution, or third-party credential management is an immediate architectural violation.

**CONFIDENCE LEVEL: CONFIRMED.**
