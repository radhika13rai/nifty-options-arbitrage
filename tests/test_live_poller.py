"""Unit tests for Live Global Macro & News Poller."""
import asyncio
import pytest
from global_macro.poller import LiveMacroPoller, categorize_headline
from global_macro.indicators import macro_engine


def test_headline_categorization():
    assert categorize_headline("Brent crude surges past $90 as OPEC meets") == "CRUDE_ENERGY"
    assert categorize_headline("US Fed holds interest rate steady; Powell cites CPI") == "CENTRAL_BANK"
    assert categorize_headline("New tariff sanctions announced on steel imports") == "TRADE_TARIFFS"
    assert categorize_headline("Nifty 50 approaches record high on strong DII buying") == "DOMESTIC_INDIA"
    assert categorize_headline("Military tensions escalate along disputed border") == "GEOPOLITICS"


def test_live_poller_mock_poll():
    async def _run():
        poller = LiveMacroPoller(poll_interval_sec=30.0)
        poller.enable_mock_mode(True)
        
        res = await poller.poll_once()
        assert res["status"] == "SUCCESS"
        assert res["brent"] == 84.50
        assert res["dxy"] == 103.95
        assert "posture" in res
        assert "fear_index" in res
        assert res["news_count"] >= 2
        
        # Verify macro_engine was updated
        snap = macro_engine.get_snapshot()
        assert snap.brent_crude_usd == 84.50
        
        # Status verification
        status = poller.get_status()
        assert status["poll_count"] == 1
        assert status["successful_poll_count"] == 1
        assert status["last_error"] is None
        assert len(status["quotes_snapshot"]) == 5

    asyncio.run(_run())


def test_live_poller_error_resilience(monkeypatch):
    async def _run():
        poller = LiveMacroPoller(poll_interval_sec=30.0)
        
        # Force exception during quotes fetch
        def bad_fetch():
            raise ConnectionResetError("Simulated socket drop")
            
        monkeypatch.setattr(poller, "_fetch_all_yahoo_quotes", bad_fetch)
        
        res = await poller.poll_once()
        assert res["status"] == "ERROR"
        assert "Simulated socket drop" in res["error"]
        
        status = poller.get_status()
        assert status["last_error"] is not None

    asyncio.run(_run())
