"""Simple Moving Average crossover strategy."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from trader.core.models import Signal
from trader.strategies.base import Strategy


class SMACrossover(Strategy):
    """Buy when fast SMA crosses above slow SMA, sell when it crosses below."""

    def __init__(
        self,
        symbols: list[str],
        fast_period: int = 10,
        slow_period: int = 30,
    ) -> None:
        self.name = "sma_crossover"
        self.symbols = symbols
        self.fast_period = fast_period
        self.slow_period = slow_period
        self._prev_signal: dict[str, str] = {}  # symbol -> "BUY"/"SELL"

    def on_bar(self, symbol: str, bars: pd.DataFrame) -> Signal | None:
        if len(bars) < self.slow_period:
            return None

        fast_sma = bars["close"].rolling(self.fast_period).mean()
        slow_sma = bars["close"].rolling(self.slow_period).mean()

        # Current and previous crossover state
        current_above = fast_sma.iloc[-1] > slow_sma.iloc[-1]
        prev_above = fast_sma.iloc[-2] > slow_sma.iloc[-2]

        prev_signal = self._prev_signal.get(symbol)

        if current_above and not prev_above:
            # Bullish crossover
            self._prev_signal[symbol] = "BUY"
            if prev_signal != "BUY":
                return Signal(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    direction="BUY",
                    strength=0.7,
                    strategy_name=self.name,
                    metadata={
                        "fast_sma": round(fast_sma.iloc[-1], 2),
                        "slow_sma": round(slow_sma.iloc[-1], 2),
                    },
                )

        elif not current_above and prev_above:
            # Bearish crossover
            self._prev_signal[symbol] = "SELL"
            if prev_signal != "SELL":
                return Signal(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    direction="SELL",
                    strength=0.7,
                    strategy_name=self.name,
                    metadata={
                        "fast_sma": round(fast_sma.iloc[-1], 2),
                        "slow_sma": round(slow_sma.iloc[-1], 2),
                    },
                )

        return None

    def get_params(self) -> dict:
        return {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "symbols": self.symbols,
        }
