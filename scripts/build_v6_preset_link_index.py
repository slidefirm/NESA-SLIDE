"""Build the release-only link index for the formal v6 Preset batch.

The tool fails closed.  It accepts only the fixed 18-Preset cohort, a formal
``new-deck`` batch plan, and a written final QA ledger classified as ``pass``.
``--check`` performs the same validation as ``--write`` without touching the
filesystem.  ``--write`` emits only ``preset-links.json`` and ``index.html``.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import quote

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRESET_CATALOG = Path("prompt_system/presets/catalog.yaml")
JSON_NAME = "preset-links.json"
HTML_NAME = "index.html"
SCHEMA_VERSION = "html-image-background-v6-preset-links/v1"

EXPECTED_PRESETS = (
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
EXPECTED_PRESET_COUNT = len(EXPECTED_PRESETS)

WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_PASS_GATES = (
    "exact_18_presets",
    "dynamic_page_inventory",
    "model_adjacent_embedded_hash_parity",
    "pptx_background_attributes",
    "computed_background_wins_neutralizer",
    "references_masks_prompts_present",
    "qa_reports_complete",
    "portable_paths",
    "required_command_kinds_complete",
    "human_review_required",
)


class LinkIndexError(ValueError):
    """Raised when the v6 delivery cannot be proven release-ready."""

    def __init__(self, errors: Iterable[str]):
        self.errors = list(dict.fromkeys(str(error) for error in errors if str(error)))
        if not self.errors:
            self.errors = ["unknown v6 Preset link-index validation error"]
        super().__init__("\n".join(self.errors))


class _SlideParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.slides: list[dict[str, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.lower() != "section":
            return
        values = {str(key).lower(): str(value or "") for key, value in attrs}
        if "slide" in set(values.get("class", "").split()):
            self.slides.append(values)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LinkIndexError([f"invalid {label}: {path}: {exc}"]) from exc
    if not isinstance(payload, dict):
        raise LinkIndexError([f"{label} must contain a JSON object: {path}"])
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portable_path(value: Any, label: str, *, allow_parent: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LinkIndexError([f"{label} must be a non-empty path string"])
    raw = value.strip()
    if (
        raw.startswith(("/", "\\", "file://"))
        or WINDOWS_ABSOLUTE_RE.match(raw)
        or "\\" in raw
    ):
        raise LinkIndexError([f"{label} must be portable POSIX, got: {value}"])
    pure = PurePosixPath(raw)
    forbidden = {"", "."} if allow_parent else {"", ".", ".."}
    if pure.is_absolute() or any(part in forbidden for part in pure.parts):
        raise LinkIndexError([f"{label} is not a valid portable path: {value}"])
    return raw


def _resolve_repo_path(repo_root: Path, value: Any, label: str) -> Path:
    portable = _portable_path(value, label)
    resolved = (repo_root / PurePosixPath(portable)).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise LinkIndexError([f"{label} escapes the repository root: {value}"]) from exc
    return resolved


def _resolve_cli_path(repo_root: Path, value: str | Path, label: str) -> Path:
    candidate = Path(value)
    resolved = candidate.resolve() if candidate.is_absolute() else (repo_root / candidate).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise LinkIndexError([f"{label} must stay inside the repository: {resolved}"]) from exc
    return resolved


def _relative(path: Path, repo_root: Path, label: str) -> str:
    try:
        relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise LinkIndexError([f"{label} escapes the repository: {path}"]) from exc
    return _portable_path(relative, label)


def _preset_id(row: Mapping[str, Any], label: str) -> str:
    value = row.get("preset_id", row.get("preset"))
    if not isinstance(value, str) or not value.strip():
        raise LinkIndexError([f"missing Preset id in {label}"])
    return value.strip()


def _integer(value: Any, label: str, errors: list[str], *, minimum: int = 0) -> int | None:
    if isinstance(value, bool):
        errors.append(f"{label} must be an integer")
        return None
    try:
        result = int(value)
    except (TypeError, ValueError):
        errors.append(f"{label} must be an integer")
        return None
    if result < minimum:
        errors.append(f"{label} must be >= {minimum}")
        return None
    return result


def _duplicates(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def _load_reusable_presets(catalog_path: Path) -> set[str]:
    try:
        payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise LinkIndexError([f"invalid Preset catalog: {catalog_path}: {exc}"]) from exc
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise LinkIndexError(["Preset catalog must contain an entries array"])
    ids: list[str] = []
    reusable: set[str] = set()
    for row in entries:
        if not isinstance(row, Mapping):
            continue
        preset = str(row.get("id") or "").strip()
        if not preset:
            continue
        ids.append(preset)
        capabilities = row.get("capabilities")
        if isinstance(capabilities, list) and "reusable-preset" in capabilities:
            reusable.add(preset)
    duplicates = _duplicates(ids)
    if duplicates:
        raise LinkIndexError([f"Preset catalog contains duplicate ids: {duplicates}"])
    missing = [preset for preset in EXPECTED_PRESETS if preset not in reusable]
    if missing:
        raise LinkIndexError(
            [f"fixed cohort Presets missing reusable-preset capability: {missing}"]
        )
    return reusable


def _validate_batch_plan(plan: Mapping[str, Any], reusable: set[str]) -> dict[str, Any]:
    errors: list[str] = []
    if plan.get("content_mode") != "new-deck":
        errors.append("batch plan content_mode must be new-deck")
    if plan.get("preset_demo") is not False:
        errors.append("batch plan preset_demo must be false")
    if plan.get("preset_count") != EXPECTED_PRESET_COUNT:
        errors.append(f"batch plan preset_count must be {EXPECTED_PRESET_COUNT}")
    cohort = plan.get("preset_cohort")
    if cohort != list(EXPECTED_PRESETS):
        errors.append("batch plan preset_cohort must equal the fixed ordered 18-Preset cohort")
    rows = plan.get("presets")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        errors.append("batch plan must contain a presets array of objects")
        rows = []
    if len(rows) != EXPECTED_PRESET_COUNT:
        errors.append(
            f"batch plan must contain exactly {EXPECTED_PRESET_COUNT} Presets, got {len(rows)}"
        )

    by_id: dict[str, Mapping[str, Any]] = {}
    ids: list[str] = []
    page_counts: dict[str, int] = {}
    for index, row in enumerate(rows):
        try:
            preset = _preset_id(row, f"batch plan row {index}")
        except LinkIndexError as exc:
            errors.extend(exc.errors)
            continue
        ids.append(preset)
        if preset in by_id:
            continue
        by_id[preset] = row
        if preset not in EXPECTED_PRESETS:
            errors.append(f"batch plan contains unknown Preset: {preset}")
        elif preset not in reusable:
            errors.append(f"batch plan Preset is not reusable: {preset}")
        if row.get("content_mode") not in (None, "new-deck"):
            errors.append(f"batch plan row content_mode must be new-deck for {preset}")
        if row.get("preset_demo") not in (None, False):
            errors.append(f"batch plan row preset_demo must be false for {preset}")
        layouts = row.get("layouts")
        if not isinstance(layouts, list) or not layouts or not all(
            isinstance(layout, str) and layout.strip() for layout in layouts
        ):
            errors.append(f"batch plan layouts must be a non-empty string array for {preset}")
        else:
            page_counts[preset] = len(layouts)
        try:
            _portable_path(row.get("output_html"), f"batch output_html for {preset}")
        except LinkIndexError as exc:
            errors.extend(exc.errors)

    duplicates = _duplicates(ids)
    if duplicates:
        errors.append(f"batch plan contains duplicate Presets: {duplicates}")
    missing = [preset for preset in EXPECTED_PRESETS if preset not in by_id]
    if missing:
        errors.append(f"batch plan is missing fixed Presets: {missing}")
    unknown = sorted(set(ids) - set(EXPECTED_PRESETS))
    if unknown:
        errors.append(f"batch plan contains unknown Presets: {unknown}")
    if ids and ids != list(EXPECTED_PRESETS):
        errors.append("batch plan presets must use the fixed cohort order")
    declared_slides = _integer(plan.get("slide_count"), "batch plan slide_count", errors, minimum=1)
    calculated_slides = sum(page_counts.values())
    if declared_slides is not None and calculated_slides and declared_slides != calculated_slides:
        errors.append(
            f"batch plan slide_count mismatch: declared={declared_slides}, layouts={calculated_slides}"
        )
    if errors:
        raise LinkIndexError(errors)
    return {
        "rows": by_id,
        "page_counts": page_counts,
        "slide_count": calculated_slides,
    }


def _parse_final_slides(path: Path, preset: str) -> list[dict[str, str]]:
    try:
        markup = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise LinkIndexError([f"cannot read final HTML for {preset}: {path}: {exc}"]) from exc
    parser = _SlideParser()
    try:
        parser.feed(markup)
        parser.close()
    except Exception as exc:
        raise LinkIndexError([f"cannot parse final HTML for {preset}: {exc}"]) from exc
    return parser.slides


def _validate_slide_inventory(
    slides: Sequence[Mapping[str, str]], preset: str, expected: int
) -> list[str]:
    errors: list[str] = []
    if len(slides) != expected:
        errors.append(
            f"final HTML page count mismatch for {preset}: expected={expected}, actual={len(slides)}"
        )
        return errors
    ids = [str(slide.get("id") or "") for slide in slides]
    if any(not slide_id for slide_id in ids):
        errors.append(f"final HTML contains a slide without id for {preset}")
    if _duplicates(ids):
        errors.append(f"final HTML contains duplicate slide ids for {preset}: {_duplicates(ids)}")
    indices: list[int] = []
    page_numbers: list[int] = []
    for position, slide in enumerate(slides):
        try:
            indices.append(int(slide.get("data-index", "")))
        except ValueError:
            errors.append(f"final HTML slide {position + 1} has invalid data-index for {preset}")
        try:
            page_numbers.append(int(slide.get("data-page-number", "")))
        except ValueError:
            errors.append(f"final HTML slide {position + 1} has invalid data-page-number for {preset}")
        try:
            page_count = int(slide.get("data-page-count", ""))
        except ValueError:
            errors.append(f"final HTML slide {position + 1} has invalid data-page-count for {preset}")
        else:
            if page_count != expected:
                errors.append(
                    f"final HTML slide {position + 1} data-page-count mismatch for {preset}"
                )
    if indices and indices != list(range(expected)):
        errors.append(f"final HTML has missing or reordered data-index values for {preset}")
    if page_numbers and page_numbers != list(range(1, expected + 1)):
        errors.append(f"final HTML has missing or reordered page numbers for {preset}")
    return errors


def _validate_qa_summary(
    qa: Mapping[str, Any],
    plan_inventory: Mapping[str, Any],
    repo_root: Path,
) -> list[dict[str, Any]]:
    errors: list[str] = []
    if qa.get("mode") != "write":
        errors.append("final QA summary mode must be write")
    if qa.get("classification") != "pass":
        errors.append("final QA summary classification must be pass")
    if qa.get("human_review_required") is not True:
        errors.append("final QA summary must require human visual review")

    summary = qa.get("summary")
    if not isinstance(summary, Mapping):
        errors.append("final QA summary must contain a summary object")
        summary = {}
    expected_total = int(plan_inventory["slide_count"])
    required_summary_values = {
        "preset_count": EXPECTED_PRESET_COUNT,
        "slide_count": expected_total,
        "partial": 0,
        "failed": 0,
        "planned": 0,
        "human_reviews_accepted": EXPECTED_PRESET_COUNT,
        "human_reviews_pending": 0,
        "human_reviews_rejected": 0,
    }
    for key, expected in required_summary_values.items():
        if summary.get(key) != expected:
            errors.append(f"final QA summary {key} must be {expected}, got {summary.get(key)!r}")

    gates = qa.get("gates")
    if not isinstance(gates, Mapping):
        errors.append("final QA summary must contain a gates object")
        gates = {}
    for gate in REQUIRED_PASS_GATES:
        if gates.get(gate) is not True:
            errors.append(f"final QA gate must pass: {gate}")

    commands = qa.get("commands")
    command_status: dict[str, str] = {}
    if not isinstance(commands, list) or not commands or not all(
        isinstance(row, Mapping) for row in commands
    ):
        errors.append("final QA summary must contain a non-empty commands array")
        commands = []
    for index, command in enumerate(commands):
        command_id = str(command.get("command_id") or "").strip()
        if not command_id:
            errors.append(f"final QA command {index} is missing command_id")
            continue
        if command_id in command_status:
            errors.append(f"final QA contains duplicate command_id: {command_id}")
        status = str(command.get("status") or "")
        command_status[command_id] = status
        if status != "pass":
            errors.append(f"final QA command is not pass: {command_id}={status or 'missing'}")

    rows = qa.get("presets")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        errors.append("final QA summary must contain a presets array of objects")
        rows = []
    if len(rows) != EXPECTED_PRESET_COUNT:
        errors.append(
            f"final QA summary must contain exactly {EXPECTED_PRESET_COUNT} Presets, got {len(rows)}"
        )
    qa_ids: list[str] = []
    qa_by_id: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(rows):
        try:
            preset = _preset_id(row, f"final QA preset row {index}")
        except LinkIndexError as exc:
            errors.extend(exc.errors)
            continue
        qa_ids.append(preset)
        if preset in qa_by_id:
            continue
        qa_by_id[preset] = row
        if preset not in EXPECTED_PRESETS:
            errors.append(f"final QA summary contains unknown Preset: {preset}")

    duplicates = _duplicates(qa_ids)
    if duplicates:
        errors.append(f"final QA summary contains duplicate Presets: {duplicates}")
    missing = [preset for preset in EXPECTED_PRESETS if preset not in qa_by_id]
    if missing:
        errors.append(f"final QA summary is missing fixed Presets: {missing}")
    unknown = sorted(set(qa_ids) - set(EXPECTED_PRESETS))
    if unknown:
        errors.append(f"final QA summary contains unknown Presets: {unknown}")
    if qa_ids and qa_ids != list(EXPECTED_PRESETS):
        errors.append("final QA presets must use the fixed cohort order")

    links: list[dict[str, Any]] = []
    final_paths: list[str] = []
    for order, preset in enumerate(EXPECTED_PRESETS, start=1):
        row = qa_by_id.get(preset)
        if row is None:
            continue
        expected_pages = int(plan_inventory["page_counts"].get(preset, 0))
        slide_count = _integer(
            row.get("slide_count"), f"final QA slide_count for {preset}", errors, minimum=1
        )
        if slide_count is not None and slide_count != expected_pages:
            errors.append(
                f"final QA page count mismatch for {preset}: plan={expected_pages}, qa={slide_count}"
            )
        review = row.get("human_review")
        review_status = review.get("status") if isinstance(review, Mapping) else None
        if review_status != "accepted":
            errors.append(f"final QA human review must be accepted for {preset}")
        page_rows = row.get("pages")
        if not isinstance(page_rows, list) or not all(isinstance(page, Mapping) for page in page_rows):
            errors.append(f"final QA pages must be an array of objects for {preset}")
            page_rows = []
        page_numbers: list[int] = []
        for page_index, page in enumerate(page_rows):
            number = _integer(
                page.get("slide_number"),
                f"final QA slide_number {page_index + 1} for {preset}",
                errors,
                minimum=1,
            )
            if number is not None:
                page_numbers.append(number)
        if len(page_rows) != expected_pages:
            errors.append(
                f"final QA pages are incomplete for {preset}: expected={expected_pages}, actual={len(page_rows)}"
            )
        if page_numbers and page_numbers != list(range(1, expected_pages + 1)):
            errors.append(f"final QA has missing or reordered pages for {preset}")

        deck_commands = row.get("commands")
        if not isinstance(deck_commands, list) or not deck_commands:
            errors.append(f"final QA Preset commands are missing for {preset}")
        else:
            for command_id in deck_commands:
                if command_status.get(str(command_id)) != "pass":
                    errors.append(
                        f"final QA Preset command is missing or not pass for {preset}: {command_id}"
                    )

        try:
            final_relative = _portable_path(row.get("final_html"), f"final HTML for {preset}")
        except LinkIndexError as exc:
            errors.extend(exc.errors)
            continue
        final_paths.append(final_relative)
        if PurePosixPath(final_relative).name != "final.html":
            errors.append(f"final HTML must be named final.html for {preset}: {final_relative}")
        final_path = _resolve_repo_path(repo_root, final_relative, f"final HTML for {preset}")
        if not final_path.is_file():
            errors.append(f"final HTML does not exist for {preset}: {final_relative}")
            continue
        slides = _parse_final_slides(final_path, preset)
        errors.extend(_validate_slide_inventory(slides, preset, expected_pages))
        actual_hash = _sha256(final_path)
        declared_hash = str(row.get("final_html_sha256") or "").lower()
        if not SHA256_RE.fullmatch(declared_hash):
            errors.append(f"final QA has no valid final_html_sha256 for {preset}")
        elif declared_hash != actual_hash:
            errors.append(f"final HTML changed after QA for {preset}")
        links.append(
            {
                "order": order,
                "preset_id": preset,
                "slide_count": expected_pages,
                "final_html": final_relative,
                "final_html_sha256": actual_hash,
            }
        )

    duplicate_paths = _duplicates(final_paths)
    if duplicate_paths:
        errors.append(f"multiple Presets point to the same final HTML: {duplicate_paths}")
    if len(links) != EXPECTED_PRESET_COUNT:
        errors.append(
            f"release link inventory is incomplete: expected={EXPECTED_PRESET_COUNT}, actual={len(links)}"
        )
    if errors:
        raise LinkIndexError(errors)
    return links


def _portable_relative_href(index_dir: Path, target: Path) -> str:
    relative = os.path.relpath(target, start=index_dir).replace("\\", "/")
    _portable_path(relative, "index href", allow_parent=True)
    return quote(relative, safe="/._-~")


def _render_html(links: Sequence[Mapping[str, Any]], output_dir: Path, repo_root: Path) -> str:
    cards: list[str] = []
    for link in links:
        target = _resolve_repo_path(repo_root, link["final_html"], "index target")
        href = _portable_relative_href(output_dir, target)
        preset = html.escape(str(link["preset_id"]))
        cards.append(
            "      <li>"
            f'<a class="preset-link" data-preset-id="{preset}" href="{html.escape(href, quote=True)}" '
            'target="_blank" rel="noopener noreferrer">'
            f'<span class="order">{int(link["order"]):02d}</span>'
            f'<span class="name">{preset}</span>'
            f'<span class="pages">{int(link["slide_count"])} 頁</span>'
            "</a></li>"
        )
    return """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>v6 正式交付｜18 Preset</title>
  <style>
    :root { color-scheme: dark; font-family: "Noto Sans TC", system-ui, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #15181d; color: #f4f6f8; }
    main { width: min(1040px, calc(100% - 40px)); margin: 48px auto; }
    h1 { margin: 0 0 8px; font-size: clamp(28px, 4vw, 46px); }
    p { margin: 0 0 28px; color: #aeb7c2; }
    ol { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; margin: 0; padding: 0; list-style: none; }
    .preset-link { display: grid; grid-template-columns: 42px 1fr auto; gap: 12px; align-items: center; min-height: 68px; padding: 14px 16px; border: 1px solid #303740; border-radius: 12px; background: #1d2229; color: inherit; text-decoration: none; }
    .preset-link:hover, .preset-link:focus-visible { border-color: #79b8ff; background: #232b35; outline: none; }
    .order { color: #79b8ff; font-variant-numeric: tabular-nums; }
    .name { font-weight: 700; overflow-wrap: anywhere; }
    .pages { color: #aeb7c2; font-size: 14px; white-space: nowrap; }
  </style>
</head>
<body>
  <main>
    <h1>v6 正式交付｜18 Preset</h1>
    <p>所有連結皆已通過 final QA；點擊後以新分頁開啟。</p>
    <ol>
""" + "\n".join(cards) + """
    </ol>
  </main>
</body>
</html>
"""


def _reject_nonportable_output(payload: Any, label: str) -> None:
    errors: list[str] = []

    def visit(value: Any, trail: str) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                visit(child, f"{trail}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{trail}[{index}]")
        elif isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith(("/", "\\", "file://")) or WINDOWS_ABSOLUTE_RE.match(stripped) or "\\" in stripped:
                errors.append(f"non-portable output string at {trail}: {value}")

    visit(payload, label)
    if errors:
        raise LinkIndexError(errors)


def build_link_index(
    *,
    batch_plan_path: Path,
    final_qa_path: Path,
    output_dir: Path,
    preset_catalog_path: Path,
    repo_root: Path = REPO_ROOT,
) -> tuple[dict[str, Any], str]:
    """Validate all release gates and return JSON/HTML output payloads."""

    repo_root = repo_root.resolve()
    batch_plan_path = _resolve_cli_path(repo_root, batch_plan_path, "batch plan")
    final_qa_path = _resolve_cli_path(repo_root, final_qa_path, "final QA summary")
    output_dir = _resolve_cli_path(repo_root, output_dir, "output directory")
    preset_catalog_path = _resolve_cli_path(repo_root, preset_catalog_path, "Preset catalog")
    reusable = _load_reusable_presets(preset_catalog_path)
    plan = _load_json(batch_plan_path, "formal batch plan")
    plan_inventory = _validate_batch_plan(plan, reusable)
    qa = _load_json(final_qa_path, "final QA summary")
    links = _validate_qa_summary(qa, plan_inventory, repo_root)
    json_output = output_dir / JSON_NAME
    html_output = output_dir / HTML_NAME
    payload = {
        "schema_version": SCHEMA_VERSION,
        "content_mode": "new-deck",
        "preset_count": EXPECTED_PRESET_COUNT,
        "slide_count": plan_inventory["slide_count"],
        "inputs": {
            "batch_plan": _relative(batch_plan_path, repo_root, "batch plan"),
            "final_qa_summary": _relative(final_qa_path, repo_root, "final QA summary"),
        },
        "outputs": {
            "json": _relative(json_output, repo_root, "JSON output"),
            "index_html": _relative(html_output, repo_root, "HTML output"),
        },
        "presets": links,
    }
    _reject_nonportable_output(payload, "preset-links")
    markup = _render_html(links, output_dir, repo_root)
    if "file://" in markup or WINDOWS_ABSOLUTE_RE.search(markup) or "\\" in markup:
        raise LinkIndexError(["index HTML contains a non-portable path"])
    return payload, markup


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the release-only 18-Preset v6 local link index"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Validate without writing files")
    mode.add_argument("--write", action="store_true", help="Write preset-links.json and index.html")
    parser.add_argument("--batch-plan", required=True, help="Formal v6 batch-plan JSON")
    parser.add_argument(
        "--final-qa-summary",
        "--final-qa",
        dest="final_qa_summary",
        required=True,
        help="Written final QA ledger/summary JSON",
    )
    parser.add_argument("--output-dir", required=True, help="Repository-contained output directory")
    parser.add_argument("--preset-catalog", default=str(DEFAULT_PRESET_CATALOG))
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    return parser


def run_cli(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        repo_root = Path(args.repo_root).resolve()
        output_dir = _resolve_cli_path(repo_root, args.output_dir, "output directory")
        payload, markup = build_link_index(
            batch_plan_path=Path(args.batch_plan),
            final_qa_path=Path(args.final_qa_summary),
            output_dir=output_dir,
            preset_catalog_path=Path(args.preset_catalog),
            repo_root=repo_root,
        )
        if args.write:
            _write_atomic(
                output_dir / JSON_NAME,
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            )
            _write_atomic(output_dir / HTML_NAME, markup)
        print(
            json.dumps(
                {
                    "status": "pass",
                    "mode": "write" if args.write else "check",
                    "preset_count": payload["preset_count"],
                    "slide_count": payload["slide_count"],
                    "outputs": payload["outputs"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except LinkIndexError as exc:
        print(
            json.dumps({"status": "fail", "errors": exc.errors}, ensure_ascii=False, indent=2),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
