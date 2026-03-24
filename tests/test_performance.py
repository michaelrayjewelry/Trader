"""Tests for the performance tracker."""

from datetime import datetime, timedelta

from trader.core.models import Trade, PortfolioSnapshot
from trader.performance.tracker import PerformanceTracker


def _trade(symbol, side, qty, price, strategy="test", days_offset=0):
    return Trade(
        symbol=symbol, side=side, quantity=qty, price=price,
        strategy_name=strategy,
        timestamp=datetime(2024, 1, 1) + timedelta(days=days_offset),
    )


def test_empty_trades():
    tracker = PerformanceTracker()
    metrics = tracker.calculate([], [])
    assert metrics.total_trades == 0
    assert metrics.win_rate == 0.0


def test_winning_trade():
    trades = [
        _trade("AAPL", "BUY", 10, 100.0, days_offset=0),
        _trade("AAPL", "SELL", 10, 110.0, days_offset=1),
    ]
    tracker = PerformanceTracker()
    metrics = tracker.calculate(trades, [])
    assert metrics.total_trades == 1
    assert metrics.winning_trades == 1
    assert metrics.total_pnl == 100.0  # (110 - 100) * 10


def test_losing_trade():
    trades = [
        _trade("AAPL", "BUY", 10, 100.0, days_offset=0),
        _trade("AAPL", "SELL", 10, 90.0, days_offset=1),
    ]
    tracker = PerformanceTracker()
    metrics = tracker.calculate(trades, [])
    assert metrics.total_trades == 1
    assert metrics.losing_trades == 1
    assert metrics.total_pnl == -100.0


def test_pnl_grouped_by_strategy():
    """Trades for the same symbol but different strategies should be paired separately."""
    trades = [
        _trade("AAPL", "BUY", 10, 100.0, strategy="strat_a", days_offset=0),
        _trade("AAPL", "BUY", 10, 150.0, strategy="strat_b", days_offset=1),
        _trade("AAPL", "SELL", 10, 120.0, strategy="strat_a", days_offset=2),
        _trade("AAPL", "SELL", 10, 140.0, strategy="strat_b", days_offset=3),
    ]
    tracker = PerformanceTracker()
    metrics = tracker.calculate(trades, [])
    # strat_a: (120-100)*10 = 200 profit
    # strat_b: (140-150)*10 = -100 loss
    assert metrics.total_trades == 2
    assert metrics.total_pnl == 100.0


def test_partial_sell():
    """Selling less than the full buy quantity."""
    trades = [
        _trade("AAPL", "BUY", 10, 100.0, days_offset=0),
        _trade("AAPL", "SELL", 5, 120.0, days_offset=1),
    ]
    tracker = PerformanceTracker()
    metrics = tracker.calculate(trades, [])
    assert metrics.total_trades == 1
    assert metrics.total_pnl == 100.0  # (120-100)*5


def test_max_drawdown():
    equities = [100, 110, 90, 95, 80, 120]
    snapshots = [
        PortfolioSnapshot(
            timestamp=datetime(2024, 1, 1) + timedelta(days=i),
            cash=0, total_equity=eq,
        )
        for i, eq in enumerate(equities)
    ]
    tracker = PerformanceTracker(starting_cash=100)
    metrics = tracker.calculate(
        [_trade("X", "BUY", 1, 100)],  # need at least 1 trade
        snapshots,
    )
    # Peak was 110, trough was 80 → dd = (110-80)/110 = 27.27%
    assert abs(metrics.max_drawdown - 0.2727) < 0.01
