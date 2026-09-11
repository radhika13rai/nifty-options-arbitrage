"""
System Configuration Module for NIFTY Options Arbitrage & Trading System.
Enforces compliance-first invariants, risk boundaries, and market parameters.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class RiskConfig:
    """Risk management limits strictly enforcing fail-safe boundaries."""
    max_trade_loss_inr: float = float(os.getenv("MAX_TRADE_LOSS_INR", "150.0"))
    max_daily_loss_inr: float = float(os.getenv("MAX_DAILY_LOSS_INR", "300.0"))
    max_lots: int = int(os.getenv("MAX_LOTS", "1"))
    capital_floor_inr: float = float(os.getenv("CAPITAL_FLOOR_INR", "2000.0"))
    stale_quote_timeout_ms: int = int(os.getenv("STALE_DATA_TIMEOUT_MS", "1500"))
    max_slippage_points: float = float(os.getenv("MAX_SLIPPAGE_POINTS", "1.5"))


@dataclass(frozen=True)
class MarketConfig:
    """Market parameters conforming to latest exchange circulars."""
    # NSE circular NSE/FAOP/70616 effective Jan 2026 revised NIFTY 50 lot size to 65
    nifty_lot_size: int = int(os.getenv("NIFTY_LOT_SIZE", "65"))
    risk_free_rate: float = float(os.getenv("RISK_FREE_RATE", "0.0675"))  # 6.75% RBI repo rate
    strike_interval: int = 50
    underlying_symbol: str = "NIFTY"


@dataclass(frozen=True)
class CostScheduleConfig:
    """Indian statutory & regulatory transaction costs schedule (2026)."""
    brokerage_per_order: float = float(os.getenv("BROKERAGE_PER_ORDER", "20.0"))
    stt_rate_sell: float = float(os.getenv("STT_RATE_SELL", "0.001"))  # 0.1% on premium (sell side)
    exchange_turnover_rate: float = float(os.getenv("EXCHANGE_TURNOVER_RATE", "0.0005"))  # 0.05%
    gst_rate: float = float(os.getenv("GST_RATE", "0.18"))  # 18% on brokerage + txn + SEBI
    stamp_duty_rate_buy: float = float(os.getenv("STAMP_DUTY_RATE_BUY", "0.00003"))  # 0.003%
    sebi_turnover_rate: float = float(os.getenv("SEBI_TURNOVER_RATE", "0.000001"))  # ₹10 per crore


@dataclass(frozen=True)
class AppConfig:
    """Master application configuration."""
    app_name: str = "NIFTY Options Arbitrage & Research Engine"
    version: str = "1.0.0"
    base_dir: Path = BASE_DIR
    db_path: Path = BASE_DIR / "database" / "trading_system.db"
    
    # Execution mode: STRICTLY 'PAPER_TRADING' in V1
    execution_mode: str = os.getenv("EXECUTION_MODE", "PAPER_TRADING")
    live_trading_enabled: bool = os.getenv("LIVE_TRADING_ENABLED", "false").lower() == "true"
    
    # Capital constraints
    initial_capital_inr: float = float(os.getenv("INITIAL_CAPITAL_INR", "3000.0"))
    
    # Server configuration
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))
    
    # Dhan Broker API Credentials (optional for live data quotes)
    dhan_client_id: str = os.getenv("DHAN_CLIENT_ID", "")
    dhan_access_token: str = os.getenv("DHAN_ACCESS_TOKEN", "")
    
    # Sub-configurations
    risk: RiskConfig = RiskConfig()
    market: MarketConfig = MarketConfig()
    costs: CostScheduleConfig = CostScheduleConfig()

    def __post_init__(self):
        # CRITICAL SAFETY INVARIANT: Live trading must NEVER be enabled in V1
        if self.live_trading_enabled:
            raise RuntimeError(
                "CRITICAL COMPLIANCE VIOLATION: LIVE_TRADING_ENABLED=true is strictly forbidden in V1. "
                "Only PAPER_TRADING is authorized under current regulatory and system gates."
            )
        if self.execution_mode != "PAPER_TRADING":
            raise RuntimeError(
                f"INVALID EXECUTION MODE: '{self.execution_mode}'. V1 only supports 'PAPER_TRADING'."
            )


config = AppConfig()
