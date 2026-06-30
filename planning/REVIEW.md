# Review: Changes Since Last Commit

## Findings

1. **High: SSE delta mode has no way to remove tickers from connected clients.**

   `PriceCache.remove()` deletes the ticker and its version stamp without incrementing the cache version or emitting any tombstone/removal state ([backend/app/market/cache.py](../backend/app/market/cache.py:77)). The stream now sends an initial snapshot and then only changed tickers ([backend/app/market/stream.py](../backend/app/market/stream.py:81), [backend/app/market/stream.py](../backend/app/market/stream.py:96)). A client that already received `AAPL` will never be told that `AAPL` was removed; it will keep rendering the stale last price indefinitely unless it reconnects. This matters for the planned watchlist removal flow and for any UI that treats SSE events as merge patches. Consider incrementing the version on removal and sending explicit removal events/tombstones, or periodically/full-snapshotting the authoritative priced set.

2. **Medium: The repo-level Stop hook runs an expensive review command after every assistant completion.**

   `.claude/settings.json` now installs a `Stop` hook that runs `codex exec "review the the changes since last commit and write your feedback to the file named planning/REVIEW.md"` unconditionally ([.claude/settings.json](../.claude/settings.json:7), [.claude/settings.json](../.claude/settings.json:13)). The plugin hook duplicates the same command ([planning/independent-reviewer/hooks/hooks.json](independent-reviewer/hooks/hooks.json:2)). If this is committed as-is, every project stop event can spawn a new Codex review, mutate `planning/REVIEW.md`, consume tokens/time, and surprise future contributors. If the hook is intended, gate it behind explicit opt-in plugin installation or keep it out of tracked project settings.

## Verification

- Passed: `backend/.venv/bin/python -m pytest` from `backend` (`86 passed in 1.08s`).
- Note: `uv run pytest` could not be used in this sandbox. First it was blocked from reading `/Users/prevost/.cache/uv/...`; with `UV_CACHE_DIR` moved into the workspace, `uv` panicked in `system-configuration`.
