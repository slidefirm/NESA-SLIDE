#!/usr/bin/env python3
"""Render an HTML-safe layout catalog per theme from a compiled renderer matrix."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from html_edit_framework import (
    EDITABLE_PLAYER_CSS,
    editable_player_markup,
    ensure_edit_mode_asset,
    validate_editable_html,
    validate_edit_layer_positions,
    validate_edit_module_structures,
)
from html_font_system import google_fonts_head
from html_layout_catalog import filter_html_layouts, load_html_layout_catalog
from html_motion_runtime import (
    motion_runtime_root_attributes,
    motion_runtime_script,
    motion_runtime_style,
)
from html_production_renderer import (
    GENERATED_TEXT_MIN_PX,
    MEDIA_PLACEHOLDER_CSS,
    PRODUCTION_CSS,
    apply_media_placeholder_policy,
    infer_page_horizontal_alignment,
    materialize_editable_production_markup,
    normalize_generated_css_font_sizes,
    render_production_layout,
    theme_tokens,
)


CW, CH = 1920, 1080


def slot_copy(role: str, slot_id: str) -> str:
    if role == "decoration":
        return ""
    if role == "title":
        return "清楚的重點標題"
    if role == "subtitle":
        return "用一句話補充背景與用途"
    if role == "picture":
        return "圖片內容區"
    if role == "chart":
        return "數據視覺區"
    if role == "table":
        return "比較資訊區"
    return "重點內容"


def font_size(role: str, height: float) -> int:
    if role == "title":
        return max(28, min(76, int(height * 0.42)))
    if role == "subtitle":
        return max(20, min(38, int(height * 0.34)))
    return max(18, min(32, int(height * 0.22)))


def render_slide(
    theme: dict[str, Any],
    layout: dict[str, Any],
    index: int,
    total: int,
    page_content: dict[str, Any] | None = None,
) -> str:
    variant = layout.get("html_variant") or {}
    variant_attributes = "".join(
        f' data-{attribute}="{html.escape(str(variant[key]))}"'
        for key, attribute in (
            ("composition_variant", "composition-variant"),
            ("header_mode", "header-mode"),
            ("surface_mode", "surface-mode"),
        )
        if variant.get(key)
    )
    media_mode = layout.get("media_mode")
    media_treatment = layout.get("media_treatment")
    media_attribute = (
        f' data-media-mode="{html.escape(str(media_mode))}"' if media_mode else ""
    )
    media_treatment_attribute = (
        f' data-media-treatment="{html.escape(str(media_treatment))}"' if media_treatment else ""
    )
    image_variant = str(layout.get("image_variant") or "").strip().lower()
    image_variant_attribute = (
        f' data-image-variant="{html.escape(image_variant)}"'
        if media_mode == "with-image" and image_variant in {"raster", "photo"}
        else ""
    )
    photo_brief = str(
        (page_content or {}).get("photo_brief")
        or (page_content or {}).get("hero_image_alt")
        or ""
    ).strip()
    photo_brief_attribute = (
        f' data-photo-brief="{html.escape(photo_brief, quote=True)}"'
        if image_variant == "photo" and photo_brief
        else ""
    )

    production = render_production_layout(layout, page_content)
    if production is not None:
        resolved_layout_variant = str(layout.get("resolved_layout_variant") or "").strip()
        requested_layout_variant = str(
            (page_content or {}).get("layout_variant_id") or ""
        ).strip()
        if resolved_layout_variant:
            variant_attributes += (
                f' data-layout-variant-id="{html.escape(resolved_layout_variant)}"'
            )
        if requested_layout_variant:
            variant_attributes += (
                f' data-requested-layout-variant-id="{html.escape(requested_layout_variant)}"'
            )
        production = apply_media_placeholder_policy(
            production,
            layout["id"],
            media_treatment,
        )
        page_alignment = (
            "center"
            if 'data-layout-flow-align="center"' in production
            else "right"
            if 'data-layout-flow-align="end"' in production
            else infer_page_horizontal_alignment(production)
        )
        production = materialize_editable_production_markup(production, page_alignment)
        return (
            f'<section class="slide{" active" if index == 0 else ""}" id="s{index + 1}" data-index="{index}" '
            f'data-page-number="{index + 1}" data-page-count="{total}" '
            f'data-layout-id="{html.escape(layout["id"])}" data-production-family="{html.escape(layout["family"])}"'
            f' data-page-horizontal-align="{page_alignment}"'
            f' data-content-binding="{("page-composition" if page_content is not None else "layout-fixture")}"'
            f'{media_attribute}{media_treatment_attribute}{image_variant_attribute}{photo_brief_attribute}{variant_attributes}>'
            f'<div class="content" data-content-area="true">{production}</div>'
            f'</section>'
        )
    colors = theme["colors"]
    elements = []
    content_area_elements = []
    centered_stack = layout.get("visual_balance", {}).get("method") == "centered-title-edge-decor"
    page_alignment = "center" if centered_stack else "left"
    for slot in layout["slots"]:
        x, y, w, h = slot["region"]
        left, top, width, height = x * 19.2, y * 10.8, w * 19.2, h * 10.8
        role = slot["semantic_role"]
        classes = ["el", f"role-{role}"]
        if role == "picture":
            classes.append("picture-placeholder")
        label = html.escape(slot["id"])
        content = html.escape(slot_copy(role, slot["id"]))
        size = max(GENERATED_TEXT_MIN_PX, font_size(role, height))
        fit_text = role in {"title", "subtitle"}
        dimensions = (
            f"width:max-content;height:auto;max-width:{width:.2f}px;max-height:{height:.2f}px;"
            if fit_text
            else f"width:{width:.2f}px;height:{height:.2f}px;"
        )
        in_content_area = centered_stack and slot["id"] in {"title", "subtitle", "speaker", "org"}
        position = "left:0px;top:0px;" if in_content_area else f"left:{left:.2f}px;top:{top:.2f}px;"
        style = f"{position}{dimensions}font-size:{size}px;"
        markup = (
            f'<div class="{" ".join(classes)}" data-slot-id="{label}" data-role="{role}" '
            f'data-edit-horizontal-align="{page_alignment}" data-edit-alignment-source="page-title" '
            f'{"data-edit-kind=\"text\" " if fit_text else ""}'
            f'{"data-edit-fit=\"text\" " if fit_text else ""}'
            f'style="{style}"><span class="slot-label">{label}</span>'
            f'<span class="slot-copy">{content}</span></div>'
        )
        (content_area_elements if in_content_area else elements).append(markup)
    if content_area_elements:
        left, top, right, bottom = layout["safe_area"]
        area_style = (
            f"left:{left * 19.2:.2f}px;top:{top * 10.8:.2f}px;"
            f"width:{(right - left) * 19.2:.2f}px;height:{(bottom - top) * 10.8:.2f}px;"
        )
        elements.insert(
            0,
            f'<div class="layout-content-area" data-content-area="cover" data-auto-layout="vertical-stack" style="{area_style}">'
            + "".join(content_area_elements)
            + "</div>",
        )
    return (
        f'<section class="slide{" active" if index == 0 else ""}" id="s{index + 1}" data-index="{index}" '
        f'data-page-number="{index + 1}" data-page-count="{total}" '
        f'data-layout-id="{html.escape(layout["id"])}" data-page-horizontal-align="{page_alignment}"{media_attribute}{media_treatment_attribute}{image_variant_attribute}{variant_attributes}>'
        + "".join(elements)
        + '</section>'
    )


def render_catalog(
    theme: dict[str, Any],
    layouts: list[dict[str, Any]],
    page_contents: list[dict[str, Any] | None] | None = None,
) -> str:
    colors = theme["colors"]
    tokens = theme_tokens(theme)
    total = len(layouts)
    resolved_contents = page_contents if page_contents is not None else [None] * total
    if len(resolved_contents) != total:
        raise ValueError("page_contents must match the rendered Layout sequence")
    slides = "\n".join(
        render_slide(theme, layout, index, total, resolved_contents[index])
        for index, layout in enumerate(layouts)
    )
    player = editable_player_markup(slides, CW, CH)
    motion_style = motion_runtime_style()
    motion_script = motion_runtime_script()
    font_head = google_fonts_head(theme)
    return f"""<!doctype html>
<html lang="zh-Hant" data-theme="{html.escape(theme['id'])}" data-theme-label="{html.escape(theme['display_name'])}" {motion_runtime_root_attributes()}><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(theme['display_name'])} Layout Catalog</title>
{font_head}
<style data-css-owner="renderer-base">
:root{{--bg:{tokens['background']};--primary:{colors['primary']};--secondary:{colors['secondary']};--accent:{tokens['accent']};--accent-ink:{tokens['accent_ink']};--surface-accent-ink:{tokens['surface_accent_ink']};--accent-text:{tokens['accent_text']};--surface:{tokens['surface']};--text:{tokens['text']};--muted:{tokens['muted']};--surface-text:{tokens['surface_text']};--surface-muted:{tokens['surface_muted']};--support-accent:{tokens['support_accent']};--font-heading:{tokens['heading_font']};--font-body:{tokens['body_font']};--font-mono:{tokens['mono_font']};--font-display:{tokens['display_font']};}}
*{{box-sizing:border-box}}html,body{{width:100%;height:100%;margin:0;overflow:hidden;background:#000;font-family:var(--font-body)}}
#stage{{width:{CW}px;height:{CH}px}}
.slide{{position:absolute;inset:0;width:{CW}px;height:{CH}px;display:none;overflow:hidden;background:var(--bg);color:var(--primary);background-image:linear-gradient(rgba(127,127,127,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(127,127,127,.035) 1px,transparent 1px);background-size:48px 48px}}
.slide.active{{display:block}}.el{{position:absolute;overflow:hidden;padding:0;border:0;border-radius:0;background:transparent;line-height:1.2}}.el[data-edit-fit="text"]{{overflow:visible}}.slide:not([data-production-family]) .el{{padding:14px 18px;border:1.5px solid color-mix(in srgb,var(--accent) 42%,transparent);border-radius:12px;background:color-mix(in srgb,var(--surface) 82%,transparent);display:flex;flex-direction:column;justify-content:center}}.layout-content-area{{position:absolute;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:28px}}.layout-content-area>.el{{position:relative;flex:0 0 auto;text-align:center}}
.role-title{{padding:0;border:0;background:transparent;font-weight:800}}.role-subtitle{{padding:0;border:0;background:transparent;color:var(--secondary);font-weight:500}}.role-decoration{{padding:0;border:0;border-radius:0;background:var(--accent);opacity:.62}}
.picture-placeholder{{background:linear-gradient(32deg,transparent 49.5%,color-mix(in srgb,var(--accent) 24%,transparent) 50%,transparent 50.5%),linear-gradient(-32deg,transparent 49.5%,color-mix(in srgb,var(--accent) 24%,transparent) 50%,transparent 50.5%),var(--surface)}}
.slot-label{{position:absolute;left:12px;top:8px;font:500 {GENERATED_TEXT_MIN_PX}px/1 var(--font-mono);color:var(--secondary);opacity:.78}}.slot-copy{{display:block}}.role-title .slot-label,.role-subtitle .slot-label,.role-decoration .slot-label{{display:none}}
{normalize_generated_css_font_sizes(PRODUCTION_CSS + MEDIA_PLACEHOLDER_CSS)}
{EDITABLE_PLAYER_CSS}
</style>
{motion_style}
</head><body>{player}{motion_script}</body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--theme", action="append")
    parser.add_argument("--limit-layouts", type=int)
    parser.add_argument("--media-mode", choices=("no-image", "with-image"))
    parser.add_argument("--include-excluded", action="store_true", help="Include photo-dependent layouts for renderer QA only")
    args = parser.parse_args()
    matrix = json.loads(Path(args.matrix).read_text(encoding="utf-8"))
    selected = set(args.theme or [])
    themes = [theme for theme in matrix["themes"] if not selected or theme["id"] in selected]
    layouts = matrix["layouts"]
    catalog = load_html_layout_catalog()
    if args.media_mode:
        media_ids = set(catalog["layout_ids_by_media_mode"][args.media_mode])
        layouts = [layout for layout in layouts if layout["id"] in media_ids]
    elif not args.include_excluded:
        allowed_ids = set(filter_html_layouts((layout["id"] for layout in layouts), catalog))
        layouts = [layout for layout in layouts if layout["id"] in allowed_ids]
    layouts = layouts[: args.limit_layouts or None]
    for layout in layouts:
        layout["media_mode"] = catalog["layout_media_mode_by_id"].get(layout["id"])
        layout["media_treatment"] = catalog["media_rendering_policy"].get(layout["media_mode"])
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    ensure_edit_mode_asset(output)
    for theme in themes:
        document = render_catalog(theme, layouts)
        validate_editable_html(document)
        validate_edit_layer_positions(document)
        validate_edit_module_structures(document)
        (output / f"{theme['id']}.html").write_text(document, encoding="utf-8", newline="\n")
    print(json.dumps({"themes": len(themes), "layouts_per_theme": len(layouts), "slides": len(themes) * len(layouts)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
