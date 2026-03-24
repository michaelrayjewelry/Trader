"""Overview dashboard routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from trader.db import queries

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def overview(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse("overview.html", {"request": request})


@router.get("/partials/portfolio-summary", response_class=HTMLResponse)
async def portfolio_summary(request: Request):
    templates = request.app.state.templates
    broker = request.app.state.broker

    data = {
        "request": request,
        "cash": 0.0,
        "total_equity": 0.0,
        "positions": [],
    }
    if broker:
        data["cash"] = broker.get_cash()
        data["total_equity"] = broker.get_total_equity()
        data["positions"] = broker.get_positions()

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
        cards.append({"name": s.name, "symbols": s.symbols, "params": s.get_params()})

    return templates.TemplateResponse("partials/strategy_cards.html", {
        "request": request, "strategies": cards,
    })


@router.get("/partials/ai-insights", response_class=HTMLResponse)
async def ai_insights(request: Request):
    templates = request.app.state.templates
    db = request.app.state.db

    analyses = []
    if db:
        analyses = queries.get_latest_analysis(db, limit=3)

    return templates.TemplateResponse("partials/ai_insights.html", {
        "request": request, "analyses": analyses,
    })
