"""Load and validate configuration from config.yaml."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class TradingConfig:
    starting_cash: float = 100_000.0
    symbols: list[str] = field(default_factory=lambda: ["SPY"])
    tick_interval_seconds: int = 60
    position_size_pct: float = 0.05  # % of equity per trade (0.05 = 5%)


@dataclass
class StrategyConfig:
    enabled: bool = True
    fast_period: int = 10
    slow_period: int = 30
    symbols: list[str] = field(default_factory=lambda: ["SPY"])


@dataclass
class BrokerConfig:
    slippage_pct: float = 0.001  # 0.001 = 0.1% slippage
    commission_per_trade: float = 0.0


@dataclass
class DashboardConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class AnalysisConfig:
    trades_before_review: int = 20
    model: str = "claude-sonnet-4-6"


@dataclass
class AppConfig:
    trading: TradingConfig = field(default_factory=TradingConfig)
    strategies: dict[str, StrategyConfig] = field(default_factory=dict)
    broker: BrokerConfig = field(default_factory=BrokerConfig)
    database_path: str = "data/trader.db"
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)


def _validate_config(config: AppConfig) -> list[str]:
    """Validate config and return list of warnings. Exit on fatal errors."""
    errors: list[str] = []
    warnings: list[str] = []

    if config.trading.starting_cash <= 0:
        errors.append("trading.starting_cash must be > 0")

    if not config.trading.symbols:
        warnings.append("No symbols configured — engine won't have anything to trade")

    if config.trading.position_size_pct <= 0 or config.trading.position_size_pct > 1:
        errors.append("trading.position_size_pct must be between 0 and 1 (e.g. 0.05 = 5%)")

    for name, strat in config.strategies.items():
        if hasattr(strat, "fast_period") and hasattr(strat, "slow_period"):
            if strat.fast_period >= strat.slow_period:
                errors.append(f"strategies.{name}: fast_period ({strat.fast_period}) must be < slow_period ({strat.slow_period})")
            if strat.fast_period < 2:
                errors.append(f"strategies.{name}: fast_period must be >= 2")
        if not strat.symbols:
            warnings.append(f"strategies.{name}: no symbols — strategy won't trade")

    if errors:
        for e in errors:
            logger.error("Config error: %s", e)
        print("\nConfiguration errors found. Fix config.yaml and try again.")
        sys.exit(1)

    return warnings


def load_config(path: str = "config.yaml") -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        logger.warning("No config.yaml found, using defaults")
        return AppConfig()

    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    trading = TradingConfig(**raw.get("trading", {}))

    strategies = {}
    for name, params in raw.get("strategies", {}).items():
        strategies[name] = StrategyConfig(**params)

    broker = BrokerConfig(**raw.get("broker", {}))
    dashboard = DashboardConfig(**raw.get("dashboard", {}))
    analysis = AnalysisConfig(**raw.get("analysis", {}))
    db_path = raw.get("database", {}).get("path", "data/trader.db")

    config = AppConfig(
        trading=trading,
        strategies=strategies,
        broker=broker,
        database_path=db_path,
        dashboard=dashboard,
        analysis=analysis,
    )

    warnings = _validate_config(config)
    for w in warnings:
        logger.warning("Config: %s", w)

    return config
