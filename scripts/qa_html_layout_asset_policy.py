#!/usr/bin/env python3
"""Verify Layout Core media requirements gate HTML selection correctly."""

from __future__ import annotations

import json
import random
from pathlib import Path

import html_production_renderer as production
import yaml
from generate_renderer_adapters import validate_layout_core
from html_design_method import load_html_design_method, resolve_content_plan, resolve_layout_plan
from html_layout_catalog import eligible_html_layouts, load_html_layout_catalog
from render_randomized_html_demo import compose_page_content


ROOT = Path(__file__).resolve().parents[1]


def _expect_value_error(callback, expected_text: str) -> str:
    try:
        callback()
    except ValueError as exc:
        message = str(exc)
        if expected_text not in message:
            raise AssertionError(
                f"Expected error containing {expected_text!r}, got {message!r}"
            ) from exc
        return message
    raise AssertionError(f"Expected ValueError containing {expected_text!r}")


def main() -> int:
    catalog = load_html_layout_catalog()
    method = load_html_design_method()
    no_image = set(catalog["layout_ids_by_media_requirement"]["no-image"])
    with_image = set(catalog["layout_ids_by_media_requirement"]["with-image"])
    pattern_only = set(eligible_html_layouts(catalog, "pattern-only"))
    image_planned = set(eligible_html_layouts(catalog, "image-planned"))

    if len(no_image) != 64 or len(with_image) != 17:
        raise AssertionError("Unexpected Layout Core media requirement counts")
    if catalog["media_requirement_by_layout_id"]["icon-grid-6"] != "no-image":
        raise AssertionError("icon-grid-6 must remain semantic-native no-image")
    if pattern_only != no_image:
        raise AssertionError("pattern-only must expose exactly the no-image Layouts")
    if image_planned != no_image | with_image:
        raise AssertionError("image-planned must expose all core Layouts")

    icon_path = ROOT / "prompt_system" / "layouts" / "icon-grid-6.yaml"
    icon_core = yaml.safe_load(icon_path.read_text(encoding="utf-8"))
    validate_layout_core(icon_path, icon_core)
    invalid_core = dict(icon_core)
    invalid_core["media_requirement"] = "semantic-icon"
    invalid_core_message = _expect_value_error(
        lambda: validate_layout_core(icon_path, invalid_core),
        "media_requirement",
    )

    extended = [
        layout_id
        for candidates in method["image_candidate_extensions"].values()
        for layout_id in candidates
    ]
    if len(extended) != len(set(extended)) or set(extended) != with_image:
        raise AssertionError("image candidate extensions must cover every with-image Layout once")

    story = {"title": "Asset policy QA", "content_plan": [{"intent": "cover"}]}
    content_plan = resolve_content_plan(story, method)
    default_plan = resolve_layout_plan(
        story,
        random.Random(20260809),
        catalog=method,
        content_plan=content_plan,
        layout_catalog=catalog,
    )
    if any(row["media_requirement"] != "no-image" for row in default_plan):
        raise AssertionError("Default HTML selection escaped the pattern-only policy")

    blocked_message = _expect_value_error(
        lambda: resolve_layout_plan(
            story,
            random.Random(20260809),
            ["hero-fullbleed"],
            method,
            content_plan=content_plan,
            asset_policy="pattern-only",
            layout_catalog=catalog,
        ),
        "asset_policy=pattern-only",
    )
    image_plan = resolve_layout_plan(
        story,
        random.Random(20260809),
        ["hero-fullbleed"],
        method,
        content_plan=content_plan,
        asset_policy="image-planned",
        layout_catalog=catalog,
    )
    if image_plan[0]["media_requirement"] != "with-image":
        raise AssertionError("image-planned did not allow an image-required Layout")

    automatic_image_plan = resolve_layout_plan(
        story,
        random.Random(20260809),
        catalog=method,
        content_plan=content_plan,
        asset_policy="image-planned",
        layout_catalog=catalog,
    )
    if not with_image.intersection(automatic_image_plan[0]["selection_candidates"]):
        raise AssertionError("image-planned automatic routing has no image-required candidates")

    matrix = json.loads(
        (ROOT / "artifacts" / "renderer-matrix" / "matrix.json").read_text(encoding="utf-8")
    )
    layout_lookup = {row["id"]: row for row in matrix["layouts"]}
    payloads = {
        "cover": {
            "title": "Image-planned cover",
            "subtitle": "Real image will be attached before delivery",
            "speaker": "QA",
            "org": "SLIDE FIRM",
        },
        "navigation": {
            "title": "Contents",
            "intro": "Image-led navigation",
            "footer": "QA",
            "items": [("01", "Context", "Why now"), ("02", "Action", "What next")],
        },
        "distribution": {
            "matrix": [
                ("North", "Priority one"),
                ("Central", "Priority two"),
                ("South", "Priority three"),
            ],
        },
        "modules": {
            "title": "Team",
            "people": [
                ("Person A", "Strategy", "Decision framing"),
                ("Person B", "Design", "Visual hierarchy"),
                ("Person C", "Engineering", "Delivery system"),
                ("Person D", "Research", "Evidence"),
                ("Person E", "QA", "Verification"),
                ("Person F", "Operations", "Handoff"),
            ],
        },
        "statement": {"quote": "One clear statement", "attribution": "QA Author"},
        "closing": {"headline": "Next step", "support": "Attach the approved image assets"},
    }
    rendered_image_layouts: list[str] = []
    for intent, layout_ids in method["image_candidate_extensions"].items():
        for layout_id in layout_ids:
            semantic_page = {
                "page_id": f"{intent}-qa",
                "intent": intent,
                "content_sha256": "qa",
                "payload": payloads[intent],
            }
            decision = {
                "layout_id": layout_id,
                "composition_feedback": {},
            }
            page_content, _ = compose_page_content({}, semantic_page, decision)
            rendered = production.render_production_layout(layout_lookup[layout_id], page_content)
            if not rendered:
                raise AssertionError(f"image-planned Layout did not render: {layout_id}")
            rendered_image_layouts.append(layout_id)
    if set(rendered_image_layouts) != with_image:
        raise AssertionError("not every with-image Layout has a new-deck composition adapter")

    invalid_message = _expect_value_error(
        lambda: eligible_html_layouts(catalog, "unknown-policy"),
        "Unknown HTML asset policy",
    )
    print(json.dumps({
        "pass": True,
        "core": len(image_planned),
        "no_image": len(no_image),
        "with_image": len(with_image),
        "pattern_only_eligible": len(pattern_only),
        "image_planned_eligible": len(image_planned),
        "icon_grid_6": catalog["media_requirement_by_layout_id"]["icon-grid-6"],
        "pattern_only_blocked_with_image": "hero-fullbleed" in blocked_message,
        "image_planned_allowed_with_image": image_plan[0]["layout_id"],
        "image_layout_composition_adapters": len(rendered_image_layouts),
        "invalid_policy_rejected": "unknown-policy" in invalid_message,
        "invalid_core_requirement_rejected": "media_requirement" in invalid_core_message,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
