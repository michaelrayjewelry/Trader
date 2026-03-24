"""Abstract strategy base class."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from trader.core.models import Signal


class Strategy(ABC):
    name: str
    symbols: list[str]

    @abstractmethod
    def on_bar(self, symbol: str, bars: pd.DataFrame) -> Signal | None:
        """Process new bar data and optionally return a trading signal.

        Args:
            symbol: The ticker symbol.
            bars: DataFrame with columns [open, high, low, close, volume]
                  indexed by datetime, most recent last.

        Returns:
            A Signal if the strategy wants to trade, None otherwise.
        """
        ...

    @abstractmethod
    def get_params(self) -> dict:
        """Return current strategy parameters for display/serialization."""
        ...
