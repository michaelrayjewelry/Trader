"""Trade history routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from trader.db import queries

router = APIRouter()


@router.get("/trades", response_class=HTMLResponse)
async def trades_page(request: Request):
    templates = request.app.state.templates
    db = request.app.state.db

    trades = []
    if db:
        trades = queries.get_trades(db, limit=100)

    return templates.TemplateResponse("trades.html", {
        "request": request, "trades": trades,
    })
