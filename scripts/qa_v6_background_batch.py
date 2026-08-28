"""Orchestrate the final v6 HTML image-background QA batch.

This module is deliberately report-only with respect to presentation sources:
it reads the formal batch plan, dynamic job queue, per-Preset ``run.json`` and
``final.html`` files; it may create QA reports, captures, PPTX exports and one
final ledger, but it never rewrites an HTML or renderer source.

``--check`` validates the inventory and prints the complete command plan.
``--write`` runs that plan and writes ``qa/final-ledger.json``.  A machine-only
pass is always classified as ``partial`` until every Preset has an explicit
accepted human visual review in its ``run.json``.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PRESET_COUNT = 18
FORMAL_RENDERER = "scripts/render_randomized_html_demo.py"
SCHEMA_VERSION = "html-image-background-v6-final-qa/v2"

WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
RGB_COLOR_RE = re.compile(
    r"rgba?\(\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*[, ]\s*(\d{1,3})",
    re.IGNORECASE,
)
FINAL_STYLE_RE = re.compile(
    r"<style\b[^>]*\bid=[\"'](?:html-image-background-per-slide-experiment-final|"
    r"html-image-background-experiment-final)[\"'][^>]*>(?P<body>.*?)</style\s*>",
    re.IGNORECASE | re.DOTALL,
)
DATA_IMAGE_RE = re.compile(
    r"background-image\s*:\s*url\(\s*[\"']?"
    r"(?P<data>data:image/[a-z0-9.+-]+;base64,[A-Za-z0-9+/=\r\n]+)"
    r"[\"']?\s*\)",
    re.IGNORECASE,
)


class BatchQaError(ValueError):
    """Raised when a final QA inventory cannot be proven complete."""

    def __init__(self, errors: Iterable[str]):
        self.errors = list(dict.fromkeys(str(error) for error in errors if str(error)))
        if not self.errors:
            self.errors = ["unknown v6 final QA validation error"]
        super().__init__("\n".join(self.errors))


@dataclass(frozen=True)
class CommandSpec:
    command_id: str
    preset: str
    kind: str
    argv: tuple[str, ...]
    display_argv: tuple[str, ...]
    report: str
    slide_number: int | None = None
    expected_output: str | None = None
    capture_stdout_json: bool = False
    subject_html: str | None = None


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
        if "slide" not in set(values.get("class", "").split()):
            return
        self.slides.append(values)


# Kept inline so the batch runner remains the only orchestration source.  The
# command is report-only and records only booleans/lengths, never the enormous
# data URL itself.
COMPUTED_BACKGROUND_PROBE_JS = r"""
const fs = require('node:fs/promises');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { loadPlaywright, browserExecutable } = require('./scripts/playwright_runtime.cjs');
(async () => {
  const htmlPath = path.resolve(process.argv[1]);
  const reportPath = path.resolve(process.argv[2]);
  const markup = await fs.readFile(htmlPath, 'utf8');
  const baseHref = pathToFileURL(path.dirname(htmlPath) + path.sep).href;
  const withBase = markup.replace(/<head>/i, '<head><base href="' + baseHref + '">');
  const { chromium } = loadPlaywright();
  const executablePath = browserExecutable();
  if (!process.env.BROWSER_CDP_URL && !executablePath) throw new Error('No Chrome or Edge executable found');
  const browser = process.env.BROWSER_CDP_URL
    ? await chromium.connectOverCDP(process.env.BROWSER_CDP_URL)
    : await chromium.launch({ headless: true, executablePath });
  let report;
  try {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
    await page.route('https://fonts.googleapis.com/**', route => route.abort());
    await page.route('https://fonts.gstatic.com/**', route => route.abort());
    await page.setContent(withBase, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await Promise.race([page.evaluate(() => document.fonts?.ready), page.waitForTimeout(5000)]);
    await page.waitForFunction(() => document.documentElement.dataset.layoutReady === 'true', null, { timeout: 120000 });
    const slides = await page.evaluate(() => [...document.querySelectorAll('#stage > section.slide')].map(slide => {
      const backgroundImage = getComputedStyle(slide).backgroundImage || 'none';
      return {
        id: slide.id || '',
        hasInlineDataUrl: /^url\(["']?data:image\//i.test(backgroundImage),
        backgroundImageIsNone: backgroundImage === 'none',
        backgroundImageLength: backgroundImage.length,
        pptxBackground: slide.dataset.pptxBackgroundImage === 'true',
        pptxEmbedded: slide.dataset.pptxBackgroundImageEmbedded === 'true',
      };
    }));
    report = {
      qaMode: 'report-only',
      gate: 'computed-background-wins-neutralizer',
      slides,
      pass: slides.length > 0 && slides.every(row => row.hasInlineDataUrl && !row.backgroundImageIsNone && row.pptxBackground && row.pptxEmbedded),
    };
    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + '\n', 'utf8');
    if (!report.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error.stack || error.message || String(error)); process.exit(1); });
""".strip()


Executor = Callable[..., subprocess.CompletedProcess[str]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BatchQaError([f"invalid {label}: {path}: {exc}"]) from exc
    if not isinstance(payload, dict):
        raise BatchQaError([f"{label} must contain a JSON object: {path}"])
    return payload


def _portable_path(value: Any, label: str, *, allow_dot_prefix: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BatchQaError([f"{label} must be a non-empty path string"])
    raw = value.strip()
    if raw.startswith(("/", "\\", "file://")) or WINDOWS_ABSOLUTE_RE.match(raw):
        raise BatchQaError([f"{label} must be repository-relative POSIX: {value}"])
    if "\\" in raw:
        raise BatchQaError([f"{label} must use POSIX separators: {value}"])
    normalized = raw[2:] if allow_dot_prefix and raw.startswith("./") else raw
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise BatchQaError([f"{label} contains traversal or an empty segment: {value}"])
    return normalized


def _resolve_repo_path(repo_root: Path, value: Any, label: str) -> Path:
    portable = _portable_path(value, label)
    resolved = (repo_root / PurePosixPath(portable)).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise BatchQaError([f"{label} escapes repository root: {value}"]) from exc
    return resolved


def _resolve_cli_path(repo_root: Path, value: str, label: str) -> Path:
    candidate = Path(value)
    resolved = candidate.resolve() if candidate.is_absolute() else (repo_root / candidate).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise BatchQaError([f"{label} must stay inside repository root: {resolved}"]) from exc
    return resolved


def _relative(path: Path, repo_root: Path, label: str) -> str:
    try:
        value = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise BatchQaError([f"{label} escapes repository root: {path}"]) from exc
    return _portable_path(value, label)


def _reject_nonportable_strings(payload: Any, label: str) -> list[str]:
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
            if (
                stripped.startswith(("/", "\\", "file://"))
                or WINDOWS_ABSOLUTE_RE.match(stripped)
                or "\\" in stripped
            ):
                errors.append(f"non-portable path-like string at {trail}: {value}")

    visit(payload, label)
    return errors


def _batch_rows(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = plan.get("presets", plan.get("decks"))
    if not isinstance(rows, list):
        raise BatchQaError(["batch plan must contain a presets array"])
    if not all(isinstance(row, dict) for row in rows):
        raise BatchQaError(["every batch plan preset row must be an object"])
    return list(rows)


def _preset_id(row: Mapping[str, Any], label: str) -> str:
    value = row.get("preset_id", row.get("preset"))
    if not isinstance(value, str) or not value.strip():
        raise BatchQaError([f"missing Preset id in {label}"])
    return value.strip()


def _plan_manifest(row: Mapping[str, Any], preset: str) -> str:
    value = row.get("output_manifest", row.get("manifest"))
    if value is None:
        html_value = row.get("output_html", row.get("html"))
        if isinstance(html_value, str) and html_value.strip():
            html_path = PurePosixPath(html_value.strip())
            value = html_path.with_suffix(".manifest.json").as_posix()
    return _portable_path(value, f"source manifest for {preset}")


def _plan_html(row: Mapping[str, Any], preset: str) -> str:
    value = row.get("output_html", row.get("html"))
    return _portable_path(value, f"source HTML for {preset}")


def _queue_jobs(queue: Mapping[str, Any]) -> list[dict[str, Any]]:
    jobs = queue.get("jobs")
    if not isinstance(jobs, list) or not all(isinstance(row, dict) for row in jobs):
        raise BatchQaError(["job queue must contain a jobs array of objects"])
    return list(jobs)


def _parse_slides(markup: str) -> list[dict[str, str]]:
    parser = _SlideParser()
    parser.feed(markup)
    return parser.slides


def _extract_embedded_hashes(markup: str) -> list[str]:
    style_match = FINAL_STYLE_RE.search(markup)
    if not style_match:
        raise BatchQaError(["final HTML is missing the per-slide background style block"])
    style = style_match.group("body")
    if "!important" in style:
        raise BatchQaError(["final background style must not use !important"])
    hashes: list[str] = []
    for match in DATA_IMAGE_RE.finditer(style):
        data_url = match.group("data")
        encoded = re.sub(r"\s+", "", data_url.split(",", 1)[1])
        try:
            payload = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise BatchQaError(["final HTML contains an invalid embedded background data URL"]) from exc
        hashes.append(hashlib.sha256(payload).hexdigest())
    if not hashes:
        raise BatchQaError(["final HTML has no embedded raster background data URL"])
    return hashes


def _record_index(record: Mapping[str, Any], fallback: int) -> int:
    value = record.get("index", record.get("slide_index", fallback))
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise BatchQaError([f"invalid slide record index: {value!r}"]) from exc


def _nested(mapping: Mapping[str, Any], *keys: str) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _first_value(mapping: Mapping[str, Any], paths: Sequence[Sequence[str]]) -> Any:
    for path in paths:
        value = _nested(mapping, *path)
        if value not in (None, ""):
            return value
    return None


RUN_PATH_ALIASES: dict[str, tuple[tuple[str, ...], ...]] = {
    "reference_screenshot": (
        ("source_reference",),
        ("reference_screenshot",),
        ("clean_reference",),
    ),
    "protected_mask": (("mask",), ("protected_mask",)),
    "prompt": (("prompt",),),
    "model_output": (
        ("model_output",),
        ("model_output_provenance", "source_path"),
        ("preserved_model_output", "source"),
    ),
    "final_background": (
        ("background",),
        ("background_asset",),
        ("preserved_model_output", "adjacent_byte_preserving_copy"),
    ),
}


def _run_record_path(record: Mapping[str, Any], key: str, label: str) -> str:
    value = _first_value(record, RUN_PATH_ALIASES[key])
    return _portable_path(value, label)


def _declared_hashes(record: Mapping[str, Any], kind: str) -> list[str]:
    if kind == "model_output":
        values = [
            record.get("model_output_sha256"),
            _nested(record, "model_output_provenance", "sha256"),
        ]
    else:
        values = [
            record.get("background_sha256"),
            record.get("background_asset_sha256"),
            _nested(record, "preserved_model_output", "sha256"),
        ]
    return [str(value).lower() for value in values if isinstance(value, str) and value]


def _css_color_to_hex(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if HEX_COLOR_RE.fullmatch(text):
        return text.upper()
    match = RGB_COLOR_RE.match(text)
    if not match:
        return None
    channels = [int(group) for group in match.groups()]
    if any(channel > 255 for channel in channels):
        return None
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def _machine_palette(record: Mapping[str, Any], preset: str, number: int) -> tuple[list[str], list[str]]:
    contract = record.get("palette_contrast_contract")
    if not isinstance(contract, Mapping):
        raise BatchQaError([f"{preset} slide {number} is missing palette_contrast_contract"])

    bases: list[str] = []
    explicit_bases = contract.get("base_colors", contract.get("base_palette"))
    if isinstance(explicit_bases, list):
        bases.extend(color for value in explicit_bases if (color := _css_color_to_hex(value)))
    background_base = _css_color_to_hex(contract.get("background_base"))
    if background_base:
        bases.append(background_base)
    tokens = contract.get("palette_tokens")
    if isinstance(tokens, Mapping):
        for key in ("--bg", "--surface"):
            color = _css_color_to_hex(tokens.get(key))
            if color:
                bases.append(color)

    foreground: list[str] = []
    explicit = contract.get("qa_foreground_colors")
    if isinstance(explicit, list):
        foreground.extend(
            str(value) for value in explicit
            if isinstance(value, str) and "=" in value and "@" in value
        )
    token_thresholds = {
        "--ink": 4.5,
        "--text": 4.5,
        "--primary": 4.5,
        "--muted": 4.5,
        "--surface-text": 4.5,
        "--surface-muted": 4.5,
        "--accent": 3.0,
        "--support": 3.0,
        "--support-accent": 3.0,
    }
    if isinstance(tokens, Mapping):
        for key, threshold in token_thresholds.items():
            color = _css_color_to_hex(tokens.get(key))
            if color:
                foreground.append(f"{key[2:]}={color}@{threshold:.1f}")
    measured = contract.get("foreground_colors")
    if isinstance(measured, list):
        for index, value in enumerate(measured, start=1):
            color = _css_color_to_hex(value)
            if color:
                foreground.append(f"measured-{index}={color}@4.5")

    bases = list(dict.fromkeys(bases))
    foreground = list(dict.fromkeys(foreground))
    if not bases:
        raise BatchQaError([f"{preset} slide {number} has no usable base color for machine QA"])
    if not foreground:
        raise BatchQaError([f"{preset} slide {number} has no usable foreground color for machine QA"])
    return bases, foreground


def _human_review(run: Mapping[str, Any]) -> dict[str, Any]:
    candidates = [
        run.get("human_review"),
        _nested(run, "qa", "human_review"),
        _nested(run, "qa", "human_visual_review"),
        _nested(run, "qa", "composite_visual_review"),
    ]
    value = next((candidate for candidate in candidates if candidate not in (None, "")), None)
    if isinstance(value, Mapping):
        value = value.get("status", value.get("decision"))
    if value is True:
        return {"required": True, "status": "accepted"}
    if value is False:
        return {"required": True, "status": "rejected"}
    normalized = str(value or "pending").strip().lower().replace("_", "-")
    if any(token in normalized for token in ("reject", "fail", "block")):
        status = "rejected"
    elif any(token in normalized for token in ("pending", "await", "needs-review", "not-reviewed")):
        status = "pending"
    elif normalized in {"pass", "passed", "approved", "accepted", "complete", "completed"}:
        status = "accepted"
    elif normalized.startswith(("approved ", "accepted ", "passed ")):
        status = "accepted"
    else:
        status = "pending"
    return {"required": True, "status": status}


def _ensure_file(path: Path, label: str, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"missing {label}: {path}")


def _path_from_job(job: Mapping[str, Any], key: str, preset: str, number: int) -> str:
    paths = job.get("paths")
    if not isinstance(paths, Mapping):
        raise BatchQaError([f"{preset} slide {number} job is missing paths"])
    return _portable_path(paths.get(key), f"{preset} slide {number} {key}")


def _static_inventory(
    *,
    repo_root: Path,
    batch_plan_path: Path,
    job_queue_path: Path,
) -> dict[str, Any]:
    plan = _load_json(batch_plan_path, "formal batch plan")
    queue = _load_json(job_queue_path, "job queue")
    errors = [
        *_reject_nonportable_strings(plan, "batch-plan"),
        *_reject_nonportable_strings(queue, "job-queue"),
    ]
    if plan.get("content_mode") != "new-deck":
        errors.append("batch plan content_mode must be new-deck")
    if plan.get("preset_demo") not in (None, False):
        errors.append("batch plan preset_demo must be false")
    renderer = plan.get("renderer_entrypoint", plan.get("renderer"))
    if isinstance(renderer, Mapping):
        renderer = renderer.get("entrypoint")
    if renderer not in (None, FORMAL_RENDERER):
        errors.append(f"batch plan renderer must be {FORMAL_RENDERER}")

    plan_rows = _batch_rows(plan)
    queue_jobs = _queue_jobs(queue)
    queue_presets_raw = queue.get("presets")
    if not isinstance(queue_presets_raw, list) or not all(isinstance(row, dict) for row in queue_presets_raw):
        errors.append("job queue must contain a presets array of objects")
        queue_presets: list[dict[str, Any]] = []
    else:
        queue_presets = list(queue_presets_raw)

    if len(plan_rows) != EXPECTED_PRESET_COUNT:
        errors.append(f"batch plan must contain exactly {EXPECTED_PRESET_COUNT} Presets, got {len(plan_rows)}")
    if len(queue_presets) != EXPECTED_PRESET_COUNT:
        errors.append(f"job queue must contain exactly {EXPECTED_PRESET_COUNT} Presets, got {len(queue_presets)}")
    if plan.get("preset_count") not in (None, EXPECTED_PRESET_COUNT):
        errors.append(f"batch plan preset_count must be {EXPECTED_PRESET_COUNT}")
    if queue.get("preset_count") != EXPECTED_PRESET_COUNT:
        errors.append(f"job queue preset_count must be {EXPECTED_PRESET_COUNT}")

    plan_by_preset: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(plan_rows):
        try:
            preset = _preset_id(row, f"batch plan row {index}")
        except BatchQaError as exc:
            errors.extend(exc.errors)
            continue
        if preset in plan_by_preset:
            errors.append(f"duplicate Preset in batch plan: {preset}")
        plan_by_preset[preset] = row

    queue_by_preset: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(queue_presets):
        try:
            preset = _preset_id(row, f"job queue preset row {index}")
        except BatchQaError as exc:
            errors.extend(exc.errors)
            continue
        if preset in queue_by_preset:
            errors.append(f"duplicate Preset in job queue: {preset}")
        queue_by_preset[preset] = row
    if set(plan_by_preset) != set(queue_by_preset):
        errors.append("batch plan and job queue Preset cohorts differ")

    jobs_by_preset: dict[str, list[dict[str, Any]]] = {}
    seen_job_ids: set[str] = set()
    for position, job in enumerate(queue_jobs):
        try:
            preset = _preset_id(job, f"job {position}")
        except BatchQaError as exc:
            errors.extend(exc.errors)
            continue
        job_id = job.get("job_id")
        if not isinstance(job_id, str) or not job_id:
            errors.append(f"job {position} is missing job_id")
        elif job_id in seen_job_ids:
            errors.append(f"duplicate page job: {job_id}")
        else:
            seen_job_ids.add(job_id)
        jobs_by_preset.setdefault(preset, []).append(job)

    declared_total = queue.get("slide_count")
    if declared_total != len(queue_jobs):
        errors.append(f"dynamic page total mismatch: queue={declared_total}, jobs={len(queue_jobs)}")

    decks: list[dict[str, Any]] = []
    for preset in sorted(plan_by_preset):
        plan_row = plan_by_preset[preset]
        preset_jobs = jobs_by_preset.get(preset, [])
        if not preset_jobs:
            errors.append(f"missing all page jobs for {preset}")
            continue
        indexed_jobs: dict[int, dict[str, Any]] = {}
        for fallback, job in enumerate(preset_jobs):
            try:
                index = int(job.get("slide_index", fallback))
            except (TypeError, ValueError):
                errors.append(f"invalid page index for {preset}: {job.get('slide_index')!r}")
                continue
            if index in indexed_jobs:
                errors.append(f"duplicate page {index + 1} for {preset}")
            indexed_jobs[index] = job
        expected_indices = list(range(len(preset_jobs)))
        actual_indices = sorted(indexed_jobs)
        if actual_indices != expected_indices:
            missing = sorted(set(expected_indices) - set(actual_indices))
            errors.append(f"missing page indices for {preset}: {missing}; actual={actual_indices}")
            continue
        preset_jobs = [indexed_jobs[index] for index in expected_indices]
        queue_preset = queue_by_preset.get(preset, {})
        declared = queue_preset.get("slide_count")
        if declared != len(preset_jobs):
            errors.append(f"job queue page count mismatch for {preset}: preset={declared}, jobs={len(preset_jobs)}")
        planned = plan_row.get("pages", plan_row.get("slide_count"))
        if planned is not None:
            try:
                planned_int = int(planned)
            except (TypeError, ValueError):
                errors.append(f"invalid planned page count for {preset}: {planned!r}")
            else:
                if planned_int != len(preset_jobs):
                    errors.append(f"batch plan page count mismatch for {preset}: plan={planned_int}, jobs={len(preset_jobs)}")

        try:
            source_html_rel = _plan_html(plan_row, preset)
            source_html = _resolve_repo_path(repo_root, source_html_rel, f"source HTML for {preset}")
            source_manifest_rel = _plan_manifest(plan_row, preset)
            source_manifest = _resolve_repo_path(repo_root, source_manifest_rel, f"source manifest for {preset}")
        except BatchQaError as exc:
            errors.extend(exc.errors)
            continue
        _ensure_file(source_html, f"source HTML for {preset}", errors)
        _ensure_file(source_manifest, f"source manifest for {preset}", errors)
        queue_source_html = queue_preset.get("source_html")
        if queue_source_html is not None:
            try:
                if _portable_path(queue_source_html, f"job queue source HTML for {preset}") != source_html_rel:
                    errors.append(f"batch plan and job queue source HTML differ for {preset}")
            except BatchQaError as exc:
                errors.extend(exc.errors)

        try:
            run_rel_values = {
                _path_from_job(job, "run_manifest", preset, index + 1)
                for index, job in enumerate(preset_jobs)
            }
            final_rel_values = {
                _path_from_job(job, "final_html", preset, index + 1)
                for index, job in enumerate(preset_jobs)
            }
        except BatchQaError as exc:
            errors.extend(exc.errors)
            continue
        if len(run_rel_values) != 1:
            errors.append(f"{preset} page jobs disagree on run.json path")
            continue
        if len(final_rel_values) != 1:
            errors.append(f"{preset} page jobs disagree on final.html path")
            continue
        run_rel = next(iter(run_rel_values))
        final_rel = next(iter(final_rel_values))
        run_path = _resolve_repo_path(repo_root, run_rel, f"run.json for {preset}")
        final_path = _resolve_repo_path(repo_root, final_rel, f"final HTML for {preset}")
        _ensure_file(run_path, f"run.json for {preset}", errors)
        _ensure_file(final_path, f"final HTML for {preset}", errors)
        if not run_path.is_file() or not final_path.is_file():
            continue
        run = _load_json(run_path, f"run.json for {preset}")
        errors.extend(_reject_nonportable_strings(run, f"run.json for {preset}"))
        if run.get("source_was_modified") is not False:
            errors.append(f"run.json source_was_modified must be false for {preset}")
        if run.get("production_integration") is not False:
            errors.append(f"run.json production_integration must be false for {preset}")
        if run.get("automatic_pass") is True or _nested(run, "qa", "automatic_pass") is True:
            errors.append(f"run.json must not declare automatic_pass=true for {preset}")
        run_preset = run.get("preset_id", run.get("preset"))
        if run_preset not in (None, preset):
            errors.append(f"run.json Preset mismatch for {preset}: {run_preset!r}")
        run_final = run.get("final_html")
        if run_final is not None:
            try:
                if _portable_path(run_final, f"run final_html for {preset}") != final_rel:
                    errors.append(f"run.json final_html mismatch for {preset}")
            except BatchQaError as exc:
                errors.extend(exc.errors)
        records_raw = run.get("slide_records")
        if not isinstance(records_raw, list) or not all(isinstance(row, dict) for row in records_raw):
            errors.append(f"run.json for {preset} must contain slide_records")
            continue
        records_by_index: dict[int, dict[str, Any]] = {}
        for fallback, record in enumerate(records_raw):
            try:
                index = _record_index(record, fallback)
            except BatchQaError as exc:
                errors.extend(exc.errors)
                continue
            if index in records_by_index:
                errors.append(f"duplicate run.json page {index + 1} for {preset}")
            records_by_index[index] = record
        if sorted(records_by_index) != expected_indices:
            missing = sorted(set(expected_indices) - set(records_by_index))
            errors.append(f"missing run.json page indices for {preset}: {missing}")
            continue
        if run.get("slide_count") not in (None, len(preset_jobs)):
            errors.append(f"run.json page count mismatch for {preset}")

        source_markup = source_html.read_text(encoding="utf-8")
        source_sha_before = _sha256(source_html)
        source_slides = _parse_slides(source_markup)
        if len(source_slides) != len(preset_jobs):
            errors.append(
                f"source HTML page count mismatch for {preset}: "
                f"HTML={len(source_slides)}, jobs={len(preset_jobs)}"
            )

        markup = final_path.read_text(encoding="utf-8")
        final_sha_before = _sha256(final_path)
        slides = _parse_slides(markup)
        if len(slides) != len(preset_jobs):
            errors.append(f"final HTML page count mismatch for {preset}: HTML={len(slides)}, jobs={len(preset_jobs)}")
            continue
        html_indices: list[int] = []
        for fallback, slide in enumerate(slides):
            try:
                html_indices.append(int(slide.get("data-index", fallback)))
            except ValueError:
                errors.append(f"invalid final HTML data-index for {preset} slide {fallback + 1}")
        if html_indices != expected_indices:
            errors.append(f"final HTML pages are not contiguous for {preset}: {html_indices}")
        try:
            embedded_hashes = _extract_embedded_hashes(markup)
        except BatchQaError as exc:
            errors.extend(f"{preset}: {error}" for error in exc.errors)
            embedded_hashes = []
        if embedded_hashes and len(embedded_hashes) != len(preset_jobs):
            errors.append(f"embedded background count mismatch for {preset}: embedded={len(embedded_hashes)}, pages={len(preset_jobs)}")
        neutral_at = markup.find('id="html-image-background-experiment-neutral"')
        final_at = max(
            markup.find('id="html-image-background-per-slide-experiment-final"'),
            markup.find('id="html-image-background-experiment-final"'),
        )
        static_order_pass = final_at >= 0 and (neutral_at < 0 or final_at > neutral_at)
        if not static_order_pass:
            errors.append(f"final background CSS does not follow the neutralizer for {preset}")

        pages: list[dict[str, Any]] = []
        for index, job in enumerate(preset_jobs):
            number = index + 1
            record = records_by_index[index]
            try:
                paths = {
                    key: _path_from_job(job, key, preset, number)
                    for key in (
                        "reference_screenshot",
                        "protected_mask",
                        "prompt",
                        "model_output",
                        "final_background",
                        "qa_report",
                    )
                }
            except BatchQaError as exc:
                errors.extend(exc.errors)
                continue
            resolved = {
                key: _resolve_repo_path(repo_root, value, f"{preset} slide {number} {key}")
                for key, value in paths.items()
            }
            for key in ("reference_screenshot", "protected_mask", "prompt", "model_output", "final_background"):
                _ensure_file(resolved[key], f"{key} for {preset} slide {number}", errors)
            for key in ("reference_screenshot", "protected_mask", "prompt", "model_output", "final_background"):
                try:
                    run_value = _run_record_path(record, key, f"run {key} for {preset} slide {number}")
                    if run_value != paths[key]:
                        errors.append(f"run/job {key} mismatch for {preset} slide {number}: {run_value} != {paths[key]}")
                except BatchQaError as exc:
                    errors.extend(exc.errors)

            model_hash = _sha256(resolved["model_output"]) if resolved["model_output"].is_file() else None
            adjacent_hash = _sha256(resolved["final_background"]) if resolved["final_background"].is_file() else None
            if model_hash and adjacent_hash and model_hash != adjacent_hash:
                errors.append(f"model output hash does not match adjacent copy for {preset} slide {number}")
            for declared_hash in _declared_hashes(record, "model_output"):
                if model_hash and declared_hash != model_hash:
                    errors.append(f"declared model output hash mismatch for {preset} slide {number}")
            for declared_hash in _declared_hashes(record, "final_background"):
                if adjacent_hash and declared_hash != adjacent_hash:
                    errors.append(f"declared adjacent background hash mismatch for {preset} slide {number}")
            output_hashes = job.get("output_hashes")
            if isinstance(output_hashes, Mapping):
                for key, actual in (
                    ("model_output_sha256", model_hash),
                    ("final_background_sha256", adjacent_hash),
                ):
                    declared_hash = output_hashes.get(key)
                    if declared_hash not in (None, actual):
                        errors.append(f"job queue {key} mismatch for {preset} slide {number}")
            embedded_hash = embedded_hashes[index] if index < len(embedded_hashes) else None
            if adjacent_hash and embedded_hash and embedded_hash != adjacent_hash:
                errors.append(f"embedded raster hash does not match adjacent copy for {preset} slide {number}")

            slide = slides[index]
            if slide.get("data-pptx-background-image") != "true":
                errors.append(f"missing data-pptx-background-image=true for {preset} slide {number}")
            if slide.get("data-pptx-background-image-embedded") != "true":
                errors.append(f"missing data-pptx-background-image-embedded=true for {preset} slide {number}")
            src = slide.get("data-pptx-background-image-src")
            try:
                src_portable = _portable_path(src, f"PPTX background src for {preset} slide {number}", allow_dot_prefix=True)
                src_resolved = (final_path.parent / PurePosixPath(src_portable)).resolve()
                if src_resolved != resolved["final_background"].resolve():
                    errors.append(f"PPTX background src does not resolve to adjacent copy for {preset} slide {number}")
            except BatchQaError as exc:
                errors.extend(exc.errors)

            try:
                base_colors, foreground_colors = _machine_palette(record, preset, number)
            except BatchQaError as exc:
                errors.extend(exc.errors)
                base_colors, foreground_colors = [], []
            pages.append(
                {
                    "slide_index": index,
                    "slide_number": number,
                    "job_id": job.get("job_id"),
                    "paths": paths,
                    "hashes": {
                        "model_output_sha256": model_hash,
                        "adjacent_copy_sha256": adjacent_hash,
                        "embedded_raster_sha256": embedded_hash,
                    },
                    "machine_qa_inputs": {
                        "base_colors": base_colors,
                        "foreground_colors": foreground_colors,
                    },
                    "human_review_required": True,
                }
            )

        decks.append(
            {
                "preset": preset,
                "slide_count": len(preset_jobs),
                "source_html": source_html_rel,
                "source_html_sha256": source_sha_before,
                "source_manifest": source_manifest_rel,
                "run_manifest": run_rel,
                "final_html": final_rel,
                "final_html_sha256": final_sha_before,
                "run": run,
                "human_review": _human_review(run),
                "static_background_order_pass": static_order_pass,
                "pages": pages,
            }
        )

    unknown_job_presets = sorted(set(jobs_by_preset) - set(plan_by_preset))
    if unknown_job_presets:
        errors.append(f"job queue contains unknown Presets: {unknown_job_presets}")
    dynamic_total = sum(deck["slide_count"] for deck in decks)
    if not errors and dynamic_total != len(queue_jobs):
        errors.append(f"validated dynamic page total mismatch: decks={dynamic_total}, jobs={len(queue_jobs)}")
    if errors:
        raise BatchQaError(errors)
    return {
        "batch_plan": _relative(batch_plan_path, repo_root, "batch plan"),
        "job_queue": _relative(job_queue_path, repo_root, "job queue"),
        "preset_count": len(decks),
        "slide_count": dynamic_total,
        "decks": decks,
    }


def _report_paths(deck: Mapping[str, Any], repo_root: Path) -> dict[str, str]:
    run_path = _resolve_repo_path(repo_root, deck["run_manifest"], "run manifest")
    qa = run_path.parent / "qa"
    return {
        "pre_generation_text_geometry": _relative(
            qa / "pre-generation-html-text-geometry.json",
            repo_root,
            "pre-generation text geometry report",
        ),
        "final_text_geometry": _relative(
            qa / "final-html-text-geometry.json",
            repo_root,
            "final text geometry report",
        ),
        "ownership": _relative(qa / "final-html-css-ownership.json", repo_root, "ownership report"),
        "geometry": _relative(qa / "final-html-css-geometry.json", repo_root, "geometry report"),
        "visual": _relative(qa / "final-html-visual-contract.json", repo_root, "visual report"),
        "selection": _relative(qa / "final-html-selection-panel.json", repo_root, "selection report"),
        "interactions": _relative(qa / "final-html-edit-interactions.json", repo_root, "interaction report"),
        "object_tree": _relative(qa / "final-html-object-tree.json", repo_root, "object-tree report"),
        "pptx": _relative(qa / "final-html-pptx-export.json", repo_root, "PPTX report"),
        "pptx_output": _relative(qa / "final-html-exported.pptx", repo_root, "PPTX output"),
        "capture": _relative(qa / "final-html-composite-capture.json", repo_root, "capture report"),
        "capture_dir": _relative(qa / "composite-captures", repo_root, "capture directory"),
        "computed_background": _relative(qa / "final-html-computed-background.json", repo_root, "computed background report"),
    }


def _commands_for_deck(deck: Mapping[str, Any], repo_root: Path) -> list[CommandSpec]:
    preset = str(deck["preset"])
    source_html = str(deck["source_html"])
    html = str(deck["final_html"])
    manifest = str(deck["source_manifest"])
    reports = _report_paths(deck, repo_root)
    commands = [
        CommandSpec(
            f"{preset}/pre-generation-text-geometry",
            preset,
            "text_geometry_pre_generation",
            (
                "node", "scripts/qa_html_text_geometry.cjs", "--file", source_html,
                "--report", reports["pre_generation_text_geometry"],
            ),
            (
                "node", "scripts/qa_html_text_geometry.cjs", "--file", source_html,
                "--report", reports["pre_generation_text_geometry"],
            ),
            reports["pre_generation_text_geometry"],
            subject_html=source_html,
        ),
        CommandSpec(
            f"{preset}/final-text-geometry",
            preset,
            "text_geometry_final",
            (
                "node", "scripts/qa_html_text_geometry.cjs", "--file", html,
                "--report", reports["final_text_geometry"],
            ),
            (
                "node", "scripts/qa_html_text_geometry.cjs", "--file", html,
                "--report", reports["final_text_geometry"],
            ),
            reports["final_text_geometry"],
            subject_html=html,
        ),
        CommandSpec(
            f"{preset}/html-css-ownership", preset, "ownership",
            ("python", "scripts/html_css_ownership.py", "--html", html, "--manifest", manifest),
            ("python", "scripts/html_css_ownership.py", "--html", html, "--manifest", manifest),
            reports["ownership"], capture_stdout_json=True,
        ),
        CommandSpec(
            f"{preset}/css-geometry-invariant", preset, "geometry",
            ("node", "scripts/qa_html_css_geometry_invariant.cjs", "--file", html, "--report", reports["geometry"]),
            ("node", "scripts/qa_html_css_geometry_invariant.cjs", "--file", html, "--report", reports["geometry"]),
            reports["geometry"],
        ),
        CommandSpec(
            f"{preset}/visual-contract", preset, "visual",
            ("node", "scripts/qa_html_visual_contract.cjs", "--file", html, "--report", reports["visual"]),
            ("node", "scripts/qa_html_visual_contract.cjs", "--file", html, "--report", reports["visual"]),
            reports["visual"],
        ),
        CommandSpec(
            f"{preset}/selection-panel-placement", preset, "selection",
            (
                "node", "scripts/qa_html_selection_panel_placement.cjs", "--html", html,
                "--selector", ".slide.active .el:is(.cover-title,.cover-center-title,.cover-split-title,.prod-title)",
                "--report", reports["selection"],
            ),
            (
                "node", "scripts/qa_html_selection_panel_placement.cjs", "--html", html,
                "--selector", ".slide.active .el:is(.cover-title,.cover-center-title,.cover-split-title,.prod-title)",
                "--report", reports["selection"],
            ),
            reports["selection"],
        ),
        CommandSpec(
            f"{preset}/edit-interactions", preset, "interactions",
            ("node", "scripts/qa_html_edit_interactions.cjs", "--html", html, "--report", reports["interactions"]),
            ("node", "scripts/qa_html_edit_interactions.cjs", "--html", html, "--report", reports["interactions"]),
            reports["interactions"],
        ),
        CommandSpec(
            f"{preset}/repeat-object-tree", preset, "object_tree",
            ("node", "scripts/qa_html_repeat_group.cjs", "--html", html, "--report", reports["object_tree"]),
            ("node", "scripts/qa_html_repeat_group.cjs", "--html", html, "--report", reports["object_tree"]),
            reports["object_tree"],
        ),
        CommandSpec(
            f"{preset}/pptx-browser-export-package", preset, "pptx",
            (
                "node", "scripts/qa_html_pptx_browser_export.cjs", "--html", html,
                "--output", reports["pptx_output"], "--report", reports["pptx"],
                "--sentinel", f"V6-BACKGROUND-QA-{preset}",
            ),
            (
                "node", "scripts/qa_html_pptx_browser_export.cjs", "--html", html,
                "--output", reports["pptx_output"], "--report", reports["pptx"],
                "--sentinel", f"V6-BACKGROUND-QA-{preset}",
            ),
            reports["pptx"], expected_output=reports["pptx_output"],
        ),
        CommandSpec(
            f"{preset}/capture-composite", preset, "capture",
            (
                "node", "scripts/capture_html_matrix.cjs", "--html-dir",
                _relative(_resolve_repo_path(repo_root, html, "final HTML").parent, repo_root, "HTML directory"),
                "--file", Path(html).name, "--output-dir", reports["capture_dir"],
                "--report", reports["capture"],
            ),
            (
                "node", "scripts/capture_html_matrix.cjs", "--html-dir",
                _relative(_resolve_repo_path(repo_root, html, "final HTML").parent, repo_root, "HTML directory"),
                "--file", Path(html).name, "--output-dir", reports["capture_dir"],
                "--report", reports["capture"],
            ),
            reports["capture"], expected_output=reports["capture_dir"],
        ),
        CommandSpec(
            f"{preset}/computed-background-wins-neutralizer", preset, "computed_background",
            ("node", "-e", COMPUTED_BACKGROUND_PROBE_JS, html, reports["computed_background"]),
            ("node", "-e", "<inline-computed-background-probe>", html, reports["computed_background"]),
            reports["computed_background"],
        ),
    ]
    for page in deck["pages"]:
        number = int(page["slide_number"])
        paths = page["paths"]
        qa_inputs = page["machine_qa_inputs"]
        argv: list[str] = [
            "python", "scripts/qa_html_image_background.py",
            "--raster", paths["final_background"],
            "--mask", paths["protected_mask"],
            "--source-raster", paths["model_output"],
            "--provenance-json", deck["run_manifest"],
            "--output", paths["qa_report"],
        ]
        for color in qa_inputs["base_colors"]:
            argv.extend(("--base-color", color))
        for color in qa_inputs["foreground_colors"]:
            argv.extend(("--foreground-color", color))
        commands.append(
            CommandSpec(
                f"{preset}/slide-{number:03d}/background-machine-qa",
                preset,
                "machine_background",
                tuple(argv),
                tuple(argv),
                paths["qa_report"],
                slide_number=number,
            )
        )
    return commands


def _default_executor(argv: Sequence[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv),
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def _report_status(kind: str, report: Mapping[str, Any], expected_slides: int) -> tuple[str, list[str]]:
    issues: list[str] = []
    if kind in {"text_geometry_pre_generation", "text_geometry_final"}:
        status = report.get("status")
        if status in {"runtime-error", "runtime-blocked"}:
            error = report.get("error")
            detail = str(error).splitlines()[0] if isinstance(error, str) and error else "unknown runtime error"
            return "blocked", [f"text geometry runtime blocked: {detail}"]
        checks = report.get("checks")
        if status != "pass":
            outside = checks.get("textOutsideModule") if isinstance(checks, Mapping) else None
            overlap = checks.get("textLayerOverlap") if isinstance(checks, Mapping) else None
            return "fail", [
                f"text geometry report status is not pass "
                f"(textOutsideModule={outside}, textLayerOverlap={overlap})"
            ]
        valid = (
            report.get("schemaVersion") == "html-text-geometry-v1"
            and report.get("inputUnchanged") is True
            and isinstance(checks, Mapping)
            and checks.get("slides") == expected_slides
            and checks.get("textOutsideModule") == 0
            and checks.get("textLayerOverlap") == 0
        )
        if valid:
            return "pass", []
        return "fail", [
            "text geometry report is incomplete or contains outside/overlap failures"
        ]
    if kind == "machine_background":
        overall = report.get("overall")
        status = overall.get("status") if isinstance(overall, Mapping) else None
        if status not in {"pass", "partial", "fail"}:
            return "fail", ["machine QA report has no valid overall.status"]
        contract = report.get("contract")
        if not isinstance(contract, Mapping) or contract.get("human_visual_review_required") is not True:
            issues.append("machine QA report must declare human_visual_review_required=true")
        if issues:
            return "fail", issues
        return str(status), []
    if kind in {"geometry", "visual"}:
        return ("pass", []) if report.get("status") == "pass" else ("fail", [f"{kind} report status is not pass"])
    if kind == "capture":
        report_issues = report.get("issues")
        immutability = report.get("sourceImmutability")
        violations = immutability.get("violations") if isinstance(immutability, Mapping) else None
        capture_ok = (
            isinstance(report_issues, list)
            and not report_issues
            and report.get("slides") == expected_slides
            and isinstance(violations, list)
            and not violations
        )
        return ("pass", []) if capture_ok else ("fail", ["composite capture report is incomplete or has issues"])
    if kind == "pptx":
        package = report.get("package")
        checks = report.get("checks")
        package_ok = isinstance(package, Mapping) and (
            package.get("expectedBackgrounds") == expected_slides
            and package.get("layoutRasterBackgrounds") == expected_slides
            and package.get("slidePictureObjects") == 0
            and package.get("fidelityOverlayObjects") == 0
        )
        checks_ok = isinstance(checks, Mapping) and all(
            checks.get(key) is True
            for key in ("backgroundImagesOnLayouts", "backgroundParity", "contentMode", "nativeTextLayout")
        )
        if report.get("pass") is True and package_ok and checks_ok:
            return "pass", []
        return "fail", ["PPTX browser export/package contract did not pass"]
    if kind == "computed_background":
        slides = report.get("slides")
        if report.get("pass") is True and isinstance(slides, list) and len(slides) == expected_slides:
            return "pass", []
        return "fail", ["computed raster background did not win the neutralizer on every slide"]
    return ("pass", []) if report.get("pass") is True else ("fail", [f"{kind} report pass is not true"])


def _invoke(
    spec: CommandSpec,
    *,
    repo_root: Path,
    final_html: Path,
    expected_slides: int,
    executor: Executor,
) -> dict[str, Any]:
    report_path = _resolve_repo_path(repo_root, spec.report, f"report for {spec.command_id}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    subject_html = (
        _resolve_repo_path(repo_root, spec.subject_html, f"subject HTML for {spec.command_id}")
        if spec.subject_html
        else final_html
    )
    before = _sha256(subject_html)
    try:
        result = executor(spec.argv, cwd=repo_root)
        returncode = int(result.returncode)
        stdout = result.stdout or ""
    except OSError as exc:
        if spec.kind in {"text_geometry_pre_generation", "text_geometry_final"}:
            runtime_issue = (
                f"text geometry runtime blocked: {exc.__class__.__name__} "
                f"errno={getattr(exc, 'errno', None)} winerror={getattr(exc, 'winerror', None)}"
            )
            payload = {
                "schemaVersion": "html-text-geometry-v1",
                "file": spec.subject_html or _relative(subject_html, repo_root, "subject HTML"),
                "status": "runtime-blocked",
                "runtimeStatus": "blocked",
                "errorType": exc.__class__.__name__,
                "errno": getattr(exc, "errno", None),
                "winerror": getattr(exc, "winerror", None),
            }
            _write_json_atomic(report_path, payload)
            return {
                "command_id": spec.command_id,
                "kind": spec.kind,
                "slide_number": spec.slide_number,
                "argv": list(spec.display_argv),
                "report": spec.report,
                "report_sha256": _sha256(report_path),
                "status": "blocked",
                "runtime_status": "blocked",
                "returncode": None,
                "human_review_required": False,
                "issues": [runtime_issue],
            }
        return {
            "command_id": spec.command_id,
            "kind": spec.kind,
            "slide_number": spec.slide_number,
            "argv": list(spec.display_argv),
            "report": spec.report,
            "status": "fail",
            "returncode": None,
            "human_review_required": spec.kind == "machine_background",
            "issues": [f"command launch failed: {exc.__class__.__name__}"],
        }
    after = _sha256(subject_html)
    issues: list[str] = []
    if before != after:
        issues.append("QA command modified its subject HTML")
    if spec.capture_stdout_json:
        try:
            payload = json.loads(stdout)
            report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except (json.JSONDecodeError, OSError) as exc:
            issues.append(f"unable to persist command JSON output: {exc.__class__.__name__}")
    if not report_path.is_file():
        issues.append("expected QA report is missing")
        report: dict[str, Any] = {}
        report_sha = None
        report_status = "fail"
    else:
        report_sha = _sha256(report_path)
        try:
            report = _load_json(report_path, f"report for {spec.command_id}")
            report_status, report_issues = _report_status(spec.kind, report, expected_slides)
            issues.extend(report_issues)
        except BatchQaError as exc:
            report_status = "fail"
            issues.extend(exc.errors)
    runtime_blocked = report_status == "blocked" and returncode == 2 and before == after
    if returncode != 0:
        if runtime_blocked:
            issues.append("text geometry runtime blocked: command returned 2")
        else:
            issues.append(f"command returned {returncode}")
    if spec.expected_output:
        output_path = _resolve_repo_path(repo_root, spec.expected_output, f"output for {spec.command_id}")
        if spec.kind == "capture":
            captures = list(output_path.rglob("*.jpg")) + list(output_path.rglob("*.png")) if output_path.is_dir() else []
            if len(captures) < expected_slides:
                issues.append(f"capture output has {len(captures)} images; expected at least {expected_slides}")
        elif not output_path.is_file():
            issues.append("expected command output is missing")
    status = "blocked" if runtime_blocked else (
        "fail" if issues or report_status == "fail" else report_status
    )
    return {
        "command_id": spec.command_id,
        "kind": spec.kind,
        "slide_number": spec.slide_number,
        "argv": list(spec.display_argv),
        "report": spec.report,
        "report_sha256": report_sha,
        "status": status,
        "runtime_status": "blocked" if status == "blocked" else None,
        "returncode": returncode,
        "human_review_required": spec.kind == "machine_background",
        "issues": issues,
    }


def _planned(spec: CommandSpec) -> dict[str, Any]:
    return {
        "command_id": spec.command_id,
        "kind": spec.kind,
        "slide_number": spec.slide_number,
        "argv": list(spec.display_argv),
        "report": spec.report,
        "status": "planned",
        "human_review_required": spec.kind == "machine_background",
    }


def _classification(mode: str, decks: Sequence[Mapping[str, Any]], commands: Sequence[Mapping[str, Any]]) -> str:
    if any(command.get("status") == "fail" for command in commands):
        return "fail"
    if any(deck["human_review"]["status"] == "rejected" for deck in decks):
        return "fail"
    if mode == "check":
        return "partial"
    machine_partial = any(command.get("status") in {"partial", "blocked"} for command in commands)
    human_pending = any(deck["human_review"]["status"] != "accepted" for deck in decks)
    return "partial" if machine_partial or human_pending else "pass"


def build_final_ledger(
    *,
    batch_plan_path: Path,
    job_queue_path: Path,
    repo_root: Path = REPO_ROOT,
    mode: str = "check",
    executor: Executor | None = None,
) -> dict[str, Any]:
    """Validate, optionally execute, and return the final QA ledger payload."""

    if mode not in {"check", "write"}:
        raise BatchQaError([f"unsupported mode: {mode}"])
    repo_root = repo_root.resolve()
    inventory = _static_inventory(
        repo_root=repo_root,
        batch_plan_path=batch_plan_path.resolve(),
        job_queue_path=job_queue_path.resolve(),
    )
    execute = executor or _default_executor
    all_command_results: list[dict[str, Any]] = []
    deck_ledgers: list[dict[str, Any]] = []
    for deck in inventory["decks"]:
        specs = _commands_for_deck(deck, repo_root)
        final_html = _resolve_repo_path(repo_root, deck["final_html"], f"final HTML for {deck['preset']}")
        if mode == "write":
            results = [
                _invoke(
                    spec,
                    repo_root=repo_root,
                    final_html=final_html,
                    expected_slides=int(deck["slide_count"]),
                    executor=execute,
                )
                for spec in specs
            ]
        else:
            results = [_planned(spec) for spec in specs]
        after_hash = _sha256(final_html)
        if after_hash != deck["final_html_sha256"]:
            results.append(
                {
                    "command_id": f"{deck['preset']}/source-immutability",
                    "kind": "source_immutability",
                    "slide_number": None,
                    "argv": [],
                    "report": None,
                    "status": "fail",
                    "returncode": None,
                    "issues": ["final.html changed during the QA batch"],
                }
            )
        all_command_results.extend(results)
        deck_ledgers.append(
            {
                "preset": deck["preset"],
                "slide_count": deck["slide_count"],
                "source_html": deck["source_html"],
                "source_html_sha256": deck["source_html_sha256"],
                "source_manifest": deck["source_manifest"],
                "run_manifest": deck["run_manifest"],
                "final_html": deck["final_html"],
                "final_html_sha256": after_hash,
                "human_review": deck["human_review"],
                "human_review_required": True,
                "pages": deck["pages"],
                "commands": [result["command_id"] for result in results],
            }
        )

    status = _classification(mode, deck_ledgers, all_command_results)
    required_kinds = {
        "text_geometry_pre_generation",
        "text_geometry_final",
        "ownership",
        "geometry",
        "visual",
        "selection",
        "interactions",
        "object_tree",
        "pptx",
        "capture",
        "computed_background",
        "machine_background",
    }
    actual_kinds = {str(command.get("kind")) for command in all_command_results}
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "mode": mode,
        "classification": status,
        "human_review_required": True,
        "machine_pass_can_release": False,
        "inputs": {
            "batch_plan": inventory["batch_plan"],
            "job_queue": inventory["job_queue"],
        },
        "summary": {
            "preset_count": inventory["preset_count"],
            "slide_count": inventory["slide_count"],
            "commands": len(all_command_results),
            "passed": sum(command.get("status") == "pass" for command in all_command_results),
            "partial": sum(command.get("status") == "partial" for command in all_command_results),
            "blocked": sum(command.get("status") == "blocked" for command in all_command_results),
            "failed": sum(command.get("status") == "fail" for command in all_command_results),
            "planned": sum(command.get("status") == "planned" for command in all_command_results),
            "human_reviews_accepted": sum(deck["human_review"]["status"] == "accepted" for deck in deck_ledgers),
            "human_reviews_pending": sum(deck["human_review"]["status"] == "pending" for deck in deck_ledgers),
            "human_reviews_rejected": sum(deck["human_review"]["status"] == "rejected" for deck in deck_ledgers),
        },
        "gates": {
            "exact_18_presets": inventory["preset_count"] == EXPECTED_PRESET_COUNT,
            "dynamic_page_inventory": inventory["slide_count"] == sum(deck["slide_count"] for deck in deck_ledgers),
            "model_adjacent_embedded_hash_parity": True,
            "pptx_background_attributes": True,
            "computed_background_wins_neutralizer": (
                "planned" if mode == "check" else all(
                    command.get("status") == "pass"
                    for command in all_command_results
                    if command.get("kind") == "computed_background"
                )
            ),
            "pre_generation_text_geometry": (
                "planned" if mode == "check" else all(
                    command.get("status") == "pass"
                    for command in all_command_results
                    if command.get("kind") == "text_geometry_pre_generation"
                )
            ),
            "final_text_geometry": (
                "planned" if mode == "check" else all(
                    command.get("status") == "pass"
                    for command in all_command_results
                    if command.get("kind") == "text_geometry_final"
                )
            ),
            "references_masks_prompts_present": True,
            "qa_reports_complete": (
                "planned" if mode == "check" else all(
                    command.get("status") in {"pass", "partial"}
                    for command in all_command_results
                )
            ),
            "portable_paths": True,
            "required_command_kinds": sorted(required_kinds),
            "required_command_kinds_complete": required_kinds.issubset(actual_kinds),
            "human_review_required": True,
        },
        "presets": deck_ledgers,
        "commands": all_command_results,
    }
    portability_errors = _reject_nonportable_strings(ledger, "final-ledger")
    if portability_errors:
        raise BatchQaError(portability_errors)
    return ledger


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Orchestrate the final v6 HTML image-background QA batch")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Validate inventory and list QA commands without running them")
    mode.add_argument("--write", action="store_true", help="Run QA commands and write qa/final-ledger.json")
    parser.add_argument("--batch-plan", required=True)
    parser.add_argument("--job-queue", required=True)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--output", help="Ledger path; defaults to <job-queue-dir>/qa/final-ledger.json")
    return parser


def run_cli(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    try:
        batch_plan = _resolve_cli_path(repo_root, args.batch_plan, "batch plan")
        job_queue = _resolve_cli_path(repo_root, args.job_queue, "job queue")
        output = (
            _resolve_cli_path(repo_root, args.output, "ledger output")
            if args.output
            else job_queue.parent / "qa" / "final-ledger.json"
        )
        mode = "write" if args.write else "check"
        ledger = build_final_ledger(
            batch_plan_path=batch_plan,
            job_queue_path=job_queue,
            repo_root=repo_root,
            mode=mode,
        )
        if args.write:
            _write_json_atomic(output, ledger)
        summary = {
            "mode": mode,
            "classification": ledger["classification"],
            "preset_count": ledger["summary"]["preset_count"],
            "slide_count": ledger["summary"]["slide_count"],
            "human_reviews_pending": ledger["summary"]["human_reviews_pending"],
            "ledger": _relative(output, repo_root, "ledger output") if args.write else None,
            "commands": ledger["commands"] if args.check else len(ledger["commands"]),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1 if ledger["classification"] == "fail" else 0
    except BatchQaError as exc:
        print(json.dumps({"status": "fail", "errors": exc.errors}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
