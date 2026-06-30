# FinAlly — AI Trading Workstation

A visually rich, AI-powered trading workstation that streams live market data, simulates portfolio trading, and integrates an LLM chat assistant that can analyze positions and execute trades via natural language.

Built entirely by coding agents as a capstone project for an agentic AI coding course.

## Status

🚧 **In active development.** The market-data subsystem (GBM simulator, thread-safe price cache, SSE streaming, Massive API client) is complete and tested. The full REST API, portfolio engine, AI chat, and Next.js frontend are still being built. See [`planning/PLAN.md`](planning/PLAN.md) for the full specification and [`planning/MARKET_DATA_SUMMARY.md`](planning/MARKET_DATA_SUMMARY.md) for what's done.

## Features

- **Live price streaming** via SSE with green/red flash animations
- **Simulated portfolio** — $10k virtual cash, market orders, instant fills
- **Portfolio visualizations** — heatmap (treemap), P&L chart, positions table
- **AI chat assistant** — analyzes holdings, suggests and auto-executes trades
- **Watchlist management** — track tickers manually or via AI
- **Dark terminal aesthetic** — Bloomberg-inspired, data-dense layout

## Architecture

Single Docker container serving everything on port 8000:

- **Frontend**: Next.js (static export) with TypeScript and Tailwind CSS
- **Backend**: FastAPI (Python/uv) with SSE streaming
- **Database**: SQLite with lazy initialization
- **AI**: LiteLLM → OpenRouter (Cerebras inference) with structured outputs
- **Market data**: Built-in GBM simulator (default) or Massive API (optional)

## Quick Start

### Run the backend (available today)

```bash
cd backend
uv sync --extra dev

uv run market_data_demo.py   # Live terminal dashboard of simulated prices
uv run pytest                # Run the test suite
```

### Full app via Docker (target deployment)

```bash
cp .env.example .env         # then add your OPENROUTER_API_KEY
docker build -t finally .
docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
# Open http://localhost:8000
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | For chat | OpenRouter API key; chat is disabled without it |
| `MASSIVE_API_KEY` | No | Massive (Polygon.io) key for real market data; omit to use the simulator |
| `LLM_MOCK` | No | Set `true` for deterministic mock LLM responses (testing) |

## Project Structure

```
finally/
├── frontend/    # Next.js static export (planned)
├── backend/     # FastAPI uv project — market data subsystem built
├── planning/    # Project documentation and agent contracts
├── test/        # Playwright E2E tests (planned)
├── db/          # SQLite volume mount (runtime)
└── scripts/     # Start/stop helpers (planned)
```

## License

See [LICENSE](LICENSE).
