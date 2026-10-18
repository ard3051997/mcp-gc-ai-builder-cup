# Data Flow Diagram (DFD) & System Architecture

This document describes the high-level architecture and data flows of the **Kalagato App Management & Growth Agent** built using the Google Antigravity SDK.

---

## 1. Complete System Architecture

The following diagram illustrates how the Coordinator Agent, Specialist Sub-Agents, MCP Servers, and the Human-in-the-Loop (HITL) Telegram Approval policy interact.

```mermaid
graph TD
    %% External Trigger / Interface
    User[User / CLI Interface] <-->|Interactive REPL / Commands| Coord[Coordinator Router Agent]
    Cron[Antigravity SDK Cron / Trigger] -->|Scheduled Job Trigger| Coord
    
    %% Coordinator Delegation
    subgraph Brain [Antigravity Orchestration Layer]
        Coord
        PolicyEngine[Safety Policy Hook Engine]
    end

    %% Specialist Delegation (Multi-Agent Mode)
    Coord -->|Delegates Queries via Tools| SpecialistPS[Play Store Sub-Agent]
    Coord -->|Delegates Queries via Tools| SpecialistRC[RevenueCat Sub-Agent]
    Coord -->|Delegates Queries via Tools| SpecialistGA[GA4 Analytics Sub-Agent]
    Coord -->|Delegates Queries via Tools| SpecialistAM[AdMob Sub-Agent]
    Coord -->|Delegates Queries via Tools| SpecialistASO[ASO Keywords Sub-Agent]
    Coord -->|Delegates Queries via Tools| SpecialistFE[Funnel Engine Sub-Agent]
    Coord -->|Delegates Queries via Tools| SpecialistGCS[GCS Sub-Agent]

    %% MCP Integration Layer
    subgraph MCP [Model Context Protocol Servers]
        SpecialistPS <-->|MCP Protocol stdio| PSMCP[play_store_mcp]
        SpecialistRC <-->|MCP Protocol stdio| RCMCP[revenuecat_mcp]
        SpecialistGA <-->|MCP Protocol stdio| GAMCP[analytics_mcp]
        SpecialistAM <-->|MCP Protocol stdio| AMMCP[admob_mcp]
        SpecialistASO <-->|MCP Protocol stdio| ASOMCP[aso_keyword_mcp]
        SpecialistFE <-->|MCP Protocol stdio| FEMCP[funnel_engine_mcp]
        SpecialistGCS <-->|MCP Protocol stdio| GCSMCP[gcs_mcp]
    end

    %% GCS Analyst Specific Data Flow
    FEMCP <-->|Reads/Writes Store Vitals| LocalDB[(SQLite Local DB - data/store_performance.db)]
    GCSMCP -->|Ingests Store Performance CSVs| LocalDB

    %% External APIs & Services
    subgraph ExternalServices [External Platforms & APIs]
        PSMCP <-->|Google Play Developer API| GP[Google Play Console]
        RCMCP <-->|RevenueCat REST API| RC[RevenueCat Platform]
        GAMCP <-->|GA4 Data API| GA[Google Analytics 4]
        AMMCP <-->|AdMob API| AM[Google AdMob]
        ASOMCP <-->|Play Store Scraping / AutoASO scripts| PSScr[Google Play Store / AppFollow]
        GCSMCP <-->|GCS Storage Client| GCSB[Play Console GCS Export Bucket]
    end

    %% Human in the loop Policy Interception
    PSMCP -.->|1. Intercepts deploy_app / update_listing| PolicyEngine
    PolicyEngine -->|2. Sends Inline Keyboard request| Telegram[Telegram Bot API]
    Telegram -->|3. Renders buttons| UserTelegram[User's Telegram App]
    UserTelegram -->|4. Clicks Approve / Reject| Telegram
    Telegram -->|5. Callback Query decision| PolicyEngine
    PolicyEngine -.->|6. Allows or Denies| PSMCP
```

---

## 2. Detailed Data Flow Description

### A. Ingestion Loop (Storefront Analyst)
1. **CSV Downloads:** `gcs_mcp` connects to the GCS play console bucket to download raw storefront performance report CSVs.
2. **Database Write:** The Storefront Analyst parses the CSVs and maps metrics (visitors, installs, conversion rates) by country, traffic source, and keyword into the local SQLite database (`data/store_performance.db`).
3. **Synthesis:** `funnel_engine_mcp` reads this SQLite data alongside GA4 and RevenueCat metrics to compute full-funnel activation, retention, and pricing benchmarks.

### B. Execution Loop & Safety Interception (ASO / Deployments)
1. **Action Generation:** The ASO Keyword specialist identifies keyword stuffing or ranking decay and drafts updated storefront listing description metadata (as verified in [update_emi_listing.py](file:///Users/abhishekdhobe/.gemini/antigravity-ide/brain/753ab145-7c3a-463c-b171-aae957d7282c/scratch/update_emi_listing.py)).
2. **Pre-Call Interception:** The agent calls `update_listing` or `deploy_app` on `play_store_mcp`. 
3. **Safety Evaluation:** The Antigravity hook `_PolicyDecideHook` intercepts the call, looking up policies mapped to `play_store/*` tools.
4. **Interactive Approval:** 
   * The policy engine halts execution and dispatches a JSON payload to `https://api.telegram.org/bot{token}/sendMessage` containing inline buttons (`Approve` and `Reject`).
   * The policy engine polls `getUpdates` for 5 minutes.
   * If a callback query is returned with `Approve`, the hook returns `allow=True` and the Play Store API call executes. If the user clicks `Reject` or the request times out, it fails closed, raising an exception to deny execution.
