# NIFTY Options Arbitrage & Algorithmic Research Engine (V1)

[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Regulatory Framework](https://img.shields.io/badge/SEBI%20Retail%20Algo-Compliant%20(April%202026)-green.svg)](docs/regulatory_framework_2026.md)
[![Execution Mode](https://img.shields.io/badge/Mode-PAPER__TRADING__ONLY-crimson.svg)](config.py)
[![NIFTY Lot Size](https://img.shields.io/badge/NIFTY%20Lot%20Size-65-blueviolet.svg)](market_data/instruments.py)
[![Test Suite](https://img.shields.io/badge/Tests-26%20Passed-success.svg)](tests/)

A compliance-first, research-grade algorithmic trading and arbitrage analysis platform engineered for Indian equity derivatives (NSE NIFTY 50 options). Built under the active **SEBI Retail Algorithmic Trading Framework** (effective April 1, 2026) and exchange specifications (NSE Lot Size = **65**).

---

## 1. Executive Summary & Core Hypothesis

### The ₹3,000 Retail Capital Hypothesis
> **Hypothesis:** Can a retail trader execute risk-free options arbitrage (Put-Call Parity, Box Spreads, Synthetic Forwards) in the Indian derivatives market with an initial capital of ₹3,000?

### Findings & Mathematical Proof:
1. **Mathematical Refutation of Retail Arbitrage (`CAPITAL_INFEASIBLE`):**
   - True options arbitrage requires simultaneous long and short legs across options and underlying futures.
   - Under the NSE/SEBI SPAN + Exposure Margin framework, shorting an options leg or future requires approximately **₹1,20,000 to ₹1,50,000** in margin per lot.
   - Even with spread-offset benefits (e.g. Box Spreads), exchange portfolio margin rules require a minimum of **₹65,000 to ₹90,000** per 4-leg set.
   - **Conclusion:** Arbitrage is mathematically impossible with ₹3,000 capital. The system explicitly flags all multi-leg arbitrage signals as `CAPITAL_INFEASIBLE` and prohibits fictitious execution.

2. **Statutory Transaction Friction Drag:**
   - Under the 2026 statutory fee schedule (Brokerage ₹40 round trip + STT 0.1% sell + GST 18% + Exchange txn 0.05% + Stamp duty 0.003% + SEBI fee), total friction per executed round-trip trade on 1 lot (65 units) is approximately **₹52.00 to ₹117.00** depending on premium.
   - On a ₹2,000 capital allocation, this represents an immediate **2.6% to 5.8%** return hurdle before breakeven.

3. **Viable Research Strategy: Single-Leg OTM Volatility Breakout:**
   - The only mathematically viable options research strategy for ₹3,000 capital is buying single-leg low-premium out-of-the-money (OTM) options (< ₹38.00 per unit, outlay < ₹2,470 for 65 units).
   - Strict risk limits: ₹150 max trade loss (including fees), ₹300 daily loss ceiling (10% drawdown halt), and emergency capital floor of ₹2,000.

---

## 2. Core Architectural Invariants

* **Compile-Time Live Trading Lock:** In V1, live trading is permanently disabled. Attempting to enable live orders or route orders through live brokers throws an uncatchable `RuntimeError`.
* **NSE NIFTY Lot Size = 65:** Conforms strictly to NSE circular `NSE/FAOP/70616` (effective January 2026). All instruments, order sizes, and margin formulas enforce 65.
* **Realistic Orderbook Queue Execution:** Paper broker walks real Level-2 bid/ask depth with conservative slippage models. Zero instant fictitious mid-price fills.
* **Stale Quote Guard (1,500ms):** Ticks or orderbooks older than 1,500ms automatically trip `STALE_DATA_HALT`, rejecting any pending execution.
* **Emergency Latching Kill Switch:** Can be engaged instantly via UI or REST API. Automatically latches on daily loss breach (₹300) or capital floor breach (₹2,000).

---

## 3. Technology Stack

- **Core Runtime:** Python 3.14 (AsyncIO native, Starlette ASGI)
- **Database:** SQLite 3 with Write-Ahead Logging (`journal_mode=WAL`), synchronized in async background threads
- **Broker Interface:** DhanHQ v2 WebSocket & quote integration (live data feed only; orders fail-closed) + High-fidelity local replay engine
- **User Interface:** Mobile-first, dark-mode Android HUD (WebSockets, real-time MTM, low-latency streaming)

---

## 4. Repository Structure

```
nifty-options-arbitrage/
├── api/                   # Starlette REST & WebSocket endpoints
│   ├── app.py             # ASGI routes & streaming websocket
│   └── __init__.py
├── broker/                # Broker abstraction layer
│   ├── interface.py       # Universal broker interface
│   ├── dhan/              # DhanHQ v2 integration (quotes only)
│   ├── zerodha/           # Kite Connect stub adapter
│   └── mock/              # In-memory mock broker for testing
├── config.py              # Centralized configuration & compliance invariants
├── costs/                 # Indian statutory fee schedule & microstructure
│   ├── transaction_costs.py # Brokerage, STT, GST, Stamp Duty, SEBI fees
│   ├── slippage.py        # Orderbook depth walking & spread crossing
│   └── liquidity.py       # Liquidity scoring & bid-ask spread health
├── cto/                   # Executive & architectural sign-off reviews
│   ├── executive_decision.md
│   ├── implementation_gate.md
│   └── final_implementation_review.md
├── dashboard/             # Android-responsive trading HUD
│   └── index.html         # Real-time WebSocket trading & monitoring interface
├── database/              # Persistence & audit trail
│   ├── db.py              # SQLite WAL async repository
│   └── schema.sql         # Orders, trades, positions, risk events tables
├── execution/             # Order execution systems
│   ├── paper_broker.py    # High-fidelity paper trading engine
│   ├── live_broker_disabled.py # Hard compile-time safety lock
│   └── order_manager.py   # OMS signal-to-order coordinator
├── market_data/           # Market data feeds & normalization
│   ├── instruments.py     # NIFTY 50 contracts registry (Lot Size: 65)
│   ├── normalizer.py      # Level-2 tick parsing & validation
│   ├── orderbook.py       # Real-time L2 orderbook, micro-price, imbalance
│   ├── replay.py          # Deterministic tick replay simulator
│   └── websocket.py       # Live feed manager with auto-fallback
├── portfolio/             # Real-time position & P&L management
│   ├── positions.py       # Inventory & Mark-to-Market tracking
│   ├── pnl.py             # Gross/Net P&L, fees, and drawdown
│   └── margin.py          # SPAN vs Cash margin feasibility analyzer
├── research/              # Specialist agent reports (Compliance, Quant, Systems, Risk, Adversarial)
├── risk/                  # Pre-trade risk controls & invariants
│   ├── limits.py          # ₹150 trade limit, ₹300 daily limit, 1 lot cap
│   ├── stale_data_guard.py# 1,500ms max quote age check
│   ├── kill_switch.py     # Latching emergency stop mechanism
│   └── engine.py          # 7-point sequential pre-trade check gate
└── tests/                 # Automated test suite (26 unit & integration tests)
```

---

## 5. Getting Started

### Installation
Clone the repository and install the lightweight pure-Python dependencies:
```bash
git clone https://github.com/your-org/nifty-options-arbitrage.git
cd nifty-options-arbitrage
pip install -r requirements.txt
```

### Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Ensure the invariants remain locked:
```ini
EXECUTION_MODE=PAPER_TRADING
LIVE_TRADING_ENABLED=false
NIFTY_LOT_SIZE=65
INITIAL_CAPITAL_INR=3000.0
```

### Running Automated Test Suite
Execute the 26-test comprehensive suite:
```bash
pytest tests/ -v
```

### Starting the Server & Dashboard
Run the Starlette application with Uvicorn:
```bash
python3 -m uvicorn api.app:app --host 0.0.0.0 --port 8000
```
Open your smartphone browser or desktop browser to:
`http://localhost:8000`

---

## 6. Android Mobile Dashboard (Dual Phone HUD)

The responsive dashboard is optimized for mobile touch interaction and dual-monitor viewing:
- **Phone 1 (Trading HUD):** Live NIFTY Spot ticker, virtual cash balance, net P&L after friction, open positions with real-time MTM, 1-tap test execution, and latching Emergency Kill Switch.
- **Phone 2 (Arbitrage & Risk Scanner):** Put-Call Parity and Box Spread mispricing radar, `CAPITAL_INFEASIBLE` flags, orderbook imbalance meters, and active statutory fee audits.

---

## 7. Regulatory Compliance (SEBI 2026)

This software conforms strictly to the **SEBI Algorithmic Trading Framework for Retail Investors**:
1. Zero unvetted live order routing (`LIVE_TRADING_ENABLED=false`).
2. Comprehensive, immutable audit trail persisted in SQLite WAL database.
3. Pre-trade risk checks executed entirely in software prior to any order consideration.
4. Compliant with NSE circular `NSE/FAOP/70616` revising NIFTY lot sizes to **65**.
