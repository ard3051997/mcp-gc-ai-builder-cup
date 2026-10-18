# Repository Guidelines

## Project Structure & Module Organization

Python code lives under `src/`. Each `src/*_mcp/` package is a runnable MCP server; use the console commands declared in `pyproject.toml`. Shared helpers are in `src/mcp_gc_shared/`. `src/app_manager/` provides orchestration; `src/api_server/` and `src/run_autonomous_loop.py` are source-tree applications.

The React/Vite application and colocated tests are under `frontend/src/`; Python tests are in `tests/`. Deployment files live in `deploy/` and `compose.yaml`, and tooling in `scripts/`. `HDC-Pro/` is a separate Gradle Android project. Treat `config/`, `.env`, and local data files as credential-bearing.

## Build, Test, and Development Commands

Install Python 3.11+ dependencies with `uv sync --extra dev`; use `uv sync --all-extras` when working on optional integrations.

```bash
uv run ruff check src/ tests/            # lint Python
uv run ruff format --check src/ tests/   # verify formatting
uv run mypy src/                         # type-check configured packages
uv run pytest tests/ --ignore=tests/test_integration.py -v --cov=src
uv build                                 # build wheel and source distribution
npm --prefix frontend ci
npm --prefix frontend run test
npm --prefix frontend run lint
npm --prefix frontend run build
```

Run the API with `uv run uvicorn api_server.main:app --reload`, the UI with `npm --prefix frontend run dev`, and orchestration with `uv run app-manager`.

## Coding Style & Naming Conventions

Ruff uses four-space indentation, double quotes, and a 100-character line limit. Use `snake_case` for Python modules/functions, `PascalCase` for classes, and annotate new functions. Apply formatting with `uv run ruff format src/ tests/`. ESLint checks TypeScript/React; use `PascalCase` for components, `useCamelCase` for hooks, and `camelCase` for values.

For stdio MCP servers, reserve stdout for JSON-RPC and send diagnostics to stderr. MCP implementations differ, so inspect the target package before copying patterns.

## Testing Guidelines

Use pytest files named `test_*.py`, shared fixtures from `tests/conftest.py`, and mock external APIs. Frontend tests use Vitest and Testing Library with `*.test.ts` or `*.test.tsx` names. Add regression tests for fixes and maintain or improve coverage.

`tests/test_integration.py` can make live, read-only Google Play calls when credentials are exported. Exclude it for normal CI-equivalent runs; never place real credentials in fixtures or logs.

## Commit & Pull Request Guidelines

Create `feature/...` branches instead of committing to `main`. Prefer descriptive Conventional Commit-style subjects such as `feat: add journey filtering`, `fix: handle API timeout`, or `docs: update setup`. Keep commits focused.

Pull requests should explain the motivation, list verification commands, link issues, and include screenshots for UI changes. Ensure checks pass and update documentation when commands, configuration, or MCP tools change.


<claude-mem-context>
# Memory Context

# [MCP-GC] recent context, 2026-07-22 6:52pm GMT+5:30

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 19 obs (3,183t read) | 298,456t work | 99% savings

### Jun 9, 2026
683 12:30p ✅ Contributor Guide for Repository
### Jun 10, 2026
705 3:53p 🔵 ASO Subagent Development Status
706 3:57p 🔵 ASO Subagent Development Status
### Jul 20, 2026
1258 1:54a ✅ Initial Greeting and Session Start
1259 1:57a ✅ Initial greeting received
1260 1:59a ✅ Initial greeting acknowledged
1261 2:00a ✅ Initial greeting exchange
S136 Initial User Greeting (Jul 20 at 2:00 AM)
1262 " ✅ Initial greeting interaction
1263 " ✅ Session Cleared
### Jul 22, 2026
1477 6:45p ✅ Contributor Guide Generation
1478 6:46p 🔵 Existing Contributor Guide Check
1486 6:49p ✅ Contributor Guide Content Populated
1485 " ✅ Contributor Guide Generation
1487 6:50p ✅ Contributor Guide Refinement
1488 " ✅ Contributor Guide Details Added
1492 6:51p ✅ Contributor Guide Deployed
1494 " ✅ Contributor Guide Finalized
1496 " ✅ Contributor Guide Refined
1497 " ✅ Contributor Guide Status Verified

Access 298k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>