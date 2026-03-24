"""Load and validate configuration from config.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class TradingConfig:
    starting_cash: float = 100_000.0
    symbols: list[str] = field(default_factory=lambda: ["SPY"])
    tick_interval_seconds: int = 60


@dataclass
class StrategyConfig:
    enabled: bool = True
    fast_period: int = 10
    slow_period: int = 30
    symbols: list[str] = field(default_factory=lambda: ["SPY"])


@dataclass
class BrokerConfig:
    slippage_pct: float = 0.001
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


def load_config(path: str = "config.yaml") -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
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

    return AppConfig(
        trading=trading,
        strategies=strategies,
        broker=broker,
        database_path=db_path,
        dashboard=dashboard,
        analysis=analysis,
    )
