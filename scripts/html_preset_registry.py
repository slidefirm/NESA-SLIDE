#!/usr/bin/env python3
"""Load and validate the single HTML PRESET identity/publication registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "prompt_system" / "presets" / "catalog.yaml"
REUSABLE_PRESET_SOURCE = ROOT / "prompt_system" / "renderers" / "html" / "preset-themes.yaml"
THEME_LAB_SOURCES = (
    ROOT / "prompt_system" / "demos" / "html-theme-lab.json",
    ROOT / "prompt_system" / "demos" / "html-theme-lab-extensions.json",
)
DEFAULT_GALLERY = ROOT / "artifacts" / "deploy" / "themes-gallery.js"
CAPABILITIES = {"theme-lab-case", "reusable-preset"}
GALLERY_SOURCES = {"theme-lab", "reusable-preset"}


def _source_inventory() -> tuple[dict[str, dict[str, Any]], set[str], dict[str, str]]:
    preset_data = yaml.safe_load(REUSABLE_PRESET_SOURCE.read_text(encoding="utf-8")) or {}
    reusable_themes = preset_data.get("themes") or {}
    if not isinstance(reusable_themes, dict):
        raise ValueError("HTML reusable Preset themes must be an object")
    lab_ids: set[str] = set()
    lab_source_by_id: dict[str, str] = {}
    for source in THEME_LAB_SOURCES:
        data = json.loads(source.read_text(encoding="utf-8"))
        for row in data.get("themes", []):
            theme_id = row.get("theme_id")
            if theme_id in lab_ids:
                raise ValueError(f"Duplicate Theme Lab id: {theme_id}")
            if "publish" in row:
                raise ValueError(
                    f"{theme_id}: publication belongs in {DEFAULT_REGISTRY.relative_to(ROOT)}, "
                    f"not {source.relative_to(ROOT)}"
                )
            lab_ids.add(theme_id)
            lab_source_by_id[theme_id] = source.relative_to(ROOT).as_posix()
    return reusable_themes, lab_ids, lab_source_by_id


def selection_publication_issues(
    entries: list[dict[str, Any]],
    reusable_themes: dict[str, dict[str, Any]],
) -> list[str]:
    """Keep automatic selection inside the published, curated Preset pool."""

    status_by_id = {
        str(row.get("id", "")).strip(): row.get("gallery_status")
        for row in entries
        if isinstance(row, dict)
    }
    issues: list[str] = []
    for theme_id, theme in reusable_themes.items():
        if not isinstance(theme, dict):
            continue
        auto_select = theme.get("auto_select")
        if not isinstance(auto_select, bool):
            issues.append(f"{theme_id}: auto_select must be true or false")
        elif auto_select and status_by_id.get(theme_id) != "published":
            issues.append(f"{theme_id}: auto-selectable reusable Preset must be published")
    return issues


def published_entries(registry: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        (row for row in registry["entries"] if row["gallery_status"] == "published"),
        key=lambda row: row["gallery_order"],
    )


def load_preset_registry(
    path: Path = DEFAULT_REGISTRY,
    *,
    check_gallery: bool = False,
    gallery_path: Path = DEFAULT_GALLERY,
) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = data.get("entries") or []
    issues: list[str] = []
    if not isinstance(entries, list) or not entries:
        raise ValueError("HTML Preset registry entries must be a non-empty list")

    reusable_themes, lab_source_ids, lab_source_by_id = _source_inventory()
    reusable_source_ids = set(reusable_themes)
    issues.extend(selection_publication_issues(entries, reusable_themes))
    known_source_ids = reusable_source_ids | lab_source_ids
    by_id: dict[str, dict[str, Any]] = {}
    display_names: set[str] = set()
    reusable_registry_ids: set[str] = set()
    lab_registry_ids: set[str] = set()

    for row in entries:
        if not isinstance(row, dict):
            issues.append("every registry entry must be an object")
            continue
        theme_id = str(row.get("id", "")).strip()
        display_name = str(row.get("display_name", "")).strip()
        if not theme_id:
            issues.append("entry id is required")
            continue
        if theme_id in by_id:
            issues.append(f"{theme_id}: duplicate registry id")
            continue
        by_id[theme_id] = row
        if not display_name:
            issues.append(f"{theme_id}: display_name is required")
        elif display_name in display_names:
            issues.append(f"{theme_id}: duplicate display_name {display_name}")
        display_names.add(display_name)

        capabilities = set(row.get("capabilities") or [])
        unknown_capabilities = capabilities - CAPABILITIES
        if not capabilities or unknown_capabilities:
            issues.append(f"{theme_id}: invalid capabilities {sorted(capabilities)}")
        if "reusable-preset" in capabilities:
            reusable_registry_ids.add(theme_id)
        if "theme-lab-case" in capabilities:
            lab_registry_ids.add(theme_id)

        refs = list(row.get("source_refs") or [])
        for ref in refs:
            source_path, _, fragment = str(ref).partition("#")
            if not (ROOT / source_path).is_file():
                issues.append(f"{theme_id}: missing source_ref {source_path}")
            if fragment and not fragment.endswith(theme_id):
                issues.append(f"{theme_id}: source_ref fragment points to another id: {ref}")
        if "reusable-preset" in capabilities:
            expected = f"prompt_system/renderers/html/preset-themes.yaml#themes.{theme_id}"
            if expected not in refs:
                issues.append(f"{theme_id}: reusable-preset source_ref missing")
        if "theme-lab-case" in capabilities:
            expected_source = lab_source_by_id.get(theme_id)
            expected = f"{expected_source}#themes.{theme_id}" if expected_source else ""
            if not expected or expected not in refs:
                issues.append(f"{theme_id}: Theme Lab source_ref missing")

        status = row.get("gallery_status")
        if status == "published":
            order = row.get("gallery_order")
            gallery_source = row.get("gallery_source")
            if not isinstance(order, int) or order < 1:
                issues.append(f"{theme_id}: published entry requires a positive gallery_order")
            if gallery_source not in GALLERY_SOURCES:
                issues.append(f"{theme_id}: invalid gallery_source {gallery_source}")
            if gallery_source == "theme-lab" and "theme-lab-case" not in capabilities:
                issues.append(f"{theme_id}: theme-lab gallery source lacks theme-lab-case capability")
            if gallery_source == "reusable-preset" and "reusable-preset" not in capabilities:
                issues.append(f"{theme_id}: reusable gallery source lacks reusable-preset capability")
            gallery_artifact = str(row.get("gallery_html_artifact", "")).strip()
            gallery_url = str(row.get("gallery_html_url", "")).strip()
            if bool(gallery_artifact) != bool(gallery_url):
                issues.append(f"{theme_id}: gallery_html_artifact and gallery_html_url must be paired")
            if gallery_artifact and not (ROOT / gallery_artifact).is_file():
                issues.append(f"{theme_id}: missing active Gallery HTML artifact {gallery_artifact}")
        elif status == "draft":
            if "gallery_order" in row or "gallery_source" in row:
                issues.append(f"{theme_id}: draft entry cannot reserve Gallery placement")
            if not str(row.get("reason", "")).strip():
                issues.append(f"{theme_id}: draft entry requires a reason")
            if "gallery_html_artifact" in row or "gallery_html_url" in row:
                issues.append(f"{theme_id}: draft entry cannot expose a Gallery HTML artifact")
        else:
            issues.append(f"{theme_id}: gallery_status must be published or draft")

    registry_ids = set(by_id)
    if registry_ids != known_source_ids:
        issues.append(
            "registry/source id mismatch: "
            f"missing={sorted(known_source_ids - registry_ids)} extra={sorted(registry_ids - known_source_ids)}"
        )
    if reusable_registry_ids != reusable_source_ids:
        issues.append(
            "reusable-preset capability mismatch: "
            f"missing={sorted(reusable_source_ids - reusable_registry_ids)} "
            f"extra={sorted(reusable_registry_ids - reusable_source_ids)}"
        )
    if lab_registry_ids != lab_source_ids:
        issues.append(
            "theme-lab-case capability mismatch: "
            f"missing={sorted(lab_source_ids - lab_registry_ids)} extra={sorted(lab_registry_ids - lab_source_ids)}"
        )

    published = [row for row in entries if row.get("gallery_status") == "published"]
    expected_count = int((data.get("publication_policy") or {}).get("accepted_gallery_count", 0))
    if len(published) != expected_count:
        issues.append(f"published count is {len(published)}, expected {expected_count}")
    orders = sorted(row.get("gallery_order") for row in published if isinstance(row.get("gallery_order"), int))
    if orders != list(range(1, len(published) + 1)):
        issues.append(f"published gallery_order must be continuous from 1: {orders}")

    if issues:
        raise ValueError("HTML Preset registry invalid: " + "; ".join(issues))

    data["by_id"] = by_id
    data["counts"] = {
        "entries": len(entries),
        "published": len(published),
        "draft": len(entries) - len(published),
        "reusable_presets": len(reusable_registry_ids),
        "theme_lab_cases": len(lab_registry_ids),
    }
    if check_gallery:
        verify_gallery(data, gallery_path)
    return data


def verify_gallery(registry: dict[str, Any], gallery_path: Path = DEFAULT_GALLERY) -> None:
    raw = gallery_path.read_text(encoding="utf-8").strip()
    prefix = "window.THEME_GALLERY = "
    if not raw.startswith(prefix) or not raw.endswith(";"):
        raise ValueError(f"Unexpected Theme Gallery wrapper: {gallery_path}")
    rows = json.loads(raw[len(prefix) : -1])
    actual = [row for row in rows if row.get("theme_kind") == "html-preset"]
    expected = published_entries(registry)
    actual_ids = [row.get("id") for row in actual]
    expected_ids = [row["id"] for row in expected]
    if actual_ids != expected_ids:
        raise ValueError(f"Theme Gallery PRESET order mismatch: actual={actual_ids} expected={expected_ids}")
    actual_names = [row.get("display_name") for row in actual]
    expected_names = [row["display_name"] for row in expected]
    if actual_names != expected_names:
        raise ValueError(
            f"Theme Gallery PRESET names mismatch: actual={actual_names} expected={expected_names}"
        )
    missing_links = [row.get("id") for row in actual if not str(row.get("html_url", "")).strip()]
    if missing_links:
        raise ValueError(f"Theme Gallery PRESET HTML links missing: {missing_links}")
    for row in actual:
        theme_id = row.get("id")
        expected_url = f"/theme-html-lab/{theme_id}/"
        if row.get("html_url") != expected_url:
            raise ValueError(
                f"{theme_id}: Theme Gallery PRESET HTML URL must be {expected_url}, "
                f"got {row.get('html_url')}"
            )
        deployed_html = ROOT / "artifacts" / "deploy" / "theme-html-lab" / str(theme_id) / "index.html"
        if not deployed_html.is_file():
            raise ValueError(f"{theme_id}: missing deployed Gallery HTML {deployed_html.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--gallery", type=Path, default=DEFAULT_GALLERY)
    parser.add_argument("--skip-gallery", action="store_true")
    args = parser.parse_args()
    data = load_preset_registry(
        args.registry.resolve(),
        check_gallery=not args.skip_gallery,
        gallery_path=args.gallery.resolve(),
    )
    print(json.dumps({"id": data["id"], **data["counts"], "pass": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
