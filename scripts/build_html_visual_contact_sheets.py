#!/usr/bin/env python3
"""Build readable contact sheets from browser-rendered HTML slide screenshots."""

from __future__ import annotations

import argparse
import io
import math
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


THUMB_SIZE = (640, 360)
LABEL_HEIGHT = 34


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/msjh.ttc"),
    ):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def build_sheet(files: list[Path], output: Path, columns: int, rows: int) -> None:
    cell_w, cell_h = THUMB_SIZE[0], THUMB_SIZE[1] + LABEL_HEIGHT
    canvas = Image.new("RGB", (columns * cell_w, rows * cell_h), "#10151d")
    draw = ImageDraw.Draw(canvas)
    font = load_font(17)
    for index, path in enumerate(files):
        row, column = divmod(index, columns)
        x, y = column * cell_w, row * cell_h
        with Image.open(path) as image:
            thumb = image.convert("RGB").resize(THUMB_SIZE, Image.Resampling.LANCZOS)
        canvas.paste(thumb, (x, y))
        label = path.stem.replace("slide-", "")
        draw.rectangle((x, y + THUMB_SIZE[1], x + cell_w, y + cell_h), fill="#182230")
        draw.text((x + 12, y + THUMB_SIZE[1] + 7), label, font=font, fill="#e9f0fa")
    output.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    canvas.save(buffer, format="JPEG", quality=88, subsampling=0)
    payload = buffer.getvalue()
    for attempt in range(8):
        try:
            output.write_bytes(payload)
            break
        except OSError:
            if attempt == 7:
                raise
            time.sleep(0.18 * (attempt + 1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--columns", type=int, default=3)
    parser.add_argument("--rows", type=int, default=3)
    args = parser.parse_args()

    source = Path(args.input_dir).resolve()
    output = Path(args.output_dir).resolve()
    files = sorted(path for pattern in ("slide-*.jpg", "slide-*.png") for path in source.glob(pattern))
    page_size = args.columns * args.rows
    if not files:
        raise SystemExit(f"No slide screenshots found in {source}")
    output.mkdir(parents=True, exist_ok=True)
    for stale in output.glob("contact-*.jpg"):
        stale.unlink()
    pages = math.ceil(len(files) / page_size)
    for page in range(pages):
        start = page * page_size
        build_sheet(
            files[start : start + page_size],
            output / f"contact-{page + 1:02d}.jpg",
            args.columns,
            args.rows,
        )
    print({"slides": len(files), "contact_sheets": pages, "output": str(output)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
