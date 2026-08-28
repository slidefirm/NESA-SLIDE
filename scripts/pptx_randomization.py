"""Seeded PPTX Layout/Variant selection.

This module is the planning boundary for randomized PPTX decks.  It never
mutates a canonical Layout: a seed only chooses among compatible Layouts and
then asks the PPTX Variant runtime to materialize the selected projection.
The resulting selection manifest is consumed by the JavaScript builder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
from pathlib import Path
from typing import Any, Iterable

import yaml

from pptx_background_runtime import resolve_background_set
from pptx_variant_runtime import project_placeholders, resolve_variant


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "artifacts" / "renderer-matrix" / "matrix.json"
DEFAULT_CONTENT = ROOT / "release" / "fixtures" / "pptx-randomization-content.json"
BACKGROUND_SET_DIR = ROOT / "prompt_system" / "pptx_background_sets"
RETIRED_LAYOUT_IDS = {"toc-2", "toc-2-image-left", "toc-2-panel-rows", "toc-2-vertical"}
U32_MASK = 0xFFFFFFFF
LCG_MULTIPLIER = 1664525
LCG_INCREMENT = 1013904223
ALGORITHM = {
    "id": "lcg32-numerical-recipes",
    "formula": "state = (1664525 * state + 1013904223) mod 2^32; u = state / 2^32",
}


class Lcg32:
    """Small cross-runtime PRNG whose draws can be replayed in JS or Python."""

    def __init__(self, seed: int, *, stream: int = 0) -> None:
        self.state = (int(seed) ^ int(stream)) & U32_MASK

    def draw(self, pool: Iterable[str]) -> tuple[str, dict[str, Any]]:
        values = list(pool)
        if not values:
            raise ValueError("Cannot draw from an empty PPTX randomization pool")
        self.state = (LCG_MULTIPLIER * self.state + LCG_INCREMENT) & U32_MASK
        u = self.state / 2**32
        index = min(len(values) - 1, int(u * len(values)))
        return values[index], {
            "state": self.state,
            "u": u,
            "index": index,
            "pool": values,
            "selected": values[index],
        }


def _portable(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return value


def _layout_family(layout: dict[str, Any]) -> str:
    return str(layout.get("family") or "").strip().lower()


def _page_intent(page: dict[str, Any]) -> str:
    explicit = str(page.get("intent") or page.get("page_role") or "").strip().lower()
    if explicit in {"cover", "navigation", "comparison", "modules", "evidence", "statement", "closing"}:
        return explicit
    role_map = {
        "agenda": "navigation",
        "problem_statement": "statement",
        "framework_explainer": "modules",
        "data_insight": "evidence",
        "exercise": "modules",
        "takeaway": "statement",
        "closing": "closing",
    }
    if explicit in role_map:
        return role_map[explicit]
    role = str(page.get("role") or "").strip().lower()
    if role in {"toc", "agenda", "index", "index-or-map"}:
        return "navigation"
    if role in {"closing", "close"}:
        return "closing"
    if role in {"quote", "takeaway", "statement"}:
        return "statement"
    return "general"


def _candidate_layouts(layouts: list[dict[str, Any]], intent: str) -> list[dict[str, Any]]:
    """Return all semantically compatible active Layouts in stable order."""
    family_by_intent = {
        "cover": {"cover"},
        "navigation": {"toc"},
        "comparison": {"comparison", "data-viz"},
        "modules": {"modules", "metrics", "sequence", "content", "infographic"},
        "evidence": {"metrics", "data-viz", "comparison", "infographic"},
        "statement": {"statement", "chapter", "closing"},
        "closing": {"closing", "statement", "chapter"},
    }
    families = family_by_intent.get(intent)
    if not families:
        return list(layouts)
    filtered = [layout for layout in layouts if _layout_family(layout) in families]
    # A semantic route may intentionally have no family match in a reduced
    # fixture.  Keep the planner usable while recording the fallback pool.
    return filtered or list(layouts)


def _layout_content_compatible(layout: dict[str, Any], intent: str, hints: dict[str, Any]) -> bool:
    """Reject semantically impossible random choices before drawing."""
    layout_id = str(layout.get("id") or "")
    schema = (layout.get("pptx") or {}).get("placeholder_schema") or []
    if intent in {"cover", "navigation", "comparison", "modules", "evidence", "statement", "closing"} and hints.get("has_title"):
        # If the page has a real title, do not randomly choose a scaffold that
        # only exposes one giant body slot.  Such composite decomposition must
        # be supplied by a dedicated PPTX Variant first.
        if schema and not any(str(row.get("placeholder_type")) == "title" for row in schema if isinstance(row, dict)):
            return False
    if layout.get("media_requirement") == "with-image" and not hints.get("has_image"):
        return False
    if layout_id in {"executive-bio", "people-3", "team-grid"} and not hints.get("has_people"):
        return False
    if layout_id.startswith("map-") and not hints.get("has_map"):
        return False
    if layout_id in {"heat-map", "radar-chart", "multi-line-chart", "data-annotation", "matrix-4quadrant"} and not hints.get("has_chart"):
        return False
    if layout_id == "comparison-table" and not hints.get("has_table"):
        return False
    if layout_id == "pricing-3col" and not hints.get("has_pricing"):
        return False
    if layout_id == "swot-quadrant" and not hints.get("has_quadrants"):
        return False
    if intent == "statement" and layout_id.startswith("chapter-") and not hints.get("has_chapter"):
        return False
    if intent == "statement" and layout_id == "testimonial-full" and not hints.get("quote"):
        return False
    return True


def _capacity_filtered(candidates: list[dict[str, Any]], intent: str, hints: dict[str, Any]) -> list[dict[str, Any]]:
    """Keep count-specific families aligned with the page's content count."""
    count = hints.get("item_count")
    if not isinstance(count, int) or count <= 0:
        return candidates
    pattern = r"^toc-(\d+)(?:-|$)" if intent == "navigation" else r"^cards-1-plus-(\d+)$" if intent == "modules" else None
    if not pattern:
        return candidates
    sized: list[tuple[dict[str, Any], int]] = []
    for candidate in candidates:
        match = re.match(pattern, str(candidate.get("id")))
        if match:
            sized.append((candidate, int(match.group(1))))
    if not sized:
        return candidates
    exact = [candidate for candidate, size in sized if size == count]
    if exact:
        return exact
    larger = [candidate for candidate, size in sized if size >= count]
    return larger or candidates


def _flatten_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for child in value.values():
            result.extend(_flatten_text(child))
        return result
    if isinstance(value, list):
        result = []
        for child in value:
            result.extend(_flatten_text(child))
        return result
    return []


def content_hints(page: dict[str, Any]) -> dict[str, Any]:
    """Normalize page content into the predicates used by PPTX Variants."""
    raw = page.get("content") if isinstance(page.get("content"), dict) else page
    raw = raw if isinstance(raw, dict) else {}
    intent = _page_intent(page)
    items: list[Any] = []
    for key in ("items", "chapters", "stages", "milestones", "phases", "quadrants", "stats", "priorities", "recommendations"):
        if isinstance(raw.get(key), list):
            items = list(raw[key])
            break
    if not items and isinstance(raw.get("toc-content"), str):
        items = [line for line in raw["toc-content"].splitlines() if line.strip()]
    hints: dict[str, Any] = {
        "item_count": len(items) if items else raw.get("item_count"),
        "has_image": bool(raw.get("image") or raw.get("images") or raw.get("photo_path") or raw.get("has_image")),
        "has_people": bool(raw.get("people") or raw.get("members")),
        "has_map": bool(raw.get("map") or raw.get("locations") or raw.get("region")),
        "has_chart": bool(raw.get("chart") or raw.get("metrics") or raw.get("stats") or raw.get("data") or any(str(key).startswith("metric") for key in raw)),
        "has_table": bool(raw.get("table") or raw.get("comparison_table") or raw.get("comparison-table")),
        "has_pricing": bool(raw.get("pricing") or raw.get("tiers") or raw.get("plans")),
        "has_quadrants": bool(raw.get("quadrants") or raw.get("swot")),
        "has_chapter": bool(raw.get("chapter") or raw.get("chapters")),
        "has_title": bool(raw.get("title") or raw.get("headline")),
        "quote": raw.get("quote") or raw.get("headline") if intent == "statement" else raw.get("quote"),
        "items": items,
        "attribution_card": bool(raw.get("attribution_card")),
        "all_icons_resolved": bool(raw.get("all_icons_resolved") or raw.get("icons_resolved")),
    }
    if hints["item_count"] is None:
        hints["item_count"] = {
            "navigation": 4,
            "comparison": 2,
            "modules": 3,
            "evidence": 3,
        }.get(intent)
    if intent == "statement" and not hints.get("quote"):
        hints["quote"] = "示範語句"
    if items and not hints["all_icons_resolved"]:
        # This is only a compatibility hint; the renderer never invents icons.
        hints["all_icons_resolved"] = all(isinstance(item, dict) and bool(item.get("icon")) for item in items)
    bodies = [text for text in _flatten_text(items) if text.strip()]
    if bodies:
        hints["body_chars_in_range"] = all(21 <= len(text) <= 140 for text in bodies)
    return {key: value for key, value in hints.items() if value is not None}


def _default_pages() -> list[dict[str, Any]]:
    return [
        {"slide_id": "cover", "intent": "cover", "content": {"title": "隨機 PPTX 示範", "subtitle": "同一個 seed 可重現不同 Layout sequence"}},
        {"slide_id": "toc", "intent": "navigation", "content": {"title": "閱讀路徑", "chapters": [{"title": str(i)} for i in range(1, 5)]}},
        {"slide_id": "content-1", "intent": "comparison", "content": {"title": "前後差異", "items": [{"body": "比較項目"}, {"body": "比較項目"}]}},
        {"slide_id": "content-2", "intent": "modules", "content": {"title": "三個模組", "items": [{"body": "模組內容"}] * 3}},
        {"slide_id": "content-3", "intent": "evidence", "content": {"title": "證據與判斷", "stats": [{"value": "01"}, {"value": "02"}, {"value": "03"}]}},
        {"slide_id": "qa", "intent": "statement", "content": {"quote": "先選擇合適的投影，再填入內容。"}},
    ]


def pages_from_content(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("slides")
    if isinstance(raw, list):
        pages = [dict(item) for item in raw if isinstance(item, dict)]
        if pages:
            return pages
    if isinstance(raw, dict):
        key_intents = {
            "cover": "cover",
            "toc": "navigation",
            "content-a": "comparison",
            "content-b": "modules",
            "content-c": "statement",
            "qa": "evidence",
        }
        pages = []
        for slide_id, value in raw.items():
            page = dict(value) if isinstance(value, dict) else {"content": value}
            if isinstance(value, dict) and "content" not in page:
                # The current demo manifest uses a role-keyed map whose value
                # is already the page content.  Preserve it as content for
                # the builder instead of dropping every field at handoff.
                page["content"] = dict(value)
            page.setdefault("slide_id", str(slide_id))
            page.setdefault("intent", key_intents.get(str(slide_id), "general"))
            pages.append(page)
        if pages:
            return pages
    return _default_pages()


def _layout_slots(layout_id: str) -> list[dict[str, Any]]:
    path = ROOT / "prompt_system" / "layouts" / f"{layout_id}.yaml"
    if not path.exists():
        raise ValueError(f"Missing canonical Layout for PPTX random selection: {layout_id}")
    data = _load_yaml(path)
    slots = data.get("slots")
    if not isinstance(slots, list) or not slots:
        raise ValueError(f"Layout has no slots: {path}")
    return slots


def _select_variant_projection(layout_id: str, page: dict[str, Any], rng: Lcg32, draw_stream: int) -> tuple[dict[str, Any], dict[str, Any] | None]:
    hints = content_hints(page)
    resolved = resolve_variant(layout_id, hints)
    variant_draw = None
    selected = resolved.get("selected_variant_id")
    candidates = list(resolved.get("variant_candidates") or [])
    if candidates:
        selected, variant_draw = Lcg32(rng.state, stream=draw_stream).draw(candidates)
        # Advance the main stream by replaying exactly the same draw.  This
        # keeps the ledger linear and makes the JS/Python boundary explicit.
        rng.state = variant_draw["state"]
        resolved = resolve_variant(layout_id, hints, requested_id=selected)
    projection = project_placeholders(
        layout_id,
        _layout_slots(layout_id),
        hints,
        requested_id=selected,
    )
    return projection, variant_draw


def _background_role_for_layout(layout: dict[str, Any], index: int) -> str:
    """Map a selected Layout family to one of the six background roles."""
    family = _layout_family(layout)
    if family == "cover":
        return "cover"
    if family == "toc":
        return "toc"
    if family in {"metrics", "data-viz"}:
        return "qa"
    if family in {"statement", "closing", "chapter"}:
        return "content-c"
    return "content-a" if index % 2 else "content-b"


def _ready_background_candidates(theme_id: str, *, root: Path = ROOT) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for path in sorted((root / "prompt_system" / "pptx_background_sets").glob("*.yaml")):
        set_id = path.stem
        result = resolve_background_set(theme_id, set_id, require_assets=True, root=root)
        if result.get("status") != "ready":
            continue
        source_kind = str((result.get("background_set") or {}).get("source_kind") or "")
        candidates.append({
            "theme_id": theme_id,
            "background_set_id": set_id,
            "source_manifest": result.get("source_manifest"),
            "source_kind": source_kind or "existing-qa-passed-set",
            "fresh": "fresh" in set_id or "fresh" in source_kind or "generation" in source_kind,
            "roles": [
                {"id": str(role.get("id")), "asset": str(role.get("asset"))}
                for role in (result.get("roles") or [])
                if isinstance(role, dict) and role.get("id") and role.get("asset")
            ],
        })
    return candidates


def build_selection(
    matrix: dict[str, Any],
    *,
    seed: int,
    matrix_source: Path | None = None,
    content: dict[str, Any] | None = None,
    theme_id: str | None = None,
    random_theme: bool = False,
    random_background: bool = False,
    background_set_id: str | None = None,
) -> dict[str, Any]:
    layouts = [
        dict(layout)
        for layout in matrix.get("layouts", [])
        if isinstance(layout, dict) and str(layout.get("id")) not in RETIRED_LAYOUT_IDS
    ]
    layouts.sort(key=lambda item: str(item.get("id")))
    themes = [dict(theme) for theme in matrix.get("themes", []) if isinstance(theme, dict)]
    if not layouts:
        raise ValueError("PPTX randomization requires at least one active Layout")
    if not themes:
        raise ValueError("PPTX randomization requires at least one Theme")

    rng = Lcg32(seed)
    theme_ids = [str(theme.get("id")) for theme in themes if theme.get("id")]
    if theme_id:
        if theme_id not in theme_ids:
            raise ValueError(f"Unknown PPTX Theme: {theme_id}")
        selected_theme = theme_id
        theme_draw = None
        theme_basis = "explicit-theme"
    elif random_theme:
        ready_theme_ids = [theme for theme in theme_ids if _ready_background_candidates(theme)]
        if not ready_theme_ids:
            raise ValueError("Random PPTX Theme selection requires at least one Theme-compatible ready background set")
        selected_theme, theme_draw = rng.draw(ready_theme_ids)
        theme_ids = ready_theme_ids
        theme_basis = "seeded-theme-draw"
    else:
        selected_theme = "brand-editorial" if "brand-editorial" in theme_ids else theme_ids[0]
        theme_draw = None
        theme_basis = "default-theme-fixed"

    pages = pages_from_content(content or {})
    previous_layout: str | None = None
    slide_rows: list[dict[str, Any]] = []
    layout_draws: list[dict[str, Any]] = []
    variant_draws: list[dict[str, Any]] = []
    for index, page in enumerate(pages, 1):
        intent = _page_intent(page)
        hints = content_hints(page)
        candidates = _capacity_filtered(_candidate_layouts(layouts, intent), intent, hints)
        content_compatible = [candidate for candidate in candidates if _layout_content_compatible(candidate, intent, hints)]
        if content_compatible:
            candidates = content_compatible
        compatible: list[dict[str, Any]] = []
        for candidate in candidates:
            # The compiled matrix already records whether a Layout has a
            # bespoke Variant pool.  Baseline projections do not need to
            # reparse the catalog just to prove compatibility.
            if not (candidate.get("pptx") or {}).get("variant_candidates"):
                compatible.append(candidate)
                continue
            try:
                _select_variant_projection(str(candidate["id"]), page, Lcg32(0), index)
            except (ValueError, KeyError):
                continue
            compatible.append(candidate)
        if not compatible:
            raise ValueError(f"No PPTX Layout candidates remain for intent={intent}")
        if previous_layout and len(compatible) > 1:
            non_repeat = [candidate for candidate in compatible if candidate["id"] != previous_layout]
            if non_repeat:
                compatible = non_repeat
        selected_layout, layout_draw = rng.draw([str(candidate["id"]) for candidate in compatible])
        layout_draw.update({"slide": index, "intent": intent})
        layout_draws.append(layout_draw)
        projection, variant_draw = _select_variant_projection(selected_layout, page, rng, 0x50505458 + index)
        selected_layout_record = next(candidate for candidate in layouts if candidate["id"] == selected_layout)
        background_role = _background_role_for_layout(selected_layout_record, index)
        if variant_draw:
            variant_draw = dict(variant_draw)
            variant_draw.update({"slide": index, "layout_id": selected_layout})
            variant_draws.append(variant_draw)
        slide_rows.append({
            "slide_id": str(page.get("slide_id") or page.get("id") or f"slide-{index:02d}"),
            "intent": intent,
            "content": page.get("content") if isinstance(page.get("content"), dict) else {},
            "layout_id": selected_layout,
            # A repeated Layout can legitimately receive a different role
            # background.  Keep those materialized child Layouts distinct.
            "layout_name": f"{projection['layout_name']}--{background_role}",
            "variant_candidates": projection["variant_candidates"],
            "selected_variant_id": projection["selected_variant_id"],
            "selection_basis": projection["selection_basis"],
            "placeholder_schema": projection["placeholder_schema"],
            "surfaces": projection.get("surfaces", []),
            "background_role": background_role,
        })
        previous_layout = selected_layout

    background_candidates = _ready_background_candidates(selected_theme)
    fresh_candidates = [candidate for candidate in background_candidates if candidate["fresh"]]
    background_pool = fresh_candidates or background_candidates
    if background_set_id:
        selected_background = next((item for item in background_candidates if item["background_set_id"] == background_set_id), None)
        if selected_background is None:
            raise ValueError(f"Background set {background_set_id!r} is not ready for Theme {selected_theme!r}")
        background_draw = None
        background_basis = "explicit-background-set"
    elif random_background and len(background_pool) > 1:
        selected_id, background_draw = rng.draw([item["background_set_id"] for item in background_pool])
        selected_background = next(item for item in background_pool if item["background_set_id"] == selected_id)
        background_basis = "seeded-background-set-draw"
    elif background_pool:
        selected_background = background_pool[0]
        background_draw = None
        background_basis = "fresh-background-set-default" if fresh_candidates else "qa-background-set-default"
    else:
        selected_background = None
        background_draw = None
        background_basis = "generation-required"

    randomized_dimensions = ["layout-sequence"]
    if variant_draws:
        randomized_dimensions.append("pptx-variant")
    if random_theme:
        randomized_dimensions.append("theme")
    if random_background and background_draw:
        randomized_dimensions.append("background-set")
    source_matrix = (matrix_source or DEFAULT_MATRIX).resolve()
    return {
        "schema_version": 1,
        "kind": "pptx_random_selection_manifest",
        "renderer": "pptx",
        "deck_id": f"pptx-random-{int(seed) & U32_MASK}",
        "seed": int(seed) & U32_MASK,
        "algorithm": ALGORITHM,
        "randomized_dimensions": randomized_dimensions,
        "fixed_dimensions": {
            "slide_count": len(slide_rows),
            "aspect_ratio": "16:9",
            "canonical_stage_px": [1920, 1080],
            "artifact_stage_px": [1280, 720],
            "editability": "hybrid-with-native-content",
            "theme_randomized": bool(random_theme),
            "background_randomized": bool(random_background and background_draw),
        },
        "source": {
            "matrix": _portable(source_matrix),
            "matrix_sha256": _sha256(source_matrix) if source_matrix.exists() else None,
            "variant_catalog": "prompt_system/renderers/pptx/layout-variants/catalog.yaml",
        },
        "theme_selection": {
            "candidates": theme_ids,
            "selected": selected_theme,
            "selection_basis": theme_basis,
            "draw": theme_draw,
        },
        "background_selection": {
            "candidates": background_pool,
            "selected": selected_background,
            "selection_basis": background_basis,
            "draw": background_draw,
            "status": "ready" if selected_background else "generation-required",
        },
        "layout_draws": layout_draws,
        "variant_draws": variant_draws,
        "slides": slide_rows,
        "replay": {
            "layout_selection": "semantic-family-pool-without-consecutive-repeat",
            "variant_selection": "compatible-candidates-seeded-draw",
            "background_selection": "fresh-compatible-pool-first",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a reproducible seeded PPTX Layout/Variant selection manifest.")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--content", type=Path, default=DEFAULT_CONTENT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--theme")
    parser.add_argument("--random-theme", action="store_true")
    parser.add_argument("--random-background", action="store_true")
    parser.add_argument("--background-set")
    args = parser.parse_args()
    matrix = _load_json(args.matrix.resolve())
    content = _load_json(args.content.resolve()) if args.content.exists() else {}
    seed = args.seed if args.seed is not None else secrets.randbits(32)
    selection = build_selection(
        matrix,
        seed=seed,
        matrix_source=args.matrix,
        content=content,
        theme_id=args.theme,
        random_theme=args.random_theme,
        random_background=args.random_background,
        background_set_id=args.background_set,
    )
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": _portable(output),
        "seed": selection["seed"],
        "slides": len(selection["slides"]),
        "theme": selection["theme_selection"]["selected"],
        "layouts": [row["layout_id"] for row in selection["slides"]],
        "background": selection["background_selection"]["selected"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
