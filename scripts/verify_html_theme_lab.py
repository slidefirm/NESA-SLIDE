#!/usr/bin/env python3
"""Verify the formal HTML Theme Lab from design archive through deploy artifacts."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from html_theme_lab_catalog import load_catalog  # noqa: E402
ARCHIVE = ROOT / "artifacts" / "theme-demos" / "html-theme-lab" / "theme-lab-archive.json"
QA_ROOT = ROOT / "artifacts" / "theme-demos" / "html-theme-lab" / "qa"
DEPLOY = ROOT / "artifacts" / "renderer-cases-deploy"
DEPLOY_MANIFEST = DEPLOY / "manifest.json"
PUBLIC_DEPLOY = ROOT / "artifacts" / "deploy" / "theme-html-lab"
SUBPAGE = PUBLIC_DEPLOY / "index.html"
REPORT = QA_ROOT / "theme-lab-verification.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slide_layout_ids(html: str) -> list[str]:
    """Return layout ids from real slide sections, excluding CSS selectors."""
    ids: list[str] = []
    for tag in re.findall(r"<section\b[^>]*>", html, flags=re.IGNORECASE):
        class_match = re.search(r'class="([^"]*)"', tag, flags=re.IGNORECASE)
        if not class_match or "slide" not in class_match.group(1).split():
            continue
        layout_match = re.search(r'data-layout-id="([^"]+)"', tag, flags=re.IGNORECASE)
        if layout_match:
            ids.append(layout_match.group(1))
    return ids


def main() -> None:
    failures: list[str] = []
    catalog = load_catalog()
    archive = json.loads(ARCHIVE.read_text(encoding="utf-8"))
    deployed = json.loads(DEPLOY_MANIFEST.read_text(encoding="utf-8"))
    editor = json.loads((QA_ROOT / "editor-sync.json").read_text(encoding="utf-8"))
    browser = json.loads((QA_ROOT / "capture-report.json").read_text(encoding="utf-8"))
    visual = json.loads((QA_ROOT / "visual-review.json").read_text(encoding="utf-8"))
    selection_capabilities = json.loads(
        (QA_ROOT / "selection-capabilities.json").read_text(encoding="utf-8")
    )
    selection_above = json.loads(
        (QA_ROOT / "selection-controls-above.json").read_text(encoding="utf-8")
    )
    selection_below = json.loads(
        (QA_ROOT / "selection-controls-below.json").read_text(encoding="utf-8")
    )

    theme_rows = catalog["themes"]
    theme_ids = [row["theme_id"] for row in theme_rows]
    public_theme_ids = [row["theme_id"] for row in theme_rows if row.get("publish", True)]
    unpublished_theme_ids = [row["theme_id"] for row in theme_rows if not row.get("publish", True)]
    expected_themes = len(theme_ids)
    expected_public_themes = len(public_theme_ids)
    expected_slide_counts = {row["theme_id"]: len(row["slides"]) for row in theme_rows}
    expected_slides = sum(expected_slide_counts.values())
    expected_public_slides = sum(expected_slide_counts[theme_id] for theme_id in public_theme_ids)
    archive_by_id = {row["theme_id"]: row for row in archive["themes"]}
    deployed_by_id = {
        row["theme_id"]: row
        for row in deployed["cases"]
        if row.get("group") == "html-theme-lab"
    }
    if expected_themes != 14 or len(set(theme_ids)) != expected_themes:
        failures.append("catalog must contain fourteen unique authored themes")
    if expected_public_themes != 13 or len(set(public_theme_ids)) != expected_public_themes:
        failures.append("catalog must contain thirteen unique public themes")
    if set(archive_by_id) != set(theme_ids):
        failures.append("archive theme ids differ from catalog")
    if set(deployed_by_id) != set(theme_ids):
        failures.append("deployed theme cases differ from catalog")
    for key in (
        "unique_patterns", "unique_materials", "unique_color_block_systems",
        "unique_decoration_sets", "unique_layout_sequences",
        "unique_architecture_sequences", "unique_content_topics",
        "unique_design_dialects", "unique_compositions",
        "unique_assembly_signatures",
    ):
        if archive["counts"].get(key) != expected_themes:
            failures.append(f"archive {key} is not {expected_themes}")

    rows: list[dict] = []
    for theme_id in theme_ids:
        source_row = archive_by_id.get(theme_id, {})
        deployed_row = deployed_by_id.get(theme_id, {})
        source_html = ROOT / source_row.get("source_html", "missing")
        deployed_html = DEPLOY / f"theme-html-lab/{theme_id}/index.html"
        public_html = PUBLIC_DEPLOY / theme_id / "index.html"
        is_public = theme_id in public_theme_ids
        screenshots = sorted((QA_ROOT / "screenshots" / theme_id).glob("slide-*.jpg"))
        contact_sheets = sorted((QA_ROOT / "contact-sheets" / theme_id).glob("contact-*.jpg"))
        html = source_html.read_text(encoding="utf-8") if source_html.is_file() else ""
        layouts = slide_layout_ids(html)
        decisions = source_row.get("design_decisions", [])
        composition_variants = {item.get("composition_variant") for item in decisions}
        header_modes = {item.get("header_mode") for item in decisions}
        surface_modes = {item.get("surface_mode") for item in decisions}
        asset_policy_match = re.search(r'data-asset-policy="([^"]+)"', html)
        asset_policy = asset_policy_match.group(1) if asset_policy_match else ""
        style_text = html.split("<style>", 1)[1].split("</style>", 1)[0] if "<style>" in html else ""
        pattern_only = (
            asset_policy == "pattern-geometry-only"
            and not source_row.get("asset_provenance")
            and "data:image" not in style_text.lower()
            and "background-image:url(" not in style_text.lower()
        )
        row = {
            "theme_id": theme_id,
            "source_html": source_html.is_file(),
            "deployed_html": deployed_html.is_file(),
            "hash_match": source_html.is_file() and deployed_html.is_file() and sha256(source_html) == sha256(deployed_html),
            "published": is_public,
            "public_html": public_html.is_file(),
            "public_hash_match": (
                source_html.is_file()
                and public_html.is_file()
                and sha256(source_html) == sha256(public_html)
            ) if is_public else not public_html.exists(),
            "slides": len(layouts),
            "layouts_match": layouts == source_row.get("layouts") == deployed_row.get("layout_ids"),
            "topic_id": source_row.get("topic", {}).get("id"),
            "architecture": source_row.get("architecture", []),
            "architecture_match": source_row.get("architecture") == deployed_row.get("architecture"),
            "design_dialect": source_row.get("design_dialect"),
            "design_dialect_match": source_row.get("design_dialect") == deployed_row.get("design_dialect"),
            "techniques": source_row.get("techniques", []),
            "assembly": source_row.get("assembly", {}),
            "assembly_match": source_row.get("assembly") == deployed_row.get("assembly"),
            "design_decisions": len(decisions),
            "design_decisions_match": decisions == deployed_row.get("design_decisions", []),
            "composition_variants": len(composition_variants),
            "header_modes": len(header_modes),
            "surface_modes": len(surface_modes),
            "pattern_only": pattern_only,
            "embedded_editor": 'script data-edit-mode-embedded="true"' in html and "window.EditMode" in html,
            "screenshots": len(screenshots),
            "contact_sheets": len(contact_sheets),
        }
        public_design_pass = (
            not is_public
            or (
                row["design_decisions"] == expected_slide_counts[theme_id]
                and row["design_decisions_match"]
                and row["composition_variants"] >= 7
                and row["header_modes"] >= 3
                and row["surface_modes"] >= 3
                and row["pattern_only"]
            )
        )
        row["pass"] = all([
            row["source_html"], row["deployed_html"], row["hash_match"],
            row["slides"] == expected_slide_counts[theme_id], row["layouts_match"], row["architecture_match"],
            row["design_dialect_match"], bool(row["design_dialect"]), len(row["techniques"]) >= 3,
            row["assembly_match"], bool(row["assembly"].get("id")),
            public_design_pass,
            row["embedded_editor"],
            row["public_hash_match"],
            row["screenshots"] == expected_slide_counts[theme_id], row["contact_sheets"] >= 1,
        ])
        if not row["pass"]:
            failures.append(f"{theme_id} source/deploy/QA contract failed")
        rows.append(row)

    subpage = SUBPAGE.read_text(encoding="utf-8") if SUBPAGE.is_file() else ""
    for theme_id in public_theme_ids:
        if theme_id not in subpage:
            failures.append(f"subpage missing {theme_id}")
    for theme_id in unpublished_theme_ids:
        if theme_id in subpage:
            failures.append(f"subpage unexpectedly publishes {theme_id}")
    if "../" not in subpage or "HTML_THEME_LAB" not in subpage:
        failures.append("subpage navigation or payload missing")
    if not editor.get("pass") or editor.get("matched") != expected_themes:
        failures.append("embedded editor sync failed")
    if browser.get("files") != expected_themes or browser.get("slides") != expected_slides:
        failures.append("browser screenshot coverage is incomplete")
    if browser.get("issues"):
        failures.append(f"browser QA contains {len(browser['issues'])} unwaived issue pages")
    if not visual.get("pass") or visual.get("summary", {}).get("reviewed_slides") != expected_slides:
        failures.append("manual contact-sheet review is incomplete")
    required_selection_checks = {
        "textSelectionUsable",
        "visualSelectionHonest",
        "visualObjectActionUsable",
        "compositeSelectionHonest",
        "compositeTextLayerUsable",
    }
    if not selection_capabilities.get("pass") or not required_selection_checks.issubset(
        {key for key, value in selection_capabilities.get("checks", {}).items() if value}
    ):
        failures.append("selection capability QA failed")
    if (
        not selection_above.get("pass")
        or selection_above.get("before", {}).get("badgeRelation", {}).get("placement") != "above"
        or not selection_above.get("checks", {}).get("selectionAnchoredPanel")
    ):
        failures.append("selection panel above-placement QA failed")
    if (
        not selection_below.get("pass")
        or selection_below.get("before", {}).get("badgeRelation", {}).get("placement") != "below"
        or not selection_below.get("checks", {}).get("selectionAnchoredPanel")
    ):
        failures.append("selection panel below-placement QA failed")
    if archive["counts"].get("unique_techniques", 0) < 20:
        failures.append("archive unique_techniques is below 20")

    report = {
        "requirements": {
            "themes": expected_themes,
            "slides": expected_slides,
            "public_themes": expected_public_themes,
            "public_slides": expected_public_slides,
            "unique_patterns": expected_themes,
            "unique_materials": expected_themes,
            "unique_color_block_systems": expected_themes,
            "unique_decoration_sets": expected_themes,
            "unique_layout_sequences": expected_themes,
            "unique_architecture_sequences": expected_themes,
            "unique_content_topics": expected_themes,
            "unique_design_dialects": expected_themes,
            "unique_compositions": expected_themes,
            "unique_assembly_signatures": expected_themes,
            "minimum_unique_techniques": 20,
        },
        "automated_browser_warnings": len(browser.get("issues", [])),
        "visual_review_pass": visual.get("pass", False),
        "editor_sync_pass": editor.get("pass", False),
        "selection_capability_pass": selection_capabilities.get("pass", False),
        "selection_panel_above_pass": selection_above.get("pass", False),
        "selection_panel_below_pass": selection_below.get("pass", False),
        "subpage": SUBPAGE.relative_to(ROOT).as_posix(),
        "results": rows,
        "failures": failures,
        "pass": not failures and all(row["pass"] for row in rows),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
