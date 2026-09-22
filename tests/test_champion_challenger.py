"""
Unit & Integration Tests for Closed-Loop Self-Learning & Champion-Challenger Governance.
Verifies:
1. 16-dimensional unified entry feature extraction
2. Reconciled trade episode persistence into SQLite (zero unfulfilled trades)
3. Challenger model training on historical holdout splits
4. Strict institutional promotion gate (Win Rate, Sharpe, Profit Factor, Drawdown)
5. Automated rollback to conservative priors upon drift guard trigger
"""

import asyncio
import json
import time
import pytest

from ml.features import feature_extractor
from ml.champion_challenger import ChampionChallengerEngine, champion_challenger
from ml.drift_guard import ModelDriftGuard, drift_guard
from database.db import db_manager
from market_data.normalizer import MarketTick
from market_data.orderbook import OrderbookSnapshot
from execution.auto_engine import ManagedTrade, auto_engine


def test_16d_unified_feature_vector_structure():
    """Verify that extract_unified_vector returns exactly 16 normalized floats."""
    snap = OrderbookSnapshot(
        symbol="NIFTY_TEST_23400_CE",
        timestamp_ms=time.time() * 1000.0,
        age_ms=10.0,
        best_bid=24.0,
        best_ask=24.5,
        mid_price=24.25,
        micro_price=24.30,
        spread=0.50,
        imbalance=0.25,
        total_bid_volume=1200,
        total_ask_volume=800,
        bids=[],
        asks=[]
    )

    vec = feature_extractor.extract_unified_vector(
        snapshot=snap,
        atm_iv=0.165,
        put_call_skew=0.015,
        days_to_expiry=3.0,
        delta=0.48,
        brent_pct_chg=1.2,
        dxy_pct_chg=-0.3,
        news_sentiment=0.45,
        tension_index=0.20
    )

    assert isinstance(vec, list)
    assert len(vec) == 16
    for val in vec:
        assert isinstance(val, (int, float))
        # Value should be reasonably normalized
        assert -10.0 <= val <= 10.0


def test_reconciled_episode_persistence_and_retrieval():
    """Verify that only reconciled completed trades are written to SQLite learning dataset."""
    async def _run():
        await db_manager.async_init_db()

        ep_id = f"EP_TEST_{int(time.time()*1000)}"
        features = [0.15 * i for i in range(16)]
        
        ep_data = {
            "episode_id": ep_id,
            "trade_id": "TRD_RECONCILED_01",
            "symbol": "NIFTY_2026-09-24_23400_CE",
            "option_type": "CE",
            "entry_time_ms": time.time() * 1000.0 - 60000.0,
            "exit_time_ms": time.time() * 1000.0,
            "entry_price": 22.50,
            "exit_price": 26.80,
            "quantity": 65,
            "gross_pnl": 279.50,
            "fees_friction": 50.79,
            "net_pnl": 228.71,
            "points_moved": 4.30,
            "is_win": True,
            "exit_reason": "TARGET_1_3_REACHED",
            "features": features,
            "macro_snapshot": {"brent": 82.5, "sentiment": 0.35}
        }

        await db_manager.record_learning_episode(ep_data)

        # Retrieve
        episodes = await db_manager.get_learning_episodes(limit=10)
        found = [e for e in episodes if e["episode_id"] == ep_id]
        assert len(found) == 1

        rec = found[0]
        assert rec["symbol"] == "NIFTY_2026-09-24_23400_CE"
        assert rec["net_pnl"] == 228.71
        assert rec["is_win"] == 1
        stored_feats = json.loads(rec["features_json"])
        assert len(stored_feats) == 16
        assert abs(stored_feats[1] - 0.15) < 1e-4

    asyncio.run(_run())


def test_champion_challenger_promotion_gate():
    """Verify strict out-of-sample promotion criteria."""
    engine = ChampionChallengerEngine()
    initial_champ_id = engine.champion.model_id

    # 1. Attempting promotion without challenger should return False
    res0 = engine.evaluate_and_promote()
    assert res0["promoted"] is False
    assert res0["reason"] == "NO_CHALLENGER_AVAILABLE"

    # 2. Build high-performing synthetic episodes
    episodes = []
    base_time = time.time() * 1000.0
    for i in range(20):
        # 16-D feature vector with positive momentum alignment
        feats = [0.5, 0.2, 0.01, 0.3, 0.4, 0.2, 0.05, 0.6, 0.1, 0.2, 0.0, 0.5, 0.1, -0.1, 0.4, 0.2]
        is_winner = i % 4 != 0  # 75% win rate
        pts = 3.5 if is_winner else -1.5
        net = (pts * 65) - 50.0
        
        episodes.append({
            "episode_id": f"EP_SYNTH_{i}",
            "trade_id": f"TRD_SYNTH_{i}",
            "entry_time_ms": base_time + (i * 60000.0),
            "option_type": "CE",
            "points_moved": pts,
            "net_pnl": net,
            "features": feats
        })

    # 3. Train Challenger
    challenger = engine.train_challenger(episodes, split_ratio=0.70)
    assert challenger is not None
    assert engine.challenger is not None

    # 4. If challenger beats champion criteria, it is promoted
    # Force superior metrics on challenger to test promotion gate
    engine.challenger.metrics.win_rate = 0.75
    engine.challenger.metrics.net_profit_factor = 2.40
    engine.challenger.metrics.sharpe_ratio = 2.50  # Exceeds Champion 1.80 + 0.15
    engine.challenger.metrics.max_drawdown_pct = 6.0

    promo_res = engine.evaluate_and_promote()
    assert promo_res["promoted"] is True
    assert promo_res["reason"] == "OOS_VALIDATION_SURPASSED"
    assert engine.champion.model_id.startswith("CHALLENGER_")
    assert len(engine.promotion_history) == 1

    # 5. If a new challenger fails the criteria (e.g. low win rate), it is rejected
    inferior_challenger = engine.train_challenger(episodes)
    inferior_challenger.metrics.win_rate = 0.45  # Fails 55% hurdle
    res_rejected = engine.evaluate_and_promote()
    assert res_rejected["promoted"] is False
    assert "Win Rate" in res_rejected["reason"]


def test_automated_rollback_to_baseline_priors():
    """Verify that drift guard or operator triggers reset to conservative baseline priors."""
    engine = ChampionChallengerEngine()
    
    # Mutate champion weights
    engine.champion.weights[0] = 999.0
    assert engine.champion.weights[0] == 999.0

    # Execute rollback
    engine.rollback_to_baseline(reason="CONSECUTIVE_LOSS_STREAK")
    assert engine.champion.model_id.startswith("CHAMPION_ROLLBACK_")
    assert abs(engine.champion.weights[0] - 1.8) < 1e-4  # Restored to baseline 1.8
    assert engine.challenger is None
