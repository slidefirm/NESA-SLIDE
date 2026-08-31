from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = ROOT / "artifacts" / "deploy"
GALLERY_PATH = DEPLOY_DIR / "layout-gallery.js"
LAYOUTS_DIR = ROOT / "prompt_system" / "layouts"
PREFIX = "window.LAYOUT_GALLERY = "
GALLERY_CATEGORY_ORDER = ["封面", "目錄", "內容", "圖表", "資訊圖像", "特定版面"]
GALLERY_CONTENT_IDS = {
    "cards-1-plus-2", "cards-1-plus-3", "cards-1-plus-4",
    "cards-1-plus-5", "cards-1-plus-6", "cards-1-plus-8",
}
GALLERY_CHART_IDS = {
    "comparison-table", "data-annotation", "heat-map", "multi-line-chart", "radar-chart",
}
GALLERY_INFOGRAPHIC_IDS = {
    "cycle-hub-6", "flow-stages-3", "funnel-4", "gantt-roadmap", "infographic-stage",
    "map-region", "map-spotlight", "matrix-4quadrant", "org-chart", "process-flow",
    "pyramid", "timeline-milestones", "timeline-vertical",
}
EXCLUDED_IDS = {
    "infographic-stage",
    "toc-2",
    "toc-2-image-left",
    "toc-2-panel-rows",
    "toc-2-vertical",
}
SLIDE_ROLE_ORDER = ["封面", "目錄", "章節頁", "內容頁", "結尾頁"]
TITLE_RELATION_ORDER = [
    "上標｜下內容",
    "左標｜右內容",
    "右標｜左內容",
    "標題置中",
    "標題疊合",
]
CONTENT_FLOW_ORDER = [
    "單一主體",
    "左右分區",
    "橫向排列",
    "直向排列",
    "網格排列",
    "流程路徑",
    "階層／環形",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_gallery() -> dict:
    text = GALLERY_PATH.read_text(encoding="utf-8").strip()
    if not text.startswith(PREFIX) or not text.endswith(";"):
        raise ValueError(f"Unexpected Gallery payload wrapper: {GALLERY_PATH}")
    return json.loads(text[len(PREFIX) : -1])


def slide_role_for(item: dict) -> str:
    if item.get("slide_role"):
        return str(item["slide_role"])
    category = str(item.get("category", ""))
    if category in {"封面", "目錄", "章節頁"}:
        return category
    if category == "結尾 / CTA":
        return "結尾頁"
    return "內容頁"


def gallery_category_for(item: dict) -> str:
    if item.get("gallery_category"):
        return str(item["gallery_category"])
    layout_id = str(item.get("id", ""))
    category = str(item.get("category", ""))
    if category in {"封面", "目錄"}:
        return category
    if layout_id in GALLERY_CONTENT_IDS:
        return "內容"
    if layout_id in GALLERY_CHART_IDS:
        return "圖表"
    if layout_id in GALLERY_INFOGRAPHIC_IDS:
        return "資訊圖像"
    return "特定版面"


def main() -> int:
    payload = load_gallery()
    expected_ids = {
        path.stem for path in LAYOUTS_DIR.glob("*.yaml") if path.stem not in EXCLUDED_IDS
    }
    layouts = payload.get("layouts") or []
    actual_ids = {str(item.get("id", "")) for item in layouts}
    errors: list[str] = []

    if payload.get("count") != len(layouts):
        errors.append(f"payload count {payload.get('count')} != layout rows {len(layouts)}")
    if actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        if missing:
            errors.append(f"missing Layouts: {', '.join(missing)}")
        if extra:
            errors.append(f"unexpected Layouts: {', '.join(extra)}")

    actual_slide_roles = payload.get("slide_roles") or [
        value for value in SLIDE_ROLE_ORDER if any(slide_role_for(item) == value for item in layouts)
    ]
    expected_slide_roles = [
        value
        for value in SLIDE_ROLE_ORDER
        if any(slide_role_for(item) == value for item in layouts)
    ]
    if actual_slide_roles != expected_slide_roles:
        errors.append(f"slide_roles {actual_slide_roles!r} != expected {expected_slide_roles!r}")

    actual_gallery_categories = payload.get("gallery_categories") or [
        value
        for value in GALLERY_CATEGORY_ORDER
        if any(gallery_category_for(item) == value for item in layouts)
    ]
    expected_gallery_categories = [
        value
        for value in GALLERY_CATEGORY_ORDER
        if any(gallery_category_for(item) == value for item in layouts)
    ]
    if actual_gallery_categories != expected_gallery_categories:
        errors.append(
            f"gallery_categories {actual_gallery_categories!r} != expected {expected_gallery_categories!r}"
        )

    actual_title_relations = payload.get("title_relations") or []
    expected_title_relations = [
        value
        for value in TITLE_RELATION_ORDER
        if any(item.get("title_relation") == value for item in layouts)
    ]
    if actual_title_relations != expected_title_relations:
        errors.append(
            f"title_relations {actual_title_relations!r} != expected {expected_title_relations!r}"
        )

    actual_content_flows = payload.get("content_flows") or []
    expected_content_flows = [
        value
        for value in CONTENT_FLOW_ORDER
        if any(item.get("content_flow") == value for item in layouts)
    ]
    if actual_content_flows != expected_content_flows:
        errors.append(f"content_flows {actual_content_flows!r} != expected {expected_content_flows!r}")

    for item in layouts:
        layout_id = str(item.get("id", "<missing-id>"))
        missing_taxonomy = [
            key
            for key in [
                "category",
                "subgroup",
                "structure",
                "position_family",
                "composition",
                "title_relation",
                "content_flow",
            ]
            if not str(item.get(key, "")).strip()
        ]
        if missing_taxonomy:
            errors.append(f"{layout_id}: missing taxonomy fields: {', '.join(missing_taxonomy)}")
        if slide_role_for(item) not in SLIDE_ROLE_ORDER:
            errors.append(f"{layout_id}: invalid slide_role {slide_role_for(item)!r}")
        if gallery_category_for(item) not in GALLERY_CATEGORY_ORDER:
            errors.append(
                f"{layout_id}: invalid gallery_category {gallery_category_for(item)!r}"
            )

        variants = item.get("preview_variants") or []
        if len(variants) != 3:
            errors.append(f"{layout_id}: expected 3 cases, found {len(variants)}")
            continue

        sources = [str(variant.get("src", "")) for variant in variants]
        if len(set(sources)) != 3:
            errors.append(f"{layout_id}: duplicate case paths")
            continue
        if any(not source or source.lower().endswith(".svg") for source in sources):
            errors.append(f"{layout_id}: case must be a rendered visual, not SVG or empty")
            continue

        paths = [DEPLOY_DIR / source for source in sources]
        missing_paths = [path for path in paths if not path.is_file()]
        if missing_paths:
            errors.append(f"{layout_id}: missing files: {', '.join(path.as_posix() for path in missing_paths)}")
            continue
        if len({sha256_file(path) for path in paths}) != 3:
            errors.append(f"{layout_id}: duplicate visual content")

    by_id = {str(item.get("id", "")): item for item in layouts}
    for layout_id in ["heat-map", "map-region", "map-spotlight", "org-chart"]:
        item = by_id.get(layout_id)
        if not item:
            errors.append(f"{layout_id}: missing from gallery")
        elif item.get("category") != "圖表類型":
            errors.append(f"{layout_id}: expected 圖表類型, found {item.get('category')!r}")

    if errors:
        print("Gallery triptych verification: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Gallery triptych verification: PASS ({len(layouts)} layouts x 3 distinct visual cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
