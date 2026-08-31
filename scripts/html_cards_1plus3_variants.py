#!/usr/bin/env python3
"""Canonical HTML composition variants for the cards-1-plus-3 Layout."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = (
    PROJECT_ROOT
    / "prompt_system"
    / "renderers"
    / "html"
    / "layout-variants"
    / "cards-1-plus-3.yaml"
)

GAP = {"none": 0, "xs": 12, "s": 20, "m": 28, "l": 40, "xl": 56}
METRIC_RE = re.compile(
    r"^(?P<value>\d[\d.,]*)\s*(?P<unit>%|萬|億|小時|分鐘|天|週|個月|年|倍|件|人|公里)?"
    r"[\s　]+(?P<rest>.+)$"
)
def esc(value: object) -> str:
    return html.escape(str(value))


def load_cards_1plus3_variant_catalog() -> dict[str, Any]:
    payload = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8")) or {}
    if payload.get("layout_id") != "cards-1-plus-3":
        raise ValueError("cards-1-plus-3 variant catalog has the wrong layout_id")
    variants = payload.get("variants")
    if not isinstance(variants, dict) or not variants:
        raise ValueError("cards-1-plus-3 variant catalog has no variants")
    return payload


CARDS_1PLUS3_VARIANT_CATALOG = load_cards_1plus3_variant_catalog()
CARDS_1PLUS3_VARIANT_IDS = tuple(CARDS_1PLUS3_VARIANT_CATALOG["variants"])


def _items(content: dict[str, Any]) -> list[tuple[str, str, str]]:
    rows = content.get("items") or []
    normalized: list[tuple[str, str, str]] = []
    for row in rows:
        if isinstance(row, dict):
            normalized.append(
                (str(row.get("title", "")), str(row.get("body", "")), str(row.get("tag", "")))
            )
        elif isinstance(row, (list, tuple)) and len(row) >= 3:
            normalized.append((str(row[0]), str(row[1]), str(row[2])))
        else:
            raise ValueError("cards-1-plus-3 items must be title/body/tag triples")
    if len(normalized) != 3:
        raise ValueError(f"cards-1-plus-3 requires exactly 3 items; got {len(normalized)}")
    return normalized


def _icon_lookup(content: dict[str, Any]) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    family = content.get("icon_family") or {}
    registry = {
        str(key).strip().upper(): str(value)
        for key, value in (family.get("registry") or {}).items()
    }
    raw_icons = family.get("icons") or []
    if isinstance(raw_icons, dict):
        icons = {str(key): dict(value) for key, value in raw_icons.items()}
    else:
        icons = {str(entry["id"]): dict(entry) for entry in raw_icons if isinstance(entry, dict) and entry.get("id")}
    return registry, icons


def _resolve_icon(
    tag: str,
    registry: dict[str, str],
    icons: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any]] | None:
    icon_id = registry.get(tag.strip().upper())
    if not icon_id:
        return None
    entry = icons.get(icon_id)
    if not entry or not str(entry.get("primitives") or "").strip():
        return None
    return icon_id, entry


def _all_icons_resolved(content: dict[str, Any], items: list[tuple[str, str, str]]) -> bool:
    registry, icons = _icon_lookup(content)
    return all(_resolve_icon(tag, registry, icons) is not None for _, _, tag in items)


def _compatible(
    variant_id: str,
    content: dict[str, Any],
    items: list[tuple[str, str, str]],
    *,
    explicit: bool,
) -> bool:
    bodies = [body.strip() for _, body, _ in items]
    if variant_id == "icon-title-body":
        return _all_icons_resolved(content, items) and all(21 <= len(body) <= 90 for body in bodies)
    if variant_id == "side-icon-body":
        return _all_icons_resolved(content, items) and all(36 <= len(body) <= 140 for body in bodies)
    if variant_id == "metric-title":
        return all(METRIC_RE.match(body) for body in bodies)
    if variant_id == "label-rule-body":
        return True
    return False


def resolve_cards_1plus3_variant(
    content: dict[str, Any],
    requested_variant: str | None = None,
) -> str:
    items = _items(content)
    if requested_variant:
        if requested_variant not in CARDS_1PLUS3_VARIANT_IDS:
            raise ValueError(f"Unknown cards-1-plus-3 variant: {requested_variant}")
        if not _compatible(requested_variant, content, items, explicit=True):
            raise ValueError(
                f"cards-1-plus-3 variant {requested_variant!r} is incompatible with the supplied content"
            )
        return requested_variant

    for variant_id in CARDS_1PLUS3_VARIANT_CATALOG["auto_selection_order"]:
        if _compatible(variant_id, content, items, explicit=False):
            return variant_id
    return "label-rule-body"


def _alignment_attrs() -> str:
    return ' data-edit-horizontal-align="left" data-edit-alignment-source="module-interior"'


def _band(
    css_class: str,
    inner: str,
    gap: str,
    *,
    tag: str = "div",
) -> str:
    margin = GAP[gap]
    style = f' style="margin-top:{margin}px"' if margin else ""
    return (
        f'<{tag} class="{css_class}" data-edit-layer="text" data-edit-position="flow"'
        f'{_alignment_attrs()} data-layout-item{style}>{inner}</{tag}>'
    )


def _sub_layer(css_class: str, inner: str, *, layer: str = "text", style: str = "") -> str:
    style_attr = f' style="{style}"' if style else ""
    alignment = _alignment_attrs() if layer in {"text", "metric"} else ""
    return (
        f'<div class="{css_class}" data-edit-layer="{layer}" data-edit-position="flow"'
        f'{alignment} data-layout-item{style_attr}>{inner}</div>'
    )


def _absolute_sub_layer(
    css_class: str,
    inner: str,
    *,
    layer: str,
    style: str,
) -> str:
    alignment = _alignment_attrs() if layer in {"text", "metric"} else ""
    return (
        f'<div class="{css_class}" data-edit-layer="{layer}" data-edit-position="absolute"'
        f'{alignment} style="{style}">{inner}</div>'
    )


def _fixed_band(
    css_class: str,
    inner: str,
    gap: str,
    *,
    layer: str,
    height: int,
    width: str = "100%",
    child_top: int = 0,
) -> str:
    margin = GAP[gap]
    wrapper_style = f"position:relative;width:{width};height:{height}px"
    if margin:
        wrapper_style += f";margin-top:{margin}px"
    child_style = f"left:0;top:{child_top}px;width:100%;height:{height - child_top}px"
    return (
        '<div class="cards-1plus3-fixed-band" data-edit-layout-only="true" '
        f'data-layout-item style="{wrapper_style}">'
        + _absolute_sub_layer(css_class, inner, layer=layer, style=child_style)
        + "</div>"
    )


def _group_band(css_class: str, inner: str, gap: str, *, auto_layout: str) -> str:
    margin = GAP[gap]
    style = f' style="margin-top:{margin}px"' if margin else ""
    return (
        f'<div class="{css_class}" data-edit-layout-only="true" '
        f'data-auto-layout="{auto_layout}" data-layout-item{style}>{inner}</div>'
    )


def _head_row(label: str, gap: str, *, tag_tone: bool = False) -> str:
    label_class = "cards-1plus3-head-label is-tag" if tag_tone else "cards-1plus3-head-label"
    return _group_band(
        "cards-1plus3-head-row",
        _sub_layer(label_class, esc(label))
        + '<div class="cards-1plus3-head-rule-slot" data-edit-layout-only="true" '
        'data-layout-item><div class="cards-1plus3-head-rule" data-edit-layer="visual" '
        'data-edit-position="absolute" style="left:0;top:0;width:100%;height:1px"></div></div>',
        gap,
        auto_layout="cards-1plus3-head-row",
    )


def _rule(gap: str, *, short: bool = False) -> str:
    css_class = "cards-1plus3-rule is-short" if short else "cards-1plus3-rule"
    return _fixed_band(
        css_class,
        "",
        gap,
        layer="visual",
        height=1,
        width="72px" if short else "100%",
    )


def _icon_svg(
    icon_id: str,
    entry: dict[str, Any],
    *,
    label: str,
    size: int = 56,
) -> str:
    css_class = "cards-1plus3-icon is-large" if size > 56 else "cards-1plus3-icon"
    primitives = str(entry["primitives"])
    return (
        f'<svg class="{css_class}" data-edit-layer="visual" data-edit-position="absolute" '
        f'data-icon-role="semantic" data-icon-id="{esc(icon_id)}" '
        f'role="img" aria-label="{esc(label)}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" style="left:0;top:0;width:{size}px;height:{size}px">{primitives}</svg>'
    )


def _icon_band(
    icon_id: str,
    entry: dict[str, Any],
    *,
    label: str,
    gap: str = "none",
    size: int = 56,
) -> str:
    margin = GAP[gap]
    style = f"position:relative;width:{size}px;height:{size}px"
    if margin:
        style += f";margin-top:{margin}px"
    return (
        '<div class="cards-1plus3-icon-slot" data-edit-layout-only="true" '
        f'data-layout-item style="{style}">'
        + _icon_svg(icon_id, entry, label=label, size=size)
        + "</div>"
    )


def _render_item(
    variant_id: str,
    item: tuple[str, str, str],
    index: int,
    content: dict[str, Any],
) -> str:
    title, body, tag = item
    registry, icons = _icon_lookup(content)
    resolved = _resolve_icon(tag, registry, icons)

    if variant_id == "icon-title-body":
        assert resolved is not None
        icon_id, entry = resolved
        return (
            _icon_band(icon_id, entry, label=title)
            + _band("cards-1plus3-title", esc(title), "l")
            + _band("cards-1plus3-body", esc(body), "s")
        )

    if variant_id == "metric-title":
        match = METRIC_RE.match(body.strip())
        assert match is not None
        unit = match.group("unit") or ""
        metric = esc(match.group("value") + unit)
        markup = (
            _head_row(tag, "none", tag_tone=True)
            + _band("cards-1plus3-title", esc(title), "m")
            + _fixed_band(
                "cards-1plus3-metric",
                metric,
                "s",
                layer="metric",
                height=108,
                child_top=4,
            )
        )
        if match.group("rest").strip():
            markup += _band("cards-1plus3-body", esc(match.group("rest")), "s")
        return markup

    if variant_id == "label-rule-body":
        return (
            _band("cards-1plus3-eyebrow", esc(tag), "none")
            + _rule("s")
            + _band("cards-1plus3-title", esc(title), "m")
            + _band("cards-1plus3-body", esc(body), "s")
        )

    if variant_id == "side-icon-body":
        assert resolved is not None
        icon_id, entry = resolved
        copy = _sub_layer("cards-1plus3-title", esc(title)) + _sub_layer(
            "cards-1plus3-body", "　　" + esc(body), style=f"margin-top:{GAP['s']}px"
        )
        return _group_band(
            "cards-1plus3-side-row",
            _icon_band(icon_id, entry, label=title)
            + '<div class="cards-1plus3-side-copy" data-edit-layout-only="true" '
            f'data-auto-layout="cards-1plus3-side-copy" data-layout-item>{copy}</div>',
            "none",
            auto_layout="cards-1plus3-side-row",
        )

    raise ValueError(f"Unsupported cards-1-plus-3 variant: {variant_id}")


def render_cards_1plus3_variant(
    content: dict[str, Any],
    requested_variant: str | None = None,
) -> tuple[str, str]:
    items = _items(content)
    variant_id = resolve_cards_1plus3_variant(content, requested_variant)
    surfaces = []
    for index, item in enumerate(items, 1):
        interior = _render_item(variant_id, item, index, content)
        inherit_page_title = variant_id == "icon-title-body"
        if inherit_page_title:
            interior = interior.replace(_alignment_attrs(), "")
        module_alignment = "" if inherit_page_title else ' data-module-interior-align="left"'
        surfaces.append(
            f'<div class="el diagram-node cards-1plus3-surface card-{index}" '
            f'data-edit-composite="cards-1plus3-{index}"{module_alignment} '
            f'data-auto-layout="cards-1plus3-surface" data-layout-variant-id="{variant_id}">'
            '<div class="diagram-node-bg" data-edit-layer="background" '
            'data-edit-position="absolute"></div>'
            f'{interior}</div>'
        )
    row = (
        '<div class="cards-1plus3-row layout-flow-follow-region" data-edit-layout-only="true" '
        'data-auto-layout="cards-1plus3-row" data-layout-follow="primary-header" '
        'data-layout-follow-gap="56" style="left:0;top:0;width:1728px;height:auto" '
        f'data-layout-variant-id="{variant_id}">{"".join(surfaces)}</div>'
    )
    return row, variant_id


CARDS_1PLUS3_VARIANT_CSS = r"""
.cards-1plus3-row{position:absolute;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));column-gap:48px;align-items:stretch;pointer-events:none}
.cards-1plus3-row>.el{position:relative;pointer-events:auto}
.cards-1plus3-surface{display:block;padding:40px 44px;overflow:visible;border-radius:18px;background:transparent}
.cards-1plus3-surface>.diagram-node-bg{position:absolute;inset:0;border-radius:18px}
.cards-1plus3-surface [data-edit-layer][data-edit-position="flow"],.cards-1plus3-surface [data-edit-layout-only="true"]{position:relative;left:auto;right:auto;top:auto;bottom:auto;display:block;z-index:2;min-width:0}
.cards-1plus3-eyebrow{font:700 36px/1.24 var(--font-mono);letter-spacing:.12em;color:var(--surface-muted)}
.cards-1plus3-title{font:800 52px/1.16 var(--font-heading);letter-spacing:-.02em;color:var(--surface-text)}
.cards-1plus3-body{font:450 36px/1.45 var(--font-body);color:var(--surface-muted)}
.cards-1plus3-metric{display:flex!important;flex-direction:row!important;align-items:baseline!important;justify-content:flex-start!important;white-space:nowrap;font:850 104px/1 var(--font-display);font-variant-numeric:tabular-nums;letter-spacing:-.03em;color:var(--accent)}
.cards-1plus3-rule{height:1px;background:color-mix(in srgb,var(--surface-text) 24%,transparent)}
.cards-1plus3-rule.is-short{width:72px}
.cards-1plus3-icon{display:block;width:56px;height:56px;color:var(--accent)}
.cards-1plus3-head-row{display:flex;align-items:center;gap:20px;width:100%}
.cards-1plus3-head-label{flex:0 0 auto;width:auto;font:700 36px/1 var(--font-mono);letter-spacing:.1em;color:var(--surface-accent-ink)}
.cards-1plus3-head-label.is-tag{letter-spacing:.12em;color:var(--surface-muted)}
.cards-1plus3-head-rule{flex:1 1 auto;height:1px;background:color-mix(in srgb,var(--surface-text) 24%,transparent)}
.cards-1plus3-side-row{display:grid!important;grid-template-columns:56px minmax(0,1fr);column-gap:28px;align-items:start;width:100%}
.cards-1plus3-side-copy{display:block;min-width:0}
"""
