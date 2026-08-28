#!/usr/bin/env python3
"""Static production-contract QA for one HTML layout family."""

from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from html_production_renderer import COVER_CONTENT, PRODUCTION_CSS, STATEMENT_CONTENT, density_profile


ROOT = Path(__file__).resolve().parents[1]
CORE_THEME_DIR = ROOT / "prompt_system" / "themes"
REPRESENTATIVE_THEMES = {
    "clinical-report",
    "dark-circuit",
    "brand-editorial",
    "product-strategy-signal",
}

FAMILY_LAYOUTS = {
    "diagram": {"cycle-hub-6", "funnel-4", "org-chart", "pyramid"},
    "comparison": {
        "before-after",
        "comparison-table",
        "matrix-4quadrant",
        "pricing-3col",
        "split-comparison",
        "swot-quadrant",
    },
    "metrics": {"dashboard-overview", "kpi-scorecards", "stats-3-row"},
    "closing": {"closing-photo-overlay-contact"},
    "statement": {"highlight-callout", "quote-attribution-3", "quote-focus", "title-center"},
    "chapter": {"chapter-fullbleed-overlay-title", "chapter-number-bg-left-title-rule", "chapter-opener", "chapter-text-left-photo-brand"},
    "content": {"recommendation-stack", "strategic-priorities"},
    "sequence": {"flow-stages-3", "gantt-roadmap", "process-flow", "timeline-milestones", "timeline-vertical"},
    "cover": {"cover-center-title-edge-decor", "cover-center-title-double-frame", "cover-left-title-open-field", "cover-photo-frame-reverse", "cover-photo-frame", "cover-photo-overlay-block", "hero-fullbleed-brand-footer", "hero-fullbleed"},
    "data-viz": {"data-annotation", "heat-map", "map-region", "map-spotlight", "multi-line-chart", "radar-chart"},
    "media": {"executive-bio", "photo-left-overlay-title-right", "testimonial-full"},
    "modules": {"cards-1-plus-2", "cards-1-plus-3", "cards-1-plus-4", "cards-1-plus-5", "cards-1-plus-6", "cards-1-plus-8", "icon-grid-6", "people-3", "team-grid"},
    "toc": {
        "toc-3-panel-left", "toc-3-panel-rows", "toc-3-vertical", "toc-3",
        "toc-4-image-left", "toc-4-panel-grid", "toc-4-panel-rows", "toc-4-vertical", "toc-4",
        "toc-5-number-panel-left", "toc-5-panel-grid", "toc-5-panel-rows", "toc-5-vertical", "toc-5",
        "toc-6-panel-rows", "toc-6-vertical", "toc-6", "toc-8",
    },
}


class EditLayerParser(HTMLParser):
    """Detect granular layers that are not owned by an editable root."""

    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[bool] = []
        self.orphan_layers = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if "data-edit-layer" in values and not any(self.stack):
            self.orphan_layers += 1
        if tag not in self.VOID_TAGS:
            self.stack.append("el" in classes)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if "data-edit-layer" in values and not any(self.stack):
            self.orphan_layers += 1

    def handle_endtag(self, tag: str) -> None:
        if self.stack:
            self.stack.pop()


def section_for(markup: str, layout_id: str) -> str | None:
    match = re.search(
        rf'<section\b[^>]*data-layout-id="{re.escape(layout_id)}"[^>]*>(.*?)</section>',
        markup,
        re.DOTALL,
    )
    return match.group(1) if match else None


def style_number(markup: str, prop: str) -> float | None:
    match = re.search(rf'(?:^|;)\s*{re.escape(prop)}:([0-9.]+)(?:px)?', markup)
    return float(match.group(1)) if match else None


def node_boxes(section: str, class_name: str) -> list[dict[str, float]]:
    boxes = []
    pattern = rf'<(?:div|svg)\b[^>]*class="[^"]*\b{re.escape(class_name)}\b[^"]*"[^>]*style="([^"]+)"'
    for style in re.findall(pattern, section):
        values = {key: style_number(style, key) for key in ("left", "top", "width", "height")}
        if all(value is not None for value in values.values()):
            boxes.append({key: float(value) for key, value in values.items()})
    return boxes


def class_style_number(section: str, class_name: str, prop: str) -> float | None:
    pattern = rf'<(?:div|svg)\b[^>]*class="[^"]*\b{re.escape(class_name)}\b[^"]*"[^>]*style="([^"]+)"'
    match = re.search(pattern, section)
    return style_number(match.group(1), prop) if match else None


def centered(box: dict[str, float], center_x: float = 864, tolerance: float = 1.1) -> bool:
    return abs(box["left"] + box["width"] / 2 - center_x) <= tolerance


def check_edit_contract(section: str) -> list[str]:
    issues = []
    tags = re.findall(r'<[a-z][^>]*class="[^"]*\bel\b[^"]*"[^>]*>', section)
    for tag in tags:
        if not any(attribute in tag for attribute in ("data-edit-composite=", "data-edit-kind=")):
            issues.append("editable-root-without-contract")
    if "data-edit-layer=" not in section and section.count("data-edit-kind=") < 2:
        issues.append("missing-granular-layers")
    parser = EditLayerParser()
    parser.feed(section)
    if parser.orphan_layers:
        issues.append(f"orphan-granular-layers:{parser.orphan_layers}")
    return issues


def check_frame(section: str) -> list[str]:
    issues = []
    frame_match = re.search(r'<div class="prod-frame[^"]*"([^>]*)>', section)
    if not frame_match:
        return ["missing-production-frame"]
    attrs = frame_match.group(1)
    ratio_match = re.search(r'data-fill-ratio="([0-9.]+)"', attrs)
    style_match = re.search(r'style="([^"]+)"', attrs)
    if not ratio_match or not style_match:
        return ["missing-soft-fill-contract"]
    ratio = float(ratio_match.group(1))
    style = style_match.group(1)
    top = style_number(style, "top")
    height = style_number(style, "height")
    if ratio not in {0.84, 0.90, 0.96}:
        issues.append("invalid-fill-ratio")
    if top is None or height is None:
        issues.append("missing-frame-geometry")
    else:
        if abs(height / 888 - ratio) > 0.01:
            issues.append("fill-ratio-mismatch")
        if abs(top - (888 - height) / 2) > 1:
            issues.append("frame-not-vertically-centered")
    return issues


def check_diagram(layout_id: str, section: str) -> list[str]:
    issues = check_edit_contract(section) + check_frame(section)
    if not has_content_wrapper(section):
        # The section capture starts after the section tag and includes content.
        issues.append("missing-content-wrapper")
    if layout_id == "cycle-hub-6":
        if section.count('data-edit-composite="cycle-node-') != 6:
            issues.append("cycle-node-count")
        if section.count('marker-end="url(#production-cycle-arrow)"') != 6:
            issues.append("cycle-arrow-count")
        if not re.search(r'<circle\b[^>]*r="260"', section):
            issues.append("cycle-ring-not-circle")
        boxes = node_boxes(section, "cycle-node")
        if len(boxes) != 6 or any(abs(box["width"] - box["height"]) > 0.1 for box in boxes):
            issues.append("cycle-nodes-not-circular")
    elif layout_id == "funnel-4":
        boxes = node_boxes(section, "funnel-stage")
        if len(boxes) != 4:
            issues.append("funnel-stage-count")
        else:
            widths = [box["width"] for box in boxes]
            if not all(first > second for first, second in zip(widths, widths[1:])):
                issues.append("funnel-widths-not-descending")
            if not all(centered(box) for box in boxes):
                issues.append("funnel-centerline-drift")
        if section.count("funnel-bg") != 4:
            issues.append("funnel-shape-count")
    elif layout_id == "org-chart":
        if section.count('data-edit-composite="org-root"') != 1:
            issues.append("org-root-count")
        if section.count('data-edit-composite="org-child-') != 3:
            issues.append("org-child-count")
        if section.count('<path d="M 864') != 3:
            issues.append("org-connector-count")
        boxes = node_boxes(section, "org-child")
        if len(boxes) != 3 or max(box["top"] for box in boxes) - min(box["top"] for box in boxes) > 0.1:
            issues.append("org-children-not-aligned")
    elif layout_id == "pyramid":
        boxes = node_boxes(section, "pyramid-layer")
        if len(boxes) != 5:
            issues.append("pyramid-layer-count")
        else:
            widths = [box["width"] for box in boxes]
            if not all(first < second for first, second in zip(widths, widths[1:])):
                issues.append("pyramid-widths-not-ascending")
            if not all(centered(box) for box in boxes):
                issues.append("pyramid-centerline-drift")
        if section.count("pyramid-bg") != 5:
            issues.append("pyramid-shape-count")
    else:
        issues.append("unknown-diagram-layout")
    return issues


def same_size(boxes: list[dict[str, float]], tolerance: float = 0.1) -> bool:
    if not boxes:
        return False
    first = boxes[0]
    return all(
        abs(box["width"] - first["width"]) <= tolerance
        and abs(box["height"] - first["height"]) <= tolerance
        for box in boxes[1:]
    )


def check_comparison(layout_id: str, section: str) -> list[str]:
    issues = check_edit_contract(section) + check_frame(section)
    if not has_content_wrapper(section):
        issues.append("missing-content-wrapper")
    if layout_id == "before-after":
        panels = node_boxes(section, "compare-panel")
        if len(panels) != 2:
            issues.append("before-after-panel-count")
        elif not same_size(panels) or abs(panels[0]["top"] - panels[1]["top"]) > 0.1:
            issues.append("before-after-panels-unbalanced")
        if section.count('data-edit-composite="before-after-rail"') != 1:
            issues.append("before-after-rail-count")
        if "BEFORE" not in section or "AFTER" not in section:
            issues.append("before-after-temporal-labels")
    elif layout_id == "comparison-table":
        if section.count('class="compare-table-cell') != 20:
            issues.append("comparison-table-cell-count")
        if section.count("compare-table-cell header") != 4:
            issues.append("comparison-table-header-count")
        if section.count("recommended") != 5:
            issues.append("comparison-table-recommended-column")
        boxes = node_boxes(section, "compare-table")
        if len(boxes) != 1 or abs(boxes[0]["width"] - 1728) > 0.1:
            issues.append("comparison-table-width")
    elif layout_id == "matrix-4quadrant":
        cards = node_boxes(section, "matrix-card")
        if len(cards) != 4:
            issues.append("matrix-card-count")
        else:
            xs = sorted({round(box["left"], 1) for box in cards})
            ys = sorted({round(box["top"], 1) for box in cards})
            if len(xs) != 2 or len(ys) != 2 or not same_size(cards):
                issues.append("matrix-not-balanced-2x2")
        if section.count('marker-start="url(#matrix-arrow)"') != 2 or section.count('marker-end="url(#matrix-arrow)"') != 2:
            issues.append("matrix-axis-count")
        if section.count('class="el matrix-axis') != 4:
            issues.append("matrix-axis-label-count")
    elif layout_id == "pricing-3col":
        cards = node_boxes(section, "price-card")
        if len(cards) != 3:
            issues.append("pricing-card-count")
        elif not same_size(cards) or max(box["top"] for box in cards) - min(box["top"] for box in cards) > 0.1:
            issues.append("pricing-cards-unbalanced")
        if section.count('class="price-cta"') != 3:
            issues.append("pricing-cta-count")
        if section.count("price-card tier-2") != 1:
            issues.append("pricing-recommended-tier")
    elif layout_id == "split-comparison":
        panels = node_boxes(section, "split-panel")
        if len(panels) != 2:
            issues.append("split-panel-count")
        elif not same_size(panels) or abs(panels[0]["top"] - panels[1]["top"]) > 0.1:
            issues.append("split-panels-unbalanced")
        if section.count('class="el split-divider"') != 1:
            issues.append("split-divider-count")
    elif layout_id == "swot-quadrant":
        cards = node_boxes(section, "swot-card")
        if len(cards) != 4:
            issues.append("swot-card-count")
        else:
            xs = sorted({round(box["left"], 1) for box in cards})
            ys = sorted({round(box["top"], 1) for box in cards})
            if len(xs) != 2 or len(ys) != 2 or not same_size(cards):
                issues.append("swot-not-balanced-2x2")
        letters = re.findall(r'class="swot-letter"[^>]*>([SWOT])</span>', section)
        if letters != ["S", "W", "O", "T"]:
            issues.append("swot-semantic-labels")
    else:
        issues.append("unknown-comparison-layout")
    return issues


def css_font_size(class_name: str) -> float | None:
    match = re.search(rf'\.{re.escape(class_name)}\{{[^}}]*font:[^;]*?([0-9.]+)px/', PRODUCTION_CSS)
    if not match:
        match = re.search(rf'\.{re.escape(class_name)}\{{[^}}]*font-size:([0-9.]+)px', PRODUCTION_CSS)
    return float(match.group(1)) if match else None


def has_python_chart(section: str, family: str) -> bool:
    return (
        'data-chart-renderer="python-matplotlib-svg"' in section
        and 'data-python-chart-engine="matplotlib"' in section
        and f'data-python-chart-family="{family}"' in section
        and re.search(r'data-chart-spec-sha256="[0-9a-f]{64}"', section) is not None
        and '<image ' not in section
        and 'data:image' not in section
    )


def has_content_wrapper(section: str) -> bool:
    return re.search(r'<div class="content"(?:\s|>)', section) is not None


def check_metrics(layout_id: str, section: str) -> list[str]:
    issues = check_edit_contract(section) + check_frame(section)
    if not has_content_wrapper(section):
        issues.append("missing-content-wrapper")
    if layout_id == "dashboard-overview":
        if section.count('class="metric-strip-item') != 4:
            issues.append("dashboard-kpi-count")
        chart_boxes = node_boxes(section, "metric-chart-panel")
        insight_boxes = node_boxes(section, "metric-insight")
        if len(chart_boxes) != 1 or len(insight_boxes) != 1:
            issues.append("dashboard-module-count")
        else:
            chart, insight = chart_boxes[0], insight_boxes[0]
            if abs(chart["top"] - insight["top"]) > 0.1 or abs(chart["height"] - insight["height"]) > 0.1:
                issues.append("dashboard-modules-not-aligned")
            if abs(chart["left"] + chart["width"] + 40 - insight["left"]) > 0.1:
                issues.append("dashboard-module-gap")
            if abs(insight["left"] + insight["width"] - 1728) > 0.1:
                issues.append("dashboard-right-edge")
        if not has_python_chart(section, "dashboard-combo"):
            issues.append("dashboard-chart-semantics")
        if len(re.findall(r'id="python-bar-[1-6]"', section)) != 6:
            issues.append("dashboard-chart-bar-count")
        if len(re.findall(r'class="[^"]*\bmetric-footnote\b[^"]*"', section)) != 1:
            issues.append("dashboard-footnote")
        value_size = css_font_size("metric-strip-value")
        title_size = css_font_size("prod-title")
        if value_size is None or title_size is None or value_size < title_size:
            issues.append("dashboard-number-not-dominant")
    elif layout_id == "kpi-scorecards":
        cards = node_boxes(section, "metric-kpi-card")
        if len(cards) != 4:
            issues.append("kpi-card-count")
        elif not same_size(cards) or max(box["top"] for box in cards) - min(box["top"] for box in cards) > 0.1:
            issues.append("kpi-cards-unbalanced")
        if section.count('class="metric-card-value"') != 4:
            issues.append("kpi-value-count")
        if section.count('data-edit-composite="metric-takeaway"') != 1:
            issues.append("kpi-takeaway-count")
        value_size = css_font_size("metric-card-value")
        label_size = css_font_size("metric-card-label")
        if value_size is None or label_size is None or value_size < label_size:
            issues.append("kpi-number-not-dominant")
    elif layout_id == "stats-3-row":
        cards = node_boxes(section, "metric-stat-card")
        if len(cards) != 3:
            issues.append("stats-card-count")
        elif not same_size(cards) or max(box["top"] for box in cards) - min(box["top"] for box in cards) > 0.1:
            issues.append("stats-cards-unbalanced")
        if 'class="el prod-title"' in section:
            issues.append("stats-unexpected-framing-title")
        if section.count('class="metric-stat-value"') != 3:
            issues.append("stats-value-count")
        if section.count('class="el metric-eyebrow"') != 1 or section.count('class="el metric-footnote"') != 1:
            issues.append("stats-context-lines")
        value_size = css_font_size("metric-stat-value")
        label_size = css_font_size("metric-stat-label")
        if value_size is None or label_size is None or value_size < label_size:
            issues.append("stats-number-not-dominant")
    else:
        issues.append("unknown-metrics-layout")
    return issues


def check_closing(layout_id: str, section: str) -> list[str]:
    issues = check_edit_contract(section)
    if not has_content_wrapper(section):
        issues.append("missing-content-wrapper")
    if layout_id != "closing-photo-overlay-contact":
        return issues + ["unknown-closing-layout"]
    frame = re.search(r'<div class="prod-frame closing-frame"([^>]*)>', section)
    if not frame or 'data-full-bleed-media="true"' not in frame.group(1):
        issues.append("closing-fullbleed-contract")
    photo_boxes = node_boxes(section, "closing-photo-field")
    if len(photo_boxes) != 1:
        issues.append("closing-photo-layer-count")
    else:
        photo = photo_boxes[0]
        if any(abs(photo[key] - expected) > 0.1 for key, expected in {"left": 0, "top": 0, "width": 1920, "height": 1080}.items()):
            issues.append("closing-photo-not-fullbleed")
    copy_boxes = node_boxes(section, "closing-copy-panel")
    social_boxes = node_boxes(section, "closing-social-panel")
    if len(copy_boxes) != 1 or len(social_boxes) != 1:
        issues.append("closing-overlay-module-count")
    else:
        copy, social = copy_boxes[0], social_boxes[0]
        if abs(copy["top"] - social["top"]) > 0.1 or abs(copy["height"] - social["height"]) > 0.1:
            issues.append("closing-overlays-not-aligned")
        if abs(copy["left"] + copy["width"] - social["left"]) > 0.1:
            issues.append("closing-overlays-not-adjacent")
        if social["left"] + social["width"] > 1920 * 0.64:
            issues.append("closing-photo-open-area-too-small")
        if copy["left"] < 1920 * 0.08:
            issues.append("closing-copy-outside-safe-area")
    if section.count('class="closing-social-row') != 3:
        issues.append("closing-social-count")
    if section.count("<li>") != 3:
        issues.append("closing-contact-count")
    if section.count('class="closing-title"') != 1:
        issues.append("closing-title-count")
    return issues


def check_statement(layout_id: str, section: str) -> list[str]:
    issues = check_edit_contract(section) + check_frame(section)
    if not has_content_wrapper(section):
        issues.append("missing-content-wrapper")
    if layout_id == "highlight-callout":
        chart_boxes = node_boxes(section, "statement-chart-panel")
        callouts = node_boxes(section, "statement-callout")
        if len(chart_boxes) != 1 or len(callouts) != 3:
            issues.append("highlight-module-count")
        else:
            if not same_size(callouts) or len({round(box["left"], 1) for box in callouts}) != 1:
                issues.append("highlight-callouts-unbalanced")
            if chart_boxes[0]["left"] + chart_boxes[0]["width"] + 40 != callouts[0]["left"]:
                issues.append("highlight-column-gap")
        if not has_python_chart(section, "highlight-line"):
            issues.append("highlight-chart-annotation-count")
        if len(re.findall(r'id="python-focus-[1-3]"', section)) != 3:
            issues.append("highlight-chart-focus-count")
    elif layout_id == "quote-attribution-3":
        cards = node_boxes(section, "statement-quote-card")
        if len(cards) != 3:
            issues.append("quote-card-count")
        elif not same_size(cards) or max(box["top"] for box in cards) - min(box["top"] for box in cards) > 0.1:
            issues.append("quote-cards-unbalanced")
        if section.count("<blockquote ") != 3 or section.count('class="statement-quote-mark"') != 3:
            issues.append("quote-card-semantic-content")
    elif layout_id == "quote-focus":
        if 'class="el prod-title"' in section:
            issues.append("quote-focus-unexpected-title")
        if section.count('class="el statement-focus-quote"') != 1 or section.count('class="el statement-focus-attribution"') != 1:
            issues.append("quote-focus-copy-count")
        rails = node_boxes(section, "statement-focus-rail")
        quote_left = class_style_number(section, "statement-focus-quote", "left")
        attribution_left = class_style_number(section, "statement-focus-attribution", "left")
        if len(rails) != 1 or quote_left is None or rails[0]["left"] + rails[0]["width"] >= quote_left:
            issues.append("quote-focus-left-rail")
        if quote_left is None or attribution_left is None or abs(quote_left - attribution_left) > 0.1:
            issues.append("quote-focus-copy-left-alignment")
        if "statement-focus-mark" in section:
            issues.append("quote-focus-legacy-mark")
        quote_size = css_font_size("statement-focus-quote")
        attribution_size = css_font_size("statement-focus-attribution")
        if quote_size is None or attribution_size is None or quote_size <= attribution_size * 2:
            issues.append("quote-focus-typographic-dominance")
    elif layout_id == "title-center":
        areas = node_boxes(section, "statement-center-area")
        if len(areas) != 1 or not centered(areas[0]):
            issues.append("title-center-area-center")
        if 'data-auto-layout="vertical-stack"' not in section:
            issues.append("title-center-auto-layout")
        if section.count('class="el statement-center-headline"') != 1 or section.count('class="el statement-center-support"') != 1:
            issues.append("title-center-copy-count")
        if section.count('class="el statement-center-rule"') != 1:
            issues.append("title-center-rule-count")
        headline_match = re.search(
            r'class="el statement-center-headline"[^>]*>(.*?)</div>',
            section,
            re.DOTALL,
        )
        headline_markup = headline_match.group(1) if headline_match else ""
        if any(punctuation in headline_markup for punctuation in "，；：") and not re.search(
            r"[，；：]\s*<br\b",
            headline_markup,
        ):
            issues.append("title-center-punctuation-break")
        content = STATEMENT_CONTENT[layout_id]
        if len(content["headline"]) > len(content["support"]):
            issues.append("title-center-headline-too-long")
        headline_size = css_font_size("statement-center-headline")
        support_size = css_font_size("statement-center-support")
        if headline_size is None or support_size is None or headline_size <= support_size * 2:
            issues.append("title-center-typographic-dominance")
    else:
        issues.append("unknown-statement-layout")
    return issues


def check_chapter(layout_id: str, section: str) -> list[str]:
    issues = check_edit_contract(section)
    if not has_content_wrapper(section):
        issues.append("missing-content-wrapper")
    if layout_id in {"chapter-number-bg-left-title-rule", "chapter-opener"}:
        issues.extend(check_frame(section))
    if layout_id == "chapter-fullbleed-overlay-title":
        if 'data-full-bleed-media="true"' not in section:
            issues.append("chapter-fullbleed-contract")
        photos = node_boxes(section, "chapter-media-full")
        overlays = node_boxes(section, "chapter-overlay-title")
        panels = node_boxes(section, "chapter-number-panel")
        if len(photos) != 1 or photos[0]["width"] != 1920 or photos[0]["height"] != 1080:
            issues.append("chapter-fullbleed-photo")
        if len(overlays) != 1 or overlays[0]["left"] > 1920 * 0.08 or overlays[0]["width"] > 1920 * 0.34:
            issues.append("chapter-overlay-title-geometry")
        if len(panels) != 1 or panels[0]["height"] != 1080 or panels[0]["left"] + panels[0]["width"] != 1920:
            issues.append("chapter-number-panel-geometry")
    elif layout_id == "chapter-number-bg-left-title-rule":
        if section.count('class="el chapter-number-ghost"') != 1:
            issues.append("chapter-background-number-count")
        if section.count('class="el chapter-left-title"') != 1 or section.count('class="el chapter-left-subtitle"') != 1:
            issues.append("chapter-left-copy-count")
        if section.count('class="el chapter-title-rule"') != 1 or section.count('class="el chapter-side-decor"') != 1:
            issues.append("chapter-structural-decor-count")
    elif layout_id == "chapter-opener":
        if section.count('class="el chapter-opener-title"') != 1 or section.count('class="el chapter-opener-ghost"') != 1:
            issues.append("chapter-opener-copy-count")
        ghost_left = re.search(r'class="el chapter-opener-ghost"[^>]*style="[^"]*left:([0-9.]+)px', section)
        if not ghost_left or float(ghost_left.group(1)) < 1200:
            issues.append("chapter-opener-right-balance")
        if section.count('class="el chapter-dot-field"') != 1:
            issues.append("chapter-opener-theme-zone")
    elif layout_id == "chapter-text-left-photo-brand":
        if 'data-full-height-media="true"' not in section:
            issues.append("chapter-split-media-contract")
        photos = node_boxes(section, "chapter-media-right")
        overlays = node_boxes(section, "chapter-brand-overlay")
        if len(photos) != 1 or photos[0]["left"] != 864 or photos[0]["width"] != 1056 or photos[0]["height"] != 1080:
            issues.append("chapter-right-photo-geometry")
        if len(overlays) != 1:
            issues.append("chapter-brand-overlay-count")
        else:
            overlay = overlays[0]
            if overlay["left"] < 864 or overlay["left"] + overlay["width"] > 1920:
                issues.append("chapter-brand-overlay-placement")
        if section.count('class="el chapter-split-title"') != 1 or section.count('class="el chapter-split-body"') != 1:
            issues.append("chapter-split-copy-count")
    else:
        issues.append("unknown-chapter-layout")
    return issues


def check_content(layout_id: str, section: str) -> list[str]:
    issues = check_edit_contract(section) + check_frame(section)
    if not has_content_wrapper(section):
        issues.append("missing-content-wrapper")
    if layout_id == "recommendation-stack":
        stacks = node_boxes(section, "content-rec-stack")
        if len(stacks) != 1 or stacks[0]["width"] != 1728:
            issues.append("recommendation-stack-geometry")
        row_tags = re.findall(r'<div class="content-rec-row\b[^>]*>', section)
        row_count = len(row_tags)
        if not 2 <= row_count <= 5:
            issues.append("recommendation-row-count")
        numbers = re.findall(r'class="content-rec-row[^>]*>\s*<span[^>]*>(\d{2})</span>', section)
        if numbers != [f"{index:02d}" for index in range(1, row_count + 1)]:
            issues.append("recommendation-order")
        row_boxes = []
        for tag in row_tags:
            style_match = re.search(r'\bstyle="([^"]+)"', tag)
            if not style_match:
                continue
            style = style_match.group(1)
            top = style_number(style, "top")
            height = style_number(style, "height")
            if top is not None and height is not None:
                row_boxes.append((top, height))
        if len(row_boxes) != row_count or not stacks:
            issues.append("recommendation-row-geometry")
        elif (
            any(abs(height - row_boxes[0][1]) > 0.1 for _, height in row_boxes[1:])
            or abs(row_boxes[0][0]) > 0.1
            or any(abs(row_boxes[index][0] - index * row_boxes[0][1]) > 0.2 for index in range(row_count))
            or abs(sum(height for _, height in row_boxes) - stacks[0]["height"]) > 0.2
        ):
            issues.append("recommendation-row-geometry")
        if section.count('data-edit-composite="recommendation-rationale"') != 1:
            issues.append("recommendation-rationale-count")
    elif layout_id == "strategic-priorities":
        cards = node_boxes(section, "content-priority-card")
        if len(cards) != 3:
            issues.append("priority-card-count")
        else:
            if not same_size(cards) or max(box["top"] for box in cards) - min(box["top"] for box in cards) > 0.1:
                issues.append("priority-cards-not-equal-size")
            gaps = [
                cards[index + 1]["left"] - (cards[index]["left"] + cards[index]["width"])
                for index in range(len(cards) - 1)
            ]
            if any(abs(gap - 40) > 0.1 for gap in gaps):
                issues.append("priority-card-gaps")
            if abs(cards[-1]["left"] + cards[-1]["width"] - 1728) > 0.1:
                issues.append("priority-right-edge")
        if section.count("--allocation:") != 3:
            issues.append("priority-allocation-bars")
        number_size = css_font_size("content-priority-number")
        title_size = css_font_size("content-priority-card>b")
        if number_size is None or title_size is None or number_size < title_size:
            issues.append("priority-number-not-dominant")
        if section.count('data-edit-composite="strategic-impact-note"') != 1:
            issues.append("priority-impact-note-count")
    else:
        issues.append("unknown-content-layout")
    return issues


def check_sequence(layout_id: str, section: str) -> list[str]:
    issues = check_edit_contract(section) + check_frame(section)
    if not has_content_wrapper(section):
        issues.append("missing-content-wrapper")
    if layout_id == "flow-stages-3":
        cards = node_boxes(section, "sequence-stage-card")
        if len(cards) != 3:
            issues.append("stage-card-count")
        elif not same_size(cards) or max(box["top"] for box in cards) - min(box["top"] for box in cards) > 0.1:
            issues.append("stage-cards-unbalanced")
        if section.count('marker-end="url(#stage-arrow)"') != 2:
            issues.append("stage-arrow-count")
        if section.count('data-edit-composite="flow-takeaway"') != 1:
            issues.append("stage-takeaway-count")
    elif layout_id == "gantt-roadmap":
        gantt = node_boxes(section, "sequence-gantt")
        if len(gantt) != 1 or gantt[0]["width"] != 1728:
            issues.append("gantt-area-geometry")
        if section.count('class="gantt-bar') != 5:
            issues.append("gantt-bar-count")
        if section.count('data-edit-layer="text" style="left:') < 6:
            issues.append("gantt-period-header-count")
        if section.count("<b data-edit-layer=\"text\" style=\"top:") != 5:
            issues.append("gantt-task-count")
        starts = [float(value) for value in re.findall(r'class="gantt-bar[^"]*"[^>]*style="left:([0-9.]+)px', section)]
        if len(starts) != 5 or starts != sorted(starts):
            issues.append("gantt-sequence-order")
    elif layout_id == "process-flow":
        nodes = node_boxes(section, "sequence-process-node")
        if len(nodes) != 5:
            issues.append("process-node-count")
        elif not same_size(nodes) or max(box["top"] for box in nodes) - min(box["top"] for box in nodes) > 0.1:
            issues.append("process-nodes-unbalanced")
        if section.count('marker-end="url(#process-arrow)"') != 4:
            issues.append("process-arrow-count")
        if section.count('data-edit-composite="process-note"') != 1:
            issues.append("process-note-count")
    elif layout_id == "timeline-milestones":
        if section.count('class="timeline-milestone') != 6:
            issues.append("milestone-count")
        if section.count('class="timeline-axis"') != 1:
            issues.append("milestone-axis-count")
        tops = [float(value) for value in re.findall(r'class="timeline-milestone[^>]*style="[^"]*top:([0-9.]+)px', section)]
        if len(tops) != 6 or sorted(set(tops)) != [70.0, 350.0]:
            issues.append("milestone-alternating-notes")
    elif layout_id == "timeline-vertical":
        event_count = section.count('class="timeline-vertical-event')
        if not 4 <= event_count <= 5:
            issues.append("vertical-event-count")
        if section.count('class="timeline-vertical-line"') != 1:
            issues.append("vertical-axis-count")
        tops = [float(value) for value in re.findall(r'class="timeline-vertical-event[^>]*style="top:([0-9.]+)px', section)]
        expected_step = 640 / event_count if event_count else 0
        if len(tops) != event_count or any(abs(second - first - expected_step) > 0.1 for first, second in zip(tops, tops[1:])):
            issues.append("vertical-event-spacing")
    else:
        issues.append("unknown-sequence-layout")
    return issues


def check_cover(layout_id: str, section: str) -> list[str]:
    issues = check_edit_contract(section)
    if not has_content_wrapper(section):
        issues.append("missing-content-wrapper")
    content = COVER_CONTENT[layout_id]
    if "subtitle" in content and len(content["title"]) > len(content["subtitle"]):
        issues.append("cover-title-copy-too-long")
    if layout_id == "cover-center-title-edge-decor":
        issues.extend(check_frame(section))
        areas = node_boxes(section, "cover-center-area")
        if len(areas) != 1 or not centered(areas[0]):
            issues.append("cover-center-area-center")
        if 'data-auto-layout="vertical-stack"' not in section:
            issues.append("cover-center-auto-layout")
        if section.count('class="el cover-edge-decor') != 4:
            issues.append("cover-edge-decor-count")
        if section.count('data-edit-composite="cover-logo"') != 1:
            issues.append("cover-logo-count")
        title_size = css_font_size("cover-center-title")
        subtitle_size = css_font_size("cover-center-subtitle")
        if title_size is None or subtitle_size is None or title_size <= subtitle_size * 2:
            issues.append("cover-center-title-dominance")
    elif layout_id == "cover-center-title-double-frame":
        issues.extend(check_frame(section))
        if section.count('class="cover-frame-title-stack title-flow-stack"') != 1:
            issues.append("cover-double-frame-stack-count")
        for class_name in ("cover-frame-title", "cover-frame-rule", "cover-frame-subtitle"):
            if section.count(f'class="el {class_name}"') != 1:
                issues.append(f"cover-double-frame-{class_name.removeprefix('cover-frame-')}-count")
        for class_name in ("cover-frame-speaker", "cover-frame-org"):
            count = section.count(f'class="el {class_name}"')
            if count > 1:
                issues.append(f"cover-double-frame-{class_name.removeprefix('cover-frame-')}-count")
        if 'data-visual-balance="center-title-double-frame"' not in section:
            issues.append("cover-double-frame-visual-balance")
        title_size = css_font_size("cover-frame-title")
        subtitle_size = css_font_size("cover-frame-subtitle")
        if title_size is None or subtitle_size is None or title_size <= subtitle_size * 2:
            issues.append("cover-double-frame-title-dominance")
    elif layout_id == "cover-left-title-open-field":
        issues.extend(check_frame(section))
        if section.count('class="cover-left-title-stack title-flow-stack"') != 1:
            issues.append("cover-left-stack-count")
        for class_name in ("cover-left-title", "cover-left-rule", "cover-left-subtitle", "cover-left-speaker"):
            if section.count(f'class="el {class_name}"') != 1:
                issues.append(f"cover-left-{class_name.removeprefix('cover-left-')}-count")
        if "cover-center-org" in section or "writing-mode" in section:
            issues.append("cover-left-vertical-metadata-present")
        title_size = css_font_size("cover-left-title")
        subtitle_size = css_font_size("cover-left-subtitle")
        if title_size is None or subtitle_size is None or title_size <= subtitle_size * 2:
            issues.append("cover-left-title-dominance")
    elif layout_id in {"cover-photo-frame", "cover-photo-frame-reverse"}:
        if 'data-full-height-media="true"' not in section:
            issues.append("cover-split-media-contract")
        photos = node_boxes(section, "cover-media-field")
        if len(photos) != 1 or photos[0]["width"] != 768 or photos[0]["height"] != 1080:
            issues.append("cover-split-photo-geometry")
        else:
            expected_left = 0 if layout_id == "cover-photo-frame" else 1152
            if photos[0]["left"] != expected_left:
                issues.append("cover-split-photo-side")
        if section.count('class="el cover-split-title"') != 1 or section.count('class="el cover-split-subtitle"') != 1:
            issues.append("cover-split-copy-count")
        if section.count('data-edit-composite="cover-logo"') != 1:
            issues.append("cover-split-logo-count")
    elif layout_id == "cover-photo-overlay-block":
        if 'data-full-bleed-media="true"' not in section:
            issues.append("cover-overlay-media-contract")
        photos = node_boxes(section, "cover-overlay-photo")
        blocks = node_boxes(section, "cover-overlay-block")
        accents = node_boxes(section, "cover-overlay-accent")
        if len(photos) != 1 or photos[0]["left"] != 326 or photos[0]["left"] + photos[0]["width"] != 1920:
            issues.append("cover-overlay-photo-geometry")
        if len(blocks) != 1 or blocks[0]["left"] != 96 or blocks[0]["left"] + blocks[0]["width"] > 1920 * 0.51:
            issues.append("cover-overlay-block-geometry")
        if len(accents) != 1 or not blocks or accents[0]["top"] != blocks[0]["top"] or accents[0]["height"] != blocks[0]["height"] or accents[0]["left"] + accents[0]["width"] != 1920:
            issues.append("cover-overlay-accent-geometry")
    elif layout_id in {"hero-fullbleed-brand-footer", "hero-fullbleed"}:
        if 'data-full-bleed-media="true"' not in section:
            issues.append("cover-hero-media-contract")
        photos = node_boxes(section, "cover-hero-media")
        if len(photos) != 1 or photos[0]["width"] != 1920 or photos[0]["height"] != 1080:
            issues.append("cover-hero-photo-geometry")
        if section.count('data-edit-composite="cover-logo"') != 1:
            issues.append("cover-hero-logo-count")
        expected_title_class = "cover-hero-title" if layout_id == "hero-fullbleed-brand-footer" else "cover-bottom-title"
        if section.count(f'class="el {expected_title_class}"') != 1:
            issues.append("cover-hero-title-count")
    else:
        issues.append("unknown-cover-layout")
    return issues


def check_dataviz(layout_id: str, section: str) -> list[str]:
    issues = check_edit_contract(section) + check_frame(section)
    if not has_content_wrapper(section):
        issues.append("missing-content-wrapper")
    if layout_id == "data-annotation":
        charts = node_boxes(section, "dataviz-annotation-chart")
        cards = node_boxes(section, "dataviz-annotation-card")
        if len(charts) != 1 or charts[0]["width"] != 1728:
            issues.append("annotation-chart-geometry")
        if not has_python_chart(section, "annotation-line"):
            issues.append("annotation-line-semantics")
        if len(cards) != 2 or not same_size(cards):
            issues.append("annotation-card-balance")
        if section.count('data-edit-composite="chart-annotation-') != 2:
            issues.append("annotation-edit-contract")
    elif layout_id == "heat-map":
        if not has_python_chart(section, "heat-map"):
            issues.append("heat-python-chart-contract")
        if len(re.findall(r'id="python-heat-cell-[1-5]-[1-6]"', section)) != 30:
            issues.append("heat-cell-count")
        if section.count('class="heat-row"') != 5:
            issues.append("heat-axis-label-count")
        if section.count('class="el heat-legend"') != 1:
            issues.append("heat-legend-count")
        row_panels = node_boxes(section, "heat-row-panel")
        grids = node_boxes(section, "heat-grid")
        if len(row_panels) != 1 or len(grids) != 1:
            issues.append("heat-module-count")
        elif row_panels[0]["top"] != grids[0]["top"] or row_panels[0]["height"] != grids[0]["height"]:
            issues.append("heat-modules-not-aligned")
    elif layout_id == "map-region":
        if section.count('class="map-region-shape ') != 5:
            issues.append("region-shape-count")
        if section.count('class="city-pin ') != 0 or 'class="map-outline"' in section:
            issues.append("region-map-wrong-semantics")
        cards = node_boxes(section, "map-data-card")
        if len(cards) != 3 or not same_size(cards):
            issues.append("region-card-balance")
    elif layout_id == "map-spotlight":
        if section.count('class="map-outline"') != 1 or section.count('class="city-pin ') != 3:
            issues.append("spotlight-pin-semantics")
        if 'class="map-region-shape ' in section:
            issues.append("spotlight-unexpected-regions")
        cards = node_boxes(section, "map-data-card")
        if len(cards) != 3 or not same_size(cards):
            issues.append("spotlight-card-balance")
    elif layout_id == "multi-line-chart":
        if not has_python_chart(section, "multi-line"):
            issues.append("multiline-python-chart-contract")
        if len(re.findall(r'id="python-series-[123]"', section)) != 3:
            issues.append("multiline-series-count")
    elif layout_id == "radar-chart":
        if not has_python_chart(section, "radar"):
            issues.append("radar-python-chart-contract")
        if len(re.findall(r'id="python-series-[12]"', section)) != 2:
            issues.append("radar-series-count")
        if len(re.findall(r'<span data-edit-layer="text" style="left:', section)) != 6:
            issues.append("radar-label-count")
        if section.count('class="radar-legend-row ') != 2:
            issues.append("radar-legend-row-count")
    else:
        issues.append("unknown-data-viz-layout")
    return issues


def check_media(layout_id: str, section: str) -> list[str]:
    issues = check_edit_contract(section) + check_frame(section)
    if not has_content_wrapper(section):
        issues.append("missing-content-wrapper")
    if layout_id == "executive-bio":
        photos = node_boxes(section, "media-executive-photo")
        bios = node_boxes(section, "media-bio-panel")
        if len(photos) != 1 or photos[0]["height"] < 700:
            issues.append("executive-photo-geometry")
        if len(bios) != 1 or bios[0]["left"] <= photos[0]["left"] + photos[0]["width"] if photos else True:
            issues.append("executive-copy-separation")
        if section.count('class="media-bio-row ') != 3:
            issues.append("executive-bio-row-count")
        for class_name in ("media-executive-name", "media-executive-role", "media-executive-meta"):
            if section.count(f'class="el {class_name}"') != 1:
                issues.append(f"executive-{class_name}-count")
    elif layout_id == "photo-left-overlay-title-right":
        photos = node_boxes(section, "media-framed-photo")
        overlays = node_boxes(section, "media-overlay-title")
        if len(photos) != 1 or len(overlays) != 1 or section.count('class="el media-overlay-body"') != 1:
            issues.append("overlay-module-count")
        else:
            if photos[0]["left"] != 0 or photos[0]["width"] >= overlays[0]["left"]:
                issues.append("overlay-photo-frame-geometry")
            if overlays[0]["left"] != 930 or not re.search(r'class="el media-overlay-body"[^>]*style="left:962px;', section):
                issues.append("overlay-copy-left-edge")
        if section.count('data-edit-composite="framed-photo-left"') != 1 or section.count('data-edit-composite="photo-overlay-title"') != 1:
            issues.append("overlay-edit-contract")
    elif layout_id == "testimonial-full":
        photos = node_boxes(section, "media-testimonial-photo")
        logos = node_boxes(section, "media-testimonial-logo")
        if len(photos) != 1 or abs(photos[0]["width"] - photos[0]["height"]) > 0.1:
            issues.append("testimonial-photo-not-circular")
        if len(logos) != 1 or logos[0]["left"] + logos[0]["width"] != 1728:
            issues.append("testimonial-logo-right-edge")
        if section.count('class="el media-testimonial-quote"') != 1 or 'max-width:1460px' not in section:
            issues.append("testimonial-quote-dominance")
        if section.count('class="el media-testimonial-name"') != 1 or section.count('class="el media-testimonial-role"') != 1:
            issues.append("testimonial-attribution-count")
        if section.count('data-edit-composite="quote-decoration"') != 1:
            issues.append("testimonial-quote-decoration")
    else:
        issues.append("unknown-media-layout")
    return issues


def check_modules(layout_id: str, section: str) -> list[str]:
    issues = check_edit_contract(section) + check_frame(section)
    if not has_content_wrapper(section):
        issues.append("missing-content-wrapper")
    if layout_id.startswith("cards-1-plus-"):
        count = int(layout_id.rsplit("-", 1)[1])
        cards = node_boxes(section, "module-card")
        if len(cards) != count:
            issues.append("module-card-count")
        elif not same_size(cards):
            issues.append("module-card-size-mismatch")
        else:
            rows: dict[float, list[dict[str, float]]] = {}
            for card in cards:
                rows.setdefault(card["top"], []).append(card)
            expected_rows = {2: [2], 3: [3], 4: [2, 2], 5: [3, 2], 6: [3, 3], 8: [4, 4]}[count]
            actual_rows = [len(rows[top]) for top in sorted(rows)]
            if actual_rows != expected_rows:
                issues.append("module-card-grid-shape")
            for row in rows.values():
                left = min(card["left"] for card in row)
                right = max(card["left"] + card["width"] for card in row)
                if abs((left + right) / 2 - 864) > 1:
                    issues.append("module-row-center-drift")
                    break
        if section.count('data-edit-composite="module-card-') != count:
            issues.append("module-card-edit-contract")
        if section.count('class="module-number"') != count or section.count('class="module-tag"') != count:
            issues.append("module-card-layer-count")
        number_size = css_font_size("module-number")
        if number_size is None or number_size < 31:
            issues.append("module-number-not-dominant")
        if section.count('class="el module-subtitle"') != 1:
            issues.append("module-subtitle-count")
    elif layout_id == "icon-grid-6":
        cells = node_boxes(section, "module-icon-cell")
        if len(cells) != 6 or not same_size(cells):
            issues.append("icon-cell-count-or-size")
        else:
            if len({cell["left"] for cell in cells}) != 3 or len({cell["top"] for cell in cells}) != 2:
                issues.append("icon-grid-not-3x2")
        if section.count('class="module-icon-shape"') != 6 or section.count('data-edit-composite="icon-cell-') != 6:
            issues.append("icon-grid-layer-count")
    elif layout_id == "people-3":
        cards = node_boxes(section, "module-person-card")
        if len(cards) != 3 or not same_size(cards) or len({card["top"] for card in cards}) != 1:
            issues.append("people-card-balance")
        if section.count('class="module-person-photo"') != 3:
            issues.append("people-photo-count")
        if section.count('data-edit-composite="person-card-') != 3:
            issues.append("people-edit-contract")
        if "border-radius:50%" not in PRODUCTION_CSS:
            issues.append("people-photo-not-circular")
    elif layout_id == "team-grid":
        cards = node_boxes(section, "module-team-card")
        if len(cards) != 6 or not same_size(cards):
            issues.append("team-card-count-or-size")
        else:
            if len({card["left"] for card in cards}) != 3 or len({card["top"] for card in cards}) != 2:
                issues.append("team-grid-not-3x2")
        if section.count('class="module-team-photo"') != 6 or section.count('data-edit-composite="team-member-') != 6:
            issues.append("team-card-layer-count")
    else:
        issues.append("unknown-modules-layout")
    return issues


def check_toc(layout_id: str, section: str) -> list[str]:
    issues = check_edit_contract(section) + check_frame(section)
    if not has_content_wrapper(section):
        issues.append("missing-content-wrapper")
    standard = {"toc-3", "toc-4", "toc-5", "toc-6", "toc-8"}
    if layout_id in standard:
        count = int(layout_id.split("-")[1])
        cards = node_boxes(section, "toc-nav-card")
        if len(cards) != count or not same_size(cards):
            issues.append("toc-standard-card-count-or-size")
        else:
            rows: dict[float, list[dict[str, float]]] = {}
            for card in cards:
                rows.setdefault(card["top"], []).append(card)
            expected = {2: [2], 3: [3], 4: [2, 2], 5: [3, 2], 6: [3, 3], 8: [4, 4]}[count]
            if [len(rows[top]) for top in sorted(rows)] != expected:
                issues.append("toc-standard-grid-shape")
            for row in rows.values():
                left = min(card["left"] for card in row)
                right = max(card["left"] + card["width"] for card in row)
                if abs((left + right) / 2 - 864) > 1:
                    issues.append("toc-standard-row-center")
                    break
        if section.count('class="el toc-subtitle"') != 1:
            issues.append("toc-standard-subtitle")
    elif layout_id.endswith("-vertical"):
        count = int(layout_id.split("-")[1])
        rows = node_boxes(section, "toc-vertical-row")
        if len(rows) != count or not same_size(rows):
            issues.append("toc-vertical-row-count-or-size")
        elif any(row["left"] != 0 or row["width"] != 1728 for row in rows):
            issues.append("toc-vertical-row-width")
    elif layout_id.endswith("-panel-rows"):
        count = int(layout_id.split("-")[1])
        panels = node_boxes(section, "toc-side-panel")
        rows = node_boxes(section, "toc-panel-row")
        if len(panels) != 1 or panels[0]["width"] != 520:
            issues.append("toc-panel-rows-intro-panel")
        if len(rows) != count or not same_size(rows):
            issues.append("toc-panel-row-count-or-size")
        elif any(row["left"] != 580 or row["left"] + row["width"] != 1728 for row in rows):
            issues.append("toc-panel-row-column-geometry")
    elif layout_id.endswith("-panel-grid"):
        count = int(layout_id.split("-")[1])
        panels = node_boxes(section, "toc-side-panel")
        cards = node_boxes(section, "toc-panel-grid-card")
        if len(panels) != 1 or len(cards) != count:
            issues.append("toc-panel-grid-module-count")
        elif count == 4:
            if not same_size(cards) or len({card["left"] for card in cards}) != 2 or len({card["top"] for card in cards}) != 2:
                issues.append("toc-panel-grid-not-2x2")
        else:
            if cards[-1]["width"] != 1148 or cards[-1]["left"] != 580:
                issues.append("toc-panel-grid-feature-row")
    elif layout_id == "toc-3-panel-left":
        panels = node_boxes(section, "toc-wide-panel")
        cards = node_boxes(section, "toc-panel-feature")
        if len(panels) != 1 or panels[0]["width"] != 650:
            issues.append("toc-wide-panel-geometry")
        if len(cards) != 3 or not same_size(cards) or any(card["left"] != 700 for card in cards):
            issues.append("toc-panel-feature-balance")
    elif layout_id == "toc-4-image-left":
        count = int(layout_id.split("-")[1])
        photos = node_boxes(section, "toc-image-field")
        rows = node_boxes(section, "toc-image-row")
        if len(photos) != 1 or photos[0]["left"] != 0 or photos[0]["width"] != 700 or photos[0]["height"] != 760:
            issues.append("toc-image-left-geometry")
        if len(rows) != count or not same_size(rows) or any(row["left"] != 760 for row in rows):
            issues.append("toc-image-row-balance")
        if section.count('class="el toc-image-title"') != 1:
            issues.append("toc-image-title-count")
    elif layout_id == "toc-5-number-panel-left":
        panels = node_boxes(section, "toc-number-panel")
        rows = node_boxes(section, "toc-number-row")
        if len(panels) != 1 or panels[0]["width"] != 420:
            issues.append("toc-number-panel-geometry")
        if section.count('class="toc-number-strip ') != 5:
            issues.append("toc-number-strip-count")
        if len(rows) != 5 or not same_size(rows) or any(row["left"] != 470 for row in rows):
            issues.append("toc-number-row-balance")
    else:
        issues.append("unknown-toc-layout")
    expected_chapters = int(layout_id.split("-")[1])
    if section.count('data-edit-composite="toc-chapter-') != expected_chapters:
        issues.append("toc-chapter-edit-contract")
    return issues


def check_family(family: str, layout_id: str, section: str) -> list[str]:
    if family == "diagram":
        return check_diagram(layout_id, section)
    if family == "comparison":
        return check_comparison(layout_id, section)
    if family == "metrics":
        return check_metrics(layout_id, section)
    if family == "closing":
        return check_closing(layout_id, section)
    if family == "statement":
        return check_statement(layout_id, section)
    if family == "chapter":
        return check_chapter(layout_id, section)
    if family == "content":
        return check_content(layout_id, section)
    if family == "sequence":
        return check_sequence(layout_id, section)
    if family == "cover":
        return check_cover(layout_id, section)
    if family == "data-viz":
        return check_dataviz(layout_id, section)
    if family == "media":
        return check_media(layout_id, section)
    if family == "modules":
        return check_modules(layout_id, section)
    if family == "toc":
        return check_toc(layout_id, section)
    return ["unknown-production-family"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html-dir", required=True)
    parser.add_argument("--family", required=True, choices=sorted(FAMILY_LAYOUTS))
    parser.add_argument("--theme-scope", choices=("representative", "all"), default="representative")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    directory = Path(args.html_dir).resolve()
    layouts = FAMILY_LAYOUTS[args.family]
    all_files = sorted(path for path in directory.glob("*.html") if path.name != "edit-mode.js")
    expected_theme_ids = (
        {path.stem for path in CORE_THEME_DIR.glob("*.yaml")}
        if args.theme_scope == "all"
        else set(REPRESENTATIVE_THEMES)
    )
    available_by_theme = {path.stem: path for path in all_files}
    missing_themes = sorted(expected_theme_ids - set(available_by_theme))
    unexpected_themes = (
        sorted(set(available_by_theme) - expected_theme_ids)
        if args.theme_scope == "all"
        else []
    )
    files = [available_by_theme[theme_id] for theme_id in sorted(expected_theme_ids & set(available_by_theme))]
    expected_files = len(expected_theme_ids)
    issues: list[dict[str, Any]] = [
        {"theme": theme_id, "issue": "missing-theme-catalog"}
        for theme_id in missing_themes
    ]
    issues.extend(
        {"theme": theme_id, "issue": "unexpected-theme-catalog"}
        for theme_id in unexpected_themes
    )
    checked = 0
    for path in files:
        markup = path.read_text(encoding="utf-8")
        if f'data-theme="{path.stem}"' not in markup:
            issues.append({"theme": path.stem, "issue": "theme-identity-mismatch"})
        if markup.count('data-edit-mode-embedded="true"') != 1:
            issues.append({"theme": path.stem, "issue": "embedded-editor-count"})
        for layout_id in sorted(layouts):
            section = section_for(markup, layout_id)
            if section is None:
                issues.append({"theme": path.stem, "layout": layout_id, "issue": "missing-layout"})
                continue
            checked += 1
            for issue in check_family(args.family, layout_id, section):
                issues.append({"theme": path.stem, "layout": layout_id, "issue": issue})

    density_cases = {
        "low": {"title": "短標", "items": ["短句"] * 3},
        "medium": {"title": "一般長度且需要補充背景的決策標題", "items": ["一般內容說明文字"] * 6},
        "high": {"title": "需要更多文字才能完整表達的高密度決策標題內容", "items": ["這是一段需要保留語意與限制條件的較長內容說明"] * 8},
    }
    density_coverage = {name: density_profile(content) for name, content in density_cases.items()}
    if [value[0] for value in density_coverage.values()] != ["low", "medium", "high"]:
        issues.append({"issue": "density-branch-coverage", "actual": density_coverage})

    report = {
        "family": args.family,
        "theme_scope": args.theme_scope,
        "expected_themes": sorted(expected_theme_ids),
        "missing_themes": missing_themes,
        "unexpected_themes": unexpected_themes,
        "representative_themes": sorted(REPRESENTATIVE_THEMES),
        "layouts": sorted(layouts),
        "files": len(files),
        "slides_checked": checked,
        "density_coverage": density_coverage,
        "issues": issues,
        "pass": len(files) == expected_files and checked == expected_files * len(layouts) and not issues,
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
