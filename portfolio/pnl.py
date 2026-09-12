"""
Real-Time P&L & Friction Accounting Module.
Calculates instantaneous gross P&L, statutory friction breakdown, net P&L, and drawdown.
"""

from dataclasses import dataclass
import time
from config import config
from portfolio.positions import position_tracker


@dataclass(frozen=True)
class PortfolioPnLReport:
    timestamp: float
    starting_cash: float
    current_cash: float
    invested_capital: float
    total_portfolio_value: float
    gross_realized_pnl: float
    gross_unrealized_pnl: float
    total_gross_pnl: float
    total_friction_inr: float
    net_pnl: float
    net_pnl_percentage: float
    peak_capital: float
    drawdown_inr: float
    drawdown_pct: float
    max_drawdown_pct: float = 0.0
    is_daily_limit_breached: bool = False


class PnLManager:
    """Manages real-time PnL, friction accounting, and peak-to-trough drawdowns."""

    def __init__(self, initial_capital: float = config.initial_capital_inr):
        self.starting_cash = initial_capital
        self.current_cash = initial_capital
        self.peak_capital = initial_capital
        self.total_friction = 0.0
        self.max_drawdown_inr = 0.0
        self.max_drawdown_pct = 0.0

    @property
    def cash_balance(self) -> float:
        """Returns available liquid cash balance."""
        return self.current_cash

    def adjust_cash(self, net_cash_flow: float, friction: float) -> None:
        """Applies order cash flow and friction fees."""
        self.current_cash = round(self.current_cash + net_cash_flow, 2)
        self.total_friction = round(self.total_friction + friction, 2)

    def reset(self, new_initial_capital: Optional[float] = None) -> None:
        """Resets PnL and cash to initial capital baseline."""
        cap = new_initial_capital if new_initial_capital is not None else config.initial_capital_inr
        self.starting_cash = cap
        self.current_cash = cap
        self.peak_capital = cap
        self.total_friction = 0.0
        self.max_drawdown_inr = 0.0
        self.max_drawdown_pct = 0.0

    def reset_balance(self, capital: float = config.initial_capital_inr) -> None:
        """Alias for reset."""
        self.reset(capital)

    def generate_report(self) -> PortfolioPnLReport:
        """Generates comprehensive Mark-to-Market PnL and Drawdown report."""
        open_positions = position_tracker.get_open_positions()
        all_positions = position_tracker.get_all_positions()

        invested_capital = sum(p.average_price * p.quantity for p in open_positions if p.side == "BUY")
        unrealized = sum(p.unrealized_pnl for p in open_positions)
        realized = sum(p.realized_pnl for p in all_positions)

        total_gross = round(realized + unrealized, 2)
        net_pnl = round(total_gross - self.total_friction, 2)
        
        # Portfolio value = cash + current market value of long options
        mtm_value = sum(p.current_price * p.quantity for p in open_positions if p.side == "BUY")
        total_value = round(self.current_cash + mtm_value, 2)

        if total_value > self.peak_capital:
            self.peak_capital = total_value

        drawdown = round(max(0.0, self.peak_capital - total_value), 2)
        drawdown_pct = round((drawdown / self.peak_capital) * 100, 2) if self.peak_capital > 0 else 0.0
        
        # Track true running maximum drawdown over all history
        if drawdown > self.max_drawdown_inr:
            self.max_drawdown_inr = drawdown
        if drawdown_pct > self.max_drawdown_pct:
            self.max_drawdown_pct = drawdown_pct

        net_pct = round((net_pnl / self.starting_cash) * 100, 2) if self.starting_cash > 0 else 0.0
        daily_breached = (realized - self.total_friction) <= -config.risk.max_daily_loss_inr

        return PortfolioPnLReport(
            timestamp=time.time(),
            starting_cash=self.starting_cash,
            current_cash=self.current_cash,
            invested_capital=round(invested_capital, 2),
            total_portfolio_value=total_value,
            gross_realized_pnl=round(realized, 2),
            gross_unrealized_pnl=round(unrealized, 2),
            total_gross_pnl=total_gross,
            total_friction_inr=self.total_friction,
            net_pnl=net_pnl,
            net_pnl_percentage=net_pct,
            peak_capital=round(self.peak_capital, 2),
            drawdown_inr=drawdown,
            drawdown_pct=drawdown_pct,
            max_drawdown_pct=self.max_drawdown_pct,
            is_daily_limit_breached=daily_breached
        )


pnl_manager = PnLManager()
