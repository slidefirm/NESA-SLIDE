#!/usr/bin/env python3
"""Verify that a theme demo shares valid Theme/Layout sources and contains no placeholder copy."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


FORBIDDEN = ["重點內容", "清楚的重點標題", "圖片內容區", "數據視覺區", "比較資訊區"]
EMU_PER_PX = 9525
CONTENT_BOUNDS_PX = {"left": 64, "top": 64, "right": 1216, "bottom": 656}
NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


def pptx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        chunks = []
        for name in archive.namelist():
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", name):
                chunks.append(archive.read(name).decode("utf-8", errors="ignore"))
        return "\n".join(chunks)


def pptx_slide_count(path: Path) -> int:
    with zipfile.ZipFile(path) as archive:
        return len([name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)])


def pptx_card_alignment(path: Path, slide_numbers: list[int]) -> list[dict[str, float | int | bool]]:
    results = []
    with zipfile.ZipFile(path) as archive:
        for slide_number in slide_numbers:
            root = ET.fromstring(archive.read(f"ppt/slides/slide{slide_number}.xml"))
            shapes = []
            for shape in root.findall(".//p:sp", NS):
                meta = shape.find("./p:nvSpPr/p:cNvPr", NS)
                transform = shape.find("./p:spPr/a:xfrm", NS)
                if meta is None or transform is None:
                    continue
                name = meta.attrib.get("name", "")
                if not (name.startswith("card-") and name not in {"card-page-title", "card-page-subtitle"}) and name not in {"card-page-title", "card-page-subtitle"}:
                    continue
                offset = transform.find("a:off", NS)
                extent = transform.find("a:ext", NS)
                if offset is None or extent is None:
                    continue
                shapes.append(
                    {
                        "name": name,
                        "left": int(offset.attrib["x"]) / EMU_PER_PX,
                        "top": int(offset.attrib["y"]) / EMU_PER_PX,
                        "width": int(extent.attrib["cx"]) / EMU_PER_PX,
                        "height": int(extent.attrib["cy"]) / EMU_PER_PX,
                    }
                )
            cards = [shape for shape in shapes if str(shape["name"]).startswith("card-") and shape["name"] not in {"card-page-title", "card-page-subtitle"}]
            left = min(float(shape["left"]) for shape in cards)
            right = max(float(shape["left"]) + float(shape["width"]) for shape in cards)
            top = min(float(shape["top"]) for shape in shapes)
            bottom = max(float(shape["top"]) + float(shape["height"]) for shape in shapes)
            edge_error = max(abs(left - CONTENT_BOUNDS_PX["left"]), abs(right - CONTENT_BOUNDS_PX["right"]))
            vertical_balance_error = abs((top - CONTENT_BOUNDS_PX["top"]) - (CONTENT_BOUNDS_PX["bottom"] - bottom))
            results.append(
                {
                    "slide": slide_number,
                    "edge_error_px": round(edge_error, 3),
                    "vertical_balance_error_px": round(vertical_balance_error, 3),
                    "pass": edge_error <= 1 and vertical_balance_error <= 1,
                }
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--demo", required=True)
    parser.add_argument("--html", required=True)
    parser.add_argument("--pptx", required=True)
    parser.add_argument("--html-report", required=True)
    parser.add_argument("--pptx-report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    matrix = json.loads(Path(args.matrix).read_text(encoding="utf-8"))
    demo = json.loads(Path(args.demo).read_text(encoding="utf-8"))
    html = Path(args.html).read_text(encoding="utf-8")
    pptx = pptx_text(Path(args.pptx))
    html_report = json.loads(Path(args.html_report).read_text(encoding="utf-8"))
    pptx_report = json.loads(Path(args.pptx_report).read_text(encoding="utf-8-sig"))
    pptx_path = Path(args.pptx)

    theme_ids = {row["id"] for row in matrix["themes"]}
    layout_ids = {row["id"] for row in matrix["layouts"]}
    selected = [row["layout_id"] for row in demo["slides"]]
    card_slide_numbers = [index for index, row in enumerate(demo["slides"], 1) if row["kind"] == "cards"]
    card_alignment = pptx_card_alignment(pptx_path, card_slide_numbers)
    checks = {
        "theme_exists": demo["theme_id"] in theme_ids,
        "layouts_exist": all(layout_id in layout_ids for layout_id in selected),
        "layout_count": len(selected),
        "unique_layout_count": len(set(selected)),
        "html_slide_count": html.count('<section class="slide'),
        "pptx_slide_count": pptx_slide_count(pptx_path),
        "html_overflow_issues": len(html_report.get("issues", [])),
        "pptx_render_failures": int(pptx_report.get("failures", 0)),
        "html_edge_fit_frames": html.count('data-content-frame="edge-fit"'),
        "html_edit_framework": all(fragment in html for fragment in ['id="canvasBox"', 'id="barInner"', 'id="hint"', 'data-edit-mode-embedded="true"'])
        and '<script src="edit-mode.js"></script>' not in html,
        "html_stable_slide_ids": all(f'id="s{index}"' in html for index in range(1, 15)),
        "pptx_card_alignment": card_alignment,
        "forbidden_copy_in_html": [value for value in FORBIDDEN if value in html],
        "forbidden_copy_in_pptx": [value for value in FORBIDDEN if value in pptx],
    }
    checks["pass"] = all([
        checks["theme_exists"],
        checks["layouts_exist"],
        checks["layout_count"] == 14,
        checks["unique_layout_count"] == 14,
        checks["html_slide_count"] == 14,
        checks["pptx_slide_count"] == 14,
        checks["html_overflow_issues"] == 0,
        checks["pptx_render_failures"] == 0,
        checks["html_edge_fit_frames"] == len(card_slide_numbers),
        checks["html_edit_framework"],
        checks["html_stable_slide_ids"],
        all(row["pass"] for row in card_alignment),
        not checks["forbidden_copy_in_html"],
        not checks["forbidden_copy_in_pptx"],
    ])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=False))
    return 0 if checks["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
