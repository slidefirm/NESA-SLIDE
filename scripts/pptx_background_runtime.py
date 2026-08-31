"""PPTX-only background set selection and preflight.

This resolver is intentionally strict: a missing or incompatible set produces
an explicit generation-required result and never selects brand-editorial as a
fallback for another Theme.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
BACKGROUND_SET_DIR = ROOT / "prompt_system" / "pptx_background_sets"
REQUIRED_ROLES = ("cover", "toc", "content-a", "content-b", "content-c", "qa")


def _load(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
    else:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Background manifest must be a mapping: {path}")
    return value


def _generation_required(theme_id: str, background_set_id: str | None, basis: str, reason: str, *, issues: list[str] | None = None) -> dict[str, Any]:
    set_id = background_set_id or f"{theme_id}-fresh"
    return {
        "status": "generation-required",
        "theme_id": theme_id,
        "background_set_id": set_id,
        "selection_basis": basis,
        "reason": reason,
        "issues": issues or [],
        "generation_plan": {
            "renderer": "image2",
            "roles": list(REQUIRED_ROLES),
            "visible_text": "forbidden",
            "provenance_required": ["seed", "source_manifest", "source_theme", "qa_report"],
        },
    }


def _validate_set(theme_id: str, set_id: str, source_path: Path, data: dict[str, Any], *, require_assets: bool, root: Path = ROOT) -> dict[str, Any]:
    issues: list[str] = []
    if data.get("theme_id") != theme_id:
        return _generation_required(theme_id, set_id, "explicit-set-theme-mismatch", "background set theme_id does not match requested theme", issues=[f"set.theme_id={data.get('theme_id')!r}"])
    theme_ref = str(data.get("theme_ref") or "")
    if theme_ref and Path(theme_ref).stem != theme_id:
        issues.append(f"theme_ref={theme_ref!r}")
    roles = data.get("roles")
    if not isinstance(roles, list):
        issues.append("roles must be a list")
        roles = []
    role_ids = [str(role.get("id")) for role in roles if isinstance(role, dict)]
    if set(role_ids) != set(REQUIRED_ROLES) or len(role_ids) != len(REQUIRED_ROLES):
        issues.append(f"roles={role_ids!r}; expected={list(REQUIRED_ROLES)!r}")
    missing_assets: list[str] = []
    for role in roles:
        if not isinstance(role, dict):
            continue
        asset = role.get("asset")
        if not asset:
            missing_assets.append(f"{role.get('id')}:missing-asset")
        elif require_assets and not Path(str(asset)).is_absolute() and not (root / str(asset)).exists():
            missing_assets.append(f"{role.get('id')}:{asset}")
    if missing_assets:
        issues.append(f"missing_assets={missing_assets!r}")
    if issues:
        return _generation_required(theme_id, set_id, "invalid-background-set", "background set failed preflight", issues=issues)
    return {
        "status": "ready",
        "theme_id": theme_id,
        "background_set_id": set_id,
        "source_manifest": str(source_path.relative_to(ROOT)).replace("\\", "/"),
        "source_theme": theme_ref or f"prompt_system/themes/{theme_id}.yaml",
        "seed": data.get("seed") or data.get("generation_seed"),
        "provenance": data.get("provenance") or {},
        "selection_basis": "explicit-background-set",
        "canvas": data.get("canvas"),
        "roles": roles,
        "background_set": data,
    }


def resolve_background_set(theme_id: str, background_set_id: str | None = None, runtime_manifest: str | Path | None = None, *, require_assets: bool = True, root: Path = ROOT) -> dict[str, Any]:
    """Resolve a Theme-compatible set or return generation-required state."""
    root = Path(root).resolve()
    set_dir = root / "prompt_system" / "pptx_background_sets"
    if runtime_manifest:
        runtime_path = Path(runtime_manifest)
        if not runtime_path.is_absolute():
            runtime_path = root / runtime_path
        if not runtime_path.exists():
            return _generation_required(theme_id, background_set_id, "runtime-manifest-missing", f"runtime manifest not found: {runtime_path}")
        data = _load(runtime_path)
        manifest_theme = str(data.get("theme_id") or "")
        if manifest_theme != theme_id:
            return _generation_required(theme_id, background_set_id, "runtime-manifest-theme-mismatch", "runtime manifest theme_id does not match requested theme", issues=[f"manifest.theme_id={manifest_theme!r}"])
        set_id = str(data.get("background_set_id") or background_set_id or theme_id)
        result = _validate_set(theme_id, set_id, runtime_path, data, require_assets=require_assets, root=root)
        result["selection_basis"] = "explicit-runtime-manifest"
        result["runtime_manifest"] = str(runtime_path.relative_to(root)).replace("\\", "/")
        return result

    candidates = sorted(set_dir.glob("*.yaml")) if set_dir.exists() else []
    if background_set_id:
        candidate = Path(background_set_id)
        if candidate.suffix.lower() not in {".yaml", ".yml"}:
            candidate = set_dir / f"{background_set_id}.yaml"
        elif not candidate.is_absolute():
            candidate = root / candidate
        if not candidate.exists():
            return _generation_required(theme_id, background_set_id, "explicit-set-missing", f"background set not found: {candidate}")
        return _validate_set(theme_id, candidate.stem, candidate, _load(candidate), require_assets=require_assets, root=root)

    matching = []
    for candidate in candidates:
        data = _load(candidate)
        if data.get("theme_id") == theme_id:
            matching.append((candidate, data))
    if not matching:
        return _generation_required(theme_id, None, "no-theme-compatible-set", "no background set exists for this Theme")
    if len(matching) > 1:
        return _generation_required(theme_id, None, "ambiguous-theme-compatible-sets", "more than one Theme-compatible set exists; explicit background_set_id is required", issues=[str(path) for path, _ in matching])
    candidate, data = matching[0]
    return _validate_set(theme_id, candidate.stem, candidate, data, require_assets=require_assets, root=root)
