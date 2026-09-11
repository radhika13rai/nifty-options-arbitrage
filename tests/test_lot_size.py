"""
Tests for NIFTY 50 Lot Size (Strictly 65 according to NSE Circular NSE/FAOP/70616).
"""

import pytest
from config import config
from market_data.instruments import instrument_registry, OptionContract


def test_config_lot_size_is_65():
    """Assert that the master configuration uses lot size 65."""
    assert config.market.nifty_lot_size == 65


def test_instrument_registry_lot_size():
    """Assert that the instrument registry mandates lot size 65."""
    contract = OptionContract(
        symbol="NIFTY_TEST_24500_CE",
        underlying="NIFTY",
        strike=24500.0,
        option_type="CE",
        expiry="2026-09-24",
        lot_size=65
    )
    assert contract.lot_size == 65

    # Registering contract with wrong lot size must raise ValueError
    with pytest.raises(ValueError):
        invalid_contract = OptionContract(
            symbol="NIFTY_INVALID_24500_CE",
            underlying="NIFTY",
            strike=24500.0,
            option_type="CE",
            expiry="2026-09-24",
            lot_size=50  # Old lot size
        )
        instrument_registry.register(invalid_contract)


def test_chain_generation_uses_65():
    """Verify generated option chain contracts enforce lot size 65."""
    chain = instrument_registry.generate_nifty_option_chain(
        spot_price=24500.0,
        expiry="2026-09-24",
        num_strikes=3
    )
    assert len(chain) == 14  # (3 ITM + 1 ATM + 3 OTM) * 2 (CE + PE)
    for c in chain:
        assert c.lot_size == 65
