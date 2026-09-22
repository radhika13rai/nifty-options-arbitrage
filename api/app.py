"""
Core REST & WebSocket API Server.
Built on Starlette ASGI for zero-overhead, async-first performance.
Provides real-time endpoints for Android HUD and desktop trading monitoring.
"""

import asyncio
import dataclasses
import json
import logging
import time
from pathlib import Path
from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse, FileResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import os

from config import config
from api.auth import AuthenticationMiddleware
from database.db import db_manager
from market_data.orderbook import orderbook_manager
from market_data.websocket import market_feed
from market_data.instruments import instrument_registry
from ml.features import feature_extractor
from portfolio.positions import position_tracker
from portfolio.pnl import pnl_manager
from risk.kill_switch import kill_switch
from execution.paper_broker import paper_broker
from broker.interface import BrokerOrderRequest
from strategies.volatility_breakout import VolatilityBreakoutStrategy
from strategies.put_call_parity import put_call_parity_scanner
from strategies.box_spread import box_spread_scanner
from ml.learner import learning_engine
from ml.engine import adaptive_ml_strategy
from ml.dataset import ml_repo
from global_macro.indicators import macro_engine
from global_macro.news_feed import news_feed
from global_macro.multimodal_fusion import multimodal_fusion
from global_macro.dataset import macro_dataset
from global_macro.trainer import macro_trainer
from global_macro.poller import live_macro_poller
from execution.auto_engine import auto_engine
from scheduler.daily_routine import market_scheduler, MarketPhase
from analytics.greeks import calculate_all_greeks, calculate_implied_volatility
from analytics.strike_screener import strike_screener
from analytics.volatility_surface import volatility_surface
from market_intelligence import market_intelligence, alert_engine
from ml.champion_challenger import champion_challenger

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("APIServer")

# Active strategy instances
vol_strategy = VolatilityBreakoutStrategy()


# Background market tick handler
def on_new_tick(tick):
    """Processes incoming tick through strategies, ML engine, auto-execution, and MTM."""
    # 1. Update position MTM
    position_tracker.mark_to_market(tick.symbol, tick.ltp)
    
    # 2. Feed to rule-based strategy
    rule_signals = vol_strategy.on_tick(tick) or []

    # 3. Dynamic Ratchet Trailing Stop & Auto Position Management
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(auto_engine.on_tick(tick))
    except RuntimeError:
        pass

    # 4. Feed to self-learning ML strategy
    ml_signals = adaptive_ml_strategy.on_tick(tick) or []
    signals = rule_signals + ml_signals

    # 5. Autonomous signal execution dispatch
    if signals and auto_engine.is_auto_trading_enabled:
        for sig in signals:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(auto_engine.handle_signal(sig))
            except RuntimeError:
                pass


market_feed.subscribe(on_new_tick)


# --- REST Endpoints ---

async def health_check(request):
    """System health and mode status."""
    return JSONResponse({
        "status": "HEALTHY",
        "app": config.app_name,
        "version": config.version,
        "execution_mode": config.execution_mode,
        "live_trading_enabled": config.live_trading_enabled,
        "lot_size": config.market.nifty_lot_size,
        "kill_switch_engaged": kill_switch.is_engaged,
        "timestamp_ms": time.time() * 1000.0
    })


async def get_system_status(request):
    """Full operational telemetry."""
    pnl = pnl_manager.generate_report()
    ks = kill_switch.get_status()
    open_positions = position_tracker.get_open_positions()

    return JSONResponse({
        "execution_mode": config.execution_mode,
        "is_market_open": market_scheduler.is_trading_permitted,
        "market_phase": market_scheduler.current_phase.value,
        "real_nifty_spot": live_macro_poller.last_fetched_quotes.get("nifty", (23414.3, 0.0))[0],
        "kill_switch": {
            "is_engaged": ks.is_engaged,
            "reason": ks.reason,
            "triggered_by": ks.triggered_by
        },
        "capital": {
            "starting_cash": pnl.starting_cash,
            "current_cash": pnl.current_cash,
            "invested_capital": pnl.invested_capital,
            "total_portfolio_value": pnl.total_portfolio_value
        },
        "pnl": {
            "gross_pnl": pnl.total_gross_pnl,
            "total_friction": pnl.total_friction_inr,
            "net_pnl": pnl.net_pnl,
            "net_pnl_pct": pnl.net_pnl_percentage,
            "drawdown_pct": pnl.drawdown_pct,
            "daily_limit_breached": pnl.is_daily_limit_breached
        },
        "positions_count": len(open_positions),
        "lot_size": config.market.nifty_lot_size,
        "server_time": time.time()
    })


async def get_quotes(request):
    """Current orderbook snapshots for all tracked symbols."""
    snaps = orderbook_manager.get_all_snapshots()
    results = {}
    for sym, s in snaps.items():
        results[sym] = {
            "symbol": s.symbol,
            "best_bid": s.best_bid,
            "best_ask": s.best_ask,
            "mid_price": s.mid_price,
            "micro_price": s.micro_price,
            "spread": s.spread,
            "imbalance": s.imbalance,
            "age_ms": round(s.age_ms, 1),
            "bid_volume": s.total_bid_volume,
            "ask_volume": s.total_ask_volume
        }
    return JSONResponse(results)


async def get_positions(request):
    """Current open positions with MTM calculations."""
    positions = position_tracker.get_all_positions()
    return JSONResponse([
        {
            "symbol": p.symbol,
            "side": p.side,
            "quantity": p.quantity,
            "average_price": p.average_price,
            "current_price": p.current_price,
            "unrealized_pnl": p.unrealized_pnl,
            "realized_pnl": p.realized_pnl,
            "total_costs": p.total_costs,
            "is_open": p.is_open,
            "updated_at": p.updated_at
        }
        for p in positions
    ])


async def get_orders(request):
    """Recent order history from SQLite."""
    orders = await db_manager.get_recent_orders(limit=40)
    return JSONResponse(orders)


async def get_trades(request):
    """Recent executed trades with statutory fee breakdown."""
    trades = await db_manager.get_recent_trades(limit=40)
    return JSONResponse(trades)


async def get_pnl_report(request):
    """Detailed PnL and friction report."""
    pnl = pnl_manager.generate_report()
    return JSONResponse({
        "starting_cash": pnl.starting_cash,
        "current_cash": pnl.current_cash,
        "invested_capital": pnl.invested_capital,
        "total_portfolio_value": pnl.total_portfolio_value,
        "gross_realized_pnl": pnl.gross_realized_pnl,
        "gross_unrealized_pnl": pnl.gross_unrealized_pnl,
        "total_gross_pnl": pnl.total_gross_pnl,
        "total_friction_inr": pnl.total_friction_inr,
        "net_pnl": pnl.net_pnl,
        "net_pnl_percentage": pnl.net_pnl_percentage,
        "peak_capital": pnl.peak_capital,
        "drawdown_inr": pnl.drawdown_inr,
        "drawdown_pct": pnl.drawdown_pct,
        "is_daily_limit_breached": pnl.is_daily_limit_breached
    })


async def get_arbitrage_opportunities(request):
    """
    Evaluates current orderbooks for Put-Call Parity and Box Spreads.
    Explicitly labels whether signals are capital feasible under ₹3,000 capital.
    """
    spot_snap = orderbook_manager.get_snapshot("NIFTY_SPOT")
    if not spot_snap or spot_snap.mid_price <= 0:
        return JSONResponse({
            "status": "NO_MARKET_DATA",
            "detail": "NIFTY_SPOT market data unavailable; real-time spot price required for arbitrage detection",
            "timestamp": time.time(),
            "spot_price": None,
            "total_detected": 0,
            "capital_feasible_count": 0,
            "capital_infeasible_count": 0,
            "opportunities": []
        })

    spot_price = spot_snap.mid_price
    opportunities = []

    # 1. Dynamic ATM strike calculation and active weekly expiry resolution
    atm = round(spot_price / 50.0) * 50
    strikes = [atm + (i * 50) for i in range(-2, 3)]

    import datetime
    today = datetime.date.today()
    days_ahead = (3 - today.weekday()) % 7
    if days_ahead == 0 and datetime.datetime.now().hour >= 15 and datetime.datetime.now().minute >= 30:
        days_ahead = 7
    next_thursday = today + datetime.timedelta(days=days_ahead)
    expiry = next_thursday.strftime("%Y-%m-%d")

    # Check if active orderbooks exist with a specific expiry code
    all_snaps = orderbook_manager.get_all_snapshots()
    for s_name in all_snaps:
        if s_name.startswith("NIFTY_20") and ("_CE" in s_name or "_PE" in s_name):
            parts = s_name.split("_")
            if len(parts) >= 4:
                expiry = parts[1]
                break

    # 1. Scan Put-Call Parity across dynamic ATM strike pairs
    for k in strikes:
        ce_sym = f"NIFTY_{expiry}_{k}_CE"
        pe_sym = f"NIFTY_{expiry}_{k}_PE"
        sigs = put_call_parity_scanner.scan_strike(k, ce_sym, pe_sym, spot_price)
        for sig in sigs:
            opportunities.append({
                "strategy": sig.strategy_name,
                "symbol": sig.symbol,
                "action": sig.action,
                "is_capital_feasible": sig.is_capital_feasible,
                "infeasibility_reason": sig.infeasibility_reason,
                "metadata": sig.metadata
            })

    # 2. Scan Box Spreads
    for i in range(len(strikes) - 1):
        k1 = strikes[i]
        k2 = strikes[i+1]
        c1 = f"NIFTY_{expiry}_{k1}_CE"
        c2 = f"NIFTY_{expiry}_{k2}_CE"
        p1 = f"NIFTY_{expiry}_{k1}_PE"
        p2 = f"NIFTY_{expiry}_{k2}_PE"
        box_sig = box_spread_scanner.scan_box(k1, k2, c1, c2, p1, p2)
        if box_sig:
            opportunities.append({
                "strategy": box_sig.strategy_name,
                "symbol": box_sig.symbol,
                "action": box_sig.action,
                "is_capital_feasible": box_sig.is_capital_feasible,
                "infeasibility_reason": box_sig.infeasibility_reason,
                "metadata": box_sig.metadata
            })

    return JSONResponse({
        "status": "OK",
        "timestamp": time.time(),
        "spot_price": spot_price,
        "total_detected": len(opportunities),
        "capital_feasible_count": sum(1 for o in opportunities if o["is_capital_feasible"]),
        "capital_infeasible_count": sum(1 for o in opportunities if not o["is_capital_feasible"]),
        "opportunities": opportunities
    })


async def trigger_kill_switch(request):
    """Emergency manual engage or reset of kill switch."""
    try:
        data = await request.json()
    except Exception:
        data = {}

    action = data.get("action", "engage")
    if action == "engage":
        reason = data.get("reason", "Operator manual engagement from dashboard")
        res = kill_switch.engage(reason, "MANUAL_OPERATOR")
        await db_manager.record_audit_log("KILL_SWITCH_ENGAGED", "CRITICAL", "API", reason)
        return JSONResponse({"success": True, "status": res.__dict__})
    elif action == "reset":
        token = data.get("token") or data.get("signature") or ""
        nonce = data.get("nonce", "RESET_AUTHORIZATION")
        try:
            res = kill_switch.reset(token, nonce=nonce)
            await db_manager.record_audit_log("KILL_SWITCH_RESET", "WARNING", "API", "Cryptographic HMAC reset by operator")
            return JSONResponse({"success": True, "status": res.__dict__})
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=403)
    
    return JSONResponse({"error": "Unknown action"}, status_code=400)


async def reset_paper_account(request):
    """Resets paper account balance to ₹3,000 virtual capital."""
    pnl_manager.reset_balance(config.initial_capital_inr)
    position_tracker._positions.clear()
    await db_manager.record_audit_log("PAPER_ACCOUNT_RESET", "INFO", "API", "Account reset to ₹3,000")
    return JSONResponse({"success": True, "message": "Paper trading account reset to ₹3,000 initial capital."})


async def place_paper_order(request):
    """Allows manual or automated submission of a paper order."""
    try:
        body = await request.json()
        symbol = body.get("symbol")
        side = body.get("side", "BUY").upper()
        quantity = int(body.get("quantity", config.market.nifty_lot_size))
        price = float(body.get("price", 0.0))

        if not symbol:
            return JSONResponse({"error": "Symbol is required"}, status_code=400)

        order_req = BrokerOrderRequest(
            symbol=symbol,
            side=side,
            order_type="MARKET",
            quantity=quantity,
            price=price
        )

        resp = await paper_broker.place_order(order_req)
        return JSONResponse({
            "order_id": resp.order_id,
            "status": resp.status,
            "fill_price": resp.fill_price,
            "quantity": resp.filled_quantity,
            "charges_inr": resp.total_charges_inr,
            "rejection_reason": resp.rejection_reason
        })
    except Exception as e:
        logger.error(f"Error placing paper order: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# --- WebSocket Stream Endpoint ---

async def websocket_stream(websocket: WebSocket):
    """
    High-frequency WebSocket endpoint for the Android dashboard HUD.
    Pushes live orderbook, PnL, risk alerts, and arbitrage telemetry every 250ms.
    Enforces cryptographic or local authentication check prior to accepting connection.
    """
    from api.auth import is_websocket_authenticated
    if not is_websocket_authenticated(websocket):
        await websocket.close(code=1008, reason="Unauthorized: Valid API key required")
        return

    await websocket.accept()
    try:
        while True:
            # 1. PnL & Account
            pnl = pnl_manager.generate_report()
            ks = kill_switch.get_status()
            open_positions = position_tracker.get_open_positions()

            # 3. Machine Learning Metrics
            ml_met = learning_engine.get_metrics()

            # 4. Global Macro & News Intelligence Fusion
            macro_snap = macro_engine.get_snapshot()
            news_embs = news_feed.get_recent_embeddings()
            gm_fusion = multimodal_fusion.fuse(macro_snap, news_embs)
            mie_snap = market_intelligence.get_snapshot()
            recent_alerts = alert_engine.get_recent_alerts(limit=5)

            # 5. Quotes
            snaps = orderbook_manager.get_all_snapshots()
            quotes_data = {}
            for sym, s in snaps.items():
                quotes_data[sym] = {
                    "sym": s.symbol,
                    "bid": s.best_bid,
                    "ask": s.best_ask,
                    "mid": s.mid_price,
                    "micro": s.micro_price,
                    "spread": s.spread,
                    "imbalance": s.imbalance,
                    "age_ms": round(s.age_ms, 1)
                }

            nifty_quote = live_macro_poller.last_fetched_quotes.get("nifty", (23414.3, 0.29))
            is_market_open = market_scheduler.is_trading_permitted
            curr_phase = market_scheduler.current_phase.value

            payload = {
                "type": "STREAM_UPDATE",
                "timestamp": time.time(),
                "is_market_open": is_market_open,
                "market_phase": curr_phase,
                "real_nifty_spot": nifty_quote[0],
                "real_nifty_change_pct": nifty_quote[1],
                "dhan_status": "CONNECTED" if getattr(market_feed, "is_live_connected", False) else "STANDBY_FALLBACK",
                "kill_switch": {
                    "is_engaged": ks.is_engaged,
                    "reason": ks.reason
                },
                "pnl": {
                    "cash": pnl.current_cash,
                    "invested": pnl.invested_capital,
                    "total_val": pnl.total_portfolio_value,
                    "gross_pnl": pnl.total_gross_pnl,
                    "fees": pnl.total_friction_inr,
                    "net_pnl": pnl.net_pnl,
                    "net_pct": pnl.net_pnl_percentage,
                    "drawdown_pct": pnl.drawdown_pct
                },
                "ml": {
                    "epoch": ml_met.epoch,
                    "regime": ml_met.regime,
                    "confidence": ml_met.confidence_score,
                    "win_rate": ml_met.expected_win_rate,
                    "hurdle_inr": ml_met.statutory_hurdle_inr,
                    "rls_steps": ml_met.rls_steps
                },
                "global_macro": {
                    "bias": gm_fusion.global_bias,
                    "fear_index": gm_fusion.geopolitical_fear_index,
                    "expected_gap": gm_fusion.expected_nifty_gap_points,
                    "posture": gm_fusion.recommended_options_posture,
                    "crude": macro_snap.brent_crude_usd,
                    "crude_chg": macro_snap.brent_change_pct,
                    "dxy": macro_snap.dollar_index_dxy,
                    "gift_nifty_gap": macro_snap.gift_nifty_gap_pts,
                    "synthesis": gm_fusion.synthesis_reason
                },
                "market_intelligence": {
                    "news_sentiment": mie_snap.news_sentiment_score,
                    "geopolitical_tension": mie_snap.geopolitical_tension_index,
                    "stand_down_active": mie_snap.is_shock_stand_down_active,
                    "stand_down_remaining_sec": mie_snap.stand_down_remaining_sec,
                    "stand_down_reason": mie_snap.stand_down_reason,
                    "alerts": recent_alerts,
                    "headlines": mie_snap.recent_headlines[:5]
                },
                "champion_challenger": {
                    "champion_id": champion_challenger.champion.model_id,
                    "champion_sharpe": champion_challenger.champion.metrics.sharpe_ratio,
                    "champion_win_rate": champion_challenger.champion.metrics.win_rate,
                    "has_challenger": champion_challenger.challenger is not None,
                    "challenger_id": champion_challenger.challenger.model_id if champion_challenger.challenger else None,
                    "promotions_count": len(champion_challenger.promotion_history)
                },
                "auto_trade": auto_engine.get_status(),
                "scheduler": market_scheduler.get_status(),
                "positions": [
                    {
                        "symbol": p.symbol,
                        "side": p.side,
                        "quantity": p.quantity,
                        "avg": p.average_price,
                        "ltp": p.current_price,
                        "unrealized": p.unrealized_pnl,
                        "costs": p.total_costs
                    }
                    for p in open_positions
                ],
                "quotes": quotes_data
            }

            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")


# --- ML Endpoints ---

async def get_ml_status(request):
    """Returns real-time ML metrics, market regime, and adaptation state."""
    m = learning_engine.get_metrics()
    return JSONResponse({
        "epoch": m.epoch,
        "regime": m.regime,
        "confidence_score": m.confidence_score,
        "expected_win_rate": m.expected_win_rate,
        "sample_win_rate": round(m.sample_win_rate, 2),
        "rls_steps": m.rls_steps,
        "statutory_hurdle_inr": m.statutory_hurdle_inr,
        "last_update_time": m.last_update_time
    })


async def trigger_ml_retrain(request):
    """Triggers an online walk-forward adaptation step using empirical round-trip trade P&L."""
    formatted = []

    # 1. Primary source: Verified round-trip trades from AutoExecutionEngine history
    if auto_engine._trade_history:
        for t in auto_engine._trade_history[-25:]:
            sym = t.get("symbol", "")
            snap = orderbook_manager.get_snapshot(sym)
            fv = feature_extractor.extract_features(snap).to_list() if snap else [0.0, 0.0, 0.01, 0.0, 0.0, 0.0, 0.02, 0.5]
            formatted.append({
                "features": fv,
                "option_type": "CE" if "CE" in sym else "PE",
                "points_moved": float(t.get("points_moved", 0.0)),
                "net_pnl": float(t.get("net_pnl", 0.0))
            })

    # 2. Secondary source: Pair BUY and SELL executions from DB into realized round-trips
    if not formatted:
        trades = await db_manager.get_recent_trades(limit=50)
        by_symbol = {}
        for t in reversed(trades):
            sym = str(t.get("symbol", ""))
            by_symbol.setdefault(sym, []).append(t)

        for sym, sym_trades in by_symbol.items():
            buys = [t for t in sym_trades if t.get("side") == "BUY"]
            sells = [t for t in sym_trades if t.get("side") == "SELL"]
            for b, s in zip(buys, sells):
                b_price = float(b.get("price", 0.0))
                s_price = float(s.get("price", 0.0))
                qty = int(min(b.get("quantity", 65), s.get("quantity", 65)))
                pts = round(s_price - b_price, 2)
                gross = round(pts * qty, 2)
                fees = float(b.get("total_costs", 24.8)) + float(s.get("total_costs", 27.2))
                net = round(gross - fees, 2)
                snap = orderbook_manager.get_snapshot(sym)
                fv = feature_extractor.extract_features(snap).to_list() if snap else [0.0, 0.0, 0.01, 0.0, 0.0, 0.0, 0.02, 0.5]
                formatted.append({
                    "features": fv,
                    "option_type": "CE" if "CE" in sym else "PE",
                    "points_moved": pts,
                    "net_pnl": net
                })

    # 3. Fallback: Microstructure sampling from active snapshots with exact round-trip cost hurdle
    if not formatted:
        snapshots = orderbook_manager.get_all_snapshots()
        for sym, snap in list(snapshots.items())[:10]:
            fv = feature_extractor.extract_features(snap).to_list()
            diff = round(snap.micro_price - snap.mid_price, 2)
            rt = cost_engine.calculate_round_trip("BUY", snap.mid_price, max(0.05, snap.micro_price), config.market.nifty_lot_size)
            formatted.append({
                "features": fv,
                "option_type": "CE" if "CE" in sym else "PE",
                "points_moved": diff,
                "net_pnl": round((diff * config.market.nifty_lot_size) - rt.total_friction, 2)
            })

    # 4. Fallback baseline if orderbooks empty
    if not formatted:
        rt = cost_engine.calculate_round_trip("BUY", 25.0, 25.0, config.market.nifty_lot_size)
        formatted = [{
            "features": [0.0, 0.0, 0.01, 0.0, 0.0, 0.0, 0.02, 0.5],
            "option_type": "CE",
            "points_moved": 0.0,
            "net_pnl": -rt.total_friction
        }]

    metrics = learning_engine.run_daily_adaptation_step(formatted)
    return JSONResponse({
        "success": True,
        "message": f"Walk-forward adaptation complete. Advanced to Epoch {metrics.epoch}.",
        "epoch": metrics.epoch,
        "regime": metrics.regime,
        "confidence": metrics.confidence_score,
        "rls_steps": metrics.rls_steps,
        "samples_trained": len(formatted)
    })


# --- Global Macro & Geopolitics Endpoints ---

async def get_global_macro_status(request):
    """Returns real-time global macro indicators, news sentiment, and multimodal fusion."""
    snap = macro_engine.get_snapshot()
    embs = news_feed.get_recent_embeddings()
    fusion = multimodal_fusion.fuse(snap, embs)
    headlines = news_feed.get_recent_items(limit=8)
    return JSONResponse({
        "macro": {
            "brent_crude_usd": snap.brent_crude_usd,
            "brent_change_pct": snap.brent_change_pct,
            "dollar_index_dxy": snap.dollar_index_dxy,
            "dxy_change_pct": snap.dxy_change_pct,
            "gift_nifty_points": snap.gift_nifty_points,
            "gift_nifty_gap_pts": snap.gift_nifty_gap_pts,
            "us_vix": snap.us_vix,
            "us_vix_change_pct": snap.us_vix_change_pct,
            "sp500_change_pct": snap.sp500_change_pct
        },
        "fusion": {
            "global_bias": fusion.global_bias,
            "geopolitical_fear_index": fusion.geopolitical_fear_index,
            "expected_nifty_gap_points": fusion.expected_nifty_gap_points,
            "iv_expansion_probability": fusion.iv_expansion_probability,
            "recommended_options_posture": fusion.recommended_options_posture,
            "confidence_score": fusion.confidence_score,
            "synthesis_reason": fusion.synthesis_reason
        },
        "headlines": headlines
    })


async def set_global_scenario(request):
    """Applies a world event scenario (e.g. MIDDLE_EAST_WAR_CRISIS, GLOBAL_DEESCALATION_RELIEF)."""
    try:
        body = await request.json()
        scenario = body.get("scenario", "NEUTRAL")
        macro_snap = macro_engine.apply_scenario(scenario)
        news_embs = news_feed.load_scenario(scenario)
        fusion = multimodal_fusion.fuse(macro_snap, news_embs)
        return JSONResponse({
            "success": True,
            "scenario": scenario,
            "global_bias": fusion.global_bias,
            "geopolitical_fear_index": fusion.geopolitical_fear_index,
            "recommended_options_posture": fusion.recommended_options_posture,
            "expected_nifty_gap_points": fusion.expected_nifty_gap_points,
            "synthesis_reason": fusion.synthesis_reason
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def trigger_macro_train(request):
    """Triggers supervised training of multimodal macro & news fusion weights."""
    try:
        res = macro_trainer.train_on_dataset()
        return JSONResponse({
            "success": True,
            "epoch": res.epoch,
            "num_samples": res.num_samples,
            "macro_weights": res.macro_weights,
            "news_weights": res.news_weights,
            "train_mse": res.train_mse,
            "directional_accuracy": res.directional_accuracy,
            "cross_val_mae": res.cross_val_mae,
            "duration_ms": res.training_duration_ms,
            "message": f"Multimodal training complete: {res.directional_accuracy*100:.1f}% directional accuracy on {res.num_samples} historical shock events."
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def get_macro_dataset(request):
    """Returns historical global macro & news samples."""
    samples = macro_dataset.get_all_samples()
    if not samples:
        macro_dataset.seed_historical_events()
        samples = macro_dataset.get_all_samples()
    return JSONResponse({
        "count": len(samples),
        "samples": [
            {
                "id": s.sample_id,
                "event": s.event_name,
                "headline": s.headline,
                "brent": s.brent_crude,
                "brent_chg": s.brent_change_pct,
                "dxy": s.dollar_index_dxy,
                "gift_gap": s.gift_nifty_gap_pts,
                "actual_gap": s.actual_nifty_open_gap,
                "direction": s.actual_direction,
                "best_side": s.best_option_side,
                "net_pnl": s.net_pnl_1lot
            }
            for s in samples
        ]
    })


async def get_auto_trade_status(request):
    """Returns autonomous trading engine state and active managed trades."""
    return JSONResponse(auto_engine.get_status())


async def toggle_auto_trade(request):
    """Enables or disables autonomous trade execution."""
    try:
        body = await request.json()
        enable = body.get("enabled", True)
        if enable:
            auto_engine.enable()
        else:
            auto_engine.disable()
        return JSONResponse({"success": True, "is_enabled": auto_engine.is_auto_trading_enabled})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def square_off_all(request):
    """Mandatory manual or scheduled intraday square-off."""
    results = await auto_engine.mandatory_intraday_square_off()
    return JSONResponse({"success": True, "closed_trades": results})


async def poll_macro_now(request):
    """Triggers an immediate live macro and RSS refresh."""
    res = await live_macro_poller.poll_once()
    return JSONResponse(res)


async def get_poller_status(request):
    """Returns poller telemetry."""
    return JSONResponse(live_macro_poller.get_status())


async def get_scheduler_status(request):
    """Returns intraday routine scheduler telemetry."""
    return JSONResponse(market_scheduler.get_status())


async def advance_scheduler_phase(request):
    """Advances or sets the market routine phase (simulated or manual override)."""
    try:
        body = await request.json()
        phase_str = body.get("phase")
        if not phase_str:
            return JSONResponse({"error": "Phase is required"}, status_code=400)
        target_phase = MarketPhase(phase_str)
        market_scheduler.set_simulated_mode(True)
        res = await market_scheduler.execute_phase_transition(target_phase)
        return JSONResponse({"success": True, "transition": res, "status": market_scheduler.get_status()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def get_drift_status(request):
    """Returns AI model drift telemetry and rollback status."""
    from ml.drift_guard import drift_guard
    status = drift_guard.check_drift()
    return JSONResponse(dataclasses.asdict(status))


async def get_intelligence_snapshot(request):
    """Returns real-time Market Intelligence snapshot (deduplicated, classified headlines & alerts)."""
    snap = market_intelligence.get_snapshot()
    return JSONResponse(dataclasses.asdict(snap))


async def get_intelligence_alerts(request):
    """Returns active market alerts and shock stand-down cooldown."""
    return JSONResponse({
        "stand_down_active": alert_engine.is_shock_stand_down_active(),
        "stand_down_remaining_sec": alert_engine.get_remaining_stand_down_sec(),
        "stand_down_reason": alert_engine.get_last_shock_reason(),
        "alerts": alert_engine.get_recent_alerts(limit=30)
    })


async def post_intelligence_headline(request):
    """Ingests, deduplicates, classifies, and evaluates a news wire headline."""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    headline = str(data.get("headline", "")).strip()
    if not headline:
        return JSONResponse({"error": "Headline is required"}, status_code=400)

    source = str(data.get("source", "Manual Wire"))
    classified = market_intelligence.process_incoming_headline(headline, source=source)
    is_dup = classified is None

    return JSONResponse({
        "status": "DUPLICATE_DROPPED" if is_dup else "PROCESSED",
        "is_duplicate": is_dup,
        "classification": dataclasses.asdict(classified) if classified else None,
        "current_snapshot": dataclasses.asdict(market_intelligence.get_snapshot())
    })


async def get_learning_episodes(request):
    """Returns reconciled closed-loop training episodes from SQLite."""
    limit = int(request.query_params.get("limit", 50))
    episodes = await db_manager.get_learning_episodes(limit=limit)
    total = await db_manager.get_total_learning_episodes_count()
    return JSONResponse({
        "status": "SUCCESS",
        "count": len(episodes),
        "total_recorded_episodes": total,
        "episodes": episodes
    })


async def get_champion_status(request):
    """Returns Champion and Challenger model parameters, OOS metrics, and promotion history."""
    return JSONResponse({
        "champion": dataclasses.asdict(champion_challenger.champion),
        "challenger": dataclasses.asdict(champion_challenger.challenger) if champion_challenger.challenger else None,
        "promotion_history": champion_challenger.promotion_history
    })


async def evaluate_challenger_endpoint(request):
    """
    Trains Challenger model on reconciled historical episodes with 70/30 OOS split
    and runs the strict institutional promotion gate.
    """
    episodes = await db_manager.get_learning_episodes(limit=500)
    if not episodes:
        from ml.dataset import ml_repo
        episodes = ml_repo.get_all_episodes()

    challenger = champion_challenger.train_challenger(episodes)
    promo_report = champion_challenger.evaluate_and_promote()
    return JSONResponse({
        "status": "SUCCESS",
        "training_samples": len(episodes),
        "challenger_created": challenger is not None,
        "report": promo_report
    })


async def get_stream_status(request):
    """Returns continuous live market data stream health."""
    from market_data.stream import market_streamer
    health = market_streamer.get_health()
    return JSONResponse(dataclasses.asdict(health))


async def get_slippage_status(request):
    """Returns empirical microstructure slippage and queue priority telemetry."""
    from costs.slippage import slippage_model
    return JSONResponse(slippage_model.get_telemetry())


_soak_task = None


async def get_soak_status(request):
    """Returns continuous paper soak runner telemetry and health scorecard."""
    from simulation.soak_runner import soak_runner
    return JSONResponse(soak_runner.get_metrics_dict())


async def start_soak_runner(request):
    """Launches continuous paper soak runner in background task."""
    global _soak_task
    from simulation.soak_runner import soak_runner
    if _soak_task and not _soak_task.done():
        return JSONResponse({"status": "ALREADY_RUNNING", "message": "Soak runner is already executing."})

    try:
        body = await request.json()
    except Exception:
        body = {}

    days = int(body.get("days", 30))
    interval = float(body.get("interval_sec", 0.05))

    _soak_task = asyncio.create_task(soak_runner.run(max_days=days, interval_sec=interval))
    return JSONResponse({"status": "STARTED", "target_days": days, "interval_sec": interval})


async def stop_soak_runner(request):
    """Stops background paper soak runner."""
    from simulation.soak_runner import soak_runner
    soak_runner.stop()
    return JSONResponse({"status": "STOP_REQUESTED"})


async def reset_soak_runner(request):
    """Resets paper soak runner state and metrics."""
    from simulation.soak_runner import soak_runner
    soak_runner.reset()
    return JSONResponse({"status": "RESET_COMPLETE", "metrics": soak_runner.get_metrics_dict()})


# --- Black-Scholes Greeks & Strike Screener Handlers ---

async def calculate_greeks_endpoint(request):
    """Calculates Black-Scholes Greeks and theoretical pricing."""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    try:
        spot = float(data.get("spot", 24500.0))
        strike = float(data.get("strike", 24700.0))
        days = float(data.get("days_to_expiry", 4.0))
        iv = float(data.get("iv", 0.155))
        opt_type = str(data.get("option_type", "CE"))
        rate = float(data.get("risk_free_rate", config.market.risk_free_rate))
        lot_size = int(data.get("lot_size", config.market.nifty_lot_size))

        greeks = calculate_all_greeks(
            spot=spot,
            strike=strike,
            days_to_expiry=days,
            iv=iv,
            option_type=opt_type,
            risk_free_rate=rate,
            lot_size=lot_size
        )
        return JSONResponse({"status": "SUCCESS", "greeks": greeks.to_dict()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def calculate_iv_endpoint(request):
    """Solves for Implied Volatility (IV) given option market price."""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    try:
        market_price = float(data.get("market_price", 0.0))
        spot = float(data.get("spot", 24500.0))
        strike = float(data.get("strike", 24700.0))
        days = float(data.get("days_to_expiry", 4.0))
        opt_type = str(data.get("option_type", "CE"))
        rate = float(data.get("risk_free_rate", config.market.risk_free_rate))

        t_years = max(0.0001, days / 365.0)
        solved_iv = calculate_implied_volatility(
            market_price=market_price,
            spot=spot,
            strike=strike,
            time_to_expiry_years=t_years,
            risk_free_rate=rate,
            option_type=opt_type
        )
        if solved_iv is None:
            return JSONResponse(
                {"status": "ERROR", "message": "No arbitrage-free IV solution found for given price and parameters"},
                status_code=422
            )

        return JSONResponse({
            "status": "SUCCESS",
            "implied_volatility": solved_iv,
            "iv_pct": round(solved_iv * 100.0, 2),
            "inputs": {
                "market_price": market_price,
                "spot": spot,
                "strike": strike,
                "days_to_expiry": days,
                "option_type": opt_type
            }
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def strike_screener_endpoint(request):
    """Screens option chain for micro-capital compliant OTM strikes."""
    if request.method == "POST":
        try:
            params = await request.json()
        except Exception:
            params = {}
    else:
        params = dict(request.query_params)

    try:
        spot = float(params.get("spot", 24500.0))
        days = float(params.get("days_to_expiry", 4.0))
        iv = float(params.get("iv", 0.155))
        bias = str(params.get("bias", "BULLISH"))
        use_skew = str(params.get("use_skew", "false")).lower() in ("true", "1", "yes")

        screened = strike_screener.generate_and_screen(
            spot=spot,
            days_to_expiry=days,
            iv=iv,
            directional_bias=bias,
            use_skew=use_skew
        )
        eligible = [s for s in screened if s.is_eligible]
        best = eligible[0] if eligible else None

        return JSONResponse({
            "status": "SUCCESS",
            "spot": spot,
            "directional_bias": bias,
            "days_to_expiry": days,
            "iv": iv,
            "best_strike": best.to_dict() if best else None,
            "eligible_count": len(eligible),
            "eligible_strikes": [s.to_dict() for s in eligible],
            "total_screened": len(screened)
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def get_volatility_skew_endpoint(request):
    """Returns parametric Volatility Skew curve across strikes."""
    params = dict(request.query_params)
    try:
        spot = float(params.get("spot", 24500.0))
        days = float(params.get("days_to_expiry", 4.0))
        atm_override = float(params["atm_iv"]) if "atm_iv" in params else None

        skew_points = volatility_surface.generate_skew_curve(
            spot=spot,
            days_to_expiry=days,
            atm_iv_override=atm_override
        )
        return JSONResponse({
            "status": "SUCCESS",
            "spot": spot,
            "days_to_expiry": days,
            "base_atm_iv": volatility_surface.base_atm_iv,
            "skew_slope": volatility_surface.skew_slope,
            "smile_curvature": volatility_surface.smile_curvature,
            "points": [dataclasses.asdict(p) for p in skew_points]
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def get_volatility_surface_endpoint(request):
    """Returns 2D grid matrix of implied volatility across strikes and expiries."""
    params = dict(request.query_params)
    try:
        spot = float(params.get("spot", 24500.0))
        grid = volatility_surface.get_surface_grid(spot=spot)
        return JSONResponse({"status": "SUCCESS", "surface": grid})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def calibrate_volatility_endpoint(request):
    """Calibrates skew parameters (ATM, slope, curvature) from orderbook quotes."""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    try:
        quotes = data.get("quotes", [])
        spot = float(data.get("spot", 24500.0))
        days = float(data.get("days_to_expiry", 4.0))

        result = volatility_surface.calibrate_from_market_chain(quotes, spot, days)
        return JSONResponse({"status": "SUCCESS", "calibration": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# --- Dashboard HTML Handler ---

async def serve_dashboard(request):
    """Serves mobile-first Android-responsive Trading HUD."""
    html_path = config.base_dir / "dashboard" / "index.html"
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        key = os.environ.get("SERQ_API_KEY", "")
        if key:
            injection = f'<script>window.__SERQ_CONFIG__ = {{ apiKey: "{key}" }};</script>'
            content = content.replace("</head>", f"{injection}\n</head>")
        return HTMLResponse(content)
    return HTMLResponse("<h1>Dashboard loading...</h1>")


# --- Starlette App Factory ---

routes = [
    Route("/health", health_check, methods=["GET"]),
    Route("/api/status", get_system_status, methods=["GET"]),
    Route("/api/quotes", get_quotes, methods=["GET"]),
    Route("/api/positions", get_positions, methods=["GET"]),
    Route("/api/orders", get_orders, methods=["GET"]),
    Route("/api/trades", get_trades, methods=["GET"]),
    Route("/api/pnl", get_pnl_report, methods=["GET"]),
    Route("/api/arbitrage/opportunities", get_arbitrage_opportunities, methods=["GET"]),
    Route("/api/ml/status", get_ml_status, methods=["GET"]),
    Route("/api/ml/retrain", trigger_ml_retrain, methods=["POST"]),
    Route("/api/ml/drift", get_drift_status, methods=["GET"]),
    Route("/api/intelligence/snapshot", get_intelligence_snapshot, methods=["GET"]),
    Route("/api/intelligence/alerts", get_intelligence_alerts, methods=["GET"]),
    Route("/api/intelligence/headline", post_intelligence_headline, methods=["POST"]),
    Route("/api/learning/episodes", get_learning_episodes, methods=["GET"]),
    Route("/api/learning/champion", get_champion_status, methods=["GET"]),
    Route("/api/learning/evaluate-challenger", evaluate_challenger_endpoint, methods=["POST"]),
    Route("/api/market-stream/status", get_stream_status, methods=["GET"]),
    Route("/api/costs/slippage", get_slippage_status, methods=["GET"]),
    Route("/api/soak/status", get_soak_status, methods=["GET"]),
    Route("/api/soak/start", start_soak_runner, methods=["POST"]),
    Route("/api/soak/stop", stop_soak_runner, methods=["POST"]),
    Route("/api/soak/reset", reset_soak_runner, methods=["POST"]),
    Route("/api/global-macro/status", get_global_macro_status, methods=["GET"]),
    Route("/api/global-macro/scenario", set_global_scenario, methods=["POST"]),
    Route("/api/global-macro/train", trigger_macro_train, methods=["POST"]),
    Route("/api/global-macro/dataset", get_macro_dataset, methods=["GET"]),
    Route("/api/global-macro/poll", poll_macro_now, methods=["POST"]),
    Route("/api/global-macro/poller-status", get_poller_status, methods=["GET"]),
    Route("/api/scheduler/status", get_scheduler_status, methods=["GET"]),
    Route("/api/scheduler/advance", advance_scheduler_phase, methods=["POST"]),
    Route("/api/auto-trade/status", get_auto_trade_status, methods=["GET"]),
    Route("/api/auto-trade/toggle", toggle_auto_trade, methods=["POST"]),
    Route("/api/auto-trade/square-off", square_off_all, methods=["POST"]),
    Route("/api/kill-switch", trigger_kill_switch, methods=["POST"]),
    Route("/api/paper/reset", reset_paper_account, methods=["POST"]),
    Route("/api/paper/order", place_paper_order, methods=["POST"]),
    Route("/api/greeks/calculate", calculate_greeks_endpoint, methods=["POST"]),
    Route("/api/greeks/iv", calculate_iv_endpoint, methods=["POST"]),
    Route("/api/greeks/screener", strike_screener_endpoint, methods=["GET", "POST"]),
    Route("/api/greeks/skew", get_volatility_skew_endpoint, methods=["GET"]),
    Route("/api/greeks/surface", get_volatility_surface_endpoint, methods=["GET"]),
    Route("/api/greeks/calibrate", calibrate_volatility_endpoint, methods=["POST"]),
    WebSocketRoute("/ws/stream", websocket_stream),
    Route("/", serve_dashboard, methods=["GET"]),
]

allowed_origins_env = os.environ.get("SERQ_ALLOWED_ORIGINS", "")
if allowed_origins_env:
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
else:
    allowed_origins = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

middleware = [
    Middleware(AuthenticationMiddleware),
    Middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    ),
]

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: Starlette):
    """Initializes SQLite schema and starts background services."""
    logger.info("Initializing database...")
    await db_manager.async_init_db()
    logger.info("Starting background market feed...")
    await market_feed.start()
    logger.info("Starting live global macro & RSS poller...")
    await live_macro_poller.start()
    logger.info("Starting market routine scheduler...")
    await market_scheduler.start()
    logger.info("System startup complete. Ready for paper trading.")
    yield
    logger.info("Stopping market scheduler...")
    await market_scheduler.stop()
    logger.info("Stopping live macro poller...")
    await live_macro_poller.stop()
    logger.info("Stopping market feed...")
    await market_feed.stop()
    logger.info("System shutdown complete.")


debug_mode = os.environ.get("SERQ_DEBUG", "false").lower() in ("true", "1")
app = Starlette(debug=debug_mode, routes=routes, middleware=middleware, lifespan=lifespan)

