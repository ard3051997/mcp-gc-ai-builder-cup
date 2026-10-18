"""Agent definitions for the App Management System using Google Antigravity SDK."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from google.antigravity import LocalAgentConfig, types

from app_manager.personas import COORDINATOR_PERSONA, COORDINATOR_ROUTER_PERSONA
from app_manager.tools import get_app_rulebook, get_system_status
from app_manager.vertex import llm_kwargs
from mcp_gc_shared.write_guard import is_read_only

if TYPE_CHECKING:
    from app_manager.config import AppManagerConfig


def _build_mcp_servers(config: AppManagerConfig) -> list[types.McpStdioServer]:
    """Build MCP server configurations based on available credentials.

    Only includes servers for which credentials are configured.

    Args:
        config: App manager configuration.

    Returns:
        List of MCP server configurations.
    """
    servers: list[types.McpStdioServer] = []
    python = sys.executable
    read_only = is_read_only()

    # Play Store MCP — always include if Google credentials exist
    if config.google_credentials_path and not read_only:
        env: dict[str, str] = {
            "GOOGLE_APPLICATION_CREDENTIALS": config.google_credentials_path,
        }
        servers.append(
            types.McpStdioServer(
                name="play_store",
                command=python,
                args=["-m", "play_store_mcp"],
                env=env,
            )
        )

    # RevenueCat MCP
    if config.revenuecat_api_key and not read_only:
        env = {"REVENUECAT_API_KEY": config.revenuecat_api_key}
        if config.revenuecat_project_id:
            env["REVENUECAT_PROJECT_ID"] = config.revenuecat_project_id
        servers.append(
            types.McpStdioServer(
                name="revenuecat",
                command=python,
                args=["-m", "revenuecat_mcp"],
                env=env,
            )
        )

    # Analytics MCP
    if config.ga4_property_id and config.google_credentials_path:
        servers.append(
            types.McpStdioServer(
                name="analytics",
                command=python,
                args=["-m", "analytics_mcp"],
                env={
                    "GA4_PROPERTY_ID": config.ga4_property_id,
                    "GOOGLE_APPLICATION_CREDENTIALS": config.google_credentials_path,
                },
            )
        )

    # AdMob MCP
    if config.admob_account_id and config.google_credentials_path:
        servers.append(
            types.McpStdioServer(
                name="admob",
                command=python,
                args=["-m", "admob_mcp"],
                env={
                    "ADMOB_ACCOUNT_ID": config.admob_account_id,
                    "GOOGLE_APPLICATION_CREDENTIALS": config.google_credentials_path,
                },
            )
        )

    # ASO Keyword MCP — always available (uses public scraping)
    servers.append(
        types.McpStdioServer(
            name="aso_keywords",
            command=python,
            args=["-m", "aso_keyword_mcp"],
        )
    )

    # Image Generation MCP (creative assets)
    if config.gemini_api_key:
        servers.append(
            types.McpStdioServer(
                name="image_gen",
                command=python,
                args=["-m", "image_gen_mcp"],
                env={"GEMINI_API_KEY": config.gemini_api_key},
            )
        )

    # Official Google Ads MCP
    if (
        not read_only
        and config.google_ads_config_path
        and Path(config.google_ads_config_path).exists()
    ):
        servers.append(
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
        )

    # GCS MCP
    if not read_only and config.google_credentials_path and config.gcs_play_console_bucket:
        servers.append(
            types.McpStdioServer(
                name="gcs",
                command=python,
                args=["-m", "gcs_mcp"],
                env={
                    "GOOGLE_APPLICATION_CREDENTIALS": config.google_credentials_path,
                    "GCS_PLAY_CONSOLE_BUCKET": config.gcs_play_console_bucket,
                },
            )
        )
    # Funnel Engine MCP — requires Google and optionally RevenueCat
    if config.google_credentials_path and not read_only:
        env = {"GOOGLE_APPLICATION_CREDENTIALS": config.google_credentials_path}
        if config.ga4_property_id:
            env["GA4_PROPERTY_ID"] = config.ga4_property_id
        if config.revenuecat_api_key:
            env["REVENUECAT_API_KEY"] = config.revenuecat_api_key
        if config.revenuecat_project_id:
            env["REVENUECAT_PROJECT_ID"] = config.revenuecat_project_id

        servers.append(
            types.McpStdioServer(
                name="funnel_engine",
                command=python,
                args=["-m", "funnel_engine_mcp"],
                env=env,
            )
        )

    return servers


def create_coordinator_agent(config: AppManagerConfig) -> LocalAgentConfig:
    """Create the coordinator agent with direct access to all configured MCP servers."""
    mcp_servers = _build_mcp_servers(config)

    available_services = config.get_available_services()
    service_list = ", ".join(available_services) if available_services else "none"
    context_note = f"\n\nCurrently configured services: {service_list}"

    play_store_server = next((s for s in mcp_servers if s.name == "play_store"), None)
    policies = []
    if play_store_server:
        from app_manager.safety_policies import get_play_store_policies

        policies.extend(get_play_store_policies(play_store_server))

    kwargs: dict = {
        "system_instructions": COORDINATOR_PERSONA + context_note,
        "mcp_servers": mcp_servers,
        "tools": [get_system_status, get_app_rulebook],
        "policies": policies,
    }
    kwargs.update(llm_kwargs(config.gemini_api_key))

    return LocalAgentConfig(**kwargs)


def create_multiagent_coordinator(config: AppManagerConfig) -> LocalAgentConfig:
    """Create a true multi-agent coordinator that delegates to specialist sub-agents.

    The coordinator has NO direct MCP server access. Every data request is
    routed to the appropriate specialist via async Python tool functions, each
    of which spawns a focused sub-agent with only its relevant MCP server.

    This keeps each specialist's context window small (one MCP's tool list)
    and lets the coordinator synthesize across domains without context bloat.
    """
    from app_manager.specialists import make_specialist_tools

    available_services = config.get_available_services()
    service_list = ", ".join(available_services) if available_services else "none"
    context_note = f"\n\nCurrently configured services: {service_list}"

    specialist_tools = make_specialist_tools(config)

    kwargs: dict = {
        "system_instructions": COORDINATOR_ROUTER_PERSONA + context_note,
        # No mcp_servers — all data flows through specialist tools
        "tools": [get_system_status, get_app_rulebook, *specialist_tools],
        "capabilities": types.CapabilitiesConfig(enable_subagents=True),
    }
    kwargs.update(llm_kwargs(config.gemini_api_key))

    return LocalAgentConfig(**kwargs)
