#!/usr/bin/env python3
"""Build a compact, hash-backed manifest for HTML browser regression screenshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHOT_RE = re.compile(r"slide-(\d{3})-(.+)\.jpg$")


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-themes", type=int)
    parser.add_argument("--expected-layouts", type=int)
    args = parser.parse_args()

    expected_themes = args.expected_themes
    if expected_themes is None:
        expected_themes = len(list((ROOT / "prompt_system" / "themes").glob("*.yaml")))
    expected_layouts = args.expected_layouts
    if expected_layouts is None:
        expected_layouts = len(list((ROOT / "prompt_system" / "layouts").glob("*.yaml")))
    if expected_themes <= 0 or expected_layouts <= 0:
        parser.error("expected theme and layout counts must both be positive")

    screenshot_root = Path(args.root).resolve()
    output = Path(args.output).resolve()
    if not screenshot_root.is_dir():
        parser.error(f"screenshot root does not exist or is not a directory: {screenshot_root}")
    try:
        screenshot_root.relative_to(ROOT)
    except ValueError:
        parser.error(f"screenshot root must be inside the project: {ROOT}")
    rows: list[dict[str, object]] = []
    issues: list[dict[str, object]] = []

    for path in sorted(screenshot_root.glob("*/*.jpg")):
        match = SHOT_RE.fullmatch(path.name)
        if not match:
            issues.append({"issue": "unexpected-filename", "path": str(path)})
            continue
        rows.append({
            "theme": path.parent.name,
            "slide": int(match.group(1)),
            "layout": match.group(2),
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest(path),
        })

    expected_total = expected_themes * expected_layouts
    theme_counts: dict[str, int] = {}
    for row in rows:
        theme = str(row["theme"])
        theme_counts[theme] = theme_counts.get(theme, 0) + 1
    if len(rows) != expected_total:
        issues.append({"issue": "screenshot-count", "actual": len(rows), "expected": expected_total})
    if len(theme_counts) != expected_themes:
        issues.append({"issue": "theme-count", "actual": len(theme_counts), "expected": expected_themes})
    for theme, count in sorted(theme_counts.items()):
        if count != expected_layouts:
            issues.append({"issue": "theme-layout-count", "theme": theme, "actual": count, "expected": expected_layouts})

    header = {
        "schemaVersion": "1.0",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "root": screenshot_root.relative_to(ROOT).as_posix(),
        "themes": len(theme_counts),
        "screenshots": len(rows),
        "expected": {"themes": expected_themes, "layoutsPerTheme": expected_layouts, "screenshots": expected_total},
        "issues": issues,
        "pass": not issues,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps({"type": "manifest", **header}, ensure_ascii=False) + "\n")
        for row in rows:
            stream.write(json.dumps({"type": "screenshot", **row}, ensure_ascii=False) + "\n")
    print(json.dumps(header, ensure_ascii=False))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
