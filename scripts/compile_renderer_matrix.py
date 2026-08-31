#!/usr/bin/env python3
"""Resolve canonical theme/layout YAML and adapters into a renderer matrix JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

from pptx_variant_runtime import load_catalog, project_placeholders


ROOT = Path(__file__).resolve().parents[1]
RETIRED_LAYOUT_IDS = {
    "toc-2",
    "toc-2-image-left",
    "toc-2-panel-rows",
    "toc-2-vertical",
}


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return data


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_hex(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        raise ValueError(f"Expected six-digit hex color, got {value!r}")
    return value.upper()


def mix(color_a: str, color_b: str, amount_b: float) -> str:
    def rgb(value: str) -> tuple[int, int, int]:
        value = value.lstrip("#")
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]

    a = rgb(color_a)
    b = rgb(color_b)
    values = [round(x * (1 - amount_b) + y * amount_b) for x, y in zip(a, b)]
    return "#" + "".join(f"{value:02X}" for value in values)


def theme_record(path: Path) -> dict[str, Any]:
    data = load_yaml(path)
    theme_id = str(data["id"])
    visual = data["visual_base"]
    palette = visual["color_palette"]
    background = valid_hex(visual["background_color"])
    primary = valid_hex(palette["primary"]["hex"])
    secondary = valid_hex(palette["secondary"]["hex"])
    accent = valid_hex(palette["accent"]["hex"])
    support_items = palette.get("support") or []
    support = [valid_hex(item["hex"]) for item in support_items if isinstance(item, dict) and "hex" in item]
    neutral_items = palette.get("neutral") or []
    neutral = [valid_hex(item["hex"]) for item in neutral_items if isinstance(item, dict) and "hex" in item]
    surface_item = palette.get("surface")
    if isinstance(surface_item, dict) and surface_item.get("hex"):
        surface = valid_hex(surface_item["hex"])
    else:
        surface = support[0] if support else mix(background, primary, 0.12)
    html_adapter = load_yaml(ROOT / "prompt_system/renderers/html/themes" / path.name)
    pptx_adapter = load_yaml(ROOT / "prompt_system/renderers/pptx/themes" / path.name)
    return {
        "id": theme_id,
        "display_name": data["display_name"],
        "colors": {
            "background": background,
            "primary": primary,
            "secondary": secondary,
            "accent": accent,
            "support": support,
            "neutral": neutral,
            "surface": surface,
        },
        "typography": visual.get("typography") or {},
        "mood": visual.get("mood") or [],
        "illustration_style": visual.get("illustration_style") or {},
        "source": {
            "path": f"prompt_system/themes/{path.name}",
            "sha256": file_hash(path),
        },
        "support_status": {
            "html": html_adapter["support_status"],
            "pptx": pptx_adapter["support_status"],
        },
    }


def layout_record(path: Path) -> dict[str, Any]:
    data = load_yaml(path)
    layout_id = str(data["id"])
    html_adapter = load_yaml(ROOT / "prompt_system/renderers/html/layouts" / path.name)
    pptx_adapter = load_yaml(ROOT / "prompt_system/renderers/pptx/layouts" / path.name)
    html_slots = {row["slot_id"]: row for row in html_adapter["projection"]["slot_entries"]}
    pptx_slots = {row["slot_id"]: row for row in pptx_adapter["projection"]["slot_entries"]}
    variant_catalog = load_catalog()
    variant_entry = (variant_catalog.get("layouts") or {}).get(layout_id) or {}
    variants = variant_entry.get("variants") or []
    representative_content = {
        "item_count": 3,
        "has_image": True,
        "quote": "sample",
        "items": [{"body": "representative module body text"}] * 3,
    }
    # Give the renderer projection the adapter's explicit semantic type.  The
    # core Layout owns geometry; the PPTX adapter owns how each slot becomes a
    # native placeholder.  This keeps baseline (non-Variant) Layouts usable
    # without copying a second coordinate system into the Variant catalog.
    projection_slots = []
    for slot in data["slots"]:
        slot_id = str(slot.get("id"))
        adapter_slot = pptx_slots.get(slot_id, {})
        projection_slots.append(
            {
                **slot,
                "placeholder_type": adapter_slot.get("placeholder_type"),
                "semantic_role": adapter_slot.get("semantic_role"),
                "content_kind": adapter_slot.get("materialization"),
            }
        )
    pptx_projection = project_placeholders(
        layout_id,
        projection_slots,
        representative_content if variants else {},
    )
    slots = []
    for slot in data["slots"]:
        slot_id = str(slot["id"])
        geometry_source = "region"
        region = slot.get("region")
        if region is None and isinstance(slot.get("placement"), dict):
            placement = slot["placement"]
            default = str(placement.get("default", "main"))
            region = placement.get(f"{default}_region") or placement.get("main_region") or placement.get("watermark_region")
            geometry_source = f"placement.{default}_region"
        if region is None and isinstance(slot.get("anchor"), list) and len(slot["anchor"]) == 2:
            anchor_x, anchor_y = slot["anchor"]
            region = [max(0, min(90, anchor_x - 5)), max(0, min(95, anchor_y - 2.5)), 10, 5]
            geometry_source = "anchor-derived-region"
        if not isinstance(region, list) or len(region) != 4 or not all(isinstance(v, (int, float)) for v in region):
            raise ValueError(f"Invalid region in {path}: {slot_id}")
        slots.append(
            {
                "id": slot_id,
                "region": region,
                "geometry_source": geometry_source,
                "weight": slot.get("weight", "secondary"),
                "note": slot.get("note", ""),
                "semantic_role": html_slots[slot_id]["semantic_role"],
                "html": {
                    "element": html_slots[slot_id]["element"],
                    "edit_contract": html_slots[slot_id]["edit_contract"],
                },
                "pptx": {
                    "placeholder_type": pptx_slots[slot_id]["placeholder_type"],
                    "materialization": pptx_slots[slot_id]["materialization"],
                },
            }
        )
    # Atomic PPTX projection is the renderer contract. Keep the legacy core
    # slot rows above for cross-renderer traceability, and expose the actual
    # typed rows separately so composite slots never masquerade as body text.
    typed_rows = []
    for row in pptx_projection["placeholder_schema"]:
        typed_rows.append({
            "id": row["id"],
            "source_slot_id": row.get("source_slot_id"),
            "placeholder_type": row["placeholder_type"],
            "content_kind": row["content_kind"],
            "optional": row.get("optional", False),
            "style_role": row.get("style_role", row["placeholder_type"]),
            "frame_policy": row.get("frame_policy", "fixed" if row["placeholder_type"] in {"title", "subtitle"} else "content-fit"),
            "region": row["region"],
            "geometry_transform": "percent-region-to-1920x1080-stage-then-2-over-3-artifact",
        })
    return {
        "id": layout_id,
        "display_name": data["display_name"],
        "family": html_adapter["family"],
        "media_requirement": data["media_requirement"],
        "safe_area": data["safe_area"],
        "alignment_rules": data["alignment_rules"],
        "visual_balance": data["visual_balance"],
        "slots": slots,
        "pptx": {
            "coordinate_system": variant_catalog.get("coordinate_system"),
            "layout_name": pptx_projection["layout_name"],
            "variant_candidates": pptx_projection["variant_candidates"],
            "selected_variant_id": pptx_projection["selected_variant_id"],
            "selection_basis": pptx_projection["selection_basis"],
            "placeholder_schema": typed_rows,
            "surfaces": pptx_projection.get("surfaces", []),
            "variant_catalog_path": "prompt_system/renderers/pptx/layout-variants/catalog.yaml",
        },
        "source": {
            "path": f"prompt_system/layouts/{path.name}",
            "sha256": file_hash(path),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    themes = [theme_record(path) for path in sorted((ROOT / "prompt_system/themes").glob("*.yaml"))]
    layouts = [
        layout_record(path)
        for path in sorted((ROOT / "prompt_system/layouts").glob("*.yaml"))
        if path.stem not in RETIRED_LAYOUT_IDS
    ]
    matrix = {
        "schema_version": 1,
        "source_of_truth": {
            "themes": "prompt_system/themes/*.yaml",
            "layouts": "prompt_system/layouts/*.yaml",
            "adapters": "prompt_system/renderers/{image2,html,pptx}/{themes,layouts}/*.yaml",
        },
        "counts": {
            "themes": len(themes),
            "layouts": len(layouts),
            "combinations_per_renderer": len(themes) * len(layouts),
        },
        "themes": themes,
        "layouts": layouts,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(matrix["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
