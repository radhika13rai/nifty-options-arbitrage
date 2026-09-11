"""
ML Dataset & Historical Feature Persistence Repository.
Maintains historical candles and model checkpoints in SQLite WAL.
"""

import json
import time
from typing import Optional
from database.db import db_manager


class MLDatasetRepository:
    """Manages persistence of ML feature vectors, candles, and model state."""

    async def init_ml_tables(self) -> None:
        """Creates ML specific tables in SQLite."""
        query = """
        CREATE TABLE IF NOT EXISTS ml_feature_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_ms REAL NOT NULL,
            symbol TEXT NOT NULL,
            features_json TEXT NOT NULL,
            trade_action TEXT,
            realized_pnl REAL,
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ml_model_checkpoints (
            checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
            epoch INTEGER NOT NULL,
            weights_json TEXT NOT NULL,
            regime TEXT NOT NULL,
            expected_win_rate REAL NOT NULL,
            created_at REAL NOT NULL
        );
        """
        await db_manager.async_write(query)

    async def record_features(
        self,
        symbol: str,
        features: list[float],
        trade_action: Optional[str] = None,
        realized_pnl: Optional[float] = None
    ) -> None:
        query = """
            INSERT INTO ml_feature_logs (timestamp_ms, symbol, features_json, trade_action, realized_pnl, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        await db_manager.async_write(
            query,
            (time.time() * 1000.0, symbol, json.dumps(features), trade_action, realized_pnl, time.time())
        )

    async def save_checkpoint(
        self,
        epoch: int,
        weights: list[float],
        regime: str,
        expected_win_rate: float
    ) -> None:
        query = """
            INSERT INTO ml_model_checkpoints (epoch, weights_json, regime, expected_win_rate, created_at)
            VALUES (?, ?, ?, ?, ?)
        """
        await db_manager.async_write(
            query,
            (epoch, json.dumps(weights), regime, expected_win_rate, time.time())
        )

    async def get_latest_checkpoint(self) -> Optional[dict]:
        rows = await db_manager.async_query(
            "SELECT * FROM ml_model_checkpoints ORDER BY epoch DESC LIMIT 1"
        )
        return rows[0] if rows else None


ml_repo = MLDatasetRepository()
