# MCP-GC: multi-agent copilot for mobile app teams

AI Builder Cup submission. **Live prototype:** https://mcp-gc-105392482006.asia-south1.run.app

App teams juggle Google Play Console, RevenueCat, GA4, AdMob and ASO tools to decide what to change next.
MCP-GC puts a Gemini-powered coordinator agent in front of all of them. It answers questions in plain language,
turns funnel data into experiment proposals, and runs approved changes through a human approval gate.

## How it uses Google Cloud
- **Gemini on Vertex AI**: every agent runs on `gemini-2.5-flash` through the Google Antigravity SDK
  (`vertex=True`, project and location from env, service-account identity, no API key).
- **Multi-agent system (Antigravity SDK)**: a coordinator routes questions to specialist sub-agents
  (Play Store, RevenueCat, Analytics, AdMob, ASO, funnel engine, ...), each with only its own MCP server.
- **Firestore (Firebase's database)**: experiments and the audit log are written to Firestore so they survive
  container restarts; the dashboard reads them back from there (`src/funnel_engine/firestore_store.py`).
- **Cloud Run**: one container serves the FastAPI backend and the built React dashboard (`Dockerfile.cloudrun`).
- **Cloud Build + Artifact Registry** build and store the image.

## Try it
- Dashboard: open the live link. The Experiments and Action Log pages show sample data seeded into Firestore
  (`scripts/seed_demo_firestore.py`, tagged `demo-seed`).
- Agent chat: `POST /api/apps/com.finance.loan.emicalculator/chat` with `{"question": "..."}`.
- The public demo is read-only apart from chat, and ships with no real credentials.

## Run / deploy
```bash
uv sync --all-extras
FIRESTORE_PROJECT=<project> VERTEX_PROJECT=<project> uv run uvicorn api_server.main:app --app-dir src
gcloud builds submit --config cloudbuild.yaml .   # then: gcloud run deploy mcp-gc --image ...
```

## Layout
`src/*_mcp/` MCP servers, `src/app_manager/` agents and experiment engine, `src/funnel_engine/` funnel analysis and
storage, `src/api_server/` REST API, `frontend/` React dashboard. This is the Antigravity multi-agent version of
the project.
