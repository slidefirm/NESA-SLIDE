#!/usr/bin/env python3
"""Load and apply the renderer-scoped HTML design method catalog."""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Any

import yaml

from html_assembly import load_html_assembly_catalog
from html_layout_catalog import ASSET_POLICIES, eligible_html_layouts, load_html_layout_catalog


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "prompt_system" / "renderers" / "html" / "design-method.yaml"


def _expand_candidate_selectors(
    routing: dict[str, Any],
    layout_catalog: dict[str, Any],
) -> list[str]:
    """Expand catalog-backed candidate pools before design-method validation."""

    issues: list[str] = []
    for intent, rule in routing.items():
        selector = rule.get("candidate_selector")
        if not selector:
            continue
        if not isinstance(selector, dict) or selector.get("type") != "catalog-prefix":
            issues.append(f"{intent}: unsupported candidate_selector")
            continue
        pool_name = selector.get("pool", "allowed_layout_ids")
        pool = layout_catalog.get(pool_name)
        prefix = selector.get("prefix")
        if not isinstance(pool, list) or not isinstance(prefix, str) or not prefix:
            issues.append(f"{intent}: candidate_selector requires a catalog pool and prefix")
            continue
        selected = [layout_id for layout_id in pool if str(layout_id).startswith(prefix)]
        if not selected:
            issues.append(f"{intent}: candidate_selector matched no layouts")
            continue
        rule["candidates"] = list(dict.fromkeys(selected))
        rule["candidate_pool"] = {
            "source": "html-layout-catalog",
            "pool": pool_name,
            "selector": {"type": "catalog-prefix", "prefix": prefix},
        }
    return issues


def load_html_design_method(path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    issues: list[str] = []
    routing = data.get("content_routing") or {}
    default_route = data.get("default_deck_route") or []
    theme_profiles = data.get("theme_selection_profiles") or {}
    layout_catalog = load_html_layout_catalog()
    assembly = load_html_assembly_catalog()
    issues.extend(_expand_candidate_selectors(routing, layout_catalog))
    visible = set(layout_catalog["visible_layout_ids"])
    pattern_only = set(layout_catalog["layout_ids_by_asset_policy"]["pattern-only"])
    with_image = set(layout_catalog["layout_ids_by_media_requirement"]["with-image"])

    diversity_policy = data.get("layout_diversity_policy") or {}
    if diversity_policy.get("default_selection") not in {"preferred", "dynamic", "diverse"}:
        issues.append(
            "layout_diversity_policy.default_selection must be preferred, dynamic, or diverse"
        )
    if diversity_policy.get("no_consecutive_repeat") is not True:
        issues.append("layout_diversity_policy.no_consecutive_repeat must be true")
    if diversity_policy.get("reuse_policy") != "least-used-candidate":
        issues.append(
            "layout_diversity_policy.reuse_policy must be least-used-candidate"
        )

    preset_policy = data.get("preset_rebuild_policy") or {}
    source_isolation = preset_policy.get("source_isolation") or {}
    if source_isolation.get("runtime_import") != "forbidden":
        issues.append("preset_rebuild_policy must forbid old-case runtime import")
    required_forbidden_fields = {
        "source_style_case", "example_story", "example_layouts", "content", "layouts", "css",
    }
    if not required_forbidden_fields.issubset(set(source_isolation.get("forbidden_fields") or [])):
        issues.append("preset_rebuild_policy source isolation is incomplete")

    css_gate = data.get("css_ownership_gate") or {}
    if css_gate.get("geometry_owner") != "renderer-base":
        issues.append("css_ownership_gate.geometry_owner must be renderer-base")
    if set(css_gate.get("appearance_owners") or []) != {"theme-appearance", "preset-appearance"}:
        issues.append("css_ownership_gate appearance owners are invalid")
    if css_gate.get("validation_mode") != "reject-not-repair":
        issues.append("css_ownership_gate must reject conflicts instead of repairing them")
    browser_invariant = css_gate.get("browser_invariant") or {}
    if browser_invariant.get("tolerance_px") != 0.5 or browser_invariant.get("failure") != "blocking":
        issues.append("css_ownership_gate browser invariant must block geometry drift over 0.5px")

    fit_feedback = data.get("composition_fit_feedback") or {}
    if fit_feedback.get("run_after") != "layout-scaffold-selection":
        issues.append("composition fit feedback must run after Layout scaffold selection")
    if fit_feedback.get("owner") != "per-slide-composition":
        issues.append("composition fit feedback must be owned per slide")
    if fit_feedback.get("layout_count_metadata") != "compatibility-hint-only":
        issues.append("Layout item-count metadata must remain a compatibility hint")

    if not default_route:
        issues.append("default_deck_route must not be empty")
    for intent in default_route:
        if intent not in routing:
            issues.append(f"default route references unknown intent: {intent}")

    for intent, rule in routing.items():
        candidates = rule.get("candidates") or []
        if not candidates:
            issues.append(f"{intent}: candidates must not be empty")
        unknown = sorted(set(candidates) - pattern_only)
        if unknown:
            issues.append(f"{intent}: base candidates are not pattern-only eligible: {unknown}")
        for key in ("signature_composition", "ordinary_grid_loss", "visual_intensity"):
            if not rule.get(key):
                issues.append(f"{intent}: missing {key}")

    variant_profiles = data.get("layout_variant_profiles") or {}
    for layout_id, profile in variant_profiles.items():
        if layout_id not in visible:
            issues.append(f"layout variant profile references unavailable HTML layout: {layout_id}")
        for key in ("composition_variants", "header_modes", "surface_modes"):
            values = profile.get(key) or []
            if not values:
                issues.append(f"{layout_id}: missing non-empty {key}")
            elif len(values) != len(set(values)):
                issues.append(f"{layout_id}: duplicate values in {key}")

    image_extensions = data.get("image_candidate_extensions") or {}
    if not isinstance(image_extensions, dict):
        issues.append("image_candidate_extensions must be an object")
        image_extensions = {}
    extended_layouts: list[str] = []
    for intent, candidates in image_extensions.items():
        if intent not in routing:
            issues.append(f"image candidate extension references unknown intent: {intent}")
            continue
        if not isinstance(candidates, list) or not candidates:
            issues.append(f"{intent}: image candidate extension must be a non-empty list")
            continue
        if len(candidates) != len(set(candidates)):
            issues.append(f"{intent}: image candidate extension contains duplicates")
        unknown = sorted(set(candidates) - visible)
        if unknown:
            issues.append(f"{intent}: image candidates are not core Layouts: {unknown}")
        wrong_mode = sorted(set(candidates) - with_image)
        if wrong_mode:
            issues.append(f"{intent}: image candidates must require images: {wrong_mode}")
        extended_layouts.extend(candidates)
    duplicate_extensions = sorted(
        layout_id for layout_id in set(extended_layouts) if extended_layouts.count(layout_id) > 1
    )
    if duplicate_extensions:
        issues.append(f"image candidates appear under multiple intents: {duplicate_extensions}")
    if set(extended_layouts) != with_image:
        missing = sorted(with_image - set(extended_layouts))
        extra = sorted(set(extended_layouts) - with_image)
        issues.append(f"image candidate coverage mismatch; missing={missing}, extra={extra}")

    expected_themes = set(assembly["recipes"])
    if set(theme_profiles) != expected_themes:
        missing = sorted(expected_themes - set(theme_profiles))
        extra = sorted(set(theme_profiles) - expected_themes)
        issues.append(f"theme selection profiles mismatch; missing={missing}, extra={extra}")
    for theme_id, profile in theme_profiles.items():
        for key in ("best_for", "avoid_for", "signature_compositions"):
            if not profile.get(key):
                issues.append(f"{theme_id}: missing {key}")

    questions = (data.get("deck_review") or {}).get("questions") or []
    expected_question_ids = {
        "repeated-skeleton", "page-rhythm", "signature-fit",
        "type-capacity-fit", "unintended-collision", "layout-only-edit-hit",
        "nested-group-preservation", "body-field-balance", "palette-jarring",
    }
    if len(questions) != len(expected_question_ids):
        issues.append("deck_review must contain exactly nine questions")
    if {row.get("id") for row in questions} != expected_question_ids:
        issues.append("deck_review question ids do not match the formal nine-question review")

    if issues:
        raise ValueError("HTML design method invalid: " + "; ".join(issues))

    data["counts"] = {
        "content_intents": len(routing),
        "theme_profiles": len(theme_profiles),
        "layout_variant_profiles": len(variant_profiles),
        "review_questions": len(questions),
    }
    return data


_CONTENT_SPECS: dict[str, dict[str, Any]] = {
    "cover": {
        "content_key": "cover",
        "source_fields": ["title", "subtitle", "speaker", "org"],
        "content_relation": "single-proposition-hero",
    },
    "navigation": {
        "content_key": "toc",
        "source_fields": ["toc"],
        "content_relation": "reading-path",
    },
    "prioritization": {
        "content_key": "prioritization",
        "source_fields": ["priorities", "recommendations", "matrix"],
        "content_relation": "ranked-decision",
    },
    "comparison": {
        "content_key": "comparison",
        "source_fields": ["before", "after", "matrix"],
        "content_relation": "state-change",
    },
    "distribution": {
        "content_key": "distribution",
        "source_fields": ["matrix"],
        "content_relation": "position-and-cluster",
    },
    "evidence": {
        "content_key": "evidence",
        "source_fields": ["metrics", "chart"],
        "content_relation": "measurable-proof",
    },
    "sequence": {
        "content_key": "sequence",
        "source_fields": ["process", "timeline"],
        "content_relation": "ordered-path",
    },
    "statement": {
        "content_key": "statement",
        "source_fields": ["quote", "attribution"],
        "content_relation": "single-conclusion",
    },
    "closing": {
        "content_key": "closing",
        "source_fields": ["closing"],
        "content_relation": "next-action",
    },
}


def _has_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def _content_item_count(story: dict[str, Any], fields: list[str]) -> int | None:
    for field in fields:
        value = story.get(field)
        if isinstance(value, (list, dict)):
            return len(value)
    return None


def _normalise_content_plan(
    entries: list[Any],
    method: dict[str, Any],
    source: str,
    story: dict[str, Any],
) -> list[dict[str, Any]]:
    routing = method["content_routing"]
    plan: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if isinstance(entry, str):
            intent = entry
            payload: dict[str, Any] = {}
        elif isinstance(entry, dict):
            intent = entry.get("intent")
            payload = entry
        else:
            raise ValueError("content plan entries must be intent strings or objects")
        if intent not in routing:
            raise ValueError(f"Unknown content intent in content plan: {intent}")
        spec = _CONTENT_SPECS.get(intent, {})
        source_fields = list(payload.get("source_fields") or spec.get("source_fields") or [])
        item = {
            "page_index": index + 1,
            "page_id": payload.get("page_id") or f"{intent}-{index + 1:02d}",
            "intent": intent,
            "content_key": payload.get("content_key") or spec.get("content_key", intent),
            "source_fields": source_fields,
            "content_relation": payload.get("content_relation") or spec.get("content_relation", intent),
            "content_item_count": payload.get("content_item_count")
            if payload.get("content_item_count") is not None
            else _content_item_count(story, source_fields),
            "plan_source": source,
        }
        if payload.get("preferred_layout"):
            item["preferred_layout"] = payload["preferred_layout"]
        plan.append(item)
    if not plan:
        raise ValueError("Content plan must contain at least one page")
    return plan


def resolve_content_plan(
    story: dict[str, Any],
    catalog: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Decide each page's semantic content before any Layout is sampled."""

    method = catalog or load_html_design_method()
    explicit_plan = story.get("content_plan")
    if isinstance(explicit_plan, list) and explicit_plan:
        return _normalise_content_plan(explicit_plan, method, "explicit-content-plan", story)

    slide_plan = story.get("slide_plan")
    if isinstance(slide_plan, list) and slide_plan:
        return _normalise_content_plan(slide_plan, method, "explicit-slide-plan", story)

    inferred: list[dict[str, Any]] = []

    def add(
        intent: str,
        required_fields: list[str] | None = None,
        source_fields: list[str] | None = None,
    ) -> None:
        spec = _CONTENT_SPECS[intent]
        presence_fields = required_fields or spec["source_fields"]
        if not any(_has_content(story.get(field)) for field in presence_fields):
            return
        fields = source_fields or [
            field for field in spec["source_fields"]
            if _has_content(story.get(field))
        ]
        inferred.append({
            "intent": intent,
            "content_key": spec["content_key"],
            "source_fields": fields,
            "content_relation": spec["content_relation"],
        })

    add("cover", ["title"])
    add("navigation", ["toc"])
    add("prioritization", ["priorities", "recommendations"])
    if _has_content(story.get("before")) and _has_content(story.get("after")):
        add(
            "comparison",
            ["before", "after"],
            ["title", "before", "after", "toc", "priorities", "closing"],
        )
    elif _has_content(story.get("matrix")):
        add("distribution", ["matrix"], ["matrix"])
    add("evidence", ["metrics", "chart"])
    add("sequence", ["process", "timeline"])
    add("statement", ["quote"])
    add("closing", ["closing"])
    return _normalise_content_plan(inferred, method, "inferred-content-plan", story)


def _composition_feedback(entry: dict[str, Any]) -> dict[str, Any]:
    """Describe fit work without turning content count into a Layout veto."""

    return {
        "stage": "post-scaffold-selection",
        "owner": "per-slide-composition",
        "content_item_count": entry.get("content_item_count"),
        "fit_policy": "compose-page-content-then-validate",
        "capacity_role": "renderer-feedback-not-layout-eligibility",
        "remediation_order": [
            "reflow-within-scaffold",
            "change-composition-recipe",
            "capacity-compatible-layout-with-requested-resolved-provenance",
            "split-page",
            "explicit-user-authorized-integration-with-mutation-ledger",
        ],
    }


def _apply_layout_variants(
    decisions: list[dict[str, Any]],
    rng: random.Random,
    method: dict[str, Any],
) -> list[dict[str, Any]]:
    profiles = method.get("layout_variant_profiles") or {}
    for decision in decisions:
        layout_id = decision["layout_id"]
        profile = profiles.get(layout_id)
        if profile:
            decision["composition_variant"] = rng.choice(profile["composition_variants"])
            decision["header_mode"] = rng.choice(profile["header_modes"])
            decision["surface_mode"] = rng.choice(profile["surface_modes"])
            decision["variant_source"] = "layout-variant-profile"
        else:
            decision["composition_variant"] = f"{layout_id}-native"
            decision["header_mode"] = "layout-defined"
            decision["surface_mode"] = "layout-defined"
            decision["variant_source"] = "layout-native-fallback"
    return decisions


def _validate_no_consecutive_layouts(
    layout_ids: list[str],
    *,
    source: str,
) -> None:
    for index in range(1, len(layout_ids)):
        if layout_ids[index] == layout_ids[index - 1]:
            raise ValueError(
                "Layout diversity requires no consecutive duplicate Layouts: "
                f"source={source}, slide={index + 1}, layout={layout_ids[index]}"
            )


def _select_layout_candidate(
    candidates: list[str],
    rng: random.Random,
    *,
    previous_layout_id: str | None,
    usage_counts: dict[str, int],
    intent: str,
    layout_selection: str,
) -> tuple[str, str]:
    unique_candidates = list(dict.fromkeys(candidates))
    if not unique_candidates:
        raise ValueError(f"No Layout candidates remain for intent={intent}")

    if previous_layout_id in unique_candidates:
        alternatives = [
            layout_id for layout_id in unique_candidates if layout_id != previous_layout_id
        ]
        if not alternatives:
            raise ValueError(
                "Layout diversity cannot avoid a consecutive duplicate: "
                f"intent={intent}, layout={previous_layout_id}"
            )
        unique_candidates = alternatives

    if layout_selection == "diverse":
        least_used = min(usage_counts.get(layout_id, 0) for layout_id in unique_candidates)
        unique_candidates = [
            layout_id
            for layout_id in unique_candidates
            if usage_counts.get(layout_id, 0) == least_used
        ]
        return rng.choice(unique_candidates), "semantic-candidates-seeded-diverse"

    return rng.choice(unique_candidates), "semantic-candidates-seeded-tiebreaker"


def resolve_layout_plan(
    story: dict[str, Any],
    rng: random.Random,
    forced_layouts: list[str] | None = None,
    catalog: dict[str, Any] | None = None,
    content_plan: list[dict[str, Any]] | None = None,
    asset_policy: str | None = None,
    layout_catalog: dict[str, Any] | None = None,
    layout_selection: str = "diverse",
) -> list[dict[str, Any]]:
    method = catalog or load_html_design_method()
    layout_policy = layout_catalog or load_html_layout_catalog()
    resolved_asset_policy = asset_policy or layout_policy["default_asset_policy"]
    if resolved_asset_policy not in ASSET_POLICIES:
        raise ValueError(f"Unknown HTML asset policy: {resolved_asset_policy}")
    if layout_selection not in {"preferred", "dynamic", "diverse"}:
        raise ValueError(f"Unknown HTML layout selection mode: {layout_selection}")
    dynamic_selection = layout_selection in {"dynamic", "diverse"}
    eligible_layout_ids = set(eligible_html_layouts(layout_policy, resolved_asset_policy))
    visible_layout_ids = set(layout_policy["visible_layout_ids"])
    routing = method["content_routing"]
    default_route = list(method["default_deck_route"])
    content_plan = content_plan or resolve_content_plan(story, method)

    if forced_layouts:
        unknown = sorted(set(forced_layouts) - visible_layout_ids)
        if unknown:
            raise ValueError(f"Unknown forced HTML Layouts: {unknown}")
        blocked = sorted(set(forced_layouts) - eligible_layout_ids)
        if blocked:
            requirements = {
                layout_id: layout_policy["media_requirement_by_layout_id"][layout_id]
                for layout_id in blocked
            }
            raise ValueError(
                f"Forced Layouts are not eligible for asset_policy={resolved_asset_policy}: "
                f"{requirements}"
            )
        _validate_no_consecutive_layouts(forced_layouts, source="forced-layouts")
        decisions: list[dict[str, Any]] = []
        for index, layout_id in enumerate(forced_layouts):
            plan_entry = content_plan[min(index, len(content_plan) - 1)]
            intent = plan_entry["intent"] if plan_entry else default_route[min(index, len(default_route) - 1)]
            rule = routing[intent]
            effective_candidates = list(rule["candidates"])
            if resolved_asset_policy == "image-planned":
                effective_candidates.extend((method.get("image_candidate_extensions") or {}).get(intent, []))
            effective_candidates = list(dict.fromkeys(effective_candidates))
            decision = {
                "intent": intent,
                "layout_id": layout_id,
                "layout_role": "scaffold",
                "signature_composition": rule["signature_composition"],
                "ordinary_grid_loss": rule["ordinary_grid_loss"],
                "visual_intensity": rule["visual_intensity"],
                "source": "forced-layout",
                "route_match": layout_id in effective_candidates,
                "selection_candidates": [layout_id],
                "selection_basis": "forced-layout",
                "asset_policy": resolved_asset_policy,
                "media_requirement": layout_policy["media_requirement_by_layout_id"][layout_id],
            }
            if plan_entry:
                decision.update({
                    "content_plan_index": plan_entry["page_index"],
                    "content_page_id": plan_entry["page_id"],
                    "content_key": plan_entry["content_key"],
                    "content_source_fields": plan_entry["source_fields"],
                    "content_relation": plan_entry["content_relation"],
                    "content_item_count": plan_entry.get("content_item_count"),
                    "composition_feedback": _composition_feedback(plan_entry),
                })
            decisions.append(decision)
        return _apply_layout_variants(decisions, rng, method)

    decisions = []
    usage_counts: dict[str, int] = {}
    previous_layout_id: str | None = None
    for entry in content_plan:
        intent = entry["intent"]
        preferred = entry.get("preferred_layout")
        if intent not in routing:
            raise ValueError(f"Unknown content intent in content plan: {intent}")
        rule = routing[intent]
        effective_candidates = list(rule["candidates"])
        if resolved_asset_policy == "image-planned":
            effective_candidates.extend((method.get("image_candidate_extensions") or {}).get(intent, []))
        effective_candidates = [
            layout_id
            for layout_id in dict.fromkeys(effective_candidates)
            if layout_id in eligible_layout_ids
        ]
        if not effective_candidates:
            raise ValueError(
                f"No Layout candidates remain for intent={intent}, asset_policy={resolved_asset_policy}"
            )
        if (
            intent == "navigation"
            and dynamic_selection
            and entry.get("content_item_count") is not None
        ):
            # TOC image layouts are authored for four rows. Keep the
            # image-capable variant when it actually fits, but do not let a
            # six- or eight-item reading path overflow that scaffold merely
            # because image-planned mode appended it to the candidate pool.
            item_count = int(entry["content_item_count"])
            sized_candidates = []
            for candidate in effective_candidates:
                match = re.match(r"^toc-(\d+)(?:-|$)", candidate)
                if match and int(match.group(1)) == item_count:
                    sized_candidates.append(candidate)
            if not sized_candidates:
                sized_candidates = [
                    candidate
                    for candidate in effective_candidates
                    if (match := re.match(r"^toc-(\d+)(?:-|$)", candidate))
                    and int(match.group(1)) >= item_count
                ]
            if sized_candidates:
                effective_candidates = sized_candidates
        if (
            dynamic_selection
            and resolved_asset_policy == "image-planned"
            and intent in {"cover", "navigation", "closing"}
        ):
            # These anchor pages must visibly use the image-capable Layout
            # family in an image-planned deck. The choice within that family
            # stays seed-driven, so the deck is not reduced to one template.
            image_anchor_candidates = [
                layout_id
                for layout_id in (method.get("image_candidate_extensions") or {}).get(intent, [])
                if layout_id in effective_candidates
                and layout_policy["media_requirement_by_layout_id"].get(layout_id) == "with-image"
                and not (
                    intent == "cover"
                    and layout_id in {"hero-fullbleed", "hero-fullbleed-brand-footer"}
                )
            ]
            if image_anchor_candidates:
                effective_candidates = image_anchor_candidates
        if intent == "modules" and dynamic_selection:
            # People/team image Layouts need authored people data. Do not
            # turn a generic priority list into fake portrait cards.
            source_fields = set(entry.get("source_fields") or [])
            effective_candidates = [
                layout_id
                for layout_id in effective_candidates
                if layout_id not in {"executive-bio", "people-3", "team-grid"}
                or bool(source_fields & {"people", "members"})
            ]
            if not effective_candidates:
                raise ValueError("Dynamic modules route has no content-compatible Layout candidates")
        if intent == "distribution" and dynamic_selection:
            # The catalog also exposes swot-quadrant as a visual option, but
            # the new-deck content adapter intentionally supports the matrix,
            # heat-map, and map families only. Do not sample a scaffold that
            # the renderer cannot bind to the page payload.
            composable_distribution = {
                "matrix-4quadrant",
                "heat-map",
                "map-region",
                "map-spotlight",
            }
            effective_candidates = [
                layout_id for layout_id in effective_candidates
                if layout_id in composable_distribution
            ]
            if not effective_candidates:
                raise ValueError("Dynamic distribution route has no composable Layout candidates")
        if intent == "modules" and entry.get("content_item_count") is not None:
            item_count = int(entry["content_item_count"])
            effective_candidates = [
                layout_id
                for layout_id in effective_candidates
                if not layout_id.startswith("cards-1-plus-")
                or int(re.search(r"(\d+)$", layout_id).group(1)) == item_count
            ]
            if not effective_candidates:
                raise ValueError(
                    f"No module Layout matches content_item_count={item_count}"
                )
        if preferred and layout_selection == "preferred" and preferred not in effective_candidates:
            raise ValueError(f"preferred_layout {preferred} does not match intent {intent}")
        if preferred and layout_selection == "preferred":
            if preferred == previous_layout_id:
                raise ValueError(
                    "Layout diversity requires no consecutive duplicate Layouts: "
                    f"source=preferred-layout, layout={preferred}"
                )
            selection_candidates = [preferred]
            selection_basis = "preferred-layout"
            layout_id = preferred
        else:
            selection_candidates = list(effective_candidates)
            layout_id, selection_basis = _select_layout_candidate(
                selection_candidates,
                rng,
                previous_layout_id=previous_layout_id,
                usage_counts=usage_counts,
                intent=intent,
                layout_selection=layout_selection,
            )
        decision = {
            "intent": intent,
            "layout_id": layout_id,
            "layout_role": "scaffold",
            "signature_composition": rule["signature_composition"],
            "ordinary_grid_loss": rule["ordinary_grid_loss"],
            "visual_intensity": rule["visual_intensity"],
            "source": (
                "content-plan-dynamic"
                if layout_selection == "dynamic"
                else entry.get("plan_source", "content-plan")
            ),
            "route_match": True,
            "selection_candidates": selection_candidates,
            "selection_basis": selection_basis,
            "asset_policy": resolved_asset_policy,
            "media_requirement": layout_policy["media_requirement_by_layout_id"][layout_id],
            "content_plan_index": entry["page_index"],
            "content_page_id": entry["page_id"],
            "content_key": entry["content_key"],
            "content_source_fields": entry["source_fields"],
            "content_relation": entry["content_relation"],
            "content_item_count": entry.get("content_item_count"),
            "composition_feedback": _composition_feedback(entry),
        }
        decisions.append(decision)
        usage_counts[layout_id] = usage_counts.get(layout_id, 0) + 1
        previous_layout_id = layout_id
    return _apply_layout_variants(decisions, rng, method)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()
    catalog = load_html_design_method(args.catalog.resolve())
    print(json.dumps({"id": catalog["id"], **catalog["counts"], "pass": True}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
