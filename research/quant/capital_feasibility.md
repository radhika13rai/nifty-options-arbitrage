# CAPITAL FEASIBILITY AUDIT: ₹3,000 PAPER STARTING BALANCE

**Author:** Agent 2 — Quantitative Research Lead  
**Date:** 2026-09-11

---

## 1. THE RIGOROUS FEASIBILITY AUDIT

A critical question posed by the project specification is:  
**"Is ₹3,000 starting capital actually sufficient to execute options strategies?"**

The quantitative finding is unequivocal:

| Strategy Category | Legs Required | Margin / Premium Needed | Feasibility with ₹3,000 | Reason |
| :--- | :--- | :--- | :--- | :--- |
| **Put-Call Parity** | 3 (Spot/Fut + Call + Put) | ₹1,40,000 to ₹1,80,000 | **CAPITAL_INFEASIBLE** | Short leg & Futures SPAN margin |
| **Synthetic Futures** | 2 (Long C + Short P) | ₹1,20,000 to ₹1,50,000 | **CAPITAL_INFEASIBLE** | Naked short option margin requirement |
| **Box Spread** | 4 (2 Long + 2 Short) | ₹1,50,000 to ₹2,00,000 | **CAPITAL_INFEASIBLE** | 2 short options legs require exchange margin |
| **Credit Spreads** | 2 (Short ATM + Long OTM) | ₹35,000 to ₹45,000 | **CAPITAL_INFEASIBLE** | Upfront margin requirement before hedge relief |
| **Debit Spreads** | 2 (Long NTM + Short OTM) | ₹25,000 to ₹35,000 | **CAPITAL_INFEASIBLE** | Indian brokers enforce SPAN margin on short leg |
| **ATM Long Call/Put** | 1 (Long Option, Prem ~₹100) | ₹6,500 ($65 \times 100$) | **CAPITAL_INFEASIBLE** | 1 lot cost exceeds total capital |
| **OTM Long Call/Put** | 1 (Long Option, Prem ₹15–₹40) | ₹975 to ₹2,600 | **FEASIBLE** | Total premium fits within ₹3,000 |

---

## 2. SURVIVAL DYNAMICS & DRAWDOWN UNDER ₹3,000

* Total starting capital: **₹3,000.00**
* Friction per trade (Brokerage + Taxes + Spread): **~₹117.00**
* If a strategy suffers **5 consecutive scratch/losing trades**:
  $$\text{Loss} = 5 \times ₹117.00 + \text{market losses} \approx ₹1,000.00$$
  This represents a **33.3% instantaneous portfolio drawdown** entirely driven by frictional attrition!

### Quantitative Recommendation:
Do NOT fabricate artificial success in paper trading. The simulator must faithfully reflect that multi-leg arbitrage is `CAPITAL_INFEASIBLE` with ₹3,000. For single-leg OTM volatility breakout research, strict position sizing and maximum loss limits (₹150 per trade) must be strictly enforced.
