#!/usr/bin/env python3
"""Consolidated current-state audit for the current Theme x Layout HTML matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from html_production_renderer import render_production_layout
from verify_html_production_family import FAMILY_LAYOUTS, check_family, section_for


ROOT = Path(__file__).resolve().parents[1]
EDITOR_RE = re.compile(r'<script\s+data-edit-mode-embedded="true">(.*?)</script>', re.DOTALL)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--html-dir", required=True)
    parser.add_argument("--qa-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    matrix = load_json(Path(args.matrix).resolve())
    html_dir = Path(args.html_dir).resolve()
    qa_root = Path(args.qa_root).resolve()
    output = Path(args.output).resolve()
    themes = {item["id"] for item in matrix["themes"]}
    layouts = {item["id"]: item for item in matrix["layouts"]}
    expected_theme_count = len(themes)
    expected_layout_count = len(layouts)
    expected_slides = expected_theme_count * expected_layout_count
    expected_representative_screenshots = 4 * expected_layout_count
    family_union = set().union(*FAMILY_LAYOUTS.values())
    issues: list[dict[str, Any]] = []

    if len(FAMILY_LAYOUTS) != 13:
        issues.append({"issue": "family-count", "actual": len(FAMILY_LAYOUTS), "expected": 13})
    if not layouts:
        issues.append({"issue": "matrix-layout-count", "actual": 0, "expected": "non-zero"})
    if family_union != set(layouts):
        issues.append({
            "issue": "family-layout-coverage",
            "missing": sorted(set(layouts) - family_union),
            "extra": sorted(family_union - set(layouts)),
        })
    duplicate_total = sum(len(items) for items in FAMILY_LAYOUTS.values())
    if duplicate_total != len(family_union):
        issues.append({"issue": "duplicate-family-layout-membership", "memberships": duplicate_total, "unique": len(family_union)})

    for layout_id, layout in layouts.items():
        rendered = render_production_layout(layout)
        if not rendered or 'class="prod-frame' not in rendered:
            issues.append({"layout": layout_id, "issue": "missing-production-renderer"})

    files = sorted(path for path in html_dir.glob("*.html") if path.name != "edit-mode.js")
    if {path.stem for path in files} != themes:
        issues.append({
            "issue": "theme-file-coverage",
            "missing": sorted(themes - {path.stem for path in files}),
            "extra": sorted({path.stem for path in files} - themes),
        })

    source_editor = (ROOT / "src" / "html-editor" / "edit-mode.js").read_text(encoding="utf-8").replace("</script", "<\\/script")
    source_hash = hashlib.sha256(source_editor.encode("utf-8")).hexdigest()
    slide_count = 0
    contract_checks = 0
    for path in files:
        markup = path.read_text(encoding="utf-8")
        if f'data-theme="{path.stem}"' not in markup:
            issues.append({"theme": path.stem, "issue": "theme-identity"})
        section_ids = re.findall(r'<section\b[^>]*data-layout-id="([^"]+)"', markup)
        slide_count += len(section_ids)
        if len(section_ids) != expected_layout_count or set(section_ids) != set(layouts):
            issues.append({"theme": path.stem, "issue": "layout-section-coverage", "count": len(section_ids)})
        editor_matches = EDITOR_RE.findall(markup)
        if len(editor_matches) != 1:
            issues.append({"theme": path.stem, "issue": "embedded-editor-count", "count": len(editor_matches)})
        elif hashlib.sha256(editor_matches[0].encode("utf-8")).hexdigest() != source_hash:
            issues.append({"theme": path.stem, "issue": "embedded-editor-hash"})
        for family, family_layouts in FAMILY_LAYOUTS.items():
            for layout_id in family_layouts:
                section = section_for(markup, layout_id)
                if section is None:
                    issues.append({"theme": path.stem, "family": family, "layout": layout_id, "issue": "missing-layout"})
                    continue
                contract_checks += 1
                for issue in check_family(family, layout_id, section):
                    issues.append({"theme": path.stem, "family": family, "layout": layout_id, "issue": issue})

    qa_files = 0
    for family in sorted(FAMILY_LAYOUTS):
        family_dir = qa_root / family
        for name in ("summary.json", "all-themes.json", "contrast.json", "editor-hash.json"):
            path = family_dir / name
            qa_files += 1
            if not path.exists():
                issues.append({"family": family, "issue": "missing-qa-file", "file": name})
                continue
            if not load_json(path).get("pass"):
                issues.append({"family": family, "issue": "qa-not-pass", "file": name})
        if not (family_dir / "report.md").exists():
            issues.append({"family": family, "issue": "missing-qa-report"})

    machine_pass = (
        not issues
        and len(files) == expected_theme_count
        and slide_count == expected_slides
        and contract_checks == expected_slides
    )
    visual_issues: list[dict[str, Any]] = []
    visual_report_path = qa_root / "browser-visual-regression.json"
    visual_report: dict[str, Any] = {}
    if not visual_report_path.exists():
        visual_issues.append({"issue": "missing-browser-visual-regression", "path": str(visual_report_path)})
    else:
        visual_report = load_json(visual_report_path)
        expected_representatives = {
            "clinical-report",
            "dark-circuit",
            "brand-editorial",
            "product-strategy-signal",
        }
        theme_rows = visual_report.get("themes", [])
        screenshot_evidence = visual_report.get("screenshotEvidence", {})
        human_review = visual_report.get("representativeHumanReview", {})
        frame_checks = visual_report.get("editorFrameChecks", [])
        if not visual_report.get("pass"):
            visual_issues.append({"issue": "browser-visual-regression-not-pass"})
        if theme_rows and (len(theme_rows) != expected_theme_count or any(
            not row.get("pass")
            or row.get("slides") != expected_layout_count
            or row.get("uniqueLayouts") != expected_layout_count
            for row in theme_rows
        )):
            visual_issues.append({"issue": "browser-theme-layout-coverage", "themes": len(theme_rows)})
        if visual_report.get("slides") != expected_slides or visual_report.get("issues"):
            visual_issues.append({
                "issue": "browser-slide-regression",
                "slides": visual_report.get("slides"),
                "issue_groups": len(visual_report.get("issues", [])),
            })
        screenshot_report_count = screenshot_evidence.get("count", visual_report.get("slides"))
        if screenshot_report_count != expected_slides:
            visual_issues.append({"issue": "browser-screenshot-report-count", "count": screenshot_report_count})
        manifest_path = qa_root / "browser-visual-regression-manifest.jsonl"
        manifest_rows: list[dict[str, Any]] = []
        if manifest_path.exists():
            manifest_rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        manifest_header = manifest_rows[0] if manifest_rows else {}
        screenshot_rows = [row for row in manifest_rows[1:] if row.get("type") == "screenshot"]
        manifest_theme_counts: dict[str, int] = {}
        for row in screenshot_rows:
            theme = str(row.get("theme", ""))
            manifest_theme_counts[theme] = manifest_theme_counts.get(theme, 0) + 1
        valid_hash_rows = all(
            isinstance(row.get("bytes"), int)
            and row.get("bytes", 0) > 0
            and re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256", "")))
            for row in screenshot_rows
        )
        if (
            manifest_header.get("type") != "manifest"
            or not manifest_header.get("pass")
            or len(screenshot_rows) != expected_slides
            or len(manifest_theme_counts) != expected_theme_count
            or any(count != expected_layout_count for count in manifest_theme_counts.values())
            or not valid_hash_rows
        ):
            visual_issues.append({
                "issue": "browser-screenshot-manifest",
                "rows": len(screenshot_rows),
                "themes": len(manifest_theme_counts),
                "valid_hash_rows": valid_hash_rows,
            })
        reviewed_themes = set(human_review.get("themes", []))
        if (
            human_review.get("status") != "pass"
            or reviewed_themes != expected_representatives
            or human_review.get("screenshots") != expected_representative_screenshots
            or human_review.get("contactSheets") != 36
        ):
            visual_issues.append({
                "issue": "representative-human-review",
                "status": human_review.get("status"),
                "themes": sorted(reviewed_themes),
            })
        contact_sheet_root = qa_root / "visual-contact-sheets"
        if len(list(contact_sheet_root.glob("*/*.jpg"))) != 36:
            visual_issues.append({"issue": "representative-contact-sheet-files"})
        if len(frame_checks) != 4 or any(not item.get("pass") or item.get("maxDelta", 999) >= 1 for item in frame_checks):
            visual_issues.append({"issue": "editor-frame-checks", "checks": len(frame_checks)})
        frame_sample_root = qa_root / "editor-frame-samples"
        missing_frame_samples = sorted(
            theme for theme in expected_representatives
            if not (frame_sample_root / f"{theme}-chapter-number-ghost.jpg").exists()
        )
        if missing_frame_samples:
            visual_issues.append({"issue": "editor-frame-sample-files", "missing": missing_frame_samples})

    visual_pass = not visual_issues
    report = {
        "themes": len(themes),
        "layouts": len(layouts),
        "families": len(FAMILY_LAYOUTS),
        "rendered_catalogs": len(files),
        "slides": slide_count,
        "current_contract_checks": contract_checks,
        "qa_json_files_checked": qa_files,
        "machine_pass": machine_pass,
        "visual_gate": {
            "status": "pass" if visual_pass else "fail",
            "report": str(visual_report_path.relative_to(ROOT)).replace("\\", "/"),
            "screenshots": visual_report.get("screenshotEvidence", {}).get("count", visual_report.get("slides", 0)),
            "representative_contact_sheets": visual_report.get("representativeHumanReview", {}).get("contactSheets", 0),
            "editor_frame_checks": len(visual_report.get("editorFrameChecks", [])),
            "issues": visual_issues,
        },
        "production_complete": machine_pass and visual_pass,
        "issues": issues,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["production_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
