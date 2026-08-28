"""Validate and compile the shared Art Direction contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "prompt_system" / "art_direction" / "schema.yaml"


class ArtDirectionError(ValueError):
    """Raised when an Art Direction document violates the formal contract."""


def _mapping(value: Any, label: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label} 必須是 object")
        return {}
    return value


def _list(value: Any, label: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{label} 必須是 list")
        return []
    return value


def _required(mapping: dict[str, Any], fields: list[str], label: str, errors: list[str]) -> None:
    missing = [field for field in fields if field not in mapping]
    if missing:
        errors.append(f"{label} 缺少欄位：{', '.join(missing)}")


def _enum(value: Any, allowed: list[str], label: str, errors: list[str]) -> None:
    if value not in allowed:
        errors.append(f"{label} 必須是：{', '.join(allowed)}")


def _https_url(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not re.match(r"^https://[^/]+/.+", value):
        errors.append(f"{label} 必須是完整 https 官方網址")


def load_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ArtDirectionError(f"Art Direction schema 無法解析：{path}")
    return payload


def validate_art_direction(
    payload: dict[str, Any],
    *,
    require_approved: bool = False,
    project_root: Path = PROJECT_ROOT,
    schema: dict[str, Any] | None = None,
) -> list[str]:
    """Return all contract errors without mutating the input payload."""

    schema = schema or load_schema()
    errors: list[str] = []
    _required(payload, schema["required_top_level"], "root", errors)

    if payload.get("schema_version") != schema["schema_version"]:
        errors.append(f"schema_version 必須是 {schema['schema_version']}")
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", str(payload.get("id", ""))):
        errors.append("id 只能使用小寫英數與連字號")

    status = payload.get("status")
    _enum(status, schema["statuses"], "status", errors)

    brief = _mapping(payload.get("brief"), "brief", errors)
    brief_schema = schema["brief"]
    _required(brief, brief_schema["required"], "brief", errors)
    _enum(brief.get("visual_genre"), brief_schema["visual_genres"], "brief.visual_genre", errors)
    metaphor = brief.get("narrative_metaphor")
    if not isinstance(metaphor, str) or not 12 <= len(metaphor.strip()) <= 160:
        errors.append("brief.narrative_metaphor 必須是 12–160 字的完整概念句")

    signature = _mapping(brief.get("signature_move"), "brief.signature_move", errors)
    _required(
        signature,
        ["name", "concept_link", "allowed_variations", "minimum_presence"],
        "brief.signature_move",
        errors,
    )
    if not _list(signature.get("allowed_variations"), "brief.signature_move.allowed_variations", errors):
        errors.append("brief.signature_move.allowed_variations 不得為空")

    spatial = _mapping(brief.get("spatial_rule"), "brief.spatial_rule", errors)
    _required(
        spatial,
        ["primary_anchor", "reading_axis", "crop_logic", "whitespace_logic", "content_alignment"],
        "brief.spatial_rule",
        errors,
    )
    _enum(spatial.get("primary_anchor"), brief_schema["primary_anchors"], "brief.spatial_rule.primary_anchor", errors)
    _enum(spatial.get("reading_axis"), brief_schema["reading_axes"], "brief.spatial_rule.reading_axis", errors)
    _enum(spatial.get("crop_logic"), brief_schema["crop_logics"], "brief.spatial_rule.crop_logic", errors)
    _enum(brief.get("edge_behavior"), brief_schema["edge_behaviors"], "brief.edge_behavior", errors)

    typography = _mapping(brief.get("typography_role"), "brief.typography_role", errors)
    _required(
        typography,
        ["primary_role", "hierarchy_method", "family_policy", "maximum_families", "ai_minimum_visual_text_px"],
        "brief.typography_role",
        errors,
    )
    _enum(
        typography.get("primary_role"),
        brief_schema["typography_primary_roles"],
        "brief.typography_role.primary_role",
        errors,
    )
    _enum(
        typography.get("family_policy"),
        brief_schema["typography_family_policies"],
        "brief.typography_role.family_policy",
        errors,
    )
    if typography.get("maximum_families") not in (1, 2):
        errors.append("brief.typography_role.maximum_families 只能是 1 或 2")
    if typography.get("ai_minimum_visual_text_px") != 36:
        errors.append("brief.typography_role.ai_minimum_visual_text_px 必須是 36")

    color = _mapping(brief.get("color_behavior"), "brief.color_behavior", errors)
    _required(color, ["primary_job", "accent_job", "accent_area_limit"], "brief.color_behavior", errors)
    _enum(color.get("primary_job"), brief_schema["color_primary_jobs"], "brief.color_behavior.primary_job", errors)
    _enum(color.get("accent_job"), brief_schema["color_accent_jobs"], "brief.color_behavior.accent_job", errors)

    cliches = _list(brief.get("forbidden_cliches"), "brief.forbidden_cliches", errors)
    if len(cliches) < brief_schema["forbidden_cliche_min_items"]:
        errors.append(
            "brief.forbidden_cliches 至少需要 "
            f"{brief_schema['forbidden_cliche_min_items']} 項"
        )
    unknown_cliches = sorted(set(cliches) - set(brief_schema["allowed_forbidden_cliches"]))
    if unknown_cliches:
        errors.append(f"brief.forbidden_cliches 含未知項目：{', '.join(unknown_cliches)}")

    packet = _mapping(payload.get("reference_packet"), "reference_packet", errors)
    packet_schema = schema["reference_packet"]
    _required(packet, packet_schema["required"], "reference_packet", errors)
    official_cases = _list(packet.get("official_cases"), "reference_packet.official_cases", errors)
    if status in {"ready-for-audition", "approved-for-renderer"}:
        minimum = packet_schema["official_cases"]["min_items_for_audition"]
        if len(official_cases) < minimum:
            errors.append(f"ready-for-audition 以上至少需要 {minimum} 個官方案例")
    if len(official_cases) > packet_schema["official_cases"]["max_items"]:
        errors.append("reference_packet.official_cases 最多 4 個")
    for index, case in enumerate(official_cases):
        case_mapping = _mapping(case, f"reference_packet.official_cases[{index}]", errors)
        _required(
            case_mapping,
            packet_schema["official_cases"]["required_fields"],
            f"reference_packet.official_cases[{index}]",
            errors,
        )
        if status in {"ready-for-audition", "approved-for-renderer"}:
            _https_url(
                case_mapping.get("official_url"),
                f"reference_packet.official_cases[{index}].official_url",
                errors,
            )

    cross_reference = _mapping(
        packet.get("cross_domain_reference"),
        "reference_packet.cross_domain_reference",
        errors,
    )
    _required(
        cross_reference,
        ["type", "title", "source_url", "borrowed_method"],
        "reference_packet.cross_domain_reference",
        errors,
    )
    if status in {"ready-for-audition", "approved-for-renderer"}:
        _https_url(
            cross_reference.get("source_url"),
            "reference_packet.cross_domain_reference.source_url",
            errors,
        )

    asset_sources = _list(
        packet.get("reusable_asset_sources"),
        "reference_packet.reusable_asset_sources",
        errors,
    )
    if status in {"ready-for-audition", "approved-for-renderer"} and not asset_sources:
        errors.append("ready-for-audition 以上至少需要一個 reusable asset source")
    forbidden_licenses = set(packet_schema["forbidden_license_states"])
    for index, source in enumerate(asset_sources):
        source_mapping = _mapping(source, f"reference_packet.reusable_asset_sources[{index}]", errors)
        _required(
            source_mapping,
            packet_schema["reusable_asset_source_required_fields"],
            f"reference_packet.reusable_asset_sources[{index}]",
            errors,
        )
        license_status = str(source_mapping.get("license_status", "")).strip().lower()
        if not license_status or license_status in forbidden_licenses:
            errors.append(
                f"reference_packet.reusable_asset_sources[{index}].license_status 尚未驗證"
            )

    anti_reference = _mapping(packet.get("anti_reference"), "reference_packet.anti_reference", errors)
    _required(anti_reference, ["description", "failure_risk"], "reference_packet.anti_reference", errors)

    asset_family = _mapping(payload.get("asset_family"), "asset_family", errors)
    asset_schema = schema["asset_family"]
    _required(asset_family, asset_schema["required"], "asset_family", errors)
    if asset_family.get("maximum_families") != asset_schema["maximum_families"]:
        errors.append(f"asset_family.maximum_families 必須是 {asset_schema['maximum_families']}")
    if asset_family.get("provenance_required") is not True:
        errors.append("asset_family.provenance_required 必須是 true")
    if asset_family.get("no_mixed_icon_families") is not True:
        errors.append("asset_family.no_mixed_icon_families 必須是 true")
    roles = _list(asset_family.get("allowed_roles"), "asset_family.allowed_roles", errors)
    unknown_roles = sorted(set(roles) - set(asset_schema["allowed_roles"]))
    if unknown_roles:
        errors.append(f"asset_family.allowed_roles 含未知項目：{', '.join(unknown_roles)}")

    grammar = _mapping(payload.get("scene_grammar"), "scene_grammar", errors)
    _required(grammar, ["mode", "scenes"], "scene_grammar", errors)
    scenes = _list(grammar.get("scenes"), "scene_grammar.scenes", errors)
    if not scenes:
        errors.append("scene_grammar.scenes 不得為空")
    scene_roles: list[str] = []
    intensities: list[int] = []
    for index, scene in enumerate(scenes):
        scene_mapping = _mapping(scene, f"scene_grammar.scenes[{index}]", errors)
        _required(
            scene_mapping,
            ["slide_id", "role", "visual_intensity", "primary_focus", "signature_move_variant"],
            f"scene_grammar.scenes[{index}]",
            errors,
        )
        role = scene_mapping.get("role")
        _enum(role, schema["scene_grammar"]["roles"], f"scene_grammar.scenes[{index}].role", errors)
        if isinstance(role, str):
            scene_roles.append(role)
        intensity = scene_mapping.get("visual_intensity")
        minimum = schema["scene_grammar"]["visual_intensity"]["minimum"]
        maximum = schema["scene_grammar"]["visual_intensity"]["maximum"]
        if not isinstance(intensity, int) or not minimum <= intensity <= maximum:
            errors.append(
                f"scene_grammar.scenes[{index}].visual_intensity 必須介於 {minimum}–{maximum}"
            )
        else:
            intensities.append(intensity)

    maximum_run = schema["scene_grammar"]["maximum_consecutive_same_role"]
    current_role = None
    current_run = 0
    for role in scene_roles:
        if role == current_role:
            current_run += 1
        else:
            current_role = role
            current_run = 1
        if current_run > maximum_run:
            errors.append(f"scene role 不得連續超過 {maximum_run} 頁：{role}")
            break

    if grammar.get("mode") == "full-deck" and status in {
        "ready-for-audition",
        "approved-for-renderer",
    }:
        missing_roles = sorted(
            set(schema["scene_grammar"]["required_roles_for_full_deck"]) - set(scene_roles)
        )
        if missing_roles:
            errors.append(f"full-deck 缺少 scene role：{', '.join(missing_roles)}")
        if intensities:
            pause_limit = schema["scene_grammar"]["visual_intensity"]["approved_requires_pause_at_or_below"]
            peak_limit = schema["scene_grammar"]["visual_intensity"]["approved_requires_peak_at_or_above"]
            if min(intensities) > pause_limit:
                errors.append(f"full-deck 至少需要一頁 visual_intensity <= {pause_limit}")
            if max(intensities) < peak_limit:
                errors.append(f"full-deck 至少需要一頁 visual_intensity >= {peak_limit}")

    renderer_handoff = _mapping(payload.get("renderer_handoff"), "renderer_handoff", errors)
    html_preset_ids: set[str] = set()
    html_preset_catalog = (
        project_root / "prompt_system" / "renderers" / "html" / "preset-themes.yaml"
    )
    if html_preset_catalog.exists():
        preset_payload = yaml.safe_load(html_preset_catalog.read_text(encoding="utf-8")) or {}
        html_preset_ids = set((preset_payload.get("themes") or {}).keys())

    for renderer in schema["renderer_handoff"]["renderers"]:
        renderer_payload = _mapping(
            renderer_handoff.get(renderer),
            f"renderer_handoff.{renderer}",
            errors,
        )
        _required(
            renderer_payload,
            schema["renderer_handoff"]["required_per_renderer"],
            f"renderer_handoff.{renderer}",
            errors,
        )
        themes = _list(
            renderer_payload.get("theme_candidates"),
            f"renderer_handoff.{renderer}.theme_candidates",
            errors,
        )
        layouts = _list(
            renderer_payload.get("layout_sequence"),
            f"renderer_handoff.{renderer}.layout_sequence",
            errors,
        )
        if not themes:
            errors.append(f"renderer_handoff.{renderer}.theme_candidates 不得為空")
        if len(layouts) != len(scenes):
            errors.append(
                f"renderer_handoff.{renderer}.layout_sequence 必須與 scenes 同為 {len(scenes)} 頁"
            )
        for theme_id in themes:
            theme_path = (
                project_root
                / "prompt_system"
                / "renderers"
                / renderer
                / "themes"
                / f"{theme_id}.yaml"
            )
            is_html_preset = renderer == "html" and theme_id in html_preset_ids
            if not theme_path.exists() and not is_html_preset:
                errors.append(f"{renderer} 找不到 Theme adapter：{theme_id}")
        for layout_id in layouts:
            layout_path = (
                project_root
                / "prompt_system"
                / "renderers"
                / renderer
                / "layouts"
                / f"{layout_id}.yaml"
            )
            if not layout_path.exists():
                errors.append(f"{renderer} 找不到 Layout adapter：{layout_id}")

    approval = _mapping(payload.get("approval"), "approval", errors)
    machine = _mapping(approval.get("machine"), "approval.machine", errors)
    human = _mapping(approval.get("human"), "approval.human", errors)
    _enum(
        machine.get("status"),
        schema["approval"]["machine_states"],
        "approval.machine.status",
        errors,
    )
    _enum(
        human.get("status"),
        schema["approval"]["human_states"],
        "approval.human.status",
        errors,
    )

    perceptual = _mapping(payload.get("perceptual_qa"), "perceptual_qa", errors)
    perceptual_checks = _list(
        perceptual.get("required_checks"),
        "perceptual_qa.required_checks",
        errors,
    )
    missing_checks = sorted(
        set(schema["perceptual_qa"]["required_checks"]) - set(perceptual_checks)
    )
    if missing_checks:
        errors.append(f"perceptual_qa.required_checks 缺少：{', '.join(missing_checks)}")

    approved_gate = (
        status == "approved-for-renderer"
        and machine.get("status") == "pass"
        and human.get("status") == "approved"
        and bool(human.get("approved_by"))
        and bool(human.get("approved_at"))
    )
    if status == "approved-for-renderer" and not approved_gate:
        errors.append("approved-for-renderer 必須同時有 machine pass 與具名 human approval")
    if require_approved and not approved_gate:
        errors.append("正式 renderer gate 未通過；目前只可做方向試演")

    return errors


def load_art_direction(path: Path, *, require_approved: bool = False) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ArtDirectionError(f"Art Direction 必須是 YAML object：{path}")
    errors = validate_art_direction(payload, require_approved=require_approved)
    if errors:
        raise ArtDirectionError("\n".join(f"- {error}" for error in errors))
    return payload


def build_renderer_handoff(payload: dict[str, Any], source_path: Path | None = None) -> dict[str, Any]:
    """Compile only renderer-safe, reference-free direction instructions."""

    approval = payload["approval"]
    formal_publish_allowed = (
        payload["status"] == "approved-for-renderer"
        and approval["machine"]["status"] == "pass"
        and approval["human"]["status"] == "approved"
    )
    handoff = {
        "schema_version": payload["schema_version"],
        "art_direction_id": payload["id"],
        "status": payload["status"],
        "formal_publish_allowed": formal_publish_allowed,
        "story_ref": payload["story_ref"],
        "brief": deepcopy(payload["brief"]),
        "asset_family": deepcopy(payload["asset_family"]),
        "scene_plan": deepcopy(payload["scene_grammar"]["scenes"]),
        "renderers": deepcopy(payload["renderer_handoff"]),
        "perceptual_qa": deepcopy(payload["perceptual_qa"]),
        "compiled_at": datetime.now(timezone.utc).isoformat(),
    }
    if source_path:
        source_bytes = source_path.read_bytes()
        handoff["source"] = {
            "path": str(source_path),
            "sha256": hashlib.sha256(source_bytes).hexdigest(),
            "schema_path": str(SCHEMA_PATH),
            "schema_sha256": hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest(),
        }
    return handoff


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and compile Art Direction YAML.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--require-approved", action="store_true")
    parser.add_argument("--emit-handoff", type=Path)
    args = parser.parse_args()

    source_path = args.path.resolve()
    try:
        payload = load_art_direction(source_path, require_approved=args.require_approved)
    except (OSError, yaml.YAMLError, ArtDirectionError) as exc:
        print(f"Art Direction validation failed:\n{exc}")
        return 1

    handoff = build_renderer_handoff(payload, source_path)
    if args.emit_handoff:
        output_path = args.emit_handoff.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(handoff, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "status": "valid",
                "id": payload["id"],
                "direction_status": payload["status"],
                "formal_publish_allowed": handoff["formal_publish_allowed"],
                "scene_count": len(handoff["scene_plan"]),
                "handoff": str(args.emit_handoff.resolve()) if args.emit_handoff else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
