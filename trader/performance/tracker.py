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

        if equity_history:
            equities = [s.total_equity for s in sorted(equity_history, key=lambda s: s.timestamp)]
            metrics.max_drawdown = self._max_drawdown(equities)
            metrics.total_return_pct = ((equities[-1] - self.starting_cash) / self.starting_cash) * 100

            if len(equities) > 1:
                returns = [(equities[i] - equities[i - 1]) / equities[i - 1]
                           for i in range(1, len(equities)) if equities[i - 1] != 0]
                metrics.sharpe_ratio = self._sharpe(returns)

        return metrics

    @staticmethod
    def _compute_trade_pnls(trades: list[Trade]) -> list[float]:
        """Pair BUY/SELL trades per (symbol, strategy) in FIFO order."""
        buys: dict[tuple[str, str], list[Trade]] = {}
        pnls: list[float] = []
        sorted_trades = sorted(trades, key=lambda t: t.timestamp)
        for t in sorted_trades:
            key = (t.symbol, t.strategy_name)
            if t.side == "BUY":
                buys.setdefault(key, []).append(t)
            elif t.side == "SELL" and buys.get(key):
                remaining_sell_qty = t.quantity
                while remaining_sell_qty > 0 and buys.get(key):
                    buy = buys[key][0]
                    matched_qty = min(buy.quantity, remaining_sell_qty)
                    pnls.append((t.price - buy.price) * matched_qty)
                    buy.quantity -= matched_qty
                    remaining_sell_qty -= matched_qty
                    if buy.quantity <= 0:
                        buys[key].pop(0)
        return pnls

    @staticmethod
    def _max_drawdown(equities: list[float]) -> float:
        if not equities:
            return 0.0
        peak = equities[0]
        max_dd = 0.0
        for eq in equities:
            if eq > peak:
                peak = eq
            if peak > 0:
                dd = (peak - eq) / peak
                if dd > max_dd:
                    max_dd = dd
        return max_dd

    @staticmethod
    def _sharpe(returns: list[float], risk_free_annual: float = 0.0, periods: int = 252) -> float:
        if len(returns) < 2:
            return 0.0
        mean_r = sum(returns) / len(returns)
        excess = mean_r - risk_free_annual / periods
        variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
        std_r = math.sqrt(variance)
        if std_r == 0:
            return 0.0
        return (excess / std_r) * math.sqrt(periods)
