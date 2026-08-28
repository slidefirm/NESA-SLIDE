"""Build a reproducible per-slide work ledger for HTML image-background generation.

This planner is read-only with respect to source decks.  It converts the existing
browser-measured occupancy records into conservative generation instructions; it
does not generate or alter raster images.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


SLIDE_WIDTH = 1920.0
SLIDE_HEIGHT = 1080.0
GUARD_PX = 96.0
MIN_OPEN_WIDTH = 320.0
MIN_OPEN_HEIGHT = 240.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _theme_tokens(html: str) -> dict[str, str]:
    pairs = re.findall(
        r"--(bg|surface|ink|muted|accent|support)\s*:\s*([^;}{]+)", html, re.IGNORECASE
    )
    tokens: dict[str, str] = {}
    for key, value in pairs:
        # The self-contained HTML embeds editor chrome before the deck's final
        # Preset variables.  CSS cascade order means the last declaration is the
        # effective slide token; keeping the first one can invert light/dark
        # polarity by accidentally reading editor chrome colors.
        tokens[key.lower()] = value.strip()
    return tokens


def _hex_rgb(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    match = re.fullmatch(r"#([0-9a-fA-F]{6})", value.strip())
    if not match:
        return None
    raw = match.group(1)
    return tuple(int(raw[offset : offset + 2], 16) for offset in (0, 2, 4))


def _relative_luminance(value: str | None) -> float | None:
    rgb = _hex_rgb(value)
    if rgb is None:
        return None

    def linear(channel: int) -> float:
        normalized = channel / 255.0
        return normalized / 12.92 if normalized <= 0.04045 else ((normalized + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(channel) for channel in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _clip_box(box: dict) -> dict[str, float]:
    left = max(0.0, min(SLIDE_WIDTH, float(box.get("x", 0.0))))
    top = max(0.0, min(SLIDE_HEIGHT, float(box.get("y", 0.0))))
    right = max(left, min(SLIDE_WIDTH, left + max(0.0, float(box.get("w", 0.0)))))
    bottom = max(top, min(SLIDE_HEIGHT, top + max(0.0, float(box.get("h", 0.0)))))
    return {"x": left, "y": top, "w": right - left, "h": bottom - top}


def _expand_box(box: dict[str, float], guard: float = GUARD_PX) -> dict[str, float]:
    left = max(0.0, box["x"] - guard)
    top = max(0.0, box["y"] - guard)
    right = min(SLIDE_WIDTH, box["x"] + box["w"] + guard)
    bottom = min(SLIDE_HEIGHT, box["y"] + box["h"] + guard)
    return {"x": left, "y": top, "w": right - left, "h": bottom - top}


def _union_area(boxes: list[dict[str, float]]) -> float:
    """Exact axis-aligned rectangle union area using a small sweep."""
    if not boxes:
        return 0.0
    xs = sorted({box["x"] for box in boxes} | {box["x"] + box["w"] for box in boxes})
    area = 0.0
    for left, right in zip(xs, xs[1:]):
        if right <= left:
            continue
        spans = sorted(
            (box["y"], box["y"] + box["h"])
            for box in boxes
            if box["x"] < right and box["x"] + box["w"] > left
        )
        covered = 0.0
        start = end = None
        for top, bottom in spans:
            if start is None:
                start, end = top, bottom
            elif top <= end:
                end = max(end, bottom)
            else:
                covered += end - start
                start, end = top, bottom
        if start is not None:
            covered += end - start
        area += (right - left) * covered
    return area


def _safe_edge_pockets(boxes: list[dict[str, float]]) -> list[dict[str, float | str]]:
    """Return only large edge-connected rectangles clear of guarded occupied boxes.

    The result is intentionally conservative.  It tests four full-width/height
    strips and corner rectangles, then rejects anything smaller than the minimum
    focal-detail contract.  The actual foreground screenshot remains authoritative.
    """
    candidates = [
        ("top", 0.0, 0.0, SLIDE_WIDTH, MIN_OPEN_HEIGHT),
        ("bottom", 0.0, SLIDE_HEIGHT - MIN_OPEN_HEIGHT, SLIDE_WIDTH, MIN_OPEN_HEIGHT),
        ("left", 0.0, 0.0, MIN_OPEN_WIDTH, SLIDE_HEIGHT),
        ("right", SLIDE_WIDTH - MIN_OPEN_WIDTH, 0.0, MIN_OPEN_WIDTH, SLIDE_HEIGHT),
        ("top-left", 0.0, 0.0, MIN_OPEN_WIDTH, MIN_OPEN_HEIGHT),
        ("top-right", SLIDE_WIDTH - MIN_OPEN_WIDTH, 0.0, MIN_OPEN_WIDTH, MIN_OPEN_HEIGHT),
        ("bottom-left", 0.0, SLIDE_HEIGHT - MIN_OPEN_HEIGHT, MIN_OPEN_WIDTH, MIN_OPEN_HEIGHT),
        ("bottom-right", SLIDE_WIDTH - MIN_OPEN_WIDTH, SLIDE_HEIGHT - MIN_OPEN_HEIGHT, MIN_OPEN_WIDTH, MIN_OPEN_HEIGHT),
    ]
    safe: list[dict[str, float | str]] = []
    for name, x, y, width, height in candidates:
        right, bottom = x + width, y + height
        intersects = any(
            box["x"] < right
            and box["x"] + box["w"] > x
            and box["y"] < bottom
            and box["y"] + box["h"] > y
            for box in boxes
        )
        if not intersects:
            safe.append({"name": name, "x": x, "y": y, "w": width, "h": height})
    # Prefer corner pockets over strips and remove duplicate-contained candidates.
    corners = [item for item in safe if "-" in str(item["name"])]
    return corners or [item for item in safe if "-" not in str(item["name"])]


def build_ledger(source_root: Path, output_root: Path) -> dict:
    presets = []
    for preset_dir in sorted(path for path in source_root.iterdir() if path.is_dir()):
        neutral = preset_dir / "neutral.html"
        masks_path = preset_dir / "masks.json"
        if not neutral.is_file() or not masks_path.is_file():
            continue
        html = neutral.read_text(encoding="utf-8")
        masks = json.loads(masks_path.read_text(encoding="utf-8"))
        records = masks.get("records") or []
        tokens = _theme_tokens(html)
        bg_luminance = _relative_luminance(tokens.get("bg"))
        polarity = "dark" if bg_luminance is not None and bg_luminance < 0.35 else "light"
        slides = []
        for position, record in enumerate(records):
            boxes = [_clip_box(box) for box in (record.get("occupied_boxes") or [])]
            guarded = [_expand_box(box) for box in boxes]
            occupied_ratio = _union_area(boxes) / (SLIDE_WIDTH * SLIDE_HEIGHT)
            guarded_ratio = _union_area(guarded) / (SLIDE_WIDTH * SLIDE_HEIGHT)
            pockets = _safe_edge_pockets(guarded)
            detail_policy = "edge-ambient-only" if pockets and guarded_ratio < 0.72 else "texture-only"
            reference = preset_dir / "references" / f"slide-{position + 1:03d}.png"
            mask = preset_dir / "masks" / f"protected-mask-{position + 1:03d}.png"
            slides.append(
                {
                    "index": int(record.get("index", position)),
                    "number": position + 1,
                    "id": record.get("id"),
                    "scene_id": record.get("scene_id"),
                    "scene_role": record.get("scene_role"),
                    "layout_id": record.get("layout_id"),
                    "occupied_boxes": boxes,
                    "guard_px": GUARD_PX,
                    "guarded_occupied_ratio": round(guarded_ratio, 6),
                    "occupied_ratio": round(occupied_ratio, 6),
                    "candidate_edge_pockets": pockets,
                    "detail_policy": detail_policy,
                    "reference_screenshot": reference.relative_to(source_root.parent.parent.parent.parent).as_posix()
                    if reference.is_file()
                    else None,
                    "reference_sha256": _sha256(reference) if reference.is_file() else None,
                    "protected_mask": mask.relative_to(source_root.parent.parent.parent.parent).as_posix()
                    if mask.is_file()
                    else None,
                    "protected_mask_sha256": _sha256(mask) if mask.is_file() else None,
                    "human_reference_priority": "binding; mask and candidate pockets are advisory only",
                }
            )
        presets.append(
            {
                "preset": preset_dir.name,
                "source_html": neutral.relative_to(source_root.parent.parent.parent.parent).as_posix(),
                "source_html_sha256": _sha256(neutral),
                "masks_json": masks_path.relative_to(source_root.parent.parent.parent.parent).as_posix(),
                "theme_tokens": tokens,
                "background_polarity": polarity,
                "slide_count": len(slides),
                "slides": slides,
            }
        )
    ledger = {
        "mode": "html-image-background-v6-work-ledger",
        "created_at": _utc_now(),
        "source_root": source_root.relative_to(source_root.parent.parent.parent.parent).as_posix(),
        "output_root": output_root.relative_to(output_root.parent.parent.parent.parent).as_posix(),
        "contract": {
            "slide_size": [1920, 1080],
            "foreground_guard_px": GUARD_PX,
            "minimum_localized_detail_space": [MIN_OPEN_WIDTH, MIN_OPEN_HEIGHT],
            "reference_precedence": ["actual foreground screenshot", "protected mask", "computed edge pockets"],
            "no_open_zone_result": "texture-only model-native continuous raster",
            "post_generation_cutout": False,
        },
        "preset_count": len(presets),
        "slide_count": sum(item["slide_count"] for item in presets),
        "presets": presets,
    }
    return ledger


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--ledger", required=True)
    args = parser.parse_args()
    source_root = Path(args.source_root).resolve()
    output_root = Path(args.output_root).resolve()
    ledger_path = Path(args.ledger).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger = build_ledger(source_root, output_root)
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"presets": ledger["preset_count"], "slides": ledger["slide_count"], "ledger": str(ledger_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
