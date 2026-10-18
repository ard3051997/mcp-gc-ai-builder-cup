import asyncio
import json
import os
import sqlite3

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field

from api_server.auth import revenuecat_verification_required
from api_server.webhook_store import (
    claim_next_webhook_event,
    claim_webhook_event,
    finish_webhook_event,
    finish_webhook_receipt,
)
from app_manager.config import AppManagerConfig
from app_manager.credential_store import get_app_credentials
from app_manager.specialists import make_specialist_tools
from funnel_engine.db import DEFAULT_DB_PATH, log_db_action
from mcp_gc_shared.write_guard import assert_writes_allowed, is_read_only

logger = structlog.get_logger("api_webhooks")

router = APIRouter()


class RevenueCatEvent(BaseModel):
    id: str | None = Field(default=None, description="RevenueCat provider event ID")
    type: str = Field(..., description="RevenueCat event type, e.g. CANCELLATION or BILLING_ERROR")
    app_id: str = Field(..., description="The app's package name / bundle ID")
    app_user_id: str = Field(..., description="The subscriber's user ID")
    product_id: str | None = None
    entitlement_id: str | None = None


class RevenueCatWebhookPayload(BaseModel):
    event: RevenueCatEvent


def _redacted_action_arguments(event: RevenueCatEvent) -> str:
    return json.dumps(
        {
            "user_id": "[REDACTED]",
            "event_type": event.type,
            "product_id": event.product_id,
        }
    )


async def run_fcm_reengagement(event: RevenueCatEvent) -> None:
    """Asynchronously delegate to the FCM Push specialist to dispatch re-engagement notifications."""
    assert_writes_allowed("FCM re-engagement")
    logger.info("Starting FCM re-engagement logic", event_type=event.type, app=event.app_id)
    try:
        # Resolve app-specific credentials from the credential store
        creds = get_app_credentials(event.app_id)
        config = AppManagerConfig(
            package_name=event.app_id,
            google_credentials_path=creds.google_credentials_path,
            revenuecat_api_key=creds.revenuecat_api_key,
            revenuecat_project_id=creds.revenuecat_project_id,
            ga4_property_id=creds.ga4_property_id,
            admob_account_id=creds.admob_account_id,
            gcs_play_console_bucket=creds.gcs_play_console_bucket,
            gemini_api_key=creds.gemini_api_key or os.environ.get("GEMINI_API_KEY"),
        )

        # Initialize specialists with resolved credentials
        tools = make_specialist_tools(config)
        ask_fcm_push = None
        for t in tools:
            if t.__name__ == "ask_fcm_push":
                ask_fcm_push = t
                break

        if not ask_fcm_push:
            logger.error("FCM Push specialist not found in registered tools.")
            # Log failure to DB
            log_db_action(
                db_path=DEFAULT_DB_PATH,
                action_type="push_reengagement",
                app_package=event.app_id,
                tool_name="fcm_push/send_push_to_token",
                arguments=_redacted_action_arguments(event),
                result="failed",
                reasoning="FCM Push specialist not found in registered tools.",
            )
            raise RuntimeError("FCM Push specialist is unavailable")

        # Build natural language prompt for the specialist agent
        query = (
            "Construct a compelling re-engagement push notification with an appropriate title and "
            "body based on this verified provider event. "
            f"A RevenueCat event of type '{event.type}' occurred for app '{event.app_id}'. "
            f"The user ID is '{event.app_user_id}' and product ID is '{event.product_id or 'unknown'}'. "
            "Win back this user or resolve the billing issue, and send it to user registration token "
            f"'{event.app_user_id}' using the FCM send_push_to_token tool."
        )

        logger.info("Invoking FCM Push specialist", event_type=event.type, app=event.app_id)
        await ask_fcm_push(query)
        logger.info("FCM Push specialist finished", event_type=event.type, app=event.app_id)

        # Log successful action to DB
        log_db_action(
            db_path=DEFAULT_DB_PATH,
            action_type="push_reengagement",
            app_package=event.app_id,
            tool_name="fcm_push/send_push_to_token",
            arguments=_redacted_action_arguments(event),
            result="success",
            reasoning=f"RevenueCat {event.type} event triggered FCM push.",
        )
    except Exception:
        # Specialist exceptions may include the prompt and subscriber token.
        logger.error(  # noqa: TRY400
            "FCM re-engagement pipeline execution failed",
            event_type=event.type,
            app=event.app_id,
        )
        # Log exception failure to DB
        try:
            log_db_action(
                db_path=DEFAULT_DB_PATH,
                action_type="push_reengagement",
                app_package=event.app_id,
                tool_name="fcm_push/send_push_to_token",
                arguments=_redacted_action_arguments(event),
                result="failed",
                reasoning="Exception during FCM re-engagement pipeline.",
            )
        except Exception:
            logger.error("Failed to log re-engagement failure to DB")  # noqa: TRY400
        raise


async def _process_revenuecat_event(event: RevenueCatEvent, claim_token: str) -> None:
    """Process one claimed event and durably publish its terminal state."""
    try:
        await run_fcm_reengagement(event)
    except Exception as exc:
        finish_webhook_event(
            "revenuecat",
            event.id or "",
            claim_token,
            succeeded=False,
            error_safe=f"FCM re-engagement failed ({type(exc).__name__})",
            db_path=DEFAULT_DB_PATH,
        )
        return
    finish_webhook_event(
        "revenuecat",
        event.id or "",
        claim_token,
        succeeded=True,
        db_path=DEFAULT_DB_PATH,
    )


async def run_revenuecat_outbox_worker() -> None:
    """Recover failed or expired RevenueCat outbox work in the background."""
    while True:
        await asyncio.sleep(30)
        if is_read_only():
            continue
        try:
            claim = claim_next_webhook_event("revenuecat", DEFAULT_DB_PATH)
            if claim is None:
                continue
            try:
                payload = RevenueCatWebhookPayload.model_validate_json(claim["payload_json"])
            except Exception as exc:
                finish_webhook_receipt(
                    "revenuecat",
                    claim["event_id_hash"],
                    claim["claim_token"],
                    succeeded=False,
                    error_safe=f"Invalid stored webhook payload ({type(exc).__name__})",
                    db_path=DEFAULT_DB_PATH,
                )
                continue
            if payload.event.type in ("CANCELLATION", "BILLING_ERROR"):
                await _process_revenuecat_event(payload.event, claim["claim_token"])
            else:
                finish_webhook_receipt(
                    "revenuecat",
                    claim["event_id_hash"],
                    claim["claim_token"],
                    succeeded=True,
                    db_path=DEFAULT_DB_PATH,
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("RevenueCat outbox recovery iteration failed")


@router.post("/revenuecat")
async def receive_revenuecat_webhook(
    payload: RevenueCatWebhookPayload,
    background_tasks: BackgroundTasks,
    request: Request,
) -> dict[str, str]:
    """Receive webhook events from RevenueCat and trigger FCM re-engagement campaigns."""
    if is_read_only():
        raise HTTPException(
            status_code=403,
            detail="API is in read-only mode; webhook processing is disabled",
        )
    event = payload.event
    verified = getattr(request.state, "revenuecat_webhook_verified", False)
    if revenuecat_verification_required() and not verified:
        raise HTTPException(status_code=401, detail="Invalid RevenueCat webhook secret")
    if not event.id:
        raise HTTPException(status_code=400, detail="RevenueCat event ID is required")

    try:
        state, claim_token = claim_webhook_event(
            "revenuecat",
            event.id,
            payload.model_dump_json(),
            DEFAULT_DB_PATH,
        )
    except (sqlite3.Error, RuntimeError):
        logger.exception("Unable to persist RevenueCat webhook receipt")
        raise HTTPException(status_code=503, detail="Webhook receipt store unavailable")
    if claim_token is None:
        logger.info(
            "Ignored replayed RevenueCat webhook",
            type=event.type,
            app=event.app_id,
            receipt_state=state,
        )
        return {"status": "duplicate", "message": f"Event is already {state}"}

    logger.info("Received RevenueCat webhook event", type=event.type, app=event.app_id)

    if event.type in ("CANCELLATION", "BILLING_ERROR"):
        background_tasks.add_task(_process_revenuecat_event, event, claim_token)
        return {"status": "processing", "message": f"Triggered FCM push for {event.type}"}

    if not finish_webhook_event(
        "revenuecat",
        event.id,
        claim_token,
        succeeded=True,
        db_path=DEFAULT_DB_PATH,
    ):
        raise HTTPException(status_code=503, detail="Webhook receipt finalization failed")
    return {"status": "ignored", "message": f"Event type {event.type} does not require action"}
