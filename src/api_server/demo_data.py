"""Sample-data overlay for the public hackathon demo.

Enabled with ``MCP_GC_DEMO_DATA=true``. The public Cloud Run deployment ships without
real Play Console / RevenueCat / GA4 / AdMob credentials, so the read endpoints that
would call those APIs return clearly labelled *sample* data instead of "unavailable".
Every payload carries ``"demo": true`` and a ``demo_sample`` provenance source.
Experiments and the action log are NOT faked here: they come from Firestore.
"""

from __future__ import annotations

import os
import re
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import Request, Response

APPS: dict[str, dict[str, Any]] = {
    "com.finance.loan.emicalculator": {
        "name": "EMI Calculator", "scale": 1.0, "score": 71, "mrr": 1840.0, "ads": 2210.0, "iap": 460.0,
        "rating": 4.6, "reviews": 3120,
    },
    "com.cama.app.huge80sclockPro": {
        "name": "Huge Digital Clock Pro", "scale": 0.7, "score": 64, "mrr": 960.0, "ads": 880.0, "iap": 1210.0,
        "rating": 4.4, "reviews": 1480,
    },
    "com.cama.app.huge80sclock": {
        "name": "Huge Digital Clock", "scale": 0.5, "score": 58, "mrr": 0.0, "ads": 1530.0, "iap": 0.0,
        "rating": 4.2, "reviews": 2290,
    },
}

_STEPS = [
    ("Store listing view to install", 0.264, 0.310, 21000),
    ("Install to first open", 0.910, 0.930, 5540),
    ("Onboarding completed", 0.620, 0.700, 5040),
    ("Paywall viewed to trial start", 0.082, 0.110, 3120),
    ("Trial to paid", 0.310, 0.390, 256),
    ("Day-7 retention", 0.140, 0.190, 5040),
]


def _prov(period: str = "30d") -> dict[str, Any]:
    return {
        "source": "demo_sample",
        "captured_at": datetime.now(UTC).isoformat(),
        "period": period,
        "is_live": False,
    }


def _series(pkg: str, base: float, n: int = 30) -> list[float]:
    seed = sum(ord(c) for c in pkg)
    return [round(base * (0.85 + 0.3 * (((seed + i * 37) % 17) / 16)), 2) for i in range(n)]


def portfolio() -> dict[str, Any]:
    out = []
    for pkg, a in APPS.items():
        total = a["ads"] + a["iap"] + a["mrr"]
        out.append({
            "package_name": pkg, "display_name": a["name"], "funnel_health_score": a["score"],
            "mrr": a["mrr"], "mrr_change_pct": 4.2, "revenue_30d": round(total, 2),
            "profit_30d": round(total * 0.62, 2), "revenue_change_pct": 6.8,
            "ad_revenue_30d": a["ads"], "subscription_revenue_30d": a["mrr"], "iap_revenue_30d": a["iap"],
            "google_ads_spend_30d": round(total * 0.18, 2),
            "installs_7d": [int(v) for v in _series(pkg, 700 * a["scale"], 7)],
            "active_experiments": 1,
            "worst_stage": {"name": _STEPS[3][0], "value": _STEPS[3][1], "benchmark": _STEPS[3][2]},
            "top_opportunity": {
                "id": f"opp-{pkg}", "app_package": pkg, "rank": 1, "impact": round(total * 0.09, 0),
                "impact_unit": "USD/month",
                "freshness": datetime.now(UTC).isoformat(),
                "title": "Raise paywall-to-trial conversion",
                "summary": "Trial start is 2.8pp under the category benchmark; test a 7-day annual trial.",
                "provenance": _prov(),
            },
            "as_of": datetime.now(UTC).isoformat(), "freshness": "sample", "source": "demo_sample",
            "partial": False, "period": "30d", "demo": True,
        })
    return {"apps": out, "demo": True}


def summary() -> dict[str, Any]:
    rows = portfolio()["apps"]
    return {"portfolio_summary": {
        "total_mrr": round(sum(r["mrr"] for r in rows), 2),
        "total_revenue_30d": round(sum(r["revenue_30d"] for r in rows), 2),
        "total_profit_30d": round(sum(r["profit_30d"] for r in rows), 2),
        "total_ad_revenue_30d": round(sum(r["ad_revenue_30d"] for r in rows), 2),
        "active_experiments": 3, "pending_approvals": 1, "trust_tier": "moderate", "demo": True,
    }}


def funnel(pkg: str) -> dict[str, Any]:
    a = APPS[pkg]
    steps = []
    for name, rate, bench, entered in _STEPS:
        entered = int(entered * a["scale"])
        steps.append({
            "name": name, "conversion_rate": rate, "benchmark_rate": bench, "gap": round(bench - rate, 3),
            "users_entered": entered, "users_completed": int(entered * rate),
            "priority": "high" if bench - rate > 0.04 else "medium",
            "insight": f"{name} is {abs(bench - rate) * 100:.1f}pp below the category benchmark.",
            "provenance": _prov(),
        })
    ranked = sorted(steps, key=lambda s: s["gap"], reverse=True)[:3]
    leaks = [{
        "rank": i + 1, "stage": s["name"], "score": round(s["gap"] * 100, 1), "conversion_rate": s["conversion_rate"],
        "benchmark_rate": s["benchmark_rate"], "gap": s["gap"],
        "estimated_monthly_impact": round((a["ads"] + a["iap"] + a["mrr"]) * (0.12 - i * 0.03), 0),
        "insight": s["insight"], "provenance": _prov(),
    } for i, s in enumerate(ranked)]
    return {
        "status": "ok", "app_id": pkg, "period": "30d", "funnel_health_score": a["score"],
        "total_monthly_revenue_impact": sum(x["estimated_monthly_impact"] for x in leaks),
        "leaks": leaks, "ranked_leaks": leaks, "all_steps": steps,
        "data_sources": ["demo_sample"], "unavailable_sources": [],
        "summary": "Sample funnel analysis for the public demo.", "provenance": _prov(), "demo": True,
    }


def revenue(pkg: str) -> dict[str, Any]:
    a = APPS[pkg]
    return {
        "admob": {"ad_revenue_30d": a["ads"]},
        "revenuecat": {"revenue": a["mrr"] + a["iap"], "mrr": a["mrr"], "active_subscriptions": int(a["mrr"] / 4.5)}
        if a["mrr"] else None,
        "gcs_iap": {"iap_revenue_30d": a["iap"]}, "app_store": None, "ga4": None, "google_ads": None, "demo": True,
    }


def storefront(pkg: str) -> dict[str, Any]:
    a = APPS[pkg]
    countries = [("IN", 9200, .291), ("US", 4100, .224), ("ID", 2600, .318), ("BR", 2100, .251), ("GB", 1400, .207)]
    sources = [("Google Play search", 11800, .301), ("Explore", 4300, .198), ("Third-party referrer", 2100, .245),
               ("Web referrer", 1200, .176)]
    mk = lambda rows, key: [  # noqa: E731
        {key: n, "visitors": int(v * a["scale"]), "installs": int(v * a["scale"] * r), "conversion_rate": r}
        for n, v, r in rows
    ]
    return {
        "country": mk(countries, "country"), "traffic_source": mk(sources, "traffic_source"),
        "search_term": [{"search_term": t, "visitors": int(v * a["scale"]), "installs": int(v * a["scale"] * r),
                         "conversion_rate": r} for t, v, r in
                        [("emi calculator", 3900, .33), ("loan calculator", 2100, .29), ("home loan emi", 1300, .27)]],
        "status": "ok", "as_of": datetime.now(UTC).isoformat(), "freshness": "sample", "record_count": 12,
        "provenance": _prov(), "demo": True,
    }


def retention(pkg: str) -> dict[str, Any]:
    today = date.today()
    cohorts = [{"date": (today - timedelta(days=29 - i)).isoformat(), "new_users": int(v * 0.4),
                "returning_users": int(v * 0.6)} for i, v in enumerate(_series(pkg, 520 * APPS[pkg]["scale"]))]
    return {"cohorts": cohorts, "d1": 0.41, "d7": 0.14, "demo": True}


def admob_timeline(pkg: str) -> dict[str, Any]:
    today = date.today()
    vals = _series(pkg, APPS[pkg]["ads"] / 30)
    return {"daily": [{"date": (today - timedelta(days=29 - i)).isoformat(), "revenue": v}
                      for i, v in enumerate(vals)], "demo": True}


def reviews(pkg: str) -> list[dict[str, Any]]:
    return [
        {"author_name": "Priya S.", "star_rating": 5, "rating": 5, "comment": "Fast and accurate, exactly what I needed.",
         "developer_reply": None},
        {"author_name": "Mark T.", "star_rating": 4, "rating": 4, "comment": "Great app, wish the trial was longer.",
         "developer_reply": "Thanks Mark, we are testing a longer trial."},
        {"author_name": "Ravi K.", "star_rating": 2, "rating": 2, "comment": "Paywall appears too early.",
         "developer_reply": None},
    ]


def reviews_analysis(pkg: str) -> dict[str, Any]:
    a = APPS[pkg]
    return {
        "average_rating": a["rating"], "total_reviews": a["reviews"],
        "sentiment": {"positive": 71, "neutral": 17, "negative": 12},
        "keywords": [{"keyword": "paywall", "count": 38, "sentiment": "negative"},
                     {"keyword": "accurate", "count": 112, "sentiment": "positive"},
                     {"keyword": "trial", "count": 29, "sentiment": "neutral"}],
        "stage_correlation": {}, "status": "ok", "provenance": _prov(), "demo": True,
    }


def system_status() -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "status": "ok", "trust_tier": "moderate", "last_prao_cycle": now,
        "services": dict.fromkeys(("analytics", "play_store", "revenuecat", "admob", "aso", "google_ads", "gcs", "funnel_engine", "fcm_push", "journey_map"), "ok"),
        "scheduler": {"state": "running", "heartbeat_at": now, "last_cycle_status": "ok"},
        "latest_snapshot": None, "source_runs": [],
        "capabilities": {"read_only": True, "config_writes": False}, "demo": True,
    }


def listing(pkg: str) -> dict[str, Any]:
    name = APPS[pkg]["name"]
    title = "EMI Calculator - Loan & Home EMI" if "emi" in pkg else f"{name} - Night Clock & Alarm"
    return {
        "status": "ok", "title": title,
        "short_description": "Calculate loan EMI, interest and amortization schedules in seconds.",
        "full_description": (
            f"{name} helps you plan every loan with clarity. Compare tenures, see total interest, and export a full "
            "amortization schedule. Works offline, no sign-up required."
        ),
        "default_language": "en-US", "locale": "en-US", "version": "sample-1",
        "fetched_at": datetime.now(UTC).isoformat(),
        "provenance": {"source": "demo_sample", "live": False, "is_live": False,
                       "retrieved_at": datetime.now(UTC).isoformat(), "captured_at": datetime.now(UTC).isoformat()},
        "demo": True,
    }


def keywords(pkg: str) -> list[dict[str, Any]]:
    rows = [("loan emi", 64, 34.2, 7, 2), ("emi calculator", 65, 50.6, 3, 1), ("loan calculator", 65, 78.3, 18, -1),
            ("finance calculator", 41, 36.0, 11, 4), ("interest calculator", 38, 29.5, 5, 0),
            ("mortgage calculator", 52, 71.0, 24, -3)]
    label = lambda d: "Easy" if d < 30 else "Medium" if d < 55 else "Hard" if d < 75 else "Very Hard"  # noqa: E731
    return [{"keyword": k, "rank": r, "found": True, "volume": v, "difficulty": d, "difficulty_label": label(d),
             "rank_change": c} for k, v, d, r, c in rows]


def _experiment_view(doc: dict[str, Any], detail: bool = False) -> dict[str, Any]:
    """Map a Firestore experiment document onto the dashboard's Experiment shape."""
    status = doc.get("status", "proposed")
    base = doc.get("baseline_value")
    result = doc.get("result_value")
    created = doc.get("created_at") or datetime.now(UTC).isoformat()
    view: dict[str, Any] = {
        "id": doc["id"], "app_package": doc.get("app_package"), "experiment_type": doc.get("experiment_type"),
        "hypothesis": doc.get("hypothesis"), "status": status, "success_metric": doc.get("success_metric"),
        "baseline_value": base, "result_value": result, "confidence": doc.get("confidence"),
        "result_verdict": doc.get("result_verdict"), "autonomy_mode": "recommend_only",
        "effective_autonomy_mode": "recommend_only", "min_observation_days": 7,
        "days_active": 21 if status == "concluded" else 6 if status == "active" else 0,
        "created_at": created, "updated_at": doc.get("updated_at") or created,
        "provenance": {"source": "firestore", "is_live": True, "captured_at": doc.get("updated_at") or created},
        "evidence": [{"label": "Store conversion vs benchmark", "value": "26.4% vs 31.0%", "source": "demo_sample"}],
        "available_actions": [], "action_links": [], "requires_review": status == "proposed",
    }
    if base and result:
        view["change_pct"] = round((result - base) / base * 100, 1)
    if detail:
        if status in ("concluded", "active") and base:
            top = result or base * 1.06
            view["observations"] = [
                {"id": i, "experiment_id": doc["id"], "observed_at": (date.today() - timedelta(days=20 - i * 4)).isoformat(),
                 "metric_value": round(base + (top - base) * i / 5, 4), "source": "demo_sample", "sample_size": 1500 + i * 400}
                for i in range(6 if status == "concluded" else 3)
            ]
        if status == "concluded":
            view["evaluation"] = {
                "verdict": "win", "confidence": doc.get("confidence"), "observed_change": view.get("change_pct"),
                "treatment_rate": result, "observation_days": 21,
                "reason": "Welch t-test on daily conversion: treatment beats baseline with 96% confidence.",
                "evaluated_at": doc.get("updated_at"),
            }
    return view


_APP_ROUTES: dict[str, Callable[[str], Any]] = {
    "funnel": funnel, "revenue": revenue, "storefront": storefront, "retention": retention,
    "admob_timeline": admob_timeline, "reviews": reviews, "keywords": keywords, "reviews/analysis": reviews_analysis,
}
_APP_RE = re.compile(r"^/api/apps/([^/]+)/(funnel|revenue|storefront|retention|admob_timeline|reviews/analysis|reviews|keywords)/?$")


def demo_enabled() -> bool:
    return os.environ.get("MCP_GC_DEMO_DATA", "").strip().lower() in {"1", "true", "yes", "on"}


class DemoDataMiddleware(BaseHTTPMiddleware):
    """Answer selected GET reads with sample data when demo mode is on."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.method != "GET" or not demo_enabled():
            return await call_next(request)
        path = request.url.path.rstrip("/")
        payload: Any = None
        if path == "/api/portfolio":
            payload = portfolio()
        elif path == "/api/portfolio/summary":
            payload = summary()
        elif path == "/api/system/status":
            payload = system_status()
        elif path == "/api/system/safety":
            now = datetime.now(UTC).isoformat()
            payload = {"emergency_brake": "Armed", "crash_rate": 0.42, "crash_threshold": 1.0, "anr_rate": 0.19,
                       "anr_threshold": 0.47, "last_scan": now,
                       "provenance": {"source": "demo_sample", "captured_at": now, "is_live": False}, "demo": True}
        elif path == "/api/experiments" or re.match(r"^/api/experiments/[^/]+$", path):
            from funnel_engine import firestore_store

            rows = firestore_store.list_experiments(request.query_params.get("app"), request.query_params.get("status"))
            if rows is not None:
                if path == "/api/experiments":
                    payload = {"experiments": [_experiment_view(r) for r in rows]}
                else:
                    exp_id = path.rsplit("/", 1)[1]
                    match = next((r for r in rows if r.get("id") == exp_id), None)
                    if match is not None:
                        payload = _experiment_view(match, detail=True)
        else:
            lm = re.match(r"^/api/apps/([^/]+)/listing/[^/]+/?$", request.url.path)
            if lm and lm.group(1) in APPS:
                return JSONResponse(listing(lm.group(1)))
            m = _APP_RE.match(request.url.path)
            if m and m.group(1) in APPS:
                payload = _APP_ROUTES[m.group(2)](m.group(1))
        if payload is None:
            return await call_next(request)
        return JSONResponse(payload)


async def grounded_answer(package: str, question: str) -> str:
    """Real Gemini answer (Antigravity SDK on Vertex AI) grounded in the sample data and live Firestore experiments."""
    import json

    from google.antigravity import Agent, LocalAgentConfig

    from app_manager.vertex import llm_kwargs
    from funnel_engine import firestore_store

    app = APPS.get(package)
    if app is None:
        return "No sample data is available for this app."
    context = {
        "app": app["name"], "package": package, "funnel": funnel(package), "revenue": revenue(package),
        "storefront": storefront(package), "reviews": reviews_analysis(package),
        "experiments": firestore_store.list_experiments(package, None) or [],
    }
    config = LocalAgentConfig(
        system_instructions=(
            "You are the coordinator agent of an app-portfolio copilot. Answer only from the JSON context, "
            "which is sample data for a public demo. Be concise (at most 5 sentences), name the primary bottleneck, "
            "the estimated monthly impact and one recommended experiment. Do not ask follow-up questions and do not "
            "mention missing tools."
        ),
        **llm_kwargs(),
    )
    prompt = f"Context JSON:\n{json.dumps(context, default=str)[:12000]}\n\nQuestion: {question}"
    chunks: list[str] = []
    async with Agent(config) as agent:
        response = await agent.chat(prompt)
        async for chunk in response:
            chunks.append(chunk)
    return "".join(chunks).strip()
