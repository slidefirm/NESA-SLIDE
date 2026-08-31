#!/usr/bin/env python3
"""Load, validate, and resolve renderer-scoped HTML assembly recipes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "prompt_system" / "renderers" / "html" / "assembly-catalog.yaml"


def load_html_assembly_catalog(path: Path = DEFAULT_CATALOG) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profiles = data.get("profiles") or {}
    recipes = data.get("recipes") or {}
    layers = data.get("layers") or []
    issues: list[str] = []

    required_layers = {
        "story", "theme_adapter", "layout_adapter", "composition",
        "background_pattern", "surface", "depth", "typography",
        "component_recipe", "editor_contract",
    }
    if not required_layers.issubset(set(layers)):
        missing = sorted(required_layers - set(layers))
        issues.append(f"missing assembly layers: {missing}")

    ownership = data.get("layer_ownership") or {}
    if ownership.get("composition") != "per-slide-after-layout-scaffold":
        issues.append("composition must bind page content after Layout scaffold selection")
    if ownership.get("layout_adapter") != "all-slide-and-module-geometry":
        issues.append("layout_adapter must own all slide/module geometry")
    css_ownership = data.get("css_ownership") or {}
    if css_ownership.get("geometry_owner") != "renderer-base":
        issues.append("CSS geometry owner must be renderer-base")
    if css_ownership.get("post_materialize_theme_geometry") != "forbidden":
        issues.append("post-materialize Theme geometry must be forbidden")
    if css_ownership.get("semantic_guard_mode") != "validate-not-correct":
        issues.append("semantic guards must validate instead of correcting CSS")

    profile_types = (
        "composition", "background_pattern", "surface", "depth",
        "typography", "component_recipe",
    )
    for profile_type in profile_types:
        if not isinstance(profiles.get(profile_type), dict) or not profiles[profile_type]:
            issues.append(f"profiles.{profile_type} must be a non-empty object")

    for theme_id, recipe in recipes.items():
        if not isinstance(recipe, dict):
            issues.append(f"{theme_id}: recipe must be an object")
            continue
        for profile_type in profile_types:
            profile_id = recipe.get(profile_type)
            if not profile_id:
                issues.append(f"{theme_id}: missing {profile_type}")
            elif profile_id not in profiles.get(profile_type, {}):
                issues.append(f"{theme_id}: unknown {profile_type} profile {profile_id}")

    pattern_policy = data.get("pattern_effect_policy") or {}
    required_pattern_labels = set(pattern_policy.get("required_labels") or [])
    performance_levels = set(pattern_policy.get("performance_levels") or [])
    readability_levels = set(pattern_policy.get("readability_risk_levels") or [])
    for pattern_id, pattern in profiles.get("background_pattern", {}).items():
        missing_labels = sorted(required_pattern_labels - set(pattern))
        if missing_labels:
            issues.append(f"{pattern_id}: missing pattern labels {missing_labels}")
        if pattern.get("performance") not in performance_levels:
            issues.append(f"{pattern_id}: invalid performance label")
        if pattern.get("readability_risk") not in readability_levels:
            issues.append(f"{pattern_id}: invalid readability_risk label")
        max_opacity = pattern.get("max_opacity")
        if not isinstance(max_opacity, (int, float)) or not 0 < max_opacity <= 0.25:
            issues.append(f"{pattern_id}: max_opacity must be between 0 and 0.25")

    if len(recipes) != len(set(recipes)):
        issues.append("recipe ids must be unique")
    recipe_signatures = [tuple(recipe.get(key) for key in profile_types) for recipe in recipes.values()]
    if len(recipe_signatures) != len(set(recipe_signatures)):
        issues.append("every theme must have a unique assembly signature")

    editor = data.get("editor_contract") or {}
    if editor.get("max_history") != 100:
        issues.append("editor_contract.max_history must be 100")
    guardrails = data.get("guardrails") or {}
    if guardrails.get("raster_assets") not in {"forbidden", "provenance-tracked-opt-in"}:
        issues.append("HTML assembly raster policy must be forbidden or provenance-tracked-opt-in")

    if issues:
        raise ValueError("HTML assembly catalog invalid: " + "; ".join(issues))

    data["counts"] = {
        "recipes": len(recipes),
        "profile_types": len(profile_types),
        "profiles": sum(len(profiles[key]) for key in profile_types),
        "unique_signatures": len(set(recipe_signatures)),
    }
    return data


def resolve_html_assembly(theme_id: str, path: Path = DEFAULT_CATALOG) -> dict:
    catalog = load_html_assembly_catalog(path)
    recipe = catalog["recipes"].get(theme_id)
    if recipe is None:
        raise ValueError(f"Theme has no HTML assembly recipe: {theme_id}")
    profile_types = (
        "composition", "background_pattern", "surface", "depth",
        "typography", "component_recipe",
    )
    resolved_profiles = {
        profile_type: catalog["profiles"][profile_type][profile_id]
        for profile_type, profile_id in recipe.items()
        if profile_type in profile_types
    }
    if "continuity_element" in recipe:
        resolved_profiles["continuity_element"] = recipe["continuity_element"]
    return {
        "id": f"{theme_id}-assembly",
        "theme_id": theme_id,
        "canvas": catalog["canvas"],
        "layers": catalog["layers"],
        "recipe": recipe,
        "profiles": resolved_profiles,
        "editor_contract": catalog["editor_contract"],
        "guardrails": catalog["guardrails"],
        "pattern_effect_policy": catalog["pattern_effect_policy"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--theme")
    args = parser.parse_args()
    catalog = load_html_assembly_catalog(args.catalog.resolve())
    payload = resolve_html_assembly(args.theme, args.catalog.resolve()) if args.theme else {
        "id": catalog["id"], **catalog["counts"], "pass": True,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
