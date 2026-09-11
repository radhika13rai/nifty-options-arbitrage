"""
Tests for Multimodal Global Macro & News Intelligence Engine.
Verifies economic indicator embeddings, geopolitical news NLP,
multimodal fusion, and strategy directional alignment.
"""

from global_macro.indicators import macro_engine, MacroIndicatorSnapshot
from global_macro.news_embedder import news_embedder, NewsItem
from global_macro.news_feed import news_feed
from global_macro.multimodal_fusion import multimodal_fusion
from ml.engine import adaptive_ml_strategy
from market_data.normalizer import MarketDataNormalizer
from market_data.orderbook import orderbook_manager


def test_macro_indicators_vector():
    """Verify macro engine creates normalized 5-dimensional dense vectors."""
    snap = macro_engine.get_snapshot()
    vec = snap.to_dense_vector()
    assert len(vec) == 5
    for val in vec:
        assert isinstance(val, float)


def test_news_embedder_conflict():
    """Verify that military/war headlines generate high conflict intensity and bearish sentiment."""
    item = NewsItem(
        headline="Breaking: Missile strike reported on oil tankers in Red Sea; military escalation imminent",
        source="Reuters",
        timestamp_ms=1000.0,
        category="GEOPOLITICS"
    )
    emb = news_embedder.embed_headline(item)
    assert emb.geopolitical_conflict_intensity >= 0.70
    assert emb.directional_sentiment < -0.40
    assert len(emb.dense_vector) == 8


def test_news_embedder_deescalation():
    """Verify that peace/ceasefire headlines generate bullish sentiment and low conflict."""
    item = NewsItem(
        headline="Historic peace agreement signed: Ceasefire treaty takes effect; sanctions eased globally",
        source="Bloomberg",
        timestamp_ms=1000.0,
        category="GEOPOLITICS"
    )
    emb = news_embedder.embed_headline(item)
    assert emb.geopolitical_conflict_intensity == 0.0
    assert emb.directional_sentiment >= 0.50
    assert len(emb.dense_vector) == 8


def test_multimodal_fusion_war_crisis():
    """Verify war crisis scenario fuses into high fear and FAVOR_PUT_BREAKOUT posture."""
    macro_snap = macro_engine.apply_scenario("MIDDLE_EAST_WAR_CRISIS")
    news_embs = news_feed.load_scenario("MIDDLE_EAST_WAR_CRISIS")

    fusion_res = multimodal_fusion.fuse(macro_snap, news_embs)
    assert fusion_res.geopolitical_fear_index >= 0.70
    assert fusion_res.global_bias in ["STRONG_BEARISH", "MODERATE_BEARISH"]
    assert fusion_res.recommended_options_posture == "FAVOR_PUT_BREAKOUT"
    assert fusion_res.expected_nifty_gap_points < -100.0  # Big gap down expected
    assert len(fusion_res.fused_embedding_vector) == 13


def test_multimodal_fusion_peace_relief():
    """Verify de-escalation scenario fuses into bullish relief and FAVOR_CALL_BREAKOUT posture."""
    macro_snap = macro_engine.apply_scenario("GLOBAL_DEESCALATION_RELIEF")
    news_embs = news_feed.load_scenario("GLOBAL_DEESCALATION_RELIEF")

    fusion_res = multimodal_fusion.fuse(macro_snap, news_embs)
    assert fusion_res.geopolitical_fear_index <= 0.30
    assert fusion_res.global_bias in ["STRONG_BULLISH", "MODERATE_BULLISH"]
    assert fusion_res.recommended_options_posture == "FAVOR_CALL_BREAKOUT"
    assert fusion_res.expected_nifty_gap_points > 100.0  # Gap up expected


def test_adaptive_ml_strategy_global_alignment():
    """Verify that AdaptiveMLStrategy suppresses Call options during war shock."""
    # 1. Apply war crisis
    macro_engine.apply_scenario("MIDDLE_EAST_WAR_CRISIS")
    news_feed.load_scenario("MIDDLE_EAST_WAR_CRISIS")

    # 2. Feed Call option orderbook
    call_sym = "NIFTY_2026-09-24_24500_CE"
    tick = MarketDataNormalizer.create_synthetic_tick(call_sym, mid_price=25.0)
    orderbook_manager.update_tick(tick)
    snap = orderbook_manager.get_snapshot(call_sym)
    assert snap is not None

    # Even if technicals suggest trade, global macro war filter MUST block Call buying!
    signals = adaptive_ml_strategy.on_orderbook(snap)
    assert len(signals) == 0  # Call buying blocked!

    # Reset to neutral
    macro_engine.apply_scenario("NEUTRAL")
    news_feed.load_scenario("NEUTRAL")


def test_macro_dataset_seeding_and_retrieval():
    """Verify macro dataset seeds historical shock events and queries correctly."""
    from global_macro.dataset import macro_dataset
    macro_dataset.init_tables()
    inserted = macro_dataset.seed_historical_events()
    assert inserted >= 10

    samples = macro_dataset.get_all_samples()
    assert len(samples) >= 10
    
    first = samples[0]
    assert first.brent_crude > 0
    assert len(first.fused_features) == 13
    assert first.actual_direction in ["BEARISH", "BULLISH", "CHOPPY"]


def test_multimodal_trainer_convergence_and_accuracy():
    """Verify that pure-Python Ridge regression converges with high directional accuracy."""
    from global_macro.trainer import macro_trainer
    res = macro_trainer.train_on_dataset()

    assert res.num_samples >= 10
    assert len(res.macro_weights) == 5
    assert len(res.news_weights) == 8
    assert res.directional_accuracy >= 0.75  # Minimum 75% directional precision
    assert res.training_duration_ms > 0
    assert res.training_duration_ms < 500.0  # Ultra-fast <500ms execution


def test_multimodal_weights_hot_update():
    """Verify that trained weights dynamically update multimodal_fusion engine."""
    from global_macro.multimodal_fusion import multimodal_fusion
    from global_macro.trainer import macro_trainer
    
    res = macro_trainer.train_on_dataset()
    active = multimodal_fusion.get_weights()
    assert active["macro_weights"] == res.macro_weights
    assert active["news_weights"] == res.news_weights
