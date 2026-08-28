#!/usr/bin/env python3
"""Load and validate HTML-only preset themes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

try:
    from html_css_ownership import assert_appearance_css
    from html_preset_registry import load_preset_registry
except ModuleNotFoundError:  # package-style imports used by tests and notebooks
    from .html_css_ownership import assert_appearance_css
    from .html_preset_registry import load_preset_registry


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "prompt_system" / "renderers" / "html" / "preset-themes.yaml"
CORE_THEMES = ROOT / "prompt_system" / "themes"

FORBIDDEN_REUSABLE_FIELDS = {
    "source_style_case",
    "source_html",
    "source_css",
    "example_story",
    "example_layouts",
    "story",
    "layouts",
    "layout_id",
    "content",
    "text_replacements",
    "css",
}
ALLOWED_REUSABLE_FIELDS = {
    "display_name",
    "base_theme",
    "scope",
    "pure_html",
    "auto_select",
    "design_dialect",
    "composition",
    "techniques",
    "palette",
    "typography",
    "background_pattern",
    "background_graphics",
    "visual_asset_policy",
    "background_asset",
    "continuity_element",
    "surface",
}

IMAGE_BACKGROUND_POLICY = "generated-raster-background-opt-in"
IMAGE_BACKGROUND_GRAPHICS = "safe-zone-minimal-raster"
IMAGE_BACKGROUND_SAFE_PRESET_COHORT = (
    "line-argument-journal",
    "signal-route-atlas",
    "field-index-manual",
    "tide-signal-observatory",
    "craft-archive-editions",
    "incident-command-redline",
    "harbor-ribbon-program",
    "neighborhood-newsroom-proof",
    "scent-veil-launch",
    "restoration-blueprint-ledger",
    "ai-operations-signal",
    "brave-classroom-contours",
    "night-transit-wayfinding",
    "sepia-retail-case",
    "dark-ai-city",
    "dark-city-network-report",
    "clinical-evidence-atlas",
    "moonlit-herbarium-atlas",
)
FORBIDDEN_IMAGE_BACKGROUND_PATTERN = re.compile(
    r"(?:radial-gradient|repeating-radial-gradient|ellipse|orbit|ring|arc)",
    re.IGNORECASE,
)

PATTERN_PAINT = {
    "none": "background-image:none",
    "paper-grain": (
        "background-image:radial-gradient(circle,color-mix(in srgb,var(--text) 7%,transparent) 0 1px,transparent 1.5px);"
        "background-size:6px 6px"
    ),
    "circuit-nodes": (
        "background-image:radial-gradient(circle,color-mix(in srgb,var(--accent) 28%,transparent) 0 1px,transparent 1.6px);"
        "background-size:24px 24px"
    ),
    "engineering-grid": (
        "background-image:linear-gradient(color-mix(in srgb,var(--accent) 8%,transparent) 1px,transparent 1px),"
        "linear-gradient(90deg,color-mix(in srgb,var(--accent) 8%,transparent) 1px,transparent 1px);"
        "background-size:48px 48px"
    ),
    "coordinate-map-stock": (
        "background-image:linear-gradient(color-mix(in srgb,var(--support-accent) 6%,transparent) 1px,transparent 1px),"
        "linear-gradient(90deg,color-mix(in srgb,var(--support-accent) 6%,transparent) 1px,transparent 1px);"
        "background-size:72px 72px"
    ),
    "herbarium-ink-wash": (
        "background-image:radial-gradient(ellipse at 4% 12%,color-mix(in srgb,var(--support-accent) 10%,transparent),transparent 31%),"
        "radial-gradient(ellipse at 96% 88%,color-mix(in srgb,var(--accent) 7%,transparent),transparent 28%);"
        "background-size:100% 100%"
    ),
    "generated-paper-field": (
        "background-image:radial-gradient(circle at 82% 22%,color-mix(in srgb,var(--accent) 14%,transparent),transparent 28%),"
        "radial-gradient(circle at 12% 82%,color-mix(in srgb,var(--support-accent) 16%,transparent),transparent 32%),"
        "linear-gradient(120deg,rgba(255,255,255,.75),transparent 48%);"
        "background-size:100% 100%"
    ),
    "fine-ledger-grid": (
        "background-image:linear-gradient(color-mix(in srgb,var(--text) 4%,transparent) 1px,transparent 1px),"
        "linear-gradient(90deg,color-mix(in srgb,var(--text) 4%,transparent) 1px,transparent 1px);"
        "background-size:64px 64px"
    ),
    "nocturne-ambient": (
        "background-image:radial-gradient(circle at 15% 20%,color-mix(in srgb,var(--accent) 14%,transparent),transparent 28%),"
        "radial-gradient(circle at 85% 80%,color-mix(in srgb,var(--support-accent) 10%,transparent),transparent 30%);"
        "background-size:100% 100%"
    ),
    "woven-geometry": (
        "background-image:linear-gradient(135deg,color-mix(in srgb,var(--accent) 8%,transparent) 25%,transparent 25% 50%,color-mix(in srgb,var(--accent) 8%,transparent) 50% 75%,transparent 75%),"
        "linear-gradient(45deg,color-mix(in srgb,var(--support-accent) 7%,transparent) 25%,transparent 25% 50%,color-mix(in srgb,var(--support-accent) 7%,transparent) 50% 75%,transparent 75%);"
        "background-size:56px 56px"
    ),
    "ivory-arc-frame": (
        "background-image:"
        "radial-gradient(circle at -2% -8%,transparent 0 238px,color-mix(in srgb,var(--text) 12%,transparent) 239px 241px,transparent 242px),"
        "radial-gradient(circle at 103% 108%,transparent 0 300px,color-mix(in srgb,var(--text) 12%,transparent) 301px 303px,transparent 304px),"
        "linear-gradient(to bottom,transparent 0 28px,color-mix(in srgb,var(--text) 12%,transparent) 28px 30px,transparent 30px calc(100% - 30px),color-mix(in srgb,var(--text) 12%,transparent) calc(100% - 30px) calc(100% - 28px),transparent calc(100% - 28px));"
        "background-size:100% 100%"
    ),
}

SURFACE_PAINT = {
    "editorial-rule": "background:color-mix(in srgb,var(--surface) 88%,var(--bg));border-color:color-mix(in srgb,var(--accent) 46%,transparent);border-radius:2px",
    "ink-column": "background:color-mix(in srgb,var(--surface) 76%,transparent);border-color:color-mix(in srgb,var(--text) 22%,transparent);border-radius:0",
    "circuit-glass": "background:color-mix(in srgb,var(--surface) 78%,transparent);border-color:color-mix(in srgb,var(--accent) 58%,transparent);border-radius:6px;backdrop-filter:blur(10px)",
    "transfer-map-sheet": "background:color-mix(in srgb,var(--surface) 90%,var(--bg));border-color:color-mix(in srgb,var(--support-accent) 48%,transparent);border-radius:4px",
    "veil-pane": "background:color-mix(in srgb,var(--surface) 62%,transparent);border-color:color-mix(in srgb,var(--accent) 28%,transparent);border-radius:42px 12px 42px 12px;backdrop-filter:blur(14px)",
    "signal-strip": "background:color-mix(in srgb,var(--surface) 68%,var(--bg));border-color:color-mix(in srgb,var(--accent) 48%,transparent);border-radius:0",
    "ledger-sheet": "background:color-mix(in srgb,var(--surface) 88%,var(--bg));border-color:color-mix(in srgb,var(--text) 28%,transparent);border-radius:0",
    "night-glass": "background:color-mix(in srgb,var(--surface) 76%,transparent);border-color:color-mix(in srgb,var(--text) 18%,transparent);border-radius:24px;backdrop-filter:blur(16px)",
    "open-hairline-sheet": "background:color-mix(in srgb,var(--surface) 58%,transparent);border-color:color-mix(in srgb,var(--text) 20%,transparent);border-radius:0",
}

DEPTH_PAINT = {
    "editorial-flat": "box-shadow:none",
    "product-flat": "box-shadow:none",
    "technical-glass": "box-shadow:0 16px 38px color-mix(in srgb,var(--text) 9%,transparent)",
    "paper-stack": "box-shadow:0 14px 32px color-mix(in srgb,var(--text) 9%,transparent)",
    "restrained-luminous-paper": "box-shadow:0 24px 60px color-mix(in srgb,var(--text) 9%,transparent),inset 0 1px rgba(255,255,255,.82)",
    "ledger-flat": "box-shadow:0 10px 24px color-mix(in srgb,var(--text) 7%,transparent)",
    "nocturne-float": "box-shadow:0 22px 68px color-mix(in srgb,#000 32%,transparent)",
}


def _rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        raise ValueError(f"Preset palette color must be #RGB or #RRGGBB: {hex_color}")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _luminance(hex_color: str) -> float:
    channels = []
    for value in _rgb(hex_color):
        channel = value / 255
        channels.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(left: str, right: str) -> float:
    a, b = sorted((_luminance(left), _luminance(right)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _best_ink(background: str, candidates: list[str]) -> str:
    return max(candidates, key=lambda value: _contrast(background, value))


def build_preset_appearance_css(
    theme_id: str,
    theme: dict[str, Any],
    assembly_recipe: dict[str, Any],
) -> str:
    """Build appearance-only CSS from Preset tokens, never from an old case."""

    palette = theme["palette"]
    accent_text = _best_ink(
        palette["accent"],
        [palette["background"], palette["text"], "#000000", "#ffffff"],
    )
    scope = f'html[data-preset-theme="{theme_id}"]'
    surface_text = _best_ink(
        palette["surface"],
        [palette["text"], palette["background"], "#000000", "#ffffff"],
    )
    surface_muted = (
        palette["muted"]
        if _contrast(palette["muted"], palette["surface"]) >= 4.5
        else _best_ink(palette["surface"], [palette["muted"], surface_text, "#000000", "#ffffff"])
    )
    variables = {
        "--bg": palette["background"],
        "--primary": palette["text"],
        "--secondary": palette["muted"],
        "--accent": palette["accent"],
        "--support-accent": palette["support"],
        "--surface": palette["surface"],
        "--text": palette["text"],
        "--muted": palette["muted"],
        "--surface-text": surface_text,
        "--surface-muted": surface_muted,
        "--accent-ink": _best_ink(palette["background"], [palette["accent"], palette["text"]]),
        "--surface-accent-ink": _best_ink(palette["surface"], [palette["accent"], palette["text"]]),
        "--accent-text": accent_text,
    }
    typography = theme.get("typography") or {}
    if typography.get("display"):
        variables["--font-display"] = json.dumps(str(typography["display"]), ensure_ascii=False)
        variables["--font-heading"] = variables["--font-display"]
    if typography.get("body"):
        variables["--font-body"] = json.dumps(str(typography["body"]), ensure_ascii=False)
    if typography.get("utility"):
        variables["--font-mono"] = json.dumps(str(typography["utility"]), ensure_ascii=False)

    image_background_mode = theme.get("visual_asset_policy") == IMAGE_BACKGROUND_POLICY
    pattern_id = (
        "none"
        if image_background_mode
        else str(theme.get("background_pattern") or assembly_recipe["background_pattern"])
    )
    surface = theme.get("surface") or {}
    surface_id = str(surface.get("default") if isinstance(surface, dict) else surface or assembly_recipe["surface"])
    if not surface_id or surface_id == "None":
        surface_id = str(assembly_recipe["surface"])
    depth_id = str(assembly_recipe["depth"])
    pattern_css = PATTERN_PAINT.get(pattern_id, "background-image:none")
    if image_background_mode and FORBIDDEN_IMAGE_BACKGROUND_PATTERN.search(pattern_css):
        raise ValueError(
            f"{theme_id}: image-background mode cannot emit symbolic ambient pattern paint"
        )
    surface_css = SURFACE_PAINT.get(
        surface_id,
        "background:color-mix(in srgb,var(--surface) 84%,var(--bg));border-color:color-mix(in srgb,var(--accent) 36%,transparent);border-radius:8px",
    )
    depth_css = DEPTH_PAINT.get(depth_id, "box-shadow:none")
    variable_css = ";".join(f"{name}:{value}" for name, value in variables.items())
    css = f"""
{scope}{{{variable_css}}}
{scope} .slide{{color:var(--text);background-color:var(--bg);{pattern_css}}}
{scope} .diagram-node-bg{{{surface_css};{depth_css}}}
{scope} :is(.prod-title,.cover-center-title,.cover-split-title,.statement-focus-quote,.statement-center-headline){{color:var(--text);font-family:var(--font-display);font-weight:800;letter-spacing:-.025em;text-shadow:none}}
{scope} :is(.prod-subtitle,.cover-center-subtitle,.statement-center-support){{color:var(--muted);font-family:var(--font-body)}}
{scope} :is(.chapter-brand-overlay,.media-overlay-title,.cover-overlay-block,.cover-overlay-accent) > .diagram-node-bg{{background:var(--surface);background-image:none;border-top:5px solid var(--accent);backdrop-filter:none}}
{scope} :is(.chapter-brand-overlay,.media-overlay-title,.cover-overlay-block,.cover-overlay-accent) > :is(span,b,em){{color:var(--surface-text)}}
{scope} [data-visual-surface-role="accent"]>.diagram-node-bg{{background:var(--accent);background-image:none;border-color:transparent}}
{scope} [data-visual-surface-role="none"]>.diagram-node-bg{{background:none;border-color:transparent;box-shadow:none}}
""".strip()
    assert_appearance_css(css, source=f"preset:{theme_id}")
    return css


def load_html_preset_theme_catalog(path: Path = DEFAULT_CATALOG) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    themes = data.get("themes") or {}
    core_ids = {item.stem for item in CORE_THEMES.glob("*.yaml")}
    issues: list[str] = []

    if data.get("schema_version") != 2:
        issues.append("schema_version must be 2")
    runtime_contract = data.get("runtime_contract") or {}
    expected_runtime_contract = {
        "css_owner": "preset-appearance",
        "content_source": "caller-only",
        "layout_source": "layout-core-only",
        "legacy_case_import": "forbidden",
        "embedded_css": "forbidden",
        "layout_selectors": "forbidden",
        "geometry_properties": "forbidden",
        "important": "forbidden",
    }
    if runtime_contract != expected_runtime_contract:
        issues.append("runtime_contract must enforce appearance-only Preset isolation")
    if not themes:
        issues.append("themes must be a non-empty object")
    for theme_id, theme in themes.items():
        if not isinstance(theme, dict):
            issues.append(f"{theme_id}: theme must be an object")
            continue
        if theme_id in core_ids:
            issues.append(f"{theme_id}: preset id collides with a core theme")
        if theme.get("base_theme") not in core_ids:
            issues.append(f"{theme_id}: unknown base_theme {theme.get('base_theme')}")
        if theme.get("scope") != "html-only" or theme.get("pure_html") is not True:
            issues.append(f"{theme_id}: preset must be html-only and pure_html")
        forbidden_fields = sorted(FORBIDDEN_REUSABLE_FIELDS & set(theme))
        if forbidden_fields:
            issues.append(f"{theme_id}: reusable Preset contains demo/runtime fields {forbidden_fields}")
        unknown_fields = sorted(set(theme) - ALLOWED_REUSABLE_FIELDS)
        if unknown_fields:
            issues.append(f"{theme_id}: unknown reusable Preset fields {unknown_fields}")
        if not theme.get("design_dialect") or not theme.get("composition"):
            issues.append(f"{theme_id}: design_dialect and composition are required")
        if len(theme.get("techniques") or []) < 3:
            issues.append(f"{theme_id}: at least three HTML techniques are required")
        if theme_id in IMAGE_BACKGROUND_SAFE_PRESET_COHORT:
            if theme.get("visual_asset_policy") != IMAGE_BACKGROUND_POLICY:
                issues.append(
                    f"{theme_id}: fixed image-background cohort must explicitly use "
                    f"visual_asset_policy={IMAGE_BACKGROUND_POLICY}"
                )
            if theme.get("background_pattern") != "none":
                issues.append(
                    f"{theme_id}: fixed image-background cohort must set background_pattern to none"
                )
            if theme.get("background_graphics") != IMAGE_BACKGROUND_GRAPHICS:
                issues.append(
                    f"{theme_id}: fixed image-background cohort must use "
                    f"background_graphics={IMAGE_BACKGROUND_GRAPHICS}"
                )
        elif theme.get("visual_asset_policy") == IMAGE_BACKGROUND_POLICY:
            if theme.get("background_pattern") != "none":
                issues.append(
                    f"{theme_id}: image-background Preset must set background_pattern to none"
                )
            if theme.get("background_graphics") != IMAGE_BACKGROUND_GRAPHICS:
                issues.append(
                    f"{theme_id}: image-background Preset must use "
                    f"background_graphics={IMAGE_BACKGROUND_GRAPHICS}"
                )
        palette = theme.get("palette") or {}
        required_colors = {"background", "surface", "text", "muted", "accent", "support"}
        if not required_colors.issubset(palette):
            issues.append(f"{theme_id}: incomplete curated palette")

    missing_image_background_presets = sorted(
        set(IMAGE_BACKGROUND_SAFE_PRESET_COHORT) - set(themes)
    )
    if missing_image_background_presets:
        issues.append(
            "fixed image-background cohort is missing Presets "
            f"{missing_image_background_presets}"
        )

    policy = data.get("selection_policy") or {}
    if policy.get("random_hue_mutation") != "forbidden":
        issues.append("selection_policy.random_hue_mutation must be forbidden")
    content_policy = data.get("content_policy") or {}
    if content_policy.get("default_mode") != "new-deck":
        issues.append("content_policy.default_mode must be new-deck")
    if content_policy.get("preset_demo_mode") != "explicit-only":
        issues.append("content_policy.preset_demo_mode must be explicit-only")
    if content_policy.get("demo_source") != "external-isolated-route-only":
        issues.append("content_policy.demo_source must be external-isolated-route-only")
    if content_policy.get("reusable_preset_demo_fields") != "forbidden":
        issues.append("content_policy.reusable_preset_demo_fields must be forbidden")
    if issues:
        raise ValueError("HTML preset theme catalog invalid: " + "; ".join(issues))

    if path.resolve() == DEFAULT_CATALOG.resolve():
        registry = load_preset_registry(check_gallery=False)
        registry_themes = {
            row["id"]: row
            for row in registry["entries"]
            if "reusable-preset" in row["capabilities"]
        }
        if set(themes) != set(registry_themes):
            raise ValueError("HTML preset theme catalog does not match the Preset registry")
        for theme_id, theme in themes.items():
            theme["display_name"] = registry_themes[theme_id]["display_name"]
        data["registry"] = "prompt_system/presets/catalog.yaml"

    data["counts"] = {
        "presets": len(themes),
        "auto_select": sum(1 for theme in themes.values() if theme.get("auto_select")),
    }
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()
    data = load_html_preset_theme_catalog(args.catalog.resolve())
    try:
        from html_assembly import resolve_html_assembly
    except ModuleNotFoundError:  # package-style imports used by tests and notebooks
        from .html_assembly import resolve_html_assembly
    for theme_id, theme in data["themes"].items():
        assembly = resolve_html_assembly(theme_id)
        build_preset_appearance_css(theme_id, theme, assembly["recipe"])
    print(json.dumps({"id": data["id"], **data["counts"], "css_contracts": len(data["themes"]), "pass": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
