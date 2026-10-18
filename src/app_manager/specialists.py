"""Specialist agent tool functions for the multi-agent coordinator.

Each function spawns a domain-specific sub-agent with only its relevant MCP
server and returns the specialist's full text response.  The coordinator calls
these as regular Python tools — the SDK handles async dispatch automatically.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from google.antigravity import Agent, LocalAgentConfig, types

from app_manager.personas import (
    ADMOB_PERSONA,
    ANALYTICS_PERSONA,
    APP_STORE_PERSONA,
    ASO_PERSONA,
    ATLASSIAN_PERSONA,
    FCM_PUSH_PERSONA,
    FUNNEL_ENGINE_PERSONA,
    GCS_PERSONA,
    GOOGLE_ADS_PERSONA,
    IMAGE_GEN_PERSONA,
    JOURNEY_MAP_PERSONA,
    PLAY_STORE_PERSONA,
    REVENUECAT_PERSONA,
    STOREFRONT_ANALYST_PERSONA,
)
from app_manager.vertex import llm_kwargs
from mcp_gc_shared.write_guard import is_read_only

if TYPE_CHECKING:
    from collections.abc import Callable

    from app_manager.config import AppManagerConfig

logger = structlog.get_logger(__name__)


def _run_specialist(config: LocalAgentConfig, query: str) -> str:
    """Synchronous wrapper — runs a specialist agent and returns its full response.

    The SDK's ToolRunner executes tool calls by awaiting coroutines when they
    are async, so the async variant below is used.  This sync helper is kept for
    reference / testing without an event loop.
    """
    import asyncio

    async def _run() -> str:
        chunks: list[str] = []
        async with Agent(config) as agent:
            response = await agent.chat(query)
            async for chunk in response:
                chunks.append(chunk)
        return "".join(chunks)

    return asyncio.run(_run())


async def _run_specialist_async(config: LocalAgentConfig, query: str) -> str:
    """Async version used as the actual tool implementation."""
    chunks: list[str] = []
    async with Agent(config) as agent:
        response = await agent.chat(query)
        async for chunk in response:
            chunks.append(chunk)
    return "".join(chunks)


def _base_kwargs(config: AppManagerConfig) -> dict:
    """Common kwargs for all specialist LocalAgentConfig instances."""
    return dict(llm_kwargs(config.gemini_api_key))


def make_specialist_tools(config: AppManagerConfig) -> list[Callable]:
    """Return a list of async tool functions bound to *config*.

    Only tools whose required credentials are present are included — the
    coordinator receives a dynamic tool set that reflects available services.
    """
    python = sys.executable
    tools: list[Callable] = []
    base = _base_kwargs(config)
    read_only = is_read_only()

    # -------------------------------------------------------------------------
    # Play Store
    # -------------------------------------------------------------------------
    if config.google_credentials_path and not read_only:
        from app_manager.safety_policies import get_play_store_policies

        _ps_server = types.McpStdioServer(
            name="play_store",
            command=python,
            args=["-m", "play_store_mcp"],
            env={"GOOGLE_APPLICATION_CREDENTIALS": config.google_credentials_path},
        )
        _ps_cfg = LocalAgentConfig(
            system_instructions=PLAY_STORE_PERSONA,
            mcp_servers=[_ps_server],
            policies=get_play_store_policies(_ps_server),
            **base,
        )

        async def ask_play_store(query: str) -> str:
            """Query the Play Store specialist.

            Use for: app releases, staged rollouts, store listings, reviews,
            Android Vitals (crashes/ANRs), subscriptions, in-app products,
            tester management, and deployment operations.
            """
            logger.info("Delegating to Play Store specialist", query=query[:80])
            return await _run_specialist_async(_ps_cfg, query)

        tools.append(ask_play_store)

    # -------------------------------------------------------------------------
    # RevenueCat
    # -------------------------------------------------------------------------
    if config.revenuecat_api_key and not read_only:
        _rc_env = {"REVENUECAT_API_KEY": config.revenuecat_api_key}
        if config.revenuecat_project_id:
            _rc_env["REVENUECAT_PROJECT_ID"] = config.revenuecat_project_id

        _rc_cfg = LocalAgentConfig(
            system_instructions=REVENUECAT_PERSONA,
            mcp_servers=[
                types.McpStdioServer(
                    name="revenuecat",
                    command=python,
                    args=["-m", "revenuecat_mcp"],
                    env=_rc_env,
                )
            ],
            **base,
        )

        async def ask_revenuecat(query: str) -> str:
            """Query the RevenueCat specialist.

            Use for: MRR, ARR, churn rate, subscriber profiles, entitlements,
            trial conversions, refunds, offerings, and transaction history.
            """
            logger.info("Delegating to RevenueCat specialist", query=query[:80])
            return await _run_specialist_async(_rc_cfg, query)

        tools.append(ask_revenuecat)

    # -------------------------------------------------------------------------
    # Analytics (GA4)
    # -------------------------------------------------------------------------
    if config.ga4_property_id and config.google_credentials_path:
        _ga_cfg = LocalAgentConfig(
            system_instructions=ANALYTICS_PERSONA,
            mcp_servers=[
                types.McpStdioServer(
                    name="analytics",
                    command=python,
                    args=["-m", "analytics_mcp"],
                    env={
                        "GA4_PROPERTY_ID": config.ga4_property_id,
                        "GOOGLE_APPLICATION_CREDENTIALS": config.google_credentials_path,
                    },
                )
            ],
            **base,
        )

        async def ask_analytics(query: str) -> str:
            """Query the Analytics specialist.

            Use for: DAU/WAU/MAU, user retention cohorts, event tracking,
            acquisition channels, screen views, revenue reports, demographics,
            and real-time active users.
            """
            logger.info("Delegating to Analytics specialist", query=query[:80])
            return await _run_specialist_async(_ga_cfg, query)

        tools.append(ask_analytics)

    # -------------------------------------------------------------------------
    # AdMob
    # -------------------------------------------------------------------------
    if config.admob_account_id and config.google_credentials_path:
        _am_cfg = LocalAgentConfig(
            system_instructions=ADMOB_PERSONA,
            mcp_servers=[
                types.McpStdioServer(
                    name="admob",
                    command=python,
                    args=["-m", "admob_mcp"],
                    env={
                        "ADMOB_ACCOUNT_ID": config.admob_account_id,
                        "GOOGLE_APPLICATION_CREDENTIALS": config.google_credentials_path,
                    },
                )
            ],
            **base,
        )

        async def ask_admob(query: str) -> str:
            """Query the AdMob specialist.

            Use for: ad earnings, eCPM, fill rates, network/mediation reports,
            ad unit performance, impressions, clicks, and revenue breakdown.
            """
            logger.info("Delegating to AdMob specialist", query=query[:80])
            return await _run_specialist_async(_am_cfg, query)

        tools.append(ask_admob)

    # -------------------------------------------------------------------------
    # ASO Keywords
    # -------------------------------------------------------------------------
    _aso_cfg = LocalAgentConfig(
        system_instructions=ASO_PERSONA,
        mcp_servers=[
            types.McpStdioServer(
                name="aso_keywords",
                command=python,
                args=["-m", "aso_keyword_mcp"],
            )
        ],
        **base,
    )

    async def ask_aso(query: str) -> str:
        """Query the ASO (App Store Optimization) specialist.

        Use for: keyword research, difficulty scoring, keyword volume,
        competitor keyword gaps, ranking tracking, listing optimization,
        and ASO health scores.
        """
        logger.info("Delegating to ASO specialist", query=query[:80])
        return await _run_specialist_async(_aso_cfg, query)

    tools.append(ask_aso)

    # -------------------------------------------------------------------------
    # Image Generation (creative assets)
    # -------------------------------------------------------------------------
    if config.gemini_api_key:
        _image_gen_cfg = LocalAgentConfig(
            system_instructions=IMAGE_GEN_PERSONA,
            mcp_servers=[
                types.McpStdioServer(
                    name="image_gen",
                    command=python,
                    args=["-m", "image_gen_mcp"],
                    env={"GEMINI_API_KEY": config.gemini_api_key},
                )
            ],
            **base,
        )

        async def ask_image_gen(query: str) -> str:
            """Query the creative asset specialist.

            Use for: generating App Store screenshot/icon draft concepts and
            other store-listing creative imagery from a text description.
            """
            logger.info("Delegating to image generation specialist", query=query[:80])
            return await _run_specialist_async(_image_gen_cfg, query)

        tools.append(ask_image_gen)

    # -------------------------------------------------------------------------
    # Google Ads
    # -------------------------------------------------------------------------
    if (
        not read_only
        and config.google_ads_config_path
        and Path(config.google_ads_config_path).exists()
    ):
        _ads_cfg = LocalAgentConfig(
            system_instructions=GOOGLE_ADS_PERSONA,
            mcp_servers=[
                types.McpStdioServer(
                    name="google_ads",
                    command="uvx",
                    args=[
                        "--from",
                        "git+https://github.com/googleads/google-ads-mcp.git",
                        "google-ads-mcp",
                    ],
                    env={"GOOGLE_ADS_CONFIGURATION_FILE_PATH": config.google_ads_config_path},
                )
            ],
            **base,
        )

        async def ask_google_ads(query: str) -> str:
            """Query the Google Ads specialist.

            Use for: campaign performance, ad groups, ads, budgets, CPC, CTR,
            conversion rates, keyword bids, and account structure.
            """
            logger.info("Delegating to Google Ads specialist", query=query[:80])
            return await _run_specialist_async(_ads_cfg, query)

        tools.append(ask_google_ads)

    # -------------------------------------------------------------------------
    # Funnel Engine
    # -------------------------------------------------------------------------
    if config.google_credentials_path and not read_only:
        _fe_env = {"GOOGLE_APPLICATION_CREDENTIALS": config.google_credentials_path}
        if config.ga4_property_id:
            _fe_env["GA4_PROPERTY_ID"] = config.ga4_property_id
        if config.revenuecat_api_key:
            _fe_env["REVENUECAT_API_KEY"] = config.revenuecat_api_key
        if config.revenuecat_project_id:
            _fe_env["REVENUECAT_PROJECT_ID"] = config.revenuecat_project_id

        _fe_cfg = LocalAgentConfig(
            system_instructions=FUNNEL_ENGINE_PERSONA,
            mcp_servers=[
                types.McpStdioServer(
                    name="funnel_engine",
                    command=python,
                    args=["-m", "funnel_engine_mcp"],
                    env=_fe_env,
                )
            ],
            **base,
        )

        async def ask_funnel(query: str) -> str:
            """Query the Funnel Engine specialist.

            Use for: full-funnel stitching across acquisition → activation →
            revenue → retention, leak detection, funnel health scores, LTV
            estimation, benchmark comparisons, and growth recommendations.
            """
            logger.info("Delegating to Funnel Engine specialist", query=query[:80])
            return await _run_specialist_async(_fe_cfg, query)

        tools.append(ask_funnel)

    # -------------------------------------------------------------------------
    # Google Cloud Storage
    # -------------------------------------------------------------------------
    if not read_only and config.google_credentials_path and config.gcs_play_console_bucket:
        _gcs_cfg = LocalAgentConfig(
            system_instructions=GCS_PERSONA,
            mcp_servers=[
                types.McpStdioServer(
                    name="gcs",
                    command=python,
                    args=["-m", "gcs_mcp"],
                    env={
                        "GOOGLE_APPLICATION_CREDENTIALS": config.google_credentials_path,
                        "GCS_PLAY_CONSOLE_BUCKET": config.gcs_play_console_bucket,
                    },
                )
            ],
            **base,
        )

        async def ask_gcs(query: str) -> str:
            """Query the Google Cloud Storage specialist.

            Use for: Play Console bulk export CSVs (installs, ratings, crashes,
            ANRs), listing and reading GCS blobs, and downloading large reports.
            """
            logger.info("Delegating to GCS specialist", query=query[:80])
            return await _run_specialist_async(_gcs_cfg, query)

        tools.append(ask_gcs)

    # -------------------------------------------------------------------------
    # Journey Map — always available (uses local EVENTS.md + funnel_engine)
    # -------------------------------------------------------------------------
    _jm_env: dict[str, str] = {}
    if config.google_credentials_path:
        _jm_env["GOOGLE_APPLICATION_CREDENTIALS"] = config.google_credentials_path
    if config.ga4_property_id:
        _jm_env["GA4_PROPERTY_ID"] = config.ga4_property_id
    if config.gcs_play_console_bucket:
        _jm_env["GCS_PLAY_CONSOLE_BUCKET"] = config.gcs_play_console_bucket
    if config.revenuecat_api_key:
        _jm_env["REVENUECAT_API_KEY"] = config.revenuecat_api_key
    if config.package_name:
        _jm_env["APP_PACKAGE_NAME"] = config.package_name

    _jm_cfg = LocalAgentConfig(
        system_instructions=JOURNEY_MAP_PERSONA,
        mcp_servers=[
            types.McpStdioServer(
                name="journey_map",
                command=python,
                args=["-m", "journey_map_mcp"],
                env=_jm_env,
            )
        ],
        **base,
    )

    async def ask_journey_map(query: str) -> str:
        """Query the Journey Map specialist.

        Use for: generating or refreshing journey_map.html with live funnel data,
        parsing EVENTS.md to get structured journey/stage/branch data, listing
        all defined GA4 events and source file references, computing emotion scores,
        and producing the JMIP interactive dashboard.
        """
        logger.info("Delegating to Journey Map specialist", query=query[:80])
        return await _run_specialist_async(_jm_cfg, query)

    if not read_only:
        tools.append(ask_journey_map)

    # -------------------------------------------------------------------------
    # Storefront Performance Analyst
    # -------------------------------------------------------------------------
    if config.google_credentials_path and not read_only:
        _sfa_env = {
            "GOOGLE_APPLICATION_CREDENTIALS": config.google_credentials_path,
        }
        if config.gcs_play_console_bucket:
            _sfa_env["GCS_PLAY_CONSOLE_BUCKET"] = config.gcs_play_console_bucket
        if config.package_name:
            _sfa_env["APP_PACKAGE_NAME"] = config.package_name

        _sfa_cfg = LocalAgentConfig(
            system_instructions=STOREFRONT_ANALYST_PERSONA,
            mcp_servers=[
                types.McpStdioServer(
                    name="funnel_engine",
                    command=python,
                    args=["-m", "funnel_engine_mcp"],
                    env=_sfa_env,
                )
            ],
            **base,
        )

        async def ask_storefront_analyst(query: str) -> str:
            """Query the Storefront Analyst specialist.

            Use for: ingesting Google Play Console storefront performance reports
            from GCS into SQLite, analyzing visitor, install, and conversion rates,
            and querying historical metrics by country, traffic source, or search term.
            """
            logger.info("Delegating to Storefront Analyst specialist", query=query[:80])
            return await _run_specialist_async(_sfa_cfg, query)

        tools.append(ask_storefront_analyst)

    # -------------------------------------------------------------------------
    # FCM Push Notifications
    # -------------------------------------------------------------------------
    _fcm_env = {}
    if config.google_credentials_path:
        _fcm_env["GOOGLE_APPLICATION_CREDENTIALS"] = config.google_credentials_path

    _fcm_cfg = LocalAgentConfig(
        system_instructions=FCM_PUSH_PERSONA,
        mcp_servers=[
            types.McpStdioServer(
                name="fcm_push",
                command=python,
                args=["-m", "fcm_push_mcp"],
                env=_fcm_env,
            )
        ],
        **base,
    )

    async def ask_fcm_push(query: str) -> str:
        """Query the FCM Push specialist.

        Use for: sending push notifications via topics, individual tokens, or
        conditional logic, and targeted re-engagement campaigns.
        """
        logger.info("Delegating to FCM Push specialist", query=query[:80])
        return await _run_specialist_async(_fcm_cfg, query)

    if not read_only:
        tools.append(ask_fcm_push)

    # -------------------------------------------------------------------------
    # iOS App Store Connect
    # -------------------------------------------------------------------------
    _app_store_env = {}
    if os.environ.get("APP_STORE_CONNECT_KEY_ID"):
        _app_store_env["APP_STORE_CONNECT_KEY_ID"] = os.environ.get("APP_STORE_CONNECT_KEY_ID")
    if os.environ.get("APP_STORE_CONNECT_ISSUER_ID"):
        _app_store_env["APP_STORE_CONNECT_ISSUER_ID"] = os.environ.get(
            "APP_STORE_CONNECT_ISSUER_ID"
        )
    if os.environ.get("APP_STORE_CONNECT_PRIVATE_KEY"):
        _app_store_env["APP_STORE_CONNECT_PRIVATE_KEY"] = os.environ.get(
            "APP_STORE_CONNECT_PRIVATE_KEY"
        )

    _app_store_cfg = LocalAgentConfig(
        system_instructions=APP_STORE_PERSONA,
        mcp_servers=[
            types.McpStdioServer(
                name="app_store",
                command=python,
                args=["-m", "app_store_mcp"],
                env=_app_store_env,
            )
        ],
        **base,
    )

    async def ask_app_store(query: str) -> str:
        """Query the App Store Connect specialist.

        Use for: iOS App Store details, fetching and replying to reviews,
        updating storefront metadata listings (titles/descriptions), and
        managing App Store Connect releases/builds.
        """
        logger.info("Delegating to App Store Connect specialist", query=query[:80])
        return await _run_specialist_async(_app_store_cfg, query)

    if not read_only:
        tools.append(ask_app_store)

    # -------------------------------------------------------------------------
    # Atlassian (Jira/Confluence)
    # -------------------------------------------------------------------------
    if not read_only and config.jira_url and config.jira_username and config.jira_api_token:
        from app_manager.safety_policies import get_atlassian_policies

        _at_env = {
            "JIRA_URL": config.jira_url,
            "JIRA_USERNAME": config.jira_username,
            "JIRA_API_TOKEN": config.jira_api_token,
        }
        if config.confluence_url and config.confluence_username:
            _at_env["CONFLUENCE_URL"] = config.confluence_url
            _at_env["CONFLUENCE_USERNAME"] = config.confluence_username

        _at_server = types.McpStdioServer(
            name="atlassian",
            command="uvx",
            args=["mcp-atlassian"],
            env=_at_env,
        )

        _at_cfg = LocalAgentConfig(
            system_instructions=ATLASSIAN_PERSONA,
            mcp_servers=[_at_server],
            policies=get_atlassian_policies(_at_server),
            **base,
        )

        async def ask_atlassian(query: str) -> str:
            """Query the Atlassian specialist.

            Use for: creating and managing dev tasks, bug tickets in Jira,
            and creating/updating documentation in Confluence.
            """
            logger.info("Delegating to Atlassian specialist", query=query[:80])
            return await _run_specialist_async(_at_cfg, query)

        tools.append(ask_atlassian)

    return tools
