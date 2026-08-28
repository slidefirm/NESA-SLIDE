#!/usr/bin/env python3
"""Build the Layout Catalog HTML Theme Lab subpage from archived theme cases."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "artifacts" / "theme-demos" / "html-theme-lab" / "theme-lab-archive.json"
DEFAULT_CASES = ROOT / "artifacts" / "deploy" / "renderer-cases.js"
DEFAULT_TEMPLATE = ROOT / "scripts" / "templates" / "html-theme-lab" / "index.html"
DEFAULT_OUTPUT = ROOT / "artifacts" / "deploy" / "theme-html-lab" / "index.html"


def build(archive_path: Path, cases_path: Path, template_path: Path, output_path: Path) -> dict:
    # Keep cases_path in the public function signature for older build commands.
    # Theme Lab assets now live on this same Pages site, so no renderer-case lookup is needed.
    _ = cases_path
    archive = json.loads(archive_path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for row in archive["themes"]:
        if row.get("publish", True) is False:
            continue
        theme_id = row["theme_id"]
        rows.append({
            **row,
            "preview_url": f"/theme-presets/{theme_id}.jpg",
            "html_url": f"/theme-html-lab/{theme_id}/",
        })
    payload = {**archive, "themes": rows}
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    document = template_path.read_text(encoding="utf-8")
    document = document.replace("__BUILD_TIMESTAMP__", now)
    document = document.replace("__THEME_LAB_DATA__", json.dumps(payload, ensure_ascii=False))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(8):
        try:
            output_path.write_text(document, encoding="utf-8", newline="\n")
            break
        except OSError:
            if attempt == 7:
                raise
            time.sleep(0.18 * (attempt + 1))
    result = {
        "themes": len(rows),
        "output": output_path.relative_to(ROOT).as_posix(),
        "public_url": "https://layout-catalog.pages.dev/theme-html-lab/",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.archive.resolve(), args.cases.resolve(), args.template.resolve(), args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
