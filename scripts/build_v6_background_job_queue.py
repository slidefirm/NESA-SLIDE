"""Build and validate the v6 per-slide image-background production queue.

The batch plan is the only deck inventory.  Every plan entry must point to a
formal reusable-Preset/new-deck HTML and manifest pair.  Slide totals are read
from those artifacts; no page count or authored/core directory split is baked
into this helper.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
V6_RELATIVE_ROOT = Path(
    "artifacts/experiments/html-image-background/"
    "html-preset-regeneration-20260813-v6"
)
DEFAULT_OUTPUT = V6_RELATIVE_ROOT / "job-queue.json"
DEFAULT_EDITOR = Path("src/html-editor/edit-mode.js")
DEFAULT_PRESET_CATALOG = Path("prompt_system/presets/catalog.yaml")

EXPECTED_PRESET_COUNT = 18
SHARD_COUNT = 6
FORMAL_RENDERER = "scripts/render_randomized_html_demo.py"
SCHEMA_VERSION = "html-image-background-v6-job-queue-v2"

WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
EMBEDDED_EDITOR_RE = re.compile(
    r"<script\b(?P<attrs>[^>]*)>(?P<body>.*?)</script\s*>",
    re.IGNORECASE | re.DOTALL,
)
EDITOR_ATTRIBUTE_RE = re.compile(
    r"\bdata-edit-mode-embedded\s*=\s*(['\"])true\1", re.IGNORECASE
)


class QueueValidationError(ValueError):
    """Raised when the production queue cannot be proven complete/current."""

    def __init__(self, errors: Iterable[str]):
        self.errors = list(dict.fromkeys(str(row) for row in errors if str(row)))
        if not self.errors:
            self.errors = ["unknown queue validation error"]
        super().__init__("\n".join(self.errors))


class _SlideParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.slides: list[dict[str, str | None]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.lower() != "section":
            return
        values = {str(key).lower(): value for key, value in attrs}
        if "slide" not in set((values.get("class") or "").split()):
            return
        self.slides.append(
            {
                "id": values.get("id"),
                "index": values.get("data-index"),
                "page_number": values.get("data-page-number"),
                "page_count": values.get("data-page-count"),
                "layout_id": values.get("data-layout-id"),
                "scene_role": values.get("data-scene-role"),
                "production_family": values.get("data-production-family"),
            }
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_if_file(path: Path) -> str | None:
    return _sha256(path) if path.is_file() else None


def _validate_repo_relative_posix(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QueueValidationError([f"{label} must be a non-empty path string"])
    raw = value.strip()
    if (
        raw.startswith(("/", "\\", "file://"))
        or WINDOWS_ABSOLUTE_RE.match(raw)
        or "\\" in raw
    ):
        raise QueueValidationError(
            [f"{label} must be repo-relative POSIX, got: {value}"]
        )
    pure = PurePosixPath(raw)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise QueueValidationError(
            [f"{label} must be repo-relative POSIX without traversal: {value}"]
        )
    return raw


def _repo_relative(path: Path, repo_root: Path, label: str) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise QueueValidationError(
            [f"{label} escapes repository root: {resolved}"]
        ) from exc
    return _validate_repo_relative_posix(relative.as_posix(), label)


def _resolve_repo_path(repo_root: Path, value: str | Path, label: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        path = candidate.resolve()
        _repo_relative(path, repo_root, label)
        return path
    portable = _validate_repo_relative_posix(str(value), label)
    path = (repo_root / PurePosixPath(portable)).resolve()
    _repo_relative(path, repo_root, label)
    return path


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise QueueValidationError([f"invalid {label}: {path}: {exc}"]) from exc
    if not isinstance(payload, dict):
        raise QueueValidationError([f"{label} must contain a JSON object: {path}"])
    return payload


def _reject_absolute_strings(payload: Any, label: str) -> list[str]:
    """Reject absolute/Windows paths anywhere in a tracked plan or manifest."""

    errors: list[str] = []

    def visit(value: Any, trail: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                visit(child, f"{trail}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{trail}[{index}]")
        elif isinstance(value, str):
            stripped = value.strip()
            if (
                stripped.startswith(("/", "\\", "file://"))
                or WINDOWS_ABSOLUTE_RE.match(stripped)
                or "\\" in stripped
            ):
                errors.append(f"absolute/non-POSIX path in {label} at {trail}: {value}")

    visit(payload, label)
    return errors


def _load_reusable_preset_ids(catalog_path: Path) -> set[str]:
    try:
        payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise QueueValidationError(
            [f"invalid Preset catalog: {catalog_path}: {exc}"]
        ) from exc
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise QueueValidationError([f"Preset catalog entries must be an array: {catalog_path}"])
    reusable: set[str] = set()
    for row in entries:
        if not isinstance(row, dict):
            continue
        preset = str(row.get("id") or "").strip()
        capabilities = set(row.get("capabilities") or [])
        if preset and "reusable-preset" in capabilities:
            reusable.add(preset)
    if not reusable:
        raise QueueValidationError([f"Preset catalog has no reusable Presets: {catalog_path}"])
    return reusable


def _coalesced_field(
    row: dict[str, Any], names: tuple[str, ...], label: str, errors: list[str]
) -> Any:
    present = [(name, row.get(name)) for name in names if row.get(name) is not None]
    if not present:
        errors.append(f"missing {label}; expected one of {list(names)}")
        return None
    values = {json.dumps(value, sort_keys=True, ensure_ascii=False) for _, value in present}
    if len(values) > 1:
        errors.append(f"conflicting {label}: {present}")
        return None
    return present[0][1]


def _batch_rows(batch_plan: dict[str, Any], errors: list[str]) -> list[dict[str, Any]]:
    candidates = [
        (key, batch_plan.get(key))
        for key in ("presets", "results")
        if batch_plan.get(key) is not None
    ]
    if len(candidates) != 1 or not isinstance(candidates[0][1], list):
        errors.append("batch plan must contain exactly one presets/results array")
        return []
    return candidates[0][1]


def _renderer_entrypoint(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("entrypoint"), str):
        return value["entrypoint"]
    return None


def _parse_slides(html: str, preset: str, errors: list[str]) -> list[dict[str, Any]]:
    parser = _SlideParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:  # fail closed on malformed generated HTML
        errors.append(f"cannot parse HTML slides for {preset}: {exc}")
        return []

    slides: list[dict[str, Any]] = []
    indices: list[int] = []
    ids: list[str] = []
    for position, raw in enumerate(parser.slides):
        try:
            index = int(raw.get("index"))
        except (TypeError, ValueError):
            errors.append(f"{preset} slide at DOM position {position} has invalid data-index")
            continue
        slide_id = str(raw.get("id") or "")
        if not slide_id:
            errors.append(f"{preset} slide index {index} is missing id")
        indices.append(index)
        ids.append(slide_id)
        slides.append({**raw, "index": index, "id": slide_id})

    duplicate_indices = sorted({value for value in indices if indices.count(value) > 1})
    duplicate_ids = sorted({value for value in ids if value and ids.count(value) > 1})
    if duplicate_indices:
        errors.append(f"duplicate page indices in {preset}: {duplicate_indices}")
    if duplicate_ids:
        errors.append(f"duplicate page ids in {preset}: {duplicate_ids}")
    if not slides:
        errors.append(f"HTML contains no slides for {preset}")
        return []

    expected_indices = set(range(len(slides)))
    actual_indices = set(indices)
    missing = sorted(expected_indices - actual_indices)
    extra = sorted(actual_indices - expected_indices)
    if missing:
        errors.append(f"missing page indices in {preset}: {missing}")
    if extra:
        errors.append(f"unexpected page indices in {preset}: {extra}")

    count = len(slides)
    for slide in slides:
        index = int(slide["index"])
        try:
            page_number = int(slide.get("page_number"))
            page_count = int(slide.get("page_count"))
        except (TypeError, ValueError):
            errors.append(f"{preset} slide {index} has invalid page-number/page-count")
            continue
        if page_number != index + 1:
            errors.append(
                f"{preset} slide {index} page number must be {index + 1}, got {page_number}"
            )
        if page_count != count:
            errors.append(
                f"{preset} slide {index} page count must be {count}, got {page_count}"
            )
    return sorted(slides, key=lambda row: int(row["index"]))


def _extract_embedded_editor(html: str, preset: str) -> str:
    matches = [
        match.group("body")
        for match in EMBEDDED_EDITOR_RE.finditer(html)
        if EDITOR_ATTRIBUTE_RE.search(match.group("attrs"))
    ]
    if len(matches) != 1:
        raise QueueValidationError(
            [f"{preset} must contain exactly one embedded editor; found {len(matches)}"]
        )
    return matches[0]


def _manifest_preset_id(manifest: dict[str, Any]) -> tuple[str | None, str | None]:
    preset_theme = manifest.get("preset_theme")
    theme = manifest.get("theme")
    preset_id = (
        str(preset_theme.get("id"))
        if isinstance(preset_theme, dict) and preset_theme.get("id")
        else str(theme.get("id"))
        if isinstance(theme, dict) and theme.get("id")
        else None
    )
    theme_kind = str(theme.get("kind")) if isinstance(theme, dict) and theme.get("kind") else None
    return preset_id, theme_kind


def _scene_role(
    manifest: dict[str, Any], index: int, slide: dict[str, Any]
) -> str | None:
    pages = manifest.get("content_pages")
    if isinstance(pages, list) and index < len(pages):
        row = pages[index]
        if isinstance(row, dict) and row.get("intent"):
            return str(row["intent"])
    architecture = manifest.get("architecture")
    if isinstance(architecture, list) and index < len(architecture) and architecture[index]:
        return str(architecture[index])
    decisions = manifest.get("layout_decisions") or manifest.get("design_decisions")
    if isinstance(decisions, list) and index < len(decisions):
        row = decisions[index]
        if isinstance(row, dict):
            for key in ("intent", "composition", "scene_role"):
                if row.get(key):
                    return str(row[key])
    return (
        str(slide.get("scene_role"))
        if slide.get("scene_role")
        else str(slide.get("production_family"))
        if slide.get("production_family")
        else None
    )


def _assign_shards(decks: list[dict[str, Any]]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    loads = [0] * SHARD_COUNT
    members: list[list[str]] = [[] for _ in range(SHARD_COUNT)]
    assignment: dict[str, str] = {}
    for deck in sorted(decks, key=lambda row: (-row["slide_count"], row["preset"])):
        index = min(range(SHARD_COUNT), key=lambda value: (loads[value], value))
        shard_id = f"shard-{index + 1:02d}"
        assignment[deck["preset"]] = shard_id
        loads[index] += deck["slide_count"]
        members[index].append(deck["preset"])
    shards = [
        {
            "id": f"shard-{index + 1:02d}",
            "preset_count": len(members[index]),
            "slide_count": loads[index],
            "presets": sorted(members[index]),
        }
        for index in range(SHARD_COUNT)
    ]
    return assignment, shards


def _job_paths(
    repo_root: Path, v6_root: Path, preset: str, number: int
) -> tuple[dict[str, str], dict[str, str | None]]:
    run_dir = v6_root / preset
    files = {
        "reference_screenshot": (
            run_dir / "references" / f"slide-{number:03d}-clean-foreground.png"
        ),
        "protected_mask": run_dir / "masks" / f"protected-mask-{number:03d}.png",
        "prompt": run_dir / "prompts" / f"slide-{number:03d}-imagegen-prompt.txt",
        "model_output": run_dir / "model-output" / f"slide-{number:03d}.png",
        "final_background": run_dir / "backgrounds" / f"slide-{number:03d}.png",
        "final_html": run_dir / "final.html",
        "qa_report": run_dir / "qa" / f"slide-{number:03d}-image-background.json",
        "run_manifest": run_dir / "run.json",
    }
    paths = {
        name: _repo_relative(path, repo_root, name) for name, path in files.items()
    }
    hashes = {f"{name}_sha256": _hash_if_file(path) for name, path in files.items()}
    return paths, hashes


def _validate_plan_row_paths(
    row: dict[str, Any], position: int, errors: list[str]
) -> tuple[str | None, str | None, str | None]:
    preset = _coalesced_field(
        row, ("preset_id", "preset"), f"preset id at batch row {position}", errors
    )
    html = _coalesced_field(
        row,
        ("output_html", "html"),
        f"output HTML at batch row {position}",
        errors,
    )
    manifest = row.get("output_manifest", row.get("manifest"))
    if manifest is None and isinstance(html, str) and html.strip():
        html_path = PurePosixPath(html.strip())
        manifest = str(html_path.with_suffix(".manifest.json"))
    if preset is not None and (not isinstance(preset, str) or not preset.strip()):
        errors.append(f"invalid preset id at batch row {position}: {preset!r}")
        preset = None
    for value, label in (
        (html, f"batch output HTML at row {position}"),
        (manifest, f"batch output manifest at row {position}"),
    ):
        if value is not None:
            try:
                _validate_repo_relative_posix(value, label)
            except QueueValidationError as exc:
                errors.extend(exc.errors)
    return (
        str(preset).strip() if preset is not None else None,
        str(html) if html is not None else None,
        str(manifest) if manifest is not None else None,
    )


def build_job_queue(
    *,
    batch_plan_path: Path,
    repo_root: Path = REPO_ROOT,
    v6_root: Path | None = None,
    editor_path: Path | None = None,
    preset_catalog_path: Path | None = None,
) -> dict[str, Any]:
    """Return a validated dynamic queue or raise ``QueueValidationError``."""

    repo_root = repo_root.resolve()
    batch_plan_path = batch_plan_path.resolve()
    v6_root = (v6_root or repo_root / V6_RELATIVE_ROOT).resolve()
    editor_path = (editor_path or repo_root / DEFAULT_EDITOR).resolve()
    preset_catalog_path = (
        preset_catalog_path or repo_root / DEFAULT_PRESET_CATALOG
    ).resolve()

    errors: list[str] = []
    for label, path in (
        ("batch plan", batch_plan_path),
        ("v6 root", v6_root),
        ("canonical editor", editor_path),
        ("Preset catalog", preset_catalog_path),
    ):
        try:
            _repo_relative(path, repo_root, label)
        except QueueValidationError as exc:
            errors.extend(exc.errors)
    for label, path in (
        ("batch plan", batch_plan_path),
        ("canonical editor", editor_path),
        ("Preset catalog", preset_catalog_path),
    ):
        if not path.is_file():
            errors.append(f"missing {label}: {path}")
    if errors:
        raise QueueValidationError(errors)

    batch_plan = _load_json(batch_plan_path, "batch plan")
    errors.extend(_reject_absolute_strings(batch_plan, "batch plan"))
    if batch_plan.get("content_mode") != "new-deck":
        errors.append(
            f"batch plan content_mode must be new-deck, got {batch_plan.get('content_mode')!r}"
        )
    if batch_plan.get("preset_demo") not in (None, False):
        errors.append("batch plan preset_demo must be false")
    plan_renderer = _renderer_entrypoint(
        batch_plan.get("renderer_entrypoint", batch_plan.get("renderer"))
    )
    if plan_renderer is not None and plan_renderer != FORMAL_RENDERER:
        errors.append(
            f"batch plan renderer must be {FORMAL_RENDERER}, got {plan_renderer}"
        )

    rows = _batch_rows(batch_plan, errors)
    if len(rows) != EXPECTED_PRESET_COUNT:
        errors.append(
            f"batch plan must contain exactly {EXPECTED_PRESET_COUNT} Presets, got {len(rows)}"
        )
    if batch_plan.get("preset_count") not in (None, EXPECTED_PRESET_COUNT):
        errors.append(
            f"batch plan preset_count must be {EXPECTED_PRESET_COUNT}, "
            f"got {batch_plan.get('preset_count')}"
        )

    reusable_ids = _load_reusable_preset_ids(preset_catalog_path)
    canonical_editor_text = editor_path.read_text(encoding="utf-8")
    canonical_editor_sha = _sha256(editor_path)
    expected_embedded_editor = canonical_editor_text.replace("</script", "<\\/script")
    expected_embedded_sha = _sha256_text(expected_embedded_editor)

    plan_entries: list[dict[str, Any]] = []
    preset_ids: list[str] = []
    html_paths: list[str] = []
    manifest_paths: list[str] = []
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"batch plan row {position} must be an object")
            continue
        preset, html_relative, manifest_relative = _validate_plan_row_paths(
            row, position, errors
        )
        if not preset or not html_relative or not manifest_relative:
            continue
        preset_ids.append(preset)
        html_paths.append(html_relative)
        manifest_paths.append(manifest_relative)
        if preset not in reusable_ids:
            errors.append(f"unknown or non-reusable Preset in batch plan: {preset}")
        plan_entries.append(
            {
                "preset": preset,
                "html_relative": html_relative,
                "manifest_relative": manifest_relative,
                "row": row,
            }
        )

    duplicate_presets = sorted(
        {value for value in preset_ids if preset_ids.count(value) > 1}
    )
    duplicate_html = sorted({value for value in html_paths if html_paths.count(value) > 1})
    duplicate_manifests = sorted(
        {value for value in manifest_paths if manifest_paths.count(value) > 1}
    )
    if duplicate_presets:
        errors.append(f"duplicate Presets in batch plan: {duplicate_presets}")
    if duplicate_html:
        errors.append(f"duplicate output HTML paths in batch plan: {duplicate_html}")
    if duplicate_manifests:
        errors.append(f"duplicate output manifest paths in batch plan: {duplicate_manifests}")

    decks: list[dict[str, Any]] = []
    for entry in plan_entries:
        preset = entry["preset"]
        row = entry["row"]
        try:
            html_path = _resolve_repo_path(
                repo_root, entry["html_relative"], f"output HTML for {preset}"
            )
            manifest_path = _resolve_repo_path(
                repo_root, entry["manifest_relative"], f"output manifest for {preset}"
            )
        except QueueValidationError as exc:
            errors.extend(exc.errors)
            continue
        missing = False
        if not html_path.is_file():
            errors.append(f"missing output HTML for {preset}: {entry['html_relative']}")
            missing = True
        if not manifest_path.is_file():
            errors.append(
                f"missing output manifest for {preset}: {entry['manifest_relative']}"
            )
            missing = True
        if missing:
            continue

        manifest = _load_json(manifest_path, f"manifest for {preset}")
        errors.extend(_reject_absolute_strings(manifest, f"manifest for {preset}"))
        html = html_path.read_text(encoding="utf-8")

        if manifest.get("renderer_entrypoint") != FORMAL_RENDERER:
            errors.append(
                f"manifest renderer for {preset} must be {FORMAL_RENDERER}, "
                f"got {manifest.get('renderer_entrypoint')!r}"
            )
        if manifest.get("content_mode") != "new-deck":
            errors.append(
                f"manifest content_mode for {preset} must be new-deck, "
                f"got {manifest.get('content_mode')!r}"
            )
        manifest_preset, theme_kind = _manifest_preset_id(manifest)
        if manifest_preset != preset:
            errors.append(
                f"manifest Preset id mismatch for {preset}: {manifest_preset!r}"
            )
        if theme_kind != "html-preset":
            errors.append(
                f"manifest theme.kind for {preset} must be html-preset, got {theme_kind!r}"
            )

        manifest_output = manifest.get("output")
        try:
            output = _validate_repo_relative_posix(
                manifest_output, f"manifest output for {preset}"
            )
            if output != entry["html_relative"]:
                errors.append(
                    f"manifest output for {preset} must equal batch-plan HTML: "
                    f"{output} != {entry['html_relative']}"
                )
        except QueueValidationError as exc:
            errors.extend(exc.errors)

        external_editor = html_path.parent / "edit-mode.js"
        external_editor_sha = _hash_if_file(external_editor)
        if external_editor_sha is None:
            errors.append(f"missing external editor copy for {preset}: {external_editor}")
        elif external_editor_sha != canonical_editor_sha:
            errors.append(
                f"non-current external editor hash for {preset}: "
                f"{external_editor_sha} != {canonical_editor_sha}"
            )

        editable_dom = manifest.get("editable_dom")
        manifest_editor_sha = (
            editable_dom.get("editor_sha256")
            if isinstance(editable_dom, dict)
            else None
        )
        if manifest_editor_sha != canonical_editor_sha:
            errors.append(
                f"non-current manifest editor hash for {preset}: "
                f"{manifest_editor_sha} != {canonical_editor_sha}"
            )
        if isinstance(editable_dom, dict) and editable_dom.get("editor_source"):
            try:
                _validate_repo_relative_posix(
                    editable_dom["editor_source"], f"manifest editor_source for {preset}"
                )
            except QueueValidationError as exc:
                errors.extend(exc.errors)

        try:
            embedded_editor = _extract_embedded_editor(html, preset)
            embedded_editor_sha = _sha256_text(embedded_editor)
            if embedded_editor_sha != expected_embedded_sha:
                errors.append(
                    f"non-current embedded editor hash for {preset}: "
                    f"{embedded_editor_sha} != {expected_embedded_sha}"
                )
        except QueueValidationError as exc:
            errors.extend(exc.errors)
            embedded_editor_sha = None

        slides = _parse_slides(html, preset, errors)
        layouts = manifest.get("layouts")
        if not isinstance(layouts, list):
            errors.append(f"manifest layouts for {preset} must be an array")
            layouts = []
        if len(layouts) != len(slides):
            errors.append(
                f"manifest/HTML page count mismatch for {preset}: "
                f"manifest={len(layouts)}, HTML={len(slides)}"
            )
            if len(layouts) > len(slides):
                actual_indices = {int(slide["index"]) for slide in slides}
                missing_indices = sorted(set(range(len(layouts))) - actual_indices)
                errors.append(
                    f"missing page indices in {preset} from manifest contract: "
                    f"{missing_indices}"
                )

        planned_pages = row.get("pages", row.get("slide_count"))
        if planned_pages is not None:
            try:
                planned_pages_int = int(planned_pages)
            except (TypeError, ValueError):
                errors.append(f"invalid planned page count for {preset}: {planned_pages!r}")
            else:
                if planned_pages_int != len(slides):
                    errors.append(
                        f"batch-plan/HTML page count mismatch for {preset}: "
                        f"plan={planned_pages_int}, HTML={len(slides)}"
                    )
                    if planned_pages_int > len(slides):
                        actual_indices = {int(slide["index"]) for slide in slides}
                        missing_indices = sorted(
                            set(range(planned_pages_int)) - actual_indices
                        )
                        errors.append(
                            f"missing page indices in {preset} from batch-plan contract: "
                            f"{missing_indices}"
                        )
        planned_layouts = row.get("layouts")
        if planned_layouts is not None and planned_layouts != layouts:
            errors.append(f"batch-plan/manifest layout sequence mismatch for {preset}")

        page_records: list[dict[str, Any]] = []
        for slide in slides:
            index = int(slide["index"])
            layout_id = str(slide.get("layout_id") or "")
            manifest_layout = str(layouts[index]) if index < len(layouts) else ""
            if not layout_id:
                errors.append(f"missing layout id in HTML for {preset} slide {index}")
            if manifest_layout and manifest_layout != layout_id:
                errors.append(
                    f"layout mismatch for {preset} slide {index}: "
                    f"HTML={layout_id}, manifest={manifest_layout}"
                )
            scene_role = _scene_role(manifest, index, slide)
            if not scene_role:
                errors.append(f"missing scene role for {preset} slide {index}")
                scene_role = "unknown"
            page_records.append(
                {
                    "slide_index": index,
                    "slide_number": index + 1,
                    "slide_id": slide["id"],
                    "layout_id": layout_id,
                    "scene_role": scene_role,
                }
            )

        decks.append(
            {
                "preset": preset,
                "slide_count": len(slides),
                "source_html": entry["html_relative"],
                "source_manifest": entry["manifest_relative"],
                "source_hashes": {
                    "html_sha256": _sha256(html_path),
                    "manifest_sha256": _sha256(manifest_path),
                    "canonical_editor_sha256": canonical_editor_sha,
                    "embedded_editor_sha256": embedded_editor_sha,
                    "external_editor_sha256": external_editor_sha,
                    "manifest_editor_sha256": manifest_editor_sha,
                },
                "pages": page_records,
            }
        )

    if errors:
        raise QueueValidationError(errors)

    assignment, shards = _assign_shards(decks)
    jobs: list[dict[str, Any]] = []
    preset_records: list[dict[str, Any]] = []
    for deck in sorted(decks, key=lambda row: row["preset"]):
        preset = deck["preset"]
        shard = assignment[preset]
        job_ids: list[str] = []
        for page in deck["pages"]:
            number = page["slide_number"]
            job_id = f"{preset}/slide-{number:03d}"
            job_ids.append(job_id)
            paths, output_hashes = _job_paths(repo_root, v6_root, preset, number)
            required_inputs = (
                "reference_screenshot",
                "protected_mask",
                "prompt",
                "run_manifest",
            )
            missing_inputs = [
                name
                for name in required_inputs
                if output_hashes.get(f"{name}_sha256") is None
            ]
            if missing_inputs:
                raise QueueValidationError(
                    [
                        f"missing prepared image-background inputs for {job_id}: "
                        f"{missing_inputs}"
                    ]
                )
            jobs.append(
                {
                    "job_id": job_id,
                    "preset": preset,
                    "agent_shard": shard,
                    **page,
                    "source": {
                        "html": deck["source_html"],
                        "manifest": deck["source_manifest"],
                    },
                    "source_hashes": dict(deck["source_hashes"]),
                    "paths": paths,
                    "output_hashes": output_hashes,
                }
            )
        preset_records.append(
            {
                "preset": preset,
                "agent_shard": shard,
                "slide_count": deck["slide_count"],
                "source_html": deck["source_html"],
                "source_manifest": deck["source_manifest"],
                "source_hashes": deck["source_hashes"],
                "job_ids": job_ids,
            }
        )

    job_ids = [row["job_id"] for row in jobs]
    duplicate_jobs = sorted({value for value in job_ids if job_ids.count(value) > 1})
    if duplicate_jobs:
        raise QueueValidationError([f"duplicate page jobs: {duplicate_jobs}"])
    total_slides = sum(deck["slide_count"] for deck in decks)
    if len(jobs) != total_slides:
        raise QueueValidationError(
            [f"dynamic queue completeness mismatch: jobs={len(jobs)}, slides={total_slides}"]
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "mode": "v6-background-production-queue",
        "preset_count": len(decks),
        "slide_count": total_slides,
        "shard_count": SHARD_COUNT,
        "contract": {
            "inventory_source": "batch-plan-only",
            "content_mode": "new-deck",
            "renderer": FORMAL_RENDERER,
            "one_model_raster_per_slide": True,
            "preset_may_split_across_shards": False,
            "page_count_policy": "dynamic-from-validated-html-and-manifest",
            "path_format": "repository-relative-posix",
            "source_gate": [
                "exact-18-reusable-presets",
                "formal-new-deck-renderer",
                "unique-contiguous-slide-index-and-id",
                "html-manifest-layout-parity",
                "current-external-and-embedded-editor",
            ],
        },
        "inputs": {
            "batch_plan": _repo_relative(batch_plan_path, repo_root, "batch plan"),
            "batch_plan_sha256": _sha256(batch_plan_path),
            "preset_catalog": _repo_relative(
                preset_catalog_path, repo_root, "Preset catalog"
            ),
            "preset_catalog_sha256": _sha256(preset_catalog_path),
            "canonical_editor": _repo_relative(
                editor_path, repo_root, "canonical editor"
            ),
            "canonical_editor_sha256": canonical_editor_sha,
        },
        "shards": shards,
        "presets": preset_records,
        "jobs": jobs,
    }


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the dynamic v6 18-Preset image-background job queue"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Validate inputs; do not write")
    mode.add_argument("--write", action="store_true", help="Validate and write job-queue.json")
    parser.add_argument("--batch-plan", required=True)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--v6-root", default=V6_RELATIVE_ROOT.as_posix())
    parser.add_argument("--editor", default=DEFAULT_EDITOR.as_posix())
    parser.add_argument("--preset-catalog", default=DEFAULT_PRESET_CATALOG.as_posix())
    parser.add_argument("--output", default=DEFAULT_OUTPUT.as_posix())
    return parser


def run_cli(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    try:
        batch_plan = _resolve_repo_path(repo_root, args.batch_plan, "batch plan")
        v6_root = _resolve_repo_path(repo_root, args.v6_root, "v6 root")
        editor = _resolve_repo_path(repo_root, args.editor, "canonical editor")
        catalog = _resolve_repo_path(repo_root, args.preset_catalog, "Preset catalog")
        output = _resolve_repo_path(repo_root, args.output, "queue output")
        queue = build_job_queue(
            batch_plan_path=batch_plan,
            repo_root=repo_root,
            v6_root=v6_root,
            editor_path=editor,
            preset_catalog_path=catalog,
        )
        if args.write:
            _write_json_atomic(output, queue)
        print(
            json.dumps(
                {
                    "ok": True,
                    "mode": "write" if args.write else "check",
                    "presets": queue["preset_count"],
                    "slides": queue["slide_count"],
                    "shards": queue["shard_count"],
                    "shard_slide_counts": [
                        row["slide_count"] for row in queue["shards"]
                    ],
                    "output": _repo_relative(output, repo_root, "queue output")
                    if args.write
                    else None,
                },
                ensure_ascii=False,
            )
        )
        return 0
    except QueueValidationError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "mode": "write" if args.write else "check",
                    "error_count": len(exc.errors),
                    "errors": exc.errors,
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1


def main() -> None:
    raise SystemExit(run_cli())


if __name__ == "__main__":
    main()
