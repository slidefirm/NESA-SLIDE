#!/usr/bin/env python3
"""Build the independently deployed HTML/PPTX renderer case site.

The heavy case artifacts stay outside artifacts/deploy.  The main Layout
Catalog receives only renderer-cases.js, which contains metadata and links.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "prompt_system" / "demos" / "renderer-case-catalog.json"
DEFAULT_TEMPLATE = ROOT / "scripts" / "templates" / "renderer-cases" / "index.html"
DEFAULT_OUTPUT = ROOT / "artifacts" / "renderer-cases-deploy"
DEFAULT_MAIN_MANIFEST = ROOT / "artifacts" / "deploy" / "renderer-cases.js"
DEFAULT_THEME_LAB_ARCHIVE = ROOT / "artifacts" / "theme-demos" / "html-theme-lab" / "theme-lab-archive.json"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def assert_source(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {rel(path)}")


def safe_clean_output(output: Path) -> None:
    output = output.resolve()
    allowed_parent = (ROOT / "artifacts").resolve()
    if output.parent != allowed_parent or output.name != "renderer-cases-deploy":
        raise ValueError(f"Refusing to clean unexpected output path: {output}")
    if output.exists():
        try:
            shutil.rmtree(output)
        except PermissionError:
            # OneDrive/PowerPoint can hold an unrelated exported PPTX directory
            # open.  The deploy manifest is authoritative, so preserve that
            # locked directory and overwrite every current case artifact below.
            pass
    output.mkdir(parents=True, exist_ok=True)


def html_layout_map(source: Path) -> dict[str, int]:
    text = source.read_text(encoding="utf-8")
    # Only count real slide section tags. Theme adapters may legitimately
    # contain CSS selectors such as [data-layout-id="..."]; treating those as
    # slides makes the deploy catalog report layouts that do not exist.
    section_tags = re.findall(r"<section\b[^>]*>", text, flags=re.IGNORECASE)
    ids: list[str] = []
    for tag in section_tags:
        class_match = re.search(r'class="([^"]*)"', tag, flags=re.IGNORECASE)
        if not class_match or "slide" not in class_match.group(1).split():
            continue
        layout_match = re.search(r'data-layout-id="([^"]+)"', tag, flags=re.IGNORECASE)
        if layout_match:
            ids.append(layout_match.group(1))
    return {layout_id: index for index, layout_id in enumerate(ids, start=1)}


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def public_url(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def theme_lab_cases(archive_path: Path) -> list[dict]:
    if not archive_path.is_file():
        return []
    archive = json.loads(archive_path.read_text(encoding="utf-8"))
    cases: list[dict] = []
    for row in sorted(archive.get("themes", []), key=lambda item: item["order"]):
        theme_id = row["theme_id"]
        display_name = row["theme"]["display_name"]
        cases.append({
            "id": f"html-theme-lab-{theme_id}",
            "priority": 100 + int(row["order"]),
            "featured": False,
            "group": "html-theme-lab",
            "family": row["family"],
            "title": display_name,
            "eyebrow": f"HTML THEME LAB · {row['order']:02d}",
            "theme_id": theme_id,
            "summary": row["design_intent"],
            "slide_count": row["slide_count"],
            "layout_ids": row["layouts"],
            "architecture": row.get("architecture", []),
            "design_dialect": row.get("design_dialect"),
            "composition": row.get("composition"),
            "techniques": row.get("techniques", []),
            "assembly": row.get("assembly", {}),
            "design_decisions": row.get("design_decisions", []),
            "pattern": row["pattern"],
            "material": row["material"],
            "color_blocks": row["color_blocks"],
            "decorations": row["decorations"],
            "design_intent": row["design_intent"],
            "topic": row["topic"],
            "preview_source": f"artifacts/theme-demos/html-theme-lab/qa/contact-sheets/{theme_id}/contact-01.jpg",
            "qa": [f"{row['slide_count']} 頁可編輯 HTML", "內容先行的獨立 assembly", "逐頁瀏覽器與編輯器 QA"],
            "formats": {
                "html": {
                    "source": row["source_html"],
                    "public_path": f"theme-html-lab/{theme_id}/index.html",
                    "label": "開啟 HTML",
                    "description": f"檢查 {display_name} 的 {row['slide_count']} 頁完整可編輯內容先行 HTML deck。",
                }
            },
        })
    return cases


def build(
    catalog_path: Path,
    template_path: Path,
    output: Path,
    main_manifest: Path,
    theme_lab_archive: Path = DEFAULT_THEME_LAB_ARCHIVE,
) -> dict:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["cases"] = [*catalog["cases"], *theme_lab_cases(theme_lab_archive)]
    base_url = catalog["site"]["public_base_url"].rstrip("/")
    safe_clean_output(output)

    public_cases: list[dict] = []
    total_bytes = 0

    for source_case in sorted(catalog["cases"], key=lambda item: item.get("priority", 999)):
        case = {key: value for key, value in source_case.items() if key not in {"preview_source", "formats"}}

        preview_source = ROOT / source_case["preview_source"]
        assert_source(preview_source, f"{source_case['id']} preview")
        preview_path = f"previews/{source_case['id']}{preview_source.suffix.lower()}"
        copy_file(preview_source, output / preview_path)
        total_bytes += preview_source.stat().st_size
        case["preview_url"] = public_url(base_url, preview_path)

        public_formats: dict[str, dict] = {}
        html_map: dict[str, int] = {}
        for format_id, source_format in source_case["formats"].items():
            source = ROOT / source_format["source"]
            assert_source(source, f"{source_case['id']} {format_id}")
            destination = output / source_format["public_path"]
            copy_file(source, destination)
            total_bytes += source.stat().st_size

            if format_id == "html":
                html_map = html_layout_map(source)
                editor_source = source.parent / "edit-mode.js"
                if editor_source.is_file():
                    copy_file(editor_source, destination.parent / "edit-mode.js")
                    total_bytes += editor_source.stat().st_size

            public_formats[format_id] = {
                key: value for key, value in source_format.items() if key not in {"source", "public_path"}
            }
            url_path = source_format["public_path"]
            if format_id == "html" and url_path.endswith("/index.html"):
                url_path = url_path[: -len("index.html")]
            public_formats[format_id]["url"] = public_url(base_url, url_path)
            public_formats[format_id]["bytes"] = source.stat().st_size

        declared_layouts = source_case.get("layout_ids", [])
        if html_map and set(html_map) != set(declared_layouts):
            missing = sorted(set(declared_layouts) - set(html_map))
            extra = sorted(set(html_map) - set(declared_layouts))
            raise ValueError(f"{source_case['id']} layout mismatch; missing={missing}, extra={extra}")

        case["formats"] = public_formats
        case["html_slide_by_layout"] = html_map
        public_cases.append(case)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    public_manifest = {
        "version": catalog["version"],
        "generated_at": now,
        "asset_base_url": base_url,
        "total_asset_bytes": total_bytes,
        "cases": public_cases,
    }

    manifest_json = json.dumps(public_manifest, ensure_ascii=False, indent=2)
    (output / "manifest.json").write_text(manifest_json + "\n", encoding="utf-8")

    template = template_path.read_text(encoding="utf-8")
    template = template.replace("__BUILD_TIMESTAMP__", now)
    template = template.replace("__MANIFEST_VERSION__", str(catalog["version"]))
    template = template.replace("__RENDERER_CASE_DATA__", json.dumps(public_manifest, ensure_ascii=False))
    (output / "index.html").write_text(template, encoding="utf-8")

    main_manifest.parent.mkdir(parents=True, exist_ok=True)
    main_manifest.write_text(
        "window.RENDERER_CASES = " + json.dumps(public_manifest, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )

    return {
        "cases": len(public_cases),
        "formats": sum(len(case["formats"]) for case in public_cases),
        "total_asset_bytes": total_bytes,
        "output": rel(output),
        "main_manifest": rel(main_manifest),
        "base_url": base_url,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--main-manifest", type=Path, default=DEFAULT_MAIN_MANIFEST)
    parser.add_argument("--theme-lab-archive", type=Path, default=DEFAULT_THEME_LAB_ARCHIVE)
    args = parser.parse_args()

    result = build(
        args.catalog.resolve(),
        args.template.resolve(),
        args.output.resolve(),
        args.main_manifest.resolve(),
        args.theme_lab_archive.resolve(),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
