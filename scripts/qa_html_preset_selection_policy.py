#!/usr/bin/env python3
"""Regression QA for HTML Preset publication and auto-selection compatibility."""

from __future__ import annotations

import json

from html_preset_registry import load_preset_registry, selection_publication_issues


def main() -> int:
    valid_issues = selection_publication_issues(
        [
            {"id": "published-preset", "gallery_status": "published"},
            {"id": "draft-preset", "gallery_status": "draft"},
        ],
        {
            "published-preset": {"auto_select": True},
            "draft-preset": {"auto_select": False},
        },
    )
    invalid_issues = selection_publication_issues(
        [{"id": "draft-preset", "gallery_status": "draft"}],
        {"draft-preset": {"auto_select": True}},
    )
    registry = load_preset_registry(check_gallery=False)
    passed = not valid_issues and invalid_issues == [
        "draft-preset: auto-selectable reusable Preset must be published"
    ]
    report = {
        "valid_case_issues": valid_issues,
        "invalid_case_issues": invalid_issues,
        "registry_counts": registry["counts"],
        "pass": passed,
    }
    print(json.dumps(report, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
