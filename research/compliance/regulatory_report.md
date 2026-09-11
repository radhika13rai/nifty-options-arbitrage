# REGULATORY REPORT: SEBI & NSE RETAIL ALGO FRAMEWORK (2025-2026)

**Author:** Agent 1 — Regulatory & Compliance Lead  
**Date of Assessment:** 2026-09-11  
**Regulatory Horizon:** Post-April 1, 2026 Implementation  
**Jurisdiction:** Republic of India (SEBI / NSE / BSE)

---

## 1. EXECUTIVE SUMMARY & JURISPRUDENTIAL STATUS

As of September 2026, algorithmic trading in the Indian capital markets is governed by the landmark SEBI Circular **SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/0000013** dated February 4, 2025 (*'Safer participation of retail investors in Algorithmic trading'*), as amended and extended to full broker applicability from **April 1, 2026**.

The fundamental regulatory pivot of the 2025-2026 regime is the **elimination of unmonitored retail API trading**. Every automated order reaching an exchange engine must now be definitively classified, tagged with a unique exchange-assigned Algo ID, and routed through broker-controlled Risk Management Systems (RMS) under strict principal-agent liability.

```
+-------------------------------------------------------------------------+
|                  SEBI RETAIL ALGO REGULATORY LANDSCAPE                  |
+-------------------------------------------------------------------------+
|  Tier 1: Personal Paper Research (Current V1 Scope)                    |
|  - Zero exchange connectivity                                           |
|  - Zero broker order placement                                          |
|  - EXEMPT from NNF/Algo ID tagging (Reads market data only)             |
+-------------------------------------------------------------------------+
|  Tier 2: Direct Client Trading (Future Live Stage C Gate)               |
|  - Mandatory Static Public IP whitelisting                              |
|  - Exchange-approved NNF / Algo Identifier tag                          |
|  - Broker Pre-Trade Risk Controls (Price bands, OPS rate limits)        |
+-------------------------------------------------------------------------+
|  Tier 3: Multi-User / Algo Vendor / SaaS (Strictly Out of Scope)         |
|  - Mandatory Research Analyst (RA) or Investment Adviser (IA) license   |
|  - Exchange Strategy Approval per algo                                  |
|  - Broker-Vendor formal tripartite agreements                           |
+-------------------------------------------------------------------------+
```

---

## 2. CORE REGULATORY PILLARS (SEBI & NSE 2026)

### Pillar I: Mandatory Algo Categorization (White Box vs. Black Box)
* **White Box Execution Algos:** Strategies where complete execution logic, mathematical parameters, and triggers are disclosed to and controllable by the investor.
* **Black Box Algos:** Strategies where mathematical logic is obscured, proprietary, or non-replicable. Under SEBI rules, distributing Black Box algos to any third party mandates registration under SEBI (Research Analysts) Regulations, 2014.
* **Project Status:** This project is classified strictly as a **Personal White-Box Research System**. It is neither marketed nor distributed.

### Pillar II: Order Tagging & NNF Identification
* Every order submitted via automated interfaces must populate the Exchange Non-NEAT Frontend (NNF) flag.
* The order packet must carry the Broker-assigned Client Direct API Identifier and the Exchange Strategy ID.
* Orders without a valid registered Algo ID are rejected at the broker RMS layer prior to reaching the NSE matching engine.

### Pillar III: Static IP Whitelisting & 2FA Session Security
* Order-placement APIs require strict binding to registered static public IPs.
* API tokens are cryptographically bound to single-day sessions (maximum 24-hour lifetime).
* Unattended overnight persistence of trading authorizations without multi-factor authentication is prohibited.

---

## 3. COMPLIANCE VERDICT FOR V1

| Operational Domain | Status in V1 | Regulatory Mandate | Compliance Action Taken |
| :--- | :--- | :--- | :--- |
| **Market Data Consumption** | **ACTIVE** | Permitted via broker WebSocket / REST | Read-only market data feeds; no order placement |
| **Paper Execution** | **ACTIVE** | Unregulated internal simulation | Runs entirely in local SQLite memory; zero broker packets |
| **Live Order Placement** | **DISABLED** | Requires Exchange Algo ID & Static IP | Completely walled off behind compile-time disabled module |
| **Multi-User Access** | **DISABLED** | Requires SEBI RA/Broker Vendor status | Local single-tenant system; zero multi-tenant routes |

**CONFIDENCE LEVEL: CONFIRMED.** V1 paper research operates fully within legal, non-licensable boundaries.
