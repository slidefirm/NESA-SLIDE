#!/usr/bin/env python3
"""Compile one Theme's six PPTX background roles into Image2 YAML + runtime JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from pptx_background_runtime import resolve_background_set


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def palette(theme: dict[str, Any]) -> dict[str, Any]:
    visual = theme["visual_base"]
    colors = visual["color_palette"]
    primary = colors["primary"]
    secondary = colors["secondary"]
    accent = colors["accent"]
    neutrals = colors.get("neutral") or colors.get("support") or []
    if isinstance(neutrals, dict):
        neutrals = [neutrals]
    return {
        "background": visual["background_color"],
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
        "support": neutrals,
    }


def typeface(theme: dict[str, Any], role: str) -> dict[str, Any]:
    typography = theme["visual_base"]["typography"][role]
    return {
        "family": typography["family"],
        "weight": typography["weight"],
        "size_pt": "not rendered; background contains no text",
    }


def assembled(theme: dict[str, Any], background_set: dict[str, Any], role: dict[str, Any]) -> dict[str, Any]:
    visual = theme["visual_base"]
    colors = palette(theme)
    zones = role["decoration_zones"]
    primary_blank = role["blank_regions"][0]["region"]
    zone_block: dict[str, Any] = {
        "rule": (
            "只允許非文字的邊角與背景裝飾；所有裝飾必須避開 manifest 指定的 blank_regions。"
            "禁止文字、字母、數字、logo 字樣、假卡片、圖表、表格、UI 面板、內容框與 placeholder 外框。"
        )
    }
    for name, description in zones.items():
        zone_block[name] = {"decoration": description}
    support = [
        {"color": row["hex"], "usage": [row.get("use", "背景支援色")]} for row in colors["support"]
    ]
    return {
        "page_type_and_mood": {
            "prompt": f"16:9 PowerPoint 母片底圖，角色為 {role['label']}；{role['structure']}。專業沉穩、出版排版、品牌感強，但完全不顯示文字與內容架構。"
        },
        "visual_base_2a": {
            "background": {
                "color": colors["background"],
                "texture": f"{visual['background_style']}；以材質、漸層、光影與抽象出版裝飾建立層次，blank region 維持低細節低對比。",
                "bleed": "full",
            },
            "typography": {
                "heading": {"color": colors["primary"]["hex"], **typeface(theme, "heading")},
                "body": {"color": [colors["secondary"]["hex"], "theme neutral"], **typeface(theme, "body"), "line_spacing": "not applicable"},
            },
            "color_system": {
                "primary": {"color": colors["primary"]["hex"], "usage": [colors["primary"]["use"]]},
                "secondary": {"color": colors["secondary"]["hex"], "usage": [colors["secondary"]["use"]]},
                "accent": {"color": colors["accent"]["hex"], "usage": [colors["accent"]["use"]]},
                "support": support,
            },
            "illustration_style": {"type": "無", "note": "不放插圖人物；只使用背景材質、抽象色場、攝影紋理與邊角裝飾。"},
        },
        "corner_decoration_2b": zone_block,
        "layout_description": {
            "structure": role["structure"],
            "title_region": {
                "horizontal_range": f"{primary_blank[0]}%-{primary_blank[0] + primary_blank[2]}%",
                "vertical_range": f"{primary_blank[1]}%-{primary_blank[1] + primary_blank[3]}%",
                "description": "這是 PowerPoint Placeholder 的保留空白區，不在底圖中繪製文字或框線。",
            },
            "body_region": {
                "horizontal_range": f"{primary_blank[0]}%-{primary_blank[0] + primary_blank[2]}%",
                "vertical_range": f"{primary_blank[1]}%-{primary_blank[1] + primary_blank[3]}%",
                "description": "整片區域保持低細節、低對比、連續且乾淨，供母片疊加 Placeholder。",
            },
            "image_column": "none",
            "alignment_rule": "底圖只負責視覺重量與空白平衡；所有內容對齊由 PPTX 母片 Placeholder 決定。",
        },
        "content": {
            "visible_text": "none",
            "visible_numbers": "none",
            "visible_logos": "none",
            "visible_content_structure": "none; no cards, charts, tables, frames, grids, panels, or placeholder outlines",
        },
        "safe_zone_constraints": {
            "hard_constraint": f"Keep the entire reserved blank region {primary_blank} free of high-contrast detail and foreground objects.",
            "edge_rule": "Only low-priority texture may bleed; decorative accents stay inside declared decoration zones.",
            "exception": "Background texture and color fields may bleed full canvas, but must not create readable glyphs or content structure.",
        },
        "closing_design_intent": {
            "prompt": f"生成一張成熟的 {theme['display_name']} PowerPoint 母片底圖。{background_set['generation_policy']['required']} {background_set['generation_policy']['blank_region_rule']}"
        },
    }


def runtime_manifest(theme: dict[str, Any], background_set: dict[str, Any]) -> dict[str, Any]:
    colors = palette(theme)
    heading = theme["visual_base"]["typography"]["heading"]["family"]
    body = theme["visual_base"]["typography"]["body"]["family"]
    background_hex = colors["background"].lstrip("#")
    red, green, blue = (int(background_hex[index:index + 2], 16) for index in (0, 2, 4))
    luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255.0
    if luminance < 0.45:
        text_primary = next((row["hex"] for row in colors["support"] if "淺" in row.get("use", "")), "#F0EDE5")
        text_secondary = "#B7B1A7"
    else:
        text_primary = colors["primary"]["hex"]
        text_secondary = colors["secondary"]["hex"]
    return {
        "schema_version": 1,
        "kind": "pptx_background_runtime_manifest",
        "theme_id": theme["id"],
        "master_name": f"theme--{theme['id']}--image-background",
        "canvas": background_set["canvas"],
        "colors": {
            "background": colors["background"],
            "primary_text": text_primary,
            "secondary_text": text_secondary,
            "accent": colors["accent"]["hex"],
        },
        "fonts": {"heading": heading, "body": body},
        "placeholder_styles": background_set["placeholder_styles"],
        "roles": background_set["roles"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--background-set", required=True)
    parser.add_argument("--runtime-output", required=True)
    args = parser.parse_args()
    set_path = (ROOT / args.background_set).resolve()
    background_set = load_yaml(set_path)
    theme_path = (ROOT / background_set["theme_ref"]).resolve()
    theme = load_yaml(theme_path)
    preflight = resolve_background_set(theme["id"], background_set_id=set_path.stem, require_assets=False)
    if preflight["status"] != "ready":
        raise ValueError(json.dumps(preflight, ensure_ascii=False))
    written = []
    for role in background_set["roles"]:
        output = (ROOT / role["prompt_yaml"]).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(yaml.safe_dump(assembled(theme, background_set, role), allow_unicode=True, sort_keys=False, width=110), encoding="utf-8", newline="\n")
        written.append(str(output.relative_to(ROOT)))
    runtime_path = (ROOT / args.runtime_output).resolve()
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime = runtime_manifest(theme, background_set)
    runtime.update({
        "background_set_id": set_path.stem,
        "source_manifest": str(set_path.relative_to(ROOT)).replace("\\", "/"),
        "selection_basis": "explicit-background-set",
        "seed": background_set.get("seed") or background_set.get("generation_seed"),
        "provenance": background_set.get("provenance") or {},
    })
    runtime_path.write_text(json.dumps(runtime, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"theme": theme["id"], "prompts": written, "runtime": str(runtime_path.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
