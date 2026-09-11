# SEBI & Regulatory AI Guardrail Architecture

**Document Reference:** `RES-SEBI-AI-2026-09-11-V1`  
**Regulatory Baseline:** SEBI Circular on Retail Algorithmic Trading (Effective April 1, 2026)  

---

## 1. Regulatory Context for Self-Learning Algos in India

Under SEBI regulations, automated trading algorithms operating on client broker APIs must comply with strict predictability and safety standards:
1. **No Unbounded Self-Mutation**: Code that mutates its own risk parameters or bypasses predefined exchange limits is strictly prohibited.
2. **Pre-Trade Risk Control Primacy**: Algorithmic decision logic cannot supersede broker or client pre-trade risk controls.
3. **Audit Trail Completeness**: Every model prediction, decision rationale, and weight adaptation must be logged with microsecond timestamps.

---

## 2. The Separation of Powers Architecture

To maintain 100% compliance, the system enforces a strict architectural separation:

```
┌─────────────────────────────────────────────────────────┐
│               ADAPTIVE INTELLIGENCE LAYER               │
│  - Suggests strikes, momentum scores, probability p     │
│  - Updates weights W_t based on past outcomes           │
│  - CANNOT place orders directly                         │
└────────────────────────────┬────────────────────────────┘
                             │ Proposes Order
                             ▼
┌─────────────────────────────────────────────────────────┐
│              IMMUTABLE PRE-TRADE RISK GATE              │
│  - Hardware / Software Locked Checks:                   │
│    1. Emergency Kill Switch Disengaged?                 │
│    2. Trade Risk <= ₹150.00?                            │
│    3. Daily Realized Loss < ₹300.00?                    │
│    4. Cash >= ₹2,000.00 Floor?                          │
│    5. Lot Size == 65 and <= 1 Lot?                      │
│    6. Quote Freshness <= 1,500 ms?                      │
│  - Vetoes the AI if any parameter is violated          │
└────────────────────────────┬────────────────────────────┘
                             │ Approved Order
                             ▼
┌─────────────────────────────────────────────────────────┐
│                 PAPER EXECUTION BROKER                  │
│  - Simulates realistic queue fills                      │
│  - Records audit log in SQLite WAL                      │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Fail-Safe Guardrails Summary

1. **Max Loss Hard Cap**: If an AI prediction fails, the trailing stop-loss triggers at ₹150 max loss. The AI cannot "average down" or remove the stop.
2. **Circuit Breaker Halt**: If the AI hits 2 consecutive stop-losses (reaching the ₹300 daily loss ceiling), the system engages the emergency kill switch and shuts down trading for the rest of the day.
3. **Model Confidence Threshold**: The system requires an AI posterior confidence score $\ge 0.70$ before any order is submitted.
4. **Out-of-Distribution (OOD) Detection**: If market spread, volatility, or volume moves beyond 3 standard deviations of the 30-day training set (e.g. during an unannounced geopolitical event), the AI automatically stands down and transitions to cash.
