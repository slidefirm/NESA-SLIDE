#!/usr/bin/env python3
"""Read-only machine-proxy QA for an HTML slide raster background.

The tool never edits the raster or protected mask.  It measures a raster against
an aligned mask where black pixels are protected foreground regions, then emits
JSON.  Its contrast and detail checks operate on mask pixels, not actual glyph
pixels, so a machine pass is never presented as glyph-level or human approval.

Example:

    python scripts/qa_html_image_background.py \
      --raster path/to/background.png \
      --mask path/to/protected-mask.png \
      --base-color '#F2EFE5' --base-color '#FAF8F1' \
      --foreground-color 'ink=#102A36@4.5' \
      --foreground-color 'muted=#4E6269@4.5' \
      --output path/to/qa/background-proxy.json

Foreground syntax is NAME=#RRGGBB@MIN_CONTRAST.  The contrast suffix is optional
and defaults to 4.5.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Iterable

try:
    import numpy as np
except ImportError:  # pragma: no cover - exercised only in dependency-degraded environments
    np = None  # type: ignore[assignment]

try:
    from PIL import Image, ImageFilter, __version__ as PILLOW_VERSION
except ImportError:  # pragma: no cover - Pillow is a tracked project dependency
    Image = None  # type: ignore[assignment]
    ImageFilter = None  # type: ignore[assignment]
    PILLOW_VERSION = None


ROOT = Path(__file__).resolve().parents[1]
TARGET_ASPECT_RATIO = 16.0 / 9.0
RENDERER_READY_SIZE = (1920, 1080)

DEFAULT_THRESHOLDS: dict[str, float | int] = {
    "aspect_ratio_relative_tolerance": 0.005,
    "mask_black_threshold": 127,
    "contrast_fail_ratio": 0.01,
    "detail_partial_ratio": 0.001,
    "low_frequency_delta_e": 8.0,
    "low_frequency_fail_ratio": 0.01,
    "high_frequency_delta_e": 4.0,
    "high_frequency_fail_ratio": 0.01,
    "gradient_delta_e": 3.0,
    "blur_radius_on_mask_canvas_px": 32,
    "seam_band_radius_px": 16,
    "seam_cross_delta_e_p95": 3.0,
    "seam_cross_to_near_p95_ratio": 1.5,
    "seam_partial_delta_e_p95": 2.0,
    "seam_partial_p95_ratio": 1.25,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path | None) -> str | None:
    if path is None:
        return None
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return str(resolved)


def _round(value: float | np.floating[Any], digits: int = 6) -> float:
    return round(float(value), digits)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    text = value.strip().upper()
    if not text.startswith("#") or len(text) != 7:
        raise ValueError(f"Expected #RRGGBB color, got {value!r}")
    try:
        return tuple(int(text[index:index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]
    except ValueError as exc:
        raise ValueError(f"Expected #RRGGBB color, got {value!r}") from exc


def _canonical_hex(value: str) -> str:
    rgb = _hex_to_rgb(value)
    return "#" + "".join(f"{channel:02X}" for channel in rgb)


def parse_foreground_color(spec: str) -> dict[str, Any]:
    if "=" not in spec:
        raise ValueError(
            f"Foreground color must use NAME=#RRGGBB@MIN_CONTRAST, got {spec!r}"
        )
    name, remainder = spec.split("=", 1)
    name = name.strip()
    if not name:
        raise ValueError(f"Foreground color name is empty in {spec!r}")
    if "@" in remainder:
        color_text, threshold_text = remainder.rsplit("@", 1)
        try:
            threshold = float(threshold_text)
        except ValueError as exc:
            raise ValueError(f"Invalid contrast threshold in {spec!r}") from exc
    else:
        color_text = remainder
        threshold = 4.5
    if threshold <= 1.0:
        raise ValueError(f"Contrast threshold must be greater than 1.0 in {spec!r}")
    return {
        "name": name,
        "hex": _canonical_hex(color_text.strip()),
        "required_ratio": threshold,
    }


def _dependency_report() -> dict[str, Any]:
    scipy_available = importlib.util.find_spec("scipy") is not None
    return {
        "pillow": {
            "available": Image is not None,
            "version": PILLOW_VERSION,
        },
        "numpy": {
            "available": np is not None,
            "version": None if np is None else np.__version__,
        },
        "scipy": {
            "available": scipy_available,
            "version": None,
            "required": False,
        },
        "degradation": (
            None
            if scipy_available
            else "SciPy unavailable; using Pillow GaussianBlur/MaxFilter and NumPy finite-difference proxies."
        ),
    }


def _image_info(path: Path) -> dict[str, Any]:
    if Image is None:
        raise RuntimeError("Pillow is required to inspect raster files")
    with Image.open(path) as image:
        width, height = image.size
        return {
            "path": _display_path(path),
            "sha256": _sha256(path),
            "width": width,
            "height": height,
            "mode": image.mode,
            "format": image.format,
            "aspect_ratio": _round(width / height),
        }


def _relative_ratio_error(value: float, target: float) -> float:
    return abs(value - target) / target


def _dimension_report(
    raster_info: dict[str, Any],
    mask_info: dict[str, Any],
    tolerance: float,
) -> dict[str, Any]:
    raster_ratio = raster_info["width"] / raster_info["height"]
    mask_ratio = mask_info["width"] / mask_info["height"]
    raster_error = _relative_ratio_error(raster_ratio, TARGET_ASPECT_RATIO)
    mask_error = _relative_ratio_error(mask_ratio, TARGET_ASPECT_RATIO)
    cross_error = _relative_ratio_error(raster_ratio, mask_ratio)
    scale_x = mask_info["width"] / raster_info["width"]
    scale_y = mask_info["height"] / raster_info["height"]
    scale_delta = abs(scale_x - scale_y) / max(scale_x, scale_y)
    aspect_ok = raster_error <= tolerance and mask_error <= tolerance
    alignment_ok = cross_error <= tolerance and scale_delta <= tolerance
    exact_renderer_size = (
        raster_info["width"], raster_info["height"]
    ) == RENDERER_READY_SIZE
    return {
        "status": "pass" if aspect_ok and alignment_ok else "fail",
        "machine_proxy": True,
        "raster": {
            "width": raster_info["width"],
            "height": raster_info["height"],
            "aspect_ratio": _round(raster_ratio),
            "target_aspect_ratio": _round(TARGET_ASPECT_RATIO),
            "relative_error": _round(raster_error),
            "relative_tolerance": tolerance,
            "status": "pass" if raster_error <= tolerance else "fail",
        },
        "mask": {
            "width": mask_info["width"],
            "height": mask_info["height"],
            "aspect_ratio": _round(mask_ratio),
            "relative_error": _round(mask_error),
            "status": "pass" if mask_error <= tolerance else "fail",
        },
        "analysis_alignment": {
            "status": "pass" if alignment_ok else "fail",
            "raster_to_mask_scale_x": _round(scale_x),
            "raster_to_mask_scale_y": _round(scale_y),
            "relative_nonuniform_scale_delta": _round(scale_delta),
            "raster_to_mask_aspect_error": _round(cross_error),
            "in_memory_resize_required": (
                raster_info["width"], raster_info["height"]
            ) != (mask_info["width"], mask_info["height"]),
            "method": "Pillow LANCZOS, analysis memory only; no raster is written or replaced",
        },
        "renderer_ready_advisory": {
            "expected_width": RENDERER_READY_SIZE[0],
            "expected_height": RENDERER_READY_SIZE[1],
            "exact_size": exact_renderer_size,
            "status": "ready" if exact_renderer_size else "advisory",
            "blocking": False,
            "note": (
                "A legal near-16:9 model output is not failed only because it is not 1920x1080. "
                "Renderer materialization should record any resize/crop operation."
            ),
        },
    }


def _extract_transform_fields(value: Any, prefix: str = "") -> dict[str, Any]:
    fields: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            lowered = key.lower()
            if any(token in lowered for token in ("crop", "resize", "resample", "transform", "postprocess")):
                if isinstance(child, (str, int, float, bool, type(None), list)):
                    fields[child_prefix] = child
            fields.update(_extract_transform_fields(child, child_prefix))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            fields.update(_extract_transform_fields(child, f"{prefix}[{index}]"))
    return fields


def _pixel_identity(first: Path, second: Path) -> bool | None:
    if Image is None or np is None:
        return None
    with Image.open(first) as first_image, Image.open(second) as second_image:
        if first_image.size != second_image.size:
            return False
        first_rgb = np.asarray(first_image.convert("RGB"))
        second_rgb = np.asarray(second_image.convert("RGB"))
        return bool(np.array_equal(first_rgb, second_rgb))


def _provenance_report(
    raster_path: Path,
    source_raster: Path | None,
    provenance_json: Path | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "machine_proxy": True,
        "source_raster": None,
        "provenance_json": None,
        "unrecorded_crop_or_nonuniform_distortion": {
            "status": "not-verifiable",
            "reason": "A single raster cannot prove whether an earlier crop or nonuniform transform occurred.",
        },
    }
    declared_fields: dict[str, Any] = {}
    if provenance_json is not None:
        payload = json.loads(provenance_json.read_text(encoding="utf-8"))
        declared_fields = _extract_transform_fields(payload)
        result["provenance_json"] = {
            "path": _display_path(provenance_json),
            "sha256": _sha256(provenance_json),
            "declared_transform_fields": declared_fields,
        }
    if source_raster is None:
        return result

    source_info = _image_info(source_raster)
    target_info = _image_info(raster_path)
    same_bytes = source_info["sha256"] == target_info["sha256"]
    same_pixels = True if same_bytes else _pixel_identity(source_raster, raster_path)
    result["source_raster"] = {
        **source_info,
        "same_bytes_as_evaluated_raster": same_bytes,
        "same_pixels_as_evaluated_raster": same_pixels,
    }
    if same_pixels is True:
        result["unrecorded_crop_or_nonuniform_distortion"] = {
            "status": "not-detected",
            "reason": "The supplied source raster and evaluated raster are pixel-identical.",
        }
    elif not declared_fields:
        result["unrecorded_crop_or_nonuniform_distortion"] = {
            "status": "potential-unrecorded-transform",
            "reason": (
                "The supplied source and evaluated raster differ, but provenance declares no crop/resize/transform."
            ),
        }
    else:
        result["unrecorded_crop_or_nonuniform_distortion"] = {
            "status": "declared-but-not-pixel-verified",
            "reason": "A transform is declared, but this proxy does not reconstruct it to prove correctness.",
        }
    return result


def _srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    normalized = rgb.astype(np.float32) / 255.0
    return np.where(
        normalized <= 0.04045,
        normalized / 12.92,
        ((normalized + 0.055) / 1.055) ** 2.4,
    ).astype(np.float32)


def _relative_luminance(rgb: np.ndarray) -> np.ndarray:
    linear = _srgb_to_linear(rgb)
    return (
        0.2126 * linear[..., 0]
        + 0.7152 * linear[..., 1]
        + 0.0722 * linear[..., 2]
    ).astype(np.float32)


def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    linear = _srgb_to_linear(rgb)
    matrix = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ],
        dtype=np.float32,
    )
    xyz = linear @ matrix.T
    xyz /= np.array([0.95047, 1.0, 1.08883], dtype=np.float32)
    epsilon = 216.0 / 24389.0
    kappa = 24389.0 / 27.0
    transformed = np.where(
        xyz > epsilon,
        np.cbrt(xyz),
        (kappa * xyz + 16.0) / 116.0,
    )
    return np.stack(
        [
            116.0 * transformed[..., 1] - 16.0,
            500.0 * (transformed[..., 0] - transformed[..., 1]),
            200.0 * (transformed[..., 1] - transformed[..., 2]),
        ],
        axis=-1,
    ).astype(np.float32)


def _summarize(values: np.ndarray) -> dict[str, Any]:
    flat = np.asarray(values, dtype=np.float32).reshape(-1)
    if flat.size == 0:
        return {"count": 0}
    return {
        "count": int(flat.size),
        "min": _round(np.min(flat)),
        "p01": _round(np.percentile(flat, 1)),
        "p05": _round(np.percentile(flat, 5)),
        "p10": _round(np.percentile(flat, 10)),
        "p50": _round(np.percentile(flat, 50)),
        "p90": _round(np.percentile(flat, 90)),
        "p95": _round(np.percentile(flat, 95)),
        "p99": _round(np.percentile(flat, 99)),
        "max": _round(np.max(flat)),
        "mean": _round(np.mean(flat)),
        "stddev": _round(np.std(flat)),
    }


def _ratio_status(value: float, partial_threshold: float, fail_threshold: float) -> str:
    if value >= fail_threshold:
        return "fail"
    if value > partial_threshold:
        return "partial"
    return "pass"


def _protected_region_report(
    rgb: np.ndarray,
    protected: np.ndarray,
    base_palette: list[str],
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray]:
    luminance = _relative_luminance(rgb)
    lab = _rgb_to_lab(rgb)
    protected_lab = lab[protected]
    robust_base = np.median(protected_lab, axis=0).astype(np.float32)
    palette_rgb = np.array([_hex_to_rgb(color) for color in base_palette], dtype=np.uint8)
    palette_lab = _rgb_to_lab(palette_rgb.reshape((-1, 1, 3))).reshape((-1, 3))
    base_distances = np.linalg.norm(palette_lab - robust_base, axis=1)
    nearest_index = int(np.argmin(base_distances))
    pixel_palette_distance = np.min(
        np.linalg.norm(lab[..., None, :] - palette_lab[None, None, :, :], axis=-1),
        axis=-1,
    )
    report = {
        "status": "pass",
        "machine_proxy": True,
        "black_is_protected": True,
        "protected_pixel_count": int(np.count_nonzero(protected)),
        "protected_fraction": _round(np.mean(protected)),
        "luminance": {
            "metric": "WCAG relative luminance, not perceptual L*",
            **_summarize(luminance[protected]),
        },
        "robust_base": {
            "method": "per-channel median CIELAB over protected pixels",
            "lab": [_round(value) for value in robust_base],
            "nearest_base_palette_color": base_palette[nearest_index],
            "delta_e_76_to_nearest_palette_color": _round(base_distances[nearest_index]),
        },
        "base_palette_distance": {
            "metric": "DeltaE76 to nearest supplied base-palette color",
            **_summarize(pixel_palette_distance[protected]),
        },
    }
    return report, luminance, lab, robust_base


def _contrast_report(
    luminance: np.ndarray,
    protected: np.ndarray,
    foreground_colors: list[dict[str, Any]],
    fail_ratio_threshold: float,
) -> dict[str, Any]:
    background_luminance = luminance[protected]
    rows: list[dict[str, Any]] = []
    for color in foreground_colors:
        foreground_rgb = np.array(_hex_to_rgb(color["hex"]), dtype=np.uint8).reshape((1, 1, 3))
        foreground_luminance = float(_relative_luminance(foreground_rgb)[0, 0])
        ratios = (
            (np.maximum(background_luminance, foreground_luminance) + 0.05)
            / (np.minimum(background_luminance, foreground_luminance) + 0.05)
        )
        fail_ratio = float(np.mean(ratios < color["required_ratio"]))
        status = (
            "fail"
            if fail_ratio >= fail_ratio_threshold
            else ("partial" if fail_ratio > 0.0 else "pass")
        )
        rows.append(
            {
                **color,
                "foreground_relative_luminance": _round(foreground_luminance),
                "status": status,
                "mask_pixel_fail_ratio": _round(fail_ratio),
                "ratios": _summarize(ratios),
            }
        )
    statuses = {row["status"] for row in rows}
    status = "fail" if "fail" in statuses else ("partial" if "partial" in statuses else "pass")
    return {
        "status": status,
        "machine_proxy": True,
        "mask_level_only": True,
        "glyph_level_proof": False,
        "fail_ratio_threshold": fail_ratio_threshold,
        "interpretation": (
            "Each foreground color is tested against every protected-mask background pixel. "
            "This is conservative coverage evidence, not proof of actual glyph placement or antialiasing."
        ),
        "colors": rows,
    }


def _gradient_map(lab: np.ndarray) -> np.ndarray:
    horizontal = np.linalg.norm(lab[:, 1:, :] - lab[:, :-1, :], axis=2)
    vertical = np.linalg.norm(lab[1:, :, :] - lab[:-1, :, :], axis=2)
    gradient = np.zeros(lab.shape[:2], dtype=np.float32)
    gradient[:, 1:] = np.maximum(gradient[:, 1:], horizontal)
    gradient[:, :-1] = np.maximum(gradient[:, :-1], horizontal)
    gradient[1:, :] = np.maximum(gradient[1:, :], vertical)
    gradient[:-1, :] = np.maximum(gradient[:-1, :], vertical)
    return gradient


def _detail_report(
    aligned_image: Any,
    lab: np.ndarray,
    robust_base: np.ndarray,
    protected: np.ndarray,
    thresholds: dict[str, float | int],
) -> dict[str, Any]:
    blur_radius = int(thresholds["blur_radius_on_mask_canvas_px"])
    blurred_rgb = np.asarray(
        aligned_image.filter(ImageFilter.GaussianBlur(radius=blur_radius)).convert("RGB"),
        dtype=np.uint8,
    )
    blurred_lab = _rgb_to_lab(blurred_rgb)
    low_frequency_delta = np.linalg.norm(blurred_lab - robust_base, axis=2)
    high_frequency_delta = np.linalg.norm(lab - blurred_lab, axis=2)
    gradient = _gradient_map(lab)

    low_threshold = float(thresholds["low_frequency_delta_e"])
    high_threshold = float(thresholds["high_frequency_delta_e"])
    gradient_threshold = float(thresholds["gradient_delta_e"])
    partial_ratio = float(thresholds["detail_partial_ratio"])
    low_ratio = float(np.mean(low_frequency_delta[protected] > low_threshold))
    high_ratio = float(np.mean(high_frequency_delta[protected] > high_threshold))
    gradient_ratio = float(np.mean(gradient[protected] > gradient_threshold))
    low_status = _ratio_status(
        low_ratio,
        partial_ratio,
        float(thresholds["low_frequency_fail_ratio"]),
    )
    high_status = _ratio_status(
        high_ratio,
        partial_ratio,
        float(thresholds["high_frequency_fail_ratio"]),
    )
    statuses = {low_status, high_status}
    status = "fail" if "fail" in statuses else ("partial" if "partial" in statuses else "pass")
    return {
        "status": status,
        "machine_proxy": True,
        "method": (
            "CIELAB DeltaE76 proxies on the mask canvas. Low frequency compares a Gaussian-blurred "
            "image with the protected-region robust median; high frequency compares original pixels "
            "with the blurred image. Finite-difference gradients are descriptive only."
        ),
        "low_frequency": {
            "status": low_status,
            "blur_radius_px": blur_radius,
            "delta_e_threshold": low_threshold,
            "intrusion_ratio": _round(low_ratio),
            "partial_ratio_threshold": partial_ratio,
            "fail_ratio_threshold": thresholds["low_frequency_fail_ratio"],
            "delta_e_distribution": _summarize(low_frequency_delta[protected]),
        },
        "high_frequency": {
            "status": high_status,
            "delta_e_threshold": high_threshold,
            "intrusion_ratio": _round(high_ratio),
            "partial_ratio_threshold": partial_ratio,
            "fail_ratio_threshold": thresholds["high_frequency_fail_ratio"],
            "delta_e_distribution": _summarize(high_frequency_delta[protected]),
        },
        "gradient_proxy": {
            "status": "report-only",
            "delta_e_threshold": gradient_threshold,
            "ratio_above_threshold": _round(gradient_ratio),
            "distribution": _summarize(gradient[protected]),
        },
    }


def _seam_report(
    lab: np.ndarray,
    protected: np.ndarray,
    thresholds: dict[str, float | int],
) -> dict[str, Any]:
    horizontal_delta = np.linalg.norm(lab[:, 1:, :] - lab[:, :-1, :], axis=2)
    vertical_delta = np.linalg.norm(lab[1:, :, :] - lab[:-1, :, :], axis=2)
    horizontal_cross = protected[:, 1:] != protected[:, :-1]
    vertical_cross = protected[1:, :] != protected[:-1, :]
    cross_values = np.concatenate(
        [horizontal_delta[horizontal_cross], vertical_delta[vertical_cross]]
    )
    if cross_values.size == 0:
        return {
            "status": "not-applicable",
            "machine_proxy": True,
            "reason": "The supplied mask has no protected/unprotected boundary.",
        }

    boundary_pixels = np.zeros(protected.shape, dtype=np.uint8)
    boundary_pixels[:, 1:] |= horizontal_cross
    boundary_pixels[:, :-1] |= horizontal_cross
    boundary_pixels[1:, :] |= vertical_cross
    boundary_pixels[:-1, :] |= vertical_cross
    band_radius = int(thresholds["seam_band_radius_px"])
    filter_size = max(3, band_radius * 2 + 1)
    if filter_size % 2 == 0:
        filter_size += 1
    boundary_band = np.asarray(
        Image.fromarray(boundary_pixels * 255).filter(ImageFilter.MaxFilter(filter_size)),
        dtype=np.uint8,
    ) > 0
    horizontal_near = (
        boundary_band[:, 1:]
        & boundary_band[:, :-1]
        & ~horizontal_cross
    )
    vertical_near = (
        boundary_band[1:, :]
        & boundary_band[:-1, :]
        & ~vertical_cross
    )
    near_values = np.concatenate(
        [horizontal_delta[horizontal_near], vertical_delta[vertical_near]]
    )
    cross_summary = _summarize(cross_values)
    near_summary = _summarize(near_values)
    cross_p95 = float(cross_summary["p95"])
    near_p95 = max(float(near_summary.get("p95", 0.0)), 1e-6)
    ratio = cross_p95 / near_p95
    fail = (
        cross_p95 >= float(thresholds["seam_cross_delta_e_p95"])
        and ratio >= float(thresholds["seam_cross_to_near_p95_ratio"])
    )
    partial = (
        cross_p95 >= float(thresholds["seam_partial_delta_e_p95"])
        and ratio >= float(thresholds["seam_partial_p95_ratio"])
    )
    status = "fail" if fail else ("partial" if partial else "pass")
    return {
        "status": status,
        "machine_proxy": True,
        "method": (
            "DeltaE76 across pixel-neighbor edges that cross the mask boundary, compared with "
            "non-crossing edges in a nearby band. This flags mask-shaped steps but is not a semantic seam proof."
        ),
        "band_radius_px": band_radius,
        "cross_boundary_delta_e": cross_summary,
        "near_boundary_delta_e": near_summary,
        "cross_to_near_p95_ratio": _round(ratio),
        "fail_thresholds": {
            "cross_boundary_p95_delta_e": thresholds["seam_cross_delta_e_p95"],
            "cross_to_near_p95_ratio": thresholds["seam_cross_to_near_p95_ratio"],
        },
        "partial_thresholds": {
            "cross_boundary_p95_delta_e": thresholds["seam_partial_delta_e_p95"],
            "cross_to_near_p95_ratio": thresholds["seam_partial_p95_ratio"],
        },
    }


def _not_run(reason: str) -> dict[str, Any]:
    return {"status": "not-run", "machine_proxy": True, "reason": reason}


def _overall_report(checks: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    gated_ids = ("dimensions", "mask", "contrast", "detail_intrusion", "mask_boundary_seam")
    blocking = [
        check_id
        for check_id in gated_ids
        if checks.get(check_id, {}).get("status") == "fail"
    ]
    partial = [
        check_id
        for check_id in gated_ids
        if checks.get(check_id, {}).get("status") in {"partial", "not-run", "not-applicable"}
    ]
    provenance_status = provenance["unrecorded_crop_or_nonuniform_distortion"]["status"]
    if provenance_status in {"not-verifiable", "declared-but-not-pixel-verified"}:
        partial.append("provenance")
    elif provenance_status == "potential-unrecorded-transform":
        blocking.append("provenance")
    status = "fail" if blocking else ("partial" if partial else "pass")
    unverified = [
        "actual glyph coverage, antialiasing, and per-glyph contrast",
        "foreground pseudo-elements or design objects missing from the supplied mask",
        "OCR, symbols, semantic imagery, and human aesthetic fit",
        "live HTML compositing, editor interaction, export, and PPTX layout integration",
    ]
    if provenance_status == "not-verifiable":
        unverified.append("earlier crop, resize, or nonuniform transform before the supplied raster")
    return {
        "status": status,
        "machine_proxy_status": status,
        "release_status": "needs-human-review",
        "blocking_checks": sorted(set(blocking)),
        "partial_checks": sorted(set(partial)),
        "mask_level_pass_is_glyph_level_pass": False,
        "human_visual_review_required": True,
        "unverified": unverified,
    }


def analyze_background(
    raster_path: Path,
    mask_path: Path,
    base_palette: Iterable[str],
    foreground_specs: Iterable[str],
    *,
    source_raster: Path | None = None,
    provenance_json: Path | None = None,
    threshold_overrides: dict[str, float | int] | None = None,
) -> dict[str, Any]:
    """Analyze inputs without writing or mutating any image."""

    raster_path = raster_path.resolve()
    mask_path = mask_path.resolve()
    source_raster = source_raster.resolve() if source_raster else None
    provenance_json = provenance_json.resolve() if provenance_json else None
    for path, label in ((raster_path, "raster"), (mask_path, "mask")):
        if not path.is_file():
            raise ValueError(f"{label} does not exist: {path}")
    if source_raster is not None and not source_raster.is_file():
        raise ValueError(f"source raster does not exist: {source_raster}")
    if provenance_json is not None and not provenance_json.is_file():
        raise ValueError(f"provenance JSON does not exist: {provenance_json}")

    palette = [_canonical_hex(color) for color in base_palette]
    if not palette:
        raise ValueError("At least one --base-color is required")
    foreground_colors = [parse_foreground_color(spec) for spec in foreground_specs]
    if not foreground_colors:
        raise ValueError("At least one --foreground-color is required")

    thresholds = dict(DEFAULT_THRESHOLDS)
    if threshold_overrides:
        thresholds.update(threshold_overrides)
    dependencies = _dependency_report()
    if Image is None or np is None:
        missing = [name for name in ("pillow", "numpy") if not dependencies[name]["available"]]
        return {
            "schema_version": "html-image-background-qa/v1",
            "tool": {"name": "qa_html_image_background.py", "dependencies": dependencies},
            "contract": {
                "read_only_inputs": True,
                "machine_proxy": True,
                "glyph_level_proof": False,
            },
            "inputs": {
                "raster": _display_path(raster_path),
                "protected_mask": _display_path(mask_path),
                "base_palette": palette,
                "foreground_colors": foreground_colors,
            },
            "checks": {},
            "overall": {
                "status": "fail",
                "machine_proxy_status": "fail",
                "release_status": "needs-human-review",
                "blocking_checks": ["dependencies"],
                "partial_checks": [],
                "missing_dependencies": missing,
            },
        }

    raster_info = _image_info(raster_path)
    mask_info = _image_info(mask_path)
    dimension_check = _dimension_report(
        raster_info,
        mask_info,
        float(thresholds["aspect_ratio_relative_tolerance"]),
    )
    provenance = _provenance_report(raster_path, source_raster, provenance_json)

    with Image.open(mask_path) as mask_image:
        mask_gray = np.asarray(mask_image.convert("L"), dtype=np.uint8)
    protected = mask_gray <= int(thresholds["mask_black_threshold"])
    protected_count = int(np.count_nonzero(protected))
    mask_check = {
        "status": "pass" if protected_count > 0 else "fail",
        "machine_proxy": True,
        "black_is_protected": True,
        "black_threshold_inclusive": thresholds["mask_black_threshold"],
        "protected_pixel_count": protected_count,
        "protected_fraction": _round(np.mean(protected)),
    }

    checks: dict[str, Any] = {
        "dimensions": dimension_check,
        "mask": mask_check,
    }
    invalid_alignment = dimension_check["status"] == "fail"
    invalid_mask = mask_check["status"] == "fail"
    if invalid_alignment or invalid_mask:
        reason = (
            "Raster/mask aspect alignment is outside tolerance."
            if invalid_alignment
            else "The mask contains no protected pixels."
        )
        checks.update(
            {
                "protected_region": _not_run(reason),
                "contrast": _not_run(reason),
                "detail_intrusion": _not_run(reason),
                "mask_boundary_seam": _not_run(reason),
            }
        )
    else:
        with Image.open(raster_path) as source_image:
            original_mode = source_image.mode
            alpha_nonopaque_fraction = 0.0
            if "A" in source_image.getbands():
                alpha = np.asarray(source_image.getchannel("A"), dtype=np.uint8)
                alpha_nonopaque_fraction = float(np.mean(alpha < 255))
            rgb_image = source_image.convert("RGB")
            if rgb_image.size != (mask_info["width"], mask_info["height"]):
                aligned_image = rgb_image.resize(
                    (mask_info["width"], mask_info["height"]),
                    Image.Resampling.LANCZOS,
                )
            else:
                aligned_image = rgb_image.copy()
        checks["alpha"] = {
            "status": "partial" if alpha_nonopaque_fraction > 0 else "pass",
            "original_mode": original_mode,
            "nonopaque_pixel_fraction": _round(alpha_nonopaque_fraction),
            "note": "RGB analysis ignores alpha; nonopaque backgrounds require renderer-specific review.",
        }
        rgb = np.asarray(aligned_image, dtype=np.uint8)
        protected_report, luminance, lab, robust_base = _protected_region_report(
            rgb, protected, palette
        )
        checks["protected_region"] = protected_report
        checks["contrast"] = _contrast_report(
            luminance,
            protected,
            foreground_colors,
            float(thresholds["contrast_fail_ratio"]),
        )
        checks["detail_intrusion"] = _detail_report(
            aligned_image,
            lab,
            robust_base,
            protected,
            thresholds,
        )
        checks["mask_boundary_seam"] = _seam_report(lab, protected, thresholds)

    report = {
        "schema_version": "html-image-background-qa/v1",
        "tool": {
            "name": "qa_html_image_background.py",
            "dependencies": dependencies,
        },
        "contract": {
            "read_only_inputs": True,
            "raster_or_mask_modified": False,
            "machine_proxy": True,
            "glyph_level_proof": False,
            "human_visual_review_required": True,
            "dimension_policy": (
                "Near-16:9 model-native rasters are valid QA inputs; exact 1920x1080 is a nonblocking "
                "renderer-ready advisory."
            ),
        },
        "inputs": {
            "raster": raster_info,
            "protected_mask": mask_info,
            "base_palette": [
                {
                    "hex": color,
                    "rgb": list(_hex_to_rgb(color)),
                }
                for color in palette
            ],
            "foreground_colors": foreground_colors,
        },
        "thresholds": thresholds,
        "provenance": provenance,
        "checks": checks,
    }
    report["overall"] = _overall_report(checks, provenance)
    return report


def _error_report(message: str) -> dict[str, Any]:
    return {
        "schema_version": "html-image-background-qa/v1",
        "tool": {
            "name": "qa_html_image_background.py",
            "dependencies": _dependency_report(),
        },
        "contract": {
            "read_only_inputs": True,
            "machine_proxy": True,
            "glyph_level_proof": False,
        },
        "checks": {},
        "overall": {
            "status": "fail",
            "machine_proxy_status": "fail",
            "release_status": "needs-human-review",
            "blocking_checks": ["input"],
            "partial_checks": [],
            "error": message,
        },
    }


def _write_report(report: dict[str, Any], output: Path | None) -> None:
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    print(payload, end="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only mask-level QA for an HTML raster image background."
    )
    parser.add_argument("--raster", type=Path, required=True)
    parser.add_argument("--mask", type=Path, required=True, help="PNG/JPEG mask; black means protected")
    parser.add_argument("--base-color", action="append", required=True, help="#RRGGBB; repeatable")
    parser.add_argument(
        "--foreground-color",
        action="append",
        required=True,
        help="NAME=#RRGGBB@MIN_CONTRAST; repeatable",
    )
    parser.add_argument("--source-raster", type=Path)
    parser.add_argument("--provenance-json", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--aspect-ratio-tolerance",
        type=float,
        default=float(DEFAULT_THRESHOLDS["aspect_ratio_relative_tolerance"]),
    )
    parser.add_argument(
        "--mask-black-threshold",
        type=int,
        default=int(DEFAULT_THRESHOLDS["mask_black_threshold"]),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = analyze_background(
            args.raster,
            args.mask,
            args.base_color,
            args.foreground_color,
            source_raster=args.source_raster,
            provenance_json=args.provenance_json,
            threshold_overrides={
                "aspect_ratio_relative_tolerance": args.aspect_ratio_tolerance,
                "mask_black_threshold": args.mask_black_threshold,
            },
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        report = _error_report(str(exc))
    _write_report(report, args.output)
    return 1 if report["overall"]["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
