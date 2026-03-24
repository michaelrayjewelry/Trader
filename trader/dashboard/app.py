"""FastAPI dashboard application."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

if TYPE_CHECKING:
    from trader.core.events import EventBus

DASHBOARD_DIR = Path(__file__).parent
TEMPLATES_DIR = DASHBOARD_DIR / "templates"
STATIC_DIR = DASHBOARD_DIR / "static"


def create_app(event_bus: "EventBus" = None, **kwargs) -> FastAPI:
    app = FastAPI(title="Trader Dashboard", docs_url="/api/docs")
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    # Store shared state on app
    app.state.event_bus = event_bus
    app.state.db = kwargs.get("db")
    app.state.broker = kwargs.get("broker")
    app.state.engine = kwargs.get("engine")
    app.state.strategies = kwargs.get("strategies", [])
    app.state.performance_tracker = kwargs.get("performance_tracker")
    app.state.analyst = kwargs.get("analyst")
    app.state.templates = templates

    # Register routes
    from trader.dashboard.routes.overview import router as overview_router
    from trader.dashboard.routes.trades import router as trades_router
    from trader.dashboard.routes.performance import router as performance_router

    app.include_router(overview_router)
    app.include_router(trades_router)
    app.include_router(performance_router)

    # SSE endpoint for live updates
    @app.get("/api/stream")
    async def event_stream(request: Request):
        async def generate():
            queue: asyncio.Queue = asyncio.Queue()

            async def handler(data):
                await queue.put(data)

            if app.state.event_bus:
                app.state.event_bus.on("trade", handler)
                app.state.event_bus.on("tick", handler)

            try:
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        data = await asyncio.wait_for(queue.get(), timeout=30)
                        yield {"event": "update", "data": str(data)}
                    except asyncio.TimeoutError:
                        yield {"event": "ping", "data": ""}
            finally:
                if app.state.event_bus:
                    app.state.event_bus.off("trade", handler)
                    app.state.event_bus.off("tick", handler)

        return EventSourceResponse(generate())

    return app
