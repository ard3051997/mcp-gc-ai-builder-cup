# PRD — Kalagato Journey Map Intelligence Platform (JMIP)

## Overview

Kalagato operates 15+ Android and iOS apps. User journey maps currently live in spreadsheets — disconnected from live data, hard to read, impossible to share with the team. This PRD defines the **Journey Map Intelligence Platform (JMIP)**: a purpose-built tool that makes journey maps readable, interactive, and connected to real behavioral signals.

> **One-line pitch:** A beautiful interface that turns your spreadsheet journey maps + GA4 data + Play Store signals + codebase events into living, actionable maps your whole team can use.
> 

---

## Problem Statement

Right now, journey maps at Kalagato:

- Live in spreadsheets that are hard to navigate and even harder to share with non-technical team members
- Are disconnected from live GA4 data — you can't see drop-off rates alongside the flow
- Have no link to the codebase — friction points are identified but root causes are unknown
- Cannot show branching paths — only the happy path is documented
- Require Abhishek to translate for the team before anyone can act on them

The result: fixes are reactive. Problems get caught only when revenue drops or reviews spike.

---

## Goals

- Beautiful, interactive UI for reading and navigating journey maps — optimised for non-technical readers
- One app processed at a time — full depth over breadth
- Import from existing Excel/Sheets journey maps — zero re-entry cost
- Connect GA4 as a live signal overlay on manually-defined flows
- Connect Play Store reviews and vitals as a qualitative signal layer
- Link each stage and branch to the exact file + line in the codebase via `EVENTS.md`
- Generate branch-aware funnel analysis — not just happy-path completion rates
- Output sprint-ready opportunities with code-level specificity

## Non-Goals

- Not a real-time dashboard (GA4 queried on demand, not streaming)
- Not a persona segmentation tool (no PII; archetypes are behavioral hypotheses)
- Not a cross-app portfolio view in v1 — one app at a time
- Not a replacement for GA4 Explorations — complements it and links out
- Not a deployment or release management tool

---

## Users

| User | Role | Primary Need |
| --- | --- | --- |
| Abhishek | Founder / CPO | Weekly triage — which app, flow, and branch is bleeding |
| Raghav | Developer | Specific code-level fix with file + line reference |
| Sumit | PM | Sprint-ready opportunity backlog, effort-ranked |
| Mehak | Marketing | Which acquisition channels lead to high-friction onboarding |

---

## System Architecture

The UI reads pre-generated JSON written by Claude Code. It never calls MCPs directly — this keeps the UI fast and decoupled from data collection.

```
JMIP UI  →  reads /data/  ←  Claude Code  →  analytics-mcp + play-store-mcp
```

**Data layers:**

| Layer | Source | What it provides |
| --- | --- | --- |
| Flow definition | EVENTS.md (manual, per app) | All branches, state transitions, blind spots |
| Behavioral signals | GA4 Data API via analytics-mcp | Event counts, D1/D7/D30 retention, acquisition channels |
| Qualitative signals | play-store-mcp | Review themes by star rating, crash rate, ANR rate |
| Code context | EVENTS.md  • codebase scan | File + line per event, branch conditions, re-entry points |
| Deep analysis | GA4 Explorations (manual) / BigQuery (on-demand) | Per-user path sequences, validated branch rates |

**Import path for existing spreadsheets:**

Existing Excel/Sheets journey maps → CSV export → one-click import in JMIP → mapped to internal JSON schema. Column mapping UI handles non-standard spreadsheet layouts.

---

## Core Concepts

### Journey Map Structure

Each app has one journey map containing:

- **Flows** — major user journeys (Onboarding, Connect, Paywall, Retention)
- **Stages** — sequential phases within a flow
- **Branches** — alternate paths at decision, error, or permission points
- **Events** — GA4 events marking transitions between stages and branches
- **Signals** — quantitative (completion rate, retention) and qualitative (review themes, crash rate)
- **Opportunities** — specific, code-level fixes ranked by impact × effort

### Branch Types

| Type | Description | Example |
| --- | --- | --- |
| Happy path | All steps completed | onboarding_started → ... → onboarding_completed |
| Skip branch | User skips optional steps | step_2_skipped → completed (partial) |
| Error branch | System or permission failure | permission_denied → rationale_shown → recover or churn |
| Re-entry branch | Returning user who didn't complete | app_opened → onboarding_resume_shown |
| Dead end | No subsequent event within session | onboarding_dismissed → silent churn |

### Emotion Scoring

Scores (1–5) are derived from behavioral signals, not assumed:

| Signal | Effect |
| --- | --- |
| Branch completion rate > 70% | +2 |
| Branch completion rate 40–70% | +1 |
| Branch completion rate < 40% | −1 |
| Crash rate > 1% at this stage | −2 |
| D1 retention > 40% | +1 to Onboard stage |
| Dead end rate > 20% | −2 |
| Review sentiment majority positive | +1 |

Weighted emotion score = average across all branch scores, weighted by branch trigger rate.

---

## Feature Specifications

### F1 — App Selector + Flow Navigator

Left sidebar listing all configured apps. Selecting an app loads its flows. Selecting a flow opens the journey map canvas.

**Details:**

- App list loaded from `apps.json` (package name, GA4 property ID, display name)
- Flows loaded from the app's `EVENTS.md`
- Red badge on apps with any stage at emotion score ≤ 2
- Last viewed app + flow remembered across sessions

---

### F2 — Journey Map Canvas

The main view. Horizontal stage columns, rows for each data layer, branches expandable per stage.

**Layout rows:**

1. Stage header (name + sub-label)
2. User actions
3. Touchpoints
4. Emotion arc (SVG curve, colour-coded)
5. Branches (collapsed by default, expand to show per-branch rates)
6. Pain points
7. Opportunities

**Behaviour:**

- Critical stages (emotion ≤ 2) show a red left border
- Branches collapse/expand on click
- Each cell opens the Detail Panel (F4) on click
- Readable by non-technical team members — no jargon in default view, jargon in expandable detail

---

### F3 — Live Signal Overlay

Toggle to overlay GA4 data on the map. When ON, each stage shows real event counts and completion rates.

**Behaviour:**

- Toggle in top bar: **Live data ON / OFF**
- Date range selector: 7d / 30d / 90d
- Completion rate shown as % below each stage column header
- Branch trigger rates shown as small pills next to each branch label
- Inline tooltip: *"Rates are aggregate ratios, not per-user funnels. Use GA4 Explorations for validated path analysis."*
- Stale data indicator if last fetch > 24 hours ago

**GA4 queries executed per flow:**

1. Event counts for all events in flow
2. D1 / D7 / D30 retention
3. Acquisition channel breakdown

---

### F4 — Stage / Branch Detail Panel

Right-side slide-in panel on any cell or branch click. Full context for non-technical and technical readers.

**Sections:**

1. Signal summary — emotion score, completion rate, branch trigger rate
2. Events — GA4 event list with counts and trend sparkline
3. Code references — file, line, trigger condition, active A/B tests (from EVENTS.md)
4. Review excerpts — 3–5 representative 1–3 star reviews mentioning this stage
5. Vitals — crash rate / ANR rate if relevant
6. Opportunities — ranked fixes with effort (S/M/L), expected impact, code location
7. GA4 Explorations link — deep link to funnel explorer pre-filtered for this flow
8. BigQuery query — collapsed SQL block for per-user path analysis (generated, not executed)

---

### F5 — Spreadsheet Importer

One-click import from the existing Excel/Sheets journey maps.

**Behaviour:**

- Upload CSV or paste Google Sheets URL
- Column mapping UI: drag spreadsheet columns to JMIP fields (Stage, Action, Touchpoint, Pain Point, Opportunity)
- Auto-detects common column names (case-insensitive match)
- Preview before import
- Import creates the base journey map — live signals and code references added incrementally
- Re-import merges changes without overwriting manually added signal data

---

### F6 — EVENTS.md Editor

In-app editor for maintaining the event flow graph per app. Split view: editor left, rendered branch diagram right.

**Behaviour:**

- "Generate from code" — paste a code file, Claude generates event entries in the correct format
- Validation warning if an event in EVENTS.md has no GA4 data match (naming mismatch or uninstrumented)
- Diff view on update — shows what changed vs previous version
- Blind spot highlighting — stages with no instrumented events shown in amber
- Export as `.md` file

---

### F7 — Opportunity Backlog

Aggregated list of all opportunities across all stages for the current app, ranked by priority score.

**Priority formula:**

```
Priority = (branch_trigger_rate × drop_off_rate × 10) / effort_score
(effort: S=1, M=2, L=4)
```

**Columns:** Opportunity · Flow · Stage · Branch · Trigger rate · Drop-off · Effort · Priority · Code location

**Actions:**

- Sort and filter by any column
- "Export to Notion" — creates a task page per opportunity
- "Copy as sprint ticket" — formats as a Linear/Jira ticket template

---

### F8 — Claude Code Prompt Generator

Generates the ready-to-run Claude Code prompt for the selected app, pre-filled with package name, GA4 property ID, flow list, and scoring rules.

Output is a versioned `.md` file the user drops into their Claude Code session. The file is regenerated automatically when `EVENTS.md` changes.

---

## Build Phases

### Phase 1 — UI Shell (Week 1–2)

*Immediately useful. No MCP, no codebase needed.*

- App selector sidebar
- Journey map canvas with manual data entry
- Emotion arc visualisation
- Branch expand/collapse
- **Spreadsheet importer (F5)** — this is the unlock for existing maps
- Static detail panel

**Done when:** All existing spreadsheet journey maps are readable in the UI.

---

### Phase 2 — EVENTS.md Layer (Week 3)

- EVENTS.md parser and editor
- Code reference display in detail panel
- Branch diagram rendered from EVENTS.md
- Generator modal (paste code → generate entries)
- Blind spot warnings

**Done when:** Voice Changer Android fully instrumented in EVENTS.md with all branches mapped.

---

### Phase 3 — GA4 Signal Layer (Week 4–5)

- analytics-mcp integration
- Live data toggle and date range selector
- Event count overlay on stages
- Branch completion rate pills
- D1/D7/D30 retention display
- Emotion scores auto-computed from signals

**Done when:** Live GA4 data visible on Voice Changer map with auto-scored emotion arc.

---

### Phase 4 — Play Store Layer (Week 5–6)

- play-store-mcp integration
- Review excerpts in detail panel
- Vitals overlay (crash/ANR rates)
- Review sentiment → pain point extraction via Claude

**Done when:** Pain points in Voice Changer map backed by real review data, not assumptions.

---

### Phase 5 — Opportunity Backlog + Prompt Generator (Week 7)

- Priority scoring
- Opportunity backlog view with export
- Claude Code prompt generator (F8)
- Sprint ticket formatter

**Done when:** Raghav/Sumit can take the backlog directly into a sprint without translation from Abhishek.

---

## Known Limitations

| Limitation | Impact | Mitigation |
| --- | --- | --- |
| GA4 Data API gives aggregate counts, not per-user paths | Branch completion rates are approximations | Label estimates clearly; link to GA4 Explorations for validation |
| Reviews represent ~1–2% of users and skew extreme | Pain points may not reflect the median user | Triangulate with vitals and analytics; weight reviews lower |
| EVENTS.md requires manual maintenance | Goes stale after codebase changes | Flag in UI if EVENTS.md > 90 days old; update trigger = any PR touching analytics calls |
| Personas are behavioral archetypes, not validated segments | Persona labels are hypotheses | Label as "Archetype" in UI; never use for targeting without PII validation |
| play-store-mcp is community-maintained (0 stars) | May break on Play API changes | Pin to a specific version; fallback to manual review CSV import |
| GA4 Explorations not API-accessible | Deep path analysis requires manual work | BigQuery SQL templates auto-generated in detail panel for on-demand runs |

---

## Success Metrics

| Metric | Target |
| --- | --- |
| Time to identify top friction point per app | < 5 minutes |
| Journey maps maintained for apps > $5K MRR | 100% |
| EVENTS.md coverage of GA4 events | > 80% mapped to code location |
| Opportunities actioned per sprint | ≥ 1 per active app |
| Emotion score improvement after fix | +0.5 average within 2 sprints |

---

## Starting App

**Voice Changer Android** — flagship app at ~$60K MRR. Highest ROI for getting the system right first. Phase 1 target is importing the existing spreadsheet map. Phase 2 target is completing the EVENTS.md with all onboarding and core-action branches.

> Spreadsheet column mapping for import will need to be confirmed once the existing map is shared. Tag Abhishek to provide the file before Phase 1 kickoff.
>