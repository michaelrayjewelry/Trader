"""Paper broker — simulates trade execution without real money."""

from __future__ import annotations

import logging
from datetime import datetime

from trader.broker.base import Broker
from trader.core.models import Order, Position, Trade
from trader.db.database import Database
from trader.db import queries

logger = logging.getLogger(__name__)


class PaperBroker(Broker):
    def __init__(
        self,
        db: Database,
        starting_cash: float = 100_000.0,
        slippage_pct: float = 0.001,
    ) -> None:
        self.db = db
        self._cash = starting_cash
        self._positions: dict[tuple[str, str], Position] = {}  # (symbol, strategy) -> Position
        self.slippage_pct = slippage_pct
        self._current_prices: dict[str, float] = {}

    def update_price(self, symbol: str, price: float) -> None:
        self._current_prices[symbol] = price
        for key, pos in self._positions.items():
            if key[0] == symbol:
                pos.current_price = price

    def execute(self, order: Order, strategy_name: str = "") -> Trade | None:
        price = self._current_prices.get(order.symbol)
        if price is None:
            logger.warning("No price for %s, rejecting order", order.symbol)
            return None

        # Apply slippage
        if order.side == "BUY":
            fill_price = price * (1 + self.slippage_pct)
        else:
            fill_price = price * (1 - self.slippage_pct)

        cost = fill_price * order.quantity

        # Check buying power
        if order.side == "BUY" and cost > self._cash:
            logger.warning("Insufficient cash for %s %s (need %.2f, have %.2f)",
                           order.side, order.symbol, cost, self._cash)
            return None

        # Create trade
        trade = Trade(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            strategy_name=strategy_name,
            order_id=order.id,
            timestamp=datetime.now(),
        )

        # Update position
        key = (order.symbol, strategy_name)
        pos = self._positions.get(key)

        if order.side == "BUY":
            self._cash -= cost
            if pos:
                total_cost = pos.avg_entry_price * pos.quantity + cost
                pos.quantity += order.quantity
                pos.avg_entry_price = total_cost / pos.quantity
            else:
                pos = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    avg_entry_price=fill_price,
                    strategy_name=strategy_name,
                    current_price=price,
                )
                self._positions[key] = pos
        else:  # SELL
            self._cash += cost
            if pos:
                pos.quantity -= order.quantity
                if pos.quantity <= 0:
                    del self._positions[key]
                    pos.quantity = 0

        # Persist
        queries.insert_trade(self.db, trade)
        if pos:
            queries.upsert_position(self.db, pos)

        order.status = "FILLED"
        logger.info("FILLED: %s %s %.2f shares @ $%.2f", order.side, order.symbol,
                     order.quantity, fill_price)
        return trade

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    def get_cash(self) -> float:
        return self._cash

    def get_total_equity(self) -> float:
        positions_value = sum(p.market_value for p in self._positions.values())
        return self._cash + positions_value
