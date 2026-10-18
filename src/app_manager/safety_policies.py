"""Safety policies and Telegram approval flow for the App Management System."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from typing import TYPE_CHECKING, Any, cast

import httpx
from google.antigravity import types

if TYPE_CHECKING:
    from google.antigravity.types import ToolCall

logger = logging.getLogger(__name__)


async def telegram_interactive_approval_handler(tool_call: ToolCall) -> bool:
    """Ask the user for approval via a Telegram bot with inline keyboard buttons.

    Blocks execution and polls for the user's choice (Approve/Reject) on Telegram.
    Fails closed (returns False) on timeout or error.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not configured. Failing closed.")
        return False

    exec_id = uuid.uuid4().hex[:8]
    approve_data = f"appr_{exec_id}"
    reject_data = f"rjct_{exec_id}"

    # Format message content
    args_pretty = json.dumps(tool_call.args, indent=2)
    message_text = (
        f"⚠️ *Production Action Approval Requested*\n\n"
        f"The AI agent is attempting to run the following tool:\n"
        f"• *Tool:* `{tool_call.name}`\n\n"
        f"*Arguments:*\n"
        f"```json\n"
        f"{args_pretty}\n"
        f"```\n"
        f"Please click one of the options below to approve or reject."
    )

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": approve_data},
                {"text": "❌ Reject", "callback_data": reject_data},
            ]
        ]
    }

    print(
        f"\n[Safety Policy] Intercepted '{tool_call.name}'. Requesting approval on Telegram (ID: {exec_id})..."
    )

    async with httpx.AsyncClient() as client:
        # 1. Determine starting offset to avoid reading old messages
        offset = 0
        try:
            res = await client.get(
                f"https://api.telegram.org/bot{token}/getUpdates", params={"limit": 1, "offset": -1}
            )
            res.raise_for_status()
            updates_data = res.json()
            if updates_data.get("ok") and updates_data.get("result"):
                offset = updates_data["result"][0]["update_id"] + 1
        except Exception as e:
            logger.warning(
                "Could not pre-fetch Telegram updates offset: %s. Continuing with offset=0.", e
            )

        # 2. Send the message with inline buttons
        try:
            payload = {
                "chat_id": chat_id,
                "text": message_text,
                "parse_mode": "Markdown",
                "reply_markup": reply_markup,
            }
            res = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage", json=payload
            )
            res.raise_for_status()
            msg_data = res.json()
            if not msg_data.get("ok"):
                logger.error("Failed to send Telegram message: %s", msg_data.get("description"))
                return False
            message_id = msg_data["result"]["message_id"]
        except Exception:
            logger.exception("Failed to send Telegram message for approval")
            return False

        # 3. Poll for the callback query response
        timeout_seconds = 300  # 5 minutes
        poll_interval = 2.0
        elapsed = 0.0

        print("[Safety Policy] Waiting for response...")
        try:
            while elapsed < timeout_seconds:
                try:
                    params = {"offset": offset, "timeout": 10}
                    res = await client.get(
                        f"https://api.telegram.org/bot{token}/getUpdates",
                        params=params,
                        timeout=12.0,
                    )
                    res.raise_for_status()
                    updates = res.json()

                    if updates.get("ok") and updates.get("result"):
                        for update in updates["result"]:
                            offset = update["update_id"] + 1
                            callback_query = update.get("callback_query")
                            if not callback_query:
                                continue

                            data = callback_query.get("data")
                            query_id = callback_query.get("id")

                            if data == approve_data:
                                # Acknowledge callback
                                await client.post(
                                    f"https://api.telegram.org/bot{token}/answerCallbackQuery",
                                    json={"callback_query_id": query_id, "text": "Approved!"},
                                )
                                # Update message
                                updated_text = message_text + "\n\n🟢 *Status: Approved by User*"
                                await client.post(
                                    f"https://api.telegram.org/bot{token}/editMessageText",
                                    json={
                                        "chat_id": chat_id,
                                        "message_id": message_id,
                                        "text": updated_text,
                                        "parse_mode": "Markdown",
                                    },
                                )
                                print(f"🟢 [Safety Policy] Approved via Telegram (ID: {exec_id})")
                                return True

                            elif data == reject_data:
                                # Acknowledge callback
                                await client.post(
                                    f"https://api.telegram.org/bot{token}/answerCallbackQuery",
                                    json={"callback_query_id": query_id, "text": "Rejected!"},
                                )
                                # Update message
                                updated_text = message_text + "\n\n🔴 *Status: Rejected by User*"
                                await client.post(
                                    f"https://api.telegram.org/bot{token}/editMessageText",
                                    json={
                                        "chat_id": chat_id,
                                        "message_id": message_id,
                                        "text": updated_text,
                                        "parse_mode": "Markdown",
                                    },
                                )
                                print(f"🔴 [Safety Policy] Rejected via Telegram (ID: {exec_id})")
                                return False

                except httpx.HTTPError as he:
                    logger.warning("Telegram API polling error: %s", he)

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval + 10.0  # Accounts for read timeout if empty

            # Timeout case: edit message to show expired
            expired_text = message_text + "\n\n🟡 *Status: Expired (No response within 5m)*"
            await client.post(
                f"https://api.telegram.org/bot{token}/editMessageText",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": expired_text,
                    "parse_mode": "Markdown",
                },
            )
            print("🟡 [Safety Policy] Approval request expired (timeout).")
            return False

        except Exception:
            logger.exception("Error in Telegram polling loop")
            return False


def get_play_store_policies(play_store_server: types.BaseMcpServerConfig) -> list[Any]:
    """Generate the security policies for the Play Store MCP server."""
    from google.antigravity.hooks import policy

    return cast(
        "list[Any]",
        policy.ask_user(
            play_store_server,
            mcp_tools=[
                "deploy_app",
                "deploy_app_multilang",
                "promote_release",
                "update_rollout",
                "halt_release",
                "update_listing",
                "batch_deploy",
            ],
            handler=telegram_interactive_approval_handler,
        ),
    )


def get_atlassian_policies(atlassian_server: types.BaseMcpServerConfig) -> list[Any]:
    """Generate the security policies for the Atlassian MCP server.

    Intercepts any ticket or page creation/mutation so it can be approved via Telegram.
    """
    from google.antigravity.hooks import policy

    return cast(
        "list[Any]",
        policy.ask_user(
            atlassian_server,
            mcp_tools=[
                "jira_create_issue",
                "jira_update_issue",
                "jira_add_comment",
                "jira_transition_issue",
                "confluence_create_page",
                "confluence_update_page",
                "confluence_add_comment",
            ],
            handler=telegram_interactive_approval_handler,
        ),
    )
