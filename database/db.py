"""
High-Performance SQLite Repository Module.
Configures WAL journal mode, enables non-blocking async execution via asyncio.to_thread,
and provides auditable persistence for all trading operations.
"""

import asyncio
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional
from config import config

DB_PATH = config.db_path


class DatabaseManager:
    """Manages SQLite connection lifecycle and thread-safe execution."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        # WAL mode enables concurrent readers without locking writer
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        """Initializes tables and indexes from schema.sql."""
        schema_path = self.db_path.parent / "schema.sql"
        if not schema_path.exists():
            schema_path = Path(__file__).parent / "schema.sql"

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        with self._get_connection() as conn:
            conn.executescript(schema_sql)
            conn.commit()

    def execute_write(self, query: str, params: tuple = ()) -> None:
        with self._get_connection() as conn:
            conn.execute(query, params)
            conn.commit()

    def execute_query(self, query: str, params: tuple = ()) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # Async wrappers ensuring zero blocking of asyncio event loop
    async def async_init_db(self) -> None:
        await asyncio.to_thread(self.init_db)

    async def async_write(self, query: str, params: tuple = ()) -> None:
        await asyncio.to_thread(self.execute_write, query, params)

    async def async_query(self, query: str, params: tuple = ()) -> list[dict]:
        return await asyncio.to_thread(self.execute_query, query, params)

    # Repository operations
    async def record_audit_log(self, event_type: str, severity: str, component: str, details: str) -> None:
        query = """
            INSERT INTO audit_logs (event_type, severity, component, details, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """
        await self.async_write(query, (event_type, severity, component, details, time.time()))

    async def record_risk_event(self, event_type: str, reason: str, blocked_payload: Optional[dict] = None) -> None:
        payload_str = json.dumps(blocked_payload) if blocked_payload else None
        query = """
            INSERT INTO risk_events (event_type, reason, blocked_payload, timestamp)
            VALUES (?, ?, ?, ?)
        """
        await self.async_write(query, (event_type, reason, payload_str, time.time()))

    async def record_order(
        self,
        order_id: str,
        client_order_id: str,
        symbol: str,
        side: str,
        order_type: str,
        quantity: int,
        requested_price: float,
        fill_price: Optional[float],
        status: str,
        total_costs: float = 0.0,
        rejection_reason: Optional[str] = None
    ) -> None:
        now = time.time()
        query = """
            INSERT INTO orders (order_id, client_order_id, symbol, side, order_type, quantity, requested_price, fill_price, status, total_costs, rejection_reason, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(order_id) DO UPDATE SET
                fill_price = excluded.fill_price,
                status = excluded.status,
                total_costs = excluded.total_costs,
                rejection_reason = excluded.rejection_reason,
                updated_at = excluded.updated_at
        """
        await self.async_write(
            query,
            (order_id, client_order_id, symbol, side, order_type, quantity, requested_price, fill_price, status, total_costs, rejection_reason, now, now)
        )

    async def record_trade(
        self,
        trade_id: str,
        order_id: str,
        symbol: str,
        side: str,
        price: float,
        quantity: int,
        turnover: float,
        brokerage: float,
        stt: float,
        exchange_charges: float,
        gst: float,
        stamp_duty: float,
        sebi_charges: float,
        total_costs: float,
        net_cash_flow: float
    ) -> None:
        query = """
            INSERT INTO trades (trade_id, order_id, symbol, side, price, quantity, turnover, brokerage, stt, exchange_charges, gst, stamp_duty, sebi_charges, total_costs, net_cash_flow, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.async_write(
            query,
            (trade_id, order_id, symbol, side, price, quantity, turnover, brokerage, stt, exchange_charges, gst, stamp_duty, sebi_charges, total_costs, net_cash_flow, time.time())
        )

    async def record_daily_pnl(
        self,
        date_str: str,
        starting_cash: float,
        ending_cash: float,
        gross_pnl: float,
        total_friction: float,
        net_pnl: float,
        trades_count: int,
        max_drawdown: float
    ) -> None:
        query = """
            INSERT INTO daily_pnl (date, starting_cash, ending_cash, gross_pnl, total_friction, net_pnl, trades_count, max_drawdown, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                starting_cash = excluded.starting_cash,
                ending_cash = excluded.ending_cash,
                gross_pnl = excluded.gross_pnl,
                total_friction = excluded.total_friction,
                net_pnl = excluded.net_pnl,
                trades_count = excluded.trades_count,
                max_drawdown = excluded.max_drawdown,
                updated_at = excluded.updated_at
        """
        await self.async_write(
            query,
            (date_str, starting_cash, ending_cash, gross_pnl, total_friction, net_pnl, trades_count, max_drawdown, time.time())
        )

    async def checkpoint_wal(self) -> None:
        """Flushes SQLite WAL to database file to maintain zero-fragmentation during soak tests."""
        await self.async_write("PRAGMA wal_checkpoint(PASSIVE);")

    async def get_daily_pnl_records(self, limit: int = 50) -> list[dict]:
        return await self.async_query("SELECT * FROM daily_pnl ORDER BY date DESC LIMIT ?", (limit,))

    async def get_recent_orders(self, limit: int = 50) -> list[dict]:
        return await self.async_query("SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,))

    async def get_recent_trades(self, limit: int = 50) -> list[dict]:
        return await self.async_query("SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?", (limit,))

    async def get_audit_logs(self, limit: int = 50) -> list[dict]:
        return await self.async_query("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))


db_manager = DatabaseManager()
