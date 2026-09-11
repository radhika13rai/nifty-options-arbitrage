# TRANSACTION COST MODEL: NSE DERIVATIVES REGIME (2026)

**Author:** Agent 2 — Quantitative Research Lead  
**Date:** 2026-09-11

---

## 1. INDIAN STATUTORY & BROKERAGE FEE SCHEDULE

| Fee Component | Rate / Formula | Applied To | Statutory Authority |
| :--- | :--- | :--- | :--- |
| **Brokerage** | ₹20.00 flat per executed order | Both Buy & Sell Orders | Broker Tariff Schedule (Dhan/Zerodha) |
| **STT (Securities Transaction Tax)** | 0.10% (100 bps) | **Sell Side Premium Only** | Finance Act (Revised Oct 2024/2025) |
| **Exchange Transaction Charge** | 0.0505% (50.5 bps) | Both Buy & Sell Premium | NSE Circular NSE/F&O/2024/25 |
| **SEBI Turnover Fee** | ₹10.00 per crore (0.0001%) | Both Buy & Sell Premium | SEBI Fee Schedule |
| **Integrated GST** | 18.00% | (Brokerage + Exchange + SEBI) | Central Goods & Services Tax Act |
| **State Stamp Duty** | 0.0030% (3 bps) | **Buy Side Premium Only** | Indian Stamp Act (Maharashtra/Delhi) |

---

## 2. EMPIRICAL EXAMPLE: 1 LOT NIFTY OPTION

* **Contract:** NIFTY 25,000 CE (1 Lot = 65 Qty)
* **Entry Premium:** ₹30.00 (Buy Turnover = $65 \times 30 = ₹1,950.00$)
* **Exit Premium:** ₹35.00 (Sell Turnover = $65 \times 35 = ₹2,275.00$)

```
Statutory Friction Breakdown:
--------------------------------------------------
Brokerage (Buy + Sell):                 ₹40.00
STT (0.10% on ₹2,275.00 Sell):           ₹2.28
Exchange Charges (0.05% on ₹4,225.00):   ₹2.13
SEBI Fee (₹10/Cr on ₹4,225.00):          ₹0.01
Stamp Duty (0.003% on ₹1,950.00):        ₹0.06
GST (18% on ₹40.00 + ₹2.13 + ₹0.01):     ₹7.59
--------------------------------------------------
TOTAL STATUTORY & BROKERAGE COSTS:      ₹52.07
--------------------------------------------------

Microstructure Friction (Spread + Slippage):
Bid-Ask Spread Crossing (0.80 pts x 65): ₹52.00
Latency Slippage (0.20 pts x 65):        ₹13.00
--------------------------------------------------
TOTAL FRICTION PER ROUND TRIP:          ₹117.07
==================================================
```

### Critical Deduction:
On a gross price move of +5.00 points ($65 \times 5 = +₹325.00$), total friction of ₹117.07 consumes **36.0% of the entire gross profit**. If the price move is only +1.80 points ($65 \times 1.80 = +₹117.00$), the net profit is exactly **ZERO**.
