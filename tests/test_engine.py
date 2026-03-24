"""Tests for the trading engine."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pandas as pd

from trader.broker.paper import PaperBroker
from trader.core.engine import TradingEngine
from trader.core.events import EventBus
from trader.core.models import Signal
from trader.db.database import Database
from trader.strategies.sma_crossover import SMACrossover


def _make_engine(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.init_schema()

    broker = PaperBroker(db=db, starting_cash=100_000.0, slippage_pct=0.0)
    event_bus = EventBus()
    data_provider = AsyncMock()
    strategy = SMACrossover(symbols=["AAPL"], fast_period=3, slow_period=5)

    engine = TradingEngine(
        data_provider=data_provider,
        strategies=[strategy],
        broker=broker,
        db=db,
        event_bus=event_bus,
    )
    return engine, data_provider, broker


def test_tick_with_no_data(tmp_path):
    engine, data_provider, broker = _make_engine(tmp_path)
    data_provider.get_bars.return_value = pd.DataFrame()

    asyncio.run(engine.tick())

    # No trades should happen with empty data
    assert broker.get_cash() == 100_000.0


def test_tick_with_signal(tmp_path):
    engine, data_provider, broker = _make_engine(tmp_path)

    # Create data that triggers a buy signal (fast SMA crossing above slow)
    dates = [datetime(2024, 1, i + 1) for i in range(13)]
    prices = [100, 99, 98, 97, 96, 95, 94, 93, 92, 91, 95, 100, 110]
    df = pd.DataFrame({
        "open": prices, "high": prices, "low": prices,
        "close": prices, "volume": [1000000] * 13,
    }, index=dates)
    data_provider.get_bars.return_value = df

    asyncio.run(engine.tick())

    # Engine should have processed the data (exact trade depends on signal)
    assert data_provider.get_bars.called


def test_engine_stop(tmp_path):
    engine, _, _ = _make_engine(tmp_path)
    engine.stop()
    assert engine._running is False
