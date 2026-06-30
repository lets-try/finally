"""SSE streaming endpoint for live price updates."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .cache import PriceCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stream", tags=["streaming"])


def create_stream_router(price_cache: PriceCache) -> APIRouter:
    """Create the SSE streaming router with a reference to the price cache.

    This factory pattern lets us inject the PriceCache without globals.
    """

    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        """SSE endpoint for live price updates.

        Sends one full snapshot of the current priced set on connect, then
        pushes only the tickers whose price changed on each subsequent tick
        (~500ms). The client connects with EventSource and receives events in
        the format:

            data: {"AAPL": {"ticker": "AAPL", "price": 190.50, ...}, ...}

        A periodic ``: keepalive`` comment holds the connection open through
        proxies during quiet periods. Includes a retry directive so the browser
        auto-reconnects on disconnection (EventSource built-in behavior).
        """
        return StreamingResponse(
            _generate_events(price_cache, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering if proxied
            },
        )

    return router


def _format_event(prices: dict) -> str:
    """Serialize a {ticker: PriceUpdate} mapping into an SSE data frame."""
    data = {ticker: update.to_dict() for ticker, update in prices.items()}
    return f"data: {json.dumps(data)}\n\n"


async def _generate_events(
    price_cache: PriceCache,
    request: Request,
    interval: float = 0.5,
    keepalive_interval: float = 15.0,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE-formatted price events.

    Sends one full snapshot on connect, then emits only the tickers that
    changed on each `interval`. A `: keepalive` comment is sent after
    `keepalive_interval` seconds of no changes to hold the connection open
    through proxies. Stops when the client disconnects (detected via
    request.is_disconnected()).
    """
    # Tell the client to retry after 1 second if the connection drops
    yield "retry: 1000\n\n"

    client_ip = request.client.host if request.client else "unknown"
    logger.info("SSE client connected: %s", client_ip)

    # Read the version before the snapshot so any update racing in between is
    # re-sent on the next tick (a harmless duplicate) rather than missed.
    last_version = price_cache.version
    snapshot = price_cache.get_all()
    if snapshot:
        yield _format_event(snapshot)
    last_sent = time.monotonic()

    try:
        while True:
            # Check for client disconnect
            if await request.is_disconnected():
                logger.info("SSE client disconnected: %s", client_ip)
                break

            current_version = price_cache.version
            if current_version != last_version:
                changed = price_cache.changed_since(last_version)
                last_version = current_version
                if changed:
                    yield _format_event(changed)
                    last_sent = time.monotonic()
            elif time.monotonic() - last_sent >= keepalive_interval:
                # Quiet period: send a comment to keep proxies from dropping us
                yield ": keepalive\n\n"
                last_sent = time.monotonic()

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled for: %s", client_ip)
