"""Interactive CLI for the App Management System using Antigravity SDK."""

from __future__ import annotations

import asyncio

from google.antigravity import Agent

from app_manager.agents import create_coordinator_agent, create_multiagent_coordinator
from app_manager.config import AppManagerConfig

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🚀  App Manager — AI-Powered App Management System  🚀    ║
║                                                              ║
║   Powered by Google Antigravity SDK                          ║
║   Play Store • RevenueCat • Analytics • AdMob • ASO          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
Available commands:
  /status    — Check which services are configured
  /health    — Probe each configured service for connectivity issues
  /report    — Generate a daily health report
  /revenue   — Compare subscription vs ad revenue
  /actions   — Get AI-recommended actions
  /help      — Show this help message
  /quit      — Exit the app manager

Or just ask anything in natural language!

Examples:
  • "How is my app doing today?"
  • "What are the top keywords for task manager apps?"
  • "Show me reviews from the last week"
  • "Deploy v2.1.0 to 10% of production users"
  • "What's my MRR and churn rate?"
  • "Optimize my store listing for better rankings"
"""


async def run_interactive(config: AppManagerConfig, *, single_agent: bool = False) -> None:
    """Run the interactive CLI session.

    Args:
        config: App manager configuration.
    """
    print(BANNER)

    # Fail fast on missing GEMINI_API_KEY or credential file not found
    config.validate_or_exit()

    # Show non-critical warnings
    all_msgs = config.validate()
    warnings = [m for m in all_msgs if "GEMINI_API_KEY" not in m and "not found:" not in m]
    if warnings:
        print("⚠️  Configuration warnings:")
        for warning in warnings:
            print(f"   • {warning}")
        print()

    # Show available services
    services = config.get_available_services()
    print(f"✅ Available services: {', '.join(services)}")
    if config.package_name:
        print(f"📦 Default package: {config.package_name}")
    print()
    print("Type /help for commands or ask anything in natural language.")
    print("─" * 60)

    # Create the coordinator agent
    if single_agent:
        print("⚙️  Mode: single-agent (direct MCP access)")
        agent_config = create_coordinator_agent(config)
    else:
        print("🤖 Mode: multi-agent (specialist delegation)")
        agent_config = create_multiagent_coordinator(config)

    async with Agent(agent_config) as agent:
        while True:
            try:
                user_input = input("\n🤖 > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nGoodbye! 👋")
                break

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ("/quit", "/exit", "/q"):
                print("Goodbye! 👋")
                break

            if user_input.lower() == "/help":
                print(HELP_TEXT)
                continue

            if user_input.lower() == "/status":
                from app_manager.tools import get_system_status

                print(get_system_status())
                continue

            if user_input.lower() == "/health":
                _run_health_check(config)
                continue

            if user_input.lower() == "/report":
                if config.package_name:
                    from app_manager.tools import generate_daily_report_prompt

                    user_input = generate_daily_report_prompt(config.package_name)
                else:
                    print("❌ Set APP_PACKAGE_NAME to use /report")
                    continue

            if user_input.lower() == "/revenue":
                if config.package_name:
                    from app_manager.tools import compare_revenue_prompt

                    user_input = compare_revenue_prompt(config.package_name)
                else:
                    print("❌ Set APP_PACKAGE_NAME to use /revenue")
                    continue

            if user_input.lower() == "/actions":
                if config.package_name:
                    from app_manager.tools import suggest_actions_prompt

                    user_input = suggest_actions_prompt(config.package_name)
                else:
                    print("❌ Set APP_PACKAGE_NAME to use /actions")
                    continue

            # Send to agent
            try:
                print()
                response = await agent.chat(user_input)
                async for chunk in response:
                    print(chunk, end="", flush=True)
                print()
            except KeyboardInterrupt:
                print("\n[interrupted]")
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print(
                    "   Tip: use /health to check service connectivity, or /status to verify config."
                )


def _run_health_check(config: AppManagerConfig) -> None:
    """Probe each configured service and report status."""
    import json
    import subprocess
    import sys
    from pathlib import Path

    checks: list[tuple[str, bool, str]] = []

    # GEMINI_API_KEY — required
    checks.append(
        (
            "Gemini API key",
            bool(config.gemini_api_key),
            "set" if config.gemini_api_key else "GEMINI_API_KEY missing",
        )
    )

    # Google credentials file
    if config.google_credentials_path:
        creds_path = Path(config.google_credentials_path)
        if creds_path.exists():
            try:
                json.loads(creds_path.read_text())
                checks.append(("Google credentials", True, str(creds_path)))
            except (json.JSONDecodeError, OSError) as e:
                checks.append(("Google credentials", False, f"invalid JSON: {e}"))
        else:
            checks.append(("Google credentials", False, f"file not found: {creds_path}"))
    else:
        checks.append(("Google credentials", False, "GOOGLE_APPLICATION_CREDENTIALS not set"))

    # RevenueCat API key format
    if config.revenuecat_api_key:
        valid = config.revenuecat_api_key.startswith("sk_")
        checks.append(
            (
                "RevenueCat API key",
                valid,
                "valid format" if valid else "unexpected format (expected sk_...)",
            )
        )
    else:
        checks.append(("RevenueCat API key", False, "REVENUECAT_API_KEY not set"))

    # GA4 property ID — must be numeric
    if config.ga4_property_id:
        valid = config.ga4_property_id.isdigit()
        checks.append(
            ("GA4 property ID", valid, config.ga4_property_id if valid else "must be numeric")
        )
    else:
        checks.append(("GA4 property ID", False, "GA4_PROPERTY_ID not set"))

    # AdMob account ID format
    if config.admob_account_id:
        valid = config.admob_account_id.startswith("pub-")
        checks.append(
            (
                "AdMob account ID",
                valid,
                config.admob_account_id if valid else "unexpected format (expected pub-...)",
            )
        )
    else:
        checks.append(("AdMob account ID", False, "ADMOB_ACCOUNT_ID not set"))

    # GCS bucket
    checks.append(
        (
            "GCS bucket",
            bool(config.gcs_play_console_bucket),
            config.gcs_play_console_bucket or "GCS_PLAY_CONSOLE_BUCKET not set",
        )
    )

    # Google Ads YAML
    if config.google_ads_config_path:
        exists = Path(config.google_ads_config_path).exists()
        checks.append(
            (
                "Google Ads config",
                exists,
                config.google_ads_config_path
                if exists
                else f"file not found: {config.google_ads_config_path}",
            )
        )
    else:
        checks.append(("Google Ads config", False, "not configured (optional)"))

    # MCP server import check (catches missing deps)
    for module, label in [
        ("play_store_mcp", "play-store-mcp"),
        ("revenuecat_mcp", "revenuecat-mcp"),
        ("analytics_mcp", "analytics-mcp"),
        ("admob_mcp", "admob-mcp"),
        ("aso_keyword_mcp", "aso-keyword-mcp"),
    ]:
        # The interpreter and module names are fixed above; no user input reaches the command.
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", f"import {module}"],
            capture_output=True,
            timeout=5,
        )
        ok = result.returncode == 0
        checks.append(
            (
                f"MCP import: {label}",
                ok,
                "ok"
                if ok
                else result.stderr.decode().strip().splitlines()[-1]
                if result.stderr
                else "import failed",
            )
        )

    print("\nHealth check:")
    print("─" * 50)
    for name, ok, detail in checks:
        icon = "✅" if ok else "❌"
        print(f"  {icon}  {name}: {detail}")
    print()


def main() -> None:
    """Entry point for the App Manager CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="App Manager — AI-powered app management")
    parser.add_argument(
        "--single-agent",
        action="store_true",
        help="Use single-agent mode (coordinator with direct MCP access) instead of multi-agent delegation",
    )
    args = parser.parse_args()

    config = AppManagerConfig.from_env()
    asyncio.run(run_interactive(config, single_agent=args.single_agent))


if __name__ == "__main__":
    main()
