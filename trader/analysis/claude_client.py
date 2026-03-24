"""Claude API client for trade analysis and strategy improvement."""

from __future__ import annotations

import logging
import os

from anthropic import Anthropic

from trader.analysis.prompts import build_performance_review_prompt
from trader.core.models import Trade
from trader.db.database import Database
from trader.db import queries
from trader.performance.tracker import PerformanceMetrics

logger = logging.getLogger(__name__)


class ClaudeAnalyst:
    """Uses Claude to analyze trading performance and suggest improvements."""

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set — AI analysis disabled")
            self._client = None
        else:
            self._client = Anthropic(api_key=api_key)
        self.model = model

    async def review_performance(
        self,
        trades: list[Trade],
        metrics: PerformanceMetrics,
        strategy_params: dict[str, dict],
        db: Database,
    ) -> str | None:
        """Ask Claude to review recent trading performance and suggest improvements."""
        if not self._client:
            return None

        prompt = build_performance_review_prompt(trades, metrics, strategy_params)

        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text

            # Persist the analysis
            queries.insert_analysis(db, "performance_review", content)
            logger.info("Claude analysis complete (%d chars)", len(content))
            return content

        except Exception:
            logger.exception("Claude analysis failed")
            return None
