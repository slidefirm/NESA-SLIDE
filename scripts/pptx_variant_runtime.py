"""Renderer-owned PPTX variant resolution and typed placeholder projection.

The canonical Layout remains untouched. This module is deliberately small and
pure so adapters, matrix compilation, and tests can share the same decision.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "prompt_system" / "renderers" / "pptx" / "layout-variants" / "catalog.yaml"
CANONICAL_STAGE_PX = (1920, 1080)
ARTIFACT_TOOL_STAGE_PX = (1280, 720)
STAGE_SCALE = 2 / 3
ALLOWED_PLACEHOLDER_TYPES = {"title", "subtitle", "body", "picture", "chart", "table"}
DEFAULT_FONT_SIZE_STAGE_PX = {"title": 56, "subtitle": 28, "body": 24, "picture": 18, "chart": 24, "table": 22}


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("renderer") != "pptx":
        raise ValueError(f"Invalid PPTX variant catalog: {path}")
    _validate_catalog(data)
    return data


def _validate_catalog(data: dict[str, Any]) -> None:
    for layout_id, entry in (data.get("layouts") or {}).items():
        if not isinstance(entry, dict):
            raise ValueError(f"PPTX catalog layout {layout_id!r} must be a mapping")
        variant_sets = []
        if entry.get("base_placeholder_contract") is not None:
            variant_sets.append(("base", entry["base_placeholder_contract"]))
        for variant in entry.get("variants") or []:
            if not isinstance(variant, dict) or not variant.get("id"):
                raise ValueError(f"PPTX catalog {layout_id!r} has an invalid variant")
            variant_sets.append((str(variant["id"]), variant.get("placeholders") or []))
        for scope, rows in variant_sets:
            ids: set[str] = set()
            templates: set[str] = set()
            if not isinstance(rows, list):
                raise ValueError(f"PPTX catalog {layout_id}/{scope} placeholders must be a list")
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError(f"PPTX catalog {layout_id}/{scope} has a non-mapping placeholder")
                if row.get("template"):
                    template = str(row["template"])
                    if template in templates:
                        raise ValueError(f"Duplicate PPTX placeholder template {layout_id}/{scope}/{template}")
                    templates.add(template)
                    continue
                row_id = str(row.get("id") or "")
                if not row_id or row_id in ids:
                    raise ValueError(f"Duplicate or missing PPTX placeholder id {layout_id}/{scope}/{row_id}")
                ids.add(row_id)
                role = str(row.get("placeholder_type") or "")
                if role not in ALLOWED_PLACEHOLDER_TYPES:
                    raise ValueError(f"Invalid PPTX placeholder type {layout_id}/{scope}/{row_id}: {role}")


def stage_px_to_artifact(value: float) -> float:
    return float(value) * STAGE_SCALE


def stage_region_to_artifact(region: list[float]) -> list[float]:
    if len(region) != 4:
        raise ValueError(f"Expected [x,y,w,h], got {region!r}")
    x, y, w, h = (float(value) for value in region)
    return [stage_px_to_artifact(x), stage_px_to_artifact(y), stage_px_to_artifact(w), stage_px_to_artifact(h)]


def stage_font_px_to_points(value: float) -> float:
    return float(value) * 0.5


def placeholder_type(slot_id: str, slot: dict[str, Any] | None = None) -> str:
    """Infer a role only when the semantic alias is unambiguous.

    In particular, ``title-role`` is a person's role and therefore subtitle,
    never the slide title. Decoration slots are intentionally not placeholders.
    """
    value = slot_id.strip().lower().replace("_", "-")
    label = str((slot or {}).get("label", "")).lower()
    note = str((slot or {}).get("note", "")).lower()
    if any(token in f"{value} {label} {note}" for token in ("decor", "accent-bar", "divider", "ornament", "裝飾")):
        return "decoration"
    if value in {"title", "headline", "page-title", "main-title"} or "主標題" in label:
        return "title"
    if value in {"subtitle", "sub-title", "page-subtitle", "kicker"} or "副標" in label:
        return "subtitle"
    if value in {"title-role", "role", "position", "job-title"}:
        return "subtitle"
    if any(token in value for token in ("photo", "image", "avatar", "portrait", "logo")):
        return "picture"
    if any(token in value for token in ("chart", "graph", "map", "axis", "radar", "heat")):
        return "chart"
    if "table" in value:
        return "table"
    if any(token in value for token in ("subtitle", "header", "note", "caption", "footer", "source", "label", "speaker", "org", "date", "meta", "eyebrow", "kicker", "footnote")):
        return "subtitle"
    return "body"


def _matches(match: dict[str, Any], content: dict[str, Any]) -> bool:
    if "item_count" in match and content.get("item_count", len(content.get("items", []))) != match["item_count"]:
        return False
    if match.get("requires_image") and not (content.get("has_image") or content.get("image") or content.get("images")):
        return False
    if match.get("requires_quote") and not content.get("quote"):
        return False
    if match.get("requires_symbol") and not (content.get("has_symbol") or content.get("symbols")):
        return False
    items = content.get("items") or []
    bodies = [str(item.get("body", "")) if isinstance(item, dict) else str(item) for item in items]
    if "body_chars" in match:
        bounds = match["body_chars"]
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2 or not all(int(bounds[0]) <= len(body) <= int(bounds[1]) for body in bodies):
            # A precomputed flag is accepted by content manifests that have
            # already normalized item bodies.
            if not content.get("body_chars_in_range"):
                return False
    if match.get("all_icons_resolved") and not (content.get("all_icons_resolved") or content.get("icons_resolved")):
        return False
    if match.get("all_metrics_extractable"):
        import re
        metric_re = re.compile(r"^\d[\d.,]*\s*(?:%|萬|億|小時|分鐘|天|週|個月|年|倍|件|人|公里)?\s+.+$")
        if not (content.get("all_metrics_extractable") or (bodies and all(metric_re.match(body.strip()) for body in bodies))):
            return False
    if "orientation" in match and content.get("orientation") != match["orientation"]:
        return False
    if "attribution_card" in match and bool(content.get("attribution_card")) != bool(match["attribution_card"]):
        return False
    return True


def resolve_variant(layout_id: str, content: dict[str, Any] | None = None, requested_id: str | None = None, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    catalog = catalog or load_catalog()
    content = content or {}
    entry = (catalog.get("layouts") or {}).get(layout_id) or {}
    variants = entry.get("variants") or []
    candidates = [str(item["id"]) for item in variants if isinstance(item, dict) and item.get("id") and _matches(item.get("match") or {}, content)]
    if requested_id:
        known = {str(item.get("id")): item for item in variants if isinstance(item, dict)}
        if requested_id not in known:
            raise ValueError(f"Unknown PPTX layout variant {layout_id!r}/{requested_id!r}")
        if requested_id not in candidates:
            raise ValueError(f"Incompatible PPTX layout variant {layout_id!r}/{requested_id!r}; candidates={candidates}")
        selected = requested_id
        basis = "explicit-compatible-override"
    elif variants:
        if not candidates:
            raise ValueError(f"No compatible PPTX layout variant for {layout_id!r}")
        ranked = sorted((item for item in variants if str(item.get("id")) in candidates), key=lambda item: (-int(item.get("priority", 0)), str(item.get("id"))))
        selected = str(ranked[0]["id"])
        basis = "content-match-priority"
    else:
        selected = None
        basis = "fixed-base-projection"
    selected_spec = next((deepcopy(item) for item in variants if str(item.get("id")) == selected), None) if selected else None
    return {
        "layout_id": layout_id,
        "variant_candidates": candidates,
        "selected_variant_id": selected,
        "selection_basis": basis,
        "placeholder_schema": selected_spec.get("placeholders", []) if selected_spec else entry.get("base_placeholder_contract", []),
        "surfaces": selected_spec.get("surfaces", []) if selected_spec else entry.get("base_surfaces", []),
        "variant_spec": selected_spec,
    }


def _child_region(parent: list[float], child: list[float]) -> list[float]:
    px, py, pw, ph = parent
    cx, cy, cw, ch = child
    return [px + pw * cx / 100, py + ph * cy / 100, pw * cw / 100, ph * ch / 100]


def _slot_region(slot: dict[str, Any]) -> list[float] | None:
    region = slot.get("region")
    if isinstance(region, list) and len(region) == 4:
        return list(region)
    placement = slot.get("placement")
    if isinstance(placement, dict):
        default = str(placement.get("default", "main"))
        candidate = placement.get(f"{default}_region") or placement.get("main_region") or placement.get("watermark_region")
        if isinstance(candidate, list) and len(candidate) == 4:
            return list(candidate)
    anchor = slot.get("anchor")
    if isinstance(anchor, list) and len(anchor) == 2:
        anchor_x, anchor_y = (float(value) for value in anchor)
        return [max(0.0, min(90.0, anchor_x - 5.0)), max(0.0, min(95.0, anchor_y - 2.5)), 10.0, 5.0]
    return None


def _default_base_contract(slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project every non-decoration core slot when no special Variant exists.

    The Variant catalog is allowed to override a Layout, but it must not turn
    the other Layouts into unsupported cases.  Baseline PPTX adapters already
    carry a renderer-owned ``placeholder_type``; direct callers can omit it and
    use the semantic inference above.
    """
    rows: list[dict[str, Any]] = []
    for slot in slots:
        if not isinstance(slot, dict):
            continue
        source_id = str(slot.get("id") or "").strip()
        if not source_id:
            continue
        role = str(
            slot.get("placeholder_type")
            or slot.get("pptx_placeholder_type")
            or slot.get("semantic_role")
            or placeholder_type(source_id, slot)
        )
        if role == "decoration":
            continue
        if role not in ALLOWED_PLACEHOLDER_TYPES:
            role = placeholder_type(source_id, slot)
        if role not in ALLOWED_PLACEHOLDER_TYPES:
            raise ValueError(f"Invalid inferred PPTX placeholder type {role!r} for {source_id}")
        region = _slot_region(slot)
        if region is None:
            raise ValueError(f"Missing region for baseline PPTX placeholder {source_id}")
        if role == "picture":
            content_kind = "image"
        elif role == "chart":
            content_kind = "chart"
        elif role == "table":
            content_kind = "table"
        else:
            content_kind = "text"
        rows.append(
            {
                "id": source_id,
                "source_slot_id": source_id,
                "placeholder_type": role,
                "content_kind": content_kind,
                "optional": bool(slot.get("optional", False)),
                "style_role": slot.get("style_role") or role,
                "font_size_stage_px": DEFAULT_FONT_SIZE_STAGE_PX[role],
                "frame_policy": "fixed" if role in {"title", "subtitle"} else "content-fit",
                "region": list(region),
            }
        )
    return rows


def project_placeholders(layout_id: str, slots: list[dict[str, Any]], content: dict[str, Any] | None = None, requested_id: str | None = None, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return atomic typed rows with stage-space percentage geometry.

    ``slots`` is loaded from the core Layout; the catalog only supplies the
    renderer-specific projection and never mutates that source object.
    """
    resolved = resolve_variant(layout_id, content, requested_id, catalog)
    slot_map = {str(slot.get("id")): slot for slot in slots if isinstance(slot, dict)}
    schema = resolved["placeholder_schema"]
    # Every active core Layout has a PPTX adapter.  When it has no bespoke
    # Variant entry, derive a typed baseline contract from that adapter/core
    # slot list instead of returning an empty schema and a blank slide.
    if not schema and resolved["selected_variant_id"] is None:
        schema = _default_base_contract(slots)
    rows: list[dict[str, Any]] = []
    for item in schema:
        if not isinstance(item, dict):
            continue
        if item.get("template") in {"person", "member", "module"}:
            parent_ids = [slot_id for slot_id in sorted(slot_map) if slot_id.startswith("person-") or slot_id.startswith("member-") or slot_id.startswith("module-")]
            parent_kind = "person" if item["template"] in {"person", "member"} else "module"
            children = item.get("children") or []
            for parent_id in parent_ids:
                parent = slot_map[parent_id]
                region = parent.get("region")
                if not isinstance(region, list) or len(region) != 4:
                    raise ValueError(f"Missing parent region for {layout_id}/{parent_id}")
                for child in children:
                    child_id = f"{parent_id}-{child}"
                    if child == "icon":
                        child_type, kind, child_region = "picture", "image", [8, 8, 24, 24]
                    elif child == "rule":
                        child_type, kind, child_region = "decoration", "decoration", [10, 48, 80, 1]
                    elif child == "source":
                        child_type, kind, child_region = "subtitle", "text", [10, 8, 80, 10]
                    elif child == "metric":
                        child_type, kind, child_region = "body", "text", [10, 32, 80, 28]
                    elif child == "name" or child == "label":
                        child_type, kind, child_region = "body", "text", [10, 48, 80, 12]
                    elif child == "role":
                        child_type, kind, child_region = "subtitle", "text", [10, 62, 80, 9]
                    else:
                        child_type, kind, child_region = "body", "text", [10, 74, 80, 20]
                    if parent_kind == "person" and child == "photo":
                        child_type, kind, child_region = "picture", "image", [10, 8, 80, 38]
                    if child_type != "decoration":
                        rows.append({"id": child_id, "parent_slot_id": parent_id, "source_slot_id": parent_id, "placeholder_type": child_type, "content_kind": kind, "font_size_stage_px": DEFAULT_FONT_SIZE_STAGE_PX[child_type], "region": _child_region(region, child_region)})
            continue
        source_id = str(item.get("source_slot_id") or item.get("id") or "")
        source = slot_map.get(source_id)
        if source is None:
            raise ValueError(f"Placeholder {layout_id}/{source_id} has no core slot")
        region = _slot_region(source)
        if region is None:
            raise ValueError(f"Missing region for {layout_id}/{source_id}")
        role = str(item.get("placeholder_type") or placeholder_type(source_id, source))
        if role == "decoration":
            continue
        if role not in ALLOWED_PLACEHOLDER_TYPES:
            raise ValueError(f"Invalid PPTX placeholder type {role!r} for {layout_id}/{source_id}")
        rows.append({"id": str(item.get("id") or source_id), "source_slot_id": source_id, "placeholder_type": role, "content_kind": str(item.get("content_kind") or ("image" if role == "picture" else "text")), "optional": bool(item.get("optional", False)), "style_role": item.get("style_role") or role, "font_size_stage_px": float(item.get("font_size_stage_px", DEFAULT_FONT_SIZE_STAGE_PX[role])), "frame_policy": str(item.get("frame_policy") or ("fixed" if role in {"title", "subtitle"} else "content-fit")), "region": list(region)})
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate PPTX placeholder ids in {layout_id}: {ids}")
    return {**resolved, "placeholder_schema": rows, "layout_name": f"layout--{layout_id}" + (f"--{resolved['selected_variant_id']}" if resolved["selected_variant_id"] else "")}
