"""Performance metrics calculation from trade history."""

from __future__ import annotations

import math
from dataclasses import dataclass

from trader.core.models import Trade, PortfolioSnapshot


@dataclass
class PerformanceMetrics:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    total_return_pct: float = 0.0


class PerformanceTracker:
    def __init__(self, starting_cash: float = 100_000.0) -> None:
        self.starting_cash = starting_cash

    def calculate(
        self, trades: list[Trade], equity_history: list[PortfolioSnapshot]
    ) -> PerformanceMetrics:
        metrics = PerformanceMetrics()

        if not trades:
            return metrics

        # Match buy/sell trades per symbol to compute PnL
        pnls = self._compute_trade_pnls(trades)
        metrics.total_trades = len(pnls)
        metrics.winning_trades = sum(1 for p in pnls if p > 0)
        metrics.losing_trades = sum(1 for p in pnls if p < 0)
        metrics.total_pnl = sum(pnls)

        if metrics.total_trades > 0:
            metrics.win_rate = metrics.winning_trades / metrics.total_trades

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        metrics.avg_win = sum(wins) / len(wins) if wins else 0.0
        metrics.avg_loss = sum(losses) / len(losses) if losses else 0.0

        # Equity-based metrics
        if equity_history:
            equities = [s.total_equity for s in sorted(equity_history, key=lambda s: s.timestamp)]
            metrics.max_drawdown = self._max_drawdown(equities)
            metrics.total_return_pct = ((equities[-1] - self.starting_cash) / self.starting_cash) * 100

            # Daily returns for Sharpe
            if len(equities) > 1:
                returns = [(equities[i] - equities[i - 1]) / equities[i - 1]
                           for i in range(1, len(equities))]
                metrics.sharpe_ratio = self._sharpe(returns)

        return metrics

    @staticmethod
    def _compute_trade_pnls(trades: list[Trade]) -> list[float]:
        """Simple PnL: pair BUY then SELL for same symbol."""
        buys: dict[str, list[Trade]] = {}
        pnls = []
        # Process in chronological order
        sorted_trades = sorted(trades, key=lambda t: t.timestamp)
        for t in sorted_trades:
            if t.side == "BUY":
                buys.setdefault(t.symbol, []).append(t)
            elif t.side == "SELL" and buys.get(t.symbol):
                buy = buys[t.symbol].pop(0)
                qty = min(buy.quantity, t.quantity)
                pnls.append((t.price - buy.price) * qty)
        return pnls

    @staticmethod
    def _max_drawdown(equities: list[float]) -> float:
        peak = equities[0]
        max_dd = 0.0
        for eq in equities:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak
            if dd > max_dd:
                max_dd = dd
        return max_dd

    @staticmethod
    def _sharpe(returns: list[float], risk_free: float = 0.0, periods: int = 252) -> float:
        if not returns:
            return 0.0
        mean_r = sum(returns) / len(returns) - risk_free / periods
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / len(returns))
        if std_r == 0:
            return 0.0
        return (mean_r / std_r) * math.sqrt(periods)
