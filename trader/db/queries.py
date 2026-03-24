"""Named query functions for database operations."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from trader.core.models import Position, PortfolioSnapshot, Trade

if TYPE_CHECKING:
    from trader.db.database import Database


def insert_trade(db: Database, trade: Trade) -> None:
    db.conn.execute(
        "INSERT INTO trades (id, order_id, symbol, side, quantity, price, timestamp, strategy_name) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (trade.id, trade.order_id, trade.symbol, trade.side,
         trade.quantity, trade.price, trade.timestamp.isoformat(), trade.strategy_name),
    )
    db.conn.commit()


def get_trades(db: Database, strategy_name: str | None = None, limit: int = 100) -> list[Trade]:
    if strategy_name:
        rows = db.conn.execute(
            "SELECT * FROM trades WHERE strategy_name = ? ORDER BY timestamp DESC LIMIT ?",
            (strategy_name, limit),
        ).fetchall()
    else:
        rows = db.conn.execute(
            "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return [
        Trade(
            id=r["id"], order_id=r["order_id"], symbol=r["symbol"],
            side=r["side"], quantity=r["quantity"], price=r["price"],
            timestamp=datetime.fromisoformat(r["timestamp"]),
            strategy_name=r["strategy_name"],
        )
        for r in rows
    ]


def upsert_position(db: Database, position: Position) -> None:
    if position.quantity == 0:
        db.conn.execute(
            "DELETE FROM positions WHERE symbol = ? AND strategy_name = ?",
            (position.symbol, position.strategy_name),
        )
    else:
        db.conn.execute(
            "INSERT INTO positions (symbol, strategy_name, quantity, avg_entry_price) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(symbol, strategy_name) DO UPDATE SET quantity=?, avg_entry_price=?",
            (position.symbol, position.strategy_name, position.quantity,
             position.avg_entry_price, position.quantity, position.avg_entry_price),
        )
    db.conn.commit()


def get_positions(db: Database, strategy_name: str | None = None) -> list[Position]:
    if strategy_name:
        rows = db.conn.execute(
            "SELECT * FROM positions WHERE strategy_name = ?", (strategy_name,)
        ).fetchall()
    else:
        rows = db.conn.execute("SELECT * FROM positions").fetchall()
    return [
        Position(
            symbol=r["symbol"], quantity=r["quantity"],
            avg_entry_price=r["avg_entry_price"],
            strategy_name=r["strategy_name"],
        )
        for r in rows
    ]


def insert_equity_snapshot(db: Database, snapshot: PortfolioSnapshot) -> None:
    db.conn.execute(
        "INSERT INTO equity_snapshots (timestamp, total_equity, cash, strategy_name) "
        "VALUES (?, ?, ?, ?)",
        (snapshot.timestamp.isoformat(), snapshot.total_equity,
         snapshot.cash, snapshot.strategy_name),
    )
    db.conn.commit()


def get_equity_history(db: Database, strategy_name: str | None = None, limit: int = 500) -> list[PortfolioSnapshot]:
    if strategy_name:
        rows = db.conn.execute(
            "SELECT * FROM equity_snapshots WHERE strategy_name = ? ORDER BY timestamp DESC LIMIT ?",
            (strategy_name, limit),
        ).fetchall()
    else:
        rows = db.conn.execute(
            "SELECT * FROM equity_snapshots WHERE strategy_name IS NULL ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        PortfolioSnapshot(
            timestamp=datetime.fromisoformat(r["timestamp"]),
            total_equity=r["total_equity"], cash=r["cash"],
            strategy_name=r["strategy_name"],
        )
        for r in rows
    ]


def get_trade_count(db: Database) -> int:
    row = db.conn.execute("SELECT COUNT(*) as cnt FROM trades").fetchone()
    return row["cnt"]


def insert_analysis(db: Database, analysis_type: str, content: str, recommendations: str | None = None) -> None:
    db.conn.execute(
        "INSERT INTO analysis_results (timestamp, analysis_type, content, recommendations) "
        "VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), analysis_type, content, recommendations),
    )
    db.conn.commit()


def get_latest_analysis(db: Database, limit: int = 5) -> list[dict]:
    rows = db.conn.execute(
        "SELECT * FROM analysis_results ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]
