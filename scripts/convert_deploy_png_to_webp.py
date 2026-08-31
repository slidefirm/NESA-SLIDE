from __future__ import annotations

import argparse
import re
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = ROOT / "artifacts" / "deploy"


def convert_png(path: Path, quality: int, force: bool) -> tuple[Path, int, int] | None:
    out = path.with_suffix(".webp")
    if out.exists() and not force and out.stat().st_mtime >= path.stat().st_mtime:
        return out, path.stat().st_size, out.stat().st_size

    with Image.open(path) as image:
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
        out.parent.mkdir(parents=True, exist_ok=True)
        image.save(out, "WEBP", quality=quality, method=6)
    return out, path.stat().st_size, out.stat().st_size


def rewrite_references(path: Path) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        ref = match.group(0)
        if ref.startswith(("http://", "https://", "data:")):
            return ref
        webp_ref = ref[:-4] + ".webp"
        candidate = (path.parent / webp_ref).resolve()
        if candidate.exists() and DEPLOY_DIR.resolve() in candidate.parents:
            return webp_ref
        deploy_candidate = (DEPLOY_DIR / webp_ref).resolve()
        if deploy_candidate.exists():
            return webp_ref
        return ref

    updated = re.sub(r'(?<![A-Za-z0-9_./:-])(?:[A-Za-z0-9_\-./]+)\.png', replace, text)
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert deployed PNG previews to WebP and rewrite deploy references.")
    parser.add_argument("--quality", type=int, default=84)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    png_paths = sorted(DEPLOY_DIR.rglob("*.png"))
    converted = []
    for path in png_paths:
        result = convert_png(path, args.quality, args.force)
        if result:
            converted.append(result)

    rewrite_targets = [
        DEPLOY_DIR / "index.html",
        DEPLOY_DIR / "layout-gallery.js",
        DEPLOY_DIR / "themes-gallery.js",
    ]
    review_dir = DEPLOY_DIR / "review"
    if review_dir.exists():
        rewrite_targets.extend(sorted(review_dir.glob("**/*.html")))
        rewrite_targets.extend(sorted(review_dir.glob("**/*.json")))
    rewritten = sum(rewrite_references(path) for path in rewrite_targets)

    total_png = sum(before for _, before, _ in converted)
    total_webp = sum(after for _, _, after in converted)
    saved = total_png - total_webp
    ratio = (total_webp / total_png * 100) if total_png else 0

    print(f"PNG files scanned: {len(png_paths)}")
    print(f"WebP files ready: {len(converted)}")
    print(f"Original PNG total: {total_png / 1024 / 1024:.2f} MB")
    print(f"WebP total: {total_webp / 1024 / 1024:.2f} MB")
    print(f"Saved: {saved / 1024 / 1024:.2f} MB ({ratio:.1f}% of PNG size)")
    print(f"Reference files rewritten: {rewritten}")


if __name__ == "__main__":
    main()
