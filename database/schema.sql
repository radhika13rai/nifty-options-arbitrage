-- NIFTY Options Trading System Database Schema
-- Optimized for SQLite WAL Mode

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    client_order_id TEXT UNIQUE,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    requested_price REAL NOT NULL,
    fill_price REAL,
    status TEXT NOT NULL,
    total_costs REAL DEFAULT 0.0,
    rejection_reason TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
    trade_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    turnover REAL NOT NULL,
    brokerage REAL NOT NULL,
    stt REAL NOT NULL,
    exchange_charges REAL NOT NULL,
    gst REAL NOT NULL,
    stamp_duty REAL NOT NULL,
    sebi_charges REAL NOT NULL,
    total_costs REAL NOT NULL,
    net_cash_flow REAL NOT NULL,
    timestamp REAL NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(order_id)
);

CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY,
    side TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    average_price REAL NOT NULL,
    current_price REAL NOT NULL,
    unrealized_pnl REAL DEFAULT 0.0,
    realized_pnl REAL DEFAULT 0.0,
    total_costs REAL DEFAULT 0.0,
    is_open INTEGER NOT NULL DEFAULT 1,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    component TEXT NOT NULL,
    details TEXT NOT NULL,
    timestamp REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS risk_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    reason TEXT NOT NULL,
    blocked_payload TEXT,
    timestamp REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_pnl (
    date TEXT PRIMARY KEY,
    starting_cash REAL NOT NULL,
    ending_cash REAL NOT NULL,
    gross_pnl REAL NOT NULL,
    total_friction REAL NOT NULL,
    net_pnl REAL NOT NULL,
    trades_count INTEGER NOT NULL,
    max_drawdown REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
