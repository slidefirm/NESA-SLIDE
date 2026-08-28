#!/usr/bin/env python3
"""Render the fixed v6 18-Preset cohort through the formal new-deck renderer.

This runner is intentionally orchestration-only.  It validates a generated
batch plan, invokes ``render_randomized_html_demo.py`` once per Preset, and
records a portable render ledger.  It does not repair catalogs, rewrite the
plan, patch generated HTML, or delete partial output after a failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORMAL_RENDERER = PROJECT_ROOT / "scripts" / "render_randomized_html_demo.py"
CANONICAL_EDITOR = PROJECT_ROOT / "src" / "html-editor" / "edit-mode.js"
COMPANION_EDITOR = PROJECT_ROOT / "artifacts" / "html-test" / "edit-mode.js"
LEDGER_NAME = "render-ledger.json"
ASSET_POLICY = "pattern-only"
CONTENT_MODE = "new-deck"
DEFAULT_SEED_BASE = 2026081301

EXPECTED_PRESET_IDS = (
    "line-argument-journal",
    "signal-route-atlas",
    "field-index-manual",
    "tide-signal-observatory",
    "craft-archive-editions",
    "incident-command-redline",
    "harbor-ribbon-program",
    "neighborhood-newsroom-proof",
    "scent-veil-launch",
    "restoration-blueprint-ledger",
    "ai-operations-signal",
    "brave-classroom-contours",
    "night-transit-wayfinding",
    "sepia-retail-case",
    "dark-ai-city",
    "dark-city-network-report",
    "clinical-evidence-atlas",
    "moonlit-herbarium-atlas",
)

WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
PATH_KEY_RE = re.compile(
    r"(?:path|file|output|source|entrypoint|contract|definition|manifest|html|"
    r"editor|renderer|sidecar|batch_plan|output_root|story_ref|renderer_args)",
    re.IGNORECASE,
)
FORMAL_THEME_CONTRACT_PATTERNS = (
    re.compile(
        r"HTML_PRESET_THEME_CATALOG\s*=\s*load_html_preset_theme_catalog\s*\(\s*\)"
    ),
    re.compile(
        r"PRESET_THEME_POOL\s*=\s*sorted\s*\(\s*HTML_PRESET_THEME_DEFINITIONS\s*\)"
    ),
    re.compile(r"THEME_POOL\s*=\s*BASE_THEME_POOL\s*\+\s*PRESET_THEME_POOL"),
    re.compile(
        r"parser\.add_argument\s*\(\s*[\"']--theme[\"']\s*,\s*choices\s*=\s*THEME_POOL\s*\)"
    ),
)


class BatchContractError(RuntimeError):
    """Raised when preflight or generated output violates the v6 contract."""


class RenderStepError(RuntimeError):
    """Raised when one formal renderer subprocess returns a failure."""

    def __init__(self, preset_id: str, returncode: int) -> None:
        super().__init__(f"{preset_id}: renderer returned exit code {returncode}")
        self.preset_id = preset_id
        self.returncode = returncode


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_root(path: Path) -> Path:
    return path.resolve()


def _require_repo_local(path: Path, *, project_root: Path, label: str) -> Path:
    root = _repo_root(project_root)
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise BatchContractError(f"{label} must stay inside the repository") from exc
    return resolved


def _portable(path: Path, *, project_root: Path) -> str:
    resolved = _require_repo_local(path, project_root=project_root, label="path")
    return resolved.relative_to(_repo_root(project_root)).as_posix()


def _resolve_plan_path(value: Any, *, project_root: Path, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise BatchContractError(f"{label} must be a non-empty repository-relative POSIX path")
    if value != value.strip():
        raise BatchContractError(f"{label} must not contain surrounding whitespace")
    if "\\" in value or value.startswith("file://") or WINDOWS_ABSOLUTE_RE.match(value):
        raise BatchContractError(f"{label} must be repository-relative POSIX")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or pure.as_posix() != value:
        raise BatchContractError(f"{label} must be a normalized repository-relative POSIX path")
    resolved = (project_root.resolve() / Path(*pure.parts)).resolve()
    return _require_repo_local(resolved, project_root=project_root, label=label)


def _is_path_key(label: str) -> bool:
    return bool(PATH_KEY_RE.search(label))


def _assert_portable_strings(value: Any, *, label: str) -> None:
    """Reject local absolute paths and Windows separators in path-valued fields."""

    if isinstance(value, dict):
        for key, child in value.items():
            _assert_portable_strings(child, label=f"{label}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _assert_portable_strings(child, label=f"{label}[{index}]")
        return
    if not isinstance(value, str):
        return
    text = value.strip()
    if text.startswith("file://") or text.startswith("\\\\") or WINDOWS_ABSOLUTE_RE.match(text):
        raise BatchContractError(f"absolute local path at {label}")
    if _is_path_key(label) and (text.startswith("/") or "\\" in text):
        raise BatchContractError(f"non-portable path at {label}")


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BatchContractError(f"unable to read {label}") from exc
    if not isinstance(value, dict):
        raise BatchContractError(f"{label} must contain a JSON object")
    return value


def _editor_hashes(canonical: Path, companion: Path) -> tuple[str, str]:
    if not canonical.is_file():
        raise BatchContractError("canonical editor is missing")
    if not companion.is_file():
        raise BatchContractError("companion editor is missing")
    return _sha256(canonical), _sha256(companion)


def _editor_snapshot(canonical: Path, companion: Path) -> str:
    canonical_hash, companion_hash = _editor_hashes(canonical, companion)
    if canonical_hash != companion_hash:
        raise BatchContractError("canonical and companion editor hashes differ")
    return canonical_hash


def _assert_editor_unchanged(canonical: Path, companion: Path, expected: str) -> None:
    canonical_hash, companion_hash = _editor_hashes(canonical, companion)
    if canonical_hash != companion_hash:
        raise BatchContractError("canonical and companion editor hashes diverged during the batch")
    if canonical_hash != expected:
        raise BatchContractError("editor hash changed during the batch")


def _load_canonical_preset_catalog() -> dict[str, Any]:
    if __package__:
        from .html_preset_themes import load_html_preset_theme_catalog
    else:
        from html_preset_themes import load_html_preset_theme_catalog

    return load_html_preset_theme_catalog()


def load_formal_renderer_accepted_preset_ids(
    renderer: Path = FORMAL_RENDERER,
    *,
    preset_catalog_loader: Callable[[], dict[str, Any]] | None = None,
) -> set[str]:
    """Read the formal contract and registry without importing or executing the renderer."""

    if not renderer.is_file():
        raise BatchContractError("formal renderer is missing")
    try:
        source = renderer.read_text(encoding="utf-8")
    except OSError as exc:
        raise BatchContractError("formal renderer contract could not be read") from exc
    if any(not pattern.search(source) for pattern in FORMAL_THEME_CONTRACT_PATTERNS):
        raise BatchContractError("formal renderer Preset theme contract has drifted")

    loader = preset_catalog_loader or _load_canonical_preset_catalog
    try:
        catalog = loader()
    except Exception as exc:
        raise BatchContractError("formal Preset registry could not be loaded") from exc
    themes = catalog.get("themes") if isinstance(catalog, dict) else None
    if not isinstance(themes, dict) or not themes or not all(
        isinstance(theme_id, str) and theme_id for theme_id in themes
    ):
        raise BatchContractError("formal Preset registry theme ids are invalid")
    return set(themes)


def _seed_for_entry(
    entry: dict[str, Any],
    *,
    index: int,
    plan: dict[str, Any],
) -> tuple[int, str]:
    if "seed" in entry:
        seed = entry["seed"]
        source = "plan-entry"
    else:
        seed_base = plan.get("seed_base", DEFAULT_SEED_BASE)
        if isinstance(seed_base, bool) or not isinstance(seed_base, int):
            raise BatchContractError("batch-plan seed_base must be an integer")
        seed = seed_base + index
        source = "plan-seed-base" if "seed_base" in plan else "v6-fixed-index-sequence"
    if isinstance(seed, bool) or not isinstance(seed, int) or not (0 <= seed <= 0xFFFFFFFF):
        raise BatchContractError("each Preset seed must be an unsigned 32-bit integer")
    return seed, source


def _validate_plan(
    *,
    batch_plan: Path,
    output_root: Path,
    project_root: Path,
    renderer: Path,
    accepted_themes: set[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    plan = _read_json(batch_plan, label="batch-plan")
    _assert_portable_strings(plan, label="batch-plan")

    if plan.get("content_mode") != CONTENT_MODE:
        raise BatchContractError("batch-plan content_mode must be new-deck")
    if plan.get("preset_demo") is not False:
        raise BatchContractError("batch-plan must explicitly disable preset-demo")
    if plan.get("preset_count") != len(EXPECTED_PRESET_IDS):
        raise BatchContractError("batch-plan preset_count must be exactly 18")

    batch_plan_ref = _resolve_plan_path(
        plan.get("batch_plan_file"),
        project_root=project_root,
        label="batch-plan.batch_plan_file",
    )
    if batch_plan_ref != batch_plan:
        raise BatchContractError("batch-plan batch_plan_file does not name itself")
    plan_output_root = _resolve_plan_path(
        plan.get("output_root"),
        project_root=project_root,
        label="batch-plan.output_root",
    )
    if plan_output_root != output_root:
        raise BatchContractError("batch-plan output_root differs from --output-root")
    if tuple(plan.get("preset_cohort") or ()) != EXPECTED_PRESET_IDS:
        raise BatchContractError("batch-plan preset_cohort differs from the fixed v6 18")

    renderer_ref = _resolve_plan_path(
        plan.get("renderer"), project_root=project_root, label="batch-plan.renderer"
    )
    if renderer_ref != renderer.resolve():
        raise BatchContractError("batch-plan must name the formal renderer entrypoint")

    rows = plan.get("presets")
    if not isinstance(rows, list) or len(rows) != len(EXPECTED_PRESET_IDS):
        raise BatchContractError("batch-plan must contain exactly 18 Preset entries")
    if not all(isinstance(row, dict) for row in rows):
        raise BatchContractError("every batch-plan Preset entry must be an object")

    preset_ids = tuple(row.get("preset_id") for row in rows)
    if preset_ids != EXPECTED_PRESET_IDS:
        raise BatchContractError("batch-plan Preset cohort or order differs from the fixed v6 18")
    missing_themes = [preset_id for preset_id in preset_ids if preset_id not in accepted_themes]
    if missing_themes:
        raise BatchContractError(
            "formal renderer does not accept every v6 Preset: " + ", ".join(missing_themes)
        )

    entries: list[dict[str, Any]] = []
    output_paths: set[Path] = set()
    output_parents: set[Path] = set()
    for index, row in enumerate(rows):
        preset_id = EXPECTED_PRESET_IDS[index]
        if row.get("content_mode", CONTENT_MODE) != CONTENT_MODE:
            raise BatchContractError(f"{preset_id}: entry content_mode must be new-deck")
        if row.get("preset_demo", False) is not False:
            raise BatchContractError(f"{preset_id}: entry must not enable preset-demo")

        story_file = _resolve_plan_path(
            row.get("story_file"), project_root=project_root, label=f"{preset_id}.story_file"
        )
        art_direction_file = _resolve_plan_path(
            row.get("art_direction_file"),
            project_root=project_root,
            label=f"{preset_id}.art_direction_file",
        )
        output_html = _resolve_plan_path(
            row.get("output_html"), project_root=project_root, label=f"{preset_id}.output_html"
        )
        if not story_file.is_file():
            raise BatchContractError(f"{preset_id}: story_file is missing")
        if story_file.suffix.lower() != ".json":
            raise BatchContractError(f"{preset_id}: story_file must be JSON")
        if not art_direction_file.is_file():
            raise BatchContractError(f"{preset_id}: art_direction_file is missing")
        if art_direction_file.suffix.lower() not in {".yaml", ".yml"}:
            raise BatchContractError(f"{preset_id}: art_direction_file must be YAML")
        if output_html.suffix.lower() != ".html":
            raise BatchContractError(f"{preset_id}: output_html must end in .html")
        try:
            output_html.relative_to(output_root)
        except ValueError as exc:
            raise BatchContractError(f"{preset_id}: output_html must stay under --output-root") from exc

        layouts = row.get("layouts")
        if (
            not isinstance(layouts, list)
            or not layouts
            or not all(isinstance(layout, str) and layout.strip() == layout for layout in layouts)
        ):
            raise BatchContractError(f"{preset_id}: layouts must be a non-empty string list")
        if any(not layout for layout in layouts):
            raise BatchContractError(f"{preset_id}: layouts must not contain empty ids")

        seed, seed_source = _seed_for_entry(row, index=index, plan=plan)
        manifest = output_html.with_suffix(".manifest.json")
        editor_sidecar = output_html.parent / "edit-mode.js"
        if output_html in output_paths:
            raise BatchContractError(f"{preset_id}: duplicate output_html")
        if output_html.parent in output_parents:
            raise BatchContractError(f"{preset_id}: each Preset must use a distinct output directory")
        output_paths.add(output_html)
        output_parents.add(output_html.parent)
        for target in (output_html, manifest, editor_sidecar):
            if target.exists():
                raise BatchContractError(f"{preset_id}: refusing to overwrite an existing output")

        entries.append(
            {
                "index": index + 1,
                "preset_id": preset_id,
                "seed": seed,
                "seed_source": seed_source,
                "story_file": story_file,
                "art_direction_file": art_direction_file,
                "layouts": list(layouts),
                "output_html": output_html,
                "output_manifest": manifest,
                "editor_sidecar": editor_sidecar,
            }
        )
    return plan, entries


def _renderer_args(entry: dict[str, Any], *, project_root: Path) -> list[str]:
    """Return the portable formal arguments recorded in the render ledger."""

    return [
        "--output",
        _portable(entry["output_html"], project_root=project_root),
        "--seed",
        str(entry["seed"]),
        "--theme",
        entry["preset_id"],
        "--story-file",
        _portable(entry["story_file"], project_root=project_root),
        "--layouts",
        ",".join(entry["layouts"]),
        "--art-direction",
        _portable(entry["art_direction_file"], project_root=project_root),
        "--content-mode",
        CONTENT_MODE,
        "--asset-policy",
        ASSET_POLICY,
    ]


def _subprocess_command(entry: dict[str, Any], *, renderer: Path) -> list[str]:
    return [
        sys.executable,
        str(renderer),
        "--output",
        str(entry["output_html"]),
        "--seed",
        str(entry["seed"]),
        "--theme",
        entry["preset_id"],
        "--story-file",
        str(entry["story_file"]),
        "--layouts",
        ",".join(entry["layouts"]),
        "--art-direction",
        str(entry["art_direction_file"]),
        "--content-mode",
        CONTENT_MODE,
        "--asset-policy",
        ASSET_POLICY,
    ]


def _validate_manifest(
    entry: dict[str, Any],
    *,
    editor_hash: str,
    project_root: Path,
) -> dict[str, str]:
    preset_id = entry["preset_id"]
    output_html: Path = entry["output_html"]
    manifest_path: Path = entry["output_manifest"]
    editor_sidecar: Path = entry["editor_sidecar"]
    if not output_html.is_file():
        raise BatchContractError(f"{preset_id}: renderer did not create output_html")
    if not manifest_path.is_file():
        raise BatchContractError(f"{preset_id}: renderer did not create its manifest")
    if not editor_sidecar.is_file() or _sha256(editor_sidecar) != editor_hash:
        raise BatchContractError(f"{preset_id}: generated editor sidecar hash mismatch")

    manifest = _read_json(manifest_path, label=f"{preset_id} manifest")
    _assert_portable_strings(manifest, label=f"manifest.{preset_id}")
    if manifest.get("content_mode") != CONTENT_MODE:
        raise BatchContractError(f"{preset_id}: manifest content_mode mismatch")
    if "example_reference" in manifest:
        raise BatchContractError(f"{preset_id}: preset-demo provenance leaked into manifest")
    if manifest.get("theme", {}).get("id") != preset_id:
        raise BatchContractError(f"{preset_id}: manifest theme id mismatch")
    preset_manifest = manifest.get("preset_theme")
    if not isinstance(preset_manifest, dict) or preset_manifest.get("id") != preset_id:
        raise BatchContractError(f"{preset_id}: manifest Preset id mismatch")
    if preset_manifest.get("legacy_case_imported") is not False:
        raise BatchContractError(f"{preset_id}: manifest imported a legacy Preset case")
    if preset_manifest.get("css_owner") != "preset-appearance":
        raise BatchContractError(f"{preset_id}: manifest did not use preset-appearance")
    if preset_manifest.get("raster_assets") != []:
        raise BatchContractError(f"{preset_id}: renderer attached a raster asset before background work")
    if manifest.get("seed") != entry["seed"]:
        raise BatchContractError(f"{preset_id}: manifest seed mismatch")
    if manifest.get("layouts") != entry["layouts"]:
        raise BatchContractError(f"{preset_id}: manifest Layout sequence mismatch")
    if manifest.get("editable_dom", {}).get("editor_sha256") != editor_hash:
        raise BatchContractError(f"{preset_id}: manifest editor hash mismatch")
    layout_media = manifest.get("layout_media")
    if not isinstance(layout_media, dict) or layout_media.get("asset_policy") != ASSET_POLICY:
        raise BatchContractError(f"{preset_id}: manifest asset policy mismatch")
    if layout_media.get("eligible_media_requirements") != ["no-image"]:
        raise BatchContractError(f"{preset_id}: manifest pattern-only eligibility mismatch")
    expected_requirements = {layout_id: "no-image" for layout_id in entry["layouts"]}
    if layout_media.get("layout_media_requirements") != expected_requirements:
        raise BatchContractError(f"{preset_id}: manifest includes an image-required Layout")
    media_counts = layout_media.get("counts")
    if not isinstance(media_counts, dict) or (
        media_counts.get("no-image") != len(entry["layouts"])
        or media_counts.get("with-image") != 0
    ):
        raise BatchContractError(f"{preset_id}: manifest media counts mismatch")
    if manifest.get("output") != _portable(output_html, project_root=project_root):
        raise BatchContractError(f"{preset_id}: manifest output path mismatch")

    return {
        "content_mode": "pass",
        "preset_id": "pass",
        "seed": "pass",
        "layout_sequence": "pass",
        "editor_hash": "pass",
        "portable_paths": "pass",
        "pattern_only": "pass",
        "no_image_layouts": "pass",
        "no_renderer_raster": "pass",
        "no_demo_provenance": "pass",
    }


def _build_ledger(
    *,
    batch_plan: Path,
    output_root: Path,
    renderer: Path,
    renderer_hash: str,
    canonical_editor: Path,
    companion_editor: Path,
    editor_hash: str,
    entries: Sequence[dict[str, Any]],
    project_root: Path,
) -> dict[str, Any]:
    started_at = _utc_now()
    records = []
    for entry in entries:
        records.append(
            {
                "index": entry["index"],
                "preset_id": entry["preset_id"],
                "status": "pending",
                "seed": entry["seed"],
                "seed_source": entry["seed_source"],
                "story_file": _portable(entry["story_file"], project_root=project_root),
                "art_direction_file": _portable(
                    entry["art_direction_file"], project_root=project_root
                ),
                "layouts": list(entry["layouts"]),
                "output_html": _portable(entry["output_html"], project_root=project_root),
                "output_manifest": _portable(
                    entry["output_manifest"], project_root=project_root
                ),
                "editor_sidecar": _portable(entry["editor_sidecar"], project_root=project_root),
                "renderer_args": _renderer_args(entry, project_root=project_root),
                "checks": {},
            }
        )
    return {
        "schema_version": 1,
        "id": "html-preset-regeneration-20260813-v6-formal-new-deck-render",
        "mode": "write",
        "status": "running",
        "content_mode": CONTENT_MODE,
        "asset_policy": ASSET_POLICY,
        "preset_count": len(entries),
        "completed_count": 0,
        "failed_count": 0,
        "not_run_count": len(entries),
        "started_at": started_at,
        "updated_at": started_at,
        "batch_plan": _portable(batch_plan, project_root=project_root),
        "output_root": _portable(output_root, project_root=project_root),
        "renderer": {
            "entrypoint": _portable(renderer, project_root=project_root),
            "sha256": renderer_hash,
            "python": "current-interpreter",
        },
        "editor": {
            "canonical": _portable(canonical_editor, project_root=project_root),
            "companion": _portable(companion_editor, project_root=project_root),
            "before_sha256": editor_hash,
            "canonical_after_sha256": None,
            "companion_after_sha256": None,
        },
        "records": records,
        "failure": None,
    }


def _update_counts(ledger: dict[str, Any]) -> None:
    statuses = [record["status"] for record in ledger["records"]]
    ledger["completed_count"] = statuses.count("completed")
    ledger["failed_count"] = statuses.count("failed")
    ledger["not_run_count"] = statuses.count("pending") + statuses.count("not-run")
    ledger["updated_at"] = _utc_now()


def _write_ledger(path: Path, ledger: dict[str, Any]) -> None:
    _assert_portable_strings(ledger, label="render-ledger")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _safe_editor_after(canonical: Path, companion: Path) -> tuple[str | None, str | None]:
    canonical_hash = _sha256(canonical) if canonical.is_file() else None
    companion_hash = _sha256(companion) if companion.is_file() else None
    return canonical_hash, companion_hash


def _failure_code(exc: Exception) -> str:
    if isinstance(exc, RenderStepError):
        return "renderer-failed"
    if isinstance(exc, BatchContractError):
        return "contract-failed"
    return "unexpected-failure"


def run_batch(
    *,
    batch_plan: Path,
    output_root: Path,
    write: bool,
    project_root: Path = PROJECT_ROOT,
    renderer: Path = FORMAL_RENDERER,
    canonical_editor: Path = CANONICAL_EDITOR,
    companion_editor: Path = COMPANION_EDITOR,
    accepted_themes: Iterable[str] | None = None,
    preset_catalog_loader: Callable[[], dict[str, Any]] | None = None,
    process_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    """Validate or render one fixed v6 batch.

    ``write=False`` is a read-only preflight.  ``write=True`` writes a ledger
    before the first renderer call and keeps all successful output on failure.
    """

    project_root = project_root.resolve()
    batch_plan = _require_repo_local(
        batch_plan, project_root=project_root, label="--batch-plan"
    )
    output_root = _require_repo_local(
        output_root, project_root=project_root, label="--output-root"
    )
    renderer = _require_repo_local(renderer, project_root=project_root, label="formal renderer")
    canonical_editor = _require_repo_local(
        canonical_editor, project_root=project_root, label="canonical editor"
    )
    companion_editor = _require_repo_local(
        companion_editor, project_root=project_root, label="companion editor"
    )
    if output_root == project_root:
        raise BatchContractError("--output-root must not be the repository root")
    if not batch_plan.is_file():
        raise BatchContractError("--batch-plan does not exist")
    if not renderer.is_file():
        raise BatchContractError("formal renderer does not exist")

    ledger_path = output_root / LEDGER_NAME
    if ledger_path.exists():
        raise BatchContractError("refusing to overwrite an existing render-ledger.json")

    editor_hash = _editor_snapshot(canonical_editor, companion_editor)
    renderer_hash = _sha256(renderer)
    accepted = (
        set(accepted_themes)
        if accepted_themes is not None
        else load_formal_renderer_accepted_preset_ids(
            renderer,
            preset_catalog_loader=preset_catalog_loader,
        )
    )
    plan, entries = _validate_plan(
        batch_plan=batch_plan,
        output_root=output_root,
        project_root=project_root,
        renderer=renderer,
        accepted_themes=accepted,
    )

    if not write:
        result = {
            "schema_version": 1,
            "mode": "check",
            "status": "pass",
            "content_mode": CONTENT_MODE,
            "asset_policy": ASSET_POLICY,
            "preset_count": len(entries),
            "batch_plan": _portable(batch_plan, project_root=project_root),
            "output_root": _portable(output_root, project_root=project_root),
            "renderer": {
                "entrypoint": _portable(renderer, project_root=project_root),
                "sha256": renderer_hash,
            },
            "editor": {
                "canonical": _portable(canonical_editor, project_root=project_root),
                "companion": _portable(companion_editor, project_root=project_root),
                "sha256": editor_hash,
            },
            "preset_ids": [entry["preset_id"] for entry in entries],
            "render_ledger": _portable(ledger_path, project_root=project_root),
        }
        _assert_portable_strings(result, label="check-result")
        return result

    del plan  # The validated plan is represented by portable per-record inputs below.
    ledger = _build_ledger(
        batch_plan=batch_plan,
        output_root=output_root,
        renderer=renderer,
        renderer_hash=renderer_hash,
        canonical_editor=canonical_editor,
        companion_editor=companion_editor,
        editor_hash=editor_hash,
        entries=entries,
        project_root=project_root,
    )
    _write_ledger(ledger_path, ledger)
    runner = process_runner or subprocess.run
    current_index: int | None = None

    try:
        for index, entry in enumerate(entries):
            current_index = index
            record = ledger["records"][index]
            _assert_editor_unchanged(canonical_editor, companion_editor, editor_hash)
            command = _subprocess_command(entry, renderer=renderer)
            if "--preset-demo" in command or "--style-case" in command:
                raise BatchContractError("demo flags are forbidden in the formal v6 runner")
            completed = runner(
                command,
                cwd=str(project_root),
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if completed.returncode != 0:
                raise RenderStepError(entry["preset_id"], completed.returncode)
            _assert_editor_unchanged(canonical_editor, companion_editor, editor_hash)
            checks = _validate_manifest(
                entry, editor_hash=editor_hash, project_root=project_root
            )
            _assert_editor_unchanged(canonical_editor, companion_editor, editor_hash)
            record.update(
                {
                    "status": "completed",
                    "checks": checks,
                    "output_html_sha256": _sha256(entry["output_html"]),
                    "output_manifest_sha256": _sha256(entry["output_manifest"]),
                    "editor_sidecar_sha256": _sha256(entry["editor_sidecar"]),
                }
            )
            _update_counts(ledger)
            _write_ledger(ledger_path, ledger)

        current_index = None
        _assert_editor_unchanged(canonical_editor, companion_editor, editor_hash)
        canonical_after, companion_after = _editor_hashes(canonical_editor, companion_editor)
        ledger["editor"]["canonical_after_sha256"] = canonical_after
        ledger["editor"]["companion_after_sha256"] = companion_after
        ledger["status"] = "complete"
        ledger["failure"] = None
        _update_counts(ledger)
        _write_ledger(ledger_path, ledger)
        return ledger
    except Exception as exc:
        if current_index is not None:
            failed_record = ledger["records"][current_index]
            if failed_record["status"] == "pending":
                failed_record["status"] = "failed"
                failed_record["checks"] = {"batch_step": "fail"}
            for record in ledger["records"][current_index + 1 :]:
                if record["status"] == "pending":
                    record["status"] = "not-run"
        canonical_after, companion_after = _safe_editor_after(canonical_editor, companion_editor)
        ledger["editor"]["canonical_after_sha256"] = canonical_after
        ledger["editor"]["companion_after_sha256"] = companion_after
        ledger["status"] = "partial"
        ledger["failure"] = {
            "code": _failure_code(exc),
            "preset_id": (
                entries[current_index]["preset_id"] if current_index is not None else None
            ),
            "detail": exc.__class__.__name__,
        }
        _update_counts(ledger)
        _write_ledger(ledger_path, ledger)
        return ledger


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate or render the fixed formal v6 18-Preset new-deck batch."
    )
    parser.add_argument("--batch-plan", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Read-only preflight; do not invoke renderer")
    mode.add_argument("--write", action="store_true", help="Run formal renderer and write render-ledger.json")
    args = parser.parse_args(argv)

    try:
        result = run_batch(
            batch_plan=args.batch_plan,
            output_root=args.output_root,
            write=args.write,
        )
    except BatchContractError as exc:
        print(
            json.dumps(
                {"status": "preflight-failed", "error": str(exc)},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"pass", "complete"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
