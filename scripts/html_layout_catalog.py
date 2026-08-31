#!/usr/bin/env python3
"""Load and validate the renderer-scoped HTML-safe layout catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "prompt_system" / "renderers" / "html" / "layout-catalog.yaml"
CORE_LAYOUTS = ROOT / "prompt_system" / "layouts"
MEDIA_MODES = ("no-image", "with-image")
ASSET_POLICIES = ("pattern-only", "image-planned")
DEFAULT_ASSET_POLICY = "pattern-only"
RETIRED_LAYOUT_IDS = {
    "toc-2",
    "toc-2-image-left",
    "toc-2-panel-rows",
    "toc-2-vertical",
}
MEDIA_RENDERING_POLICIES = {
    "no-image": "semantic-native",
    "with-image": "placeholder-fill",
}


def _load_core_media_requirements() -> dict[str, str]:
    """Read the canonical media requirement from every Layout Core file."""

    requirements: dict[str, str] = {}
    issues: list[str] = []
    for path in sorted(CORE_LAYOUTS.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            issues.append(f"{path.name}: expected a YAML object")
            continue
        layout_id = str(data.get("id", "")).strip()
        if not layout_id:
            issues.append(f"{path.name}: missing id")
            continue
        if layout_id in RETIRED_LAYOUT_IDS:
            continue
        if layout_id in requirements:
            issues.append(f"duplicate Layout id: {layout_id}")
            continue
        requirement = str(data.get("media_requirement", "")).strip()
        if requirement not in MEDIA_MODES:
            issues.append(
                f"{layout_id}: media_requirement must be one of {MEDIA_MODES}"
            )
            continue
        requirements[layout_id] = requirement
    if issues:
        raise ValueError("Layout Core media requirements invalid: " + "; ".join(issues))
    return requirements


def load_html_layout_catalog(path: Path = DEFAULT_CATALOG) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected HTML layout catalog object: {path}")

    media_mode_by_id = _load_core_media_requirements()
    core_ids = sorted(media_mode_by_id)
    media_groups = {
        mode: [layout_id for layout_id in core_ids if media_mode_by_id[layout_id] == mode]
        for mode in MEDIA_MODES
    }
    default_asset_policy = str(data.get("default_asset_policy", "")).strip()
    asset_policies = data.get("asset_policies") or {}
    allowed = data.get("allowed_layout_ids") or []  # compatibility projection
    manual_only = data.get("manual_only_layouts") or data.get("excluded_layouts") or []
    manual_only_ids = [row.get("id") for row in manual_only if isinstance(row, dict)]
    issues: list[str] = []
    if data.get("schema_version") != 3:
        issues.append("schema_version must be 3")
    if default_asset_policy != DEFAULT_ASSET_POLICY:
        issues.append(f"default_asset_policy must be {DEFAULT_ASSET_POLICY}")
    if not isinstance(asset_policies, dict):
        issues.append("asset_policies must be an object")
        asset_policies = {}
    if set(asset_policies) != set(ASSET_POLICIES):
        issues.append(f"asset_policies must contain exactly {ASSET_POLICIES}")
    expected_policy_modes = {
        "pattern-only": ["no-image"],
        "image-planned": ["no-image", "with-image"],
    }
    normalized_policy_modes: dict[str, list[str]] = {}
    for policy_name, expected_modes in expected_policy_modes.items():
        row = asset_policies.get(policy_name) or {}
        actual_modes = row.get("allowed_media_requirements") if isinstance(row, dict) else None
        if actual_modes != expected_modes:
            issues.append(
                f"asset_policies.{policy_name}.allowed_media_requirements must be {expected_modes}"
            )
        normalized_policy_modes[policy_name] = list(expected_modes)

    layout_ids_by_asset_policy = {
        policy_name: [
            layout_id
            for layout_id in core_ids
            if media_mode_by_id[layout_id] in allowed_modes
        ]
        for policy_name, allowed_modes in normalized_policy_modes.items()
    }
    expected_allowed = layout_ids_by_asset_policy[DEFAULT_ASSET_POLICY]
    expected_manual_only = sorted(set(core_ids) - set(expected_allowed))
    if len(allowed) != len(set(allowed)):
        issues.append("allowed_layout_ids contains duplicates")
    if len(manual_only_ids) != len(set(manual_only_ids)):
        issues.append("manual_only_layouts contains duplicates")
    if allowed != expected_allowed:
        issues.append("allowed_layout_ids must mirror the pattern-only core projection")
    if sorted(manual_only_ids) != expected_manual_only:
        issues.append("manual_only_layouts must mirror Layout Core with-image requirements")

    compatibility_media_groups = data.get("layout_media_modes") or {}
    if not isinstance(compatibility_media_groups, dict):
        issues.append("layout_media_modes must be an object")
        compatibility_media_groups = {}
    unknown_modes = sorted(set(compatibility_media_groups) - set(MEDIA_MODES))
    if unknown_modes:
        issues.append(f"unknown layout media modes: {unknown_modes}")
    for mode in MEDIA_MODES:
        values = compatibility_media_groups.get(mode) or []
        if not isinstance(values, list):
            issues.append(f"layout_media_modes.{mode} must be a list")
            continue
        if len(values) != len(set(values)):
            issues.append(f"layout_media_modes.{mode} contains duplicates")
        if sorted(values) != sorted(media_groups[mode]):
            issues.append(
                f"layout_media_modes.{mode} must mirror Layout Core media_requirement"
            )

    media_rendering_policy = data.get("media_rendering_policy") or {}
    if not isinstance(media_rendering_policy, dict):
        issues.append("media_rendering_policy must be an object")
        media_rendering_policy = {}
    for mode, expected_policy in MEDIA_RENDERING_POLICIES.items():
        actual_policy = str(media_rendering_policy.get(mode, "")).strip()
        if actual_policy != expected_policy:
            issues.append(
                f"media_rendering_policy.{mode} must be {expected_policy!r}"
            )

    if issues:
        raise ValueError("HTML layout catalog invalid: " + "; ".join(issues))
    data["allowed_layout_ids"] = list(expected_allowed)
    data["manual_only_layout_ids"] = list(expected_manual_only)
    data["excluded_layout_ids"] = list(expected_manual_only)  # compatibility for older callers
    data["visible_layout_ids"] = core_ids
    data["media_requirement_by_layout_id"] = media_mode_by_id
    data["layout_ids_by_media_requirement"] = {
        mode: list(media_groups[mode]) for mode in MEDIA_MODES
    }
    data["layout_media_mode_by_id"] = media_mode_by_id
    data["layout_ids_by_media_mode"] = {
        mode: list(media_groups[mode]) for mode in MEDIA_MODES
    }
    data["layout_ids_by_asset_policy"] = layout_ids_by_asset_policy
    data["asset_policy_media_requirements"] = normalized_policy_modes
    data["media_rendering_policy"] = dict(MEDIA_RENDERING_POLICIES)
    data["counts"] = {
        "core": len(core_ids),
        "visible": len(core_ids),
        "auto_select": len(expected_allowed),
        "manual_only": len(expected_manual_only),
        "allowed": len(expected_allowed),
        "excluded": len(expected_manual_only),
        "no_image": len(media_groups["no-image"]),
        "with_image": len(media_groups["with-image"]),
        "pattern_only_eligible": len(layout_ids_by_asset_policy["pattern-only"]),
        "pattern_only_blocked": len(expected_manual_only),
        "image_planned_eligible": len(layout_ids_by_asset_policy["image-planned"]),
    }
    return data


def eligible_html_layouts(
    catalog: dict[str, Any] | None = None,
    asset_policy: str | None = None,
) -> list[str]:
    policy = catalog or load_html_layout_catalog()
    resolved = asset_policy or policy["default_asset_policy"]
    if resolved not in ASSET_POLICIES:
        raise ValueError(f"Unknown HTML asset policy: {resolved}")
    return list(policy["layout_ids_by_asset_policy"][resolved])


def filter_html_layouts(
    layout_ids: Iterable[str],
    catalog: dict | None = None,
    media_mode: str | None = None,
    asset_policy: str | None = None,
) -> list[str]:
    policy = catalog or load_html_layout_catalog()
    allowed = set(eligible_html_layouts(policy, asset_policy))
    if media_mode is not None:
        if media_mode not in MEDIA_MODES:
            raise ValueError(f"Unknown HTML layout media mode: {media_mode}")
        allowed &= set(policy["layout_ids_by_media_mode"][media_mode])
    return [layout_id for layout_id in layout_ids if layout_id in allowed]


def visible_html_layouts(
    catalog: dict | None = None,
    media_mode: str | None = None,
    asset_policy: str | None = None,
) -> list[str]:
    """Return the complete user/model-visible Layout catalog, optionally by media mode."""
    policy = catalog or load_html_layout_catalog()
    visible = (
        eligible_html_layouts(policy, asset_policy)
        if asset_policy is not None
        else list(policy["visible_layout_ids"])
    )
    if media_mode is not None:
        if media_mode not in MEDIA_MODES:
            raise ValueError(f"Unknown HTML layout media mode: {media_mode}")
        mode_ids = set(policy["layout_ids_by_media_mode"][media_mode])
        visible = [layout_id for layout_id in visible if layout_id in mode_ids]
    return visible


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--media-mode", choices=MEDIA_MODES)
    parser.add_argument("--asset-policy", choices=ASSET_POLICIES)
    args = parser.parse_args()
    data = load_html_layout_catalog(args.catalog.resolve())
    payload = {"id": data["id"], **data["counts"], "pass": True}
    if args.media_mode:
        payload["selected_media_mode"] = args.media_mode
    if args.asset_policy:
        payload["selected_asset_policy"] = args.asset_policy
    if args.media_mode or args.asset_policy:
        payload["selected_layouts"] = visible_html_layouts(
            data,
            media_mode=args.media_mode,
            asset_policy=args.asset_policy,
        )
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
