"""Gemini-on-Vertex-AI settings shared by every Antigravity agent."""

from __future__ import annotations

import os
from typing import Any


def vertex_enabled() -> bool:
    """True when agents should call Gemini through Vertex AI (Cloud Run, ADC)."""
    return bool(os.environ.get("VERTEX_PROJECT") or os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"))


def llm_kwargs(api_key: str | None = None) -> dict[str, Any]:
    """LocalAgentConfig kwargs selecting Vertex AI (no key) or a Gemini API key."""
    if vertex_enabled():
        return {
            "vertex": True,
            "project": os.environ.get("VERTEX_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT"),
            "location": os.environ.get("VERTEX_LOCATION", "us-central1"),
            "model": os.environ.get("VERTEX_MODEL", "gemini-2.5-flash"),
        }
    return {"api_key": api_key} if api_key else {}
