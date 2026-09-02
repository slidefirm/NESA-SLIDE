#!/usr/bin/env python3
"""Verify page content stays independent from HTML Layout scaffold identity."""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import html_production_renderer as production  # noqa: E402
from html_design_method import resolve_content_plan, resolve_layout_plan  # noqa: E402
from render_randomized_html_demo import (  # noqa: E402
    HTML_DESIGN_METHOD,
    STORIES,
    build_semantic_pages,
    compose_page_content,
)


FORCED_LAYOUTS = [
    "cover-center-title-edge-decor",
    "toc-3",
    "strategic-priorities",
    "before-after",
    "kpi-scorecards",
    "process-flow",
    "quote-focus",
    "title-center",
]


def _contains_layout_identity(value: Any) -> bool:
    if isinstance(value, dict):
        if {"layout_id", "layout_scaffold_id", "preferred_layout"} & set(value):
            return True
        return any(_contains_layout_identity(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_layout_identity(item) for item in value)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    story = next(row for row in STORIES if row["id"] == "craft-memory-atlas")
    content_plan = resolve_content_plan(story, HTML_DESIGN_METHOD)
    semantic_pages = build_semantic_pages(story, content_plan)
    navigation_page = next(page for page in semantic_pages if page["intent"] == "navigation")
    if _contains_layout_identity(navigation_page):
        raise AssertionError("semantic page content contains Layout identity")

    matrix = json.loads(
        (ROOT / "artifacts" / "renderer-matrix" / "matrix.json").read_text(encoding="utf-8")
    )
    layout_lookup = {row["id"]: row for row in matrix["layouts"]}
    # This authored-scene Layout intentionally has no Gallery fixture and must
    # reach the generic renderer when page content is absent. Cover layouts are
    # no longer valid probes because production now materializes their fixtures.
    generic_fallback_id = "infographic-stage"
    if production.render_production_layout(layout_lookup[generic_fallback_id]) is not None:
        raise AssertionError("Layout without a production fixture did not reach the generic renderer")
    fixture_before = json.dumps(
        {"items": production.TOC_ITEMS, "context": production.TOC_CONTEXT},
        ensure_ascii=False,
        sort_keys=True,
    )

    cover_photo_fixture = {
        "title": "可追溯的封面圖片",
        "title_lines": ["可追溯的", "封面圖片"],
        "subtitle": "替代封面 Layout 必須保留同一張語意照片。",
        "speaker": "測試提案方",
        "org": "測試受眾",
        "hero_image_src": "assets/cover-hero.png",
        "hero_image_alt": "測試封面主題照片",
    }
    cover_semantic_photo_layouts = [
        "cover-photo-frame-reverse",
        "cover-photo-overlay-block",
    ]
    for layout_id in cover_semantic_photo_layouts:
        rendered_cover = production.render_production_layout(
            layout_lookup[layout_id], cover_photo_fixture
        )
        if not rendered_cover or 'data-semantic-image="true"' not in rendered_cover:
            raise AssertionError(f"{layout_id} dropped the semantic cover photo")
        if 'src="assets/cover-hero.png"' not in rendered_cover:
            raise AssertionError(f"{layout_id} did not bind hero_image_src")
        if 'alt="測試封面主題照片"' not in rendered_cover:
            raise AssertionError(f"{layout_id} did not bind hero_image_alt")
        if "可追溯的<br>封面圖片" not in rendered_cover:
            raise AssertionError(f"{layout_id} did not preserve the authored title break")

    panel_row_fixture = {
        "title": "四段閱讀路徑",
        "intro": "每列保留編號、標題與說明。",
        "items": [
            ("01", "第一段", "第一段說明"),
            ("02", "第二段", "第二段說明"),
            ("03", "第三段", "第三段說明"),
            ("04", "第四段", "第四段說明"),
        ],
    }
    rendered_panel_rows = production.render_production_layout(
        layout_lookup["toc-4-panel-rows"], panel_row_fixture
    )
    if 'data-edit-position="flow"' in rendered_panel_rows:
        raise AssertionError("toc-4-panel-rows must keep title and description in separate absolute columns")

    render_results = []
    route_candidate_counts: dict[str, int] = {}
    rendered_candidate_count = 0
    for page_index, semantic_page in enumerate(semantic_pages):
        intent = semantic_page["intent"]
        candidates = list(HTML_DESIGN_METHOD["content_routing"][intent]["candidates"])
        if intent == "navigation":
            item_count = len(semantic_page["payload"]["items"])
            candidates = [
                layout_id
                for layout_id in candidates
                if (match := re.match(r"^toc-(\d+)(?:-|$)", layout_id))
                and int(match.group(1)) == item_count
            ]
        route_candidate_counts[intent] = len(candidates)
        hashes = set()
        for scaffold_id in candidates:
            forced = list(FORCED_LAYOUTS)
            forced[page_index] = scaffold_id
            for neighbor_index in (page_index - 1, page_index + 1):
                if not (0 <= neighbor_index < len(forced)):
                    continue
                if forced[neighbor_index] != scaffold_id:
                    continue
                neighbor_intent = semantic_pages[neighbor_index]["intent"]
                alternatives = [
                    layout_id
                    for layout_id in HTML_DESIGN_METHOD["content_routing"][neighbor_intent]["candidates"]
                    if layout_id != scaffold_id
                ]
                if alternatives:
                    forced[neighbor_index] = alternatives[0]
            layout_plan = resolve_layout_plan(
                story,
                random.Random(20260809),
                forced,
                HTML_DESIGN_METHOD,
                content_plan=content_plan,
            )
            decision = layout_plan[page_index]
            if decision["intent"] != intent:
                raise AssertionError("forced Layout changed the content-plan intent")
            # The new-deck adapter receives an empty story on purpose: after
            # content planning it must depend only on the page object.
            page_content, feedback = compose_page_content({}, semantic_page, decision)
            rendered = production.render_production_layout(layout_lookup[scaffold_id], page_content)
            if not rendered:
                raise AssertionError(f"{scaffold_id} returned no page composition")
            if feedback["capacity_role"] != "renderer-feedback-not-layout-eligibility":
                raise AssertionError("composition feedback became a Layout eligibility gate")
            hashes.add(feedback["content_sha256"])
            rendered_candidate_count += 1
            if intent == "navigation":
                rendered_items = rendered.count('data-edit-composite="toc-chapter-')
                if rendered_items != 6 or len(page_content["items"]) != 6:
                    raise AssertionError(
                        f"{scaffold_id} did not preserve all six navigation items: "
                        f"{rendered_items}"
                    )
                render_results.append({
                    "layout_scaffold_id": scaffold_id,
                    "content_page_id": feedback["content_page_id"],
                    "content_sha256": feedback["content_sha256"],
                    "rendered_items": rendered_items,
                    "content_identity_preserved": feedback["content_identity_preserved"],
                    "content_mutated": feedback["content_mutated"],
                })
        if len(hashes) != 1:
            raise AssertionError(
                f"the same {intent} semantic page changed identity across Layout scaffolds"
            )

    automatic_plan = resolve_layout_plan(
        story,
        random.Random(20260809),
        catalog=HTML_DESIGN_METHOD,
        content_plan=content_plan,
    )
    automatic_navigation = next(row for row in automatic_plan if row["intent"] == "navigation")
    navigation_count = len(navigation_page["payload"]["items"])
    expected_candidates = [
        layout_id
        for layout_id in HTML_DESIGN_METHOD["content_routing"]["navigation"]["candidates"]
        if (match := re.match(r"^toc-(\d+)(?:-|$)", layout_id))
        and int(match.group(1)) == navigation_count
    ]
    if automatic_navigation["selection_candidates"] != expected_candidates:
        raise AssertionError("navigation candidates were filtered by item count before selection")
    if "selection_filter" in automatic_navigation:
        raise AssertionError("legacy capacity selection_filter is still present")

    fixture_after = json.dumps(
        {"items": production.TOC_ITEMS, "context": production.TOC_CONTEXT},
        ensure_ascii=False,
        sort_keys=True,
    )
    if fixture_after != fixture_before:
        raise AssertionError("new-deck composition mutated the Gallery fixture store")

    result = {
        "pass": True,
        "semantic_page_has_layout_identity": False,
        "navigation_candidate_count": len(expected_candidates),
        "rendered_route_candidates": rendered_candidate_count,
        "route_candidate_counts": route_candidate_counts,
        "preselection_capacity_filter": "navigation-exact-capacity-only",
        "composition_reads_story_after_planning": False,
        "gallery_fixture_mutated": False,
        "gallery_generic_fallback": generic_fallback_id,
        "cover_semantic_photo_layouts": cover_semantic_photo_layouts,
        "render_results": render_results,
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
