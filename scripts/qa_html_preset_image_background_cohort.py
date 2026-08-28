#!/usr/bin/env python3
"""Validate the fixed 18-Preset image-background-safe cohort."""

from __future__ import annotations

from copy import deepcopy
import json
import re
from pathlib import Path
from typing import Any

import yaml

from html_assembly import resolve_html_assembly
from html_css_ownership import assert_appearance_css
from html_preset_registry import load_preset_registry
from html_preset_themes import (
    IMAGE_BACKGROUND_GRAPHICS,
    IMAGE_BACKGROUND_POLICY,
    IMAGE_BACKGROUND_SAFE_PRESET_COHORT,
    build_preset_appearance_css,
    load_html_preset_theme_catalog,
)


ROOT = Path(__file__).resolve().parents[1]
DESIGN_METHOD = ROOT / "prompt_system" / "renderers" / "html" / "design-method.yaml"
PRESET_THEMES = ROOT / "prompt_system" / "renderers" / "html" / "preset-themes.yaml"
REPAIRED_PRESETS = {
    "signal-route-atlas",
    "ai-operations-signal",
    "sepia-retail-case",
    "dark-ai-city",
    "dark-city-network-report",
    "clinical-evidence-atlas",
    "moonlit-herbarium-atlas",
}
FORBIDDEN_VISUAL_SEMANTICS = re.compile(
    r"(?<![0-9A-Za-z])(?:orbit|rings?|grids?|arcs?|radial|dots?|symbols?)(?![0-9A-Za-z])"
    r"|(?:網格|圓環|環線|放射|圓點|圖騰)",
    re.IGNORECASE,
)


def _flatten_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class _InMemoryCatalogPath:
    def __init__(self, data: dict[str, Any]) -> None:
        self._text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)

    def read_text(self, *, encoding: str) -> str:
        assert encoding == "utf-8"
        return self._text

    def resolve(self) -> Path:
        return (ROOT / "_qa_in_memory_preset_themes.yaml").resolve()


def _assert_missing_policy_is_rejected() -> int:
    source = yaml.safe_load(PRESET_THEMES.read_text(encoding="utf-8")) or {}
    required_fields = (
        "background_pattern",
        "background_graphics",
        "visual_asset_policy",
    )
    rejected = 0
    for preset_id in IMAGE_BACKGROUND_SAFE_PRESET_COHORT:
        for field in required_fields:
            candidate = deepcopy(source)
            candidate["themes"][preset_id].pop(field, None)
            try:
                load_html_preset_theme_catalog(_InMemoryCatalogPath(candidate))
            except ValueError as error:
                if preset_id not in str(error):
                    raise AssertionError(
                        f"{preset_id}: validator failed for the wrong reason after removing {field}"
                    ) from error
                rejected += 1
            else:
                raise AssertionError(
                    f"{preset_id}: validator accepted missing required field {field}"
                )
    return rejected


def main() -> int:
    catalog = load_html_preset_theme_catalog()
    themes = catalog["themes"]
    registry = load_preset_registry(check_gallery=False)
    reusable_ids = {
        row["id"]
        for row in registry["entries"]
        if "reusable-preset" in row["capabilities"]
    }
    design_method = yaml.safe_load(DESIGN_METHOD.read_text(encoding="utf-8")) or {}
    profiles = design_method.get("theme_selection_profiles") or {}

    records: list[dict[str, Any]] = []
    for preset_id in IMAGE_BACKGROUND_SAFE_PRESET_COHORT:
        if preset_id not in reusable_ids:
            raise AssertionError(f"{preset_id}: not registered as reusable-preset")
        theme = themes[preset_id]
        assert theme.get("background_pattern") == "none", preset_id
        assert theme.get("background_graphics") == IMAGE_BACKGROUND_GRAPHICS, preset_id
        assert theme.get("visual_asset_policy") == IMAGE_BACKGROUND_POLICY, preset_id

        assembly = resolve_html_assembly(preset_id)
        css = build_preset_appearance_css(preset_id, theme, assembly["recipe"])
        assert_appearance_css(css, source=f"qa:image-background:{preset_id}")
        if "background-image:none" not in css:
            raise AssertionError(f"{preset_id}: appearance CSS did not disable ambient pattern paint")

        if preset_id in REPAIRED_PRESETS:
            forbidden = FORBIDDEN_VISUAL_SEMANTICS.search(_flatten_text(theme))
            if forbidden:
                raise AssertionError(
                    f"{preset_id}: forbidden image-background semantic {forbidden.group(0)!r}"
                )

        records.append(
            {
                "id": preset_id,
                "background_pattern": theme["background_pattern"],
                "background_graphics": theme["background_graphics"],
                "visual_asset_policy": theme["visual_asset_policy"],
                "css_ownership": "pass",
            }
        )

    dark_ai_signatures = profiles["dark-ai-city"]["signature_compositions"]
    forbidden_signature = FORBIDDEN_VISUAL_SEMANTICS.search(_flatten_text(dark_ai_signatures))
    if forbidden_signature:
        raise AssertionError(
            "dark-ai-city: signature retains forbidden image-background semantic "
            f"{forbidden_signature.group(0)!r}"
        )
    if "low-frequency-ambient-field" not in dark_ai_signatures:
        raise AssertionError("dark-ai-city: missing non-localized ambient signature")

    negative_cases = _assert_missing_policy_is_rejected()

    print(
        json.dumps(
            {
                "schema_version": "html-preset-image-background-cohort-qa/v1",
                "pass": True,
                "cohort_count": len(IMAGE_BACKGROUND_SAFE_PRESET_COHORT),
                "repaired_count": len(REPAIRED_PRESETS),
                "missing_policy_rejections": negative_cases,
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
