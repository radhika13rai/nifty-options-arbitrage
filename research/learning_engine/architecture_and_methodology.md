# Adaptive Self-Learning Options Engine: Architecture & Methodology

**Document Reference:** `RES-AI-2026-09-11-V1`  
**System Target:** NIFTY 50 Options Algorithmic Trading  
**Capital Constraint:** ₹3,000 Retail Account  
**Regulatory Context:** SEBI Retail Algorithmic Framework (2026)  

---

## 1. Executive Vision & Core Philosophy

The goal is to design an inbuilt, self-updating algorithmic engine that:
1. Ingests daily market data (price, orderbook depth, implied volatility, open interest).
2. Evaluates historical trade outcomes and market reactions.
3. Automatically updates its feature weights and entry thresholds overnight.
4. Identifies shifting market regimes (trending vs. choppy) and adapts its rules dynamically.
5. Remains strictly bounded by hard, immutable pre-trade risk gates (max ₹150 loss per trade, ₹300 daily loss, 65 lot size).

---

## 2. The Daily Learning Loop (Walk-Forward Architecture)

In financial markets, training a static machine learning model once and letting it run indefinitely leads to rapid alpha decay. Markets are non-stationary: participants adapt, macroeconomic regimes rotate, and volatility cycles expand and contract.

The architecture employs an **End-of-Day Walk-Forward Adaptation Loop**:

```
[Day T: Trading Session]
       │
       ▼
[09:15 - 15:30] Real-Time Signal Generation using Model Weights W_T
       │
       ▼
[15:35] Market Close: Ingestion of All 1-Min OHLCV + Options Chain + OI
       │
       ▼
[16:00] Post-Trade Reconciliation & Feature Attribution:
       - Which feature vectors yielded positive Net PnL (after ₹52+ friction)?
       - Which feature vectors resulted in stop-loss hits or theta decay?
       │
       ▼
[16:30] Walk-Forward Model Retraining:
       - Rolling window of past N days (e.g., 30 days) with exponential time decay.
       - Bayesian posterior update of strike-selection probabilities.
       - Recursive parameter adjustment for momentum and imbalance thresholds.
       │
       ▼
[17:00] In-Sample vs. Out-of-Sample Overfitting Guard:
       - If validation performance degrades, revert to defensive default weights.
       │
       ▼
[Day T+1: Morning Prep]
       - Load updated Model Weights W_{T+1} into the live Trading Engine.
```

---

## 3. High-Speed, Zero-Dependency Machine Learning

To guarantee extreme reliability, deterministic execution, and zero compilation friction on ARM/Android/Linux architectures:

1. **No Heavy External Frameworks Required**:
   - Heavy C-extension frameworks (TensorFlow, PyTorch, C-compiled SciPy) introduce multi-gigabyte bloat, compilation failures, and unpredictable latency spikes.
   - For tabular financial data, decision trees, recursive least squares, and Bayesian conjugate updating implemented in pure Python are:
     - 100x lighter (< 5 MB RAM).
     - Deterministic and auditable down to individual mathematical equations.
     - Ultra-low latency: prediction inference takes $< 0.5 \text{ ms}$ (ideal for fast options scalping).

2. **Core Mathematical Models Selected**:
   - **Recursive Least Squares (RLS) with Exponential Forgetting**: Fast online adaptation to trend slopes and micro-price shifts.
   - **Conjugate Bayesian Estimator (Beta-Binomial)**: Continuously tracks the probability of success for specific strike distances and momentum setups.
   - **Pure-Python Ensemble Decision Forest**: Captures non-linear relationships between RSI, VWAP distance, and Orderbook Imbalance without overfitting.
   - **Regime Transition Detector**: Classifies current market volatility into `LOW_VOL_CHOPPY`, `HIGH_VOL_TRENDING`, or `EVENT_SHOCK`.

---

## 4. Key Invariants & Safety Principles

1. **Net Profit Optimization**: The objective function penalizes every trade with the exact 2026 Indian statutory fee schedule (~₹52.02 per lot), teaching the model to stay flat when edge is small.
2. **Hard Risk Subjugation**: The AI model is an *advisor*, never a sovereign authority. The Pre-Trade Risk Engine (`risk/engine.py`) has final veto power over every single order.
3. **Fail-Closed Fallback**: If an overnight training run fails or produces unstable parameters, the engine automatically rolls back to verified conservative default parameters.
