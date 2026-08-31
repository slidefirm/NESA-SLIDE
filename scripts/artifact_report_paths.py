#!/usr/bin/env python3
"""Portable path values for tracked artifact manifests and QA reports."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def portable_report_path(value: str | Path) -> str:
    resolved = Path(value).resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix() or "."
    except ValueError:
        return resolved.as_posix()
