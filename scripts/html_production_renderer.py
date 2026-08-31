#!/usr/bin/env python3
"""Production-grade family renderers shared by the HTML matrix catalogs.

The module deliberately keys behavior by layout semantics, never by a
Theme x Layout combination.  Themes only provide visual tokens and optional
family-level decoration overrides.
"""

from __future__ import annotations

import html
import math
import re
from typing import Any

from html_cards_1plus3_variants import (
    CARDS_1PLUS3_VARIANT_CSS,
    CARDS_1PLUS3_VARIANT_IDS,
    render_cards_1plus3_variant,
)
from html_font_system import css_font_stack, resolve_google_font_family, theme_font_contract
from python_chart_renderer import (
    render_annotation_line_chart_svg,
    render_dashboard_combo_chart_svg,
    render_heat_map_chart_svg,
    render_highlight_line_chart_svg,
    render_multi_line_chart_svg,
    render_radar_chart_svg,
)


CONTENT_W = 1728
CONTENT_H = 888
GENERATED_TEXT_MIN_PX = 36
KPI_TAKEAWAY_MIN_CHARS = 18
KPI_TAKEAWAY_MAX_CHARS = 44

# The heat map is one table: row headers, column headers and value cells are all
# drawn by the chart contract in a single coordinate system. Splitting the row
# labels into their own HTML card gave them a second geometry that drifted from
# the cells and read as two tables. Six-character CJK labels need this much room
# at the generated 36px floor. The table ends before the separate legend rail.
HEAT_ROW_LABEL_W = 260
HEAT_GRID_W = 1376
HEAT_TABLE_W = HEAT_ROW_LABEL_W + HEAT_GRID_W
HEAT_GRID_H = 600
HEAT_PANEL_TOP = 140
HEAT_LEGEND_X = 1660

# Centered-cover text measures are a share of the stack that owns them, never a
# literal px constant. A stack that grows must not leave its headline capped at
# a width copied from a narrower composition. Ratios are the ones the original
# 1420px centered cover shipped with: title 0.93, subtitle 0.775, meta 0.634.
_COVER_TITLE_MEASURE = 0.93
_COVER_SUBTITLE_MEASURE = 0.775
_COVER_META_MEASURE = 0.634


def _cover_measure(stack_width: int, share: float) -> int:
    """Resolve one centered-cover text measure from the stack that contains it."""
    return round(stack_width * share)


def _wrapped_line_count(text: str, measure_px: float, font_px: float) -> int:
    """Estimate wrapped line count so fixed-height panels can fail closed.

    Full-width CJK advances one em; Latin and digits advance about half. The
    estimate stays deliberately optimistic so it only rejects content that
    cannot fit under any reasonable font metric.
    """
    per_line = max(1.0, measure_px / font_px)
    lines = 1
    used = 0.0
    for char in text:
        if char == "\n":
            lines += 1
            used = 0.0
            continue
        advance = 1.0 if ord(char) > 0x2E7F else 0.5
        if used + advance > per_line:
            lines += 1
            used = 0.0
        used += advance
    return lines


def _non_whitespace_character_count(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


DIAGRAM_CONTENT: dict[str, dict[str, Any]] = {
    "cycle-hub-6": {
        "title": "可驗證\n決策循環",
        "items": [
            ("01", "收集", "保留原始訊號"),
            ("02", "分類", "拆開症狀與原因"),
            ("03", "取捨", "選出關鍵假設"),
            ("04", "測試", "設定可否證條件"),
            ("05", "判讀", "比較結果與預期"),
            ("06", "回寫", "更新規則與下一步"),
        ],
    },
    "funnel-4": {
        "title": "把市場關注轉成可驗證需求",
        "items": [
            ("觸及", "12,400", "100%", "看見核心訊息"),
            ("互動", "5,580", "45%", "願意深入理解"),
            ("試用", "1,730", "31%", "進入真實情境"),
            ("採用", "620", "36%", "形成持續行為"),
        ],
    },
    "org-chart": {
        "title": "一個決策中心，三條清楚責任線",
        "root": ("產品決策小組", "統一問題定義與驗收標準"),
        "children": [
            ("研究與洞察", "整理訊號與使用者證據", "3 人"),
            ("產品與設計", "提出假設並完成原型", "5 人"),
            ("工程與數據", "建立實驗與量測回路", "6 人"),
        ],
        "note": "共同節奏：每週判讀、雙週驗證、每月回寫規則",
    },
    "pyramid": {
        "title": "從共同基礎走向可複製決策",
        "items": [
            ("05", "可複製決策", "方法能跨團隊重用"),
            ("04", "驗證機制", "結果可以被觀察"),
            ("03", "共同規格", "輸入輸出定義一致"),
            ("02", "結構化訊號", "分類症狀、原因與風險"),
            ("01", "原始證據", "保留情境、來源與限制"),
        ],
    },
}


COMPARISON_CONTENT: dict[str, dict[str, Any]] = {
    "before-after": {
        "before": ("BEFORE · 意見池", "聲量競爭", "大家都在提案，但沒有共同判斷方法", ["回饋與需求混在一起", "優先級跟著會議聲量變動", "做完後沒有留下學習"]),
        "after": ("AFTER · 訊號系統", "證據決策", "每個選擇都連結證據、假設與可驗證結果", ["訊號先標示來源與強度", "優先級透過共同濾網比較", "驗證結果回寫為團隊記憶"]),
    },
    "comparison-table": {
        "title": "三種決策方法，哪一種能持續累積？",
        "subtitle": "以證據連結、驗收標準、學習回寫與擴張成本作為共同比較基準",
        "columns": ["比較基準", "個別經驗", "固定模板", "證據循環"],
        "rows": [
            ("連結原始證據", "低", "中", "高"),
            ("驗收標準一致", "低", "高", "高"),
            ("結果回寫規則", "無", "部分", "完整"),
            ("跨團隊擴張", "難", "中", "易"),
        ],
        "note": "建議：使用模板固定結構，再用證據循環持續更新判斷。",
    },
    "matrix-4quadrant": {
        "title": "先找出高證據、高影響的決策訊號",
        "axes": ("證據弱", "證據強", "影響低", "影響高"),
        "quadrants": [
            ("觀察區", "資料不足，先保留並繼續收集"),
            ("快速決策", "證據充足，可直接排入行動"),
            ("低優先", "影響有限，不急於投入資源"),
            ("優先驗證", "影響大但證據弱，先設計實驗"),
        ],
    },
    "pricing-3col": {
        "title": "依據團隊成熟度選擇導入層級",
        "tiers": [
            ("START", "$0", "個人起步", ["基礎 Theme 與 Layout", "HTML 自由編輯", "社群支援"], "免費開始"),
            ("TEAM", "$49", "最適團隊", ["共用主題與版型庫", "原生可編輯 PPTX", "證據與 QA ledger"], "建議方案"),
            ("SCALE", "CUSTOM", "跨組織擴張", ["專屬 Theme token", "權限與版本管理", "導入與顧問支援"], "聯絡我們"),
        ],
    },
    "split-comparison": {
        "title": "同一份回饋，可以產生兩種完全不同的行動",
        "left": ("× 直覺排序", "先做最常被提到的需求", ["忽略來源與使用情境", "大聲量不等於高影響", "結果難以驗證"]),
        "right": ("✓ 證據排序", "先找到影響大且可否證的假設", ["保留訊號來源與強度", "用共同濾網比較", "結果回寫成新規則"]),
    },
    "swot-quadrant": {
        "title": "用 SWOT 看清 AI 簡報系統的導入條件",
        "subtitle": "內部能力與外部環境必須放在同一個判斷框架",
        "quadrants": [
            ("S", "STRENGTHS", ["主題與版型可重用", "HTML 與 PPTX 共用語意", "檢查流程可自動化"]),
            ("W", "WEAKNESSES", ["視覺調校仍需人眼", "複雜組件需額外 renderer", "字體環境影響量測"]),
            ("O", "OPPORTUNITIES", ["降低簡報重複製作", "沉澱組織設計規則", "建立可追蹤品質基準"]),
            ("T", "THREATS", ["過度規則化造成僵化", "低品質輸入被快速放大", "版本漂移破壞一致性"]),
        ],
    },
}


METRICS_CONTENT: dict[str, dict[str, Any]] = {
    "dashboard-overview": {
        "title": "決策系統本月運作概況",
        "subtitle": "2026 Q2 · 產品、研究與營運團隊共用資料",
        "kpis": [
            ("決策週期", "3.2天", "↓ 18%"),
            ("證據覆蓋", "86%", "↑ 11pt"),
            ("可否證實驗", "42", "↑ 9"),
            ("重複爭論", "18%", "↓ 7pt"),
        ],
        "chart": {
            "title": "證據覆蓋率連續六週提升",
            "metric": "+24pt",
            "bars": [38, 46, 51, 63, 74, 86],
            "labels": ["W1", "W2", "W3", "W4", "W5", "W6"],
        },
        "insight": (
            "本月洞察",
            "速度變快，但不是靠省略驗證",
            ["研究輸入改為統一證據格式", "高影響假設優先進入實驗", "每週回寫失敗與停止理由"],
        ),
        "footnote": "資料來源：Decision Ledger · 統計範圍為近 90 天；數值為 Demo 模擬資料。",
    },
    "kpi-scorecards": {
        "title": "用學習速度驗收決策系統",
        "cards": [
            ("3.2天", "中位決策時間", "較上季縮短 1.4 天", "↓ 30%"),
            ("42", "每月可否證實驗", "其中 31 個完成回寫", "↑ 27%"),
            ("86%", "有來源決策紀錄", "跨三個產品團隊", "↑ 11pt"),
            ("18%", "重複爭論率", "相同議題再次開會", "↓ 7pt"),
        ],
        "takeaway": "真正的效率不是做得更快，而是更快得到可以被下一次重用的確定性。",
    },
    "stats-3-row": {
        "eyebrow": "THIS QUARTER · 我們的學習成績單",
        "stats": [
            ("24pt", "證據覆蓋提升", "從 62% 提升至 86%"),
            ("1.4天", "決策時間縮短", "中位數降至 3.2 天"),
            ("31次", "驗證結果回寫", "成為下一輪共同規則"),
        ],
        "footnote": "同一期間、同一統計口徑；數值為版型展示用模擬資料。",
    },
}


CLOSING_CONTENT: dict[str, dict[str, Any]] = {
    "closing-photo-overlay-contact": {
        "kicker": "SLIDE FIRM · SYSTEM DEMO",
        "title": "THANK YOU",
        "body": "把每一次簡報製作，變成下一次可以直接重用的共同能力。",
        "contact": [
            ("MAIL", "hello@slidefirm.tw"),
            ("WEB", "slidefirm.tw"),
            ("TEL", "+886 2 5550 2026"),
        ],
        "social": [("in", "LINKEDIN"), ("ig", "INSTAGRAM"), ("yt", "YOUTUBE")],
    },
}


STATEMENT_CONTENT: dict[str, dict[str, Any]] = {
    "highlight-callout": {
        "title": "三個轉折點，解釋證據覆蓋為何持續上升",
        "chart": ("近六週證據覆蓋率", [42, 47, 55, 68, 76, 86], ["W1", "W2", "W3", "W4", "W5", "W6"]),
        "callouts": [
            ("01", "格式統一", "研究輸入改用同一份證據欄位"),
            ("02", "先驗證高影響假設", "會議不再從所有需求同時開始"),
            ("03", "結果必須回寫", "失敗與停止理由也成為團隊資產"),
        ],
    },
    "quote-attribution-3": {
        "title": "同一套系統，讓三種角色用同一種語言合作",
        "quotes": [
            ("我們終於能說清楚，現在相信的是證據還是假設。", "林子晴", "產品負責人"),
            ("研究不再只是一份報告，而是每個決策都能追溯的輸入。", "周以安", "研究主管"),
            ("驗收標準先寫清楚後，工程團隊少了很多重複猜測。", "陳奕辰", "工程經理"),
        ],
    },
    "quote-focus": {
        "quote": "好系統不是替人做決定，而是讓每個決定都能被理解、驗證與重用。",
        "attribution": "— Slide Firm · System Principle 04",
    },
    "title-center": {
        "headline": "真正的效率，是更快得到確定性",
        "support": "把證據、假設、驗收與回寫放進同一個循環，團隊就不用每次從零開始爭論。",
    },
}


CHAPTER_CONTENT: dict[str, dict[str, Any]] = {
    "chapter-fullbleed-overlay-title": {
        "label": "CHAPTER",
        "title": "從訊號走向決策",
        "subtitle": "建立共同判斷語言",
        "number": "03",
    },
    "chapter-number-bg-left-title-rule": {
        "label": "CHAPTER 04",
        "title": "讓驗證結果成為下一輪輸入",
        "subtitle": "回寫不是收尾，而是組織開始累積判斷能力的地方。",
        "number": "04",
    },
    "chapter-opener": {
        "label": "CHAPTER 05",
        "title": "把學習寫回系統",
        "subtitle": "從一次性的專案經驗，轉成下一次可以直接使用的共同規則。",
        "number": "05",
    },
    "chapter-text-left-photo-brand": {
        "label": "PART 06",
        "title": "讓方法長成品牌能力",
        "body": "當 Theme、Layout、內容與驗收共用同一套語意，品牌一致性就不再依賴某一位設計師記得所有細節。",
        "brand": "SLIDE FIRM",
        "brand_note": "PRESENTATION SYSTEM",
    },
}


CONTENT_CONTENT: dict[str, dict[str, Any]] = {
    "recommendation-stack": {
        "title": "四個動作，依序降低簡報系統的導入風險",
        "subtitle": "排序依據：影響範圍、依賴關係與最短可驗證時間",
        "recommendations": [
            ("01", "先鎖定共同輸入", "Theme、Layout 與內容都從同一份語意資料讀取。", "NOW"),
            ("02", "再統一驗收方式", "把溢位、對比、可編輯性與語意圖形寫成共同檢查。", "NEXT"),
            ("03", "建立人工視覺關卡", "自動檢查後仍保留代表 Theme 的人眼設計判斷。", "NEXT"),
            ("04", "最後擴大到所有 Theme", "先證明 family renderer 穩定，再跑完整 31×81 回歸。", "SCALE"),
        ],
        "rationale": "先穩定語意與驗收，再擴大產量；否則只會更快複製不一致。",
    },
    "strategic-priorities": {
        "title": "把資源放在最能累積組織能力的地方",
        "subtitle": "優先順序綜合影響、急迫性、依賴關係與可驗證程度",
        "priorities": [
            ("01", "共同 renderer", "所有輸出共享 Theme 與 Layout 語意", "HIGH IMPACT", "55%"),
            ("02", "編輯可靠性", "縮放、群組、復原與匯出必須穩定", "CRITICAL", "30%"),
            ("03", "自動化 QA", "把可量測問題提早擋在交付之前", "ENABLE", "15%"),
        ],
        "impact": "資源配置原則：先處理會影響所有後續輸出的共同層，再處理單一版型的局部優化。",
    },
}


SEQUENCE_CONTENT: dict[str, dict[str, Any]] = {
    "flow-stages-3": {
        "title": "三個階段，把零散回饋變成可驗證決策",
        "subtitle": "每一階段都有自己的輸入、工作與明確輸出",
        "stages": [
            ("01", "整理訊號", "保留來源、情境與強度", "INPUT"),
            ("02", "形成假設", "區分證據、推論與未知", "FRAME"),
            ("03", "驗證回寫", "用結果更新共同規則", "LEARN"),
        ],
        "takeaway": "流程的價值不在於多三個步驟，而在於每一步都留下下一步能使用的輸出。",
    },
    "gantt-roadmap": {
        "title": "十二週完成 HTML Layout Production 化",
        "subtitle": "以 family 為交付單位，先完成代表 Theme，再擴大到 31 Theme 回歸",
        "periods": ["W1–2", "W3–4", "W5–6", "W7–8", "W9–10", "W11–12"],
        "tasks": [
            ("語意盤點", 0, 2, "done"),
            ("Renderer 實作", 1, 4, "active"),
            ("代表 Theme QA", 2, 4, "active"),
            ("31 Theme 回歸", 4, 2, "next"),
            ("人工視覺驗收", 5, 1, "next"),
        ],
        "footnote": "里程碑：每個 family 都有獨立 commit、QA ledger 與可回溯產物。",
    },
    "process-flow": {
        "title": "一次決策，依序通過五個必要關卡",
        "subtitle": "節點之間有明確輸入輸出，不能任意跳過或交換順序",
        "steps": [
            ("01", "收集", "保留原始訊號"),
            ("02", "分類", "區分症狀與原因"),
            ("03", "取捨", "選最值得驗證者"),
            ("04", "測試", "設定可否證條件"),
            ("05", "回寫", "更新判斷規則"),
        ],
        "note": "例外：若關鍵證據缺失，流程應回到收集，而不是直接做出不可追溯的結論。",
    },
    "timeline-milestones": {
        "title": "六個里程碑，逐步建立共同簡報系統",
        "subtitle": "時間順序是主角，每個節點只保留一個可驗收成果",
        "milestones": [
            ("JAN", "共用 Theme"), ("FEB", "Layout Schema"), ("MAR", "HTML 編輯"),
            ("APR", "PPTX 輸出"), ("MAY", "QA Ledger"), ("JUN", "全量回歸"),
        ],
    },
    "timeline-vertical": {
        "title": "從原型走到可交付系統的五次關鍵轉折",
        "events": [
            ("2026.01", "建立共用入口", "Theme 與 Layout 不再分散在三種輸出流程。"),
            ("2026.02", "加入單檔編輯器", "HTML 可以直接改字、移動、縮放與復原。"),
            ("2026.03", "修正群組縮放", "文字與物件同步縮放且不產生意外換行。"),
            ("2026.04", "導入語意 renderer", "循環、漏斗、比較表與時間線使用正確圖形。"),
            ("NEXT", "完成 31×81 驗收", "跨 Theme 無溢位、無錯誤語意圖形、編輯框可靠。"),
        ],
    },
}


COVER_CONTENT: dict[str, dict[str, Any]] = {
    "cover-center-title-edge-decor": {
        "title": "把 AI 簡報變成共同系統",
        "subtitle": "從 Theme、Layout 到 HTML 與 PPTX 的可重複製作方法",
        "speaker": "NEO · 簡報事務所",
        "org": "SLIDE FIRM · 2026",
    },
    "cover-center-title-double-frame": {
        "title": "讓重要主張安靜地被看見",
        "subtitle": "以雙線外框建立邊界，中央只保留必要的開場訊息。",
        "speaker": "NEO · 簡報事務所",
        "org": "SLIDE FIRM · 2026",
    },
    "cover-left-title-open-field": {
        "title": "讓每一頁都有清楚的閱讀入口",
        "subtitle": "主張、證據與下一步各自站在對的位置。",
        "speaker": "NEO · 簡報事務所",
        "org": "SLIDE FIRM · 2026",
    },
    "cover-upper-center-stack-meta-lower-right": {
        "title": "建立可持續的簡報方法",
        "subtitle": "同一套語意，可以延伸到不同輸出。",
        "speaker": "NEO",
        "org": "2026",
    },
    "cover-photo-frame-reverse": {
        "title": "讓每一份簡報都能延續",
        "subtitle": "設計不再從空白頁開始，而是從共同語意與可編輯版型開始。",
        "speaker": "NEO · System Designer",
        "org": "SLIDE FIRM",
    },
    "cover-photo-frame": {
        "title": "共同語意，三種輸出",
        "subtitle": "一套 Theme 與 Layout，同時支援 Image、HTML 與原生可編輯 PPTX。",
        "speaker": "NEO · Presentation Engineer",
        "org": "SLIDE FIRM",
    },
    "cover-photo-overlay-block": {
        "title": "從一次性製作，走向可複製系統",
        "subtitle": "把設計、內容、輸出與驗收收進同一條工作流。",
    },
    "hero-fullbleed-brand-footer": {
        "title": "建立可以持續長大的簡報系統",
        "subtitle": "不只產生投影片，也保存每一次選擇背後的設計與判斷。",
        "speaker": "NEO · Founder",
        "org": "SLIDE FIRM",
    },
    "hero-fullbleed": {
        "title": "簡報不該每次都從零開始",
        "subtitle": "讓組織把好的結構、視覺與驗收方式持續累積下來。",
        "speaker": "NEO",
        "org": "SLIDE FIRM · 2026",
    },
}


DATAVIZ_CONTENT: dict[str, dict[str, Any]] = {
    "data-annotation": {
        "title": "兩次制度改動，帶動證據覆蓋率跨越關鍵門檻",
        "values": [34, 38, 41, 49, 63, 67, 74, 86],
        "labels": ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG"],
        "annotations": [(3, "統一輸入格式", "+8pt"), (6, "強制驗證回寫", "+7pt")],
    },
    "heat-map": {
        "title": "不同團隊在五項能力上的成熟度分布",
        "columns": ["證據", "假設", "驗收", "回寫", "編輯", "回歸"],
        "rows": ["產品", "研究", "工程", "營運", "品牌"],
        "values": [
            [5, 4, 4, 3, 4, 3], [5, 5, 3, 4, 3, 2], [3, 4, 5, 4, 5, 4],
            [3, 3, 4, 3, 4, 3], [1, 3, 3, 2, 5, 3],
        ],
    },
    "map-region": {
        "title": "北中南三區的導入成熟度已出現明顯差異",
        "cards": [("北區", "86%", "共同規則最完整"), ("中區", "68%", "驗收仍在整合"), ("南區", "52%", "優先補齊資料入口")],
    },
    "map-spotlight": {
        "title": "三個城市，分別承擔研究、產品與驗證節點",
        "locations": [("台北", "研究中樞", "25.033°N"), ("台中", "產品協作", "24.147°N"), ("高雄", "驗證基地", "22.627°N")],
    },
    "multi-line-chart": {
        "title": "三項能力同步提升，但回寫速度仍落後",
        "labels": ["W1", "W2", "W3", "W4", "W5", "W6", "W7"],
        "series": [
            ("證據覆蓋", [42, 48, 55, 63, 68, 77, 86]),
            ("驗收一致", [38, 44, 50, 58, 66, 72, 79]),
            ("結果回寫", [28, 31, 38, 42, 49, 54, 61]),
        ],
    },
    "radar-chart": {
        "title": "新流程提升整體能力，最大差距仍在回寫",
        "axes": ["證據", "假設", "取捨", "驗收", "回寫", "擴張"],
        "series": [("導入前", [2, 3, 2, 3, 1, 2]), ("導入後", [5, 4, 4, 5, 3, 4])],
    },
}


MEDIA_CONTENT: dict[str, dict[str, Any]] = {
    "executive-bio": {
        "name": "林映辰",
        "role": "產品策略與研究負責人",
        "bio": [
            "把使用者訊號轉成可驗證的產品決策。",
            "建立跨研究、設計與工程的共同判斷語言。",
            "持續累積可追溯、可重用的組織證據。",
        ],
        "meta": "12 YEARS · PRODUCT / RESEARCH / SYSTEMS",
    },
    "photo-left-overlay-title-right": {
        "title": "保留現場的重量",
        "kicker": "DOCUMENT THE REAL CONTEXT",
        "body": "左側照片提供情境與情緒；右側文字只負責指出觀察重點，不搶走畫面的主角。",
    },
    "testimonial-full": {
        "quote": "當團隊開始用同一份證據討論，會議不再比誰更有把握，而是更快知道下一步該驗證什麼。",
        "name": "周柏翰",
        "role": "COO · NORTHSTAR LABS",
        "logo": "NS",
    },
}


MODULE_ITEMS: list[tuple[str, str, str]] = [
    ("結構", "先確認資訊關係，再決定畫面形狀。", "SYSTEM"),
    ("內容", "用真實文案驗證字級、密度與閱讀節奏。", "CONTENT"),
    ("視覺", "以對比、留白與節奏建立清楚焦點。", "VISUAL"),
    ("編輯", "交付後仍能移動、改字、縮放與群組。", "EDIT"),
    ("輸出", "HTML、PPTX 與 Image2 維持共同規格。", "OUTPUT"),
    ("驗收", "檢查溢位、對比、語意與跨 Theme 回歸。", "QA"),
    ("累積", "把修正回寫成可重用的版型能力。", "LEARN"),
    ("擴張", "新增 Theme 時不重新發明每個 Layout。", "SCALE"),
]


MODULES_CONTENT: dict[str, dict[str, Any]] = {
    layout_id: {
        "title": title,
        "subtitle": subtitle,
        "items": MODULE_ITEMS[:count],
    }
    for layout_id, title, subtitle, count in [
        ("cards-1-plus-2", "兩個支柱，撐起可複製的簡報系統", "一邊負責設計判斷，一邊負責交付能力。", 2),
        ("cards-1-plus-3", "三層驗收，避免只做出看起來完整的畫面", "結構、內容與後續編輯能力缺一不可。", 3),
        ("cards-1-plus-4", "四個面向，決定一份簡報能不能正式上場", "從共同來源一路驗收到實際交付。", 4),
        ("cards-1-plus-5", "五個環節，把一次性製作改造成共同流程", "上排建立系統，下排負責驗收與輸出。", 5),
        ("cards-1-plus-6", "六項能力，共同定義 Production 等級", "每一格都能被獨立理解，也能組成完整工作流。", 6),
        ("cards-1-plus-8", "八個模組，組成完整的簡報生產閉環", "高密度頁面仍保持清楚編號與極短說明。", 8),
    ]
}


ICON_GRID_CONTENT = {
    "title": "六個快速入口，對應簡報生產的核心能力",
    "items": [("結構", "01"), ("主題", "02"), ("版型", "03"), ("圖像", "04"), ("輸出", "05"), ("驗收", "06")],
}


PEOPLE_CONTENT = {
    "title": "三種專業角色，共同完成一份可交付簡報",
    "people": [
        ("林映辰", "產品策略", "把問題、證據與決策路徑整理成清楚敘事。"),
        ("陳郁文", "資訊設計", "讓每一頁的視覺重心與閱讀順序可被感知。"),
        ("周柏翰", "系統工程", "確保 HTML、PPTX 與編輯能力可重複運作。"),
    ],
}


TEAM_CONTENT = {
    "title": "跨職能小隊，讓內容、設計與系統同步前進",
    "members": [
        ("林映辰", "Product Strategy"), ("陳郁文", "Information Design"), ("周柏翰", "System Engineering"),
        ("許安琪", "Research"), ("王正凱", "Quality Assurance"), ("李欣柔", "Content Operations"),
    ],
}


TOC_ITEMS: list[tuple[str, str, str]] = [
    ("01", "問題與目標", "先定義這份簡報必須推動的決策。"),
    ("02", "受眾與情境", "確認誰會看、何時看，以及需要帶走什麼。"),
    ("03", "證據與洞察", "整理足以支持判斷的資料、觀察與限制。"),
    ("04", "策略與取捨", "把可行方向、代價與選擇標準說清楚。"),
    ("05", "方案與體驗", "將策略轉成可感知、可討論的具體方案。"),
    ("06", "執行與節奏", "交代先後順序、責任與驗收節點。"),
    ("07", "風險與回應", "提前標示不確定性與觸發條件。"),
    ("08", "結論與下一步", "收斂決策並指定下一個可追蹤行動。"),
]


TOC_CONTEXT = {
    "title": "從問題到行動，八個章節形成一條決策路徑",
    "intro": "依閱讀情境選擇清單、面板、網格或影像導覽；章節順序維持一致。",
    "footer": "CONTENTS · DECISION PATH · 2026",
}


def esc(value: Any) -> str:
    return html.escape(str(value)).replace("\n", "<br>")


def _copy_value(value: Any) -> str:
    return str(value or "").strip()


def _optional_layer_text(
    value: Any,
    *,
    class_name: str = "",
    tag: str = "span",
    attrs: str = "",
) -> str:
    text = _copy_value(value)
    if not text:
        return ""
    class_attr = f' class="{class_name}"' if class_name else ""
    attrs_text = f" {attrs.strip()}" if attrs.strip() else ""
    return f'<{tag}{class_attr}{attrs_text}>{esc(text)}</{tag}>'


def _optional_loose_text(
    value: Any,
    *,
    class_name: str,
    style: str,
    attrs: str = "",
) -> str:
    text = _copy_value(value)
    if not text:
        return ""
    attrs_text = f" {attrs.strip()}" if attrs.strip() else ""
    return (
        f'<div class="el {class_name}" data-edit-kind="text" data-edit-fit="text"'
        f'{attrs_text} style="{style}">{esc(text)}</div>'
    )


def _svg_coord(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _short_flow_arrow_path(span: float, *, padding: float = 14) -> str:
    """Render a short connector without stroke-width-scaled SVG markers."""

    if span <= 0:
        raise ValueError("flow arrow span must be positive")
    center_y = padding
    tip_x = padding + span
    head_length = min(12.0, span * 0.32)
    head_half_height = min(padding - 2, max(7.0, head_length * 0.65))
    base_x = tip_x - head_length
    return (
        '<path data-arrow-geometry="user-space-chevron" '
        f'data-arrow-span="{_svg_coord(span)}" '
        f'data-arrow-head-length="{_svg_coord(head_length)}" '
        f'd="M {_svg_coord(padding)} {_svg_coord(center_y)} H {_svg_coord(tip_x)} '
        f'M {_svg_coord(base_x)} {_svg_coord(center_y - head_half_height)} '
        f'L {_svg_coord(tip_x)} {_svg_coord(center_y)} '
        f'L {_svg_coord(base_x)} {_svg_coord(center_y + head_half_height)}"/>'
    )


def _user_space_arrow_marker(
    marker_id: str,
    *,
    size: float = 20,
    orient: str = "auto",
) -> str:
    """Return a long-path marker whose size is independent of stroke width."""

    inset = 2.0
    center = size / 2
    tip = size - inset
    safe_id = html.escape(marker_id, quote=True)
    safe_orient = html.escape(orient, quote=True)
    return (
        f'<marker id="{safe_id}" markerUnits="userSpaceOnUse" '
        f'markerWidth="{_svg_coord(size)}" markerHeight="{_svg_coord(size)}" '
        f'viewBox="0 0 {_svg_coord(size)} {_svg_coord(size)}" '
        f'refX="{_svg_coord(tip)}" refY="{_svg_coord(center)}" orient="{safe_orient}">'
        f'<path d="M{_svg_coord(inset)},{_svg_coord(inset)} '
        f'L{_svg_coord(tip)},{_svg_coord(center)} '
        f'L{_svg_coord(inset)},{_svg_coord(size - inset)} z"/></marker>'
    )


def _rgb(value: str) -> tuple[int, int, int]:
    clean = value.strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join(char * 2 for char in clean)
    return tuple(int(clean[index:index + 2], 16) for index in (0, 2, 4))


def _luminance(value: str) -> float:
    def channel(number: int) -> float:
        item = number / 255
        return item / 12.92 if item <= 0.04045 else ((item + 0.055) / 1.055) ** 2.4

    red, green, blue = (channel(item) for item in _rgb(value))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(first: str, second: str) -> float:
    bright, dark = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (bright + 0.05) / (dark + 0.05)


def _mix(foreground: str, background: str, weight: float) -> str:
    front = _rgb(foreground)
    back = _rgb(background)
    values = [round(a * weight + b * (1 - weight)) for a, b in zip(front, back)]
    return "#" + "".join(f"{value:02X}" for value in values)


def _best_text(background: str, candidates: list[str]) -> str:
    return max(candidates, key=lambda candidate: _contrast(candidate, background))


def _ensure_contrast(color: str, background: str, fallback: str, minimum: float) -> str:
    if _contrast(color, background) >= minimum:
        return color
    for step in range(1, 21):
        candidate = _mix(fallback, color, step / 20)
        if _contrast(candidate, background) >= minimum:
            return candidate
    return fallback


def normalize_font_family(value: str | None) -> str:
    return css_font_stack(resolve_google_font_family(value))


def theme_tokens(theme: dict[str, Any]) -> dict[str, str]:
    colors = theme["colors"]
    background = colors["background"]
    support = list(colors.get("support") or [])
    text = _best_text(background, [colors["primary"], "#111827", "#F8FAFC"])
    muted = _ensure_contrast(colors["secondary"], background, text, 5.0)
    explicit_surface = colors.get("surface")
    surface_candidates = ([explicit_surface] if explicit_surface else []) + support
    valid_surfaces = [
        candidate
        for candidate in surface_candidates
        if candidate and _contrast(candidate, background) >= 1.08
    ]
    valid_support_surfaces = [
        candidate
        for candidate in support
        if candidate and _contrast(candidate, background) >= 1.08
    ]
    if explicit_surface and explicit_surface in valid_surfaces:
        surface = explicit_surface
    elif valid_support_surfaces:
        # Support colors are only a fallback for legacy Themes without an
        # explicit surface role. Once a Theme declares surface, preserve that
        # semantic role even when the same color also appears in support.
        surface = min(valid_support_surfaces, key=lambda candidate: _contrast(candidate, background))
    elif valid_surfaces:
        surface = min(valid_surfaces, key=lambda candidate: _contrast(candidate, background))
    else:
        surface = background
    surface_text = _best_text(surface, [text, colors["primary"], "#111827", "#F8FAFC"])
    # Production cards often mix the surface with the page background. A
    # stronger source-material margin keeps text readable after that blend.
    surface_muted = _ensure_contrast(colors["secondary"], surface, surface_text, 7.0)
    accent = colors["accent"]
    accent_ink = _ensure_contrast(accent, background, text, 4.5)
    surface_accent_ink = _ensure_contrast(accent, surface, surface_text, 7.0)
    # Mid-tone accents can fail with near-black / near-white UI neutrals even
    # though true black or white would pass.  CTA and recommended-column text
    # therefore choose from the full luminance endpoints as well.
    accent_text = _best_text(accent, ["#000000", "#FFFFFF", "#111827", "#F8FAFC", text])
    support_accent = support[0] if support else colors["secondary"]
    fonts = theme_font_contract(theme)
    return {
        "background": background,
        "text": text,
        "muted": muted,
        "accent": accent,
        "accent_ink": accent_ink,
        "surface_accent_ink": surface_accent_ink,
        "accent_text": accent_text,
        "surface": surface,
        "surface_text": surface_text,
        "surface_muted": surface_muted,
        "support_accent": support_accent,
        "heading_font": fonts["heading_stack"],
        "body_font": fonts["body_stack"],
        "mono_font": fonts["mono_stack"],
        "display_font": fonts["display_stack"],
    }


def _content_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [item for child in value.values() for item in _content_strings(child)]
    if isinstance(value, (list, tuple)):
        return [item for child in value for item in _content_strings(child)]
    return [str(value)]


def density_profile(content: dict[str, Any]) -> tuple[str, float]:
    strings = _content_strings(content)
    longest = max((len(value.replace("\n", "")) for value in strings), default=0)
    total = sum(len(value.replace("\n", "")) for value in strings)
    if longest <= 14 and total <= 90:
        return "low", 0.84
    if longest <= 24 and total <= 155:
        return "medium", 0.90
    return "high", 0.96


_HTML_START_TAG_RE = re.compile(r"<(?P<tag>[A-Za-z][\w:-]*)(?P<attrs>[^<>]*)(?P<close>/?>)")
_HTML_ATTR_RE = re.compile(r"\b(?P<name>[\w:-]+)\s*=\s*(?P<quote>[\"'])(?P<value>.*?)(?P=quote)")


def _append_markup_attribute(tag_text: str, name: str, value: str) -> str:
    """Add one deterministic attribute without reserializing the HTML tree."""

    if re.search(rf"\b{re.escape(name)}\s*=", tag_text):
        return tag_text
    close = "/>" if tag_text.endswith("/>") else ">"
    return f'{tag_text[:-len(close)]} {name}="{html.escape(value, quote=True)}"{close}'


def _set_markup_attribute(tag_text: str, name: str, value: str) -> str:
    """Set one deterministic attribute while preserving the original tag text."""

    escaped = html.escape(value, quote=True)
    pattern = re.compile(
        rf"(?P<prefix>\b{re.escape(name)}\s*=\s*)(?P<quote>[\"'])(?P<value>.*?)(?P=quote)"
    )
    if pattern.search(tag_text):
        return pattern.sub(lambda match: f'{match.group("prefix")}\"{escaped}\"', tag_text, count=1)
    return _append_markup_attribute(tag_text, name, value)


def infer_page_horizontal_alignment(markup: str) -> str:
    """Infer the rendered page text alignment from the authored title contract."""

    title_align = re.search(r'\bdata-edit-title-align=["\'](left|center|right)["\']', markup)
    if title_align:
        return title_align.group(1)
    if re.search(r'\bdata-edit-align-contract=["\']center-axis["\']', markup):
        return "center"
    return "left"


# Semantic surface roles.  Layout owns which module appears and where; this
# table only says what kind of job the module does, so Preset appearance CSS can
# vary the surface outline per role without ever touching geometry.  Keeping it
# here means the 80-odd component renderers stay unaware of Preset concerns.
SURFACE_ROLE_EXCEPTIONS = {
    "module-icon-cell": "index",
}

SURFACE_ROLE_PREFIXES = (
    ("toc-", "index"),
    ("org-", "index"),
    ("metric-", "metric"),
    ("dataviz-", "metric"),
    ("heat-", "metric"),
    ("radar-", "metric"),
    ("price-", "metric"),
    ("sequence-", "timeline"),
    ("cycle-", "timeline"),
    ("funnel-", "timeline"),
    ("pyramid-", "timeline"),
    ("compare-", "ledger"),
    ("matrix-", "ledger"),
    ("swot-", "ledger"),
    ("split-", "ledger"),
    ("statement-", "statement"),
    ("closing-", "statement"),
    ("chapter-", "statement"),
    ("cover-", "statement"),
    ("content-", "panel"),
    ("module-", "panel"),
    ("media-", "panel"),
    ("map-", "panel"),
)


def resolve_surface_role(class_tokens: set[str]) -> str | None:
    """Return the semantic surface role for one module root, if it has one."""

    for token in sorted(class_tokens):
        role = SURFACE_ROLE_EXCEPTIONS.get(token)
        if role:
            return role
    for token in sorted(class_tokens):
        for prefix, role in SURFACE_ROLE_PREFIXES:
            if token.startswith(prefix):
                return role
    return None


def materialize_editable_production_markup(
    markup: str,
    page_horizontal_alignment: str | None = None,
) -> str:
    """Project legacy production markup onto the shared editable DOM contract.

    The production family renderers intentionally stay focused on visual
    composition. This adapter is the single boundary where their repeated
    card/module markup becomes editor-owned geometry: every composite becomes a
    semantic module, every layer declares its positioning mode, and text-like
    layers carry the shared vertical-alignment default.

    A visual layer may also carry ``data-edit-anchor="bottom"``.  That is a
    semantic parent-edge relationship, not a Theme/Preset geometry override;
    the editor uses it to re-resolve the visual after a parent resize.
    """

    page_alignment = page_horizontal_alignment or infer_page_horizontal_alignment(markup)
    if page_alignment not in {"left", "center", "right"}:
        raise ValueError(f"Unsupported page horizontal alignment: {page_alignment!r}")

    def rewrite(match: re.Match[str]) -> str:
        tag_text = match.group(0)
        attrs = {item.group("name"): item.group("value") for item in _HTML_ATTR_RE.finditer(tag_text)}
        class_tokens = set((attrs.get("class") or "").split())
        layer_kind = attrs.get("data-edit-layer")
        if layer_kind:
            tag_text = _append_markup_attribute(tag_text, "data-edit-position", "absolute")
            anchor = attrs.get("data-edit-anchor")
            if anchor and (layer_kind != "visual" or anchor != "bottom"):
                raise ValueError(
                    "data-edit-anchor currently supports only bottom visual layers; "
                    f"got {anchor!r} on {layer_kind!r}"
                )
            if layer_kind in {"text", "metric"}:
                tag_text = _append_markup_attribute(tag_text, "data-edit-vertical-align", "center")
                if "circle-number-metric" in class_tokens:
                    horizontal_alignment = "center"
                    alignment_source = "circle-number-exception"
                elif attrs.get("data-edit-alignment-source") == "module-interior":
                    horizontal_alignment = attrs.get("data-edit-horizontal-align", "")
                    if horizontal_alignment not in {"left", "center", "right"}:
                        raise ValueError(
                            "module-interior text layers require an explicit left/center/right "
                            f"data-edit-horizontal-align; got {horizontal_alignment!r}"
                        )
                    alignment_source = "module-interior"
                else:
                    horizontal_alignment = page_alignment
                    alignment_source = "page-title"
                tag_text = _set_markup_attribute(tag_text, "data-edit-horizontal-align", horizontal_alignment)
                tag_text = _set_markup_attribute(tag_text, "data-edit-alignment-source", alignment_source)
            return tag_text

        if not attrs.get("data-surface-role"):
            surface_role = resolve_surface_role(class_tokens)
            if surface_role:
                tag_text = _append_markup_attribute(tag_text, "data-surface-role", surface_role)

        if "el" in class_tokens and attrs.get("data-edit-composite"):
            if not attrs.get("data-edit-structure"):
                tag_text = _append_markup_attribute(tag_text, "data-edit-structure", "module")
            if not attrs.get("data-edit-fit"):
                tag_text = _append_markup_attribute(tag_text, "data-edit-fit", "container")
            if not attrs.get("data-edit-role"):
                tag_text = _append_markup_attribute(tag_text, "data-edit-role", "module")
            tag_text = _set_markup_attribute(tag_text, "data-edit-horizontal-align", page_alignment)
            tag_text = _set_markup_attribute(tag_text, "data-edit-alignment-source", "page-title")
        if attrs.get("data-edit-kind") == "text":
            tag_text = _set_markup_attribute(tag_text, "data-edit-horizontal-align", page_alignment)
            tag_text = _set_markup_attribute(tag_text, "data-edit-alignment-source", "page-title")
        return tag_text

    return _HTML_START_TAG_RE.sub(rewrite, markup)


def apply_media_placeholder_policy(
    markup: str,
    layout_id: str,
    media_treatment: str | None,
) -> str:
    """Replace image-like artwork with a plain filled slot for HTML stress tests."""

    if media_treatment != "placeholder-fill":
        return markup
    if layout_id == "icon-grid-6":
        markup, changed = re.subn(
            r'class="module-icon-shape"',
            'class="module-icon-shape media-placeholder-fill"',
            markup,
            count=1,
        )
        if changed != 1:
            raise ValueError("icon-grid-6 is missing its visual placeholder slot")
    if layout_id in {"map-region", "map-spotlight"}:
        markup, changed = re.subn(
            r'<svg(?=[^>]*\bdata-edit-layer="visual")(?=[^>]*\bviewBox="0 0 700 700")[^>]*>.*?</svg>',
            '<div class="media-placeholder-fill map-media-placeholder" data-edit-layer="visual" aria-label="MEDIA PLACEHOLDER"></div>',
            markup,
            count=1,
            flags=re.S,
        )
        if changed != 1:
            raise ValueError(f"{layout_id} is missing its visual placeholder slot")
    return markup

_HTML_TOKEN_RE = re.compile(r'<!--.*?-->|</?[A-Za-z][^<>]*?>', re.S)
_VOID_HTML_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
def _frame(content: dict[str, Any], body: str) -> str:
    density, fill_ratio = density_profile(content)
    height = round(CONTENT_H * fill_ratio)
    top = round((CONTENT_H - height) / 2)
    page_alignment = infer_page_horizontal_alignment(body)
    body = materialize_editable_production_markup(body, page_alignment)
    return (
        f'<div class="prod-frame diagram-frame" data-edit-layout-only="true" '
        f'data-density="{density}" '
        f'data-auto-fill-cap="soft" data-fill-ratio="{fill_ratio:.2f}" data-visual-balance="content-bounds" '
        f'data-page-horizontal-align="{page_alignment}" '
        f'style="top:{top}px;height:{height}px;--prod-frame-height:{height}px">{body}</div>'
    )


def _title(text: str) -> str:
    return (
        f'<div class="el prod-title" data-edit-kind="text" data-edit-fit="text" data-edit-title-align="left" '
        f'style="left:0;top:0;width:max-content;height:auto;max-width:1500px">{esc(text)}</div>'
    )


def _centered_title(text: str) -> str:
    return (
        f'<div class="el prod-title prod-title-center-axis" data-edit-kind="text" data-edit-fit="text" '
        f'data-edit-title-align="center" style="left:864px;top:0;width:max-content;height:auto;max-width:1500px;translate:-50% 0">{esc(text)}</div>'
    )


def _flow_header(
    title: str,
    subtitle: str | None,
    *,
    title_centered: bool = False,
    subtitle_centered: bool | None = None,
    title_max_width: int = 1500,
    subtitle_max_width: int = 1580,
    flow_id: str = "primary-header",
) -> str:
    """Lay out dependent header copy in flow without creating an edit group."""
    if subtitle_centered is None:
        subtitle_centered = title_centered
    title_classes = "el prod-title"
    title_style = f"width:max-content;height:auto;max-width:{title_max_width}px"
    title_contract = ""
    if title_centered:
        title_classes += " prod-title-center-axis"
        title_style += ";align-self:center"
        title_contract = ' data-edit-align-contract="center-axis"'
    subtitle_markup = ""
    if subtitle is not None:
        subtitle_classes = "el prod-subtitle"
        subtitle_style = f"width:max-content;height:auto;max-width:{subtitle_max_width}px"
        subtitle_contract = ""
        if subtitle_centered:
            subtitle_classes += " prod-subtitle-center-axis"
            subtitle_style += ";align-self:center"
            subtitle_contract = ' data-edit-align-contract="center-axis"'
        subtitle_markup = (
            f'<div class="{subtitle_classes}" data-edit-kind="text" data-edit-fit="text"'
            f'{subtitle_contract} style="{subtitle_style}">{esc(subtitle)}</div>'
        )
    flow_align = "center" if title_centered else "start"
    title_horizontal_align = "center" if title_centered else "left"
    return f'''<div class="title-flow-stack" data-edit-layout-only="true" data-auto-layout="vertical-stack" data-layout-flow-id="{esc(flow_id)}" data-layout-flow-align="{flow_align}" data-layout-flow-gap="standard" style="left:0;top:0;width:1728px;height:auto">
      <div class="{title_classes}" data-edit-kind="text" data-edit-fit="text" data-edit-title-align="{title_horizontal_align}"{title_contract} style="{title_style}">{esc(title)}</div>
      {subtitle_markup}
    </div>'''


def _flow_follow(body: str, *, flow_id: str = "primary-header", gap: int = 24) -> str:
    """Move one layout-owned body as a unit when its flow header grows."""
    return f'''<div class="layout-flow-follow-region" data-edit-layout-only="true" data-layout-follow="{esc(flow_id)}" data-layout-follow-gap="{gap}" style="left:0;top:0;width:1728px;height:var(--prod-frame-height)">{body}</div>'''


def _cycle(content: dict[str, Any]) -> str:
    items = list(content["items"])
    if len(items) != 6:
        raise ValueError(
            "cycle-hub-6 requires exactly six items for its canonical left/right slots; "
            "route the content to another compatible Layout"
        )

    center_x, center_y, radius = 864, 390, 260
    node_size = 84
    hub_size = 400
    frame_height = 780
    marker_id = "production-cycle-arrow"
    nodes = []
    callouts = []
    leader_paths = []
    # The visual traversal is the content traversal: 01 starts at upper-right
    # and moves clockwise through right-middle, right-bottom, left-bottom,
    # left-middle, and left-top before returning to 01.
    slot_geometry = [
        ("right", 1248, 64, 480, 210, -60),
        ("right", 1248, 285, 480, 210, 0),
        ("right", 1248, 506, 480, 210, 60),
        ("left", 0, 506, 480, 210, 120),
        ("left", 0, 285, 480, 210, 180),
        ("left", 0, 64, 480, 210, -120),
    ]
    for index, (item, geometry) in enumerate(zip(items, slot_geometry)):
        order = index + 1
        position = (
            "upper-right", "right-middle", "lower-right",
            "lower-left", "left-middle", "upper-left",
        )[index]
        side, callout_left, callout_top, callout_width, callout_height, angle = geometry
        radians = math.radians(angle)
        x = center_x + radius * math.cos(radians)
        y = center_y + radius * math.sin(radians)
        left = x - node_size / 2
        top = y - node_size / 2
        no, title, body = item
        nodes.append(
            f'''<div class="el diagram-node cycle-node" data-edit-composite="cycle-node-{order}" data-cycle-order="{order}" data-cycle-position="{position}"{' data-cycle-start="true"' if order == 1 else ''} style="left:{left:.1f}px;top:{top:.1f}px;width:{node_size}px;height:{node_size}px">
              <div class="diagram-node-bg" data-edit-layer="background"></div>
              <span class="diagram-no circle-number-metric" data-edit-layer="metric" data-edit-horizontal-align="center">{esc(no)}</span>
            </div>'''
        )
        callouts.append(
            f'''<div class="el diagram-node cycle-callout cycle-callout-{side}" data-edit-composite="cycle-callout-{order}" data-cycle-slot="item-{order}" data-cycle-callout-for="{order}" data-cycle-order="{order}" style="left:{callout_left}px;top:{callout_top}px;width:{callout_width}px;height:{callout_height}px">
              <div class="diagram-node-bg" data-edit-layer="background"></div>
              <b class="diagram-node-title" data-edit-layer="text" data-edit-position="flow">{esc(title)}</b>
              <span class="diagram-node-body" data-edit-layer="text" data-edit-position="flow">{esc(body)}</span>
            </div>'''
        )
        if side == "left":
            leader_paths.append(f'<path class="cycle-leader" d="M {callout_left + callout_width:.1f} {y:.1f} H {x - node_size / 2:.1f}"/>')
        else:
            leader_paths.append(f'<path class="cycle-leader" d="M {x + node_size / 2:.1f} {y:.1f} H {callout_left:.1f}"/>')
    ordered_angles = (-60, 0, 60, 120, 180, 240)
    node_clearance_degrees = 11
    cycle_arcs = []
    for index, angle in enumerate(ordered_angles, 1):
        start = math.radians(angle + node_clearance_degrees)
        end = math.radians(angle + 60 - node_clearance_degrees)
        start_x = center_x + radius * math.cos(start)
        start_y = center_y + radius * math.sin(start)
        end_x = center_x + radius * math.cos(end)
        end_y = center_y + radius * math.sin(end)
        cycle_arcs.append(
            f'<path class="cycle-arc" data-cycle-arc="{index}" data-cycle-from="{index:02d}" '
            f'data-cycle-to="{(index % 6) + 1:02d}" d="M {start_x:.1f} {start_y:.1f} '
            f'A {radius} {radius} 0 0 1 {end_x:.1f} {end_y:.1f}" '
            f'marker-end="url(#{marker_id})"/>'
        )
    visual = f'''<svg class="el diagram-connectors cycle-connectors" data-edit-kind="visual" style="left:0;top:0;width:{CONTENT_W}px;height:{frame_height}px" viewBox="0 0 {CONTENT_W} {frame_height}" aria-hidden="true">
      <defs>{_user_space_arrow_marker(marker_id)}</defs>
      <circle class="cycle-ring" data-cycle-loop="true" data-cycle-order="clockwise-01-02-03-04-05-06" cx="{center_x}" cy="{center_y}" r="{radius}"/>{''.join(cycle_arcs)}{''.join(leader_paths)}</svg>'''
    hub_left = center_x - hub_size / 2
    hub_top = center_y - hub_size / 2
    hub = f'''<div class="el diagram-node cycle-hub" data-edit-composite="cycle-hub" data-cycle-geometry="circle" data-visual-surface-role="none" style="left:{hub_left:.1f}px;top:{hub_top:.1f}px;width:{hub_size}px;height:{hub_size}px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>
      <b class="diagram-hub-title" data-edit-layer="text" data-edit-title-align="center">{esc(content['title'])}</b>
    </div>'''
    top = round((CONTENT_H - frame_height) / 2)
    return (
        f'<div class="prod-frame diagram-frame cycle-frame" data-edit-layout-only="true" data-density="low" data-auto-fill-cap="soft" '
        f'data-fill-ratio="0.88" data-visual-balance="content-bounds" data-content-frame="radial-balance" '
        f'data-cycle-geometry="circle" data-cycle-node-count="6" style="top:{top}px;height:{frame_height}px;--prod-frame-height:{frame_height}px">'
        f'{visual}{hub}{"".join(nodes)}{"".join(callouts)}</div>'
    )

def _funnel(content: dict[str, Any]) -> str:
    widths = [1240, 1080, 920, 760]
    stage_height = 174
    top = 40
    stage_step = 180
    stages = []
    for index, (item, width) in enumerate(zip(content["items"], widths)):
        label, value, rate, note = item
        left = (CONTENT_W - width) / 2
        stages.append(
            f'''<div class="el diagram-node funnel-stage" data-edit-composite="funnel-stage-{index + 1}" style="left:{left:.1f}px;top:{top + index * stage_step}px;width:{width}px;height:{stage_height}px">
              <div class="diagram-node-bg funnel-bg" data-edit-layer="background" style="--stage-tone:{88 - index * 8}%"></div>
              <span class="funnel-index" data-edit-layer="metric">{index + 1:02d}</span>
              <b class="funnel-title" data-edit-layer="text">{esc(label)}</b>
              <strong class="funnel-value" data-edit-layer="metric">{esc(value)}</strong>
              <span class="funnel-rate" data-edit-layer="metric">留存 {esc(rate)}</span>
              <span class="funnel-note" data-edit-layer="text">{esc(note)}</span>
            </div>'''
        )
    return _frame(content, _centered_title(content["title"]) + "".join(stages))


def _org_chart(content: dict[str, Any]) -> str:
    root_title, root_body = content["root"]
    child_width, child_height = 430, 176
    child_lefts = [91, 649, 1207]
    connector_paths = [
        "M 864 342 V 410 H 306 V 470",
        "M 864 342 V 470",
        "M 864 410 H 1422 V 470",
    ]
    connectors = (
        f'<svg class="el diagram-connectors org-connectors" data-edit-kind="visual" style="left:0;top:0;width:{CONTENT_W}px;height:820px" '
        f'viewBox="0 0 {CONTENT_W} 820" aria-hidden="true">'
        + "".join(f'<path d="{path}"/>' for path in connector_paths)
        + "</svg>"
    )
    root_label = _optional_layer_text(
        content.get("root_label"),
        class_name="diagram-kicker",
        attrs='data-edit-layer="text"',
    )
    root = f'''<div class="el diagram-node org-root" data-edit-composite="org-root" style="left:604px;top:182px;width:520px;height:160px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>
      {root_label}
      <b class="org-title" data-edit-layer="text">{esc(root_title)}</b>
      <span class="org-body" data-edit-layer="text">{esc(root_body)}</span>
    </div>'''
    children = []
    for index, (left, item) in enumerate(zip(child_lefts, content["children"]), 1):
        title, body, metric = item
        children.append(
            f'''<div class="el diagram-node org-child" data-edit-composite="org-child-{index}" style="left:{left}px;top:470px;width:{child_width}px;height:{child_height}px">
              <div class="diagram-node-bg" data-edit-layer="background"></div>
              <span class="diagram-no" data-edit-layer="metric">{index:02d}</span>
              <b class="org-title" data-edit-layer="text">{esc(title)}</b>
              <span class="org-body" data-edit-layer="text">{esc(body)}</span>
              <strong class="org-metric" data-edit-layer="metric">{esc(metric)}</strong>
            </div>'''
        )
    note = f'''<div class="el diagram-node org-note" data-edit-composite="org-note" style="left:250px;top:700px;width:1228px;height:84px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>
      <span data-edit-layer="text" data-edit-position="flow">{esc(content['note'])}</span>
    </div>'''
    return _frame(content, _centered_title(content["title"]) + connectors + root + "".join(children) + note)


def _pyramid(content: dict[str, Any]) -> str:
    widths = [560, 700, 840, 980, 1160]
    layer_height = 116
    top = 160
    layers = []
    for index, (item, width) in enumerate(zip(content["items"], widths)):
        no, title, body = item
        left = (CONTENT_W - width) / 2
        layers.append(
            f'''<div class="el diagram-node pyramid-layer" data-edit-composite="pyramid-layer-{index + 1}" style="left:{left:.1f}px;top:{top + index * 120}px;width:{width}px;height:{layer_height}px">
              <div class="diagram-node-bg pyramid-bg" data-edit-layer="background"></div>
              <span class="pyramid-no" data-edit-layer="metric">{esc(no)}</span>
              <b class="pyramid-title" data-edit-layer="text">{esc(title)}</b>
              <span class="pyramid-body" data-edit-layer="text">{esc(body)}</span>
            </div>'''
        )
    return _frame(content, _centered_title(content["title"]) + "".join(layers))


def _comparison_header(side: str, content: tuple[str, str, str, list[str]], left: int) -> str:
    """Render a state header as a real vertical text stack, not fixed offsets."""
    label, title, subtitle, _ = content
    return f'''<div class="el diagram-node compare-state-header {side}" data-edit-composite="{side}-state-header" style="left:{left}px;top:0;width:805px;height:238px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>
      <span class="compare-kicker" data-edit-layer="text" data-edit-position="flow">{esc(label)}</span>
      <strong class="compare-title" data-edit-layer="text" data-edit-position="flow">{esc(title)}</strong>
      <span class="compare-subtitle" data-edit-layer="text" data-edit-position="flow">{esc(subtitle)}</span>
    </div>'''


def _comparison_pair_row(index: int, before_item: str, after_item: str, top: int) -> str:
    """One causal row connects a specific before state to its after state."""
    return f'''<div class="el diagram-node compare-pair-row" data-edit-composite="comparison-transition-{index}" data-comparison-pair-index="{index}" style="left:0;top:{top}px;width:1728px;height:142px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>
      <span class="compare-pair-index" data-edit-layer="metric">{index:02d}</span>
      <b class="compare-pair-before" data-edit-layer="text" data-edit-position="flow">{esc(before_item)}</b>
      <span class="compare-pair-arrow" data-edit-layer="icon">→</span>
      <b class="compare-pair-after" data-edit-layer="text" data-edit-position="flow">{esc(after_item)}</b>
    </div>'''


def _before_after(content: dict[str, Any]) -> str:
    before_items = list(content["before"][3])
    after_items = list(content["after"][3])
    if len(before_items) != len(after_items):
        raise ValueError(
            "before-after requires the same number of before and after items for paired causal rows"
        )
    if not 2 <= len(before_items) <= 4:
        raise ValueError(
            "before-after supports two to four paired causal rows; split or choose another comparison Layout"
        )
    row_height = 142
    row_gap = 14
    rows = "".join(
        _comparison_pair_row(
            index,
            before_item,
            after_item,
            258 + (index - 1) * (row_height + row_gap),
        )
        for index, (before_item, after_item) in enumerate(zip(before_items, after_items), 1)
    )
    return _frame(
        content,
        _comparison_header("before", content["before"], 0)
        + _comparison_header("after", content["after"], 923)
        + rows,
    )


def _comparison_table(content: dict[str, Any]) -> str:
    columns = content["columns"]
    rows = [columns, *content["rows"]]
    column_widths = [430, 400, 400, 498]
    row_heights = [76, 82, 82, 82, 82]
    cells = []
    top = 0
    for row_index, row in enumerate(rows):
        left = 0
        for column_index, (value, width) in enumerate(zip(row, column_widths)):
            classes = ["compare-table-cell"]
            if row_index == 0:
                classes.append("header")
            if column_index == 3:
                classes.append("recommended")
            cells.append(
                f'<span class="{" ".join(classes)}" data-edit-layer="text" '
                f'style="left:{left}px;top:{top}px;width:{width}px;height:{row_heights[row_index]}px">{esc(value)}</span>'
            )
            left += width
        top += row_heights[row_index]
    table = f'''<div class="el diagram-node compare-table" data-edit-composite="comparison-table" style="left:0;top:200px;width:1728px;height:404px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>{''.join(cells)}
    </div>'''
    note = f'''<div class="el diagram-node compare-note" data-edit-composite="comparison-note" style="left:0;top:650px;width:1728px;height:92px">
      <div class="diagram-node-bg" data-edit-layer="background"></div><span data-edit-layer="text" data-edit-position="flow">{esc(content['note'])}</span>
    </div>'''
    return _frame(
        content,
        _flow_header(
            content["title"],
            content["subtitle"],
            title_centered=True,
            subtitle_max_width=1600,
        )
        + _flow_follow(table + note),
    )


def _matrix(content: dict[str, Any]) -> str:
    left_axis, right_axis, bottom_axis, top_axis = content["axes"]
    # Keep a deliberate title-to-matrix margin, then let the shared browser
    # materialization pass recenter the visible title + body union as one unit.
    body_offset_y = 40
    visual = f'''<svg class="el diagram-connectors matrix-axes" data-edit-kind="visual" style="left:214px;top:{150 + body_offset_y}px;width:1300px;height:600px" viewBox="0 0 1300 600" aria-hidden="true">
      <defs>{_user_space_arrow_marker("matrix-arrow", orient="auto-start-reverse")}</defs>
      <path d="M 20 300 H 1280" marker-start="url(#matrix-arrow)" marker-end="url(#matrix-arrow)"/>
      <path d="M 650 580 V 20" marker-start="url(#matrix-arrow)" marker-end="url(#matrix-arrow)"/>
    </svg>'''
    labels = (
        f'<span class="el matrix-axis left" data-edit-kind="text" data-edit-fit="container" style="left:16px;top:{424 + body_offset_y}px;width:180px;height:52px">{esc(left_axis)}</span>'
        f'<span class="el matrix-axis right" data-edit-kind="text" data-edit-fit="container" style="left:1532px;top:{424 + body_offset_y}px;width:180px;height:52px">{esc(right_axis)}</span>'
        f'<span class="el matrix-axis bottom" data-edit-kind="text" data-edit-fit="container" style="left:774px;top:{764 + body_offset_y}px;width:180px;height:52px">{esc(bottom_axis)}</span>'
        f'<span class="el matrix-axis top" data-edit-kind="text" data-edit-fit="container" style="left:774px;top:{84 + body_offset_y}px;width:180px;height:52px">{esc(top_axis)}</span>'
    )
    positions = [
        (300, 170 + body_offset_y),
        (928, 170 + body_offset_y),
        (300, 490 + body_offset_y),
        (928, 490 + body_offset_y),
    ]
    cards = []
    for index, ((title, body), (left, top)) in enumerate(zip(content["quadrants"], positions), 1):
        cards.append(
            f'''<div class="el diagram-node matrix-card q{index}" data-edit-composite="matrix-quadrant-{index}" style="left:{left}px;top:{top}px;width:500px;height:260px">
              <div class="diagram-node-bg" data-edit-layer="background"></div>
              <span class="diagram-no" data-edit-layer="metric">Q{index}</span>
              <b data-edit-layer="text">{esc(title)}</b><p data-edit-layer="text">{esc(body)}</p>
            </div>'''
        )
    return _frame(content, _centered_title(content["title"]) + visual + labels + "".join(cards))


def _pricing(content: dict[str, Any]) -> str:
    cards = []
    positions = [80, 624, 1168]
    for index, (left, tier) in enumerate(zip(positions, content["tiers"]), 1):
        name, price, subtitle, features, cta = tier
        feature_markup = "".join(
            f'<li><span data-edit-layer="icon">✓</span><b data-edit-layer="text">{esc(feature)}</b></li>'
            for feature in features
        )
        cards.append(
            f'''<div class="el diagram-node price-card tier-{index}" data-edit-composite="pricing-tier-{index}" style="left:{left}px;top:145px;width:480px;height:620px">
              <div class="diagram-node-bg" data-edit-layer="background"></div>
              <span class="price-name" data-edit-layer="text">{esc(name)}</span>
              <strong class="price-value" data-edit-layer="metric">{esc(price)}</strong>
              <span class="price-subtitle" data-edit-layer="text">{esc(subtitle)}</span>
              <ul>{feature_markup}</ul>
              <b class="price-cta" data-edit-layer="text">{esc(cta)}</b>
            </div>'''
        )
    return _frame(content, _title(content["title"]) + "".join(cards))


def _split_panel(side: str, content: tuple[str, str, list[str]], left: int) -> str:
    label, statement, items = content
    list_top = 250 if len(items) <= 5 else 208
    row_height = 88 if len(items) <= 5 else max(58, (610 - list_top - 10) / len(items))
    rows = "".join(
        f'<li><span data-edit-layer="metric">{index:02d}</span><b data-edit-layer="text">{esc(item)}</b></li>'
        for index, item in enumerate(items, 1)
    )
    return f'''<div class="el diagram-node split-panel {side}" data-edit-composite="split-{side}" data-row-count="{len(items)}" style="left:{left}px;top:150px;width:805px;height:610px;--split-list-top:{list_top}px;--split-row-height:{row_height:.3f}px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>
      <span class="split-label" data-edit-layer="text">{esc(label)}</span>
      <strong data-edit-layer="text">{esc(statement)}</strong>
      <ul>{rows}</ul>
    </div>'''


def _split_comparison(content: dict[str, Any]) -> str:
    divider = '<div class="el split-divider" data-edit-kind="visual" style="left:854px;top:150px;width:20px;height:610px"></div>'
    return _frame(
        content,
        _title(content["title"])
        + _split_panel("left", content["left"], 0)
        + divider
        + _split_panel("right", content["right"], 923),
    )


INFOGRAPHIC_STAGE_BOUNDS = (0.0, 142.0, float(CONTENT_W), 704.0)
INFOGRAPHIC_SCENE_TYPES = {"connector", "module", "rule", "text"}
INFOGRAPHIC_MODULE_SHAPES = {"circle", "cut", "pill", "rounded", "square"}
INFOGRAPHIC_MODULE_SURFACES = {"accent", "dark", "outline", "soft", "surface", "transparent"}
INFOGRAPHIC_TEXT_TONES = {"accent", "accent-text", "inverse", "muted", "surface-muted", "surface-text", "text"}
INFOGRAPHIC_PATH_RE = re.compile(r"^[MmLlHhVvCcSsQqTtAaZz0-9.,+\-\s]+$")


def _infographic_number(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Infographic scene {label} must be numeric") from error
    if not math.isfinite(number):
        raise ValueError(f"Infographic scene {label} must be finite")
    return number


def _infographic_geometry(spec: dict[str, Any], object_id: str) -> tuple[float, float, float, float]:
    x = _infographic_number(spec.get("x"), f"{object_id}.x")
    y = _infographic_number(spec.get("y"), f"{object_id}.y")
    width = _infographic_number(spec.get("w"), f"{object_id}.w")
    height = _infographic_number(spec.get("h"), f"{object_id}.h")
    if width <= 0 or height <= 0:
        raise ValueError(f"Infographic scene {object_id} must have positive width and height")
    stage_x, stage_y, stage_width, stage_height = INFOGRAPHIC_STAGE_BOUNDS
    epsilon = 0.5
    if (
        x < stage_x - epsilon
        or y < stage_y - epsilon
        or x + width > stage_x + stage_width + epsilon
        or y + height > stage_y + stage_height + epsilon
    ):
        raise ValueError(
            f"Infographic scene {object_id} is outside the open stage: "
            f"({x}, {y}, {width}, {height})"
        )
    return x, y, width, height


def _infographic_inline_geometry(x: float, y: float, width: float, height: float) -> str:
    return f"left:{x:.1f}px;top:{y:.1f}px;width:{width:.1f}px;height:{height:.1f}px"


def _infographic_text_layer(layer: dict[str, Any], module_id: str, index: int, width: float, height: float) -> str:
    layer_id = str(layer.get("id") or f"layer-{index}")
    kind = str(layer.get("kind") or "text")
    if kind not in {"label", "metric", "text"}:
        raise ValueError(f"Infographic module {module_id} has unsupported layer kind: {kind}")
    text = layer.get("text")
    if text is None or not str(text).strip():
        raise ValueError(f"Infographic module {module_id}.{layer_id} must contain text")
    x = _infographic_number(layer.get("x"), f"{module_id}.{layer_id}.x")
    y = _infographic_number(layer.get("y"), f"{module_id}.{layer_id}.y")
    layer_width = _infographic_number(layer.get("w"), f"{module_id}.{layer_id}.w")
    layer_height = _infographic_number(layer.get("h"), f"{module_id}.{layer_id}.h")
    if x < 0 or y < 0 or layer_width <= 0 or layer_height <= 0:
        raise ValueError(f"Infographic module {module_id}.{layer_id} has invalid geometry")
    if x + layer_width > width + 0.5 or y + layer_height > height + 0.5:
        raise ValueError(f"Infographic module {module_id}.{layer_id} escapes its semantic module")
    font_size = _infographic_number(layer.get("font_size", GENERATED_TEXT_MIN_PX), f"{module_id}.{layer_id}.font_size")
    if font_size < GENERATED_TEXT_MIN_PX:
        raise ValueError(
            f"Infographic module {module_id}.{layer_id} is below {GENERATED_TEXT_MIN_PX}px"
        )
    weight = int(_infographic_number(layer.get("weight", 700), f"{module_id}.{layer_id}.weight"))
    line_height = _infographic_number(layer.get("line_height", 1.08), f"{module_id}.{layer_id}.line_height")
    align = str(layer.get("align") or "left")
    if align not in {"center", "left", "right"}:
        raise ValueError(f"Infographic module {module_id}.{layer_id} has unsupported alignment: {align}")
    tone = str(layer.get("tone") or "surface-text")
    if tone not in INFOGRAPHIC_TEXT_TONES:
        raise ValueError(f"Infographic module {module_id}.{layer_id} has unsupported tone: {tone}")
    edit_kind = "metric" if kind == "metric" else "text"
    return (
        f'<span class="infographic-scene-layer kind-{kind} tone-{tone}" '
        f'data-edit-layer="{edit_kind}" data-scene-layer-id="{html.escape(layer_id, quote=True)}" '
        f'style="{_infographic_inline_geometry(x, y, layer_width, layer_height)};'
        f'font-size:{font_size:.1f}px;font-weight:{weight};line-height:{line_height:.3f};text-align:{align}">'
        f'{esc(text)}</span>'
    )


def _infographic_scene_module(spec: dict[str, Any], object_id: str) -> str:
    x, y, width, height = _infographic_geometry(spec, object_id)
    shape = str(spec.get("shape") or "rounded")
    surface = str(spec.get("surface") or "surface")
    if shape not in INFOGRAPHIC_MODULE_SHAPES:
        raise ValueError(f"Infographic module {object_id} has unsupported shape: {shape}")
    if surface not in INFOGRAPHIC_MODULE_SURFACES:
        raise ValueError(f"Infographic module {object_id} has unsupported surface: {surface}")
    layers = spec.get("layers")
    if not isinstance(layers, list) or not layers:
        raise ValueError(f"Infographic module {object_id} must contain editable layers")
    layer_ids = [str(layer.get("id") or f"layer-{index}") for index, layer in enumerate(layers, 1)]
    if len(layer_ids) != len(set(layer_ids)):
        raise ValueError(f"Infographic module {object_id} contains duplicate layer ids")
    layer_markup = "".join(
        _infographic_text_layer(layer, object_id, index, width, height)
        for index, layer in enumerate(layers, 1)
    )
    surface_role = ' data-visual-surface-role="accent"' if surface == "accent" else ""
    return (
        f'<div class="el diagram-node infographic-scene-module shape-{shape} surface-{surface}" '
        f'data-edit-composite="scene-{html.escape(object_id, quote=True)}" '
        f'data-scene-object-id="{html.escape(object_id, quote=True)}"{surface_role} '
        f'style="{_infographic_inline_geometry(x, y, width, height)}">'
        f'<div class="diagram-node-bg infographic-scene-module-bg" data-edit-layer="background"></div>'
        f'{layer_markup}</div>'
    )


def _infographic_scene_connector(spec: dict[str, Any], object_id: str, scene_id: str) -> str:
    x, y, width, height = _infographic_geometry(spec, object_id)
    paths = spec.get("paths")
    if not isinstance(paths, list) or not paths:
        raise ValueError(f"Infographic connector {object_id} must contain SVG paths")
    safe_paths = []
    for path in paths:
        path_value = str(path).strip()
        if not path_value or not INFOGRAPHIC_PATH_RE.fullmatch(path_value):
            raise ValueError(f"Infographic connector {object_id} contains an invalid SVG path")
        safe_paths.append(path_value)
    tone = str(spec.get("tone") or "accent")
    if tone not in {"accent", "muted", "support"}:
        raise ValueError(f"Infographic connector {object_id} has unsupported tone: {tone}")
    dashed = " is-dashed" if spec.get("dashed") else ""
    arrow = bool(spec.get("arrow", True))
    marker_id = re.sub(r"[^A-Za-z0-9_-]", "-", f"scene-{scene_id}-{object_id}-arrow")
    marker = _user_space_arrow_marker(marker_id, size=18) if arrow else ""
    marker_attr = f' marker-end="url(#{marker_id})"' if arrow else ""
    path_markup = "".join(f'<path d="{path}"{marker_attr}/>' for path in safe_paths)
    return (
        f'<svg class="el infographic-scene-connector tone-{tone}{dashed}" data-edit-kind="visual" '
        f'data-scene-object-id="{html.escape(object_id, quote=True)}" '
        f'style="{_infographic_inline_geometry(x, y, width, height)}" '
        f'viewBox="0 0 {width:.1f} {height:.1f}" aria-label="CONNECTOR {html.escape(object_id, quote=True)}">'
        f'<defs>{marker}</defs>{path_markup}</svg>'
    )


def _infographic_scene_rule(spec: dict[str, Any], object_id: str) -> str:
    x, y, width, height = _infographic_geometry(spec, object_id)
    tone = str(spec.get("tone") or "muted")
    if tone not in {"accent", "muted", "support"}:
        raise ValueError(f"Infographic rule {object_id} has unsupported tone: {tone}")
    return (
        f'<div class="el infographic-scene-rule tone-{tone}" data-edit-kind="visual" '
        f'data-scene-object-id="{html.escape(object_id, quote=True)}" '
        f'style="{_infographic_inline_geometry(x, y, width, height)}"></div>'
    )


def _infographic_scene_text(spec: dict[str, Any], object_id: str) -> str:
    x, y, width, height = _infographic_geometry(spec, object_id)
    text = spec.get("text")
    if text is None or not str(text).strip():
        raise ValueError(f"Infographic text {object_id} must contain text")
    font_size = _infographic_number(spec.get("font_size", GENERATED_TEXT_MIN_PX), f"{object_id}.font_size")
    if font_size < GENERATED_TEXT_MIN_PX:
        raise ValueError(f"Infographic text {object_id} is below {GENERATED_TEXT_MIN_PX}px")
    weight = int(_infographic_number(spec.get("weight", 700), f"{object_id}.weight"))
    line_height = _infographic_number(spec.get("line_height", 1.08), f"{object_id}.line_height")
    align = str(spec.get("align") or "left")
    tone = str(spec.get("tone") or "text")
    if align not in {"center", "left", "right"}:
        raise ValueError(f"Infographic text {object_id} has unsupported alignment: {align}")
    if tone not in INFOGRAPHIC_TEXT_TONES:
        raise ValueError(f"Infographic text {object_id} has unsupported tone: {tone}")
    anchor_x = x if align == "left" else x + width / 2 if align == "center" else x + width
    translate = "" if align == "left" else "translate:-50% 0;" if align == "center" else "translate:-100% 0;"
    return (
        f'<div class="el infographic-scene-text tone-{tone}" data-edit-kind="text" data-edit-fit="text" '
        f'data-scene-object-id="{html.escape(object_id, quote=True)}" '
        f'style="left:{anchor_x:.1f}px;top:{y:.1f}px;width:max-content;height:auto;max-width:{width:.1f}px;'
        f'{translate}font-size:{font_size:.1f}px;font-weight:{weight};line-height:{line_height:.3f};text-align:{align}">'
        f'{esc(text)}</div>'
    )


def _infographic_stage(content: dict[str, Any]) -> str:
    required = {
        "title", "composition_intent", "reading_path", "signature_composition",
        "ordinary_grid_loss", "scene",
    }
    missing = sorted(required - set(content))
    if missing:
        raise ValueError(f"infographic-stage content is missing: {missing}")
    scene = content["scene"]
    if not isinstance(scene, dict):
        raise ValueError("infographic-stage scene must be an object")
    scene_id = str(scene.get("id") or "authored-scene")
    objects = scene.get("objects")
    if not isinstance(objects, list) or not objects:
        raise ValueError("infographic-stage scene must contain authored objects")
    object_ids = [str(item.get("id") or "") for item in objects if isinstance(item, dict)]
    if len(object_ids) != len(objects) or any(not value for value in object_ids):
        raise ValueError("Every infographic-stage object must have a non-empty id")
    if len(object_ids) != len(set(object_ids)):
        raise ValueError("infographic-stage object ids must be unique")

    connectors: list[str] = []
    foreground: list[str] = []
    for spec, object_id in zip(objects, object_ids):
        object_type = str(spec.get("type") or "")
        if object_type not in INFOGRAPHIC_SCENE_TYPES:
            raise ValueError(f"Infographic scene {object_id} has unsupported type: {object_type}")
        if object_type == "connector":
            connectors.append(_infographic_scene_connector(spec, object_id, scene_id))
        elif object_type == "rule":
            connectors.append(_infographic_scene_rule(spec, object_id))
        elif object_type == "module":
            foreground.append(_infographic_scene_module(spec, object_id))
        else:
            foreground.append(_infographic_scene_text(spec, object_id))

    subtitle = ""
    if content.get("subtitle"):
        subtitle = (
            f'<div class="el infographic-stage-subtitle" data-edit-kind="text" data-edit-fit="text" '
            f'data-layout-slot="subtitle" style="left:0;top:82px;width:max-content;height:auto;max-width:1660px">'
            f'{esc(content["subtitle"])}</div>'
        )
    stage_meta = (
        f'<div class="infographic-stage-meta" data-edit-layout-only="true" '
        f'data-layout-slot="infographic-stage" data-scene-id="{html.escape(scene_id, quote=True)}" '
        f'data-composition-intent="{html.escape(str(content["composition_intent"]), quote=True)}" '
        f'data-reading-path="{html.escape(str(content["reading_path"]), quote=True)}" '
        f'data-signature-composition="{html.escape(str(content["signature_composition"]), quote=True)}" '
        f'data-ordinary-grid-loss="{html.escape(str(content["ordinary_grid_loss"]), quote=True)}"></div>'
    )
    return _frame(
        content,
        _title(content["title"])
        + subtitle
        + stage_meta
        + "".join(connectors)
        + "".join(foreground),
    )


def _swot(content: dict[str, Any]) -> str:
    positions = [(0, 180), (884, 180), (0, 490), (884, 490)]
    cards = []
    for index, ((letter, label, items), (left, top)) in enumerate(zip(content["quadrants"], positions), 1):
        rows = "".join(f'<li data-edit-layer="text">{esc(item)}</li>' for item in items)
        cards.append(
            f'''<div class="el diagram-node swot-card swot-{letter.lower()}" data-edit-composite="swot-{letter.lower()}" style="left:{left}px;top:{top}px;width:844px;height:250px">
              <div class="diagram-node-bg" data-edit-layer="background"></div>
              <span class="swot-letter" data-edit-layer="metric">{esc(letter)}</span>
              <b class="swot-label" data-edit-layer="text">{esc(label)}</b><ul>{rows}</ul>
            </div>'''
        )
    return _frame(
        content,
        _flow_header(content["title"], content["subtitle"], subtitle_max_width=1500)
        + _flow_follow("".join(cards)),
    )


def _dashboard_overview(content: dict[str, Any]) -> str:
    kpis = list(content["kpis"])
    if not 2 <= len(kpis) <= 4:
        raise ValueError(
            "dashboard-overview supports two to four KPI summaries at 36px; "
            "route denser content to another compatible Layout"
        )
    item_width = CONTENT_W / len(kpis)
    kpi_items = []
    for index, (label, value, delta) in enumerate(kpis):
        kpi_items.append(
            f'''<div class="metric-strip-item item-{index + 1}" style="left:{index * item_width:.3f}px;top:0;width:{item_width:.3f}px;height:164px">
              <span class="metric-strip-label" data-edit-layer="text" data-edit-position="absolute">{esc(label)}</span><b class="metric-strip-value" data-edit-layer="metric" data-edit-position="absolute">{esc(value)}</b><strong class="metric-strip-delta" data-edit-layer="text" data-edit-position="absolute">{esc(delta)}</strong>
            </div>'''
        )
    kpi_strip = f'''<div class="el diagram-node metric-kpi-strip" data-edit-composite="dashboard-kpi-strip" style="left:0;top:154px;width:1728px;height:164px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>{''.join(kpi_items)}
    </div>'''

    chart = content["chart"]
    chart_svg = render_dashboard_combo_chart_svg(chart["labels"], chart["bars"])
    labels = "".join(
        f'<span data-edit-layer="text" data-edit-position="flow">{esc(label)}</span>'
        for label in chart["labels"]
    )
    chart_kicker = _optional_layer_text(
        chart.get("kicker"),
        class_name="metric-panel-kicker",
        attrs='data-edit-layer="text" data-edit-position="flow"',
    )
    chart_panel = f'''<div class="el diagram-node metric-chart-panel" data-edit-composite="dashboard-chart" data-chart-renderer="python-matplotlib-svg" style="left:0;top:342px;width:1060px;height:442px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>
      {chart_kicker}
      <b class="metric-panel-title" data-edit-layer="text" data-edit-position="flow">{esc(chart['title'])}</b>
      <strong class="metric-panel-value" data-edit-layer="metric" data-edit-position="absolute">{esc(chart['metric'])}</strong>
      {chart_svg}<div class="metric-chart-labels">{labels}</div>
    </div>'''

    kicker, title, bullets = content["insight"]
    if len(bullets) != 3:
        raise ValueError(
            "dashboard-overview requires exactly three insight rows at 36px; "
            "route denser content to another compatible Layout"
        )
    # The insight panel is a fixed 442px box, so an over-long conclusion silently
    # squeezes the three rows until their text overlaps. Fail closed instead.
    insight_budget = 442 - (22 + 14) - 36 - 8 - 14
    title_height = _wrapped_line_count(title, 568, 36) * 36 * 1.15
    rows_height = 3 * max(
        _wrapped_line_count(bullet, 496, 36) for bullet in bullets
    ) * 36 * 1.22
    if title_height + rows_height > insight_budget:
        raise ValueError(
            "dashboard-overview insight panel cannot fit this conclusion and its "
            f"three rows at 36px (needs {title_height + rows_height:.0f}px of "
            f"{insight_budget}px); shorten the conclusion or the rows"
        )
    bullet_markup = "".join(
        f'<li><span data-edit-layer="metric" data-edit-position="absolute">{index:02d}</span><b data-edit-layer="text" data-edit-position="flow">{esc(item)}</b></li>'
        for index, item in enumerate(bullets, 1)
    )
    insight = f'''<div class="el diagram-node metric-insight" data-edit-composite="dashboard-insight" style="left:1100px;top:342px;width:628px;height:442px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>
      <span class="metric-panel-kicker" data-edit-layer="text" data-edit-position="flow">{esc(kicker)}</span>
      <b class="metric-insight-title" data-edit-layer="text" data-edit-position="flow">{esc(title)}</b><ul>{bullet_markup}</ul>
    </div>'''
    footnote = f'<div class="el metric-footnote dashboard-footnote" data-edit-kind="text" data-edit-fit="text" style="left:0;top:806px;width:max-content;height:auto;max-width:1728px">{esc(content["footnote"])}</div>'
    return _frame(
        content,
        _flow_header(
            content["title"],
            content["subtitle"],
            title_max_width=1600,
            subtitle_max_width=1600,
            flow_id="dashboard-header",
        )
        + _flow_follow(kpi_strip + chart_panel + insight + footnote, flow_id="dashboard-header", gap=20),
    )


def _kpi_scorecards(content: dict[str, Any]) -> str:
    card_items = list(content["cards"])
    if not 3 <= len(card_items) <= 6:
        raise ValueError(
            "kpi-scorecards supports three to six 36px-safe cards; "
            "route other item counts to another compatible Layout"
        )
    gap = 24
    card_width = (CONTENT_W - gap * (len(card_items) - 1)) / len(card_items)
    cards = []
    for index, (value, label, note, delta) in enumerate(card_items):
        left = index * (card_width + gap)
        cards.append(
            f'''<div class="el diagram-node metric-kpi-card card-{index + 1} count-{len(card_items)}" data-edit-composite="kpi-card-{index + 1}" style="left:{left:.3f}px;top:176px;width:{card_width:.3f}px;height:430px">
              <div class="diagram-node-bg" data-edit-layer="background"></div>
              <strong class="metric-card-value" data-edit-layer="metric" data-edit-position="absolute">{esc(value)}</strong>
              <b class="metric-card-label" data-edit-layer="text" data-edit-position="absolute">{esc(label)}</b>
              <span class="metric-card-note" data-edit-layer="text" data-edit-position="absolute">{esc(note)}</span>
              <em class="metric-card-delta" data-edit-layer="metric" data-edit-position="absolute">{esc(delta)}</em>
            </div>'''
        )
    takeaway_text = str(content.get("takeaway") or "").strip()
    takeaway = ""
    if takeaway_text:
        takeaway_length = _non_whitespace_character_count(takeaway_text)
        if not KPI_TAKEAWAY_MIN_CHARS <= takeaway_length <= KPI_TAKEAWAY_MAX_CHARS:
            raise ValueError(
                "kpi-scorecards optional takeaway must contain "
                f"{KPI_TAKEAWAY_MIN_CHARS} to {KPI_TAKEAWAY_MAX_CHARS} "
                "non-whitespace characters when present; omit it when no "
                "qualified summary is available"
            )
        takeaway = f'''<div class="el diagram-node metric-takeaway" data-edit-composite="metric-takeaway" style="left:0;top:634px;width:1728px;height:134px">
          <div class="diagram-node-bg" data-edit-layer="background"></div><span data-edit-layer="text" data-edit-position="flow">{esc(takeaway_text)}</span>
        </div>'''
    return _frame(
        content,
        _flow_header(content["title"], None, title_centered=True, flow_id="kpi-header")
        + _flow_follow("".join(cards) + takeaway, flow_id="kpi-header", gap=20),
    )


def _stats_three_row(content: dict[str, Any]) -> str:
    stats = list(content["stats"])
    gap = 30
    card_width = (CONTENT_W - gap * (len(stats) - 1)) / len(stats)
    cards = []
    for index, (value, label, note) in enumerate(stats):
        cards.append(
            f'''<div class="el diagram-node metric-stat-card stat-{index + 1}" data-edit-composite="hero-stat-{index + 1}" style="left:{index * (card_width + gap):.3f}px;top:150px;width:{card_width:.3f}px;height:500px">
              <div class="diagram-node-bg" data-edit-layer="background"></div>
              <span class="metric-stat-index" data-edit-layer="metric">0{index + 1}</span>
              <strong class="metric-stat-value" data-edit-layer="metric">{esc(value)}</strong>
              <b class="metric-stat-label" data-edit-layer="text">{esc(label)}</b>
              <span class="metric-stat-note" data-edit-layer="text">{esc(note)}</span>
            </div>'''
        )
    eyebrow = f'<div class="el metric-eyebrow" data-edit-kind="text" data-edit-fit="text" style="left:0;top:28px;width:max-content;height:auto;max-width:1500px">{esc(content["eyebrow"])}</div>'
    footnote = f'<div class="el metric-footnote" data-edit-kind="text" data-edit-fit="text" style="left:0;top:710px;width:max-content;height:auto;max-width:1728px">{esc(content["footnote"])}</div>'
    return _frame(content, eyebrow + "".join(cards) + footnote)


def _closing_photo_overlay_contact(content: dict[str, Any]) -> str:
    title_text = str(content["title"])
    title_length = len("".join(title_text.split()))
    title_size = 92 if title_length <= 12 else 78 if title_length <= 18 else 64 if title_length <= 26 else 54
    title_markup = _preferred_headline_markup(title_text)
    title_parts = [part for part in title_text.splitlines() if part.strip()] or [title_text]
    estimated_title_lines = sum(max(1, math.ceil(len("".join(part.split())) / 8)) for part in title_parts)
    contact_top = 520 - 44 - 54 * len(content.get("contact") or [])
    body_top = max(272, 93 + estimated_title_lines * title_size * 1.04 + 24)
    if content.get("contact"):
        body_top = min(body_top, contact_top - 96)
    else:
        body_top = min(body_top, 390)
    title_style = (
        f'left:50px;right:46px;top:93px;font-size:{title_size}px;'
        'line-height:1.04;letter-spacing:-.045em'
    )
    body_style = f'left:52px;right:56px;top:{round(body_top)}px'
    contact_rows = "".join(
        f'<li><span data-edit-layer="text">{esc(label)}</span><b data-edit-layer="text">{esc(value)}</b></li>'
        for label, value in content["contact"]
    )
    social_rows = "".join(
        f'''<div class="closing-social-row row-{index + 1}">
          <b data-edit-layer="icon">{esc(icon)}</b><span data-edit-layer="text">{esc(label)}</span>
        </div>'''
        for index, (icon, label) in enumerate(content["social"])
    )
    social_panel = (
        f'''<div class="el diagram-node closing-social-panel" data-edit-composite="closing-social" style="left:940px;top:278px;width:250px;height:600px">
        <div class="diagram-node-bg" data-edit-layer="background"></div>{social_rows}
      </div>'''
        if social_rows
        else ""
    )
    kicker = _optional_layer_text(
        content.get("kicker"),
        class_name="closing-kicker",
        attrs='data-edit-layer="text"',
    )
    density, _ = density_profile(content)
    return f'''<div class="prod-frame closing-frame" data-density="{density}" data-full-bleed-media="true" style="left:-96px;top:-96px;width:1920px;height:1080px">
      <div class="el closing-photo-field" data-edit-kind="visual" style="left:0;top:0;width:1920px;height:1080px">
        <div class="closing-photo-glow"></div><div class="closing-photo-subject"><i></i><i></i><i></i></div><div class="closing-photo-grain"></div>
      </div>
      <div class="el diagram-node closing-copy-panel" data-edit-composite="closing-copy" style="left:160px;top:278px;width:780px;height:600px">
        <div class="diagram-node-bg" data-edit-layer="background"></div>
        {kicker}
        <strong class="closing-title" data-edit-layer="text" style="{title_style}">{title_markup}</strong>
        <span class="closing-body" data-edit-layer="text" style="{body_style}">{esc(content['body'])}</span><ul>{contact_rows}</ul>
      </div>
      {social_panel}
    </div>'''


def _highlight_callout(content: dict[str, Any]) -> str:
    chart_title, values, labels = content["chart"]
    focus_count = min(len(content["callouts"]), max(0, len(values) - 1))
    if focus_count <= 1:
        focus_indices = (len(values) - 1,) if values else ()
    else:
        focus_indices = tuple(
            round(1 + index * (len(values) - 2) / (focus_count - 1))
            for index in range(focus_count)
        )
    chart_svg = render_highlight_line_chart_svg(
        labels,
        values,
        focus_indices=focus_indices,
    )
    label_markup = "".join(
        f'<span data-edit-layer="text" data-edit-position="flow">{esc(label)}</span>'
        for label in labels
    )
    chart_kicker = _optional_layer_text(
        content.get("chart_kicker"),
        class_name="statement-chart-kicker",
        attrs='data-edit-layer="text"',
    )
    chart = f'''<div class="el diagram-node statement-chart-panel" data-edit-composite="highlight-main-visual" data-chart-renderer="python-matplotlib-svg" style="left:0;top:135px;width:1080px;height:620px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>
      {chart_kicker}
      <b class="statement-chart-title" data-edit-layer="text">{esc(chart_title)}</b>
      <strong class="statement-chart-value" data-edit-layer="metric">{values[-1]}%</strong>
      {chart_svg}<div class="statement-chart-labels">{label_markup}</div>
    </div>'''
    callouts = []
    for index, (number, title, body) in enumerate(content["callouts"]):
        callouts.append(
            f'''<div class="el diagram-node statement-callout callout-{index + 1}" data-edit-composite="highlight-callout-{index + 1}" style="left:1120px;top:{135 + index * 210}px;width:608px;height:200px">
              <div class="diagram-node-bg" data-edit-layer="background"></div><span data-edit-layer="metric">{esc(number)}</span>
              <b data-edit-layer="text">{esc(title)}</b><p data-edit-layer="text">{esc(body)}</p>
            </div>'''
        )
    return _frame(content, _title(content["title"]) + chart + "".join(callouts))


def _quote_attribution_three(content: dict[str, Any]) -> str:
    cards = []
    for index, (quote, name, role) in enumerate(content["quotes"]):
        cards.append(
            f'''<div class="el diagram-node statement-quote-card quote-{index + 1}" data-edit-composite="quote-card-{index + 1}" style="left:{index * 586}px;top:150px;width:556px;height:570px">
              <div class="diagram-node-bg" data-edit-layer="background"></div><span class="statement-quote-mark" data-edit-layer="icon">“</span>
              <blockquote data-edit-layer="text">{esc(quote)}</blockquote><b data-edit-layer="text">{esc(name)}</b><em data-edit-layer="text">{esc(role)}</em>
            </div>'''
        )
    return _frame(content, _title(content["title"]) + "".join(cards))


def _quote_focus(content: dict[str, Any]) -> str:
    quote_text = str(content["quote"])
    compact = "\n" not in quote_text and len(quote_text) <= 24
    quote_top = 210 if compact else 190
    attribution_top = 405 if compact else 610
    text_left = 76
    rail_left = 34
    rail_top = quote_top - 18
    rail_height = attribution_top + 32 - rail_top
    quote = f'<div class="el statement-focus-quote" data-edit-kind="text" data-edit-fit="text" style="left:{text_left}px;top:{quote_top}px;width:max-content;height:auto;max-width:1250px">{esc(quote_text)}</div>'
    attribution = _optional_loose_text(
        content.get("attribution"),
        class_name="statement-focus-attribution",
        style=f"left:{text_left}px;top:{attribution_top}px;width:max-content;height:auto;max-width:1500px",
    )
    rail = f'''<div class="el statement-focus-rail" data-edit-kind="visual" data-edit-fit="container" data-overflow-intent="clip" style="left:{rail_left}px;top:{rail_top}px;width:4px;height:{rail_height}px">
      <div class="statement-focus-rail-line" data-edit-layer="visual"></div>
    </div>'''
    return _frame(content, quote + attribution + rail)


def _preferred_headline_markup(text: str) -> str:
    """Keep statement-layout line breaks on meaningful punctuation boundaries."""

    raw = str(text)
    candidates = [
        (abs((index + 1) - len(raw) / 2), index)
        for index, character in enumerate(raw)
        if character in "，；："
    ]
    if not candidates:
        return esc(raw)
    _, break_index = min(candidates)
    first_line = raw[: break_index + 1].rstrip()
    second_line = raw[break_index + 1 :].lstrip()
    if not first_line or not second_line:
        return esc(raw)
    return f"{esc(first_line)}<br>{esc(second_line)}"


def _balanced_chapter_title_markup(text: str) -> str:
    """Keep image-chapter titles balanced without changing their wording."""

    raw = str(text)
    compact = "".join(raw.split())
    if len(compact) <= 10:
        return esc(raw)
    candidates = [
        (abs((index + 1) - len(raw) / 2), index)
        for index, character in enumerate(raw)
        if character in "、，；："
    ]
    if not candidates:
        return esc(raw)
    _, break_index = min(candidates)
    first_line = raw[: break_index + 1].rstrip()
    second_line = raw[break_index + 1 :].lstrip()
    if not first_line or not second_line:
        return esc(raw)
    return f"{esc(first_line)}<br>{esc(second_line)}"


def _title_center(content: dict[str, Any]) -> str:
    density, fill_ratio = density_profile(content)
    height = round(CONTENT_H * fill_ratio)
    top = round((CONTENT_H - height) / 2)
    area = f'''<div class="title-flow-stack statement-center-area" data-edit-layout-only="true" data-auto-layout="vertical-stack" data-layout-flow-align="center" style="left:154px;top:100px;width:1420px;height:{height - 160}px;overflow:visible">
      <div class="el statement-center-headline" data-edit-kind="text" data-edit-fit="text" data-edit-align-contract="center-axis" style="width:max-content;height:auto;max-width:1420px">{_preferred_headline_markup(content['headline'])}</div>
      <div class="el statement-center-rule" data-edit-kind="visual" data-edit-align-contract="center-axis" style="width:180px;height:8px"></div>
      <div class="el statement-center-support" data-edit-kind="text" data-edit-fit="text" data-edit-align-contract="center-axis" style="width:max-content;height:auto;max-width:1120px">{esc(content['support'])}</div>
    </div>'''
    return f'<div class="prod-frame diagram-frame statement-center-frame" data-edit-layout-only="true" data-density="{density}" data-auto-fill-cap="soft" data-fill-ratio="{fill_ratio:.2f}" data-visual-balance="content-bounds" style="top:{top}px;height:{height}px;--prod-frame-height:{height}px">{area}</div>'


def _chapter_fullbleed_overlay_title(content: dict[str, Any]) -> str:
    label = _optional_layer_text(content.get("label"), attrs='data-edit-layer="text"')
    panel_label = _optional_layer_text(
        content.get("panel_label") or content.get("label"),
        attrs='data-edit-layer="text"',
    )
    return f'''<div class="prod-frame chapter-fullbleed-frame" data-density="low" data-full-bleed-media="true" style="left:-96px;top:-96px;width:1920px;height:1080px">
      <div class="el chapter-media-field chapter-media-full" data-edit-kind="visual" style="left:0;top:0;width:1920px;height:1080px"><i></i><i></i><i></i></div>
      <div class="el diagram-node chapter-overlay-title" data-edit-composite="chapter-title-overlay" style="left:96px;top:86px;width:614px;height:270px">
        <div class="diagram-node-bg" data-edit-layer="background"></div>{label}
        <b data-edit-layer="text">{esc(content['title'])}</b><em data-edit-layer="text">{esc(content['subtitle'])}</em>
      </div>
      <div class="el diagram-node chapter-number-panel" data-edit-composite="chapter-number-panel" style="left:1574px;top:0;width:346px;height:1080px">
        <div class="diagram-node-bg" data-edit-layer="background"></div>{panel_label}<b data-edit-layer="metric">{esc(content['number'])}</b>
      </div>
    </div>'''


def _chapter_number_background(content: dict[str, Any]) -> str:
    label = _optional_loose_text(
        content.get("label"),
        class_name="chapter-label",
        style="left:0;top:170px;width:max-content;height:auto;max-width:720px",
    )
    rule = '<div class="el chapter-title-rule" data-edit-kind="visual" style="left:0;top:245px;width:150px;height:8px"></div>'
    title = f'<div class="el chapter-left-title" data-edit-kind="text" data-edit-fit="text" style="left:0;top:292px;width:max-content;height:auto;max-width:1050px">{esc(content["title"])}</div>'
    subtitle = f'<div class="el chapter-left-subtitle" data-edit-kind="text" data-edit-fit="text" style="left:0;top:610px;width:max-content;height:auto;max-width:1080px">{esc(content["subtitle"])}</div>'
    number = f'<div class="el chapter-number-ghost" data-edit-kind="text" data-edit-fit="container" data-contrast-skip="true" data-overflow-intent="clip" style="left:890px;top:70px;width:max-content;height:auto;max-width:650px">{esc(content["number"])}</div>'
    return _frame(content, label + rule + title + subtitle + number)


def _chapter_opener(content: dict[str, Any]) -> str:
    label = _optional_loose_text(
        content.get("label"),
        class_name="chapter-label",
        style="left:80px;top:190px;width:max-content;height:auto;max-width:700px",
    )
    rule = '<div class="el chapter-title-rule" data-edit-kind="visual" style="left:80px;top:260px;width:130px;height:9px"></div>'
    title = f'<div class="el chapter-opener-title" data-edit-kind="text" data-edit-fit="text" style="left:80px;top:310px;width:max-content;height:auto;max-width:1120px">{esc(content["title"])}</div>'
    subtitle = f'<div class="el chapter-left-subtitle" data-edit-kind="text" data-edit-fit="text" style="left:82px;top:600px;width:max-content;height:auto;max-width:980px">{esc(content["subtitle"])}</div>'
    ghost = f'<div class="el chapter-opener-ghost" data-edit-kind="text" data-edit-fit="container" data-contrast-skip="true" data-overflow-intent="clip" style="left:1260px;top:160px;width:max-content;height:auto;max-width:420px">{esc(content["number"])}</div>'
    dots = '<div class="el chapter-dot-field" data-edit-kind="visual" style="left:1250px;top:590px;width:390px;height:140px"></div>'
    return _frame(content, label + rule + title + subtitle + ghost + dots)


def _chapter_text_photo_brand(content: dict[str, Any]) -> str:
    brand = _copy_value(content.get("brand"))
    brand_note = _copy_value(content.get("brand_note"))
    brand_mark = _copy_value(content.get("brand_mark"))
    title_length = len("".join(str(content.get("title") or "").split()))
    title_font_size = 60 if title_length <= 10 else 48
    title_markup = _balanced_chapter_title_markup(content["title"])
    brand_overlay = ""
    if brand or brand_note or brand_mark:
        brand_overlay = f'''<div class="el diagram-node chapter-brand-overlay" data-edit-composite="chapter-brand-overlay" style="left:1018px;top:324px;width:614px;height:432px">
        <div class="diagram-node-bg" data-edit-layer="background"></div>{_optional_layer_text(brand_mark, tag="span", attrs='data-edit-layer="icon"')}
        {_optional_layer_text(brand, tag="b", attrs='data-edit-layer="text"')}{_optional_layer_text(brand_note, tag="em", attrs='data-edit-layer="text"')}
      </div>'''
    return f'''<div class="prod-frame chapter-split-frame" data-density="medium" data-full-height-media="true" style="left:-96px;top:-96px;width:1920px;height:1080px">
      <div class="chapter-left-field"></div><div class="el chapter-edge-strip" data-edit-kind="visual" style="left:0;top:0;width:18px;height:1080px"></div>
      <div class="el chapter-media-field chapter-media-right" data-edit-kind="visual" style="left:864px;top:0;width:1056px;height:1080px"><i></i><i></i><i></i></div>
      <div class="el chapter-split-label" data-edit-kind="text" data-edit-fit="text" style="left:192px;top:270px;width:max-content;height:auto;max-width:620px">{esc(content['label'])}</div>
      <div class="el chapter-split-title" data-edit-kind="text" data-edit-fit="container" style="left:192px;top:340px;width:620px;height:220px;white-space:normal;overflow-wrap:anywhere;word-break:break-all;font-size:{title_font_size}px;line-height:1.12">{title_markup}</div>
      <div class="el chapter-split-body" data-edit-kind="text" data-edit-fit="text" style="left:194px;top:560px;width:max-content;height:auto;max-width:590px">{esc(content['body'])}</div>
      {brand_overlay}
    </div>'''


def _recommendation_stack(content: dict[str, Any]) -> str:
    recommendations = list(content["recommendations"])
    if not 2 <= len(recommendations) <= 5:
        raise ValueError(
            "recommendation-stack supports two to five recommendation rows; "
            "route other item counts to another compatible Layout"
        )
    stack_height = 448
    row_height = stack_height / len(recommendations)
    rows = "".join(
        f'''<div class="content-rec-row row-{index + 1}" data-row-align="center" data-row-count="{len(recommendations)}" style="top:{index * row_height:.3f}px;height:{row_height:.3f}px">
          <span data-edit-layer="metric">{esc(number)}</span><b data-edit-layer="text">{esc(title)}</b><p data-edit-layer="text">{esc(body)}</p><em data-edit-layer="text">{esc(stage)}</em>
        </div>'''
        for index, (number, title, body, stage) in enumerate(recommendations)
    )
    stack = f'''<div class="el diagram-node content-rec-stack" data-edit-composite="recommendation-stack" data-row-count="{len(recommendations)}" style="left:0;top:170px;width:1728px;height:{stack_height}px;--recommendation-row-height:{row_height:.3f}px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>{rows}
    </div>'''
    rationale = f'''<div class="el diagram-node content-rationale" data-edit-composite="recommendation-rationale" style="left:0;top:665px;width:1728px;height:100px">
      <div class="diagram-node-bg" data-edit-layer="background"></div><span data-edit-layer="text" data-edit-position="flow">{esc(content['rationale'])}</span>
    </div>'''
    return _frame(
        content,
        _flow_header(content["title"], content["subtitle"])
        + _flow_follow(stack + rationale),
    )


def _strategic_priorities(content: dict[str, Any]) -> str:
    priorities = list(content["priorities"])
    gap = 40
    card_width = (CONTENT_W - gap * (len(priorities) - 1)) / len(priorities)
    positions = [
        (index * (card_width + gap), card_width)
        for index in range(len(priorities))
    ]
    cards = []
    for index, ((number, title, body, tag, allocation), (left, width)) in enumerate(zip(priorities, positions), 1):
        cards.append(
            f'''<div class="el diagram-node content-priority-card" data-edit-composite="strategic-priority-{index}" data-card-index="{index}" style="left:{left:.3f}px;top:175px;width:{width:.3f}px;height:470px">
              <div class="diagram-node-bg" data-edit-layer="background"></div><span class="content-priority-number" data-edit-layer="metric">{esc(number)}</span>
              <em data-edit-layer="text">{esc(tag)}</em><b data-edit-layer="text">{esc(title)}</b><p data-edit-layer="text">{esc(body)}</p>
              <strong data-edit-layer="metric">{esc(allocation)}</strong><i data-edit-layer="visual" data-edit-anchor="bottom" style="--allocation:{esc(allocation)}"></i>
            </div>'''
        )
    impact = f'''<div class="el diagram-node content-impact-note" data-edit-composite="strategic-impact-note" style="left:0;top:690px;width:1728px;height:90px">
      <div class="diagram-node-bg" data-edit-layer="background"></div><span data-edit-layer="text" data-edit-position="flow">{esc(content['impact'])}</span>
    </div>'''
    return _frame(
        content,
        _flow_header(content["title"], content["subtitle"])
        + _flow_follow("".join(cards) + impact),
    )


def _flow_stages_three(content: dict[str, Any]) -> str:
    stages = list(content["stages"])
    if not 3 <= len(stages) <= 6:
        raise ValueError("flow-stages scaffold supports 3 to 6 composed stages")
    gap = 36 if len(stages) >= 5 else 44
    card_width = (CONTENT_W - gap * (len(stages) - 1)) / len(stages)
    positions = [index * (card_width + gap) for index in range(len(stages))]
    stage_top = 180
    card_body_top = 230
    body_measure = max(1.0, card_width - 68)
    max_body_lines = max(
        _wrapped_line_count(str(body), body_measure, 36)
        for _, _, body, _ in stages
    )
    card_height = max(460, math.ceil(card_body_top + max_body_lines * 36 * 1.42 + 24))
    arrow_padding = 14
    stage_arrows = []
    for index in range(len(stages) - 1):
        start = positions[index] + card_width
        end = positions[index + 1]
        arrow_span = end - start
        arrow_width = arrow_span + arrow_padding * 2
        stage_arrows.append(
            f'''<svg class="el diagram-connectors sequence-stage-connectors flow-arrow flow-arrow-{index}" data-edit-kind="visual" data-edit-object="connector-arrow" data-edit-connector-index="{index}" style="left:{start - arrow_padding}px;top:{stage_top + card_height / 2 - arrow_padding:.3f}px;width:{arrow_width}px;height:{arrow_padding * 2}px" viewBox="0 0 {arrow_width} {arrow_padding * 2}" aria-hidden="true">
      {_short_flow_arrow_path(arrow_span, padding=arrow_padding)}</svg>'''
        )
    connectors = "".join(stage_arrows)
    cards = []
    for index, ((number, title, body, tag), left) in enumerate(zip(stages, positions)):
        cards.append(
            f'''<div class="el diagram-node sequence-stage-card stage-{index + 1}" data-edit-composite="flow-stage-{index + 1}" style="left:{left:.3f}px;top:{stage_top}px;width:{card_width:.3f}px;height:{card_height}px">
              <div class="diagram-node-bg" data-edit-layer="background"></div><span data-edit-layer="metric">{esc(number)}</span>
              <em data-edit-layer="text">{esc(tag)}</em><b data-edit-layer="text">{esc(title)}</b><p data-edit-layer="text">{esc(body)}</p>
            </div>'''
        )
    takeaway_top = stage_top + card_height + 30
    takeaway = f'''<div class="el diagram-node sequence-takeaway" data-edit-composite="flow-takeaway" style="left:180px;top:{takeaway_top}px;width:1368px;height:100px">
      <div class="diagram-node-bg" data-edit-layer="background"></div><span data-edit-layer="text" data-edit-position="flow">{esc(content['takeaway'])}</span>
    </div>'''
    return _frame(
        content,
        _flow_header(content["title"], content["subtitle"], title_centered=True, subtitle_centered=True, subtitle_max_width=1550)
        + _flow_follow(connectors + "".join(cards) + takeaway),
    )


def _gantt_roadmap(content: dict[str, Any]) -> str:
    period_width = 238
    headers = "".join(
        f'<span data-edit-layer="text" style="left:{300 + index * period_width}px;width:{period_width}px">{esc(period)}</span>'
        for index, period in enumerate(content["periods"])
    )
    task_labels = []
    bars = []
    for index, (task, start, duration, status) in enumerate(content["tasks"]):
        top = 82 + index * 82
        task_labels.append(f'<b data-edit-layer="text" style="top:{top}px">{esc(task)}</b>')
        bars.append(
            f'<i class="gantt-bar {status}" data-edit-layer="visual" style="left:{310 + start * period_width}px;top:{top + 14}px;width:{duration * period_width - 20}px;height:42px"></i>'
        )
    grid_lines = "".join(f'<i style="left:{300 + index * period_width}px"></i>' for index in range(7))
    gantt = f'''<div class="el diagram-node sequence-gantt" data-edit-composite="gantt-roadmap" style="left:0;top:170px;width:1728px;height:510px">
      <div class="diagram-node-bg" data-edit-layer="background"></div><div class="gantt-header">{headers}</div>
      <div class="gantt-grid">{grid_lines}</div><div class="gantt-task-labels">{''.join(task_labels)}</div>{''.join(bars)}
    </div>'''
    footnote = f'<div class="el metric-footnote" data-edit-kind="text" data-edit-fit="text" style="left:0;top:722px;width:max-content;height:auto;max-width:1728px">{esc(content["footnote"])}</div>'
    return _frame(
        content,
        _flow_header(content["title"], content["subtitle"], subtitle_max_width=1600)
        + _flow_follow(gantt + footnote),
    )


def _process_flow(content: dict[str, Any]) -> str:
    steps = list(content["steps"])
    if not 3 <= len(steps) <= 6:
        raise ValueError("process-flow supports 3 to 6 steps")
    node_count = len(steps)
    gap = 36 if node_count == 6 else 44 if node_count == 5 else 56
    node_width = (1728 - gap * (node_count - 1)) // node_count
    positions = [index * (node_width + gap) for index in range(node_count)]
    connector_y = 235
    arrow_padding = 14
    arrow_height = arrow_padding * 2
    arrow_top = 170 + connector_y - arrow_padding
    arrow_svgs = []
    for index in range(node_count - 1):
        arrow_start = positions[index] + node_width
        arrow_width = gap + arrow_padding * 2
        arrow_svgs.append(
            f'''<svg class="el diagram-connectors sequence-process-connectors process-arrow process-arrow-{index + 1}" data-edit-kind="visual" data-edit-object="connector-arrow" data-edit-connector-index="{index + 1}" style="left:{arrow_start - arrow_padding}px;top:{arrow_top}px;width:{arrow_width}px;height:{arrow_height}px" viewBox="0 0 {arrow_width} {arrow_height}" aria-hidden="true">
      {_short_flow_arrow_path(gap, padding=arrow_padding)}</svg>'''
        )
    connectors = "".join(arrow_svgs)
    nodes = []
    for index, ((number, title, body), left) in enumerate(zip(steps, positions), 1):
        nodes.append(
            f'''<div class="el diagram-node sequence-process-node node-{index}" data-edit-composite="process-step-{index}" style="left:{left}px;top:220px;width:{node_width}px;height:370px">
              <div class="diagram-node-bg" data-edit-layer="background"></div><span class="circle-number-metric" data-edit-layer="metric" data-edit-horizontal-align="center" data-edit-align-contract="parent-center-axis">{esc(number)}</span>
              <b data-edit-layer="text">{esc(title)}</b><p data-edit-layer="text">{esc(body)}</p>
            </div>'''
        )
    note = f'''<div class="el diagram-node sequence-note" data-edit-composite="process-note" style="left:0;top:630px;width:1728px;height:110px">
      <div class="diagram-node-bg" data-edit-layer="background"></div><span data-edit-layer="text" data-edit-position="flow">{esc(content['note'])}</span>
    </div>'''
    return _frame(
        content,
        _flow_header(content["title"], content["subtitle"], title_centered=True, subtitle_max_width=1550)
        + _flow_follow(connectors + "".join(nodes) + note),
    )


def _timeline_milestones(content: dict[str, Any]) -> str:
    milestones = list(content["milestones"])
    if not 2 <= len(milestones) <= 6:
        raise ValueError("timeline-milestones supports 2 to 6 milestones")
    node_width = 360
    first_center = node_width / 2
    last_center = CONTENT_W - node_width / 2
    step = (last_center - first_center) / (len(milestones) - 1)
    centers = [first_center + index * step for index in range(len(milestones))]
    nodes = []
    for index, (milestone, center) in enumerate(zip(milestones, centers), 1):
        date, label, *detail_parts = milestone
        detail = detail_parts[0] if detail_parts else ""
        top = 36 if index % 2 else 336
        marker_top = 220 if index % 2 else -65
        marker_left = (node_width - 16) / 2
        detail_markup = f'<p data-edit-layer="text">{esc(detail)}</p>' if detail else ""
        position_class = "milestone-top" if index % 2 else "milestone-bottom"
        milestone_height = 340 if position_class == "milestone-top" else 190
        nodes.append(
            f'''<div class="timeline-milestone {position_class} item-{index}" style="left:{center - node_width / 2:.1f}px;top:{top}px;width:{node_width}px;height:{milestone_height}px">
              <div class="timeline-milestone-copy" data-edit-layout-only="true"> <span data-edit-layer="metric">{esc(date)}</span><b data-edit-layer="text">{esc(label)}</b>{detail_markup}</div><i data-edit-layer="visual" style="left:{marker_left:.1f}px;top:{marker_top}px"></i>
            </div>'''
        )
    timeline = f'''<div class="el diagram-node sequence-timeline" data-edit-composite="timeline-milestones" data-visual-surface-role="none" style="left:0;top:150px;width:1728px;height:634px">
      <div class="diagram-node-bg" data-edit-layer="background"></div><div class="timeline-axis" data-edit-layer="visual"></div>{''.join(nodes)}
    </div>'''
    return _frame(
        content,
        _flow_header(content["title"], None, title_centered=True)
        + _flow_follow(timeline),
    )


def _timeline_vertical(content: dict[str, Any]) -> str:
    events = list(content.get("events") or [])
    if not 4 <= len(events) <= 5:
        raise ValueError(
            "timeline-vertical supports four to five events; "
            "route other counts to a compatible sequence Layout"
        )
    timeline_height = 640
    row_step = timeline_height / len(events)
    event_height = round(row_step - 10, 1)
    line_height = round((len(events) - 1) * row_step + 58, 1)
    rows = []
    for index, (date, title, body) in enumerate(events):
        top = round(index * row_step, 1)
        rows.append(
            f'''<div class="timeline-vertical-event event-{index + 1}" style="top:{top:g}px;height:{event_height:g}px">
              <span data-edit-layer="metric">{esc(date)}</span><i data-edit-layer="visual"></i><b data-edit-layer="text">{esc(title)}</b><p data-edit-layer="text">{esc(body)}</p>
            </div>'''
        )
    timeline = f'''<div class="el diagram-node sequence-vertical" data-edit-composite="timeline-vertical" style="left:0;top:130px;width:1728px;height:640px">
      <div class="diagram-node-bg" data-edit-layer="background"></div><div class="timeline-vertical-line" data-edit-layer="visual" style="left:222px;top:32px;width:4px;height:{line_height:g}px"></div>{''.join(rows)}
    </div>'''
    return _frame(content, _title(content["title"]) + timeline)


HTML_DEFAULT_WATERMARK = False


def _cover_logo(left: int, top: int, inverse: bool = False) -> str:
    # Logo output is opt-in and content-backed.  The canonical renderer has no
    # project-brand fallback; callers without an approved logo emit nothing.
    return ""


def _cover_center_title_edge(content: dict[str, Any], variant: dict[str, Any] | None = None) -> str:
    density, fill_ratio = density_profile(content)
    height = round(CONTENT_H * fill_ratio)
    top = round((CONTENT_H - height) / 2)
    if (variant or {}).get("composition_variant") == "centered-signal-hero":
        stack_width = CONTENT_W
        speaker = _optional_loose_text(
            content.get("speaker"),
            class_name="cover-center-speaker",
            attrs='data-edit-align-contract="center-axis"',
            style=f"width:max-content;height:auto;max-width:{_cover_measure(stack_width, _COVER_META_MEASURE)}px",
        )
        org = _optional_loose_text(
            content.get("org"),
            class_name="cover-center-org",
            attrs='data-edit-align-contract="center-axis"',
            style=f"width:max-content;height:auto;max-width:{_cover_measure(stack_width, _COVER_META_MEASURE)}px",
        )
        area = f'''<div class="cover-center-area explicit-center-stack title-flow-stack" data-edit-layout-only="true" data-auto-layout="vertical-stack" data-layout-flow-align="center" style="left:0;top:0;width:{stack_width}px;height:{height}px">
          <div class="el cover-center-title" data-edit-kind="text" data-edit-fit="text" data-edit-align-contract="center-axis" style="width:max-content;height:auto;max-width:{_cover_measure(stack_width, _COVER_TITLE_MEASURE)}px">{esc(content['title'])}</div>
          <div class="el cover-center-rule" data-edit-kind="visual" data-edit-align-contract="center-axis" style="width:260px;height:7px"></div>
          <div class="el cover-center-subtitle" data-edit-kind="text" data-edit-fit="text" data-edit-align-contract="center-axis" style="width:max-content;height:auto;max-width:{_cover_measure(stack_width, _COVER_SUBTITLE_MEASURE)}px">{esc(content['subtitle'])}</div>
          {speaker}{org}
        </div>'''
    else:
        stack_width = 1420
        speaker = _optional_loose_text(
            content.get("speaker"),
            class_name="cover-center-speaker",
            style=f"width:max-content;height:auto;max-width:{_cover_measure(stack_width, _COVER_META_MEASURE)}px",
        )
        org = _optional_loose_text(
            content.get("org"),
            class_name="cover-center-org",
            style=f"width:max-content;height:auto;max-width:{_cover_measure(stack_width, _COVER_META_MEASURE)}px",
        )
        area = f'''<div class="cover-center-area title-flow-stack" data-edit-layout-only="true" data-auto-layout="vertical-stack" data-layout-flow-align="center" style="left:154px;top:115px;width:{stack_width}px;height:{height - 170}px">
          <div class="el cover-center-title" data-edit-kind="text" data-edit-fit="text" style="width:max-content;height:auto;max-width:{_cover_measure(stack_width, _COVER_TITLE_MEASURE)}px">{esc(content['title'])}</div>
          <div class="el cover-center-rule" data-edit-kind="visual" style="width:190px;height:9px"></div>
          <div class="el cover-center-subtitle" data-edit-kind="text" data-edit-fit="text" style="width:max-content;height:auto;max-width:{_cover_measure(stack_width, _COVER_SUBTITLE_MEASURE)}px">{esc(content['subtitle'])}</div>
          {speaker}{org}
        </div>'''
    return f'<div class="prod-frame diagram-frame cover-center-frame" data-edit-layout-only="true" data-density="{density}" data-auto-fill-cap="soft" data-fill-ratio="{fill_ratio:.2f}" data-visual-balance="content-bounds" style="top:{top}px;height:{height}px;--prod-frame-height:{height}px">{area}{_cover_logo(1538, height - 100)}</div>'


def _cover_left_title_open_field(content: dict[str, Any]) -> str:
    density, fill_ratio = density_profile(content)
    height = round(CONTENT_H * fill_ratio)
    top = round((CONTENT_H - height) / 2)
    speaker = _optional_loose_text(
        content.get("speaker"),
        class_name="cover-left-speaker",
        style="width:max-content;height:auto;max-width:800px",
    )
    area = f'''<div class="cover-left-title-stack title-flow-stack" data-edit-layout-only="true" data-auto-layout="vertical-stack" data-layout-flow-id="cover-left-title-open-field" data-layout-flow-align="start" data-layout-flow-gap="standard" style="left:0;top:0;width:1728px;height:888px">
      <div class="el cover-left-title" data-edit-kind="text" data-edit-fit="text" style="width:max-content;height:auto;max-width:1120px">{esc(content['title'])}</div>
      <div class="el cover-left-rule" data-edit-kind="visual" style="width:244px;height:7px"></div>
      <div class="el cover-left-subtitle" data-edit-kind="text" data-edit-fit="text" style="width:max-content;height:auto;max-width:1100px">{esc(content['subtitle'])}</div>
      {speaker}
    </div>'''
    return f'<div class="prod-frame diagram-frame cover-left-title-open-field" data-edit-layout-only="true" data-density="{density}" data-fill-ratio="{fill_ratio:.2f}" data-visual-balance="left-title-open-field" style="top:{top}px;height:{height}px;--prod-frame-height:{height}px">{area}</div>'


def _cover_center_title_double_frame(content: dict[str, Any]) -> str:
    density, fill_ratio = density_profile(content)
    height = round(CONTENT_H * fill_ratio)
    top = round((CONTENT_H - height) / 2)
    stack_width = 1360
    speaker = _optional_loose_text(
        content.get("speaker"),
        class_name="cover-frame-speaker",
        attrs='data-edit-align-contract="center-axis"',
        style="width:max-content;height:auto;max-width:960px",
    )
    org = _optional_loose_text(
        content.get("org"),
        class_name="cover-frame-org",
        attrs='data-edit-align-contract="center-axis"',
        style="width:max-content;height:auto;max-width:960px",
    )
    area = f'''<div class="cover-frame-title-stack title-flow-stack" data-edit-layout-only="true" data-auto-layout="vertical-stack" data-layout-flow-id="cover-center-title-double-frame" data-layout-flow-align="center" style="left:184px;top:90px;width:{stack_width}px;height:{max(620, height - 180)}px">
      <div class="el cover-frame-title" data-edit-kind="text" data-edit-fit="text" data-edit-align-contract="center-axis" style="width:max-content;height:auto;max-width:1280px">{esc(content['title'])}</div>
      <div class="el cover-frame-rule" data-edit-kind="visual" data-edit-align-contract="center-axis" style="width:220px;height:5px"></div>
      <div class="el cover-frame-subtitle" data-edit-kind="text" data-edit-fit="text" data-edit-align-contract="center-axis" style="width:max-content;height:auto;max-width:1180px">{esc(content['subtitle'])}</div>
      {speaker}{org}
    </div>'''
    return f'<div class="prod-frame diagram-frame cover-center-title-double-frame" data-edit-layout-only="true" data-density="{density}" data-auto-fill-cap="soft" data-fill-ratio="{fill_ratio:.2f}" data-visual-balance="center-title-double-frame" style="top:{top}px;height:{height}px;--prod-frame-height:{height}px">{area}</div>'


def _cover_variant_frame(body: str) -> str:
    """Wrap an authored non-image cover composition in the content frame."""

    return (
        '<div class="prod-frame cover-variant-frame" data-edit-layout-only="true" '
        'data-density="medium" data-auto-fill-cap="soft" '
        'style="left:0;top:0;width:1728px;height:888px">'
        f"{body}</div>"
    )


def _cover_variant_text(
    class_name: str,
    text: str,
    left: float,
    top: float,
    max_width: float,
    *,
    align: str = "left",
    center_axis: bool = False,
) -> str:
    if not _copy_value(text):
        return ""
    center_style = ";translate:-50% 0" if center_axis else ""
    center_contract = (
        ' data-edit-align-contract="center-axis"' if center_axis else ""
    )
    return (
        f'<div class="el {class_name}" data-edit-kind="text" '
        f'data-edit-fit="text"{center_contract} '
        f'style="left:{left:.1f}px;top:{top:.1f}px;width:max-content;'
        f'height:auto;max-width:{max_width:.1f}px;text-align:{align}{center_style}">'
        f"{esc(text)}</div>"
    )


def _cover_variant_meta(content: dict[str, Any]) -> str:
    values = [
        str(content.get("speaker") or "").strip(),
        str(content.get("org") or "").strip(),
    ]
    return " · ".join(value for value in values if value)


def _cover_focal_field(
    class_name: str,
    left: float,
    top: float,
    width: float,
    height: float,
) -> str:
    return (
        f'<div class="el cover-focal-field {class_name}" data-edit-kind="visual" '
        f'data-edit-fit="container" aria-hidden="true" '
        f'style="left:{left:.1f}px;top:{top:.1f}px;width:{width:.1f}px;height:{height:.1f}px">'
        '<i></i><i></i><i></i></div>'
    )


def _cover_upper_center_stack(content: dict[str, Any]) -> str:
    meta = _cover_variant_meta(content)
    body = "".join(
        [
            _cover_variant_text(
                "cover-variant-title", content["title"], 864.0, 98.4, 998.4,
                align="center", center_axis=True,
            ),
            _cover_variant_text(
                "cover-variant-subtitle", content["subtitle"], 864.0, 314.4, 691.2,
                align="center", center_axis=True,
            ),
            _cover_variant_text("cover-variant-meta", meta, 1152.0, 768.0, 441.6, align="right"),
        ]
    )
    return _cover_variant_frame(body)


def _cover_photo_frame(
    content: dict[str, Any],
    photo_side: str,
    *,
    asset_src: str | None = None,
    asset_alt: str | None = None,
) -> str:
    photo_left = 0 if photo_side == "left" else 1152
    text_left = 922 if photo_side == "left" else 154
    logo_left = 58 if photo_side == "left" else 1712
    kicker = _optional_loose_text(
        content.get("kicker"),
        class_name="cover-split-kicker",
        style=f"left:{text_left}px;top:220px;width:max-content;height:auto;max-width:760px",
    )
    speaker = _optional_loose_text(
        content.get("speaker"),
        class_name="cover-split-speaker",
        style=f"left:{text_left}px;top:755px;width:max-content;height:auto;max-width:650px",
    )
    org = _optional_loose_text(
        content.get("org"),
        class_name="cover-split-org",
        style=f"left:{text_left}px;top:805px;width:max-content;height:auto;max-width:650px;white-space:normal;overflow-wrap:anywhere;word-break:break-all;letter-spacing:0",
    )
    media_asset = (
        f'<img class="media-photo-asset" data-edit-layer="visual" data-semantic-image="true" '
        f'src="{esc(asset_src)}" alt="{esc(asset_alt or "產品團隊在決策地圖上整理訊號")}">'
        if asset_src
        else ""
    )
    return f'''<div class="prod-frame cover-split-frame photo-{photo_side}" data-density="medium" data-full-height-media="true" style="left:-96px;top:-96px;width:1920px;height:1080px">
      <div class="el cover-media-field" data-edit-kind="visual" style="left:{photo_left}px;top:0;width:768px;height:1080px">{media_asset}<i></i><i></i><i></i></div>
      {kicker}
      <div class="el cover-split-title" data-edit-kind="text" data-edit-fit="text" style="left:{text_left}px;top:285px;width:max-content;height:auto;max-width:820px">{esc(content['title'])}</div>
      <div class="el cover-split-subtitle" data-edit-kind="text" data-edit-fit="text" style="left:{text_left}px;top:545px;width:max-content;height:auto;max-width:760px">{esc(content['subtitle'])}</div>
      {speaker}{org}
      {_cover_logo(logo_left, 920, inverse=True)}
    </div>'''


def _cover_photo_overlay(content: dict[str, Any]) -> str:
    kicker = _optional_layer_text(content.get("kicker"), attrs='data-edit-layer="text"')
    return f'''<div class="prod-frame cover-overlay-frame" data-density="medium" data-full-bleed-media="true" style="left:-96px;top:-96px;width:1920px;height:1080px">
      <div class="cover-overlay-canvas"></div><div class="el cover-media-field cover-overlay-photo" data-edit-kind="visual" style="left:326px;top:0;width:1594px;height:1080px"><i></i><i></i><i></i></div>
      <div class="el diagram-node cover-overlay-block" data-edit-composite="cover-overlay-copy" style="left:96px;top:140px;width:883px;height:616px">
        <div class="diagram-node-bg" data-edit-layer="background"></div>{kicker}
        <b data-edit-layer="text">{esc(content['title'])}</b><p data-edit-layer="text">{esc(content['subtitle'])}</p>
      </div><div class="el cover-overlay-accent" data-edit-kind="visual" style="left:1862px;top:140px;width:58px;height:616px"></div>
    </div>'''


def _hero_fullbleed_brand(content: dict[str, Any]) -> str:
    speaker = _optional_loose_text(
        content.get("speaker"),
        class_name="cover-hero-speaker",
        style="left:158px;top:730px;width:max-content;height:auto;max-width:700px",
    )
    org = _optional_loose_text(
        content.get("org"),
        class_name="cover-hero-org",
        style="left:158px;top:782px;width:max-content;height:auto;max-width:700px",
    )
    return f'''<div class="prod-frame cover-hero-brand-frame" data-density="medium" data-full-bleed-media="true" style="left:-96px;top:-96px;width:1920px;height:1080px">
      <div class="el cover-media-field cover-hero-media" data-edit-kind="visual" style="left:0;top:0;width:1920px;height:1080px"><i></i><i></i><i></i></div><div class="cover-hero-scrim"></div>
      <div class="el cover-hero-title" data-edit-kind="text" data-edit-fit="text" style="left:154px;top:270px;width:max-content;height:auto;max-width:960px">{esc(content['title'])}</div>
      <div class="el cover-hero-subtitle" data-edit-kind="text" data-edit-fit="text" style="left:158px;top:570px;width:max-content;height:auto;max-width:850px">{esc(content['subtitle'])}</div>
      {speaker}{org}
      {_cover_logo(1710, 920, inverse=True)}
    </div>'''


def _hero_fullbleed(content: dict[str, Any]) -> str:
    meta_markup = _optional_loose_text(
        _cover_variant_meta(content),
        class_name="cover-bottom-meta",
        style="left:158px;top:930px;width:max-content;height:auto;max-width:900px",
    )
    return f'''<div class="prod-frame cover-hero-frame" data-density="medium" data-full-bleed-media="true" style="left:-96px;top:-96px;width:1920px;height:1080px">
      <div class="el cover-media-field cover-hero-media" data-edit-kind="visual" style="left:0;top:0;width:1920px;height:1080px"><i></i><i></i><i></i></div><div class="cover-bottom-scrim"></div>
      <div class="el cover-bottom-title" data-edit-kind="text" data-edit-fit="text" style="left:154px;top:625px;width:max-content;height:auto;max-width:1380px">{esc(content['title'])}</div>
      <div class="el cover-bottom-subtitle" data-edit-kind="text" data-edit-fit="text" style="left:158px;top:835px;width:max-content;height:auto;max-width:1190px">{esc(content['subtitle'])}</div>
      {meta_markup}
      {_cover_logo(1710, 62, inverse=True)}
    </div>'''


def _data_annotation(content: dict[str, Any]) -> str:
    chart_svg = render_annotation_line_chart_svg(content["labels"], content["values"])
    labels = "".join(
        f'<span data-edit-layer="text" data-edit-position="flow">{esc(label)}</span>'
        for label in content["labels"]
    )
    chart = f'''<div class="el diagram-node dataviz-annotation-chart" data-edit-composite="annotation-line-chart" data-chart-renderer="python-matplotlib-svg" style="left:0;top:120px;width:1728px;height:650px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>{chart_svg}<div class="dataviz-xlabels">{labels}</div>
    </div>'''
    cards = []
    card_positions = [(430, 165), (1080, 310)]
    for index, ((point_index, title, delta), (left, top)) in enumerate(zip(content["annotations"], card_positions), 1):
        cards.append(
            f'''<div class="el diagram-node dataviz-annotation-card note-{index}" data-edit-composite="chart-annotation-{index}" data-overflow-intent="clip" style="left:{left}px;top:{top}px;width:420px;height:150px">
              <div class="diagram-node-bg" data-edit-layer="background"></div><span data-edit-layer="metric">0{index}</span>
              <b data-edit-layer="text">{esc(title)}</b><strong data-edit-layer="metric">{esc(delta)}</strong><i data-edit-layer="visual"></i>
            </div>'''
        )
    return _frame(content, _title(content["title"]) + chart + "".join(cards))


def _heat_map(content: dict[str, Any]) -> str:
    chart_svg = render_heat_map_chart_svg(
        content["columns"],
        content["values"],
        rows=content["rows"],
        row_label_width=HEAT_ROW_LABEL_W,
        width=HEAT_TABLE_W,
        height=HEAT_GRID_H,
    )
    table = f'''<div class="el diagram-node heat-table" data-edit-composite="heat-map-table" data-chart-renderer="python-matplotlib-svg" data-visual-surface-role="none" style="left:0;top:{HEAT_PANEL_TOP}px;width:{HEAT_TABLE_W}px;height:{HEAT_GRID_H}px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>{chart_svg}</div>'''
    legend = f'<div class="el heat-legend" data-edit-kind="visual" style="left:{HEAT_LEGEND_X}px;top:240px;width:32px;height:400px"></div>'
    return _frame(content, _title(content["title"]) + table + legend)


def _map_svg(region_mode: bool) -> str:
    regions = '''<path class="map-region-shape region-1" d="M350 36 L468 110 L438 208 L308 210 L268 120 Z"/>
      <path class="map-region-shape region-2" d="M308 210 L438 208 L456 302 L330 338 L268 286 Z"/>
      <path class="map-region-shape region-3" d="M330 338 L456 302 L474 402 L354 442 L292 392 Z"/>
      <path class="map-region-shape region-4" d="M354 442 L474 402 L462 510 L360 564 L310 500 Z"/>
      <path class="map-region-shape region-5" d="M360 564 L462 510 L430 624 L352 680 L318 612 Z"/>'''
    if region_mode:
        return regions
    return f'''<path class="map-outline" d="M350 36 L468 110 L438 208 L456 302 L474 402 L462 510 L430 624 L352 680 L318 612 L360 564 L310 500 L354 442 L292 392 L330 338 L268 286 L308 210 L268 120 Z"/>
      <g class="city-pin pin-1"><circle cx="390" cy="144" r="18"/><circle cx="390" cy="144" r="6"/></g>
      <g class="city-pin pin-2"><circle cx="370" cy="350" r="18"/><circle cx="370" cy="350" r="6"/></g>
      <g class="city-pin pin-3"><circle cx="370" cy="560" r="18"/><circle cx="370" cy="560" r="6"/></g>'''


def _map_with_cards(content: dict[str, Any], spotlight: bool) -> str:
    map_class = "dataviz-map spotlight" if spotlight else "dataviz-map region"
    map_image = content.get("map_image_src")
    image_markup = (
        f'<img class="map-media-asset" data-edit-layer="visual" src="{esc(map_image)}" alt="港灣區域視覺">'
        if map_image
        else ""
    )
    map_caption = _optional_layer_text(
        content.get("map_caption") or content.get("caption"),
        class_name="map-caption",
        attrs='data-edit-layer="text"',
    )
    map_root = f'''<div class="el diagram-node {map_class}" data-edit-composite="{'city-map' if spotlight else 'region-map'}" style="left:0;top:115px;width:1050px;height:660px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>{image_markup}<svg data-edit-layer="visual" viewBox="0 0 700 700" aria-hidden="true">{_map_svg(not spotlight)}</svg>
      {map_caption}</div>'''
    source = content["locations"] if spotlight else content["cards"]
    card_width = 553
    note_width = card_width - 92 - 48
    note_lines = [
        _wrapped_line_count(str(item[2]), note_width, GENERATED_TEXT_MIN_PX)
        for item in source
    ]
    max_note_lines = max(note_lines, default=1)
    card_height = round(92 + max_note_lines * GENERATED_TEXT_MIN_PX * 1.4 + 16)
    stack_height = 660
    gap = (stack_height - card_height * len(source)) / max(1, len(source) - 1)
    if gap < 12:
        raise ValueError(
            "map layout cannot contain the longest location note at the 36px floor; "
            "shorten the note or route to another distribution Layout"
        )
    cards = []
    for index, item in enumerate(source, 1):
        label, value, note = item
        cards.append(
            f'''<div class="el diagram-node map-data-card card-{index}" data-edit-composite="map-card-{index}" style="left:1175px;top:{115 + (index - 1) * (card_height + gap):.1f}px;width:{card_width}px;height:{card_height}px">
              <div class="diagram-node-bg" data-edit-layer="background"></div><span data-edit-layer="metric">0{index}</span>
              <b data-edit-layer="text" style="right:48px">{esc(label)}</b><strong data-edit-layer="metric" style="right:48px">{esc(value)}</strong><p data-edit-layer="text" style="right:48px">{esc(note)}</p>
            </div>'''
        )
    return _frame(content, _title(content["title"]) + map_root + "".join(cards))


def _multi_line_chart(content: dict[str, Any]) -> str:
    chart_svg = render_multi_line_chart_svg(content["labels"], content["series"])
    chart = f'''<div class="el diagram-node dataviz-multiline" data-edit-composite="multi-line-chart" data-chart-renderer="python-matplotlib-svg" style="left:0;top:120px;width:1728px;height:650px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>{chart_svg}
    </div>'''
    return _frame(content, _title(content["title"]) + chart)


def _radar_chart(content: dict[str, Any]) -> str:
    chart_svg = render_radar_chart_svg(content["axes"], content["series"])
    label_positions = [(315, 20), (650, 170), (650, 470), (315, 590), (25, 470), (20, 170)]
    labels = "".join(f'<span data-edit-layer="text" style="left:{left}px;top:{top}px">{esc(label)}</span>' for label, (left, top) in zip(content["axes"], label_positions))
    radar = f'''<div class="el diagram-node dataviz-radar" data-edit-composite="radar-chart" data-chart-renderer="python-matplotlib-svg" style="left:0;top:110px;width:1120px;height:670px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>{chart_svg}{labels}
    </div>'''
    legend_rows = "".join(
        f'<div class="radar-legend-row row-{index}"><i data-edit-layer="visual"></i><b data-edit-layer="text">{esc(name)}</b><span data-edit-layer="metric">{sum(values)}/30</span></div>'
        for index, (name, values) in enumerate(content["series"], 1)
    )
    legend_label = _optional_layer_text(
        content.get("legend_label"),
        class_name="content-panel-kicker",
        attrs='data-edit-layer="text"',
    )
    legend = f'''<div class="el diagram-node radar-legend" data-edit-composite="radar-legend" style="left:1160px;top:220px;width:568px;height:430px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>{legend_label}{legend_rows}
    </div>'''
    return _frame(content, _title(content["title"]) + radar + legend)


def _media_photo(
    class_name: str,
    composite: str,
    left: int,
    top: int,
    width: int,
    height: int,
    label: str,
    asset_src: str | None = None,
) -> str:
    media_visual = (
        f'<img class="media-photo-asset" data-edit-layer="visual" src="{esc(asset_src)}" alt="{esc(label)}">'
        if asset_src
        else '<i class="media-photo-art" data-edit-layer="visual"></i>'
    )
    label_markup = _optional_layer_text(
        label,
        class_name="media-photo-label",
        attrs='data-edit-layer="text"',
    )
    return f'''<div class="el diagram-node media-photo {class_name}" data-edit-composite="{composite}" style="left:{left}px;top:{top}px;width:{width}px;height:{height}px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>{media_visual}
      <em class="media-photo-accent" data-edit-layer="visual" data-edit-anchor="bottom"></em>{label_markup}
    </div>'''


def _executive_bio(content: dict[str, Any]) -> str:
    bio_rows = "".join(
        f'<div class="media-bio-row row-{index}"><span data-edit-layer="metric">0{index}</span><p data-edit-layer="text">{esc(text)}</p></div>'
        for index, text in enumerate(content["bio"], 1)
    )
    photo = _media_photo(
        "media-executive-photo", "executive-photo", 0, 66, 500, 720,
        _copy_value(content.get("photo_label")),
    )
    name = f'''<div class="el media-executive-name" data-edit-kind="text" data-edit-fit="text" style="left:580px;top:52px;width:max-content;height:auto;max-width:1050px">{esc(content['name'])}</div>
      <div class="el media-executive-role" data-edit-kind="text" data-edit-fit="text" style="left:584px;top:170px;width:max-content;height:auto;max-width:1030px">{esc(content['role'])}</div>'''
    panel_label = _optional_layer_text(
        content.get("panel_label"),
        class_name="media-panel-kicker",
        attrs='data-edit-layer="text"',
    )
    bio = f'''<div class="el diagram-node media-bio-panel" data-edit-composite="executive-bio-copy" style="left:580px;top:280px;width:1148px;height:370px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>{panel_label}{bio_rows}
    </div>'''
    meta = _optional_loose_text(
        content.get("meta"),
        class_name="media-executive-meta",
        style="left:584px;top:706px;width:max-content;height:auto;max-width:1080px",
    )
    return _frame(content, photo + name + bio + meta)


def _photo_left_overlay(content: dict[str, Any]) -> str:
    photo = _media_photo(
        "media-framed-photo", "framed-photo-left", 0, 26, 850, 800,
        _copy_value(content.get("photo_label")),
    )
    kicker = _optional_layer_text(content.get("kicker"), attrs='data-edit-layer="text"')
    overlay = f'''<div class="el diagram-node media-overlay-title" data-edit-composite="photo-overlay-title" style="left:930px;top:125px;width:798px;height:285px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>{kicker}<b data-edit-layer="text">{esc(content['title'])}</b>
    </div>'''
    body = f'''<div class="el media-overlay-body" data-edit-kind="text" data-edit-fit="text" style="left:962px;top:500px;width:max-content;height:auto;max-width:700px">{esc(content['body'])}</div>'''
    return _frame(content, photo + overlay + body)


def _testimonial_full(content: dict[str, Any]) -> str:
    missing = [field for field in ("quote", "name", "role") if not str(content.get(field) or "").strip()]
    if missing:
        raise ValueError(
            "testimonial-full requires an attributed person statement: "
            f"missing {', '.join(missing)}"
        )
    mark = '''<div class="el diagram-node media-testimonial-mark" data-edit-composite="quote-decoration" data-overflow-intent="bleed" style="left:0;top:20px;width:150px;height:170px"><div class="diagram-node-bg" data-edit-layer="background"></div><span data-edit-layer="text">“</span></div>'''
    quote = f'''<div class="el media-testimonial-quote" data-edit-kind="text" data-edit-fit="text" style="left:160px;top:70px;width:max-content;height:auto;max-width:1460px">{esc(content['quote'])}</div>'''
    photo = _media_photo("media-testimonial-photo", "testimonial-photo", 160, 610, 150, 150, "")
    attribution = f'''<div class="el media-testimonial-name" data-edit-kind="text" data-edit-fit="text" style="left:350px;top:632px;width:max-content;height:auto;max-width:760px">{esc(content['name'])}</div>
      <div class="el media-testimonial-role" data-edit-kind="text" data-edit-fit="text" style="left:352px;top:696px;width:max-content;height:auto;max-width:900px">{esc(content['role'])}</div>'''
    logo_text = _copy_value(content.get("logo"))
    voice_label = _copy_value(content.get("voice_label"))
    logo = ""
    if logo_text or voice_label:
        logo = f'''<div class="el diagram-node media-testimonial-logo" data-edit-composite="testimonial-logo" style="left:1400px;top:625px;width:328px;height:120px"><div class="diagram-node-bg" data-edit-layer="background"></div>{_optional_layer_text(logo_text, tag="b", attrs='data-edit-layer="text"')}{_optional_layer_text(voice_label, attrs='data-edit-layer="text"')}</div>'''
    return _frame(content, mark + quote + photo + attribution + logo)


def _module_card_geometry(count: int) -> list[tuple[int, int, int, int]]:
    if count == 1:
        return [(284, 180, 1160, 560)]
    if count == 2:
        return [(0, 180, 840, 560), (888, 180, 840, 560)]
    if count == 3:
        return [(0, 180, 544, 560), (592, 180, 544, 560), (1184, 180, 544, 560)]
    if count == 4:
        return [(0, 180, 840, 250), (888, 180, 840, 250), (0, 470, 840, 250), (888, 470, 840, 250)]
    if count == 5:
        return [(0, 180, 520, 250), (604, 180, 520, 250), (1208, 180, 520, 250), (302, 470, 520, 250), (906, 470, 520, 250)]
    if count == 6:
        return [(0, 180, 520, 250), (604, 180, 520, 250), (1208, 180, 520, 250), (0, 470, 520, 250), (604, 470, 520, 250), (1208, 470, 520, 250)]
    if count == 7:
        return [(x, 180, 408, 250) for x in (0, 440, 880, 1320)] + [(x, 470, 408, 250) for x in (220, 660, 1100)]
    if count == 8:
        return [(x, y, 408, 250) for y in (180, 470) for x in (0, 440, 880, 1320)]
    raise ValueError(f"Unsupported module card count: {count}")


def _module_cards(content: dict[str, Any]) -> str:
    count = len(content["items"])
    cards = []
    for index, ((title, body, tag), (left, top, width, height)) in enumerate(zip(content["items"], _module_card_geometry(count)), 1):
        cards.append(
            f'''<div class="el diagram-node module-card count-{count} card-{index}" data-edit-composite="module-card-{index}" style="left:{left}px;top:{top}px;width:{width}px;height:{height}px">
              <div class="diagram-node-bg" data-edit-layer="background"></div><span class="module-number" data-edit-layer="metric">{index:02d}</span>
              <em class="module-tag" data-edit-layer="text">{esc(tag)}</em><b data-edit-layer="text">{esc(title)}</b><p data-edit-layer="text">{esc(body)}</p><i data-edit-layer="visual" data-edit-anchor="bottom"></i>
            </div>'''
        )
    subtitle = f'''<div class="el module-subtitle module-subtitle-center-axis" data-edit-kind="text" data-edit-fit="text" style="left:864px;top:100px;width:max-content;height:auto;max-width:1480px;translate:-50% 0;text-align:center">{esc(content['subtitle'])}</div>'''
    return _frame(content, _centered_title(content["title"]) + subtitle + "".join(cards))


def _module_cards_1plus3_variant(
    content: dict[str, Any],
    requested_variant: str | None = None,
) -> tuple[str, str]:
    row, resolved_variant = render_cards_1plus3_variant(content, requested_variant)
    header = _flow_header(content["title"], content.get("subtitle", ""), title_centered=True)
    return _frame(content, header + row), resolved_variant


def _icon_grid(content: dict[str, Any]) -> str:
    boxes = [(0, 150), (596, 150), (1192, 150), (0, 465), (596, 465), (1192, 465)]
    cells = []
    for index, ((label, number), (left, top)) in enumerate(zip(content["items"], boxes), 1):
        cells.append(
            f'''<div class="el diagram-node module-icon-cell cell-{index}" data-edit-composite="icon-cell-{index}" style="left:{left}px;top:{top}px;width:536px;height:285px">
              <div class="diagram-node-bg" data-edit-layer="background"></div><i class="module-icon-shape" data-edit-layer="visual"></i>
              <span data-edit-layer="metric">{esc(number)}</span><b data-edit-layer="text">{esc(label)}</b>
            </div>'''
        )
    return _frame(content, _title(content["title"]) + "".join(cells))


def _people_three(content: dict[str, Any]) -> str:
    cards = []
    for index, (name, role, bio) in enumerate(content["people"], 1):
        left = (index - 1) * 594
        cards.append(
            f'''<div class="el diagram-node module-person-card person-{index}" data-edit-composite="person-card-{index}" style="left:{left}px;top:150px;width:540px;height:620px">
              <div class="diagram-node-bg" data-edit-layer="background"></div><i class="module-person-photo" data-edit-layer="visual"></i>
              <span data-edit-layer="metric">0{index}</span><b data-edit-layer="text">{esc(name)}</b><em data-edit-layer="text">{esc(role)}</em><p data-edit-layer="text">{esc(bio)}</p>
            </div>'''
        )
    return _frame(content, _title(content["title"]) + "".join(cards))


def _team_grid(content: dict[str, Any]) -> str:
    boxes = [(0, 145), (594, 145), (1188, 145), (0, 455), (594, 455), (1188, 455)]
    members = []
    for index, ((name, role), (left, top)) in enumerate(zip(content["members"], boxes), 1):
        members.append(
            f'''<div class="el diagram-node module-team-card member-{index}" data-edit-composite="team-member-{index}" style="left:{left}px;top:{top}px;width:540px;height:285px">
              <div class="diagram-node-bg" data-edit-layer="background"></div><i class="module-team-photo" data-edit-layer="visual"></i>
              <span data-edit-layer="metric">{index:02d}</span><b data-edit-layer="text">{esc(name)}</b><em data-edit-layer="text">{esc(role)}</em>
            </div>'''
        )
    return _frame(content, _title(content["title"]) + "".join(members))


def _toc_title(count: int, content: dict[str, Any]) -> str:
    configured = str(content.get("short_title") or content.get("title") or "").strip()
    if configured:
        return configured
    labels = {2: "兩章建立共同起點", 3: "三章說清決策脈絡", 4: "四章完成核心論證", 5: "五章串起完整提案", 6: "六章推進共同決策", 8: "八章走完決策路徑"}
    return labels.get(count, f"{count} 章串起完整閱讀路徑")


def _toc_card(
    item: tuple[str, str, str],
    index: int,
    left: int,
    top: int,
    width: int,
    height: int,
    class_name: str = "toc-nav-card",
    show_number: bool = True,
) -> str:
    number, title, body = item
    number_markup = f'<span data-edit-layer="metric">{esc(number)}</span>' if show_number else ""
    row_align = ' data-row-align="center"' if "toc-vertical-row" in class_name.split() else ""
    bottom_anchor = (
        ' data-edit-anchor="bottom"'
        if set(class_name.split()) & {"toc-nav-card", "toc-panel-grid-card", "toc-panel-feature"}
        else ""
    )
    return f'''<div class="el diagram-node {class_name} card-{index}" data-edit-composite="toc-chapter-{index}"{row_align} style="left:{left}px;top:{top}px;width:{width}px;height:{height}px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>{number_markup}
      <b data-edit-layer="text">{esc(title)}</b><p data-edit-layer="text">{esc(body)}</p><i data-edit-layer="visual"{bottom_anchor}>→</i>
    </div>'''


def _toc_dynamic_grid(count: int) -> list[tuple[int, int, int, int]]:
    if count in {2, 3, 4, 5, 6, 8}:
        return _module_card_geometry(count)
    columns = 2 if count <= 4 else 3 if count <= 6 else 4
    rows = (count + columns - 1) // columns
    gap_x = 36
    gap_y = 30
    width = round((1728 - gap_x * (columns - 1)) / columns)
    height = round((560 - gap_y * (rows - 1)) / rows)
    return [
        (column * (width + gap_x), 180 + row * (height + gap_y), width, height)
        for row in range(rows)
        for column in range(columns)
    ][:count]


def _toc_standard(content: dict[str, Any]) -> str:
    count = len(content["items"])
    cards = [
        _toc_card(item, index, *box, f"toc-nav-card count-{count}")
        for index, (item, box) in enumerate(zip(content["items"], _toc_dynamic_grid(count)), 1)
    ]
    subtitle = f'''<div class="el toc-subtitle" data-edit-kind="text" data-edit-fit="text" style="left:0;top:100px;width:max-content;height:auto;max-width:1540px">{esc(content['intro'])}</div>'''
    return _frame(content, _title(_toc_title(count, content)) + subtitle + "".join(cards))


def _toc_vertical(content: dict[str, Any]) -> str:
    count = len(content["items"])
    gap = 14
    height = (620 - gap * (count - 1)) / count
    rows = [
        _toc_card(item, index, 0, round(155 + (index - 1) * (height + gap)), 1728, round(height), "toc-vertical-row")
        for index, item in enumerate(content["items"], 1)
    ]
    subtitle = f'''<div class="el toc-subtitle" data-edit-kind="text" data-edit-fit="text" style="left:0;top:95px;width:max-content;height:auto;max-width:1540px">{esc(content['intro'])}</div>'''
    return _frame(content, _title(_toc_title(count, content)) + subtitle + "".join(rows))


def _toc_panel_intro(content: dict[str, Any], class_name: str = "toc-side-panel") -> str:
    count = len(content["items"])
    index_label = _optional_layer_text(
        content.get("index_label"),
        attrs='data-edit-layer="text"',
    )
    footer = _optional_layer_text(
        content.get("footer"),
        tag="em",
        attrs='data-edit-layer="text"',
    )
    return f'''<div class="el diagram-node {class_name}" data-edit-composite="toc-intro-panel" data-visual-surface-role="accent" data-visual-ink-role="accent-text" style="left:0;top:20px;width:520px;height:760px">
      <div class="diagram-node-bg" data-edit-layer="background"></div>{index_label}
      <b data-edit-layer="text">{esc(_toc_title(count, content))}</b><p data-edit-layer="text">{esc(content['intro'])}</p>{footer}
    </div>'''


def _toc_panel_rows(content: dict[str, Any]) -> str:
    count = len(content["items"])
    gap = 16
    height = (760 - gap * (count - 1)) / count
    rows = [
        _toc_card(item, index, 580, round(20 + (index - 1) * (height + gap)), 1148, round(height), "toc-panel-row")
        for index, item in enumerate(content["items"], 1)
    ]
    return _frame(content, _toc_panel_intro(content) + "".join(rows))


def _toc_panel_grid(content: dict[str, Any], *, capacity: int, layout_id: str) -> str:
    count = len(content["items"])
    if count > capacity:
        raise ValueError(
            f"{layout_id} has {capacity} chapter slots but received {count} items; "
            "source routing must select a compatible TOC Layout"
        )
    columns = 2
    rows = (count + columns - 1) // columns
    gap_x = 40
    gap_y = 18
    width = 554
    height = round((760 - gap_y * (rows - 1)) / rows)
    boxes = [
        (580 + column * (width + gap_x), 20 + row * (height + gap_y), width, height)
        for row in range(rows)
        for column in range(columns)
    ][:count]
    cards = [_toc_card(item, index, *box, "toc-panel-grid-card") for index, (item, box) in enumerate(zip(content["items"], boxes), 1)]
    return _frame(content, _toc_panel_intro(content) + "".join(cards))


def _toc_panel_left(content: dict[str, Any]) -> str:
    count = len(content["items"])
    gap = 16
    height = round((760 - gap * (count - 1)) / count)
    panel = _toc_panel_intro(content, "toc-wide-panel").replace("width:520px", "width:650px")
    cards = [_toc_card(item, index, 700, 20 + (index - 1) * (height + gap), 1028, height, "toc-panel-feature") for index, item in enumerate(content["items"], 1)]
    return _frame(content, panel + "".join(cards))


def _toc_image_left(content: dict[str, Any]) -> str:
    count = len(content["items"])
    image = _media_photo(
        "toc-image-field",
        "toc-hero-image",
        0,
        20,
        700,
        760,
        _copy_value(content.get("image_label")),
        asset_src=content.get("hero_image_src"),
    )
    title = f'''<div class="el toc-image-title" data-edit-kind="text" data-edit-fit="text" style="left:760px;top:36px;width:max-content;height:auto;max-width:900px">{esc(_toc_title(count, content))}</div>
      <div class="el toc-image-intro" data-edit-kind="text" data-edit-fit="text" style="left:764px;top:145px;width:max-content;height:auto;max-width:860px">{esc(content['intro'])}</div>'''
    gap = 18
    height = (500 - gap * (count - 1)) / count
    rows = [_toc_card(item, index, 760, round(270 + (index - 1) * (height + gap)), 968, round(height), "toc-image-row") for index, item in enumerate(content["items"], 1)]
    return _frame(content, image + title + "".join(rows))


def _toc_number_panel_left(content: dict[str, Any]) -> str:
    count = len(content["items"])
    row_height = 760 / count
    numbers = "".join(f'<span class="toc-number-strip strip-{index}" data-edit-layer="metric" style="top:{round((index - 1) * row_height)}px;height:{round(row_height)}px">{number}</span>' for index, (number, _, _) in enumerate(content["items"], 1))
    panel = f'''<div class="el diagram-node toc-number-panel" data-edit-composite="toc-number-panel" style="left:0;top:20px;width:420px;height:760px"><div class="diagram-node-bg" data-edit-layer="background"></div>{numbers}</div>'''
    gap = 16
    height = round((760 - gap * (count - 1)) / count)
    rows = [
        _toc_card(item, index, 470, 20 + (index - 1) * (height + gap), 1258, height, "toc-number-row", show_number=False)
        for index, item in enumerate(content["items"], 1)
    ]
    return _frame(content, panel + "".join(rows))


def render_production_layout(layout: dict[str, Any], page_content: dict[str, Any] | None = None) -> str | None:
    layout_id = layout["id"]
    family = layout.get("family")

    def content_or_fixture(fixtures: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
        return page_content if page_content is not None else fixtures.get(layout_id)

    if family == "diagram":
        content = content_or_fixture(DIAGRAM_CONTENT)
        if content is None:
            return None
        if layout_id == "cycle-hub-6":
            return _cycle(content)
        if layout_id == "funnel-4":
            return _funnel(content)
        if layout_id == "org-chart":
            return _org_chart(content)
        if layout_id == "pyramid":
            return _pyramid(content)
        raise ValueError(f"Missing production diagram renderer: {layout_id}")
    if family == "infographic":
        if page_content is None:
            return None
        if layout_id == "infographic-stage":
            return _infographic_stage(page_content)
        raise ValueError(f"Missing production infographic renderer: {layout_id}")
    if family == "comparison":
        content = content_or_fixture(COMPARISON_CONTENT)
        if content is None:
            return None
        if layout_id == "before-after":
            return _before_after(content)
        if layout_id == "comparison-table":
            return _comparison_table(content)
        if layout_id == "matrix-4quadrant":
            return _matrix(content)
        if layout_id == "pricing-3col":
            return _pricing(content)
        if layout_id == "split-comparison":
            return _split_comparison(content)
        if layout_id == "swot-quadrant":
            return _swot(content)
        raise ValueError(f"Missing production comparison renderer: {layout_id}")
    if family == "metrics":
        content = content_or_fixture(METRICS_CONTENT)
        if content is None:
            return None
        if layout_id == "dashboard-overview":
            return _dashboard_overview(content)
        if layout_id == "kpi-scorecards":
            return _kpi_scorecards(content)
        if layout_id == "stats-3-row":
            return _stats_three_row(content)
        raise ValueError(f"Missing production metrics renderer: {layout_id}")
    if family == "closing":
        content = content_or_fixture(CLOSING_CONTENT)
        if content is None:
            return None
        if layout_id == "closing-photo-overlay-contact":
            return _closing_photo_overlay_contact(content)
        raise ValueError(f"Missing production closing renderer: {layout_id}")
    if family == "statement":
        content = content_or_fixture(STATEMENT_CONTENT)
        if content is None:
            return None
        if layout_id == "highlight-callout":
            return _highlight_callout(content)
        if layout_id == "quote-attribution-3":
            return _quote_attribution_three(content)
        if layout_id == "quote-focus":
            return _quote_focus(content)
        if layout_id == "title-center":
            return _title_center(content)
        raise ValueError(f"Missing production statement renderer: {layout_id}")
    if family == "chapter":
        content = content_or_fixture(CHAPTER_CONTENT)
        if content is None:
            return None
        if layout_id == "chapter-fullbleed-overlay-title":
            return _chapter_fullbleed_overlay_title(content)
        if layout_id == "chapter-number-bg-left-title-rule":
            return _chapter_number_background(content)
        if layout_id == "chapter-opener":
            return _chapter_opener(content)
        if layout_id == "chapter-text-left-photo-brand":
            return _chapter_text_photo_brand(content)
        raise ValueError(f"Missing production chapter renderer: {layout_id}")
    if family == "content":
        content = content_or_fixture(CONTENT_CONTENT)
        if content is None:
            return None
        if layout_id == "recommendation-stack":
            return _recommendation_stack(content)
        if layout_id == "strategic-priorities":
            return _strategic_priorities(content)
        raise ValueError(f"Missing production content renderer: {layout_id}")
    if family == "sequence":
        content = content_or_fixture(SEQUENCE_CONTENT)
        if content is None:
            return None
        if layout_id == "flow-stages-3":
            return _flow_stages_three(content)
        if layout_id == "gantt-roadmap":
            return _gantt_roadmap(content)
        if layout_id == "process-flow":
            return _process_flow(content)
        if layout_id == "timeline-milestones":
            return _timeline_milestones(content)
        if layout_id == "timeline-vertical":
            return _timeline_vertical(content)
        raise ValueError(f"Missing production sequence renderer: {layout_id}")
    if family == "cover":
        content = content_or_fixture(COVER_CONTENT)
        if content is None:
            return None
        if layout_id == "cover-center-title-edge-decor":
            return _cover_center_title_edge(content, layout.get("html_variant"))
        if layout_id == "cover-center-title-double-frame":
            return _cover_center_title_double_frame(content)
        if layout_id == "cover-left-title-open-field":
            return _cover_left_title_open_field(content)
        if layout_id == "cover-upper-center-stack-meta-lower-right":
            return _cover_upper_center_stack(content)
        if layout_id == "cover-photo-frame-reverse":
            return _cover_photo_frame(content, "right")
        if layout_id == "cover-photo-frame":
            return _cover_photo_frame(
                content,
                "left",
                asset_src=content.get("hero_image_src"),
                asset_alt=content.get("hero_image_alt"),
            )
        if layout_id == "cover-photo-overlay-block":
            return _cover_photo_overlay(content)
        if layout_id == "hero-fullbleed-brand-footer":
            return _hero_fullbleed_brand(content)
        if layout_id == "hero-fullbleed":
            return _hero_fullbleed(content)
        raise ValueError(f"Missing production cover renderer: {layout_id}")
    if family == "data-viz":
        content = content_or_fixture(DATAVIZ_CONTENT)
        if content is None:
            return None
        if layout_id == "data-annotation":
            return _data_annotation(content)
        if layout_id == "heat-map":
            return _heat_map(content)
        if layout_id == "map-region":
            return _map_with_cards(content, False)
        if layout_id == "map-spotlight":
            return _map_with_cards(content, True)
        if layout_id == "multi-line-chart":
            return _multi_line_chart(content)
        if layout_id == "radar-chart":
            return _radar_chart(content)
        raise ValueError(f"Missing production data-viz renderer: {layout_id}")
    if family == "media":
        content = content_or_fixture(MEDIA_CONTENT)
        if content is None:
            return None
        if layout_id == "executive-bio":
            return _executive_bio(content)
        if layout_id == "photo-left-overlay-title-right":
            return _photo_left_overlay(content)
        if layout_id == "testimonial-full":
            return _testimonial_full(content)
        raise ValueError(f"Missing production media renderer: {layout_id}")
    if family == "modules":
        if page_content is not None:
            if layout_id == "cards-1-plus-3":
                requested_variant = str(page_content.get("layout_variant_id") or "").strip() or None
                html_variant = layout.get("html_variant") or {}
                composition_variant = str(html_variant.get("composition_variant") or "").strip()
                if not requested_variant and composition_variant in CARDS_1PLUS3_VARIANT_IDS:
                    requested_variant = composition_variant
                rendered, resolved_variant = _module_cards_1plus3_variant(
                    page_content,
                    requested_variant,
                )
                layout["resolved_layout_variant"] = resolved_variant
                return rendered
            if layout_id == "icon-grid-6":
                return _icon_grid(page_content)
            if layout_id == "people-3":
                return _people_three(page_content)
            if layout_id == "team-grid":
                return _team_grid(page_content)
            return _module_cards(page_content)
        if layout_id in MODULES_CONTENT:
            return _module_cards(MODULES_CONTENT[layout_id])
        if layout_id == "icon-grid-6":
            return _icon_grid(ICON_GRID_CONTENT)
        if layout_id == "people-3":
            return _people_three(PEOPLE_CONTENT)
        if layout_id == "team-grid":
            return _team_grid(TEAM_CONTENT)
        raise ValueError(f"Missing production modules renderer: {layout_id}")
    if family == "toc":
        declared_count = int(layout_id.split("-")[1])
        content = page_content if page_content is not None else {
            "title": _toc_title(declared_count, TOC_CONTEXT),
            "intro": TOC_CONTEXT["intro"],
            "footer": TOC_CONTEXT["footer"],
            "items": TOC_ITEMS[:declared_count],
        }
        if layout_id in {"toc-3", "toc-4", "toc-5", "toc-6", "toc-8"}:
            return _toc_standard(content)
        if layout_id.endswith("-vertical"):
            return _toc_vertical(content)
        if layout_id.endswith("-panel-rows"):
            return _toc_panel_rows(content)
        if layout_id.endswith("-panel-grid"):
            return _toc_panel_grid(content, capacity=declared_count, layout_id=layout_id)
        if layout_id == "toc-3-panel-left":
            return _toc_panel_left(content)
        if layout_id == "toc-4-image-left":
            return _toc_image_left(content)
        if layout_id == "toc-5-number-panel-left":
            return _toc_number_panel_left(content)
        raise ValueError(f"Missing production toc renderer: {layout_id}")
    return None


PRODUCTION_CSS = r'''
.content{position:absolute;left:96px;top:96px;width:1728px;height:888px}
.prod-frame{position:absolute;left:0;width:1728px;color:var(--text);overflow:visible}.prod-frame[data-edit-layout-only="true"]{pointer-events:none}.prod-frame[data-edit-layout-only="true"] .el{pointer-events:auto}
[data-edit-horizontal-align="left"]{text-align:left!important}[data-edit-horizontal-align="center"]{text-align:center!important}[data-edit-horizontal-align="right"]{text-align:right!important}
.prod-title{z-index:5;padding:0;border:0;background:transparent;font:800 68px/1.06 var(--font-heading);letter-spacing:-.045em;color:var(--text)}
.diagram-node{z-index:3;padding:0;border:0;background:transparent;color:var(--surface-text);overflow:visible}
.diagram-node-bg{position:absolute;inset:0;z-index:0;border:2px solid color-mix(in srgb,var(--accent) 48%,transparent);background:var(--surface)}
.diagram-node>[data-edit-layer]:not(.diagram-node-bg){position:absolute;z-index:2}
.metric-kpi-card[data-edit-structure="module"]>.diagram-node-bg{inset:0;z-index:0}
.diagram-connectors{z-index:1;display:block;padding:0;border:0;border-radius:0;background:transparent;overflow:visible}
.diagram-connectors circle,.diagram-connectors path{fill:none;stroke:color-mix(in srgb,var(--accent) 72%,var(--support-accent));stroke-width:4;stroke-linecap:round;stroke-linejoin:round}
.diagram-connectors marker path{fill:var(--accent);stroke:none}
.diagram-kicker{font:750 36px/1 var(--font-mono);letter-spacing:.18em;color:var(--accent)}
.diagram-no{font:850 37px/1 var(--font-display);color:var(--accent)}.circle-number-metric{text-align:center}
.cycle-hub{border-radius:50%;text-align:center}.cycle-hub .diagram-node-bg{border:0;border-radius:50%;background:transparent;box-shadow:none}
.diagram-hub-title{left:40px;right:40px;top:50%;translate:0 -50%;font:850 52px/1.12 var(--font-heading);color:var(--text);text-wrap:balance}
.cycle-node{border-radius:50%;text-align:center}.cycle-node .diagram-node-bg{border-radius:50%;box-shadow:0 10px 28px color-mix(in srgb,var(--text) 10%,transparent)}
.cycle-node .diagram-no{left:0;right:0;top:23px;font-size:36px}
.cycle-callout{display:flex;flex-direction:column;justify-content:center;gap:8px;box-sizing:border-box;padding:24px 28px;text-align:left}.cycle-callout .diagram-node-bg{border-width:1px;background:color-mix(in srgb,var(--surface) 94%,transparent);box-shadow:0 12px 30px color-mix(in srgb,var(--text) 8%,transparent)}
.diagram-node.cycle-callout>[data-edit-position="flow"]{position:relative;left:auto;right:auto;top:auto;bottom:auto;z-index:2;min-width:0}.cycle-callout .diagram-node-title{font:800 42px/1.08 var(--font-heading);color:var(--surface-text);text-wrap:balance}.cycle-callout .diagram-node-body{font:500 36px/1.22 var(--font-body);color:var(--surface-muted);text-wrap:balance}
.cycle-callout-left{text-align:right}.cycle-callout-left:after,.cycle-callout-right:after{content:"";position:absolute;top:0;bottom:0;width:6px;background:var(--accent)}
.cycle-callout-left:after{right:0}.cycle-callout-right:after{left:0}
.cycle-connectors .cycle-ring{stroke-width:5;opacity:.78}.cycle-connectors .cycle-arc{stroke-width:5;opacity:.94}.cycle-connectors .cycle-leader{stroke-width:2;opacity:.42}.prod-title-center-axis,.prod-subtitle-center-axis,.module-subtitle-center-axis{text-align:center}.funnel-stage{color:var(--surface-text)}.funnel-bg{clip-path:polygon(3% 0,97% 0,91% 100%,9% 100%);border:0;background:color-mix(in srgb,var(--surface) var(--stage-tone),var(--accent))}
.funnel-index{left:8%;top:calc(50% - 12px);font:800 36px/1 var(--font-mono);color:var(--accent)}.funnel-title{left:18%;right:40%;top:22px;font:800 42px/1.1 var(--font-heading)}
.funnel-value{right:18%;top:20px;width:21%;text-align:right;font:850 46px/1 var(--font-display)}.funnel-rate{right:18%;top:76px;width:21%;padding:0;background:transparent;text-align:right;color:var(--surface-muted);font:750 36px/1 var(--font-mono);letter-spacing:.06em}
.funnel-note{left:18%;right:40%;top:70px;font:500 36px/1.28 var(--font-body);color:var(--surface-muted)}
.org-connectors path{stroke-width:3}.org-root .diagram-node-bg,.org-child .diagram-node-bg{border-radius:18px;box-shadow:0 12px 30px color-mix(in srgb,var(--text) 8%,transparent)}
.org-root .diagram-kicker{left:30px;top:27px}.org-title{left:30px;right:88px;top:58px;font:800 42px/1.08 var(--font-heading)}.org-body{left:30px;right:30px;top:104px;font:500 36px/1.2 var(--font-body);color:var(--surface-muted)}
.org-child .diagram-no{left:26px;top:26px}.org-child .org-title{left:82px;right:100px;top:30px;font-size:42px}.org-child .org-body{left:28px;right:28px;top:88px;font-size:36px}.org-metric{right:26px;top:28px;font:850 36px/1 var(--font-display);color:var(--accent)}
.org-note{z-index:3;padding:0;border:0;background:transparent;text-align:center}.org-note .diagram-node-bg{border-radius:999px;background:color-mix(in srgb,var(--surface) 76%,transparent)}.org-note span{left:40px;right:40px;top:26px;font:600 36px/1.25 var(--font-body);color:var(--surface-text)}
.pyramid-bg{clip-path:polygon(10% 0,90% 0,100% 100%,0 100%);border:0;background:color-mix(in srgb,var(--surface) 78%,var(--accent))}.pyramid-layer:nth-of-type(even) .pyramid-bg{background:color-mix(in srgb,var(--support-accent) 66%,var(--surface))}
.pyramid-no{left:12%;top:20px;font:850 36px/1 var(--font-display);color:var(--accent)}.pyramid-title{left:24%;right:12%;top:18px;font:800 42px/1.1 var(--font-heading)}.pyramid-body{left:24%;right:12%;top:64px;text-align:right;font:500 36px/1.1 var(--font-body);color:var(--surface-text)}
.prod-subtitle{z-index:5;display:block;padding:0;border:0;border-radius:0;background:transparent;font:500 36px/1.42 var(--font-body);color:var(--muted)}
.compare-state-header{display:flex;flex-direction:column;justify-content:center;gap:12px;box-sizing:border-box;padding:26px 42px;--semantic-text-stack-gap:12px}.compare-state-header .diagram-node-bg{border-radius:18px;box-shadow:0 16px 42px color-mix(in srgb,var(--text) 8%,transparent)}.compare-state-header>[data-edit-position="flow"]{position:relative;left:auto;right:auto;top:auto;bottom:auto;translate:none;z-index:2;min-width:0}.compare-kicker{font:750 42px/1 var(--font-mono);letter-spacing:.16em;color:var(--surface-muted)}.compare-title{font:850 58px/.98 var(--font-heading);letter-spacing:-.04em;color:var(--surface-text);text-wrap:balance}.compare-subtitle{font:500 36px/1.34 var(--font-body);color:var(--surface-muted);text-wrap:pretty}.compare-state-header.before .diagram-node-bg{background:color-mix(in srgb,var(--surface) 94%,var(--bg))}.compare-state-header.after .diagram-node-bg{border-color:var(--accent);background:color-mix(in srgb,var(--surface) 92%,var(--accent))}
.compare-pair-row{display:grid;grid-template-columns:74px minmax(0,1fr) 110px minmax(0,1fr);align-items:center;column-gap:24px;box-sizing:border-box;padding:0 30px}.compare-pair-row .diagram-node-bg{border:0;border-bottom:1px solid color-mix(in srgb,var(--surface-text) 18%,transparent);border-radius:0;background:transparent}.compare-pair-row>[data-edit-position="flow"],.compare-pair-row>.compare-pair-index,.compare-pair-row>.compare-pair-arrow{position:relative;left:auto;right:auto;top:auto;bottom:auto;translate:none;z-index:2;min-width:0}.compare-pair-index{font:800 36px/1 var(--font-mono);color:var(--accent-label)}.compare-pair-before,.compare-pair-after{font:650 40px/1.2 var(--font-body);text-wrap:balance}.compare-pair-before{color:var(--surface-muted)}.compare-pair-after{color:var(--surface-text)}.compare-pair-arrow{display:grid;place-content:center;width:76px;height:76px;border:2px solid var(--accent);border-radius:50%;font:800 42px/1 var(--font-heading);color:var(--accent);background:var(--bg)}
/* These are renderer-owned flow members. Their selector must outrank the
   generic absolute layer rule above, otherwise a later font load collapses
   the stack back onto its source origin. */
.diagram-node.compare-state-header>[data-edit-position="flow"],.diagram-node.compare-pair-row>[data-edit-position="flow"],.diagram-node.compare-pair-row>.compare-pair-index,.diagram-node.compare-pair-row>.compare-pair-arrow{position:relative;left:auto;right:auto;top:auto;bottom:auto;translate:none;z-index:2;min-width:0}
.compare-table{display:block}.compare-table .diagram-node-bg{border-radius:14px;overflow:hidden}.compare-table-cell{display:flex;align-items:center;padding:0 28px;border-right:1px solid color-mix(in srgb,var(--surface-text) 15%,transparent);border-bottom:1px solid color-mix(in srgb,var(--surface-text) 15%,transparent);font:650 36px/1.2 var(--font-body);color:var(--surface-text)}
.compare-table-cell.header{background:color-mix(in srgb,var(--surface-text) 7%,var(--surface));font:800 36px/1.1 var(--font-heading);letter-spacing:.03em}.compare-table-cell.recommended{background:color-mix(in srgb,var(--accent) 13%,var(--surface));color:var(--surface-text)}.compare-table-cell.header.recommended{background:var(--accent);color:var(--accent-text)}
.compare-note{display:block}.compare-note .diagram-node-bg{border:0;border-left:8px solid var(--accent);border-radius:4px;background:color-mix(in srgb,var(--accent) 10%,var(--bg))}.compare-note span{left:36px;right:36px;top:28px;font:650 36px/1.35 var(--font-body);color:var(--text)}
.matrix-axes path{stroke-width:3}.matrix-axis{z-index:5;display:flex;align-items:center;justify-content:center;box-sizing:border-box;padding:8px 12px;border:0;border-radius:999px;background:var(--bg);overflow:visible;white-space:nowrap;text-align:center;font:750 36px/1 var(--font-mono);letter-spacing:.08em;color:var(--muted)}
.matrix-card{display:block}.matrix-card .diagram-node-bg{border-radius:16px;background:color-mix(in srgb,var(--surface) 92%,var(--bg));box-shadow:0 12px 30px color-mix(in srgb,var(--text) 7%,transparent)}.matrix-card .diagram-no{left:28px;top:26px}.matrix-card b{left:104px;right:28px;top:28px;font:800 42px/1.08 var(--font-heading);color:var(--surface-text)}.matrix-card p{left:104px;right:30px;top:84px;margin:0;font:500 36px/1.22 var(--font-body);color:var(--surface-muted)}
.matrix-card.q2 .diagram-node-bg,.matrix-card.q4 .diagram-node-bg{border-color:color-mix(in srgb,var(--support-accent) 72%,transparent)}.matrix-card.q4 .diagram-node-bg{background:color-mix(in srgb,var(--accent) 10%,var(--surface))}
.price-card{display:block}.price-card .diagram-node-bg{border-radius:18px;box-shadow:0 16px 40px color-mix(in srgb,var(--text) 8%,transparent)}.price-name{left:40px;top:38px;font:800 48px/1 var(--font-mono);letter-spacing:.18em;color:var(--accent)}
.price-value{left:40px;right:40px;top:82px;font:850 78px/.95 var(--font-heading);letter-spacing:-.045em;color:var(--surface-text)}.price-card.tier-3 .price-value{top:98px;font-size:48px;letter-spacing:-.02em}.price-subtitle{left:40px;right:40px;top:180px;font:700 36px/1.2 var(--font-heading);color:var(--surface-muted)}
.price-card ul{position:absolute;left:40px;right:40px;top:248px;list-style:none;margin:0;padding:0}.price-card li{height:70px;display:flex;align-items:center;gap:16px;border-bottom:1px solid color-mix(in srgb,var(--surface-text) 14%,transparent)}.price-card li span{position:static;flex:0 0 auto;color:var(--accent);font:900 36px/1 var(--font-heading)}.price-card li b{position:static;font:600 42px/1.25 var(--font-body);color:var(--surface-text)}
.price-cta{left:40px;right:40px;bottom:38px;height:66px;display:grid;place-content:center;border:2px solid var(--accent);border-radius:8px;font:800 36px/1 var(--font-heading);color:var(--accent)}.price-card.tier-2 .diagram-node-bg{border:4px solid var(--accent);background:color-mix(in srgb,var(--accent) 9%,var(--surface))}.price-card.tier-2 .price-cta{background:var(--accent);color:var(--accent-text)}
.split-panel{display:block}.split-panel .diagram-node-bg{border-radius:18px}.split-label{left:42px;top:42px;font:800 42px/1 var(--font-mono);letter-spacing:.13em;color:var(--accent)}.split-panel>strong{left:42px;right:42px;top:92px;font:850 42px/1.12 var(--font-heading);letter-spacing:-.035em;color:var(--surface-text)}
.split-panel ul{position:absolute;left:42px;right:42px;top:var(--split-list-top,250px);list-style:none;margin:0;padding:0}.split-panel li{height:var(--split-row-height,88px);display:flex;align-items:center;gap:22px;border-bottom:1px solid color-mix(in srgb,var(--surface-text) 15%,transparent)}.split-panel li span{position:static;font:800 36px/1 var(--font-mono);color:var(--accent)}.split-panel li b{position:static;font:650 42px/1.25 var(--font-body);color:var(--surface-text)}
.split-panel.left .diagram-node-bg{background:color-mix(in srgb,var(--surface) 94%,var(--bg))}.split-panel.right .diagram-node-bg{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 8%,var(--surface))}.split-divider{padding:0;border:0;border-radius:999px;background:linear-gradient(transparent,var(--accent) 18% 82%,transparent)}
.infographic-stage-subtitle{z-index:5;padding:0;border:0;background:transparent;font:550 36px/1.25 var(--font-body);color:var(--muted)}
.infographic-stage-meta{display:none}
.infographic-scene-connector{z-index:1;display:block;padding:0;border:0;border-radius:0;background:transparent;overflow:visible}.infographic-scene-connector path{fill:none;stroke:var(--accent);stroke-width:5;stroke-linecap:round;stroke-linejoin:round}.infographic-scene-connector marker path{fill:var(--accent);stroke:none}.infographic-scene-connector.tone-support path{stroke:var(--support-accent)}.infographic-scene-connector.tone-muted path{stroke:color-mix(in srgb,var(--muted) 72%,transparent)}.infographic-scene-connector.is-dashed path{stroke-dasharray:14 12}
.infographic-scene-rule{z-index:1;padding:0;border:0;border-radius:999px;background:color-mix(in srgb,var(--muted) 38%,transparent)}.infographic-scene-rule.tone-accent{background:var(--accent)}.infographic-scene-rule.tone-support{background:var(--support-accent)}
.infographic-scene-module{z-index:3;display:block}.infographic-scene-module .infographic-scene-module-bg{border-radius:18px;background:var(--surface);box-shadow:0 14px 34px color-mix(in srgb,var(--text) 9%,transparent)}.infographic-scene-module.surface-soft .infographic-scene-module-bg{background:color-mix(in srgb,var(--surface) 82%,var(--bg));border-color:color-mix(in srgb,var(--accent) 24%,transparent)}.infographic-scene-module.surface-outline .infographic-scene-module-bg{background:transparent;border-color:color-mix(in srgb,var(--text) 35%,transparent);box-shadow:none}.infographic-scene-module.surface-accent .infographic-scene-module-bg{background:var(--accent);border-color:transparent}.infographic-scene-module.surface-dark .infographic-scene-module-bg{background:color-mix(in srgb,var(--text) 88%,var(--surface));border-color:color-mix(in srgb,var(--accent) 52%,transparent)}.infographic-scene-module.surface-transparent .infographic-scene-module-bg{background:transparent;border-color:transparent;box-shadow:none}
.infographic-scene-module.shape-circle .infographic-scene-module-bg{border-radius:50%}.infographic-scene-module.shape-pill .infographic-scene-module-bg{border-radius:999px}.infographic-scene-module.shape-square .infographic-scene-module-bg{border-radius:2px}.infographic-scene-module.shape-cut .infographic-scene-module-bg{border-radius:0;clip-path:polygon(0 0,92% 0,100% 24%,100% 100%,8% 100%,0 76%)}
.infographic-scene-layer{display:flex;align-items:center;box-sizing:border-box;overflow:hidden;font-family:var(--font-heading);letter-spacing:-.025em}.infographic-scene-layer.kind-label{font-family:var(--font-mono);letter-spacing:.06em}.infographic-scene-layer.kind-metric{font-family:var(--font-display);letter-spacing:-.05em}.infographic-scene-text{z-index:4;padding:0;border:0;background:transparent;font-family:var(--font-heading);letter-spacing:-.03em;overflow:visible}
.infographic-scene-layer.tone-text,.infographic-scene-text.tone-text{color:var(--text)}.infographic-scene-layer.tone-muted,.infographic-scene-text.tone-muted{color:var(--muted)}.infographic-scene-layer.tone-accent,.infographic-scene-text.tone-accent{color:var(--accent)}.infographic-scene-layer.tone-surface-text,.infographic-scene-text.tone-surface-text{color:var(--surface-text)}.infographic-scene-layer.tone-surface-muted,.infographic-scene-text.tone-surface-muted{color:var(--surface-muted)}.infographic-scene-layer.tone-accent-text,.infographic-scene-text.tone-accent-text{color:var(--accent-text)}.infographic-scene-layer.tone-inverse,.infographic-scene-text.tone-inverse{color:var(--bg)}
.swot-card{display:block}.swot-card .diagram-node-bg{border-radius:16px}.swot-letter{left:30px;top:30px;font:850 72px/.9 var(--font-display);color:var(--accent)}.swot-label{left:132px;right:30px;top:35px;font:800 42px/1 var(--font-heading);letter-spacing:.08em;color:var(--surface-text)}
.swot-card ul{position:absolute;left:132px;right:28px;top:82px;list-style:none;margin:0;padding:0}.swot-card li{position:relative!important;padding-left:22px;margin:0 0 12px;font:550 36px/1.25 var(--font-body);color:var(--surface-muted)}.swot-card li:before{content:"";position:absolute;left:0;top:.56em;width:8px;height:8px;border-radius:50%;background:var(--accent)}
.swot-w .diagram-node-bg,.swot-t .diagram-node-bg{border-color:color-mix(in srgb,var(--support-accent) 72%,transparent)}.swot-o .diagram-node-bg{background:color-mix(in srgb,var(--accent) 8%,var(--surface))}.swot-t .diagram-node-bg{background:color-mix(in srgb,var(--support-accent) 10%,var(--surface))}
.metric-eyebrow,.metric-footnote{z-index:5;display:block;padding:0;border:0;border-radius:0;background:transparent}.metric-eyebrow{font:800 36px/1 var(--font-mono);letter-spacing:.18em;color:var(--accent)}.metric-footnote{font:500 36px/1.3 var(--font-body);color:var(--muted)}.dashboard-footnote{font-size:36px;line-height:1.2}
[data-layout-flow-id="dashboard-header"] .prod-subtitle,[data-layout-flow-id="kpi-header"] .prod-subtitle{font-size:36px;line-height:1.3}
.metric-kpi-strip{display:block}.metric-kpi-strip .diagram-node-bg{border-radius:16px}.metric-strip-item{position:absolute;z-index:2;box-sizing:border-box;padding:20px 24px;border-right:1px solid color-mix(in srgb,var(--surface-text) 16%,transparent)}.metric-strip-item:last-child{border-right:0}.metric-strip-item>[data-edit-layer]{position:absolute;z-index:2;min-width:0}.metric-strip-label{left:24px;right:24px;top:20px;font:650 36px/1.15 var(--font-body);color:var(--surface-muted)}.metric-strip-value{left:24px;bottom:20px;white-space:nowrap;font:850 58px/1 var(--font-heading);letter-spacing:-.05em;color:var(--surface-text)}.metric-strip-delta{right:24px;bottom:20px;white-space:nowrap;font:800 36px/1 var(--font-mono);color:var(--accent)}
.metric-chart-panel{position:relative;box-sizing:border-box;padding:22px 30px 18px}.metric-insight{display:flex;flex-direction:column;box-sizing:border-box;padding:22px 30px 14px}.metric-chart-panel .diagram-node-bg,.metric-insight .diagram-node-bg{border-radius:16px}.diagram-node.metric-insight>[data-edit-position="flow"]{position:relative;left:auto;right:auto;top:auto;bottom:auto;z-index:2;min-width:0}.metric-panel-kicker{position:absolute;left:30px;top:22px;font:800 36px/1 var(--font-mono);letter-spacing:.08em;color:var(--accent)}.metric-panel-title{position:absolute;left:30px;top:72px;width:700px;font:800 42px/1.15 var(--font-heading);color:var(--surface-text);text-wrap:balance}.metric-panel-value{position:absolute;right:30px;top:72px;white-space:nowrap;font:850 48px/1 var(--font-heading);color:var(--accent)}
.metric-chart-panel>.python-matplotlib-chart{left:30px;top:142px;width:1000px;height:240px}.metric-chart-labels{position:absolute;left:30px;right:30px;bottom:18px;height:44px;display:flex;align-items:flex-start;justify-content:space-between}.metric-chart-labels span{position:static;width:72px;text-align:center;font:700 36px/1 var(--font-mono);color:var(--surface-muted)}
.metric-insight .metric-panel-kicker{position:relative;left:auto;top:auto;flex:0 0 auto}.metric-insight-title{position:relative;left:auto;top:auto;flex:0 0 auto;margin-top:8px;font:800 42px/1.15 var(--font-heading);letter-spacing:-.025em;color:var(--surface-text);text-wrap:balance}.metric-insight ul{position:relative;z-index:2;display:grid;grid-template-rows:repeat(3,minmax(0,1fr));flex:1 1 auto;min-height:0;list-style:none;margin:14px 0 0;padding:0}.metric-insight li{position:relative;min-height:0;display:grid;grid-template-columns:minmax(0,1fr);align-items:center;gap:16px;border-bottom:1px solid color-mix(in srgb,var(--surface-text) 14%,transparent)}.metric-insight li span{position:absolute;left:0;top:50%;transform:translateY(-50%);font:800 36px/1 var(--font-mono);color:var(--accent)}.metric-insight li b{position:relative;display:block;min-width:0;margin-left:72px;font:600 42px/1.22 var(--font-body);color:var(--surface-text);text-wrap:balance}
 .metric-kpi-card{position:absolute;box-sizing:border-box;padding:28px;overflow:visible;text-align:center}.metric-kpi-card .diagram-node-bg{border-radius:16px;box-shadow:0 14px 34px color-mix(in srgb,var(--text) 7%,transparent)}.metric-kpi-card>[data-edit-layer]{position:absolute;left:28px;right:28px;z-index:2;min-width:0;text-align:center}.metric-card-value{top:52px;white-space:nowrap;font:850 72px/.96 var(--font-heading);letter-spacing:-.055em;color:var(--surface-text)}.metric-card-label{top:144px;font:800 42px/1.15 var(--font-heading);color:var(--surface-text);text-wrap:balance}.metric-card-note{top:210px;font:500 36px/1.22 var(--font-body);color:var(--surface-muted);text-wrap:balance}.metric-card-delta{left:28px;right:28px;bottom:28px;font:800 36px/1 var(--font-mono);font-style:normal;color:var(--accent)}.metric-kpi-card.count-5,.metric-kpi-card.count-6{padding:24px}.metric-kpi-card.count-5 .metric-card-value,.metric-kpi-card.count-6 .metric-card-value{font-size:56px}
.metric-kpi-card.card-2 .diagram-node-bg,.metric-kpi-card.card-4 .diagram-node-bg,.metric-kpi-card.card-6 .diagram-node-bg{border-color:color-mix(in srgb,var(--support-accent) 72%,transparent)}.metric-takeaway{display:flex;align-items:center;box-sizing:border-box;padding:22px 40px}.metric-takeaway[data-edit-horizontal-align="left"]{justify-content:flex-start}.metric-takeaway[data-edit-horizontal-align="center"]{justify-content:center}.metric-takeaway[data-edit-horizontal-align="right"]{justify-content:flex-end}.metric-takeaway .diagram-node-bg{border:0;border-left:9px solid var(--accent);border-radius:4px;background:color-mix(in srgb,var(--accent) 9%,var(--bg))}.diagram-node.metric-takeaway>[data-edit-position="flow"]{position:relative;left:auto;right:auto;top:auto;bottom:auto;z-index:2}.metric-takeaway span{font:650 36px/1.35 var(--font-body);color:var(--text);text-wrap:balance}
.metric-stat-card{display:block;text-align:left}.metric-stat-card .diagram-node-bg{border:0;border-top:6px solid var(--accent);border-radius:0;background:color-mix(in srgb,var(--surface) 82%,var(--bg))}.metric-stat-index{left:32px;top:36px;font:800 36px/1 var(--font-mono);letter-spacing:.14em;color:var(--accent)}.metric-stat-value{left:32px;right:32px;top:112px;font:850 138px/.88 var(--font-heading);letter-spacing:-.07em;color:var(--surface-text)}.metric-stat-label{left:32px;right:32px;top:280px;font:850 42px/1.05 var(--font-heading);color:var(--surface-text)}.metric-stat-note{left:32px;right:32px;top:350px;font:500 36px/1.35 var(--font-body);color:var(--surface-muted)}
.metric-stat-card.stat-2 .diagram-node-bg{border-top-color:var(--support-accent)}.metric-stat-card.stat-3 .diagram-node-bg{background:color-mix(in srgb,var(--accent) 9%,var(--surface))}
.closing-frame{z-index:0;overflow:visible}.closing-photo-field{z-index:0;display:block;padding:0;border:0;border-radius:0;background:linear-gradient(90deg,color-mix(in srgb,var(--bg) 66%,transparent) 0 48%,color-mix(in srgb,var(--bg) 18%,transparent) 72%,transparent),radial-gradient(circle at 76% 24%,color-mix(in srgb,var(--accent) 72%,transparent),transparent 31%),linear-gradient(138deg,color-mix(in srgb,var(--support-accent) 76%,var(--bg)),var(--bg) 64%);overflow:hidden}
.closing-photo-glow{position:absolute;right:-90px;top:-120px;width:940px;height:940px;border-radius:50%;background:radial-gradient(circle,color-mix(in srgb,var(--accent) 52%,transparent),transparent 66%);filter:blur(8px)}.closing-photo-subject{position:absolute;right:80px;top:120px;width:760px;height:820px;border-radius:48% 48% 24% 24%;background:radial-gradient(circle at 52% 20%,color-mix(in srgb,var(--surface) 78%,var(--accent)) 0 11%,transparent 11.5%),linear-gradient(160deg,transparent 0 24%,color-mix(in srgb,var(--surface) 42%,var(--support-accent)) 24% 100%);filter:drop-shadow(0 42px 65px color-mix(in srgb,#000 42%,transparent));opacity:.82}.closing-photo-subject i{position:absolute;bottom:0;width:120px;background:color-mix(in srgb,var(--surface) 22%,transparent);border-top:3px solid color-mix(in srgb,var(--accent) 60%,transparent)}.closing-photo-subject i:nth-child(1){left:24px;height:46%}.closing-photo-subject i:nth-child(2){left:176px;height:67%}.closing-photo-subject i:nth-child(3){left:328px;height:84%}.closing-photo-grain{position:absolute;inset:0;background-image:radial-gradient(rgba(255,255,255,.15) .8px,transparent .8px);background-size:6px 6px;mix-blend-mode:soft-light;opacity:.18}
.closing-copy-panel,.closing-social-panel{display:block;z-index:3}.closing-copy-panel .diagram-node-bg{border:0;border-radius:0;background:color-mix(in srgb,var(--surface) 88%,transparent);backdrop-filter:blur(12px);box-shadow:0 24px 70px color-mix(in srgb,#000 24%,transparent)}.closing-social-panel .diagram-node-bg{border:0;border-radius:0;background:var(--accent)}
.closing-kicker{left:52px;top:48px;font:800 36px/1 var(--font-mono);letter-spacing:.18em;color:var(--accent)}.closing-title{left:50px;right:46px;top:93px;font:900 98px/.9 var(--font-heading);letter-spacing:-.065em;color:var(--surface-text)}.closing-body{left:52px;right:56px;top:210px;font:600 36px/1.5 var(--font-body);color:var(--surface-muted)}
.closing-copy-panel ul{position:absolute;left:52px;right:52px;bottom:44px;list-style:none;margin:0;padding:0}.closing-copy-panel li{height:54px;display:flex;align-items:center;gap:24px;border-bottom:1px solid color-mix(in srgb,var(--surface-text) 15%,transparent)}.closing-copy-panel li span{position:static;flex:0 0 74px;font:800 36px/1 var(--font-mono);letter-spacing:.15em;color:var(--accent)}.closing-copy-panel li b{position:static;font:650 42px/1.2 var(--font-body);color:var(--surface-text)}
.closing-social-row{position:absolute;left:0;width:250px;height:173px;z-index:2;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;border-bottom:1px solid color-mix(in srgb,var(--accent-text) 20%,transparent)}.closing-social-row.row-1{top:0}.closing-social-row.row-2{top:173px}.closing-social-row.row-3{top:346px;border-bottom:0}.closing-social-row b{position:static;width:66px;height:66px;display:grid;place-content:center;border:2px solid var(--accent-text);border-radius:50%;font:900 42px/1 var(--font-heading);text-transform:uppercase;color:var(--accent-text)}.closing-social-row span{position:static;font:800 36px/1 var(--font-mono);letter-spacing:.14em;color:var(--accent-text)}
[data-theme="brand-editorial"] .closing-copy-panel .diagram-node-bg{background:color-mix(in srgb,var(--surface) 94%,transparent)}[data-theme="brand-editorial"] .closing-body,[data-theme="brand-editorial"] .closing-copy-panel li b{font-family:var(--font-display)}[data-theme="clinical-report"] .closing-photo-field{background:linear-gradient(90deg,color-mix(in srgb,var(--bg) 70%,transparent),transparent),linear-gradient(140deg,var(--support-accent),var(--bg))}[data-theme="product-strategy-signal"] .closing-social-panel .diagram-node-bg{background:var(--accent)}
.statement-chart-panel{display:block}.statement-chart-panel .diagram-node-bg{border-radius:16px}.statement-chart-kicker{left:38px;top:34px;font:800 36px/1 var(--font-mono);letter-spacing:.16em;color:var(--accent)}.statement-chart-title{left:38px;right:220px;top:64px;font:800 42px/1.15 var(--font-heading);color:var(--surface-text)}.statement-chart-value{right:38px;top:48px;font:850 64px/.95 var(--font-heading);color:var(--accent)}
.statement-chart-panel>.python-matplotlib-chart{left:20px;top:130px;width:1040px;height:410px;overflow:hidden}.statement-chart-labels{position:absolute;left:20px;top:558px;width:1040px;height:44px;display:flex;align-items:flex-start;justify-content:space-between}.statement-chart-labels span{position:static;width:64px;text-align:center;font:700 36px/1 var(--font-mono);color:var(--surface-muted)}
.statement-callout{display:block}.statement-callout .diagram-node-bg{border-radius:14px}.statement-callout>span{left:28px;top:28px;font:850 38px/1 var(--font-display);color:var(--accent)}.statement-callout>b{left:96px;right:28px;top:32px;font:800 42px/1.08 var(--font-heading);color:var(--surface-text)}.statement-callout>p{left:96px;right:30px;top:83px;margin:0;font:500 36px/1.38 var(--font-body);color:var(--surface-muted)}.statement-callout.callout-2 .diagram-node-bg{border-color:color-mix(in srgb,var(--support-accent) 72%,transparent)}.statement-callout.callout-3 .diagram-node-bg{background:color-mix(in srgb,var(--accent) 8%,var(--surface))}
.statement-quote-card{display:block}.statement-quote-card .diagram-node-bg{border:0;border-top:6px solid var(--accent);border-radius:0;background:color-mix(in srgb,var(--surface) 86%,var(--bg))}.statement-quote-mark{left:30px;top:32px;font:900 110px/.8 var(--font-display);color:color-mix(in srgb,var(--accent) 72%,transparent)}.statement-quote-card blockquote{left:34px;right:34px;top:142px;margin:0;font:700 38px/1.42 var(--font-heading);letter-spacing:-.025em;color:var(--surface-text)}.statement-quote-card>b{left:34px;bottom:76px;font:800 42px/1 var(--font-heading);color:var(--surface-text)}.statement-quote-card>em{left:34px;bottom:42px;font:600 36px/1 var(--font-body);font-style:normal;color:var(--surface-muted)}.statement-quote-card.quote-2 .diagram-node-bg{border-top-color:var(--support-accent)}.statement-quote-card.quote-3 .diagram-node-bg{background:color-mix(in srgb,var(--accent) 8%,var(--surface))}
.statement-focus-quote{z-index:4;display:block;padding:0;border:0;border-radius:0;background:transparent;font:800 76px/1.28 var(--font-heading);letter-spacing:-.045em;color:var(--text)}.statement-focus-attribution{z-index:4;display:block;padding:0;border:0;border-radius:0;background:transparent;font:750 36px/1 var(--font-mono);letter-spacing:.14em;color:var(--accent)}.statement-focus-rail{z-index:3;display:block;padding:0;border:0;border-radius:0;background:transparent}.statement-focus-rail-line{position:absolute;inset:0;background:linear-gradient(var(--accent),color-mix(in srgb,var(--accent) 48%,var(--support-accent)))}
.statement-column-body{display:block}.statement-column-body .diagram-node-bg{border:0;border-top:4px solid var(--accent);border-radius:0;background:color-mix(in srgb,var(--surface) 72%,transparent)}.statement-column-intro{left:52px;right:52px;top:42px;margin:0;font:600 36px/1.5 var(--font-body);color:var(--surface-text)}.statement-column-section{position:absolute;left:52px;right:52px;height:110px;z-index:2;border-top:1px solid color-mix(in srgb,var(--surface-text) 14%,transparent)}.statement-column-section.section-1{top:205px}.statement-column-section.section-2{top:320px}.statement-column-section.section-3{top:435px}.statement-column-section>[data-edit-layer]{position:absolute;z-index:2}.statement-column-section>span{left:0;top:36px;font:850 36px/1 var(--font-mono);color:var(--accent)}.statement-column-section>b{left:72px;top:28px;width:300px;font:800 42px/1.1 var(--font-heading);color:var(--surface-text)}.statement-column-section>p{left:390px;right:0;top:24px;margin:0;font:500 36px/1.4 var(--font-body);color:var(--surface-muted)}
.statement-center-area{position:absolute;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:46px;text-align:center}.statement-center-area>.el{position:relative;flex:0 0 auto}.statement-center-headline,.statement-center-support{display:block;padding:0;border:0;border-radius:0;background:transparent;text-align:center}.statement-center-headline{font:900 92px/1.13 var(--font-heading);letter-spacing:-.055em;color:var(--text)}.statement-center-rule{padding:0;border:0;border-radius:999px;background:var(--accent)}.statement-center-support{font:550 36px/1.5 var(--font-body);color:var(--muted)}
[data-theme="brand-editorial"] .statement-quote-card blockquote,[data-theme="brand-editorial"] .statement-focus-quote,[data-theme="brand-editorial"] .statement-column-intro,[data-theme="brand-editorial"] .statement-column-section>p,[data-theme="brand-editorial"] .statement-center-support{font-family:var(--font-display)}[data-theme="clinical-report"] .statement-quote-card .diagram-node-bg,[data-theme="clinical-report"] .statement-column-body .diagram-node-bg{background:var(--surface)}
.chapter-fullbleed-frame,.chapter-split-frame{z-index:0;overflow:visible}.chapter-media-field{z-index:0;display:block;padding:0;border:0;border-radius:0;overflow:hidden;background:linear-gradient(115deg,color-mix(in srgb,var(--bg) 68%,transparent),transparent 54%),radial-gradient(circle at 70% 24%,color-mix(in srgb,var(--accent) 68%,transparent),transparent 32%),linear-gradient(145deg,color-mix(in srgb,var(--support-accent) 78%,var(--bg)),var(--bg) 66%)}.chapter-media-field:after{content:"";position:absolute;inset:0;background-image:radial-gradient(rgba(255,255,255,.14) .8px,transparent .8px);background-size:7px 7px;opacity:.16}.chapter-media-field i{position:absolute;bottom:-90px;width:250px;border-radius:160px 160px 0 0;background:color-mix(in srgb,var(--surface) 28%,transparent);border-top:3px solid color-mix(in srgb,var(--accent) 48%,transparent)}.chapter-media-field i:nth-child(1){right:70px;height:72%}.chapter-media-field i:nth-child(2){right:350px;height:54%}.chapter-media-field i:nth-child(3){right:630px;height:38%}
.chapter-overlay-title,.chapter-number-panel{display:block;z-index:3}.chapter-overlay-title .diagram-node-bg{border:0;border-radius:0;background:color-mix(in srgb,var(--surface) 88%,transparent);backdrop-filter:blur(10px)}.chapter-overlay-title>span{left:38px;top:34px;font:800 42px/1 var(--font-mono);letter-spacing:.18em;color:var(--accent)}.chapter-overlay-title>b{left:38px;right:32px;top:76px;font:850 54px/1.05 var(--font-heading);letter-spacing:-.04em;color:var(--surface-text)}.chapter-overlay-title>em{left:40px;right:32px;bottom:34px;font:600 42px/1.25 var(--font-body);font-style:normal;color:var(--surface-muted)}
.chapter-number-panel .diagram-node-bg{border:0;border-radius:0;background:var(--accent)}.chapter-number-panel>span{left:0;right:0;top:74px;text-align:center;font:800 36px/1 var(--font-mono);letter-spacing:.18em;color:var(--accent-text)}.chapter-number-panel>b{left:0;right:0;top:360px;text-align:center;font:900 190px/.82 var(--font-heading);letter-spacing:-.08em;color:var(--accent-text);writing-mode:horizontal-tb}
.chapter-label,.chapter-left-title,.chapter-left-subtitle,.chapter-number-ghost,.chapter-opener-title,.chapter-opener-ghost,.chapter-split-label,.chapter-split-title,.chapter-split-body{z-index:4;display:block;padding:0;border:0;border-radius:0;background:transparent}.chapter-label,.chapter-split-label{font:800 42px/1 var(--font-mono);letter-spacing:.2em;color:var(--accent)}.chapter-title-rule{z-index:4;padding:0;border:0;border-radius:999px;background:var(--accent)}.chapter-left-title{font:900 90px/1.02 var(--font-heading);letter-spacing:-.055em;color:var(--text)}.chapter-left-subtitle{font:550 36px/1.5 var(--font-body);color:var(--muted)}.chapter-number-ghost{z-index:1;font:900 500px/.8 var(--font-display);letter-spacing:-.08em;color:color-mix(in srgb,var(--accent) 10%,transparent)}.chapter-side-decor{z-index:4;padding:0;border:0;border-radius:999px;background:linear-gradient(var(--accent),var(--support-accent))}
.chapter-opener-title{font:900 106px/1.02 var(--font-heading);letter-spacing:-.06em;color:var(--text)}.chapter-opener-ghost{z-index:1;font:900 420px/.8 var(--font-display);color:color-mix(in srgb,var(--accent) 9%,transparent)}.chapter-dot-field{z-index:2;padding:0;border:0;border-radius:0;background-image:radial-gradient(var(--accent) 3px,transparent 3.5px);background-size:24px 24px;opacity:.34}
.chapter-left-field{position:absolute;left:0;top:0;width:864px;height:1080px;background:var(--bg)}.chapter-edge-strip{z-index:4;padding:0;border:0;border-radius:0;background:var(--accent)}.chapter-split-title{font:900 68px/1.08 var(--font-heading);letter-spacing:-.045em;color:var(--text)}.chapter-split-body{font:550 36px/1.58 var(--font-body);color:var(--muted)}
.chapter-brand-overlay{display:block;z-index:3}.chapter-brand-overlay .diagram-node-bg{border:0;border-radius:0;background:color-mix(in srgb,var(--accent) 84%,transparent);backdrop-filter:blur(10px)}.chapter-brand-overlay>span{left:52px;top:58px;width:100px;height:100px;display:grid;place-content:center;border:3px solid var(--accent-text);border-radius:50%;font:900 36px/1 var(--font-heading);color:var(--accent-text)}.chapter-brand-overlay>b{left:52px;right:40px;top:200px;font:900 52px/1 var(--font-heading);letter-spacing:-.04em;color:var(--accent-text)}.chapter-brand-overlay>em{left:54px;right:40px;top:272px;font:800 36px/1 var(--font-mono);letter-spacing:.18em;font-style:normal;color:var(--accent-text)}
[data-theme="brand-editorial"] .chapter-overlay-title .diagram-node-bg{background:color-mix(in srgb,var(--surface) 94%,transparent)}[data-theme="brand-editorial"] .chapter-left-subtitle,[data-theme="brand-editorial"] .chapter-split-body{font-family:var(--font-display)}[data-theme="clinical-report"] .chapter-media-field{background:linear-gradient(145deg,var(--support-accent),var(--bg))}[data-theme="product-strategy-signal"] .chapter-number-panel .diagram-node-bg,[data-theme="product-strategy-signal"] .chapter-brand-overlay .diagram-node-bg{background:var(--accent)}
.content-logo-panel,.content-palette-panel,.content-voice-panel,.content-do-panel,.content-application-note,.content-rec-stack,.content-rationale,.content-priority-card,.content-impact-note{display:block}.content-logo-panel .diagram-node-bg,.content-palette-panel .diagram-node-bg,.content-voice-panel .diagram-node-bg,.content-do-panel .diagram-node-bg,.content-rec-stack .diagram-node-bg,.content-priority-card .diagram-node-bg{border-radius:16px}
.content-logo-panel>span{left:38px;top:42px;width:92px;height:92px;display:grid;place-content:center;border:3px solid var(--accent);border-radius:50%;font:900 36px/1 var(--font-heading);color:var(--accent)}.content-logo-panel>b{left:160px;right:30px;top:54px;font:800 42px/1.08 var(--font-heading);color:var(--surface-text)}.content-logo-panel>p{left:160px;right:30px;top:104px;margin:0;font:500 36px/1.4 var(--font-body);color:var(--surface-muted)}.content-logo-panel>i{left:28px;top:30px;width:112px;height:112px;border:1px dashed color-mix(in srgb,var(--accent) 60%,transparent);border-radius:50%}
.content-panel-kicker{left:34px;top:28px;font:800 36px/1 var(--font-mono);letter-spacing:.16em;color:var(--accent)}.content-swatches{position:absolute;left:34px;top:68px;width:500px;height:142px;display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.content-swatches i{position:relative!important;border-radius:8px}.content-swatches i:nth-child(1){background:var(--text)}.content-swatches i:nth-child(2){background:var(--accent)}.content-swatches i:nth-child(3){background:var(--support-accent)}.content-swatches i:nth-child(4){background:var(--surface);border:1px solid color-mix(in srgb,var(--surface-text) 18%,transparent)}
.content-type-pair{position:absolute;left:584px;right:32px;top:54px;height:168px}.content-type-pair>[data-edit-layer]{position:absolute}.content-type-pair>strong{left:0;top:0;font:900 92px/.9 var(--font-heading);color:var(--surface-text)}.content-type-pair>b{left:150px;top:10px;font:800 42px/1 var(--font-heading);color:var(--surface-text)}.content-type-pair>em{left:150px;top:48px;font:600 36px/1 var(--font-body);font-style:normal;color:var(--surface-muted)}.content-type-pair>span{left:150px;right:0;top:92px;font:500 36px/1.35 var(--font-body);color:var(--surface-muted)}
.content-voice-item{position:absolute;top:72px;width:320px;height:120px;border-right:1px solid color-mix(in srgb,var(--surface-text) 15%,transparent)}.content-voice-item.item-1{left:34px}.content-voice-item.item-2{left:365px}.content-voice-item.item-3{left:696px;border-right:0}.content-voice-item>[data-edit-layer]{position:absolute}.content-voice-item>span{left:0;top:0;font:800 36px/1 var(--font-mono);color:var(--accent)}.content-voice-item>b{left:0;top:32px;font:800 42px/1 var(--font-heading);color:var(--surface-text)}.content-voice-item>p{left:0;right:26px;top:68px;margin:0;font:500 36px/1.35 var(--font-body);color:var(--surface-muted)}
.content-do,.content-dont{position:absolute;left:30px;right:30px;height:82px}.content-do{top:28px;border-bottom:1px solid color-mix(in srgb,var(--surface-text) 15%,transparent)}.content-dont{top:118px}.content-do>[data-edit-layer],.content-dont>[data-edit-layer]{position:absolute}.content-do span,.content-dont span{left:0;top:7px;width:74px;font:900 36px/1 var(--font-mono);color:var(--accent)}.content-dont span{color:var(--support-accent)}.content-do b,.content-dont b{left:90px;right:0;top:0;font:650 42px/1.35 var(--font-body);color:var(--surface-text)}
.content-application-note .diagram-node-bg,.content-rationale .diagram-node-bg,.content-impact-note .diagram-node-bg{border:0;border-left:8px solid var(--accent);border-radius:4px;background:color-mix(in srgb,var(--accent) 9%,var(--bg))}.content-application-note span{left:34px;top:22px;width:max-content;height:auto;max-width:1660px;font:650 36px/1.3 var(--font-body);color:var(--text)}
.content-rec-row{position:absolute;left:0;right:0;height:var(--recommendation-row-height,112px);z-index:2;border-bottom:1px solid color-mix(in srgb,var(--surface-text) 15%,transparent)}.content-rec-row>[data-edit-layer]{position:absolute;top:50%;translate:0 -50%}.content-rec-row>span{left:30px;font:900 42px/1 var(--font-display);color:var(--accent)}.content-rec-row>b{left:116px;width:390px;font:800 42px/1.1 var(--font-heading);color:var(--surface-text)}.content-rec-row>p{left:535px;right:180px;margin:0;font:500 36px/1.4 var(--font-body);color:var(--surface-muted)}.content-rec-row>em{right:34px;padding:10px 14px;border:1px solid var(--accent);border-radius:999px;font:800 36px/1 var(--font-mono);font-style:normal;color:var(--accent)}.content-rec-row.row-1{background:color-mix(in srgb,var(--accent) 8%,transparent)}.content-rationale span,.content-impact-note span{font:650 36px/1.35 var(--font-body);color:var(--text)}
.content-priority-card{display:block}.content-priority-card .diagram-node-bg{border-radius:16px}.content-priority-number{left:32px;top:30px;font:900 64px/.9 var(--font-display);color:var(--accent)}.content-priority-card>em{right:30px;top:34px;padding:9px 12px;border:1px solid var(--accent);border-radius:999px;font:800 36px/1 var(--font-mono);font-style:normal;color:var(--accent)}.content-priority-card>b{left:32px;right:30px;top:122px;font:850 42px/1.08 var(--font-heading);letter-spacing:-.035em;color:var(--surface-text)}.content-priority-card>p{left:32px;right:32px;top:190px;margin:0;font:500 36px/1.45 var(--font-body);color:var(--surface-muted);text-wrap:balance}.content-priority-card>strong{left:32px;bottom:76px;font:850 48px/1 var(--font-heading);color:var(--surface-text)}.content-priority-card>i{left:32px;right:32px;bottom:34px;height:14px;border-radius:999px;background:linear-gradient(90deg,var(--accent) 0 var(--allocation),color-mix(in srgb,var(--surface-text) 12%,transparent) var(--allocation) 100%)}
[data-theme="brand-editorial"] .content-logo-panel .diagram-node-bg,[data-theme="brand-editorial"] .content-palette-panel .diagram-node-bg,[data-theme="brand-editorial"] .content-voice-panel .diagram-node-bg,[data-theme="brand-editorial"] .content-do-panel .diagram-node-bg,[data-theme="brand-editorial"] .content-rec-stack .diagram-node-bg,[data-theme="brand-editorial"] .content-priority-card .diagram-node-bg{border-radius:0}[data-theme="brand-editorial"] .content-logo-panel>p,[data-theme="brand-editorial"] .content-type-pair>span,[data-theme="brand-editorial"] .content-voice-item>p,[data-theme="brand-editorial"] .content-rec-row>p,[data-theme="brand-editorial"] .content-priority-card>p{font-family:var(--font-display)}
.sequence-stage-card,.sequence-takeaway,.sequence-gantt,.sequence-process-node,.sequence-note,.sequence-timeline,.sequence-vertical{display:block}.sequence-stage-card .diagram-node-bg,.sequence-gantt .diagram-node-bg,.sequence-process-node .diagram-node-bg,.sequence-timeline .diagram-node-bg,.sequence-vertical .diagram-node-bg{border-radius:16px}.sequence-stage-card>span{left:34px;top:24px;font:900 66px/.9 var(--font-display);color:var(--accent)}.sequence-stage-card>em{left:34px;right:auto;top:88px;width:max-content;padding:9px 12px;border:1px solid var(--accent);border-radius:999px;font:800 36px/1 var(--font-mono);font-style:normal;color:var(--accent);white-space:nowrap}.sequence-stage-card>b{left:34px;right:34px;top:166px;font:850 42px/1.08 var(--font-heading);color:var(--surface-text)}.sequence-stage-card>p{left:34px;right:34px;top:230px;margin:0;font:500 36px/1.42 var(--font-body);color:var(--surface-muted);text-wrap:pretty}.sequence-stage-card.stage-2 .diagram-node-bg{border-color:color-mix(in srgb,var(--support-accent) 72%,transparent)}.sequence-stage-card.stage-3 .diagram-node-bg{background:color-mix(in srgb,var(--accent) 8%,var(--surface))}.sequence-stage-connectors path,.sequence-process-connectors path{stroke-width:5}
.sequence-takeaway .diagram-node-bg,.sequence-note .diagram-node-bg{border:0;border-left:8px solid var(--accent);border-radius:4px;background:color-mix(in srgb,var(--accent) 9%,var(--bg))}.sequence-takeaway span{left:36px;right:36px;top:30px;text-align:center;font:650 36px/1.35 var(--font-body);color:var(--text)}
.sequence-gantt .diagram-node-bg{background:color-mix(in srgb,var(--surface) 88%,var(--bg))}.gantt-header{position:absolute;left:0;right:0;top:0;height:72px;border-bottom:1px solid color-mix(in srgb,var(--surface-text) 18%,transparent)}.gantt-header span{position:absolute;top:28px;text-align:center;font:800 36px/1 var(--font-mono);color:var(--surface-muted)}.gantt-task-labels b{position:absolute;left:28px;width:250px;height:70px;display:flex;align-items:center;font:750 42px/1.2 var(--font-heading);color:var(--surface-text)}.gantt-grid{position:absolute;left:0;right:0;top:72px;bottom:0;background-image:linear-gradient(color-mix(in srgb,var(--surface-text) 10%,transparent) 1px,transparent 1px);background-size:100% 82px}.gantt-grid i{position:absolute;top:0;bottom:0;width:1px;background:color-mix(in srgb,var(--surface-text) 12%,transparent)}.gantt-bar{border-radius:8px;background:var(--accent)}.gantt-bar.done{background:color-mix(in srgb,var(--support-accent) 74%,var(--surface))}.gantt-bar.next{background:color-mix(in srgb,var(--surface-text) 18%,var(--surface));border:2px dashed var(--accent)}
.sequence-process-node>span{left:50%;top:32px;translate:-50% 0;width:76px;height:76px;display:grid;place-content:center;border:2px solid var(--accent);border-radius:50%;font:900 36px/1 var(--font-heading);color:var(--accent)}.sequence-process-node>b{left:28px;right:28px;top:142px;font:850 42px/1.08 var(--font-heading);color:var(--surface-text)}.sequence-process-node>p{left:28px;right:28px;top:202px;margin:0;font:500 36px/1.42 var(--font-body);color:var(--surface-muted);text-wrap:balance}.sequence-process-node.node-2 .diagram-node-bg,.sequence-process-node.node-4 .diagram-node-bg{border-color:color-mix(in srgb,var(--support-accent) 72%,transparent)}.sequence-process-node.node-5 .diagram-node-bg{background:color-mix(in srgb,var(--accent) 8%,var(--surface))}.sequence-note span{left:36px;right:36px;top:34px;font:600 36px/1.4 var(--font-body);color:var(--text)}
.sequence-timeline .diagram-node-bg{border:0;background:transparent}.timeline-axis{left:100px;right:100px;top:284px;height:4px;border-radius:999px;background:linear-gradient(90deg,var(--accent),var(--support-accent))}.timeline-milestone{position:absolute;z-index:2;text-align:center}.timeline-milestone>[data-edit-layer]{position:absolute}.timeline-milestone>span{left:16px;right:16px;top:18px;font:850 36px/1 var(--font-heading);color:var(--accent)}.timeline-milestone>b{left:16px;right:16px;top:58px;font:750 42px/1.2 var(--font-body);color:var(--surface-text)}.timeline-milestone>p{left:18px;right:18px;top:102px;margin:0;font:500 36px/1.35 var(--font-body);color:var(--surface-muted)}.timeline-milestone>i{width:16px;height:65px;border-radius:999px;background:var(--accent)}.timeline-milestone>i:after{content:"";position:absolute;left:-10px;bottom:-12px;width:32px;height:32px;border:6px solid var(--bg);border-radius:50%;background:var(--accent);box-shadow:0 0 0 2px var(--accent)}.timeline-milestone.item-2>i:after,.timeline-milestone.item-4>i:after,.timeline-milestone.item-6>i:after{top:-12px;bottom:auto}
.sequence-vertical .diagram-node-bg{border:0;background:transparent}.timeline-vertical-line{left:222px;top:32px;width:4px;height:570px;border-radius:999px;background:linear-gradient(var(--accent),var(--support-accent))}.timeline-vertical-event{position:absolute;left:0;right:0;height:118px;z-index:2;border-bottom:1px solid color-mix(in srgb,var(--text) 12%,transparent)}.timeline-vertical-event>[data-edit-layer]{position:absolute}.timeline-vertical-event>span{left:0;top:40px;width:180px;text-align:right;font:800 36px/1 var(--font-mono);color:var(--accent)}.timeline-vertical-event>i{left:207px;top:32px;width:34px;height:34px;border:7px solid var(--bg);border-radius:50%;background:var(--accent);box-shadow:0 0 0 2px var(--accent)}.timeline-vertical-event>b{left:285px;top:24px;width:420px;font:850 42px/1.1 var(--font-heading);color:var(--text)}.timeline-vertical-event>p{left:740px;right:28px;top:20px;margin:0;font:500 36px/1.45 var(--font-body);color:var(--muted)}
[data-theme="brand-editorial"] .sequence-stage-card .diagram-node-bg,[data-theme="brand-editorial"] .sequence-gantt .diagram-node-bg,[data-theme="brand-editorial"] .sequence-process-node .diagram-node-bg{border-radius:0}[data-theme="brand-editorial"] .sequence-stage-card>p,[data-theme="brand-editorial"] .sequence-process-node>p,[data-theme="brand-editorial"] .timeline-vertical-event>p{font-family:var(--font-display)}
.title-flow-stack{position:absolute;display:flex;flex-direction:column;pointer-events:none}.title-flow-stack[data-layout-flow-align="start"]{align-items:flex-start}.title-flow-stack[data-layout-flow-align="center"]{align-items:center}.title-flow-stack[data-layout-flow-align="end"]{align-items:flex-end}.title-flow-stack[data-layout-flow-gap="standard"]{gap:16px}.title-flow-stack>.el{position:relative;flex:0 0 auto;pointer-events:auto}.layout-flow-follow-region{position:absolute;pointer-events:none}.layout-flow-follow-region>.el{pointer-events:auto}
.cover-center-area{position:absolute;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:30px;text-align:center}.cover-center-area>.el{position:relative;flex:0 0 auto}.cover-center-area.explicit-center-stack{display:flex}.cover-center-area.explicit-center-stack>.el{position:relative;flex:0 0 auto}.cover-center-title,.cover-center-subtitle,.cover-center-speaker,.cover-center-org{display:block;padding:0;border:0;border-radius:0;background:transparent;text-align:center}.cover-center-title{font:900 96px/1.08 var(--font-heading);letter-spacing:-.06em;color:var(--text)}.cover-center-rule{padding:0;border:0;border-radius:999px;background:var(--accent)}.cover-center-subtitle{font:600 36px/1.45 var(--font-body);color:var(--muted)}.cover-center-speaker{margin-top:20px;font:800 36px/1 var(--font-heading);letter-spacing:.08em;color:var(--text)}.cover-center-org{font:750 36px/1 var(--font-mono);letter-spacing:.17em;color:var(--accent)}.cover-edge-decor{z-index:2;padding:0;border:0;border-radius:0;background:linear-gradient(90deg,var(--accent),var(--support-accent))}.cover-edge-decor.decor-b,.cover-edge-decor.decor-d{background:linear-gradient(var(--accent),var(--support-accent))}
.cover-center-title-double-frame{z-index:0;overflow:visible}.cover-frame-title-stack{z-index:3;position:absolute;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:24px;pointer-events:none;text-align:center}.cover-frame-title-stack>.el{position:relative;flex:0 0 auto;pointer-events:auto;text-align:center}.cover-frame-title,.cover-frame-subtitle,.cover-frame-speaker,.cover-frame-org{display:block;padding:0;border:0;border-radius:0;background:transparent;text-align:center}.cover-frame-title{font:850 104px/1.08 var(--font-heading);letter-spacing:-.05em;color:var(--text);text-wrap:balance}.cover-frame-rule{padding:0;border:0;border-radius:999px;background:linear-gradient(90deg,transparent,var(--accent) 22% 78%,transparent)}.cover-frame-subtitle{font:500 38px/1.4 var(--font-body);color:var(--muted);text-wrap:pretty}.cover-frame-speaker{margin-top:20px;font:750 36px/1 var(--font-heading);letter-spacing:.08em;color:var(--text)}.cover-frame-org{font:700 36px/1 var(--font-mono);letter-spacing:.14em;color:var(--accent)}#stage .slide[data-layout-id="cover-center-title-double-frame"]{isolation:isolate}#stage .slide[data-layout-id="cover-center-title-double-frame"]>.content{z-index:1}#stage .slide[data-layout-id="cover-center-title-double-frame"]::before,#stage .slide[data-layout-id="cover-center-title-double-frame"]::after{content:"";display:block;position:absolute;pointer-events:none;box-sizing:border-box;z-index:0;border-radius:4px}#stage .slide[data-layout-id="cover-center-title-double-frame"]::before{inset:18px;border:2px solid color-mix(in srgb,var(--accent) 72%,var(--text))}#stage .slide[data-layout-id="cover-center-title-double-frame"]::after{inset:38px;border:1px solid color-mix(in srgb,var(--accent) 42%,var(--muted))}
.cover-logo{display:block;z-index:5}.cover-logo .diagram-node-bg{border:1px solid color-mix(in srgb,var(--surface-text) 18%,transparent);border-radius:8px;background:color-mix(in srgb,var(--surface) 84%,transparent)}.cover-logo>b{left:16px;top:16px;width:48px;height:48px;display:grid;place-content:center;border:2px solid var(--accent);border-radius:50%;font:900 42px/1 var(--font-heading);color:var(--accent)}.cover-logo>span{left:76px;right:10px;top:32px;font:800 36px/1.2 var(--font-mono);letter-spacing:.08em;color:var(--surface-text)}.cover-logo.inverse .diagram-node-bg{background:rgba(8,12,18,.82);border-color:rgba(255,255,255,.36);backdrop-filter:blur(8px)}.cover-logo.inverse>b{border-color:#fff;color:#fff}.cover-logo.inverse>span{color:#fff}
.cover-variant-frame{z-index:0;overflow:visible}.cover-variant-title,.cover-variant-subtitle,.cover-variant-meta{z-index:3;display:block;padding:0;border:0;border-radius:0;background:transparent}.cover-variant-title{font:900 86px/1.04 var(--font-heading);letter-spacing:-.06em;color:var(--text)}.cover-variant-subtitle{font:600 36px/1.35 var(--font-body);color:var(--muted)}.cover-variant-meta{font:750 36px/1.1 var(--font-mono);letter-spacing:.04em;color:var(--accent)}.cover-focal-field{z-index:1;display:block;padding:0;border:1px solid color-mix(in srgb,var(--accent) 34%,transparent);overflow:visible;background:color-mix(in srgb,var(--surface) 62%,transparent)}.cover-focal-field i{position:absolute;display:block;pointer-events:none}.cover-focal-field.rail-field{border:0;border-left:8px solid var(--accent);background:linear-gradient(135deg,color-mix(in srgb,var(--accent) 9%,transparent),transparent 68%)}.cover-focal-field.rail-field i:nth-child(1){left:18%;top:20%;width:64%;height:1px;background:var(--support-accent);opacity:.72}.cover-focal-field.rail-field i:nth-child(2){left:42%;top:20%;width:1px;height:62%;background:var(--accent);opacity:.58}.cover-focal-field.rail-field i:nth-child(3){right:14%;bottom:18%;width:9px;height:9px;border-radius:50%;background:var(--accent)}.cover-focal-field.focal-column-field{border-right:8px solid var(--support-accent);background:linear-gradient(90deg,color-mix(in srgb,var(--support-accent) 12%,transparent),transparent 74%)}.cover-focal-field.focal-column-field i:nth-child(1){left:16%;top:20%;width:68%;height:1px;background:var(--accent);opacity:.72}.cover-focal-field.focal-column-field i:nth-child(2){left:24%;top:42%;width:48%;height:8px;border-top:1px solid var(--support-accent);border-bottom:1px solid var(--support-accent);opacity:.58}.cover-focal-field.focal-column-field i:nth-child(3){left:22%;bottom:18%;width:12px;height:12px;border:2px solid var(--accent);border-radius:50%}.cover-focal-field.center-field{border-top:5px solid var(--accent);border-bottom:5px solid var(--support-accent);background:linear-gradient(135deg,transparent 0 42%,color-mix(in srgb,var(--accent) 8%,transparent) 42% 58%,transparent 58%)}.cover-focal-field.center-field i:nth-child(1){left:20%;top:50%;width:60%;height:1px;background:var(--accent);opacity:.62}.cover-focal-field.center-field i:nth-child(2){left:50%;top:18%;width:1px;height:64%;background:var(--support-accent);opacity:.62}.cover-focal-field.center-field i:nth-child(3){left:calc(50% - 6px);top:calc(50% - 6px);width:12px;height:12px;border:2px solid var(--accent);border-radius:50%;background:var(--surface)}.cover-focal-field.lower-left-field{border:0;border-top:6px solid var(--support-accent);background:linear-gradient(180deg,color-mix(in srgb,var(--support-accent) 10%,transparent),transparent 72%)}.cover-focal-field.lower-left-field i:nth-child(1){left:14%;top:24%;width:72%;height:1px;background:var(--accent);opacity:.7}.cover-focal-field.lower-left-field i:nth-child(2){left:26%;top:44%;width:44%;height:44%;border-left:1px solid var(--support-accent);border-bottom:1px solid var(--support-accent);opacity:.58}.cover-focal-field.lower-left-field i:nth-child(3){left:22%;bottom:14%;width:10px;height:10px;border-radius:50%;background:var(--accent)}.cover-focal-field.opposing-field{border:0;background:linear-gradient(135deg,transparent 0 36%,color-mix(in srgb,var(--accent) 8%,transparent) 36% 38%,transparent 38%),linear-gradient(90deg,transparent 0 52%,color-mix(in srgb,var(--support-accent) 9%,transparent) 52% 54%,transparent 54%)}.cover-focal-field.opposing-field i:nth-child(1){left:8%;top:28%;width:84%;height:1px;background:var(--accent);opacity:.64}.cover-focal-field.opposing-field i:nth-child(2){left:52%;top:8%;width:1px;height:84%;background:var(--support-accent);opacity:.58}.cover-focal-field.opposing-field i:nth-child(3){right:8%;top:24%;width:12px;height:12px;border:2px solid var(--accent);border-radius:50%;background:var(--surface)}
.cover-split-frame,.cover-overlay-frame,.cover-hero-brand-frame,.cover-hero-frame{z-index:0;overflow:visible}.cover-split-frame.photo-left::after{content:"";position:absolute;z-index:2;left:768px;top:0;width:64px;height:1080px;pointer-events:none;background:linear-gradient(90deg,transparent 0 48px,var(--accent) 48px 51px,transparent 51px),linear-gradient(90deg,color-mix(in srgb,var(--surface) 94%,var(--bg)) 0 18px,color-mix(in srgb,var(--bg) 96%,#fff) 18px 100%)}.cover-media-field{z-index:0;display:block;padding:0;border:0;border-radius:0;overflow:hidden;background:linear-gradient(120deg,rgba(6,12,22,.68),transparent 58%),radial-gradient(circle at 72% 26%,color-mix(in srgb,var(--accent) 74%,transparent),transparent 31%),linear-gradient(145deg,color-mix(in srgb,var(--support-accent) 82%,#111827),#08111f 68%)}.cover-media-field:after{content:"";position:absolute;inset:0;background-image:radial-gradient(rgba(255,255,255,.14) .8px,transparent .8px);background-size:7px 7px;opacity:.16}.cover-media-field i{position:absolute;bottom:-120px;width:260px;border-radius:180px 180px 0 0;background:rgba(255,255,255,.11);border-top:3px solid color-mix(in srgb,var(--accent) 62%,transparent)}.cover-media-field i:nth-child(1){right:40px;height:78%}.cover-media-field i:nth-child(2){right:320px;height:58%}.cover-media-field i:nth-child(3){right:600px;height:42%}
.cover-split-kicker,.cover-split-title,.cover-split-subtitle,.cover-split-speaker,.cover-split-org{z-index:4;display:block;padding:0;border:0;border-radius:0;background:transparent}.cover-split-kicker{font:800 36px/1 var(--font-mono);letter-spacing:.18em;color:var(--accent)}.cover-split-title{font:900 82px/1.06 var(--font-heading);letter-spacing:-.055em;color:var(--text)}.cover-split-subtitle{font:600 36px/1.5 var(--font-body);color:var(--muted)}.cover-split-speaker{font:800 36px/1 var(--font-heading);color:var(--text)}.cover-split-org{font:750 36px/1 var(--font-mono);letter-spacing:.15em;color:var(--accent)}
.cover-overlay-canvas{position:absolute;inset:0;background:var(--bg)}.cover-overlay-block{display:block;z-index:3}.cover-overlay-block .diagram-node-bg{border:0;border-radius:0;background:color-mix(in srgb,var(--surface) 84%,transparent);backdrop-filter:blur(12px)}.cover-overlay-block>span{left:56px;top:54px;font:800 36px/1 var(--font-mono);letter-spacing:.18em;color:var(--accent)}.cover-overlay-block>b{left:56px;right:48px;top:118px;font:900 76px/1.07 var(--font-heading);letter-spacing:-.055em;color:var(--surface-text)}.cover-overlay-block>p{left:58px;right:54px;bottom:66px;margin:0;font:600 36px/1.48 var(--font-body);color:var(--surface-muted)}.cover-overlay-accent{z-index:4;padding:0;border:0;border-radius:0;background:color-mix(in srgb,var(--surface) 84%,transparent);backdrop-filter:blur(12px)}
.cover-hero-scrim{position:absolute;inset:0;background:linear-gradient(90deg,rgba(2,8,16,.82) 0 46%,rgba(2,8,16,.32) 66%,transparent)}.cover-bottom-scrim{position:absolute;inset:0;background:linear-gradient(0deg,rgba(2,8,16,.88) 0 42%,rgba(2,8,16,.18) 74%,transparent)}.cover-hero-title,.cover-hero-subtitle,.cover-hero-speaker,.cover-hero-org,.cover-bottom-title,.cover-bottom-subtitle,.cover-bottom-meta{z-index:4;display:block;padding:0;border:0;border-radius:0;background:transparent;color:#fff}.cover-hero-title{font:900 90px/1.04 var(--font-heading);letter-spacing:-.06em}.cover-hero-subtitle{font:600 36px/1.48 var(--font-body);color:rgba(255,255,255,.82)}.cover-hero-speaker{font:800 36px/1 var(--font-heading)}.cover-hero-org{font:750 36px/1 var(--font-mono);letter-spacing:.16em;color:color-mix(in srgb,var(--accent) 72%,#fff)}.cover-bottom-title{font:900 88px/1.04 var(--font-heading);letter-spacing:-.058em}.cover-bottom-subtitle{font:600 36px/1.45 var(--font-body);color:rgba(255,255,255,.82)}.cover-bottom-meta{font:750 36px/1 var(--font-mono);letter-spacing:.12em;color:#fff}
[data-theme="brand-editorial"] .cover-center-subtitle,[data-theme="brand-editorial"] .cover-split-subtitle,[data-theme="brand-editorial"] .cover-overlay-block>p,[data-theme="brand-editorial"] .cover-hero-subtitle,[data-theme="brand-editorial"] .cover-bottom-subtitle{font-family:var(--font-display)}[data-theme="clinical-report"] .cover-media-field{background:linear-gradient(145deg,var(--support-accent),#0b1726)}[data-theme="brand-editorial"] .cover-overlay-block .diagram-node-bg{background:color-mix(in srgb,var(--surface) 92%,transparent)}
.dataviz-annotation-chart,.heat-table,.dataviz-map,.map-data-card,.dataviz-multiline,.dataviz-radar,.radar-legend{display:block}.dataviz-annotation-chart .diagram-node-bg,.dataviz-map .diagram-node-bg,.map-data-card .diagram-node-bg,.dataviz-multiline .diagram-node-bg,.dataviz-radar .diagram-node-bg,.radar-legend .diagram-node-bg{border-radius:16px}.dataviz-annotation-chart>.python-matplotlib-chart,.dataviz-multiline>.python-matplotlib-chart{left:0;top:20px;width:1728px;height:580px}.dataviz-xlabels{position:absolute;left:0;right:0;bottom:72px;height:44px;display:flex;align-items:flex-start;justify-content:space-between}.dataviz-xlabels span{position:static;width:64px;text-align:center;font:700 36px/1 var(--font-mono);color:var(--surface-muted)}
.dataviz-annotation-card{display:block;z-index:5}.dataviz-annotation-card .diagram-node-bg{border-radius:12px;background:color-mix(in srgb,var(--surface) 94%,var(--accent));box-shadow:0 14px 34px color-mix(in srgb,var(--text) 10%,transparent)}.dataviz-annotation-card>span{left:24px;top:26px;font:900 36px/1 var(--font-display);color:var(--accent)}.dataviz-annotation-card>b{left:84px;right:110px;top:30px;font:800 42px/1.1 var(--font-heading);color:var(--surface-text)}.dataviz-annotation-card>strong{right:22px;top:26px;font:900 36px/1 var(--font-heading);color:var(--accent)}.dataviz-annotation-card>i{left:34px;bottom:-84px;width:3px;height:84px;background:var(--accent)}
.heat-table>.python-matplotlib-chart{left:0;top:0;width:1636px;height:600px}.heat-legend{padding:0;border:0;border-radius:999px;background:linear-gradient(var(--accent),color-mix(in srgb,var(--accent) 8%,var(--surface)))}
.dataviz-map>svg{left:100px;top:20px;width:850px;height:600px}.map-region-shape{stroke:var(--bg);stroke-width:8;stroke-linejoin:round}.map-region-shape.region-1{fill:color-mix(in srgb,var(--accent) 88%,var(--surface))}.map-region-shape.region-2{fill:color-mix(in srgb,var(--accent) 68%,var(--surface))}.map-region-shape.region-3{fill:color-mix(in srgb,var(--accent) 52%,var(--surface))}.map-region-shape.region-4{fill:color-mix(in srgb,var(--accent) 36%,var(--surface))}.map-region-shape.region-5{fill:color-mix(in srgb,var(--accent) 20%,var(--surface))}.map-outline{fill:color-mix(in srgb,var(--support-accent) 22%,var(--surface));stroke:var(--accent);stroke-width:7}.city-pin circle:first-child{fill:var(--surface);stroke:var(--accent);stroke-width:7}.city-pin circle:last-child{fill:var(--accent)}.map-caption{left:32px;bottom:28px;font:750 36px/1 var(--font-mono);letter-spacing:.14em;color:var(--surface-muted)}
.map-data-card{display:block}.map-data-card>span{left:28px;top:28px;font:900 36px/1 var(--font-display);color:var(--accent)}.map-data-card>b{left:92px;top:32px;font:850 42px/1 var(--font-heading);color:var(--surface-text)}.map-data-card>strong{right:28px;top:28px;font:900 48px/1 var(--font-heading);color:var(--accent)}.map-data-card>p{left:92px;right:30px;top:92px;margin:0;font:500 36px/1.4 var(--font-body);color:var(--surface-muted)}.map-data-card.card-2 .diagram-node-bg{border-color:color-mix(in srgb,var(--support-accent) 72%,transparent)}.map-data-card.card-3 .diagram-node-bg{background:color-mix(in srgb,var(--accent) 8%,var(--surface))}
.python-matplotlib-chart{position:absolute;overflow:visible}.dataviz-radar>.python-matplotlib-chart{left:210px;top:0;width:700px;height:660px}.dataviz-radar>span{font:750 36px/1 var(--font-body);color:var(--surface-muted)}.radar-legend-row{position:absolute;left:34px;right:34px;height:120px;display:flex;align-items:center;gap:18px;border-bottom:1px solid color-mix(in srgb,var(--surface-text) 15%,transparent)}.radar-legend-row.row-1{top:100px}.radar-legend-row.row-2{top:230px}.radar-legend-row>i{position:static;width:42px;height:8px;background:var(--support-accent)}.radar-legend-row.row-2>i{background:var(--accent)}.radar-legend-row>b{position:static;font:800 42px/1 var(--font-heading);color:var(--surface-text)}.radar-legend-row>span{position:static;margin-left:auto;font:900 36px/1 var(--font-heading);color:var(--accent)}
[data-theme="brand-editorial"] .dataviz-annotation-chart .diagram-node-bg,[data-theme="brand-editorial"] .dataviz-map .diagram-node-bg,[data-theme="brand-editorial"] .map-data-card .diagram-node-bg,[data-theme="brand-editorial"] .dataviz-multiline .diagram-node-bg,[data-theme="brand-editorial"] .dataviz-radar .diagram-node-bg,[data-theme="brand-editorial"] .radar-legend .diagram-node-bg{border-radius:0}
.media-photo,.media-bio-panel,.media-icon-list,.media-overlay-title,.media-testimonial-mark,.media-testimonial-logo{display:block}.media-photo{overflow:hidden}.media-photo .diagram-node-bg{border:0;border-radius:18px;background:linear-gradient(145deg,color-mix(in srgb,var(--support-accent) 74%,var(--bg)),color-mix(in srgb,var(--accent) 38%,var(--surface)) 58%,var(--surface));box-shadow:0 22px 54px color-mix(in srgb,var(--text) 12%,transparent)}.media-photo-art{left:9%;right:9%;top:9%;bottom:9%;border-radius:48% 52% 38% 62%/42% 34% 66% 58%;background:radial-gradient(circle at 66% 24%,color-mix(in srgb,var(--accent-text) 58%,transparent) 0 7%,transparent 8%),linear-gradient(155deg,color-mix(in srgb,var(--surface) 58%,transparent),color-mix(in srgb,var(--accent) 44%,transparent));clip-path:polygon(0 14%,72% 0,100% 40%,88% 100%,18% 86%)}.media-photo-accent{right:0;bottom:0;width:34%;height:30%;background:var(--accent);clip-path:polygon(36% 0,100% 0,100% 100%,0 100%)}.media-photo-label{left:26px;bottom:24px;padding:10px 13px;background:color-mix(in srgb,var(--bg) 76%,transparent);font:800 36px/1 var(--font-mono);letter-spacing:.14em;color:var(--text)}
.media-executive-photo .media-photo-art{left:8%;right:8%;top:6%;bottom:0;border-radius:46% 46% 10% 10%;clip-path:polygon(22% 0,78% 0,96% 36%,88% 100%,12% 100%,4% 36%)}.media-executive-name{font:900 96px/.94 var(--font-heading);letter-spacing:-.06em;color:var(--text)}.media-executive-role{font:800 36px/1.15 var(--font-heading);color:var(--accent)}.media-executive-meta{font:750 36px/1 var(--font-mono);letter-spacing:.14em;color:var(--muted)}.media-bio-panel .diagram-node-bg{border:0;border-top:5px solid var(--accent);border-radius:0;background:color-mix(in srgb,var(--surface) 76%,var(--bg))}.media-panel-kicker{left:36px;top:30px;font:800 36px/1 var(--font-mono);letter-spacing:.16em;color:var(--accent)}.media-bio-row{position:absolute;left:36px;right:36px;height:84px;border-top:1px solid color-mix(in srgb,var(--surface-text) 15%,transparent)}.media-bio-row.row-1{top:86px}.media-bio-row.row-2{top:174px}.media-bio-row.row-3{top:262px}.media-bio-row>[data-edit-layer]{position:absolute;z-index:2}.media-bio-row>span{left:0;top:28px;font:850 36px/1 var(--font-mono);color:var(--accent)}.media-bio-row>p{left:68px;right:0;top:20px;margin:0;font:600 36px/1.35 var(--font-body);color:var(--surface-text)}
.media-split-title{font:900 68px/1.08 var(--font-heading);letter-spacing:-.05em;color:var(--text)}.media-split-body{font:500 36px/1.5 var(--font-body);color:var(--muted)}.media-icon-list .diagram-node-bg{border:0;border-left:7px solid var(--accent);border-radius:0;background:color-mix(in srgb,var(--surface) 70%,var(--bg))}.media-icon-row{position:absolute;left:36px;right:36px;height:78px;border-bottom:1px solid color-mix(in srgb,var(--surface-text) 15%,transparent)}.media-icon-row.row-1{top:25px}.media-icon-row.row-2{top:105px}.media-icon-row.row-3{top:185px}.media-icon-row>[data-edit-layer]{position:absolute;z-index:2}.media-icon-row>span{left:0;top:28px;font:850 36px/1 var(--font-mono);color:var(--accent)}.media-icon-row>b{left:72px;right:0;top:21px;font:750 42px/1.2 var(--font-heading);color:var(--surface-text)}.media-split-photo .media-photo-art{left:7%;right:7%;top:7%;bottom:7%;clip-path:polygon(0 0,74% 0,100% 34%,90% 100%,16% 92%)}
.media-gallery-subtitle{font:500 36px/1.4 var(--font-body);color:var(--muted)}.media-gallery-caption{font:700 36px/1 var(--font-mono);letter-spacing:.12em;color:var(--muted)}.media-gallery-tile .diagram-node-bg{border-radius:12px}.media-gallery-tile .media-photo-label{left:18px;bottom:16px}.media-gallery-tile.tile-2 .diagram-node-bg,.media-gallery-tile.tile-5 .diagram-node-bg{background:linear-gradient(145deg,color-mix(in srgb,var(--accent) 56%,var(--surface)),var(--support-accent))}.media-gallery-tile.tile-3 .diagram-node-bg{background:linear-gradient(155deg,var(--surface),color-mix(in srgb,var(--support-accent) 66%,var(--bg)))}.media-gallery-tile.tile-4 .media-photo-art{clip-path:circle(46% at 50% 50%)}
.media-framed-photo{box-shadow:inset 0 0 0 24px var(--bg)}.media-framed-photo .diagram-node-bg{inset:24px;border-radius:0}.media-framed-photo .media-photo-art{left:10%;right:10%;top:9%;bottom:9%}.media-overlay-title .diagram-node-bg{border:0;border-radius:0;background:var(--accent)}.media-overlay-title>span{left:48px;top:46px;font:800 42px/1 var(--font-mono);letter-spacing:.16em;color:var(--accent-text)}.media-overlay-title>b{left:48px;right:40px;top:102px;font:900 64px/1.03 var(--font-heading);letter-spacing:-.05em;color:var(--accent-text)}.media-overlay-body{font:550 36px/1.55 var(--font-body);color:var(--muted)}
.media-testimonial-mark .diagram-node-bg{border:0;border-radius:0;background:transparent}.media-testimonial-mark>span{left:0;top:0;font:900 210px/.78 var(--font-display);color:color-mix(in srgb,var(--accent) 66%,transparent)}.media-testimonial-quote{font:800 64px/1.38 var(--font-heading);letter-spacing:-.04em;color:var(--text)}.media-testimonial-photo{border-radius:50%}.media-testimonial-photo .diagram-node-bg,.media-testimonial-photo .media-photo-art{border-radius:50%;clip-path:none}.media-testimonial-photo .media-photo-label,.media-testimonial-photo .media-photo-accent{display:none}.media-testimonial-name{font:850 42px/1 var(--font-heading);color:var(--text)}.media-testimonial-role{font:750 36px/1 var(--font-mono);letter-spacing:.14em;color:var(--muted)}.media-testimonial-logo .diagram-node-bg{border:2px solid var(--accent);border-radius:0;background:transparent}.media-testimonial-logo>b{left:28px;top:24px;font:900 48px/1 var(--font-heading);color:var(--accent)}.media-testimonial-logo>span{right:26px;top:52px;font:800 36px/1 var(--font-mono);letter-spacing:.14em;color:var(--muted)}
[data-theme="brand-editorial"] .media-photo .diagram-node-bg,[data-theme="brand-editorial"] .media-gallery-tile .diagram-node-bg{border-radius:0}[data-theme="brand-editorial"] .media-bio-row>p,[data-theme="brand-editorial"] .media-split-body,[data-theme="brand-editorial"] .media-gallery-subtitle,[data-theme="brand-editorial"] .media-overlay-body,[data-theme="brand-editorial"] .media-testimonial-quote{font-family:var(--font-display)}[data-theme="clinical-report"] .media-photo .diagram-node-bg{box-shadow:none}[data-theme="product-strategy-signal"] .media-overlay-title .diagram-node-bg{background:var(--accent)}
.module-subtitle{font:500 36px/1.4 var(--font-body);color:var(--muted)}.module-card,.module-icon-cell,.module-person-card,.module-team-card{display:block}.module-card .diagram-node-bg,.module-icon-cell .diagram-node-bg,.module-person-card .diagram-node-bg,.module-team-card .diagram-node-bg{border-radius:16px;box-shadow:0 14px 34px color-mix(in srgb,var(--text) 7%,transparent)}.module-card.card-2 .diagram-node-bg,.module-card.card-4 .diagram-node-bg,.module-card.card-6 .diagram-node-bg,.module-card.card-8 .diagram-node-bg{border-color:color-mix(in srgb,var(--support-accent) 72%,transparent)}.module-card .module-number{left:34px;top:30px;font:900 56px/.9 var(--font-display);color:var(--accent)}.module-card .module-tag{right:30px;top:34px;padding:9px 11px;border:1px solid var(--accent);border-radius:999px;font:800 36px/1 var(--font-mono);font-style:normal;color:var(--accent)}.module-card>b{left:118px;right:30px;top:37px;font:850 42px/1.05 var(--font-heading);letter-spacing:-.03em;color:var(--surface-text)}.module-card>p{left:118px;right:34px;top:91px;margin:0;font:500 36px/1.38 var(--font-body);color:var(--surface-muted)}.module-card>i{left:118px;right:34px;bottom:28px;height:8px;background:linear-gradient(90deg,var(--accent) 0 62%,color-mix(in srgb,var(--surface-text) 12%,transparent) 62%)}
.module-card.count-2 .module-number{left:46px;top:48px;font-size:104px}.module-card.count-2 .module-tag{right:44px;top:54px;font-size:36px}.module-card.count-2>b{left:48px;right:48px;top:190px;font-size:58px}.module-card.count-2>p{left:48px;right:60px;top:285px;font-size:36px;line-height:1.5}.module-card.count-2>i{left:48px;right:48px;bottom:54px;height:14px}.module-card.count-3 .module-number{left:40px;top:44px;font-size:84px}.module-card.count-3 .module-tag{right:38px;top:50px}.module-card.count-3>b{left:40px;right:40px;top:170px;font-size:45px}.module-card.count-3>p{left:40px;right:44px;top:246px;font-size:36px;line-height:1.48}.module-card.count-3>i{left:40px;right:40px;bottom:48px;height:12px}.module-card.count-8 .module-number{font-size:48px}.module-card.count-8>b{left:102px;font-size:42px}.module-card.count-8>p{left:102px;font-size:36px}.module-card.count-8>i{left:102px}
.module-icon-cell .diagram-node-bg{background:color-mix(in srgb,var(--surface) 88%,var(--bg))}.module-icon-shape{left:188px;top:44px;width:160px;height:160px;border:4px solid var(--accent);border-radius:38% 62% 54% 46%;background:radial-gradient(circle at 66% 32%,var(--accent) 0 18%,transparent 19%),color-mix(in srgb,var(--accent) 10%,var(--surface));transform:rotate(8deg)}.module-icon-cell:nth-of-type(even) .module-icon-shape{border-color:var(--support-accent);transform:rotate(-8deg)}.module-icon-cell>span{left:30px;top:28px;font:900 46px/.9 var(--font-display);color:var(--accent)}.module-icon-cell>b{left:0;right:0;bottom:32px;text-align:center;font:850 42px/1 var(--font-heading);color:var(--surface-text)}
.module-person-photo{left:160px;top:48px;width:220px;height:220px;border-radius:50%;background:radial-gradient(circle at 52% 32%,color-mix(in srgb,var(--accent-text) 56%,transparent) 0 12%,transparent 13%),linear-gradient(145deg,var(--support-accent),var(--accent));box-shadow:0 0 0 12px color-mix(in srgb,var(--accent) 10%,transparent)}.module-person-card>span{left:34px;top:32px;font:900 60px/.9 var(--font-display);color:var(--accent)}.module-person-card>b{left:34px;right:34px;top:325px;text-align:center;font:850 42px/1 var(--font-heading);color:var(--surface-text)}.module-person-card>em{left:34px;right:34px;top:386px;text-align:center;font:800 36px/1 var(--font-mono);letter-spacing:.14em;font-style:normal;color:var(--accent)}.module-person-card>p{left:44px;right:44px;top:448px;margin:0;text-align:center;font:500 36px/1.45 var(--font-body);color:var(--surface-muted)}
.module-team-card .diagram-node-bg{background:color-mix(in srgb,var(--surface) 86%,var(--bg))}.module-team-photo{left:38px;top:72px;width:140px;height:140px;border-radius:50%;background:linear-gradient(145deg,var(--support-accent),var(--accent));box-shadow:0 0 0 9px color-mix(in srgb,var(--accent) 10%,transparent)}.module-team-card>span{right:28px;top:26px;font:900 42px/.9 var(--font-display);color:var(--accent)}.module-team-card>b{left:220px;right:30px;top:88px;font:850 42px/1 var(--font-heading);color:var(--surface-text)}.module-team-card>em{left:222px;right:28px;top:146px;font:700 36px/1.25 var(--font-mono);letter-spacing:.08em;font-style:normal;color:var(--surface-muted)}
[data-theme="brand-editorial"] .module-card .diagram-node-bg,[data-theme="brand-editorial"] .module-icon-cell .diagram-node-bg,[data-theme="brand-editorial"] .module-person-card .diagram-node-bg,[data-theme="brand-editorial"] .module-team-card .diagram-node-bg{border-radius:0;box-shadow:none}[data-theme="brand-editorial"] .module-card>p,[data-theme="brand-editorial"] .module-person-card>p{font-family:var(--font-display)}[data-theme="clinical-report"] .module-card .diagram-node-bg,[data-theme="clinical-report"] .module-icon-cell .diagram-node-bg,[data-theme="clinical-report"] .module-person-card .diagram-node-bg,[data-theme="clinical-report"] .module-team-card .diagram-node-bg{box-shadow:none}
.toc-subtitle{font:500 36px/1.4 var(--font-body);color:var(--muted)}.toc-nav-card,.toc-vertical-row,.toc-panel-row,.toc-panel-grid-card,.toc-panel-feature,.toc-image-row,.toc-number-row,.toc-side-panel,.toc-wide-panel,.toc-number-panel{display:block}.toc-nav-card .diagram-node-bg,.toc-vertical-row .diagram-node-bg,.toc-panel-row .diagram-node-bg,.toc-panel-grid-card .diagram-node-bg,.toc-panel-feature .diagram-node-bg,.toc-image-row .diagram-node-bg,.toc-number-row .diagram-node-bg{border-radius:14px;background:color-mix(in srgb,var(--surface) 88%,var(--bg))}.toc-nav-card.card-2 .diagram-node-bg,.toc-nav-card.card-4 .diagram-node-bg,.toc-nav-card.card-6 .diagram-node-bg,.toc-nav-card.card-8 .diagram-node-bg{border-color:color-mix(in srgb,var(--support-accent) 72%,transparent)}.toc-nav-card>span{left:30px;top:28px;font:900 58px/.9 var(--font-display);color:var(--accent)}.toc-nav-card>b{left:112px;right:34px;top:34px;font:850 42px/1.08 var(--font-heading);letter-spacing:-.03em;color:var(--surface-text)}.toc-nav-card>p{left:112px;right:40px;top:92px;margin:0;font:500 36px/1.38 var(--font-body);color:var(--surface-muted)}.toc-nav-card>i{right:30px;bottom:26px;font:900 36px/1 var(--font-heading);font-style:normal;color:var(--accent)}.toc-nav-card.count-2>span{left:46px;top:48px;font-size:112px}.toc-nav-card.count-2>b{left:48px;right:48px;top:190px;font-size:56px}.toc-nav-card.count-2>p{left:48px;right:60px;top:285px;font-size:36px;line-height:1.5}.toc-nav-card.count-2>i{right:48px;bottom:48px;font-size:52px}.toc-nav-card.count-3>span{left:40px;top:44px;font-size:88px}.toc-nav-card.count-3>b{left:40px;right:40px;top:170px;font-size:44px}.toc-nav-card.count-3>p{left:40px;right:44px;top:246px;font-size:36px;line-height:1.48}.toc-nav-card.count-3>i{right:40px;bottom:44px;font-size:44px}.toc-nav-card.count-8>span{font-size:48px}.toc-nav-card.count-8>b{left:100px;font-size:42px}.toc-nav-card.count-8>p{left:100px;font-size:36px}.toc-nav-card.count-8>i{font-size:36px}
.toc-vertical-row .diagram-node-bg{border:0;border-top:2px solid color-mix(in srgb,var(--accent) 62%,transparent);border-radius:0;background:transparent}.toc-vertical-row>span,.toc-vertical-row>b,.toc-vertical-row>p,.toc-vertical-row>i{top:50%;transform:translateY(-50%)}.toc-vertical-row>span{left:28px;font:900 58px/.9 var(--font-display);color:var(--accent)}.toc-vertical-row>b{left:150px;font:850 42px/1 var(--font-heading);color:var(--text)}.toc-vertical-row>p{left:620px;right:150px;margin:0;font:500 36px/1.35 var(--font-body);color:var(--muted)}.toc-vertical-row>i{right:36px;font:900 36px/1 var(--font-heading);font-style:normal;color:var(--accent)}
.toc-side-panel,.toc-wide-panel{background:var(--accent)}.toc-side-panel .diagram-node-bg,.toc-wide-panel .diagram-node-bg{border:0;border-radius:0;background:var(--accent)}.toc-side-panel>span,.toc-wide-panel>span{left:42px;top:48px;font:800 36px/1 var(--font-mono);letter-spacing:.17em;color:var(--accent-text)}.toc-side-panel>b,.toc-wide-panel>b{left:42px;right:38px;top:150px;font:900 58px/1.02 var(--font-heading);letter-spacing:-.05em;color:var(--accent-text);text-wrap:balance}.toc-side-panel>p,.toc-wide-panel>p{left:42px;right:42px;top:330px;margin:0;font:550 36px/1.55 var(--font-body);color:var(--accent-text)}.toc-side-panel>em,.toc-wide-panel>em{left:42px;bottom:44px;font:750 36px/1 var(--font-mono);letter-spacing:.12em;font-style:normal;color:var(--accent-text)}.toc-panel-row .diagram-node-bg{border:0;border-bottom:1px solid color-mix(in srgb,var(--surface-text) 18%,transparent);border-radius:0;background:color-mix(in srgb,var(--surface) 72%,var(--bg))}.toc-panel-row>span,.toc-panel-row>b,.toc-panel-row>p,.toc-panel-row>i{top:50%;transform:translateY(-50%)}.toc-panel-row>span{left:30px;font:900 56px/.9 var(--font-display);color:var(--accent)}.toc-panel-row>b{left:118px;font:850 42px/1 var(--font-heading);color:var(--surface-text);text-wrap:balance}.toc-panel-row>p{left:430px;right:90px;margin:0;font:500 36px/1.3 var(--font-body);color:var(--surface-muted)}.toc-panel-row>i{right:30px;font:900 36px/1 var(--font-heading);font-style:normal;color:var(--accent)}
.toc-panel-grid-card>span,.toc-panel-feature>span{left:30px;top:30px;font:900 62px/.9 var(--font-display);color:var(--accent)}.toc-panel-grid-card>b,.toc-panel-feature>b{left:30px;right:30px;top:92px;font:850 42px/1.05 var(--font-heading);color:var(--surface-text)}.toc-panel-grid-card>p,.toc-panel-feature>p{left:30px;right:34px;top:142px;margin:0;font:500 36px/1.38 var(--font-body);color:var(--surface-muted)}.toc-panel-grid-card>i,.toc-panel-feature>i{right:28px;bottom:26px;font:900 36px/1 var(--font-heading);font-style:normal;color:var(--accent)}.toc-panel-feature>span{font-size:78px}.toc-panel-feature>b{left:160px;top:44px;font-size:42px}.toc-panel-feature>p{left:160px;top:104px;font-size:36px}.toc-panel-feature>i{bottom:30px;font-size:38px}
.toc-image-field .diagram-node-bg{border-radius:0}.toc-image-title{font:900 64px/1.05 var(--font-heading);letter-spacing:-.05em;color:var(--text)}.toc-image-intro{font:500 36px/1.5 var(--font-body);color:var(--muted)}.toc-image-row .diagram-node-bg{border:0;border-top:2px solid color-mix(in srgb,var(--accent) 54%,transparent);border-radius:0;background:transparent}.toc-image-row>span{left:24px;top:calc(50% - 25px);font:900 50px/.9 var(--font-display);color:var(--accent)}.toc-image-row>b{left:116px;top:calc(50% - 22px);font:850 42px/1 var(--font-heading);color:var(--text)}.toc-image-row>p{display:none}.toc-image-row>i{right:24px;top:calc(50% - 15px);font:900 36px/1 var(--font-heading);font-style:normal;color:var(--accent)}
.toc-number-panel .diagram-node-bg{border:0;border-radius:0;background:var(--accent)}.toc-number-strip{left:0;right:0;height:152px;display:grid;place-content:center;border-bottom:1px solid color-mix(in srgb,var(--accent-text) 26%,transparent);font:900 78px/.9 var(--font-display);color:var(--accent-text)}.toc-number-strip.strip-1{top:0}.toc-number-strip.strip-2{top:152px}.toc-number-strip.strip-3{top:304px}.toc-number-strip.strip-4{top:456px}.toc-number-strip.strip-5{top:608px}.toc-number-row .diagram-node-bg{border:0;border-bottom:1px solid color-mix(in srgb,var(--surface-text) 18%,transparent);border-radius:0;background:transparent}.toc-number-row>span{display:none}.toc-number-row>b{left:34px;top:28px;font:850 42px/1 var(--font-heading);color:var(--text)}.toc-number-row>p{left:420px;right:90px;top:30px;margin:0;font:500 36px/1.3 var(--font-body);color:var(--muted)}.toc-number-row>i{right:28px;top:30px;font:900 36px/1 var(--font-heading);font-style:normal;color:var(--accent)}
.toc-number-cell .diagram-node-bg{border:0;border-top:5px solid var(--accent);border-radius:0;background:color-mix(in srgb,var(--surface) 80%,var(--bg))}.toc-number-cell>span{left:26px;top:30px;font:900 70px/.9 var(--font-display);color:var(--accent)}.toc-number-cell>b{left:26px;right:26px;top:115px;font:850 42px/1 var(--font-heading);color:var(--surface-text)}.toc-number-cell>p{display:none}.toc-number-cell>i{right:24px;bottom:24px;font:900 36px/1 var(--font-heading);font-style:normal;color:var(--accent)}.toc-grid-footer{font:750 36px/1 var(--font-mono);letter-spacing:.14em;color:var(--muted)}
[data-theme="brand-editorial"] .toc-nav-card .diagram-node-bg,[data-theme="brand-editorial"] .toc-panel-grid-card .diagram-node-bg,[data-theme="brand-editorial"] .toc-panel-feature .diagram-node-bg{border-radius:0;box-shadow:none}[data-theme="brand-editorial"] .toc-nav-card>p,[data-theme="brand-editorial"] .toc-vertical-row>p,[data-theme="brand-editorial"] .toc-side-panel>p,[data-theme="brand-editorial"] .toc-wide-panel>p,[data-theme="brand-editorial"] .toc-panel-row>p,[data-theme="brand-editorial"] .toc-panel-grid-card>p,[data-theme="brand-editorial"] .toc-panel-feature>p,[data-theme="brand-editorial"] .toc-image-intro,[data-theme="brand-editorial"] .toc-number-row>p{font-family:var(--font-display)}[data-theme="clinical-report"] .toc-nav-card .diagram-node-bg,[data-theme="clinical-report"] .toc-panel-grid-card .diagram-node-bg,[data-theme="clinical-report"] .toc-panel-feature .diagram-node-bg{box-shadow:none}
.diagram-frame[data-density="low"]{--diagram-scale:1}.diagram-frame[data-density="medium"]{--diagram-scale:.94}.diagram-frame[data-density="high"]{--diagram-scale:.88}
[data-theme="clinical-report"] .diagram-node-bg{border-radius:2px;box-shadow:none}[data-theme="clinical-report"] .prod-title{font-weight:700}[data-theme="clinical-report"] .org-note .diagram-node-bg{border-radius:2px}
[data-theme="dark-circuit"] .slide{background-image:radial-gradient(color-mix(in srgb,var(--muted) 30%,transparent) 1px,transparent 1.5px);background-size:24px 24px}[data-theme="dark-circuit"] .diagram-node-bg{border-color:color-mix(in srgb,var(--text) 58%,transparent);box-shadow:0 0 24px color-mix(in srgb,var(--accent) 16%,transparent)}[data-theme="dark-circuit"] .diagram-connectors circle,[data-theme="dark-circuit"] .diagram-connectors path{filter:drop-shadow(0 0 5px color-mix(in srgb,var(--accent) 48%,transparent))}
[data-theme="brand-editorial"] .diagram-node-bg{border-radius:0;box-shadow:none}[data-theme="brand-editorial"] .prod-title:after{content:"";display:block;width:150px;height:5px;margin-top:20px;background:var(--accent)}[data-theme="brand-editorial"] .org-note .diagram-node-bg{border-radius:0}[data-theme="brand-editorial"] .diagram-node-body,[data-theme="brand-editorial"] .org-body,[data-theme="brand-editorial"] .funnel-note,[data-theme="brand-editorial"] .pyramid-body,[data-theme="brand-editorial"] .prod-subtitle,[data-theme="brand-editorial"] .compare-subtitle,[data-theme="brand-editorial"] .compare-panel li b,[data-theme="brand-editorial"] .matrix-card p,[data-theme="brand-editorial"] .price-card li b,[data-theme="brand-editorial"] .split-panel li b,[data-theme="brand-editorial"] .swot-card li{font-family:var(--font-display)}
[data-theme="product-strategy-signal"] .diagram-node-bg{border-radius:10px;box-shadow:none}[data-theme="product-strategy-signal"] .cycle-node .diagram-node-bg,[data-theme="product-strategy-signal"] .cycle-hub .diagram-node-bg{border-radius:50%}[data-theme="product-strategy-signal"] .org-note .diagram-node-bg{border-radius:10px}[data-theme="product-strategy-signal"] .diagram-connectors circle,[data-theme="product-strategy-signal"] .diagram-connectors path{stroke:var(--accent)}

/* Single-message note bars share the KPI takeaway's alignment behavior:
   vertical centering is structural; horizontal alignment follows the page title. */
.org-note,.compare-note,.content-rationale,.content-impact-note,.sequence-takeaway,.sequence-note{display:flex;align-items:center;box-sizing:border-box;padding:12px 40px}
.org-note[data-edit-horizontal-align="left"],.compare-note[data-edit-horizontal-align="left"],.content-rationale[data-edit-horizontal-align="left"],.content-impact-note[data-edit-horizontal-align="left"],.sequence-takeaway[data-edit-horizontal-align="left"],.sequence-note[data-edit-horizontal-align="left"]{justify-content:flex-start}
.org-note[data-edit-horizontal-align="center"],.compare-note[data-edit-horizontal-align="center"],.content-rationale[data-edit-horizontal-align="center"],.content-impact-note[data-edit-horizontal-align="center"],.sequence-takeaway[data-edit-horizontal-align="center"],.sequence-note[data-edit-horizontal-align="center"]{justify-content:center}
.org-note[data-edit-horizontal-align="right"],.compare-note[data-edit-horizontal-align="right"],.content-rationale[data-edit-horizontal-align="right"],.content-impact-note[data-edit-horizontal-align="right"],.sequence-takeaway[data-edit-horizontal-align="right"],.sequence-note[data-edit-horizontal-align="right"]{justify-content:flex-end}
.diagram-node.org-note>[data-edit-position="flow"],.diagram-node.compare-note>[data-edit-position="flow"],.diagram-node.content-rationale>[data-edit-position="flow"],.diagram-node.content-impact-note>[data-edit-position="flow"],.diagram-node.sequence-takeaway>[data-edit-position="flow"],.diagram-node.sequence-note>[data-edit-position="flow"]{position:relative;left:auto;right:auto;top:auto;bottom:auto;z-index:2;min-width:0}

/* Accent fills may stay expressive; accent typography must remain readable on its actual material. */
.slide{--accent-label:var(--accent-ink)}.diagram-node{--accent-label:var(--surface-accent-ink)}
.sequence-timeline,.sequence-vertical,.cycle-hub,.statement-focus-rail{--accent-label:var(--accent-ink)}
.sequence-timeline{position:relative}
.media-photo-asset{position:absolute;inset:0;width:100%;height:100%;display:block;object-fit:cover;z-index:1}
.map-media-asset{position:absolute;left:100px;top:20px;width:850px;height:600px;display:block;object-fit:cover;z-index:1;border-radius:12px}
.map-data-card>b{right:48px}.map-data-card>strong{right:48px}.map-data-card>p{right:48px}
.sequence-timeline .timeline-axis{left:180px;right:180px}
.sequence-timeline .timeline-milestone-copy{position:absolute;left:16px;right:16px;top:18px;display:flex;flex-direction:column;align-items:center;gap:8px;text-align:center;box-sizing:border-box}
.sequence-timeline .timeline-milestone.milestone-top .timeline-milestone-copy{top:-18px;bottom:auto}
.sequence-timeline .timeline-milestone-copy>[data-edit-layer]{position:static;left:auto;right:auto;top:auto;width:100%;height:auto}
.sequence-timeline .timeline-milestone-copy>span{font:850 36px/1 var(--font-heading);color:var(--accent-label)}
.sequence-timeline .timeline-milestone-copy>b{font:750 42px/1.2 var(--font-body);color:var(--surface-text);text-wrap:balance}
.sequence-timeline .timeline-milestone-copy>p{margin:0;font:500 36px/1.35 var(--font-body);color:var(--surface-muted);text-wrap:balance}
.cover-left-title-open-field{z-index:0;overflow:visible}.cover-left-title-stack{z-index:3;position:absolute;display:flex;flex-direction:column;align-items:flex-start;justify-content:center;gap:24px;box-sizing:border-box;padding:0 480px 0 112px;pointer-events:none;text-align:left}.cover-left-title-stack>.el{position:relative;flex:0 0 auto;pointer-events:auto;text-align:left}.cover-left-title,.cover-left-subtitle,.cover-left-speaker{display:block;padding:0;border:0;border-radius:0;background:transparent;text-align:left}.cover-left-title{font:800 104px/1.03 var(--font-heading);letter-spacing:-.055em;color:var(--text)}.cover-left-rule{padding:0;border:0;border-radius:999px;background:linear-gradient(90deg,var(--accent) 0 72%,var(--support-accent) 72% 100%)}.cover-left-subtitle{font:500 38px/1.38 var(--font-body);color:var(--muted)}.cover-left-speaker{font:800 36px/1 var(--font-heading);letter-spacing:.08em;color:var(--accent)}#stage .slide[data-layout-id="cover-left-title-open-field"]{background-color:var(--bg);background-image:linear-gradient(90deg,transparent 68%,color-mix(in srgb,var(--accent) 8%,var(--bg)) 68% 100%),linear-gradient(90deg,transparent 74%,color-mix(in srgb,var(--support-accent) 16%,transparent) 74% 74.4%,transparent 74.4%),linear-gradient(color-mix(in srgb,var(--accent) 2.4%,transparent) 1px,transparent 1px),linear-gradient(90deg,color-mix(in srgb,var(--accent) 2.4%,transparent) 1px,transparent 1px);background-size:100% 100%,100% 100%,64px 64px,64px 64px;box-shadow:18px 0 0 inset var(--accent)}
.diagram-kicker,.diagram-no,.funnel-index,.org-metric,.pyramid-no,.compare-panel li span,.compare-rail,.price-name,.price-card li span,.price-cta,.split-label,.split-panel li span,.swot-letter,.metric-eyebrow,.metric-strip-item strong,.metric-panel-kicker,.metric-panel-value,.metric-insight li span,.metric-card-delta,.metric-stat-index,.closing-kicker,.closing-copy-panel li span,.statement-chart-kicker,.statement-chart-value,.statement-callout>span,.statement-focus-attribution,.statement-column-section>span,.chapter-overlay-title>span,.chapter-label,.chapter-split-label,.content-logo-panel>span,.content-panel-kicker,.content-voice-item>span,.content-do span,.content-dont span,.content-rec-row>span,.content-rec-row>em,.content-priority-number,.content-priority-card>em,.sequence-stage-card>span,.sequence-stage-card>em,.sequence-process-node>span,.timeline-milestone>span,.timeline-vertical-event>span,.cover-center-org,.cover-logo>b,.cover-split-kicker,.cover-split-org,.cover-overlay-block>span,.dataviz-annotation-card>span,.dataviz-annotation-card>strong,.map-data-card>span,.map-data-card>strong,.radar-legend-row>span,.media-executive-role,.media-panel-kicker,.media-bio-row>span,.media-icon-row>span,.media-testimonial-logo>b,.module-card .module-number,.module-card .module-tag,.module-icon-cell>span,.module-person-card>span,.module-person-card>em,.module-team-card>span,.toc-nav-card>span,.toc-nav-card>i,.toc-vertical-row>span,.toc-vertical-row>i,.toc-panel-row>span,.toc-panel-row>i,.toc-panel-grid-card>span,.toc-panel-feature>span,.toc-panel-grid-card>i,.toc-panel-feature>i,.toc-image-row>span,.toc-image-row>i,.toc-number-row>i,.toc-number-cell>span,.toc-number-cell>i{color:var(--accent-label)}
'''


MEDIA_PLACEHOLDER_CSS = r'''
/* Image-dependent Layouts keep their media geometry but render only a filled slot. */
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .cover-media-field,
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .chapter-media-field,
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .closing-photo-field,
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .media-photo .diagram-node-bg{
  background:linear-gradient(135deg,color-mix(in srgb,var(--surface) 94%,var(--accent)),color-mix(in srgb,var(--accent) 32%,var(--bg))) !important;
  background-image:none !important;
  box-shadow:none !important;
}
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .cover-media-field i,
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .chapter-media-field i,
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .chapter-media-field::after,
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .closing-photo-glow,
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .closing-photo-subject,
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .closing-photo-grain,
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .media-photo-art,
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .media-photo-accent{
  display:none !important;
}
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .module-icon-shape,
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .module-person-photo,
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .module-team-photo{
  border:0 !important;
  border-radius:50% !important;
  background:linear-gradient(135deg,var(--support-accent),var(--accent)) !important;
  background-image:none !important;
  clip-path:none !important;
  transform:none !important;
}
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .dataviz-map > svg{
  display:none !important;
}
section[data-media-mode="with-image"][data-media-treatment="placeholder-fill"] .map-media-placeholder{
  left:100px;
  top:20px;
  width:850px;
  height:600px;
  display:block;
  border:0;
  border-radius:16px;
  background:linear-gradient(135deg,color-mix(in srgb,var(--surface) 94%,var(--accent)),color-mix(in srgb,var(--accent) 32%,var(--bg)));
  background-image:none;
  box-shadow:none;
}

/* In a final image-planned deck, the generated slide-level raster is the
   image layer. Keep the Layout's media geometry for editing, but remove every
   synthetic photo, blob, map, and placeholder so it cannot compete with that
   background or become a strange independent decoration. */
html[data-layout-asset-policy="image-planned"] section.slide::before,
html[data-layout-asset-policy="image-planned"] section.slide::after{
  content:none !important;
  display:none !important;
}
section[data-media-mode="with-image"][data-media-treatment="raster-background"] :is(
  .cover-media-field,
  .cover-overlay-canvas,
  .cover-overlay-accent,
  .chapter-media-field,
  .closing-photo-field,
  .media-photo .diagram-node-bg,
  .map-media-placeholder
){
  background:transparent !important;
  background-image:none !important;
  border:0 !important;
  box-shadow:none !important;
}
section[data-media-mode="with-image"][data-media-treatment="raster-background"] :is(
  .cover-media-field i,
  .chapter-media-field i,
  .chapter-media-field::after,
  .closing-photo-glow,
  .closing-photo-subject,
  .closing-photo-grain,
  .media-photo-art,
  .media-photo-accent,
  .module-person-photo,
  .module-team-photo,
  .dataviz-map > svg
){
  display:none !important;
}
section[data-media-mode="with-image"][data-media-treatment="raster-background"] .cover-media-field::after{
  content:none !important;
  display:none !important;
}
'''
# Semantic role guards are appended after Theme/Preset CSS. They keep a component's
# declared surface/ink pair intact when a broad visual override targets shared layers.
SEMANTIC_CONTRACT_CSS = r'''
html[data-preset-theme][data-theme-id][data-style-profile][data-theme-kind] [data-edit-align-contract="center-axis"],
[data-edit-align-contract="center-axis"]{left:864px!important;right:auto!important;translate:-50% 0!important;text-align:center!important}
html[data-preset-theme][data-theme-id][data-style-profile][data-theme-kind] [data-visual-surface-role="accent"]>.diagram-node-bg,
[data-visual-surface-role="accent"]>.diagram-node-bg{background:var(--accent)!important;background-image:none!important;border-color:transparent!important}
html[data-preset-theme][data-theme-id][data-style-profile][data-theme-kind] [data-visual-surface-role="none"]>.diagram-node-bg,
[data-visual-surface-role="none"]>.diagram-node-bg{background:transparent!important;background-image:none!important;border:0!important;box-shadow:none!important}
html[data-preset-theme][data-theme-id][data-style-profile][data-theme-kind] [data-visual-surface-role="accent"] :is(span,b,p,em),
[data-visual-surface-role="accent"] :is(span,b,p,em){color:var(--accent-text)!important}
'''


_FONT_SIZE_DECL_RE = re.compile(r"(?P<prefix>\bfont-size\s*:\s*)(?P<size>\d+(?:\.\d+)?)(?P<unit>px)", re.IGNORECASE)
_FONT_SHORTHAND_RE = re.compile(r"(?P<prefix>\bfont\s*:[^;{}]*?)(?P<size>\d+(?:\.\d+)?)(?P<unit>px)", re.IGNORECASE)


def normalize_generated_css_font_sizes(css: str, minimum: int = GENERATED_TEXT_MIN_PX) -> str:
    """Assert that renderer source was designed for the font floor.

    Keep the historical helper name for callers, but never rewrite type after
    Layout geometry has been authored.  A violation now identifies an unmigrated
    source owner and blocks rendering.
    """

    violations: list[float] = []
    for pattern in (_FONT_SIZE_DECL_RE, _FONT_SHORTHAND_RE):
        for match in pattern.finditer(css):
            size = float(match.group("size"))
            if size < minimum:
                violations.append(size)
    if violations:
        preview = ", ".join(f"{value:g}px" for value in violations[:12])
        raise ValueError(
            "Renderer CSS contains typography below the generated-text floor; "
            f"migrate the owning Layout geometry before rendering: {preview}"
        )
    return css


PRODUCTION_CSS += "\n" + CARDS_1PLUS3_VARIANT_CSS
PRODUCTION_CSS = normalize_generated_css_font_sizes(PRODUCTION_CSS)
