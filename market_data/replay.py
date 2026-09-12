"""
Deterministic Market Data Replay & Simulation Engine.
Generates realistic high-resolution NIFTY index and options market streams
for backtesting and offline paper trading.
"""

import math
import random
import time
from typing import AsyncGenerator, Generator
from config import config
from market_data.normalizer import MarketDataNormalizer, MarketTick
from market_data.instruments import instrument_registry, OptionContract


class MarketDataReplayEngine:
    """Simulates realistic options market microstructure with geometric Brownian motion and jump diffusion."""

    def __init__(
        self,
        base_spot: float = 24500.0,
        volatility: float = 0.15,
        drift: float = 0.0,
        seed: int = 42
    ):
        self.base_spot = base_spot
        self.current_spot = base_spot
        self.volatility = volatility
        self.drift = drift
        self.rng = random.Random(seed)
        self.contracts: list[OptionContract] = []
        self._init_default_contracts()

    def _init_default_contracts(self):
        """Generates active NIFTY contracts around base spot with 10 strikes (covering OTM corridor)."""
        self.contracts = instrument_registry.generate_nifty_option_chain(
            spot_price=self.base_spot,
            expiry="2026-09-24",
            num_strikes=10
        )

    def step_spot(self) -> float:
        """
        Advance spot price tick-by-tick with realistic intraday variance.
        Spot oscillates gently around base_spot with realistic ±0.50 to ±1.50 pt micro-ticks.
        """
        # Mean reversion pull towards base_spot to maintain realistic trading corridor
        reversion = -0.015 * (self.current_spot - self.base_spot)
        # Micro tick noise: standard tick shock ~0.65 pts
        tick_shock = self.rng.gauss(0.0, 0.65)
        
        # 0.5% chance of an intraday breakout impulse (3.0 - 8.0 pts)
        impulse = 0.0
        if self.rng.random() < 0.005:
            impulse = self.rng.choice([-1, 1]) * self.rng.uniform(3.0, 8.0)

        self.current_spot = round(self.current_spot + reversion + tick_shock + impulse, 2)
        spot_rounded = self.current_spot

        # Dynamically recenter contracts around ATM if spot moves past a strike interval
        current_atm = round(spot_rounded / config.market.strike_interval) * config.market.strike_interval
        if self.contracts:
            center_k = self.contracts[len(self.contracts) // 2].strike
            if abs(current_atm - center_k) >= config.market.strike_interval:
                self.contracts = instrument_registry.generate_nifty_option_chain(
                    spot_price=spot_rounded,
                    expiry="2026-09-24",
                    num_strikes=10
                )

        return spot_rounded

    def calculate_bsm_price(self, contract: OptionContract, spot: float, t_years: float = 4.0 / 365.0) -> float:
        """Calculates skew-aware option price using VolatilitySurface parametric IV."""
        k = contract.strike
        r = config.market.risk_free_rate
        days = t_years * 365.0
        
        try:
            from analytics.volatility_surface import volatility_surface
            sigma = volatility_surface.get_implied_volatility(strike=k, spot=spot, days_to_expiry=days)
        except Exception:
            sigma = self.volatility
        
        if t_years <= 0.0001:
            return contract.intrinsic_value(spot)

        d1 = (math.log(spot / k) + (r + 0.5 * sigma ** 2) * t_years) / (sigma * math.sqrt(t_years))
        d2 = d1 - sigma * math.sqrt(t_years)

        def norm_cdf(x):
            return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

        if contract.is_call():
            price = spot * norm_cdf(d1) - k * math.exp(-r * t_years) * norm_cdf(d2)
        else:
            price = k * math.exp(-r * t_years) * norm_cdf(-d2) - spot * norm_cdf(-d1)

        # Minimum tick price
        return max(0.05, round(price, 2))

    def generate_tick_batch(self) -> list[MarketTick]:
        """Generates a synchronized batch of ticks for NIFTY spot and all active options."""
        spot = self.step_spot()
        ticks = []

        # 1. NIFTY Index Spot Tick
        spot_tick = MarketDataNormalizer.create_synthetic_tick(
            symbol="NIFTY_SPOT",
            mid_price=spot,
            spread=0.50,
            volume=int(self.rng.uniform(10000, 50000)),
            bid_qty=1300,
            ask_qty=1300
        )
        ticks.append(spot_tick)

        # 2. Options Contract Ticks
        for contract in self.contracts:
            bsm_price = self.calculate_bsm_price(contract, spot)
            # Add small random micro-spread and noise
            noise = self.rng.uniform(-0.15, 0.15)
            mid = max(0.10, round(bsm_price + noise, 2))
            spread = max(0.10, round(min(1.50, mid * 0.02), 2))
            
            opt_tick = MarketDataNormalizer.create_synthetic_tick(
                symbol=contract.symbol,
                mid_price=mid,
                spread=spread,
                volume=int(self.rng.uniform(2000, 15000)),
                bid_qty=int(self.rng.choice([65, 130, 260, 520])),
                ask_qty=int(self.rng.choice([65, 130, 260, 520]))
            )
            ticks.append(opt_tick)

        return ticks

    async def stream_ticks(self, interval_sec: float = 0.25) -> AsyncGenerator[list[MarketTick], None]:
        """Asynchronous tick generator yielding simulated real-time ticks."""
        import asyncio
        while True:
            batch = self.generate_tick_batch()
            yield batch
            await asyncio.sleep(interval_sec)


replay_engine = MarketDataReplayEngine()
