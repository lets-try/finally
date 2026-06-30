"""Tests for the SSE streaming generator."""

import json

from app.market.cache import PriceCache
from app.market.stream import _generate_events


class FakeClient:
    host = "127.0.0.1"


class FakeRequest:
    """Minimal stand-in for a Starlette Request driving the SSE generator."""

    def __init__(self, disconnected: bool = False) -> None:
        self.client = FakeClient()
        self.disconnected = disconnected

    async def is_disconnected(self) -> bool:
        return self.disconnected


def _parse_data(event: str) -> dict:
    """Extract the JSON payload from an SSE `data:` frame."""
    assert event.startswith("data: ")
    return json.loads(event[len("data: ") :].strip())


class TestStreamGenerator:
    """Unit tests for _generate_events."""

    async def test_first_frame_is_retry_directive(self):
        """The stream opens with a retry directive for EventSource."""
        cache = PriceCache()
        gen = _generate_events(cache, FakeRequest(disconnected=True), interval=0.01)
        first = await anext(gen)
        assert first == "retry: 1000\n\n"

    async def test_initial_snapshot_contains_all_tickers(self):
        """On connect the client receives a full snapshot of the priced set."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        cache.update("GOOGL", 175.00)

        gen = _generate_events(cache, FakeRequest(), interval=0.01)
        await anext(gen)  # retry
        snapshot = _parse_data(await anext(gen))
        assert set(snapshot.keys()) == {"AAPL", "GOOGL"}
        assert snapshot["AAPL"]["price"] == 190.00

    async def test_only_changed_tickers_pushed_after_snapshot(self):
        """Subsequent frames carry only the tickers that changed."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)

        gen = _generate_events(cache, FakeRequest(), interval=0.01)
        await anext(gen)  # retry
        _parse_data(await anext(gen))  # initial snapshot (AAPL)

        # A new ticker moves; the next frame should contain only it.
        cache.update("GOOGL", 175.00)
        changed = _parse_data(await anext(gen))
        assert set(changed.keys()) == {"GOOGL"}

    async def test_empty_cache_sends_no_snapshot(self):
        """With an empty cache there is no snapshot frame before the loop."""
        cache = PriceCache()
        gen = _generate_events(cache, FakeRequest(disconnected=True), interval=0.01)
        assert await anext(gen) == "retry: 1000\n\n"
        # Disconnected immediately and nothing to send -> generator stops.
        try:
            await anext(gen)
            raise AssertionError("expected the generator to stop")
        except StopAsyncIteration:
            pass

    async def test_disconnect_stops_generator(self):
        """The generator terminates once the client disconnects."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        request = FakeRequest()

        gen = _generate_events(cache, request, interval=0.01)
        await anext(gen)  # retry
        await anext(gen)  # snapshot

        request.disconnected = True
        try:
            await anext(gen)
            raise AssertionError("expected the generator to stop")
        except StopAsyncIteration:
            pass

    async def test_keepalive_during_quiet_period(self):
        """A keepalive comment is emitted when no prices change."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)

        # keepalive_interval=0 makes the comment fire on the first quiet tick.
        gen = _generate_events(
            cache, FakeRequest(), interval=0.01, keepalive_interval=0.0
        )
        await anext(gen)  # retry
        await anext(gen)  # snapshot
        # No cache change -> next yield is the keepalive comment.
        assert await anext(gen) == ": keepalive\n\n"
