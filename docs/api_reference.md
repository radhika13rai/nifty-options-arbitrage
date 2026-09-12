# REST API & WebSocket Streaming Reference

## Base URL
`http://localhost:8000`

---

## 1. REST Endpoints

### `GET /health`
Returns system health, execution mode, and active lot size.
```json
{
  "status": "HEALTHY",
  "app": "NIFTY Options Arbitrage & Research Engine",
  "version": "1.0.0",
  "execution_mode": "PAPER_TRADING",
  "live_trading_enabled": false,
  "lot_size": 65,
  "kill_switch_engaged": false,
  "timestamp_ms": 1789094902799.37
}
```

### `GET /api/status`
Returns full capital, P&L, risk state, and position counts.

### `GET /api/quotes`
Returns instantaneous Level-2 orderbook snapshots for NIFTY spot and active options strikes.

### `GET /api/positions`
Returns active open and closed positions with real-time Mark-to-Market (MTM) calculations.

### `GET /api/orders`
Returns recent order history from SQLite.

### `GET /api/trades`
Returns executed trades with statutory tax deductions itemized.

### `GET /api/arbitrage/opportunities`
Scans active orderbooks for Put-Call Parity and Box Spread deviations.
Returns signals with `is_capital_feasible` boolean and `infeasibility_reason` explaining SPAN margin requirements.

### `POST /api/kill-switch`
Engages or resets the emergency latching kill switch.
- **Payload to engage:** `{"action": "engage", "reason": "Operator command"}`
- **Payload to reset:** `{"action": "reset", "token": "<HMAC_SHA256_TOKEN>"}` (or `signature` header/field generated with `KILL_SWITCH_SECRET`)

### `POST /api/paper/reset`
Resets the virtual paper trading account to ₹3,000 initial capital.

### `POST /api/paper/order`
Submits a test paper order for execution:
```json
{
  "symbol": "NIFTY_2026-09-24_24500_CE",
  "side": "BUY",
  "quantity": 65,
  "price": 25.0
}
```

---

## 2. WebSocket Streaming

### `WebSocket /ws/stream`
Broadcasts real-time state every 250ms:
- Ticker & orderbooks (bids, asks, mid, micro-price, imbalance)
- Account cash & invested capital
- Real-time gross & net PnL
- Kill switch alerts & notifications
