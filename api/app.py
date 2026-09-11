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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("APIServer")

# Active strategy instances
vol_strategy = VolatilityBreakoutStrategy()


# Background market tick handler
def on_new_tick(tick):
    """Processes incoming tick through strategies, ML engine, and MTM."""
    # Update position MTM
    position_tracker.mark_to_market(tick.symbol, tick.ltp)
    # Feed to rule-based strategy
    vol_strategy.on_tick(tick)
    # Feed to self-learning ML strategy
    adaptive_ml_strategy.on_tick(tick)


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

            # 2. Machine Learning Metrics
            ml_met = learning_engine.get_metrics()

            # 3. Quotes
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

