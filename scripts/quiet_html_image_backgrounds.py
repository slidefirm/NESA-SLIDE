"""Create a quieter v2 copy of per-slide HTML image-background experiments.

The image-background skill uses protected masks as generation guidance.  This
post-generation pass makes that guidance enforceable: foreground regions are
kept as a low-contrast, low-frequency field so generated lines, rings, and
high-frequency decoration do not run through editable text or content.

The source experiment is never modified.  The output is a sibling experiment
directory and is then assembled with the existing apply-deck command.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]
APPLY_SCRIPT = ROOT / "scripts" / "html_image_background_experiment.py"
THEME_COLOR_RE = re.compile(
    r"--(?P<name>ink|muted|accent|support|bg|surface|text|primary|secondary|"
    r"surface-text|surface-muted|support-accent|accent-ink|surface-accent-ink)\s*:\s*"
    r"(?P<value>#[0-9a-fA-F]{3,8})",
    re.IGNORECASE,
)
GUARD_VERSION = 2


def _slide_source(background_dir: Path, number: int) -> Path:
    matches = sorted(
        path
        for path in background_dir.glob(f"slide-{number:03d}.*")
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one slide-{number:03d} background in {background_dir}; "
            f"found {len(matches)}"
        )
    return matches[0]


def _hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    if len(value) >= 6:
        return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))
    raise ValueError(f"Unsupported CSS color: #{value}")


def _srgb_luminance(rgb: tuple[int, int, int]) -> float:
    channels = []
    for channel in rgb:
        value = channel / 255.0
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast_ratio(first: float, second: float) -> float:
    high, low = max(first, second), min(first, second)
    return (high + 0.05) / (low + 0.05)


def _target_field_rgb(
    colors: dict[str, tuple[int, int, int]],
    text_is_dark: bool,
    foreground_lumas: list[float],
) -> tuple[int, int, int]:
    """Use the preset's own background color, nudged into a safe luminance family."""
    candidate = colors.get("bg") or colors.get("surface")
    if candidate is None:
        candidate = (236, 238, 232) if text_is_dark else (18, 29, 38)
    current = _srgb_luminance(candidate)
    if text_is_dark:
        # Keep the authored hue, but guarantee a light negative-space field.
        required = max(0.82, *(4.5 * (luma + 0.05) - 0.05 for luma in foreground_lumas))
        while current < required and candidate != (255, 255, 255):
            candidate = tuple(min(255, round(channel + (255 - channel) * 0.16)) for channel in candidate)
            current = _srgb_luminance(candidate)
    else:
        # Keep the authored hue, but guarantee a dark negative-space field.
        required = min(0.30, *((luma + 0.05) / 4.5 - 0.05 for luma in foreground_lumas))
        while current > required and candidate != (0, 0, 0):
            candidate = tuple(max(0, round(channel * 0.78)) for channel in candidate)
            current = _srgb_luminance(candidate)
    return candidate


def _theme_colors(html_path: Path) -> dict[str, tuple[int, int, int]]:
    """Read the authored foreground palette instead of guessing from the bitmap."""
    text = html_path.read_text(encoding="utf-8", errors="replace")
    colors: dict[str, tuple[int, int, int]] = {}
    for match in THEME_COLOR_RE.finditer(text):
        colors[match.group("name").lower()] = _hex_rgb(match.group("value"))
    # Older HTML presets call the same semantic roles --text/--primary and
    # --secondary/--surface-muted. Normalize those names before the guard
    # computes contrast, so every preset gets the same enforceable treatment.
    for target, aliases in {
        "ink": ("text", "primary", "surface-text"),
        "muted": ("secondary", "surface-muted"),
        "support": ("support-accent",),
    }.items():
        if target not in colors:
            for alias in aliases:
                if alias in colors:
                    colors[target] = colors[alias]
                    break
    if "ink" not in colors:
        raise ValueError(f"No foreground color (--ink/--text/--primary) in {html_path}")
    if "muted" not in colors:
        colors["muted"] = colors["ink"]
    if "accent" not in colors:
        colors["accent"] = colors["ink"]
    if "support" not in colors:
        colors["support"] = colors["accent"]
    return colors


def _protected_stats(image: Image.Image, protected: Image.Image) -> dict[str, float]:
    """Return stable low-resolution luminance stats for the protected area."""
    sample_size = (128, 72)
    image_sample = image.resize(sample_size, Image.Resampling.BILINEAR).convert("RGB")
    mask_sample = protected.resize(sample_size, Image.Resampling.BILINEAR)
    values: list[float] = []
    for pixel, mask_value in zip(image_sample.getdata(), mask_sample.getdata()):
        if mask_value < 160:
            continue
        values.append(_srgb_luminance(pixel))
    if not values:
        return {"mean": 0.0, "p10": 0.0, "p90": 0.0, "samples": 0.0}
    values.sort()
    return {
        "mean": sum(values) / len(values),
        "p10": values[max(0, int(len(values) * 0.10) - 1)],
        "p90": values[min(len(values) - 1, int(len(values) * 0.90))],
        "samples": float(len(values)),
    }


def quiet_background(
    source: Path,
    mask: Path,
    destination: Path,
    foreground_colors: dict[str, tuple[int, int, int]],
) -> dict[str, object]:
    """Keep the generated image while enforcing whitespace and text contrast."""
    with Image.open(source) as image:
        base = image.convert("RGB")
    if base.size != (1920, 1080):
        base = base.resize((1920, 1080), Image.Resampling.LANCZOS)

    with Image.open(mask) as mask_image:
        protected = ImageOps.invert(mask_image.convert("L").resize((1920, 1080), Image.Resampling.NEAREST))

    # First reduce visual noise across the whole slide without flattening the
    # scene completely.  This also makes open-zone decoration less aggressive.
    global_field = base.filter(ImageFilter.GaussianBlur(28))
    global_field = ImageEnhance.Contrast(global_field).enhance(0.58)
    global_field = ImageEnhance.Color(global_field).enhance(0.68)
    softened = Image.blend(base, global_field, 0.48)

    # Protected regions receive a much lower-frequency treatment.  Broad tone
    # remains, but lines, rings, text-like marks, and small objects disappear.
    quiet_field = base.filter(ImageFilter.GaussianBlur(118))
    quiet_field = ImageEnhance.Contrast(quiet_field).enhance(0.30)
    quiet_field = ImageEnhance.Color(quiet_field).enhance(0.52)
    quiet_mask = protected.filter(ImageFilter.GaussianBlur(26))

    # The authored ink/muted colors decide the protected field direction.  A
    # dark image behind dark HTML text is not a usable background, even when
    # the image has already been blurred, so the protected field is pushed to
    # the opposite luminance family.  Open zones retain the generated scene.
    ink_luma = _srgb_luminance(foreground_colors["ink"])
    muted_luma = _srgb_luminance(foreground_colors["muted"])
    text_is_dark = (ink_luma + muted_luma) / 2 < 0.46
    foreground_lumas = [ink_luma, muted_luma]
    target_rgb = _target_field_rgb(foreground_colors, text_is_dark, foreground_lumas)
    target_field = Image.new("RGB", (1920, 1080), target_rgb)
    blend = 1.0
    hard_protected = protected.point(lambda value: 255 if value >= 128 else 0)
    result: Image.Image | None = None
    stats: dict[str, float] = {}
    for _ in range(5):
        contrast_field = Image.blend(quiet_field, target_field, blend)
        candidate = Image.composite(contrast_field, softened, quiet_mask)
        # The exact occupied pixels must contain no generated detail.  The
        # feathered mask only softens the transition outside the safe zone.
        candidate = Image.composite(contrast_field, candidate, hard_protected)
        stats = _protected_stats(candidate, hard_protected)
        target_luma = _srgb_luminance(target_rgb)
        minimum_contrast = min(_contrast_ratio(target_luma, value) for value in foreground_lumas)
        if minimum_contrast >= 4.5 and (
            (text_is_dark and stats["p10"] >= 0.45)
            or (not text_is_dark and stats["p90"] <= 0.52)
        ):
            result = candidate
            break
        blend = min(0.96, blend + 0.05)
    if result is None:
        result = Image.composite(Image.blend(quiet_field, target_field, blend), softened, quiet_mask)
        stats = _protected_stats(result, hard_protected)

    target_luma = _srgb_luminance(target_rgb)
    contrast_by_color = {
        name: round(_contrast_ratio(target_luma, _srgb_luminance(rgb)), 3)
        for name, rgb in foreground_colors.items()
        if name in {"ink", "muted", "accent", "support"}
    }
    minimum_contrast = min(contrast_by_color.values()) if contrast_by_color else 0.0
    body_contrast = min(
        contrast_by_color.get(name, 99.0) for name in ("ink", "muted")
    )
    accent_contrast = min(contrast_by_color.get(name, 99.0) for name in ("accent", "support"))

    destination.parent.mkdir(parents=True, exist_ok=True)
    result.save(destination, format="PNG", optimize=True)
    return {
        "guard_version": GUARD_VERSION,
        "foreground_mode": "dark-text-on-light-field" if text_is_dark else "light-text-on-dark-field",
        "foreground_colors": {
            name: "#%02X%02X%02X" % rgb for name, rgb in foreground_colors.items()
        },
        "protected_luminance": {key: round(value, 4) for key, value in stats.items()},
        "protected_field_blend": round(blend, 3),
        "target_field_rgb": "#%02X%02X%02X" % target_rgb,
        "ink_muted_min_contrast_ratio": round(body_contrast, 3),
        "accent_support_min_contrast_ratio": round(accent_contrast, 3),
        "palette_min_contrast_ratio": round(minimum_contrast, 3),
        "contrast_gate_pass": bool(
            body_contrast >= 4.5
            and (
                (text_is_dark and stats["p10"] >= 0.45)
                or (not text_is_dark and stats["p90"] <= 0.52)
            )
        ),
    }


def _copy_provenance(source_preset: Path, output_preset: Path) -> None:
    output_preset.mkdir(parents=True, exist_ok=True)
    for filename in ("neutral.html", "masks.json", "imagegen-prompt-template.txt"):
        source = source_preset / filename
        if source.is_file():
            shutil.copy2(source, output_preset / filename)
    for dirname in ("masks", "prompts", "mask-pages"):
        source = source_preset / dirname
        if source.is_dir():
            shutil.copytree(source, output_preset / dirname, dirs_exist_ok=True)


def process_preset(source_preset: Path, output_preset: Path, pilot: Path | None) -> dict:
    manifest_path = source_preset / "run.json"
    if not manifest_path.is_file():
        raise ValueError(f"Missing run.json: {source_preset}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest.get("slide_records") or []
    if not records:
        raise ValueError(f"Missing slide_records: {manifest_path}")

    _copy_provenance(source_preset, output_preset)
    foreground_colors = _theme_colors(source_preset / "neutral.html")
    quiet_dir = output_preset / "quiet-backgrounds"
    source_backgrounds = source_preset / "backgrounds"
    if not source_backgrounds.is_dir():
        raise ValueError(f"Missing backgrounds directory: {source_backgrounds}")

    background_guards: list[dict[str, object]] = []
    for position, record in enumerate(records):
        index = int(record.get("index", position))
        number = index + 1
        mask_value = record.get("mask")
        mask = Path(mask_value) if mask_value else source_preset / "masks" / f"protected-mask-{number:03d}.png"
        if not mask.is_file():
            fallback = source_preset / "masks" / f"protected-mask-{number:03d}.png"
            mask = fallback
        if not mask.is_file():
            raise ValueError(f"Missing protected mask for slide {number}: {mask}")
        source = pilot if pilot is not None and source_preset.name == "tide-signal-observatory" and number == 1 else _slide_source(source_backgrounds, number)
        destination = quiet_dir / f"slide-{number:03d}.png"
        guard = quiet_background(source, mask, destination, foreground_colors)
        guard["slide"] = number
        guard["source_background"] = str(source.resolve())
        background_guards.append(guard)

    # Keep the source run's provenance while making the new output explicit.
    manifest.update(
        {
            "status": "needs-review",
            "parent_run": str(source_preset.resolve()),
            "background_mode": "per-slide",
            "mask_usage": "generation-guidance-and-post-generation-quieting",
            "post_generation_quieting": True,
            "quiet_backgrounds_directory": str(quiet_dir.resolve()),
            "source_was_modified": False,
            "production_integration": False,
            "background_guard_version": GUARD_VERSION,
            "background_guards": background_guards,
            "qa": {
                "automatic_pass": False,
                "reason": "Protected-zone quieting and contrast gate are automatic; visual review is still required for semantic fit.",
                "protected_zone_contrast_pass": all(
                    bool(item["contrast_gate_pass"]) for item in background_guards
                ),
            },
        }
    )
    (output_preset / "run.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    subprocess.run(
        [
            sys.executable,
            str(APPLY_SCRIPT),
            "apply-deck",
            "--run-dir",
            str(output_preset),
            "--background-dir",
            str(quiet_dir),
        ],
        cwd=ROOT,
        check=True,
    )
    applied_manifest = json.loads((output_preset / "run.json").read_text(encoding="utf-8"))
    applied_manifest.update(
        {
            "parent_run": str(source_preset.resolve()),
            "mask_usage": "generation-guidance-and-post-generation-quieting",
            "post_generation_quieting": True,
            "quiet_backgrounds_directory": str(quiet_dir.resolve()),
            "source_was_modified": False,
            "production_integration": False,
            "background_guard_version": GUARD_VERSION,
            "background_guards": background_guards,
            "qa": {
                "automatic_pass": False,
                "reason": "Protected-zone quieting and contrast gate are automatic; visual review is still required for semantic fit.",
                "protected_zone_contrast_pass": all(
                    bool(item["contrast_gate_pass"]) for item in background_guards
                ),
            },
        }
    )
    (output_preset / "run.json").write_text(
        json.dumps(applied_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "preset": source_preset.name,
        "slides": len(records),
        "final_html": str((output_preset / "final.html").resolve()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--pilot", type=Path, help="Optional replacement image for the tide cover pilot")
    parser.add_argument("--only", action="append", help="Process only this preset name; repeat for a batch")
    parser.add_argument("--resume", action="store_true", help="Skip output presets already produced with guard v2")
    args = parser.parse_args()

    input_root = args.input_root.resolve()
    output_root = args.output_root.resolve()
    pilot = args.pilot.resolve() if args.pilot else None
    if not input_root.is_dir():
        raise SystemExit(f"Input root does not exist: {input_root}")
    if pilot is not None and not pilot.is_file():
        raise SystemExit(f"Pilot image does not exist: {pilot}")
    output_root.mkdir(parents=True, exist_ok=True)

    selected = set(args.only or [])
    source_presets = sorted(path for path in input_root.iterdir() if path.is_dir())
    if selected:
        known = {path.name for path in source_presets}
        unknown = selected - known
        if unknown:
            raise SystemExit(f"Unknown preset(s): {', '.join(sorted(unknown))}")
        source_presets = [path for path in source_presets if path.name in selected]

    results = []
    for source_preset in source_presets:
        output_preset = output_root / source_preset.name
        existing_manifest = output_preset / "run.json"
        if args.resume and existing_manifest.is_file():
            try:
                existing = json.loads(existing_manifest.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = {}
            if existing.get("background_guard_version") == GUARD_VERSION and (output_preset / "final.html").is_file():
                results.append({"preset": source_preset.name, "skipped": True})
                continue
        results.append(process_preset(source_preset, output_preset, pilot))
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
