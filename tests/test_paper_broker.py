"""Tests for the paper broker."""

from trader.broker.paper import PaperBroker
from trader.core.models import Order
from trader.db.database import Database


def _make_broker(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.init_schema()
    broker = PaperBroker(db=db, starting_cash=100_000.0, slippage_pct=0.0)
    return broker, db


def test_buy_order(tmp_path):
    broker, db = _make_broker(tmp_path)
    broker.update_price("AAPL", 150.0)

    order = Order(symbol="AAPL", side="BUY", quantity=10)
    trade = broker.execute(order, strategy_name="test")

    assert trade is not None
    assert trade.symbol == "AAPL"
    assert trade.side == "BUY"
    assert trade.quantity == 10
    assert trade.price == 150.0
    assert broker.get_cash() == 100_000.0 - 1500.0
    assert len(broker.get_positions()) == 1
    assert broker.get_positions()[0].quantity == 10


def test_sell_order(tmp_path):
    broker, db = _make_broker(tmp_path)
    broker.update_price("AAPL", 150.0)

    # Buy first
    broker.execute(Order(symbol="AAPL", side="BUY", quantity=10), strategy_name="test")

    # Sell
    broker.update_price("AAPL", 160.0)
    trade = broker.execute(Order(symbol="AAPL", side="SELL", quantity=10), strategy_name="test")

    assert trade is not None
    assert trade.price == 160.0
    assert broker.get_cash() == 100_000.0 - 1500.0 + 1600.0
    assert len(broker.get_positions()) == 0


def test_insufficient_cash(tmp_path):
    broker, db = _make_broker(tmp_path)
    broker.update_price("AAPL", 150.0)

    order = Order(symbol="AAPL", side="BUY", quantity=1000)
    trade = broker.execute(order, strategy_name="test")

    assert trade is None  # Cost would be 150k, only have 100k


def test_total_equity(tmp_path):
    broker, db = _make_broker(tmp_path)
    broker.update_price("AAPL", 150.0)

    broker.execute(Order(symbol="AAPL", side="BUY", quantity=10), strategy_name="test")

    # Equity = cash + position value
    assert broker.get_total_equity() == 100_000.0  # No price change, no slippage
