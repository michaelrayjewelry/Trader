"""Entry point — starts the trading engine and dashboard."""

from __future__ import annotations

import asyncio
import logging

import uvicorn

from trader.analysis.claude_client import ClaudeAnalyst
from trader.broker.paper import PaperBroker
from trader.config import load_config
from trader.core.engine import TradingEngine
from trader.core.events import EventBus
from trader.dashboard.app import create_app
from trader.data.yahoo import YahooDataProvider
from trader.db.database import Database
from trader.db import queries
from trader.performance.tracker import PerformanceTracker
from trader.strategies.sma_crossover import SMACrossover

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def build_components():
    """Wire up all components from config."""
    config = load_config()

    # Database
    db = Database(config.database_path)
    db.init_schema()

    # Event bus
    event_bus = EventBus()

    # Broker
    broker = PaperBroker(
        db=db,
        starting_cash=config.trading.starting_cash,
        slippage_pct=config.broker.slippage_pct,
    )

    # Strategies
    strategies = []
    sma_config = config.strategies.get("sma_crossover")
    if sma_config and sma_config.enabled:
        strategies.append(SMACrossover(
            symbols=sma_config.symbols,
            fast_period=sma_config.fast_period,
            slow_period=sma_config.slow_period,
        ))

    # Data provider
    data_provider = YahooDataProvider()

    # Performance tracker
    performance_tracker = PerformanceTracker(starting_cash=config.trading.starting_cash)

    # Claude analyst
    analyst = ClaudeAnalyst(model=config.analysis.model)

    # Trading engine
    engine = TradingEngine(
        data_provider=data_provider,
        strategies=strategies,
        broker=broker,
        db=db,
        event_bus=event_bus,
    )

    # Wire up analysis trigger
    trade_count_at_last_review = 0

    async def maybe_run_analysis(trade):
        nonlocal trade_count_at_last_review
        count = queries.get_trade_count(db)
        if count - trade_count_at_last_review >= config.analysis.trades_before_review:
            trade_count_at_last_review = count
            trades = queries.get_trades(db, limit=100)
            equity = queries.get_equity_history(db, limit=500)
            metrics = performance_tracker.calculate(trades, equity)
            params = {s.name: s.get_params() for s in strategies}
            await analyst.review_performance(trades, metrics, params, db)

    event_bus.on("trade", maybe_run_analysis)

    # Dashboard
    app = create_app(
        event_bus=event_bus,
        db=db,
        broker=broker,
        engine=engine,
        strategies=strategies,
        performance_tracker=performance_tracker,
        analyst=analyst,
    )

    return app, engine, config


async def run():
    app, engine, config = build_components()

    # Start trading engine in background
    engine_task = asyncio.create_task(
        engine.run(interval_seconds=config.trading.tick_interval_seconds)
    )

    # Start dashboard
    server_config = uvicorn.Config(
        app,
        host=config.dashboard.host,
        port=config.dashboard.port,
        log_level="info",
    )
    server = uvicorn.Server(server_config)

    try:
        await server.serve()
    finally:
        engine.stop()
        engine_task.cancel()


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
