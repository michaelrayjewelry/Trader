"""Trading engine — orchestrates data, strategies, and broker."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from trader.broker.paper import PaperBroker
from trader.core.events import EventBus
from trader.core.models import Order, PortfolioSnapshot
from trader.data.base import DataProvider
from trader.db.database import Database
from trader.db import queries
from trader.strategies.base import Strategy

logger = logging.getLogger(__name__)


class TradingEngine:
    def __init__(
        self,
        data_provider: DataProvider,
        strategies: list[Strategy],
        broker: PaperBroker,
        db: Database,
        event_bus: EventBus,
        position_size_pct: float = 0.05,
    ) -> None:
        self.data_provider = data_provider
        self.strategies = strategies
        self.broker = broker
        self.db = db
        self.event_bus = event_bus
        self.position_size_pct = position_size_pct
        self._running = False

    async def tick(self) -> None:
        """One iteration: fetch data, run strategies, execute orders."""
        for strategy in self.strategies:
            for symbol in strategy.symbols:
                try:
                    # Fetch latest bars
                    bars = await self.data_provider.get_bars(symbol, period="3mo", interval="1d")
                    if bars.empty:
                        continue

                    # Update broker with latest price
                    current_price = float(bars["close"].iloc[-1])
                    self.broker.update_price(symbol, current_price)

                    # Run strategy
                    signal = strategy.on_bar(symbol, bars)
                    if signal is None:
                        continue

                    logger.info("Signal: %s %s from %s (strength=%.2f)",
                                signal.direction, signal.symbol, signal.strategy_name, signal.strength)

                    # Convert signal to order
                    order = self._signal_to_order(signal)
                    if order is None:
                        continue

                    # Execute
                    trade = self.broker.execute(order, strategy_name=strategy.name)
                    if trade:
                        await self.event_bus.emit("trade", trade)

                except Exception:
                    logger.exception("Error processing %s with %s", symbol, strategy.name)

        # Snapshot equity
        snapshot = PortfolioSnapshot(
            timestamp=datetime.now(),
            cash=self.broker.get_cash(),
            total_equity=self.broker.get_total_equity(),
        )
        queries.insert_equity_snapshot(self.db, snapshot)
        await self.event_bus.emit("tick", snapshot)

    def _signal_to_order(self, signal) -> Order | None:
        equity = self.broker.get_total_equity()
        position_value = equity * self.position_size_pct * signal.strength

        price = self.broker._current_prices.get(signal.symbol)
        if not price or price <= 0:
            return None

        quantity = int(position_value / price)
        if quantity <= 0:
            return None

        # For SELL signals, only sell if we have a position
        if signal.direction == "SELL":
            positions = self.broker.get_positions()
            held = sum(p.quantity for p in positions
                       if p.symbol == signal.symbol and p.strategy_name == signal.strategy_name)
            if held <= 0:
                return None
            quantity = min(quantity, int(held))

        return Order(
            symbol=signal.symbol,
            side=signal.direction,
            quantity=quantity,
        )

    async def run(self, interval_seconds: int = 60) -> None:
        """Main loop."""
        self._running = True
        logger.info("Trading engine started (interval=%ds)", interval_seconds)
        while self._running:
            await self.tick()
            await asyncio.sleep(interval_seconds)

    def stop(self) -> None:
        self._running = False
        logger.info("Trading engine stopped")
