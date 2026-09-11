# MATHEMATICAL MODELS & FORMULATION

**Author:** Agent 2 — Quantitative Research Lead  
**Date:** 2026-09-11

---

## 1. PUT-CALL PARITY MODEL

For European options on non-dividend paying underlying index $S$ with strike $K$, risk-free rate $r$, and time to expiry $	au = T - t$:

$$C(S, K, 	au) - P(S, K, 	au) = S - K e^{-r	au}$$

In the presence of discrete dividends $D_i$ at time $t_i$:

$$C - P = S - \sum D_i e^{-r t_i} - K e^{-r	au}$$

### Arbitrage Conditions:
* **Conversion Opportunity (Synthetic Short):**
  $$\text{Spread}_{\text{conv}} = S_{\text{bid}} - K e^{-r	au} - (C_{\text{ask}} - P_{\text{bid}}) > \text{Friction}$$
* **Reversal Opportunity (Synthetic Long):**
  $$\text{Spread}_{\text{rev}} = (C_{\text{bid}} - P_{\text{ask}}) - (S_{\text{ask}} - K e^{-r	au}) > \text{Friction}$$

---

## 2. BLACK-SCHOLES-MERTON & IMPLIED VOLATILITY

For European option pricing:

$$d_1 = \frac{\ln(S / K) + (r + \frac{\sigma^2}{2})\tau}{\sigma \sqrt{\tau}}, \quad d_2 = d_1 - \sigma \sqrt{\tau}$$

$$C = S N(d_1) - K e^{-r	au} N(d_2)$$
$$P = K e^{-r	au} N(-d_2) - S N(-d_1)$$

Greeks calculations:
- **Delta ($\Delta$):** $\frac{\partial V}{\partial S} = N(d_1)$ (Calls), $N(d_1) - 1$ (Puts)
- **Gamma ($\Gamma$):** $\frac{\partial^2 V}{\partial S^2} = \frac{N'(d_1)}{S \sigma \sqrt{\tau}}$
- **Vega ($\nu$):** $\frac{\partial V}{\partial \sigma} = S \sqrt{\tau} N'(d_1)$
- **Theta ($\Theta$):** Time decay derivative
