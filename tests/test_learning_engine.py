"""
Tests for Adaptive Self-Learning Options Engine.
Verifies RLS online learning, Bayesian Thompson sampling, tax-aware hurdle filtering,
and market regime classification.
"""

from ml.features import feature_extractor
from ml.learner import (
    RecursiveLeastSquares,
    BayesianThompsonSampler,
    AdaptiveLearningEngine
)
from market_data.normalizer import MarketDataNormalizer


def test_feature_extraction():
    """Verify that feature extractor generates normalized 8-dimension vectors."""
    tick = MarketDataNormalizer.create_synthetic_tick(
        symbol="NIFTY_2026-09-24_24500_CE",
        mid_price=25.0,
        spread=0.20
    )
    from market_data.orderbook import orderbook_manager
    orderbook_manager.update_tick(tick)
    snap = orderbook_manager.get_snapshot("NIFTY_2026-09-24_24500_CE")
    assert snap is not None

    feat_vec = feature_extractor.extract_features(snap)
    feats = feat_vec.to_list()
    assert len(feats) == 8
    # Imbalance must be within [-1.0, 1.0]
    assert -1.0 <= feats[0] <= 1.0


def test_rls_online_learning():
    """Verify Recursive Least Squares adapts weights to minimize prediction error."""
    rls = RecursiveLeastSquares(dim=4, lam=0.98, delta=1.0)
    x = [1.0, 0.5, -0.2, 0.8]
    target_y = 3.5

    # Initial error
    init_err = abs(target_y - rls.predict(x))

    # Perform 5 online adaptation updates on this signal pattern
    for _ in range(5):
        rls.update(x, target_y)

    final_err = abs(target_y - rls.predict(x))
    assert final_err < init_err
    assert rls.steps == 5


def test_bayesian_thompson_sampling():
    """Verify Bayesian conjugate prior updates win rate correctly."""
    sampler = BayesianThompsonSampler(alpha_prior=2.0, beta_prior=2.0)
    assert sampler.expected_win_rate == 0.50

    # Observe 5 winning trades
    for _ in range(5):
        sampler.update(is_winning_trade=True)

    assert sampler.expected_win_rate > 0.70

    # Observe 5 losing trades
    for _ in range(5):
        sampler.update(is_winning_trade=False)

    assert 0.45 <= sampler.expected_win_rate <= 0.55


def test_tax_aware_friction_hurdle():
    """Verify that expected moves not overcoming the ~₹52 fee hurdle are rejected."""
    engine = AdaptiveLearningEngine(lot_size=65)
    # Set regime to trending
    engine.current_regime = "TRENDING_BULL"

    # 1. Weak setup: Small positive features predicting only 0.2 points move (Gross: ₹13, Fees: ₹52)
    weak_features = [0.05, 0.0, 0.01, 0.0, 0.0, 0.0, 0.0, 0.0]
    should_trade, conf, reason = engine.evaluate_opportunity(weak_features, "CE", premium=25.0)
    assert should_trade is False
    assert "Sub-hurdle" in reason

    # 2. Strong breakout setup: High positive imbalance and strong momentum
    strong_features = [0.8, 0.5, 0.005, 1.2, 1.5, 0.6, 0.8, 0.9]
    # Warm up weights
    engine.rls.w = [2.5, 1.5, -1.0, 1.0, 1.5, 0.5, 0.5, 0.5]
    should_trade, conf, reason = engine.evaluate_opportunity(strong_features, "CE", premium=25.0)
    assert should_trade is True
    assert "AI Conviction" in reason
    assert conf >= 0.60


def test_regime_classification_choppy_pause():
    """Verify that when market is choppy, long option trades are paused."""
    engine = AdaptiveLearningEngine(lot_size=65)
    # Zero EMA slope and moderate ATR => CHOPPY_CONSOLIDATION
    regime = engine.classify_regime(spot_ema_slope=0.0001, spot_atr=20.0)
    assert regime == "CHOPPY_CONSOLIDATION"

    strong_features = [0.8, 0.5, 0.005, 1.2, 1.5, 0.6, 0.8, 0.9]
    should_trade, conf, reason = engine.evaluate_opportunity(strong_features, "CE", premium=25.0)
    assert should_trade is False
    assert "CHOPPY" in reason


def test_daily_walk_forward_step():
    """Verify that end-of-day walk-forward adaptation step increments epoch and adapts."""
    engine = AdaptiveLearningEngine(lot_size=65)
    init_epoch = engine.epoch

    trades = [
        {"features": [0.5] * 8, "option_type": "CE", "points_moved": 3.0, "net_pnl": 140.0},
        {"features": [0.6] * 8, "option_type": "CE", "points_moved": -1.5, "net_pnl": -150.0},
    ]

    metrics = engine.run_daily_adaptation_step(trades)
    assert metrics.epoch == init_epoch + 1
    assert metrics.rls_steps == 2
