"""Safely preserve one v6 model image and record durable provenance.

The job queue remains immutable.  This helper validates one selected job,
copies the model-native PNG byte-for-byte into that job's ``model-output``
path, and atomically installs a per-slide receipt.  It never records the
external generated-image directory; only the source basename and digest are
kept in the portable receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import sys
import uuid
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_SCHEMA_VERSION = "html-image-background-v6-job-queue-v2"
RECEIPT_SCHEMA_VERSION = "html-image-background-v6-generation-receipt-v1"
TARGET_ASPECT_RATIO = 16 / 9
ASPECT_RATIO_TOLERANCE = 0.005
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
HEX_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PRESET_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SHARD_RE = re.compile(r"^shard-[0-9]{2}$")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")


class ReceiptValidationError(ValueError):
    """Raised when a generation record cannot be proven safe/current."""

    def __init__(self, errors: str | Iterable[str]):
        if isinstance(errors, str):
            rows = [errors]
        else:
            rows = [str(row) for row in errors if str(row)]
        self.errors = list(dict.fromkeys(rows)) or ["unknown receipt validation error"]
        super().__init__("\n".join(self.errors))


@dataclass(frozen=True)
class PngInfo:
    width: int
    height: int
    byte_length: int
    sha256: str
    aspect_ratio: float
    relative_aspect_error: float


@dataclass(frozen=True)
class PreparedRecord:
    repo_root: Path
    queue_path: Path
    queue_relative: str
    queue_sha256: str
    job: Mapping[str, Any]
    job_id: str
    preset: str
    shard: str
    slide_number: int
    input_paths: Mapping[str, Path]
    input_relative_paths: Mapping[str, str]
    input_hashes: Mapping[str, str]
    source_path: Path
    source_info: PngInfo
    target_path: Path
    target_relative: str
    receipt_path: Path
    receipt_relative: str
    attempt: int
    decision: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReceiptValidationError(f"invalid {label}: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReceiptValidationError(f"{label} must contain a JSON object: {path}")
    return payload


def _portable_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReceiptValidationError(f"{label} must be a non-empty path string")
    raw = value.strip()
    if (
        raw.startswith(("/", "\\", "file://"))
        or WINDOWS_ABSOLUTE_RE.match(raw)
        or "\\" in raw
    ):
        raise ReceiptValidationError(
            f"{label} must be repository-relative POSIX, got: {value}"
        )
    pure = PurePosixPath(raw)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ReceiptValidationError(
            f"{label} must not be absolute or contain traversal: {value}"
        )
    return pure.as_posix()


def _inside(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ReceiptValidationError(f"{label} escapes repository root: {resolved}") from exc
    return resolved


def _resolve_repo_path(repo_root: Path, value: Any, label: str) -> tuple[Path, str]:
    portable = _portable_path(value, label)
    resolved = _inside(repo_root / PurePosixPath(portable), repo_root, label)
    return resolved, portable


def _resolve_queue_path(repo_root: Path, value: str | Path) -> tuple[Path, str]:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    resolved = _inside(candidate, repo_root, "job queue")
    if not resolved.is_file():
        raise ReceiptValidationError(f"job queue does not exist: {resolved}")
    relative = resolved.relative_to(repo_root.resolve()).as_posix()
    return resolved, _portable_path(relative, "job queue")


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not HEX_SHA256_RE.fullmatch(value):
        raise ReceiptValidationError(f"{label} must be a lowercase SHA256 digest")
    return value


def _positive_integer(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise ReceiptValidationError(f"{label} must be a positive integer")
    try:
        converted = int(value)
    except (TypeError, ValueError) as exc:
        raise ReceiptValidationError(f"{label} must be a positive integer") from exc
    if converted <= 0 or str(value).strip() != str(converted):
        raise ReceiptValidationError(f"{label} must be a positive integer")
    return converted


def _validate_attempt(value: Any) -> int:
    attempt = _positive_integer(value, "attempt")
    if attempt > 3:
        raise ReceiptValidationError("attempt must be between 1 and 3")
    return attempt


def _validate_decision(value: Any) -> str:
    if not isinstance(value, str):
        raise ReceiptValidationError("decision must be a non-empty string")
    decision = value.strip()
    if not decision or len(decision) > 240:
        raise ReceiptValidationError("decision must contain 1 to 240 characters")
    if any(ord(character) < 32 for character in decision):
        raise ReceiptValidationError("decision must not contain control characters")
    return decision


def _read_exact(handle: Any, count: int, label: str) -> bytes:
    value = handle.read(count)
    if len(value) != count:
        raise ReceiptValidationError(f"truncated PNG while reading {label}")
    return value


def _inspect_png(path: Path) -> PngInfo:
    if path.suffix.lower() != ".png" or not path.is_file():
        raise ReceiptValidationError(f"model source must be an existing PNG: {path}")
    width: int | None = None
    height: int | None = None
    saw_idat = False
    saw_iend = False
    try:
        with path.open("rb") as handle:
            if _read_exact(handle, len(PNG_SIGNATURE), "signature") != PNG_SIGNATURE:
                raise ReceiptValidationError(f"model source is not a PNG: {path}")
            chunk_index = 0
            while not saw_iend:
                length = struct.unpack(">I", _read_exact(handle, 4, "chunk length"))[0]
                chunk_type = _read_exact(handle, 4, "chunk type")
                if length > 256 * 1024 * 1024:
                    raise ReceiptValidationError("PNG chunk is unreasonably large")
                chunk_data = _read_exact(handle, length, chunk_type.decode("ascii", "replace"))
                declared_crc = struct.unpack(">I", _read_exact(handle, 4, "chunk CRC"))[0]
                actual_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
                if declared_crc != actual_crc:
                    raise ReceiptValidationError(
                        f"PNG CRC mismatch in {chunk_type.decode('ascii', 'replace')}"
                    )
                if chunk_index == 0 and chunk_type != b"IHDR":
                    raise ReceiptValidationError("PNG IHDR must be the first chunk")
                if chunk_type == b"IHDR":
                    if chunk_index != 0 or length != 13 or width is not None:
                        raise ReceiptValidationError("PNG has an invalid IHDR chunk")
                    width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                        ">IIBBBBB", chunk_data
                    )
                    if width <= 0 or height <= 0:
                        raise ReceiptValidationError("PNG dimensions must be positive")
                    if compression != 0 or filtering != 0 or interlace not in {0, 1}:
                        raise ReceiptValidationError("PNG IHDR methods are invalid")
                    valid_depths = {
                        0: {1, 2, 4, 8, 16},
                        2: {8, 16},
                        3: {1, 2, 4, 8},
                        4: {8, 16},
                        6: {8, 16},
                    }
                    if bit_depth not in valid_depths.get(color_type, set()):
                        raise ReceiptValidationError("PNG bit depth/color type is invalid")
                elif chunk_type == b"IDAT":
                    saw_idat = True
                elif chunk_type == b"IEND":
                    if length != 0:
                        raise ReceiptValidationError("PNG IEND must be empty")
                    saw_iend = True
                chunk_index += 1
            if handle.read(1):
                raise ReceiptValidationError("PNG contains trailing bytes after IEND")
    except OSError as exc:
        raise ReceiptValidationError(f"unable to read model source PNG: {path}: {exc}") from exc
    if width is None or height is None or not saw_idat or not saw_iend:
        raise ReceiptValidationError("PNG must contain IHDR, IDAT, and IEND chunks")
    aspect_ratio = width / height
    relative_error = abs(aspect_ratio - TARGET_ASPECT_RATIO) / TARGET_ASPECT_RATIO
    if relative_error > ASPECT_RATIO_TOLERANCE:
        raise ReceiptValidationError(
            f"model source PNG is {width}x{height} ({aspect_ratio:.6f}); "
            f"expected 16:9 within {ASPECT_RATIO_TOLERANCE:.3%} relative error"
        )
    return PngInfo(
        width=width,
        height=height,
        byte_length=path.stat().st_size,
        sha256=_sha256(path),
        aspect_ratio=aspect_ratio,
        relative_aspect_error=relative_error,
    )


def _selected_job(queue: Mapping[str, Any], job_id: str) -> Mapping[str, Any]:
    if queue.get("schema_version") != QUEUE_SCHEMA_VERSION:
        raise ReceiptValidationError(
            f"job queue schema must be {QUEUE_SCHEMA_VERSION}"
        )
    jobs = queue.get("jobs")
    if not isinstance(jobs, list):
        raise ReceiptValidationError("job queue jobs must be an array")
    matches = [row for row in jobs if isinstance(row, dict) and row.get("job_id") == job_id]
    if len(matches) != 1:
        raise ReceiptValidationError(
            f"job-id must identify exactly one queue job; found {len(matches)}: {job_id}"
        )
    return matches[0]


def _validate_membership(queue: Mapping[str, Any], job: Mapping[str, Any]) -> tuple[str, str, int]:
    job_id = str(job.get("job_id") or "")
    preset = str(job.get("preset") or "")
    shard = str(job.get("agent_shard") or "")
    if not PRESET_RE.fullmatch(preset):
        raise ReceiptValidationError(f"invalid job Preset id: {preset}")
    if not SHARD_RE.fullmatch(shard):
        raise ReceiptValidationError(f"invalid job shard id: {shard}")
    slide_number = _positive_integer(job.get("slide_number"), "slide_number")
    expected_job_id = f"{preset}/slide-{slide_number:03d}"
    if job_id != expected_job_id:
        raise ReceiptValidationError(
            f"job-id/preset/slide mismatch: expected {expected_job_id}, got {job_id}"
        )
    slide_index = job.get("slide_index")
    if slide_index is not None and slide_index != slide_number - 1:
        raise ReceiptValidationError(f"slide index mismatch for {job_id}")

    jobs = queue.get("jobs")
    assert isinstance(jobs, list)
    same_preset_shards = {
        str(row.get("agent_shard") or "")
        for row in jobs
        if isinstance(row, dict) and row.get("preset") == preset
    }
    if same_preset_shards != {shard}:
        raise ReceiptValidationError(
            f"Preset {preset} crosses shards: {sorted(same_preset_shards)}"
        )

    shards = queue.get("shards")
    if not isinstance(shards, list):
        raise ReceiptValidationError("job queue shards must be an array")
    shard_ids = [row.get("id") for row in shards if isinstance(row, dict)]
    if len(shard_ids) != len(set(shard_ids)):
        raise ReceiptValidationError("job queue contains duplicate shard ids")
    listed_in = [
        str(row.get("id") or "")
        for row in shards
        if isinstance(row, dict)
        and isinstance(row.get("presets"), list)
        and preset in row["presets"]
    ]
    if listed_in != [shard]:
        raise ReceiptValidationError(
            f"Preset {preset} must belong to exactly {shard}; shard listings={listed_in}"
        )

    presets = queue.get("presets")
    if not isinstance(presets, list):
        raise ReceiptValidationError("job queue presets must be an array")
    records = [
        row for row in presets if isinstance(row, dict) and row.get("preset") == preset
    ]
    if len(records) != 1:
        raise ReceiptValidationError(
            f"Preset {preset} must have exactly one queue record"
        )
    record = records[0]
    if record.get("agent_shard") != shard:
        raise ReceiptValidationError(f"Preset record shard mismatch for {preset}")
    job_ids = record.get("job_ids")
    if not isinstance(job_ids, list) or job_ids.count(job_id) != 1:
        raise ReceiptValidationError(
            f"job {job_id} must appear once in its Preset record"
        )
    foreign_records = [
        row.get("preset")
        for row in presets
        if isinstance(row, dict)
        and row.get("preset") != preset
        and isinstance(row.get("job_ids"), list)
        and job_id in row["job_ids"]
    ]
    if foreign_records:
        raise ReceiptValidationError(
            f"job {job_id} is also assigned to other Presets: {foreign_records}"
        )
    return preset, shard, slide_number


def _validate_job_paths(
    repo_root: Path,
    queue: Mapping[str, Any],
    job: Mapping[str, Any],
    preset: str,
    slide_number: int,
) -> tuple[dict[str, Path], dict[str, str], Path, str, Path, str]:
    paths = job.get("paths")
    if not isinstance(paths, dict):
        raise ReceiptValidationError("selected job paths must be an object")
    required = ("reference_screenshot", "protected_mask", "prompt", "model_output")
    missing = [name for name in required if name not in paths]
    if missing:
        raise ReceiptValidationError(f"selected job is missing paths: {missing}")

    resolved: dict[str, Path] = {}
    portable: dict[str, str] = {}
    for name, value in paths.items():
        path, relative = _resolve_repo_path(repo_root, value, f"job path {name}")
        resolved[str(name)] = path
        portable[str(name)] = relative

    source = job.get("source")
    if source is not None:
        if not isinstance(source, dict):
            raise ReceiptValidationError("selected job source must be an object")
        for name, value in source.items():
            _resolve_repo_path(repo_root, value, f"job source {name}")

    target = resolved["model_output"]
    model_relative = PurePosixPath(portable["model_output"])
    expected_filename = f"slide-{slide_number:03d}.png"
    if model_relative.name != expected_filename or model_relative.parent.name != "model-output":
        raise ReceiptValidationError(
            f"model_output path does not match job page: {portable['model_output']}"
        )
    run_relative = model_relative.parent.parent
    if run_relative.name != preset:
        raise ReceiptValidationError(
            f"model_output belongs to Preset {run_relative.name}, not {preset}"
        )
    run_dir = _inside(repo_root / run_relative, repo_root, "Preset run directory")

    expected_paths = {
        "reference_screenshot": run_relative
        / "references"
        / f"slide-{slide_number:03d}-clean-foreground.png",
        "protected_mask": run_relative
        / "masks"
        / f"protected-mask-{slide_number:03d}.png",
        "prompt": run_relative
        / "prompts"
        / f"slide-{slide_number:03d}-imagegen-prompt.txt",
        "model_output": run_relative / "model-output" / expected_filename,
    }
    for name, expected in expected_paths.items():
        if PurePosixPath(portable[name]) != expected:
            raise ReceiptValidationError(
                f"{name} path crosses page/Preset boundary: {portable[name]}"
            )
    if "run_manifest" in portable and PurePosixPath(portable["run_manifest"]) != run_relative / "run.json":
        raise ReceiptValidationError("run_manifest path crosses Preset boundary")
    for name, path in resolved.items():
        try:
            path.relative_to(run_dir)
        except ValueError as exc:
            raise ReceiptValidationError(
                f"job path {name} escapes Preset run directory: {portable[name]}"
            ) from exc

    jobs = queue.get("jobs")
    assert isinstance(jobs, list)
    collisions: list[str] = []
    for other in jobs:
        if not isinstance(other, dict) or other is job:
            continue
        other_paths = other.get("paths")
        if not isinstance(other_paths, dict) or "model_output" not in other_paths:
            continue
        _, other_relative = _resolve_repo_path(
            repo_root, other_paths["model_output"], "other job model_output"
        )
        if other_relative == portable["model_output"]:
            collisions.append(str(other.get("job_id") or "<unknown>"))
    if collisions:
        raise ReceiptValidationError(
            f"model_output target is shared with other jobs: {collisions}"
        )

    receipt_relative_path = run_relative / "receipts" / f"slide-{slide_number:03d}.json"
    receipt_path, receipt_relative = _resolve_repo_path(
        repo_root, receipt_relative_path.as_posix(), "receipt path"
    )
    return resolved, portable, target, portable["model_output"], receipt_path, receipt_relative


def _validate_inputs(
    job: Mapping[str, Any],
    paths: Mapping[str, Path],
    relative_paths: Mapping[str, str],
) -> tuple[dict[str, Path], dict[str, str], dict[str, str]]:
    output_hashes = job.get("output_hashes")
    if not isinstance(output_hashes, dict):
        raise ReceiptValidationError("selected job output_hashes must be an object")
    selected_paths: dict[str, Path] = {}
    selected_relative: dict[str, str] = {}
    selected_hashes: dict[str, str] = {}
    for name in ("prompt", "reference_screenshot", "protected_mask"):
        path = paths[name]
        if not path.is_file():
            raise ReceiptValidationError(f"current {name} input is missing: {path}")
        actual = _sha256(path)
        declared = _require_sha256(
            output_hashes.get(f"{name}_sha256"), f"queue {name} hash"
        )
        if actual != declared:
            raise ReceiptValidationError(
                f"{name} hash drift for {job.get('job_id')}: queue={declared}, current={actual}"
            )
        selected_paths[name] = path
        selected_relative[name] = relative_paths[name]
        selected_hashes[name] = actual
    return selected_paths, selected_relative, selected_hashes


def _prepare(
    *,
    repo_root: Path,
    job_queue: str | Path,
    job_id: str,
    model_source: str | Path,
    attempt: int,
    decision: str,
) -> PreparedRecord:
    repo_root = repo_root.resolve()
    if not repo_root.is_dir():
        raise ReceiptValidationError(f"repository root does not exist: {repo_root}")
    queue_path, queue_relative = _resolve_queue_path(repo_root, job_queue)
    queue_sha = _sha256(queue_path)
    queue = _load_json(queue_path, "job queue")
    job = _selected_job(queue, job_id)
    preset, shard, slide_number = _validate_membership(queue, job)
    paths, relative_paths, target, target_relative, receipt, receipt_relative = _validate_job_paths(
        repo_root, queue, job, preset, slide_number
    )
    input_paths, input_relative, input_hashes = _validate_inputs(
        job, paths, relative_paths
    )

    source = Path(model_source).expanduser().resolve()
    source_info = _inspect_png(source)
    if source == target:
        raise ReceiptValidationError("model source must not be the model_output target")
    output_hashes = job.get("output_hashes")
    assert isinstance(output_hashes, dict)
    queued_model_hash = output_hashes.get("model_output_sha256")
    if queued_model_hash is not None:
        declared_model_hash = _require_sha256(
            queued_model_hash, "queue model_output hash"
        )
        if declared_model_hash != source_info.sha256:
            raise ReceiptValidationError(
                "model source hash does not match the queue's declared model_output hash"
            )

    return PreparedRecord(
        repo_root=repo_root,
        queue_path=queue_path,
        queue_relative=queue_relative,
        queue_sha256=queue_sha,
        job=job,
        job_id=job_id,
        preset=preset,
        shard=shard,
        slide_number=slide_number,
        input_paths=input_paths,
        input_relative_paths=input_relative,
        input_hashes=input_hashes,
        source_path=source,
        source_info=source_info,
        target_path=target,
        target_relative=target_relative,
        receipt_path=receipt,
        receipt_relative=receipt_relative,
        attempt=_validate_attempt(attempt),
        decision=_validate_decision(decision),
    )


def _receipt_payload(prepared: PreparedRecord, recorded_at: str) -> dict[str, Any]:
    info = prepared.source_info
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "recorded_at": recorded_at,
        "status": "recorded",
        "tool": "image_gen__imagegen",
        "job": {
            "job_id": prepared.job_id,
            "preset_id": prepared.preset,
            "agent_shard": prepared.shard,
            "slide_number": prepared.slide_number,
        },
        "queue": {
            "path": prepared.queue_relative,
            "sha256": prepared.queue_sha256,
            "schema_version": QUEUE_SCHEMA_VERSION,
        },
        "generation": {
            "attempt": prepared.attempt,
            "decision": prepared.decision,
        },
        "inputs": {
            name: {
                "path": prepared.input_relative_paths[name],
                "sha256": prepared.input_hashes[name],
            }
            for name in ("prompt", "reference_screenshot", "protected_mask")
        },
        "model_source": {
            "basename": prepared.source_path.name,
            "sha256": info.sha256,
            "byte_length": info.byte_length,
            "format": "PNG",
            "native_dimensions": {"width": info.width, "height": info.height},
            "aspect_ratio": round(info.aspect_ratio, 8),
            "target_aspect_ratio": round(TARGET_ASPECT_RATIO, 8),
            "aspect_ratio_relative_error": round(info.relative_aspect_error, 8),
            "aspect_ratio_tolerance": ASPECT_RATIO_TOLERANCE,
        },
        "model_output": {
            "path": prepared.target_relative,
            "sha256": info.sha256,
            "byte_length": info.byte_length,
            "source_bytes_preserved": True,
            "copy_method": "shutil.copyfile-then-atomic-install",
        },
    }


def _validate_recorded_at(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ReceiptValidationError("receipt recorded_at is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReceiptValidationError("receipt recorded_at is invalid") from exc
    if parsed.tzinfo is None:
        raise ReceiptValidationError("receipt recorded_at must include a timezone")
    return value


def _validate_resume(prepared: PreparedRecord) -> bool:
    target_exists = prepared.target_path.exists() or prepared.target_path.is_symlink()
    receipt_exists = prepared.receipt_path.exists() or prepared.receipt_path.is_symlink()
    if target_exists and not prepared.target_path.is_file():
        raise ReceiptValidationError("existing model_output target is not a regular file")
    if receipt_exists and not prepared.receipt_path.is_file():
        raise ReceiptValidationError("existing receipt is not a regular file")
    if target_exists != receipt_exists:
        if target_exists:
            raise ReceiptValidationError(
                "existing model_output has no receipt; refusing unproven target"
            )
        raise ReceiptValidationError(
            "receipt exists but model_output is missing; refusing inconsistent resume"
        )
    if not target_exists:
        return False

    target_hash = _sha256(prepared.target_path)
    if target_hash != prepared.source_info.sha256:
        raise ReceiptValidationError(
            "existing model_output hash differs from the supplied model source"
        )
    receipt = _load_json(prepared.receipt_path, "generation receipt")
    recorded_at = _validate_recorded_at(receipt.get("recorded_at"))
    expected = _receipt_payload(prepared, recorded_at)
    if receipt != expected:
        raise ReceiptValidationError(
            "resume receipt is not completely consistent with the queue, inputs, source, attempt, and decision"
        )
    return True


def _fsync_file(path: Path) -> None:
    # Windows' os.fsync delegates to _commit(), which requires a descriptor
    # opened for writing even when the file content is already complete.
    with path.open("r+b") as handle:
        os.fsync(handle.fileno())


def _install_without_replace(temporary: Path, destination: Path) -> None:
    """Atomically expose a complete file while refusing destination overwrite."""

    try:
        os.link(temporary, destination)
    except FileExistsError as exc:
        raise ReceiptValidationError(
            f"destination appeared during record; refusing overwrite: {destination}"
        ) from exc
    except OSError as exc:
        raise ReceiptValidationError(
            f"unable to atomically install {destination}: {exc}"
        ) from exc


def _record_fresh(prepared: PreparedRecord) -> None:
    target_parent = prepared.target_path.parent
    receipt_parent = prepared.receipt_path.parent
    target_parent.mkdir(parents=True, exist_ok=True)
    receipt_parent.mkdir(parents=True, exist_ok=True)
    _inside(target_parent, prepared.repo_root, "model_output directory")
    _inside(receipt_parent, prepared.repo_root, "receipt directory")

    token = f"{os.getpid()}-{uuid.uuid4().hex}"
    target_temp = target_parent / f".{prepared.target_path.name}.{token}.tmp"
    receipt_temp = receipt_parent / f".{prepared.receipt_path.name}.{token}.tmp"
    target_installed = False
    try:
        shutil.copyfile(prepared.source_path, target_temp)
        _fsync_file(target_temp)
        copied_hash = _sha256(target_temp)
        if copied_hash != prepared.source_info.sha256:
            raise ReceiptValidationError(
                "byte-for-byte copy verification failed before model_output install"
            )

        payload = _receipt_payload(prepared, _utc_now())
        receipt_bytes = (
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        with receipt_temp.open("xb") as handle:
            handle.write(receipt_bytes)
            handle.flush()
            os.fsync(handle.fileno())

        _install_without_replace(target_temp, prepared.target_path)
        target_installed = True
        if _sha256(prepared.target_path) != prepared.source_info.sha256:
            raise ReceiptValidationError(
                "installed model_output hash does not equal model source hash"
            )
        _install_without_replace(receipt_temp, prepared.receipt_path)
    except Exception:
        if target_installed and not prepared.receipt_path.exists():
            try:
                prepared.target_path.unlink()
            except OSError:
                pass
        raise
    finally:
        target_temp.unlink(missing_ok=True)
        receipt_temp.unlink(missing_ok=True)

    if _sha256(prepared.target_path) != prepared.source_info.sha256:
        raise ReceiptValidationError("final model_output/source SHA256 mismatch")
    recorded = _load_json(prepared.receipt_path, "generation receipt")
    recorded_at = _validate_recorded_at(recorded.get("recorded_at"))
    if recorded != _receipt_payload(prepared, recorded_at):
        raise ReceiptValidationError("atomically written receipt failed verification")


def process_job(
    *,
    mode: str,
    repo_root: Path,
    job_queue: str | Path,
    job_id: str,
    model_source: str | Path,
    attempt: int,
    decision: str,
) -> dict[str, Any]:
    if mode not in {"check", "record"}:
        raise ReceiptValidationError("mode must be check or record")
    prepared = _prepare(
        repo_root=repo_root,
        job_queue=job_queue,
        job_id=job_id,
        model_source=model_source,
        attempt=attempt,
        decision=decision,
    )
    resume = _validate_resume(prepared)
    status = "resume-consistent" if resume else "ready-to-record"
    if mode == "record" and not resume:
        _record_fresh(prepared)
        status = "recorded"
    return {
        "status": status,
        "mode": mode,
        "job_id": prepared.job_id,
        "preset_id": prepared.preset,
        "agent_shard": prepared.shard,
        "model_output": prepared.target_relative,
        "model_output_sha256": prepared.source_info.sha256,
        "receipt": prepared.receipt_relative,
        "wrote_files": mode == "record" and not resume,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record or validate one durable v6 image-generation receipt"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Validate only; write nothing")
    mode.add_argument("--record", action="store_true", help="Copy and record one accepted PNG")
    parser.add_argument("--job-queue", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--model-source", required=True)
    parser.add_argument("--attempt", required=True, type=int)
    parser.add_argument("--decision", required=True)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    return parser


def run_cli(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = process_job(
            mode="record" if args.record else "check",
            repo_root=Path(args.repo_root),
            job_queue=args.job_queue,
            job_id=args.job_id,
            model_source=args.model_source,
            attempt=args.attempt,
            decision=args.decision,
        )
    except ReceiptValidationError as exc:
        for error in exc.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
