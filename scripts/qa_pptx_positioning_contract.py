from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"p": P, "a": A, "r": R}
EMU_PER_PX = 9525


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalize_type(value: str | None) -> str:
    return {
        "title": "title",
        "subtitle": "subTitle",
        "subTitle": "subTitle",
        "body": "body",
        "picture": "pic",
        "pic": "pic",
        "chart": "chart",
        "table": "tbl",
        "tbl": "tbl",
    }.get(value or "body", value or "body")


def part_number(name: str) -> int:
    match = re.search(r"(\d+)\.xml$", name)
    return int(match.group(1)) if match else 0


def relationship_rows(archive: zipfile.ZipFile, rel_name: str) -> list[dict[str, str]]:
    if rel_name not in archive.namelist():
        return []
    root = ET.fromstring(archive.read(rel_name))
    return [
        {"type": row.attrib.get("Type", ""), "target": row.attrib.get("Target", "")}
        for row in root.findall("./r:Relationship", NS)
    ]


def resolve_target(part_dir: str, target: str) -> str:
    return target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(part_dir, target))


def shape_rows(xml: bytes) -> dict[str, dict[str, Any]]:
    root = ET.fromstring(xml)
    rows: dict[str, dict[str, Any]] = {}
    for shape in root.findall(".//p:sp", NS):
        c_nv = shape.find("./p:nvSpPr/p:cNvPr", NS)
        if c_nv is None:
            continue
        name = c_nv.attrib.get("name", "")
        ph = shape.find("./p:nvSpPr/p:nvPr/p:ph", NS)
        xfrm = shape.find("./p:spPr/a:xfrm", NS)
        position = None
        if xfrm is not None:
            off = xfrm.find("./a:off", NS)
            ext = xfrm.find("./a:ext", NS)
            if off is not None and ext is not None:
                position = {
                    "left": int(off.attrib["x"]),
                    "top": int(off.attrib["y"]),
                    "width": int(ext.attrib["cx"]),
                    "height": int(ext.attrib["cy"]),
                }
        adjustment = None
        gd = shape.find("./p:spPr/a:prstGeom/a:avLst/a:gd[@name='adj']", NS)
        if gd is not None:
            match = re.search(r"(-?\d+)", gd.attrib.get("fmla", ""))
            adjustment = int(match.group(1)) if match else None
        index = None
        ph_type = None
        if ph is not None:
            ph_type = normalize_type(ph.attrib.get("type"))
            index = int(ph.attrib["idx"]) if ph.attrib.get("idx", "").isdigit() else (0 if ph_type == "title" else None)
        rows[name] = {"type": ph_type, "index": index, "position": position, "adjustment": adjustment}
    return rows


def layout_name(xml: bytes) -> str:
    root = ET.fromstring(xml)
    c_sld = root.find("./p:cSld", NS)
    return c_sld.attrib.get("name", "") if c_sld is not None else ""


def placeholder_indices(rows: list[dict[str, Any]]) -> list[int]:
    used: set[int] = set()
    next_index = 0
    result: list[int] = []
    for row_index, row in enumerate(rows):
        if row.get("index") is not None:
            index = int(row["index"])
            if index < 0 or index in used:
                raise ValueError(f"invalid or duplicate placeholder index at row {row_index}: {index}")
            used.add(index)
            next_index = max(next_index, index + 1)
        else:
            while next_index in used:
                next_index += 1
            index = next_index
            used.add(index)
            next_index += 1
        result.append(index)
    return result


def offset_for(slide: dict[str, Any]) -> dict[str, float]:
    value = slide.get("composition_offset_percent") or {}
    return {"dx": float(value.get("dx", 0)), "dy": float(value.get("dy", 0))}


def materialized_layout_name(slide: dict[str, Any]) -> str:
    base = str(slide["layout_name"])
    offset = offset_for(slide)
    if abs(offset["dx"]) < 1e-9 and abs(offset["dy"]) < 1e-9:
        return base

    def encode(value: float) -> str:
        text = str(int(value)) if value.is_integer() else str(value)
        return text.replace("-", "m").replace(".", "p")

    return f"{base}--offset-{encode(offset['dx'])}-{encode(offset['dy'])}"


def expected_position(region: list[float], offset: dict[str, float]) -> dict[str, int]:
    x, y, width, height = (float(value) for value in region)
    return {
        "left": round((x + offset["dx"]) * 12.8 * EMU_PER_PX),
        "top": round((y + offset["dy"]) * 7.2 * EMU_PER_PX),
        "width": round(width * 12.8 * EMU_PER_PX),
        "height": round(height * 7.2 * EMU_PER_PX),
    }


def max_delta_px(actual: dict[str, int] | None, expected: dict[str, int]) -> float | None:
    if actual is None:
        return None
    return max(abs(actual[key] - expected[key]) / EMU_PER_PX for key in expected)


def optional_json(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pptx", required=True)
    parser.add_argument("--selection-manifest", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--powerpoint-report")
    parser.add_argument("--reset-report")
    parser.add_argument("--slides-test-report")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    pptx_path = Path(args.pptx).resolve()
    selection_path = Path(args.selection_manifest).resolve()
    project_root = Path(args.project_root).resolve()
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    slide_reports: list[dict[str, Any]] = []
    selected_background = (selection.get("background_selection") or {}).get("selected") or {}
    background_by_role = {str(row.get("id")): str(row.get("asset")) for row in selected_background.get("roles", [])}

    with zipfile.ZipFile(pptx_path) as archive:
        names = archive.namelist()
        absolute_relationships = []
        for name in names:
            if name.endswith(".rels"):
                for row in relationship_rows(archive, name):
                    if row["target"].startswith("/"):
                        absolute_relationships.append({"part": name, "target": row["target"]})
        if absolute_relationships:
            errors.append(f"absolute relationship targets={len(absolute_relationships)}")

        layouts: dict[str, dict[str, Any]] = {}
        for part in sorted((name for name in names if re.fullmatch(r"ppt/slideLayouts/slideLayout\d+\.xml", name)), key=part_number):
            rel_name = part.replace("ppt/slideLayouts/", "ppt/slideLayouts/_rels/") + ".rels"
            image_hashes = []
            for row in relationship_rows(archive, rel_name):
                if row["type"].endswith("/image"):
                    target = resolve_target("ppt/slideLayouts", row["target"])
                    image_hashes.append(sha256_bytes(archive.read(target)))
            layouts[layout_name(archive.read(part))] = {"part": part, "shapes": shape_rows(archive.read(part)), "image_hashes": image_hashes}

        slide_parts = sorted((name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)), key=part_number)
        if len(slide_parts) != len(selection.get("slides", [])):
            errors.append(f"slide count={len(slide_parts)} expected={len(selection.get('slides', []))}")

        slide_image_relationships = 0
        for slide_index, slide_spec in enumerate(selection.get("slides", [])):
            expected_layout_name = materialized_layout_name(slide_spec)
            layout = layouts.get(expected_layout_name)
            if layout is None:
                errors.append(f"slide-{slide_index + 1}: missing layout {expected_layout_name}")
                continue
            slide_part = slide_parts[slide_index]
            slide_shapes = shape_rows(archive.read(slide_part))
            slide_rel_name = slide_part.replace("ppt/slides/", "ppt/slides/_rels/") + ".rels"
            slide_layout_target = None
            for row in relationship_rows(archive, slide_rel_name):
                if row["type"].endswith("/slideLayout"):
                    slide_layout_target = resolve_target("ppt/slides", row["target"])
                if row["type"].endswith("/image"):
                    slide_image_relationships += 1
            if slide_layout_target != layout["part"]:
                errors.append(f"slide-{slide_index + 1}: layout relationship={slide_layout_target} expected={layout['part']}")

            role = str(slide_spec.get("background_role"))
            asset = background_by_role.get(role)
            expected_background_hash = sha256_file(project_root / asset) if asset else None
            if layout["image_hashes"] != ([expected_background_hash] if expected_background_hash else []):
                errors.append(f"slide-{slide_index + 1}: background hash mismatch")

            schema = [row for row in slide_spec.get("placeholder_schema", []) if isinstance(row, dict)]
            indices = placeholder_indices(schema)
            offset = offset_for(slide_spec)
            placeholder_report = []
            for row_index, row in enumerate(schema):
                name = str(row.get("id") or row.get("source_slot_id") or "")
                layout_row = layout["shapes"].get(name)
                slide_row = slide_shapes.get(name)
                expected_type = normalize_type(str(row.get("placeholder_type") or "body"))
                expected_index = indices[row_index]
                expected_geometry = expected_position(list(row["region"]), offset)
                if layout_row is None or slide_row is None:
                    errors.append(f"slide-{slide_index + 1}:{name}: missing Layout or Slide Placeholder")
                    continue
                for scope, actual in (("layout", layout_row), ("slide", slide_row)):
                    if actual["type"] != expected_type:
                        errors.append(f"slide-{slide_index + 1}:{name}:{scope} type={actual['type']} expected={expected_type}")
                    if actual["index"] != expected_index:
                        errors.append(f"slide-{slide_index + 1}:{name}:{scope} index={actual['index']} expected={expected_index}")
                layout_delta = max_delta_px(layout_row["position"], expected_geometry)
                slide_delta = max_delta_px(slide_row["position"], expected_geometry)
                if layout_delta is None or layout_delta > 1:
                    errors.append(f"slide-{slide_index + 1}:{name}: Layout geometry delta={layout_delta}")
                if slide_delta is None or slide_delta > 1:
                    errors.append(f"slide-{slide_index + 1}:{name}: Slide geometry delta={slide_delta}")
                placeholder_report.append({"id": name, "type": expected_type, "index": expected_index, "layout_delta_px": layout_delta, "slide_delta_px": slide_delta})

            surface_report = []
            for surface_index, surface in enumerate(slide_spec.get("surfaces") or []):
                surface_id = str(surface.get("id") or surface_index)
                name = f"surface-{surface_id}"
                actual = layout["shapes"].get(name)
                if actual is None:
                    errors.append(f"slide-{slide_index + 1}:{name}: missing Surface")
                    continue
                if str(surface.get("shape") or "roundRect") != "rect":
                    expected_geometry = expected_position(list(surface["region"]), offset)
                    short_side_px = min(expected_geometry["width"], expected_geometry["height"]) / EMU_PER_PX
                    radius_stage_px = float(surface.get("corner_radius_stage_px", 18))
                    expected_adjustment = round((radius_stage_px * (2 / 3)) / short_side_px * 100000)
                    if actual["adjustment"] is None or abs(actual["adjustment"] - expected_adjustment) > 2:
                        errors.append(f"slide-{slide_index + 1}:{name}: adjustment={actual['adjustment']} expected={expected_adjustment}")
                    surface_report.append({"id": name, "radius_pptx_px": radius_stage_px * (2 / 3), "actual_adjustment": actual["adjustment"], "expected_adjustment": expected_adjustment})

            composition_offset = slide_spec.get("composition_offset_percent") or {}
            if composition_offset.get("original_center_y") is not None and composition_offset.get("target_center_y") is not None:
                effective_center = float(composition_offset["original_center_y"]) + float(composition_offset.get("dy", 0))
                if abs(effective_center - float(composition_offset["target_center_y"])) > 1e-9:
                    errors.append(f"slide-{slide_index + 1}: effective center={effective_center} target={composition_offset['target_center_y']}")
            slide_reports.append({
                "slide": slide_index + 1,
                "slide_id": slide_spec.get("slide_id"),
                "layout": expected_layout_name,
                "composition_offset_percent": composition_offset or None,
                "background_role": role,
                "background_sha256": expected_background_hash,
                "placeholders": placeholder_report,
                "surfaces": surface_report,
            })

        if slide_image_relationships:
            errors.append(f"ordinary slide image relationships={slide_image_relationships}")

    powerpoint = optional_json(args.powerpoint_report)
    if powerpoint and (powerpoint.get("failures") != 0 or int(powerpoint.get("rendered", 0)) != len(selection.get("slides", []))):
        errors.append("PowerPoint native render failed")
    reset = optional_json(args.reset_report)
    if reset and reset.get("status") != "pass":
        errors.append("PowerPoint Reset geometry failed")
    slides_test = Path(args.slides_test_report).read_text(encoding="utf-8-sig").strip() if args.slides_test_report else None
    if slides_test is not None and "Test passed. No overflow detected." not in slides_test:
        errors.append("slides_test failed")

    relative_artifact = Path(posixpath.join(*pptx_path.relative_to(project_root).parts)).as_posix()
    relative_selection = Path(posixpath.join(*selection_path.relative_to(project_root).parts)).as_posix()
    report = {
        "schema_version": 1,
        "kind": "pptx_positioning_contract_qa",
        "status": "pass" if not errors else "fail",
        "artifact": relative_artifact,
        "selection_manifest": relative_selection,
        "checks": {
            "slide_local_explicit_geometry": "pass" if not any("Slide geometry" in item for item in errors) else "fail",
            "layout_slide_placeholder_identity": "pass" if not any("Placeholder" in item or " type=" in item or " index=" in item for item in errors) else "fail",
            "composition_offset_applied_once": "pass" if not any("effective center" in item for item in errors) else "fail",
            "backgrounds_on_custom_layouts_only": "pass" if not any("background hash" in item or "ordinary slide image" in item for item in errors) else "fail",
            "round_rect_absolute_radius": "pass" if not any("adjustment=" in item for item in errors) else "fail",
            "powerpoint_native_render": "pass" if powerpoint and not any("PowerPoint native render" in item for item in errors) else ("not-run" if not powerpoint else "fail"),
            "powerpoint_reset": "pass" if reset and not any("Reset geometry" in item for item in errors) else ("not-run" if not reset else "fail"),
            "slides_test": "pass" if slides_test and not any("slides_test" in item for item in errors) else ("not-run" if not slides_test else "fail"),
        },
        "slides": slide_reports,
        "errors": errors,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": len(errors), "slides": len(slide_reports)}, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
