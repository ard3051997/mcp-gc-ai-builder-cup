"""Firestore persistence for experiments and the action log.

SQLite stays the local working store for the heavy funnel pipeline. When
``FIRESTORE_PROJECT`` is set (Cloud Run), experiments and the audit log are
also written to Firestore so they survive container restarts, and the
dashboard reads them back from there.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

EXPERIMENTS = "experiments"
ACTIONS = "action_log"

_client: Any = None


def enabled() -> bool:
    return bool(os.environ.get("FIRESTORE_PROJECT"))


def _db() -> Any:
    global _client
    if _client is None:
        from google.cloud import firestore

        _client = firestore.Client(project=os.environ["FIRESTORE_PROJECT"])
    return _client


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def mirror_experiment(exp_id: str, fields: dict[str, Any]) -> None:
    """Create or merge an experiment document. Never raises."""
    if not enabled():
        return
    try:
        doc = {k: v for k, v in fields.items() if v is not None}
        doc["id"] = exp_id
        doc.setdefault("created_at", now_iso())
        doc["updated_at"] = now_iso()
        _db().collection(EXPERIMENTS).document(exp_id).set(doc, merge=True)
    except Exception as exc:
        logger.warning("firestore_experiment_write_failed", exp_id=exp_id, error=str(exc))


def mirror_action(entry: dict[str, Any]) -> None:
    """Append an audit-log document. Never raises."""
    if not enabled():
        return
    try:
        doc = {k: v for k, v in entry.items() if v is not None}
        doc["timestamp"] = now_iso()
        doc["ts_ms"] = int(time.time() * 1000)
        _db().collection(ACTIONS).add(doc)
    except Exception as exc:
        logger.warning("firestore_action_write_failed", error=str(exc))


def list_experiments(app_package: str | None, status: str | None) -> list[dict[str, Any]] | None:
    """Return experiments from Firestore, or None if unavailable."""
    if not enabled():
        return None
    try:
        rows = [d.to_dict() for d in _db().collection(EXPERIMENTS).stream()]
    except Exception as exc:
        logger.warning("firestore_experiment_read_failed", error=str(exc))
        return None
    if app_package:
        rows = [r for r in rows if r.get("app_package") == app_package]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return rows


def list_actions(
    app_package: str | None,
    action_type: str | None,
    experiment_id: str | None,
    limit: int,
) -> list[dict[str, Any]] | None:
    """Return recent actions from Firestore, or None if unavailable."""
    if not enabled():
        return None
    try:
        rows = [d.to_dict() for d in _db().collection(ACTIONS).stream()]
    except Exception as exc:
        logger.warning("firestore_action_read_failed", error=str(exc))
        return None
    for key, val in (
        ("app_package", app_package),
        ("action_type", action_type),
        ("experiment_id", experiment_id),
    ):
        if val:
            rows = [r for r in rows if r.get(key) == val]
    rows.sort(key=lambda r: r.get("ts_ms", 0), reverse=True)
    return rows[:limit]
