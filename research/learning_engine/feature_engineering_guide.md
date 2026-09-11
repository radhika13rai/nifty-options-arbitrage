# NIFTY Options Feature Engineering & Signal Design

**Document Reference:** `RES-FEAT-2026-09-11-V1`  
**Target Asset:** NSE NIFTY 50 Weekly / Monthly Options  

---

## 1. Feature Taxonomy

To train an effective adaptive options model, raw price alone is insufficient. We divide features into four distinct quantitative categories:

1. **Microstructure & Order Flow** (Sub-second to 1-minute resolution)
2. **Implied Volatility & Greeks** (Option surface dynamics)
3. **Open Interest (OI) & Structural Support/Resistance** (Institutional positioning)
4. **Intraday Price Action & Trend Momentum** (Index spot momentum)

---

## 2. Quantitative Feature Specifications

### 2.1 Microstructure & Order Flow Features
- **Orderbook Imbalance ($I_{\text{book}}$)**:
  $$I_{\text{book}} = \frac{\sum_{i=1}^5 \text{BidQty}_i - \sum_{i=1}^5 \text{AskQty}_i}{\sum_{i=1}^5 \text{BidQty}_i + \sum_{i=1}^5 \text{AskQty}_i} \in [-1.0, 1.0]$$
  *Intuition*: Values $> +0.40$ indicate aggressive buying demand, providing a favorable tailwind for long call breakouts.
- **Micro-Price Spread Delta ($\Delta_{\text{micro}}$)**:
  $$\Delta_{\text{micro}} = P_{\text{micro}} - P_{\text{mid}}$$
  Measures whether queue pressure is front-running the next tick.
- **Bid-Ask Spread Efficiency ($S_{\text{eff}}$)**:
  $$S_{\text{eff}} = \frac{P_{\text{ask}} - P_{\text{bid}}}{P_{\text{mid}}}$$
  Filters out illiquid strikes with wide bid-ask spreads that would immediately destroy capital through spread crossing.

### 2.2 Volatility & Greeks Features
- **Implied Volatility Percentile ($\text{IVP}$)**:
  Measures current IV relative to the past 20 sessions.
  *Rule*: Avoid buying options when $\text{IVP} > 85\%$ (extreme IV crush risk upon reversal); prefer entering when $\text{IVP} < 50\%$ right before volatility expansion.
- **Theta Decay Velocity ($\theta_{\text{hourly}}$)**:
  $$\theta_{\text{hourly}} = \frac{\theta_{\text{daily}}}{6.25}$$
  For intraday trades, theta decay on weekly expiry options accelerates drastically after 13:00 IST. The model discounts long premium holds as the clock advances.
- **Delta Distance ($\Delta_{\text{target}}$)**:
  Selects strikes with Delta between $0.20$ and $0.35$ (low-premium OTM options under ₹38.00) that fit the ₹3,000 capital limit while retaining sufficient gamma acceleration upon a spot breakout.

### 2.3 Open Interest (OI) & Market Structure
- **Put-Call Ratio ($\text{PCR}_{\text{volume}}$ & $\text{PCR}_{\text{OI}}$)**:
  $$\text{PCR} = \frac{\sum \text{Put Open Interest}}{\sum \text{Call Open Interest}}$$
  *Intuition*: Extreme values ($\text{PCR} > 1.30$ or $< 0.70$) signal contrarian exhaustion or strong directional institutional bias.
- **Max Pain Strike Distance**:
  Calculates the strike price where option writers lose the least money at expiry. The index gravitates toward this level on expiry afternoons.

### 2.4 Intraday Price Action & Trend Features
- **VWAP Stretch ($Z_{\text{VWAP}}$)**:
  $$Z_{\text{VWAP}} = \frac{P_{\text{spot}} - \text{VWAP}}{\sigma_{\text{VWAP}}}$$
  Measures standardized deviation from institutional volume-weighted average price.
- **EMA Trend Slope**:
  Slope of 9-period and 21-period exponential moving averages on 5-minute candles.
- **Opening Range Breakout (ORB)**:
  Distance of current spot relative to the 09:15 - 09:30 high/low boundary.

---

## 3. Normalization & Feature Scaling Pipeline

All continuous features are dynamically scaled using rolling median and Interquartile Range (IQR) to prevent single-candle outliers (such as flash news spikes) from distorting the self-learning weights:

$$x_{\text{scaled}} = \frac{x - \text{Median}_{30\text{d}}}{\text{IQR}_{30\text{d}}}$$

This guarantees bounded, well-behaved input tensors for the learning algorithms.
