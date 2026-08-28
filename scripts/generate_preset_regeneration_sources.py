#!/usr/bin/env python3
"""Create fresh story and Art Direction sources for every current HTML Preset.

This preparation step is intentionally separate from the formal HTML renderer:
it owns only new content and renderer-neutral direction.  The renderer remains
the source of truth for HTML structure, editor semantics, and manifest output.
The target root is versioned and write-once so a rerun cannot overwrite an
existing regeneration or an older delivered artifact.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from html_design_method import load_html_design_method
from html_layout_catalog import eligible_html_layouts, load_html_layout_catalog


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BATCH_ID = "html-preset-regeneration-20260813-v6"
DEFAULT_BASE_SEED = 2026081301
DEFAULT_ROOT = PROJECT_ROOT / "artifacts" / "experiments" / DEFAULT_BATCH_ID
PRESET_REGISTRY = PROJECT_ROOT / "prompt_system" / "presets" / "catalog.yaml"
DASHBOARD_INSIGHT_MAX_CHARS = 12

PRESET_COHORT = (
    "line-argument-journal",
    "signal-route-atlas",
    "field-index-manual",
    "tide-signal-observatory",
    "craft-archive-editions",
    "incident-command-redline",
    "harbor-ribbon-program",
    "neighborhood-newsroom-proof",
    "scent-veil-launch",
    "restoration-blueprint-ledger",
    "ai-operations-signal",
    "brave-classroom-contours",
    "night-transit-wayfinding",
    "sepia-retail-case",
    "dark-ai-city",
    "dark-city-network-report",
    "clinical-evidence-atlas",
    "moonlit-herbarium-atlas",
)


def _visible_copy_safe_item(source: dict[str, Any]) -> dict[str, Any]:
    """Remove invented audience metadata before any page composition is built."""

    item = copy.deepcopy(source)
    item["speaker"] = ""
    item["org"] = ""
    item["attribution"] = ""
    item["priorities"] = [
        [title, body, f"重點 {index:02d}", allocation]
        for index, (title, body, _tag, allocation) in enumerate(item["priorities"], 1)
    ]
    item["metrics"] = [
        [value, label, body, ""]
        for value, label, body, _delta in item["metrics"]
    ]
    item["timeline"] = [
        [f"第 {index} 階段", title, body]
        for index, (_label, title, body) in enumerate(item["timeline"], 1)
    ]
    return item

EXPECTED_SLIDE_COUNTS = {
    "line-argument-journal": 12,
    "signal-route-atlas": 12,
    "field-index-manual": 12,
    "tide-signal-observatory": 10,
    "craft-archive-editions": 10,
    "incident-command-redline": 10,
    "harbor-ribbon-program": 10,
    "neighborhood-newsroom-proof": 10,
    "scent-veil-launch": 10,
    "restoration-blueprint-ledger": 10,
    "ai-operations-signal": 10,
    "brave-classroom-contours": 10,
    "night-transit-wayfinding": 10,
    "sepia-retail-case": 15,
    "dark-ai-city": 8,
    "dark-city-network-report": 8,
    "clinical-evidence-atlas": 15,
    "moonlit-herbarium-atlas": 10,
}

CANONICAL_VISUAL_GENRES = frozenset(
    {
        "institutional-editorial",
        "cultural-exhibition",
        "documentary-field-guide",
        "scientific-atlas",
        "kinetic-typography",
        "archival-publication",
        "data-journal",
        "campaign-poster-system",
        "product-narrative",
        "custom",
    }
)
CANONICAL_PRIMARY_JOBS = frozenset(
    {"institutional", "atmospheric", "documentary", "neutral-stage", "chapter-code"}
)
CANONICAL_ACCENT_JOBS = frozenset(
    {"classification", "status", "time", "risk", "brand", "single-emotional-focus"}
)
CANONICAL_FORBIDDEN_CLICHES = frozenset(
    {
        "equal-rounded-card-wall",
        "generic-purple-orange-gradient",
        "concentric-circles",
        "decorative-random-curves",
        "glassmorphism-everywhere",
        "icon-title-two-line-card",
        "generic-right-side-illustration-cover",
        "glow-plus-grid-plus-grain",
        "floating-pills",
        "arbitrary-corner-ornaments",
        "fake-dashboard",
        "mixed-illustration-libraries",
        "outline-text-as-decoration",
        "custom",
    }
)

PRIMARY_JOB_ALIASES = {"supportive": "neutral-stage"}
ACCENT_JOB_ALIASES = {"evidence": "classification"}
FORBIDDEN_CLICHE_ALIASES = {
    "decorative-arcs": "decorative-random-curves",
    "repeated-diagonal-background-route": "decorative-random-curves",
    "repeated-diagonal-route": "decorative-random-curves",
    "botanical-stickers": "mixed-illustration-libraries",
    "craft-stickers": "mixed-illustration-libraries",
    "school-doodles": "mixed-illustration-libraries",
    "cute-stickers": "arbitrary-corner-ornaments",
    "compass-symbols": "arbitrary-corner-ornaments",
    "radar-symbols": "arbitrary-corner-ornaments",
    "fake-technical-symbols": "arbitrary-corner-ornaments",
    "glow-grid": "glow-plus-grid-plus-grain",
    "full-page-grid": "glow-plus-grid-plus-grain",
    "wave-illustration": "generic-right-side-illustration-cover",
    "newspaper-collage": "mixed-illustration-libraries",
    "fake-aged-paper": "custom",
}

# These four schema-native values preserve the user's cross-Preset prohibition
# against decorative rings, arcs, grids, and symbols after custom source terms
# are canonicalized.
REQUIRED_BACKGROUND_PROHIBITIONS = (
    "concentric-circles",
    "decorative-random-curves",
    "glow-plus-grid-plus-grain",
    "arbitrary-corner-ornaments",
)

SCENE_ROLE_CYCLE = (
    "hero",
    "index-or-map",
    "relationship",
    "evidence",
    "pause-or-close",
    "relationship",
    "evidence",
    "index-or-map",
)
SCENE_INTENSITY_CYCLE = (5, 2, 4, 3, 1, 4, 3, 2)

_LEGACY_LAYOUT_ALIASES = {
    "chapter-opener": "strategic-priorities",
    "comparison-table": "split-comparison",
    "highlight-callout": "dashboard-overview",
}


def _toc_capacity(layout_id: str) -> int | None:
    match = re.match(r"^toc-(\d+)", layout_id)
    return int(match.group(1)) if match else None


def _module_layout_capacity(layout_id: str) -> int | None:
    match = re.match(r"^cards-1-plus-(\d+)$", layout_id)
    return int(match.group(1)) if match else None


def _formal_layout_id(layout_id: str, toc_count: int) -> str:
    """Project historical source names onto canonical new-deck Layout routes."""

    layout_id = _LEGACY_LAYOUT_ALIASES.get(layout_id, layout_id)
    capacity = _toc_capacity(layout_id)
    if capacity is not None and capacity < toc_count:
        # The current cohort has six TOC chapters. Keep the visual family while
        # selecting a real six-slot Layout from the canonical catalog.
        return "toc-6-panel-rows"
    return layout_id


COMMON_OFFICIAL_CASES = [
    {
        "title": "The Met Collection Open Access records",
        "original_author_or_studio": "The Metropolitan Museum of Art",
        "official_url": "https://www.metmuseum.org/about-the-met/policies-and-documents/open-access",
        "borrowed_method": "借用物件、來源、時間與索引並列的證據整理方法，不複製作品的造型或版面。",
    },
    {
        "title": "Free to Use and Share",
        "original_author_or_studio": "Library of Congress",
        "official_url": "https://www.loc.gov/free-to-use/",
        "borrowed_method": "借用公開來源的分類、標註與 provenance 觀念，讓素材角色先於裝飾效果。",
    },
]

COMMON_CROSS_DOMAIN_REFERENCE = {
    "type": "archival-publication",
    "title": "公開典藏的索引與來源標註方法",
    "source_url": "https://www.metmuseum.org/about-the-met/policies-and-documents/open-access",
    "borrowed_method": "把每個視覺標記限制在可解釋的分類、時間、責任或證據工作上。",
}

COMMON_ASSET_SOURCES = [
    {
        "catalog_id": "project-native-css-geometry",
        "source_url": "https://developer.mozilla.org/en-US/docs/Web/CSS",
        "license_status": "official documentation; no copied assets",
    }
]


def _entry(
    *,
    preset_id: str,
    base_theme: str,
    story_id: str,
    title: str,
    subtitle: str,
    speaker: str,
    org: str,
    chapter_number: str,
    toc: list[list[str]],
    priorities: list[list[str]],
    metrics: list[list[str]],
    timeline: list[list[str]],
    quote: str,
    attribution: str,
    closing: list[str],
    layouts: list[str],
    direction: dict[str, Any],
) -> dict[str, Any]:
    return {
        "preset_id": preset_id,
        "base_theme": base_theme,
        "story_id": story_id,
        "title": title,
        "subtitle": subtitle,
        "speaker": speaker,
        "org": org,
        "chapter_number": chapter_number,
        "toc": toc,
        "priorities": priorities,
        "metrics": metrics,
        "timeline": timeline,
        "quote": quote,
        "attribution": attribution,
        "closing": closing,
        "layouts": layouts,
        "direction": direction,
    }


_PRESET_DEFINITIONS: list[dict[str, Any]] = [
    _entry(
        preset_id="sepia-retail-case",
        base_theme="grainy-editorial",
        story_id="rainwater-second-route",
        title="雨水不是浪費，是城市的第二條供應線",
        subtitle="把屋頂、街角蓄水與清潔需求編成一條看得見、可維護、可停止的城市水路",
        speaker="URBAN WATER FIELD EDITORIAL",
        org="FIELD NOTE · 2026",
        chapter_number="21",
        toc=[
            ["屋頂收集", "先盤點雨水落在哪裡，才知道哪裡值得留下。"],
            ["街角蓄水", "把短暫的積水轉成可辨識、可清理的公共節點。"],
            ["清潔回用", "只把水送到不需要飲用等級的明確工作。"],
            ["維護責任", "每個槽體都有一個看得見的照顧人與回報時限。"],
            ["雨季節奏", "用幾次降雨的觀察調整容量，而不是一次做滿。"],
            ["社區回看", "讓使用者看見節省了什麼，也看見下一輪要修哪裡。"],
        ],
        priorities=[
            ["漏斗入口", "先處理能收集、能清理、能被鄰里看見的屋頂與街角。", "START", "45%"],
            ["共同維護", "把清潔、巡檢與異常通報寫成同一張責任表。", "BUILD", "35%"],
            ["乾旱備援", "只在基準資料足夠後，才擴張到更多公共工作。", "NEXT", "20%"],
        ],
        metrics=[
            ["18站", "蓄水節點", "概念試算，不代表現地承諾", "FIELD"],
            ["72%", "雨後可用率", "以清潔與灌溉為測試口徑", "PILOT"],
            ["11分", "取水準備時間", "從巡檢到可用的模擬流程", "FLOW"],
            ["3類", "維護角色", "社區、物業、場域管理", "OWNERS"],
        ],
        timeline=[
            ["M01", "測量屋頂", "找出落水方向、遮蔭與清理入口。"],
            ["M02", "試做街角槽", "先用一個節點驗證可見性與安全距離。"],
            ["M03", "接入清潔", "把回用工作限定在可追蹤的非飲用用途。"],
            ["M04", "建立維護", "將清理、回報與停用條件寫進值班節奏。"],
            ["M06", "雨季回看", "用實際紀錄決定保留、調整或停止。"],
        ],
        quote="真正的節水，不是把每一滴都留下，\n而是知道哪一滴值得被下一個工作接住。",
        attribution="URBAN WATER FIELD NOTE · 21",
        closing=["讓雨水有下一個工作，\n也讓維護有一個清楚的人。", "先從一個可被看見、可被清理的街角節點開始。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-6-panel-rows", "strategic-priorities",
            "recommendation-stack", "split-comparison", "cards-1-plus-4", "matrix-4quadrant",
            "dashboard-overview", "heat-map", "kpi-scorecards", "process-flow",
            "timeline-vertical", "before-after", "quote-focus", "title-center",
        ],
        direction={
            "visual_genre": "archival-publication",
            "narrative_metaphor": "把一場雨當成一份會流動的城市帳本，沿著落水、保存、使用與維護逐格記下責任。",
            "signature_name": "water-ledger-spine",
            "signature_concept": "用一條窄邊索引把水的去向與維護責任連在一起，讓紙面留白承載判斷而非裝飾。",
            "variations": ["rule", "ledger", "split", "milestone"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "editorial-columns", "crop": "frame-within-frame",
            "whitespace": "左側保留索引空間，主要內容沿紙面基準線收合。", "alignment": "left",
            "edge": "structural-index", "type_role": "index", "family": "serif-sans-pair",
            "primary_job": "documentary", "accent_job": "classification", "accent_limit": "不超過一般頁面視覺面積 12%。",
            "forbidden": ["equal-rounded-card-wall", "generic-purple-orange-gradient", "floating-pills", "fake-dashboard", "decorative-random-curves"],
            "anti_reference": "把水滴、葉片與巨大圓形當成氣氛貼紙，讓維護責任被柔和裝飾吃掉。",
        },
    ),
    _entry(
        preset_id="dark-ai-city",
        base_theme="dark-circuit",
        story_id="nocturnal-delivery-agreement",
        title="深夜配送，先把安靜當成一種路權",
        subtitle="以必要貨件、社區睡眠與最後一公里責任，重畫城市夜間配送的交接規則",
        speaker="NIGHT ROUTE OPERATIONS LAB",
        org="URBAN LOGISTICS · 2026",
        chapter_number="22",
        toc=[
            ["必要貨件", "先辨認真正不能等到白天的貨件與服務。"],
            ["安靜時段", "把聲音、燈光與停靠時間寫成可量測的限制。"],
            ["微型轉運", "用更小的交接節點取代長時間佔用街角。"],
            ["司機交接", "每次移交都留下時間、位置與異常責任。"],
            ["居民回報", "讓被影響的人能回報，不必成為系統專家。"],
            ["規則回寫", "每輪試運後只回寫一個最值得保留的規則。"],
        ],
        priorities=[
            ["靜默優先", "先處理停靠聲、倒車提示與照明外溢。", "QUIET", "42%"],
            ["轉運可見", "讓微型轉運站在夜裡也有清楚的交接標記。", "HANDOFF", "33%"],
            ["回報閉環", "每一筆居民回報都要有回應、調整或停止結果。", "LOOP", "25%"],
        ],
        metrics=[
            ["7站", "微型轉運節點", "情境模擬的候選位置", "ROUTE"],
            ["84%", "低噪交接率", "測試流程的目標門檻", "QUIET"],
            ["16分", "平均停靠時間", "從進站到離站的模擬值", "TIME"],
            ["4種", "居民回報類型", "聲音、光線、阻塞、遺漏", "SIGNAL"],
        ],
        timeline=[
            ["00:00", "開啟靜默窗", "清楚標記夜間可做與不可做的動作。"],
            ["00:08", "首個交接", "測量停靠、掃描與搬運的聲音節點。"],
            ["00:16", "完成轉運", "把責任與異常寫回同一筆紀錄。"],
            ["07:30", "居民回看", "用白天回報校正夜間規則。"],
            ["W04", "規則回寫", "只保留被證據支持的改動。"],
        ],
        quote="夜間系統的效率，不是更快通過，\n而是讓每一次通過都不驚動不需要被驚動的人。",
        attribution="NIGHT ROUTE OPERATIONS · 22",
        closing=["把安靜寫進路線，\n配送才真正進入城市。", "先用一個轉運站測量交接，再決定是否擴張整條夜間網。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-4-panel-grid", "cards-1-plus-4", "before-after",
            "kpi-scorecards", "process-flow", "highlight-callout", "title-center",
        ],
        direction={
            "visual_genre": "kinetic-typography",
            "narrative_metaphor": "把夜間配送視為一條低亮度的城市訊號線，每個交接都是被驗證過的安靜節點。",
            "signature_name": "quiet-route-pulse",
            "signature_concept": "以少量高對比節點標出交接與回報，線條只在責任真正移動時出現。",
            "variations": ["pulse", "handoff", "matrix", "signal-bar"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "right-axis", "axis": "route", "crop": "one-edge",
            "whitespace": "深色場域保留大片低亮度區，讓高亮訊號成為單一視線出口。", "alignment": "left",
            "edge": "one-edge-crop", "type_role": "protagonist", "family": "single-family",
            "primary_job": "atmospheric", "accent_job": "status", "accent_limit": "高亮訊號不超過一般頁面視覺面積 10%。",
            "forbidden": ["generic-purple-orange-gradient", "glow-plus-grid-plus-grain", "glassmorphism-everywhere", "equal-rounded-card-wall", "outline-text-as-decoration"],
            "anti_reference": "把所有模組都做成發光卡片，讓真正的交接訊號失去優先級。",
        },
    ),
    _entry(
        preset_id="dark-city-network-report",
        base_theme="brand-editorial",
        story_id="river-corridor-heat",
        title="一條河流，如何穿過城市的熱區",
        subtitle="從遮蔭、親水到通勤路徑，建立一張把公共空間與高溫風險放在同一頁的城市報告",
        speaker="RIVER CORRIDOR OBSERVATORY",
        org="CIVIC DATA REPORT · 2026",
        chapter_number="23",
        toc=[
            ["熱點分布", "先看人真正停留與移動的位置，而不是只看行政區。"],
            ["遮蔭缺口", "把樹蔭、騎樓與可停留空間畫成一條連續路徑。"],
            ["親水節點", "確認接近河岸的方式是否真的讓人更安全。"],
            ["通勤轉折", "將每天必走的轉折點納入熱風險判讀。"],
            ["維運窗口", "把澆灌、清潔與照明安排連回空間使用。"],
            ["公開回看", "讓居民能看見資料如何改變下一輪空間決策。"],
        ],
        priorities=[
            ["連續遮蔭", "先補上熱點之間最常被走過、卻沒有停留條件的缺口。", "SHADE", "46%"],
            ["安全親水", "將接近河岸的階段動作與風險標示拆開處理。", "EDGE", "31%"],
            ["資料回看", "用公開圖層追蹤哪一段改善真的改變了日常路徑。", "OPEN", "23%"],
        ],
        metrics=[
            ["12段", "熱區步行斷點", "情境地圖中的優先路段", "MAP"],
            ["68%", "遮蔭連續度", "概念性基準，不代表實測結果", "SHADE"],
            ["9處", "河岸停留節點", "含安全、清潔與照明條件", "EDGE"],
            ["5層", "公開資料圖層", "熱點、遮蔭、水邊、路徑、維運", "OPEN"],
        ],
        timeline=[
            ["SPRING", "畫出熱點", "以日常路徑補足單一測站看不到的地方。"],
            ["EARLY SUMMER", "確認遮蔭", "找出連續路徑最短的補點方案。"],
            ["MID SUMMER", "試走河岸", "把安全與停留兩種需求分開觀察。"],
            ["AUTUMN", "回收維運", "將清潔、灌溉與照明成本列回報告。"],
            ["NEXT", "公開回看", "讓下一輪預算有可追蹤的空間證據。"],
        ],
        quote="城市不是被平均降溫的，\n而是在每一次轉彎處被重新感受到。",
        attribution="RIVER CORRIDOR OBSERVATORY · 23",
        closing=["讓河流成為一條可走的降溫線，\n而不是地圖上的藍色邊界。", "先修補一段連續路徑，再把資料與維運一起公開。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-4-panel-rows", "chapter-opener", "comparison-table",
            "dashboard-overview", "process-flow", "quote-focus", "title-center",
        ],
        direction={
            "visual_genre": "data-journal",
            "narrative_metaphor": "把河流當成一條穿越熱區的編輯主線，沿著每個轉彎重新安排資料、路徑與公共責任。",
            "signature_name": "river-editorial-thread",
            "signature_concept": "一條細長主線只在熱點、遮蔭、親水與維運資料發生關係時轉向，避免變成背景路網。",
            "variations": ["route", "cross-section", "map-strip", "evidence-rule"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "route", "crop": "opposing-edges",
            "whitespace": "以一側大留白容納報告索引，另一側承擔河岸路徑與資料密度。", "alignment": "left",
            "edge": "opposing-edge-crop", "type_role": "evidence-label", "family": "serif-sans-pair",
            "primary_job": "documentary", "accent_job": "classification", "accent_limit": "分類色只標示路徑與資料層，不作滿版填色。",
            "forbidden": ["fake-dashboard", "equal-rounded-card-wall", "generic-purple-orange-gradient", "decorative-random-curves", "floating-pills"],
            "anti_reference": "把城市網路畫成均勻的霓虹線，卻沒有說明哪一條線代表什麼責任。",
        },
    ),
    _entry(
        preset_id="moonlit-herbarium-atlas",
        base_theme="soft-organic-education",
        story_id="night-school-biological-clock",
        title="校園在夜裡也有一份生物課表",
        subtitle="用低干擾照明、棲地節點與觀察紀錄，讓校園夜間生態成為可學習的日常",
        speaker="CAMPUS NIGHT ECOLOGY LAB",
        org="FIELD CLASS · 2026",
        chapter_number="24",
        toc=[
            ["光線邊界", "先找出哪些地方必須亮，哪些地方可以讓夜色留下。"],
            ["棲地節點", "把水、土、樹冠與落葉層視為不同的觀察入口。"],
            ["觀察日記", "用固定欄位記下看到、沒看到與不能推論的事。"],
            ["學生路徑", "讓學習走過真實的夜間邊界，而不是只看一張圖。"],
            ["照明試驗", "把亮度調整與安全需求放進同一次小規模試做。"],
            ["季節回看", "用不同季節的紀錄更新校園的夜間課表。"],
        ],
        priorities=[
            ["低干擾照明", "先保留真正需要的安全光，再降低棲地邊緣的干擾。", "DARK", "41%"],
            ["可追蹤觀察", "每次記錄都要標明時間、位置與不能推論的範圍。", "LOG", "36%"],
            ["學生共學", "將觀察變成可重複的課堂任務，不把生態當成展板背景。", "LEARN", "23%"],
        ],
        metrics=[
            ["6區", "夜間觀察棲地", "校園情境設計的分類", "HABITAT"],
            ["4級", "低干擾照明", "從必要光到可關閉光", "LIGHT"],
            ["28筆", "觀察日記", "第一輪課堂測試目標", "FIELD"],
            ["3季", "回看節奏", "春、夏、秋的對照", "CYCLE"],
        ],
        timeline=[
            ["W01", "繪製光線邊界", "先把安全與棲地需求分開畫出來。"],
            ["W03", "設置觀察點", "每個點只保留一個主要觀察問題。"],
            ["W05", "學生夜走", "以小組任務測試路徑與記錄表。"],
            ["W08", "微調照明", "比較可見度、干擾與維護條件。"],
            ["W12", "季節回看", "把不能推論的部分也寫進課表。"],
        ],
        quote="夜裡的學習，不是把白天的燈打開，\n而是學會分辨什麼應該被看見。",
        attribution="CAMPUS NIGHT ECOLOGY · FIELD NOTE 24",
        closing=["讓校園保留一點夜色，\n也讓每一次觀察都留下下一個問題。", "從低干擾照明與一張誠實的觀察表開始。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-4-panel-grid", "cards-1-plus-4", "split-comparison",
            "kpi-scorecards", "timeline-milestones", "comparison-table", "process-flow", "quote-focus", "title-center",
        ],
        direction={
            "visual_genre": "scientific-atlas",
            "narrative_metaphor": "把校園夜間生態視為一座仍在發芽的觀察標本館，讓光線、棲地與學生筆記互相校正。",
            "signature_name": "nocturnal-specimen-compare",
            "signature_concept": "用成對觀察欄比較照明介入前後，讓棲地、證據與限制各自保持清楚邊界。",
            "variations": ["field-note", "specimen-index", "light-state-pair", "seasonal-compare"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "editorial-columns", "crop": "frame-within-frame",
            "whitespace": "以寬鬆留白模擬標本紙的呼吸，密度只在觀察證據頁提高。", "alignment": "left",
            "edge": "quiet", "type_role": "evidence-label", "family": "serif-sans-pair",
            "primary_job": "documentary", "accent_job": "time", "accent_limit": "色彩只標示季節與照明狀態，不描繪物種插圖。",
            "forbidden": ["decorative-random-curves", "glow-plus-grid-plus-grain", "equal-rounded-card-wall", "mixed-illustration-libraries", "generic-right-side-illustration-cover"],
            "anti_reference": "用大量植物插畫裝飾每頁，卻沒有留下時間、位置與觀察限制。",
        },
    ),
    _entry(
        preset_id="clinical-evidence-atlas",
        base_theme="clinical-report",
        story_id="remote-care-signal-silence",
        title="遠距照護，先辨認沉默是不是訊號",
        subtitle="把回覆、未回覆與生活節律放進同一條照護判讀路徑，避免單一提醒取代人的理解",
        speaker="REMOTE CARE SERVICE STUDY",
        org="EDUCATION PROTOTYPE · 2026",
        chapter_number="25",
        toc=[
            ["回覆不等於穩定", "一次回覆只能代表一次接觸，不能代替完整狀態判斷。"],
            ["沉默的種類", "區分忙碌、疲累、技術障礙與真正需要支援的沉默。"],
            ["節律觀察", "把連續幾次的生活訊號放在單一提醒之前。"],
            ["人工接手", "符合條件時由人接手，而不是讓系統自行推論。"],
            ["照顧者回看", "讓照顧者看見系統做了什麼與沒有做什麼。"],
            ["停止條件", "任何自動化都要有清楚的退出、轉介與人工確認。"],
        ],
        priorities=[
            ["先理解", "先把沉默分類，再決定要提醒、等待或由人接手。", "READ", "44%"],
            ["可追溯", "每次提醒都留下觸發條件、回應與人工處置。", "TRACE", "34%"],
            ["能退出", "當推論不可靠時立即停止自動化並轉交專業團隊。", "STOP", "22%"],
        ],
        metrics=[
            ["5類", "沉默情境", "服務設計的概念分類", "SIGNAL"],
            ["3層", "人工接手", "提醒、關懷、專業轉介", "CARE"],
            ["100%", "紀錄可追溯", "本原型的必要驗收條件", "TRACE"],
            ["36px", "最小生成字級", "投影閱讀的版型護欄", "TYPE"],
        ],
        timeline=[
            ["STEP 01", "建立基準", "先確認每個人可接受的聯絡節奏。"],
            ["STEP 02", "辨認沉默", "把狀態不明與風險升高分開。"],
            ["STEP 03", "人工接手", "符合條件就停止猜測並轉交人。"],
            ["STEP 04", "共同回看", "與本人及照顧者核對系統紀錄。"],
            ["STEP 05", "調整規則", "只修改被驗證的觸發條件。"],
        ],
        quote="真正安全的遠距照護，\n不是永遠在線，而是知道何時不能再猜。",
        attribution="REMOTE CARE SERVICE STUDY · 25",
        closing=["讓沉默有被理解的入口，\n也讓自動化有可以退出的邊界。", "本頁為服務設計教育原型，不構成診斷、治療或個別照護建議。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-6-panel-rows", "before-after", "stats-3-row",
            "kpi-scorecards", "data-annotation", "multi-line-chart", "dashboard-overview",
            "heat-map", "process-flow", "timeline-vertical", "strategic-priorities",
            "recommendation-stack", "quote-focus", "title-center",
        ],
        direction={
            "visual_genre": "scientific-atlas",
            "narrative_metaphor": "把遠距照護畫成一張可回溯的判讀圖譜，讓每個訊號都帶著來源、限制與人工出口。",
            "signature_name": "evidence-spine",
            "signature_concept": "一條細直脊線連接訊號、人工判讀與退出條件，任何沒有證據的跳躍都停在脊線外。",
            "variations": ["spine", "before-after", "risk-field", "handoff"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "vertical", "crop": "none",
            "whitespace": "把資料層與文字層分開留白，避免密度被誤讀成確定性。", "alignment": "left",
            "edge": "structural-index", "type_role": "evidence-label", "family": "single-family",
            "primary_job": "institutional", "accent_job": "risk", "accent_limit": "風險標記只出現在觸發條件與退出節點。",
            "forbidden": ["fake-dashboard", "floating-pills", "generic-purple-orange-gradient", "equal-rounded-card-wall", "outline-text-as-decoration"],
            "anti_reference": "用醫療藍、警示紅與大數字做出假權威，卻沒有說明資料限制與人工出口。",
        },
    ),
    _entry(
        preset_id="signal-route-atlas",
        base_theme="product-strategy-signal",
        story_id="repair-parts-transfer",
        title="社區維修，不缺零件，只缺一條看得見的轉運線",
        subtitle="把報修、備件、志工與回訪編成一張不靠記憶運作的維修路線圖",
        speaker="NEIGHBORHOOD REPAIR ROUTE",
        org="SERVICE BLUEPRINT · 2026",
        chapter_number="26",
        toc=[
            ["報修入口", "先把故障描述變成可以被分流的最小訊號。"],
            ["備件索引", "知道手上有什麼，才不會讓等待變成黑箱。"],
            ["轉運節點", "把零件與人力安排成短而清楚的交接路徑。"],
            ["志工派工", "每次派工都留下技能、距離與回訪責任。"],
            ["完成驗收", "由使用者確認修好，而不是由派工者單方面結案。"],
            ["路線回寫", "把缺件、延誤與重複故障回寫進下一輪索引。"],
        ],
        priorities=[
            ["入口標準", "先讓每一筆報修有一致的物件、位置與時間欄位。", "INPUT", "39%"],
            ["交接透明", "讓備件、志工與使用者看見同一條轉運進度。", "ROUTE", "37%"],
            ["回訪閉環", "修好只是中途；七日內的回訪才完成一條路線。", "VERIFY", "24%"],
        ],
        metrics=[
            ["9站", "社區備件點", "服務藍圖的候選節點", "STATION"],
            ["76%", "一次派工完成率", "第一輪流程的概念目標", "FLOW"],
            ["2.4日", "平均等待時間", "從報修到首次到場的模擬值", "WAIT"],
            ["5步", "完整回訪路徑", "報修、分流、轉運、修復、回看", "LOOP"],
        ],
        timeline=[
            ["A", "收進報修", "將描述整理成可分流的最小單位。"],
            ["B", "查備件", "先查附近節點，再決定是否調貨。"],
            ["C", "派工交接", "把技能、距離與抵達時間放在一條線上。"],
            ["D", "現場修復", "保留缺件與重複故障的證據。"],
            ["E", "使用者回看", "確認修復是否真的結束問題。"],
        ],
        quote="路線圖不是把所有人畫在一起，\n而是讓每一次交接都有下一站。",
        attribution="NEIGHBORHOOD REPAIR ROUTE · 26",
        closing=["讓維修從一筆報修，\n走成一條有人接手的路。", "先把一個社區的備件與回訪串起來，再決定要不要擴到下一區。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-5-panel-rows", "strategic-priorities", "cards-1-plus-4",
            "recommendation-stack", "comparison-table", "dashboard-overview", "process-flow",
            "matrix-4quadrant", "timeline-milestones", "quote-focus", "title-center",
        ],
        direction={
            "visual_genre": "product-narrative",
            "narrative_metaphor": "把社區維修視為一張轉乘地圖，每個零件、角色與回訪都必須在下一站留下可用的訊號。",
            "signature_name": "transfer-spine",
            "signature_concept": "一條橙青轉運主線依頁面語意變成入口、交接、流程、環線或驗收基準。",
            "variations": ["station", "platform", "junction", "loop"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "route", "crop": "one-edge",
            "whitespace": "在主線兩側保留站點空間，避免每個節點被等寬卡片化。", "alignment": "left",
            "edge": "continuation-across-slides", "type_role": "index", "family": "display-plus-text",
            "primary_job": "neutral-stage", "accent_job": "classification", "accent_limit": "主線與轉運節點不超過兩種強調色。",
            "forbidden": ["equal-rounded-card-wall", "repeated-diagonal-background-route", "floating-pills", "generic-purple-orange-gradient", "fake-dashboard"],
            "anti_reference": "把一條斜線重複十二頁當成品牌背景，卻沒有讓它承擔交接或閱讀順序。",
        },
    ),
    _entry(
        preset_id="scent-veil-launch",
        base_theme="brand-editorial",
        story_id="tactile-packaging-launch",
        title="看不見的觸感，也能成為品牌入口",
        subtitle="從開箱、辨識到回收，設計一套讓不同手感都能讀懂的包裝發布節奏",
        speaker="TACTILE PACKAGING STUDIO",
        org="LAUNCH JOURNAL · 2026",
        chapter_number="27",
        toc=[
            ["觸感入口", "先讓使用者不用看字，也能知道從哪裡開始。"],
            ["辨識節點", "把材質差異、開口方向與用途做成可被摸到的線索。"],
            ["使用節奏", "讓拆封、取用、保存與回收各自有清楚手感。"],
            ["多感官語氣", "同一品牌不靠複雜圖形，也能維持穩定辨識。"],
            ["試用回訪", "把不同使用者的觸感回饋收回產品設計。"],
            ["回收出口", "在最後一步仍保留完整、可理解的指示。"],
        ],
        priorities=[
            ["先做入口", "以一個清楚的開口與觸感標記降低第一次使用的猜測。", "OPEN", "43%"],
            ["維持語氣", "讓材質、字體與距離共同形成品牌辨識，而非只靠圖案。", "TONE", "32%"],
            ["設計回收", "把使用後的拆解與回收也當作發布體驗的一部分。", "RETURN", "25%"],
        ],
        metrics=[
            ["4種", "觸感入口", "開口、紋理、厚薄、方向", "TOUCH"],
            ["82%", "首次辨識成功", "概念測試的觀察目標", "READ"],
            ["3段", "開箱節奏", "拿起、打開、回收", "RITUAL"],
            ["1條", "玫瑰索引線", "每頁只保留一個主要 thread", "THREAD"],
        ],
        timeline=[
            ["01", "觸感採集", "把材質與使用動作分開記錄。"],
            ["02", "入口試作", "只改一個開口，觀察第一次辨識。"],
            ["03", "整體發布", "把使用、保存與回收放回同一條節奏。"],
            ["04", "多感官回看", "比較不同使用者的觸感語言。"],
            ["05", "回收收束", "讓最後一個動作仍保留品牌的照顧。"],
        ],
        quote="好的包裝不是讓人多看一眼，\n而是讓人不用猜就知道下一個動作。",
        attribution="TACTILE PACKAGING STUDIO · 27",
        closing=["讓手先讀懂，\n再讓品牌被記住。", "從一個可以被摸到的入口開始，讓包裝完整走過使用與回收。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-4-panel-grid", "cards-1-plus-4", "split-comparison",
            "kpi-scorecards", "before-after", "comparison-table", "timeline-milestones", "quote-focus", "title-center",
        ],
        direction={
            "visual_genre": "cultural-exhibition",
            "narrative_metaphor": "把包裝發布當成一條柔軟的觸感線，從第一次接觸、辨識、使用一路延伸到回收。",
            "signature_name": "tactile-scent-thread",
            "signature_concept": "一條細玫瑰線只作為文字框線、分隔或流程連接，讓觸感語意而非霧氣成為主體。",
            "variations": ["thread", "veil-pane", "index-node", "state-pair"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "center", "axis": "horizontal", "crop": "frame-within-frame",
            "whitespace": "紙面留白要讓手感語彙有停頓，不把每個頁面塞滿薄霧與卡片。", "alignment": "left",
            "edge": "structural-index", "type_role": "protagonist", "family": "single-family",
            "primary_job": "atmospheric", "accent_job": "single-emotional-focus", "accent_limit": "玫瑰色 thread 每頁只出現一次主要節點。",
            "forbidden": ["glassmorphism-everywhere", "concentric-circles", "floating-pills", "equal-rounded-card-wall", "generic-right-side-illustration-cover"],
            "anti_reference": "用霧、香水瓶與漂浮光暈替代真正的使用動作，讓無障礙入口只剩氣氛。",
        },
    ),
    _entry(
        preset_id="ai-operations-signal",
        base_theme="dark-circuit",
        story_id="research-retrace-rhythm",
        title="AI 研究團隊的速度，必須能被回溯",
        subtitle="把假設、證據、責任與撤回條件串成一條可追蹤的研究運作軸",
        speaker="RETRACE RESEARCH OPERATIONS",
        org="AI GOVERNANCE LAB · 2026",
        chapter_number="28",
        toc=[
            ["假設入口", "先寫清楚想證明什麼，再決定要跑哪一種實驗。"],
            ["證據分層", "把觀察、推論、引用與未驗證部分分開標記。"],
            ["責任交接", "每個研究動作都有一位能回答問題的人。"],
            ["控制門檻", "達到什麼條件才可以進入下一輪或接觸使用者。"],
            ["撤回條件", "結果不穩定時，先知道怎麼停下來。"],
            ["回寫節奏", "把失敗與例外寫回規則，不只留下成功 demo。"],
        ],
        priorities=[
            ["可回溯假設", "每次實驗都保留輸入、版本、評估與未解問題。", "TRACE", "40%"],
            ["交接可見", "讓研究、工程、法遵與產品看見同一個狀態。", "HANDOFF", "34%"],
            ["撤回優先", "任何不可解釋的漂移都觸發停用與人工複核。", "STOP", "26%"],
        ],
        metrics=[
            ["8層", "研究紀錄", "假設到回寫的操作分層", "LOG"],
            ["93%", "版本可追溯", "原型驗收目標，不是生產指標", "TRACE"],
            ["14分", "交接確認時間", "從研究到產品的演練值", "HANDOFF"],
            ["2次", "撤回演練", "先做停止，再做擴張", "STOP"],
        ],
        timeline=[
            ["T0", "寫下假設", "不讓 prompt 或 demo 代替問題定義。"],
            ["T1", "固定證據", "把來源、資料版本與評估口徑放在同一筆。"],
            ["T2", "交接檢查", "讓下一個角色能重播而不是重新猜。"],
            ["T3", "撤回演練", "用失敗路徑驗證控制是否真的有效。"],
            ["T4", "回寫規則", "將例外與不確定性納入下一輪研究。"],
        ],
        quote="研究速度的上限，\n不是多快產生答案，而是多快知道答案不能用。",
        attribution="RETRACE RESEARCH OPERATIONS · 28",
        closing=["讓每一次加速，\n都帶著一條可以回頭的路。", "先用可回溯的研究紀錄建立共同節奏，再把通過驗證的流程交給更多人。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-5-panel-rows", "process-flow", "matrix-4quadrant",
            "kpi-scorecards", "cards-1-plus-4", "comparison-table", "timeline-vertical", "before-after", "title-center",
        ],
        direction={
            "visual_genre": "institutional-editorial",
            "narrative_metaphor": "把 AI 研究畫成一條有控制點的運作軸，速度、證據、責任與撤回都在同一條線上留下痕跡。",
            "signature_name": "operating-axis",
            "signature_concept": "藍色交接線與萊姆狀態線只連接任務、證據、控制與回寫，不作裝飾性網格。",
            "variations": ["handoff", "control-ledger", "status-strip", "rollback"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "vertical", "crop": "one-edge",
            "whitespace": "深色底面保持低裝飾，讓狀態線與撤回門檻成為唯一峰值。", "alignment": "left",
            "edge": "structural-index", "type_role": "evidence-label", "family": "display-plus-text",
            "primary_job": "institutional", "accent_job": "status", "accent_limit": "狀態色只能表示已驗證、待複核或停止。",
            "forbidden": ["glow-plus-grid-plus-grain", "fake-dashboard", "glassmorphism-everywhere", "floating-pills", "equal-rounded-card-wall"],
            "anti_reference": "把每個研究步驟都做成亮色科技卡片，卻沒有顯示證據與撤回條件。",
        },
    ),
    _entry(
        preset_id="line-argument-journal",
        base_theme="grainy-editorial",
        story_id="public-proposal-proof-line",
        title="一項公共提案，先把主張與證據排成同一條線",
        subtitle="讓問題、來源、反方意見與承諾逐段可核對，不用口號跳過推論",
        speaker="PUBLIC ARGUMENT STUDIO",
        org="CIVIC PROOF JOURNAL · 2026",
        chapter_number="31",
        toc=[
            ["主張入口", "先用一句話界定提案要改變的公共問題。"],
            ["證據來源", "每個數字與案例都保留來源、日期與限制。"],
            ["反方問題", "把最可能推翻提案的疑問放進主要閱讀線。"],
            ["替代方案", "比較不行動、局部試做與完整推進的代價。"],
            ["責任承諾", "說清楚誰決定、誰執行、誰能要求停止。"],
            ["公開回看", "用固定節奏公布保留、修正與撤回的理由。"],
        ],
        priorities=[
            ["先鎖主張", "主張只保留一個可被證據支持或推翻的句子。", "CLAIM", "40%"],
            ["補齊反證", "把不利資料與未解問題放進同一份證據表。", "PROOF", "35%"],
            ["寫明承諾", "每個推進節點都附責任人與停止條件。", "PACT", "25%"],
        ],
        metrics=[
            ["6段", "論證鏈", "主張到公開回看的必要節點", "CHAIN"],
            ["12筆", "來源紀錄", "內容測試用的證據索引", "SOURCE"],
            ["3案", "替代路徑", "不行動、試做、完整推進", "OPTION"],
            ["2次", "公開回看", "pilot 的預定檢查節奏", "REVIEW"],
        ],
        timeline=[
            ["D01", "寫下主張", "確認一句話可以被驗證。"],
            ["D05", "整理證據", "標出來源、限制與資料缺口。"],
            ["D09", "納入反方", "用最強反例測試論證是否成立。"],
            ["D14", "小規模試做", "只驗證最關鍵的因果環節。"],
            ["D30", "公開回看", "決定保留、修正或停止。"],
        ],
        quote="可信的提案不是沒有反對聲音，\n而是每個反對聲音都有一個可被回答的位置。",
        attribution="PUBLIC ARGUMENT STUDIO · 31",
        closing=["讓每一個主張，\n都能沿著證據走回責任。", "先完成一條可被反駁的論證線，再邀請更多人加入決策。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-5-panel-rows", "chapter-opener", "recommendation-stack",
            "before-after", "recommendation-stack", "process-flow", "matrix-4quadrant",
            "dashboard-overview", "timeline-milestones", "quote-focus", "title-center",
        ],
        direction={
            "visual_genre": "editorial-argument-journal",
            "narrative_metaphor": "把論證視為一條可逐段核對的編輯主線，證據與反證只在推論轉折處出現。",
            "signature_name": "proof-rule",
            "signature_concept": "細長規則線只負責串接主張、證據與責任，不形成裝飾邊框。",
            "variations": ["claim-rule", "source-index", "counterpoint", "commitment-line"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "editorial-columns", "crop": "one-edge",
            "whitespace": "主張周圍保留大片紙面，證據密度只在中段逐步增加。", "alignment": "left",
            "edge": "structural-index", "type_role": "protagonist", "family": "serif-sans-pair",
            "primary_job": "documentary", "accent_job": "evidence", "accent_limit": "酒紅只標示反證與承諾，不作大片填色。",
            "forbidden": ["concentric-circles", "decorative-arcs", "equal-rounded-card-wall", "floating-pills", "fake-dashboard"],
            "anti_reference": "用巨大幾何與滿版格線營造理性，卻沒有讓主張回到來源與責任。",
        },
    ),
    _entry(
        preset_id="field-index-manual",
        base_theme="grainy-editorial",
        story_id="street-tree-care-index",
        title="每一棵行道樹，都需要一份能被接手的照護索引",
        subtitle="把位置、健康訊號、處置與回訪整理成現場人員能快速更新的手冊",
        speaker="URBAN TREE FIELD UNIT",
        org="CARE INDEX MANUAL · 2026",
        chapter_number="32",
        toc=[
            ["位置編碼", "先用街廓與樹位建立不會重複的現場索引。"],
            ["健康訊號", "只記錄可觀察的葉況、樹皮、傾斜與根域變化。"],
            ["風險分級", "把立即處理與持續觀察分成不同責任節奏。"],
            ["處置紀錄", "每次修剪、支撐與澆灌都留下原因與日期。"],
            ["居民回報", "讓非專業回報也能進入同一份索引。"],
            ["季節回訪", "用固定季節重新核對狀態，不以單次照片結案。"],
        ],
        priorities=[
            ["統一編碼", "先讓所有角色指向同一棵樹與同一筆紀錄。", "INDEX", "42%"],
            ["分清風險", "高風險即時處理，低風險保留觀察證據。", "RISK", "34%"],
            ["固定回訪", "處置後必須回到現場驗證效果。", "RETURN", "24%"],
        ],
        metrics=[
            ["24株", "pilot 樹位", "內容測試用的索引規模", "TREES"],
            ["4級", "風險分類", "觀察、安排、優先、立即", "RISK"],
            ["6欄", "現場紀錄", "位置、訊號、照片、處置、責任、回訪", "LOG"],
            ["3季", "回訪節奏", "春、夏、秋的概念排程", "CYCLE"],
        ],
        timeline=[
            ["W01", "建立樹位", "確認編碼與現場標記一致。"],
            ["W02", "完成初檢", "只記錄可被重現的觀察。"],
            ["W04", "安排處置", "依風險分派責任與期限。"],
            ["W08", "第一次回訪", "確認處置是否改善風險。"],
            ["季末", "更新手冊", "將例外寫回下一輪欄位。"],
        ],
        quote="好的索引不是把現場變成表格，\n而是讓下一個人不用重新猜。",
        attribution="URBAN TREE FIELD UNIT · 32",
        closing=["讓每一次照護，\n都成為下一次判斷的起點。", "先用一條街測試索引與回訪，再決定如何擴大巡檢範圍。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-4-panel-rows", "chapter-opener", "cards-1-plus-4",
            "strategic-priorities", "comparison-table", "process-flow", "kpi-scorecards",
            "dashboard-overview", "timeline-milestones", "quote-focus", "title-center",
        ],
        direction={
            "visual_genre": "field-index-publication",
            "narrative_metaphor": "把巡檢手冊視為可翻查的田野索引，每個標記都對應一個位置、狀態或回訪。",
            "signature_name": "field-tab-system",
            "signature_concept": "窄頁籤與編號只負責定位紀錄，不生成仿植物插圖。",
            "variations": ["tab", "specimen-row", "risk-mark", "return-stamp"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "editorial-columns", "crop": "frame-within-frame",
            "whitespace": "索引欄固定收窄，主要紀錄保留可手寫般的呼吸距離。", "alignment": "left",
            "edge": "structural-index", "type_role": "index", "family": "serif-sans-pair",
            "primary_job": "documentary", "accent_job": "classification", "accent_limit": "分類色只標示風險與回訪狀態。",
            "forbidden": ["botanical-stickers", "concentric-circles", "decorative-arcs", "equal-rounded-card-wall", "floating-pills"],
            "anti_reference": "用葉片貼圖冒充田野感，卻讓位置、風險與回訪關係變得難讀。",
        },
    ),
    _entry(
        preset_id="tide-signal-observatory",
        base_theme="brand-editorial",
        story_id="shoreline-change-watch",
        title="海岸每天都在變，觀測必須留下可比較的基準",
        subtitle="把水位、侵蝕、生態與居民回報串成不誇大、可追蹤的沿岸觀測節奏",
        speaker="SHORELINE FIELD OBSERVATORY",
        org="COAST WATCH · 2026",
        chapter_number="33",
        toc=[
            ["固定基準", "先確定每次觀測都從相同位置與高度開始。"],
            ["水位紀錄", "保留時間、天候與不能直接比較的條件。"],
            ["侵蝕訊號", "把可見變化與推論分開，不用單張照片下結論。"],
            ["生態節點", "記錄棲地變化，同時標示觀測限制。"],
            ["居民回報", "讓日常使用者補足研究團隊看不到的時段。"],
            ["行動門檻", "只有累積證據跨過門檻才啟動處置。"],
        ],
        priorities=[
            ["守住基準", "先讓位置、時間與觀測方法可以重複。", "BASE", "41%"],
            ["分開推論", "觀察、推測與行動建議使用不同標記。", "SIGNAL", "35%"],
            ["設定門檻", "避免單一事件直接觸發永久工程。", "GATE", "24%"],
        ],
        metrics=[
            ["8點", "固定觀測站", "沿岸情境中的概念配置", "STATION"],
            ["4類", "變化訊號", "水位、侵蝕、生態、使用", "SIGNAL"],
            ["30日", "比較窗口", "pilot 的觀察節奏", "WINDOW"],
            ["3級", "行動門檻", "觀察、準備、介入", "GATE"],
        ],
        timeline=[
            ["D01", "設定基準", "固定觀測位置與拍攝方向。"],
            ["D07", "第一次比較", "標出可比與不可比資料。"],
            ["D14", "居民回報", "補足夜間與假日使用訊號。"],
            ["D21", "跨域判讀", "讓工程與生態角色共同檢查。"],
            ["D30", "決定行動", "依門檻選擇觀察、準備或介入。"],
        ],
        quote="觀測不是替海岸說話，\n而是讓每一次變化都有被正確比較的條件。",
        attribution="SHORELINE FIELD OBSERVATORY · 33",
        closing=["先留下可比較的基準，\n再決定海岸真的需要什麼。", "用一個月建立共同觀測節奏，不讓單張影像取代長期判讀。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-4-panel-grid", "cards-1-plus-4", "before-after",
            "kpi-scorecards", "process-flow", "comparison-table", "timeline-milestones", "quote-focus", "title-center",
        ],
        direction={
            "visual_genre": "coastal-observation-journal",
            "narrative_metaphor": "把沿岸變化整理成低頻、可比較的觀測帶，視覺停頓代表尚未下結論。",
            "signature_name": "tidal-baseline",
            "signature_concept": "水平基準線只標示比較位置與時間，不畫波浪、圓環或儀表盤。",
            "variations": ["baseline", "station", "comparison-strip", "threshold"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "horizontal", "crop": "one-edge",
            "whitespace": "大面積安靜底色作為未下結論的觀測空間。", "alignment": "left",
            "edge": "one-edge-crop", "type_role": "evidence-label", "family": "single-family",
            "primary_job": "documentary", "accent_job": "status", "accent_limit": "橙色只表示跨過門檻的訊號。",
            "forbidden": ["concentric-circles", "wave-illustration", "decorative-arcs", "compass-symbols", "fake-dashboard"],
            "anti_reference": "用海浪、羅盤與圓環堆出海洋氣氛，卻沒有保留可比較的觀測基準。",
        },
    ),
    _entry(
        preset_id="craft-archive-editions",
        base_theme="grainy-editorial",
        story_id="repair-technique-living-archive",
        title="修復手藝要留下來，不能只留下完成品",
        subtitle="把材料判斷、操作手勢、失敗與回訪編成下一位學徒能接續的活檔案",
        speaker="REPAIR CRAFT ARCHIVE",
        org="MAKING MEMORY · 2026",
        chapter_number="34",
        toc=[
            ["材料辨識", "先記錄材質、老化與不能確認的部分。"],
            ["工具選擇", "說明每件工具為何適合這一步。"],
            ["操作手勢", "用步驟與力道描述可重複的動作。"],
            ["失敗樣本", "保留錯誤與修正，不只展示成功結果。"],
            ["學徒接手", "讓下一位操作者能從同一基準繼續。"],
            ["回訪紀錄", "修復後再次檢查材料如何變化。"],
        ],
        priorities=[
            ["記下判斷", "操作前先寫材料狀態與選擇理由。", "MATERIAL", "40%"],
            ["保存失敗", "失敗樣本與成功步驟使用同等索引。", "TRACE", "34%"],
            ["安排接手", "每個階段都有下一位可讀的交接註記。", "HANDOFF", "26%"],
        ],
        metrics=[
            ["7步", "修復流程", "從辨識到回訪的內容結構", "STEPS"],
            ["5種", "材料狀態", "內容測試用分類", "MATERIAL"],
            ["9筆", "失敗樣本", "保留修正原因與結果", "TRACE"],
            ["2輪", "學徒接手", "pilot 的交接演練", "HANDOFF"],
        ],
        timeline=[
            ["01", "建立材料卡", "標出已知、未知與風險。"],
            ["02", "記錄手勢", "拆解工具、方向與力道。"],
            ["03", "保存失敗", "留下無效做法與修正理由。"],
            ["04", "學徒重做", "由另一位操作者重現步驟。"],
            ["05", "回訪材料", "確認修復結果是否穩定。"],
        ],
        quote="技藝真正被保存的時刻，\n是另一雙手能讀懂上一雙手為何這樣做。",
        attribution="REPAIR CRAFT ARCHIVE · 34",
        closing=["留下判斷與失敗，\n手藝才有下一個版本。", "先完成一件物件的全流程檔案，再測試學徒能否獨立接手。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-4-panel-rows", "strategic-priorities", "before-after",
            "cards-1-plus-4", "process-flow", "comparison-table", "timeline-milestones", "quote-focus", "title-center",
        ],
        direction={
            "visual_genre": "craft-archive-publication",
            "narrative_metaphor": "把修復過程編成一冊可接手的材料檔案，織紋只代表步驟交接。",
            "signature_name": "material-weave-index",
            "signature_concept": "短線與編碼建立材料、工具與手勢對照，不使用仿古貼圖。",
            "variations": ["material-card", "tool-index", "failure-note", "handoff-thread"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "editorial-columns", "crop": "frame-within-frame",
            "whitespace": "紙面與材料紀錄之間保留明顯間隔，失敗樣本頁才提高密度。", "alignment": "left",
            "edge": "structural-index", "type_role": "index", "family": "serif-sans-pair",
            "primary_job": "documentary", "accent_job": "classification", "accent_limit": "染色標記只用於材料與風險分類。",
            "forbidden": ["craft-stickers", "concentric-circles", "decorative-arcs", "equal-rounded-card-wall", "fake-aged-paper"],
            "anti_reference": "堆疊印章、線團與仿古紙張，卻沒有讓操作判斷被下一位學徒讀懂。",
        },
    ),
    _entry(
        preset_id="incident-command-redline",
        base_theme="dark-circuit",
        story_id="first-hour-incident-command",
        title="資安事件的第一小時，先把責任與停止線畫清楚",
        subtitle="用單一事件節奏整合偵測、隔離、通報、復原與事後回寫",
        speaker="INCIDENT COMMAND CELL",
        org="FIRST HOUR PROTOCOL · 2026",
        chapter_number="35",
        toc=[
            ["確認訊號", "先區分可疑現象與已被驗證的事件。"],
            ["指定指揮", "讓一位角色負責節奏與跨組決定。"],
            ["隔離範圍", "只切斷被證據支持的影響面。"],
            ["對外通報", "依已知事實更新，不用猜測填補空白。"],
            ["復原門檻", "明定何時能恢復與誰批准。"],
            ["事後回寫", "把例外、延誤與誤判寫回操作卡。"],
        ],
        priorities=[
            ["單一指揮", "所有跨組決定由同一事件節奏協調。", "COMMAND", "42%"],
            ["證據隔離", "隔離動作必須連到可重播的證據。", "CONTAIN", "34%"],
            ["停止有據", "復原或擴大處置都有明確批准門檻。", "GATE", "24%"],
        ],
        metrics=[
            ["6關", "事件節點", "偵測到回寫的操作鏈", "STAGE"],
            ["15分", "首輪確認", "演練用目標，不是實績", "TIME"],
            ["4角", "責任角色", "指揮、技術、溝通、業務", "ROLE"],
            ["2次", "撤回演練", "驗證停止與復原路徑", "ROLLBACK"],
        ],
        timeline=[
            ["T+00", "接收訊號", "先保留原始觀察與來源。"],
            ["T+10", "指定指揮", "建立單一決策節奏。"],
            ["T+20", "隔離影響", "依證據縮小可疑範圍。"],
            ["T+40", "更新利害關係人", "只發布已確認資訊。"],
            ["T+60", "決定下一階段", "選擇復原、維持或擴大。"],
        ],
        quote="事件處理的速度，\n來自每個人都知道誰能決定停止。",
        attribution="INCIDENT COMMAND CELL · 35",
        closing=["先守住責任線，\n再讓系統往前走。", "用一次完整演練驗證停止與復原，不把漂亮儀表板當成指揮。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-5-panel-rows", "process-flow", "matrix-4quadrant",
            "kpi-scorecards", "before-after", "comparison-table", "timeline-milestones", "highlight-callout", "title-center",
        ],
        direction={
            "visual_genre": "incident-command-ledger",
            "narrative_metaphor": "把事件處理畫成一條有明確停止點的紅線，每個動作都帶著責任與證據。",
            "signature_name": "command-redline",
            "signature_concept": "紅色只表示已確認事件、停止與批准門檻，不生成科技網格。",
            "variations": ["alert-line", "containment", "handoff", "recovery-gate"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "vertical", "crop": "one-edge",
            "whitespace": "深色低頻底面讓紅線只在真正決策處出現。", "alignment": "left",
            "edge": "structural-index", "type_role": "evidence-label", "family": "display-plus-text",
            "primary_job": "institutional", "accent_job": "status", "accent_limit": "紅色不得用於一般裝飾或大面積表面。",
            "forbidden": ["glow-grid", "concentric-circles", "radar-symbols", "decorative-arcs", "fake-dashboard"],
            "anti_reference": "用雷達、網格與大量紅光製造緊張，卻看不出誰在何時能做決定。",
        },
    ),
    _entry(
        preset_id="harbor-ribbon-program",
        base_theme="brand-editorial",
        story_id="harbor-arrival-transfer",
        title="抵達港區之後，轉乘不該從重新找路開始",
        subtitle="把下船、查詢、候車、行李與無障礙協助編成一條連續抵達帶",
        speaker="HARBOR ARRIVAL PROGRAM",
        org="PORT TRANSFER LAB · 2026",
        chapter_number="36",
        toc=[
            ["下船入口", "讓旅客一離船就看見下一個行動。"],
            ["資訊交接", "船班與陸運使用同一套時間與狀態語言。"],
            ["候車節奏", "把等待、改點與延誤分成可理解的狀態。"],
            ["行李路徑", "避免行李與人流在轉折處互相阻塞。"],
            ["協助入口", "無障礙與語言協助不藏在服務台後。"],
            ["離港回看", "用抵達後回饋校正下一輪指引。"],
        ],
        priorities=[
            ["連續指引", "每個轉折都能看到下一站與剩餘距離。", "ROUTE", "43%"],
            ["狀態共用", "船班、接駁與現場使用同一組狀態。", "STATUS", "33%"],
            ["協助可見", "需要協助的人不必離開主要路徑尋找入口。", "ACCESS", "24%"],
        ],
        metrics=[
            ["5站", "抵達節點", "情境設計的轉乘段落", "STATION"],
            ["3色", "共同狀態", "正常、等待、改點", "STATUS"],
            ["9分", "查找時間", "pilot 的目標上限", "TIME"],
            ["2路", "行李動線", "人流與大件行李分流", "FLOW"],
        ],
        timeline=[
            ["P01", "下船辨識", "確認第一個可見轉乘訊號。"],
            ["P02", "狀態同步", "統一船班與接駁更新。"],
            ["P03", "候車測試", "觀察等待與改點是否可理解。"],
            ["P04", "協助演練", "驗證無障礙入口是否在主路徑。"],
            ["P05", "離港回看", "收回旅客的最後一段經驗。"],
        ],
        quote="好的抵達不是看到更多標誌，\n而是每一次轉彎都知道自己仍在同一條路上。",
        attribution="HARBOR ARRIVAL PROGRAM · 36",
        closing=["讓港口的最後一段，\n成為城市的第一個清楚動作。", "先驗證一條抵達帶，再把共用狀態擴到更多船班與接駁。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-6-panel-rows", "cards-1-plus-4", "process-flow",
            "before-after", "kpi-scorecards", "comparison-table", "timeline-milestones", "quote-focus", "title-center",
        ],
        direction={
            "visual_genre": "public-program-wayfinding",
            "narrative_metaphor": "把抵達過程視為一條持續可見的港灣帶，顏色只標示站點與狀態。",
            "signature_name": "arrival-ribbon",
            "signature_concept": "帶狀索引只承擔閱讀順序與轉乘交接，不變成滿版波浪。",
            "variations": ["arrival", "handoff", "waiting-band", "access-marker"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "route", "crop": "one-edge",
            "whitespace": "轉乘帶的一側保持安靜，讓文字與狀態有固定落點。", "alignment": "left",
            "edge": "continuation-across-slides", "type_role": "index", "family": "single-family",
            "primary_job": "neutral-stage", "accent_job": "classification", "accent_limit": "主帶與狀態最多使用兩個強調色。",
            "forbidden": ["wave-illustration", "concentric-circles", "decorative-arcs", "floating-pills", "repeated-diagonal-route"],
            "anti_reference": "把每頁畫成波浪與緞帶海報，卻沒有形成真正連續的轉乘路徑。",
        },
    ),
    _entry(
        preset_id="neighborhood-newsroom-proof",
        base_theme="grainy-editorial",
        story_id="local-news-source-proof",
        title="社區消息發布前，每一個主張都要能走回來源",
        subtitle="用採訪、文件、交叉核對、修正與回覆建立小型新聞室的公開證據鏈",
        speaker="NEIGHBORHOOD NEWSROOM",
        org="PUBLIC PROOF DESK · 2026",
        chapter_number="37",
        toc=[
            ["問題定義", "先說清楚居民需要知道的是哪一件事。"],
            ["來源分層", "把當事人、文件、觀察與傳聞分開。"],
            ["交叉核對", "重要主張至少有兩條獨立驗證路徑。"],
            ["發布門檻", "未確認資訊保留狀態，不假裝完整。"],
            ["修正紀錄", "更正內容保留時間、理由與影響範圍。"],
            ["公開回覆", "讓提問者知道編輯部如何處理。"],
        ],
        priorities=[
            ["來源可追", "每個關鍵句都有可回到的採訪或文件。", "SOURCE", "42%"],
            ["不確定可見", "未確認與爭議資訊使用明確狀態。", "STATUS", "34%"],
            ["修正不消失", "每次更正都保留版本與影響說明。", "CORRECT", "24%"],
        ],
        metrics=[
            ["10筆", "來源卡", "內容測試用的採訪與文件索引", "SOURCE"],
            ["2路", "交叉核對", "重要主張的最低驗證路徑", "VERIFY"],
            ["4態", "發布狀態", "草稿、核對、發布、修正", "STATUS"],
            ["24時", "回覆窗口", "pilot 的目標節奏", "REPLY"],
        ],
        timeline=[
            ["09:00", "定義問題", "確認報導要回答的公共問題。"],
            ["11:00", "完成採訪", "區分事實、經驗與推測。"],
            ["14:00", "交叉核對", "補足第二條獨立來源。"],
            ["17:00", "發布審查", "標出尚未確認的部分。"],
            ["NEXT", "公開回覆", "持續更新修正與讀者問題。"],
        ],
        quote="可信不是從來不出錯，\n而是錯誤發生時仍看得見來源、版本與修正。",
        attribution="NEIGHBORHOOD NEWSROOM · 37",
        closing=["讓每一則消息，\n都保留一條回到來源的路。", "先把一篇報導完整走過核對與修正，再建立固定發布節奏。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-5-panel-rows", "strategic-priorities", "before-after",
            "recommendation-stack", "process-flow", "comparison-table", "timeline-milestones", "quote-focus", "title-center",
        ],
        direction={
            "visual_genre": "newsroom-proof-sheet",
            "narrative_metaphor": "把報導當成一張可追蹤的校樣，來源、狀態與修正都留在同一閱讀面。",
            "signature_name": "proof-margin",
            "signature_concept": "窄邊校樣註記只標示來源與修正，不使用報紙拼貼裝飾。",
            "variations": ["source-note", "verification-rule", "status-mark", "correction-log"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "editorial-columns", "crop": "frame-within-frame",
            "whitespace": "正文與校樣邊註保持分離，未確認資訊周圍保留更多空間。", "alignment": "left",
            "edge": "structural-index", "type_role": "evidence-label", "family": "serif-sans-pair",
            "primary_job": "documentary", "accent_job": "status", "accent_limit": "紅色只用於修正與未確認狀態。",
            "forbidden": ["newspaper-collage", "concentric-circles", "decorative-arcs", "equal-rounded-card-wall", "floating-pills"],
            "anti_reference": "用報紙剪貼與半調網點製造新聞感，卻找不到主張對應的來源。",
        },
    ),
    _entry(
        preset_id="restoration-blueprint-ledger",
        base_theme="brand-editorial",
        story_id="old-house-restoration-ledger",
        title="老屋修復不是回到原樣，而是讓每個改動都有依據",
        subtitle="把現況測繪、材料判讀、施工決策與驗收版本寫進同一張修復藍圖",
        speaker="RESTORATION FIELD OFFICE",
        org="BUILDING CARE LEDGER · 2026",
        chapter_number="38",
        toc=[
            ["現況測繪", "先記錄尺寸、損壞與仍待確認的地方。"],
            ["價值判讀", "分清必須保留、可以調整與需要替換的元素。"],
            ["材料試驗", "用小樣確認相容性，再進入大面積施工。"],
            ["施工留痕", "每個改動保留位置、日期、材料與責任人。"],
            ["版本比較", "驗收時回看原始狀態與核准方案。"],
            ["維護交接", "把未解問題與下一次檢查留給使用者。"],
        ],
        priorities=[
            ["先建基準", "現況測繪與照片使用同一位置索引。", "BASE", "41%"],
            ["小樣先行", "未知材料先測試相容性，不直接全面施工。", "TEST", "35%"],
            ["版本可追", "每次改動都有核准、執行與驗收紀錄。", "VERSION", "24%"],
        ],
        metrics=[
            ["12區", "現況分區", "內容測試用的測繪範圍", "ZONE"],
            ["5類", "材料狀態", "保留、修補、替換、觀察、未知", "MATERIAL"],
            ["3版", "決策版本", "現況、核准、完工", "VERSION"],
            ["2輪", "驗收回看", "施工中與完工後", "REVIEW"],
        ],
        timeline=[
            ["S01", "完成測繪", "建立空間與損壞索引。"],
            ["S02", "確認價值", "標出保留與可調整範圍。"],
            ["S03", "材料小樣", "測試相容性與可逆性。"],
            ["S04", "分段施工", "每個改動同步更新版本。"],
            ["S05", "交接維護", "留下未解問題與回訪節奏。"],
        ],
        quote="修復的可信度，\n不在於看起來多新，而在於每個改動都能被說明。",
        attribution="RESTORATION FIELD OFFICE · 38",
        closing=["把每個改動寫進藍圖，\n老屋才有下一段可維護的生命。", "先完成一個房間的基準、試驗與版本比較，再擴大施工。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-4-panel-rows", "chapter-opener", "recommendation-stack",
            "before-after", "process-flow", "comparison-table", "timeline-milestones", "quote-focus", "title-center",
        ],
        direction={
            "visual_genre": "restoration-blueprint-ledger",
            "narrative_metaphor": "把修復視為可回查的版本藍圖，線條只標示現況、改動與驗收關係。",
            "signature_name": "restoration-trace",
            "signature_concept": "藍圖細線與版本標記服務測繪與比較，不生成滿版格線。",
            "variations": ["survey", "material-test", "version-compare", "handoff-note"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "editorial-columns", "crop": "frame-within-frame",
            "whitespace": "測繪線周圍保留乾淨紙面，資訊密度集中在版本比較頁。", "alignment": "left",
            "edge": "structural-index", "type_role": "index", "family": "single-family",
            "primary_job": "documentary", "accent_job": "classification", "accent_limit": "藍色標記只指向改動與版本。",
            "forbidden": ["full-page-grid", "concentric-circles", "decorative-arcs", "equal-rounded-card-wall", "fake-technical-symbols"],
            "anti_reference": "用格線、羅盤與工程符號堆出藍圖感，卻沒有呈現改動前後與責任。",
        },
    ),
    _entry(
        preset_id="brave-classroom-contours",
        base_theme="soft-organic-education",
        story_id="quiet-classroom-participation",
        title="課堂參與，不該只獎勵最快舉手的人",
        subtitle="用靜默整理、書寫、兩人交換與共同發表，讓不同節奏都能留下理解證據",
        speaker="BRAVE CLASSROOM LAB",
        org="LEARNING PARTICIPATION · 2026",
        chapter_number="39",
        toc=[
            ["靜默整理", "先給每位學生獨立形成想法的時間。"],
            ["寫下理解", "用一句話或圖示留下目前的理解。"],
            ["兩人交換", "在低壓情境中測試想法是否說得清楚。"],
            ["小組整合", "保留差異，不急著壓成唯一答案。"],
            ["共同發表", "讓發表代表小組證據，不代表個人競速。"],
            ["課後回看", "用離場回覆調整下一堂課的入口。"],
        ],
        priorities=[
            ["先有思考時間", "每個問題先留一段不被打斷的整理時間。", "THINK", "40%"],
            ["留下理解證據", "口說、書寫與圖示都能成為課堂輸入。", "TRACE", "35%"],
            ["共同承擔發表", "小組分工降低單一學生的表演壓力。", "SHARE", "25%"],
        ],
        metrics=[
            ["4種", "參與入口", "想、寫、說、整合", "ENTRY"],
            ["60秒", "靜默整理", "教學流程的概念起點", "THINK"],
            ["3輪", "理解回看", "個人、同伴、全班", "REVIEW"],
            ["1張", "離場回覆", "每位學生保留一筆證據", "EXIT"],
        ],
        timeline=[
            ["01", "安靜想", "先整理而不是搶答。"],
            ["02", "寫下來", "留下自己的理解證據。"],
            ["03", "和一人說", "測試表達是否清楚。"],
            ["04", "小組整合", "保留差異與共同點。"],
            ["05", "共同發表", "把證據帶回全班。"],
        ],
        quote="勇敢的課堂不是每個人都立刻說話，\n而是每個人都有一條能走進討論的路。",
        attribution="BRAVE CLASSROOM LAB · 39",
        closing=["讓不同節奏都能被看見，\n參與才不只是一場搶答。", "下一堂課先加入一分鐘靜默整理，再比較誰因此更能進入討論。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-4-panel-grid", "cards-1-plus-4", "split-comparison",
            "kpi-scorecards", "before-after", "process-flow", "timeline-milestones", "quote-focus", "title-center",
        ],
        direction={
            "visual_genre": "learning-field-notebook",
            "narrative_metaphor": "把參與路徑畫成幾個清楚的學習入口，留白代表思考時間而不是待填區。",
            "signature_name": "participation-contour",
            "signature_concept": "柔和輪廓只包住真正的學習步驟，不畫蘋果、地球或課堂貼紙。",
            "variations": ["think-space", "note", "pair", "share"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "horizontal", "crop": "one-edge",
            "whitespace": "每個參與入口之間保留足夠安靜區，避免背景與文字混在一起。", "alignment": "left",
            "edge": "one-edge-crop", "type_role": "protagonist", "family": "single-family",
            "primary_job": "supportive", "accent_job": "classification", "accent_limit": "橙藍只標示不同參與入口。",
            "forbidden": ["school-doodles", "concentric-circles", "decorative-arcs", "cute-stickers", "equal-rounded-card-wall"],
            "anti_reference": "用蘋果、燈泡與地球貼圖營造教育感，卻讓文字與學習步驟互相干擾。",
        },
    ),
    _entry(
        preset_id="night-transit-wayfinding",
        base_theme="dark-circuit",
        story_id="last-mile-night-transfer",
        title="末班車之後，回家的路仍然需要清楚的下一站",
        subtitle="把夜間轉乘、候車安全、步行接續與求助入口整合成低干擾導引",
        speaker="NIGHT TRANSIT FIELD TEAM",
        org="SAFE ARRIVAL PROTOCOL · 2026",
        chapter_number="40",
        toc=[
            ["末班狀態", "先清楚顯示仍可使用與已停止的服務。"],
            ["候車位置", "讓照明、視線與上車點形成一致入口。"],
            ["轉乘距離", "標出步行時間與每個必要轉折。"],
            ["替代路徑", "服務中斷時提供可理解的下一個選擇。"],
            ["求助入口", "讓需要協助的人不用離開主要動線。"],
            ["抵達確認", "在最後一段仍保留回報與關閉機制。"],
        ],
        priorities=[
            ["狀態先行", "先告訴旅客什麼仍可用，再提供細節。", "STATUS", "42%"],
            ["轉折可見", "每個步行轉折都有下一站與距離。", "ROUTE", "34%"],
            ["求助不繞路", "協助入口直接位於主要回家動線。", "HELP", "24%"],
        ],
        metrics=[
            ["6站", "夜間節點", "情境設計的轉乘範圍", "STATION"],
            ["3態", "服務狀態", "可用、等待、停止", "STATUS"],
            ["12分", "步行接續", "pilot 的目標上限", "WALK"],
            ["2路", "替代選擇", "接駁與安全步行", "OPTION"],
        ],
        timeline=[
            ["23:30", "確認末班", "顯示最後可用班次與狀態。"],
            ["23:45", "進入候車", "對齊照明、視線與上車點。"],
            ["00:00", "啟用替代路徑", "服務停止時切換指引。"],
            ["00:15", "求助檢查", "確認協助入口仍可使用。"],
            ["00:30", "抵達回報", "收回最後一段路徑問題。"],
        ],
        quote="夜間導引不需要更亮，\n只需要讓下一個安全動作比黑暗更清楚。",
        attribution="NIGHT TRANSIT FIELD TEAM · 40",
        closing=["讓末班之後的每一步，\n仍有一個清楚的下一站。", "先測試一條轉乘路徑的狀態、距離與求助入口，再擴到整個夜間網。"],
        layouts=[
            "cover-center-title-edge-decor", "toc-4-panel-grid", "cards-1-plus-4", "process-flow",
            "before-after", "kpi-scorecards", "comparison-table", "timeline-milestones", "quote-focus", "title-center",
        ],
        direction={
            "visual_genre": "night-wayfinding-system",
            "narrative_metaphor": "把夜間轉乘視為低亮度的連續路徑，亮色只指向狀態、轉折與求助。",
            "signature_name": "safe-arrival-line",
            "signature_concept": "一條清楚路徑線依序連接站點，不生成羅盤、軌道圓環或斜線背景。",
            "variations": ["status", "transfer", "walk", "help-point"],
            "minimum_presence": "至少出現在 hero、relationship、evidence 與 pause-or-close。",
            "anchor": "left-axis", "axis": "route", "crop": "one-edge",
            "whitespace": "深色底面維持低細節，讓文字與路徑訊號保持明顯對比。", "alignment": "left",
            "edge": "continuation-across-slides", "type_role": "index", "family": "display-plus-text",
            "primary_job": "atmospheric", "accent_job": "status", "accent_limit": "亮色只標示仍可使用的下一步。",
            "forbidden": ["concentric-circles", "compass-symbols", "decorative-arcs", "glow-grid", "repeated-diagonal-route"],
            "anti_reference": "用霓虹軌道、羅盤與大圓環製造交通感，卻讓真正的轉乘文字失去對比。",
        },
    ),
]

for _item in _PRESET_DEFINITIONS:
    _item["layouts"] = [
        _formal_layout_id(layout_id, len(_item["toc"]))
        for layout_id in _item["layouts"]
    ]

_PRESET_BY_ID = {item["preset_id"]: item for item in _PRESET_DEFINITIONS}
if len(_PRESET_BY_ID) != len(_PRESET_DEFINITIONS):
    raise RuntimeError("Preset source definitions contain duplicate ids")
if set(_PRESET_BY_ID) != set(PRESET_COHORT):
    raise RuntimeError(
        "Preset source definitions must match the fixed 18-Preset cohort: "
        f"missing={sorted(set(PRESET_COHORT) - set(_PRESET_BY_ID))} "
        f"extra={sorted(set(_PRESET_BY_ID) - set(PRESET_COHORT))}"
    )
PRESETS: list[dict[str, Any]] = [_PRESET_BY_ID[preset_id] for preset_id in PRESET_COHORT]
for preset in PRESETS:
    expected_count = EXPECTED_SLIDE_COUNTS[preset["preset_id"]]
    if len(preset["layouts"]) != expected_count:
        raise RuntimeError(
            f"{preset['preset_id']}: expected {expected_count} layouts, "
            f"found {len(preset['layouts'])}"
        )


def _dashboard_insight_items(priorities: list[list[str]]) -> list[str]:
    """Return whole semantic labels that fit the compact dashboard panel."""

    insights: list[str] = []
    for title, _body, _tag, _allocation in priorities[:3]:
        phrase = str(title).strip()
        if not phrase:
            raise RuntimeError("Dashboard insight labels must not be empty")
        if len(phrase) > DASHBOARD_INSIGHT_MAX_CHARS:
            raise RuntimeError(
                "Dashboard insight exceeds the compact panel capacity; "
                f"rewrite the whole phrase instead of truncating it: {phrase!r}"
            )
        insights.append(phrase)
    if len(insights) != 3:
        raise RuntimeError("Dashboard overview requires exactly three short insights")
    return insights


def _layout_content(item: dict[str, Any]) -> dict[str, Any]:
    toc = item["toc"]
    priorities = item["priorities"]
    metrics = item["metrics"]
    timeline = item["timeline"]
    process_steps = [[f"{index:02d}", title, body] for index, (title, body) in enumerate(toc[:5], 1)]
    priority_rows = [
        [f"{index:02d}", title, body, tag, allocation]
        for index, (title, body, tag, allocation) in enumerate(priorities, 1)
    ]
    recommendations = [
        [f"{index:02d}", title, body, ("READ", "BUILD", "TEST", "SCALE")[index - 1]]
        for index, (title, body) in enumerate(toc[:4], 1)
    ]
    cards = [[title, body, tag] for title, body, tag, _ in priorities]
    dashboard_insights = _dashboard_insight_items(priorities)
    matrix = [
        ["保留觀察", toc[0][1]],
        ["立即推進", priorities[0][1]],
        ["補足證據", toc[1][1]],
        ["優先試驗", priorities[1][1]],
    ]
    kpis = [[label, value, delta] for value, label, _, delta in metrics]
    chart_values = [34 + index * 7 + int(item["chapter_number"]) % 5 for index in range(7)]
    return {
        "cover-center-title-edge-decor": {
            "title": item["title"], "subtitle": item["subtitle"],
            "speaker": item["speaker"], "org": item["org"],
        },
        "strategic-priorities": {
            "title": f"{item['title'].split('，')[0]}：三項推進優先",
            "subtitle": "先處理共同入口，再把證據、責任與回看節奏接起來。",
            "priorities": priority_rows,
            "impact": "資源先落在能改變整條路徑的共同節點，而不是只修飾單一末端。",
        },
        "recommendation-stack": {
            "title": f"{item['toc'][0][0]}到{item['toc'][3][0]}：四個可驗收動作",
            "subtitle": item["subtitle"],
            "recommendations": recommendations,
            "rationale": "每個動作都要留下下一個角色可直接使用的輸入，才算完成。",
        },
        "cards-1-plus-4": {
            "title": f"{item['title'].split('，')[0]}：四個內容入口",
            "subtitle": "每個入口只承擔一個工作，不把不同關係壓進同一張卡。",
            "items": [[title, body, f"{index:02d}"] for index, (title, body) in enumerate(toc[:4], 1)],
        },
        "toc-6-panel-rows": {
            "title": f"六個入口，讀懂{item['title'].split('，')[0]}",
            "short_title": f"六個入口，讀懂{item['title'].split('，')[0]}",
            "intro": item["subtitle"],
            "footer": "",
            "items": [
                [f"{index:02d}", title, ""]
                for index, (title, _body) in enumerate(toc, 1)
            ],
        },
        "before-after": {
            "before": ["目前 · 分散處理", toc[0][0], "資訊停留在各自節點，下一步必須靠記憶補上。", [body for _, body in toc[:3]]],
            "after": ["目標 · 共同路徑", priorities[0][0], "用共同輸入、責任與驗收條件推進。", [body for _, body, _, _ in priorities]],
            "bridge": "建立可回看的共同路徑",
        },
        "cycle-hub-6": {
            "title": "六步形成\n可回看的循環", "subtitle": "每一輪結果都改變下一輪輸入",
            "items": [[f"{index:02d}", title, body] for index, (title, body) in enumerate(toc, 1)],
        },
        "split-comparison": {
            "title": f"從{toc[0][0]}到{priorities[0][0]}：把分散狀態改成共同路徑",
            "left": [
                "目前 · 分散處理",
                toc[0][0],
                [body for _title, body in toc[:3]],
            ],
            "right": [
                "目標 · 共同路徑",
                priorities[0][0],
                [body for _title, body, _tag, _allocation in priorities],
            ],
        },
        "matrix-4quadrant": {
            "title": "用證據與影響，決定下一個動作",
            "axes": ["證據弱", "證據強", "影響低", "影響高"],
            "quadrants": matrix,
        },
        "comparison-table": {
            "title": "三種推進方式，哪一種能留下長期能力？",
            "subtitle": item["subtitle"],
            "columns": ["比較基準", "臨時處理", "單次專案", "共同路徑"],
            "rows": [[title, "低", "中", "高"] for title, _ in toc[:4]],
            "note": f"建議先從「{priorities[0][0]}」建立共同入口，再逐步擴張。",
        },
        "kpi-scorecards": {
            "title": f"{item['title'].split('，')[0]} · 四個驗收訊號",
            "subtitle": "數值是本次版型內容測試值；正式使用時需補上來源、期間與口徑。",
            "cards": metrics,
            "takeaway": "數字不是裝飾；每一個指標都要連到保留、調整或停止的決定。",
        },
        "stats-3-row": {
            "eyebrow": f"{item['title'].split('，')[0]}：試辦成績單",
            "stats": [[value, label, body] for value, label, body, _ in metrics[:3]],
            "footnote": "本頁為內容與版型測試；正式使用時需補入來源、期間與統計口徑。",
        },
        "dashboard-overview": {
            "title": f"{priorities[0][0]} · 本期運作概況",
            "subtitle": item["subtitle"],
            "kpis": kpis,
            "chart": {
                "title": f"{metrics[0][1]}連續七期變化",
                "metric": metrics[0][0],
                "bars": chart_values,
                "labels": [f"第 {index} 期" for index in range(1, 8)],
            },
            "insight": ["本期洞察", "三項優先已收斂", dashboard_insights],
            "footnote": "本頁為概念試算；正式報告需補上資料來源、計算口徑與責任人。",
        },
        "process-flow": {
            "title": f"五個關卡，把{item['toc'][0][0]}變成可追蹤決定",
            "subtitle": "每個節點只保留一個清楚輸出，缺證據時回到前一關。",
            "steps": process_steps,
            "note": "若關鍵證據缺失，流程應回到前一個節點，而不是用漂亮結論跳過驗證。",
        },
        "timeline-milestones": {
            "title": f"五個轉折，讓{item['toc'][0][0]}長成共同系統",
            "subtitle": "每個節點只保留一個可以被驗收的成果。",
            "milestones": [[label, title] for label, title, _ in timeline] + [["下一輪", "下一輪回看"]],
        },
        "highlight-callout": {
            "title": f"三個轉折，讓{item['title'].split('，')[0]}可以被回看",
            "chart": [metrics[0][1], chart_values[:6], [label for label, _, _ in timeline[:5]] + ["下一輪"]],
            "callouts": [[f"{index:02d}", title, body] for index, (title, body, _, _) in enumerate(priorities, 1)],
        },
        "quote-focus": {"quote": item["quote"], "attribution": f"— {item['attribution']}", "mark": "R"},
        "chapter-opener": {
            "label": f"第 {item['chapter_number']} 章", "title": item["toc"][3][0],
            "subtitle": item["toc"][3][1], "number": item["chapter_number"],
        },
        "title-center": {"headline": item["closing"][0], "support": item["closing"][1]},
    }


_LAYOUT_INTENTS = {
    "cover-center-title-edge-decor": "cover",
    "strategic-priorities": "prioritization",
    "recommendation-stack": "prioritization",
    "split-comparison": "comparison",
    "before-after": "comparison",
    "matrix-4quadrant": "distribution",
    "heat-map": "distribution",
    "cards-1-plus-4": "modules",
    "dashboard-overview": "evidence",
    "kpi-scorecards": "evidence",
    "stats-3-row": "evidence",
    "data-annotation": "evidence",
    "multi-line-chart": "evidence",
    "process-flow": "sequence",
    "timeline-milestones": "sequence",
    "timeline-vertical": "sequence",
    "quote-focus": "statement",
    "title-center": "statement",
}


@lru_cache(maxsize=1)
def _formal_source_routes() -> dict[str, set[str]]:
    method = load_html_design_method()
    layout_catalog = load_html_layout_catalog()
    eligible = set(eligible_html_layouts(layout_catalog, "pattern-only"))
    return {
        intent: {
            layout_id
            for layout_id in rule.get("candidates", [])
            if layout_id in eligible
        }
        for intent, rule in method["content_routing"].items()
    }


def _semantic_payload(item: dict[str, Any], intent: str, layout_id: str) -> dict[str, Any]:
    toc = item["toc"]
    priorities = item["priorities"]
    metrics = item["metrics"]
    timeline = item["timeline"]
    chart_values = [34 + index * 7 + int(item["chapter_number"]) % 5 for index in range(7)]

    if intent == "cover":
        return {
            "title": item["title"],
            "subtitle": item["subtitle"],
            "speaker": "",
            "org": "",
        }
    if intent == "navigation":
        return {
            "title": item["title"].split("嚗?")[0],
            "intro": item["subtitle"],
            "footer": "",
            "items": [
                [f"{index:02d}", title, body]
                for index, (title, body) in enumerate(toc, 1)
            ],
        }
    if intent == "prioritization":
        return {
            "title": item["title"],
            "subtitle": item["subtitle"],
            "items": [list(row) for row in priorities],
            "conclusion": priorities[0][1],
        }
    if intent == "comparison":
        before = ["BEFORE", toc[0][0], toc[0][1], [body for _, body in toc[:3]]]
        after = ["AFTER", priorities[0][0], priorities[0][1], [body for _, body, _, _ in priorities]]
        return {
            "claim": item["title"],
            "title": f"{before[1]} / {after[1]}",
            "subtitle": item["subtitle"],
            "before": before,
            "after": after,
            "left_labels": [title for title, _ in toc[:3]],
            "right_labels": [title for title, _, _, _ in priorities],
            "takeaway": item["closing"][1],
        }
    if intent == "distribution":
        matrix = [
            [toc[0][0], toc[0][1]],
            [priorities[0][0], priorities[0][1]],
            [toc[1][0], toc[1][1]],
            [priorities[1][0], priorities[1][1]],
        ]
        return {
            "title": item["title"],
            "matrix": matrix,
            "columns": [title for title, _ in toc[:4]],
            "rows": [row[0] for row in matrix],
            "values": [[1 + ((r * 2 + c) % 5) for c in range(4)] for r in range(4)],
            "value_note": "qualitative routing signal",
        }
    if intent == "modules":
        module_items = [list(row[:3]) for row in priorities]
        module_capacity = _module_layout_capacity(layout_id)
        if module_capacity is not None and len(module_items) < module_capacity:
            # Formal module Layouts must receive their exact authored capacity.
            # The extra module is derived from the story's next TOC entry; it is
            # not a renderer-side filler or a silent truncation.
            for title, body in toc:
                candidate = [title, body, "FIELD"]
                if candidate[:2] not in [row[:2] for row in module_items]:
                    module_items.append(candidate)
                if len(module_items) == module_capacity:
                    break
        if module_capacity is not None and len(module_items) != module_capacity:
            raise RuntimeError(
                f"{layout_id} requires {module_capacity} authored modules; "
                f"story only produced {len(module_items)}"
            )
        return {
            "title": item["title"],
            "subtitle": item["subtitle"],
            "items": module_items,
        }
    if intent == "evidence":
        chart = [
            [metrics[0][1], chart_values],
            [metrics[1][1], [value + 3 for value in chart_values]],
            [metrics[2][1], [value - 4 for value in chart_values]],
        ]
        return {
            "title": item["title"],
            "subtitle": item["org"],
            "metrics": [list(row) for row in metrics],
            "chart": chart,
            "labels": [f"R{index}" for index in range(1, 8)],
            "conclusion": metrics[0][2],
            "footnote": item["subtitle"],
        }
    if intent == "sequence":
        return {
            "title": item["title"],
            "subtitle": item["subtitle"],
            "process": [[title, body] for title, body in toc[:5]],
            "timeline": [list(row) for row in timeline],
            "conclusion": timeline[-1][2],
        }
    if intent == "statement":
        return {"quote": item["quote"], "attribution": item["attribution"]}
    if intent == "closing":
        return {"headline": item["closing"][0], "support": item["closing"][1]}
    raise RuntimeError(f"No semantic payload contract for intent={intent}, layout={layout_id}")


def _content_plan_and_compositions(
    item: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    routes = _formal_source_routes()
    content_plan: list[dict[str, Any]] = []
    page_compositions: dict[str, dict[str, Any]] = {}
    total_pages = EXPECTED_SLIDE_COUNTS[item["preset_id"]]
    if len(item["layouts"]) != total_pages:
        raise RuntimeError(f"{item['preset_id']}: source Layout count drifted")

    for page_index, layout_id in enumerate(item["layouts"], 1):
        intent = (
            "closing"
            if page_index == total_pages and layout_id == "title-center"
            else "navigation"
            if layout_id.startswith("toc-")
            else _LAYOUT_INTENTS.get(layout_id)
        )
        if intent is None:
            raise RuntimeError(f"No new-deck intent for Layout {layout_id}")
        if layout_id not in routes.get(intent, set()):
            raise RuntimeError(
                f"{item['preset_id']} page {page_index}: {layout_id} is not a formal candidate for {intent}"
            )
        if intent == "navigation":
            capacity = _toc_capacity(layout_id)
            if capacity is None or len(item["toc"]) > capacity:
                raise RuntimeError(
                    f"{item['preset_id']} page {page_index}: TOC exceeds {layout_id} capacity"
                )

        page_id = f"{item['story_id']}-page-{page_index:02d}"
        payload = _semantic_payload(item, intent, layout_id)
        source_fields = {
            "cover": ["title", "subtitle", "speaker", "org"],
            "navigation": ["toc"],
            "prioritization": ["priorities"],
            "comparison": ["toc", "priorities", "closing"],
            "distribution": ["toc", "priorities"],
            "modules": ["priorities"],
            "evidence": ["metrics", "timeline"],
            "sequence": ["toc", "timeline"],
            "statement": ["quote", "attribution"],
            "closing": ["closing"],
        }[intent]
        content_plan.append(
            {
                "page_index": page_index,
                "page_id": page_id,
                "intent": intent,
                "preferred_layout": layout_id,
                "content_key": intent,
                "source_fields": source_fields,
                "content_relation": {
                    "cover": "single-proposition-hero",
                    "navigation": "reading-path",
                    "prioritization": "ranked-decision",
                    "comparison": "state-change",
                    "distribution": "position-and-cluster",
                    "modules": "semantic-modules",
                    "evidence": "measurable-proof",
                    "sequence": "ordered-path",
                    "statement": "single-conclusion",
                    "closing": "next-action",
                }[intent],
                "content_item_count": len(payload.get("items", payload.get("metrics", payload.get("process", [])))) or None,
            }
        )
        page_compositions[page_id] = payload

    if len(content_plan) != total_pages or len(page_compositions) != total_pages:
        raise RuntimeError(f"{item['preset_id']}: formal source contract page count mismatch")
    return content_plan, page_compositions


def _repo_relative_posix(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise RuntimeError(
            f"Generated paths must stay inside the repository: {resolved}"
        ) from exc


def _canonical_visual_genre(value: str) -> str:
    return value if value in CANONICAL_VISUAL_GENRES else "custom"


def _canonical_primary_job(value: str) -> str:
    canonical = PRIMARY_JOB_ALIASES.get(value, value)
    return canonical if canonical in CANONICAL_PRIMARY_JOBS else "neutral-stage"


def _canonical_accent_job(value: str) -> str:
    canonical = ACCENT_JOB_ALIASES.get(value, value)
    return canonical if canonical in CANONICAL_ACCENT_JOBS else "classification"


def _canonical_forbidden_cliches(values: list[str]) -> list[str]:
    canonical: list[str] = []
    for value in values:
        mapped = FORBIDDEN_CLICHE_ALIASES.get(value, value)
        if mapped not in CANONICAL_FORBIDDEN_CLICHES:
            mapped = "custom"
        if mapped not in canonical:
            canonical.append(mapped)
    for required in REQUIRED_BACKGROUND_PROHIBITIONS:
        if required not in canonical:
            canonical.append(required)
    return canonical


def _art_direction(
    item: dict[str, Any], story_path: Path, batch_id: str
) -> dict[str, Any]:
    direction = item["direction"]
    focuses = [
        item["title"],
        "六個入口的閱讀路徑",
        item["priorities"][0][0],
        item["metrics"][0][1],
        item["priorities"][1][0],
        item["timeline"][1][1],
        item["priorities"][2][0],
        item["timeline"][-1][1],
        item["quote"].split("\n")[0],
        item["closing"][0].replace("\n", ""),
    ]
    variants = direction["variations"]
    layout_sequence = list(item["layouts"])
    if len(layout_sequence) < 5:
        raise RuntimeError(
            f"Full-deck Art Direction requires at least five scenes: {item['preset_id']}"
        )
    scenes = [
        {
            "slide_id": f"{index:02d}",
            "role": SCENE_ROLE_CYCLE[(index - 1) % len(SCENE_ROLE_CYCLE)],
            "visual_intensity": SCENE_INTENSITY_CYCLE[
                (index - 1) % len(SCENE_INTENSITY_CYCLE)
            ],
            "primary_focus": focuses[(index - 1) % len(focuses)],
            "signature_move_variant": variants[(index - 1) % len(variants)],
        }
        for index in range(1, len(layout_sequence) + 1)
    ]
    story_ref = _repo_relative_posix(story_path)
    renderer_handoff = {
        "image2": {"theme_candidates": [item["base_theme"]], "layout_sequence": list(layout_sequence)},
        "html": {"theme_candidates": [item["preset_id"]], "layout_sequence": list(layout_sequence)},
        "pptx": {"theme_candidates": [item["base_theme"]], "layout_sequence": list(layout_sequence)},
    }
    return {
        "schema_version": 1,
        "id": f"{batch_id}-{item['preset_id']}",
        "status": "ready-for-audition",
        "story_ref": story_ref,
        "brief": {
            "visual_genre": _canonical_visual_genre(direction["visual_genre"]),
            "narrative_metaphor": direction["narrative_metaphor"],
            "signature_move": {
                "name": direction["signature_name"],
                "concept_link": direction["signature_concept"],
                "allowed_variations": direction["variations"],
                "minimum_presence": direction["minimum_presence"],
            },
            "spatial_rule": {
                "primary_anchor": direction["anchor"],
                "reading_axis": direction["axis"],
                "crop_logic": direction["crop"],
                "whitespace_logic": direction["whitespace"],
                "content_alignment": direction["alignment"],
            },
            "edge_behavior": direction["edge"],
            "typography_role": {
                "primary_role": direction["type_role"],
                "hierarchy_method": ["size", "weight", "position", "spacing"],
                "family_policy": direction["family"],
                "maximum_families": 2 if direction["family"] == "serif-sans-pair" else 1,
                "ai_minimum_visual_text_px": 36,
            },
            "color_behavior": {
                "primary_job": _canonical_primary_job(direction["primary_job"]),
                "accent_job": _canonical_accent_job(direction["accent_job"]),
                "accent_area_limit": direction["accent_limit"],
            },
            "forbidden_cliches": _canonical_forbidden_cliches(direction["forbidden"]),
        },
        "reference_packet": {
            "official_cases": COMMON_OFFICIAL_CASES,
            "cross_domain_reference": COMMON_CROSS_DOMAIN_REFERENCE,
            "reusable_asset_sources": COMMON_ASSET_SOURCES,
            "anti_reference": {
                "description": direction["anti_reference"],
                "failure_risk": "視覺會保留氣氛，卻失去內容關係、責任與可編輯邊界。",
            },
            "translation_note": "只借用索引、證據與閱讀節奏的方法；不複製外部案例的色票、版面、作品或素材。",
        },
        "asset_family": {
            "primary_family": "project-native-css-geometry",
            "secondary_family": "typographic-index-marks",
            "allowed_roles": ["identity-motif", "utility-icon"],
            "maximum_families": 2,
            "provenance_required": True,
            "no_mixed_icon_families": True,
        },
        "scene_grammar": {"mode": "full-deck", "scenes": scenes},
        "renderer_handoff": renderer_handoff,
        "approval": {
            "machine": {"status": "pending", "checked_at": None},
            "human": {
                "status": "pending", "approved_by": None, "approved_at": None,
                "notes": "本檔為全新內容的三頁 pilot／整份 audition source；未經人工批准不得正式發布。",
            },
        },
        "perceptual_qa": {
            "required_checks": [
                "motivated-decoration", "asset-family-consistency", "semantic-card-boundary",
                "signature-move-presence", "scene-rhythm", "visual-intensity-curve",
            ],
            "notes": "先比較 cover、一般內容頁與資訊密集頁，再決定是否晉級 approved-for-renderer。",
            "final_decision": "human",
        },
    }


def _validate_batch_id(batch_id: str) -> str:
    value = batch_id.strip()
    if not value or value in {".", ".."} or Path(value).name != value:
        raise RuntimeError(f"Invalid batch id: {batch_id!r}")
    return value


def _validate_registry_capabilities(registry_path: Path) -> None:
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    entries = registry.get("entries") or []
    if not isinstance(entries, list):
        raise RuntimeError("Preset registry entries must be a list")

    rows_by_id: dict[str, list[dict[str, Any]]] = {}
    for row in entries:
        if not isinstance(row, dict):
            continue
        preset_id = str(row.get("id", "")).strip()
        if not preset_id:
            continue
        rows_by_id.setdefault(preset_id, []).append(row)

    duplicates = [
        preset_id
        for preset_id in PRESET_COHORT
        if len(rows_by_id.get(preset_id, [])) > 1
    ]
    missing = [preset_id for preset_id in PRESET_COHORT if preset_id not in rows_by_id]
    without_capability = [
        preset_id
        for preset_id in PRESET_COHORT
        if len(rows_by_id.get(preset_id, [])) == 1
        and "reusable-preset"
        not in set(rows_by_id[preset_id][0].get("capabilities") or [])
    ]
    if duplicates or missing or without_capability:
        raise RuntimeError(
            "The fixed Preset cohort is not renderer-ready in the registry: "
            f"duplicates={duplicates} missing={missing} "
            f"reusable-preset-required={without_capability}"
        )


def _write_new(path: Path, text: str) -> None:
    if path.exists():
        raise RuntimeError(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _assert_targets_absent(paths: list[Path]) -> None:
    existing = [_repo_relative_posix(path) for path in paths if path.exists()]
    if existing:
        raise RuntimeError(
            "Refusing to overwrite existing source or output files: "
            + ", ".join(existing)
        )


def generate_sources(
    output_root: Path,
    *,
    batch_id: str = DEFAULT_BATCH_ID,
    base_seed: int = DEFAULT_BASE_SEED,
    registry_path: Path = PRESET_REGISTRY,
) -> dict[str, Any]:
    batch_id = _validate_batch_id(batch_id)
    if base_seed < 1:
        raise RuntimeError("base seed must be a positive integer")
    root = output_root.resolve()
    _repo_relative_posix(root)
    _validate_registry_capabilities(registry_path.resolve())
    if len({item["story_id"] for item in PRESETS}) != len(PRESETS):
        raise RuntimeError("Fresh story ids must be unique")

    source_dir = root / "source"
    batch_plan_path = root / "batch-plan.json"
    readme_path = root / "README.md"
    records: list[dict[str, Any]] = []
    protected_targets = [batch_plan_path, readme_path]
    for index, source_item in enumerate(PRESETS):
        item = _visible_copy_safe_item(source_item)
        preset_id = item["preset_id"]
        story_path = source_dir / f"{preset_id}.story.json"
        direction_path = source_dir / f"{preset_id}.art-direction.yaml"
        output_html = root / preset_id / f"{preset_id}-fresh.html"
        protected_targets.extend((story_path, direction_path, output_html))
        records.append(
            {
                "item": item,
                "seed": base_seed + index,
                "story_path": story_path,
                "direction_path": direction_path,
                "output_html": output_html,
            }
        )
    _assert_targets_absent(protected_targets)

    plan: dict[str, Any] = {
        "schema_version": 1,
        "id": batch_id,
        "batch_plan_file": _repo_relative_posix(batch_plan_path),
        "output_root": _repo_relative_posix(root),
        "content_mode": "new-deck",
        "preset_demo": False,
        "preserved_old_versions": True,
        "renderer": "scripts/render_randomized_html_demo.py",
        "base_seed": base_seed,
        "preset_count": len(PRESET_COHORT),
        "slide_count": sum(EXPECTED_SLIDE_COUNTS.values()),
        "preset_cohort": list(PRESET_COHORT),
        "presets": [],
    }

    for record in records:
        item = record["item"]
        seed = record["seed"]
        story_path = record["story_path"]
        direction_path = record["direction_path"]
        output_html = record["output_html"]
        content_plan, page_compositions = _content_plan_and_compositions(item)
        story_payload = {
            "regeneration": {
                "batch_id": batch_id,
                "preset_id": item["preset_id"],
                "content_mode": "new-deck",
                "preset_demo": False,
                "fresh_content": True,
                "content_source_role": "batch-new-deck-content-manifest",
                "story_id": item["story_id"],
                "seed": seed,
                "note": "全新內容來源；不引用 Preset example story、example layouts 或 Style Case。",
            },
            "concept": {
                "story_id": item["story_id"],
                "visible_text_language": "zh-Hant",
                "allowed_latin_terms": [],
                "title": item["title"],
                "subtitle": item["subtitle"],
                "toc": item["toc"],
                "priorities": item["priorities"],
                "metrics": item["metrics"],
                "timeline": item["timeline"],
                "quote": item["quote"],
                "closing": item["closing"],
                "chapter_number": item["chapter_number"],
            },
            "toc_context": {
                "title": f"六個入口，讀懂{item['title'].split('，')[0]}",
                "short_title": item["title"].split("，")[0],
                "intro": item["subtitle"],
                "footer": "",
            },
            "content_plan": content_plan,
            "page_compositions": page_compositions,
            # Historical compatibility projection only; new-deck runtime reads
            # content_plan and page_compositions above.
            "layout_content": _layout_content(item),
        }
        _write_new(
            story_path,
            json.dumps(story_payload, ensure_ascii=False, indent=2) + "\n",
        )
        _write_new(
            direction_path,
            yaml.safe_dump(
                _art_direction(item, story_path, batch_id),
                allow_unicode=True,
                sort_keys=False,
            ),
        )
        plan["presets"].append(
            {
                "preset_id": item["preset_id"],
                "base_theme": item["base_theme"],
                "story_id": item["story_id"],
                "seed": seed,
                "story_ref": _repo_relative_posix(story_path),
                "story_file": _repo_relative_posix(story_path),
                "art_direction_file": _repo_relative_posix(direction_path),
                "layouts": item["layouts"],
                "output_html": _repo_relative_posix(output_html),
            }
        )

    _write_new(
        batch_plan_path,
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
    )
    _write_new(
        readme_path,
        f"# {batch_id}\n\n"
        "本目錄保存固定 18 個 HTML Preset 的全新內容 source、Art Direction audition "
        "與正式 renderer 預定輸出位置。\n\n"
        "- content mode：`new-deck`\n"
        "- `preset-demo`：未使用\n"
        f"- base seed：`{base_seed}`\n"
        "- 路徑格式：repository-relative POSIX\n"
        "- 舊版本：保留，不覆蓋\n"
        "- HTML renderer：`scripts/render_randomized_html_demo.py`\n"
        "- Art Direction：先標記 `ready-for-audition`，完成人工 pilot 審查後才能升級正式發布\n\n"
        "每份 deck 的 source manifest 與輸出 manifest 必須記錄故事、Preset、Layout sequence、"
        "editor source hash 與 QA 證據。\n",
    )
    return plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--batch-id", default=DEFAULT_BATCH_ID)
    parser.add_argument("--base-seed", type=int, default=DEFAULT_BASE_SEED)
    args = parser.parse_args()
    root = (
        args.output_root.resolve()
        if args.output_root is not None
        else (PROJECT_ROOT / "artifacts" / "experiments" / args.batch_id).resolve()
    )
    plan = generate_sources(
        root,
        batch_id=args.batch_id,
        base_seed=args.base_seed,
        registry_path=PRESET_REGISTRY,
    )
    print(
        json.dumps(
            {
                "root": plan["output_root"],
                "batch_plan": plan["batch_plan_file"],
                "preset_count": plan["preset_count"],
                "slide_count": plan["slide_count"],
                "pass": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
