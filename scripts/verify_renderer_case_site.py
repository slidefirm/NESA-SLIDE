#!/usr/bin/env python3
"""Verify the renderer case build, HTML edit contract, and PPTX structure."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "prompt_system" / "demos" / "renderer-case-catalog.json"
OUTPUT = ROOT / "artifacts" / "renderer-cases-deploy"
MAIN_INDEX = ROOT / "artifacts" / "deploy" / "index.html"
MAIN_MANIFEST = ROOT / "artifacts" / "deploy" / "renderer-cases.js"
REPORT = ROOT / "artifacts" / "qa" / "renderer-case-site-report.json"
PAGES_FILE_LIMIT = 25 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_main_manifest() -> dict:
    text = MAIN_MANIFEST.read_text(encoding="utf-8")
    prefix = "window.RENDERER_CASES = "
    if not text.startswith(prefix) or not text.rstrip().endswith(";"):
        raise ValueError("Invalid main renderer-cases.js wrapper")
    return json.loads(text[len(prefix) :].rstrip()[:-1])


def pptx_audit(path: Path, hybrid: bool) -> dict:
    with ZipFile(path) as archive:
        names = archive.namelist()
        slide_names = sorted(name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name))
        layout_names = sorted(name for name in names if re.fullmatch(r"ppt/slideLayouts/slideLayout\d+\.xml", name))
        master_names = sorted(name for name in names if re.fullmatch(r"ppt/slideMasters/slideMaster\d+\.xml", name))

        slide_xml = "\n".join(archive.read(name).decode("utf-8", errors="replace") for name in slide_names)
        layout_xml = "\n".join(archive.read(name).decode("utf-8", errors="replace") for name in layout_names)

        layout_rel_names = [name for name in names if re.fullmatch(r"ppt/slideLayouts/_rels/slideLayout\d+\.xml\.rels", name)]
        slide_rel_names = [name for name in names if re.fullmatch(r"ppt/slides/_rels/slide\d+\.xml\.rels", name)]
        layout_image_relations = sum(
            archive.read(name).decode("utf-8", errors="replace").count("/image") for name in layout_rel_names
        )
        slide_image_relations = sum(
            archive.read(name).decode("utf-8", errors="replace").count("/image") for name in slide_rel_names
        )

    result = {
        "slides": len(slide_names),
        "layouts": len(layout_names),
        "masters": len(master_names),
        "slide_text_runs": slide_xml.count("<a:t"),
        "layout_placeholders": layout_xml.count("<p:ph"),
        "layout_image_relations": layout_image_relations,
        "slide_image_relations": slide_image_relations,
    }
    result["pass"] = (
        result["slides"] > 0
        and result["layouts"] > 0
        and result["masters"] > 0
        and result["slide_text_runs"] > 0
    )
    if hybrid:
        result["pass"] = (
            result["pass"]
            and result["layout_placeholders"] > 0
            and result["layout_image_relations"] >= result["slides"]
            and result["slide_image_relations"] == 0
        )
    return result


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    built_manifest = json.loads((OUTPUT / "manifest.json").read_text(encoding="utf-8"))
    main_manifest = read_main_manifest()
    failures: list[str] = []
    cases_report: list[dict] = []

    if built_manifest != main_manifest:
        failures.append("main manifest differs from independent-site manifest")

    main_html = MAIN_INDEX.read_text(encoding="utf-8")
    # Renderer cases are linked contextually from each matching Layout card.
    # The older standalone `#cases` section was removed from the catalog UI.
    for marker in (
        'src="renderer-cases.js"',
        "rendererCaseCatalog",
        "getRendererCaseLinks",
        "renderLayoutCaseLinks",
    ):
        if marker not in main_html:
            failures.append(f"main index missing {marker}")

    built_by_id = {item["id"]: item for item in built_manifest["cases"]}
    for source_case in catalog["cases"]:
        case_id = source_case["id"]
        built_case = built_by_id.get(case_id)
        if not built_case:
            failures.append(f"missing built case {case_id}")
            continue

        case_report = {"id": case_id, "formats": {}, "pass": True}
        for format_id, source_format in source_case["formats"].items():
            source = ROOT / source_format["source"]
            deployed = OUTPUT / source_format["public_path"]
            format_report = {
                "source": source.relative_to(ROOT).as_posix(),
                "deployed": deployed.relative_to(ROOT).as_posix(),
                "bytes": deployed.stat().st_size if deployed.exists() else 0,
                "hash_match": source.exists() and deployed.exists() and sha256(source) == sha256(deployed),
                "within_pages_file_limit": deployed.exists() and deployed.stat().st_size < PAGES_FILE_LIMIT,
            }

            if format_id == "html" and deployed.exists():
                html = deployed.read_text(encoding="utf-8")
                layouts = re.findall(r'data-layout-id="([^"]+)"', html)
                required_markers = [
                    'id="canvasBox"',
                    'id="stage"',
                    'id="barInner"',
                    'id="hint"',
                    "window.EditMode",
                    "fonts.googleapis.com/css2",
                    "new URLSearchParams(location.search).get('slide')",
                ]
                format_report.update(
                    {
                        "slides": len(layouts),
                        "layout_ids_match": layouts == source_case.get("layout_ids", []),
                        "edit_framework": all(marker in html for marker in required_markers),
                        "edit_mode_companion": (deployed.parent / "edit-mode.js").is_file(),
                    }
                )
                format_report["pass"] = all(
                    [
                        format_report["hash_match"],
                        format_report["within_pages_file_limit"],
                        format_report["layout_ids_match"],
                        format_report["edit_framework"],
                        format_report["edit_mode_companion"],
                    ]
                )
            elif format_id == "pptx" and deployed.exists():
                format_report.update(pptx_audit(deployed, hybrid=case_id.endswith("hybrid-master")))
                format_report["pass"] = all(
                    [
                        format_report["pass"],
                        format_report["hash_match"],
                        format_report["within_pages_file_limit"],
                        format_report["slides"] == source_case["slide_count"],
                    ]
                )
            else:
                format_report["pass"] = False

            if not format_report["pass"]:
                failures.append(f"{case_id}.{format_id} failed")
                case_report["pass"] = False
            case_report["formats"][format_id] = format_report

        cases_report.append(case_report)

    report = {
        "cases": len(cases_report),
        "formats": sum(len(item["formats"]) for item in cases_report),
        "total_asset_bytes": built_manifest["total_asset_bytes"],
        "main_manifest_bytes": MAIN_MANIFEST.stat().st_size,
        "failures": failures,
        "results": cases_report,
        "pass": not failures and all(item["pass"] for item in cases_report),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
