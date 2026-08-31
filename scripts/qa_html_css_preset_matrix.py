#!/usr/bin/env python3
"""Aggregate the all-Preset HTML CSS ownership regression evidence."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from artifact_report_paths import portable_report_path  # noqa: E402
from html_css_ownership import validate_html_document_text, validate_manifest_data  # noqa: E402
from html_preset_themes import load_html_preset_theme_catalog  # noqa: E402


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--capture-report", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    matrix_dir = args.matrix_dir.resolve()
    capture_path = args.capture_report.resolve()
    expected = set(load_html_preset_theme_catalog()["themes"])
    geometry_paths = {
        path.name.removesuffix(".geometry.json"): path
        for path in matrix_dir.glob("*.geometry.json")
    }
    actual = set(geometry_paths)
    blocking: list[dict[str, Any]] = []
    if missing := sorted(expected - actual):
        blocking.append({"code": "missing-presets", "presets": missing})
    if extra := sorted(actual - expected):
        blocking.append({"code": "unknown-presets", "presets": extra})

    capture = _read_json(capture_path)
    capture_hashes = {
        Path(row["file"]).stem: row.get("sha256")
        for row in capture.get("sources", [])
    }
    geometry_rows: list[dict[str, Any]] = []
    static_issue_count = 0
    for preset_id in sorted(expected & actual):
        html_path = matrix_dir / f"{preset_id}.html"
        manifest_path = matrix_dir / f"{preset_id}.manifest.json"
        geometry = _read_json(geometry_paths[preset_id])
        if not html_path.is_file() or not manifest_path.is_file():
            blocking.append({"code": "missing-artifact", "preset": preset_id})
            continue
        manifest = _read_json(manifest_path)
        markup = html_path.read_text(encoding="utf-8")
        static_issues = validate_html_document_text(
            markup,
            source=portable_report_path(html_path),
            content_mode=str(manifest.get("content_mode")),
        )
        static_issues.extend(validate_manifest_data(manifest, source=portable_report_path(manifest_path)))
        static_issue_count += len(static_issues)
        if static_issues:
            blocking.append({"code": "static-ownership", "preset": preset_id, "issues": static_issues})
        if geometry.get("status") != "pass" or geometry.get("issues"):
            blocking.append({"code": "geometry-invariant", "preset": preset_id, "issues": geometry.get("issues", [])})
        if capture_hashes.get(preset_id) != geometry.get("fileSha256"):
            blocking.append(
                {
                    "code": "evidence-hash-mismatch",
                    "preset": preset_id,
                    "captureSha256": capture_hashes.get(preset_id),
                    "geometrySha256": geometry.get("fileSha256"),
                }
            )
        geometry_rows.append(
            {
                "preset": preset_id,
                "slides": int(geometry.get("slides", 0)),
                "targets": int(geometry.get("targets", 0)),
                "status": geometry.get("status"),
                "fileSha256": geometry.get("fileSha256"),
            }
        )

    visual_slots: Counter[str] = Counter()
    visual_issue_groups = capture.get("issues", [])
    for group in visual_issue_groups:
        visual_slots.update(str(issue.get("slot", "unknown")) for issue in group.get("issues", []))

    payload = {
        "contract": "references/html-css-ownership-contract.md",
        "matrixDir": portable_report_path(matrix_dir),
        "expectedPresets": len(expected),
        "testedPresets": len(geometry_rows),
        "slides": sum(row["slides"] for row in geometry_rows),
        "targets": sum(row["targets"] for row in geometry_rows),
        "staticOwnershipIssues": static_issue_count,
        "geometryIssues": sum(1 for row in blocking if row["code"] == "geometry-invariant"),
        "evidenceHashMismatches": sum(1 for row in blocking if row["code"] == "evidence-hash-mismatch"),
        "cssOwnershipStatus": "pass" if not blocking else "fail",
        "visualQa": {
            "status": "pass" if not visual_issue_groups else "issues-present",
            "issueGroups": len(visual_issue_groups),
            "issueSlots": dict(sorted(visual_slots.items())),
            "report": portable_report_path(capture_path),
        },
        "presets": geometry_rows,
        "blockingIssues": blocking,
    }
    args.report.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.report.resolve().write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not blocking else 1


if __name__ == "__main__":
    raise SystemExit(main())
