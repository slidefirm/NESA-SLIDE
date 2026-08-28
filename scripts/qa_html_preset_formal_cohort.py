#!/usr/bin/env python3
"""Smoke-test the formal new-deck renderer for the migrated Preset cohort."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts" / "render_randomized_html_demo.py"
OWNERSHIP_QA = ROOT / "scripts" / "html_css_ownership.py"
REGISTRY = ROOT / "prompt_system" / "presets" / "catalog.yaml"
PRESET_THEMES = ROOT / "prompt_system" / "renderers" / "html" / "preset-themes.yaml"
ASSEMBLY = ROOT / "prompt_system" / "renderers" / "html" / "assembly-catalog.yaml"
DESIGN_METHOD = ROOT / "prompt_system" / "renderers" / "html" / "design-method.yaml"

COHORT = (
    "line-argument-journal",
    "field-index-manual",
    "tide-signal-observatory",
    "craft-archive-editions",
    "incident-command-redline",
    "harbor-ribbon-program",
    "neighborhood-newsroom-proof",
    "restoration-blueprint-ledger",
    "brave-classroom-contours",
    "night-transit-wayfinding",
)
IMAGE_BACKGROUND_POLICY = "generated-raster-background-opt-in"
FORBIDDEN_REUSABLE_FIELDS = {
    "source_style_case",
    "example_story",
    "example_layouts",
    "story",
    "layouts",
    "layout_id",
    "content",
    "css",
}
FORBIDDEN_AMBIENT_PATTERN = re.compile(
    r"(?:radial-gradient|repeating-radial-gradient|\bellipse\b|\bcircle\b|"
    r"\borbit\b|\bring\b|\barc\b)",
    re.IGNORECASE,
)
PRESET_STYLE = re.compile(
    r'<style\b[^>]*data-css-owner="preset-appearance"[^>]*>(.*?)</style>',
    re.DOTALL,
)


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _assert_sources() -> dict[str, int]:
    registry = _load_yaml(REGISTRY)
    preset_catalog = _load_yaml(PRESET_THEMES)
    assembly = _load_yaml(ASSEMBLY)
    design_method = _load_yaml(DESIGN_METHOD)
    registry_by_id = {row["id"]: row for row in registry["entries"]}

    assert len(registry_by_id) == 36, len(registry_by_id)
    assert len(preset_catalog["themes"]) == 36, len(preset_catalog["themes"])
    assert len(assembly["recipes"]) == 46, len(assembly["recipes"])
    assert len(design_method["theme_selection_profiles"]) == 46

    for preset_id in COHORT:
        registry_row = registry_by_id[preset_id]
        assert "reusable-preset" in registry_row["capabilities"]
        expected_ref = (
            "prompt_system/renderers/html/preset-themes.yaml#themes."
            f"{preset_id}"
        )
        assert expected_ref in registry_row["source_refs"]

        preset = preset_catalog["themes"][preset_id]
        assert not (FORBIDDEN_REUSABLE_FIELDS & set(preset))
        assert preset["visual_asset_policy"] == IMAGE_BACKGROUND_POLICY
        assert preset["background_pattern"] == "none"
        assert preset["background_graphics"] == "safe-zone-minimal-raster"

        recipe = assembly["recipes"][preset_id]
        assert recipe["background_pattern"] == "none"

        profile = design_method["theme_selection_profiles"][preset_id]
        assert not (FORBIDDEN_REUSABLE_FIELDS & set(profile))
        assert profile["best_for"] and profile["avoid_for"]
        assert profile["signature_compositions"]

    return {
        "registry_entries": len(registry_by_id),
        "reusable_presets": len(preset_catalog["themes"]),
        "assembly_recipes": len(assembly["recipes"]),
        "theme_selection_profiles": len(design_method["theme_selection_profiles"]),
    }


def _assert_help_choices() -> None:
    result = _run([sys.executable, "-B", str(RENDERER), "--help"])
    for preset_id in COHORT:
        assert preset_id in result.stdout, preset_id


def _assert_render(preset_id: str, output: Path, seed: int) -> dict[str, Any]:
    _run(
        [
            sys.executable,
            "-B",
            str(RENDERER),
            "--output",
            str(output),
            "--seed",
            str(seed),
            "--theme",
            preset_id,
            "--story",
            "ai-workflow-adoption",
            "--layouts",
            "cover-center-title-edge-decor",
            "--content-mode",
            "new-deck",
            "--asset-policy",
            "pattern-only",
            "--content-intent",
            "cover",
        ]
    )
    manifest_path = output.with_suffix(".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    html = output.read_text(encoding="utf-8")

    assert manifest["content_mode"] == "new-deck"
    assert manifest["content_intent"] == "cover"
    assert manifest["preset_theme"]["id"] == preset_id
    assert manifest["preset_theme"]["legacy_case_imported"] is False
    assert manifest["preset_theme"]["layout_binding"] == "none"
    assert manifest["preset_theme"]["content_binding"] == "none"
    assert manifest["preset_theme"]["visual_asset_policy"] == IMAGE_BACKGROUND_POLICY
    assert manifest["preset_theme"]["background_pattern"] == "none"
    assert "safe-zone-raster-opt-in" in manifest["preset_theme"]["ambient_design"]
    assert manifest["css_ownership"]["static_validation"] == "pass"
    assert manifest["css_ownership"]["geometry_owner"] == "renderer-base"
    assert manifest["css_ownership"]["appearance_can_mutate_geometry"] is False

    assert f'data-preset-theme="{preset_id}"' in html
    assert 'data-content-mode="new-deck"' in html
    assert 'data-background-profile="none"' in html
    assert 'data-css-owner="legacy-demo-override"' not in html
    style_match = PRESET_STYLE.search(html)
    assert style_match, preset_id
    theme_style_position = html.find('data-css-owner="theme-appearance"')
    assert theme_style_position >= 0
    assert style_match.start() > theme_style_position
    preset_css = style_match.group(1)
    assert "background-image:none" in preset_css
    assert "!important" not in preset_css
    assert not FORBIDDEN_AMBIENT_PATTERN.search(preset_css), preset_css
    assert "css-gradient" not in manifest["preset_theme"]["ambient_design"]
    assert "css-pattern" not in manifest["preset_theme"]["ambient_design"]

    _run(
        [
            sys.executable,
            "-B",
            str(OWNERSHIP_QA),
            "--html",
            str(output),
            "--manifest",
            str(manifest_path),
        ]
    )
    return {
        "id": preset_id,
        "content_mode": manifest["content_mode"],
        "slides": len(manifest["composition_plan"]),
        "css_ownership": manifest["css_ownership"]["static_validation"],
        "background_pattern": manifest["preset_theme"]["background_pattern"],
    }


def main() -> int:
    counts = _assert_sources()
    _assert_help_choices()
    records: list[dict[str, Any]] = []
    qa_parent = (ROOT / "artifacts" / "qa").resolve()
    root = (qa_parent / f"_tmp-formal-preset-cohort-{uuid.uuid4().hex}").resolve()
    if root.parent != qa_parent or not root.name.startswith("_tmp-formal-preset-cohort-"):
        raise ValueError(f"Unsafe smoke-test path: {root}")
    root.mkdir(parents=True, exist_ok=False)
    try:
        for index, preset_id in enumerate(COHORT):
            output = root / preset_id / "smoke.html"
            output.parent.mkdir(parents=True, exist_ok=True)
            records.append(_assert_render(preset_id, output, 2026081301 + index))
    finally:
        if root.is_dir() and root.parent == qa_parent:
            shutil.rmtree(root)

    print(
        json.dumps(
            {
                "schema_version": "formal-html-preset-cohort-smoke/v1",
                "pass": True,
                "cohort_count": len(COHORT),
                "counts": counts,
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
