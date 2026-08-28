#!/usr/bin/env python3
"""Migrate renderer-authored CSS to the 36px typography contract.

This is a source migration, not a runtime clamp.  It preserves larger type,
raises body/caption roles to 36px, and raises title-like selectors to at least
42px so module hierarchy remains visible after the migration.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


BODY_MIN_PX = 36.0
MODULE_TITLE_MIN_PX = 42.0
PAGE_TITLE_MIN_PX = 52.0

_RULE_RE = re.compile(r"(?P<selector>[^{}]+)\{(?P<body>[^{}]*)\}")
_FONT_SIZE_RE = re.compile(
    r"(?P<prefix>\bfont-size\s*:\s*)(?P<size>\d+(?:\.\d+)?)(?P<unit>px)",
    re.IGNORECASE,
)
_FONT_SHORTHAND_RE = re.compile(
    r"(?P<prefix>\bfont\s*:[^;{}]*?)(?P<size>\d+(?:\.\d+)?)(?P<unit>px)",
    re.IGNORECASE,
)

_PAGE_TITLE_RE = re.compile(
    r"(?:prod-title|cover-(?![^,{]*subtitle)[-\w]*-title|"
    r"statement-(?:center-headline|focus-quote)|chapter[-\w]*-title|"
    r"closing-title|toc-image-title)",
    re.IGNORECASE,
)
_MODULE_TITLE_RE = re.compile(
    r"(?:[>\s]\s*b(?:\b|[.:#\[])|[-_.](?:title|name)(?:\b|[-_.:#\[])|"
    r"module-title|compare-kicker|split-label|metric-card-label|"
    r"metric-stat-label|swot-label|price-name)",
    re.IGNORECASE,
)


def selector_floor(selector: str) -> float:
    if ">" not in selector and _PAGE_TITLE_RE.search(selector):
        return PAGE_TITLE_MIN_PX
    if _MODULE_TITLE_RE.search(selector):
        return MODULE_TITLE_MIN_PX
    return BODY_MIN_PX


def _format_px(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:g}"


def migrate_text(text: str) -> tuple[str, list[dict[str, object]]]:
    changes: list[dict[str, object]] = []

    def migrate_rule(match: re.Match[str]) -> str:
        selector = match.group("selector")
        body = match.group("body")
        if "font" not in body.lower():
            return match.group(0)
        floor = selector_floor(selector)

        def clamp(font_match: re.Match[str]) -> str:
            size = float(font_match.group("size"))
            if size >= floor:
                return font_match.group(0)
            changes.append(
                {
                    "selector": " ".join(selector.split())[-240:],
                    "from_px": size,
                    "to_px": floor,
                }
            )
            return (
                f"{font_match.group('prefix')}{_format_px(floor)}"
                f"{font_match.group('unit')}"
            )

        body = _FONT_SIZE_RE.sub(clamp, body)
        body = _FONT_SHORTHAND_RE.sub(clamp, body)
        return f"{selector}{{{body}}}"

    return _RULE_RE.sub(migrate_rule, text), changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output-dir")
    parser.add_argument("--report")
    args = parser.parse_args()

    report = {"mode": "write" if args.write else "check", "files": [], "changes": 0}
    for raw in args.files:
        path = Path(raw)
        original = path.read_text(encoding="utf-8")
        migrated, changes = migrate_text(original)
        output_path = path
        if args.output_dir:
            output_path = Path(args.output_dir) / path.name
        if args.write and migrated != original:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(migrated, encoding="utf-8", newline="\n")
        report["files"].append(
            {
                "path": path.as_posix(),
                "output": output_path.as_posix(),
                "changes": len(changes),
                "details": changes,
            }
        )
        report["changes"] += len(changes)
    if args.report:
        output = Path(args.report)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
