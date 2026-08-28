#!/usr/bin/env python3
"""Load the accepted HTML Theme Lab plus authored extension packs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from html_preset_registry import load_preset_registry
except ModuleNotFoundError:  # package-style imports used by tests and notebooks
    from .html_preset_registry import load_preset_registry


ROOT = Path(__file__).resolve().parents[1]
BASE_CATALOG = ROOT / "prompt_system" / "demos" / "html-theme-lab.json"
EXTENSION_CATALOG = ROOT / "prompt_system" / "demos" / "html-theme-lab-extensions.json"


def load_catalog(
    base_path: Path = BASE_CATALOG,
    extension_path: Path | None = EXTENSION_CATALOG,
) -> dict[str, Any]:
    """Return one normalized catalog without hiding each Theme's source file."""
    registry_by_id: dict[str, dict[str, Any]] = {}
    if (
        base_path.resolve() == BASE_CATALOG.resolve()
        and extension_path
        and extension_path.resolve() == EXTENSION_CATALOG.resolve()
    ):
        registry_by_id = load_preset_registry(check_gallery=False)["by_id"]

    def normalize(row: dict[str, Any], source: Path) -> dict[str, Any]:
        normalized = {**row, "_content_source": source.relative_to(ROOT).as_posix()}
        registry_row = registry_by_id.get(row["theme_id"])
        if registry_row:
            normalized["display_name"] = registry_row["display_name"]
            normalized["publish"] = registry_row["gallery_status"] == "published"
            normalized["_preset_capabilities"] = list(registry_row["capabilities"])
        return normalized

    base = json.loads(base_path.read_text(encoding="utf-8"))
    themes: list[dict[str, Any]] = []
    for row in base.get("themes", []):
        themes.append(normalize(row, base_path))

    extension: dict[str, Any] = {}
    if extension_path and extension_path.is_file():
        extension = json.loads(extension_path.read_text(encoding="utf-8"))
        for row in extension.get("themes", []):
            themes.append(normalize(row, extension_path))

    return {
        **base,
        "version": max(int(base.get("version", 1)), int(extension.get("version", 1))),
        "id": "html-theme-lab-content-first-20260722",
        "title": "HTML Theme Lab：十四種內容先行的設計系統",
        "description": (
            "保留三份已驗收的內容先行 Theme，再加入十一份不同主題、敘事架構、"
            "字重階層、背景 pattern 與視覺語法的純 HTML deck。"
        ),
        "themes": sorted(themes, key=lambda row: row["order"]),
    }
