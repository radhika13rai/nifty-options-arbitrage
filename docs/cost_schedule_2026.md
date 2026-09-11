# Indian Derivatives Statutory Cost Schedule (2026)

## 1. Statutory Tax & Fee Structure

When trading NIFTY 50 Options in India, the following statutory charges apply on every transaction:

| Statutory Charge | Rate / Percentage | Application Base | Side Applied |
|---|---|---|---|
| **Brokerage** | ₹20.00 flat per executed order leg | Per order | Buy & Sell |
| **Securities Transaction Tax (STT)** | 0.10% (10 bps) | Premium turnover ($P \times Q$) | Sell side only |
| **Exchange Transaction Fee (NSE)** | 0.05% (5 bps) | Premium turnover ($P \times Q$) | Buy & Sell |
| **Goods & Services Tax (GST)** | 18.00% | On (Brokerage + Txn Fee + SEBI Fee) | Buy & Sell |
| **Stamp Duty** | 0.003% (0.3 bps) | Premium turnover ($P \times Q$) | Buy side only |
| **SEBI Turnover Fee** | 0.0001% (₹10 / crore) | Premium turnover ($P \times Q$) | Buy & Sell |

---

## 2. Microstructure Breakeven Math (NIFTY Lot Size = 65)

### Scenario: Buy 1 Lot @ ₹30.00, Sell @ ₹35.00
- **Buy Turnover:** $30 \times 65 = ₹1,950.00$
  - Brokerage: ₹20.00
  - STT: ₹0.00
  - Exchange: ₹0.97
  - GST: ₹3.77
  - Stamp Duty: ₹0.06
  - SEBI: ₹0.00
  - **Total Buy Fees:** **₹24.80**

- **Sell Turnover:** $35 \times 65 = ₹2,275.00$
  - Brokerage: ₹20.00
  - STT: ₹2.27
  - Exchange: ₹1.14
  - GST: ₹3.81
  - Stamp Duty: ₹0.00
  - SEBI: ₹0.00
  - **Total Sell Fees:** **₹27.22**

- **Total Round-Trip Friction:** $24.80 + 27.22 =$ **₹52.02**
- **Gross Profit:** $(35 - 30) \times 65 =$ **₹325.00**
- **Net Profit:** $325.00 - 52.02 =$ **₹272.98**
- **Breakeven Points Hurdle:** $52.02 / 65 =$ **0.80 points**

On a position outlay of ₹1,950, statutory fees consume **2.67%** of deployed capital.
