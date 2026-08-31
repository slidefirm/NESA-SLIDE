#!/usr/bin/env python3
"""Render content-first, design-led editable HTML decks for the Theme Lab.

Unlike the matrix renderer, this entrypoint does not begin with a stock Layout
and pour short copy into it.  It consumes a complete deck assembly, gives each
subject one visual grammar and renders semantic compositions inside the shared
editable 1920x1080 player.
"""

from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from html_edit_framework import (
    EDITABLE_PLAYER_CSS,
    editable_player_markup,
    ensure_edit_mode_asset,
    validate_edit_layer_positions,
    validate_edit_module_structures,
    validate_editable_html,
)


ROOT = Path(__file__).resolve().parents[1]
CANVAS_W = 1920
CANVAS_H = 1080

def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def rich(value: Any) -> str:
    return esc(value).replace("\n", "<br>")


def headline(value: Any) -> str:
    """Prefer a deliberate punctuation break over a one-character tail."""

    text = str(value)
    if "\n" in text:
        return rich(text)
    if len(text.replace(" ", "")) >= 16:
        candidates = [
            index + 1
            for index, character in enumerate(text)
            if character in "，：；—" and 5 <= index <= len(text) - 6
        ]
        if candidates:
            split_at = min(candidates, key=lambda index: abs(index - len(text) / 2))
            return esc(text[:split_at]) + "<wbr>" + esc(text[split_at:])
    return esc(text)


def layer(
    class_name: str,
    content: Any,
    *,
    tag: str = "div",
    extra: str = "",
    position: str = "absolute",
    editable_root: bool = False,
) -> str:
    if position not in {"absolute", "flow"}:
        raise ValueError(f"Unsupported edit-layer position: {position}")
    root_class = "el " if editable_root else ""
    root_attrs = ' data-edit-kind="text"' if editable_root else ""
    fit = ' data-edit-fit="text"' if editable_root and position == "absolute" else ""
    return (
        f'<{tag} class="{root_class}{class_name}"{root_attrs} data-edit-layer="text"{fit} '
        f'data-edit-position="{position}" data-edit-vertical-align="center" {extra}>{content}</{tag}>'
    )


def loose_layer(
    class_name: str,
    content: Any,
    *,
    tag: str = "div",
    extra: str = "",
    position: str = "absolute",
) -> str:
    """Render an independently selectable loose text object."""

    return layer(
        class_name,
        content,
        tag=tag,
        extra=extra,
        position=position,
        editable_root=True,
    )


def footer_module(content: Any, composite: str) -> str:
    """Render a boxed footer as a real semantic module, not a loose text layer."""

    return f'''<div class="el scene-footer scene-footer-module" data-edit-kind="visual"
      data-edit-structure="module" data-edit-fit="container"
      data-edit-composite="{esc(composite)}" data-edit-role="footer-note">
      <div class="scene-footer-bg" data-edit-layer="background"
        data-edit-position="absolute" aria-hidden="true"></div>
      {layer("scene-footer-text", content, tag="p", position="flow")}
    </div>'''


def full_scene(content: str, layout_scope: str) -> str:
    return (
        f'<div class="scene" data-edit-layout-only="true" data-layout-scope="{esc(layout_scope)}" '
        f'data-visual-balance="content-bounds" '
        f'style="position:absolute;left:0;top:0;width:1728px;height:888px">{content}</div>'
    )


def split_scene(header: str, content: str, layout_scope: str, *, trailing: str = "") -> str:
    """Center sibling edit objects through a non-selectable layout frame."""

    return (
        f'<div class="scene scene-balance-frame" data-edit-layout-only="true" '
        f'data-layout-scope="{esc(layout_scope)}" data-visual-balance="content-bounds" '
        f'style="position:absolute;left:0;top:0;width:1728px;height:888px">'
        f'<div class="scene-region scene-header" data-edit-layout-only="true" '
        f'style="display:contents">{header}</div>'
        f'<div class="scene-region scene-content" data-edit-layout-only="true" '
        f'style="display:contents">{content}</div>'
        f'{trailing}</div>'
    )


def scene_header(slide: dict[str, Any]) -> str:
    vertical_stack = slide.get("_header_mode") in {"top", "side-left", "side-right"}
    position = "flow" if vertical_stack else "absolute"
    title = loose_layer(
        "scene-title",
        headline(slide["title"]),
        tag="h1",
        position=position,
        extra='data-title-stack-item="title"',
    )
    intro = loose_layer(
        "scene-intro",
        esc(slide["intro"]),
        tag="p",
        position=position,
        extra='data-title-stack-item="subtitle"',
    )
    if vertical_stack:
        return (
            f'<div class="scene-title-stack" data-title-flow="vertical" '
            f'data-edit-layout-only="true">{title}{intro}</div>'
        )
    return title + intro


def item_lines(items: list[str]) -> str:
    return "".join(
        f'<li>{layer("item-copy", esc(item), tag="span", position="flow")}</li>'
        for item in items
    )


def render_cover(slide: dict[str, Any]) -> str:
    visual = (
        '<div class="el cover-signature" data-edit-kind="visual" data-edit-layer="visual" data-edit-position="absolute" '
        'aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>'
    )
    body = f'''
      {loose_layer("cover-kicker", esc(slide["kicker"]))}
      {loose_layer("cover-title", rich(slide["title"]), tag="h1")}
      {loose_layer("cover-subtitle", esc(slide["subtitle"]), tag="p")}
      {loose_layer("cover-meta", esc(slide["meta"]))}
      {visual}
    '''
    return full_scene(body, slide["layout_id"])


def render_thesis(slide: dict[str, Any]) -> str:
    notes = "".join(
        f'''<li class="el thesis-note item-{index}" data-edit-kind="visual"
          data-edit-structure="module" data-edit-fit="container"
          data-edit-composite="{esc(slide["layout_id"])}-thesis-note-{index}">
          <div class="thesis-note-bg" data-edit-layer="background" data-edit-position="absolute" aria-hidden="true"></div>
          {layer("thesis-note-index", f"{index:02d}", tag="b", position="flow")}
          {layer("note-copy", esc(note), tag="span", position="flow")}
        </li>'''
        for index, note in enumerate(slide.get("notes", []), 1)
    )
    body = f'''
      <div class="el thesis-mark" data-edit-kind="visual" data-edit-layer="visual" data-edit-position="absolute" aria-hidden="true">“</div>
      {loose_layer("thesis-quote", rich(slide["quote"]), tag="blockquote")}
      {loose_layer("thesis-attribution", esc(slide["attribution"]))}
      <ol class="thesis-notes">{notes}</ol>
    '''
    return full_scene(body, slide["layout_id"])


def render_index(slide: dict[str, Any]) -> str:
    items = "".join(
        f'''<article class="el index-item item-{index}" data-edit-kind="visual"
          data-edit-structure="module" data-edit-fit="container"
          data-edit-composite="{esc(slide["layout_id"])}-index-item-{index}">
          <div class="index-item-bg" data-edit-layer="background" data-edit-position="absolute" aria-hidden="true"></div>
          {layer("index-label", esc(item["label"]), position="flow")}
          {layer("index-title", esc(item["title"]), tag="h2", position="flow")}
          {layer("index-body", esc(item["body"]), tag="p", position="flow")}
        </article>'''
        for index, item in enumerate(slide["items"], 1)
    )
    return split_scene(
        scene_header(slide),
        f'<div class="index-list count-{len(slide["items"])}">{items}</div>',
        slide["layout_id"],
    )


def render_contrast(slide: dict[str, Any]) -> str:
    panels = []
    for side in ("left", "right"):
        panel = slide[side]
        panels.append(
            f'''<section class="el contrast-panel contrast-{side}" data-edit-kind="visual"
              data-edit-structure="module" data-edit-fit="container"
              data-edit-composite="{esc(slide["layout_id"])}-contrast-panel-{side}">
              <div class="contrast-panel-bg" data-edit-layer="background"
                data-edit-position="absolute" aria-hidden="true"></div>
              {layer("contrast-label", "現況" if side == "left" else "目標", position="flow")}
              {layer("contrast-title", esc(panel["title"]), tag="h2", position="flow")}
              {layer("contrast-lead", esc(panel["lead"]), tag="p", position="flow")}
              <ul>{item_lines(panel["items"])}</ul>
            </section>'''
        )
    return split_scene(
        scene_header(slide),
        f'<div class="contrast-grid" data-auto-layout="grid">{"".join(panels)}</div>',
        slide["layout_id"],
    )


def render_columns(slide: dict[str, Any]) -> str:
    item_count = len(slide["items"])
    theme_id = slide.get("_theme_id", "")

    def render_item(index: int, item: dict[str, Any]) -> str:
        article = f'''<article class="el column-item item-{index}" data-edit-kind="visual"
            data-edit-structure="module" data-edit-fit="container" data-edit-composite="{esc(slide["layout_id"])}-column-card-{index}">
            <div class="column-item-bg" data-edit-layer="background" data-edit-position="absolute" aria-hidden="true"></div>
            {layer("column-tag", esc(item["tag"]), position="flow")}
            {layer("column-title", esc(item["title"]), tag="h2", position="flow")}
            {layer("column-body", esc(item["body"]), tag="p", position="flow")}
          </article>'''
        # Scent columns are intentionally the same kind of direct grid items as
        # the working timeline modules. A box-owning layout-only slot between
        # the grid and editable card steals resize ownership: the editor changes
        # the card while CSS Grid keeps the stale slot geometry.
        if theme_id in {"scent-veil-launch", "signal-route-atlas"}:
            return article
        return f'''<div class="column-slot item-{index}" data-edit-layout-only="true">{article}</div>'''

    items = "".join(render_item(index, item) for index, item in enumerate(slide["items"], 1))
    variable_width = ' data-allow-variable-width="true"' if slide["layout_id"] == "cards-1-plus-4" else ""
    return split_scene(
        scene_header(slide),
        f'<div class="column-grid count-{item_count}" data-edit-layout-only="true"{variable_width}>{items}</div>',
        slide["layout_id"],
    )

def render_flow(slide: dict[str, Any]) -> str:
    items = "".join(
        f'''<article class="el flow-item item-{index}" data-edit-kind="visual"
          data-edit-structure="module" data-edit-fit="container"
          data-edit-composite="{esc(slide["layout_id"])}-flow-step-{index}">
          <div class="flow-item-bg" data-edit-layer="background"
            data-edit-position="absolute" aria-hidden="true"></div>
          {layer("flow-label", esc(item["label"]), position="flow")}
          {layer("flow-title", esc(item["title"]), tag="h2", position="flow")}
          {layer("flow-body", esc(item["body"]), tag="p", position="flow")}
        </article>'''
        for index, item in enumerate(slide["items"], 1)
    )
    footer = footer_module(esc(slide["footer"]), f'{slide["layout_id"]}-footer-note')
    return split_scene(
        scene_header(slide),
        f'<div class="el flow-line" data-edit-kind="visual" data-edit-layer="visual" data-edit-position="absolute"></div>'
        f'<div class="flow-list count-{len(slide["items"])}">{items}</div>',
        slide["layout_id"],
        trailing=footer,
    )


def render_matrix(slide: dict[str, Any]) -> str:
    items = "".join(
        f'''<article class="el matrix-item item-{index}" data-edit-kind="visual"
          data-edit-structure="module" data-edit-fit="container"
          data-edit-composite="{esc(slide["layout_id"])}-matrix-item-{index}">
          <div class="matrix-item-bg" data-edit-layer="background" data-edit-position="absolute" aria-hidden="true"></div>
          {layer("matrix-q", esc(item["q"]), position="flow")}
          {layer("matrix-title", esc(item["label"]), tag="h2", position="flow")}
          {layer("matrix-body", esc(item["body"]), tag="p", position="flow")}
        </article>'''
        for index, item in enumerate(slide["items"], 1)
    )
    axes = slide["axes"]
    axis_markup = (
        loose_layer("axis-label axis-1 axis-left", esc(axes[0]))
        + loose_layer("axis-label axis-2 axis-right", esc(axes[1]))
        + loose_layer("axis-label axis-3 axis-bottom", esc(axes[2]))
        + loose_layer("axis-label axis-4 axis-top", esc(axes[3]))
    )
    return split_scene(
        scene_header(slide),
        f'<div class="el matrix-frame" data-edit-kind="visual" data-edit-layer="visual" data-edit-position="absolute"><i></i><i></i></div>{axis_markup}<div class="matrix-items">{items}</div>',
        slide["layout_id"],
    )


def render_ledger(slide: dict[str, Any]) -> str:
    headers = "".join(layer("ledger-cell ledger-head", esc(value), position="flow") for value in slide["headers"])
    rows = "".join(
        f'''<div class="el ledger-row" data-edit-kind="visual"
          data-edit-structure="module" data-edit-fit="container"
          data-edit-composite="{esc(slide["layout_id"])}-ledger-row-{index}">
          <div class="ledger-row-bg" data-edit-layer="background" data-edit-position="absolute" aria-hidden="true"></div>
          {"".join(layer("ledger-cell", esc(value), position="flow") for value in row)}
        </div>'''
        for index, row in enumerate(slide["rows"], 1)
    )
    header = f'''<div class="el ledger-row ledger-header" data-edit-kind="visual"
      data-edit-structure="module" data-edit-fit="container"
      data-edit-composite="{esc(slide["layout_id"])}-ledger-header">
      <div class="ledger-row-bg" data-edit-layer="background" data-edit-position="absolute" aria-hidden="true"></div>{headers}
    </div>'''
    return split_scene(
        scene_header(slide),
        f'''<div class="ledger">
          <div class="el ledger-sheet-bg" data-edit-kind="visual" data-edit-layer="background" data-edit-position="absolute" aria-hidden="true"></div>
          {header}{rows}
        </div>''',
        slide["layout_id"],
        trailing=footer_module(esc(slide["note"]), f'{slide["layout_id"]}-footer-note'),
    )


def render_timeline(slide: dict[str, Any]) -> str:
    items = "".join(
        f'''<article class="el timeline-item item-{index}" data-edit-kind="visual"
          data-edit-structure="module" data-edit-fit="container"
          data-edit-composite="{esc(slide["layout_id"])}-timeline-item-{index}">
          <div class="timeline-item-bg" data-edit-layer="background" data-edit-position="absolute" aria-hidden="true"></div>
          {layer("timeline-time", esc(item["time"]), position="flow")}
          {layer("timeline-title", esc(item["title"]), tag="h2", position="flow")}
          {layer("timeline-body", esc(item["body"]), tag="p", position="flow")}
        </article>'''
        for index, item in enumerate(slide["items"], 1)
    )
    return split_scene(
        scene_header(slide),
        f'<div class="el timeline-rule" data-edit-kind="visual" data-edit-layer="visual" data-edit-position="absolute"></div><div class="timeline-list count-{len(slide["items"])}">{items}</div>',
        slide["layout_id"],
    )


def render_map(slide: dict[str, Any]) -> str:
    nodes = "".join(
        f'''<article class="el map-node item-{index}" data-edit-kind="visual"
          data-edit-structure="module" data-edit-fit="container"
          data-edit-composite="{esc(slide["layout_id"])}-map-node-{index}">
          <div class="map-node-bg" data-edit-layer="background" data-edit-position="absolute" aria-hidden="true"></div>
          {layer("map-label", esc(node["label"]), tag="h2", position="flow")}
          {layer("map-body", esc(node["body"]), tag="p", position="flow")}
        </article>'''
        for index, node in enumerate(slide["nodes"], 1)
    )
    center = slide["center"]
    return split_scene(
        scene_header(slide),
        f'''<div class="el map-route-loop" data-edit-kind="visual" data-edit-layer="visual" data-edit-position="absolute" aria-hidden="true"></div>
        <article class="el map-center" data-edit-kind="visual"
          data-edit-structure="module" data-edit-fit="container"
          data-edit-composite="{esc(slide["layout_id"])}-map-center">
          <div class="map-center-bg" data-edit-layer="background" data-edit-position="absolute" aria-hidden="true"></div>
          {layer("map-center-title", esc(center["title"]), tag="h2", position="flow")}
          {layer("map-center-body", esc(center["body"]), tag="p", position="flow")}
        </article>
        <div class="map-nodes count-{len(slide["nodes"])}" data-edit-layout-only="true">{nodes}</div>''',
        slide["layout_id"],
    )

def render_metrics(slide: dict[str, Any]) -> str:
    theme_id = slide.get("_theme_id", "")
    metric_open = '' if theme_id == "signal-route-atlas" else '<div class="metric-slot item-{index}" data-edit-layout-only="true">'
    metric_close = '' if theme_id == "signal-route-atlas" else '</div>'
    items = "".join(
        f'''{metric_open.format(index=index)}
          <article class="el metric-item item-{index}" data-edit-kind="visual"
            data-edit-structure="module" data-edit-fit="container"
            data-edit-composite="{esc(slide["layout_id"])}-metric-item-{index}">
            <div class="metric-item-bg" data-edit-layer="background" data-edit-position="absolute" aria-hidden="true"></div>
            {layer("metric-value", esc(item["value"]), position="flow")}
            {layer("metric-label", esc(item["label"]), tag="h2", position="flow")}
            {layer("metric-meaning", esc(item["meaning"]), tag="p", position="flow")}
          </article>{metric_close}'''
        for index, item in enumerate(slide["items"], 1)
    )
    return split_scene(
        scene_header(slide),
        f'<div class="metric-grid count-{len(slide["items"])}" data-edit-layout-only="true">{items}</div>',
        slide["layout_id"],
    )


def render_close(slide: dict[str, Any]) -> str:
    visual = '<div class="el close-signature" data-edit-kind="visual" data-edit-layer="visual" data-edit-position="absolute"><i></i><i></i><i></i></div>'
    return full_scene(
        f'''{loose_layer("close-statement", rich(slide["statement"]), tag="h1")}
        {loose_layer("close-body", esc(slide["body"]), tag="p")}
        {loose_layer("close-action", esc(slide["action"]), tag="p")}
        {loose_layer("close-meta", esc(slide["meta"]))}
        {visual}''',
        slide["layout_id"],
    )


RENDERERS = {
    "cover": render_cover,
    "thesis": render_thesis,
    "index": render_index,
    "contrast": render_contrast,
    "columns": render_columns,
    "flow": render_flow,
    "matrix": render_matrix,
    "ledger": render_ledger,
    "timeline": render_timeline,
    "map": render_map,
    "metrics": render_metrics,
    "close": render_close,
}


BASE_CSS = r'''
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800&family=IBM+Plex+Mono:wght@500;600;700&family=Noto+Sans+TC:wght@400;500;600;700;800;900&family=Noto+Serif+TC:wght@500;600;700;800;900&display=swap');
*{box-sizing:border-box}html,body{width:100%;height:100%;margin:0;overflow:hidden;background:#000}body{font-family:var(--font-body);color:var(--ink)}
#stage{width:1920px;height:1080px}.slide{position:absolute;inset:0;width:1920px;height:1080px;display:none;overflow:hidden;background:var(--bg);color:var(--ink)}.slide.active{display:block}
.content{position:absolute;left:96px;top:96px;width:1728px;height:888px}.el{position:absolute;padding:0;border:0;background:transparent;overflow:visible}.scene{isolation:isolate}
.scene [data-edit-position="absolute"]{position:absolute;margin:0;padding:0}.scene [data-edit-position="flow"]{position:relative;inset:auto;width:auto;height:auto;margin:0}.scene-title{left:0;top:0;width:1500px;font:800 58px/1.14 var(--font-display);letter-spacing:-.035em;color:var(--ink)}.scene-intro{left:0;top:88px;width:1460px;font:500 24px/1.5 var(--font-body);color:var(--muted)}
.scene-footer{left:0;bottom:0;width:100%;min-height:64px;padding:18px 24px!important;border:0!important;background:transparent!important;font:600 20px/1.4 var(--font-body);color:var(--ink);display:flex!important;align-items:center;justify-content:center}
.scene-footer-bg{position:absolute!important;left:0!important;top:0!important;width:100%!important;height:100%!important;background:var(--footer-background,transparent);border:var(--footer-border,0);border-top:var(--footer-border-top,1px solid var(--line));pointer-events:auto}
.scene-footer-text{position:relative!important;width:100%;font:inherit;color:inherit;text-align:inherit}
.cover-kicker{font:700 15px/1 var(--font-utility);letter-spacing:.18em;color:var(--accent)}.cover-title{font:800 128px/.96 var(--font-display);letter-spacing:-.06em;color:var(--ink)}.cover-subtitle{font:500 58px/1.34 var(--font-body);color:var(--muted)}.cover-meta{font:600 14px/1 var(--font-utility);letter-spacing:.14em;color:var(--ink)}
.index-item,.column-item,.flow-item,.matrix-item,.timeline-item,.map-node,.metric-item,.contrast-panel,.ledger-row,.map-center{position:absolute}.index-label,.column-tag,.flow-label,.matrix-q,.timeline-time{font:700 13px/1 var(--font-utility);letter-spacing:.13em;color:var(--accent)}
.index-title,.column-title,.flow-title,.matrix-title,.timeline-title,.map-label,.metric-label,.contrast-title,.map-center-title{font:800 28px/1.2 var(--font-display);letter-spacing:-.025em;color:var(--ink)}
.index-body,.column-body,.flow-body,.matrix-body,.timeline-body,.map-body,.metric-meaning,.contrast-lead,.map-center-body{font:500 19px/1.52 var(--font-body);color:var(--muted)}
.ledger{position:absolute;left:0;right:0;top:190px;bottom:96px}.ledger-row{position:relative;width:100%;height:auto;min-height:104px;display:grid;grid-template-columns:1.05fr 1.45fr 1.65fr 1.5fr;border-bottom:1px solid var(--line)}.ledger-header{min-height:54px;border-top:2px solid var(--ink);border-bottom:1px solid var(--ink)}.ledger-cell{position:relative!important;padding:18px 22px!important;border-right:1px solid var(--line);font:500 18px/1.42 var(--font-body);color:var(--ink)}.ledger-cell:last-child{border-right:0}.ledger-head{font:700 12px/1.2 var(--font-utility);letter-spacing:.12em;color:var(--accent)}
.map-links{position:absolute;left:224px;top:210px;width:1280px;height:560px;fill:none;stroke:var(--line);stroke-width:2}.map-center{left:684px;top:390px;width:360px;height:190px;text-align:center}.map-center-title{position:relative!important;font-size:26px}.map-center-body{position:relative!important;margin-top:16px!important;font-size:17px}.map-nodes{position:absolute;left:0;top:0;width:100%;height:100%}.map-node{width:260px;height:110px}.map-node .map-label{left:0;top:0;width:100%;font-size:22px}.map-node .map-body{left:0;top:38px;width:100%;font-size:16px}.map-node.item-1{left:734px;top:188px;text-align:center}.map-node.item-2{left:1210px;top:270px}.map-node.item-3{left:1210px;top:620px}.map-node.item-4{left:734px;top:742px;text-align:center}.map-node.item-5{left:260px;top:620px;text-align:right}.map-node.item-6{left:260px;top:270px;text-align:right}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
'''


LINE_CSS = r'''
html[data-theme-id="line-argument-journal"]{--bg:#F5F4F0;--paper:#F5F4F0;--ink:#17191A;--muted:#5D666D;--accent:#8D3028;--line:#C7C9C5;--font-display:"Noto Serif TC",serif;--font-body:"Noto Sans TC",sans-serif;--font-utility:"IBM Plex Mono",monospace}
html[data-theme-id="line-argument-journal"] .slide{background-image:linear-gradient(90deg,transparent 0 95px,rgba(141,48,40,.08) 96px 97px,transparent 98px),linear-gradient(rgba(23,25,26,.022) 1px,transparent 1px);background-size:100% 100%,100% 54px}
html[data-theme-id="line-argument-journal"] .slide:before{content:"";position:absolute;left:96px;right:96px;top:66px;height:1px;background:var(--ink);opacity:.65}
html[data-theme-id="line-argument-journal"] .folio{color:#4d565c}.line-cover-thesis .cover-kicker{left:2px;top:94px}.line-cover-thesis .cover-title{left:200px;top:210px;width:1320px;font-size:150px;line-height:1.04}.line-cover-thesis .cover-subtitle{left:202px;top:600px;width:1480px}.line-cover-thesis .cover-meta{left:202px;top:770px}.line-cover-thesis .cover-signature{position:absolute;left:0;top:178px;width:130px;height:560px;border-top:1px solid var(--accent);border-bottom:1px solid var(--accent)}.line-cover-thesis .cover-signature i{position:absolute;left:0;width:100%;height:1px;background:var(--line)}.line-cover-thesis .cover-signature i:nth-child(1){top:74px}.line-cover-thesis .cover-signature i:nth-child(2){top:168px}.line-cover-thesis .cover-signature i:nth-child(3){top:282px}.line-cover-thesis .cover-signature i:nth-child(4){top:414px}.line-cover-thesis .cover-signature i:nth-child(5){left:28px;top:-20px;width:1px;height:600px;background:var(--accent)}
.line-quote-evidence .thesis-mark{left:0;top:70px;font:800 280px/.78 var(--font-display);color:var(--accent)}.line-quote-evidence .thesis-quote{left:320px;top:115px;width:1290px;font:700 76px/1.36 var(--font-display);letter-spacing:-.035em;color:var(--ink)}.line-quote-evidence .thesis-attribution{left:324px;top:570px;width:900px;font:600 14px/1.4 var(--font-utility);letter-spacing:.1em;color:var(--accent)}.line-quote-evidence .thesis-notes{position:absolute;left:324px;right:0;bottom:32px;margin:0;padding:24px 0 0;display:grid;grid-template-columns:repeat(3,1fr);gap:34px;border-top:1px solid var(--ink);list-style:none}.line-quote-evidence .thesis-notes li{position:relative;min-height:105px;padding-left:54px}.line-quote-evidence .thesis-notes b{position:absolute;left:0;top:2px;font:700 13px/1 var(--font-utility);color:var(--accent)}.line-quote-evidence .note-copy{position:relative!important;font:500 18px/1.5 var(--font-body);color:var(--muted)}
html[data-theme-id="line-argument-journal"] .index-list{position:absolute;left:0;right:0;top:210px;bottom:0}.line-index-questions .index-item{left:0;width:100%;height:150px;border-top:1px solid var(--line)}.line-index-questions .index-item.item-1{top:0}.line-index-questions .index-item.item-2{top:150px}.line-index-questions .index-item.item-3{top:300px}.line-index-questions .index-item.item-4{top:450px;border-bottom:1px solid var(--line)}.line-index-questions .index-label{left:4px;top:44px}.line-index-questions .index-title{left:120px;top:33px;width:400px;font-size:34px}.line-index-questions .index-body{left:610px;top:35px;width:990px;font-size:22px}
html[data-theme-id="line-argument-journal"] .contrast-grid{position:absolute;left:0;right:0;top:205px;bottom:0}.line-contrast-friction .contrast-panel{top:0;width:50%;height:600px;padding:52px 56px!important;border-top:2px solid var(--ink);border-bottom:1px solid var(--line)}.line-contrast-friction .contrast-left{left:0;border-right:1px solid var(--ink)}.line-contrast-friction .contrast-right{right:0}.line-contrast-friction .contrast-label{left:56px;top:42px}.line-contrast-friction .contrast-title{left:56px;top:94px;width:700px;font-size:44px}.line-contrast-friction .contrast-lead{left:56px;top:170px;width:700px;font-size:21px}.line-contrast-friction ul{position:absolute;left:56px;right:56px;top:285px;margin:0;padding:0;list-style:none}.line-contrast-friction li{position:relative;min-height:74px;padding:22px 0 18px 38px;border-top:1px solid var(--line)}.line-contrast-friction li:before{content:"—";position:absolute;left:0;top:22px;color:var(--accent)}.line-contrast-friction .item-copy{position:relative!important;font:550 20px/1.45 var(--font-body);color:var(--ink)}
html[data-theme-id="line-argument-journal"] .column-grid{position:absolute;left:0;right:0;top:210px;bottom:0;display:grid;grid-template-columns:repeat(4,1fr)}.line-voices-four .column-item,.line-risk-register .column-item{position:relative;border-top:2px solid var(--ink);border-right:1px solid var(--line);padding:46px 36px!important}.line-voices-four .column-item:last-child,.line-risk-register .column-item:last-child{border-right:0}.line-voices-four .column-tag,.line-risk-register .column-tag{left:36px;top:38px}.line-voices-four .column-title,.line-risk-register .column-title{left:36px;right:32px;top:92px;font-size:38px}.line-voices-four .column-body,.line-risk-register .column-body{left:36px;right:38px;top:175px;font-size:21px;line-height:1.65}.line-risk-register .column-grid{grid-template-columns:repeat(3,1fr);left:130px;right:130px}.line-risk-register .column-item{min-height:540px}
html[data-theme-id="line-argument-journal"] .flow-list{position:absolute;left:0;right:0;top:220px;bottom:104px;display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(2,1fr);column-gap:58px;row-gap:50px}.line-service-thread .flow-line{position:absolute;left:0;right:0;top:446px;height:1px;background:var(--accent)}.line-service-thread .flow-item{position:relative;padding:38px 20px 20px 64px!important;border-top:1px solid var(--line)}.line-service-thread .flow-item:before{content:"";position:absolute;left:0;top:-7px;width:13px;height:13px;border:2px solid var(--accent);border-radius:50%;background:var(--bg)}.line-service-thread .flow-label{left:20px;top:42px}.line-service-thread .flow-title{left:64px;top:38px;font-size:31px}.line-service-thread .flow-body{left:64px;right:20px;top:95px;font-size:18px}
html[data-theme-id="line-argument-journal"] .matrix-frame{position:absolute;left:230px;top:210px;width:1260px;height:560px;border:1px solid var(--ink)}.line-decision-matrix .matrix-frame i:first-child{position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--ink)}.line-decision-matrix .matrix-frame i:last-child{position:absolute;left:0;right:0;top:50%;height:1px;background:var(--ink)}.line-decision-matrix .matrix-items{position:absolute;left:230px;top:210px;width:1260px;height:560px}.line-decision-matrix .matrix-item{width:630px;height:280px;padding:38px 44px!important}.line-decision-matrix .matrix-item.item-1{left:0;top:0}.line-decision-matrix .matrix-item.item-2{left:630px;top:0}.line-decision-matrix .matrix-item.item-3{left:0;top:280px}.line-decision-matrix .matrix-item.item-4{left:630px;top:280px}.line-decision-matrix .matrix-q{left:44px;top:38px}.line-decision-matrix .matrix-title{left:44px;top:82px;font-size:35px}.line-decision-matrix .matrix-body{left:44px;right:40px;top:145px;font-size:19px}.line-decision-matrix .axis-label{font:600 12px/1 var(--font-utility);letter-spacing:.1em;color:var(--muted)}.line-decision-matrix .axis-1{left:230px;top:790px}.line-decision-matrix .axis-2{right:238px;top:790px}.line-decision-matrix .axis-3{left:112px;top:720px;transform:rotate(-90deg)}.line-decision-matrix .axis-4{left:112px;top:290px;transform:rotate(-90deg)}
.line-intervention-ladder .timeline-rule,.line-operating-rhythm .timeline-rule{position:absolute;left:88px;right:88px;top:430px;height:1px;background:var(--ink)}.line-intervention-ladder .timeline-list,.line-operating-rhythm .timeline-list{position:absolute;left:88px;right:88px;top:235px;height:520px;display:grid;grid-template-columns:repeat(4,1fr);gap:52px}.line-intervention-ladder .timeline-item,.line-operating-rhythm .timeline-item{position:relative;padding-top:62px!important}.line-intervention-ladder .timeline-item:before,.line-operating-rhythm .timeline-item:before{content:"";position:absolute;left:0;top:187px;width:17px;height:17px;border:2px solid var(--accent);border-radius:50%;background:var(--bg)}.line-intervention-ladder .timeline-time,.line-operating-rhythm .timeline-time{left:0;top:0}.line-intervention-ladder .timeline-title,.line-operating-rhythm .timeline-title{left:0;right:10px;top:54px;font-size:35px}.line-intervention-ladder .timeline-body,.line-operating-rhythm .timeline-body{left:0;right:30px;top:250px;font-size:19px}
html[data-theme-id="line-argument-journal"] .metric-grid{position:absolute;left:0;right:0;top:220px;bottom:0;display:grid;grid-template-columns:repeat(4,1fr)}.line-measures .metric-item{position:relative;border-top:2px solid var(--ink);border-right:1px solid var(--line);padding:42px 36px!important}.line-measures .metric-item:last-child{border-right:0}.line-measures .metric-value{left:36px;top:38px;font:800 58px/1 var(--font-display);color:var(--accent)}.line-measures .metric-label{left:36px;right:30px;top:142px;font-size:30px;line-height:1.35}.line-measures .metric-meaning{left:36px;right:38px;top:270px;font-size:19px;line-height:1.6}
.line-operating-rhythm .ledger-row{grid-template-columns:.8fr 1.35fr 1.65fr 1.5fr}.line-operating-rhythm .ledger{top:198px}.line-operating-rhythm .scene-footer{font-size:18px}
.line-close-commitment .close-statement{left:190px;top:118px;width:1300px;font:700 96px/1.25 var(--font-display);letter-spacing:-.04em;color:var(--ink)}.line-close-commitment .close-body{left:194px;top:545px;width:1050px;font:500 26px/1.6 var(--font-body);color:var(--muted)}.line-close-commitment .close-action{left:194px;top:730px;width:1200px;padding-top:24px!important;border-top:1px solid var(--ink);font:650 20px/1.4 var(--font-body);color:var(--accent)}.line-close-commitment .close-meta{right:130px;bottom:42px;font:700 13px/1 var(--font-utility);letter-spacing:.15em;color:var(--ink)}.line-close-commitment .close-signature{position:absolute;left:0;top:150px;width:90px;height:560px;border-left:2px solid var(--accent)}.line-close-commitment .close-signature i{position:absolute;left:-8px;width:14px;height:14px;border-radius:50%;border:2px solid var(--accent);background:var(--bg)}.line-close-commitment .close-signature i:nth-child(1){top:0}.line-close-commitment .close-signature i:nth-child(2){top:273px}.line-close-commitment .close-signature i:nth-child(3){bottom:0}
'''


ROUTE_CSS = r'''
html[data-theme-id="signal-route-atlas"]{--bg:#F3F6F8;--ink:#10283D;--muted:#526879;--accent:#B8421B;--support:#1B6B72;--line:#BFCAD2;--font-display:"Barlow Condensed","Noto Sans TC",sans-serif;--font-body:"Noto Sans TC",sans-serif;--font-utility:"IBM Plex Mono",monospace}
html[data-theme-id="signal-route-atlas"] .slide{background-image:linear-gradient(rgba(16,40,61,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(16,40,61,.04) 1px,transparent 1px);background-size:64px 64px}
html[data-theme-id="signal-route-atlas"] .slide:before{content:"";position:absolute;left:0;right:0;top:38px;height:18px;background:linear-gradient(90deg,var(--ink) 0 31%,var(--accent) 31% 54%,var(--support) 54% 79%,var(--ink) 79%)}
html[data-theme-id="signal-route-atlas"] .scene-title{font-size:66px;text-transform:none}.route-cover-network .cover-kicker{left:0;top:82px}.route-cover-network .cover-title{left:0;top:190px;width:1120px;font-size:156px;line-height:.92;text-transform:uppercase}.route-cover-network .cover-subtitle{left:0;top:555px;width:1320px}.route-cover-network .cover-meta{left:0;top:742px}.route-cover-network .cover-signature{position:absolute;left:1160px;top:70px;width:520px;height:700px}.route-cover-network .cover-signature:before,.route-cover-network .cover-signature:after{content:"";position:absolute;left:80px;right:0;height:12px;border-radius:99px;background:var(--ink);transform-origin:left center}.route-cover-network .cover-signature:before{top:190px;transform:rotate(18deg)}.route-cover-network .cover-signature:after{top:480px;transform:rotate(-22deg);background:var(--support)}.route-cover-network .cover-signature i{position:absolute;width:34px;height:34px;border:8px solid var(--bg);border-radius:50%;background:var(--accent);box-shadow:0 0 0 4px var(--ink)}.route-cover-network .cover-signature i:nth-child(1){left:66px;top:180px}.route-cover-network .cover-signature i:nth-child(2){left:250px;top:232px}.route-cover-network .cover-signature i:nth-child(3){right:26px;top:290px}.route-cover-network .cover-signature i:nth-child(4){left:238px;top:432px;background:var(--support)}.route-cover-network .cover-signature i:nth-child(5){right:12px;top:328px;background:var(--support)}
html[data-theme-id="signal-route-atlas"] .index-list{position:absolute;left:0;right:0;top:220px;bottom:0}.route-index-lines .index-list:before{content:"";position:absolute;left:92px;top:35px;bottom:40px;width:10px;border-radius:99px;background:linear-gradient(var(--accent) 0 42%,var(--support) 42% 74%,var(--ink) 74%)}.route-index-lines .index-item{left:0;width:100%;height:118px}.route-index-lines .index-item.item-1{top:0}.route-index-lines .index-item.item-2{top:118px}.route-index-lines .index-item.item-3{top:236px}.route-index-lines .index-item.item-4{top:354px}.route-index-lines .index-item.item-5{top:472px}.route-index-lines .index-label{left:64px;top:34px;width:64px;height:32px;padding:10px 0!important;border-radius:99px;background:var(--bg);box-shadow:0 0 0 4px var(--ink);text-align:center;color:var(--ink)}.route-index-lines .index-title{left:190px;top:19px;width:430px;font-size:36px}.route-index-lines .index-body{left:680px;top:25px;width:960px;padding-bottom:22px!important;border-bottom:1px solid var(--line);font-size:20px}
html[data-theme-id="signal-route-atlas"] .column-grid{position:absolute;left:0;right:0;top:220px;bottom:0;display:grid;grid-template-columns:repeat(4,1fr);gap:28px}.route-sources .column-item,.route-experiment-portfolio .column-item{position:relative;padding:48px 32px!important;border-top:12px solid var(--ink);background:rgba(255,255,255,.64);box-shadow:0 12px 28px rgba(16,40,61,.08)}.route-sources .column-item:nth-child(2),.route-experiment-portfolio .column-item:nth-child(2){border-top-color:var(--accent)}.route-sources .column-item:nth-child(3),.route-experiment-portfolio .column-item:nth-child(3){border-top-color:var(--support)}.route-sources .column-tag,.route-experiment-portfolio .column-tag{left:32px;top:38px;padding:8px 10px!important;background:var(--ink);color:#fff}.route-sources .column-title,.route-experiment-portfolio .column-title{left:32px;right:28px;top:105px;font-size:42px}.route-sources .column-body,.route-experiment-portfolio .column-body{left:32px;right:30px;top:190px;font-size:20px;line-height:1.6}
.route-taxonomy .ledger-row,.route-service-blueprint .ledger-row{grid-template-columns:.75fr 1.45fr 1.7fr 1.45fr}.route-taxonomy .ledger-row:not(.ledger-header) .ledger-cell:first-child,.route-service-blueprint .ledger-row:not(.ledger-header) .ledger-cell:first-child{font:750 15px/1.2 var(--font-utility);letter-spacing:.08em;color:#fff;background:var(--ink)}.route-taxonomy .ledger-row:nth-child(3) .ledger-cell:first-child,.route-service-blueprint .ledger-row:nth-child(3) .ledger-cell:first-child{background:var(--accent)}.route-taxonomy .ledger-row:nth-child(4) .ledger-cell:first-child,.route-service-blueprint .ledger-row:nth-child(4) .ledger-cell:first-child{background:var(--support)}
html[data-theme-id="signal-route-atlas"] .flow-list{position:absolute;left:0;right:0;top:270px;height:360px;display:grid;grid-template-columns:repeat(7,1fr);gap:24px}.route-map-main .flow-line{position:absolute;left:72px;right:72px;top:412px;height:12px;border-radius:99px;background:linear-gradient(90deg,var(--accent) 0 29%,var(--support) 29% 58%,var(--ink) 58%)}.route-map-main .flow-item{position:relative;text-align:center;padding-top:20px!important}.route-map-main .flow-item:before{content:"";position:absolute;left:calc(50% - 15px);top:127px;width:30px;height:30px;border:8px solid var(--bg);border-radius:50%;background:var(--ink);box-shadow:0 0 0 4px var(--ink)}.route-map-main .flow-item:nth-child(-n+2):before{background:var(--accent);box-shadow:0 0 0 4px var(--accent)}.route-map-main .flow-item:nth-child(n+3):nth-child(-n+4):before{background:var(--support);box-shadow:0 0 0 4px var(--support)}.route-map-main .flow-label{left:0;right:0;top:6px;color:var(--muted)}.route-map-main .flow-title{left:0;right:0;top:55px;font-size:30px}.route-map-main .flow-body{left:10px;right:10px;top:215px;font-size:17px}.route-map-main .scene-footer{bottom:10px;--footer-border:2px solid var(--ink);--footer-border-top:2px solid var(--ink);--footer-background:var(--bg)}
.route-confidence-matrix .matrix-frame{position:absolute;left:250px;top:210px;width:1220px;height:560px;border-left:8px solid var(--ink);border-bottom:8px solid var(--ink);background:linear-gradient(135deg,transparent 0 49.6%,var(--accent) 49.8% 50.2%,transparent 50.4%)}.route-confidence-matrix .matrix-frame i:first-child{position:absolute;left:50%;top:0;bottom:0;border-left:2px dashed var(--line)}.route-confidence-matrix .matrix-frame i:last-child{position:absolute;left:0;right:0;top:50%;border-top:2px dashed var(--line)}.route-confidence-matrix .matrix-items{position:absolute;left:250px;top:210px;width:1220px;height:560px}.route-confidence-matrix .matrix-item{width:610px;height:280px;padding:34px 44px!important}.route-confidence-matrix .matrix-item.item-1{left:0;top:0}.route-confidence-matrix .matrix-item.item-2{right:0;top:0}.route-confidence-matrix .matrix-item.item-3{left:0;bottom:0}.route-confidence-matrix .matrix-item.item-4{right:0;bottom:0}.route-confidence-matrix .matrix-q{left:44px;top:32px}.route-confidence-matrix .matrix-title{left:44px;top:78px;font-size:38px}.route-confidence-matrix .matrix-body{left:44px;right:46px;top:145px;font-size:19px}.route-confidence-matrix .axis-label{font:650 12px/1 var(--font-utility);letter-spacing:.1em;color:var(--muted)}.route-confidence-matrix .axis-1{left:250px;top:790px}.route-confidence-matrix .axis-2{right:250px;top:790px}.route-confidence-matrix .axis-3{left:126px;top:710px;transform:rotate(-90deg)}.route-confidence-matrix .axis-4{left:126px;top:290px;transform:rotate(-90deg)}
.route-decision-loop .map-links{stroke:var(--support);stroke-width:6}.route-decision-loop .map-center{left:680px;top:400px;width:368px;height:170px;padding:30px!important;background:var(--ink);color:#fff}.route-decision-loop .map-center-title,.route-decision-loop .map-center-body{color:#fff}.route-decision-loop .map-node{padding:14px 18px!important;border-left:8px solid var(--accent);background:rgba(255,255,255,.76)}
.route-operating-cadence .timeline-rule{position:absolute;left:65px;right:65px;top:445px;height:12px;border-radius:99px;background:linear-gradient(90deg,var(--accent) 0 24%,var(--support) 24% 52%,var(--ink) 52%)}.route-operating-cadence .timeline-list{position:absolute;left:65px;right:65px;top:235px;height:520px;display:grid;grid-template-columns:repeat(4,1fr);gap:42px}.route-operating-cadence .timeline-item{position:relative;padding:32px 28px!important;background:rgba(255,255,255,.72);border-top:8px solid var(--ink)}.route-operating-cadence .timeline-item:after{content:"";position:absolute;left:28px;top:196px;width:30px;height:30px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 7px var(--bg)}.route-operating-cadence .timeline-time{left:28px;top:29px}.route-operating-cadence .timeline-title{left:28px;right:24px;top:76px;font-size:38px}.route-operating-cadence .timeline-body{left:28px;right:26px;top:255px;font-size:19px}
html[data-theme-id="signal-route-atlas"] .metric-grid{position:absolute;left:0;right:0;top:220px;bottom:30px;display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(2,1fr);gap:28px}.route-metrics .metric-item{position:relative;padding:38px 42px!important;border-left:12px solid var(--ink);background:rgba(255,255,255,.76)}.route-metrics .metric-item:nth-child(2){border-left-color:var(--accent)}.route-metrics .metric-item:nth-child(3){border-left-color:var(--support)}.route-metrics .metric-value{left:42px;top:34px;font:800 52px/1 var(--font-display);text-transform:uppercase;color:var(--accent)}.route-metrics .metric-label{left:280px;right:38px;top:38px;font-size:27px}.route-metrics .metric-meaning{left:280px;right:42px;top:110px;font-size:18px}.route-metrics .metric-item:after{content:"";position:absolute;left:42px;bottom:36px;width:180px;height:10px;border-radius:99px;background:linear-gradient(90deg,var(--accent) 0 62%,var(--line) 62%)}
.route-close-platform .close-statement{left:0;top:130px;width:1200px;font:800 126px/.98 var(--font-display);letter-spacing:-.04em;text-transform:uppercase;color:var(--ink)}.route-close-platform .close-body{left:0;top:520px;width:980px;font:500 26px/1.55 var(--font-body);color:var(--muted)}.route-close-platform .close-action{left:0;top:710px;width:990px;padding:20px 26px!important;background:var(--ink);font:650 20px/1.35 var(--font-body);color:#fff}.route-close-platform .close-meta{right:20px;bottom:42px;font:700 14px/1 var(--font-utility);letter-spacing:.15em;color:var(--ink)}.route-close-platform .close-signature{position:absolute;right:28px;top:125px;width:520px;height:520px;border:10px solid var(--support);border-radius:50%}.route-close-platform .close-signature:before{content:"";position:absolute;left:-190px;top:245px;width:710px;height:14px;background:var(--accent)}.route-close-platform .close-signature i{position:absolute;width:38px;height:38px;border:8px solid var(--bg);border-radius:50%;background:var(--ink);box-shadow:0 0 0 4px var(--ink)}.route-close-platform .close-signature i:nth-child(1){left:-20px;top:230px}.route-close-platform .close-signature i:nth-child(2){left:210px;top:230px;background:var(--accent);box-shadow:0 0 0 4px var(--accent)}.route-close-platform .close-signature i:nth-child(3){right:-14px;top:230px;background:var(--support);box-shadow:0 0 0 4px var(--support)}
'''


FIELD_CSS = r'''
html[data-theme-id="field-index-manual"]{--bg:#E9EEE8;--paper:#FAFAF7;--ink:#143D2D;--muted:#52645A;--accent:#87374B;--support:#D6B34A;--line:#B9C4BA;--font-display:"Noto Serif TC",serif;--font-body:"Noto Sans TC",sans-serif;--font-utility:"IBM Plex Mono",monospace}
html[data-theme-id="field-index-manual"] .slide{background-image:radial-gradient(circle at 18px 18px,rgba(20,61,45,.075) 1.2px,transparent 1.4px);background-size:36px 36px}
html[data-theme-id="field-index-manual"] .slide:before{content:"";position:absolute;left:58px;right:58px;top:54px;bottom:54px;background:rgba(250,250,247,.92);box-shadow:0 18px 60px rgba(20,61,45,.10)}html[data-theme-id="field-index-manual"] .index-tab{padding-top:19px;background:var(--accent);color:#fff;text-align:center;font:700 13px/1 var(--font-utility);letter-spacing:.12em;box-shadow:0 8px 20px rgba(20,61,45,.15)}html[data-theme-id="field-index-manual"] .field-index .index-label{color:#815C12}
html[data-theme-id="field-index-manual"] .content{z-index:2}.field-cover-index .cover-kicker{left:70px;top:70px}.field-cover-index .cover-title{left:70px;top:185px;width:1080px;font-size:138px;line-height:1.04}.field-cover-index .cover-subtitle{left:72px;top:565px;width:1120px}.field-cover-index .cover-meta{left:72px;top:760px}.field-cover-index .cover-signature{position:absolute;right:90px;top:120px;width:420px;height:620px;border-left:1px solid var(--ink);border-right:1px solid var(--line)}.field-cover-index .cover-signature:before{content:"FIELD\A NOTES";white-space:pre;position:absolute;left:70px;top:120px;font:700 80px/.88 var(--font-display);color:var(--ink)}.field-cover-index .cover-signature:after{content:"03";position:absolute;left:76px;bottom:68px;font:800 180px/.8 var(--font-display);color:var(--support)}.field-cover-index .cover-signature i{position:absolute;right:-1px;width:76px;height:1px;background:var(--accent)}.field-cover-index .cover-signature i:nth-child(1){top:70px}.field-cover-index .cover-signature i:nth-child(2){top:160px}.field-cover-index .cover-signature i:nth-child(3){top:250px}.field-cover-index .cover-signature i:nth-child(4){top:340px}.field-cover-index .cover-signature i:nth-child(5){top:430px}
html[data-theme-id="field-index-manual"] .scene-title{left:52px;top:34px;width:1510px;font-size:62px}.field-index .scene-intro,.field-day-rhythm .scene-intro,.field-actors .scene-intro,.field-handoff-map .scene-intro,.field-artifact-spec .scene-intro,.field-exception-tree .scene-intro,.field-pilot-calendar .scene-intro,.field-service-script .scene-intro,.field-resource-ledger .scene-intro,.field-principles .scene-intro{left:54px;top:122px}.field-index .index-list{position:absolute;left:54px;right:54px;top:225px;bottom:36px;display:grid;grid-template-columns:repeat(5,1fr);gap:22px}.field-index .index-item{position:relative;padding:36px 28px!important;border-top:7px solid var(--ink);background:var(--paper);box-shadow:0 10px 24px rgba(20,61,45,.08)}.field-index .index-item:nth-child(2){border-top-color:var(--accent)}.field-index .index-item:nth-child(3){border-top-color:var(--support)}.field-index .index-label{left:28px;top:30px;font:800 72px/.9 var(--font-display);color:color-mix(in srgb,var(--support) 72%,#fff)}.field-index .index-title{left:28px;right:20px;top:135px;font-size:34px}.field-index .index-body{left:28px;right:26px;top:220px;font-size:18px;line-height:1.62}
.field-day-rhythm .timeline-rule,.field-pilot-calendar .timeline-rule{position:absolute;left:116px;top:215px;bottom:80px;width:2px;background:var(--ink)}.field-day-rhythm .timeline-list,.field-pilot-calendar .timeline-list{position:absolute;left:54px;right:70px;top:210px;bottom:42px;display:grid;grid-template-rows:repeat(4,1fr);gap:10px}.field-day-rhythm .timeline-item,.field-pilot-calendar .timeline-item{position:relative;padding:24px 28px 18px 150px!important;border-bottom:1px solid var(--line)}.field-day-rhythm .timeline-item:before,.field-pilot-calendar .timeline-item:before{content:"";position:absolute;left:52px;top:40px;width:20px;height:20px;border:6px solid var(--paper);border-radius:50%;background:var(--accent);box-shadow:0 0 0 3px var(--ink)}.field-day-rhythm .timeline-time,.field-pilot-calendar .timeline-time{left:0;top:37px;width:88px;text-align:right}.field-day-rhythm .timeline-title,.field-pilot-calendar .timeline-title{left:150px;top:22px;width:460px;font-size:35px}.field-day-rhythm .timeline-body,.field-pilot-calendar .timeline-body{left:660px;right:20px;top:28px;font-size:20px}
html[data-theme-id="field-index-manual"] .column-grid{position:absolute;left:54px;right:54px;top:225px;bottom:36px;display:grid;grid-template-columns:repeat(4,1fr);gap:26px}.field-actors .column-item{position:relative;padding:40px 30px!important;background:var(--paper);box-shadow:0 10px 26px rgba(20,61,45,.08)}.field-actors .column-item:after{content:"";position:absolute;left:30px;right:30px;bottom:32px;height:9px;background:repeating-linear-gradient(90deg,var(--accent) 0 9px,transparent 9px 18px)}.field-actors .column-tag{left:30px;top:34px;padding:8px 10px!important;border:1px solid var(--ink);color:var(--ink)}.field-actors .column-title{left:30px;right:26px;top:112px;font-size:38px}.field-actors .column-body{left:30px;right:28px;top:190px;font-size:19px;line-height:1.62}
.field-handoff-map .map-links{stroke:var(--line);stroke-width:3;stroke-dasharray:7 10}.field-handoff-map .map-center{left:682px;top:390px;width:365px;height:190px;padding:34px!important;border:2px solid var(--ink);background:var(--paper)}.field-handoff-map .map-node{padding:15px 18px!important;border-bottom:5px solid var(--accent);background:var(--paper);box-shadow:0 8px 20px rgba(20,61,45,.07)}
.field-artifact-spec .ledger,.field-resource-ledger .ledger{left:54px;right:54px;top:218px;bottom:104px}.field-artifact-spec .ledger-row,.field-resource-ledger .ledger-row{grid-template-columns:1.05fr 1.55fr 1.45fr 1.65fr;background:rgba(250,250,247,.82)}.field-artifact-spec .ledger-row:not(.ledger-header) .ledger-cell:first-child,.field-resource-ledger .ledger-row:not(.ledger-header) .ledger-cell:first-child{font-weight:800;color:var(--ink)}.field-artifact-spec .scene-footer,.field-resource-ledger .scene-footer{left:54px;width:1620px;--footer-background:var(--ink);--footer-border:0;--footer-border-top:0;color:#fff}
.field-exception-tree .flow-list{position:absolute;left:100px;right:100px;top:260px;height:410px;display:grid;grid-template-columns:repeat(4,1fr);gap:48px}.field-exception-tree .flow-line{position:absolute;left:160px;right:160px;top:420px;height:2px;background:var(--ink)}.field-exception-tree .flow-item{position:relative;padding:72px 30px 24px!important;border:1px solid var(--line);background:var(--paper)}.field-exception-tree .flow-item:before{content:"?";position:absolute;left:30px;top:-34px;width:66px;height:66px;display:grid;place-content:center;border-radius:50%;background:var(--accent);color:#fff;font:800 34px/1 var(--font-display);box-shadow:0 0 0 8px var(--bg)}.field-exception-tree .flow-label{left:112px;top:25px}.field-exception-tree .flow-title{left:30px;right:26px;top:80px;font-size:34px}.field-exception-tree .flow-body{left:30px;right:30px;top:155px;font-size:19px}.field-exception-tree .scene-footer{left:100px;width:1528px;--footer-background:var(--support);--footer-border:0;--footer-border-top:0;color:var(--ink)}
.field-service-script .contrast-grid{position:absolute;left:54px;right:54px;top:220px;bottom:54px;display:grid;grid-template-columns:1fr 1fr;gap:32px}.field-service-script .contrast-panel{position:relative;padding:40px 44px!important;background:var(--paper);border-top:8px solid var(--muted);box-shadow:0 10px 24px rgba(20,61,45,.08)}.field-service-script .contrast-right{border-top-color:var(--accent)}.field-service-script .contrast-label{left:44px;top:34px}.field-service-script .contrast-title{left:44px;right:38px;top:84px;font-size:40px}.field-service-script .contrast-lead{left:44px;right:42px;top:150px;font-size:19px}.field-service-script ul{position:absolute;left:44px;right:44px;top:265px;margin:0;padding:0;list-style:none}.field-service-script li{position:relative;min-height:82px;padding:22px 10px 18px 28px;border-top:1px solid var(--line)}.field-service-script .item-copy{position:relative!important;font:600 19px/1.45 var(--font-body);color:var(--ink)}
html[data-theme-id="field-index-manual"] .metric-grid{position:absolute;left:54px;right:54px;top:220px;bottom:48px;display:grid;grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(2,1fr);gap:24px}.field-principles .metric-item{position:relative;padding:38px 42px!important;background:var(--paper);border-left:1px solid var(--line)}.field-principles .metric-value{left:42px;top:34px;padding:12px 18px!important;background:var(--ink);font:800 34px/1 var(--font-display);color:#fff}.field-principles .metric-label{left:250px;right:38px;top:38px;font-size:29px}.field-principles .metric-meaning{left:250px;right:42px;top:112px;font-size:18px}.field-principles .metric-item:after{content:"APPROVED";position:absolute;left:42px;bottom:34px;padding:10px 14px;border:2px solid var(--accent);transform:rotate(-4deg);font:700 12px/1 var(--font-utility);letter-spacing:.13em;color:var(--accent)}
.field-close-handoff .close-statement{left:80px;top:105px;width:1260px;font:800 92px/1.25 var(--font-display);letter-spacing:-.035em;color:var(--ink)}.field-close-handoff .close-body{left:84px;top:515px;width:1060px;font:500 26px/1.6 var(--font-body);color:var(--muted)}.field-close-handoff .close-action{left:84px;top:710px;width:1120px;padding:20px 24px!important;border-left:9px solid var(--accent);background:var(--paper);font:650 20px/1.4 var(--font-body);color:var(--ink)}.field-close-handoff .close-meta{right:120px;bottom:58px;font:700 13px/1 var(--font-utility);letter-spacing:.15em;color:var(--ink)}.field-close-handoff .close-signature{position:absolute;right:110px;top:110px;width:330px;height:560px;border:1px solid var(--ink);background:repeating-linear-gradient(0deg,transparent 0 58px,var(--line) 59px 60px)}.field-close-handoff .close-signature:before{content:"HAND\A OFF";white-space:pre;position:absolute;left:48px;top:62px;font:800 82px/.9 var(--font-display);color:var(--support)}.field-close-handoff .close-signature i{position:absolute;right:-24px;width:48px;height:72px;background:var(--accent)}.field-close-handoff .close-signature i:nth-child(1){top:70px}.field-close-handoff .close-signature i:nth-child(2){top:210px;background:var(--support)}.field-close-handoff .close-signature i:nth-child(3){top:350px;background:var(--ink)}
'''


THEME_CSS = {
    "line-argument-journal": LINE_CSS,
    "signal-route-atlas": ROUTE_CSS,
    "field-index-manual": FIELD_CSS,
}

THEME_GRAMMARS = {
    "line-argument-journal": ("line-led-argument", "editorial-proof-sequence"),
    "signal-route-atlas": ("semantic-transit-map", "route-led-decision-system"),
    "field-index-manual": ("indexed-field-notes", "manual-led-knowledge-handoff"),
}

THEME_TECHNIQUES = {
    "line-argument-journal": [
        "argument-hairline", "editorial-margin-note", "quote-as-structure", "proof-numbering",
        "serif-led-thesis", "unboxed-comparison", "baseline-rhythm", "single-oxblood-risk-signal",
    ],
    "signal-route-atlas": [
        "semantic-route-line", "transfer-station", "source-line-coding", "ticket-taxonomy",
        "condensed-wayfinding-type", "diagonal-confidence-route", "looped-decision-map", "status-band",
    ],
    "field-index-manual": [
        "moving-index-tab", "field-ledger", "handoff-record", "approval-stamp",
        "paper-inset", "exception-tree", "catalog-numbering", "maintenance-first-resource-table",
    ],
}

# The first three accepted Themes stay in this renderer. Additional authored
# Theme packs live in a separate module so each visual system remains legible.
from authored_html_theme_extensions import (  # noqa: E402
    THEME_CSS as EXTENDED_THEME_CSS,
    THEME_GRAMMARS as EXTENDED_THEME_GRAMMARS,
    THEME_TECHNIQUES as EXTENDED_THEME_TECHNIQUES,
)

THEME_CSS.update(EXTENDED_THEME_CSS)
THEME_GRAMMARS.update(EXTENDED_THEME_GRAMMARS)
THEME_TECHNIQUES.update(EXTENDED_THEME_TECHNIQUES)

# The 2026-07 redesign replaces decoration-led CSS with a restrained editorial
# grammar.  Legacy theme definitions remain above only as design history; the
# generated decks use this module as their active source of truth.
from authored_html_theme_redesign import (  # noqa: E402
    GOOGLE_FONT_LINKS,
    REDESIGN_BASE_CSS,
    THEME_ASSET_PROVENANCE as REDESIGN_THEME_ASSET_PROVENANCE,
    THEME_CSS as REDESIGN_THEME_CSS,
    THEME_GRAMMARS as REDESIGN_THEME_GRAMMARS,
    THEME_TECHNIQUES as REDESIGN_THEME_TECHNIQUES,
    resolve_deck_design,
)


def render_slide(
    slide: dict[str, Any],
    theme_id: str,
    index: int,
    total: int,
    design: dict[str, str],
) -> str:
    composition = slide["composition"]
    renderer = RENDERERS.get(composition)
    if not renderer:
        raise ValueError(f"Unsupported composition: {composition}")
    tab = chr(65 + min(index // 3, 4)) if theme_id == "field-index-manual" else ""
    family = {
        "cover": "cover",
        "thesis": "statement",
        "index": "toc",
        "contrast": "comparison",
        "columns": "content",
        "flow": "sequence",
        "matrix": "comparison",
        "ledger": "content",
        "timeline": "sequence",
        "map": "diagram",
        "metrics": "metrics",
        "close": "statement",
    }[composition]
    active = " active" if index == 0 else ""
    index_tab = (
        f'<div class="el index-tab" data-edit-kind="text" data-edit-fit="container" '
        f'data-edit-vertical-align="center" style="left:1650px;top:84px;width:78px;height:58px">{tab}</div>'
        if tab else ""
    )
    render_context = dict(slide)
    render_context["_theme_id"] = theme_id
    render_context["_composition_variant"] = design["composition_variant"]
    render_context["_header_mode"] = design["header_mode"]
    return (
        f'<section class="slide{active} {esc(slide["layout_id"])}" id="s{index + 1}" '
        f'data-index="{index}" data-page-number="{index + 1}" data-page-count="{total}" '
        f'data-layout-id="{esc(slide["layout_id"])}" data-production-family="{family}" '
        f'data-composition="{esc(composition)}" '
        f'data-composition-variant="{esc(design["composition_variant"])}" '
        f'data-header-mode="{esc(design["header_mode"])}" '
        f'data-surface-mode="{esc(design["surface_mode"])}" '
        f'data-recipe="{esc(design.get("recipe_id", ""))}" '
        f'data-index-tab="{tab}"><div class="content" data-content-area="true">{renderer(render_context)}{index_tab}</div></section>'
    )


def build(spec: dict[str, Any], output_path: Path) -> dict[str, Any]:
    theme_id = spec["theme_id"]
    if theme_id not in REDESIGN_THEME_CSS:
        raise ValueError(f"Missing authored Theme CSS: {theme_id}")
    slides = spec["slides"]
    if len(slides) < 10:
        raise ValueError(f"Content-first deck must contain at least 10 slides: {theme_id}")
    layout_ids = [slide["layout_id"] for slide in slides]
    if len(layout_ids) != len(set(layout_ids)):
        raise ValueError(f"Layout ids must be unique inside deck: {theme_id}")
    design_decisions = resolve_deck_design(theme_id, slides)
    slides_html = "".join(
        render_slide(slide, theme_id, index, len(slides), design_decisions[index])
        for index, slide in enumerate(slides)
    )
    forbidden_slide_markup = {
        "<img": "raster image",
        "<svg": "inline SVG",
        "data:image": "embedded image",
        "background-image:url(": "image URL",
    }
    lower_slides_html = slides_html.lower()
    for marker, label in forbidden_slide_markup.items():
        if marker in lower_slides_html:
            raise ValueError(
                f"HTML slide content must be pattern/geometry-only; found {label}: {theme_id}"
            )
    validate_edit_layer_positions(slides_html)
    validate_edit_module_structures(slides_html)
    if theme_id in {"scent-veil-launch", "signal-route-atlas"} and 'class="column-slot' in slides_html:
        raise ValueError(
            f"{theme_id} column modules must own their grid geometry directly; "
            "column-slot wrappers break group resize ownership"
        )
    if theme_id == "signal-route-atlas" and 'class="metric-slot' in slides_html:
        raise ValueError(
            "Signal Route Atlas metric modules must own their grid geometry directly; "
            "metric-slot wrappers break group resize ownership"
        )
    player = editable_player_markup(slides_html, CANVAS_W, CANVAS_H)
    palette = spec["palette"]
    css = EDITABLE_PLAYER_CSS + REDESIGN_BASE_CSS + REDESIGN_THEME_CSS[theme_id]
    dialect_id, composition_mode = REDESIGN_THEME_GRAMMARS[theme_id]
    uses_explicit_recipes = any(decision.get("recipe_id") for decision in design_decisions)
    recipe_revision = str(spec.get("_recipe_revision", "v3"))
    assembly_id = f"preset-explicit-recipe-{recipe_revision}" if uses_explicit_recipes else "combinatorial-pattern-v2"
    theme_techniques = list(REDESIGN_THEME_TECHNIQUES[theme_id])
    if uses_explicit_recipes:
        theme_techniques = [
            technique
            for technique in theme_techniques
            if technique != "deterministic-composition-variation"
        ]
        theme_techniques.extend(["explicit-page-recipe", "recipe-specific-visual-system"])
    asset_policy = str(spec.get("_asset_policy", "pattern-geometry-only"))
    asset_provenance = list(
        spec.get("_asset_provenance", REDESIGN_THEME_ASSET_PROVENANCE.get(theme_id, []))
    )
    assembly_guardrails = ["single-content-area", "pure-html", "flat-loose-object-tree", "semantic-module-groups-only", "minimum-36px-generated-type", "non-selectable-centering-frame", "layout-only-containers-are-not-edit-objects", "default-text-vertical-center", "explicit-edit-positioning", "editor-embedded", "repeat-group-retired"]
    if asset_policy == "pattern-geometry-only":
        assembly_guardrails.extend(["pattern-and-geometry-only", "no-slide-illustration-assets"])
    else:
        theme_techniques = [technique for technique in theme_techniques if technique != "pattern-and-geometry-only"]
        theme_techniques.extend(["generated-raster-background", "background-asset-provenance"])
        assembly_guardrails.extend(["generated-background-opt-in", "no-css-drawn-decorative-background"])
    background_pattern = str(spec.get("_background_pattern", "theme-default"))
    document = f'''<!doctype html>
<!-- CONTENT-FIRST-AUTHORED-DECK theme={esc(theme_id)} slides={len(slides)} -->
<html lang="zh-Hant" data-theme="{esc(theme_id)}" data-theme-id="{esc(theme_id)}" data-theme-kind="authored-open-design" data-style-profile="{esc(theme_id)}" data-design-dialect="{esc(dialect_id)}" data-html-assembly="{assembly_id}" data-background-pattern="{esc(background_pattern)}" data-asset-policy="{esc(asset_policy)}" data-theme-label="{esc(spec['display_name'])}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(spec['topic']['title'])}</title>{GOOGLE_FONT_LINKS}<style>{css}</style></head>
<body>{player}</body></html>'''
    revision = hashlib.sha256(document.encode("utf-8")).hexdigest()[:20]
    document = document.replace('data-theme-label="', f'data-deck-revision="{revision}" data-theme-label="', 1)
    validate_editable_html(document)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8", newline="\n")
    ensure_edit_mode_asset(output_path.parent)
    manifest = {
        "skill": "html-pattern-slide",
        "renderer_entrypoint": "scripts/render_authored_html_deck.py",
        "contract": "references/presentation-production-contract.md",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "deck_revision": revision,
        "topic": spec["topic"],
        "audience": spec["audience"],
        "single_job": spec["single_job"],
        "theme": {
            "id": theme_id,
            "display_name": spec["display_name"],
            "kind": "authored-open-design",
            "signature": spec["signature"],
            "palette": palette,
            "typography": spec["typography"],
            "design_dialect": dialect_id,
            "composition": composition_mode,
            "background_pattern": background_pattern,
            "techniques": theme_techniques,
        },
        "html_assembly": {
            "id": assembly_id,
            "layers": ["subject", "narrative", "composition-variant", "header-placement", "surface-treatment", "theme-pattern", "editor"],
            "guardrails": assembly_guardrails,
        },
        "asset_provenance": asset_provenance,
        "layouts": layout_ids,
        "architecture": [slide["composition"] for slide in slides],
        "design_decisions": [
            {"layout_id": slide["layout_id"], **decision}
            for slide, decision in zip(slides, design_decisions, strict=True)
        ],
        "content_source": spec.get("_content_source", "prompt_system/demos/html-theme-lab.json"),
        "output": output_path.relative_to(ROOT).as_posix(),
    }
    output_path.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    raise SystemExit("Use scripts/build_html_theme_lab.py to render the authored collection")
