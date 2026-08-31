#!/usr/bin/env python3
"""Generate one coherent HTML deck with randomized content, layouts, and art direction."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import random
import re
import secrets
import sys
import time
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import quote


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import html_production_renderer as production  # noqa: E402
from art_direction import build_renderer_handoff, load_art_direction  # noqa: E402
from artifact_report_paths import portable_report_path  # noqa: E402
from html_assembly import load_html_assembly_catalog, resolve_html_assembly  # noqa: E402
from html_css_ownership import (  # noqa: E402
    assert_appearance_css,
    validate_html_document_text,
)
from html_design_method import (  # noqa: E402
    load_html_design_method,
    resolve_content_plan,
    resolve_layout_plan,
)
from html_design_dialects import load_html_design_dialects  # noqa: E402
from html_edit_framework import (
    pptx_browser_runtime_sha256,
    validate_editable_html,
    validate_edit_layer_positions,
    validate_edit_module_structures,
)  # noqa: E402
from html_layout_catalog import (  # noqa: E402
    ASSET_POLICIES,
    MEDIA_MODES,
    filter_html_layouts,
    load_html_layout_catalog,
    visible_html_layouts,
)
from html_layout_family import layout_family  # noqa: E402
from html_motion_runtime import motion_runtime_manifest  # noqa: E402
from html_visible_copy import assert_visible_copy  # noqa: E402
from html_preset_themes import (  # noqa: E402
    build_preset_appearance_css,
    load_html_preset_theme_catalog,
)
from render_html_matrix import render_catalog  # noqa: E402


BASE_THEME_POOL = [
    "brand-editorial",
    "brutal-grunge",
    "clean-tech-business",
    "dark-circuit",
    "festive-patterned",
    "grainy-editorial",
    "lavender-media-kit",
    "paper-collage-vintage",
    "product-strategy-signal",
    "soft-organic-education",
]

HTML_PRESET_THEME_CATALOG = load_html_preset_theme_catalog()
HTML_PRESET_THEME_DEFINITIONS = HTML_PRESET_THEME_CATALOG["themes"]
PRESET_THEME_POOL = sorted(HTML_PRESET_THEME_DEFINITIONS)
# Automatic generation may sample curated Preset themes, but it never binds
# their example story/layout sequence. Preset example content is an explicit
# demo mode only; all base themes remain available through --theme.
AUTO_THEME_POOL = [
    theme_id
    for theme_id in PRESET_THEME_POOL
    if HTML_PRESET_THEME_DEFINITIONS[theme_id].get("auto_select")
]
THEME_POOL = BASE_THEME_POOL + PRESET_THEME_POOL

# Keep this set aligned with html_production_renderer._module_card_geometry.
# Module cards use fixed slots, so the payload count must match the Layout
# capacity exactly; it is not safe to render a partial set or silently drop
# excess items.
MODULE_LAYOUT_CAPACITY = {
    f"cards-1-plus-{count}": count
    for count in (2, 3, 4, 5, 6, 8)
}
CONTENT_PRESERVING_CARD_LAYOUT = {
    1: "cards-1-plus-2",
    2: "cards-1-plus-2",
    3: "cards-1-plus-3",
    4: "cards-1-plus-4",
    5: "cards-1-plus-5",
    6: "cards-1-plus-6",
    7: "cards-1-plus-8",
    8: "cards-1-plus-8",
}


def write_text_with_retry(path: Path, text: str, *, attempts: int = 8) -> None:
    """Write generated files reliably inside OneDrive-backed workspaces."""
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(attempts):
        try:
            path.write_text(text, encoding="utf-8", newline="\n")
            return
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.18 * (attempt + 1))


def inject_owned_css(document: str, owner: str, css: str) -> str:
    """Append one auditable CSS layer without merging ownership boundaries."""

    if owner in {"theme-appearance", "preset-appearance"}:
        assert_appearance_css(css, source=owner)
    style = f'<style data-css-owner="{escape(owner, quote=True)}">\n{css}\n</style>'
    updated, count = re.subn(r"</head>", style + "</head>", document, count=1, flags=re.IGNORECASE)
    if count != 1:
        raise ValueError("Generated HTML is missing </head> for owned CSS injection")
    return updated


def apply_art_direction_metadata(document: str, handoff: dict[str, Any]) -> str:
    """Bind renderer-neutral scene decisions to the generated HTML."""

    direction_id = escape(str(handoff["art_direction_id"]), quote=True)
    direction_status = escape(str(handoff["status"]), quote=True)
    document, root_count = re.subn(
        r"(<html\b[^>]*)(>)",
        rf'\1 data-art-direction-id="{direction_id}" '
        rf'data-art-direction-status="{direction_status}"\2',
        document,
        count=1,
    )
    if root_count != 1:
        raise ValueError("Generated HTML is missing the root <html> element")

    scenes = iter(handoff["scene_plan"])

    def bind_scene(match: re.Match[str]) -> str:
        try:
            scene = next(scenes)
        except StopIteration as exc:
            raise ValueError("Art Direction scene count is smaller than rendered slide count") from exc
        role = escape(str(scene["role"]), quote=True)
        intensity = int(scene["visual_intensity"])
        slide_id = escape(str(scene["slide_id"]), quote=True)
        return (
            f'{match.group(1)} data-scene-id="{slide_id}" '
            f'data-scene-role="{role}" data-visual-intensity="{intensity}"'
        )

    document, slide_count = re.subn(
        r'(<section class="slide(?: active)?" id="s\d+")',
        bind_scene,
        document,
    )
    try:
        next(scenes)
    except StopIteration:
        pass
    else:
        raise ValueError("Art Direction scene count is larger than rendered slide count")
    if slide_count != len(handoff["scene_plan"]):
        raise ValueError(
            "Art Direction scene count does not match rendered slide count: "
            f"{len(handoff['scene_plan'])} != {slide_count}"
        )
    return document


def embedded_svg_css_url(relative_path: str) -> str:
    """Keep project-owned preset SVG decoration inside standalone HTML output."""

    source = PROJECT_ROOT / relative_path
    svg = source.read_text(encoding="utf-8")
    encoded = quote(svg, safe="/:;=,?@-._~!$&'()*+")
    return f'url("data:image/svg+xml;charset=UTF-8,{encoded}")'


def embedded_binary_css_url(relative_path: str) -> str:
    """Keep a licensed local image inside standalone HTML output."""

    source = PROJECT_ROOT / relative_path
    mime_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(source.read_bytes()).decode("ascii")
    return f'url("data:{mime_type};base64,{encoded}")'


MOONLIT_BOTANICAL_PLATE_URL = embedded_binary_css_url(
    "prompt_system/renderers/html/assets/external/moonlit-herbarium-atlas/matricaria-chamomilla-koehler-plate-64.jpg"
)


# Historical showcase payloads are quarantined behind explicit preset-demo.
# Reusable new-deck Presets never read these stories, Layout lists, content
# replacements, or CSS.  Their runtime appearance is built only from the clean
# contract in prompt_system/renderers/html/preset-themes.yaml.
PRESET_DEMO_PROFILES: dict[str, dict[str, Any]] = {
    "sepia-retail-case": {
        "style_case_source": "prompt_system/style_cases/cover-photo-frame.sepia-retail-case.yaml",
        "base_theme": "grainy-editorial",
        "story": "circular-market",
        "layouts": [
            "cover-center-title-edge-decor",
            "toc-3-panel-left",
            "split-comparison",
            "timeline-milestones",
            "quote-focus",
        ],
        "content": {
            "cover-center-title": "一座市場，如何停止製造垃圾",
            "cover-center-subtitle": "從攤商備料、消費容器到清運時間，重畫傳統市場的循環物流",
            "cover-center-speaker": "CIRCULAR MARKET COLLECTIVE",
            "cover-center-org": "FIELD REPORT · 2026",
        },
        "css": r"""
html[data-style-case="sepia-retail-case"]{--bg:#f3ede3;--surface:#fffaf2;--text:#2d211b;--muted:#6f5e54;--accent:#a96938;--support-accent:#d6b78f}
html[data-style-case="sepia-retail-case"] .slide{color:#2d211b;background-color:#f3ede3;background-image:radial-gradient(circle at 98% 96%,transparent 0 220px,rgba(102,69,48,.075) 221px 223px,transparent 224px 332px,rgba(102,69,48,.05) 333px 335px,transparent 336px),linear-gradient(116deg,rgba(177,122,74,.10),transparent 34%),radial-gradient(circle,rgba(61,40,28,.045) 0 1px,transparent 1.5px);background-size:100% 100%,100% 100%,6px 6px;box-shadow:inset 0 0 120px rgba(83,55,37,.055)}
html[data-style-case="sepia-retail-case"] .cover-edge-decor{display:none!important}
html[data-style-case="sepia-retail-case"] .cover-center-area{left:104px!important;width:1450px!important;align-items:flex-start!important;text-align:left!important;gap:26px!important}
html[data-style-case="sepia-retail-case"] .cover-center-title{max-width:1120px!important;text-align:left!important;font:700 108px/1.04 var(--font-display)!important;letter-spacing:-.05em;color:#2d211b;text-wrap:balance}
html[data-style-case="sepia-retail-case"] .cover-center-rule{width:210px!important;height:4px!important;background:linear-gradient(90deg,#a96938,rgba(169,105,56,.08))!important}
html[data-style-case="sepia-retail-case"] .cover-center-subtitle{max-width:1210px!important;text-align:left!important;font:500 38px/1.45 var(--font-display)!important;color:#6f5e54}
html[data-style-case="sepia-retail-case"] .cover-center-speaker,html[data-style-case="sepia-retail-case"] .cover-center-org{text-align:left!important;color:#6f5e54}
html[data-style-case="sepia-retail-case"] .cover-logo{display:none!important}
html[data-style-case="sepia-retail-case"] .prod-title{font-family:var(--font-display);letter-spacing:-.045em;color:#2d211b}
html[data-style-case="sepia-retail-case"] .diagram-node-bg{background:rgba(255,250,242,.78)!important;border:1px solid rgba(87,57,39,.14)!important;box-shadow:0 18px 44px rgba(74,43,25,.09)!important;backdrop-filter:blur(5px)}
html[data-style-case="sepia-retail-case"] [data-layout-id="toc-3-panel-left"] .diagram-node:first-of-type .diagram-node-bg{background:#2e211b linear-gradient(150deg,#5b3a29,#2e211b)!important;border-color:transparent!important}
html[data-style-case="sepia-retail-case"] [data-layout-id="toc-3-panel-left"] .toc-wide-panel,html[data-style-case="sepia-retail-case"] [data-layout-id="toc-3-panel-left"] .toc-wide-panel :is(span,b,p,em){color:#fffaf2!important}
html[data-style-case="sepia-retail-case"] [data-layout-id="split-comparison"] .diagram-node:nth-of-type(odd) .diagram-node-bg{background:rgba(225,198,165,.66)!important}
html[data-style-case="sepia-retail-case"] [data-layout-id="timeline-milestones"] .sequence-number{font-family:var(--font-display);color:#a96938!important}
html[data-style-case="sepia-retail-case"] [data-layout-id="quote-focus"] .statement-quote{font-family:var(--font-display);font-style:italic;text-shadow:none}
""",
    },
    "dark-ai-city": {
        "style_case_source": "prompt_system/style_cases/hero-fullbleed-brand-footer.dark-ai-city.yaml",
        "base_theme": "dark-circuit",
        "story": "night-cooling-network",
        "layouts": [
            "cover-center-title-edge-decor",
            "toc-6",
            "chapter-number-bg-left-title-rule",
            "dashboard-overview",
            "multi-line-chart",
            "cards-1-plus-3",
            "before-after",
            "cycle-hub-6",
            "matrix-4quadrant",
            "strategic-priorities",
            "process-flow",
            "kpi-scorecards",
            "timeline-milestones",
            "org-chart",
            "highlight-callout",
            "quote-focus",
            "title-center",
        ],
        "content": {
            "cover-center-title": "AI 城市基礎設施",
            "cover-center-subtitle": "用城市感測、居民路徑與維運訊號，打造可驗證、可停止、也可擴張的夜間降溫決策系統",
            "cover-center-speaker": "CITY INSIGHT · 2026 趨勢報告",
            "cover-center-org": "URBAN SYSTEMS LAB",
        },
        "css": r"""
html[data-style-case="dark-ai-city"]{--bg:#0b1220;--surface:#111d2c;--text:#f5f7fa;--muted:#9aa7b8;--accent:#3fd0e8;--support-accent:#62d6a7;--surface-text:#f5f7fa;--surface-muted:#9aa7b8;--accent-ink:#b8e3ea;--surface-accent-ink:#b8e3ea;--accent-text:#08131d}
html[data-style-case="dark-ai-city"] .slide{color:#f5f7fa;background-color:#0b1220;background-image:linear-gradient(rgba(63,208,232,.028) 1px,transparent 1px),linear-gradient(90deg,rgba(63,208,232,.028) 1px,transparent 1px);background-size:48px 48px;box-shadow:inset 0 0 120px rgba(0,0,0,.22)}
html[data-style-case="dark-ai-city"] .slide:not([data-layout-id="cover-center-title-edge-decor"]){--orbit-a-x:1720px;--orbit-a-y:190px;--orbit-b-x:110px;--orbit-b-y:940px}
html[data-style-case="dark-ai-city"] .slide:not([data-layout-id="cover-center-title-edge-decor"])::before{content:""!important;display:block!important;position:absolute;inset:0;pointer-events:none;background:radial-gradient(circle at var(--orbit-a-x) var(--orbit-a-y),transparent 0 246px,rgba(63,208,232,.22) 247px 249px,transparent 250px 304px,rgba(63,208,232,.040) 305px 350px,rgba(63,208,232,.022) 351px 398px,transparent 399px),radial-gradient(circle at var(--orbit-b-x) var(--orbit-b-y),transparent 0 172px,rgba(98,214,167,.13) 173px 175px,transparent 176px 236px,rgba(63,208,232,.025) 237px 278px,transparent 279px);opacity:.72;z-index:0}
html[data-style-case="dark-ai-city"] .slide:nth-of-type(3n+2){--orbit-a-x:1650px;--orbit-a-y:900px;--orbit-b-x:80px;--orbit-b-y:160px}
html[data-style-case="dark-ai-city"] .slide:nth-of-type(3n){--orbit-a-x:210px;--orbit-a-y:920px;--orbit-b-x:1840px;--orbit-b-y:240px}
html[data-style-case="dark-ai-city"] .slide:nth-of-type(3n+1){--orbit-a-x:1780px;--orbit-a-y:260px;--orbit-b-x:190px;--orbit-b-y:850px}
html[data-style-case="dark-ai-city"] .slide[data-production-family="chapter"]::before,html[data-style-case="dark-ai-city"] .slide[data-layout-id="title-center"]::before{opacity:.9}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="cover-center-title-edge-decor"]{background-image:linear-gradient(to bottom,transparent 0 1076px,#3fd0e8 1076px 1080px),radial-gradient(circle at 12% 12%,rgba(63,208,232,.16),transparent 30%),radial-gradient(circle at 88% 62%,rgba(63,208,232,.10),transparent 28%),linear-gradient(rgba(63,208,232,.028) 1px,transparent 1px),linear-gradient(90deg,rgba(63,208,232,.028) 1px,transparent 1px);background-size:100% 100%,100% 100%,100% 100%,48px 48px,48px 48px}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="cover-center-title-edge-decor"]::before{content:""!important;display:block!important;position:absolute;inset:0;pointer-events:none;background:radial-gradient(circle at 160px 130px,transparent 0 308px,rgba(63,208,232,.45) 309px 312px,transparent 313px 360px,rgba(63,208,232,.035) 361px 412px,rgba(63,208,232,.02) 413px 464px,transparent 465px),radial-gradient(circle at 1855px 530px,transparent 0 213px,rgba(63,208,232,.32) 214px 216px,transparent 217px);z-index:0}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="cover-center-title-edge-decor"]::after{content:""!important;display:block!important;position:absolute;left:1500px;top:48px;width:330px;height:210px;pointer-events:none;background-image:radial-gradient(circle,rgba(63,208,232,.70) 0 2px,transparent 2.5px);background-size:30px 30px;opacity:.58;z-index:0}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="toc-6"]{background-image:radial-gradient(circle at 14% 78%,rgba(63,208,232,.075),transparent 30%),radial-gradient(circle at 88% 18%,rgba(98,214,167,.045),transparent 24%),linear-gradient(rgba(63,208,232,.018) 1px,transparent 1px),linear-gradient(90deg,rgba(63,208,232,.018) 1px,transparent 1px);background-size:100% 100%,100% 100%,64px 64px,64px 64px}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="cards-1-plus-3"]{background-image:radial-gradient(circle at 83% 18%,rgba(63,208,232,.105),transparent 27%),linear-gradient(118deg,transparent 0 69%,rgba(98,214,167,.045) 69% 69.18%,transparent 69.18%),linear-gradient(rgba(63,208,232,.018) 1px,transparent 1px),linear-gradient(90deg,rgba(63,208,232,.018) 1px,transparent 1px);background-size:100% 100%,100% 100%,72px 72px,72px 72px}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="before-after"]{background-image:linear-gradient(90deg,rgba(255,255,255,.012) 0 49.8%,rgba(63,208,232,.026) 50.2% 100%),radial-gradient(circle at 25% 52%,rgba(154,167,184,.045),transparent 31%),radial-gradient(circle at 75% 52%,rgba(63,208,232,.065),transparent 31%),linear-gradient(rgba(63,208,232,.014) 1px,transparent 1px);background-size:100% 100%,100% 100%,100% 100%,100% 72px}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="cycle-hub-6"]{background-image:repeating-radial-gradient(circle at 50% 54%,transparent 0 178px,rgba(63,208,232,.022) 180px 181px,transparent 183px 252px),radial-gradient(circle at 50% 54%,rgba(63,208,232,.07),transparent 35%),linear-gradient(rgba(63,208,232,.014) 1px,transparent 1px),linear-gradient(90deg,rgba(63,208,232,.014) 1px,transparent 1px);background-size:100% 100%,100% 100%,72px 72px,72px 72px}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="matrix-4quadrant"]{background-image:linear-gradient(90deg,transparent 49.92%,rgba(63,208,232,.032) 50%,transparent 50.08%),linear-gradient(transparent 52.92%,rgba(63,208,232,.032) 53%,transparent 53.08%),radial-gradient(circle at 74% 30%,rgba(98,214,167,.052),transparent 27%),linear-gradient(rgba(63,208,232,.012) 1px,transparent 1px);background-size:100% 100%,100% 100%,100% 100%,100% 72px}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="process-flow"]{background-image:radial-gradient(ellipse at 50% 58%,rgba(63,208,232,.075),transparent 48%),linear-gradient(to bottom,transparent 0 56%,rgba(63,208,232,.045) 56% 56.18%,transparent 56.18%),repeating-linear-gradient(90deg,transparent 0 191px,rgba(63,208,232,.017) 192px,transparent 193px 288px);background-size:100% 100%,100% 100%,288px 100%}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="dashboard-overview"]{background-image:radial-gradient(circle at 12% 12%,rgba(63,208,232,.09),transparent 28%),radial-gradient(circle at 86% 84%,rgba(98,214,167,.055),transparent 31%),linear-gradient(135deg,rgba(255,255,255,.012),transparent 45%);background-size:100% 100%}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="chapter-number-bg-left-title-rule"]{background-image:linear-gradient(90deg,rgba(63,208,232,.055) 0 42%,transparent 42%),radial-gradient(circle at 76% 48%,rgba(63,208,232,.11),transparent 34%),linear-gradient(rgba(63,208,232,.018) 1px,transparent 1px),linear-gradient(90deg,rgba(63,208,232,.018) 1px,transparent 1px);background-size:100% 100%,100% 100%,72px 72px,72px 72px}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="multi-line-chart"]{background-image:linear-gradient(90deg,transparent 0 68%,rgba(98,214,167,.025) 68% 100%),radial-gradient(ellipse at 50% 78%,rgba(63,208,232,.075),transparent 46%),linear-gradient(rgba(63,208,232,.014) 1px,transparent 1px);background-size:100% 100%,100% 100%,100% 72px}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="kpi-scorecards"]{background-image:radial-gradient(ellipse at 50% 78%,rgba(63,208,232,.07),transparent 46%),linear-gradient(90deg,rgba(63,208,232,.014) 1px,transparent 1px),linear-gradient(rgba(63,208,232,.014) 1px,transparent 1px);background-size:100% 100%,96px 100%,100% 96px}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="strategic-priorities"]{background-image:radial-gradient(circle at 18% 82%,rgba(63,208,232,.08),transparent 31%),radial-gradient(circle at 84% 18%,rgba(98,214,167,.05),transparent 28%),linear-gradient(120deg,transparent 0 51%,rgba(63,208,232,.028) 51% 51.15%,transparent 51.15%);background-size:100% 100%}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="timeline-milestones"]{background-image:linear-gradient(to bottom,transparent 0 58%,rgba(63,208,232,.04) 58.08%,transparent 58.16%),radial-gradient(ellipse at 50% 58%,rgba(63,208,232,.07),transparent 54%),linear-gradient(90deg,rgba(63,208,232,.014) 1px,transparent 1px);background-size:100% 100%,100% 100%,192px 100%}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="org-chart"]{background-image:linear-gradient(90deg,transparent 49.92%,rgba(63,208,232,.028) 50%,transparent 50.08%),radial-gradient(ellipse at 50% 26%,rgba(63,208,232,.07),transparent 34%),radial-gradient(ellipse at 50% 78%,rgba(98,214,167,.035),transparent 42%);background-size:100% 100%}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="highlight-callout"]{background-image:radial-gradient(circle at 22% 76%,rgba(63,208,232,.075),transparent 32%),linear-gradient(90deg,transparent 0 64.4%,rgba(98,214,167,.028) 64.5% 100%),linear-gradient(rgba(63,208,232,.014) 1px,transparent 1px);background-size:100% 100%,100% 100%,100% 72px}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="quote-focus"]{background-image:radial-gradient(circle at 22% 50%,rgba(63,208,232,.08),transparent 34%),linear-gradient(102deg,transparent 0 71%,rgba(63,208,232,.035) 71% 71.08%,transparent 71.08%),linear-gradient(rgba(63,208,232,.012) 1px,transparent 1px);background-size:100% 100%,100% 100%,100% 72px}
html[data-style-case="dark-ai-city"] .slide[data-layout-id="title-center"]{background-image:radial-gradient(circle at 50% 50%,rgba(63,208,232,.075),transparent 29%),repeating-radial-gradient(circle at 50% 50%,transparent 0 176px,rgba(63,208,232,.036) 177px 178px,transparent 179px 278px),linear-gradient(90deg,rgba(63,208,232,.018),transparent 28%,transparent 72%,rgba(98,214,167,.018));background-size:100% 100%}
html[data-style-case="dark-ai-city"] .cover-edge-decor{display:none!important}
html[data-style-case="dark-ai-city"] .cover-center-area{left:0!important;top:0!important;width:1728px!important;height:888px!important;align-items:center!important;justify-content:center!important;text-align:center!important;gap:0!important;padding:0!important}
html[data-style-case="dark-ai-city"] .cover-center-title{top:228px!important;max-width:1500px!important;text-align:center!important;font:900 120px/1.05 var(--font-heading)!important;letter-spacing:.02em!important;color:#f5f7fa!important;background:none!important;background-clip:border-box!important;-webkit-background-clip:border-box!important;-webkit-text-fill-color:#f5f7fa!important;filter:none!important;mix-blend-mode:normal!important;text-shadow:none!important}
html[data-style-case="dark-ai-city"] .cover-center-rule{display:none!important}
html[data-style-case="dark-ai-city"] .cover-center-subtitle{top:508px!important;max-width:1320px!important;margin:0!important;text-align:center!important;font:500 36px/1.3 var(--font-body)!important;color:#9aa7b8!important}
html[data-style-case="dark-ai-city"] .cover-center-speaker{top:616px!important;margin:0!important;text-align:center!important;font:500 36px/1.35 var(--font-body)!important;color:#f5f7fa!important}
html[data-style-case="dark-ai-city"] .cover-center-org{position:absolute!important;left:864px!important;top:670px!important;margin:0!important;text-align:center!important;font:500 36px/1.35 var(--font-mono)!important;letter-spacing:.18em!important;color:#9aa7b8!important;writing-mode:horizontal-tb!important;translate:-50% 0!important}
html[data-style-case="dark-ai-city"] .cover-logo{display:none!important}
html[data-style-case="dark-ai-city"] [data-edit-kind="text"],html[data-style-case="dark-ai-city"] :is(h1,h2,h3,h4,p,b,em){text-shadow:none!important;filter:none!important;mix-blend-mode:normal!important}
html[data-style-case="dark-ai-city"] .prod-title{color:#f5f7fa!important;-webkit-text-fill-color:#f5f7fa!important;mix-blend-mode:normal!important;text-shadow:none!important;filter:none!important}
html[data-style-case="dark-ai-city"] .diagram-node-bg{background:linear-gradient(145deg,rgba(21,36,56,.96),rgba(17,29,44,.96))!important;border-color:rgba(63,208,232,.22)!important;box-shadow:0 18px 46px rgba(0,0,0,.20)!important;backdrop-filter:blur(8px)}
html[data-style-case="dark-ai-city"] [data-layout-id="toc-6"] .diagram-node-bg{background:rgba(17,29,44,.84)!important;border:1px solid rgba(63,208,232,.12)!important;box-shadow:0 12px 30px rgba(0,0,0,.13)!important;backdrop-filter:blur(4px)}
html[data-style-case="dark-ai-city"] [data-layout-id="cards-1-plus-3"] .diagram-node-bg{background:rgba(17,29,44,.88)!important;border:1px solid rgba(63,208,232,.16)!important;box-shadow:0 16px 36px rgba(0,0,0,.16)!important;backdrop-filter:blur(5px)}
html[data-style-case="dark-ai-city"] [data-layout-id="before-after"] .before .diagram-node-bg{background:rgba(17,29,44,.78)!important;border-color:rgba(154,167,184,.14)!important;box-shadow:0 15px 34px rgba(0,0,0,.14)!important}
html[data-style-case="dark-ai-city"] [data-layout-id="before-after"] .after .diagram-node-bg{background:rgba(15,34,48,.86)!important;border-color:rgba(63,208,232,.22)!important;box-shadow:0 15px 34px rgba(0,0,0,.16)!important}
html[data-style-case="dark-ai-city"] [data-layout-id="cycle-hub-6"] .diagram-node-bg{background:rgba(17,29,44,.86)!important;border-color:rgba(63,208,232,.18)!important;box-shadow:0 10px 24px rgba(0,0,0,.14)!important;backdrop-filter:none}
html[data-style-case="dark-ai-city"] [data-layout-id="matrix-4quadrant"] .diagram-node-bg{background:rgba(17,29,44,.82)!important;border-color:rgba(63,208,232,.13)!important;box-shadow:0 12px 26px rgba(0,0,0,.13)!important;backdrop-filter:none}
html[data-style-case="dark-ai-city"] [data-layout-id="process-flow"] .diagram-node-bg{background:rgba(15,27,42,.88)!important;border:1px solid rgba(63,208,232,.14)!important;box-shadow:0 12px 28px rgba(0,0,0,.14)!important;backdrop-filter:none}
html[data-style-case="dark-ai-city"] [data-layout-id="dashboard-overview"] .diagram-node-bg{background:rgba(17,29,44,.82)!important;border:1px solid rgba(63,208,232,.13)!important;box-shadow:0 14px 32px rgba(0,0,0,.14)!important;backdrop-filter:blur(4px)}
html[data-style-case="dark-ai-city"] [data-layout-id="chapter-number-bg-left-title-rule"] .chapter-number-ghost{color:rgba(63,208,232,.095)!important;text-shadow:none!important;filter:none!important}
html[data-style-case="dark-ai-city"] [data-layout-id="chapter-number-bg-left-title-rule"] .chapter-left-title{max-width:960px!important;color:#f5f7fa!important;text-shadow:none!important}
html[data-style-case="dark-ai-city"] [data-layout-id="chapter-number-bg-left-title-rule"] .chapter-left-subtitle{max-width:930px!important;color:#aebbc9!important}
html[data-style-case="dark-ai-city"] [data-layout-id="multi-line-chart"] .dataviz-multiline .diagram-node-bg{background:rgba(17,29,44,.86)!important;border:1px solid rgba(63,208,232,.14)!important;box-shadow:0 18px 42px rgba(0,0,0,.16)!important}
html[data-style-case="dark-ai-city"] [data-layout-id="multi-line-chart"] .dataviz-multiline .series-3{stroke:#7890aa!important;stroke-dasharray:18 12!important}
html[data-style-case="dark-ai-city"] [data-layout-id="kpi-scorecards"] .diagram-node-bg{background:rgba(17,29,44,.88)!important;border-color:rgba(63,208,232,.14)!important;box-shadow:0 16px 34px rgba(0,0,0,.16)!important;backdrop-filter:none}
html[data-style-case="dark-ai-city"] [data-layout-id="strategic-priorities"] .content-priority-card .diagram-node-bg{background:rgba(17,29,44,.88)!important;border-color:rgba(63,208,232,.15)!important;box-shadow:0 18px 40px rgba(0,0,0,.16)!important}
html[data-style-case="dark-ai-city"] [data-layout-id="timeline-milestones"] .diagram-node-bg{background:rgba(17,29,44,.80)!important;border-color:rgba(63,208,232,.12)!important;box-shadow:0 16px 40px rgba(0,0,0,.14)!important;backdrop-filter:none}
html[data-style-case="dark-ai-city"] [data-layout-id="timeline-milestones"] .timeline-milestone{background:rgba(17,29,44,.86)!important;border:1px solid rgba(63,208,232,.13)!important;border-radius:14px!important;box-shadow:0 12px 26px rgba(0,0,0,.14)!important}
html[data-style-case="dark-ai-city"] [data-layout-id="timeline-milestones"] .timeline-milestone>p{color:#9fb0c2!important}
html[data-style-case="dark-ai-city"] [data-layout-id="org-chart"] .diagram-node-bg{background:rgba(17,29,44,.86)!important;border-color:rgba(63,208,232,.15)!important;box-shadow:0 12px 28px rgba(0,0,0,.14)!important;backdrop-filter:none}
html[data-style-case="dark-ai-city"] [data-layout-id="org-chart"] .org-note{color:#dce5ee!important;opacity:1!important}
html[data-style-case="dark-ai-city"] [data-layout-id="org-chart"] .org-note .diagram-node-bg{background:rgba(63,208,232,.075)!important;border:1px solid rgba(63,208,232,.20)!important;box-shadow:none!important}
html[data-style-case="dark-ai-city"] [data-layout-id="org-chart"] .org-note>span{color:#dce5ee!important;opacity:1!important;font-size:36px!important;font-weight:600!important}
html[data-style-case="dark-ai-city"] [data-layout-id="highlight-callout"] .statement-chart-panel .diagram-node-bg,html[data-style-case="dark-ai-city"] [data-layout-id="highlight-callout"] .statement-callout .diagram-node-bg{background:rgba(17,29,44,.88)!important;border-color:rgba(63,208,232,.15)!important;box-shadow:0 16px 36px rgba(0,0,0,.16)!important}
html[data-style-case="dark-ai-city"] [data-layout-id="quote-focus"] .diagram-node-bg{background:rgba(17,29,44,.82)!important;border-color:rgba(63,208,232,.12)!important;box-shadow:0 16px 40px rgba(0,0,0,.16)!important;backdrop-filter:blur(4px)}
html[data-style-case="dark-ai-city"] :is(.module-number,.sequence-number,.metric-strip-value,.metric-panel-value){color:#b8e3ea!important;text-shadow:none!important;filter:none!important}
html[data-style-case="dark-ai-city"] [data-layout-id="process-flow"] .sequence-number{color:#3fd0e8!important;text-shadow:none!important;filter:none!important}
html[data-style-case="dark-ai-city"] [data-layout-id="dashboard-overview"] .metric-value{color:#3fd0e8!important;text-shadow:none!important;filter:none!important}
""",
    },
    "dark-city-network-report": {
        "style_case_source": "prompt_system/style_cases/hero-fullbleed.dark-city-network-report.yaml",
        "base_theme": "brand-editorial",
        "story": "night-cooling-network",
        "layouts": [
            "hero-fullbleed",
            "toc-3-vertical",
            "stats-3-row",
            "before-after",
            "comparison-table",
            "chapter-opener",
        ],
        "content": {
            "cover-bottom-title": "城市降溫網路報告",
            "cover-bottom-subtitle": "把夜間溫度、遮蔭與人流串成一套可驗證的高溫韌性決策",
            "cover-bottom-meta": "TREND REPORT · TAIWAN / TAIPEI",
        },
        "css": r"""
html[data-style-case="dark-city-network-report"]{--bg:#091525;--surface:#10253a;--text:#fff;--muted:#d9e2ee;--accent:#75bfe8;--support-accent:#d4af7e}
html[data-style-case="dark-city-network-report"] .slide{background-color:#091525;background-image:radial-gradient(circle at 88% 18%,rgba(117,191,232,.14),transparent 30%),linear-gradient(118deg,transparent 0 58%,rgba(212,175,126,.055) 58% 58.18%,transparent 58.18%),linear-gradient(rgba(117,191,232,.038) 1px,transparent 1px),linear-gradient(90deg,rgba(117,191,232,.038) 1px,transparent 1px);background-size:100% 100%,100% 100%,54px 54px,54px 54px}
html[data-style-case="dark-city-network-report"] .cover-media-field,html[data-style-case="dark-city-network-report"] .cover-bottom-scrim{display:none!important}
html[data-style-case="dark-city-network-report"] .cover-bottom-title{left:106px!important;top:482px!important;max-width:1180px!important;font:800 112px/1 var(--font-display)!important;letter-spacing:-.05em;color:#fff;text-shadow:none}
html[data-style-case="dark-city-network-report"] .cover-bottom-title:after{content:"";display:block;width:720px;height:4px;margin-top:32px;background:linear-gradient(90deg,#d4af7e 0 24%,#75bfe8 24% 100%)}
html[data-style-case="dark-city-network-report"] .cover-bottom-subtitle{left:110px!important;top:800px!important;max-width:1260px!important;font:540 36px/1.42 var(--font-body)!important;letter-spacing:.04em;color:#b9d8eb}
html[data-style-case="dark-city-network-report"] .cover-bottom-meta{left:102px!important;top:905px!important;font:750 36px/1 var(--font-mono)!important;letter-spacing:.18em;color:#e8f3ff}
html[data-style-case="dark-city-network-report"] .cover-logo{left:1682px!important;top:60px!important;width:158px!important;height:100px!important}
html[data-style-case="dark-city-network-report"] .cover-logo .diagram-node-bg{background:rgba(9,21,37,.68)!important;border-color:rgba(117,191,232,.65)!important;box-shadow:0 0 34px rgba(117,191,232,.16)!important;backdrop-filter:blur(8px)}
html[data-style-case="dark-city-network-report"] .slide:not([data-layout-id="hero-fullbleed"]){--bg:#f1f4f6;--surface:#fff;--text:#152132;--muted:#526173;--accent:#2c7098;--support-accent:#c68f54;--surface-text:#152132;--surface-muted:#526173;--surface-accent-ink:#245d7c;background-color:#f1f4f6;background-image:radial-gradient(circle at 92% 12%,rgba(44,112,152,.10),transparent 27%),linear-gradient(rgba(44,112,152,.036) 1px,transparent 1px),linear-gradient(90deg,rgba(44,112,152,.036) 1px,transparent 1px);background-size:100% 100%,58px 58px,58px 58px;color:#152132}
html[data-style-case="dark-city-network-report"] .slide:not([data-layout-id="hero-fullbleed"]) .prod-title{color:#111827;-webkit-text-fill-color:#111827;text-shadow:none}
html[data-style-case="dark-city-network-report"] .slide:not([data-layout-id="hero-fullbleed"]) .diagram-node-bg{background:rgba(255,255,255,.78)!important;border-color:rgba(21,33,50,.12)!important;box-shadow:0 16px 38px rgba(28,48,78,.085)!important;backdrop-filter:blur(8px)}
html[data-style-case="dark-city-network-report"] [data-layout-id="toc-3-vertical"] .diagram-node-bg{border-left:5px solid #2c7098!important}
html[data-style-case="dark-city-network-report"] [data-layout-id="stats-3-row"] .diagram-node-bg{background:#eef3f6 linear-gradient(155deg,rgba(255,255,255,.92),rgba(230,238,243,.76))!important;border-top:4px solid #c68f54!important}
html[data-style-case="dark-city-network-report"] [data-layout-id="stats-3-row"] .metric-eyebrow,html[data-style-case="dark-city-network-report"] [data-layout-id="chapter-opener"] .chapter-label{color:#245d7c!important}
html[data-style-case="dark-city-network-report"] [data-layout-id="before-after"] .diagram-node:last-of-type .diagram-node-bg{background:#194c6a linear-gradient(145deg,#2c7098,#194c6a)!important}
html[data-style-case="dark-city-network-report"] [data-layout-id="before-after"] .after :is(.compare-kicker,.compare-title,.compare-subtitle,li,li span,li b){color:#fff!important}
html[data-style-case="dark-city-network-report"] [data-layout-id="comparison-table"] .comparison-table-row:nth-child(odd){background:rgba(198,143,84,.12)}
html[data-style-case="dark-city-network-report"] [data-layout-id="chapter-opener"] .chapter-number-bg{color:rgba(44,112,152,.10)!important}
""",
    },
    "clinical-evidence-atlas": {
        "style_case_source": "prompt_system/style_cases/cover-center-title-edge-decor.clinical-evidence-atlas.yaml",
        "base_theme": "brand-editorial",
        "story": "night-cooling-network",
        "layouts": [
            "cover-center-title-edge-decor",
            "toc-4-panel-grid",
            "before-after",
            "stats-3-row",
            "pyramid",
            "split-comparison",
            "process-flow",
            "highlight-callout",
            "timeline-milestones",
            "cards-1-plus-3",
            "kpi-scorecards",
            "cards-1-plus-4",
            "recommendation-stack",
            "cycle-hub-6",
            "strategic-priorities",
            "title-center",
        ],
        "content": {
            "cover-center-title": "臨床證據圖譜",
            "cover-center-subtitle": "把療效、風險、適用條件與成熟度放進同一條可追溯路徑",
            "cover-center-speaker": "CLINICAL EVIDENCE ATLAS",
            "cover-center-org": "ACADEMIC REVIEW · 2026",
        },
        "css": r"""
html[data-style-case="clinical-evidence-atlas"]{--bg:#f5f8fa;--surface:#fff;--text:#17343d;--muted:#58707a;--accent:#0b7a75;--support-accent:#d96c5f;--surface-text:#17343d;--surface-muted:#58707a;--accent-ink:#0b6c68;--surface-accent-ink:#0b6c68;--accent-text:#fff}
html[data-style-case="clinical-evidence-atlas"] .slide{color:#17343d;background-color:#f5f8fa;background-image:linear-gradient(rgba(11,122,117,.028) 1px,transparent 1px),linear-gradient(90deg,rgba(11,122,117,.028) 1px,transparent 1px),radial-gradient(circle at 88% 12%,rgba(11,122,117,.08),transparent 25%);background-size:64px 64px,64px 64px,100% 100%;box-shadow:inset 18px 0 0 #0b7a75}
html[data-style-case="clinical-evidence-atlas"] .prod-title{font-family:var(--font-heading);font-size:68px;line-height:1.08;letter-spacing:-.045em;color:#17343d!important;-webkit-text-fill-color:#17343d!important;text-shadow:none!important}
html[data-style-case="clinical-evidence-atlas"] .prod-title:after{width:176px;height:5px;margin-top:4px;background:#0b7a75!important}
html[data-style-case="clinical-evidence-atlas"] .prod-subtitle{font-size:36px!important;line-height:1.35;color:#58707a!important}
html[data-style-case="clinical-evidence-atlas"] [data-edit-kind="text"],html[data-style-case="clinical-evidence-atlas"] [data-edit-layer="text"]{text-shadow:none!important;filter:none!important;mix-blend-mode:normal!important}
html[data-style-case="clinical-evidence-atlas"] .diagram-node-bg{background:rgba(255,255,255,.94)!important;border:1px solid rgba(23,52,61,.16)!important;border-radius:0!important;box-shadow:0 14px 32px rgba(23,52,61,.08)!important;backdrop-filter:none!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="cover-center-title-edge-decor"]{background-image:linear-gradient(90deg,transparent 0 68%,rgba(11,122,117,.08) 68% 100%),linear-gradient(90deg,transparent 0 74%,rgba(217,108,95,.16) 74% 74.4%,transparent 74.4%),linear-gradient(rgba(11,122,117,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(11,122,117,.025) 1px,transparent 1px);background-size:100% 100%,100% 100%,64px 64px,64px 64px}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-edge-decor,html[data-style-case="clinical-evidence-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-logo{display:none!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-area{left:0!important;top:0!important;width:1728px!important;height:888px!important;display:flex!important;flex-direction:column!important;align-items:flex-start!important;justify-content:center!important;text-align:left!important;padding:0 480px 0 112px!important;gap:24px!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-title{max-width:1120px!important;text-align:left!important;font:800 104px/1.03 var(--font-heading)!important;letter-spacing:-.055em!important;color:#17343d!important;-webkit-text-fill-color:#17343d!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-rule{width:244px!important;height:7px!important;background:linear-gradient(90deg,#0b7a75 0 72%,#d96c5f 72% 100%)!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-subtitle{max-width:1100px!important;text-align:left!important;font:500 42px/1.38 var(--font-body)!important;color:#58707a!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-speaker,html[data-style-case="clinical-evidence-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-org{text-align:left!important;color:#0b7a75!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-org{position:static!important;width:max-content!important;height:auto!important;max-width:1100px!important;white-space:normal!important;writing-mode:horizontal-tb!important;translate:none!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="toc-4-panel-grid"] .toc-panel-grid-card .diagram-node-bg{border-top:6px solid #0b7a75!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="toc-4-panel-grid"] .toc-side-panel .diagram-node-bg{background:#17343d!important;border-color:#17343d!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="toc-4-panel-grid"] .toc-side-panel :is(span,b,p,em){color:#fff!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="before-after"] .after .diagram-node-bg{background:#e4f1f0!important;border-top:6px solid #0b7a75!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="before-after"] .before .diagram-node-bg{background:#f1f4f5!important;border-top:6px solid #8a9ba1!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="stats-3-row"] .diagram-node-bg{border-top:7px solid #0b7a75!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="stats-3-row"] .metric-strip-item:nth-of-type(3) .diagram-node-bg{border-top-color:#d96c5f!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="pyramid"] .pyramid-layer:nth-of-type(1) .diagram-node-bg{background:#dff0ef!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="pyramid"] .pyramid-layer:nth-of-type(5) .diagram-node-bg{background:#f6e7e4!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="split-comparison"] .split-panel:last-of-type .diagram-node-bg{border-top:7px solid #0b7a75!important;background:#edf6f5!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="process-flow"] .sequence-process-node .diagram-node-bg{border-top:6px solid #0b7a75!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="process-flow"] .sequence-note .diagram-node-bg{border-left:8px solid #d96c5f!important;background:#fff6f4!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="highlight-callout"] .statement-chart-panel .diagram-node-bg{border-top:7px solid #0b7a75!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="highlight-callout"] .statement-chart-labels span{width:130px!important;translate:-33px 0;white-space:nowrap!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="highlight-callout"] .statement-callout:nth-of-type(3) .diagram-node-bg{border-left:8px solid #d96c5f!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="timeline-milestones"] .timeline-axis,html[data-style-case="clinical-evidence-atlas"] [data-layout-id="timeline-milestones"] .timeline-milestone i{background:#0b7a75!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="cards-1-plus-3"] .module-card .diagram-node-bg,html[data-style-case="clinical-evidence-atlas"] [data-layout-id="cards-1-plus-4"] .module-card .diagram-node-bg{border-top:6px solid #0b7a75!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="kpi-scorecards"] .metric-card:nth-of-type(3) .diagram-node-bg{border-top:7px solid #d96c5f!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="recommendation-stack"] .content-rec-stack .diagram-node-bg{border-left:8px solid #0b7a75!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="recommendation-stack"] .content-rationale .diagram-node-bg{border-left:8px solid #d96c5f!important;background:#fff6f4!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="cycle-hub-6"] .cycle-ring{border-color:#0b7a75!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="cycle-hub-6"] .cycle-node .diagram-node-bg{border-radius:50%!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="title-center"]{background-color:#17343d!important;background-image:linear-gradient(rgba(215,229,231,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(215,229,231,.035) 1px,transparent 1px),radial-gradient(circle at 86% 20%,rgba(11,122,117,.22),transparent 27%)!important;background-size:72px 72px,72px 72px,100% 100%!important;box-shadow:inset 18px 0 0 #0b7a75!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="title-center"] .statement-center-area{align-items:flex-start!important;text-align:left!important;padding-left:70px!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="title-center"] .statement-center-headline{color:#fff!important;-webkit-text-fill-color:#fff!important;text-shadow:none!important;text-align:left!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="title-center"] .statement-center-rule{background:linear-gradient(90deg,#0b7a75 0 72%,#d96c5f 72% 100%)!important}
html[data-style-case="clinical-evidence-atlas"] [data-layout-id="title-center"] .statement-center-support{color:#d7e5e7!important;text-align:left!important}
""",
    },
    "moonlit-herbarium-atlas": {
        "style_case_source": "prompt_system/style_cases/cover-center-title-edge-decor.moonlit-herbarium-atlas.yaml",
        "base_theme": "soft-organic-education",
        "story": "night-cooling-network",
        "layouts": [
            "cover-center-title-edge-decor",
            "toc-4-panel-grid",
            "cycle-hub-6",
            "quote-focus",
            "cards-1-plus-3",
            "timeline-milestones",
            "before-after",
            "stats-3-row",
            "comparison-table",
            "title-center",
        ],
        "content": {
            "cover-center-title": "讓城市的夜裡，仍有花粉移動",
            "cover-center-subtitle": "把屋頂、陽台、校園與街角花期串成一條可被真正使用的微棲地",
            "cover-center-speaker": "MOONLIT HERBARIUM",
            "cover-center-org": "FIELD NOTE · 2026",
        },
        "text_replacements": {
            "標出午夜後熱點": "標出午夜熱點",
            "確認必要夜間路徑": "確認夜間路徑",
            "組合三種微型介入": "組合三種介入",
            "完成小區可逆試驗": "完成可逆試驗",
            "比較溫度與行為": "比較溫度行為",
            "移往下一條路徑": "移往下一路徑",
        },
        "css": r"""
html[data-style-case="moonlit-herbarium-atlas"]{--bg:#f4ebdd;--surface:#f4ebdd;--text:#173f3a;--muted:#5f716c;--accent:#d9563f;--support-accent:#2f7467;--moonlit-plate:__MOONLIT_PLATE__}
html[data-style-case="moonlit-herbarium-atlas"] .slide{background:#f4ebdd;color:#173f3a}
html[data-style-case="moonlit-herbarium-atlas"] .prod-title{color:#173f3a!important;-webkit-text-fill-color:#173f3a!important;text-shadow:none!important}
html[data-style-case="moonlit-herbarium-atlas"] .diagram-node-bg{background:transparent!important;border:0!important;border-radius:0!important;box-shadow:none!important}
html[data-style-case="moonlit-herbarium-atlas"] .diagram-node{border-radius:0!important}
html[data-style-case="moonlit-herbarium-atlas"] .diagram-node :is(h2,h3,h4,p,span,b,em){color:#173f3a!important;text-shadow:none!important}
html[data-style-case="moonlit-herbarium-atlas"] :is(.module-number,.sequence-number,.metric-strip-value,.metric-panel-value){color:#d9563f!important;text-shadow:none!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cover-center-title-edge-decor"]{background-color:#102e2b;background-image:linear-gradient(90deg,#102e2b 0 53%,rgba(16,46,43,.96) 57%,rgba(16,46,43,.10) 100%),var(--moonlit-plate);background-position:center,100% 36%;background-size:100% 100%,900px 1280px;background-repeat:no-repeat}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-edge-decor{display:none!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-area{align-items:flex-start!important;text-align:left!important;left:96px!important;width:900px!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-title{max-width:850px!important;font-weight:800!important;color:#f4ebdd!important;text-align:left!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-subtitle{max-width:820px!important;color:#ccd8d2!important;text-align:left!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-speaker,html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-org{color:#f1bd4a!important;text-align:left!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-logo,html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-logo *{display:none!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-logo :is(b,span){color:#fff7e8!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="toc-4-panel-grid"] .toc-side-panel :is(span,b,p,em){color:#fff7e8!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="toc-4-panel-grid"] .toc-side-panel>b{font-size:52px!important;letter-spacing:-.06em!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cycle-hub-6"] .cycle-node .diagram-node-body{letter-spacing:-.20em!important;text-align:center!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cards-1-plus-3"] .module-card>p{left:24px!important;right:24px!important;letter-spacing:-.02em!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="timeline-milestones"] .timeline-milestone>b{letter-spacing:-.10em!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="before-after"] .after .diagram-node-bg{background:#173f3a!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="before-after"] .compare-title{left:48px!important;right:48px!important;font-size:48px!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="before-after"] .after :is(h2,h3,p,li,span,b,strong,em){color:#f4ebdd!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="comparison-table"] .header.recommended{color:#fff7e8!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="comparison-table"] .recommended:not(.header){color:#173f3a!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="title-center"]{background-color:#102e2b;background-image:linear-gradient(90deg,#102e2b 0 56%,rgba(16,46,43,.92) 69%,rgba(16,46,43,.16) 100%),var(--moonlit-plate);background-position:center,100% 45%;background-size:100% 100%,820px 1180px;background-repeat:no-repeat}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="title-center"] .statement-center-headline{color:#f4ebdd!important;-webkit-text-fill-color:#f4ebdd!important;text-shadow:none!important}
html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="title-center"] .statement-center-support{color:#ccd8d2!important}
""".replace("__MOONLIT_PLATE__", MOONLIT_BOTANICAL_PLATE_URL),
    },
}

PRESET_DEMO_PROFILES.setdefault("signal-route-atlas", {
    "style_case_source": "prompt_system/style_cases/cover-center-title-edge-decor.signal-route-atlas.yaml",
    "base_theme": "product-strategy-signal",
    "story": "night-cooling-network",
    "layouts": ["cover-center-title-edge-decor", "toc-5-panel-rows", "cards-1-plus-4", "comparison-table", "process-flow", "matrix-4quadrant", "timeline-milestones", "kpi-scorecards", "title-center"],
    "content": {"cover-center-title": "訊號軌道路線圖", "cover-center-subtitle": "把來源、證據、實驗與決策回寫放進同一條可追溯路徑", "cover-center-speaker": "SIGNAL ROUTE ATLAS", "cover-center-org": "DECISION SYSTEM · 2026"},
    "css": r"""
html[data-style-case="signal-route-atlas"]{--bg:#F4F1E9;--surface:#FFFFFF;--text:#17212B;--muted:#5C6770;--accent:#C94F18;--support-accent:#2B7479;--surface-text:#17212B;--surface-muted:#5C6770;--accent-ink:#A53E16;--surface-accent-ink:#A53E16;--accent-text:#FFFFFF}
html[data-style-case="signal-route-atlas"] .slide{color:#17212B;background-color:#F4F1E9;background-image:linear-gradient(rgba(23,33,43,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(23,33,43,.035) 1px,transparent 1px),radial-gradient(circle at 88% 16%,rgba(43,116,121,.09),transparent 26%);background-size:64px 64px,64px 64px,100% 100%}
html[data-style-case="signal-route-atlas"] .prod-title{color:#17212B!important;-webkit-text-fill-color:#17212B!important;text-shadow:none!important}
html[data-style-case="signal-route-atlas"] .diagram-node-bg{background:rgba(255,255,255,.76)!important;border:1px solid rgba(23,33,43,.15)!important;border-radius:4px!important;box-shadow:0 12px 28px rgba(23,33,43,.08)!important}
html[data-style-case="signal-route-atlas"] .cover-edge-decor,html[data-style-case="signal-route-atlas"] .cover-logo{display:none!important}
""",
})

PRESET_DEMO_PROFILES.setdefault("ai-operations-signal", {
    "style_case_source": "prompt_system/style_cases/cover-center-title-edge-decor.ai-operations-signal.yaml",
    "base_theme": "dark-circuit",
    "story": "night-cooling-network",
    "layouts": ["cover-center-title-edge-decor", "toc-5-panel-rows", "process-flow", "matrix-4quadrant", "kpi-scorecards", "cards-1-plus-4", "comparison-table", "timeline-milestones", "before-after", "title-center"],
    "content": {"cover-center-title": "把 AI，接進真正的工作", "cover-center-subtitle": "從個人試用走向可治理、可量測、可交接，也可撤回的團隊工作方法", "cover-center-speaker": "AI OPERATIONS PLAYBOOK", "cover-center-org": "WORK SYSTEM · 2026"},
    "css": r"""
html[data-style-case="ai-operations-signal"]{--bg:#101912;--surface:#162219;--text:#F2F5E9;--muted:#9FB0A0;--accent:#C8F169;--support-accent:#59A7FF;--surface-text:#F2F5E9;--surface-muted:#AEBEAF;--accent-ink:#C8F169;--surface-accent-ink:#C8F169;--accent-text:#101912}
html[data-style-case="ai-operations-signal"] .slide{color:#F2F5E9;background-color:#101912;background-image:linear-gradient(rgba(200,241,105,.026) 1px,transparent 1px),linear-gradient(90deg,rgba(200,241,105,.026) 1px,transparent 1px),radial-gradient(circle at 88% 18%,rgba(89,167,255,.105),transparent 27%),radial-gradient(circle at 10% 86%,rgba(200,241,105,.075),transparent 24%);background-size:72px 72px,72px 72px,100% 100%,100% 100%}
html[data-style-case="ai-operations-signal"] [data-edit-kind="text"],html[data-style-case="ai-operations-signal"] [data-edit-layer="text"]{text-shadow:none!important;filter:none!important;mix-blend-mode:normal!important}
html[data-style-case="ai-operations-signal"] .prod-title{color:#F2F5E9!important;-webkit-text-fill-color:#F2F5E9!important;letter-spacing:-.035em!important}
html[data-style-case="ai-operations-signal"] .prod-subtitle{color:#9FB0A0!important}
html[data-style-case="ai-operations-signal"] .diagram-node-bg{background:rgba(22,34,25,.92)!important;border:1px solid rgba(200,241,105,.18)!important;border-radius:6px!important;box-shadow:0 14px 34px rgba(0,0,0,.16)!important;backdrop-filter:none!important}
html[data-style-case="ai-operations-signal"] .cover-edge-decor,html[data-style-case="ai-operations-signal"] .cover-logo{display:none!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="cover-center-title-edge-decor"]{background-image:linear-gradient(90deg,transparent 0 13.8%,rgba(89,167,255,.18) 14% 14.18%,transparent 14.35% 85.65%,rgba(200,241,105,.22) 85.82% 86%,transparent 86.2%),linear-gradient(transparent 0 87.5%,rgba(200,241,105,.11) 87.7% 87.92%,transparent 88.12%),radial-gradient(circle at 50% 50%,rgba(200,241,105,.07),transparent 42%),linear-gradient(rgba(200,241,105,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(200,241,105,.025) 1px,transparent 1px);background-size:100% 100%,100% 100%,100% 100%,72px 72px,72px 72px}
html[data-style-case="ai-operations-signal"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-area{left:0!important;top:0!important;width:1728px!important;height:var(--prod-frame-height)!important;align-items:center!important;justify-content:center!important;text-align:center!important;padding:0!important;gap:24px!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="cover-center-title-edge-decor"] :is(.cover-center-title,.cover-center-subtitle,.cover-center-speaker,.cover-center-org){text-align:center!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-org{position:absolute!important;left:864px!important;top:538px!important;translate:-50% 0!important;width:max-content!important;height:max-content!important;writing-mode:horizontal-tb!important;text-orientation:mixed!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="toc-5-panel-rows"] :is(.toc-side-panel,.toc-wide-panel){background:#C8F169!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="toc-5-panel-rows"] :is(.toc-side-panel,.toc-wide-panel) .diagram-node-bg{background:#C8F169!important;border-color:#C8F169!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="toc-5-panel-rows"] :is(.toc-side-panel,.toc-wide-panel) :is(span,b,p,em){color:#101912!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="comparison-table"] .compare-table-cell.header.recommended{background:#C8F169!important;color:#101912!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-title{max-width:1120px!important;font:900 112px/1.03 var(--font-heading)!important;color:#F2F5E9!important;-webkit-text-fill-color:#F2F5E9!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-rule{width:260px!important;height:7px!important;background:linear-gradient(90deg,#C8F169 0 64%,#59A7FF 64% 100%)!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="toc-5-panel-rows"] .diagram-node-bg{border-bottom:2px solid rgba(200,241,105,.24)!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="process-flow"] .sequence-process-node .diagram-node-bg{background:transparent!important;border:0!important;border-top:3px solid #C8F169!important;border-bottom:1px solid rgba(200,241,105,.22)!important;border-radius:0!important;box-shadow:none!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="process-flow"] :is(.sequence-process-node.node-2,.sequence-process-node.node-4,.sequence-process-node.node-6) .diagram-node-bg{border-top-color:#59A7FF!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="kpi-scorecards"] .metric-kpi-card .diagram-node-bg{background:transparent!important;border:0!important;border-top:7px solid #C8F169!important;border-bottom:1px solid rgba(200,241,105,.22)!important;border-radius:0!important;box-shadow:none!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="kpi-scorecards"] :is(.metric-kpi-card.card-2,.metric-kpi-card.card-4) .diagram-node-bg{border-top-color:#59A7FF!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="cards-1-plus-4"] .module-card .diagram-node-bg{border-left:8px solid #C8F169!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="cards-1-plus-4"] .module-card:nth-of-type(even) .diagram-node-bg{border-left-color:#59A7FF!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="cards-1-plus-4"] .module-card .diagram-node-bg{box-shadow:none!important;background:rgba(22,34,25,.72)!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="matrix-4quadrant"] .matrix-card .diagram-node-bg{background:rgba(22,34,25,.58)!important;box-shadow:none!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="timeline-milestones"] .sequence-timeline .diagram-node-bg{background:transparent!important;border:0!important;box-shadow:none!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="comparison-table"] .compare-table .diagram-node-bg{border-color:rgba(200,241,105,.18)!important;border-radius:0!important;background:rgba(22,34,25,.58)!important;box-shadow:none!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="timeline-milestones"] :is(.timeline-axis,.timeline-milestone i){background:#C8F169!important;border-radius:2px!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="before-after"] .before .diagram-node-bg{background:rgba(159,176,160,.07)!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="before-after"] .after .diagram-node-bg{background:rgba(89,167,255,.09)!important;border-color:rgba(89,167,255,.34)!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="title-center"] .statement-center-headline{color:#F2F5E9!important;-webkit-text-fill-color:#F2F5E9!important;text-align:center!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="title-center"] .statement-center-rule{background:linear-gradient(90deg,#C8F169 0 68%,#59A7FF 68% 100%)!important}
html[data-style-case="ai-operations-signal"] [data-layout-id="title-center"] .statement-center-support{color:#9FB0A0!important;text-align:center!important}
""",
})


PRESET_DEMO_PROFILES.setdefault("scent-veil-launch", {
    "style_case_source": "prompt_system/demos/html-theme-lab-extensions.json#scent-veil-launch",
    "base_theme": "brand-editorial",
    "story": "scent-launch-ritual",
    "layouts": ["cover-center-title-edge-decor", "toc-4-panel-grid", "cards-1-plus-4", "cycle-hub-6", "kpi-scorecards", "before-after", "timeline-milestones", "title-center"],
    "content": {"cover-center-title": "香氣薄霧發表誌", "cover-center-subtitle": "以一條可編輯的感官線索串起品牌、體驗與上市節奏", "cover-center-speaker": "SCENT VEIL", "cover-center-org": "EDITORIAL LAUNCH · 2026"},
    "css": r"""
html[data-style-case="scent-veil-launch"] .slide{background-color:#FAF4F6}
""",
})

PRESET_DEMO_PROFILES.setdefault("folio-signal-ledger", {
    "style_case_source": "prompt_system/style_cases/cover-center-title-edge-decor.folio-signal-ledger.yaml",
    "base_theme": "product-strategy-signal",
    "story": "ai-workflow-adoption",
    "layouts": ["cover-center-title-edge-decor", "toc-4-panel-rows", "strategic-priorities", "before-after", "kpi-scorecards", "process-flow", "quote-focus", "title-center"],
    "content": {"cover-center-title": "AI，不該只停在對話框", "cover-center-subtitle": "NEXUS ONE 把任務、資料、Agent 與審核收進同一條可治理工作流", "cover-center-speaker": "NEXUS ONE", "cover-center-org": "CONCEPT PRODUCT · 2026"},
    "css": r"""
html[data-style-case="folio-signal-ledger"]{--bg:#F6F1E7;--surface:#FFFDF7;--text:#1F3140;--muted:#66717A;--accent:#B84B32;--support-accent:#1F7B73;--surface-text:#1F3140;--surface-muted:#66717A;--accent-ink:#963A29;--surface-accent-ink:#963A29;--accent-text:#FFFDF7}
html[data-style-case="folio-signal-ledger"] .slide{color:#1F3140;background-color:#F6F1E7;background-image:linear-gradient(rgba(31,49,64,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(31,49,64,.035) 1px,transparent 1px),radial-gradient(circle at 90% 10%,rgba(31,123,115,.08),transparent 23%),radial-gradient(circle at 6% 88%,rgba(184,75,50,.055),transparent 18%);background-size:64px 64px,64px 64px,100% 100%,100% 100%}
html[data-style-case="folio-signal-ledger"] .slide::before{content:"";position:absolute;left:74px;top:72px;bottom:72px;width:3px;background:#B84B32;opacity:.92;pointer-events:none;z-index:0}
html[data-style-case="folio-signal-ledger"] .slide::after{content:"";position:absolute;left:62px;top:92px;width:27px;height:27px;border:1px solid rgba(31,123,115,.48);box-sizing:border-box;pointer-events:none;z-index:0}
html[data-style-case="folio-signal-ledger"] .content{position:relative;z-index:1}
html[data-style-case="folio-signal-ledger"] [data-edit-kind="text"],html[data-style-case="folio-signal-ledger"] [data-edit-layer="text"]{text-shadow:none!important;filter:none!important;mix-blend-mode:normal!important}
html[data-style-case="folio-signal-ledger"] .prod-title{color:#1F3140!important;-webkit-text-fill-color:#1F3140!important;letter-spacing:-.035em!important}
html[data-style-case="folio-signal-ledger"] .prod-subtitle{color:#66717A!important;letter-spacing:-.012em!important}
html[data-style-case="folio-signal-ledger"] .diagram-node-bg{background:rgba(255,253,247,.86)!important;border:0!important;border-top:3px solid rgba(31,49,64,.86)!important;border-left:1px solid rgba(31,49,64,.18)!important;border-radius:0!important;box-shadow:0 10px 24px rgba(31,49,64,.07)!important}
html[data-style-case="folio-signal-ledger"] .cover-edge-decor{display:none!important}html[data-style-case="folio-signal-ledger"] .cover-logo{display:none!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="cover-center-title-edge-decor"]:not([data-composition-variant="centered-signal-hero"]) .cover-center-area{left:154px!important;top:116px!important;width:1220px!important;height:650px!important;align-items:flex-start!important;justify-content:center!important;text-align:left!important;padding:0!important;gap:24px!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="cover-center-title-edge-decor"]:not([data-composition-variant="centered-signal-hero"]) :is(.cover-center-title,.cover-center-subtitle,.cover-center-speaker,.cover-center-org){text-align:left!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="cover-center-title-edge-decor"]:not([data-composition-variant="centered-signal-hero"]) .cover-center-title{left:740px!important;max-width:1120px!important;font:900 110px/1.04 var(--font-heading)!important;color:#1F3140!important;-webkit-text-fill-color:#1F3140!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-rule{width:260px!important;height:7px!important;background:linear-gradient(90deg,#B84B32 0 62%,#1F7B73 62% 100%)!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="cover-center-title-edge-decor"]:not([data-composition-variant="centered-signal-hero"]) .cover-center-subtitle{width:880px!important;max-width:880px!important;font-size:42px!important;line-height:1.28!important;color:#66717A!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-speaker{margin-top:32px!important;color:#B84B32!important;letter-spacing:.12em!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-org{color:#1F7B73!important;letter-spacing:.08em!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="toc-4-panel-rows"] .toc-side-panel{background:#1F3140!important;color:#FFFDF7!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="toc-4-panel-rows"] .toc-side-panel .diagram-node-bg{background:#1F3140!important;border:0!important;border-right:8px solid #B84B32!important;box-shadow:none!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="toc-4-panel-rows"] .toc-side-panel :is(span,b,p,em){color:#FFFDF7!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="toc-4-panel-rows"] .toc-panel-row .diagram-node-bg{border-top:0!important;border-bottom:1px solid rgba(31,49,64,.22)!important;border-left:8px solid #B84B32!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="toc-4-panel-rows"] .toc-panel-row:nth-of-type(even) .diagram-node-bg{border-left-color:#1F7B73!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="strategic-priorities"] .content-priority-card .diagram-node-bg{border-top:8px solid #B84B32!important;box-shadow:none!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="strategic-priorities"] .content-impact-note .diagram-node-bg{background:transparent!important;border-top:0!important;border-bottom:2px solid #1F7B73!important;box-shadow:none!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="before-after"] .before .diagram-node-bg{background:rgba(255,253,247,.58)!important;border-top-color:#66717A!important;box-shadow:none!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="before-after"] .after .diagram-node-bg{background:rgba(255,253,247,.92)!important;border-top-color:#1F7B73!important;border-left:8px solid #1F7B73!important;box-shadow:0 12px 28px rgba(31,123,115,.08)!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="before-after"] .compare-rail-line{background:#B84B32!important;width:3px!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="kpi-scorecards"] .metric-kpi-card .diagram-node-bg{background:transparent!important;border-top:7px solid #B84B32!important;border-bottom:1px solid rgba(31,49,64,.22)!important;box-shadow:none!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="kpi-scorecards"] .metric-kpi-card.card-2 .diagram-node-bg,html[data-style-case="folio-signal-ledger"] [data-layout-id="kpi-scorecards"] .metric-kpi-card.card-4 .diagram-node-bg{border-top-color:#1F7B73!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="kpi-scorecards"] .metric-takeaway .diagram-node-bg{background:#1F3140!important;border:0!important;border-left:8px solid #B84B32!important;box-shadow:none!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="kpi-scorecards"] .metric-takeaway :is(span,b,p,em){color:#FFFDF7!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="process-flow"] .sequence-process-node .diagram-node-bg{background:rgba(255,253,247,.5)!important;border:0!important;border-top:5px solid #B84B32!important;border-bottom:1px solid rgba(31,49,64,.22)!important;border-radius:0!important;box-shadow:none!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="process-flow"] :is(.sequence-process-node.node-2,.sequence-process-node.node-4) .diagram-node-bg{border-top-color:#1F7B73!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="process-flow"] .sequence-process-connectors path{stroke:#1F7B73!important;stroke-width:3!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="quote-focus"] .statement-quote{border-left:8px solid #B84B32!important;color:#1F3140!important;background:transparent!important;padding-left:54px!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="quote-focus"] .quote-attribution{color:#1F7B73!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="title-center"]{background:#1F3140!important;background-image:linear-gradient(90deg,#1F3140 0 56%,rgba(31,49,64,.95) 69%,rgba(31,49,64,.2) 100%),linear-gradient(rgba(255,253,247,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,253,247,.035) 1px,transparent 1px)!important;background-size:100% 100%,64px 64px,64px 64px!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="title-center"] .statement-center-headline{color:#FFFDF7!important;-webkit-text-fill-color:#FFFDF7!important;text-shadow:none!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="title-center"] .statement-center-support{color:#D8E3DE!important}
html[data-style-case="folio-signal-ledger"] [data-layout-id="title-center"] .statement-center-rule{background:linear-gradient(90deg,#B84B32 0 68%,#1F7B73 68% 100%)!important}
""",
})
PRESET_DEMO_PROFILES.setdefault("after-dark-veil", {
    "style_case_source": "prompt_system/style_cases/cover-center-title-edge-decor.after-dark-veil.yaml",
    "base_theme": "dark-circuit",
    "story": "night-cooling-network",
    "layouts": ["cover-center-title-edge-decor", "toc-4-panel-grid", "cards-1-plus-4", "process-flow", "kpi-scorecards", "before-after", "quote-focus", "title-center"],
    "content": {"cover-center-title": "讓靠近變得安全", "cover-center-subtitle": "在深色環境光與可編輯的玻璃表面之間，讓關係、訊號與決策保留可讀的距離", "cover-center-speaker": "AFTER DARK VEIL", "cover-center-org": "HTML PRESET · 2026"},
    "css": r"""
html[data-style-case="after-dark-veil"]{--bg:#0B0D12;--surface:#171A24;--text:#F6EFE2;--muted:#B5B0A5;--accent:#C9A45C;--support-accent:#C46B72;--surface-text:#F6EFE2;--surface-muted:#B5B0A5;--accent-ink:#F0D79A;--surface-accent-ink:#F0D79A;--accent-text:#0B0D12}
html[data-style-case="after-dark-veil"] .slide{color:#F6EFE2;background-color:#0B0D12;background-image:radial-gradient(circle at 15% 20%,rgba(201,164,92,.16),transparent 28%),radial-gradient(circle at 85% 80%,rgba(196,107,114,.12),transparent 30%),linear-gradient(135deg,#08090D,#131823 55%,#090A0D);background-size:100% 100%,100% 100%,100% 100%;box-shadow:inset 0 0 120px rgba(0,0,0,.30)}
html[data-style-case="after-dark-veil"] .content{z-index:2}
html[data-style-case="after-dark-veil"] [data-edit-kind="text"],html[data-style-case="after-dark-veil"] [data-edit-layer="text"]{text-shadow:none!important;filter:none!important;mix-blend-mode:normal!important}
html[data-style-case="after-dark-veil"] :is(.prod-title,.cover-center-title,.cover-split-title){color:#F6EFE2!important;-webkit-text-fill-color:#F6EFE2!important;letter-spacing:-.045em!important}
html[data-style-case="after-dark-veil"] .prod-subtitle{color:#B5B0A5!important}
html[data-style-case="after-dark-veil"] .diagram-node-bg{background:rgba(23,26,36,.78)!important;border:1px solid rgba(246,239,226,.14)!important;border-radius:28px!important;box-shadow:0 24px 80px rgba(0,0,0,.28),inset 0 1px rgba(246,239,226,.04)!important;backdrop-filter:blur(18px) saturate(115%)}
html[data-style-case="after-dark-veil"] .diagram-node :is(h2,h3,h4,p,span,b,em,li){color:#F6EFE2!important;text-shadow:none!important}
html[data-style-case="after-dark-veil"] .cover-edge-decor{visibility:hidden!important;opacity:0!important;pointer-events:none!important}
html[data-style-case="after-dark-veil"] .cover-logo{display:block!important;visibility:hidden!important;opacity:0!important;pointer-events:none!important}
html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-area{left:124px!important;top:108px!important;width:1320px!important;height:680px!important;align-items:flex-start!important;justify-content:center!important;text-align:left!important;padding:0!important;gap:26px!important}
html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"] :is(.cover-center-title,.cover-center-subtitle,.cover-center-speaker,.cover-center-org){text-align:left!important}
html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-title{width:1070px!important;max-width:1070px!important;height:auto!important;min-height:0!important;font:900 112px/1.04 var(--font-heading)!important;color:#F6EFE2!important;-webkit-text-fill-color:#F6EFE2!important}
html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-subtitle{width:950px!important;max-width:950px!important;height:auto!important;min-height:0!important;font:500 42px/1.38 var(--font-body)!important;color:#B5B0A5!important}
html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"] :is(.cover-center-speaker,.cover-center-org){color:#C9A45C!important;letter-spacing:.10em!important}
html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-org{position:static!important;writing-mode:horizontal-tb!important;translate:none!important;color:#C46B72!important}
html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-rule{width:300px!important;height:6px!important;background:linear-gradient(90deg,#C9A45C 0 66%,#C46B72 66% 100%)!important}
html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"]::before{content:""!important;position:absolute!important;right:-132px!important;top:62px!important;width:620px!important;height:620px!important;border:1px solid rgba(201,164,92,.20)!important;border-radius:50%!important;box-shadow:0 0 0 70px rgba(201,164,92,.025),inset 0 0 80px rgba(201,164,92,.035)!important;pointer-events:none!important;z-index:0!important}
html[data-style-case="after-dark-veil"] [data-layout-id="toc-4-panel-grid"] .toc-side-panel .diagram-node-bg{background:rgba(201,164,92,.12)!important;border-color:rgba(201,164,92,.25)!important}
html[data-style-case="after-dark-veil"] [data-layout-id="cards-1-plus-4"] .module-card .diagram-node-bg{border-left:6px solid #C9A45C!important}
html[data-style-case="after-dark-veil"] [data-layout-id="cards-1-plus-4"] .module-card:nth-of-type(even) .diagram-node-bg{border-left-color:#C46B72!important}
html[data-style-case="after-dark-veil"] [data-layout-id="process-flow"] .sequence-process-node .diagram-node-bg{border:0!important;border-top:4px solid #C9A45C!important;border-bottom:1px solid rgba(246,239,226,.14)!important;border-radius:20px!important;background:rgba(23,26,36,.62)!important;box-shadow:none!important}
html[data-style-case="after-dark-veil"] [data-layout-id="process-flow"] :is(.sequence-process-node.node-2,.sequence-process-node.node-4,.sequence-process-node.node-6) .diagram-node-bg{border-top-color:#C46B72!important}
html[data-style-case="after-dark-veil"] [data-layout-id="process-flow"] .sequence-process-connectors path{stroke:#C9A45C!important;stroke-width:3!important}
html[data-style-case="after-dark-veil"] [data-layout-id="kpi-scorecards"] .metric-kpi-card .diagram-node-bg{background:rgba(23,26,36,.58)!important;border:0!important;border-top:7px solid #C9A45C!important;border-bottom:1px solid rgba(246,239,226,.14)!important;box-shadow:none!important}
html[data-style-case="after-dark-veil"] [data-layout-id="kpi-scorecards"] :is(.metric-kpi-card.card-2,.metric-kpi-card.card-4) .diagram-node-bg{border-top-color:#C46B72!important}
html[data-style-case="after-dark-veil"] [data-layout-id="before-after"] .before .diagram-node-bg{background:rgba(181,176,165,.07)!important;border-color:rgba(181,176,165,.18)!important;box-shadow:none!important}
html[data-style-case="after-dark-veil"] [data-layout-id="before-after"] .after .diagram-node-bg{background:rgba(196,107,114,.12)!important;border-color:rgba(196,107,114,.34)!important;box-shadow:0 18px 50px rgba(196,107,114,.10)!important}
html[data-style-case="after-dark-veil"] [data-layout-id="before-after"] .compare-title{font-size:52px!important;line-height:1.18!important}
html[data-style-case="after-dark-veil"] [data-layout-id="quote-focus"] .statement-quote{border-left:7px solid #C9A45C!important;color:#F6EFE2!important;background:transparent!important;padding-left:50px!important}
html[data-style-case="after-dark-veil"] [data-layout-id="quote-focus"] .quote-attribution{color:#C46B72!important}
html[data-style-case="after-dark-veil"] [data-layout-id="title-center"]{background:#10131B!important;background-image:radial-gradient(circle at 50% 50%,rgba(201,164,92,.12),transparent 32%),radial-gradient(circle at 82% 78%,rgba(196,107,114,.10),transparent 28%),linear-gradient(135deg,#0B0D12,#171A24 56%,#0B0D12)!important;background-size:100% 100%,100% 100%,100% 100%!important}
html[data-style-case="after-dark-veil"] [data-layout-id="title-center"]::before{content:""!important;position:absolute!important;left:50%!important;top:50%!important;width:720px!important;height:720px!important;transform:translate(-50%,-50%)!important;border:1px solid rgba(246,239,226,.10)!important;border-radius:50%!important;box-shadow:0 0 0 70px rgba(196,107,114,.018),0 0 0 140px rgba(201,164,92,.014)!important;pointer-events:none!important;z-index:0!important}
html[data-style-case="after-dark-veil"] [data-layout-id="title-center"] .statement-center-headline{color:#F6EFE2!important;-webkit-text-fill-color:#F6EFE2!important;text-shadow:none!important;text-align:center!important}
html[data-style-case="after-dark-veil"] [data-layout-id="title-center"] .statement-center-rule{background:linear-gradient(90deg,#C9A45C 0 68%,#C46B72 68% 100%)!important}
html[data-style-case="after-dark-veil"] [data-layout-id="title-center"] .statement-center-support{color:#B5B0A5!important;text-align:center!important}
""",
})
PRESET_DEMO_PROFILES.setdefault("midnight-terrace-garden", {
    "style_case_source": "isolated-prototype:midnight-terrace-garden",
    "base_theme": "festive-patterned",
    "story": "circular-market",
    "layouts": ["cover-center-title-edge-decor", "cards-1-plus-3", "timeline-milestones", "title-center"],
    "content": {
        "cover-center-title": "月光菜園",
        "cover-center-subtitle": "90 天把屋頂變成社區的晚餐桌",
        "cover-center-speaker": "MOONLIT TERRACE GARDEN",
        "cover-center-org": "COMMUNITY FOOD PILOT · 2026",
    },
    "css": r"""
html[data-style-case="midnight-terrace-garden"]{--bg:#18152D;--surface:#272447;--text:#FFF8E7;--muted:#D1CBEA;--accent:#F0B84B;--support-accent:#6BD6C5;--surface-text:#FFF8E7;--surface-muted:#D1CBEA;--accent-ink:#18152D;--surface-accent-ink:#18152D;--accent-text:#18152D}
html[data-style-case="midnight-terrace-garden"] .slide{color:#FFF8E7;background:#18152D;background-image:repeating-conic-gradient(from 45deg at 50% 50%,rgba(240,184,75,.08) 0 12.5%,transparent 0 25%),radial-gradient(circle at 86% 18%,rgba(107,214,197,.14),transparent 26%);background-size:84px 84px,100% 100%}
html[data-style-case="midnight-terrace-garden"] .prod-title{color:#FFF8E7!important;-webkit-text-fill-color:#FFF8E7!important;text-shadow:none!important}
html[data-style-case="midnight-terrace-garden"] .diagram-node-bg{background:rgba(39,36,71,.88)!important;border:1px solid rgba(240,184,75,.32)!important;border-radius:2px!important;box-shadow:8px 10px 0 rgba(107,214,197,.12)!important}
html[data-style-case="midnight-terrace-garden"] .cover-edge-decor,html[data-style-case="midnight-terrace-garden"] .cover-logo{display:none!important}
html[data-style-case="midnight-terrace-garden"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-title{color:#FFF8E7!important;-webkit-text-fill-color:#FFF8E7!important;text-align:left!important}
html[data-style-case="midnight-terrace-garden"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-subtitle{color:#D1CBEA!important;text-align:left!important}
html[data-style-case="midnight-terrace-garden"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-rule{background:#F0B84B!important}
""",
})
_missing_demo_theme_definitions = set(PRESET_DEMO_PROFILES) - set(HTML_PRESET_THEME_DEFINITIONS)
if _missing_demo_theme_definitions:
    raise ValueError(
        "HTML preset demo profile references missing theme definitions: "
        f"{sorted(_missing_demo_theme_definitions)}"
    )
for _preset_id, _profile in PRESET_DEMO_PROFILES.items():
    _profile["theme_definition"] = HTML_PRESET_THEME_DEFINITIONS[_preset_id]

COVER_LAYOUTS = [
    "cover-center-title-edge-decor",
    "cover-center-title-double-frame",
    "cover-left-title-open-field",
    "cover-upper-center-stack-meta-lower-right",
    "cover-photo-frame",
    "cover-photo-frame-reverse",
    "cover-photo-overlay-block",
    "hero-fullbleed",
    "hero-fullbleed-brand-footer",
]

STRATEGY_LAYOUTS = [
    "cards-1-plus-3",
    "flow-stages-3",
    "recommendation-stack",
    "strategic-priorities",
]

RELATIONSHIP_LAYOUTS = [
    "before-after",
    "cycle-hub-6",
    "matrix-4quadrant",
    "split-comparison",
]

EVIDENCE_LAYOUTS = [
    "kpi-scorecards",
    "multi-line-chart",
    "stats-3-row",
]

SEQUENCE_LAYOUTS = [
    "gantt-roadmap",
    "process-flow",
    "timeline-milestones",
    "timeline-vertical",
]

STATEMENT_LAYOUTS = [
    "chapter-number-bg-left-title-rule",
    "highlight-callout",
    "quote-attribution-3",
    "quote-focus",
]

HTML_LAYOUT_CATALOG = load_html_layout_catalog()
HTML_DESIGN_DIALECTS = load_html_design_dialects()
HTML_ASSEMBLY_CATALOG = load_html_assembly_catalog()
HTML_DESIGN_METHOD = load_html_design_method()
COVER_LAYOUTS = filter_html_layouts(COVER_LAYOUTS, HTML_LAYOUT_CATALOG)
TOC_LAYOUTS = [
    layout_id
    for layout_id in HTML_LAYOUT_CATALOG["allowed_layout_ids"]
    if layout_id.startswith("toc-")
]
STRATEGY_LAYOUTS = filter_html_layouts(STRATEGY_LAYOUTS, HTML_LAYOUT_CATALOG)
RELATIONSHIP_LAYOUTS = filter_html_layouts(RELATIONSHIP_LAYOUTS, HTML_LAYOUT_CATALOG)
EVIDENCE_LAYOUTS = filter_html_layouts(EVIDENCE_LAYOUTS, HTML_LAYOUT_CATALOG)
SEQUENCE_LAYOUTS = filter_html_layouts(SEQUENCE_LAYOUTS, HTML_LAYOUT_CATALOG)
STATEMENT_LAYOUTS = filter_html_layouts(STATEMENT_LAYOUTS, HTML_LAYOUT_CATALOG)


STORIES: list[dict[str, Any]] = [
    {
        "id": "night-cooling-network",
        "title": "讓城市在夜裡慢慢降溫",
        "subtitle": "把街區溫度、必要路徑與維運訊號串成一套可驗證、可停止、也可擴張的高溫韌性計畫",
        "speaker": "URBAN CLIMATE FIELD LAB",
        "org": "TAIPEI · SUMMER 2026",
        "toc": [
            ("熱風險", "看見日落後仍留在必要路徑上的高溫。"),
            ("優先對象", "先保護不能繞路、也無法改變時段的人。"),
            ("介入組合", "把遮蔭、冷鋪面與維運拆成可驗收模組。"),
            ("決策循環", "讓量測結果回寫下一輪配置與資源排序。"),
            ("擴張門檻", "同時檢查降溫、使用、連續性與維運。"),
            ("常態治理", "建立跨資料、工程與社區的共同節奏。"),
        ],
        "priorities": [
            ("夜間熱點", "優先處理午夜後仍高於周邊 2°C 的街廓。", "NOW", "48%"),
            ("弱勢路徑", "連接診所、車站與市場的必要步行路線。", "NEXT", "32%"),
            ("社區維運", "把澆灌、清潔與故障回報納入既有巡檢。", "ENABLE", "20%"),
        ],
        "recommendations": [
            ("先測三個熱點", "不要一開始就鋪滿全區，先比較三種介入組合。", "NOW"),
            ("建立夜間基準", "連續兩週記錄溫度、濕度與實際停留人數。", "NOW"),
            ("邀請居民共評", "把體感、安全與噪音一起放進驗收表。", "NEXT"),
            ("達標再擴張", "連續四週通過降溫與使用率門檻才複製。", "SCALE"),
        ],
        "cycle": [
            ("偵測", "標出夜間熱點"), ("走讀", "記錄必要路徑"), ("設計", "組合微型介入"),
            ("佈建", "完成小區試驗"), ("量測", "比較溫度與行為"), ("回寫", "更新擴張條件"),
        ],
        "before": ("只看白天", "單點降溫", "設備做完就算完成", ["忽略午夜後的蓄熱", "介入位置跟著空地走", "維運成本最後才被看見"]),
        "after": ("追蹤整夜", "路徑降溫", "以使用行為判斷成效", ["比較傍晚到清晨的降溫曲線", "優先保護無法繞路的居民", "維運責任在試驗前就被確認"]),
        "matrix": [
            ("持續觀察", "暴露低、證據少，先收集更多資料。"),
            ("快速改善", "暴露高、證據強，直接進入設計。"),
            ("維持現況", "暴露低、已有替代路徑。"),
            ("優先試驗", "暴露高但介入效果仍不確定。"),
        ],
        "metrics": [
            ("-2.4°C", "午夜表面溫度", "最佳試驗街廓", "模擬值"),
            ("+38%", "夜間停留人數", "21:00–24:00", "模擬值"),
            ("620m", "連續遮蔭路徑", "連接車站與市場", "PILOT"),
            ("84%", "居民可接受度", "含噪音與安全評分", "模擬值"),
        ],
        "chart": [
            ("表面溫度", [76, 72, 66, 61, 56, 51, 47]),
            ("體感舒適", [34, 39, 46, 55, 63, 72, 81]),
            ("停留意願", [29, 35, 41, 49, 58, 68, 77]),
        ],
        "process": [
            ("盤點", "整合感測與居民回報"), ("走讀", "確認必要夜間路徑"),
            ("試作", "建立三種介入組合"), ("量測", "追蹤四週溫度與行為"),
            ("決定", "擴張、調整或停止"),
        ],
        "timeline": [
            ("JUN", "建立基準", "完成兩週夜間溫度與人流量測。"),
            ("JUL", "三區試驗", "分別測試遮蔭、水霧與冷鋪面。"),
            ("AUG", "居民共評", "補入安全、噪音與維運感受。"),
            ("SEP", "調整組合", "移除低效設備並補強連續路徑。"),
            ("OCT", "決定擴張", "僅複製達到門檻的介入組合。"),
        ],
        "quote": "城市降溫不是放更多設備，\n而是讓最需要的人走過一條更舒服的路。",
        "attribution": "URBAN CLIMATE FIELD NOTE · 07",
        "center": ("真正的韌性，是炎熱來臨時仍有選擇", "把感測資料、居民路徑與維運能力放在同一張圖上，城市才知道下一筆資源應該落在哪裡。"),
        "chapter": ("CHAPTER 04", "從單點設備走向連續路徑", "下一階段不再比較哪一台設備最涼，而是驗證整段必要路徑能否持續被使用。", "04"),
        "bio": ("林映辰", "城市氣候試驗主持人", ["把環境資料轉成可以被居民感受的介入。", "以小規模試驗降低一次性大工程風險。", "建立跨里辦、工程與社區的共同驗收語言。"], "URBAN CLIMATE · FIELD RESEARCH · SYSTEMS"),
        "closing": ("把下一個炎熱夜晚，\n變成一次可以學習的試驗。", "從一條必要路徑開始，量測、調整，再決定是否擴張。"),
        "toc_context": {
            "title": "六章推進共同決策",
            "intro": "從風險定位、優先對象到 90 天試驗與治理節奏，完整回答誰需要、做什麼、何時擴張。",
            "footer": "CONTENTS · NIGHT COOLING DECISION SYSTEM",
        },
        "layout_content": {
            "chapter-number-bg-left-title-rule": {
                "label": "01 / THE DECISION PROBLEM",
                "title": "城市最熱的地方，不一定是最該先施工的地方",
                "subtitle": "真正的優先順序必須同時看高溫暴露、無法繞行的必要路徑、受影響族群與可維運條件；否則設備只會落在最容易施工的位置。",
                "number": "01"
            },
            "dashboard-overview": {
                "title": "凌晨仍比周邊熱 2.4°C：風險集中在必要路徑",
                "subtitle": "三個試驗街區 · 21:00–03:00 連續量測 · 模擬資料",
                "kpis": [
                    ("夜間溫差", "+2.4°C", "午夜峰值"),
                    ("高暴露路徑", "620m", "車站—市場"),
                    ("連續熱夜", "11晚", "近 14 天"),
                    ("受影響居民", "2,180人", "步行 10 分鐘圈"),
                ],
                "chart": {
                    "title": "21:00–03:00 路面溫差仍在午夜後達峰值",
                    "metric": "+2.4°C",
                    "bars": [42, 56, 71, 86, 78, 64, 49],
                    "labels": ["21", "22", "23", "00", "01", "02", "03"],
                },
                "insight": (
                    "判讀",
                    "設備不是起點，必要路徑才是",
                    ["風險沿通勤與就醫動線集中", "老人與夜班工作者無法避開", "單點降溫無法形成連續保護"],
                ),
                "footnote": "本頁數值為版型與決策流程示範用模擬資料；正式使用時須補上來源、期間與量測口徑。",
            },
            "multi-line-chart": {
                "title": "降溫先出現；使用與信任第 4 週才追上",
                "labels": ["W0", "W1", "W2", "W3", "W4", "W5", "W6"],
                "series": [
                    ("降溫成效", [28, 48, 62, 72, 78, 82, 86]),
                    ("路徑使用", [31, 35, 41, 49, 61, 72, 79]),
                    ("居民信任", [24, 29, 34, 40, 52, 63, 71]),
                ],
            },
            "cards-1-plus-3": {
                "title": "第一輪只做三件事：看見、保護、維持",
                "subtitle": "每個模組都有自己的輸入、負責人與驗收條件；三者同時成立，才算形成一條可用的降溫路徑。",
                "items": [
                    ("夜間訊號", "合併固定感測、手持走讀與居民回報，找出午夜後仍未散熱，而且有人持續經過的位置。", "SIGNAL"),
                    ("連續路徑", "把車站、市場、診所與照護據點串成不中斷的步行保護帶，先服務無法改道的人。", "ROUTE"),
                    ("維運回路", "在施工前就確認澆灌、清潔、耗材、故障回報與停用條件，避免設備完成後無人承接。", "OPERATE"),
                ],
            },
            "before-after": {
                "before": (
                    "BEFORE · 單點工程",
                    "哪裡有空地，就把設備放哪裡",
                    "完工等於結案",
                    ["介入位置跟著工程方便走", "設備之間沒有連續保護", "維運問題在驗收後才出現"],
                ),
            "after": (
                "AFTER · 路徑系統",
                "先找出不能繞路的人",
                "使用與維運共同驗收",
                ["用居民必要動線決定位置", "把零散節點串成完整路徑", "通過四項門檻才進入擴張"],
            ),
        },
            "cycle-hub-6": {
                "title": "六步完成\n城市降溫決策循環",
                "subtitle": "每一輪都把量測結果寫回下一輪配置",
                "items": [
                    ("01", "偵測", "標出午夜後熱點"),
                    ("02", "走讀", "確認必要夜間路徑"),
                    ("03", "設計", "組合三種微型介入"),
                    ("04", "佈建", "完成小區可逆試驗"),
                    ("05", "量測", "比較溫度與行為"),
                    ("06", "回寫", "更新門檻與下一輪配置"),
                ],
            },
            "matrix-4quadrant": {
                "title": "不是每一個熱點，都該立刻施工",
                "axes": ("證據弱", "證據強", "暴露低", "暴露高"),
                "quadrants": [
                    ("持續觀察", "暴露低、證據少；維持感測並補做夜間走讀，暫不投入固定工程。"),
                    ("快速改善", "暴露高、證據強；直接進入設計與採購，同步確認維運人力與停用條件。"),
                    ("維持現況", "暴露低、替代路徑充足；只做基本維護，把資源留給無法繞行的位置。"),
                    ("優先試驗", "暴露高但介入成效未明；先做四週可逆試驗，通過門檻後才固化。"),
                ],
            },
            "strategic-priorities": {
                "title": "第一輪資源，先投在三條不能失敗的必要路徑",
                "subtitle": "排序同時考慮暴露人口、替代路徑、夜間使用與維運成熟度；比例代表首輪試驗資源。",
                "priorities": [
                    ("01", "醫療與照護", "串接捷運、急診與長照據點；夜間無替代路線，且高齡使用者對熱暴露最敏感。", "CRITICAL", "45%"),
                    ("02", "交通轉乘", "覆蓋車站出口、公車候車與計程車排班區；重點是縮短暴露時間並維持照明安全。", "HIGH FLOW", "35%"),
                    ("03", "民生採買", "連接市場與住宅巷口；以可拆卸遮蔭和冷鋪面先驗證尖峰前後的實際使用變化。", "PILOT", "20%"),
                ],
                "impact": "首輪不追求面積最大，而是先證明一條必要路徑能同時降溫、被使用、不中斷且有人維護。",
            },
            "process-flow": {
                "title": "90 天內，讓一條必要路徑完成一次可驗證試驗",
                "subtitle": "五個關卡各自留下基準、選址、設計、結果與決定；缺任何一項，就不能用漂亮結論跳過證據。",
                "steps": [
                    ("01", "建立基準", "連續 14 晚記錄溫度、人流、停留與居民體感，保留同時段對照街廓。"),
                    ("02", "選定路徑", "以醫療、轉乘與採買動線確認不能繞行的 500–800 公尺必要路徑。"),
                    ("03", "組合介入", "配置可逆遮蔭、冷鋪面與補水節點，並先寫出巡檢、停用與修復責任。"),
                    ("04", "四週驗證", "同步追蹤降溫、路徑使用、故障、噪音與安全感，禁止只挑最好看的數字。"),
                    ("05", "做出決定", "全數達標才複製；單項失敗先調整，重大風險則立即停止並保留紀錄。"),
                ],
                "note": "治理規則：若任一關鍵證據缺失，就回到前一關補測；工期、活動曝光或已投入成本都不能取代驗收。",
            },
            "kpi-scorecards": {
                "title": "四個門檻，同時通過才擴張",
                "subtitle": "降溫、使用、連續性與維運缺一不可；單一漂亮數字不構成決策。",
                "cards": [
                    ("-2.0°C", "午夜路面溫度", "相較同時段對照街廓", "TEMP"),
                    ("+25%", "夜間路徑使用", "21:00–24:00 行人增幅", "USE"),
                    ("≥500m", "連續保護距離", "遮蔭或降溫不得中斷", "ROUTE"),
                    ("≥80%", "居民可接受度", "含安全、噪音與維護", "TRUST"),
                ],
                "takeaway": "四項全數達標才複製；任何一項失敗，都先修正介入組合與維運方式。",
            },
            "timeline-milestones": {
                "title": "五個月份，從基準量測走到擴張決定",
                "subtitle": "每個里程碑同時寫清楚成果與去留條件，避免專案在活動、採購與會議中失焦。",
                "milestones": [
                    ("JUN", "建立夜間基準", "完成 14 晚對照量測"),
                    ("JUL", "三區同步試驗", "三種介入各有對照組"),
                    ("AUG", "居民共同評估", "補入安全、噪音與體感"),
                    ("SEP", "調整介入組合", "停用低效或難維護節點"),
                    ("OCT", "做出擴張判斷", "四項門檻必須同時通過"),
                    ("NEXT", "移往下一條路徑", "保留基準與失敗紀錄"),
                ],
            },
            "org-chart": {
                "title": "一個共同目標，三條清楚責任線",
                "root": ("夜間降溫決策小組", "統一熱點、路徑、指標與擴張門檻"),
                "children": [
                    ("資料與研究", "維護基準、異常判讀與成效口徑", "每日更新"),
                    ("工程與維運", "負責佈建、巡檢、故障與成本", "每週檢視"),
                    ("里辦與居民", "回報體感、安全、噪音與實際使用", "雙週共評"),
                ],
                "note": "共同節奏：週一看數據、週三巡檢、雙週與居民共評；同一張決策表只保留一個版本。",
            },
            "highlight-callout": {
                "title": "第 4 週出現轉折：使用、信任、維運開始同步",
                "chart": ("通過驗收門檻的綜合指數", [31, 38, 47, 55, 67, 78], ["W1", "W2", "W3", "W4", "W5", "W6"]),
                "callouts": [
                    ("01", "移動兩個遮蔭節點", "把設備從空地移回實際通勤動線後，路徑使用開始上升。"),
                    ("02", "公開故障與停用紀錄", "居民知道問題會被看見，也知道何時恢復，信任不再只靠宣傳。"),
                    ("03", "把巡檢併入既有班表", "維運不再依賴專案臨時人力，連續運作才有機會被複製。"),
                ],
            },
            "quote-focus": {
                "quote": "城市降溫不是放更多設備，\n而是讓最需要的人走過一條更舒服的路。",
                "attribution": "— URBAN CLIMATE FIELD NOTE · 07",
            },
            "title-center": {
                "headline": "先把一條路徑做對，再把一套方法做大",
                "support": "下一步：選定一條 500–800 公尺必要路徑，完成 14 晚基準、四週可逆試驗與四項共同驗收，再決定是否擴張。",
            },
        },
    },
    {
        "id": "circular-market",
        "title": "一座市場，如何停止製造垃圾",
        "subtitle": "從攤商備料、消費容器到清運時間，重畫傳統市場的循環物流",
        "speaker": "CIRCULAR MARKET COLLECTIVE",
        "org": "TAICHUNG · ZERO WASTE PILOT",
        "toc": [
            ("垃圾從哪來", "拆解包材、廚餘與一次性容器來源。"),
            ("誰在承擔", "看見攤商、清潔隊與消費者的隱性成本。"),
            ("循環節點", "建立回收、清洗、再分配的共同入口。"),
            ("誘因設計", "讓重複使用比丟棄更省時間。"),
            ("小區測試", "先用一條市場動線驗證回收率。"),
            ("擴張規則", "通過衛生與營運門檻後再增加攤位。"),
        ],
        "priorities": [
            ("共用容器", "從高頻熟食攤位建立標準尺寸與回收點。", "CORE", "50%"),
            ("廚餘分流", "把可再利用原料與一般廢棄物分開。", "NEXT", "30%"),
            ("清洗節奏", "讓收運與清洗時間貼合市場尖峰。", "ENABLE", "20%"),
        ],
        "recommendations": [
            ("先鎖定高頻品項", "選擇每日重複出現、規格相近的三種容器。", "NOW"),
            ("把回收點放進動線", "不要求消費者額外繞路或排隊。", "NOW"),
            ("清洗狀態透明", "讓攤商知道乾淨容器何時會回到手上。", "NEXT"),
            ("用週轉率擴張", "容器七日週轉達標後才加入新攤位。", "SCALE"),
        ],
        "cycle": [
            ("借用", "取用標準容器"), ("消費", "完成購買與使用"), ("歸還", "就近投入回收點"),
            ("收運", "尖峰後集中回收"), ("清洗", "完成消毒與檢查"), ("再配", "回到需要的攤商"),
        ],
        "before": ("各自處理", "一次即丟", "垃圾離開攤位就消失", ["攤商各買不同包材", "消費者找不到回收入口", "清運量持續增加"]),
        "after": ("共同循環", "容器回流", "以週轉率管理系統", ["三種標準容器覆蓋高頻品項", "回收點貼近主要出口", "清洗與再配狀態可追蹤"]),
        "matrix": [
            ("延後處理", "頻率低且替代成本高。"), ("立即標準化", "頻率高且容器規格相近。"),
            ("維持自備", "一次性需求低，已有重複使用方案。"), ("優先試驗", "垃圾量高但衛生流程仍待驗證。"),
        ],
        "metrics": [
            ("73%", "容器回收率", "四週試驗平均", "模擬值"),
            ("2.8次", "每週平均週轉", "目標為 3 次", "PILOT"),
            ("-41%", "一次性包材", "參與攤位合計", "模擬值"),
            ("18家", "參與攤商", "熟食與飲品為主", "+6"),
        ],
        "chart": [
            ("回收率", [42, 49, 55, 61, 66, 70, 73]),
            ("準時再配", [38, 45, 53, 59, 67, 72, 78]),
            ("攤商採用", [29, 34, 41, 50, 58, 64, 69]),
        ],
        "process": [
            ("盤點", "找出高頻包材"), ("標準", "縮減成三種容器"), ("佈點", "回收入口貼近動線"),
            ("週轉", "收運清洗再配"), ("擴張", "達標後加入新攤位"),
        ],
        "timeline": [
            ("W1", "盤點垃圾", "完成主要包材與廚餘來源分類。"),
            ("W2", "選定容器", "確認三種標準尺寸與衛生規格。"),
            ("W3", "小區上線", "六家攤商與兩個回收點開始運作。"),
            ("W6", "調整收運", "依尖峰時間改變清洗與再配班次。"),
            ("W10", "擴至十八家", "通過週轉與衛生門檻後擴張。"),
        ],
        "quote": "循環不是請大家更有道德，\n而是讓歸還比丟棄更順手。",
        "attribution": "CIRCULAR MARKET PRINCIPLE · 03",
        "center": ("零廢棄的起點，是一條不費力的回流路徑", "當容器、回收、清洗與再配成為同一套日常物流，市場才能真正減少一次性包材。"),
        "chapter": ("CHAPTER 03", "把垃圾問題改寫成物流問題", "當系統開始追蹤容器去了哪裡，改善就不再只靠宣導。", "03"),
        "bio": ("周以安", "循環市場營運設計師", ["將垃圾量轉成可以被管理的物流節點。", "同時驗證衛生、時間與攤商採用條件。", "以小規模週轉資料決定擴張速度。"], "CIRCULAR OPERATIONS · SERVICE DESIGN · FIELD PILOT"),
        "closing": ("下一次購買，\n讓容器記得回家的路。", "從六家攤商開始，先把一條回流路徑做順。"),
    },
    {
        "id": "coastal-sensor-mesh",
        "title": "讓海岸自己說出變化",
        "subtitle": "用低成本感測網，把零散觀察變成漁村可以採取行動的共同訊號",
        "speaker": "COASTAL SIGNAL MESH",
        "org": "EAST COAST · COMMUNITY SCIENCE",
        "toc": [
            ("觀察斷點", "找出目前靠記憶與口耳相傳的資訊。"),
            ("最小感測", "只保留會影響行動的必要指標。"),
            ("社區節點", "讓漁民、學校與研究站共同維護。"),
            ("異常判讀", "區分設備故障與真正環境變化。"),
            ("行動門檻", "把訊號連到巡查與採樣決定。"),
            ("資料回流", "讓結果回到下一輪感測配置。"),
        ],
        "priorities": [
            ("水溫異常", "辨識持續升溫與短期潮汐變動。", "SIGNAL", "46%"),
            ("溶氧下降", "提前標示養殖與近岸生態風險。", "RISK", "34%"),
            ("設備健康", "區分資料缺失、漂移與真實事件。", "ENABLE", "20%"),
        ],
        "recommendations": [
            ("先定義行動", "只量測會觸發巡查、採樣或通報的指標。", "NOW"),
            ("建立人工校驗", "每週用手持設備比較固定節點。", "NOW"),
            ("公開異常理由", "訊號被排除時也留下判讀紀錄。", "NEXT"),
            ("依事件重排節點", "把設備移向最常出現不確定性的海域。", "SCALE"),
        ],
        "cycle": [
            ("感測", "持續收集水域資料"), ("比對", "檢查鄰近節點差異"), ("判讀", "排除故障與漂移"),
            ("通報", "達門檻才發出訊號"), ("採樣", "以現場證據驗證"), ("重配", "調整節點與門檻"),
        ],
        "before": ("孤立紀錄", "看見才處理", "資料留在個人設備", ["缺少連續時間序列", "設備故障常被誤認為事件", "現場結果沒有回到門檻設定"]),
        "after": ("共同訊號", "達門檻才行動", "每次驗證都更新感測網", ["鄰近節點互相比對", "異常先經人工校驗", "採樣結果回寫判讀規則"]),
        "matrix": [
            ("保留觀察", "變化小且沒有行動必要。"), ("立即通報", "變化大且多節點一致。"),
            ("設備維護", "單點異常且缺乏鄰站支持。"), ("優先採樣", "影響可能大但證據仍不足。"),
        ],
        "metrics": [
            ("24站", "沿岸感測節點", "三種維護角色", "LIVE"),
            ("92%", "每週有效資料率", "排除維修時段", "模擬值"),
            ("18分", "異常平均確認時間", "原為 64 分鐘", "模擬值"),
            ("7次", "有效事件通報", "近 90 天", "PILOT"),
        ],
        "chart": [
            ("有效資料", [58, 64, 69, 75, 81, 87, 92]),
            ("異常確認", [32, 40, 47, 55, 62, 70, 78]),
            ("社區維護", [24, 31, 39, 48, 58, 66, 73]),
        ],
        "process": [
            ("收集", "節點持續回傳"), ("交叉比對", "檢查鄰站一致性"), ("人工校驗", "排除設備問題"),
            ("事件採樣", "確認環境變化"), ("回寫", "更新門檻與位置"),
        ],
        "timeline": [
            ("M1", "六站上線", "先建立兩個漁村的基準資料。"),
            ("M2", "加入校驗", "每週固定一次人工比對。"),
            ("M3", "定義門檻", "把訊號連到採樣與通報行動。"),
            ("M4", "擴至十八站", "依資料缺口補上外海節點。"),
            ("M6", "形成共同網", "學校、漁民與研究站共同維運。"),
        ],
        "quote": "感測器不是答案，\n它只是讓社區更早知道該去哪裡找答案。",
        "attribution": "COASTAL SIGNAL PRINCIPLE · 06",
        "center": ("資料只有連到行動，才會成為訊號", "一個可信的感測網，不只回傳數字，也記錄何時通報、如何驗證，以及下一次要改變什麼。"),
        "chapter": ("CHAPTER 06", "從設備網路走向共同判讀", "下一階段的重點不是增加更多節點，而是讓每個異常都有一致的驗證路徑。", "06"),
        "bio": ("陳奕辰", "社區科學系統工程師", ["設計低成本、可維護的沿岸感測節點。", "把設備健康與環境訊號分開判讀。", "讓現場驗證結果持續改善感測配置。"], "SENSING SYSTEMS · COMMUNITY SCIENCE · COASTAL FIELDWORK"),
        "closing": ("下一個訊號，\n要能帶來一個明確行動。", "從六個節點開始，把每次異常都變成可追溯的學習。"),
    },
]


def _concept_story(
    *,
    story_id: str,
    title: str,
    subtitle: str,
    speaker: str,
    org: str,
    toc: list[tuple[str, str]],
    priorities: list[tuple[str, str, str, str]],
    metrics: list[tuple[str, str, str, str]],
    timeline: list[tuple[str, str, str]],
    quote: str,
    attribution: str,
    closing: tuple[str, str],
    chapter_number: str,
) -> dict[str, Any]:
    """Expand a compact editorial concept into the shared semantic content model.

    The copy is still topic-specific, while repetitive structural fields are derived
    here so the Theme Lab can carry many real subjects without duplicating boilerplate.
    """
    process = [(name, body) for name, body in toc[:5]]
    recommendations = [
        (name, body, ("立即", "建置", "測試", "擴張")[index])
        for index, (name, body) in enumerate(toc[:4])
    ]
    cycle = [(name, body.rstrip("。")[:9]) for name, body in toc[:6]]
    before_points = [body for _, body in toc[:3]]
    after_points = [body for _, body, _, _ in priorities]
    matrix = [
        ("繼續觀察", toc[0][1]),
        ("立即推進", priorities[0][1]),
        ("保留彈性", toc[1][1]),
        ("優先試驗", priorities[1][1]),
    ]
    shift = int(chapter_number) % 9
    chart = [
        (metrics[0][1], [34 + shift, 42 + shift, 48 + shift, 57 + shift, 66 + shift, 75 + shift, 84 + shift]),
        (metrics[1][1], [28 + shift, 35 + shift, 45 + shift, 52 + shift, 61 + shift, 69 + shift, 78 + shift]),
        (metrics[2][1], [22 + shift, 30 + shift, 38 + shift, 49 + shift, 56 + shift, 64 + shift, 73 + shift]),
    ]
    return {
        "id": story_id,
        "title": title,
        "subtitle": subtitle,
        # Demo concepts do not invent audience metadata. External story files
        # may explicitly restore real speaker/organisation values below.
        "speaker": "",
        "org": "",
        "toc": toc,
        "priorities": [
            (name, body, f"重點 {index:02d}", allocation)
            for index, (name, body, _tag, allocation) in enumerate(priorities, 1)
        ],
        "recommendations": recommendations,
        "cycle": cycle,
        "before": ("分散處理", toc[0][0], "資訊與責任停留在各自節點", before_points),
        "after": ("共同路徑", priorities[0][0], "用共同輸入與驗收條件推進", after_points),
        "matrix": matrix,
        "metrics": [
            (value, label, note, "")
            for value, label, note, _delta in metrics
        ],
        "chart": chart,
        "process": process,
        "timeline": [
            (f"第 {index} 階段", title, body)
            for index, (_label, title, body) in enumerate(timeline, 1)
        ],
        "quote": quote,
        "attribution": "",
        "center": (closing[0].replace("\n", ""), closing[1]),
        "chapter": (f"第 {chapter_number} 章", toc[3][0], toc[3][1], chapter_number),
        "bio": (
            "專案團隊",
            "跨域專案團隊",
            [item[1] for item in priorities],
            "",
        ),
        "visible_text_language": "zh-Hant",
        "allowed_latin_terms": [],
        "closing": closing,
    }


STORIES.extend([
    _concept_story(
        story_id="craft-memory-atlas",
        title="把一座城市的手藝，編成可以繼續讀的地方誌",
        subtitle="從口述訪談、工序圖譜到新一代學徒，建立不只懷舊的工藝知識庫",
        speaker="LOCAL CRAFT EDITORIAL OFFICE",
        org="TAINAN · LIVING ARCHIVE 2026",
        toc=[
            ("失落名錄", "先找出十年內即將消失的技藝與工具。"),
            ("現場採集", "把聲音、手勢、材料與時間一起記錄。"),
            ("工序編碼", "將老師傅的經驗轉成可追索的步驟。"),
            ("人物專題", "讓每一門手藝保留自己的語氣與生命史。"),
            ("學徒入口", "把知識轉成可以實際跟做的學習路徑。"),
            ("出版回流", "讓展覽、刊物與課程持續補回新內容。"),
        ],
        priorities=[
            ("深度訪談", "先完成十二位關鍵職人的完整生命史。", "FIELD", "45%"),
            ("工序圖譜", "用照片、聲音與材料建立跨媒體索引。", "EDIT", "35%"),
            ("學習轉譯", "把檔案轉成學徒能使用的任務卡。", "NEXT", "20%"),
        ],
        metrics=[
            ("12位", "完整職人檔案", "含聲音與工序影像", "ARCHIVE"),
            ("186件", "工具與材料索引", "可交叉查找", "+42"),
            ("34小時", "口述歷史錄音", "完成逐字與摘要", "FIELD"),
            ("8門", "公開工作坊", "由青年學徒共同帶領", "LIVE"),
        ],
        timeline=[
            ("APR", "建立失落名錄", "與地方協會確認優先採集對象。"),
            ("MAY", "進入工坊", "完成第一輪人物與工序拍攝。"),
            ("JUL", "編輯專題", "把生命史、工具與材料交叉編排。"),
            ("SEP", "學徒試讀", "以任務卡測試知識能否被跟做。"),
            ("NOV", "地方誌發行", "展覽、網站與紙本同步開放。"),
        ],
        quote="保存不是把手藝放進玻璃櫃，\n而是讓下一雙手知道從哪裡接下去。",
        attribution="LIVING ARCHIVE · EDITORIAL NOTE 01",
        closing=("讓一門手藝留下來，\n也讓下一個人有機會把它做得不同。", "從十二位職人的完整檔案開始，建立可以持續增補的地方知識。"),
        chapter_number="01",
    ),
    _concept_story(
        story_id="cyber-incident-room",
        title="在 17 分鐘內，看懂一次正在擴大的資安事件",
        subtitle="把警報、資產、行為與處置責任收進同一張即時判讀地圖",
        speaker="SECURITY INCIDENT COMMAND",
        org="SOC · RESPONSE EXERCISE 04",
        toc=[
            ("訊號去重", "把相同來源與相同行為的警報合併。"),
            ("資產定級", "先確認事件是否碰到關鍵服務與資料。"),
            ("攻擊路徑", "串起帳號、端點與橫向移動跡象。"),
            ("處置指揮", "每個動作都有唯一負責人與回報期限。"),
            ("證據封存", "隔離之前先保留能支持判讀的記錄。"),
            ("規則回寫", "把漏接訊號轉成下一輪偵測規則。"),
        ],
        priorities=[
            ("關鍵資產", "付款與身分服務進入最高處置優先級。", "P1", "52%"),
            ("帳號擴散", "先阻斷具管理權限的異常登入鏈。", "BLOCK", "31%"),
            ("證據完整", "隔離動作不得破壞記憶體與端點紀錄。", "HOLD", "17%"),
        ],
        metrics=[
            ("17分", "完成事件定級", "原流程需 46 分鐘", "LIVE"),
            ("6台", "受影響端點", "其中 2 台為關鍵資產", "P1"),
            ("94%", "證據保全率", "端點與登入記錄完整", "+12pt"),
            ("3條", "新偵測規則", "演練後已回寫", "SHIP"),
        ],
        timeline=[
            ("00:00", "首筆警報", "偵測到異常權限提升。"),
            ("00:04", "資產定級", "確認事件觸及身分服務。"),
            ("00:09", "路徑成形", "定位兩個被利用的管理帳號。"),
            ("00:13", "分區隔離", "先阻斷橫向移動再保存證據。"),
            ("00:17", "完成指揮", "所有處置進入可追蹤任務。"),
        ],
        quote="事件室最怕的不是資訊太少，\n而是每個人手上都有不同版本的真相。",
        attribution="INCIDENT COMMAND · RULE 04",
        closing=("下一個警報響起時，\n先讓所有人看見同一條攻擊路徑。", "用共同事件圖縮短判讀，不用省略證據。"),
        chapter_number="04",
    ),
    _concept_story(
        story_id="harbor-light-festival",
        title="讓三天的港灣燈節，成為一整年的文化引擎",
        subtitle="把居民創作、夜間動線、地方餐飲與回訪內容編成可持續的節慶系統",
        speaker="HARBOR LIGHT FESTIVAL OFFICE",
        org="KEELUNG · CULTURE PROGRAM",
        toc=[
            ("港口故事", "從碼頭工班、漁市與移民記憶選出主題。"),
            ("居民共作", "每一區至少有一件由社區完成的作品。"),
            ("夜間動線", "把展演、餐飲與交通安排成不回頭的路徑。"),
            ("節目節奏", "大型演出與小型體驗交錯分布。"),
            ("商圈串聯", "讓人流能走進平常被忽略的街巷。"),
            ("內容續航", "活動後仍能透過聲音地圖持續被看見。"),
        ],
        priorities=[
            ("共同主題", "以港口如何迎接陌生人作為年度策展主線。", "STORY", "40%"),
            ("居民作品", "預算優先支持可被共同完成的燈件。", "MAKE", "35%"),
            ("回訪內容", "把展期資料轉成全年可走讀的數位地圖。", "ALWAYS", "25%"),
        ],
        metrics=[
            ("42件", "居民共作燈件", "涵蓋九個街區", "OPEN"),
            ("6.8km", "完整夜間動線", "串聯車站與港區", "ROUTE"),
            ("73家", "地方店家加入", "共同延長營業", "+28"),
            ("61%", "非展期回訪意願", "試走調查", "PILOT"),
        ],
        timeline=[
            ("FEB", "公開徵集故事", "收集港口生活與移動記憶。"),
            ("APR", "居民工作坊", "九區同步完成作品原型。"),
            ("JUL", "夜間試走", "調整交通、照明與商圈節點。"),
            ("OCT", "燈節開幕", "三天節目分散至完整港區。"),
            ("NOV", "聲音地圖上線", "展期內容轉成全年走讀。"),
        ],
        quote="真正留下來的節慶，\n不是那三天有多亮，而是之後還有誰願意回來。",
        attribution="HARBOR PROGRAM · CURATOR NOTE",
        closing=("燈熄了以後，\n故事仍沿著港邊繼續走。", "把一次活動變成居民、店家與旅人都能持續加入的文化路徑。"),
        chapter_number="05",
    ),
    _concept_story(
        story_id="neighborhood-newsroom",
        title="一份只有八頁的社區報，如何重新連起三條街",
        subtitle="用採訪、圖像與公共提問，讓鄰里日常重新成為值得討論的新聞",
        speaker="BLOCK 37 NEWSROOM",
        org="MONTHLY PAPER · ISSUE 06",
        toc=[
            ("街角提問", "每期只追一個所有人都能回答的問題。"),
            ("人物採訪", "讓不同世代用自己的語氣描述同一條街。"),
            ("資料小圖", "把租金、空店與人流變成可讀的微型圖表。"),
            ("編輯立場", "清楚區分觀察、引述與編輯判斷。"),
            ("公開校稿", "出刊前邀請受訪者與居民一起檢查。"),
            ("下一期線索", "把讀者回信轉成後續採訪入口。"),
        ],
        priorities=[
            ("單一提問", "用一個具體問題串起整期不同版面。", "FOCUS", "38%"),
            ("多聲部", "每篇至少保留兩種互相衝突的觀點。", "VOICE", "34%"),
            ("讀者回信", "下一期選題必須回應本期公開疑問。", "LOOP", "28%"),
        ],
        metrics=[
            ("800份", "每月紙本發行", "放置 26 個街角節點", "PRINT"),
            ("47封", "首期讀者回信", "其中 18 封提供新線索", "MAIL"),
            ("23位", "居民受訪者", "年齡 16 至 82 歲", "VOICE"),
            ("9間", "空店故事被補齊", "完成公開時間線", "FIELD"),
        ],
        timeline=[
            ("D1", "選定街角提問", "編輯會議只保留一個核心問題。"),
            ("D5", "完成街訪", "記錄不同時段與不同使用者。"),
            ("D12", "資料交叉查核", "補上租金、空店與歷史資料。"),
            ("D18", "公開校稿", "邀請受訪者檢查事實與引述。"),
            ("D25", "八頁出刊", "紙本上街並同步收集回信。"),
        ],
        quote="社區不是沒有新聞，\n只是太多日常從來沒被認真問過。",
        attribution="BLOCK 37 · EDITORIAL LETTER",
        closing=("下一期的頭版，\n從你今天經過卻沒問出口的事開始。", "把回信投進街角信箱，讓一份八頁小報繼續追下去。"),
        chapter_number="06",
    ),
    _concept_story(
        story_id="scent-launch-ritual",
        title="把一支新香氣，設計成會被記住的品牌儀式",
        subtitle="從第一秒的氣味印象、觸感包裝到櫃上體驗，建立一致卻不制式的上市節奏",
        speaker="ATELIER NO.7",
        org="FRAGRANCE LAUNCH · PRIVATE EDITION",
        toc=[
            ("氣味主張", "先用一句話定義這支香想留下的情緒。"),
            ("材料語彙", "讓紙張、玻璃與金屬回應香氣層次。"),
            ("試香節奏", "把前中後調轉成三段可感知的體驗。"),
            ("櫃上儀式", "每位顧客都經過相同但可自由停留的流程。"),
            ("內容肖像", "用人物與場景呈現香氣而不是解釋配方。"),
            ("回購線索", "把記憶、場合與使用頻率帶回會員內容。"),
        ],
        priorities=[
            ("第一印象", "前三十秒只留下香氣主張與一個觸感。", "OPEN", "44%"),
            ("三段體驗", "前中後調各自對應一個材質與動作。", "RITUAL", "36%"),
            ("私人回訪", "十四天後以使用場合開啟第二次對話。", "RETURN", "20%"),
        ],
        metrics=[
            ("38秒", "完整試香停留", "比舊流程增加 14 秒", "+58%"),
            ("72%", "能說出香氣主張", "離櫃後即時調查", "RECALL"),
            ("31%", "十四日回訪率", "私人預覽名單", "+9pt"),
            ("3層", "材料體驗節點", "紙、玻璃與金屬", "TACTILE"),
        ],
        timeline=[
            ("T-8W", "確立香氣主張", "收斂為一句可被記住的情緒描述。"),
            ("T-6W", "材料測試", "比較紙張、瓶身與櫃上光線。"),
            ("T-3W", "私人預覽", "邀請三種核心客群完整試香。"),
            ("LAUNCH", "同步上櫃", "空間、內容與服務話術同時切換。"),
            ("T+2W", "回訪啟動", "以使用情境延續私人對話。"),
        ],
        quote="奢華不是多說一點，\n而是讓每一次停頓都有被設計過的理由。",
        attribution="ATELIER NO.7 · EXPERIENCE CODE",
        closing=("讓香氣離開空間以後，\n仍能喚回那一刻的動作與光。", "把產品上市變成一段可重複、可回訪、仍保有私人感的儀式。"),
        chapter_number="07",
    ),
    _concept_story(
        story_id="old-house-restoration",
        title="修一棟老屋，不抹掉時間留下的痕跡",
        subtitle="用材料分層、住戶記憶與可逆工法，決定哪些要修、哪些值得保留",
        speaker="HOUSE 1936 FIELD STUDIO",
        org="RESTORATION NOTEBOOK · NO.08",
        toc=[
            ("時間剖面", "辨識每一次增建、修補與使用留下的層次。"),
            ("住戶記憶", "把照片、口述與空間用途放回平面圖。"),
            ("材料診斷", "區分結構風險、表面老化與可保留痕跡。"),
            ("可逆工法", "新增構件必須能被拆除且不破壞原物。"),
            ("生活更新", "新設備要服務現在的居住而不是假裝古老。"),
            ("修復日誌", "每個決定都保留材料、理由與施工照片。"),
        ],
        priorities=[
            ("結構安全", "先處理會持續擴大的受潮與梁柱問題。", "SAFE", "47%"),
            ("時間痕跡", "保留能說明使用歷史的牆面與修補。", "KEEP", "33%"),
            ("可逆新增", "新設備以獨立骨架進入原空間。", "NEW", "20%"),
        ],
        metrics=[
            ("90年", "建築使用時間", "經歷四次主要增修", "1936"),
            ("17處", "保留修補痕跡", "完成材料與年代標記", "KEEP"),
            ("82%", "原木構件再用", "經檢測後回裝", "REUSE"),
            ("6件", "可逆新增模組", "衛浴、照明與收納", "NEW"),
        ],
        timeline=[
            ("W1", "建立時間剖面", "比對圖面、照片與現場痕跡。"),
            ("W3", "完成材料診斷", "標出受潮、裂縫與可保留表面。"),
            ("W6", "結構補強", "先完成屋架與基礎安全工作。"),
            ("W10", "可逆模組進場", "新設備不覆蓋原有牆面。"),
            ("W14", "修復日誌公開", "住戶可追索每一個保留與新增決定。"),
        ],
        quote="修復不是回到某一個完美年代，\n而是讓所有年代都還能被看見。",
        attribution="HOUSE 1936 · FIELD PRINCIPLE",
        closing=("讓老屋繼續被使用，\n也讓它不必假裝自己從未老去。", "用可逆工法與完整日誌，保留時間同時容納新的生活。"),
        chapter_number="08",
    ),
    _concept_story(
        story_id="ai-workflow-adoption",
        title="九十天，讓 AI 助手真正進入團隊工作流",
        subtitle="不比誰會下 Prompt，而是把高頻任務、資料入口與驗收責任接進日常系統",
        speaker="AI OPERATING MODEL TEAM",
        org="90-DAY ADOPTION REVIEW",
        toc=[
            ("任務盤點", "找出重複、高頻且可被驗收的工作。"),
            ("資料入口", "定義 AI 可以讀什麼、不能讀什麼。"),
            ("共同範本", "把優質輸入與輸出標準保存下來。"),
            ("人機分工", "高風險判斷仍由具名負責人確認。"),
            ("成效量測", "同時追蹤時間、品質與返工率。"),
            ("擴張門檻", "只複製已通過真實任務驗收的用法。"),
        ],
        priorities=[
            ("三個任務", "先鎖定週報、知識查找與會議整理。", "NOW", "50%"),
            ("共同驗收", "每個輸出都有品質範例與拒收條件。", "QA", "30%"),
            ("權限分層", "資料敏感度決定模型與工具可用範圍。", "GUARD", "20%"),
        ],
        metrics=[
            ("-38%", "週報製作時間", "包含人工覆核", "DAY 60"),
            ("86%", "首次驗收通過率", "三個核心任務", "+21pt"),
            ("4.2hr", "每人每週省下時間", "未計入探索時間", "PILOT"),
            ("12次", "風險攔截紀錄", "敏感資料與錯誤引用", "GUARD"),
        ],
        timeline=[
            ("D1–14", "鎖定三個任務", "以真實工作量與返工成本排序。"),
            ("D15–30", "建立資料入口", "完成權限、範本與拒收條件。"),
            ("D31–45", "小隊試用", "五人小隊連續執行十個工作日。"),
            ("D46–60", "修正驗收", "把常見錯誤寫回範本與檢查。"),
            ("D61–90", "跨組複製", "只擴張通過時間與品質門檻的任務。"),
        ],
        quote="AI 導入不是多一個聊天視窗，\n而是少一次重做、少一次找不到資料。",
        attribution="AI OPERATING MODEL · RULE 09",
        closing=("下一個九十天，\n從一個每天真的會發生的任務開始。", "讓工具、資料、責任與驗收一起進入工作流。"),
        chapter_number="09",
    ),
    _concept_story(
        story_id="brave-classroom",
        title="讓害怕開口的孩子，也能參與一堂課",
        subtitle="用不同回答方式、同儕小組與低壓回饋，重新設計教室裡的參與感",
        speaker="BRAVE CLASSROOM LAB",
        org="MIDDLE SCHOOL · LEARNING PILOT",
        toc=[
            ("安全入口", "先允許寫、畫、選擇，再決定是否口頭分享。"),
            ("小組尺度", "從兩人交換開始，不直接面對全班。"),
            ("等待時間", "提問後保留真正思考與組織語句的空間。"),
            ("回饋語言", "老師回應內容，不公開比較表達速度。"),
            ("參與紀錄", "追蹤每位學生用了哪一種方式加入。"),
            ("自主挑戰", "由學生選擇下一次願意多跨出哪一步。"),
        ],
        priorities=[
            ("多種回答", "每個問題至少提供口說、書寫與圖像入口。", "CHOICE", "42%"),
            ("小組先行", "全班分享之前先在兩人或四人組預演。", "PAIR", "36%"),
            ("可見進步", "只和學生自己的前一次參與方式比較。", "GROW", "22%"),
        ],
        metrics=[
            ("91%", "每週至少參與一次", "原本為 58%", "+33pt"),
            ("3.4種", "平均回答方式", "口說、書寫、圖像與選擇", "CHOICE"),
            ("+46%", "低發言學生主動加入", "八週觀察", "PILOT"),
            ("8週", "完成第一輪教學試驗", "兩個班級", "LEARN"),
        ],
        timeline=[
            ("W1", "建立安全入口", "所有提問加入非口頭回答方式。"),
            ("W2", "小組交換", "先在兩人組中整理自己的想法。"),
            ("W4", "學生自選挑戰", "每人設定下一次願意嘗試的參與方式。"),
            ("W6", "同儕回饋", "回應內容與提問，不評分表達速度。"),
            ("W8", "共同回顧", "由學生說明什麼讓自己更敢加入。"),
        ],
        quote="參與不是每個人都要大聲說話，\n而是每個人都知道自己的想法有入口。",
        attribution="BRAVE CLASSROOM · LEARNING NOTE",
        closing=("下一個問題，\n先留一個不必立刻開口的入口。", "讓每個孩子都能用自己的速度走進共同討論。"),
        chapter_number="10",
    ),
    _concept_story(
        story_id="night-transit-resilience",
        title="讓深夜後的回家路，不再只靠運氣",
        subtitle="用班次、等待、轉乘與照明訊號，重新設計城市的夜間運輸安全網",
        speaker="NIGHT TRANSIT RESILIENCE LAB",
        org="TAIPEI · MOBILITY PILOT 2026",
        toc=[
            ("末班斷點", "先找出乘客最常被留在原地的時段與轉乘點。"),
            ("真實等待", "將班距改成乘客真正感受的等待時間。"),
            ("安全路徑", "把照明、人流與深夜店家接進轉乘動線。"),
            ("彈性班次", "依大型活動與誤點訊號動態增減班次。"),
            ("現場通報", "讓司機、站務與乘客共用同一個異常入口。"),
            ("經驗回寫", "每次久候與錯過轉乘都成為下一輪調度依據。"),
        ],
        priorities=[
            ("轉乘接續", "優先保住最後一段可以安全到家的連接。", "LINK", "46%"),
            ("夜間可見", "將久候區與步行路徑納入持續照明。", "SAFE", "34%"),
            ("即時調度", "以運量與延誤訊號觸發彈性加班。", "LIVE", "20%"),
        ],
        metrics=[
            ("-37%", "平均深夜等待", "三個轉乘節點", "PILOT"),
            ("92%", "末段轉乘成功率", "原為 71%", "+21pt"),
            ("14分", "異常加班啟動", "含人工確認", "LIVE"),
            ("6站", "安全路徑完成", "連結夜間店家", "OPEN"),
        ],
        timeline=[
            ("W1", "整理斷點", "分析三個月的末班與誤點資料。"),
            ("W3", "夜間走查", "與乘客實際走完六條轉乘路徑。"),
            ("W5", "動態加班", "建立延誤與運量的觸發門檻。"),
            ("W8", "現場聯動", "站務、司機與客服共用事件編號。"),
            ("W12", "擴大路網", "只複製已降低等待且沒有增加空班的方案。"),
        ],
        quote="一座城市是否可靠，\n往往要到末班開走後才看得出來。",
        attribution="NIGHT TRANSIT · OPERATING PRINCIPLE 11",
        closing=("讓最後一段回家路，\n也有可被驗證的服務承諾。", "先從三個轉乘站開始，用真實等待與接續成功率決定是否擴張。"),
        chapter_number="11",
    ),
    _concept_story(
        story_id="food-rescue-exchange",
        title="在打烊前兩小時，讓剩食找到下一張餐桌",
        subtitle="把供給、溫度、運送與需求擺在同一個交換網，降低市場與餐飲的浪費",
        speaker="FOOD RESCUE EXCHANGE",
        org="CITY MARKET · CIRCULAR LOGISTICS",
        toc=[
            ("供給視窗", "供應端只回報數量、溫度與最後取件時間。"),
            ("需求配對", "依距離、設備與當日餐點快速篩選。"),
            ("集中取件", "同一市場只保留一個取件窗口與負責人。"),
            ("冷鏈確認", "到貨前記錄溫度、時間與外觀狀態。"),
            ("使用回報", "收受端回寫真實使用量與不適合原因。"),
            ("減量優先", "持續剩餘的品項先回到原供應流程改善。"),
        ],
        priorities=[
            ("準時取件", "先把打烊前的可用時間變成穩定窗口。", "TIME", "42%"),
            ("需求適配", "不是全收，而是先確認設備、人數與菜單。", "MATCH", "36%"),
            ("減量回寫", "把反覆剩餘的品項回傳供應端。", "REDUCE", "22%"),
        ],
        metrics=[
            ("1.8噸", "每週重新分配", "五個傳統市場", "LIVE"),
            ("84%", "配對後實際使用", "原試辦為 57%", "+27pt"),
            ("38分", "平均取件完成", "自發出通知起", "ROUTE"),
            ("29家", "穩定供應據點", "餐飲與零售", "OPEN"),
        ],
        timeline=[
            ("M1", "五市場上線", "建立固定取件窗與負責人。"),
            ("M2", "需求標籤", "收受端先登錄設備、人數與禁忌。"),
            ("M3", "路線整併", "同區訂單併成單一巡回路徑。"),
            ("M4", "減量回寫", "把未使用原因分類回傳供應端。"),
            ("M6", "擴至餐飲街區", "以使用率而不是收貨量作為擴張門檻。"),
        ],
        quote="循環不是把每一份剩食都送走，\n而是讓明天本來就少剩一點。",
        attribution="FOOD RESCUE · OPERATING NOTE 12",
        closing=("下一次打烊前，\n先讓多出來的食物被看見。", "用可用時間、真實需求與使用回報，把一次性捐贈變成穩定交換。"),
        chapter_number="12",
    ),
])


STYLE_OVERRIDES: dict[str, str] = {
    "brand-editorial": r'''
.slide{background-image:linear-gradient(90deg,transparent 0 72%,color-mix(in srgb,var(--primary) 5%,transparent) 72% 72.15%,transparent 72.15%),linear-gradient(0deg,transparent 0 18%,color-mix(in srgb,var(--secondary) 5%,transparent) 18% 18.15%,transparent 18.15%),radial-gradient(circle,color-mix(in srgb,var(--primary) 16%,transparent) 0 1.4px,transparent 2px);background-size:100% 100%,100% 100%,24px 24px;box-shadow:inset 0 0 110px rgba(0,0,0,.22)}
.diagram-node-bg{border:1px solid color-mix(in srgb,var(--primary) 58%,transparent);border-radius:3px;background:linear-gradient(145deg,color-mix(in srgb,var(--surface) 92%,transparent),color-mix(in srgb,var(--primary) 8%,var(--surface)));box-shadow:0 18px 42px color-mix(in srgb,var(--secondary) 14%,transparent)}
.prod-title,.cover-center-title,.cover-split-title{font-family:var(--font-display);letter-spacing:-.055em}
''',
    "lavender-media-kit": r'''
.slide{background-image:radial-gradient(circle at 18% 20%,color-mix(in srgb,var(--accent) 30%,transparent),transparent 34%),radial-gradient(circle at 82% 76%,color-mix(in srgb,var(--secondary) 24%,transparent),transparent 38%),linear-gradient(135deg,color-mix(in srgb,var(--bg) 92%,#fff),color-mix(in srgb,var(--support-accent) 36%,#fff))}
.diagram-node-bg{border:1px solid rgba(255,255,255,.72);border-radius:32px;background:color-mix(in srgb,var(--surface) 62%,rgba(255,255,255,.58));box-shadow:0 24px 70px color-mix(in srgb,var(--primary) 16%,transparent),inset 0 1px rgba(255,255,255,.92);backdrop-filter:blur(18px)}
.prod-title,.cover-center-title,.cover-split-title,.statement-focus-quote{font-family:var(--font-display);letter-spacing:-.035em}
''',
    "paper-collage-vintage": r'''
.slide{background-image:radial-gradient(circle,rgba(62,39,35,.075) 0 1px,transparent 1.8px),repeating-linear-gradient(6deg,transparent 0 34px,rgba(62,39,35,.025) 35px 36px);background-size:29px 31px,100% 100%;box-shadow:inset 0 0 120px rgba(62,39,35,.07)}
.diagram-node-bg{border:1px solid color-mix(in srgb,var(--secondary) 22%,transparent);border-radius:8px;box-shadow:0 18px 42px rgba(62,39,35,.12);background:color-mix(in srgb,var(--surface) 90%,#fff)}
.prod-title,.cover-center-title,.cover-split-title,.statement-focus-quote{font-family:var(--font-display)}
''',
    "brutal-grunge": r'''
.slide{background-image:radial-gradient(ellipse at 12% 20%,rgba(255,255,255,.055),transparent 34%),radial-gradient(ellipse at 78% 72%,rgba(0,0,0,.38),transparent 44%),repeating-linear-gradient(112deg,transparent 0 22px,rgba(255,255,255,.018) 23px 24px);box-shadow:inset 0 0 130px rgba(0,0,0,.42)}
.diagram-node-bg{border:1.5px solid color-mix(in srgb,var(--secondary) 68%,transparent);border-radius:28px;background:color-mix(in srgb,var(--surface) 82%,transparent);box-shadow:0 24px 60px rgba(0,0,0,.28)}
.prod-title,.cover-center-title,.cover-split-title,.statement-focus-quote{text-transform:uppercase;font-family:var(--font-display);letter-spacing:-.03em}
''',
    "product-strategy-signal": r'''
.slide{background-image:radial-gradient(circle at 82% 18%,color-mix(in srgb,var(--accent) 12%,transparent),transparent 28%),linear-gradient(color-mix(in srgb,var(--accent) 7%,transparent) 1px,transparent 1px),linear-gradient(90deg,color-mix(in srgb,var(--accent) 7%,transparent) 1px,transparent 1px);background-size:100% 100%,96px 96px,96px 96px;box-shadow:inset 0 0 90px color-mix(in srgb,var(--secondary) 6%,transparent)}
.diagram-node-bg{border:1px solid color-mix(in srgb,var(--secondary) 32%,transparent);border-top:4px solid var(--accent);border-radius:2px;background:linear-gradient(180deg,color-mix(in srgb,var(--accent) 5%,var(--surface)),var(--surface));box-shadow:none}
.prod-title,.cover-center-title,.cover-split-title{letter-spacing:-.05em}
[data-theme="product-strategy-signal"] [data-surface-role="statement"]>.diagram-node-bg{background:linear-gradient(180deg,color-mix(in srgb,var(--surface) 98%,var(--accent)),color-mix(in srgb,var(--surface) 92%,var(--accent)))}
[data-theme="product-strategy-signal"] [data-surface-role="index"]>.diagram-node-bg{background:linear-gradient(180deg,color-mix(in srgb,var(--surface) 96%,var(--accent)),color-mix(in srgb,var(--surface) 88%,var(--accent)))}
[data-theme="product-strategy-signal"] [data-surface-role="panel"]>.diagram-node-bg{background:linear-gradient(180deg,color-mix(in srgb,var(--surface) 92%,var(--accent)),color-mix(in srgb,var(--surface) 80%,var(--accent)))}
[data-theme="product-strategy-signal"] [data-surface-role="ledger"]>.diagram-node-bg{background:linear-gradient(180deg,color-mix(in srgb,var(--surface) 94%,var(--accent)),color-mix(in srgb,var(--surface) 84%,var(--accent)))}
[data-theme="product-strategy-signal"] [data-surface-role="metric"]>.diagram-node-bg{background:linear-gradient(180deg,color-mix(in srgb,var(--surface) 90%,var(--accent)),color-mix(in srgb,var(--surface) 76%,var(--accent)))}
''',
    "soft-organic-education": r'''
.slide{background-image:radial-gradient(ellipse at 8% 8%,color-mix(in srgb,var(--support-accent) 52%,transparent),transparent 34%),radial-gradient(ellipse at 92% 88%,color-mix(in srgb,var(--accent) 20%,transparent),transparent 38%),radial-gradient(circle,color-mix(in srgb,var(--secondary) 7%,transparent) 0 1.2px,transparent 1.8px);background-size:100% 100%,100% 100%,34px 34px}
.diagram-node-bg{border:0;border-radius:42px;background:color-mix(in srgb,var(--surface) 90%,#fff);box-shadow:0 18px 50px color-mix(in srgb,var(--secondary) 14%,transparent)}
.prod-title,.cover-center-title,.cover-split-title{letter-spacing:-.035em}
''',
    "festive-patterned": r'''
.slide{background-image:linear-gradient(45deg,color-mix(in srgb,var(--accent) 10%,transparent) 25%,transparent 25% 75%,color-mix(in srgb,var(--accent) 10%,transparent) 75%),linear-gradient(-45deg,color-mix(in srgb,var(--accent) 8%,transparent) 25%,transparent 25% 75%,color-mix(in srgb,var(--accent) 8%,transparent) 75%);background-size:56px 56px}
.diagram-node-bg{border:2px solid color-mix(in srgb,var(--accent) 58%,transparent);border-radius:4px;background:color-mix(in srgb,var(--surface) 94%,var(--bg));box-shadow:0 18px 42px color-mix(in srgb,#111 18%,transparent)}
.prod-title,.cover-center-title,.cover-split-title{font-family:var(--font-display)}
''',
    "grainy-editorial": r'''
.slide{background-image:linear-gradient(115deg,color-mix(in srgb,var(--accent) 5%,transparent),transparent 42%),radial-gradient(circle,rgba(0,0,0,.055) 0 1px,transparent 1.5px);background-size:100% 100%,5px 5px;box-shadow:inset 0 0 100px rgba(0,0,0,.035)}
.diagram-node-bg{border:0;border-top:2px solid var(--accent);border-radius:0;background:color-mix(in srgb,var(--surface) 72%,transparent);box-shadow:none}
.prod-title,.cover-center-title,.cover-split-title,.statement-focus-quote{font-family:var(--font-display);font-weight:700}
''',
    "clean-tech-business": r'''
.slide{background-image:radial-gradient(circle at 88% 12%,color-mix(in srgb,var(--accent) 18%,#fff),transparent 32%),linear-gradient(color-mix(in srgb,var(--accent) 10%,transparent) 1px,transparent 1px),linear-gradient(90deg,color-mix(in srgb,var(--accent) 10%,transparent) 1px,transparent 1px);background-size:100% 100%,42px 42px,42px 42px;box-shadow:inset 0 0 100px color-mix(in srgb,var(--accent) 5%,transparent)}
.diagram-node-bg{border:1px solid color-mix(in srgb,var(--accent) 42%,transparent);border-radius:18px;background:color-mix(in srgb,var(--surface) 86%,transparent);box-shadow:0 18px 48px color-mix(in srgb,var(--secondary) 12%,transparent);backdrop-filter:blur(12px)}
.prod-title,.cover-center-title,.cover-split-title{letter-spacing:-.045em}
''',
    "dark-circuit": r'''
.slide{background-image:radial-gradient(circle at 78% 18%,color-mix(in srgb,var(--accent) 14%,transparent),transparent 28%),radial-gradient(color-mix(in srgb,var(--accent) 32%,transparent) 1px,transparent 1.6px),linear-gradient(90deg,transparent 49.7%,color-mix(in srgb,var(--accent) 7%,transparent) 50%,transparent 50.3%);background-size:100% 100%,24px 24px,190px 190px;box-shadow:inset 0 0 120px rgba(0,0,0,.32)}
.diagram-node-bg{border:1px solid color-mix(in srgb,var(--accent) 70%,transparent);border-radius:4px;background:color-mix(in srgb,var(--surface) 76%,transparent);box-shadow:0 0 28px color-mix(in srgb,var(--accent) 18%,transparent),inset 0 0 24px rgba(0,0,0,.24)}
.prod-title,.cover-center-title,.cover-split-title{letter-spacing:-.045em}
''',
}

for _theme_id, _theme_css in STYLE_OVERRIDES.items():
    assert_appearance_css(
        production.normalize_generated_css_font_sizes(_theme_css),
        source=f"theme:{_theme_id}",
    )


# Theme color and material are not enough to create meaningful variation.  These
# renderer-scoped dialects change composition, text direction, edge language and
# depth model while preserving the same editable Theme/Layout semantics.
DIALECT_OVERRIDES: dict[str, str] = {
    "brand-editorial": r'''
[data-theme="brand-editorial"] .cover-center-area,[data-theme="brand-editorial"] .statement-center-area{display:grid;grid-template-columns:minmax(0,1180px) 180px;grid-auto-rows:max-content;align-content:center;justify-content:start;column-gap:54px;row-gap:24px;text-align:left}
[data-theme="brand-editorial"] .cover-center-title,[data-theme="brand-editorial"] .statement-center-headline{grid-column:1;font-size:116px;line-height:.98;max-width:1180px;text-align:left;text-wrap:balance}
[data-theme="brand-editorial"] .cover-center-rule,[data-theme="brand-editorial"] .statement-center-rule{grid-column:1;width:260px!important;height:7px!important}
[data-theme="brand-editorial"] .cover-center-subtitle,[data-theme="brand-editorial"] .statement-center-support{grid-column:1;font-size:36px;max-width:1120px;text-align:left;text-wrap:pretty}
[data-theme="brand-editorial"] .cover-center-speaker{grid-column:1;margin-top:8px;text-align:left}
[data-theme="brand-editorial"] .cover-center-org{grid-column:1;grid-row:auto;align-self:start;justify-self:start;writing-mode:horizontal-tb;font-size:36px;line-height:1.35;max-width:1100px}
[data-theme="brand-editorial"] .prod-title{font-size:76px;font-family:var(--font-display);max-width:1160px}
[data-theme="brand-editorial"]:not([data-preset-theme]) [data-production-family="modules"] .diagram-node-bg,[data-theme="brand-editorial"]:not([data-preset-theme]) [data-production-family="toc"] .diagram-node-bg{background:transparent;border-width:2px 0 0;border-color:var(--accent);box-shadow:none}
''',
    "brutal-grunge": r'''
[data-theme="brutal-grunge"] .cover-center-area,[data-theme="brutal-grunge"] .statement-center-area{align-items:flex-start;justify-content:flex-end;text-align:left;transform-style:preserve-3d;transform-origin:12% 50%}
[data-theme="brutal-grunge"] .cover-center-title,[data-theme="brutal-grunge"] .statement-center-headline{font-size:142px;line-height:.88;max-width:1520px;text-align:left;text-wrap:balance;text-shadow:14px 14px 0 rgba(0,0,0,.34);transform:translateZ(42px)}
[data-theme="brutal-grunge"] .cover-center-rule,[data-theme="brutal-grunge"] .statement-center-rule{width:520px!important;height:18px!important;clip-path:polygon(0 22%,100% 0,96% 100%,2% 78%)}
[data-theme="brutal-grunge"] .cover-center-subtitle,[data-theme="brutal-grunge"] .statement-center-support{font-size:37px;max-width:1260px;text-align:left;transform:translateZ(20px)}
[data-theme="brutal-grunge"] .prod-title{font-size:84px;line-height:.94;text-transform:uppercase}
[data-theme="brutal-grunge"] .diagram-node-bg{border-radius:0!important;clip-path:polygon(3% 0,100% 0,97% 100%,0 94%);box-shadow:16px 18px 0 rgba(0,0,0,.28)!important}
[data-theme="brutal-grunge"] .diagram-node:nth-of-type(even){rotate:-.65deg}[data-theme="brutal-grunge"] .diagram-node:nth-of-type(odd){rotate:.45deg}
''',
    "clean-tech-business": r'''
[data-theme="clean-tech-business"] .cover-center-area{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:auto auto auto;align-content:center;align-items:end;column-gap:90px;text-align:left}
[data-theme="clean-tech-business"] .cover-center-title{grid-column:1/3;font-size:104px;max-width:1500px;text-align:left;color:var(--text);-webkit-text-fill-color:var(--text);background:none;background-clip:border-box;-webkit-background-clip:border-box;text-wrap:balance}
[data-theme="clean-tech-business"] .cover-center-rule{grid-column:1;width:100%!important;height:3px!important}
[data-theme="clean-tech-business"] .cover-center-subtitle{grid-column:1/3;font-size:38px;max-width:1480px;text-align:left}
[data-theme="clean-tech-business"] .cover-center-speaker,[data-theme="clean-tech-business"] .cover-center-org{text-align:left;margin-top:22px}
[data-theme="clean-tech-business"] .prod-title{font-size:72px;letter-spacing:-.045em}
[data-theme="clean-tech-business"] .diagram-node-bg{border-radius:0!important;clip-path:polygon(0 0,calc(100% - 22px) 0,100% 22px,100% 100%,0 100%);background:linear-gradient(135deg,color-mix(in srgb,var(--surface) 88%,transparent),color-mix(in srgb,var(--accent) 7%,transparent));box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--accent) 28%,transparent)!important}
''',
    "dark-circuit": r'''
html[data-theme="dark-circuit"]{--surface-text:#F7F9FF;--surface-muted:#C5CEDD;--surface-accent-ink:#FF9A72}
[data-theme="dark-circuit"] .cover-center-area{align-items:flex-end;text-align:right;justify-content:center;padding-right:90px}
[data-theme="dark-circuit"] .statement-center-area{align-items:center;text-align:center;justify-content:center;padding-right:0}
[data-theme="dark-circuit"] .cover-center-title{width:1260px!important;max-width:1260px;font-size:118px;line-height:.96;white-space:normal;text-align:right;color:var(--text);mix-blend-mode:normal;text-shadow:none;text-wrap:balance}
[data-theme="dark-circuit"] .statement-center-headline{width:max-content!important;max-width:1420px;font-size:118px;line-height:.96;white-space:normal;text-align:center;color:var(--text);mix-blend-mode:normal;text-shadow:none;text-wrap:balance}
[data-theme="dark-circuit"] .cover-center-rule{width:420px!important;height:2px!important;box-shadow:none}
[data-theme="dark-circuit"] .statement-center-rule{width:180px!important;height:8px!important;box-shadow:none}
[data-theme="dark-circuit"] .cover-center-subtitle{text-align:right;font-size:36px;max-width:1120px}
[data-theme="dark-circuit"] .statement-center-support{text-align:center;font-size:36px;max-width:1120px}
[data-theme="dark-circuit"] .cover-center-org{writing-mode:horizontal-tb;position:static!important;translate:none!important;width:max-content!important;height:auto!important;max-width:1120px;text-align:right}
[data-theme="dark-circuit"] .prod-title{font-size:70px;color:var(--text);-webkit-text-fill-color:var(--text);text-shadow:none;filter:none;mix-blend-mode:normal}
[data-theme="dark-circuit"] .diagram-node-bg{background:linear-gradient(145deg,rgba(35,43,64,.92),rgba(20,25,42,.78))!important;backdrop-filter:blur(10px) saturate(140%)}
''',
    "festive-patterned": r'''
[data-theme="festive-patterned"] .slide{background-image:repeating-conic-gradient(from 45deg at 50% 50%,color-mix(in srgb,var(--accent) 15%,transparent) 0 12.5%,transparent 0 25%),linear-gradient(135deg,var(--bg),color-mix(in srgb,var(--support-accent) 24%,var(--bg)));background-size:84px 84px,100% 100%;background-blend-mode:multiply,normal}
[data-theme="festive-patterned"] .cover-center-area,[data-theme="festive-patterned"] .statement-center-area{align-items:flex-start;text-align:left;justify-content:center}
[data-theme="festive-patterned"] .cover-center-title,[data-theme="festive-patterned"] .statement-center-headline{font-size:126px;line-height:.92;max-width:1450px;text-align:left;text-shadow:8px 8px 0 color-mix(in srgb,var(--accent) 44%,transparent);text-wrap:balance}
[data-theme="festive-patterned"] .cover-center-rule,[data-theme="festive-patterned"] .statement-center-rule{width:680px!important;height:22px!important;clip-path:polygon(0 20%,96% 0,100% 74%,4% 100%)}
[data-theme="festive-patterned"] .cover-center-subtitle,[data-theme="festive-patterned"] .statement-center-support{text-align:left;font-size:38px;max-width:1240px}
[data-theme="festive-patterned"] .prod-title{font-size:78px;line-height:.96}
[data-theme="festive-patterned"] .diagram-node-bg{border-radius:0!important;clip-path:polygon(0 7%,96% 0,100% 92%,4% 100%);box-shadow:10px 12px 0 color-mix(in srgb,var(--text) 18%,transparent)!important}
''',
    "grainy-editorial": r'''
html[data-theme="grainy-editorial"]{--surface-muted:#51423E;--muted:#51423E;--surface-accent-ink:#59433B;--accent-ink:#59433B}
[data-theme="grainy-editorial"] .slide{background-blend-mode:multiply,normal}
[data-theme="grainy-editorial"] .cover-center-area,[data-theme="grainy-editorial"] .statement-center-area{display:grid;grid-template-columns:minmax(0,1220px) 150px;grid-template-rows:auto auto auto;column-gap:72px;align-content:center;text-align:left}
[data-theme="grainy-editorial"] .cover-center-title,[data-theme="grainy-editorial"] .statement-center-headline{grid-column:1;font-size:132px;line-height:.92;max-width:1220px;text-align:left;text-wrap:balance}
[data-theme="grainy-editorial"] .cover-center-rule,[data-theme="grainy-editorial"] .statement-center-rule{grid-column:1;width:100%!important;height:4px!important}
[data-theme="grainy-editorial"] .cover-center-subtitle,[data-theme="grainy-editorial"] .statement-center-support{grid-column:1;grid-row:auto;writing-mode:horizontal-tb;font-size:36px;line-height:1.45;max-height:none;max-width:1120px;text-align:left;text-wrap:pretty}
[data-theme="grainy-editorial"] .cover-center-speaker,[data-theme="grainy-editorial"] .cover-center-org{grid-column:1;text-align:left}
[data-theme="grainy-editorial"] .prod-title{font-size:82px;line-height:.96;max-width:1260px}
[data-theme="grainy-editorial"] .diagram-node-bg{background:color-mix(in srgb,var(--surface) 56%,transparent)!important;border-width:3px 0 0!important;box-shadow:none!important}
''',
    "lavender-media-kit": r'''
[data-theme="lavender-media-kit"] .cover-center-area,[data-theme="lavender-media-kit"] .statement-center-area{align-items:flex-end;justify-content:center;text-align:right;padding:80px 96px;background:color-mix(in srgb,var(--surface) 40%,transparent);backdrop-filter:blur(26px) saturate(125%);-webkit-mask-image:linear-gradient(115deg,transparent 0 4%,#000 18% 100%);mask-image:linear-gradient(115deg,transparent 0 4%,#000 18% 100%)}
[data-theme="lavender-media-kit"] .cover-center-title,[data-theme="lavender-media-kit"] .statement-center-headline{width:1120px!important;max-width:1120px;font-size:116px;line-height:.98;white-space:normal;text-align:right;color:var(--text);-webkit-text-fill-color:var(--text);background:none;background-clip:border-box;-webkit-background-clip:border-box;text-wrap:balance}
[data-theme="lavender-media-kit"] .cover-center-rule,[data-theme="lavender-media-kit"] .statement-center-rule{width:320px!important;height:5px!important}
[data-theme="lavender-media-kit"] .cover-center-subtitle,[data-theme="lavender-media-kit"] .statement-center-support{width:1080px!important;max-width:1080px;white-space:normal;text-align:right;font-size:36px}
[data-theme="lavender-media-kit"] .prod-title{font-size:74px;color:var(--text);-webkit-text-fill-color:var(--text);background:none;background-clip:border-box;-webkit-background-clip:border-box}
''',
    "paper-collage-vintage": r'''
[data-theme="paper-collage-vintage"] .cover-center-area,[data-theme="paper-collage-vintage"] .statement-center-area{align-items:flex-start;justify-content:center;text-align:left;padding-left:70px}
[data-theme="paper-collage-vintage"] .cover-center-title,[data-theme="paper-collage-vintage"] .statement-center-headline{font-size:124px;line-height:.94;max-width:1360px;text-align:left;text-wrap:balance;text-shadow:5px 7px 0 color-mix(in srgb,var(--secondary) 22%,transparent)}
[data-theme="paper-collage-vintage"] .cover-center-rule,[data-theme="paper-collage-vintage"] .statement-center-rule{width:460px!important;height:14px!important;rotate:2deg;-webkit-mask-image:linear-gradient(90deg,transparent,#000 3% 96%,transparent);mask-image:linear-gradient(90deg,transparent,#000 3% 96%,transparent)}
[data-theme="paper-collage-vintage"] .cover-center-subtitle,[data-theme="paper-collage-vintage"] .statement-center-support{text-align:left;font-size:37px;max-width:1160px}
[data-theme="paper-collage-vintage"] .prod-title{font-size:78px;rotate:-.7deg}
[data-theme="paper-collage-vintage"] .diagram-node-bg{clip-path:polygon(1% 2%,98% 0,100% 95%,3% 100%,0 38%);mix-blend-mode:multiply}
[data-theme="paper-collage-vintage"] .diagram-node:nth-of-type(3n){rotate:.65deg}[data-theme="paper-collage-vintage"] .diagram-node:nth-of-type(3n+1){rotate:-.5deg}
''',
    "product-strategy-signal": r'''
[data-theme="product-strategy-signal"] .cover-center-area{display:grid;grid-template-columns:110px minmax(0,1fr);grid-auto-rows:max-content;align-content:center;column-gap:44px;text-align:left}
/* The statement rail is an edge marker: its right edge shares the text
   column's left edge, so the vertical line stays outside the glyph box. */
[data-theme="product-strategy-signal"] .statement-center-area{display:grid;grid-template-columns:10px minmax(0,1fr);grid-auto-rows:max-content;align-content:center;column-gap:0;text-align:left}
[data-theme="product-strategy-signal"] .cover-center-title,[data-theme="product-strategy-signal"] .statement-center-headline{grid-column:2;font-size:116px;line-height:.94;max-width:1360px;text-align:left;text-wrap:balance}
[data-theme="product-strategy-signal"] .cover-center-rule,[data-theme="product-strategy-signal"] .statement-center-rule{grid-column:1;grid-row:1/5;width:10px!important;height:100%!important;justify-self:center;background:linear-gradient(var(--accent),var(--support-accent))}
[data-theme="product-strategy-signal"] .cover-center-subtitle,[data-theme="product-strategy-signal"] .statement-center-support{grid-column:2;text-align:left;font-size:36px;max-width:1180px}
[data-theme="product-strategy-signal"] .cover-center-speaker,[data-theme="product-strategy-signal"] .cover-center-org{grid-column:2;text-align:left}
[data-theme="product-strategy-signal"] .prod-title{font-size:72px;max-width:1120px}
[data-theme="product-strategy-signal"] .toc-side-panel,[data-theme="product-strategy-signal"] .toc-side-panel .diagram-node-bg{background:var(--primary)}
[data-theme="product-strategy-signal"] .toc-side-panel :is(span,b,p,em){color:#fff}
[data-theme="product-strategy-signal"] [data-production-family="sequence"] .diagram-node-bg,[data-theme="product-strategy-signal"] [data-production-family="content"] .diagram-node-bg{background:transparent;border-radius:0;border-width:0 0 2px;box-shadow:none}
''',
    "soft-organic-education": r'''
[data-theme="soft-organic-education"] .slide{background-image:repeating-radial-gradient(ellipse at 82% 24%,transparent 0 52px,color-mix(in srgb,var(--accent) 8%,transparent) 54px 56px,transparent 58px 94px),radial-gradient(ellipse at 10% 90%,color-mix(in srgb,var(--support-accent) 54%,transparent),transparent 42%)}
[data-theme="soft-organic-education"] .cover-center-area,[data-theme="soft-organic-education"] .statement-center-area{align-items:flex-start;justify-content:center;text-align:left;padding-left:110px;-webkit-mask-image:radial-gradient(ellipse 110% 92% at 42% 48%,#000 74%,transparent 100%);mask-image:radial-gradient(ellipse 110% 92% at 42% 48%,#000 74%,transparent 100%)}
[data-theme="soft-organic-education"] .cover-center-title,[data-theme="soft-organic-education"] .statement-center-headline{width:1180px!important;max-width:1180px;font-size:112px;line-height:1;white-space:normal;text-align:left;text-wrap:balance}
[data-theme="soft-organic-education"] .cover-center-rule,[data-theme="soft-organic-education"] .statement-center-rule{width:260px!important;height:12px!important;border-radius:48% 52% 44% 56%}
[data-theme="soft-organic-education"] .cover-center-subtitle,[data-theme="soft-organic-education"] .statement-center-support{width:1120px!important;max-width:1120px;white-space:normal;text-align:left;font-size:37px}
[data-theme="soft-organic-education"] .prod-title{font-size:74px;max-width:1240px}
[data-theme="soft-organic-education"] .diagram-node-bg{border-radius:38% 62% 48% 52%/18% 22% 78% 82%!important;box-shadow:0 22px 48px color-mix(in srgb,var(--secondary) 13%,transparent)!important}
''',
}


COMMON_RANDOM_CSS = r'''
/* Random demo typography guardrails: keep short statements compact and
   reserve separate vertical bands for closing copy and contact metadata. */
.slide::before,.slide::after{content:none!important;display:none!important}
.cover-edge-decor,.chapter-side-decor{display:none!important}
.cover-center-title,.statement-center-headline,.prod-title{text-wrap:balance}
.cover-center-subtitle,.statement-center-support,.prod-subtitle{text-wrap:pretty}
.cover-center-title,.cover-center-subtitle,.cover-center-speaker,.cover-center-org,.statement-center-headline,.statement-center-support{width:max-content;height:max-content}
/* centered-signal-hero owns one centered flow axis. Theme dialects may style
   the objects, while the renderer resolves their dependent vertical spacing. */
[data-composition-variant="centered-signal-hero"] .cover-center-area.explicit-center-stack{display:flex!important;left:0!important;top:0!important;width:1728px!important;height:var(--prod-frame-height)!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;text-align:center!important;padding:0!important;gap:30px!important}
[data-composition-variant="centered-signal-hero"] .cover-center-area.explicit-center-stack>.el{position:relative!important;flex:0 0 auto!important;grid-column:auto!important;grid-row:auto!important}
[data-composition-variant="centered-signal-hero"] .cover-center-area.explicit-center-stack :is(.cover-center-title,.cover-center-subtitle,.cover-center-speaker,.cover-center-org){text-align:center!important;writing-mode:horizontal-tb!important;text-orientation:mixed!important}
.closing-title{top:88px!important;right:44px!important;font-size:64px!important;line-height:1.02!important}
.closing-body{top:238px!important;font-size:36px!important;line-height:1.42!important}
.closing-copy-panel ul{bottom:30px!important}
.closing-copy-panel li{height:46px!important}
.closing-copy-panel li b{font-size:42px!important}
'''


def numbered(items: list[tuple[str, str]], count: int | None = None) -> list[tuple[str, str, str]]:
    selected = items[: count or len(items)]
    return [(f"{index:02d}", title, body) for index, (title, body) in enumerate(selected, 1)]


def apply_story(
    story: dict[str, Any],
    layout_ids: list[str],
    store: Any | None = None,
) -> None:
    store = store or production
    cover_id, _, strategy_id, relationship_id, evidence_id, sequence_id, statement_id, _ = layout_ids
    store.COVER_CONTENT[cover_id] = {
        "title": story["title"], "subtitle": story["subtitle"],
        "speaker": story.get("speaker") or "", "org": story.get("org") or "",
    }

    store.TOC_ITEMS[:] = numbered(story["toc"])
    store.TOC_CONTEXT.update({
        "title": "六個章節，從現場問題走向可驗證行動",
        "intro": story["subtitle"],
        "footer": "",
    })

    if strategy_id == "recommendation-stack":
        store.CONTENT_CONTENT[strategy_id] = {
            "title": "四個建議，依序降低導入風險", "subtitle": "先完成可以被量測的小規模改變，再決定是否擴張。",
            "recommendations": [(f"{i:02d}", title, body, stage) for i, (title, body, stage) in enumerate(story["recommendations"], 1)],
            "rationale": "排序原則：先處理共同入口與驗收方式，再擴大到更多區域與角色。",
        }
    elif strategy_id == "strategic-priorities":
        store.CONTENT_CONTENT[strategy_id] = {
            "title": "三項優先，決定資源先落在哪裡", "subtitle": "同時比較影響、依賴與最短可驗證時間。",
            "priorities": [(f"{i:02d}", title, body, tag, allocation) for i, (title, body, tag, allocation) in enumerate(story["priorities"], 1)],
            "impact": "資源先投入能改變整條系統的共同節點，而不是只修飾單一末端問題。",
        }
    elif strategy_id == "flow-stages-3":
        store.SEQUENCE_CONTENT[strategy_id] = {
            "title": "三個階段，把現場觀察變成可驗證行動", "subtitle": "每個階段只保留一個清楚輸出。",
            "stages": [(f"{i:02d}", title, body, tag) for i, (title, body, tag, _) in enumerate(story["priorities"], 1)],
            "takeaway": "重點不是增加流程，而是讓每一步都留下下一步能直接使用的輸入。",
        }
    else:
        store.MODULES_CONTENT[strategy_id] = {
            "title": "三個模組，撐起第一輪正式試驗", "subtitle": "每個模組可獨立驗收，也能組成完整系統。",
            "items": [(title, body, tag) for title, body, tag, _ in story["priorities"]],
        }

    if relationship_id == "cycle-hub-6":
        store.DIAGRAM_CONTENT[relationship_id] = {
            "title": "六步形成\n持續學習循環", "subtitle": "每一輪結果都會改變下一輪輸入",
            "items": [(f"{i:02d}", title, body) for i, (title, body) in enumerate(story["cycle"], 1)],
        }
    elif relationship_id == "before-after":
        before, after = story["before"], story["after"]
        store.COMPARISON_CONTENT[relationship_id] = {
            "before": ("BEFORE · 現在", before[0], before[1], before[3]),
            "after": ("AFTER · 新系統", after[0], after[1], after[3]),
        }
    elif relationship_id == "matrix-4quadrant":
        store.COMPARISON_CONTENT[relationship_id] = {
            "title": "用影響與證據，判斷下一步該做什麼",
            "axes": ("證據弱", "證據強", "影響低", "影響高"),
            "quadrants": story["matrix"],
        }
    else:
        before, after = story["before"], story["after"]
        store.COMPARISON_CONTENT[relationship_id] = {
            "title": "同一個問題，可以產生兩種完全不同的行動",
            "left": ("× 舊路徑", before[1], before[3]),
            "right": ("✓ 新路徑", after[1], after[3]),
        }

    if evidence_id == "kpi-scorecards":
        store.METRICS_CONTENT[evidence_id] = {
            "title": "四個數字，驗收第一輪試驗", "subtitle": "數值為版型測試用模擬資料；重點是清楚標示口徑與行動意義。",
            "cards": story["metrics"],
            "takeaway": "數字不是裝飾；每一個指標都必須連到下一個保留、調整或停止決定。",
        }
    elif evidence_id == "stats-3-row":
        store.METRICS_CONTENT[evidence_id] = {
            "eyebrow": "PILOT SIGNAL · 第一輪試驗成績單",
            "stats": [(value, label, body) for value, label, body, _ in story["metrics"][:3]],
            "footnote": "數值為版型測試用模擬資料；正式使用時需補入來源、期間與統計口徑。",
        }
    else:
        store.DATAVIZ_CONTENT[evidence_id] = {
            "title": "七個觀察週期，看見三項能力同步變化",
            "labels": ["R1", "R2", "R3", "R4", "R5", "R6", "R7"],
            "series": story["chart"],
        }

    if sequence_id == "process-flow":
        store.SEQUENCE_CONTENT[sequence_id] = {
            "title": "五個關卡，把一次嘗試變成可追蹤決定", "subtitle": "節點之間有明確輸入輸出，不能用一張漂亮結論跳過中間驗證。",
            "steps": [(f"{i:02d}", title, body) for i, (title, body) in enumerate(story["process"], 1)],
            "note": "若關鍵證據缺失，流程應回到前一個節點，而不是直接補上一個看似確定的答案。",
        }
    elif sequence_id == "timeline-vertical":
        store.SEQUENCE_CONTENT[sequence_id] = {
            "title": "五次轉折，讓試驗逐步長成共同系統", "events": story["timeline"],
        }
    elif sequence_id == "timeline-milestones":
        store.SEQUENCE_CONTENT[sequence_id] = {
            "title": "六個里程碑，逐步建立可持續運作能力",
            "subtitle": "每個節點只保留一個可以被驗收的成果。",
            "milestones": [(label, title) for label, title, _ in story["timeline"]] + [("NEXT", "下一輪擴張")],
        }
    else:
        store.SEQUENCE_CONTENT[sequence_id] = {
            "title": "十二週完成第一輪場域驗證", "subtitle": "先建立基準，再測試、調整並決定是否擴張。",
            "periods": ["W1–2", "W3–4", "W5–6", "W7–8", "W9–10", "W11–12"],
            "tasks": [(title, index, 2 if index < 4 else 1, "done" if index == 0 else "active" if index < 3 else "next") for index, (title, _) in enumerate(story["process"])],
            "footnote": "每個階段都必須保留基準、結果與下一步判斷。",
        }

    if statement_id == "quote-focus":
        store.STATEMENT_CONTENT[statement_id] = {"quote": story["quote"], "attribution": f"— {story['attribution']}"}
    elif statement_id == "highlight-callout":
        store.STATEMENT_CONTENT[statement_id] = {
            "title": "三個轉折，讓試驗逐步長成可複製的方法",
            "chart": ("近六週採用率", [34, 41, 53, 61, 76, 88], ["W1", "W2", "W3", "W4", "W5", "W6"]),
            "callouts": [(f"{index:02d}", title, body) for index, (title, body, _, _) in enumerate(story["priorities"][:3], 1)],
        }
    elif statement_id == "quote-attribution-3":
        store.STATEMENT_CONTENT[statement_id] = {
            "title": "三種角色，用同一套現場訊號判斷下一步",
            "quotes": [
                (story["quote"], story["attribution"], "計畫主持人"),
                (story["priorities"][0][1], "現場團隊", "第一線執行"),
                (story["closing"][1], "資料團隊", "追蹤與回寫"),
            ],
        }
    elif statement_id == "chapter-number-bg-left-title-rule":
        label, title, subtitle, number = story["chapter"]
        store.CHAPTER_CONTENT[statement_id] = {"label": label, "title": title, "subtitle": subtitle, "number": number}

    closing_title, closing_body = story["closing"]
    store.STATEMENT_CONTENT[HTML_LAYOUT_CATALOG["fallbacks"]["closing"]] = {
        "headline": closing_title,
        "support": closing_body,
    }


def _apply_extended_story(
    story: dict[str, Any],
    layout_ids: list[str],
    store: Any | None = None,
) -> None:
    store = store or production
    selected = set(layout_ids)
    toc = story["toc"]
    priorities = story["priorities"]
    metrics = story["metrics"]
    timeline = story["timeline"]

    if "chapter-opener" in selected:
        label, title, subtitle, number = story["chapter"]
        store.CHAPTER_CONTENT["chapter-opener"] = {
            "label": label, "title": title, "subtitle": subtitle, "number": number,
        }

    if "funnel-4" in selected:
        ratios = ["100%", "68%", "42%", "24%"]
        store.DIAGRAM_CONTENT["funnel-4"] = {
            "title": "四層收斂，讓關注逐步變成行動",
            "items": [
                (toc[index][0], metrics[index][0], ratios[index], toc[index][1])
                for index in range(4)
            ],
        }
    if "org-chart" in selected:
        store.DIAGRAM_CONTENT["org-chart"] = {
            "title": "一個共同目標，三條清楚責任線",
            "root": (story["speaker"], "統一目標、分工、資訊入口與驗收節奏"),
            "children": [
                (title, body, allocation) for title, body, _, allocation in priorities
            ],
            "note": f"共同節奏：{timeline[0][0]} 建立基準，{timeline[-1][0]} 完成回寫",
        }
    if "pyramid" in selected:
        store.DIAGRAM_CONTENT["pyramid"] = {
            "title": "五層能力，從現場基礎走向可持續成果",
            "items": [
                (f"{5 - index:02d}", title, body)
                for index, (title, body) in enumerate(reversed(toc[:5]))
            ],
        }

    if "comparison-table" in selected:
        store.COMPARISON_CONTENT["comparison-table"] = {
            "title": "三種推進方式，哪一種能留下長期能力？",
            "subtitle": story["subtitle"],
            "columns": ["比較基準", "臨時處理", "單次專案", "共同系統"],
            "rows": [
                (toc[index][0], "低", "中", "高") for index in range(4)
            ],
            "note": f"建議：先從「{priorities[0][0]}」建立共同入口，再逐步擴張。",
        }
    if "pricing-3col" in selected:
        store.COMPARISON_CONTENT["pricing-3col"] = {
            "title": "三種參與層級，對應不同投入與回報",
            "tiers": [
                (
                    ("START", "CORE", "SIGNATURE")[index],
                    allocation,
                    title,
                    [body, toc[index][1], f"驗收：{metrics[index][1]}"],
                    ("先行體驗", "建議方案", "深度合作")[index],
                )
                for index, (title, body, _, allocation) in enumerate(priorities)
            ],
        }
    if "swot-quadrant" in selected:
        letters = ["S", "W", "O", "T"]
        labels = ["STRENGTHS", "WEAKNESSES", "OPPORTUNITIES", "THREATS"]
        store.COMPARISON_CONTENT["swot-quadrant"] = {
            "title": f"{story['chapter'][1]}的四個推進條件",
            "subtitle": "把內部能力、限制與外部機會放進同一個判斷框架。",
            "quadrants": [
                (letters[index], labels[index], [story["matrix"][index][1], toc[index][1], priorities[index % 3][1]])
                for index in range(4)
            ],
        }

    if "dashboard-overview" in selected:
        store.METRICS_CONTENT["dashboard-overview"] = {
            "title": f"{priorities[0][0]} · 本期運作概況",
            "subtitle": story["org"],
            "kpis": [(label, value, delta) for value, label, _, delta in metrics],
            "chart": {
                "title": f"{story['chart'][0][0]}連續七期變化",
                "metric": metrics[0][0],
                "bars": story["chart"][0][1],
                "labels": [f"R{index}" for index in range(1, 8)],
            },
            "insight": ("本期洞察", priorities[0][0], [item[1] for item in priorities]),
            "footnote": "數值為 Theme Lab 內容測試資料；正式使用時需補上來源與口徑。",
        }

    if "data-annotation" in selected:
        store.DATAVIZ_CONTENT["data-annotation"] = {
            "title": f"兩次關鍵調整，改變{story['chart'][0][0]}走勢",
            "values": story["chart"][0][1] + [min(96, story["chart"][0][1][-1] + 5)],
            "labels": [f"R{index}" for index in range(1, 9)],
            "annotations": [(2, timeline[1][1], "+8pt"), (5, timeline[3][1], "+11pt")],
        }
    if "heat-map" in selected:
        store.DATAVIZ_CONTENT["heat-map"] = {
            "title": "五個工作面向，在六項能力上的成熟度分布",
            "columns": [title for title, _ in toc[:6]],
            "rows": [item[0] for item in priorities] + ["基準", "擴張"],
            "values": [
                [((row * 2 + column + int(story["chapter"][3])) % 5) + 1 for column in range(6)]
                for row in range(5)
            ],
        }
    if "map-region" in selected:
        store.DATAVIZ_CONTENT["map-region"] = {
            "title": "三個場域的推進成熟度已出現明顯差異",
            "cards": [
                (timeline[index][0], metrics[index][0], priorities[index][0]) for index in range(3)
            ],
        }
    if "map-spotlight" in selected:
        store.DATAVIZ_CONTENT["map-spotlight"] = {
            "title": "三個節點，分別承擔內容、行動與驗證角色",
            "locations": [
                (timeline[index][0], timeline[index][1], priorities[index][2]) for index in range(3)
            ],
        }
    if "radar-chart" in selected:
        store.DATAVIZ_CONTENT["radar-chart"] = {
            "title": "新方法提升整體能力，差距仍集中在最後兩項",
            "axes": [title for title, _ in toc[:6]],
            "series": [("導入前", [2, 2, 3, 2, 1, 2]), ("導入後", [4, 5, 4, 5, 3, 4])],
        }

    if "icon-grid-6" in selected:
        store.ICON_GRID_CONTENT.update({
            "title": "六個內容入口，組成這份專案的完整閱讀路徑",
            "items": [(title, f"{index:02d}") for index, (title, _) in enumerate(toc[:6], 1)],
        })


def apply_story_to_layouts(
    story: dict[str, Any],
    layout_ids: list[str],
    store: Any | None = None,
) -> Any:
    """Populate every selected semantic layout regardless of slide order."""
    store = store or production
    defaults = [
        HTML_LAYOUT_CATALOG["fallbacks"]["cover"],
        "toc-6",
        "recommendation-stack",
        "before-after",
        "kpi-scorecards",
        "process-flow",
        "quote-focus",
        HTML_LAYOUT_CATALOG["fallbacks"]["closing"],
    ]
    apply_story(story, defaults, store)
    role_pools = [
        set(COVER_LAYOUTS),
        {layout_id for layout_id in layout_ids if layout_id.startswith("toc-")},
        set(STRATEGY_LAYOUTS),
        set(RELATIONSHIP_LAYOUTS),
        set(EVIDENCE_LAYOUTS),
        set(SEQUENCE_LAYOUTS),
        set(STATEMENT_LAYOUTS),
        {HTML_LAYOUT_CATALOG["fallbacks"]["closing"]},
    ]
    for layout_id in layout_ids:
        for role_index, pool in enumerate(role_pools):
            if layout_id not in pool:
                continue
            role_layouts = defaults.copy()
            role_layouts[role_index] = layout_id
            apply_story(story, role_layouts, store)
            break
    _apply_extended_story(story, layout_ids, store)
    return store


def load_story_file(path: Path) -> dict[str, Any]:
    """Load one external content manifest into the shared semantic story model."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    concept = payload.get("concept")
    if not isinstance(concept, dict):
        raise ValueError(f"Story file must contain a 'concept' object: {path}")

    required = {
        "story_id", "title", "subtitle", "toc", "priorities",
        "metrics", "timeline", "quote", "closing", "chapter_number",
    }
    missing = sorted(required - set(concept))
    if missing:
        raise ValueError(f"Story file is missing concept fields: {missing}")

    story = _concept_story(
        **{key: concept[key] for key in required},
        speaker=str(concept.get("speaker") or ""),
        org=str(concept.get("org") or ""),
        attribution=str(concept.get("attribution") or ""),
    )
    # The helper supplies defaults for omitted optional fields, but an external
    # content manifest is authoritative for every field it explicitly sends.
    # Do not replace user-provided matrix/cycle/process/people data with demo
    # fixtures merely because those fields are not in the minimum contract.
    for key, value in concept.items():
        if key == "story_id":
            story["id"] = value
        else:
            story[key] = value
    story["layout_content"] = payload.get("layout_content", {})
    story["toc_context"] = payload.get("toc_context", {})
    page_compositions = payload.get("page_compositions", {})
    if not isinstance(page_compositions, dict):
        raise ValueError(f"Story file page_compositions must be an object: {path}")
    story["page_compositions"] = page_compositions
    if isinstance(payload.get("content_plan"), list):
        story["content_plan"] = payload["content_plan"]
    if isinstance(payload.get("slide_plan"), list):
        story["slide_plan"] = payload["slide_plan"]
    story["content_manifest"] = str(path)
    return story


def apply_story_context(story: dict[str, Any], store: Any | None = None) -> None:
    """Apply page-independent editorial context to an isolated composition."""

    store = store or production
    if story.get("toc_context"):
        store.TOC_CONTEXT.update(story["toc_context"])


def apply_legacy_layout_content_overrides(
    story: dict[str, Any],
    store: Any | None = None,
) -> None:
    """Compatibility adapter for explicit historical layout-keyed manifests."""

    store = store or production

    targets: dict[str, dict[str, dict[str, Any]]] = {
        "cover": store.COVER_CONTENT,
        "chapter": store.CHAPTER_CONTENT,
        "modules": store.MODULES_CONTENT,
        "diagram": store.DIAGRAM_CONTENT,
        "comparison": store.COMPARISON_CONTENT,
        "metrics": store.METRICS_CONTENT,
        "dataviz": store.DATAVIZ_CONTENT,
        "sequence": store.SEQUENCE_CONTENT,
        "content": store.CONTENT_CONTENT,
        "closing": store.CLOSING_CONTENT,
        "media": store.MEDIA_CONTENT,
        "statement": store.STATEMENT_CONTENT,
    }
    for layout_id, content in story.get("layout_content", {}).items():
        family = layout_family(layout_id)
        target = targets.get(family)
        if target is None:
            raise ValueError(f"External story does not support layout override: {layout_id}")
        if not isinstance(content, dict):
            raise ValueError(f"Layout override must be an object: {layout_id}")
        target[layout_id] = content


def build_semantic_pages(
    story: dict[str, Any],
    content_plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Materialize page-keyed content without storing any Layout identity."""

    pages: list[dict[str, Any]] = []
    for entry in content_plan:
        intent = entry["intent"]
        authored_payload = (story.get("page_compositions") or {}).get(entry["page_id"])
        if authored_payload is not None:
            if not isinstance(authored_payload, dict):
                raise ValueError(
                    f"Page composition must be an object: {entry['page_id']}"
                )
            payload = dict(authored_payload)
        elif intent == "cover":
            payload = {
                "title": story["title"],
                "subtitle": story["subtitle"],
                "speaker": "",
                "org": "",
            }
            for optional_key in ("speaker", "org", "kicker"):
                optional_value = str(story.get(optional_key) or "").strip()
                if optional_value:
                    payload[optional_key] = optional_value
        elif intent == "navigation":
            context = story.get("toc_context") or {}
            payload = {
                "title": context.get("title") or f"{len(story['toc'])} 個章節，串起完整閱讀路徑",
                "intro": context.get("intro") or story["subtitle"],
                "footer": context.get("footer") or "",
                "index_label": context.get("index_label") or "",
                "items": numbered(story["toc"]),
            }
        elif intent == "distribution":
            matrix = list(story.get("matrix") or [])
            if not matrix:
                raise ValueError(f"Distribution page has no matrix content: {entry['page_id']}")
            toc_items = list(story.get("toc") or [])
            payload = {
                "title": entry.get("title") or story["title"],
                "matrix": matrix,
                "columns": [
                    str(item[0])
                    for item in toc_items[:4]
                    if isinstance(item, (list, tuple)) and item
                ],
                "rows": [
                    str(item[0]) if isinstance(item, (list, tuple)) and item else f"第 {index:02d} 列"
                    for index, item in enumerate(matrix, 1)
                ],
                "values": [
                    [1 + ((row_index * 2 + column_index) % 5) for column_index in range(4)]
                    for row_index, _ in enumerate(matrix)
                ],
                "value_note": "",
            }
        elif intent == "modules":
            priorities = list(story.get("priorities") or [])
            if not priorities:
                raise ValueError(f"Modules page has no module content: {entry['page_id']}")
            payload = {
                "title": entry.get("title") or story["title"],
                "subtitle": story["subtitle"],
                "items": priorities,
            }
        elif intent == "cycle":
            cycle = list(story.get("cycle") or [])
            if not cycle:
                raise ValueError(f"Cycle page has no cycle content: {entry['page_id']}")
            payload = {
                "title": entry.get("title") or story["title"],
                "subtitle": story["subtitle"],
                "items": [
                    (f"{index:02d}", title, body)
                    for index, (title, body) in enumerate(cycle, 1)
                ],
            }
        elif intent == "prioritization":
            first_priority = story["priorities"][0]
            payload = {
                "title": f"先從「{first_priority[0]}」開始，建立可驗證的推進順序",
                "subtitle": "依影響、依賴與可驗證時間安排先後，不把所有工作同時展開。",
                "items": list(story["priorities"]),
                "recommendations": list(story["recommendations"]),
                "matrix": list(story["matrix"]),
                "axes": ("證據弱", "證據強", "影響低", "影響高"),
                "conclusion": first_priority[1],
            }
        elif intent == "comparison":
            before, after = story["before"], story["after"]
            payload = {
                "claim": story["title"],
                "title": f"從「{before[0]}」走向「{after[0]}」",
                "subtitle": f"{before[2]}；{after[2]}",
                "before": before,
                "after": after,
                "left_labels": [item[0] for item in story["toc"][:3]],
                "right_labels": [item[0] for item in story["priorities"][:3]],
                "takeaway": story["closing"][1],
            }
        elif intent == "evidence":
            first_metric = story["metrics"][0]
            payload = {
                "title": f"{first_metric[0]} {first_metric[1]}，成為第一個可驗證訊號",
                "subtitle": "每個數字都保留口徑、觀察意義與下一步判斷。",
                "metrics": list(story["metrics"]),
                "chart": list(story["chart"]),
                "labels": [f"R{index}" for index in range(1, len(story["chart"][0][1]) + 1)],
                "conclusion": first_metric[2],
                "takeaway": story["closing"][1],
                "footnote": "正式使用時請補上來源、期間與量測口徑。",
            }
        elif intent == "sequence":
            process = list(story["process"])
            payload = {
                "title": f"從「{process[0][0]}」走到「{process[-1][0]}」",
                "subtitle": "每一步都留下下一步能直接使用的輸入與驗收條件。",
                "process": process,
                "timeline": list(story["timeline"]),
                "conclusion": process[-1][1],
            }
        elif intent == "statement":
            payload = {
                "quote": story["quote"],
                "attribution": story["attribution"],
            }
        elif intent == "closing":
            headline, support = story["closing"]
            payload = {"headline": headline, "support": support}
        else:
            payload = {
                field: story[field]
                for field in entry["source_fields"]
                if field in story
            }
        content_sha256 = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        pages.append({
            "page_id": entry["page_id"],
            "intent": entry["intent"],
            "content_key": entry["content_key"],
            "content_relation": entry["content_relation"],
            "content_item_count": entry.get("content_item_count"),
            "source_fields": list(entry["source_fields"]),
            "content_sha256": content_sha256,
            "payload": payload,
        })
    return pages


def _primary_page_items(semantic_page: dict[str, Any]) -> list[Any] | None:
    payload = semantic_page["payload"]
    intent = semantic_page["intent"]
    if intent == "distribution":
        return list(payload.get("matrix") or [])
    if intent == "cycle":
        return list(payload.get("items") or [])
    if intent == "modules":
        source = payload.get("people") or payload.get("members") or payload.get("items")
        return list(source or [])
    return None


def _is_attributed_testimonial_payload(payload: dict[str, Any]) -> bool:
    """A testimonial is a person's attributable statement, not a deck footer."""
    return all(str(payload.get(field) or "").strip() for field in ("quote", "name", "role"))


def _reroute_statement_without_person_identity(
    decision: dict[str, Any],
    semantic_page: dict[str, Any],
) -> None:
    """Keep an editorial statement editorial when the person fields are absent."""
    if decision["layout_id"] != "testimonial-full":
        return
    if _is_attributed_testimonial_payload(semantic_page["payload"]):
        return
    requested_layout = decision["layout_id"]
    decision.update({
        "requested_layout_id": requested_layout,
        "layout_id": "quote-focus",
        "source": "content-shape-reroute",
        "selection_basis": "statement-without-testimonial-identity",
        "selection_candidates": ["quote-focus"],
        "route_match": True,
        "media_requirement": HTML_LAYOUT_CATALOG["media_requirement_by_layout_id"]["quote-focus"],
        "composition_variant": "quote-focus-native",
        "header_mode": "layout-defined",
        "surface_mode": "layout-defined",
        "variant_source": "content-shape-reroute",
    })
    feedback = decision.setdefault("composition_feedback", {})
    feedback.update({
        "requested_layout_id": requested_layout,
        "resolved_layout_id": "quote-focus",
        "remediation_applied": "statement-without-person-identity-reroute",
        "required_testimonial_fields": ["quote", "name", "role"],
    })


def _content_preserving_card_layout(item_count: int) -> str:
    layout_id = CONTENT_PRESERVING_CARD_LAYOUT.get(item_count)
    if layout_id is None:
        raise ValueError(
            "No single-page module composition preserves all items: "
            f"received {item_count}; split the page or provide an explicit integration plan"
        )
    return layout_id


def reconcile_layout_plan_with_content(
    layout_plan: list[dict[str, Any]],
    semantic_pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Reroute fixed-capacity scaffolds without dropping primary content."""

    for semantic_page, decision in zip(semantic_pages, layout_plan):
        _reroute_statement_without_person_identity(decision, semantic_page)
        primary_items = _primary_page_items(semantic_page)
        if primary_items is None:
            continue
        item_count = len(primary_items)
        if item_count == 0:
            raise ValueError(f"Content page has no primary items: {semantic_page['page_id']}")

        layout_id = decision["layout_id"]
        reroute = False
        if layout_id in MODULE_LAYOUT_CAPACITY:
            reroute = MODULE_LAYOUT_CAPACITY[layout_id] != item_count
        elif layout_id == "matrix-4quadrant":
            reroute = item_count != 4
        elif layout_id == "cycle-hub-6":
            reroute = item_count != 6
        elif layout_id in {"map-region", "map-spotlight"}:
            reroute = item_count > 3
        elif layout_id == "people-3":
            reroute = item_count != 3
        elif layout_id == "team-grid":
            reroute = item_count > 6
        elif layout_id == "executive-bio":
            reroute = item_count != 1

        feedback = decision.setdefault("composition_feedback", {})
        feedback["content_item_count"] = item_count
        if not reroute:
            continue

        resolved_layout = _content_preserving_card_layout(item_count)
        decision.update({
            "requested_layout_id": layout_id,
            "layout_id": resolved_layout,
            "source": "content-preserving-capacity-reroute",
            "selection_basis": "content-preserving-capacity-reroute",
            "selection_candidates": [resolved_layout],
            "route_match": True,
            "content_reframe": "modules",
            "media_requirement": HTML_LAYOUT_CATALOG["media_requirement_by_layout_id"][resolved_layout],
            "composition_variant": f"{resolved_layout}-native",
            "header_mode": "layout-defined",
            "surface_mode": "layout-defined",
            "variant_source": "content-preserving-layout-native",
        })
        feedback.update({
            "requested_layout_id": layout_id,
            "resolved_layout_id": resolved_layout,
            "remediation_applied": "alternate-capacity-compatible-scaffold",
            "all_primary_items_required": True,
        })
    return layout_plan


def _normalise_module_items(payload: dict[str, Any], intent: str) -> list[tuple[str, str, str]]:
    if intent == "distribution":
        source = list(payload.get("matrix") or [])
    elif intent == "cycle":
        source = list(payload.get("items") or [])
    else:
        source = list(payload.get("people") or payload.get("members") or payload.get("items") or [])

    items: list[tuple[str, str, str]] = []
    for index, item in enumerate(source, 1):
        if isinstance(item, dict):
            title = item.get("name") or item.get("title") or item.get("label")
            if not title:
                raise ValueError(f"Module item {index} is missing a source-backed title")
            body_parts = [item.get(key) for key in ("role", "body", "note", "description", "bio")]
            body = " · ".join(str(value) for value in body_parts if value not in (None, ""))
            tag = item.get("tag") or item.get("value") or item.get("metric") or ""
        else:
            values = list(item) if isinstance(item, (list, tuple)) else [item]
            if intent == "cycle" and len(values) >= 3:
                tag, title, body = values[0], values[1], values[2]
            else:
                if not values or values[0] in (None, ""):
                    raise ValueError(f"Module item {index} is missing a source-backed title")
                title = values[0]
                body = values[1] if len(values) > 1 else ""
                tag = " · ".join(str(value) for value in values[2:] if value not in (None, ""))
        items.append((str(title), str(body), str(tag)))
    return items


def compose_page_content(
    story: dict[str, Any],
    semantic_page: dict[str, Any],
    decision: dict[str, Any],
    *,
    allow_legacy_layout_content: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind one page to a Layout scaffold without changing the page identity."""

    layout_id = decision["layout_id"]
    legacy_override = bool(
        allow_legacy_layout_content
        and isinstance(story.get("layout_content"), dict)
        and layout_id in story["layout_content"]
    )
    intent = semantic_page["intent"]
    payload = semantic_page["payload"]

    image_candidates = set(
        (HTML_DESIGN_METHOD.get("image_candidate_extensions") or {}).get(intent, [])
    )
    composition_source = "page-content-adapter"

    if layout_id == "infographic-stage":
        profile = (HTML_DESIGN_METHOD.get("page_composition_layouts") or {}).get(layout_id) or {}
        eligible_intents = set(profile.get("eligible_intents") or [])
        if intent not in eligible_intents:
            raise ValueError(f"{layout_id} does not accept content intent {intent}")
        required_fields = set(profile.get("requires_payload_fields") or [])
        missing_fields = sorted(required_fields - set(payload))
        if missing_fields:
            raise ValueError(
                f"{layout_id} requires a page-authored Composition; missing {missing_fields}"
            )
        content = dict(payload)
        composition_source = "page-authored-infographic-scene"
        decision.update({
            "route_match": True,
            "selection_basis": "page-authored-composition",
            "signature_composition": content["signature_composition"],
            "ordinary_grid_loss": content["ordinary_grid_loss"],
            "content_composition_intent": content["composition_intent"],
            "reading_path": content["reading_path"],
        })
    elif legacy_override:
        content = story["layout_content"][layout_id]
        composition_source = "legacy-layout-content-compatibility"
    elif intent == "cover" and layout_id in COVER_LAYOUTS:
        content = dict(payload)
    elif intent == "cover" and layout_id in image_candidates:
        content = dict(payload)
    elif intent == "navigation" and layout_id.startswith("toc-"):
        content = dict(payload)
    elif intent == "distribution" and layout_id == "matrix-4quadrant":
        matrix_items = list(payload.get("matrix") or [])
        if len(matrix_items) != 4:
            raise ValueError(f"{layout_id} requires exactly four matrix items; received {len(matrix_items)}")
        quadrants = []
        for index, item in enumerate(matrix_items, 1):
            if isinstance(item, dict):
                label = item.get("label") or item.get("title") or f"第 {index:02d} 區"
                body = item.get("body") or item.get("note") or item.get("description") or ""
            else:
                values = list(item) if isinstance(item, (list, tuple)) else [item]
                label = values[0] if values else f"第 {index:02d} 區"
                body = values[1] if len(values) > 1 else ""
            quadrants.append((label, body))
        content = {
            "title": payload.get("title") or story["title"],
            "axes": ("訊號較低", "訊號較高", "影響較低", "影響較高"),
            "quadrants": quadrants,
        }
    elif intent == "distribution" and layout_id == "heat-map":
        content = {
            "title": payload.get("title") or story["title"],
            "columns": payload.get("columns") or ["01", "02", "03", "04"],
            "rows": payload.get("rows") or ["第 01 列", "第 02 列", "第 03 列", "第 04 列"],
            "values": payload.get("values") or [
                [1, 2, 3, 4],
                [2, 3, 4, 5],
                [3, 4, 5, 1],
                [4, 5, 1, 2],
            ],
        }
    elif layout_id in MODULE_LAYOUT_CAPACITY and (
        intent == "modules" or decision.get("content_reframe") == "modules"
    ):
        items = _normalise_module_items(payload, intent)
        if not items:
            raise ValueError(f"{layout_id} requires module content")
        content = {
            "title": payload.get("title") or story["title"],
            "subtitle": payload.get("subtitle") or story.get("subtitle") or "完整保留每一筆內容",
            "items": items,
        }
    elif intent == "cycle" and layout_id == "cycle-hub-6":
        items = list(payload.get("items") or [])
        if not items:
            raise ValueError(f"{layout_id} requires cycle content")
        # The hub carries one short title only; explanation belongs to the items.
        content = {
            "title": payload.get("title") or story["title"],
            "items": items,
        }
    elif intent == "distribution" and layout_id in {"map-region", "map-spotlight"}:
        matrix_items = list(payload.get("matrix") or [])
        if not matrix_items:
            raise ValueError(f"{layout_id} requires matrix or location content")
        rows = []
        for index, item in enumerate(matrix_items, 1):
            if isinstance(item, dict):
                label = item.get("label") or item.get("title") or f"第 {index:02d} 區"
                value = item.get("value") or item.get("metric") or f"{index:02d}"
                note = item.get("note") or item.get("body") or ""
            else:
                values = list(item) if isinstance(item, (list, tuple)) else [item]
                label = values[0] if values else f"第 {index:02d} 區"
                value = values[1] if len(values) > 2 else f"{index:02d}"
                note = values[-1] if len(values) > 1 else ""
            rows.append((label, value, note))
        content = {
            "title": payload.get("title") or str(rows[0][0]),
            "locations" if layout_id == "map-spotlight" else "cards": rows,
        }
        if payload.get("map_image_src"):
            content["map_image_src"] = payload["map_image_src"]
        if payload.get("map_caption") or payload.get("caption"):
            content["map_caption"] = payload.get("map_caption") or payload.get("caption")
    elif intent == "modules" and layout_id in {"executive-bio", "people-3", "team-grid"}:
        source_people = payload.get("people") or payload.get("members") or payload.get("items") or []
        if not source_people:
            raise ValueError(f"{layout_id} requires people or member content")
        people = []
        for index, item in enumerate(source_people, 1):
            if isinstance(item, dict):
                name = item.get("name") or item.get("title") or f"人物 {index:02d}"
                role = item.get("role") or item.get("subtitle") or ""
                bio = item.get("bio") or item.get("body") or ""
            else:
                values = list(item) if isinstance(item, (list, tuple)) else [item]
                name = values[0] if values else f"人物 {index:02d}"
                role = values[1] if len(values) > 1 else ""
                bio = values[2] if len(values) > 2 else ""
            people.append((name, role, bio))
        title = payload.get("title") or "團隊與角色"
        if layout_id == "people-3":
            content = {"title": title, "people": people}
        elif layout_id == "team-grid":
            content = {"title": title, "members": [(name, role) for name, role, _ in people]}
        else:
            name, role, bio = people[0]
            bio_lines = [line for line in str(bio).splitlines() if line.strip()] or [str(bio)]
            content = {
                "name": name,
                "role": role,
                "bio": bio_lines,
                "meta": payload.get("meta") or "",
                "panel_label": payload.get("panel_label") or "",
                "photo_label": payload.get("photo_label") or "",
            }
    elif intent == "prioritization" and layout_id == "strategic-priorities":
        content = {
            "title": payload["title"],
            "subtitle": payload["subtitle"],
            "priorities": [
                (f"{index:02d}", title, body, tag, allocation)
                for index, (title, body, tag, allocation) in enumerate(payload["items"], 1)
            ],
            "impact": payload["conclusion"],
        }
    elif intent == "prioritization" and layout_id == "recommendation-stack":
        content = {
            "title": payload["title"],
            "subtitle": payload["subtitle"],
            "recommendations": [
                (f"{index:02d}", title, body, tag)
                for index, (title, body, tag, _) in enumerate(payload["items"], 1)
            ],
            "rationale": payload["conclusion"],
        }
    elif intent == "comparison" and layout_id == "before-after":
        before, after = payload["before"], payload["after"]
        content = {
            "before": (before[0], before[1], before[2], before[3]),
            "after": (after[0], after[1], after[2], after[3]),
        }
    elif intent == "comparison" and layout_id == "split-comparison":
        before, after = payload["before"], payload["after"]
        content = {
            "title": payload["title"],
            "left": (before[0], before[1], before[3]),
            "right": (after[0], after[1], after[3]),
        }
    elif intent == "evidence" and layout_id == "dashboard-overview":
        first_series_name, first_series = payload["chart"][0]
        content = {
            "title": payload["title"],
            "subtitle": payload["subtitle"],
            "kpis": [(label, value, delta) for value, label, _, delta in payload["metrics"]],
            "chart": {
                "kicker": payload.get("chart_kicker") or "",
                "title": first_series_name,
                "metric": payload["metrics"][0][0],
                "bars": first_series,
                "labels": payload["labels"],
            },
            "insight": (
                "判讀",
                payload["conclusion"],
                [note for _, _, note, _ in payload["metrics"][:3]],
            ),
            "footnote": payload["footnote"],
        }
    elif intent == "evidence" and layout_id == "kpi-scorecards":
        content = {
            "title": payload["title"],
            "subtitle": payload["subtitle"],
            "cards": payload["metrics"],
            "takeaway": payload.get("takeaway"),
        }
    elif intent == "evidence" and layout_id == "stats-3-row":
        content = {
            "eyebrow": payload["title"],
            "stats": [(value, label, note) for value, label, note, _ in payload["metrics"]],
            "footnote": payload["footnote"],
        }
    elif intent == "evidence" and layout_id == "multi-line-chart":
        content = {
            "title": payload["title"],
            "labels": payload["labels"],
            "series": payload["chart"],
        }
    elif intent == "evidence" and layout_id == "data-annotation":
        metrics = payload["metrics"]
        content = {
            "title": payload["title"],
            "values": payload["chart"][0][1],
            "labels": payload["labels"],
            "annotations": [
                (2, metrics[1][1], metrics[1][3]),
                (5, metrics[2][1], metrics[2][3]),
            ],
        }
    elif intent == "evidence" and layout_id == "heat-map":
        values = [value for _, series in payload["chart"] for value in series]
        low, high = min(values), max(values)
        span = max(1, high - low)
        content = {
            "title": payload["title"],
            "columns": payload["labels"],
            "rows": [name for name, _ in payload["chart"]],
            "values": [
                [1 + round((value - low) * 4 / span) for value in series]
                for _, series in payload["chart"]
            ],
        }
    elif intent == "sequence" and layout_id == "process-flow":
        content = {
            "title": payload["title"],
            "subtitle": payload["subtitle"],
            "steps": [
                (f"{index:02d}", title, body)
                for index, (title, body) in enumerate(payload["process"], 1)
            ],
            "note": payload["conclusion"],
        }
    elif intent == "sequence" and layout_id == "flow-stages-3":
        timeline = payload["timeline"]
        content = {
            "title": payload["title"],
            "subtitle": payload["subtitle"],
            "stages": [
                (f"{index:02d}", title, body, timeline[(index - 1) % len(timeline)][0])
                for index, (title, body) in enumerate(payload["process"], 1)
            ],
            "takeaway": payload["conclusion"],
        }
    elif intent == "sequence" and layout_id == "timeline-milestones":
        content = {
            "title": payload["title"],
            "subtitle": payload["subtitle"],
            "milestones": payload["timeline"],
        }
    elif intent == "sequence" and layout_id == "timeline-vertical":
        content = {"title": payload["title"], "events": payload["timeline"]}
    elif intent == "sequence" and layout_id == "gantt-roadmap":
        content = {
            "title": payload["title"],
            "subtitle": payload["subtitle"],
            "periods": [label for label, _, _ in payload["timeline"]],
            "tasks": [
                (
                    title,
                    index,
                    1,
                    "done" if index == 0 else "active" if index < 3 else "next",
                )
                for index, (title, _) in enumerate(payload["process"])
            ],
            "footnote": payload["conclusion"],
        }
    elif intent == "statement" and layout_id == "quote-focus":
        attribution = str(payload.get("attribution") or "").strip()
        content = {
            "quote": payload["quote"],
            "attribution": f"— {attribution}" if attribution else "",
        }
    elif intent == "statement" and layout_id == "title-center":
        content = {
            "headline": payload["quote"],
            "support": payload["attribution"],
        }
    elif intent == "statement" and layout_id == "testimonial-full":
        if not _is_attributed_testimonial_payload(payload):
            raise ValueError(
                "testimonial-full requires quote, name, and role from page content; "
                "a generic attribution must route to quote-focus instead"
            )
        content = {
            "quote": payload["quote"],
            "name": payload["name"],
            "role": payload["role"],
            "logo": payload.get("logo") or "",
            "voice_label": payload.get("voice_label") or "",
        }
    elif intent == "statement" and layout_id in image_candidates:
        quote = payload["quote"]
        attribution = payload.get("attribution") or ""
        if layout_id == "photo-left-overlay-title-right":
            content = {
                "kicker": payload.get("kicker") or "",
                "title": attribution or story["title"],
                "body": quote,
                "photo_label": payload.get("photo_label") or "",
            }
        elif layout_id == "chapter-fullbleed-overlay-title":
            content = {
                "label": payload.get("label") or "",
                "title": quote,
                "subtitle": attribution,
                "number": str(story.get("chapter_number") or "01"),
            }
        else:
            content = {
                "label": payload.get("label") or "",
                "title": attribution or story["title"],
                "body": quote,
                "brand": payload.get("brand") or "",
                "brand_note": payload.get("brand_note") or "",
                "brand_mark": payload.get("brand_mark") or "",
            }
    elif intent == "closing" and layout_id == "title-center":
        content = dict(payload)
    elif intent == "closing" and layout_id == "quote-focus":
        content = {
            "quote": payload["headline"],
            "attribution": payload["support"],
        }
    elif intent == "closing" and layout_id == "closing-photo-overlay-contact":
        content = {
            "kicker": payload.get("kicker") or "",
            "title": payload["headline"],
            "body": payload["support"],
            "contact": [],
            "social": [],
        }
    else:
        raise ValueError(
            f"Layout scaffold has no page-composition adapter: {layout_id} "
            f"for content intent {intent}"
        )

    rendered_item_count = next(
        (
            len(content[key])
            for key in (
                "items", "priorities", "recommendations", "cards", "stats",
                "steps", "stages", "milestones", "events", "tasks",
                "people", "members", "locations", "quadrants",
            )
            if isinstance(content.get(key), list)
        ),
        None,
    )
    if rendered_item_count is None and isinstance(content.get("scene"), dict):
        scene_objects = content["scene"].get("objects")
        if isinstance(scene_objects, list):
            rendered_item_count = len(scene_objects)

    input_item_count = len(_primary_page_items(semantic_page) or []) or None
    if (
        input_item_count is not None
        and rendered_item_count is not None
        and input_item_count != rendered_item_count
    ):
        raise ValueError(
            "Content conservation failure: "
            f"page={semantic_page['page_id']}, input={input_item_count}, "
            f"rendered={rendered_item_count}, layout={layout_id}"
        )
    mutation_ledger = list(payload.get("mutation_ledger") or [])
    feedback = dict(decision["composition_feedback"])
    feedback.update({
        "content_page_id": semantic_page["page_id"],
        "content_sha256": semantic_page["content_sha256"],
        "layout_scaffold_id": layout_id,
        "layout_role": "scaffold",
        "composition_source": composition_source,
        "input_item_count": input_item_count,
        "rendered_item_count": rendered_item_count,
        "content_identity_preserved": not bool(mutation_ledger),
        "content_mutated": bool(mutation_ledger),
        "mutation_ledger": mutation_ledger,
    })
    if layout_id == "infographic-stage":
        scene = content["scene"]
        feedback.update({
            "scene_id": scene.get("id") or "authored-scene",
            "scene_object_count": len(scene.get("objects") or []),
            "composition_intent": content["composition_intent"],
            "reading_path": content["reading_path"],
            "signature_composition": content["signature_composition"],
            "ordinary_grid_loss": content["ordinary_grid_loss"],
            "geometry_source": "page-authored-composition",
        })
    return content, feedback


def assert_new_deck_forced_layout_routes(
    layout_plan: list[dict[str, Any]],
    *,
    content_mode: str,
    forced_layouts: list[str] | None,
) -> None:
    """Fail closed when a forced new-deck Layout violates semantic routing."""

    if content_mode != "new-deck" or not forced_layouts:
        return
    mismatches = [
        decision
        for decision in layout_plan
        if decision.get("route_match") is False
    ]
    if not mismatches:
        return
    details = "; ".join(
        (
            f"page={decision.get('content_page_id') or 'unknown'}, "
            f"intent={decision.get('intent') or 'unknown'}, "
            f"layout={decision.get('layout_id') or 'unknown'}"
        )
        for decision in mismatches
    )
    raise ValueError(
        "Forced Layout route mismatch in content_mode=new-deck "
        f"(route_match=false): {details}. "
        "Choose a Layout from the semantic route candidates or omit --layouts."
    )


def build(
    seed: int,
    matrix_path: Path,
    output_path: Path,
    forced_theme: str | None = None,
    forced_story_id: str | None = None,
    forced_layouts: list[str] | None = None,
    forced_story_file: Path | None = None,
    forced_style_case: str | None = None,
    forced_art_direction: Path | None = None,
    content_mode: str | None = None,
    layout_media_mode: str | None = None,
    asset_policy: str | None = None,
    layout_selection: str = "diverse",
    content_intent: str | None = None,
    allow_legacy_layout_content: bool = False,
) -> dict[str, Any]:
    rng = random.Random(seed)
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    resolved_content_mode = content_mode or ("preset-demo" if forced_style_case else "new-deck")
    if resolved_content_mode not in {"new-deck", "preset-demo"}:
        raise ValueError(f"Unknown HTML content mode: {resolved_content_mode}")
    if forced_style_case and resolved_content_mode != "preset-demo":
        raise ValueError("--style-case/--preset-demo requires content_mode=preset-demo")
    if resolved_content_mode == "preset-demo" and not forced_style_case:
        raise ValueError("content_mode=preset-demo requires --style-case/--preset-demo")
    preset_demo_mode = resolved_content_mode == "preset-demo"
    if resolved_content_mode == "new-deck" and allow_legacy_layout_content:
        raise ValueError(
            "--allow-legacy-layout-content cannot be combined with "
            "content_mode=new-deck; new-deck uses page content only"
        )
    if preset_demo_mode and allow_legacy_layout_content:
        raise ValueError(
            "--allow-legacy-layout-content is only for an explicit historical "
            "--story-file manifest; preset-demo uses its isolated fixture contract"
        )
    if forced_style_case and forced_art_direction:
        raise ValueError("--style-case and --art-direction cannot be combined")
    if forced_style_case and forced_style_case not in PRESET_DEMO_PROFILES:
        raise ValueError(f"Unknown HTML preset theme: {forced_style_case}")
    if forced_style_case:
        # Backward-compatible example command: only this legacy entry point
        # binds the accepted reference story/layout sequence.  Selecting the
        # same id through --theme keeps content and Layout independent.
        example_profile = PRESET_DEMO_PROFILES[forced_style_case]
        forced_theme = forced_style_case
        forced_story_id = example_profile["story"]
        forced_layouts = list(example_profile["layouts"])
        forced_story_file = None

    resolved_asset_policy = asset_policy or HTML_LAYOUT_CATALOG["default_asset_policy"]
    if asset_policy is None and forced_style_case and any(
        HTML_LAYOUT_CATALOG["media_requirement_by_layout_id"].get(layout_id) == "with-image"
        for layout_id in forced_layouts or []
    ):
        resolved_asset_policy = "image-planned"
    if resolved_asset_policy not in ASSET_POLICIES:
        raise ValueError(f"Unknown HTML asset policy: {resolved_asset_policy}")
    if layout_selection not in {"preferred", "dynamic", "diverse"}:
        raise ValueError(f"Unknown HTML layout selection mode: {layout_selection}")
    if layout_selection == "dynamic" and resolved_content_mode != "new-deck":
        raise ValueError("--layout-selection=dynamic is only valid for content_mode=new-deck")

    art_direction_handoff = None
    if forced_art_direction:
        art_direction_payload = load_art_direction(forced_art_direction)
        if art_direction_payload["status"] not in {"ready-for-audition", "approved-for-renderer"}:
            raise ValueError(
                "HTML renderer only accepts ready-for-audition or approved-for-renderer Art Direction"
            )
        art_direction_handoff = build_renderer_handoff(
            art_direction_payload,
            forced_art_direction,
        )
        handoff_source = art_direction_handoff.get("source") or {}
        for path_key in ("path", "schema_path"):
            if handoff_source.get(path_key):
                handoff_source[path_key] = portable_report_path(Path(handoff_source[path_key]))
        story_ref = str(art_direction_handoff["story_ref"])
        if story_ref.startswith("built-in:"):
            direction_story_id = story_ref.removeprefix("built-in:")
            if forced_story_file:
                raise ValueError("--story-file conflicts with the Art Direction story_ref")
            if forced_story_id and forced_story_id != direction_story_id:
                raise ValueError(
                    f"Forced story {forced_story_id} conflicts with Art Direction story_ref: "
                    f"{direction_story_id}"
                )
            forced_story_id = forced_story_id or direction_story_id
        else:
            direction_story_path = Path(story_ref)
            if not direction_story_path.is_absolute():
                direction_story_path = (PROJECT_ROOT / direction_story_path).resolve()
            if direction_story_path.exists() and direction_story_path.suffix.lower() == ".json":
                if forced_story_id:
                    raise ValueError("--story conflicts with the Art Direction story_ref")
                if forced_story_file and forced_story_file.resolve() != direction_story_path:
                    raise ValueError("--story-file conflicts with the Art Direction story_ref")
                forced_story_file = forced_story_file or direction_story_path
        html_direction = art_direction_handoff["renderers"]["html"]
        direction_themes = list(html_direction["theme_candidates"])
        direction_layouts = list(html_direction["layout_sequence"])
        if forced_theme and forced_theme not in direction_themes:
            raise ValueError(
                f"Forced theme {forced_theme} conflicts with Art Direction candidates: "
                f"{direction_themes}"
            )
        if forced_layouts and forced_layouts != direction_layouts:
            raise ValueError("--layouts conflicts with the Art Direction HTML layout sequence")
        forced_theme = forced_theme or direction_themes[0]
        # Art Direction still owns theme/story handoff in dynamic mode, but its
        # suggested sequence is treated as a review hint rather than a lock.
        if layout_selection not in {"dynamic", "diverse"}:
            forced_layouts = forced_layouts or direction_layouts

    if layout_media_mode is not None:
        if layout_media_mode not in MEDIA_MODES:
            raise ValueError(f"Unknown HTML layout media mode: {layout_media_mode}")
        if forced_style_case:
            raise ValueError("--media-mode cannot be combined with --preset-demo/--style-case")
        eligible_layouts = visible_html_layouts(
            HTML_LAYOUT_CATALOG,
            media_mode=layout_media_mode,
            asset_policy=resolved_asset_policy,
        )
        if not eligible_layouts:
            raise ValueError(
                f"No Layouts match --media-mode={layout_media_mode} under "
                f"--asset-policy={resolved_asset_policy}"
            )
        if forced_layouts is None:
            forced_layouts = eligible_layouts
        else:
            mismatched = [
                layout_id for layout_id in forced_layouts
                if HTML_LAYOUT_CATALOG["media_requirement_by_layout_id"].get(layout_id) != layout_media_mode
            ]
            if mismatched:
                raise ValueError(
                    f"Forced layouts do not match --media-mode={layout_media_mode}: {mismatched}"
                )

    if allow_legacy_layout_content and forced_story_file is None:
        raise ValueError(
            "--allow-legacy-layout-content requires an explicit historical --story-file manifest"
        )

    story_lookup = {row["id"]: row for row in STORIES}
    if forced_story_file:
        story = load_story_file(forced_story_file)
        content_source = portable_report_path(forced_story_file)
    else:
        if forced_story_id and forced_story_id not in story_lookup:
            raise ValueError(f"Unknown story_id: {forced_story_id}")
        story = story_lookup[forced_story_id] if forced_story_id else rng.choice(STORIES)
        content_source = f"built-in:{story['id']}"

    # Content planning is intentionally completed before sampling any Layout.
    # The Layout resolver receives this semantic page list; it must not invent
    # a route and then back-fill content into it.
    content_plan = resolve_content_plan(story, HTML_DESIGN_METHOD)
    if content_intent:
        if forced_layouts is not None and len(forced_layouts) != 1:
            raise ValueError("--content-intent requires exactly one forced Layout")
        matches = [entry for entry in content_plan if entry["intent"] == content_intent]
        if not matches:
            raise ValueError(
                f"Story {story['id']} has no semantic page for content intent {content_intent}"
            )
        content_plan = [matches[0]]
    semantic_pages = build_semantic_pages(story, content_plan)
    if resolved_content_mode == "new-deck" and forced_layouts is not None:
        if len(forced_layouts) != len(content_plan):
            raise ValueError(
                "content_mode=new-deck requires forced_layouts and content_plan "
                f"to have the same length (forced_layouts={len(forced_layouts)}, "
                f"content_plan={len(content_plan)})"
            )

    theme_id = forced_theme or rng.choice(AUTO_THEME_POOL)
    preset_definition = HTML_PRESET_THEME_DEFINITIONS.get(theme_id)
    preset_demo_profile = PRESET_DEMO_PROFILES.get(theme_id) if preset_demo_mode else None
    render_theme_id = preset_definition["base_theme"] if preset_definition else theme_id
    if render_theme_id not in STYLE_OVERRIDES:
        raise ValueError(f"Theme has no randomized HTML style profile: {render_theme_id}")
    dialects = HTML_DESIGN_DIALECTS["dialects"]
    if render_theme_id not in DIALECT_OVERRIDES or render_theme_id not in dialects:
        raise ValueError(f"Theme has no HTML design dialect: {render_theme_id}")
    assembly = resolve_html_assembly(theme_id)
    theme = next(row for row in matrix["themes"] if row["id"] == render_theme_id)
    layout_plan = resolve_layout_plan(
        story,
        rng,
        forced_layouts,
        HTML_DESIGN_METHOD,
        content_plan=content_plan,
        asset_policy=resolved_asset_policy,
        layout_catalog=HTML_LAYOUT_CATALOG,
        layout_selection=layout_selection,
    )
    if resolved_content_mode == "new-deck":
        layout_plan = reconcile_layout_plan_with_content(layout_plan, semantic_pages)
    assert_new_deck_forced_layout_routes(
        layout_plan,
        content_mode=resolved_content_mode,
        forced_layouts=forced_layouts,
    )
    if resolved_content_mode == "new-deck":
        if len(layout_plan) != len(semantic_pages):
            raise ValueError(
                "content_mode=new-deck requires one Layout decision per content page "
                f"(layout_plan={len(layout_plan)}, content_plan={len(semantic_pages)})"
            )
        render_semantic_pages = list(semantic_pages)
    else:
        render_semantic_pages = [
            semantic_pages[min(index, len(semantic_pages) - 1)]
            for index in range(len(layout_plan))
        ]
    layout_ids = [decision["layout_id"] for decision in layout_plan]
    layout_lookup = {row["id"]: row for row in matrix["layouts"]}
    missing = [layout_id for layout_id in layout_ids if layout_id not in layout_lookup]
    if missing:
        raise ValueError(f"Unknown layouts: {missing}")

    render_layouts = []
    for decision, semantic_page in zip(layout_plan, render_semantic_pages):
        layout = dict(layout_lookup[decision["layout_id"]])
        layout["media_requirement"] = HTML_LAYOUT_CATALOG["media_requirement_by_layout_id"][decision["layout_id"]]
        layout["media_mode"] = layout["media_requirement"]  # compatibility for existing HTML CSS
        layout["media_treatment"] = (
            "raster-background"
            if resolved_asset_policy == "image-planned" and layout["media_requirement"] == "with-image"
            else HTML_LAYOUT_CATALOG["media_rendering_policy"][layout["media_mode"]]
        )
        layout["html_variant"] = {
            "composition_variant": decision["composition_variant"],
            "header_mode": decision["header_mode"],
            "surface_mode": decision["surface_mode"],
        }
        payload = semantic_page.get("payload") if isinstance(semantic_page, dict) else None
        has_semantic_photo = bool(
            layout["media_requirement"] == "with-image"
            and isinstance(payload, dict)
            and str(payload.get("hero_image_src") or "").strip()
        )
        decision["image_variant"] = (
            "photo"
            if has_semantic_photo
            else "raster"
            if layout["media_requirement"] == "with-image"
            and layout["media_treatment"] == "raster-background"
            else None
        )
        layout["image_variant"] = decision["image_variant"]
        render_layouts.append(layout)

    composition_plan: list[dict[str, Any]] = []
    if preset_demo_mode:
        # Explicit Preset demos keep the accepted example fixture route.  The
        # normal new-deck path below never reads these Layout-keyed globals.
        apply_story_to_layouts(story, layout_ids)
        apply_story_context(story)
        apply_legacy_layout_content_overrides(story)
        page_contents = None
        composition_plan = [
            {
                "content_page_id": page["page_id"],
                "content_sha256": page["content_sha256"],
                "layout_scaffold_id": decision["layout_id"],
                "layout_role": "scaffold",
                "composition_source": "preset-demo-layout-fixture",
                "content_preserved": "demo-fixture-contract",
            }
            for page, decision in zip(render_semantic_pages, layout_plan)
        ]
    else:
        page_contents = []
        for semantic_page, decision in zip(render_semantic_pages, layout_plan):
            page_content, feedback = compose_page_content(
                story,
                semantic_page,
                decision,
                allow_legacy_layout_content=allow_legacy_layout_content,
            )
            page_contents.append(page_content)
            composition_plan.append(feedback)
    document = render_catalog(theme, render_layouts, page_contents)
    document = document.replace(f"{theme['display_name']} Layout Catalog", story["title"])
    document = re.sub(r"(<span>\d{2}) / 81(</span>)", rf"\1 / {len(layout_ids):02d}\2", document)
    base_dialect = dialects[render_theme_id]
    dialect = (
        {
            "id": preset_definition["design_dialect"],
            "composition": preset_definition["composition"],
            "techniques": list(preset_definition["techniques"]) + [
                "curated-palette",
                "css-pattern",
                "solid-text-color",
            ],
        }
        if preset_definition
        else base_dialect
    )
    layout_media_mode_label = layout_media_mode or "mixed"
    background_profile = str(assembly["recipe"]["background_pattern"])
    if preset_definition:
        background_profile = str(
            preset_definition.get("background_pattern") or background_profile
        )
        if preset_definition.get("visual_asset_policy") == "generated-raster-background-opt-in":
            background_profile = "none"
    document = re.sub(
        rf'(<html\s+lang="zh-Hant"\s+data-theme="{re.escape(render_theme_id)}")',
        (
            rf'\1 data-theme-id="{theme_id}" data-theme-kind="{("html-preset" if preset_definition else "core")}" '
            rf'data-style-profile="{theme_id}" data-design-dialect="{dialect["id"]}" '
            rf'data-html-assembly="{assembly["id"]}" '
            rf'data-background-profile="{background_profile}" '
            rf'data-background-pattern="{background_profile}" '
            rf'data-component-recipe="{assembly["recipe"]["component_recipe"]}" '
            rf'data-content-mode="{resolved_content_mode}" '
            rf'data-layout-asset-policy="{resolved_asset_policy}" '
            rf'data-random-seed="{seed}" data-layout-media-mode="{layout_media_mode_label}" '
            rf'data-media-rendering="placeholder-fill" data-edit-visual-anchor-contract="parent-edge-v1"'
        ),
        document,
        count=1,
    )
    brand_words = story["id"].split("-")[:2]
    brand_code = "".join(word[0].upper() for word in brand_words)
    brand_label = " ".join(brand_words).upper()
    if len(brand_label) > 18:
        brand_label = brand_words[0][:8].upper()
    document = document.replace(
        '>SF</b><span data-edit-layer="text">SLIDE FIRM</span>',
        f'>{brand_code}</b><span data-edit-layer="text">{brand_label}</span>',
    )
    if preset_demo_mode:
        legacy_demo_css = production.normalize_generated_css_font_sizes(
            STYLE_OVERRIDES[render_theme_id]
            + DIALECT_OVERRIDES[render_theme_id]
            + COMMON_RANDOM_CSS
            + production.MEDIA_PLACEHOLDER_CSS
        )
        document = inject_owned_css(document, "legacy-demo-override", legacy_demo_css)
    else:
        # New-deck applies only geometry-free Theme paint. Composition variants
        # have already been resolved by Layout and may not be rewritten here.
        theme_css = production.normalize_generated_css_font_sizes(STYLE_OVERRIDES[render_theme_id])
        document = inject_owned_css(document, "theme-appearance", theme_css)
    if preset_definition:
        if preset_demo_mode:
            if preset_demo_profile is None:
                raise ValueError(f"Preset demo payload missing: {theme_id}")
            preset_css = production.normalize_generated_css_font_sizes(
                preset_demo_profile["css"].replace("data-style-case=", "data-preset-theme=")
            )
            document = inject_owned_css(document, "legacy-demo-override", preset_css)
            document = inject_owned_css(document, "legacy-demo-override", production.SEMANTIC_CONTRACT_CSS)
        else:
            preset_css = build_preset_appearance_css(theme_id, preset_definition, assembly["recipe"])
            document = inject_owned_css(document, "preset-appearance", preset_css)
        document = re.sub(
            r'data-theme-label="[^"]*"',
            f'data-theme-label="{preset_definition["display_name"]}"',
            document,
            count=1,
        )
        document = re.sub(
            r'(<html\s+lang="zh-Hant"[^>]*)(>)',
            rf'\1 data-preset-theme="{theme_id}"\2',
            document,
            count=1,
        )
    if preset_demo_mode and preset_demo_profile:
        for class_name, replacement in preset_demo_profile["content"].items():
            document, changed = re.subn(
                rf'(<div class="el [^"]*\b{re.escape(class_name)}\b[^"]*"[^>]*>)[^<]*(</div>)',
                lambda match, value=replacement: f"{match.group(1)}{value}{match.group(2)}",
                document,
                count=1,
            )
            if changed != 1:
                raise ValueError(f"Style-case target class not found: {class_name}")
        for source_text, replacement_text in preset_demo_profile.get("text_replacements", {}).items():
            if source_text not in document:
                raise ValueError(f"Style-case source text not found: {source_text}")
            document = document.replace(source_text, replacement_text, 1)
    deck_kind = "CONTENT-MANIFEST-DECK" if forced_story_file else "RANDOMIZED-DECK"
    if preset_definition:
        deck_kind = "HTML-PRESET-THEME"
    if art_direction_handoff:
        deck_kind = (
            "ART-DIRECTION-DECK"
            if art_direction_handoff["formal_publish_allowed"]
            else "ART-DIRECTION-AUDITION"
        )
    document = document.replace(
        "<!doctype html>",
        f'<!doctype html>\n<!-- {deck_kind} seed={seed} topic={story["id"]} theme={theme_id} base-theme={render_theme_id} layouts={",".join(layout_ids)} -->',
        1,
    )
    if art_direction_handoff:
        document = apply_art_direction_metadata(document, art_direction_handoff)

    # Browser drafts must never survive a regenerated deck silently.  Hash the
    # complete pre-revision document (including the embedded editor runtime)
    # and expose the revision to edit-mode.js so its draft/log keys are scoped
    # to this exact build.
    deck_revision = hashlib.sha256(document.encode("utf-8")).hexdigest()[:20]
    document = re.sub(
        r'(<html\b[^>]*)(>)',
        rf'\1 data-deck-revision="{deck_revision}"\2',
        document,
        count=1,
    )

    css_ownership_issues = validate_html_document_text(
        document,
        source=portable_report_path(output_path),
        content_mode=resolved_content_mode,
    )
    if css_ownership_issues:
        summary = "; ".join(
            f"{row['code']}: {row['detail']}" for row in css_ownership_issues[:12]
        )
        raise ValueError(f"Generated HTML violates CSS ownership: {summary}")
    validate_editable_html(document)
    validate_edit_layer_positions(document)
    validate_edit_module_structures(document)
    if resolved_content_mode == "new-deck":
        visible_copy_report = assert_visible_copy(
            document,
            language=str(story.get("visible_text_language") or "zh-Hant"),
            allowed_latin_terms=story.get("allowed_latin_terms") or [],
        )
    else:
        visible_copy_report = {
            "status": "not-run",
            "reason": "isolated-preset-demo-content",
        }
    production_path = PROJECT_ROOT / "artifacts" / "html-test" / "edit-mode.js"
    production_source = production_path.read_text(encoding="utf-8")
    editor_sha256 = hashlib.sha256(production_source.encode("utf-8")).hexdigest()
    write_text_with_retry(output_path, document)
    external_editor_path = output_path.parent / "edit-mode.js"
    write_text_with_retry(external_editor_path, production_source)
    if hashlib.sha256(external_editor_path.read_bytes()).hexdigest() != editor_sha256:
        raise ValueError("Embedded editor copy failed source-hash validation")

    randomized_dimensions: list[str] = []
    candidate_pool: dict[str, Any] = {}
    # Art Direction may fix the story and Theme while dynamic/diverse routing
    # still samples the Layout sequence from seeded semantic candidates. Keep
    # that randomization evidence in the manifest instead of suppressing the
    # entire candidate-pool record whenever a direction handoff is present.
    if not preset_demo_mode:
        if content_intent:
            candidate_pool["content-intent"] = {
                "source": "explicit-user-scope",
                "mode": "fixed",
                "candidates": sorted(HTML_DESIGN_METHOD["content_routing"]),
                "selected": content_intent,
            }
        if forced_story_file:
            candidate_pool["content"] = {
                "source": portable_report_path(forced_story_file),
                "mode": "fixed-external-manifest",
                "selected": story["id"],
            }
        else:
            randomized_dimensions.append("content")
            candidate_pool["content"] = {
                "source": "built-in:STORIES",
                "version": "render-randomized-html-demo-v1",
                "candidates": [row["id"] for row in STORIES],
                "selected": story["id"],
            }
        if forced_layouts is None:
            randomized_dimensions.append("layout-sequence")
            candidate_pool["layout-sequence"] = {
                "source": "prompt_system/renderers/html/layout-catalog.yaml",
                "version": HTML_LAYOUT_CATALOG["schema_version"],
                "asset_policy": resolved_asset_policy,
                "diversity_policy": HTML_DESIGN_METHOD["layout_diversity_policy"],
                "selection_mode": layout_selection,
                "candidates": HTML_LAYOUT_CATALOG["layout_ids_by_asset_policy"][resolved_asset_policy],
                "route_candidates": [
                    {
                        "intent": decision["intent"],
                        "candidates": decision.get("selection_candidates", []),
                        "selected": decision["layout_id"],
                        "candidate_source": (
                            HTML_DESIGN_METHOD["content_routing"][decision["intent"]].get("candidate_pool")
                            or "design-method"
                        ),
                        "composition_feedback": decision.get("composition_feedback"),
                    }
                    for decision in layout_plan
                ],
                "selected": layout_ids,
            }
        if forced_theme is None:
            randomized_dimensions.extend(["theme-decoration-profile", "html-design-dialect"])
            candidate_pool["theme-decoration-profile"] = {
                "source": "AUTO_THEME_POOL",
                "version": "render-randomized-html-demo-v1",
                "candidates": AUTO_THEME_POOL,
                "selected": theme_id,
            }
            candidate_pool["html-design-dialect"] = {
                "source": "prompt_system/renderers/html/design-dialects.yaml",
                "version": "html-design-dialects-v1",
                "candidates": sorted(dialects),
                "selected": dialect["id"],
            }

    manifest = {
        "skill": "html-pattern-slide",
        "renderer_entrypoint": "scripts/render_randomized_html_demo.py",
        "contract": "references/presentation-production-contract.md",
        "editable_dom": {
            "schema": "semantic-module-v1",
            "static_validation": "pass",
            "editor_source": "artifacts/html-test/edit-mode.js",
            "editor_sha256": editor_sha256,
            "visual_anchor_contract": {
                "schema": "parent-edge-v1",
                "metadata": "data-edit-anchor",
                "supported_anchors": ["bottom"],
            },
        },
        "html_runtime": {
            "editor_embedded": True,
            "pptx_browser_runtime_embedded": True,
            "pptx_browser_runtime_sha256": pptx_browser_runtime_sha256(),
            "motion_runtime_embedded": True,
            "motion_runtime": motion_runtime_manifest(),
        },
        "seed": seed,
        "deck_revision": deck_revision,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "topic": {"id": story["id"], "title": story["title"]},
        "content_source": content_source,
        "content_mode": resolved_content_mode,
        "visible_copy": visible_copy_report,
        "legacy_layout_content_compatibility": {
            "enabled": allow_legacy_layout_content,
            "activation": "explicit-opt-in" if allow_legacy_layout_content else "disabled",
            "manifest_marker": (
                "legacy-layout-content-compatibility"
                if allow_legacy_layout_content
                else None
            ),
            "preset_demo_isolated": preset_demo_mode,
        },
        "content_intent": content_intent or "full-content-plan",
        "layout_selection": layout_selection,
        "layout_selection_contract": (
            "semantic-candidates-seeded-diverse-no-consecutive-repeat"
            if layout_selection == "diverse"
            else "semantic-candidates-seeded-tiebreaker"
            if layout_selection == "dynamic"
            else "preferred-layout-when-authored-no-consecutive-repeat"
        ),
        "layout_diversity": {
            "policy": HTML_DESIGN_METHOD["layout_diversity_policy"],
            "mode": "forced-sequence" if forced_layouts is not None else layout_selection,
            "no_consecutive_repeat": True,
            "selected_layouts": layout_ids,
        },
        "content_plan": content_plan,
        "content_pages": [
            {key: value for key, value in page.items() if key != "payload"}
            for page in semantic_pages
        ],
        "composition_plan": composition_plan,
        "css_ownership": {
            "contract": "references/html-css-ownership-contract.md",
            "static_validation": "pass",
            "owners": (
                ["renderer-base", "legacy-demo-override"]
                if preset_demo_mode
                else ["renderer-base", "theme-appearance"]
                + (["preset-appearance"] if preset_definition else [])
            ),
            "geometry_owner": "renderer-base",
            "appearance_can_mutate_geometry": False,
            "post_materialize_css_correction": False,
        },
        "theme": {
            "id": theme_id,
            "display_name": preset_definition["display_name"] if preset_definition else theme["display_name"],
            "kind": "html-preset" if preset_definition else "core",
            "base_theme": render_theme_id if preset_definition else None,
            "style_profile": theme_id,
            "design_dialect": dialect["id"],
            "composition": dialect["composition"],
            "techniques": dialect["techniques"],
            "selection_profile": HTML_DESIGN_METHOD["theme_selection_profiles"][theme_id],
        },
        "html_assembly": {
            "id": assembly["id"],
            "recipe": assembly["recipe"],
            "profiles": assembly["profiles"],
            "layers": assembly["layers"],
            "guardrails": assembly["guardrails"],
            "pattern_effect_policy": assembly["pattern_effect_policy"],
        },
        "layouts": layout_ids,
        "layout_media": {
            "asset_policy": resolved_asset_policy,
            "asset_policy_source": "prompt_system/renderers/html/layout-catalog.yaml#asset_policies",
            "eligible_media_requirements": HTML_LAYOUT_CATALOG["asset_policy_media_requirements"][resolved_asset_policy],
            "eligible_layout_count": len(
                HTML_LAYOUT_CATALOG["layout_ids_by_asset_policy"][resolved_asset_policy]
            ),
            "mode": layout_media_mode or "mixed",
            "counts": {
                mode: sum(
                    1
                    for layout_id in layout_ids
                    if HTML_LAYOUT_CATALOG["layout_media_mode_by_id"][layout_id] == mode
                )
                for mode in MEDIA_MODES
            },
            "layout_media_modes": {
                layout_id: HTML_LAYOUT_CATALOG["layout_media_mode_by_id"][layout_id]
                for layout_id in layout_ids
            },
            "layout_media_requirements": {
                layout_id: HTML_LAYOUT_CATALOG["media_requirement_by_layout_id"][layout_id]
                for layout_id in layout_ids
            },
            "rendering_policy": dict(HTML_LAYOUT_CATALOG["media_rendering_policy"]),
        },
        "architecture": [layout_family(layout_id) for layout_id in layout_ids],
        "layout_decisions": layout_plan,
        "design_method": {
            "id": HTML_DESIGN_METHOD["id"],
            "visual_checkpoint": HTML_DESIGN_METHOD["visual_checkpoint"],
            "deck_review": HTML_DESIGN_METHOD["deck_review"],
            "deferred": HTML_DESIGN_METHOD["deferred"],
            "forbidden": HTML_DESIGN_METHOD["forbidden"],
        },
        "randomized_dimensions": randomized_dimensions,
        "candidate_pool": candidate_pool,
        "output": portable_report_path(output_path),
    }
    semantic_photo_pages = []
    for index, (semantic_page, decision) in enumerate(
        zip(render_semantic_pages, layout_plan),
        start=1,
    ):
        payload = semantic_page.get("payload") if isinstance(semantic_page, dict) else None
        if not isinstance(payload, dict) or not str(payload.get("hero_image_src") or "").strip():
            continue
        semantic_photo_pages.append(
            {
                "slide": index,
                "page_id": semantic_page.get("page_id"),
                "layout_id": decision.get("layout_id"),
                "page_claim": payload.get("photo_brief") or payload.get("hero_image_alt") or "",
                "subject": payload.get("photo_subject") or "",
                "context_or_action": payload.get("photo_context") or "",
                "visual_type": payload.get("photo_visual_type") or "photo",
                "src": payload.get("hero_image_src"),
                "alt": payload.get("hero_image_alt") or "",
                "crop_behavior": payload.get("photo_crop_behavior") or "cover",
                "source": payload.get("photo_source") or "content-manifest",
            }
        )
    if semantic_photo_pages:
        manifest["semantic_photo_handoff"] = {
            "status": "attached",
            "variant": "photo",
            "pages": semantic_photo_pages,
        }
    if art_direction_handoff:
        manifest["art_direction"] = art_direction_handoff
    if preset_definition:
        preset_raster_assets = (
            [
                "prompt_system/renderers/html/assets/external/moonlit-herbarium-atlas/"
                "matricaria-chamomilla-koehler-plate-64.jpg"
            ]
            if preset_demo_mode and theme_id == "moonlit-herbarium-atlas"
            else []
        )
        preset_visual_asset_policy = str(
            preset_definition.get("visual_asset_policy") or "pattern-and-geometry-only"
        )
        preset_background_pattern = str(
            preset_definition.get("background_pattern") or assembly["recipe"]["background_pattern"]
        )
        if preset_visual_asset_policy == "generated-raster-background-opt-in":
            preset_background_pattern = "none"
        preset_ambient_design = (
            ["solid-base", "safe-zone-raster-opt-in", "shadow", "typography"]
            if preset_visual_asset_policy == "generated-raster-background-opt-in"
            else ["css-gradient", "css-pattern", "shadow", "typography"]
        )
        manifest["preset_theme"] = {
            "id": theme_id,
            "display_name": preset_definition["display_name"],
            "definition": f"prompt_system/renderers/html/preset-themes.yaml#themes.{theme_id}",
            "scope": "html-theme",
            "pure_html": True,
            "css_owner": "legacy-demo-override" if preset_demo_mode else "preset-appearance",
            "legacy_case_imported": preset_demo_mode,
            "raster_assets": preset_raster_assets,
            "ambient_design": (
                ["embedded-public-domain-plate", "open-editorial-grid", "typography"]
                if preset_demo_mode and theme_id == "moonlit-herbarium-atlas"
                else preset_ambient_design
            ),
            "visual_asset_policy": preset_visual_asset_policy,
            "background_pattern": preset_background_pattern,
            "registered_as_theme": True,
            "layout_binding": "none",
            "content_binding": "none",
            "palette": preset_definition["palette"],
        }
        if preset_demo_mode:
            manifest["example_reference"] = {
                "story": preset_demo_profile["story"],
                "layouts": list(preset_demo_profile["layouts"]),
                "scope": "isolated-preset-demo-only",
            }
    manifest_path = output_path.with_suffix(".manifest.json")
    write_text_with_retry(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", default=str(PROJECT_ROOT / "artifacts" / "renderer-matrix" / "matrix.json"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--theme", choices=THEME_POOL)
    story_group = parser.add_mutually_exclusive_group()
    story_group.add_argument("--story", help="Existing story id from the production content pool")
    story_group.add_argument("--story-file", help="External JSON content manifest")
    parser.add_argument("--layouts", help="Comma-separated HTML layout ids in slide order")
    parser.add_argument(
        "--art-direction",
        help="Shared Art Direction YAML; ready directions render as audition-only until human approval",
    )
    parser.add_argument(
        "--preset-demo",
        "--style-case",
        dest="style_case",
        choices=sorted(PRESET_DEMO_PROFILES),
        help="Explicit demo mode only: render a Preset Theme with its registered example story/layouts",
    )
    parser.add_argument(
        "--content-mode",
        choices=["new-deck", "preset-demo"],
        help="Content mode; defaults to new-deck unless --preset-demo/--style-case is supplied",
    )
    parser.add_argument("--media-mode", choices=MEDIA_MODES, help="Render only Layouts from one media capability group")
    parser.add_argument(
        "--asset-policy",
        choices=ASSET_POLICIES,
        help="Defaults to pattern-only; image-planned allows image-required Layouts for later image attachment",
    )
    parser.add_argument(
        "--layout-selection",
        choices=["preferred", "dynamic", "diverse"],
        default="diverse",
        help=(
            "diverse samples least-used semantic candidates with the seed and rejects "
            "consecutive duplicate Layouts; preferred honors authored Layout hints"
        ),
    )
    parser.add_argument(
        "--content-intent",
        choices=sorted(HTML_DESIGN_METHOD["content_routing"]),
        help="Render one semantic page intent; intended for a single explicitly selected Layout",
    )
    parser.add_argument(
        "--allow-legacy-layout-content",
        action="store_true",
        help=(
            "Explicit compatibility opt-in for layout_content in a historical --story-file; "
            "never enabled by --story-file alone"
        ),
    )
    args = parser.parse_args()
    seed = args.seed if args.seed is not None else secrets.randbits(32)
    layouts = [value.strip() for value in args.layouts.split(",") if value.strip()] if args.layouts else None
    manifest = build(
        seed,
        Path(args.matrix).resolve(),
        Path(args.output).resolve(),
        args.theme,
        args.story,
        layouts,
        Path(args.story_file).resolve() if args.story_file else None,
        args.style_case,
        Path(args.art_direction).resolve() if args.art_direction else None,
        args.content_mode,
        layout_media_mode=args.media_mode,
        asset_policy=args.asset_policy,
        layout_selection=args.layout_selection,
        content_intent=args.content_intent,
        allow_legacy_layout_content=args.allow_legacy_layout_content,
    )
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
