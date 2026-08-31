#!/usr/bin/env python3
"""Verify full HTML/PPTX Theme x Layout renderer matrix artifacts."""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import zipfile
from collections import Counter
from contextlib import nullcontext
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from PIL import Image, ImageStat


NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
REL_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}


def normalize_placeholder_type(value: str | None) -> str:
    value = (value or "body").strip().lower()
    return {
        "subtitle": "subtitle",
        "sub-title": "subtitle",
        "pic": "picture",
        "picture": "picture",
        "chart": "chart",
        "tbl": "table",
        "table": "table",
        "title": "title",
        "body": "body",
    }.get(value, value)


def expected_placeholder_schema(layout: dict[str, Any]) -> list[dict[str, Any]]:
    pptx = layout.get("pptx") or {}
    schema = pptx.get("placeholder_schema")
    if isinstance(schema, list):
        return [row for row in schema if isinstance(row, dict)]
    return [
        {"id": slot["id"], "placeholder_type": (slot.get("pptx") or {}).get("placeholder_type", "body")}
        for slot in layout.get("slots", [])
    ]


def slide_layout_target(archive: zipfile.ZipFile, slide_name: str) -> str | None:
    rel_name = f"ppt/slides/_rels/{Path(slide_name).name}.rels"
    if rel_name not in archive.namelist():
        return None
    rel_root = ET.fromstring(archive.read(rel_name))
    for rel in rel_root.findall("r:Relationship", REL_NS):
        if str(rel.attrib.get("Type", "")).endswith("/slideLayout"):
            target = rel.attrib.get("Target", "")
            return posixpath.normpath(posixpath.join("ppt/slides", target)) if not target.startswith("/") else target.lstrip("/")
    return None


def layout_placeholder_rows(archive: zipfile.ZipFile, layout_name: str) -> tuple[list[tuple[str, str, str | None]], str | None]:
    root = ET.fromstring(archive.read(layout_name))
    rows: list[tuple[str, str, str | None]] = []
    for shape in root.findall(".//p:sp", NS):
        ph = shape.find(".//p:ph", NS)
        if ph is None:
            continue
        c_nv = shape.find(".//p:nvSpPr/p:cNvPr", NS)
        shape_name = c_nv.attrib.get("name") if c_nv is not None else None
        rows.append((normalize_placeholder_type(ph.attrib.get("type")), shape_name or "", ph.attrib.get("idx")))
    c_sld = root.find(".//p:cSld", NS)
    logical_name = c_sld.attrib.get("name", "") if c_sld is not None else ""
    return rows, logical_name


def image_check(path: Path, expected_size: tuple[int, int]) -> str | None:
    with Image.open(path) as image:
        if image.size != expected_size:
            return f"size={image.size}"
        stat = ImageStat.Stat(image.convert("RGB").resize((64, 36)))
        if max(stat.var) < 1.0:
            return f"near-blank variance={stat.var}"
    return None


def numeric_part(value: str) -> int:
    match = re.search(r"(\d+)\.xml$", value)
    return int(match.group(1)) if match else 0


def pptx_structure(path: Path | zipfile.ZipFile, theme_id: str, expected_layouts: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    archive_context = zipfile.ZipFile(path) if not isinstance(path, zipfile.ZipFile) else nullcontext(path)
    with archive_context as archive:
        names = set(archive.namelist())
        slides = sorted((name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)), key=numeric_part)
        layouts = sorted((name for name in names if re.fullmatch(r"ppt/slideLayouts/slideLayout\d+\.xml", name)), key=numeric_part)
        masters = sorted((name for name in names if re.fullmatch(r"ppt/slideMasters/slideMaster\d+\.xml", name)), key=numeric_part)
        if len(slides) != len(expected_layouts):
            errors.append(f"slide-count={len(slides)}")
        layout_rows: dict[str, tuple[str, list[tuple[str, str, str | None]]]] = {}
        for layout_path in layouts:
            placeholder_rows, logical_name = layout_placeholder_rows(archive, layout_path)
            layout_rows[logical_name] = (layout_path, placeholder_rows)
        expected_layout_names = {
            str((layout.get("pptx") or {}).get("layout_name") or f"layout--{layout['id']}")
            for layout in expected_layouts
        }
        missing_layouts = sorted(expected_layout_names - set(layout_rows))
        if missing_layouts:
            errors.append(f"missing-layouts={missing_layouts}")
        for layout in expected_layouts:
            expected_name = str((layout.get("pptx") or {}).get("layout_name") or f"layout--{layout['id']}")
            if expected_name not in layout_rows:
                continue
            layout_path, actual_rows = layout_rows[expected_name]
            expected_schema = expected_placeholder_schema(layout)
            expected_types = Counter(normalize_placeholder_type(row.get("placeholder_type")) for row in expected_schema)
            actual_types = Counter(row[0] for row in actual_rows)
            if actual_types != expected_types:
                errors.append(f"layout-{expected_name}-placeholder-types={dict(actual_types)}!=expected={dict(expected_types)}")
            expected_ids = {str(row.get("id")) for row in expected_schema if row.get("id")}
            actual_ids = {row[1] for row in actual_rows if row[1]}
            missing_ids = sorted(expected_ids - actual_ids)
            if missing_ids:
                errors.append(f"layout-{expected_name}-missing-placeholder-names={missing_ids}")
            actual_indices = [int(row[2]) for row in actual_rows if row[2] is not None and str(row[2]).isdigit()]
            if actual_indices and sorted(actual_indices) != list(range(len(actual_rows))):
                errors.append(f"layout-{expected_name}-placeholder-indices={actual_indices}")
            if layout_path not in names:
                errors.append(f"layout-{expected_name}-missing-package-entry")
        master_names = {
            ET.fromstring(archive.read(name)).find(".//p:cSld", NS).attrib.get("name", "")
            for name in masters
        }
        if f"theme--{theme_id}" not in master_names:
            errors.append(f"missing-master=theme--{theme_id}")
        for index, slide_name in enumerate(slides):
            target = slide_layout_target(archive, slide_name)
            if not target or target not in names:
                errors.append(f"slide-{index + 1}-layout-relationship={target or 'missing'}")
    return {"slides": len(slides), "layouts": len(layouts), "masters": len(masters), "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--html-dir", required=True)
    parser.add_argument("--html-report", required=True)
    parser.add_argument("--html-screenshot-dir", required=True)
    parser.add_argument("--pptx-dir", required=True)
    parser.add_argument("--pptx-render-dir", required=True)
    parser.add_argument("--pptx-render-report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    matrix = json.loads(Path(args.matrix).read_text(encoding="utf-8"))
    themes = [theme["id"] for theme in matrix["themes"]]
    layouts = matrix["layouts"]
    expected_theme_count = len(themes)
    expected_layout_count = len(layouts)
    expected_slides = expected_theme_count * expected_layout_count
    errors: list[str] = []

    html_dir = Path(args.html_dir)
    html_files = sorted(html_dir.glob("*.html"))
    if {path.stem for path in html_files} != set(themes):
        errors.append("html-theme-coverage")
    for path in html_files:
        text = path.read_text(encoding="utf-8")
        count = len(re.findall(r'data-layout-id="', text))
        if count != expected_layout_count:
            errors.append(f"html-layout-count:{path.stem}={count}")

    html_report = json.loads(Path(args.html_report).read_text(encoding="utf-8"))
    if html_report.get("slides") != expected_slides:
        errors.append(f"html-captured={html_report.get('slides')}")
    if html_report.get("issues"):
        errors.append(f"html-overflow-issues={len(html_report['issues'])}")
    html_images = sorted(Path(args.html_screenshot_dir).glob("*/*.jpg"))
    if len(html_images) != expected_slides:
        errors.append(f"html-image-count={len(html_images)}")
    for path in html_images:
        issue = image_check(path, (960, 540))
        if issue:
            errors.append(f"html-image:{path.name}:{issue}")

    pptx_dir = Path(args.pptx_dir)
    pptx_files = sorted(pptx_dir.glob("*.pptx"))
    if {path.stem for path in pptx_files} != set(themes):
        errors.append("pptx-theme-coverage")
    pptx_structures: dict[str, Any] = {}
    for path in pptx_files:
        result = pptx_structure(path, path.stem, layouts)
        pptx_structures[path.stem] = result
        errors.extend(f"pptx-structure:{path.stem}:{item}" for item in result["errors"])

    pptx_render_report = json.loads(Path(args.pptx_render_report).read_text(encoding="utf-8-sig"))
    if pptx_render_report.get("rendered") != expected_slides:
        errors.append(f"pptx-rendered={pptx_render_report.get('rendered')}")
    if pptx_render_report.get("failures"):
        errors.append(f"pptx-render-failures={pptx_render_report['failures']}")
    pptx_images = sorted(Path(args.pptx_render_dir).glob("*/*.PNG"))
    if len(pptx_images) != expected_slides:
        errors.append(f"pptx-image-count={len(pptx_images)}")
    for path in pptx_images:
        issue = image_check(path, (1280, 720))
        if issue:
            errors.append(f"pptx-image:{path.name}:{issue}")

    report = {
        "status": "pass" if not errors else "fail",
        "expected": {"themes": expected_theme_count, "layouts": expected_layout_count, "slides_per_renderer": expected_slides},
        "html": {"files": len(html_files), "screenshots": len(html_images), "overflow_issues": len(html_report.get("issues", []))},
        "pptx": {"files": len(pptx_files), "renders": len(pptx_images), "structures": pptx_structures},
        "errors": errors,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": len(errors), "html": report["html"], "pptx_files": len(pptx_files), "pptx_renders": len(pptx_images)}, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
