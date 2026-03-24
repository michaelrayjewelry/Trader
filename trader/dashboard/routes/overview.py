"""Overview dashboard routes."""

from __future__ import annotations

import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from trader.db import queries

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def overview(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse("overview.html", {"request": request})


@router.get("/partials/engine-status", response_class=HTMLResponse)
async def engine_status(request: Request):
    templates = request.app.state.templates
    engine = request.app.state.engine
    broker = request.app.state.broker

    data = {
        "request": request,
        "status": "unknown",
        "tick_count": 0,
        "error_count": 0,
        "last_tick": None,
        "last_error": None,
        "trade_count": 0,
        "ai_enabled": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }
    if engine:
        data["status"] = engine.status
        data["tick_count"] = engine.tick_count
        data["error_count"] = engine.error_count
        data["last_tick"] = engine.last_tick_time
        data["last_error"] = engine.last_error

    db = request.app.state.db
    if db:
        data["trade_count"] = queries.get_trade_count(db)

    return templates.TemplateResponse("partials/engine_status.html", data)


@router.get("/partials/portfolio-summary", response_class=HTMLResponse)
async def portfolio_summary(request: Request):
    templates = request.app.state.templates
    broker = request.app.state.broker

    data = {
        "request": request,
        "cash": 0.0,
        "total_equity": 0.0,
        "positions": [],
        "starting_cash": 100_000.0,
    }
    if broker:
        data["cash"] = broker.get_cash()
        data["total_equity"] = broker.get_total_equity()
        data["positions"] = broker.get_positions()
        data["starting_cash"] = broker._cash + sum(
            p.market_value for p in broker.get_positions()
        )

    return templates.TemplateResponse("partials/portfolio_summary.html", data)


@router.get("/partials/recent-trades", response_class=HTMLResponse)
async def recent_trades(request: Request):
    templates = request.app.state.templates
    db = request.app.state.db

    trades = []
    if db:
        trades = queries.get_trades(db, limit=20)

    return templates.TemplateResponse("partials/recent_trades.html", {
        "request": request, "trades": trades,
    })


@router.get("/partials/strategy-cards", response_class=HTMLResponse)
async def strategy_cards(request: Request):
    templates = request.app.state.templates
    strategies = request.app.state.strategies or []

    cards = []
    for s in strategies:
        params = s.get_params()
        # Format lists nicely for display
        display_params = {}
        for k, v in params.items():
            if isinstance(v, list):
                display_params[k] = ", ".join(str(i) for i in v)
            else:
                display_params[k] = v
        cards.append({"name": s.name, "symbols": s.symbols, "params": display_params})

    return templates.TemplateResponse("partials/strategy_cards.html", {
        "request": request, "strategies": cards,
    })


@router.get("/partials/ai-insights", response_class=HTMLResponse)
async def ai_insights(request: Request):
    templates = request.app.state.templates
    db = request.app.state.db

    analyses = []
    ai_enabled = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if db:
        analyses = queries.get_latest_analysis(db, limit=3)

    return templates.TemplateResponse("partials/ai_insights.html", {
        "request": request, "analyses": analyses, "ai_enabled": ai_enabled,
    })
