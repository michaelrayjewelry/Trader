"""Abstract broker interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from trader.core.models import Order, Position, Trade


class Broker(ABC):
    @abstractmethod
    def execute(self, order: Order) -> Trade | None:
        """Execute an order and return the resulting trade, or None if rejected."""
        ...

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Return all open positions."""
        ...

    @abstractmethod
    def get_cash(self) -> float:
        """Return available cash balance."""
        ...

    @abstractmethod
    def get_total_equity(self) -> float:
        """Return total portfolio value (cash + positions)."""
        ...
