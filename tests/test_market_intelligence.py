"""
Unit & Integration Tests for Market Intelligence Engine (MIE).
Verifies:
1. Exact and token Jaccard news deduplication
2. Temporal half-life decay of news sentiment
3. Relevance and urgency classification for Indian markets
4. Breaking news and macroeconomic shock defense stand-down triggers
"""

import time
import pytest
from market_intelligence.deduplicator import NewsDeduplicator, normalize_headline, tokenize, jaccard_similarity
from market_intelligence.classifier import NewsClassifier, news_classifier
from market_intelligence.alert_engine import AlertEngine, alert_engine
from market_intelligence.engine import MarketIntelligenceEngine


def test_headline_normalization_and_tokenization():
    """Verify source stripping and token cleaning."""
    raw = "Breaking: Brent Crude Surges 4% Following Middle East Tanker Attack - The Economic Times"
    norm = normalize_headline(raw)
    assert "economic times" not in norm
    assert "brent crude surges" in norm

    tokens = tokenize(norm)
    assert "brent" in tokens
    assert "crude" in tokens
    assert "surge" in tokens
    # Stopwords should be filtered
    assert "the" not in tokens


def test_news_deduplication_exact_and_near_match():
    """Verify that identical and syndicated wire variants are discarded."""
    dedup = NewsDeduplicator(ttl_sec=3600.0, jaccard_threshold=0.45)
    now_ms = time.time() * 1000.0

    h1 = "Brent crude oil prices jump 3% as Middle East tensions threaten Red Sea shipping - Reuters"
    h2 = "Brent crude oil prices jump 3% as Middle East tensions threaten Red Sea shipping - LiveMint"
    h3 = "Crude oil spikes amid Middle East tension and Red Sea shipping disruption - PTI"
    h4 = "RBI Monetary Policy Committee begins meeting; repo rate cut anticipated - CNBC"

    # 1. First headline should be novel
    hash1 = dedup.register(h1, now_ms)
    assert hash1 is not None
    assert dedup.cached_count == 1

    # 2. Exact match with different wire attribution should be dropped as duplicate
    assert dedup.is_duplicate(h2, now_ms) is True
    assert dedup.register(h2, now_ms) is None

    # 3. Near-duplicate rephrasing should be caught by token Jaccard similarity (> 0.60)
    assert dedup.is_duplicate(h3, now_ms) is True

    # 4. Unrelated story must be accepted
    hash4 = dedup.register(h4, now_ms)
    assert hash4 is not None
    assert dedup.cached_count == 2


def test_temporal_half_life_decay():
    """Verify exponential half-life decay (t_half = 45 mins)."""
    classifier = NewsClassifier(half_life_minutes=45.0)
    now_ms = 1_000_000_000.0

    # At t = 0 -> weight = 1.0
    w0 = classifier.compute_temporal_decay(now_ms, now_ms)
    assert abs(w0 - 1.0) < 0.001

    # At t = 45 mins (2,700,000 ms) -> weight ~= 0.50
    w45 = classifier.compute_temporal_decay(now_ms, now_ms + (45 * 60 * 1000.0))
    assert abs(w45 - 0.50) < 0.01

    # At t = 90 mins -> weight ~= 0.25
    w90 = classifier.compute_temporal_decay(now_ms, now_ms + (90 * 60 * 1000.0))
    assert abs(w90 - 0.25) < 0.01

    # At t = 180 mins (3 hours) -> weight < 0.07
    w180 = classifier.compute_temporal_decay(now_ms, now_ms + (180 * 60 * 1000.0))
    assert w180 < 0.07


def test_relevance_and_urgency_classification():
    """Verify domain tagging, NIFTY relevance score, and shock urgency."""
    classifier = NewsClassifier()
    now_ms = time.time() * 1000.0

    # 1. Critical Geopolitical Shock
    res1 = classifier.classify("Breaking: Missile strike reported on oil tanker in Strait of Hormuz", "Wire", now_ms)
    assert res1.category in ("GEOPOLITICS", "CRUDE_ENERGY")
    assert res1.urgency == "CRITICAL_SHOCK"
    assert res1.is_shock_trigger is True
    assert res1.raw_sentiment < 0.0

    # 2. RBI Rate Action
    res2 = classifier.classify("RBI MPC announces surprise 25 bps repo rate hike to curb food inflation", "Reuters", now_ms)
    assert res2.category == "CENTRAL_BANK_RBI"
    assert res2.relevance_score >= 0.70
    assert res2.raw_sentiment <= -0.50  # Rate hike is bearish for equities

    # 3. Routine Corporate News
    res3 = classifier.classify("Tata Motors passenger vehicle retail sales rise 4% in domestic market", "ET", now_ms)
    assert res3.urgency == "ROUTINE"
    assert res3.is_shock_trigger is False


def test_alert_engine_shock_stand_down():
    """Verify that CRITICAL_SHOCK engages 15-minute defensive stand-down."""
    alerts = AlertEngine(shock_cooldown_minutes=15.0)
    alerts.clear()

    now_ms = 1_000_000_000.0
    assert alerts.is_shock_stand_down_active(now_ms) is False

    # Trigger critical shock alert
    alt = alerts.trigger_alert(
        severity="CRITICAL_SHOCK",
        event_type="GEOPOLITICAL_MISSILE_STRIKE",
        headline="Missile strikes confirmed on shipping tankers",
        action_recommended="PAUSE_ENTRIES_15M"
    )
    assert alt.severity == "CRITICAL_SHOCK"

    # Must be active immediately after
    assert alerts.is_shock_stand_down_active() is True
    assert alerts.get_remaining_stand_down_sec() > 800.0

    # Cooldown check
    future_after_cooldown_ms = time.time() * 1000.0 + (16 * 60 * 1000.0)
    assert alerts.is_shock_stand_down_active(future_after_cooldown_ms) is False
    alerts.clear()


def test_market_intelligence_macro_shock_evaluation():
    """Verify that macro price spikes (Brent > 2.2% or VIX expansion) engage shock alerts."""
    mie = MarketIntelligenceEngine(alerts=AlertEngine(shock_cooldown_minutes=15.0))
    
    # 1. Normal mild moves -> No stand-down
    mie.evaluate_macro_shock(brent_pct_chg=0.5, vix_val=14.0, vix_pct_chg=1.2)
    assert mie.alerts.is_shock_stand_down_active() is False

    # 2. Severe Brent Crude spike (+2.8%) -> Triggers CRITICAL_SHOCK
    mie.evaluate_macro_shock(brent_pct_chg=2.8, vix_val=15.5, vix_pct_chg=3.0)
    assert mie.alerts.is_shock_stand_down_active() is True

    snap = mie.get_snapshot()
    assert snap.is_shock_stand_down_active is True
    assert snap.stand_down_reason is not None
