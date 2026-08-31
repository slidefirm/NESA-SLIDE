#!/usr/bin/env python3
"""Run the formal nine-question HTML deck design review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from html_design_method import load_html_design_method


def review_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    method = load_html_design_method()
    decisions = manifest.get("layout_decisions") or []
    architecture = manifest.get("architecture") or []
    intensities = [row.get("visual_intensity") for row in decisions if row.get("visual_intensity")]

    repeated_runs: list[dict[str, Any]] = []
    for index in range(max(0, len(architecture) - 2)):
        window = architecture[index:index + 3]
        if len(set(window)) == 1:
            repeated_runs.append({"slides": [index + 1, index + 2, index + 3], "family": window[0]})

    triplets = [
        (row.get("composition_variant"), row.get("header_mode"), row.get("surface_mode"))
        for row in decisions
    ]
    missing_variant_metadata = [index + 1 for index, triplet in enumerate(triplets) if not all(triplet)]
    repeated_triplets = [
        {"slides": [index, index + 1], "triplet": triplets[index - 1]}
        for index in range(1, len(triplets))
        if triplets[index - 1] == triplets[index]
    ]
    header_modes = sorted({row.get("header_mode") for row in decisions if row.get("header_mode")})
    surface_modes = sorted({row.get("surface_mode") for row in decisions if row.get("surface_mode")})
    variety_shortfall = {
        "header_modes": header_modes,
        "surface_modes": surface_modes,
        "required_each": 3,
    } if len(decisions) >= 3 and (len(header_modes) < 3 or len(surface_modes) < 3) else None
    skeleton_issues = {
        "repeated_family_runs": repeated_runs,
        "repeated_triplets": repeated_triplets,
        "missing_variant_metadata": missing_variant_metadata,
        "variety_shortfall": variety_shortfall,
    }
    skeleton_ok = not any((repeated_runs, repeated_triplets, missing_variant_metadata, variety_shortfall))

    route_mismatches = [
        {"slide": index + 1, "intent": row.get("intent"), "layout_id": row.get("layout_id")}
        for index, row in enumerate(decisions)
        if not row.get("route_match", False) and row.get("source") != "forced-layout"
    ]
    forced_overrides = [
        {"slide": index + 1, "intent": row.get("intent"), "layout_id": row.get("layout_id")}
        for index, row in enumerate(decisions)
        if not row.get("route_match", False) and row.get("source") == "forced-layout"
    ]
    rhythm_ok = len(decisions) < 4 or len(set(intensities)) >= 3
    checks = [
        {
            "id": "repeated-skeleton",
            "status": "pass" if skeleton_ok else "fix",
            "evidence": (
                {
                    "header_modes": header_modes,
                    "surface_modes": surface_modes,
                    "composition_variants": [row.get("composition_variant") for row in decisions],
                }
                if skeleton_ok
                else skeleton_issues
            ),
        },
        {
            "id": "page-rhythm",
            "status": "pass" if rhythm_ok else "fix",
            "evidence": {"visual_intensity_sequence": intensities},
        },
        {
            "id": "signature-fit",
            "status": "fix" if route_mismatches else ("manual-review" if forced_overrides else "pass"),
            "evidence": route_mismatches or forced_overrides or "所有自動選擇的 Layout 都符合內容關係。",
        },
        {
            "id": "type-capacity-fit",
            "status": "manual-review",
            "evidence": "Layout 選定後，以正式字體截圖確認 composition 保留 primary items、達 36px 下限且無 overflow。",
        },
        {
            "id": "unintended-collision",
            "status": "manual-review",
            "evidence": "以瀏覽器幾何檢查與全頁截圖確認重疊、裁切與 overflow。",
        },
        {
            "id": "layout-only-edit-hit",
            "status": "manual-review",
            "evidence": "需要以瀏覽器互動 QA 確認 Content Area 與 layout slot 不會成為編輯選取物件。",
        },
        {
            "id": "nested-group-preservation",
            "status": "manual-review",
            "evidence": "需要以瀏覽器互動 QA 確認解除外層群組後仍保留語意小群組。",
        },
        {
            "id": "body-field-balance",
            "status": "manual-review",
            "evidence": "需要以瀏覽器幾何 QA 確認無 counterweight 的多模組頁使用至少 68% 可見寬度。",
        },
        {
            "id": "palette-jarring",
            "status": "manual-review",
            "evidence": "配色是否突兀必須以投影截圖人工判斷，不用假分數取代。",
        },
    ]
    blocking = [row for row in checks if row["status"] == "fix"]
    return {
        "id": method["id"],
        "format": method["deck_review"]["format"],
        "status": "pass" if not blocking else "fix",
        "keep": [row["id"] for row in checks if row["status"] == "pass"],
        "fix": [row["id"] for row in blocking],
        "quick_win": "先修正 fix；再用投影截圖確認配色是否突兀。",
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = review_manifest(manifest)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
