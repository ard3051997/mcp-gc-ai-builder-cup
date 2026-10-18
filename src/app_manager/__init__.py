"""App Manager - AI-powered app management orchestration using Google Antigravity SDK."""

from __future__ import annotations


def main() -> None:
    """Run the App Manager CLI. Imports lazily to avoid requiring google-antigravity at import."""
    from app_manager.cli import main as _main

    _main()


__all__ = ["main"]
