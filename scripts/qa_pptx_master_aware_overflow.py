"""Master-aware bounds QA for native PPTX decks.

The system ``slides_test.py`` expands only slide-owned shapes with python-pptx.
That is intentionally retained as an external tool signal, but it cannot move
inherited Custom Layout or Slide Master shapes. This checker follows the actual
slide -> layout -> master relationship and evaluates their native OOXML boxes
against a virtual 5% padded canvas without mutating the deck.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


def rels_path(part: str) -> str:
    return posixpath.join(posixpath.dirname(part), "_rels", f"{posixpath.basename(part)}.rels")


def resolve_target(origin_part: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(origin_part), target))


def relationship_target(archive: zipfile.ZipFile, part: str, suffix: str) -> str | None:
    rel_path = rels_path(part)
    if rel_path not in archive.namelist():
        return None
    root = ET.fromstring(archive.read(rel_path))
    for relationship in root.findall("pr:Relationship", NS):
        if str(relationship.attrib.get("Type", "")).endswith(suffix):
            return resolve_target(part, str(relationship.attrib.get("Target", "")))
    return None


def parse_box(element: ET.Element) -> Box | None:
    transform = element.find(".//a:xfrm", NS)
    if transform is None:
        return None
    offset = transform.find("a:off", NS)
    extent = transform.find("a:ext", NS)
    if offset is None or extent is None:
        return None
    try:
        return Box(
            int(offset.attrib.get("x", "0")),
            int(offset.attrib.get("y", "0")),
            int(extent.attrib.get("cx", "0")),
            int(extent.attrib.get("cy", "0")),
        )
    except ValueError:
        return None


def placeholder_key(element: ET.Element) -> tuple[str, str | None] | None:
    placeholder = element.find("p:nvSpPr/p:nvPr/p:ph", NS)
    if placeholder is None:
        return None
    return str(placeholder.attrib.get("type", "body")), placeholder.attrib.get("idx")


def non_visual_name(element: ET.Element) -> str:
    node = element.find(".//p:cNvPr", NS)
    return str(node.attrib.get("name", "")) if node is not None else ""


def object_kind(element: ET.Element) -> str:
    if element.tag.endswith("}pic"):
        return "picture"
    if element.tag.endswith("}graphicFrame"):
        if element.find(".//c:chart", NS) is not None:
            return "chart"
        if element.find(".//a:tbl", NS) is not None:
            return "table"
        return "graphic-frame"
    return "shape"


def object_records(root: ET.Element, owner: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for selector in (".//p:sp", ".//p:pic", ".//p:graphicFrame"):
        for element in root.findall(selector, NS):
            box = parse_box(element)
            if box is None:
                continue
            records.append({
                "owner": owner,
                "kind": object_kind(element),
                "name": non_visual_name(element),
                "placeholder": placeholder_key(element),
                "box_emu": asdict(box),
            })
    return records


def indexed_parts(archive: zipfile.ZipFile, pattern: str) -> list[str]:
    expression = re.compile(pattern)
    return sorted(
        [name for name in archive.namelist() if expression.fullmatch(name)],
        key=lambda value: int(re.search(r"(\d+)\.xml$", value).group(1)),
    )


def _inside_canvas(record: dict[str, Any], width: int, height: int) -> bool:
    box = record["box_emu"]
    return box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= width and box["y"] + box["height"] <= height


def audit_pptx(pptx_path: Path, *, pad_percent: float = 5.0) -> dict[str, Any]:
    """Audit slide + inherited layout/master native boxes without mutation."""
    failures: list[dict[str, Any]] = []
    slide_results: list[dict[str, Any]] = []
    with zipfile.ZipFile(pptx_path) as archive:
        presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
        size = presentation.find("p:sldSz", NS)
        if size is None:
            raise ValueError("PPTX has no presentation slide size")
        width = int(size.attrib["cx"])
        height = int(size.attrib["cy"])
        slides = indexed_parts(archive, r"ppt/slides/slide\d+\.xml")
        for number, slide_part in enumerate(slides, start=1):
            slide_root = ET.fromstring(archive.read(slide_part))
            layout_part = relationship_target(archive, slide_part, "/slideLayout")
            layout_root = ET.fromstring(archive.read(layout_part)) if layout_part and layout_part in archive.namelist() else None
            master_part = relationship_target(archive, layout_part, "/slideMaster") if layout_part else None
            master_root = ET.fromstring(archive.read(master_part)) if master_part and master_part in archive.namelist() else None

            layout_records = object_records(layout_root, "layout") if layout_root is not None else []
            master_records = object_records(master_root, "master") if master_root is not None else []
            slide_records = object_records(slide_root, "slide")
            layout_placeholder_boxes = {
                tuple(item["placeholder"]): item["box_emu"]
                for item in layout_records if item["placeholder"] is not None
            }
            effective: list[dict[str, Any]] = []
            seen_placeholders: set[tuple[str, str | None]] = set()
            for item in slide_records:
                record = dict(item)
                key = record["placeholder"]
                if key is not None:
                    seen_placeholders.add(tuple(key))
                    if record["box_emu"]["width"] == 0 and tuple(key) in layout_placeholder_boxes:
                        record["box_emu"] = layout_placeholder_boxes[tuple(key)]
                        record["inherited_geometry_from"] = "layout"
                effective.append(record)
            for item in layout_records:
                key = item["placeholder"]
                if key is None or tuple(key) not in seen_placeholders:
                    effective.append(dict(item))
            effective.extend(dict(item) for item in master_records if item["placeholder"] is None)

            for record in effective:
                if not _inside_canvas(record, width, height):
                    failures.append({"slide": number, "part": slide_part, **record})
            slide_results.append({
                "number": number,
                "slide_part": slide_part,
                "layout_part": layout_part,
                "master_part": master_part,
                "checked_object_count": len(effective),
                "placeholder_bbox_count": sum(1 for item in effective if item["placeholder"] is not None),
                "native_object_bounds": [item for item in effective if item["kind"] in {"picture", "chart", "table"}],
            })
    padding = {"percent": pad_percent, "left_emu": int(width * pad_percent / 100), "top_emu": int(height * pad_percent / 100)}
    return {
        "schema_version": 1,
        "kind": "pptx_master_aware_overflow_qa",
        "artifact": pptx_path.name,
        "canvas_emu": {"width": width, "height": height},
        "virtual_padding": padding,
        "slides": slide_results,
        "overflow": failures,
        "pass": not failures,
        "external_slides_test_limit": "slides_test.py only shifts slide-owned shapes during its padded clone; it does not shift inherited CustomLayout/SlideMaster geometry, so its raw result is retained as tool evidence but not used as the master-aware overflow verdict.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PPTX slide/layout/master native bounds with a virtual 5% pad.")
    parser.add_argument("--pptx", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--pad-percent", type=float, default=5.0)
    args = parser.parse_args()
    result = audit_pptx(args.pptx.resolve(), pad_percent=args.pad_percent)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "overflow_count": len(result["overflow"]), "report": args.report.as_posix()}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
