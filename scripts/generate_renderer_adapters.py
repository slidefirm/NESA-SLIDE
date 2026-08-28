#!/usr/bin/env python3
"""Generate renderer adapters from canonical theme and layout YAML files.

The generated adapters never copy core palette values or slot coordinates.
They reference canonical paths so Image2, HTML, and PPTX can compile their own
runtime inputs without creating three manually maintained design systems.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from html_layout_family import layout_family
from pptx_variant_runtime import CATALOG_PATH, load_catalog


ROOT = Path(__file__).resolve().parents[1]
PROMPT_SYSTEM = ROOT / "prompt_system"
OUTPUT_ROOT = PROMPT_SYSTEM / "renderers"
RENDERERS = ("image2", "html", "pptx")
MEDIA_REQUIREMENTS = ("no-image", "with-image")
FORBIDDEN_THEME_GEOMETRY_FIELDS = ("html_spec", "pptx_spec", "layout_overrides")
RETIRED_LAYOUT_IDS = {
    "toc-2",
    "toc-2-image-left",
    "toc-2-panel-rows",
    "toc-2-vertical",
}
REQUIRED_LAYOUT_FIELDS = (
    "media_requirement",
    "slots",
    "safe_area",
    "alignment_rules",
    "visual_balance",
)


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def validate_theme_core(path: Path, data: dict[str, Any]) -> None:
    forbidden = [field for field in FORBIDDEN_THEME_GEOMETRY_FIELDS if field in data]
    if forbidden:
        raise ValueError(
            f"Theme Core may not own renderer/Layout geometry in {path}: "
            f"{', '.join(forbidden)}"
        )


def source_sha256(path: Path) -> str:
    """Hash text sources after canonicalizing every line ending to LF.

    Renderer adapters are checked on Windows and in GitHub Actions.  Their
    provenance hash must describe YAML content, not a checkout-specific CRLF
    conversion.
    """

    canonical = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(canonical).hexdigest()


def ref(kind: str, item_id: str, yaml_path: str) -> str:
    return f"prompt_system/{kind}/{item_id}.yaml#{yaml_path}"


def validate_layout_core(path: Path, data: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_LAYOUT_FIELDS if field not in data]
    if missing:
        raise ValueError(f"Missing required Layout core fields in {path}: {', '.join(missing)}")

    media_requirement = data["media_requirement"]
    if media_requirement not in MEDIA_REQUIREMENTS:
        raise ValueError(
            f"Layout core media_requirement must be one of {MEDIA_REQUIREMENTS} in {path}"
        )

    slots = data["slots"]
    if not isinstance(slots, list) or not slots:
        raise ValueError(f"Layout core slots must be a non-empty list in {path}")

    safe_area = data["safe_area"]
    if (
        not isinstance(safe_area, list)
        or len(safe_area) != 4
        or not all(isinstance(value, (int, float)) for value in safe_area)
    ):
        raise ValueError(f"Layout core safe_area must be [left, top, right, bottom] in {path}")
    left, top, right, bottom = safe_area
    if not (0 <= left < right <= 100 and 0 <= top < bottom <= 100):
        raise ValueError(f"Layout core safe_area bounds are invalid in {path}: {safe_area}")

    alignment_rules = data["alignment_rules"]
    if (
        not isinstance(alignment_rules, list)
        or not alignment_rules
        or not all(isinstance(rule, str) and rule.strip() for rule in alignment_rules)
    ):
        raise ValueError(f"Layout core alignment_rules must be a non-empty string list in {path}")

    visual_balance = data["visual_balance"]
    if (
        not isinstance(visual_balance, dict)
        or not str(visual_balance.get("method", "")).strip()
        or not str(visual_balance.get("description", "")).strip()
    ):
        raise ValueError(f"Layout core visual_balance requires method and description in {path}")


def dump_yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=100,
    )


def html_decoration_component(name: str, visual: str) -> str:
    value = f"{name} {visual}".lower()
    if re.search(r"grid|pattern|texture|grain|paper|noise|紋理|顆粒", value):
        return "css-background-layer"
    if re.search(r"line|rule|divider|bracket|border|frame|線|框", value):
        return "svg-or-css-border"
    if re.search(r"icon|badge|圖示|徽章", value):
        return "svg-icon-component"
    if re.search(r"photo|image|照片|影像", value):
        return "image-layer"
    return "css-shape-layer"


def pptx_decoration_component(name: str, visual: str) -> str:
    value = f"{name} {visual}".lower()
    if re.search(r"grid|texture|grain|noise|紋理|顆粒", value):
        return "optional-local-raster-or-omit"
    if re.search(r"line|rule|divider|bracket|border|frame|線|框", value):
        return "native-line-or-shape"
    if re.search(r"icon|badge|圖示|徽章", value):
        return "native-icon-or-svg-image"
    if re.search(r"photo|image|照片|影像", value):
        return "native-image"
    return "native-shape"


def placeholder_type(slot_id: str) -> str:
    value = slot_id.lower()
    if re.search(r"decor|accent[-_]?bar|divider|rule|ornament|chrome", value):
        return "decoration"
    if "title" in value and "subtitle" not in value:
        return "title"
    if re.search(r"photo|image|avatar|portrait|logo", value):
        return "picture"
    if re.search(r"chart|graph|map|axis|radar|heat", value):
        return "chart"
    if "table" in value:
        return "table"
    if re.search(r"subtitle|header|note|caption|footer|source|label|speaker|org|date|meta", value):
        return "subtitle"
    return "body"


def html_edit_contract(role: str) -> str:
    if role in {"title", "subtitle", "decoration"}:
        return "loose-edit-object"
    if role in {"picture", "chart", "table"}:
        return "semantic-module-if-atomic-multilayer-unit"
    return "loose-object-or-semantic-module-by-content-unit"


def pptx_background_role(family: str, slots: list[Any]) -> str:
    """Map 81 logical layouts onto six Image2-backed PPTX master roles."""
    if family == "cover":
        return "cover"
    if family == "toc":
        return "toc"
    if family in {"metrics", "data-viz"}:
        return "qa"
    if family == "media":
        picture_regions = []
        for slot in slots:
            if not isinstance(slot, dict) or placeholder_type(str(slot.get("id", ""))) != "picture":
                continue
            region = slot.get("region") or slot.get("placement")
            if isinstance(region, list) and len(region) >= 4:
                picture_regions.append(region)
        if picture_regions:
            center_x = sum(float(row[0]) + float(row[2]) / 2 for row in picture_regions) / len(picture_regions)
            return "content-b" if center_x < 50 else "content-a"
    return "content-c"


def theme_adapter(renderer: str, path: Path, data: dict[str, Any]) -> dict[str, Any]:
    validate_theme_core(path, data)
    theme_id = str(data["id"])
    vocab = data.get("decoration_vocabulary") or []
    base = {
        "schema_version": 1,
        "kind": "theme_adapter",
        "renderer": renderer,
        "theme_id": theme_id,
        "support_status": "core-native" if renderer == "image2" else "baseline-from-core",
        "source": {
            "path": f"prompt_system/themes/{path.name}",
            "sha256": source_sha256(path),
        },
        "core_refs": {
            "visual_base": ref("themes", theme_id, "visual_base"),
            "palette": ref("themes", theme_id, "visual_base.color_palette"),
            "typography": ref("themes", theme_id, "visual_base.typography"),
            "illustration": ref("themes", theme_id, "visual_base.illustration_style"),
            "mood": ref("themes", theme_id, "visual_base.mood"),
            "decoration_vocabulary": ref("themes", theme_id, "decoration_vocabulary"),
            "closing_statement": ref("themes", theme_id, "closing_statement"),
        },
    }
    decoration_rows = []
    for entry in vocab:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "unnamed-decoration"))
        visual = str(entry.get("visual", ""))
        if renderer == "html":
            implementation = html_decoration_component(name, visual)
        elif renderer == "pptx":
            implementation = pptx_decoration_component(name, visual)
        else:
            implementation = "natural-language-prompt-vocabulary"
        decoration_rows.append(
            {
                "name": name,
                "source_ref": ref("themes", theme_id, f"decoration_vocabulary[name={name}]"),
                "implementation": implementation,
            }
        )

    if renderer == "image2":
        base["projection"] = {
            "output": "seven-section-assembled-yaml",
            "palette_mode": "preserve-core-hex-and-role",
            "typography_mode": "translate-semantic-style-to-prompt",
            "decoration_mode": "assign-vocabulary-to-layout-zones",
            "decoration_entries": decoration_rows,
            "closing_intent": "append-core-closing-statement",
        }
    elif renderer == "html":
        base["projection"] = {
            "output": "html-theme-token-manifest",
            "css_token_refs": {
                "background": ref("themes", theme_id, "visual_base.background_color"),
                "primary": ref("themes", theme_id, "visual_base.color_palette.primary.hex"),
                "secondary": ref("themes", theme_id, "visual_base.color_palette.secondary.hex"),
                "accent": ref("themes", theme_id, "visual_base.color_palette.accent.hex"),
                "support": ref("themes", theme_id, "visual_base.color_palette.support"),
            },
            "font_ref": ref("themes", theme_id, "visual_base.typography"),
            "renderer_override_ref": None,
            "decoration_entries": decoration_rows,
            "fallback": "references/html-generation-rules.md",
        }
    else:
        base["projection"] = {
            "output": "pptx-theme-master-manifest",
            "master_name": f"theme--{theme_id}",
            "background_set_ref": f"prompt_system/pptx_background_sets/{theme_id}.yaml",
            "background_asset_policy": "six-image2-backgrounds-on-child-layouts",
            "color_token_refs": {
                "background": ref("themes", theme_id, "visual_base.background_color"),
                "primary": ref("themes", theme_id, "visual_base.color_palette.primary.hex"),
                "secondary": ref("themes", theme_id, "visual_base.color_palette.secondary.hex"),
                "accent": ref("themes", theme_id, "visual_base.color_palette.accent.hex"),
                "support": ref("themes", theme_id, "visual_base.color_palette.support"),
            },
            "font_ref": ref("themes", theme_id, "visual_base.typography"),
            "renderer_override_ref": None,
            "decoration_entries": decoration_rows,
            "fallback": "references/pptx-generation-rules.md",
        }
    return base


def layout_adapter(renderer: str, path: Path, data: dict[str, Any]) -> dict[str, Any]:
    validate_layout_core(path, data)
    layout_id = str(data["id"])
    family = layout_family(layout_id)
    slots = data.get("slots") or []
    base = {
        "schema_version": 1,
        "kind": "layout_adapter",
        "renderer": renderer,
        "layout_id": layout_id,
        "family": family,
        "support_status": "baseline-from-core",
        "source": {
            "path": f"prompt_system/layouts/{path.name}",
            "sha256": source_sha256(path),
        },
        "core_refs": {
            "media_requirement": ref("layouts", layout_id, "media_requirement"),
            "slots": ref("layouts", layout_id, "slots"),
            "safe_area": ref("layouts", layout_id, "safe_area"),
            "alignment": ref("layouts", layout_id, "alignment_rules"),
            "visual_balance": ref("layouts", layout_id, "visual_balance"),
            "decoration": ref("layouts", layout_id, "decoration") if "decoration" in data else None,
        },
    }
    if "element_contracts" in data:
        base["core_refs"]["element_contracts"] = ref("layouts", layout_id, "element_contracts")

    slot_rows = []
    for index, slot in enumerate(slots):
        if not isinstance(slot, dict):
            continue
        slot_id = str(slot.get("id", f"slot-{index + 1}"))
        slot_ref = ref("layouts", layout_id, f"slots[id={slot_id}]")
        # Keep legacy slot_entries stable; typed PPTX rows live in the
        # renderer-owned Variant projection.
        role = placeholder_type(slot_id)
        if "region" in slot:
            geometry_ref = f"{slot_ref}.region"
            geometry_kind = "region"
        elif "placement" in slot:
            geometry_ref = f"{slot_ref}.placement"
            geometry_kind = "placement"
        elif "anchor" in slot:
            geometry_ref = f"{slot_ref}.anchor"
            geometry_kind = "anchor"
        else:
            geometry_ref = slot_ref
            geometry_kind = "semantic-only"
        row: dict[str, Any] = {
            "slot_id": slot_id,
            "source_ref": slot_ref,
            "geometry_ref": geometry_ref,
            "geometry_kind": geometry_kind,
            "semantic_role": role,
        }
        if renderer == "image2":
            row["projection"] = "describe-relative-position-and-hierarchy"
        elif renderer == "html":
            row["element"] = "div.el"
            row["geometry_transform"] = "percent-region-to-1920x1080-px"
            row["edit_contract"] = html_edit_contract(role)
        else:
            row["placeholder_type"] = role
            row["geometry_transform"] = "percent-region-to-13.333x7.5-inch"
            row["materialization"] = {
                "picture": "native-image",
                "chart": "native-chart-or-hybrid",
                "table": "native-table",
            }.get(role, "native-text-or-shape")
        slot_rows.append(row)

    if renderer == "image2":
        base["projection"] = {
            "output": "layout-description-and-decoration-zones",
            "coordinate_style": "natural-language-relative-position",
            "slot_entries": slot_rows,
            "exact_coordinates_in_prompt": False,
        }
    elif renderer == "html":
        base["projection"] = {
            "output": "html-layout-manifest",
            "component": f"layout-{family}",
            "canvas_px": [1920, 1080],
            "slot_entries": slot_rows,
            "rules": [
                "references/html-generation-rules.md",
                "references/html-layout-patterns.md",
            ],
        }
        variant_path = PROMPT_SYSTEM / "renderers" / "html" / "layout-variants" / path.name
        if variant_path.exists():
            base["projection"]["variant_catalog"] = {
                "path": f"prompt_system/renderers/html/layout-variants/{path.name}",
                "sha256": source_sha256(variant_path),
            }
    else:
        background_role = pptx_background_role(family, slots)
        variant_catalog = load_catalog()
        variant_entry = (variant_catalog.get("layouts") or {}).get(layout_id) or {}
        base["projection"] = {
            "output": "pptx-layout-and-placeholder-manifest",
            "layout_name": f"layout--{layout_id}",
            "parent_master_ref": "selected-theme-adapter.projection.master_name",
            "background_role": background_role,
            "background_role_ref": f"selected-theme-adapter.projection.background_set_ref#roles[id={background_role}]",
            "placeholder_geometry_policy": "role-placeholder-first-then-fit-core-content-semantics",
            "slide_size_in": [13.333, 7.5],
            "slot_entries": slot_rows,
            "rules": ["references/pptx-generation-rules.md"],
        }
        if variant_entry:
            base["projection"]["coordinate_system"] = variant_catalog.get("coordinate_system")
            base["projection"]["placeholder_contract"] = variant_entry.get("base_placeholder_contract")
            base["projection"]["variant_catalog"] = {
                "path": "prompt_system/renderers/pptx/layout-variants/catalog.yaml",
                "sha256": source_sha256(CATALOG_PATH),
                "variants": variant_entry.get("variants", []),
                "selection": "content-driven-with-optional-layout_variant_id-override",
            }
    if "element_contracts" in data:
        base["projection"]["element_contracts"] = data["element_contracts"]
    return base


def expected_files() -> dict[Path, str]:
    generated: dict[Path, str] = {}
    theme_paths = sorted((PROMPT_SYSTEM / "themes").glob("*.yaml"))
    layout_paths = sorted(
        path
        for path in (PROMPT_SYSTEM / "layouts").glob("*.yaml")
        if path.stem not in RETIRED_LAYOUT_IDS
    )

    for renderer in RENDERERS:
        for path in theme_paths:
            data = load_yaml(path)
            target = OUTPUT_ROOT / renderer / "themes" / path.name
            generated[target] = dump_yaml(theme_adapter(renderer, path, data))
        for path in layout_paths:
            data = load_yaml(path)
            target = OUTPUT_ROOT / renderer / "layouts" / path.name
            generated[target] = dump_yaml(layout_adapter(renderer, path, data))

    manifest = {
        "schema_version": 1,
        "generated_by": "scripts/generate_renderer_adapters.py",
        "source_of_truth": {
            "themes": "prompt_system/themes/*.yaml",
            "layouts": "prompt_system/layouts/*.yaml",
        },
        "renderers": list(RENDERERS),
        "counts": {
            "themes": len(theme_paths),
            "layouts": len(layout_paths),
            "theme_adapters": len(theme_paths) * len(RENDERERS),
            "layout_adapters": len(layout_paths) * len(RENDERERS),
            "total_adapters": (len(theme_paths) + len(layout_paths)) * len(RENDERERS),
        },
        "coverage": {
            "image2": {"themes": len(theme_paths), "layouts": len(layout_paths), "mode": "core-native"},
            "html": {
                "themes": len(theme_paths),
                "layouts": len(layout_paths),
                "tuned_theme_overrides": 0,
                "mode": "baseline-complete",
            },
            "pptx": {
                "themes": len(theme_paths),
                "layouts": len(layout_paths),
                "tuned_theme_overrides": 0,
                "mode": "baseline-complete",
            },
        },
        "theme_ids": [load_yaml(path)["id"] for path in theme_paths],
        "layout_ids": [load_yaml(path)["id"] for path in layout_paths],
    }
    generated[OUTPUT_ROOT / "manifest.yaml"] = dump_yaml(manifest)
    return generated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if generated adapters are stale or missing")
    args = parser.parse_args()
    generated = expected_files()

    stale: list[str] = []
    for path, expected in generated.items():
        actual = path.read_text(encoding="utf-8") if path.exists() else None
        if actual != expected:
            stale.append(str(path.relative_to(ROOT)))
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(expected, encoding="utf-8", newline="\n")

    expected_paths = set(generated)
    renderer_source_roots = {
        OUTPUT_ROOT / "html" / "layout-variants",
        OUTPUT_ROOT / "pptx" / "layout-variants",
    }
    extras = sorted(
        path.relative_to(ROOT)
        for path in OUTPUT_ROOT.glob("*/*/*.yaml")
        if path not in expected_paths
        and not any(root in path.parents for root in renderer_source_roots)
    ) if OUTPUT_ROOT.exists() else []

    if args.check and (stale or extras):
        for item in stale:
            print(f"STALE_OR_MISSING {item}")
        for item in extras:
            print(f"EXTRA {item}")
        return 1

    action = "verified" if args.check else "generated"
    print(f"{action} {len(generated) - 1} adapters + manifest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
