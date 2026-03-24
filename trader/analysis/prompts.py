"""Prompt templates for Claude analysis."""

from __future__ import annotations

from trader.core.models import Trade
from trader.performance.tracker import PerformanceMetrics


def build_performance_review_prompt(
    trades: list[Trade],
    metrics: PerformanceMetrics,
    strategy_params: dict[str, dict],
) -> str:
    trades_summary = "\n".join(
        f"  {t.timestamp:%Y-%m-%d %H:%M} | {t.side:4s} {t.symbol:5s} | "
        f"{t.quantity:.0f} shares @ ${t.price:.2f} | strategy={t.strategy_name}"
        for t in sorted(trades, key=lambda t: t.timestamp)[-30:]  # Last 30 trades
    )

    params_summary = "\n".join(
        f"  {name}: {params}" for name, params in strategy_params.items()
    )

    return f"""You are a quantitative trading analyst. Review this paper trading bot's recent performance and provide actionable suggestions.

## Performance Metrics
- Total trades: {metrics.total_trades}
- Win rate: {metrics.win_rate:.1%}
- Total PnL: ${metrics.total_pnl:,.2f}
- Avg win: ${metrics.avg_win:,.2f}
- Avg loss: ${metrics.avg_loss:,.2f}
- Max drawdown: {metrics.max_drawdown:.1%}
- Sharpe ratio: {metrics.sharpe_ratio:.2f}
- Total return: {metrics.total_return_pct:.2f}%

## Recent Trades
{trades_summary}

## Strategy Parameters
{params_summary}

## Instructions
Analyze the performance and provide:
1. **Assessment**: Brief assessment of overall performance (2-3 sentences)
2. **Patterns**: Any patterns in winning vs losing trades
3. **Parameter suggestions**: Specific parameter changes to try (e.g., adjust SMA periods)
4. **New theories**: 1-2 simple strategy ideas worth testing
5. **Risk**: Any risk management concerns

Keep your response concise and actionable. Focus on what to change next."""
