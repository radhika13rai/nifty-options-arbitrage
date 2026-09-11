# Mathematical Formulations for Adaptive Options Learning

**Document Reference:** `RES-MATH-2026-09-11-V1`  

---

## 1. Recursive Least Squares (RLS) with Forgetting Factor

To track changing market dynamics tick-by-tick or candle-by-candle without storing unbounded historical arrays, we implement Recursive Least Squares with an exponential forgetting factor $\lambda \in [0.95, 0.99]$.

### Mathematical Formulation
Given an input feature vector $\mathbf{x}_t \in \mathbb{R}^d$ and target return $y_t$:

1. **Prediction Error**:
   $$e_t = y_t - \mathbf{x}_t^T \mathbf{w}_{t-1}$$

2. **Gain Vector Calculation**:
   $$\mathbf{k}_t = \frac{\mathbf{P}_{t-1} \mathbf{x}_t}{\lambda + \mathbf{x}_t^T \mathbf{P}_{t-1} \mathbf{x}_t}$$

3. **Weight Vector Update**:
   $$\mathbf{w}_t = \mathbf{w}_{t-1} + \mathbf{k}_t e_t$$

4. **Covariance Matrix Update**:
   $$\mathbf{P}_t = \frac{1}{\lambda} \left( \mathbf{P}_{t-1} - \mathbf{k}_t \mathbf{x}_t^T \mathbf{P}_{t-1} \right)$$

*Advantage*: $\mathcal{O}(d^2)$ computation per step, memory footprint $< 20 \text{ KB}$, and immediately adapts to new volatility regimes.

---

## 2. Bayesian Conjugate Updating for Setup Win Rates

When evaluating a specific pattern (e.g., *High Orderbook Imbalance + ORB Breakout*), rather than assuming a static win rate, we model the probability of success $p$ as a random variable with a **Beta prior**:

$$p \sim \text{Beta}(\alpha_0, \beta_0)$$

Where $\alpha_0$ represents prior successful trades and $\beta_0$ represents prior failed trades.

### Posterior Update Rule
Upon observing $k$ wins out of $n$ live trades:
$$\alpha_{\text{post}} = \alpha_0 + k$$
$$\beta_{\text{post}} = \beta_0 + (n - k)$$

The expected win probability and credible intervals are:
$$\mathbb{E}[p] = \frac{\alpha_{\text{post}}}{\alpha_{\text{post}} + \beta_{\text{post}}}$$
$$\text{Var}(p) = \frac{\alpha_{\text{post}} \beta_{\text{post}}}{(\alpha_{\text{post}} + \beta_{\text{post}})^2 (\alpha_{\text{post}} + \beta_{\text{post}} + 1)}$$

*Thompson Sampling Strategy Selection*:
Before placing an order, the system samples $p \sim \text{Beta}(\alpha, \beta)$. If $p > \text{Threshold}_{\text{hurdle}}$ (where threshold accounts for the ~₹52.02 statutory tax hurdle), the trade is authorized; otherwise, it is skipped.

---

## 3. Pure-Python Fast Ensemble Decision Forest

For non-linear feature interactions, an ensemble of shallow decision trees (depth $\le 4$) is implemented in pure Python:

### Splitting Criterion: Information Gain / Variance Reduction
For feature $j$ and split threshold $s$:
$$\mathcal{L}_{\text{split}}(j, s) = \text{Var}(D) - \left( \frac{|D_{\text{left}}|}{|D|} \text{Var}(D_{\text{left}}) + \frac{|D_{\text{right}}|}{|D|} \text{Var}(D_{\text{right}}) \right)$$

### Regularization against Overfitting
1. **Max Depth**: Limited to 3 or 4 levels (prevents memorizing single outlier spikes).
2. **Min Samples per Leaf**: At least 15 historical instances.
3. **Feature Bagging**: Random subset of features considered at each split.
4. **Execution Speed**: Traversal of a 4-level tree in pure Python takes $< 0.05 \text{ ms}$.

---

## 4. Discrete Markov Regime Switching

Market conditions alternate between distinct hidden regimes:
1. $S_1$: `TRENDING_EXPANSION` (High momentum, wide price range, low mean-reversion).
2. $S_2$: `CHOPPY_CONSOLIDATION` (Narrow range, high mean-reversion, theta decay dominant).
3. $S_3$: `HIGH_VOL_SHOCK` (Extreme spread, gap risk, wide stop-losses).

Transition matrix $\mathbf{T} \in \mathbb{R}^{3 \times 3}$:
$$T_{ij} = P(S_{t+1} = j \mid S_t = i)$$

The model computes posterior regime probabilities using a rolling 15-minute Gaussian window of realized volatility and ATR. If $P(S_2) > 0.65$, all breakout buying is paused to protect the ₹3,000 capital from theta decay.
