from __future__ import annotations

import html
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAYOUTS_DIR = ROOT / "prompt_system" / "layouts"
OUT_DIR = ROOT / "artifacts" / "deploy" / "layout-previews"
VARIANTS_DIR = ROOT / "artifacts" / "deploy" / "layout-variants"
JS_OUT = ROOT / "artifacts" / "deploy" / "layout-gallery.js"
QA_LOG = ROOT / "artifacts" / "qa" / "layout-preview-qa.jsonl"
STYLE_CASES_DIR = ROOT / "prompt_system" / "style_cases"
STYLE_CASE_PREVIEWS_DIR = ROOT / "artifacts" / "deploy" / "layout-style-cases"

EXTRA_VARIANT_FILES = {
    "cover-upper-center-stack-meta-lower-right": "cover-upper-center-stack-meta-lower-right-variant-v3-b.webp",
    "pricing-3col": "pricing-3col-variant-codex-20260722.webp",
    "stats-3-row": "stats-3-row-variant-codex-20260722.webp",
    "testimonial-full": "testimonial-full-variant-b-codex-20260722.webp",
    "toc-5": "toc-5-variant-codex-20260722.webp",
    "toc-5-number-panel-left": "toc-5-number-panel-left-variant-codex-20260722.webp",
}

VW = 480
VH = 270


# Retired Layouts stay on disk only for historical artifact compatibility.
# Pending Layouts remain outside the public Gallery until the triptych gate passes.
EXCLUDED_IDS = {
    "infographic-stage",
    "toc-2",
    "toc-2-image-left",
    "toc-2-panel-rows",
    "toc-2-vertical",
}

# SVG files in this set are hand-crafted; skip auto-generation if the file already exists.
CUSTOM_SVG_IDS = {
    "cover-photo-frame", "cover-photo-frame-reverse",
    "cover-center-title-edge-decor",
    "cover-photo-overlay-block",
    "hero-fullbleed", "hero-fullbleed-brand-footer",
    "chapter-number-bg-left-title-rule",
    "chapter-text-left-photo-brand",
    "chapter-fullbleed-overlay-title",
    "photo-left-overlay-title-right",
    "closing-photo-overlay-contact",
    "cycle-hub-6",
    "toc-3-vertical", "toc-4-vertical", "toc-5-vertical", "toc-6-vertical",
    "toc-4-image-left",
    "cards-1-plus-8",
}

TITLE_OVERRIDES = {}  # YAML display_name is canonical source (cleared 2026-06-24)


# Gallery navigation starts with the semantic slide role, then uses two visual
# axes for refinement:
# 1. slide_role: what the slide does in the deck;
# 2. title_relation: where the title sits relative to the content region;
# 3. content_flow: how the content region is arranged.
#
# The older category/position_family/structure fields remain in the payload for
# compatibility and card details. In particular, "1 + N" is capacity metadata,
# not a Gallery directory level. Semantic types such as maps, timelines and org
# charts remain searchable metadata instead of becoming navigation folders.
CHART_TYPES: dict[str, tuple[str, str]] = {
    "before-after": ("比較 / 決策", "前後對比圖"),
    "comparison-table": ("比較 / 決策", "比較表"),
    "cycle-hub-6": ("結構 / 關係", "環形關係圖"),
    "dashboard-overview": ("數據圖表", "儀表板"),
    "data-annotation": ("數據圖表", "事件標注趨勢圖"),
    "flow-stages-3": ("流程 / 時間", "階段流程圖"),
    "funnel-4": ("流程 / 時間", "漏斗圖"),
    "gantt-roadmap": ("流程 / 時間", "甘特圖"),
    "heat-map": ("數據圖表", "熱力矩陣"),
    "highlight-callout": ("數據圖表", "主圖標注"),
    "kpi-scorecards": ("數據圖表", "KPI 計分卡"),
    "map-region": ("地圖", "區域著色地圖"),
    "map-spotlight": ("地圖", "據點標注地圖"),
    "matrix-4quadrant": ("比較 / 決策", "四象限矩陣"),
    "multi-line-chart": ("數據圖表", "多線折線圖"),
    "org-chart": ("結構 / 關係", "組織架構圖"),
    "pricing-3col": ("比較 / 決策", "方案比較"),
    "process-flow": ("流程 / 時間", "線性流程圖"),
    "pyramid": ("結構 / 關係", "金字塔圖"),
    "radar-chart": ("數據圖表", "雷達圖"),
    "recommendation-stack": ("比較 / 決策", "建議優先序"),
    "split-comparison": ("比較 / 決策", "左右對比"),
    "stats-3-row": ("數據圖表", "大數字指標"),
    "strategic-priorities": ("比較 / 決策", "策略優先序"),
    "swot-quadrant": ("比較 / 決策", "SWOT 矩陣"),
    "timeline-milestones": ("流程 / 時間", "橫向時間軸"),
    "timeline-vertical": ("流程 / 時間", "縱向時間軸"),
}

CONTENT_PARTITION_IDS = {
    "cards-1-plus-2",
    "cards-1-plus-3",
    "cards-1-plus-4",
    "cards-1-plus-5",
    "cards-1-plus-6",
    "cards-1-plus-8",
    "icon-grid-6",
}

FOCUS_LAYOUT_IDS = {
    "quote-attribution-3",
    "quote-focus",
    "testimonial-full",
    "title-center",
}

VISUAL_PEOPLE_IDS = {
    "executive-bio",
    "people-3",
    "photo-left-overlay-title-right",
    "team-grid",
}

STRUCTURE_OVERRIDES = {
    "before-after": "2-way split",
    "comparison-table": "1 + 1",
    "cover-upper-center-stack-meta-lower-right": "1 + 2",
    "dashboard-overview": "1 + 3",
    "data-annotation": "1 + 1",
    "funnel-4": "1 + 4",
    "heat-map": "1 + 1",
    "highlight-callout": "1 + 4",
    "icon-grid-6": "1 + 6",
    "map-region": "1 + 4",
    "map-spotlight": "1 + 4",
    "matrix-4quadrant": "1 + 4",
    "multi-line-chart": "1 + 1",
    "org-chart": "1 + hierarchy",
    "people-3": "1 + 3",
    "pricing-3col": "1 + 3",
    "quote-attribution-3": "1 + 3",
    "radar-chart": "1 + 2",
    "stats-3-row": "1 + 3",
    "swot-quadrant": "1 + 4",
    "team-grid": "1 + 6",
    "testimonial-full": "1 + 1",
}

POSITION_FAMILY_OVERRIDES = {
    "before-after": "左右對分",
    "chapter-fullbleed-overlay-title": "滿版內容｜標題疊合",
    "chapter-number-bg-left-title-rule": "左內容｜右視覺",
    "chapter-opener": "置中焦點",
    "chapter-text-left-photo-brand": "左內容｜右視覺",
    "closing-photo-overlay-contact": "滿版內容｜標題疊合",
    "cover-center-title-double-frame": "置中焦點｜雙線外框",
    "cover-center-title-edge-decor": "置中焦點",
    "cover-photo-frame": "左視覺｜右內容",
    "cover-photo-frame-reverse": "左內容｜右視覺",
    "cover-photo-overlay-block": "滿版內容｜標題疊合",
    "cover-upper-center-stack-meta-lower-right": "上方置中｜右下資訊",
    "cycle-hub-6": "中央主題｜兩側內容",
    "executive-bio": "左視覺｜右內容",
    "hero-fullbleed": "滿版內容｜標題疊合",
    "hero-fullbleed-brand-footer": "滿版內容｜標題疊合",
    "photo-left-overlay-title-right": "左視覺｜右內容",
    "quote-focus": "置中焦點",
    "title-center": "置中焦點",
}

COMPOSITION_OVERRIDES = {
    "before-after": "左 before｜右 after",
    "cards-1-plus-2": "上 1｜下 2 橫排",
    "cards-1-plus-3": "上 1｜下 3 橫排",
    "cards-1-plus-4": "上 1｜下 2×2",
    "cards-1-plus-5": "上 1｜下 3+2",
    "cards-1-plus-6": "上 1｜下 3×2",
    "cards-1-plus-8": "上 1｜下 4×2",
    "chapter-fullbleed-overlay-title": "滿版照片｜左上標題＋右側章節號",
    "chapter-number-bg-left-title-rule": "左主標｜右側大型章節號",
    "chapter-opener": "中央章節標記｜置中主標",
    "chapter-text-left-photo-brand": "左標題與內文｜右滿版照片",
    "closing-photo-overlay-contact": "滿版照片｜左側結尾與聯絡資訊",
    "comparison-table": "上標題｜下比較表",
    "cover-center-title-double-frame": "置中主標｜雙線外框",
    "cover-center-title-edge-decor": "置中主標｜下副標與署名",
    "cover-photo-frame": "左照片｜右主標與署名",
    "cover-photo-frame-reverse": "左主標與署名｜右照片",
    "cover-photo-overlay-block": "滿版照片｜左側色塊標題",
    "cover-upper-center-stack-meta-lower-right": "上方主副標｜左下焦點＋右下資訊",
    "cycle-hub-6": "中央 1｜左右各 3",
    "dashboard-overview": "上標題｜下 KPI、主圖與洞察",
    "data-annotation": "上標題｜下趨勢圖＋事件標注",
    "executive-bio": "左照片｜右姓名、職稱與簡介",
    "flow-stages-3": "上 1｜下 3 階段",
    "funnel-4": "上 1｜下 4 層漏斗",
    "gantt-roadmap": "上標題｜下任務欄＋時間帶",
    "heat-map": "上標題｜下熱力矩陣",
    "hero-fullbleed": "滿版照片｜左下主標",
    "hero-fullbleed-brand-footer": "滿版照片｜左側主標＋品牌底欄",
    "highlight-callout": "上標題｜左主圖＋右 3 重點",
    "icon-grid-6": "上 1｜下 3×2",
    "kpi-scorecards": "上標題｜下 4 指標",
    "map-region": "上標題｜左地圖＋右 3 數據",
    "map-spotlight": "上標題｜左地圖＋右 3 據點",
    "matrix-4quadrant": "上標題｜下 2×2 象限",
    "multi-line-chart": "上標題｜下多線趨勢圖",
    "org-chart": "上標題｜下 1→3 階層",
    "people-3": "上 1｜下 3 人並列",
    "photo-left-overlay-title-right": "左照片｜右疊合標題與內文",
    "pricing-3col": "上標題｜下 3 方案",
    "process-flow": "上標題｜下橫向步驟",
    "pyramid": "上標題｜下 3–5 層金字塔",
    "quote-attribution-3": "上 1｜下 3 則引言",
    "quote-focus": "置中引言｜下方署名",
    "radar-chart": "上標題｜左雷達圖＋右圖例",
    "recommendation-stack": "上標題｜下建議堆疊",
    "split-comparison": "上標題｜下左右對分",
    "stats-3-row": "上說明｜下 3 指標",
    "strategic-priorities": "上標題｜下策略優先序",
    "swot-quadrant": "上標題｜下 2×2 SWOT",
    "team-grid": "上 1｜下 3×2 人物",
    "testimonial-full": "上引言｜下人物與署名",
    "timeline-milestones": "上標題｜下橫向里程碑",
    "timeline-vertical": "上標題｜下 4–5 段縱向時間軸",
    "title-center": "置中主標｜下輔助文字",
}


TITLE_RELATION_ORDER = (
    "上標｜下內容",
    "左標｜右內容",
    "右標｜左內容",
    "標題置中",
    "標題疊合",
)

SLIDE_ROLE_ORDER = (
    "封面",
    "目錄",
    "章節頁",
    "內容頁",
    "結尾頁",
)

GALLERY_CATEGORY_ORDER = (
    "封面",
    "目錄",
    "內容",
    "圖表",
    "資訊圖像",
    "特定版面",
)

GALLERY_CONTENT_IDS = {
    "cards-1-plus-2",
    "cards-1-plus-3",
    "cards-1-plus-4",
    "cards-1-plus-5",
    "cards-1-plus-6",
    "cards-1-plus-8",
}

GALLERY_CHART_IDS = {
    "comparison-table",
    "data-annotation",
    "heat-map",
    "multi-line-chart",
    "radar-chart",
}

GALLERY_INFOGRAPHIC_IDS = {
    "cycle-hub-6",
    "flow-stages-3",
    "funnel-4",
    "gantt-roadmap",
    "infographic-stage",
    "map-region",
    "map-spotlight",
    "matrix-4quadrant",
    "org-chart",
    "process-flow",
    "pyramid",
    "timeline-milestones",
    "timeline-vertical",
}

CONTENT_FLOW_ORDER = (
    "單一主體",
    "左右分區",
    "橫向排列",
    "直向排列",
    "網格排列",
    "流程路徑",
    "階層／環形",
)

CENTERED_TITLE_IDS = {
    "chapter-opener",
    "cover-center-title-double-frame",
    "cover-center-title-edge-decor",
    "cover-upper-center-stack-meta-lower-right",
    "quote-focus",
    "title-center",
}

RIGHT_TITLE_POSITION_FAMILIES = {
    "左視覺｜右內容",
    "右上主標｜左側分離支援",
    "左側文字軌｜右下主標",
}

SIDE_BY_SIDE_CONTENT_IDS = {
    "before-after",
    "chapter-number-bg-left-title-rule",
    "chapter-text-left-photo-brand",
    "cover-photo-frame",
    "cover-photo-frame-reverse",
    "cover-upper-center-stack-meta-lower-right",
    "executive-bio",
    "highlight-callout",
    "map-region",
    "map-spotlight",
    "photo-left-overlay-title-right",
    "radar-chart",
    "split-comparison",
    "toc-4-image-left",
}

FLOW_PATH_CONTENT_IDS = {
    "flow-stages-3",
    "funnel-4",
    "gantt-roadmap",
    "process-flow",
    "timeline-milestones",
    "timeline-vertical",
}

RELATION_CONTENT_IDS = {
    "cycle-hub-6",
    "org-chart",
    "pyramid",
}

VERTICAL_CONTENT_IDS = {
    "recommendation-stack",
    "strategic-priorities",
    "testimonial-full",
}

GRID_CONTENT_IDS = {
    "comparison-table",
    "dashboard-overview",
    "heat-map",
    "icon-grid-6",
    "kpi-scorecards",
    "matrix-4quadrant",
    "swot-quadrant",
    "team-grid",
}

HORIZONTAL_CONTENT_IDS = {
    "cards-1-plus-2",
    "cards-1-plus-3",
    "people-3",
    "pricing-3col",
    "quote-attribution-3",
    "stats-3-row",
    "toc-3",
    "toc-3-panel-left",
}


def clean_value(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value


def parse_region(text: str) -> list[float]:
    text = text.split("#", 1)[0].strip()
    return [float(x.strip()) for x in text.split(",")]


def parse_layout(path: Path) -> dict:
    data = {
        "id": None,
        "display_name": None,
        "safe_area": [8, 8, 92, 92],
        "slots": [],
    }
    current_slot = None
    in_slots = False

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("id:") and data["id"] is None:
            data["id"] = clean_value(stripped.split(":", 1)[1])
            continue

        if stripped.startswith("display_name:") and data["display_name"] is None:
            data["display_name"] = clean_value(stripped.split(":", 1)[1])
            continue

        if stripped.startswith("safe_area:"):
            region_text = stripped.split("[", 1)[1].split("]", 1)[0]
            data["safe_area"] = parse_region(region_text)
            continue

        if stripped == "slots:":
            in_slots = True
            continue

        if in_slots and line and not line.startswith(" ") and re.match(r"^[A-Za-z_]", line):
            if current_slot:
                data["slots"].append(current_slot)
                current_slot = None
            in_slots = False

        if not in_slots:
            continue

        m_slot = re.match(r"^\s*-\s+id:\s*(.+)$", line)
        if m_slot:
            if current_slot:
                data["slots"].append(current_slot)
            current_slot = {"id": clean_value(m_slot.group(1)), "region": None, "note": ""}
            continue

        if current_slot is None:
            continue

        m_region = re.match(r"^\s+region:\s*\[(.+)\]\s*$", line)
        if m_region:
            current_slot["region"] = parse_region(m_region.group(1))
            continue

        m_note = re.match(r"^\s+note:\s*(.+)$", line)
        if m_note:
            current_slot["note"] = clean_value(m_note.group(1))
            continue

    if current_slot:
        data["slots"].append(current_slot)
    return data


def safe_display_name(value: str | None) -> str | None:
    if not value:
        return None
    if "?" in value or "�" in value:
        return None
    return value.strip()


def build_preview_variants(layout_id: str, codex_preview: str | None, preview_status: str) -> list[dict]:
    """Return exactly three visible cases while keeping QA state explicit."""
    legacy_paths = sorted(
        [
            *VARIANTS_DIR.glob(f"{layout_id}-legacy-*.webp"),
            *VARIANTS_DIR.glob(f"{layout_id}-legacy-*.svg"),
        ],
        reverse=True,
    )
    preferred_path = VARIANTS_DIR / EXTRA_VARIANT_FILES[layout_id] if layout_id in EXTRA_VARIANT_FILES else None
    candidate_paths = [preferred_path] if preferred_path and preferred_path.exists() else []
    candidate_paths.extend(path for path in legacy_paths if path != preferred_path)
    variants: list[dict] = []
    seen_hashes: set[str] = set()
    case_preview = codex_preview
    case_label = "正式預覽"
    case_kind = "current"

    if not case_preview:
        for extension in (".webp", ".png"):
            existing_path = OUT_DIR / f"{layout_id}-codex{extension}"
            if existing_path.is_file():
                case_preview = f"layout-previews/{existing_path.name}"
                case_label = {
                    "stale-qa": "既有案例 · QA 已失效",
                    "needs-review": "既有案例 · NEEDS REVIEW",
                    "missing-qa": "既有案例 · 尚無 QA",
                }.get(preview_status, "既有案例")
                case_kind = preview_status
                break

    if case_preview:
        variants.append({"src": case_preview, "label": case_label, "kind": case_kind})
        current_path = VARIANTS_DIR.parent / case_preview
        if current_path.is_file():
            seen_hashes.add(sha256_file(current_path))

    variant_labels = ["設計變體 A", "設計變體 B", "設計變體 C"]
    for variant_path in candidate_paths:
        if len(variants) >= 3:
            break
        variant_hash = sha256_file(variant_path)
        if variant_hash in seen_hashes:
            continue
        seen_hashes.add(variant_hash)
        variant_index = len(variants) - (1 if case_preview else 0)
        variants.append(
            {
                "src": f"layout-variants/{variant_path.name}",
                "label": variant_labels[variant_index],
                "kind": "variant",
            }
        )

    if len(variants) < 3:
        fallback_label = {
            "needs-review": "YAML 藍圖 · NEEDS REVIEW",
            "stale-qa": "YAML 藍圖 · QA 已失效",
            "missing-qa": "YAML 藍圖 · 尚無 QA",
        }.get(preview_status, "YAML 藍圖")
        variants.insert(
            0,
            {
                "src": f"layout-previews/{layout_id}.svg",
                "label": fallback_label,
                "kind": preview_status,
            },
        )

    if len(variants) != 3:
        raise RuntimeError(
            f"Layout {layout_id!r} requires exactly three previews; found {len(variants)}."
        )
    return variants


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else ROOT / path).resolve()


def load_latest_qa() -> dict[str, dict]:
    latest: dict[str, dict] = {}
    if not QA_LOG.exists():
        return latest
    for line_no, line in enumerate(QA_LOG.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at {QA_LOG}:{line_no}: {exc}") from exc
        layout_id = str(record.get("layout_id", "")).strip()
        if not layout_id:
            continue
        current = latest.get(layout_id)
        if current is None or str(record.get("timestamp", "")) >= str(current.get("timestamp", "")):
            latest[layout_id] = record
    return latest


def approved_codex_preview(layout_id: str, latest_qa: dict[str, dict]) -> tuple[str | None, str]:
    png_path = OUT_DIR / f"{layout_id}-codex.png"
    state = latest_qa.get(layout_id)
    if not state:
        return None, "missing-qa"
    if str(state.get("status", "")).strip() not in {"pass", "approved"}:
        return None, "needs-review"
    recorded_image = str(state.get("image", "")).strip()
    if not png_path.is_file() or not recorded_image or project_path(recorded_image) != png_path.resolve():
        return None, "stale-qa"
    recorded_hash = str(state.get("image_sha256", "")).strip()
    if recorded_hash and recorded_hash != sha256_file(png_path):
        return None, "stale-qa"
    layout_hash = str(state.get("layout_sha256", "")).strip()
    layout_path = LAYOUTS_DIR / f"{layout_id}.yaml"
    if layout_hash and layout_hash != sha256_file(layout_path):
        return None, "stale-qa"

    webp_path = OUT_DIR / f"{layout_id}-codex.webp"
    if webp_path.is_file():
        return f"layout-previews/{webp_path.name}", "approved"
    return f"layout-previews/{png_path.name}", "approved"


def fallback_title(layout_id: str) -> str:
    slug = layout_id.replace("-", " ")
    return " ".join(part.capitalize() for part in slug.split())


def infer_title(layout_id: str, display_name: str | None) -> str:
    return TITLE_OVERRIDES.get(layout_id) or safe_display_name(display_name) or fallback_title(layout_id)


def infer_category(layout_id: str, display_name: str | None = None) -> str:
    if any(key in layout_id for key in ["cover", "hero"]):
        return "封面"
    if "closing" in layout_id:
        return "結尾 / CTA"
    if "toc" in layout_id:
        return "目錄"
    if "chapter" in layout_id:
        return "章節頁"
    if layout_id in FOCUS_LAYOUT_IDS:
        return "引言 / 焦點句"
    if layout_id in VISUAL_PEOPLE_IDS:
        return "圖文 / 人物"
    if layout_id in CHART_TYPES:
        return "圖表類型"
    if layout_id in CONTENT_PARTITION_IDS:
        return "內容分區"

    # Future Layouts get a conservative semantic fallback from their canonical
    # display name. The curated IDs above remain the regression-checked source.
    title = (display_name or "").strip()
    if title.startswith(("圖表", "數據", "地圖", "矩陣", "組織架構圖", "時間軸", "流程", "比較")):
        return "圖表類型"
    if title.startswith(("人物", "圖文")):
        return "圖文 / 人物"
    return "內容分區"


def infer_slide_role(category: str) -> str:
    if category in {"封面", "目錄", "章節頁"}:
        return category
    if category == "結尾 / CTA":
        return "結尾頁"
    return "內容頁"


def infer_gallery_category(layout_id: str, category: str) -> str:
    if category in {"封面", "目錄"}:
        return category
    if layout_id in GALLERY_CONTENT_IDS:
        return "內容"
    if layout_id in GALLERY_CHART_IDS:
        return "圖表"
    if layout_id in GALLERY_INFOGRAPHIC_IDS:
        return "資訊圖像"
    return "特定版面"


def infer_structure(layout_id: str, category: str) -> str:
    if layout_id in STRUCTURE_OVERRIDES:
        return STRUCTURE_OVERRIDES[layout_id]
    if layout_id == "split-comparison":
        return "1 + 2"
    if any(key in layout_id for key in ["toc-2", "cards-1-plus-2"]):
        return "1 + 2"
    if any(key in layout_id for key in ["cards-1-plus-3", "flow-stages-3", "grid-cards", "toc-3"]):
        return "1 + 3"
    if any(key in layout_id for key in ["cards-1-plus-4", "kpi-scorecards", "toc-4"]):
        return "1 + 4"
    if any(key in layout_id for key in ["cards-1-plus-5", "toc-5"]):
        return "1 + 5"
    if any(key in layout_id for key in ["cards-1-plus-6", "toc-6"]) and "cycle" not in layout_id:
        return "1 + 6"
    if layout_id == "cycle-hub-6":
        return "1 + 6"
    if any(key in layout_id for key in ["cards-1-plus-8", "toc-8"]):
        return "1 + 8"
    if layout_id in {"gantt-roadmap", "process-flow", "timeline-milestones", "timeline-vertical"}:
        return "1 + sequence"
    if layout_id in {"recommendation-stack", "strategic-priorities"}:
        return "comparison"
    if any(key in layout_id for key in ["closing"]):
        return "1 + 1"
    if category in {"封面", "章節頁", "引言 / 焦點句", "圖文 / 人物"} and any(key in layout_id for key in ["cover", "hero", "chapter", "quote", "title-center", "photo-left"]):
        return "1 + 1"
    return "1 + N"


def infer_variant(layout_id: str, category: str) -> str:
    if layout_id == "pyramid":
        return "3–5 層階梯金字塔"
    explicit = {
        "hero-fullbleed": "滿版背景 + 左下文字",
        "hero-fullbleed-brand-footer": "滿版背景 + 左側文字欄",
        "cover-center-title-double-frame": "雙線外框 + 置中主標",
        "cover-center-title-edge-decor": "素色背景 + 置中標題",
        "cover-photo-overlay-block": "全幅照片 + 半透明色塊標題",
        "cover-photo-frame": "左圖右文",
        "cover-photo-frame-reverse": "左文右圖",
        "cover-upper-center-stack-meta-lower-right": "上方置中堆疊 + 大留白",
        "chapter-opener": "章節標記 + 大標題",
        "chapter-number-bg-left-title-rule": "背景章節數字 + 左側大標",
        "title-center": "置中大標",
        "quote-focus": "大字句焦點",
        "cards-1-plus-2": "左右雙模組",
        "cards-1-plus-3": "左中右三模組",
        "cards-1-plus-4": "2x2 模組網格",
        "cards-1-plus-5": "3 上 2 下",
        "cards-1-plus-6": "3x2 模組網格",
        "process-flow": "線性步驟",
        "flow-stages-3": "內容型階段卡",
        "timeline-milestones": "節點時間線",
        "dashboard-overview": "總覽儀表板",
        "kpi-scorecards": "指標卡片",
        "comparison-table": "表格式比較",
        "matrix-4quadrant": "四象限定位",
        "split-comparison": "左右分屏",
        "swot-quadrant": "4 格分類",
        "gantt-roadmap": "甘特時間帶",
        "cards-1-plus-8": "4×2 模組網格",
        "grid-cards": "多卡並列",
        "team-roster": "人物卡網格",
        "org-structure": "組織樹狀圖",
        "toc-3": "三欄章節卡",
        "toc-3-panel-left": "左側主文 + 三章節卡",
        "toc-3-panel-rows": "左側主文 + 三列橫排",
        "toc-4-panel-rows": "左側主文 + 四列橫排",
        "toc-5-panel-rows": "左側主文 + 五列橫排",
        "toc-6-panel-rows": "左側主文 + 六列橫排",
        "toc-4-panel-grid": "左側主文 + 2×2 格",
        "toc-5-panel-grid": "左側主文 + 3+2 格",
        "toc-4": "2×2 章節卡",
        "toc-5": "3+2 章節卡",
        "toc-6": "3×2 章節卡",
        "toc-8": "4×2 章節卡",
        "toc-3-vertical": "直向三行",
        "toc-4-vertical": "直向四行",
        "toc-5-vertical": "直向五行",
        "toc-6-vertical": "直向六行",
        "toc-4-image-left": "左插圖右 2×2",
        "toc-number-3": "大編號三欄",
        "toc-number-4": "大編號 2×2",
        "toc-number-5": "大編號 3+2",
        "toc-number-6": "大編號 3×2",
        "toc-5-number-panel-left": "左側數字欄 + 五列章節",
        "chapter-text-left-photo-brand": "文字左 + 照片右 + 品牌遮罩",
        "chapter-fullbleed-overlay-title": "滿版照片 + 遮罩標題 + 數字欄",
        "photo-left-overlay-title-right": "裱框照片左 + 遮罩標題右",
        "closing-photo-overlay-contact": "滿版照片 + 聯絡遮罩",
        "cycle-hub-6": "環形輪幅 + 中心主題",
    }
    if layout_id in explicit:
        return explicit[layout_id]
    if category == "圖表類型":
        return CHART_TYPES.get(layout_id, ("圖表", "圖表變體"))[1]
    if category == "內容分區":
        return "內容模組"
    if category == "圖文 / 人物":
        return "圖文人物混排"
    return "通用變體"


def infer_position_family(layout_id: str) -> str:
    if layout_id in POSITION_FAMILY_OVERRIDES:
        return POSITION_FAMILY_OVERRIDES[layout_id]
    if layout_id.startswith("toc-") and any(
        token in layout_id for token in ["panel-left", "panel-rows", "panel-grid", "number-panel-left"]
    ):
        return "左 1｜右 N"
    if layout_id.startswith("toc-") and "image-left" in layout_id:
        return "左視覺｜右內容"
    return "上 1｜下 N"


def infer_title_relation(layout_id: str, position_family: str) -> str:
    if position_family == "滿版內容｜標題疊合":
        return "標題疊合"
    if layout_id in CENTERED_TITLE_IDS:
        return "標題置中"
    if position_family in {"左 1｜右 N", "左內容｜右視覺"}:
        return "左標｜右內容"
    if position_family in RIGHT_TITLE_POSITION_FAMILIES:
        return "右標｜左內容"
    return "上標｜下內容"


def infer_content_flow(layout_id: str) -> str:
    if layout_id in RELATION_CONTENT_IDS:
        return "階層／環形"
    if layout_id in FLOW_PATH_CONTENT_IDS:
        return "流程路徑"
    if layout_id in SIDE_BY_SIDE_CONTENT_IDS:
        return "左右分區"
    if (
        layout_id in VERTICAL_CONTENT_IDS
        or "vertical" in layout_id
        or "panel-rows" in layout_id
        or "number-panel-left" in layout_id
    ):
        return "直向排列"
    if layout_id in GRID_CONTENT_IDS or "panel-grid" in layout_id:
        return "網格排列"

    cards_match = re.match(r"^cards-1-plus-(\d+)$", layout_id)
    if cards_match:
        return "橫向排列" if int(cards_match.group(1)) <= 3 else "網格排列"

    toc_match = re.match(r"^toc-(\d+)$", layout_id)
    if toc_match:
        return "橫向排列" if int(toc_match.group(1)) <= 3 else "網格排列"

    if layout_id in HORIZONTAL_CONTENT_IDS:
        return "橫向排列"
    return "單一主體"


def infer_composition(layout_id: str, position_family: str, variant: str) -> str:
    if layout_id in COMPOSITION_OVERRIDES:
        return COMPOSITION_OVERRIDES[layout_id]

    toc_match = re.match(r"^toc-(\d+)", layout_id)
    if toc_match:
        count = int(toc_match.group(1))
        if "number-panel-left" in layout_id:
            return f"左索引｜右 {count} 列"
        if "image-left" in layout_id:
            return f"左圖｜右標題＋{count} 格"
        if "panel-rows" in layout_id:
            return f"左 1｜右 {count} 列"
        if "panel-grid" in layout_id:
            grid = {4: "2×2", 5: "3+2"}.get(count, f"{count} 格")
            return f"左 1｜右 {grid}"
        if "panel-left" in layout_id:
            return f"左 1｜右 {count} 欄"
        if "vertical" in layout_id:
            return f"上 1｜下 {count} 直列"
        grid = {
            2: "2 欄",
            3: "3 欄",
            4: "2×2",
            5: "3+2",
            6: "3×2",
            8: "4×2",
        }.get(count, f"{count} 格")
        return f"上 1｜下 {grid}"

    return f"{position_family}（{variant}）"


def infer_subgroup(layout_id: str, category: str, position_family: str) -> str:
    if category == "圖表類型":
        return CHART_TYPES.get(layout_id, ("其他圖表", "圖表變體"))[0]
    return position_family


def infer_summary(
    layout_id: str,
    category: str,
    structure: str,
    variant: str,
    composition: str,
) -> str:
    if category == "封面":
        return "用來建立第一眼主題與氣氛，但主標仍應是主角。"
    if category == "目錄":
        return f"目錄用途；以「{composition}」建立章節層級與閱讀順序。"
    if category == "章節頁":
        return "用來切段、換氣與建立節奏。"
    if category == "引言 / 焦點句":
        return "用整頁呈現單一句子的重量，讓觀眾停下來感受一個主張或金句。"
    if category == "結尾 / CTA":
        return "用結尾主張與聯絡資訊收束內容，保持單一明確行動。"
    if category == "圖表類型":
        chart_type = CHART_TYPES.get(layout_id, ("其他圖表", variant))[1]
        return f"{chart_type}；構圖採「{composition}」，不再視為一般 1 + N 卡片。"
    if category == "圖文 / 人物":
        return f"用「{composition}」安排人物、照片與文字，讓主次關係一眼可讀。"
    if category == "內容分區":
        return f"{structure} 的「{composition}」變體；相同 N 值仍可延伸成上下、左右或不同網格。"
    return f"以「{composition}」呈現的通用 Layout。"


def pct(value: float, total: float) -> float:
    return value / 100 * total


def slot_kind(slot_id: str, note: str) -> str:
    token = f"{slot_id} {note}".lower()
    if any(k in token for k in ["footer", "meta", "bottom", "accent", "decoration", "side-mark"]):
        return "skip"
    if any(k in token for k in ["title", "headline", "quote"]):
        return "title"
    if any(k in token for k in ["subtitle", "intro", "supporting", "attribution", "takeaway", "note"]):
        return "text"
    if any(k in token for k in ["photo", "image", "gallery", "visual", "framed"]):
        return "visual"
    if any(k in token for k in ["kpi", "metric", "score", "stat", "number"]):
        return "metric"
    if any(k in token for k in ["dashboard", "chart"]):
        return "chart"
    if any(k in token for k in ["table"]):
        return "table"
    if any(k in token for k in ["matrix", "quadrant"]):
        return "matrix"
    if any(k in token for k in ["milestone", "timeline"]):
        return "timeline"
    if any(k in token for k in ["stage"]):
        return "stage-sequence"
    if any(k in token for k in ["process", "steps", "flow"]):
        return "flow"
    if any(k in token for k in ["module", "card", "grid", "item", "left_side", "right_side"]):
        return "module"
    return "module"


def draw_text_lines(x: float, y: float, w: float, h: float, strong: bool = False, count: int = 2) -> str:
    items: list[str] = []
    usable_w = w
    start_y = y + h * 0.22
    gap = h * 0.24
    for i in range(count):
        ratio = 0.88 if i == 0 else (0.72 if i == count - 1 else 0.8)
        line_w = usable_w * ratio
        line_h = 6 if strong and i == 0 else 4
        items.append(
            f'<rect x="{x:.1f}" y="{start_y + gap * i:.1f}" width="{line_w:.1f}" height="{line_h:.1f}" fill="#D3D8DF" rx="3"/>'
        )
    return "".join(items)


def draw_box(x: float, y: float, w: float, h: float, fill: str = "#F8FAFC", stroke: str = "#D7DDE5", rx: int = 10) -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1" rx="{rx}"/>'
    )


def draw_image_placeholder(x: float, y: float, w: float, h: float) -> str:
    cx = x + w / 2
    cy = y + h / 2
    icon_w = min(w * 0.22, 30)
    icon_h = icon_w * 0.72
    ix = cx - icon_w / 2
    iy = cy - icon_h / 2
    path = (
        f"M{ix + icon_w * 0.08:.1f},{iy + icon_h * 0.82:.1f} "
        f"L{ix + icon_w * 0.34:.1f},{iy + icon_h * 0.48:.1f} "
        f"L{ix + icon_w * 0.48:.1f},{iy + icon_h * 0.63:.1f} "
        f"L{ix + icon_w * 0.72:.1f},{iy + icon_h * 0.34:.1f} "
        f"L{ix + icon_w * 0.92:.1f},{iy + icon_h * 0.82:.1f} Z"
    )
    return (
        draw_box(x, y, w, h, fill="#F2F5F8", stroke="#D7DDE5", rx=10)
        + f'<rect x="{ix:.1f}" y="{iy:.1f}" width="{icon_w:.1f}" height="{icon_h:.1f}" fill="none" stroke="#BFC7D2" stroke-width="1.1" rx="3"/>'
        + f'<circle cx="{ix + icon_w * 0.26:.1f}" cy="{iy + icon_h * 0.26:.1f}" r="{icon_w * 0.09:.1f}" fill="#C5CCD6"/>'
        + f'<path d="{path}" fill="#CDD4DD"/>'
    )


def draw_module_box(x: float, y: float, w: float, h: float) -> str:
    icon = f'<circle cx="{x + 18:.1f}" cy="{y + 18:.1f}" r="6" fill="#D0D6DE"/>'
    lines = draw_text_lines(x + 32, y + 8, w - 42, 22, strong=True, count=2)
    body = draw_text_lines(x + 14, y + h * 0.48, w - 28, h * 0.28, count=2)
    return draw_box(x, y, w, h) + icon + lines + body


def draw_metric_box(x: float, y: float, w: float, h: float) -> str:
    num_size = min(h * 0.42, w * 0.22)
    return (
        draw_box(x, y, w, h)
        + f'<text x="{x + w / 2:.1f}" y="{y + h * 0.48:.1f}" text-anchor="middle" '
          f'font-family="Segoe UI, sans-serif" font-size="{num_size:.0f}" font-weight="800" fill="#C6CDD7">42</text>'
        + f'<rect x="{x + w * 0.28:.1f}" y="{y + h * 0.68:.1f}" width="{w * 0.44:.1f}" height="4" fill="#D3D8DF" rx="2"/>'
    )


def draw_flow_band(x: float, y: float, w: float, h: float) -> str:
    items = [draw_box(x, y, w, h, fill="#FBFCFE", stroke="#D7DDE5", rx=12)]
    cy = y + h / 2
    items.append(f'<line x1="{x + 22:.1f}" y1="{cy:.1f}" x2="{x + w - 22:.1f}" y2="{cy:.1f}" stroke="#D2D8E0" stroke-width="2"/>')
    count = 4
    for i in range(count):
        cx = x + 22 + i * ((w - 44) / (count - 1))
        items.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="10" fill="#FFFFFF" stroke="#D0D6DE" stroke-width="1.2"/>')
        if i < count - 1:
            nx = x + 22 + (i + 1) * ((w - 44) / (count - 1))
            items.append(f'<polygon points="{nx - 9:.1f},{cy:.1f} {nx - 15:.1f},{cy - 4:.1f} {nx - 15:.1f},{cy + 4:.1f}" fill="#D0D6DE"/>')
    return "".join(items)


def draw_stage_band(x: float, y: float, w: float, h: float) -> str:
    items: list[str] = []
    gap = 10
    cols = 3
    cell_w = (w - gap * (cols - 1)) / cols
    for i in range(cols):
        bx = x + i * (cell_w + gap)
        items.append(draw_module_box(bx, y, cell_w, h))
        if i < cols - 1:
            cx = bx + cell_w
            cy = y + h / 2
            items.append(f'<line x1="{cx + 4:.1f}" y1="{cy:.1f}" x2="{cx + gap - 4:.1f}" y2="{cy:.1f}" stroke="#D0D6DE" stroke-width="2"/>')
            items.append(f'<polygon points="{cx + gap - 4:.1f},{cy:.1f} {cx + gap - 10:.1f},{cy - 4:.1f} {cx + gap - 10:.1f},{cy + 4:.1f}" fill="#D0D6DE"/>')
    return "".join(items)


def draw_timeline_band(x: float, y: float, w: float, h: float) -> str:
    items = [f'<line x1="{x + 20:.1f}" y1="{y + h * 0.36:.1f}" x2="{x + w - 20:.1f}" y2="{y + h * 0.36:.1f}" stroke="#D2D8E0" stroke-width="2"/>']
    count = 5
    for i in range(count):
        cx = x + 20 + i * ((w - 40) / (count - 1))
        items.append(f'<circle cx="{cx:.1f}" cy="{y + h * 0.36:.1f}" r="8" fill="#FFFFFF" stroke="#D0D6DE" stroke-width="1.2"/>')
        items.append(f'<rect x="{cx - 18:.1f}" y="{y + h * 0.62:.1f}" width="36" height="4" fill="#D3D8DF" rx="2"/>')
    return "".join(items)


def draw_chart_box(x: float, y: float, w: float, h: float) -> str:
    items = [draw_box(x, y, w, h)]
    cols = 4
    gap = 12
    bar_w = (w - gap * (cols + 1)) / cols
    heights = [0.28, 0.44, 0.62, 0.38]
    for i, ratio in enumerate(heights):
        bx = x + gap + i * (bar_w + gap)
        bh = h * ratio
        by = y + h - 14 - bh
        items.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="#D5DAE1" rx="4"/>')
    return "".join(items)


def draw_table_box(x: float, y: float, w: float, h: float) -> str:
    items = [draw_box(x, y, w, h)]
    rows, cols = 4, 3
    for r in range(1, rows):
        yy = y + h * r / rows
        items.append(f'<line x1="{x:.1f}" y1="{yy:.1f}" x2="{x + w:.1f}" y2="{yy:.1f}" stroke="#D9DEE5" stroke-width="1"/>')
    for c in range(1, cols):
        xx = x + w * c / cols
        items.append(f'<line x1="{xx:.1f}" y1="{y:.1f}" x2="{xx:.1f}" y2="{y + h:.1f}" stroke="#D9DEE5" stroke-width="1"/>')
    items.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h * 0.2:.1f}" fill="#F3F6F9" rx="10"/>')
    return "".join(items)


def draw_matrix_box(x: float, y: float, w: float, h: float) -> str:
    items = [draw_box(x, y, w, h)]
    cx = x + w / 2
    cy = y + h / 2
    items.append(f'<line x1="{cx:.1f}" y1="{y + 10:.1f}" x2="{cx:.1f}" y2="{y + h - 10:.1f}" stroke="#D6DCE4" stroke-width="1.5"/>')
    items.append(f'<line x1="{x + 10:.1f}" y1="{cy:.1f}" x2="{x + w - 10:.1f}" y2="{cy:.1f}" stroke="#D6DCE4" stroke-width="1.5"/>')
    items.append(f'<circle cx="{x + w * 0.32:.1f}" cy="{y + h * 0.34:.1f}" r="8" fill="#D4D9E0"/>')
    items.append(f'<circle cx="{x + w * 0.66:.1f}" cy="{y + h * 0.62:.1f}" r="8" fill="#D4D9E0"/>')
    return "".join(items)


def draw_slot(kind: str, x: float, y: float, w: float, h: float) -> str:
    if kind == "skip":
        return ""
    if kind == "title":
        return draw_text_lines(x, y, w, h, strong=True, count=2)
    if kind == "text":
        return draw_text_lines(x, y, w, h, count=2)
    if kind == "visual":
        return draw_image_placeholder(x, y, w, h)
    if kind == "metric":
        return draw_metric_box(x, y, w, h)
    if kind == "chart":
        return draw_chart_box(x, y, w, h)
    if kind == "table":
        return draw_table_box(x, y, w, h)
    if kind == "matrix":
        return draw_matrix_box(x, y, w, h)
    if kind == "flow":
        return draw_flow_band(x, y, w, h)
    if kind == "stage-sequence":
        return draw_module_box(x, y, w, h)
    if kind == "timeline":
        return draw_timeline_band(x, y, w, h)
    return draw_module_box(x, y, w, h)


def make_svg(layout: dict) -> str:
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VW} {VH}" width="{VW}" height="{VH}">',
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        '<rect x="1.5" y="1.5" width="477" height="267" rx="18" fill="#FFFFFF" stroke="#DCE2EA" stroke-width="2"/>',
    ]

    slots = [slot for slot in layout["slots"] if slot.get("region")]
    stage_slots = [slot for slot in slots if slot_kind(slot["id"], slot.get("note", "")) == "stage-sequence"]
    if len(stage_slots) >= 3:
        first = stage_slots[0]["region"]
        last = stage_slots[-1]["region"]
        x = pct(first[0], VW)
        y = pct(first[1], VH)
        w = pct(last[0] + last[2] - first[0], VW)
        h = pct(max(slot["region"][3] for slot in stage_slots), VH)
        pieces.append(draw_stage_band(x, y, w, h))
        consumed = {slot["id"] for slot in stage_slots}
    else:
        consumed = set()

    for slot in slots:
        if slot["id"] in consumed:
            continue
        x, y, w, h = slot["region"]
        px, py, pw, ph = pct(x, VW), pct(y, VH), pct(w, VW), pct(h, VH)
        kind = slot_kind(slot["id"], slot.get("note", ""))
        pieces.append(draw_slot(kind, px, py, pw, ph))

    pieces.append("</svg>")
    return "".join(pieces)


def validate_taxonomy(layouts: list[dict]) -> None:
    legacy_categories = {"文字 / 敘事", "模組陣列", "流程 / 時間軸", "數據圖表", "比較 / 結構"}
    errors: list[str] = []
    by_id = {item["id"]: item for item in layouts}

    for item in layouts:
        missing = [
            key
            for key in [
                "category",
                "subgroup",
                "structure",
                "position_family",
                "composition",
                "gallery_category",
                "slide_role",
                "title_relation",
                "content_flow",
            ]
            if not str(item.get(key, "")).strip()
        ]
        if missing:
            errors.append(f"{item['id']}: missing taxonomy fields {', '.join(missing)}")
        if item.get("category") in legacy_categories:
            errors.append(f"{item['id']}: legacy single-axis category {item['category']!r}")
        if item.get("gallery_category") not in GALLERY_CATEGORY_ORDER:
            errors.append(
                f"{item['id']}: invalid gallery_category {item.get('gallery_category')!r}"
            )
        if item.get("slide_role") not in SLIDE_ROLE_ORDER:
            errors.append(f"{item['id']}: invalid slide_role {item.get('slide_role')!r}")
        if item.get("title_relation") not in TITLE_RELATION_ORDER:
            errors.append(f"{item['id']}: invalid title_relation {item.get('title_relation')!r}")
        if item.get("content_flow") not in CONTENT_FLOW_ORDER:
            errors.append(f"{item['id']}: invalid content_flow {item.get('content_flow')!r}")

    for layout_id in ["heat-map", "map-region", "map-spotlight", "org-chart"]:
        item = by_id.get(layout_id)
        if not item:
            errors.append(f"{layout_id}: missing from gallery")
        elif item.get("category") != "圖表類型":
            errors.append(f"{layout_id}: expected 圖表類型, found {item.get('category')!r}")

    if errors:
        raise ValueError("Invalid Layout Gallery taxonomy:\n- " + "\n- ".join(errors))


def build_payload() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    latest_qa = load_latest_qa()
    layouts: list[dict] = []
    for layout_path in sorted(LAYOUTS_DIR.glob("*.yaml")):
        layout_id = layout_path.stem
        if layout_id in EXCLUDED_IDS:
            continue
        layout = parse_layout(layout_path)
        svg = make_svg(layout)
        preview_path = OUT_DIR / f"{layout_id}.svg"
        if layout_id not in CUSTOM_SVG_IDS or not preview_path.exists():
            preview_path.write_text(svg, encoding="utf-8", newline="\n")
        category = infer_category(layout_id, layout.get("display_name"))
        gallery_category = infer_gallery_category(layout_id, category)
        slide_role = infer_slide_role(category)
        structure = infer_structure(layout_id, category)
        variant = infer_variant(layout_id, category)
        title = infer_title(layout_id, layout.get("display_name"))
        position_family = infer_position_family(layout_id)
        title_relation = infer_title_relation(layout_id, position_family)
        content_flow = infer_content_flow(layout_id)
        composition = infer_composition(layout_id, position_family, variant)
        subgroup = infer_subgroup(layout_id, category, position_family)
        chart_family, chart_type = CHART_TYPES.get(layout_id, (None, None))
        summary = infer_summary(layout_id, category, structure, variant, composition)
        style_case_path = next(iter(sorted(STYLE_CASES_DIR.glob(f"{layout_id}.*.yaml"))), None)
        style_case_preview = None
        style_case_title = None
        if style_case_path:
            style_case_id = style_case_path.stem
            style_case_preview_path = next(
                (
                    STYLE_CASE_PREVIEWS_DIR / f"{style_case_id}{ext}"
                    for ext in [".png", ".jpg", ".jpeg", ".webp", ".svg"]
                    if (STYLE_CASE_PREVIEWS_DIR / f"{style_case_id}{ext}").exists()
                ),
                None,
            )
            if style_case_preview_path:
                style_case_preview = f"layout-style-cases/{style_case_preview_path.name}"
                style_case_title = safe_display_name(parse_layout(style_case_path).get("display_name")) or style_case_id

        codex_preview, preview_status = approved_codex_preview(layout_id, latest_qa)
        preview_variants = build_preview_variants(layout_id, codex_preview, preview_status)
        layouts.append(
            {
                "id": layout_id,
                "title": title,
                "category": category,
                "gallery_category": gallery_category,
                "slide_role": slide_role,
                "subgroup": subgroup,
                "structure": structure,
                "position_family": position_family,
                "title_relation": title_relation,
                "content_flow": content_flow,
                "composition": composition,
                "variant": variant,
                "chart_family": chart_family,
                "chart_type": chart_type,
                "summary": summary,
                "slot_count": "4–7" if layout_id == "pyramid" else len(layout["slots"]),
                "preview": f"layout-previews/{layout_id}.svg",
                "codex_preview": codex_preview,
                "preview_status": preview_status,
                "preview_variants": preview_variants,
                "style_case_preview": style_case_preview,
                "style_case_title": style_case_title,
                "yaml_path": f"prompt_system/layouts/{layout_id}.yaml",
            }
        )

    validate_taxonomy(layouts)
    return {
        "count": len(layouts),
        "categories": sorted({item["category"] for item in layouts}),
        "gallery_categories": [
            value
            for value in GALLERY_CATEGORY_ORDER
            if any(item["gallery_category"] == value for item in layouts)
        ],
        "slide_roles": [
            value for value in SLIDE_ROLE_ORDER if any(item["slide_role"] == value for item in layouts)
        ],
        "title_relations": [
            value for value in TITLE_RELATION_ORDER if any(item["title_relation"] == value for item in layouts)
        ],
        "content_flows": [
            value for value in CONTENT_FLOW_ORDER if any(item["content_flow"] == value for item in layouts)
        ],
        "layouts": layouts,
    }


def main() -> None:
    payload = build_payload()
    JS_OUT.write_text(
        "window.LAYOUT_GALLERY = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Generated {payload['count']} curated layout previews in {OUT_DIR}")


if __name__ == "__main__":
    main()
