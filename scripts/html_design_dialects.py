#!/usr/bin/env python3
"""Load and validate renderer-scoped HTML design dialects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIALECTS = ROOT / "prompt_system" / "renderers" / "html" / "design-dialects.yaml"


def load_html_design_dialects(path: Path = DEFAULT_DIALECTS) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    dialects = data.get("dialects") or {}
    issues: list[str] = []
    ids: list[str] = []
    compositions: list[str] = []
    for theme_id, row in dialects.items():
        if not isinstance(row, dict):
            issues.append(f"{theme_id}: dialect must be an object")
            continue
        dialect_id = str(row.get("id", "")).strip()
        composition = str(row.get("composition", "")).strip()
        techniques = row.get("techniques") or []
        if not dialect_id:
            issues.append(f"{theme_id}: missing id")
        if not composition:
            issues.append(f"{theme_id}: missing composition")
        if len(techniques) < 3 or len(techniques) != len(set(techniques)):
            issues.append(f"{theme_id}: techniques must contain at least three unique values")
        ids.append(dialect_id)
        compositions.append(composition)
    if len(ids) != len(set(ids)):
        issues.append("dialect ids must be unique")
    if len(compositions) != len(set(compositions)):
        issues.append("dialect compositions must be unique")
    if issues:
        raise ValueError("HTML design dialects invalid: " + "; ".join(issues))
    data["dialects"] = dialects
    data["counts"] = {
        "themes": len(dialects),
        "dialects": len(set(ids)),
        "techniques": len({technique for row in dialects.values() for technique in row["techniques"]}),
    }
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_DIALECTS)
    args = parser.parse_args()
    data = load_html_design_dialects(args.catalog.resolve())
    print(json.dumps({"id": data["id"], **data["counts"], "pass": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
