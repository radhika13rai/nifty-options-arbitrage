"""
Core REST & WebSocket API Server.
Built on Starlette ASGI for zero-overhead, async-first performance.
Provides real-time endpoints for Android HUD and desktop trading monitoring.
"""

import asyncio
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

from config import config
from database.db import db_manager
from market_data.orderbook import orderbook_manager
from market_data.websocket import market_feed
from market_data.instruments import instrument_registry
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
from execution.auto_engine import auto_engine

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
    vol_strategy.on_tick(tick)

    # 3. Dynamic Ratchet Trailing Stop & Auto Position Management
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(auto_engine.on_tick(tick))
    except RuntimeError:
        pass

    # 4. Feed to self-learning ML strategy
    signals = adaptive_ml_strategy.on_tick(tick)

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
    opportunities = []
    spot_snap = orderbook_manager.get_snapshot("NIFTY_SPOT")
    spot_price = spot_snap.mid_price if spot_snap else 24500.0

    # 1. Scan Put-Call Parity across active strike pairs
    strikes = [24400, 24450, 24500, 24550, 24600]
    for k in strikes:
        ce_sym = f"NIFTY_2026-09-24_{k}_CE"
        pe_sym = f"NIFTY_2026-09-24_{k}_PE"
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
        c1 = f"NIFTY_2026-09-24_{k1}_CE"
        c2 = f"NIFTY_2026-09-24_{k2}_CE"
        p1 = f"NIFTY_2026-09-24_{k1}_PE"
        p2 = f"NIFTY_2026-09-24_{k2}_PE"
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
        token = data.get("token", "")
        if token != "CONFIRM_RESET":
            return JSONResponse({"error": "Invalid reset token. Provide 'CONFIRM_RESET'."}, status_code=400)
        res = kill_switch.reset("CONFIRM_RESET")
        await db_manager.record_audit_log("KILL_SWITCH_RESET", "WARNING", "API", "Manual reset by operator")
        return JSONResponse({"success": True, "status": res.__dict__})
    
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
    """
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

            payload = {
                "type": "STREAM_UPDATE",
                "timestamp": time.time(),
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
                "auto_trade": auto_engine.get_status(),
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
    """Triggers an online walk-forward adaptation step."""
    trades = await db_manager.get_recent_trades(limit=25)
    formatted = [
        {
            "features": [0.6, 0.3, 0.01, 0.2, 0.05, 0.1, 0.2, 0.4],
            "option_type": "CE" if str(t.get("symbol", "")).endswith("_CE") else "PE",
            "points_moved": 3.0 if t.get("net_cash_flow", 0) > 0 else -1.6,
            "net_pnl": t.get("net_cash_flow", 0)
        }
        for t in trades
    ]
    metrics = learning_engine.run_daily_adaptation_step(formatted)
    return JSONResponse({
        "success": True,
        "message": f"Walk-forward adaptation complete. Advanced to Epoch {metrics.epoch}.",
        "epoch": metrics.epoch,
        "regime": metrics.regime,
        "confidence": metrics.confidence_score,
        "rls_steps": metrics.rls_steps
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


# --- Dashboard HTML Handler ---

async def serve_dashboard(request):
    """Serves mobile-first Android-responsive Trading HUD."""
    html_path = config.base_dir / "dashboard" / "index.html"
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
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
    Route("/api/global-macro/status", get_global_macro_status, methods=["GET"]),
    Route("/api/global-macro/scenario", set_global_scenario, methods=["POST"]),
    Route("/api/global-macro/train", trigger_macro_train, methods=["POST"]),
    Route("/api/global-macro/dataset", get_macro_dataset, methods=["GET"]),
    Route("/api/auto-trade/status", get_auto_trade_status, methods=["GET"]),
    Route("/api/auto-trade/toggle", toggle_auto_trade, methods=["POST"]),
    Route("/api/auto-trade/square-off", square_off_all, methods=["POST"]),
    Route("/api/kill-switch", trigger_kill_switch, methods=["POST"]),
    Route("/api/paper/reset", reset_paper_account, methods=["POST"]),
    Route("/api/paper/order", place_paper_order, methods=["POST"]),
    WebSocketRoute("/ws/stream", websocket_stream),
    Route("/", serve_dashboard, methods=["GET"]),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: Starlette):
    """Initializes SQLite schema and starts background market feed."""
    logger.info("Initializing database...")
    await db_manager.async_init_db()
    logger.info("Starting background market feed...")
    await market_feed.start()
    logger.info("System startup complete. Ready for paper trading.")
    yield
    logger.info("Stopping market feed...")
    await market_feed.stop()
    logger.info("System shutdown complete.")


app = Starlette(debug=True, routes=routes, middleware=middleware, lifespan=lifespan)

