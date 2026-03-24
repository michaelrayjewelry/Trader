"""Yahoo Finance data provider using yfinance."""

from __future__ import annotations

import asyncio
import logging
from functools import partial

import pandas as pd
import yfinance as yf

from trader.data.base import DataProvider

logger = logging.getLogger(__name__)


class YahooDataProvider(DataProvider):
    """Fetches market data from Yahoo Finance (free, no API key needed)."""

    async def get_bars(self, symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, partial(self._fetch, symbol, period, interval))
        return df

    async def get_current_price(self, symbol: str) -> float | None:
        bars = await self.get_bars(symbol, period="1d", interval="1m")
        if bars.empty:
            return None
        return float(bars["close"].iloc[-1])

    @staticmethod
    def _fetch(symbol: str, period: str, interval: str) -> pd.DataFrame:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                logger.warning("No data returned for %s", symbol)
                return pd.DataFrame()
            df.columns = [c.lower() for c in df.columns]
            # Keep only OHLCV columns
            cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
            return df[cols]
        except Exception:
            logger.exception("Failed to fetch data for %s", symbol)
            return pd.DataFrame()
