"""Domain models for the trading system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
import uuid


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class OHLCV:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    symbol: str = ""


@dataclass
class Signal:
    timestamp: datetime
    symbol: str
    direction: Literal["BUY", "SELL"]
    strength: float  # 0.0 to 1.0
    strategy_name: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Order:
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    order_type: Literal["MARKET", "LIMIT"] = "MARKET"
    limit_price: float | None = None
    status: Literal["PENDING", "FILLED", "CANCELLED"] = "PENDING"
    id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Trade:
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: float
    price: float
    strategy_name: str
    order_id: str = ""
    id: str = field(default_factory=_new_id)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def value(self) -> float:
        return self.quantity * self.price


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_entry_price: float
    strategy_name: str
    current_price: float = 0.0

    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.avg_entry_price) * self.quantity

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price


@dataclass
class PortfolioSnapshot:
    timestamp: datetime
    cash: float
    total_equity: float
    strategy_name: str | None = None
