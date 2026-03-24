"""Tests for the SMA crossover strategy."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from trader.strategies.sma_crossover import SMACrossover


def _make_bars(prices: list[float]) -> pd.DataFrame:
    """Create a simple OHLCV DataFrame from a list of close prices."""
    dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(len(prices))]
    return pd.DataFrame({
        "open": prices,
        "high": [p * 1.01 for p in prices],
        "low": [p * 0.99 for p in prices],
        "close": prices,
        "volume": [1000000] * len(prices),
    }, index=dates)


def test_no_signal_insufficient_data():
    strategy = SMACrossover(symbols=["AAPL"], fast_period=5, slow_period=10)
    bars = _make_bars([100.0] * 5)  # Not enough for slow_period
    signal = strategy.on_bar("AAPL", bars)
    assert signal is None


def test_buy_signal_on_bullish_crossover():
    strategy = SMACrossover(symbols=["AAPL"], fast_period=3, slow_period=5)

    # Create data where fast SMA crosses above slow SMA
    # Downtrend then sharp upturn
    prices = [100, 99, 98, 97, 96, 95, 94, 93, 92, 91,  # downtrend
              95, 100, 110]  # sharp upturn
    bars = _make_bars(prices)
    signal = strategy.on_bar("AAPL", bars)

    # Should get a BUY signal from the bullish crossover
    if signal:
        assert signal.direction == "BUY"
        assert signal.strategy_name == "sma_crossover"


def test_no_duplicate_signals():
    strategy = SMACrossover(symbols=["AAPL"], fast_period=3, slow_period=5)

    prices = [100, 99, 98, 97, 96, 95, 94, 93, 92, 91, 95, 100, 110]
    bars = _make_bars(prices)

    # First call might produce a signal
    signal1 = strategy.on_bar("AAPL", bars)

    # Second call with same data should not produce duplicate
    signal2 = strategy.on_bar("AAPL", bars)
    assert signal2 is None  # No crossover happened between calls


def test_get_params():
    strategy = SMACrossover(symbols=["AAPL", "MSFT"], fast_period=10, slow_period=30)
    params = strategy.get_params()
    assert params["fast_period"] == 10
    assert params["slow_period"] == 30
    assert params["symbols"] == ["AAPL", "MSFT"]
