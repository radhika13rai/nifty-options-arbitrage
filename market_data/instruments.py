"""
Instrument Registry & Specification Module.
Enforces the 2026 NIFTY 50 lot size of 65 and standard NSE derivative parameters.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Optional
from config import config

OptionType = Literal["CE", "PE"]
InstrumentType = Literal["EQUITY", "FUTURES", "OPTIONS"]


@dataclass(frozen=True)
class OptionContract:
    """Represents an Indian equity derivative options contract."""
    symbol: str  # e.g., "NIFTY26SEP24500CE"
    underlying: str  # "NIFTY"
    strike: float  # e.g., 24500.0
    option_type: OptionType  # "CE" or "PE"
    expiry: str  # "2026-09-24"
    lot_size: int = config.market.nifty_lot_size  # Strictly 65
    tick_size: float = 0.05

    def is_call(self) -> bool:
        return self.option_type == "CE"

    def is_put(self) -> bool:
        return self.option_type == "PE"

    def intrinsic_value(self, spot_price: float) -> float:
        """Calculates theoretical intrinsic value at given spot."""
        if self.is_call():
            return max(0.0, spot_price - self.strike)
        return max(0.0, self.strike - spot_price)


class InstrumentRegistry:
    """Registry maintaining active tradable instruments."""

    def __init__(self, lot_size: int = config.market.nifty_lot_size):
        self.lot_size = lot_size
        self._registry: dict[str, OptionContract] = {}

    def register(self, contract: OptionContract) -> None:
        if contract.lot_size != self.lot_size:
            raise ValueError(
                f"Lot size mismatch for {contract.symbol}: got {contract.lot_size}, expected {self.lot_size}"
            )
        self._registry[contract.symbol] = contract

    def get(self, symbol: str) -> Optional[OptionContract]:
        return self._registry.get(symbol)

    def generate_nifty_option_chain(
        self,
        spot_price: float,
        expiry: str,
        num_strikes: int = 5,
        strike_interval: int = config.market.strike_interval
    ) -> list[OptionContract]:
        """
        Generates ATM and +/- num_strikes ITM/OTM contracts with verified 65 lot size.
        """
        atm_strike = round(spot_price / strike_interval) * strike_interval
        contracts = []
        
        for i in range(-num_strikes, num_strikes + 1):
            strike = atm_strike + (i * strike_interval)
            
            # Format standard NSE symbol: NIFTY<EXPIRY_CODE><STRIKE><TYPE>
            # e.g., NIFTY2692424500CE
            ce_sym = f"NIFTY_{expiry}_{strike}_CE"
            pe_sym = f"NIFTY_{expiry}_{strike}_PE"
            
            ce_contract = OptionContract(
                symbol=ce_sym,
                underlying="NIFTY",
                strike=float(strike),
                option_type="CE",
                expiry=expiry,
                lot_size=self.lot_size
            )
            pe_contract = OptionContract(
                symbol=pe_sym,
                underlying="NIFTY",
                strike=float(strike),
                option_type="PE",
                expiry=expiry,
                lot_size=self.lot_size
            )
            
            self.register(ce_contract)
            self.register(pe_contract)
            contracts.extend([ce_contract, pe_contract])
            
        return contracts


instrument_registry = InstrumentRegistry()
