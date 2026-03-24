"""Entry point — starts the trading engine and dashboard."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys

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


def print_banner(config, strategies, ai_enabled: bool) -> None:
    """Print a friendly startup summary."""
    symbols = set()
    for s in strategies:
        symbols.update(s.symbols)

    print()
    print("=" * 56)
    print("  TRADER — Paper Trading Bot")
    print("=" * 56)
    print()
    print(f"  Dashboard:    http://localhost:{config.dashboard.port}")
    print(f"  API docs:     http://localhost:{config.dashboard.port}/api/docs")
    print(f"  Starting cash: ${config.trading.starting_cash:,.2f}")
    print(f"  Symbols:       {', '.join(sorted(symbols)) or 'none'}")
    print(f"  Strategies:    {len(strategies)} active")
    for s in strategies:
        print(f"                 - {s.name} ({', '.join(s.symbols)})")
    print(f"  Tick interval: {config.trading.tick_interval_seconds}s")
    print(f"  Position size: {config.trading.position_size_pct:.0%} of equity per trade")
    print(f"  AI analysis:   {'enabled' if ai_enabled else 'disabled (set ANTHROPIC_API_KEY)'}")
    print(f"  Database:      {config.database_path}")
    print()
    print("  Press Ctrl+C to stop.")
    print("=" * 56)
    print()


def build_components():
    """Wire up all components from config."""
    config = load_config()

    db = Database(config.database_path)
    db.init_schema()

    event_bus = EventBus()

    broker = PaperBroker(
        db=db,
        starting_cash=config.trading.starting_cash,
        slippage_pct=config.broker.slippage_pct,
    )

    strategies = []
    sma_config = config.strategies.get("sma_crossover")
    if sma_config and sma_config.enabled:
        strategies.append(SMACrossover(
            symbols=sma_config.symbols,
            fast_period=sma_config.fast_period,
            slow_period=sma_config.slow_period,
        ))

    if not strategies:
        logger.warning("No strategies enabled — engine will run but won't trade")

    data_provider = YahooDataProvider()
    performance_tracker = PerformanceTracker(starting_cash=config.trading.starting_cash)

    ai_enabled = bool(os.environ.get("ANTHROPIC_API_KEY"))
    analyst = ClaudeAnalyst(model=config.analysis.model)

    engine = TradingEngine(
        data_provider=data_provider,
        strategies=strategies,
        broker=broker,
        db=db,
        event_bus=event_bus,
        position_size_pct=config.trading.position_size_pct,
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
            result = await analyst.review_performance(trades, metrics, params, db)
            if result:
                logger.info("AI analysis complete — view at /partials/ai-insights")

    event_bus.on("trade", maybe_run_analysis)

    app = create_app(
        event_bus=event_bus,
        db=db,
        broker=broker,
        engine=engine,
        strategies=strategies,
        performance_tracker=performance_tracker,
        analyst=analyst,
    )

    print_banner(config, strategies, ai_enabled)

    return app, engine, config, db


async def run():
    app, engine, config, db = build_components()

    engine_task = asyncio.create_task(
        engine.run(interval_seconds=config.trading.tick_interval_seconds)
    )

    server_config = uvicorn.Config(
        app,
        host=config.dashboard.host,
        port=config.dashboard.port,
        log_level="info",
    )
    server = uvicorn.Server(server_config)

    try:
        await server.serve()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        engine.stop()
        engine_task.cancel()
        try:
            await engine_task
        except asyncio.CancelledError:
            pass
        db.close()
        logger.info("Shutdown complete.")


def main():
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
