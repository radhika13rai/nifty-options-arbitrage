"""
Feature Extraction & Normalization Engine for NIFTY Options.
Computes real-time microstructure, momentum, VWAP, and volatility features
in pure Python with sub-millisecond execution latency.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Optional
from market_data.normalizer import MarketTick
from market_data.orderbook import OrderbookSnapshot


@dataclass(frozen=True)
class FeatureVector:
    """Quantitative feature vector describing instantaneous market state."""
    timestamp_ms: float
    symbol: str
    orderbook_imbalance: float   # [-1.0, 1.0]
    micro_price_delta: float     # micro_price - mid_price
    spread_pct: float            # (ask - bid) / mid
    vwap_stretch: float          # (price - vwap) / std_vwap
    ema_trend_slope: float       # (ema9 - ema21) / ema21
    rsi_14: float                # [0.0, 100.0]
    atr_norm: float              # atr / price
    volatility_rank: float       # [0.0, 1.0]

    def to_list(self) -> list[float]:
        """Returns standard normalized numeric vector."""
        return [
            self.orderbook_imbalance,
            self.micro_price_delta,
            self.spread_pct,
            self.vwap_stretch,
            self.ema_trend_slope,
            (self.rsi_14 - 50.0) / 50.0,  # Scaled to [-1.0, 1.0]
            self.atr_norm,
            self.volatility_rank
        ]


class RollingIndicatorTracker:
    """Tracks continuous indicators for an instrument in pure Python."""

    def __init__(self, symbol: str, max_history: int = 120):
        self.symbol = symbol
        self.max_history = max_history
        self.prices: list[float] = []
        self.volumes: list[int] = []
        self.timestamps: list[float] = []
        
        # State indicators
        self.ema9: Optional[float] = None
        self.ema21: Optional[float] = None
        self.cum_vol: int = 0
        self.cum_vol_price: float = 0.0

    def update(self, price: float, volume: int, timestamp_ms: float) -> None:
        """Applies a new tick/bar update."""
        if price <= 0:
            return

        self.prices.append(price)
        self.volumes.append(volume)
        self.timestamps.append(timestamp_ms)

        if len(self.prices) > self.max_history:
            self.prices.pop(0)
            self.volumes.pop(0)
            self.timestamps.pop(0)

        # 1. Update EMAs
        if self.ema9 is None:
            self.ema9 = price
            self.ema21 = price
        else:
            k9 = 2.0 / (9.0 + 1.0)
            k21 = 2.0 / (21.0 + 1.0)
            self.ema9 = (price * k9) + (self.ema9 * (1.0 - k9))
            self.ema21 = (price * k21) + (self.ema21 * (1.0 - k21))

        # 2. Update Intraday VWAP
        self.cum_vol += volume
        self.cum_vol_price += price * volume

    @property
    def vwap(self) -> float:
        if self.cum_vol > 0:
            return self.cum_vol_price / self.cum_vol
        return self.prices[-1] if self.prices else 0.0

    @property
    def rsi_14(self) -> float:
        """Computes 14-period RSI."""
        if len(self.prices) < 15:
            return 50.0  # Neutral prior

        gains = []
        losses = []
        for i in range(-14, 0):
            change = self.prices[i] - self.prices[i - 1]
            if change >= 0:
                gains.append(change)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(change))

        avg_gain = sum(gains) / 14.0
        avg_loss = sum(losses) / 14.0

        if avg_loss == 0.0:
            return 100.0 if avg_gain > 0 else 50.0

        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @property
    def atr(self) -> float:
        """Computes normalized range over the rolling window."""
        if len(self.prices) < 2:
            return 0.5
        high = max(self.prices[-14:])
        low = min(self.prices[-14:])
        return max(0.05, high - low)


class FeatureExtractor:
    """Extracts standardized ML feature vectors across all subscribed instruments."""

    def __init__(self):
        self._trackers: dict[str, RollingIndicatorTracker] = {}

    def get_or_create_tracker(self, symbol: str) -> RollingIndicatorTracker:
        if symbol not in self._trackers:
            self._trackers[symbol] = RollingIndicatorTracker(symbol)
        return self._trackers[symbol]

    def extract_features(self, snapshot: OrderbookSnapshot) -> FeatureVector:
        """Transforms an L2 orderbook snapshot into a rich quantitative feature vector."""
        tracker = self.get_or_create_tracker(snapshot.symbol)
        tracker.update(snapshot.mid_price, snapshot.total_bid_volume + snapshot.total_ask_volume, snapshot.timestamp_ms)

        # Microstructure features
        imbalance = snapshot.imbalance
        micro_delta = round(snapshot.micro_price - snapshot.mid_price, 3)
        spread_pct = round(snapshot.spread / snapshot.mid_price, 4) if snapshot.mid_price > 0 else 0.0

        # VWAP stretch
        vwap = tracker.vwap
        atr = tracker.atr
        vwap_stretch = round((snapshot.mid_price - vwap) / atr, 3) if atr > 0 else 0.0

        # EMA trend slope
        if tracker.ema9 and tracker.ema21 and tracker.ema21 > 0:
            ema_slope = round((tracker.ema9 - tracker.ema21) / tracker.ema21, 5)
        else:
            ema_slope = 0.0

        # Volatility rank proxy (based on recent range vs price)
        vol_rank = min(1.0, max(0.0, (atr / snapshot.mid_price) * 10.0)) if snapshot.mid_price > 0 else 0.5

        return FeatureVector(
            timestamp_ms=snapshot.timestamp_ms,
            symbol=snapshot.symbol,
            orderbook_imbalance=imbalance,
            micro_price_delta=micro_delta,
            spread_pct=spread_pct,
            vwap_stretch=vwap_stretch,
            ema_trend_slope=ema_slope,
            rsi_14=tracker.rsi_14,
            atr_norm=round(atr / snapshot.mid_price, 4) if snapshot.mid_price > 0 else 0.01,
            volatility_rank=vol_rank
        )

    def extract_unified_vector(
        self,
        snapshot: OrderbookSnapshot,
        atm_iv: float = 0.15,
        put_call_skew: float = 0.0,
        days_to_expiry: float = 4.0,
        delta: float = 0.50,
        brent_pct_chg: float = 0.0,
        dxy_pct_chg: float = 0.0,
        news_sentiment: float = 0.0,
        tension_index: float = 0.15
    ) -> list[float]:
        """
        Extracts 16-dimensional unified feature vector at trade inception.
        Fuses microstructure (8D), options skew (4D), and macro/news intelligence (4D).
        """
        base = self.extract_features(snapshot).to_list()  # 8 features
        
        # 4 Options Surface & Skew features
        norm_iv = round((atm_iv - 0.15) / 0.10, 4)
        norm_skew = round(put_call_skew / 0.05, 4)
        norm_dte = round((days_to_expiry - 3.5) / 3.5, 4)
        norm_delta = round(abs(delta), 4)

        # 4 Macro & Market Intelligence features
        norm_brent = round(brent_pct_chg / 3.0, 4)
        norm_dxy = round(dxy_pct_chg / 1.0, 4)
        norm_sent = round(news_sentiment, 4)
        norm_tension = round(tension_index * 2.0 - 1.0, 4)

        extended = [
            norm_iv,
            norm_skew,
            norm_dte,
            norm_delta,
            norm_brent,
            norm_dxy,
            norm_sent,
            norm_tension
        ]
        return base + extended


feature_extractor = FeatureExtractor()
