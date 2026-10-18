"""Seed clearly-labelled sample experiments and audit-log entries into Firestore.

Usage: FIRESTORE_PROJECT=<project> uv run python scripts/seed_demo_firestore.py
Removes earlier documents tagged created_by == "demo-seed" and smoke-test entries first.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta

from google.cloud import firestore

APP = "com.finance.loan.emicalculator"
db = firestore.Client(project=os.environ["FIRESTORE_PROJECT"])

for coll in ("experiments", "action_log"):
    for d in db.collection(coll).stream():
        row = d.to_dict()
        if row.get("created_by") == "demo-seed" or row.get("action_type") == "smoke_test" or d.id == "smoke-1":
            d.reference.delete()

now = datetime.now(UTC)
experiments = [
    ("demo-exp-1", "aso_metadata", "Shortening the Play title to lead with 'EMI Calculator' lifts store conversion.",
     "store_view_to_install_rate", "concluded", 0.264, 0.301, "win", 0.96, 21),
    ("demo-exp-2", "aso_metadata", "Adding 'loan' and 'interest' to the short description improves search installs.",
     "store_view_to_install_rate", "active", 0.264, None, None, None, 6),
    ("demo-exp-3", "paywall_variant", "A 7-day trial on the annual plan raises trial-to-paid conversion.",
     "trial_to_paid_conversion_rate", "proposed", 0.31, None, None, None, 0),
]
for exp_id, typ, hyp, metric, status, base, res, verdict, conf, days in experiments:
    doc = {
        "id": exp_id, "app_package": APP, "experiment_type": typ, "hypothesis": hyp,
        "success_metric": metric, "status": status, "baseline_value": base,
        "created_by": "demo-seed", "execution_mode": "approval_required",
        "created_at": (now - timedelta(days=days + 2)).isoformat(), "updated_at": now.isoformat(),
    }
    if res is not None:
        doc.update(result_value=res, result_verdict=verdict, confidence=conf)
    db.collection("experiments").document(exp_id).set(doc)

actions = [
    ("proposal_created", "funnel_engine", "Store CVR is 26% vs 31% category benchmark; proposed title test.", "demo-exp-1", 9),
    ("telegram_approval", "approval_gate", "Operator approved the metadata change via Telegram gate.", "demo-exp-1", 8),
    ("experiment_concluded", "experiment_evaluator", "Welch t-test: +3.7pp, p=0.04 -> verdict: win.", "demo-exp-1", 1),
    ("proposal_created", "revenuecat", "Trial-to-paid below benchmark; proposed 7-day annual trial.", "demo-exp-3", 0),
]
for typ, tool, why, exp_id, days_ago in actions:
    ts = now - timedelta(days=days_ago)
    db.collection("action_log").add({
        "app_package": APP, "action_type": typ, "tool_name": tool, "reasoning": why,
        "result": "ok: " + why.split(";")[0].split(".")[0], "safety_decision": "allowed",
        "experiment_id": exp_id, "created_by": "demo-seed",
        "timestamp": ts.isoformat(), "ts_ms": int(ts.timestamp() * 1000) + int(time.time()) % 7,
    })
print("seeded", len(experiments), "experiments and", len(actions), "actions")
