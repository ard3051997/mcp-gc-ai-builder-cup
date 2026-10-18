# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP-GC is an AI-powered mobile app portfolio management system. It has three layers:
1. **MCP servers** (`src/*_mcp/`) — expose Google Play, RevenueCat, GA4, AdMob, ASO, FCM, GCS, and Apple App Store APIs as MCP tools
2. **Orchestration layer** (`src/app_manager/`) — a Google Antigravity SDK coordinator that routes queries to domain-specialist sub-agents
3. **Frontend** (`frontend/`) — React/Vite/Tailwind dashboard backed by a FastAPI server (`src/api_server/`)

## Commands

All Python commands use `uv run`.

```bash
# Install all dependencies
uv sync --all-extras

# Run tests
uv run pytest
uv run pytest tests/test_play_store_server.py   # single file
uv run pytest -k "test_get_app_reviews"          # single test
uv run pytest --cov=src/ --cov-report=html

# Lint & format
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run mypy src/play_store_mcp/   # mypy is only enforced on play_store_mcp

# Run the FastAPI backend (serves the React frontend at http://localhost:8000)
uv run uvicorn src.api_server.main:app --reload

# Run the React frontend dev server (http://localhost:5173)
cd frontend && npm run dev

# Run the interactive orchestration CLI
uv run app-manager

# Run individual MCP servers (stdio transport, for MCP client integration)
uv run play-store-mcp | uv run revenuecat-mcp | uv run analytics-mcp
uv run admob-mcp | uv run aso-keyword-mcp | uv run funnel-engine-mcp
uv run gcs-mcp | uv run journey-map-mcp | uv run fcm-push-mcp | uv run app-store-mcp

# Run the autonomous scheduling loop
uv run python src/run_autonomous_loop.py
```

## Architecture

### MCP Server Pattern

Every server under `src/*_mcp/` follows the same structure:

```
src/<name>_mcp/
├── __init__.py       # re-exports main()
├── __main__.py       # entry point
├── client.py         # API client — all outbound calls wrapped with @retry_on_transient
├── models.py         # Pydantic v2 models
└── server.py         # FastMCP server — tools registered via @mcp.tool()
```

Critical conventions:
- The `lifespan()` async context manager initializes the API client and stores it in `ctx.request_context.lifespan_context`. Tool functions always retrieve the client via `get_client_from_context(ctx)` — never instantiate clients inside tool functions.
- `structlog` goes to **stderr only**; stdout is the MCP JSON-RPC channel.
- Retry logic lives in `src/mcp_gc_shared/retry.py` (`retry_on_transient` decorator). Import from there rather than re-implementing.
- `.env` is auto-loaded by the `mcp_gc_shared.env.load_dotenv()` helper, which walks up 5 parent directories.

### All MCP Servers

| Server | Entry Point | Data Source |
|--------|-------------|-------------|
| `play_store_mcp` | `play-store-mcp` | Google Play Developer API |
| `revenuecat_mcp` | `revenuecat-mcp` | RevenueCat REST v2 |
| `analytics_mcp` | `analytics-mcp` | Google Analytics 4 |
| `admob_mcp` | `admob-mcp` | AdMob API |
| `aso_keyword_mcp` | `aso-keyword-mcp` | Play Store scraping |
| `funnel_engine_mcp` | `funnel-engine-mcp` | Cross-source funnel DB |
| `gcs_mcp` | `gcs-mcp` | GCS Play Console exports |
| `journey_map_mcp` | `journey-map-mcp` | HTML journey map generator |
| `fcm_push_mcp` | `fcm-push-mcp` | Firebase Cloud Messaging |
| `app_store_mcp` | `app-store-mcp` | Apple App Store Connect |

### Orchestration Layer (`src/app_manager/`)

The coordinator agent (built with Google Antigravity SDK) spawns domain specialists as sub-agents. Each specialist gets only its own MCP server.

- **`config.py`** — `AppManagerConfig` dataclass; reads env vars, detects which services are configured
- **`credential_store.py`** — resolves per-app credentials from `config/apps.json`, falls back to `.env`
- **`agents.py`** — `create_coordinator_agent()` builds `MCPServerConfig` objects only for enabled services
- **`specialists.py`** — `make_specialist_tools()` creates callable tool functions that each spawn a focused sub-agent; the coordinator calls these as regular Python tools
- **`personas.py`** — system prompts for coordinator + all domain specialists
- **`experiment_engine.py`** — full experiment lifecycle (PROPOSED → ACTIVE → CONCLUDED); runs Welch's t-test for statistical significance; types: ASO metadata, creatives, paywall, ad unit, push campaign, UA budget, remote config
- **`rollback_manager.py`** — captures pre-experiment snapshots via `PlayStoreClient`/`RevenueCatClient`; enables automated reverts
- **`safety_policies.py`** — `telegram_interactive_approval_handler` blocks mutating tool calls until approved/rejected via Telegram inline keyboard; fails closed on timeout
- **`cli.py`** — interactive REPL with `/status`, `/report`, `/revenue`, `/actions`, `/help`, `/quit`

### FastAPI Backend (`src/api_server/`)

Thin REST wrapper consumed by the React frontend. Routers map to frontend API calls 1:1:

| Router | Prefix | Purpose |
|--------|--------|---------|
| `portfolio.py` | `/api/portfolio` | Portfolio-level metrics and summary |
| `apps.py` | `/api/apps` | Per-app funnel, revenue, storefront, keywords, reviews |
| `experiments.py` | `/api/experiments` | Experiment CRUD and evaluation |
| `actions.py` | `/api/actions` | Action log |
| `system.py` | `/api/system` | Health, config status |
| `webhooks.py` | `/api/webhooks` | RevenueCat webhook → FCM re-engagement pipeline |

The webhook handler resolves per-app credentials from `credential_store`, selects the `ask_fcm_push` specialist tool, and logs all outcomes to the funnel engine SQLite DB via `funnel_engine.db.log_db_action`.

### Frontend (`frontend/`)

React 19 + Vite + Tailwind CSS 4. Pages are under `frontend/src/pages/`:
- `PortfolioCommandCenter.tsx` — main dashboard
- `ASOWorkspace.tsx`, `ExperimentCenter.tsx`, `FunnelDiagnostics.tsx`, `JourneyMap.tsx`, `RevenueMonetization.tsx`, `ActionLog.tsx`, `Settings.tsx`

All backend calls go through `frontend/src/api/index.ts`. The API base URL defaults to `http://localhost:8000/api` and is overridden via `VITE_API_BASE_URL`.

### Multi-App Configuration

`config/apps.json` stores per-app credentials. Each entry has `package_name`, `display_name`, `app_category`, and optional fields for each service (`revenuecat_api_key`, `google_credentials_path`, `admob_account_id`, `gcs_play_console_bucket`, `google_ads_customer_id`). A `null` field means "fall back to the global `.env` value." iOS apps use App Store bundle ID conventions as `package_name`.

### Key Environment Variables

```
GEMINI_API_KEY              # Required for Antigravity SDK orchestration
GOOGLE_APPLICATION_CREDENTIALS  # Service account JSON path (Play, Analytics, AdMob)
REVENUECAT_API_KEY + REVENUECAT_PROJECT_ID
GA4_PROPERTY_ID
ADMOB_ACCOUNT_ID
GCS_PLAY_CONSOLE_BUCKET
TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID  # Required for safety policy approval gate
```

### Testing

All Google API calls are mocked with `unittest.mock` — no real network calls. Test files follow `test_<server_name>_server.py` / `test_<server_name>_client.py`. Shared fixtures are in `tests/conftest.py`. `asyncio_mode = "auto"` is set in `pyproject.toml`, so async test functions work without explicit decorators.

## Git Flow

Always create a feature branch (`feature/…`) or bugfix branch (`bugfix/…`). Do not commit directly to `main`.

