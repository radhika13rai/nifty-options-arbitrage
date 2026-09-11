# Tax-Aware Objective Functions & Friction Penalization

**Document Reference:** `RES-TAX-2026-09-11-V1`  

---

## 1. The Core Quantitative Dilemma in Indian Retail Options

In standard machine learning literature, trading models are trained to maximize accuracy:
$$\text{Accuracy} = \frac{1}{N} \sum_{i=1}^N \mathbf{1}_{(\hat{y}_i = y_i)}$$
or minimize Mean Squared Error (MSE) of price predictions:
$$\text{MSE} = \frac{1}{N} \sum_{i=1}^N (P_{t+k} - \hat{P}_{t+k})^2$$

### The Failure Mode
In the Indian options market, this formulation is **disastrous** for a retail trader with ₹3,000 capital:
- Suppose a model achieves a **65% win rate** predicting 1.5-point moves on NIFTY options.
- 10 trades taken:
  - 6 winning trades: $+1.5 \text{ pts} \times 65 = +₹97.50$ gross per trade ($+₹585.00$ gross).
  - 4 losing trades: $-1.5 \text{ pts} \times 65 = -₹97.50$ gross per trade ($-₹390.00$ gross).
  - **Gross Profit**: $+₹195.00$.
- **Statutory Taxes Deducted**:
  - 10 round-trip trades $\times ~₹52.02$ = **₹520.20** in taxes and brokerage!
- **Net Result**: $+₹195.00 - ₹520.20 =$ **-₹325.20 Net Loss** (Over 10% of total capital wiped out despite a 65% win rate!).

---

## 2. The Net Realized Friction Objective Function

To solve this, the objective function in our learning engine directly incorporates the exact 2026 Indian statutory fee schedule:

$$\mathcal{J}(\mathbf{\theta}) = \sum_{i=1}^N \Big[ \underbrace{(P_{\text{exit}, i} - P_{\text{entry}, i}) \cdot Q}_{\text{Gross PnL}} - \underbrace{\Phi(P_{\text{entry}, i}, P_{\text{exit}, i}, Q)}_{\text{Statutory Friction}} - \underbrace{\lambda \cdot \mathbf{1}_{\text{trade}}}_{\text{Overtrading Penalty}} \Big]$$

Where:
- $Q = 65$ (Mandatory NSE NIFTY lot size).
- $\Phi(P_{\text{entry}}, P_{\text{exit}}, Q)$ is the exact statutory cost function:
  $$\Phi = \text{Brokerage}(₹40) + \text{STT}(0.10\% \cdot P_{\text{exit}} Q) + \text{Exchange}(0.05\% \cdot (P_{\text{entry}} + P_{\text{exit}}) Q) + \text{GST}(18\%) + \text{StampDuty}(0.003\% \cdot P_{\text{entry}} Q) + \text{SEBI}$$
- $\lambda$ is an explicit hyperparameter penalizing unnecessary trade churn.

---

## 3. Mathematical Implications on Model Behavior

1. **Selective Patience (Selective Sparsity)**:
   - When the expected price move $\mathbb{E}[\Delta P]$ is $< 1.2$ points ($< ₹78.00$ gross), the objective function produces a negative value:
     $$\mathbb{E}[\text{Net}] = 1.2 \cdot 65 - 52.02 = 78.00 - 52.02 = +₹25.98$$
     After applying the variance and trade risk penalty, the model chooses **Action = HOLD**.
   - The AI learns that **no-trade is superior to a low-conviction trade**.
2. **Asymmetric Risk/Reward Enforcement**:
   - The model is incentivized to only fire when volatility breakout indicators show an expected move of $\ge 3.0$ to $4.0$ points ($\ge ₹195$ gross), easily overcoming the ₹52 fee barrier.
