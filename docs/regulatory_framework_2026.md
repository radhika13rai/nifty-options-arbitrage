# SEBI Regulatory Framework for Retail Algorithmic Trading (2026)

## 1. Regulatory Context
As of **September 11, 2026**, the algorithmic trading landscape in India operates under the regulatory circular issued by SEBI on **February 4, 2025**, which came into full effect on **April 1, 2026**.

The framework introduces strict safeguards designed to protect retail investors from predatory algorithms, unchecked leverage, and broker API misuse.

---

## 2. Key Pillars of the 2026 Framework

### 2.1 Distinction: Tech-Savvy Clients vs. Vendor Algo Distribution
- **Tech-Savvy Direct API Users:** Individual traders writing bespoke algorithms for their own personal accounts are permitted to connect via broker-provided Open APIs, provided:
  1. The API connects from a verified static IP or registered device fingerprint.
  2. All orders carry appropriate order tags indicating algorithmic origination.
  3. Pre-trade risk controls (order quantity, price bands, rate limits) are validated on the broker edge.
- **Algo Vendors / SaaS Providers:** Any platform distributing trading strategies, copy-trading signals, or black-box execution to third-party retail clients must obtain explicit broker and exchange algorithmic approval, including unique Algo IDs and third-party security audits.

### 2.2 Broker API Architecture (Dhan & Zerodha)
- **Static IP Whitelisting:** DhanHQ v2 mandates a static public IP for all order-routing endpoints with a 7-day modification lock. Market data feeds (quotes and WebSockets) remain accessible dynamically.
- **Session Tokens:** API tokens expire after 24 hours and require daily re-authentication.
- **Fail-Safe Requirement:** Brokers must provide an instantaneous "Kill All Orders & Positions" API and manual web-portal override.

---

## 3. Compliance Implementation in This System

1. **Gating to Paper Trading Only in V1:** To guarantee 100% regulatory immunity during development and research, V1 strictly enforces `EXECUTION_MODE = PAPER_TRADING`. Live orders cannot be submitted.
2. **Audit Logging:** Every tick evaluation, order generation, pre-trade risk check, and fill is recorded into SQLite with microsecond timestamps and unique tracking IDs.
3. **Lot Size Alignment:** Automatically synchronized with NSE circular `NSE/FAOP/70616` (NIFTY lot size = 65).
