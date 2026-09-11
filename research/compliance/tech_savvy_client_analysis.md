# TECH-SAVVY CLIENT REGULATORY ANALYSIS

**Author:** Agent 1 — Regulatory & Compliance Lead  
**Date:** 2026-09-11

---

## 1. THE "TECH-SAVVY INVESTOR" EXEMPTION BOUNDARY

Historically, Indian brokers permitted "tech-savvy investors" to build personal algorithms via open REST APIs without full institutional exchange empanelment. Under the April 2026 framework, this exemption is strictly circumscribed:

### What Is Permitted for a Tech-Savvy Client:
1. Writing custom code (Python, C++, Rust) to analyze market data.
2. Executing trades **exclusively in one's own registered demat/trading account**.
3. Hosting algorithms on private servers, home PCs, or dedicated cloud virtual machines.
4. Using White-Box execution strategies (disclosed logic).

### What Is NOT Exempt (Common False Assumptions):
* **Myth 1: "I am tech-savvy, so I don't need Static IP."** -> **FALSE.** Brokers mandate static IP for all API order placement regardless of user skill level.
* **Myth 2: "I can bypass broker RMS order rate limits."** -> **FALSE.** Exchange-level OPS (orders per second) and price validation checks are strictly enforced.
* **Myth 3: "I can trade for my friends or family."** -> **FALSE.** Trading on behalf of another individual without Portfolio Management Service (PMS) or broker sub-broker registration is a criminal regulatory violation.

**CONFIDENCE LEVEL: CONFIRMED.**
