"""Abstract data provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class DataProvider(ABC):
    @abstractmethod
    async def get_bars(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        """Fetch OHLCV bars for a symbol.

        Returns:
            DataFrame with columns [open, high, low, close, volume],
            indexed by datetime.
        """
        ...

    @abstractmethod
    async def get_current_price(self, symbol: str) -> float | None:
        """Get the latest price for a symbol."""
        ...
