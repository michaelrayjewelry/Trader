"""Performance dashboard routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from trader.db import queries

router = APIRouter()


@router.get("/performance", response_class=HTMLResponse)
async def performance_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse("performance.html", {"request": request})


@router.get("/partials/equity-curve", response_class=HTMLResponse)
async def equity_curve(request: Request):
    templates = request.app.state.templates
    db = request.app.state.db
    tracker = request.app.state.performance_tracker

    equity_data = []
    metrics = None
    if db:
        history = queries.get_equity_history(db, limit=500)
        equity_data = [
            {"time": s.timestamp.strftime("%Y-%m-%d"), "value": round(s.total_equity, 2)}
            for s in sorted(history, key=lambda s: s.timestamp)
        ]
        if tracker:
            trades = queries.get_trades(db, limit=500)
            metrics = tracker.calculate(trades, history)

    return templates.TemplateResponse("partials/equity_curve.html", {
        "request": request,
        "equity_data": json.dumps(equity_data),
        "metrics": metrics,
    })
