#!/usr/bin/env python3
"""Render one content-filled HTML demo from a shared Theme + Layout matrix."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from pathlib import Path
from typing import Any

from html_edit_framework import EDITABLE_PLAYER_CSS, editable_player_markup, ensure_edit_mode_asset, validate_editable_html
from html_font_system import google_fonts_head, theme_font_contract
from python_chart_renderer import render_line_chart_svg


CW, CH = 1920, 1080
CONTENT_MARGIN = 96


def rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def relative_luminance(hex_color: str) -> float:
    def channel(value: int) -> float:
        normalized = value / 255
        return normalized / 12.92 if normalized <= 0.04045 else ((normalized + 0.055) / 1.055) ** 2.4

    red, green, blue = (channel(value) for value in rgb(hex_color))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: str, second: str) -> float:
    bright, dark = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (bright + 0.05) / (dark + 0.05)


def mix_color(foreground: str, background: str, foreground_weight: float) -> str:
    first = rgb(foreground)
    second = rgb(background)
    values = [round(a * foreground_weight + b * (1 - foreground_weight)) for a, b in zip(first, second)]
    return "#" + "".join(f"{value:02X}" for value in values)


def best_text_color(background: str, candidates: list[str]) -> str:
    return max(candidates, key=lambda candidate: contrast_ratio(background, candidate))


def ensure_contrast(color: str, background: str, fallback: str, minimum: float) -> str:
    if contrast_ratio(color, background) >= minimum:
        return color
    for step in range(1, 21):
        candidate = mix_color(fallback, color, step / 20)
        if contrast_ratio(candidate, background) >= minimum:
            return candidate
    return fallback


def theme_tokens(colors: dict[str, Any]) -> dict[str, str]:
    background = colors["background"]
    support = list(colors.get("support") or [])
    explicit_surface = colors.get("surface")
    surface_candidates = ([explicit_surface] if explicit_surface else []) + support + [background]
    distinct_surfaces = [candidate for candidate in surface_candidates if contrast_ratio(background, candidate) >= 1.06]
    if explicit_surface in distinct_surfaces:
        surface = explicit_surface
    else:
        surface = min(distinct_surfaces or surface_candidates, key=lambda candidate: abs(relative_luminance(candidate) - relative_luminance(background)))
    neutral = list(colors.get("neutral") or [])
    text_candidates = [colors["primary"], *neutral, "#111827", "#F8FAFC"]
    text = best_text_color(background, text_candidates)
    muted_candidate = colors["secondary"] if relative_luminance(background) >= 0.45 else mix_color(text, background, 0.68)
    muted = ensure_contrast(muted_candidate, background, text, 4.6)
    card_surface = mix_color(surface, background, 0.92)
    surface_text = best_text_color(card_surface, [text, colors["primary"], "#111827", "#F8FAFC"])
    primary_text = best_text_color(colors["primary"], ["#111827", "#F8FAFC"])
    support_accent = max((candidate for candidate in support if candidate != surface), key=lambda candidate: contrast_ratio(background, candidate), default=colors["accent"])
    surface_muted = ensure_contrast(mix_color(surface_text, card_surface, 0.68), card_surface, surface_text, 4.6)
    accent_on_bg = ensure_contrast(colors["accent"], background, text, 4.6)
    accent_on_surface = ensure_contrast(colors["accent"], card_surface, surface_text, 3.2)
    return {
        "background": background,
        "surface": surface,
        "card_surface": card_surface,
        "text": text,
        "muted": muted,
        "surface_text": surface_text,
        "surface_muted": surface_muted,
        "primary_text": primary_text,
        "support_accent": support_accent,
        "accent_on_bg": accent_on_bg,
        "accent_on_surface": accent_on_surface,
    }


def esc(value: Any) -> str:
    return html.escape(str(value)).replace("\n", "<br>")


def pos(layout: dict[str, Any], slot_id: str) -> str:
    slot = next(row for row in layout["slots"] if row["id"] == slot_id)
    x, y, w, h = slot["region"]
    return f"left:{x * 19.2:.1f}px;top:{y * 10.8:.1f}px;width:{w * 19.2:.1f}px;height:{h * 10.8:.1f}px"


def content_pos(region: list[float]) -> str:
    """Convert canvas-percent geometry into coordinates relative to the 96px content frame."""
    x, y, w, h = region
    return (
        f"left:{x * 19.2 - CONTENT_MARGIN:.1f}px;top:{y * 10.8 - CONTENT_MARGIN:.1f}px;"
        f"width:{w * 19.2:.1f}px;height:{h * 10.8:.1f}px"
    )


def fit_text_pos(region: list[float], relative_to_content: bool = False) -> str:
    """Keep the layout slot as a wrapping limit while making the editable box hug its text."""
    x, y, w, h = region
    left = x * 19.2 - (CONTENT_MARGIN if relative_to_content else 0)
    top = y * 10.8 - (CONTENT_MARGIN if relative_to_content else 0)
    return (
        f"left:{left:.1f}px;top:{top:.1f}px;width:max-content;height:auto;"
        f"max-width:{w * 19.2:.1f}px"
    )


def fit_text_size(region: list[float], use_content_width: bool = False) -> str:
    """Size a text object from its content while its Content Area owns alignment."""
    _, _, w, h = region
    max_width = "100%" if use_content_width else f"{w * 19.2:.1f}px"
    return (
        f"left:0px;top:0px;width:max-content;height:auto;"
        f"max-width:{max_width};max-height:{h * 10.8:.1f}px"
    )


def content_area_pos(bounds: list[float]) -> str:
    """Convert [left, top, right, bottom] percentages to one slide Content Area."""
    left, top, right, bottom = bounds
    return (
        f"left:{left * 19.2:.1f}px;top:{top * 10.8:.1f}px;"
        f"width:{(right - left) * 19.2:.1f}px;height:{(bottom - top) * 10.8:.1f}px"
    )


def fitted_card_regions(layout: dict[str, Any]) -> dict[str, list[float]]:
    """Fit card modules to content-area edges and center the whole composition vertically."""
    slots = {row["id"]: [float(value) for value in row["region"]] for row in layout["slots"]}
    module_ids = sorted((slot_id for slot_id in slots if slot_id.startswith("module-")), key=lambda value: int(value.split("-")[-1]))
    modules = [slots[slot_id] for slot_id in module_ids]
    min_x = min(row[0] for row in modules)
    max_x = max(row[0] + row[2] for row in modules)
    scale_x = 90 / (max_x - min_x)
    content_rows = [slots[slot_id] for slot_id in ["title", "subtitle", *module_ids]]
    min_y = min(row[1] for row in content_rows)
    max_y = max(row[1] + row[3] for row in content_rows)
    shift_y = 50 - (min_y + max_y) / 2
    fitted = {
        "title": [5, slots["title"][1] + shift_y, 90, slots["title"][3]],
        "subtitle": [5, slots["subtitle"][1] + shift_y, 90, slots["subtitle"][3]],
    }
    for slot_id in module_ids:
        x, y, w, h = slots[slot_id]
        fitted[slot_id] = [5 + (x - min_x) * scale_x, y + shift_y, w * scale_x, h]
    return fitted


def chrome(index: int, layout_id: str, meta_label: str) -> str:
    return (
        '<div class="slash slash-a"></div><div class="slash slash-b"></div>'
        '<div class="dots"></div><div class="top-rule"></div>'
        f'<div class="meta"><span>{esc(meta_label)}</span><span>{index + 1:02d} / {layout_id.upper()}</span></div>'
    )


def title_block(slide: dict[str, Any], layout: dict[str, Any]) -> str:
    title_region = next(row["region"] for row in layout["slots"] if row["id"] == "title")
    subtitle_region = next(
        (row["region"] for row in layout["slots"] if row["id"] == "subtitle"),
        None,
    )
    title = f'<div class="el page-title" data-edit-kind="text" data-edit-fit="text" style="{fit_text_pos(title_region)}">{esc(slide["title"])}</div>'
    if subtitle_region is None or not slide.get("subtitle"):
        return title
    return title + f'<div class="el page-subtitle" data-edit-kind="text" data-edit-fit="text" style="{fit_text_pos(subtitle_region)}">{esc(slide["subtitle"])}</div>'


def card(item: dict[str, Any], style: str, compact: bool = False, variant: str = "") -> str:
    metric = f'<div class="card-metric" data-edit-layer="metric">{esc(item["metric"])}</div>' if item.get("metric") else ""
    tags = ""
    if item.get("tags"):
        tags = '<div class="card-tags" data-edit-layer="text">' + "".join(f"<span>{esc(tag)}</span>" for tag in item["tags"]) + "</div>"
    tags_markup = f"\n      {tags}" if tags else ""
    classes = " ".join(value for value in ["el", "demo-card", "compact" if compact else "", variant] if value)
    return f'''<div class="{classes}" data-card-no="{esc(item['no'])}" data-edit-composite="card" style="{style}">
      <div class="card-bg" data-edit-layer="background"></div>
      <div class="card-no" data-edit-layer="text">{esc(item['no'])}</div>{metric}
      <div class="card-title" data-edit-layer="text">{esc(item['title'])}</div>
      <div class="card-body" data-edit-layer="text">{esc(item['body'])}</div>{tags_markup}
    </div>'''


def render_cover(slide: dict[str, Any], layout: dict[str, Any]) -> str:
    slots = {row["id"]: row["region"] for row in layout["slots"] if "region" in row}
    return f'''<div class="cover-ghost">{esc(slide.get('ghost', 'SYSTEM'))}</div><div class="cover-band"></div>
      <div class="cover-content-area" data-content-area="cover" data-auto-layout="vertical-stack" style="{content_area_pos(layout['safe_area'])}">
        <div class="el cover-title" data-edit-kind="text" data-edit-fit="text" style="{fit_text_size(slots['title'])}">{esc(slide['title'])}</div>
        <div class="cover-title-rule" data-layout-item="decoration"></div>
        <div class="el cover-subtitle" data-edit-kind="text" data-edit-fit="text" style="{fit_text_size(slots['subtitle'], use_content_width=True)}">{esc(slide['subtitle'])}</div>
        <div class="el cover-speaker" data-edit-kind="text" data-edit-fit="text" style="{fit_text_size(slots['speaker'], use_content_width=True)}">{esc(slide['speaker'])}</div>
        <div class="el cover-org" data-edit-kind="text" data-edit-fit="text" style="{fit_text_size(slots['org'], use_content_width=True)}">{esc(slide['org'])}</div>
      </div>
      <div class="cover-seal"><b>{esc(slide.get('seal_top', 'SF'))}</b><span>{esc(slide.get('seal_bottom', 'DEMO'))}</span></div>'''


def render_toc(slide: dict[str, Any], layout: dict[str, Any]) -> str:
    intro = slide["intro"]
    parts = [f'''<div class="el toc-intro" data-edit-composite="intro" style="{pos(layout, 'panel_left')}">
      <div class="toc-kicker" data-edit-layer="text">{esc(intro['kicker'])}</div><div class="toc-title" data-edit-layer="text">{esc(intro['title'])}</div><div class="toc-body" data-edit-layer="text">{esc(intro['body'])}</div>
      <div class="toc-stat" data-edit-layer="metric">{esc(intro['stat'])}</div><div class="toc-ghost">04</div></div>''']
    for i, item in enumerate(slide["items"], 1):
        parts.append(card(item, pos(layout, f"chapter-{i}"), compact=True, variant="toc-card"))
    return "".join(parts)


def render_cards(slide: dict[str, Any], layout: dict[str, Any]) -> str:
    title_font = 64 if len(slide["title"]) > 22 else 70
    count = len(slide["items"])
    columns, rows = ({2: (2, 1), 3: (3, 1), 4: (4, 1), 5: (5, 1), 6: (3, 2), 8: (4, 2)}).get(count, (min(count, 4), (count + 3) // 4))
    card_min_height = 500 if count == 2 else 480 if count == 3 else 420 if count in {4, 5} else 280
    if count <= 4:
        number_size, card_title_size, body_size = 56, 48, 28
    elif count == 5:
        number_size, card_title_size, body_size = 48, 40, 24
    else:
        number_size, card_title_size, body_size = 40, 34, 22
    parts = [
        f'<div class="el page-title" data-edit-kind="text" data-edit-fit="text" style="left:0;top:0;width:max-content;height:auto;max-width:100%;font-size:{title_font}px">{esc(slide["title"])}</div>',
        f'<div class="el page-subtitle" data-edit-kind="text" data-edit-fit="text" style="left:0;top:0;width:max-content;height:auto;max-width:100%">{esc(slide.get("subtitle", ""))}</div>',
    ]
    compact = count >= 4
    for i, item in enumerate(slide["items"], 1):
        parts.append(card(item, "", compact=compact))
    area_style = (
        f"--card-columns:{columns};--card-rows:{rows};--card-min-height:{card_min_height}px;"
        f"--card-number-size:{number_size}px;--card-title-size:{card_title_size}px;--card-body-size:{body_size}px"
    )
    return f'<div class="cards-frame" data-card-count="{count}" data-content-frame="edge-fit" data-content-area="cards" data-auto-layout="card-grid" style="{area_style}">' + "".join(parts) + "</div>"


def render_cycle(slide: dict[str, Any], layout: dict[str, Any]) -> str:
    """Render a true closed-loop diagram inside the shared cycle Content Area."""
    items = slide["items"]
    if len(items) not in {5, 6}:
        raise ValueError("cycle renderer requires five or six items")
    # Keep both the loop and its nodes on one true circle.  The shared
    # cycle-hub-6 layout needs six equal-angle nodes; the five-node variant is
    # retained for older demos that used the same layout family.
    if len(items) == 6:
        # Same canonical traversal as the production renderer: right-upper
        # 01 → right-middle 02 → right-lower 03 → left-lower 04 →
        # left-middle 05 → left-upper 06 → 01.
        cycle_angles = (-60, 0, 60, 120, 180, 240)
        node_centers = [
            (864 + 320 * math.cos(math.radians(angle)), 444 + 320 * math.sin(math.radians(angle)))
            for angle in cycle_angles
        ]
        node_size = 190
        paths = []
        for angle in cycle_angles:
            start = math.radians(angle + 17)
            end = math.radians(angle + 43)
            paths.append(
                "M {:.1f} {:.1f} A 320 320 0 0 1 {:.1f} {:.1f}".format(
                    864 + 320 * math.cos(start),
                    444 + 320 * math.sin(start),
                    864 + 320 * math.cos(end),
                    444 + 320 * math.sin(end),
                )
            )
        ring_radius = 320
    else:
        node_centers = [(864, 119), (1173, 344), (1055, 707), (673, 707), (555, 344)]
        node_size = 210
        paths = [
            "M 975.2 138.6 A 325 325 0 0 1 1120.1 243.9",
            "M 1188.8 455.3 A 325 325 0 0 1 1133.4 625.7",
            "M 953.6 756.4 A 325 325 0 0 1 774.4 756.4",
            "M 594.6 625.7 A 325 325 0 0 1 539.2 455.3",
            "M 607.9 243.9 A 325 325 0 0 1 752.8 138.6",
        ]
        ring_radius = 325
    nodes = []
    for index, (item, (center_x, center_y)) in enumerate(zip(items, node_centers), 1):
        style = (
            f"left:{center_x - node_size / 2:.1f}px;top:{center_y - node_size / 2:.1f}px;"
            f"width:{node_size}px;height:{node_size}px"
        )
        nodes.append(f'''<div class="el cycle-node cycle-node-{index}" data-edit-composite="cycle-node" style="{style}">
          <span class="cycle-no" data-edit-layer="metric">{esc(item['no'])}</span>
          <span class="cycle-copy"><b class="cycle-title" data-edit-layer="text">{esc(item['title'])}</b><em class="cycle-body" data-edit-layer="text">{esc(item['body'])}</em></span>
        </div>''')
    # Visible arcs only occupy the open gaps between nodes, keeping arrowheads
    # out of the editable circles while preserving a closed-loop reading path.
    arrows = "".join(f'<path d="{path}" marker-end="url(#cycle-arrow)"/>' for path in paths)
    return f'''<div class="cycle-frame" data-content-frame="radial-balance" data-content-area="cycle" data-cycle-geometry="circle">
      <svg class="cycle-path" viewBox="0 0 1728 888" aria-hidden="true">
        <defs><marker id="cycle-arrow" markerUnits="userSpaceOnUse" markerWidth="22" markerHeight="22" viewBox="0 0 22 22" refX="20" refY="11" orient="auto"><path d="M2,2 L20,11 L2,20 z"/></marker></defs>
        <circle class="cycle-ring" cx="864" cy="444" r="{ring_radius}"/>
        {arrows}
      </svg>
      <div class="el cycle-hub" data-edit-composite="cycle-hub" style="left:674px;top:254px;width:380px;height:380px">
        <span class="cycle-kicker" data-edit-layer="text">DECISION LOOP</span>
        <b class="cycle-hub-title" data-edit-layer="text">{esc(slide['title'])}</b>
        <span class="cycle-hub-body" data-edit-layer="text">{esc(slide.get('subtitle', ''))}</span>
      </div>
      {''.join(nodes)}
    </div>'''


def render_before_after(slide: dict[str, Any], layout: dict[str, Any]) -> str:
    before, after = slide["before"], slide["after"]
    if len(before["items"]) != len(after["items"]):
        raise ValueError("before-after demo requires the same number of paired items")
    pair_count = len(before["items"])
    if not 2 <= pair_count <= 5:
        raise ValueError("before-after demo supports two to five paired items")
    dense = pair_count == 5 or max(
        len(before["title"]), len(after["title"]),
        len(before["subtitle"]), len(after["subtitle"]),
    ) > 18
    header_height = 248 if dense else 220
    row_top = header_height + 30
    row_gap = 10
    row_height = round((816 - row_top - row_gap * (pair_count - 1)) / pair_count)
    title_size = 48 if dense else 60
    subtitle_size = 28 if dense else 32
    pair_font_size = 30 if dense else 38

    def header(key: str, side: str) -> str:
        data = slide[key]
        source_slot = next(row for row in layout["slots"] if row["id"] == key + "-header")
        x, _, width, _ = source_slot["region"]
        style = f"left:{x * 19.2 - CONTENT_MARGIN:.1f}px;top:0;width:{width * 19.2:.1f}px;height:{header_height}px"
        return f'''<div class="el comparison-state-header {side}" data-edit-composite="before-after-{side}-header" style="{style}">
          <span class="comparison-state-label" data-edit-layer="text" data-edit-position="flow">{esc(data['label'])}</span>
          <b class="comparison-state-title" data-edit-layer="text" data-edit-position="flow">{esc(data['title'])}</b>
          <span class="comparison-state-subtitle" data-edit-layer="text" data-edit-position="flow">{esc(data['subtitle'])}</span>
        </div>'''

    rows = "".join(
        f'''<div class="el comparison-pair-row" data-edit-composite="before-after-pair-{index}" style="left:0;top:{row_top + (index - 1) * (row_height + row_gap)}px;width:1728px;height:{row_height}px">
          <span class="comparison-pair-index" data-edit-layer="metric">{index:02d}</span>
          <b class="comparison-pair-before" data-edit-layer="text" data-edit-position="flow">{esc(before_item)}</b>
          <span class="comparison-pair-arrow" data-edit-layer="icon">→</span>
          <b class="comparison-pair-after" data-edit-layer="text" data-edit-position="flow">{esc(after_item)}</b>
        </div>'''
        for index, (before_item, after_item) in enumerate(zip(before["items"], after["items"]), 1)
    )
    return (
        '<div class="comparison-pair-frame" data-density="medium" '
        'data-content-frame="visual-balance" data-auto-fill-cap="soft" data-fill-ratio="0.88" '
        f'style="top:132px;height:816px;--comparison-title-size:{title_size}px;'
        f'--comparison-subtitle-size:{subtitle_size}px;--comparison-pair-font:{pair_font_size}px">'
        + header("before", "before")
        + header("after", "after")
        + rows
        + '</div>'
    )


def render_process(slide: dict[str, Any], layout: dict[str, Any]) -> str:
    nodes = "".join(f'''<div class="process-node"><span data-edit-layer="metric">{esc(item['no'])}</span><b data-edit-layer="text">{esc(item['title'])}</b><p data-edit-layer="text">{esc(item['body'])}</p></div>''' for item in slide["steps"])
    node_count = max(1, min(len(slide["steps"]), 6))
    track_style = f'{pos(layout, "steps")};--process-count:{node_count}'
    return title_block(slide, layout) + f'<div class="el process-track" data-edit-composite="process" data-process-count="{node_count}" style="{track_style}">{nodes}</div><div class="el process-note" data-edit-composite="note" style="{pos(layout, "note")}"><span class="process-note-text" data-edit-layer="text">{esc(slide["note"])}</span></div>'


def render_kpi(slide: dict[str, Any], layout: dict[str, Any]) -> str:
    metrics = "".join(f'''<div class="metric"><span data-edit-layer="text">{esc(item['label'])}</span><b data-edit-layer="metric">{esc(item['value'])}</b><em data-edit-layer="text">{esc(item['delta'])}</em></div>''' for item in slide["metrics"])
    return title_block(slide, layout) + f'<div class="el metrics" data-edit-composite="metrics" style="{pos(layout, "scorecards")}">{metrics}</div><div class="el takeaway" data-edit-composite="takeaway" style="{pos(layout, "takeaway")}"><span class="takeaway-text" data-edit-layer="text">{esc(slide["takeaway"])}</span></div>'


def render_chart(slide: dict[str, Any], layout: dict[str, Any]) -> str:
    chart_svg = render_line_chart_svg(
        slide["labels"],
        [(series["name"], series["values"]) for series in slide["series"]],
        family="theme-demo-line",
        width=1500,
        height=600,
        domain=(0, 100),
        aria_label="Theme demo 多序列趨勢折線圖",
    )
    labels = "".join(f'<span data-edit-layer="text">{esc(label)}</span>' for label in slide["labels"])
    legends = "".join(f'<span class="legend-{i}" data-edit-layer="text"><i></i>{esc(s["name"])}</span>' for i, s in enumerate(slide["series"]))
    y_labels = "".join(f'<span data-edit-layer="metric">{value}</span>' for value in ["100", "75", "50", "25", "0"])
    end_value = slide["series"][0]["values"][-1]
    return f'''<div class="el chart-title" data-edit-kind="text" data-edit-fit="text" style="left:96px;top:96px;width:max-content;height:auto;max-width:1728px">{esc(slide['title'])}</div>
      <div class="el chart-y-axis" data-edit-composite="chart-axis" style="left:185px;top:220px;width:80px;height:600px">{y_labels}</div>
      <div class="el chart-wrap" data-edit-kind="visual" data-chart-renderer="python-matplotlib-svg" style="left:285px;top:220px;width:1500px;height:600px">{chart_svg}</div>
      <div class="el chart-value" data-edit-kind="text" data-edit-fit="text" style="left:1650px;top:270px;width:max-content;height:auto;max-width:150px">{end_value}%</div>
      <div class="el chart-labels" data-edit-composite="chart-labels" style="left:285px;top:830px;width:1500px;height:42px">{labels}</div>
      <div class="el chart-legend" data-edit-composite="chart-legend" style="left:285px;top:900px;width:1500px;height:54px">{legends}<small data-edit-layer="text">{esc(slide['note'])}</small></div>'''


def render_quote(slide: dict[str, Any], layout: dict[str, Any]) -> str:
    quote_region = next(row["region"] for row in layout["slots"] if row["id"] == "quote")
    attribution_region = next(row["region"] for row in layout["slots"] if row["id"] == "attribution")
    lines = str(slide["quote"]).splitlines() or [str(slide["quote"])]
    max_line_length = max(len(line) for line in lines)
    width_limited = int((quote_region[2] * 19.2 - 40) / max(max_line_length, 1))
    height_limited = int((quote_region[3] * 10.8 - 20) / (len(lines) * 1.2))
    quote_size = max(78, min(112, width_limited, height_limited))
    return f'''<div class="quote-rule"></div><div class="el quote" data-edit-kind="text" data-edit-fit="text" style="{fit_text_pos(quote_region)};font-size:{quote_size}px">{esc(slide['quote'])}</div><div class="el quote-by" data-edit-kind="text" data-edit-fit="text" style="{fit_text_pos(attribution_region)}">{esc(slide['attribution'])}</div><div class="quote-mark">01</div>'''


def render_closing(slide: dict[str, Any], layout: dict[str, Any]) -> str:
    title_region = next(row["region"] for row in layout["slots"] if row["id"] == "closing_title")
    contact_parts = [part.strip() for part in re.split(r"[·×]", slide["contact"]) if part.strip()]
    contact_rows = "".join(
        f'<span class="closing-contact-text" data-edit-layer="text">{esc(part)}</span>'
        for part in contact_parts
    )
    return f'''<div class="closing-panel"></div><div class="closing-strips"><i></i><i></i><i></i></div><div class="el closing-title" data-edit-kind="text" data-edit-fit="text" style="{fit_text_pos(title_region)}">{esc(slide['title'])}</div><div class="el closing-body" data-edit-kind="text" data-edit-fit="text" style="left:230px;top:525px;width:max-content;height:auto;max-width:615px">{esc(slide['body'])}</div><div class="el closing-contact" data-edit-composite="contact" style="{pos(layout, 'social_icons')}">{contact_rows}</div>'''


RENDERERS = {"cover": render_cover, "toc": render_toc, "cards": render_cards, "cycle": render_cycle, "before-after": render_before_after, "process": render_process, "kpi": render_kpi, "chart": render_chart, "quote": render_quote, "closing": render_closing}


def render_document(theme: dict[str, Any], layouts: dict[str, Any], demo: dict[str, Any]) -> str:
    colors = theme["colors"]
    tokens = theme_tokens(colors)
    fonts = theme_font_contract(theme)
    heading_font = fonts["heading_stack"]
    body_font = fonts["body_stack"]
    mono_font = fonts["mono_stack"]
    display_font = fonts["display_stack"]
    font_head = google_fonts_head(theme)
    meta_label = demo.get("meta_label", f"{theme['id'].replace('-', ' ').upper()} · HTML DEMO")
    slides = []
    for index, spec in enumerate(demo["slides"]):
        layout = layouts[spec["layout_id"]]
        content = RENDERERS[spec["kind"]](spec, layout)
        slides.append(f'<section class="slide{" active" if index == 0 else ""}" id="s{index + 1}" data-index="{index}" data-layout-id="{esc(spec["layout_id"])}">{chrome(index, spec["layout_id"], meta_label)}<div class="content-layer">{content}</div></section>')
    player = editable_player_markup("".join(slides), CW, CH)
    return f'''<!doctype html><html lang="zh-Hant" data-theme="{esc(theme['id'])}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(demo['title'])}</title>
{font_head}
<style>
:root{{--bg:{tokens['background']};--gold:{colors['primary']};--teal:{colors['secondary']};--orange:{colors['accent']};--support-accent:{tokens['support_accent']};--accent-on-bg:{tokens['accent_on_bg']};--accent-on-surface:{tokens['accent_on_surface']};--surface:{tokens['surface']};--card-surface:{tokens['card_surface']};--text:{tokens['text']};--muted:{tokens['muted']};--surface-text:{tokens['surface_text']};--surface-muted:{tokens['surface_muted']};--primary-text:{tokens['primary_text']};--font-heading:{heading_font};--font-body:{body_font};--font-mono:{mono_font};--font-display:{display_font}}}
*{{box-sizing:border-box}}html,body{{width:100%;height:100%;margin:0;overflow:hidden;background:#090909;font-family:var(--font-body)}}#stage{{width:{CW}px;height:{CH}px}}
.slide{{position:absolute;inset:0;display:none;width:{CW}px;height:{CH}px;overflow:hidden;background:var(--bg);color:var(--text)}}.slide.active{{display:block}}.content-layer{{position:absolute;inset:0;z-index:2}}.cards-frame{{position:absolute;left:96px;top:96px;width:1728px;height:888px;display:grid;grid-template-columns:repeat(var(--card-columns),minmax(0,1fr));grid-template-rows:auto auto repeat(var(--card-rows),minmax(var(--card-min-height),auto));align-content:center;gap:24px 28px}}.cards-frame>.page-title,.cards-frame>.page-subtitle{{grid-column:1/-1;position:relative}}.cards-frame>.demo-card{{position:relative;width:auto;height:auto}}[data-auto-layout].layout-materialized{{display:block}}.el{{position:absolute;overflow:hidden}}.el[data-edit-fit="text"]{{overflow:visible}}.meta{{position:absolute;left:70px;right:70px;top:42px;display:flex;justify-content:space-between;font:600 15px/1 var(--font-mono);letter-spacing:.15em;color:var(--gold);z-index:5}}.top-rule{{position:absolute;left:70px;right:70px;top:75px;height:1px;background:color-mix(in srgb,var(--gold) 36%,transparent)}}
.slash{{position:absolute;width:4px;height:118px;background:var(--gold);transform:rotate(45deg);z-index:1}}.slash-a{{left:40px;top:-30px}}.slash-b{{left:65px;top:-45px;opacity:.45}}.dots{{position:absolute;right:42px;bottom:38px;width:170px;height:98px;background-image:radial-gradient(var(--gold) 2px,transparent 2.5px);background-size:18px 18px;opacity:.45}}
.page-title{{font-size:62px;font-weight:800;line-height:1.08;letter-spacing:-.035em}}.page-subtitle{{font-size:26px;line-height:1.4;color:var(--muted)}}
.cover-ghost{{position:absolute;left:80px;top:118px;font:900 230px/.8 var(--font-display);letter-spacing:-.08em;color:color-mix(in srgb,var(--gold) 8%,transparent)}}.cover-band{{position:absolute;left:0;right:0;top:790px;height:16px;background:linear-gradient(90deg,var(--gold) 0 62%,var(--support-accent) 62% 70%,var(--orange) 70%)}}.cover-content-area{{position:absolute;display:flex;flex-direction:column;align-items:center;justify-content:center}}.cover-content-area>.el{{position:relative;flex:0 0 auto}}.cover-title{{font-size:105px;font-weight:850;line-height:1.08;text-align:center;letter-spacing:-.055em;color:var(--text)}}.cover-title-rule{{flex:0 0 auto;width:170px;height:7px;margin-top:26px;background:var(--gold)}}.cover-subtitle{{margin-top:38px;font:500 28px/1.4 var(--font-display);text-align:center;color:var(--gold)}}.cover-speaker{{margin-top:61px}}.cover-org{{margin-top:25px}}.cover-speaker,.cover-org{{font-size:20px;text-align:center;color:var(--muted);letter-spacing:.12em}}.cover-seal{{position:absolute;right:104px;bottom:103px;width:116px;height:116px;border:2px solid var(--gold);border-radius:50%;display:grid;place-content:center;text-align:center;transform:rotate(-8deg);color:var(--gold)}}.cover-seal b{{font:800 40px/1 var(--font-display)}}.cover-seal span{{font-size:13px;letter-spacing:.2em}}
.toc-intro{{padding:70px 54px;background:var(--gold);color:var(--primary-text)}}.toc-kicker{{font:700 17px/1 var(--font-mono);letter-spacing:.22em}}.toc-title{{margin-top:80px;font-size:66px;font-weight:850;line-height:1.08;letter-spacing:-.05em}}.toc-body{{margin-top:56px;font:500 25px/1.6 var(--font-display)}}.demo-card{{padding:38px 42px;color:var(--surface-text)}}.demo-card [data-edit-layer="text"]{{width:max-content;max-width:100%}}.card-bg{{position:absolute;inset:0;background:var(--card-surface);border-top:5px solid var(--gold)}}.demo-card:nth-of-type(even) .card-bg{{border-color:var(--teal)}}.card-no{{position:relative;font:700 18px/1 var(--font-mono);color:var(--accent-on-surface);letter-spacing:.14em}}.card-metric{{position:absolute;right:32px;top:27px;font:800 44px/1 var(--font-display);color:var(--surface-muted)}}.card-title{{position:relative;margin-top:58px;font-size:40px;font-weight:800;line-height:1.1;color:var(--surface-text)}}.card-body{{position:relative;margin-top:26px;color:var(--surface-muted);font:500 25px/1.5 var(--font-display)}}.demo-card.compact{{padding:28px 32px}}.demo-card.compact .card-title{{margin-top:26px;font-size:31px}}.demo-card.compact .card-body{{margin-top:14px;font-size:21px;line-height:1.35}}.demo-card.compact .card-metric{{font-size:30px}}
.cycle-frame{{position:absolute;left:96px;top:96px;width:1728px;height:888px}}.cycle-path{{position:absolute;inset:0;width:100%;height:100%;overflow:visible;z-index:0}}.cycle-path path,.cycle-ring{{fill:none;stroke:color-mix(in srgb,var(--support-accent) 78%,var(--gold));stroke-width:7;stroke-linecap:round}}.cycle-ring{{stroke-width:2;opacity:.34}}.cycle-path marker path{{fill:var(--accent-on-bg);stroke:none}}.cycle-hub{{z-index:2;display:flex;aspect-ratio:1/1;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:38px;border:2px solid color-mix(in srgb,var(--gold) 48%,transparent);border-radius:50%;background:var(--bg);box-shadow:0 0 0 18px color-mix(in srgb,var(--bg) 88%,transparent)}}.cycle-kicker{{font:750 16px/1 var(--font-mono);letter-spacing:.18em;color:var(--accent-on-bg)}}.cycle-hub-title{{display:block;margin-top:14px;max-width:292px;font:850 46px/1.04 var(--font-heading);letter-spacing:-.04em;color:var(--text)}}.cycle-hub-body{{display:block;margin-top:16px;max-width:292px;font:500 21px/1.34 var(--font-body);color:var(--muted)}}.cycle-node{{z-index:3;display:flex;aspect-ratio:1/1;flex-direction:column;align-items:center;justify-content:center;gap:8px;padding:24px;border:2px solid color-mix(in srgb,var(--gold) 28%,transparent);border-radius:50%;background:var(--card-surface);color:var(--surface-text);text-align:center;box-shadow:0 14px 36px color-mix(in srgb,var(--text) 10%,transparent)}}.cycle-node:nth-of-type(even){{border-color:color-mix(in srgb,var(--support-accent) 72%,transparent)}}.cycle-no{{flex:0 0 auto;font:850 44px/1 var(--font-display);color:var(--accent-on-surface)}}.cycle-copy{{display:flex;min-width:0;flex-direction:column;align-items:center;justify-content:center}}.cycle-title{{width:max-content;max-width:100%;font:800 34px/1.06 var(--font-heading);color:var(--surface-text)}}.cycle-body{{width:max-content;max-width:150px;margin-top:8px;font:500 18px/1.28 var(--font-body);font-style:normal;color:var(--surface-muted)}}
.ba-frame{{position:absolute;left:96px;top:96px;width:1728px;height:var(--ba-frame-height,888px)}}.ba-panel{{display:grid;grid-template-rows:auto auto minmax(var(--ba-signal-min-height),1fr) auto;align-content:stretch;gap:var(--ba-gap);padding:0 8px;overflow:visible}}.ba-header{{height:auto;padding:0 8px 14px;border-bottom:1px solid color-mix(in srgb,var(--gold) 35%,transparent)}}.ba-header span{{font:700 18px/1 var(--font-mono);letter-spacing:.18em;color:var(--muted)}}.ba-header b{{display:block;margin-top:12px;font-size:var(--ba-title-size);line-height:.98;color:var(--text)}}.ba-panel.active .ba-header span{{color:var(--accent-on-bg)}}.ba-panel.active .ba-header b{{color:var(--gold)}}.ba-subtitle{{height:auto;min-height:0;display:flex;align-items:center;padding:0 8px;font:500 var(--ba-subtitle-size)/1.28 var(--font-body);color:var(--muted);margin:0}}.ba-signal{{min-height:var(--ba-signal-min-height);height:auto;display:flex;align-items:flex-end;justify-content:space-between;gap:24px;margin:0 8px;border-bottom:1px solid color-mix(in srgb,var(--gold) 25%,transparent)}}.ba-signal i{{flex:1;max-width:110px;background:color-mix(in srgb,var(--gold) 18%,transparent);border-top:3px solid var(--gold)}}.ba-signal i:nth-child(1){{height:22%}}.ba-signal i:nth-child(2){{height:38%}}.ba-signal i:nth-child(3){{height:57%}}.ba-signal i:nth-child(4){{height:75%}}.ba-signal i:nth-child(5){{height:92%}}.ba-panel.muted{{opacity:1}}.ba-panel.muted .ba-header span,.ba-panel.muted .ba-header b,.ba-panel.muted .ba-subtitle,.ba-panel.muted li{{color:var(--muted)}}.ba-panel.muted .ba-signal{{opacity:.58}}.ba-panel.muted .ba-signal i:nth-child(1){{height:78%}}.ba-panel.muted .ba-signal i:nth-child(2){{height:38%}}.ba-panel.muted .ba-signal i:nth-child(3){{height:67%}}.ba-panel.muted .ba-signal i:nth-child(4){{height:30%}}.ba-panel.muted .ba-signal i:nth-child(5){{height:52%}}.ba-panel ul{{height:auto;list-style:none;padding:0 8px;margin:0}}.ba-panel li{{height:var(--ba-row-height);display:flex;align-items:center;gap:22px;border-bottom:1px solid color-mix(in srgb,var(--gold) 18%,transparent);font-size:var(--ba-item-size)}}.ba-panel li .ba-item-no{{flex:0 0 auto;font:700 20px/1 var(--font-mono);color:var(--accent-on-bg)}}.ba-item-text{{display:block;min-width:0}}.ba-rail{{position:absolute;left:809px;top:0;width:110px;height:100%;z-index:3;color:var(--gold)}}.ba-rail::before{{content:"";position:absolute;top:14%;bottom:14%;left:55px;width:1px;background:linear-gradient(transparent,var(--gold),transparent)}}.ba-rail b{{position:absolute;left:20px;top:calc(50% - 35px);display:grid;place-content:center;width:70px;height:70px;border:1px solid var(--gold);border-radius:50%;background:var(--bg);font-size:36px;margin:0}}
.process-track{{display:grid;grid-template-columns:repeat(var(--process-count,4),minmax(0,1fr));gap:clamp(24px,calc(66px - var(--process-count,4) * 7px),46px);overflow:hidden}}.process-track::before{{content:"";position:absolute;left:8%;right:8%;top:75px;height:2px;background:var(--gold)}}.process-node{{position:relative;min-width:0;padding-top:120px}}.process-node span{{position:absolute;left:0;top:35px;width:80px;height:80px;border:2px solid var(--gold);border-radius:50%;display:grid;place-content:center;background:var(--bg);font:700 18px/1 var(--font-mono);color:var(--accent-on-bg)}}.process-node b{{display:block;max-width:100%;font-size:36px;white-space:nowrap}}.process-node p{{max-width:100%;font:500 24px/1.45 var(--font-display);color:var(--muted)}}.process-note{{padding:25px 32px;border-left:8px solid var(--orange);background:color-mix(in srgb,var(--surface) 72%,transparent);font:500 24px/1.4 var(--font-display)}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:28px}}.metric{{padding:34px 32px;background:var(--card-surface);border-top:5px solid var(--gold);color:var(--surface-text)}}.metric span{{font-size:20px;color:var(--surface-muted)}}.metric b{{display:block;margin-top:30px;font:800 84px/1 var(--font-display);color:var(--surface-text)}}.metric em{{display:block;margin-top:24px;font:600 18px/1.3 var(--font-mono);color:var(--accent-on-surface);font-style:normal}}.takeaway{{display:flex;align-items:center;padding:0 38px;border-left:9px solid var(--gold);font:600 30px/1.35 var(--font-display);background:color-mix(in srgb,var(--gold) 8%,transparent)}}
.chart-title{{font-size:54px;font-weight:800;line-height:1.05}}.chart-wrap>.python-matplotlib-chart{{inset:0;width:100%;height:100%;overflow:visible}}.chart-labels{{display:flex;justify-content:space-between;color:var(--muted);font:600 18px/1 var(--font-mono)}}.chart-legend{{display:flex;align-items:center;gap:34px;font-size:18px;color:var(--muted)}}.chart-legend span{{display:flex;align-items:center;gap:10px}}.chart-legend i{{width:34px;height:4px;background:var(--gold)}}.chart-legend .legend-1 i{{background:var(--teal)}}.chart-legend small{{margin-left:auto}}
.quote-rule{{position:absolute;left:230px;top:205px;width:130px;height:8px;background:var(--orange)}}.quote{{font:700 100px/1.2 var(--font-display);letter-spacing:-.045em;color:var(--text)}}.quote-by{{font:700 21px/1 var(--font-mono);letter-spacing:.18em;color:var(--gold)}}.quote-mark{{position:absolute;right:150px;top:185px;font:900 430px/.8 var(--font-display);color:color-mix(in srgb,var(--gold) 8%,transparent)}}
.closing-panel{{position:absolute;left:0;top:0;width:57%;height:100%;background:var(--gold)}}.closing-strips{{position:absolute;right:0;top:0;width:43%;height:100%;display:grid;grid-template-columns:1fr 1fr 1fr}}.closing-strips i:nth-child(1){{background:var(--surface)}}.closing-strips i:nth-child(2){{background:var(--teal)}}.closing-strips i:nth-child(3){{background:var(--support-accent)}}.closing-title{{font-size:78px;font-weight:850;line-height:1.08;color:var(--primary-text)}}.closing-body{{font:600 27px/1.55 var(--font-display);color:color-mix(in srgb,var(--primary-text) 82%,transparent)}}.closing-contact{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px;padding:28px 18px;writing-mode:horizontal-tb;text-align:center;font:700 24px/1.25 var(--font-mono);letter-spacing:.12em;color:var(--text)}}.closing-contact-text{{position:static;width:100%;max-width:100%;overflow-wrap:anywhere}}
.cover-title{{font-size:96px;line-height:1.03}}.demo-card.compact{{padding:20px 28px}}.demo-card.compact .card-title{{margin-top:16px;font-size:28px}}.demo-card.compact .card-body{{margin-top:8px;font-size:18px;line-height:1.28}}.demo-card.compact .card-metric{{font-size:28px}}.ba-header{{padding:12px 8px}}.ba-header span{{font-size:16px}}.ba-header b{{margin-top:14px;line-height:.98}}.chart-wrap svg{{display:block;overflow:hidden}}.closing-title{{font-size:66px;line-height:1.02}}
.page-title{{font-size:70px}}.page-subtitle{{font-size:36px}}.cover-subtitle{{font-size:38px}}.cover-speaker{{font-size:23px}}.cover-org{{font-size:18px}}
.toc-title{{margin-top:68px;font-size:72px}}.toc-body{{margin-top:46px;font-size:29px;line-height:1.55}}.toc-stat{{position:absolute;left:54px;bottom:62px;font:700 18px/1 var(--font-mono);letter-spacing:.14em}}.toc-ghost{{position:absolute;right:34px;bottom:25px;height:134px;font:900 160px/.8 var(--font-display);color:rgba(26,26,26,.11)}}
.toc-card{{padding:34px 42px}}.toc-card::after{{content:attr(data-card-no);position:absolute;right:28px;bottom:20px;height:100px;font:900 125px/.8 var(--font-display);color:color-mix(in srgb,var(--gold) 7%,transparent)}}.toc-card .card-no{{font-size:22px}}.toc-card .card-title{{margin-top:30px;font-size:48px}}.toc-card .card-body{{margin-top:18px;font-size:28px;line-height:1.4;max-width:78%;position:relative;z-index:2}}
.demo-card:not(.compact) .card-title{{margin-top:44px;font-size:48px}}.demo-card:not(.compact) .card-body{{margin-top:22px;font-size:30px;line-height:1.45;max-width:88%}}.demo-card:not(.compact) .card-metric{{font-size:54px}}.card-tags{{position:absolute;left:42px;right:42px;bottom:36px;display:flex;gap:12px;flex-wrap:wrap}}.card-tags span{{padding:9px 14px;border:1px solid color-mix(in srgb,var(--surface-text) 36%,transparent);font:700 18px/1 var(--font-mono);color:var(--surface-text)}}
.demo-card.compact{{padding:18px 28px}}.demo-card.compact .card-no{{font-size:20px}}.demo-card.compact .card-title{{margin-top:11px;font-size:34px}}.demo-card.compact .card-body{{margin-top:5px;font-size:22px;line-height:1.25}}
.ba-content p{{font-size:30px}}.ba-content li{{height:102px;font-size:28px}}.ba-content li span{{font-size:19px}}
.process-node b{{font-size:40px}}.process-node p{{font-size:27px}}.process-note{{font-size:28px}}.metric span{{font-size:24px}}.metric b{{font-size:96px}}.metric em{{font-size:22px;font-weight:700}}.takeaway{{font-size:34px}}
.chart-title{{font-size:68px;line-height:1.08}}.chart-y-axis{{display:flex;flex-direction:column;justify-content:space-between;text-align:right;color:var(--muted);font:600 21px/1 var(--font-mono);padding:65px 0}}.chart-labels{{font-size:21px}}.chart-legend{{font-size:21px}}.chart-value{{color:var(--gold);font:800 36px/1 var(--font-mono)}}.quote{{font-size:112px}}.quote-by{{font-size:24px}}.closing-body{{font-size:31px}}.closing-contact{{font-size:28px}}
.demo-card.compact.toc-card{{padding:34px 42px}}.demo-card.compact.toc-card .card-no{{font-size:22px}}.demo-card.compact.toc-card .card-title{{margin-top:30px;font-size:48px}}.demo-card.compact.toc-card .card-body{{margin-top:18px;font-size:28px;line-height:1.4}}
.demo-card{{display:flex;flex-direction:column;align-items:flex-start;justify-content:center}}.demo-card .card-no{{position:relative;z-index:2;margin:0;font-size:56px;line-height:1;font-family:var(--font-display)}}.demo-card .card-title{{position:relative;z-index:2;margin:14px 0 0;font-size:48px;line-height:1.08}}.demo-card .card-body{{position:relative;z-index:2;margin:14px 0 0;max-width:88%;font-size:28px;line-height:1.4}}.demo-card .card-tags{{position:relative;left:auto;right:auto;bottom:auto;z-index:2;margin-top:24px}}.demo-card .card-metric{{z-index:2;top:34px;font-size:50px}}.demo-card.compact .card-no{{font-size:40px}}.demo-card.compact .card-title{{margin-top:10px;font-size:34px}}.demo-card.compact .card-body{{margin-top:8px;font-size:22px;line-height:1.3}}.demo-card.compact .card-tags{{margin-top:16px}}.demo-card.compact.toc-card .card-no{{font-size:52px}}.demo-card.compact.toc-card .card-title{{margin-top:14px;font-size:48px}}.demo-card.compact.toc-card .card-body{{margin-top:12px;font-size:28px;line-height:1.4}}
.cards-frame .demo-card .card-no{{font-size:var(--card-number-size)}}.cards-frame .demo-card .card-title{{font-size:var(--card-title-size);margin-top:12px}}.cards-frame .demo-card .card-body{{font-size:var(--card-body-size);margin-top:10px;line-height:1.35}}
.cover-band{{top:825px}}
.cover-title,.page-title,.toc-title,.card-title,.cycle-hub-title,.cycle-title,.ba-header b,.process-node b,.chart-title,.quote,.closing-title{{font-family:var(--font-heading)}}.cover-subtitle,.cover-speaker,.cover-org,.page-subtitle,.toc-body,.card-body,.cycle-hub-body,.cycle-body,.ba-subtitle,.ba-panel li,.process-node p,.process-note,.metric span,.takeaway,.closing-body{{font-family:var(--font-body)}}
[data-theme="product-strategy-signal"] .slash{{width:3px;height:86px;transform:none;background:var(--orange)}}[data-theme="product-strategy-signal"] .slash-a{{left:36px;top:0}}[data-theme="product-strategy-signal"] .slash-b{{left:47px;top:0;opacity:.22}}[data-theme="product-strategy-signal"] .top-rule{{background:color-mix(in srgb,var(--gold) 18%,transparent)}}[data-theme="product-strategy-signal"] .dots{{width:150px;height:78px;background-image:radial-gradient(var(--orange) 2.5px,transparent 3px);background-size:16px 16px;opacity:.28}}[data-theme="product-strategy-signal"] .cover-title-rule{{background:var(--orange)}}[data-theme="product-strategy-signal"] .cover-band{{height:10px;background:linear-gradient(90deg,var(--gold) 0 58%,var(--support-accent) 58% 66%,var(--orange) 66%)}}[data-theme="product-strategy-signal"] .cover-seal{{width:112px;height:76px;border-color:var(--orange);border-radius:4px;transform:none;color:var(--orange)}}[data-theme="product-strategy-signal"] .cover-seal b{{font-family:var(--font-body);font-size:30px}}[data-theme="product-strategy-signal"] .card-bg{{border:1px solid color-mix(in srgb,var(--gold) 14%,transparent);border-top:5px solid var(--orange)}}[data-theme="product-strategy-signal"] .demo-card:nth-of-type(even) .card-bg{{border-top-color:var(--support-accent)}}[data-theme="product-strategy-signal"] .card-metric{{color:var(--teal)}}[data-theme="product-strategy-signal"] .ba-panel.active .ba-header span{{color:var(--gold)}}[data-theme="product-strategy-signal"] .ba-panel.active .ba-header b{{color:var(--orange)}}[data-theme="product-strategy-signal"] .ba-panel.active .ba-signal i{{background:color-mix(in srgb,var(--orange) 18%,transparent);border-top-color:var(--orange)}}[data-theme="product-strategy-signal"] .ba-rail{{color:var(--orange)}}[data-theme="product-strategy-signal"] .ba-rail::before{{background:linear-gradient(transparent,var(--orange),transparent)}}[data-theme="product-strategy-signal"] .ba-rail b{{border-color:var(--orange)}}[data-theme="product-strategy-signal"] .process-track::before{{background:linear-gradient(90deg,var(--orange),var(--support-accent))}}[data-theme="product-strategy-signal"] .process-node span{{border-color:var(--orange);color:var(--orange)}}[data-theme="product-strategy-signal"] .process-node:last-child span{{border-color:var(--support-accent);color:var(--support-accent)}}[data-theme="product-strategy-signal"] .process-note{{border-left-color:var(--orange)}}[data-theme="product-strategy-signal"] .metric{{border-top-color:var(--orange)}}[data-theme="product-strategy-signal"] .metric:nth-child(even){{border-top-color:var(--support-accent)}}[data-theme="product-strategy-signal"] .takeaway{{border-left-color:var(--orange)}}[data-theme="product-strategy-signal"] .chart-value{{color:var(--orange)}}[data-theme="product-strategy-signal"] .quote-rule{{background:var(--orange)}}
[data-theme="product-strategy-signal"] .process-node span,[data-theme="product-strategy-signal"] .process-node:last-child span{{color:var(--accent-on-bg)}}
.comparison-pair-frame{{position:absolute;left:96px;width:1728px;overflow:visible}}.comparison-state-header{{position:absolute;display:flex;flex-direction:column;justify-content:center;gap:12px;padding:26px 42px;background:var(--card-surface);border:1px solid color-mix(in srgb,var(--gold) 34%,transparent);border-radius:14px}}.comparison-state-header>[data-edit-position="flow"]{{position:relative;left:auto;right:auto;top:auto;bottom:auto;translate:none}}.comparison-state-header.after{{border-color:var(--gold);background:color-mix(in srgb,var(--card-surface) 92%,var(--gold))}}.comparison-state-label{{font:700 20px/1 var(--font-mono);letter-spacing:.16em;color:var(--muted)}}.comparison-state-title{{font:850 var(--comparison-title-size,60px)/.98 var(--font-heading);letter-spacing:-.04em;color:var(--surface-text)}}.comparison-state-subtitle{{font:500 var(--comparison-subtitle-size,32px)/1.32 var(--font-body);color:var(--surface-muted)}}.comparison-pair-row{{position:absolute;display:grid;grid-template-columns:76px minmax(0,1fr) 108px minmax(0,1fr);align-items:center;column-gap:24px;padding:0 30px;border-bottom:1px solid color-mix(in srgb,var(--gold) 20%,transparent)}}.comparison-pair-row>[data-edit-position="flow"],.comparison-pair-row>.comparison-pair-index,.comparison-pair-row>.comparison-pair-arrow{{position:relative;left:auto;right:auto;top:auto;bottom:auto;translate:none}}.comparison-pair-index{{font:700 26px/1 var(--font-mono);color:var(--accent-on-bg)}}.comparison-pair-before,.comparison-pair-after{{font:700 var(--comparison-pair-font,38px)/1.2 var(--font-body);text-wrap:balance}}.comparison-pair-before{{color:var(--surface-muted)}}.comparison-pair-after{{color:var(--surface-text)}}.comparison-pair-arrow{{display:grid;place-content:center;width:68px;height:68px;border:2px solid var(--gold);border-radius:50%;font:800 34px/1 var(--font-heading);color:var(--gold);background:var(--bg)}}
{EDITABLE_PLAYER_CSS}
</style></head><body>{player}</body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--demo", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--theme-id", help="Temporarily render the demo with another shared Theme for cross-theme QA")
    args = parser.parse_args()
    matrix = json.loads(Path(args.matrix).read_text(encoding="utf-8"))
    demo = json.loads(Path(args.demo).read_text(encoding="utf-8"))
    theme_id = args.theme_id or demo["theme_id"]
    theme = next(row for row in matrix["themes"] if row["id"] == theme_id)
    layouts = {row["id"]: row for row in matrix["layouts"]}
    missing = [row["layout_id"] for row in demo["slides"] if row["layout_id"] not in layouts]
    if missing:
        raise ValueError(f"Unknown layouts: {missing}")
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    document = render_document(theme, layouts, demo)
    validate_editable_html(document)
    output.write_text(document, encoding="utf-8", newline="\n")
    ensure_edit_mode_asset(output.parent)
    print(json.dumps({"theme": theme["id"], "slides": len(demo["slides"]), "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
