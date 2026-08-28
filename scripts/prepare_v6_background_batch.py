#!/usr/bin/env python3
"""Prepare every formal v6 new-deck for per-slide image generation.

The script is deliberately orchestration-only: the formal renderer owns HTML,
``html_image_background_experiment.py`` owns the measurement/materialization
contract, and ``capture_html_image_background_inputs.cjs`` owns browser
capture.  Existing runs are never overwritten unless their source HTML hash
matches and the caller explicitly asks to resume them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = (
    ROOT
    / "artifacts"
    / "experiments"
    / "html-image-background"
    / "html-preset-regeneration-20260813-v6"
    / "formal-background-runs"
)
FORMAL_RENDERER = "scripts/render_randomized_html_demo.py"
CANVAS_WIDTH = 1920
CANVAS_HEIGHT = 1080


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portable(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"Project path escaped repository root: {resolved}") from exc


def _resolve_portable(value: str, label: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ":" in value or "\\" in value:
        raise ValueError(f"{label} must be repository-relative POSIX: {value}")
    resolved = (ROOT / path).resolve()
    if ROOT.resolve() not in resolved.parents:
        raise ValueError(f"{label} escaped repository root: {value}")
    return resolved


def _load_plan(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("content_mode") != "new-deck" or payload.get("preset_demo") is not False:
        raise ValueError("batch-plan must declare content_mode=new-deck and preset_demo=false")
    renderer = payload.get("renderer")
    if renderer is not None and renderer != FORMAL_RENDERER:
        raise ValueError(f"batch-plan must use the formal renderer: {FORMAL_RENDERER}")
    preset_count = payload.get("preset_count")
    if preset_count is not None and preset_count != 18:
        raise ValueError("batch-plan preset_count must be 18")
    rows = payload.get("presets")
    if not isinstance(rows, list) or len(rows) != 18:
        raise ValueError("batch-plan must contain exactly 18 Presets")
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("batch-plan Preset entries must be objects")
    ids = [str(row.get("preset_id") or "") for row in rows]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("batch-plan Preset ids must be present and unique")
    return rows


def _run(command: list[str], *, check_only: bool) -> None:
    if check_only:
        return
    subprocess.run(command, cwd=ROOT, check=True)


def _assert_resume(run_dir: Path, source_html: Path) -> None:
    manifest_path = run_dir / "run.json"
    if not manifest_path.is_file():
        raise ValueError(f"Cannot resume incomplete run without run.json: {run_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    recorded = manifest.get("source_html")
    recorded_path = Path(str(recorded)) if recorded else None
    if recorded_path is not None and not recorded_path.is_absolute():
        recorded_path = ROOT / recorded_path
    if not recorded_path or recorded_path.resolve() != source_html.resolve():
        raise ValueError(f"Run source mismatch for resume: {run_dir}")
    recorded_hash = manifest.get("source_html_sha256")
    if not recorded_hash:
        raise ValueError(f"Cannot resume run without a source hash: {run_dir}")
    if recorded_hash != _sha256(source_html):
        raise ValueError(f"Run source hash drift for resume: {run_dir}")


def _ordered_indexes(records: list[dict[str, Any]], label: str) -> list[int]:
    try:
        indexes = [int(record.get("index")) for record in records]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} records must contain integer slide indexes") from exc
    expected = list(range(len(records)))
    if sorted(indexes) != expected:
        raise ValueError(f"{label} slide indexes must be unique and contiguous: {indexes}")
    return indexes


def _assert_prepared_run(
    run_dir: Path,
    source_html: Path,
    expected_slides: int,
) -> dict[str, Any]:
    manifest_path = run_dir / "run.json"
    if not manifest_path.is_file():
        raise ValueError(f"prepare-deck did not write run.json: {run_dir}")
    prepared = json.loads(manifest_path.read_text(encoding="utf-8"))
    if prepared.get("mode") != "html-image-background-per-slide-experiment":
        raise ValueError(f"prepare-deck wrote an incompatible run manifest: {run_dir}")
    recorded_source = Path(str(prepared.get("source_html") or ""))
    if not recorded_source.is_absolute():
        recorded_source = ROOT / recorded_source
    if recorded_source.resolve() != source_html.resolve():
        raise ValueError(f"prepare-deck source mismatch: {run_dir}")
    if prepared.get("slide_count") != expected_slides:
        raise ValueError(
            f"prepare-deck page count mismatch: {prepared.get('slide_count')} != {expected_slides}"
        )
    specs = prepared.get("slide_specs")
    if not isinstance(specs, list) or len(specs) != expected_slides:
        raise ValueError(f"prepare-deck slide_specs must contain {expected_slides} records")
    _ordered_indexes(specs, "prepare-deck")
    ids = [str(spec.get("id") or "") for spec in specs]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("prepare-deck slide ids must be present and unique")
    mask_pages = prepared.get("mask_pages")
    if not isinstance(mask_pages, list) or len(mask_pages) != expected_slides:
        raise ValueError(f"prepare-deck mask_pages must contain {expected_slides} records")
    return prepared


def _mask_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"capture did not write masks.json: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records", payload) if isinstance(payload, dict) else payload
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise ValueError("masks.json must contain an array of per-slide records")
    return records


def _assert_capture_outputs(
    run_dir: Path,
    masks_path: Path,
    expected_layouts: list[Any],
    prepared_specs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records = _mask_records(masks_path)
    if len(records) != len(expected_layouts):
        raise ValueError(
            f"masks.json page count mismatch: {len(records)} != {len(expected_layouts)}"
        )
    _ordered_indexes(records, "masks.json")
    records = sorted(records, key=lambda row: int(row["index"]))
    specs = sorted(prepared_specs, key=lambda row: int(row["index"]))
    for index, record in enumerate(records):
        if record.get("id") != specs[index].get("id"):
            raise ValueError(f"masks.json slide id mismatch at index {index}")
        if record.get("layout_id") != expected_layouts[index]:
            raise ValueError(f"masks.json Layout mismatch at index {index}")
        contract = record.get("capture_contract")
        expected_contract = {
            "slide_only": True,
            "editor_chrome_hidden": True,
            "native_width": CANVAS_WIDTH,
            "native_height": CANVAS_HEIGHT,
        }
        if contract != expected_contract:
            raise ValueError(
                f"masks.json must record a {CANVAS_WIDTH}x{CANVAS_HEIGHT} slide-only capture "
                f"at index {index}: {contract}"
            )
        reference = record.get("source_reference") or record.get("reference_screenshot")
        reference_path = Path(str(reference)) if reference else None
        if reference_path is not None and not reference_path.is_absolute():
            reference_path = run_dir / reference_path
        if not reference_path or not reference_path.is_file():
            raise ValueError(f"masks.json clean reference is missing at index {index}")
        try:
            reference_path.resolve().relative_to(run_dir.resolve())
        except ValueError as exc:
            raise ValueError(
                f"masks.json clean reference escaped the run directory at index {index}"
            ) from exc
    return records


def _assert_materialized_run(
    run_dir: Path,
    expected_layouts: list[Any],
) -> dict[str, Any]:
    manifest_path = run_dir / "run.json"
    materialized = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = materialized.get("slide_records")
    if not isinstance(records, list) or len(records) != len(expected_layouts):
        actual = len(records) if isinstance(records, list) else 0
        raise ValueError(
            f"Materialized page count mismatch: {actual} != {len(expected_layouts)}"
        )
    _ordered_indexes(records, "materialized run")
    records = sorted(records, key=lambda row: int(row["index"]))
    for index, record in enumerate(records):
        if record.get("layout_id") != expected_layouts[index]:
            raise ValueError(f"Materialized Layout mismatch at index {index}")
    return materialized


def prepare_batch(
    batch_plan: Path,
    output_root: Path,
    *,
    check_only: bool,
    resume: bool,
) -> dict[str, Any]:
    batch_plan = batch_plan.resolve()
    batch_plan_portable = _portable(batch_plan)
    rows = _load_plan(batch_plan)
    output_root = output_root.resolve()
    if output_root != DEFAULT_OUTPUT_ROOT.resolve() and ROOT.resolve() not in output_root.parents:
        raise ValueError("output-root must stay inside the repository")
    if output_root.exists() and not resume and any(output_root.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty background root: {output_root}")

    records: list[dict[str, Any]] = []
    total_slides = 0
    for row in rows:
        preset_id = str(row["preset_id"])
        source_html = _resolve_portable(str(row["output_html"]), f"{preset_id}.output_html")
        if not source_html.is_file():
            raise FileNotFoundError(f"Formal HTML is missing for {preset_id}: {source_html}")
        manifest_value = row.get("output_manifest", row.get("manifest"))
        manifest_path = (
            _resolve_portable(str(manifest_value), f"{preset_id}.output_manifest")
            if manifest_value is not None
            else source_html.with_suffix(".manifest.json")
        )
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Formal manifest is missing for {preset_id}: {manifest_path}")
        formal_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if formal_manifest.get("content_mode") != "new-deck":
            raise ValueError(f"Formal manifest is not new-deck: {preset_id}")
        if formal_manifest.get("renderer_entrypoint") != FORMAL_RENDERER:
            raise ValueError(f"Formal manifest renderer mismatch: {preset_id}")
        preset_theme = formal_manifest.get("preset_theme")
        manifest_preset = (
            preset_theme.get("id") if isinstance(preset_theme, dict) else None
        )
        if manifest_preset != preset_id:
            raise ValueError(f"Formal manifest Preset mismatch: {preset_id}")
        slides = formal_manifest.get("layouts")
        if not isinstance(slides, list) or not slides:
            raise ValueError(f"Formal manifest has no Layout sequence: {preset_id}")
        if row.get("layouts") is not None and row["layouts"] != slides:
            raise ValueError(f"batch-plan/Layout manifest mismatch: {preset_id}")
        planned_pages = row.get("pages", row.get("slide_count"))
        if planned_pages is not None:
            try:
                planned_pages = int(planned_pages)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"batch-plan page count is invalid: {preset_id}") from exc
            if planned_pages != len(slides):
                raise ValueError(f"batch-plan/page manifest mismatch: {preset_id}")

        run_dir = output_root / preset_id
        if run_dir.exists():
            if not resume:
                raise FileExistsError(f"Refusing to overwrite background run: {run_dir}")
            _assert_resume(run_dir, source_html)
        else:
            _run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "html_image_background_experiment.py"),
                    "prepare-deck",
                    "--input",
                    str(source_html),
                    "--run-dir",
                    str(run_dir),
                ],
                check_only=check_only,
            )

        if not check_only:
            prepared_manifest_path = run_dir / "run.json"
            prepared = _assert_prepared_run(run_dir, source_html, len(slides))
            prepared["source_html_sha256"] = _sha256(source_html)
            prepared["formal_manifest"] = _portable(manifest_path)
            prepared["formal_manifest_sha256"] = _sha256(manifest_path)
            prepared_manifest_path.write_text(
                json.dumps(prepared, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            _run(
                [
                    "node",
                    str(ROOT / "scripts" / "capture_html_image_background_inputs.cjs"),
                    "--run-dir",
                    str(run_dir),
                ],
                check_only=False,
            )
            masks_path = run_dir / "masks.json"
            _assert_capture_outputs(
                run_dir,
                masks_path,
                slides,
                prepared["slide_specs"],
            )
            _run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "html_image_background_experiment.py"),
                    "materialize-deck",
                    "--run-dir",
                    str(run_dir),
                    "--masks-json",
                    str(masks_path),
                ],
                check_only=False,
            )
            materialized = _assert_materialized_run(run_dir, slides)
            actual_slides = len(materialized["slide_records"])
        else:
            actual_slides = len(slides)
        total_slides += actual_slides
        records.append(
            {
                "preset_id": preset_id,
                "source_html": _portable(source_html),
                "source_html_sha256": _sha256(source_html),
                "formal_manifest": _portable(manifest_path),
                "run_dir": _portable(run_dir),
                "masks_json": _portable(run_dir / "masks.json"),
                "slides": actual_slides,
                "status": "checked" if check_only else "masks-materialized",
            }
        )

    ledger = {
        "schema_version": 1,
        "mode": "formal-new-deck-html-image-background-inputs",
        "status": "checked" if check_only else "masks-materialized",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "batch_plan": batch_plan_portable,
        "output_root": _portable(output_root),
        "counts": {"presets": len(records), "slides": total_slides},
        "presets": records,
    }
    if not check_only:
        output_root.mkdir(parents=True, exist_ok=True)
        (output_root / "input-ledger.json").write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-plan", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    ledger = prepare_batch(
        args.batch_plan.resolve(),
        args.output_root.resolve(),
        check_only=args.check,
        resume=args.resume,
    )
    print(json.dumps(ledger, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
