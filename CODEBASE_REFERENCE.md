# MCP-GC Codebase Reference

> This is the canonical reference document for the Kalagato App Management System (MCP-GC).
> Keep this file updated as the codebase evolves. Used as the starting context for new Claude Code sessions.

---

## Project Overview

**Project:** Play Store MCP / Kalagato App Management System
**PyPI Name:** `play-store-mcp` (v0.3.0)
**Python Requirement:** ≥ 3.11
**Package Manager:** `uv` (with `uv.lock`)
**Build Backend:** Hatchling
**Repo:** https://github.com/lusky3/play-store-mcp

**One-line pitch:** A multi-MCP server system with an Autonomous PRAO (Perception-Reasoning-Action-Observation) Loop orchestrator for managing Android and iOS apps end-to-end — deployments, analytics, ASO, ad revenue, subscriptions, and life-cycle marketing.

---

## Goals (from PRD.md / roadmap.md)

The broader product vision is the **Autonomous App Management & Growth System** — a daily consolidated PRAO loop that autonomously manages metadata, bidding budgets, push notifications, and pricing parity across the portfolio:

- Fully autonomous execution loop (Google Antigravity SDK triggers)
- Consolidated Daily Fetch to compress LLM inference costs by 90%
- Phase 1: Organic Engine (App Store & Play Store metadata)
- Phase 2: Lifecycle Engine (FCM Push & RevenueCat events)
- Phase 3: Paid UA (Meta Ads optimization)
- Phase 4: Diagnostics & Pricing Parity (Firebase Crashlytics & Remote Config)
- Fallback tools: Journey Map Intelligence Platform (JMIP) for deep funnel overlays

**Starting App:** Voice Changer Android (~$60K MRR)

---

## Repository Structure

```
MCP-GC/
├── docs/
│   ├── AGENTS.md
│   ├── EVENTS.md
│   ├── PRD.md
│   ├── SECURITY.md
│   ├── Subscription-Value-Loop-Complete-Guide.md
│   ├── agent_plan.md
│   ├── analysis_engine.md
│   ├── emi_calculator_funnel_analysis.md
│   ├── findings.md
│   ├── plan.md
│   └── roadmap.md
├── src/
│   ├── play_store_mcp/        # Play Store MCP server
│   ├── analytics_mcp/         # GA4 Analytics MCP server
│   ├── admob_mcp/             # AdMob MCP server
│   ├── revenuecat_mcp/        # RevenueCat MCP server
│   ├── aso_keyword_mcp/       # ASO Keyword research MCP server
│   ├── funnel_engine/         # Core funnel analysis library (no MCP)
│   ├── funnel_engine_mcp/     # Funnel Engine MCP server (wraps funnel_engine)
│   └── app_manager/           # Coordinator agent + CLI + config
├── tests/
├── examples/
├── wiki/
├── CODEBASE_REFERENCE.md      # THIS FILE
├── pyproject.toml             # Project config, deps, scripts
├── .env                       # Secrets (gitignored)
├── .env.example               # Template for secrets
├── google-ads.yaml            # Google Ads credentials
├── kalagato-prod-*.json       # Google service account credentials
└── uv.lock                    # Locked dependencies
```

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│              AppManager Coordinator Agent                   │
│              (Google Antigravity SDK)                       │
│              src/app_manager/agents.py                      │
└──────┬─────────┬────────┬───────┬──────┬──────┬───────────┘
       │         │        │       │      │      │
  play_store  analytics  admob  revenuecat  aso  funnel_engine
    MCP         MCP       MCP     MCP      MCP     MCP
```

**Key Principle:** The JMIP UI reads pre-generated JSON written by Claude Code. It never calls MCPs directly — keeps UI fast and decoupled.

```
JMIP UI  →  reads /data/  ←  Claude Code  →  analytics-mcp + play-store-mcp
```

---

## MCP Servers

### 1. `play_store_mcp` (`src/play_store_mcp/`)

| File | Purpose |
|------|---------|
| `server.py` | FastMCP server, all tool definitions (~33.9KB) |
| `client.py` | Google Play Developer API client (~61KB) |
| `models.py` | Pydantic models for API responses (~10KB) |

**Entry point:** `python -m play_store_mcp`
**Key env vars:** `GOOGLE_APPLICATION_CREDENTIALS`

**Tools exposed:**
- `deploy_app`, `deploy_app_multilang`, `promote_release`, `get_releases`
- `halt_release`, `update_rollout`
- `get_app_details`, `get_reviews`, `reply_to_review`
- `list_subscriptions`, `get_subscription_status`, `list_voided_purchases`
- `get_vitals_overview`, `get_vitals_metrics`
- `list_in_app_products`, `get_in_app_product`
- `get_listing`, `update_listing`, `list_all_listings`
- `get_testers`, `update_testers`
- `get_order`, `get_expansion_file`
- `validate_package_name`, `validate_track`, `validate_listing_text`
- `batch_deploy`

---

### 2. `analytics_mcp` (`src/analytics_mcp/`)

| File | Purpose |
|------|---------|
| `server.py` | FastMCP server (~11KB) |
| `client.py` | GA4 Data API client (~22.8KB) |
| `models.py` | Pydantic models (~4.6KB) |

**Entry point:** `python -m analytics_mcp`
**Key env vars:** `GA4_PROPERTY_ID`, `GOOGLE_APPLICATION_CREDENTIALS`

**Tools exposed:**
- `run_report`, `get_realtime_report`, `get_active_users`
- `get_user_acquisition`, `get_retention`, `get_events`
- `get_revenue_report`, `get_user_demographics`
- `get_screen_views`, `get_crash_events`

---

### 3. `admob_mcp` (`src/admob_mcp/`)

**Entry point:** `python -m admob_mcp`
**Key env vars:** `ADMOB_ACCOUNT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`

**Tools exposed:**
- `list_accounts`, `get_account`, `list_ad_units`, `get_ad_unit`
- `list_apps`, `get_network_report`, `get_mediation_report`
- `get_earnings_summary`

---

### 4. `revenuecat_mcp` (`src/revenuecat_mcp/`)

**Entry point:** `python -m revenuecat_mcp`
**Key env vars:** `REVENUECAT_API_KEY`, `REVENUECAT_PROJECT_ID`

**Tools exposed:**
- `get_subscriber`, `list_offerings`, `get_offering`
- `get_overview_metrics`, `get_charts`, `get_transaction_history`
- `grant_entitlement`, `revoke_entitlement`, `refund_purchase`
- `list_products`

---

### 5. `aso_keyword_mcp` (`src/aso_keyword_mcp/`)

**Entry point:** `python -m aso_keyword_mcp`
**No API keys required** (uses public scraping via `google-play-scraper`)

**Tools exposed:**
- `search_keywords`, `get_keyword_difficulty`, `get_keyword_volume`
- `get_app_keywords`, `get_competitor_keywords`
- `track_keyword_ranking`, `get_category_top_apps`
- `analyze_listing_aso`, `generate_optimized_listing`

---

### 6. `funnel_engine` (`src/funnel_engine/`) — Library, Not MCP

| File | Purpose |
|------|---------|
| `analyzer.py` | Core `FunnelAnalyzer` class (~12.5KB) |
| `benchmarks.py` | Category-specific industry benchmarks (~11.8KB) |
| `models.py` | Pydantic models for analysis output (~6.2KB) |

**Key class:** `FunnelAnalyzer`
- `analyze_funnel(...)` → Full 10-step master funnel with leak detection
- `analyze_retention(...)` → D1/D7/D30 cohort analysis
- `compare_benchmarks(...)` → Percentile ranking vs category benchmarks

**Benchmark categories:** utilities, finance, games, health, productivity, entertainment, education, social, shopping, tools

**10-Step Master Funnel:**
```
Impressions → Store View → Install → D1 Active →
Onboarding Complete → Paywall View → Trial Start →
Paid Conversion → D7 Retained → D30 Retained
```

---

### 7. `funnel_engine_mcp` (`src/funnel_engine_mcp/`)

| File | Purpose |
|------|---------|
| `server.py` | FastMCP server wrapping `funnel_engine` (~24KB) |

**Entry point:** `python -m funnel_engine_mcp`
**Key env vars:** `GA4_PROPERTY_ID`, `GOOGLE_APPLICATION_CREDENTIALS`, `REVENUECAT_API_KEY`, `GCS_PLAY_CONSOLE_BUCKET`

**Tools exposed:**
- `run_funnel_analysis(package_name, app_category, date_range, ltv_override)` (uses real SQLite metrics if available)
- `get_funnel_health_score(package_name, app_category, date_range)`
- `get_retention_analysis(package_name, app_category, date_range)`
- `get_benchmark_comparison(package_name, app_category, date_range)`
- `ingest_play_store_reports(package_name, backfill)` (ingests GCS CSV storefront performance reports)
- `get_historical_listing_conversion(package_name, metric_type)` (queries historical SQLite storefront metrics)

**Data Sources Stitched:**
- GA4: active users, retention cohorts, events
- Play Store: app details, ratings, GCS storefront conversion metrics (via SQLite)
- AdMob: earnings summary (for LTV computation)
- RevenueCat: subscriber metrics (if subscriptions active)

**Smart LTV Computation:** If `ltv_override` is None and AdMob data present,
LTV = `(ad_revenue_30d / installs) * 3` (annualized conservative estimate)

**Ad-Monetized App Event Mapping:**
For apps without subscription events, GA4 events are mapped to funnel steps:
- `tutorial_complete` = core feature users (e.g., `emi_calculator_calculate_clicked`)
- `paywall_view` = ad impression users
- `trial_start` = ad click users
- `subscription_start` = revenue-generating users

---

### 8. `gcs_mcp` (`src/gcs_mcp/`)

**Entry point:** `python -m gcs_mcp`
**Key env vars:** `GOOGLE_APPLICATION_CREDENTIALS`, `GCS_PLAY_CONSOLE_BUCKET`

Provides a direct Model Context Protocol server client wrapper for Google Cloud Storage to search, list, and read raw Play Console stats CSV reports.

---

### 9. `journey_map_mcp` (`src/journey_map_mcp/`)

**Entry point:** `python -m journey_map_mcp`

Parses `docs/EVENTS.md` user flows and correlates GA4 analytics and Google Play Store stats to generate a self-contained `data/journey_map.html` dashboard showing detailed funnel stage completions, conversion rates, and revenue impacts.

---

### 10. `mcp_gc_shared` (`src/mcp_gc_shared/`)

A shared core utility package containing common environment loaders (`load_dotenv`) and logger configurations (`configure_logging`) to unify stderr logging across all MCP servers.

---

### 11. `data/` Directory (Local Storage)

- `store_performance.db` — Local SQLite database populated by `Storefront Analyst` containing daily visitor, install, and conversion statistics broken down by country, traffic source, and search query.
- `storefront_conversion_history.json` — Static daily aggregated storefront performance metrics JSON exported after ingestion to decouple JMIP from real-time DB calls.

---

## App Manager (Coordinator Layer) — `src/app_manager/`

| File | Purpose |
|------|---------|
| `config.py` | `AppManagerConfig` dataclass, env var loading |
| `agents.py` | Agent factory functions using Google Antigravity SDK |
| `personas.py` | System prompt strings for each specialist agent |
| `tools.py` | `get_system_status` tool |
| `cli.py` | `app-manager` CLI entry point |

### Config (`AppManagerConfig`)

Loaded via `AppManagerConfig.from_env()`. Reads from `.env` file or env vars:

| Env Var | Purpose |
|---------|---------|
| `APP_PACKAGE_NAME` | Default target app package name |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON |
| `REVENUECAT_API_KEY` | RevenueCat secret key |
| `REVENUECAT_PROJECT_ID` | RevenueCat project ID |
| `GA4_PROPERTY_ID` | GA4 property ID |
| `ADMOB_ACCOUNT_ID` | AdMob publisher ID |
| `GOOGLE_ADS_CONFIGURATION_FILE_PATH` | Path to `google-ads.yaml` |
| `GEMINI_API_KEY` | Gemini API key for Antigravity |

### Agents & Autonomous Loop (`run_autonomous_loop.py`)

Each agent is a `LocalAgentConfig` from the Google Antigravity SDK:

| Factory Function | Persona | MCP Servers |
|-----------------|---------|-------------|
| `create_coordinator_agent()` | COORDINATOR_PERSONA | All servers |
| `create_play_store_agent()` | PLAY_STORE_PERSONA | play_store, app_store_connect |
| `create_analytics_agent()` | ANALYTICS_PERSONA | analytics, firebase_ai |
| `create_admob_agent()` | ADMOB_PERSONA | admob |
| `create_revenuecat_agent()` | REVENUECAT_PERSONA | revenuecat, fcm_push |
| `create_aso_agent()` | ASO_PERSONA | aso_keywords, auto_aso |
| `create_paid_ua_agent()` | PAID_UA_PERSONA | facebook_marketing_api |
| `create_funnel_engine_agent()` | FUNNEL_ENGINE_PERSONA | funnel_engine |

#### Safety & Policy
The system leverages Antigravity SDK's declarative policy system to prevent destructive autonomous actions:
- `policy.ask_user("run_command", when=lambda args: "deploy" in args)` — Requires Slack interactive button approval before pushing code or releasing app bundles.
- Hard caps on budget updates and metadata character limits.

---

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `mcp` | ≥1.26.0 | Model Context Protocol framework |
| `google-api-python-client` | ≥2.180.0 | Google APIs |
| `google-auth` | ≥2.40.0 | Google auth |
| `google-analytics-data` | ≥0.18.0 | GA4 Data API (optional: `analytics` extra) |
| `google-play-scraper` | ≥1.2.0 | ASO scraping (optional: `aso` extra) |
| `google-antigravity` | ≥0.1.0 | AI agent orchestration (optional: `orchestration` extra) |
| `pydantic` | ≥2.10.0 | Data validation |
| `structlog` | ≥25.0.0 | Structured logging |
| `httpx` | ≥0.28.0 | Async HTTP |

**Install all extras:**
```bash
uv pip install -e ".[all]"
```

---

## CLI Entry Points

```bash
play-store-mcp       # Play Store MCP server
revenuecat-mcp       # RevenueCat MCP server
analytics-mcp        # Analytics MCP server
admob-mcp            # AdMob MCP server
aso-keyword-mcp      # ASO Keyword MCP server
funnel-engine-mcp    # Funnel Engine MCP server
app-manager          # Coordinator agent CLI
```

---

## JMIP UI Plan (Journey Map Intelligence Platform)

> Defined in `docs/plan.md`. The UI is a separate frontend to be built.

**Data flow:**
```
JMIP UI → reads /data/ ← Claude Code → analytics-mcp + play-store-mcp
```

### Features (by phase)

| Phase | Feature | Status |
|-------|---------|--------|
| 1 — UI Shell | App selector sidebar | ❌ Not started |
| 1 — UI Shell | Journey map canvas | ❌ Not started |
| 1 — UI Shell | Emotion arc visualisation | ❌ Not started |
| 1 — UI Shell | Branch expand/collapse | ❌ Not started |
| 1 — UI Shell | Spreadsheet importer (F5) | ❌ Not started |
| 1 — UI Shell | Static detail panel | ❌ Not started |
| 2 — EVENTS.md | docs/EVENTS.md parser + editor | ❌ Not started |
| 2 — EVENTS.md | Code reference display | ❌ Not started |
| 2 — EVENTS.md | Branch diagram renderer | ❌ Not started |
| 3 — GA4 | Live data toggle + date range | ❌ Not started |
| 3 — GA4 | Event count overlay | ❌ Not started |
| 3 — GA4 | Auto-computed emotion scores | ❌ Not started |
| 4 — Play Store | Review excerpts in detail panel | ❌ Not started |
| 4 — Play Store | Vitals overlay | ❌ Not started |
| 5 — Backlog | Priority scoring formula | ❌ Not started |
| 5 — Backlog | Opportunity backlog view + export | ❌ Not started |
| 5 — Backlog | Claude Code prompt generator | ❌ Not started |

### Journey Map Data Structure

```
App
└── Flows (Onboarding, Connect, Paywall, Retention)
    └── Stages (sequential phases)
        ├── Events (GA4 events)
        ├── Branches (happy path, skip, error, re-entry, dead end)
        ├── Signals (completion rates, retention, review themes, crash rate)
        └── Opportunities (code-level fixes, effort S/M/L, impact score)
```

### Emotion Scoring Rules

| Signal | Effect |
|--------|--------|
| Branch completion > 70% | +2 |
| Branch completion 40–70% | +1 |
| Branch completion < 40% | −1 |
| Crash rate > 1% at this stage | −2 |
| D1 retention > 40% | +1 to Onboard |
| Dead end rate > 20% | −2 |
| Review sentiment majority positive | +1 |

### Opportunity Priority Formula

```
Priority = (branch_trigger_rate × drop_off_rate × 10) / effort_score
(effort: S=1, M=2, L=4)
```

---

## Existing Non-JMIP Docs

| File | Purpose |
|------|---------|
| `docs/analysis_engine.md` | Detailed PRD for the funnel analysis engine (broader SaaS vision) |
| `docs/emi_calculator_funnel_analysis.md` | Funnel analysis for the EMI Calculator app |
| `docs/FEATURE_SUMMARY.md` | Summary of features shipped |
| `README.md` | Public-facing README |

---

## Known Credentials / Sensitive Files

> These are gitignored but present locally:

| File | Purpose |
|------|---------|
| `.env` | All secrets (GA4 property ID, API keys, etc.) |
| `kalagato-prod-*.json` | Google service account JSON |
| `credentials.json` | OAuth2 credentials |
| `token.json` | OAuth2 refresh token |
| `google-ads.yaml` | Google Ads config |
| `.env.admob` | AdMob-specific env vars |

---

## Development Commands

```bash
# Install with all extras
uv pip install -e ".[all]"

# Run tests
uv run pytest

# Lint
uv run ruff check src/
uv run ruff format src/

# Type check
uv run mypy src/play_store_mcp/

# Run individual MCP servers for testing
uv run python -m play_store_mcp
uv run python -m analytics_mcp
uv run python -m funnel_engine_mcp

# Run coordinator agent CLI
uv run app-manager
```

---

## Next Steps (as of June 2026)

1. **JMIP Phase 1 — UI Shell:** Build the journey map canvas frontend (HTML/CSS/JS)
2. **Voice Changer EVENTS.md:** Create `docs/EVENTS.md` for the flagship app
3. **Data directory:** Set up `/data/` directory structure for pre-generated JSON
4. **Import pipeline:** Build CSV/Sheets import → internal JSON schema converter
5. **Apps.json:** Create `apps.json` with all Kalagato apps (package names, GA4 property IDs)
6. **GCS Performance Ingestion DB Layer:** Completed. Implemented the `storefront_analyst` subagent and SQLite database layer (`data/store_performance.db`) to ingest storefront CSVs and expose query APIs.
