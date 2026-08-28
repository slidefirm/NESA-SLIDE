#!/usr/bin/env python3
"""Append archived Preset slides to a current editable HTML deck.

The current deck remains the owner of the editor, runtime, CSS, and player
shell.  Only the archived slide DOM is transplanted, re-indexed, and marked as
previous-version content.  This keeps the old HTML's embedded editor/runtime
from becoming a second active runtime in the combined deck.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


SECTION_TOKEN_RE = re.compile(r"<\/?section\b[^>]*>", re.IGNORECASE)
SECTION_OPEN_RE = re.compile(r"<section\b[^>]*>", re.IGNORECASE)
ATTR_RE = re.compile(r"\b([a-zA-Z_:][-a-zA-Z0-9_:.]*)=(['\"])(.*?)\2")
STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>([\s\S]*?)</style\s*>", re.IGNORECASE)


def portable(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def extract_legacy_css(markup: str) -> str:
    blocks = STYLE_BLOCK_RE.findall(markup)
    return blocks[0] if blocks else ""


def legacy_cover_css(preset_id: str) -> str:
    """Keep the distinctive archived cover treatment without importing all old CSS."""

    prefix = '.slide[data-version="previous"][data-layout-id="cover-center-title-edge-decor"]'
    if preset_id == "clinical-evidence-atlas":
        return f"""
{prefix} {{
  background-color: #F5F8FA !important;
  background-image: linear-gradient(90deg, transparent 0 68%, rgba(11,122,117,.08) 68% 100%), linear-gradient(90deg, transparent 0 74%, rgba(217,108,95,.16) 74% 74.4%, transparent 74.4%), linear-gradient(rgba(11,122,117,.025) 1px, transparent 1px), linear-gradient(90deg, rgba(11,122,117,.025) 1px, transparent 1px) !important;
  background-size: 100% 100%, 100% 100%, 64px 64px, 64px 64px !important;
  box-shadow: inset 18px 0 0 #0B7A75 !important;
  color: #17343D !important;
}}
{prefix} .cover-edge-decor,
{prefix} .cover-logo {{ display: none !important; }}
{prefix} .cover-center-area {{ left: 0 !important; top: 0 !important; width: 1728px !important; height: 888px !important; display: flex !important; flex-direction: column !important; align-items: flex-start !important; justify-content: center !important; text-align: left !important; padding: 0 480px 0 112px !important; gap: 24px !important; }}
{prefix} .cover-center-title {{ max-width: 1120px !important; text-align: left !important; font: 800 104px/1.03 var(--font-heading) !important; letter-spacing: -.055em !important; color: #17343D !important; -webkit-text-fill-color: #17343D !important; }}
{prefix} .cover-center-rule {{ width: 244px !important; height: 7px !important; background: linear-gradient(90deg, #0B7A75 0 72%, #D96C5F 72% 100%) !important; }}
{prefix} .cover-center-subtitle {{ max-width: 1100px !important; text-align: left !important; font: 500 38px/1.38 var(--font-body) !important; color: #58707A !important; }}
{prefix} .cover-center-speaker,
{prefix} .cover-center-org {{ text-align: left !important; color: #0B7A75 !important; }}
{prefix} .cover-center-org {{ position: absolute !important; left: 1540px !important; top: 98px !important; width: max-content !important; height: max-content !important; max-height: 700px !important; white-space: nowrap !important; writing-mode: vertical-rl !important; text-orientation: mixed !important; }}
""".strip()
    if preset_id == "sepia-retail-case":
        return f"""
{prefix} {{ background-color: #F3EDE3 !important; background-image: radial-gradient(circle at 98% 96%, transparent 0 220px, rgba(102,69,48,.075) 221px 223px, transparent 224px 332px, rgba(102,69,48,.05) 333px 335px, transparent 336px), linear-gradient(116deg, rgba(177,122,74,.10), transparent 34%), radial-gradient(circle, rgba(61,40,28,.045) 0 1px, transparent 1.5px) !important; background-size: 100% 100%, 100% 100%, 6px 6px !important; color: #2D211B !important; }}
{prefix} .cover-edge-decor,
{prefix} .cover-logo {{ display: none !important; }}
{prefix} .cover-center-area {{ left: 104px !important; width: 1450px !important; align-items: flex-start !important; text-align: left !important; gap: 26px !important; }}
{prefix} .cover-center-title {{ max-width: 1120px !important; text-align: left !important; font: 700 108px/1.04 var(--font-display) !important; letter-spacing: -.05em !important; color: #2D211B !important; }}
{prefix} .cover-center-rule {{ width: 210px !important; height: 4px !important; background: linear-gradient(90deg, #A96938, rgba(169,105,56,.08)) !important; }}
{prefix} .cover-center-subtitle {{ max-width: 1210px !important; text-align: left !important; font: 500 38px/1.45 var(--font-display) !important; color: #6F5E54 !important; }}
{prefix} .cover-center-speaker,
{prefix} .cover-center-org {{ text-align: left !important; color: #6F5E54 !important; }}
""".strip()
    return ""


def split_selector_list(selector_text: str) -> list[str]:
    selectors: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    for index, char in enumerate(selector_text):
        if quote:
            if char == quote:
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            selectors.append(selector_text[start:index].strip())
            start = index + 1
    selectors.append(selector_text[start:].strip())
    return [item for item in selectors if item]


def scope_legacy_css(css: str) -> str:
    """Scope the old appearance rules to appended previous-version slides."""

    prefix = '.slide[data-version="previous"]'
    rules: list[str] = []
    depth = 0
    start = 0
    quote: str | None = None
    selector_start: int | None = None
    for index, char in enumerate(css):
        if quote:
            if char == quote and (index == 0 or css[index - 1] != "\\"):
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == "{" and depth == 0:
            selector_start = start
            depth = 1
            body_start = index + 1
        elif char == "{" and depth > 0:
            depth += 1
        elif char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and selector_start is not None:
                selector = css[selector_start:index].strip()
                body = css[body_start:index].strip()
                scoped_selectors: list[str] = []
                for item in split_selector_list(selector):
                    compact = re.sub(r"\s+", " ", item).strip()
                    if not compact or compact.startswith("@"):
                        continue
                    if compact in {"*", "html", "body", "html,body"}:
                        continue
                    if compact.startswith(("#player", "#canvasBox", "#stage", "#bar", "#slideRail", "#hint")):
                        continue
                    if compact.startswith(":root"):
                        scoped_selectors.append(re.sub(r"^:root", prefix, compact, count=1))
                    elif re.match(r"^html(?:\[[^]]+\])?", compact, re.IGNORECASE):
                        scoped_selectors.append(re.sub(r"^html(?:\[[^]]+\])?", prefix, compact, count=1, flags=re.IGNORECASE))
                    elif compact.startswith("body"):
                        continue
                    elif compact.startswith(".slide"):
                        scoped_selectors.append(re.sub(r"^\.slide", prefix, compact, count=1))
                    else:
                        scoped_selectors.append(f"{prefix} {compact}")
                if scoped_selectors:
                    rules.append(",".join(scoped_selectors) + "{" + body + "}")
                start = index + 1
                selector_start = None
    return "\n".join(rules)


def extract_sections(markup: str) -> list[str]:
    """Extract top-level section elements without reparsing their inner HTML."""

    sections: list[str] = []
    depth = 0
    start: int | None = None
    for token in SECTION_TOKEN_RE.finditer(markup):
        token_text = token.group(0)
        is_close = token_text.startswith("</")
        if not is_close:
            if depth == 0:
                start = token.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0 and start is not None:
                sections.append(markup[start : token.end()])
                start = None
    if depth != 0:
        raise ValueError("Unbalanced <section> markup")
    return sections


def opening_tag(section: str) -> str:
    match = SECTION_OPEN_RE.search(section)
    if not match:
        raise ValueError("Section is missing an opening tag")
    return match.group(0)


def attr(tag: str, name: str, default: str = "") -> str:
    pattern = re.compile(rf"\b{re.escape(name)}=(['\"])(.*?)\1", re.IGNORECASE)
    match = pattern.search(tag)
    return match.group(2) if match else default


def family_intent(family: str, layout_id: str) -> str:
    if family == "cover":
        return "cover"
    if family == "toc":
        return "navigation"
    if family == "comparison":
        return "comparison"
    if family in {"metrics", "data-viz"}:
        return "evidence"
    if family == "sequence":
        return "sequence"
    if family == "modules":
        return "modules"
    if family == "content":
        return "prioritization"
    if family == "statement":
        return "statement"
    if layout_id == "pyramid":
        return "hierarchy"
    if layout_id == "cycle-hub-6":
        return "cycle"
    return "evidence"


def scene_role(intent: str) -> str:
    return {
        "cover": "hero",
        "navigation": "index-or-map",
        "comparison": "relationship",
        "evidence": "evidence",
        "sequence": "relationship",
        "modules": "evidence",
        "prioritization": "relationship",
        "statement": "pause-or-close",
        "hierarchy": "relationship",
        "cycle": "relationship",
    }.get(intent, "evidence")


def add_attr(tag: str, name: str, value: str) -> str:
    if re.search(rf"\b{re.escape(name)}=", tag):
        return tag
    return tag[:-1] + f' {name}="{value}"' + tag[-1:]


def normalize_layer_attributes(section: str) -> str:
    """Project legacy layer metadata onto the current editor's basic contract."""

    section = re.sub(
        r"\s+data-edit-repeat-[a-zA-Z0-9_-]+=(['\"]).*?\1",
        "",
        section,
    )

    def normalize_tag(match: re.Match[str]) -> str:
        tag = match.group(0)
        layer = attr(tag, "data-edit-layer")
        if layer:
            tag = add_attr(tag, "data-edit-position", "absolute")
            if layer in {"text", "metric"}:
                tag = add_attr(tag, "data-edit-vertical-align", "center")
        classes = set(attr(tag, "class").split())
        if "prod-frame" in classes and attr(tag, "data-visual-balance") == "content-bounds":
            tag = add_attr(tag, "data-edit-layout-only", "true")
        return tag

    normalized = re.sub(r"<(?!(?:script|style)\b)[^>]+>", normalize_tag, section, flags=re.IGNORECASE)

    # Legacy composites are not all semantic modules.  A rail or connector
    # may carry data-edit-composite for the old editor but has no selectable
    # background layer.  Only promote roots whose first child is a real
    # background layer; leave visual-only composites as loose editable roots.
    composite_pattern = re.compile(
        r"""(?P<open><(?:div|svg|article)\b[^>]*\bclass=(["'])[^"']*\bel\b[^"']*\2
        [^>]*\bdata-edit-composite=(["'])[^"']+\3[^>]*>)
        (?P<space>\s*)(?P<first><[^>]+>)""",
        re.IGNORECASE | re.VERBOSE,
    )

    def normalize_composite(match: re.Match[str]) -> str:
        opener = match.group("open")
        first_child = match.group("first")
        has_background = 'data-edit-layer="background"' in first_child or "data-edit-layer='background'" in first_child
        if has_background:
            opener = add_attr(opener, "data-edit-structure", "module")
        else:
            opener = re.sub(r"\s+data-edit-structure=(['\"]).*?\1", "", opener)
        return opener + match.group("space") + first_child

    return composite_pattern.sub(normalize_composite, normalized)


def namespace_fragment_ids(fragment: str, prefix: str) -> str:
    exact_id = r"(?<![-:A-Za-z0-9_])id=(['\"])(.*?)\1"
    ids = list(dict.fromkeys(re.findall(exact_id, fragment)))
    mapping = {old: f"{prefix}-{index}-{old}" for index, (_quote, old) in enumerate(ids, 1)}
    for old, new in mapping.items():
        fragment = re.sub(
            rf"(?<![-:A-Za-z0-9_])id=(['\"]){re.escape(old)}\1",
            f'id="{new}"',
            fragment,
        )
        fragment = fragment.replace(f"url(#{old})", f"url(#{new})")
        fragment = fragment.replace(f'href="#{old}"', f'href="#{new}"')
        fragment = fragment.replace(f"href='#{old}'", f"href='#{new}'")
        fragment = fragment.replace(f'xlink:href="#{old}"', f'xlink:href="#{new}"')
        fragment = fragment.replace(f"xlink:href='#{old}'", f"xlink:href='#{new}'")
    return fragment


def normalize_slide(
    section: str,
    *,
    preset_id: str,
    old_index: int,
    new_index: int,
    total_pages: int,
    old_total: int,
) -> tuple[str, dict[str, Any]]:
    tag = opening_tag(section)
    layout_id = attr(tag, "data-layout-id", "archived-unknown")
    family = attr(tag, "data-production-family", "content")
    intent = family_intent(family, layout_id)
    role = scene_role(intent)
    old_page = int(attr(tag, "data-page-number", str(old_index + 1)))
    intensity_cycle = (3, 2, 4, 3, 1, 4, 3, 2)
    intensity = intensity_cycle[old_index % len(intensity_cycle)]

    fragment = namespace_fragment_ids(section, f"previous-{preset_id}")
    fragment = normalize_layer_attributes(fragment)
    tag = opening_tag(fragment)
    tag = re.sub(r"\bclass=(['\"])(.*?)\1", lambda m: f'class="{m.group(2).replace(" active", "")}"', tag, count=1)
    tag = re.sub(
        r"(?<![-:A-Za-z0-9_])id=(['\"]).*?\1",
        f'id="s{new_index}"',
        tag,
        count=1,
    )
    tag = re.sub(r"\bdata-index=(['\"])\d+\1", f'data-index="{new_index - 1}"', tag, count=1)
    tag = re.sub(r"\bdata-page-number=(['\"])\d+\1", f'data-page-number="{new_index}"', tag, count=1)
    tag = re.sub(r"\bdata-page-count=(['\"])\d+\1", f'data-page-count="{total_pages}"', tag, count=1)
    tag = add_attr(tag, "data-version", "previous")
    tag = add_attr(tag, "data-previous-page-number", str(old_page))
    tag = add_attr(tag, "data-previous-page-count", str(old_total))
    tag = add_attr(tag, "data-scene-id", f"previous-{new_index:02d}")
    tag = add_attr(tag, "data-scene-role", role)
    tag = add_attr(tag, "data-visual-intensity", str(intensity))
    fragment = tag + fragment[len(opening_tag(fragment)) :]

    content_hash = sha256_text(fragment)
    page_id = f"previous-{preset_id}-page-{old_page:02d}"
    metadata = {
        "page_index": new_index,
        "page_id": page_id,
        "intent": intent,
        "layout_id": layout_id,
        "family": family,
        "role": role,
        "visual_intensity": intensity,
        "content_sha256": content_hash,
        "old_page_number": old_page,
    }
    return fragment, metadata


def append_to_html(
    new_html: str,
    old_html: str,
    *,
    preset_id: str,
    old_source: str,
) -> tuple[str, list[dict[str, Any]]]:
    new_sections = extract_sections(new_html)
    old_sections = extract_sections(old_html)
    if not new_sections or not old_sections:
        raise ValueError("Both decks must contain at least one slide")
    total_pages = len(new_sections) + len(old_sections)
    normalized: list[str] = []
    metadata: list[dict[str, Any]] = []
    for old_index, section in enumerate(old_sections):
        normalized_section, row = normalize_slide(
            section,
            preset_id=preset_id,
            old_index=old_index,
            new_index=len(new_sections) + old_index + 1,
            total_pages=total_pages,
            old_total=len(old_sections),
        )
        normalized.append(normalized_section)
        metadata.append(row)
    insertion = (
        f'\n<!-- ARCHIVED PREVIOUS VERSION: {old_source}; '
        f'pages={len(new_sections) + 1}-{total_pages} -->\n'
        + "\n".join(normalized)
        + "\n"
    )
    stage_match = re.search(
        r'(?P<open><main\b[^>]*\bid=["\']stage["\'][^>]*>)(?P<body>[\s\S]*?)(?P<close></main>)',
        new_html,
        re.IGNORECASE,
    )
    if not stage_match:
        raise ValueError("Current deck is missing <main id=\"stage\">")
    combined = new_html[: stage_match.end("body")] + insertion + new_html[stage_match.end("body") :]
    def append_root_metadata(match: re.Match[str]) -> str:
        return (
            match.group(1)
            + ' data-previous-version-appended="true"'
            + f' data-previous-version-source="{old_source}"'
            + f' data-previous-version-page-start="{len(new_sections) + 1}"'
            + f' data-previous-version-page-end="{total_pages}"'
            + match.group(2)
        )

    combined = re.sub(
        r'(<html\b[^>]*)(>)',
        append_root_metadata,
        combined,
        count=1,
        flags=re.IGNORECASE,
    )
    scoped_legacy_css = legacy_cover_css(preset_id)
    if scoped_legacy_css:
        legacy_style = (
            '<style data-css-owner="renderer-base" '
            'data-archived-previous-style="true">\n'
            f"{scoped_legacy_css}\n"
            "</style>\n"
        )
        combined, count = re.subn(
            r"</head\s*>",
            legacy_style + "</head>",
            combined,
            count=1,
            flags=re.IGNORECASE,
        )
        if count != 1:
            raise ValueError("Current deck is missing </head> for scoped archived CSS")
    revision = sha256_text(combined)[:20]
    combined = re.sub(
        r'(data-deck-revision=["\'])[^"\']+(["\'])',
        rf'\g<1>{revision}\g<2>',
        combined,
        count=1,
    )
    return combined, metadata


def update_manifest(
    manifest: dict[str, Any],
    *,
    metadata: list[dict[str, Any]],
    preset_id: str,
    old_source: str,
    output_html: Path,
    old_html: str,
    combined_html: str,
) -> dict[str, Any]:
    old_layouts = [row["layout_id"] for row in metadata]
    old_architecture = [row["family"] for row in metadata]
    old_intents = [row["intent"] for row in metadata]
    old_composition_plan: list[dict[str, Any]] = []
    old_content_pages: list[dict[str, Any]] = []
    old_content_plan: list[dict[str, Any]] = []
    old_decisions: list[dict[str, Any]] = []
    for row in metadata:
        page_id = row["page_id"]
        old_content_plan.append(
            {
                "page_index": row["page_index"],
                "page_id": page_id,
                "intent": row["intent"],
                "content_key": "previous-version",
                "source_fields": ["archived_html"],
                "content_relation": "previous-version-reference",
                "content_item_count": None,
                "plan_source": "previous-version-archive",
            }
        )
        old_content_pages.append(
            {
                "page_id": page_id,
                "intent": row["intent"],
                "content_key": "previous-version",
                "content_relation": "previous-version-reference",
                "content_item_count": None,
                "source_fields": ["archived_html"],
                "content_sha256": row["content_sha256"],
            }
        )
        old_composition_plan.append(
            {
                "stage": "archived-previous-version",
                "owner": "archived-html-slide",
                "content_item_count": None,
                "fit_policy": "preserve-archived-materialized-dom",
                "capacity_role": "archived-reference",
                "remediation_order": [],
                "content_page_id": page_id,
                "content_sha256": row["content_sha256"],
                "layout_scaffold_id": row["layout_id"],
                "layout_role": "archived-previous-version",
                "composition_source": "archived-html-slide",
                "rendered_item_count": None,
                "content_identity_preserved": True,
                "content_mutated": False,
            }
        )
        old_decisions.append(
            {
                "intent": row["intent"],
                "layout_id": row["layout_id"],
                "layout_role": "archived-previous-version",
                "signature_composition": "保留舊版頁面作為版本參照",
                "ordinary_grid_loss": "舊版原始資訊關係與視覺證據",
                "visual_intensity": "medium",
                "source": "forced-layout",
                "route_match": False,
                "selection_candidates": [row["layout_id"]],
                "selection_basis": "previous-version-archive",
                "asset_policy": "pattern-only",
                "media_requirement": "no-image",
                "content_plan_index": row["page_index"],
                "content_page_id": row["page_id"],
                "content_key": "previous-version",
                "content_source_fields": ["archived_html"],
                "content_relation": "previous-version-reference",
                "content_item_count": None,
                "composition_feedback": {
                    "stage": "archived-previous-version",
                    "owner": "archived-html-slide",
                    "content_item_count": None,
                    "fit_policy": "preserve-archived-materialized-dom",
                    "capacity_role": "archived-reference",
                    "remediation_order": [],
                },
                "composition_variant": f"previous-version-{row['layout_id']}",
                "header_mode": "archived-previous-version",
                "surface_mode": "archived-previous-version",
                "variant_source": "previous-version-archive",
            }
        )

    current_count = len(manifest.get("layouts") or [])
    manifest["layouts"] = list(manifest.get("layouts") or []) + old_layouts
    manifest["architecture"] = list(manifest.get("architecture") or []) + old_architecture
    manifest["content_plan"] = list(manifest.get("content_plan") or []) + old_content_plan
    manifest["content_pages"] = list(manifest.get("content_pages") or []) + old_content_pages
    manifest["composition_plan"] = list(manifest.get("composition_plan") or []) + old_composition_plan
    manifest["layout_decisions"] = list(manifest.get("layout_decisions") or []) + old_decisions
    layout_media = manifest.get("layout_media") or {}
    media_modes = dict(layout_media.get("layout_media_modes") or {})
    for layout_id in old_layouts:
        media_modes[layout_id] = "no-image"
    layout_media["layout_media_modes"] = media_modes
    counts = dict(layout_media.get("counts") or {})
    counts["no-image"] = int(counts.get("no-image", 0)) + len(old_layouts)
    layout_media["counts"] = counts
    manifest["layout_media"] = layout_media

    art_direction = manifest.get("art_direction") or {}
    renderers = art_direction.get("renderers") or {}
    html_renderer = renderers.get("html") or {}
    html_renderer["layout_sequence"] = list(html_renderer.get("layout_sequence") or []) + old_layouts
    renderers["html"] = html_renderer
    art_direction["renderers"] = renderers
    scene_plan = list(art_direction.get("scene_plan") or [])
    scene_plan.extend(
        {
            "slide_id": f"previous-{row['page_index']:02d}",
            "role": row["role"],
            "visual_intensity": row["visual_intensity"],
            "primary_focus": f"Previous version · {row['layout_id']}",
            "signature_move_variant": "previous-version",
        }
        for row in metadata
    )
    art_direction["scene_plan"] = scene_plan
    manifest["art_direction"] = art_direction

    manifest["previous_version_append"] = {
        "schema_version": 1,
        "preset_id": preset_id,
        "source_html": old_source,
        "source_html_sha256": hashlib.sha256(old_html.encode("utf-8")).hexdigest(),
        "source_slide_count": len(metadata),
        "new_slide_count": current_count,
        "combined_slide_count": len(manifest["layouts"]),
        "page_range": [current_count + 1, len(manifest["layouts"])],
        "mode": "append-archived-materialized-slides",
        "old_editor_runtime_embedded": False,
        "current_editor_runtime_owner": "current-new-deck",
        "legacy_appearance": "scoped-cover-only",
        "legacy_full_stylesheet_embedded": False,
        "layout_ids": old_layouts,
        "architecture": old_architecture,
        "intents": old_intents,
    }
    manifest["output"] = portable(output_html)
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    manifest["deck_revision"] = sha256_text(combined_html)[:20]
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--new-html", type=Path, required=True)
    parser.add_argument("--new-manifest", type=Path, required=True)
    parser.add_argument("--previous-html", type=Path, required=True)
    parser.add_argument("--output-html", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument("--preset-id", required=True)
    args = parser.parse_args()

    new_html_path = args.new_html.resolve()
    new_manifest_path = args.new_manifest.resolve()
    previous_html_path = args.previous_html.resolve()
    output_html = args.output_html.resolve()
    output_manifest = args.output_manifest.resolve()
    new_html = new_html_path.read_text(encoding="utf-8")
    previous_html = previous_html_path.read_text(encoding="utf-8")
    manifest = json.loads(new_manifest_path.read_text(encoding="utf-8"))
    old_source = portable(previous_html_path)
    combined_html, metadata = append_to_html(
        new_html,
        previous_html,
        preset_id=args.preset_id,
        old_source=old_source,
    )
    updated_manifest = update_manifest(
        manifest,
        metadata=metadata,
        preset_id=args.preset_id,
        old_source=old_source,
        output_html=output_html,
        old_html=previous_html,
        combined_html=combined_html,
    )
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(combined_html, encoding="utf-8", newline="\n")
    output_manifest.write_text(
        json.dumps(updated_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "preset_id": args.preset_id,
                "new_pages": len(extract_sections(new_html)),
                "previous_pages": len(metadata),
                "combined_pages": len(updated_manifest["layouts"]),
                "output_html": portable(output_html),
                "output_manifest": portable(output_manifest),
                "editor_sha256": updated_manifest["editable_dom"]["editor_sha256"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
