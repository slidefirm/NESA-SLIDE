#!/usr/bin/env python3
"""Build an isolated, editable 30-cover Layout audition from one HTML shell.

The audition deliberately does not register its 30 experimental IDs in the
formal Layout catalog. It reuses the production HTML runtime and the current
reference content so each proposal remains editable and comparable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "artifacts/experiments/cover-left-title-open-field-pilot-20260821/clinical-evidence-atlas/clinical-evidence-atlas-cover-pilot-v10.html"
DEFAULT_OUTPUT = ROOT / "artifacts/experiments/cover-layout-audition-30-20260822/cover-layout-audition-30.html"
DEFAULT_MANIFEST = ROOT / "artifacts/experiments/cover-layout-audition-30-20260822/cover-layout-audition-30.manifest.json"


CONTENT = {
    "title": "AI 重塑台灣勞動市場",
    "subtitle": "人口斷崖、任務自動化與財富雙軌化交織下的就業結構轉型",
    "speaker": "台灣就業環境分析報告",
}


def box(left: int, top: int, width: int, height: int) -> dict[str, int]:
    return {"left": left, "top": top, "width": width, "height": height}


def decor(kind: str, left: int, top: int, width: int, height: int, **extra: str | int) -> dict:
    item = {"kind": kind, **box(left, top, width, height)}
    item.update(extra)
    return item


def spec(
    number: int,
    slug: str,
    name: str,
    title_box: dict[str, int],
    subtitle_box: dict[str, int],
    speaker_box: dict[str, int],
    *,
    rule: dict[str, int] | None = None,
    decor_items: list[dict] | None = None,
    bg: str = "clinical",
    align: str = "left",
    title_size: int = 104,
    title_class: str = "",
    subtitle_size: int = 38,
    speaker_size: int = 36,
    title_color: str = "var(--text)",
    subtitle_color: str = "var(--muted)",
    speaker_color: str = "var(--accent)",
) -> dict:
    return {
        "number": number,
        "id": f"audition-cover-{number:02d}-{slug}",
        "name": name,
        "title_box": title_box,
        "subtitle_box": subtitle_box,
        "speaker_box": speaker_box,
        "rule": rule,
        "decor": decor_items or [],
        "bg": bg,
        "align": align,
        "title_size": title_size,
        "title_class": title_class,
        "subtitle_size": subtitle_size,
        "speaker_size": speaker_size,
        "title_color": title_color,
        "subtitle_color": subtitle_color,
        "speaker_color": speaker_color,
    }


VARIANTS = [
    spec(1, "left-open-field", "左軸開放場", box(112, 280, 1120, 150), box(112, 463, 1100, 58), box(112, 540, 800, 54), rule=box(112, 434, 244, 7), decor_items=[decor("field", 1175, 0, 553, 888), decor("spine", 1279, 0, 7, 888)]),
    spec(2, "left-edge-rule", "左緣主標／硬邊線", box(128, 178, 1080, 150), box(128, 362, 1000, 58), box(128, 438, 800, 54), rule=box(128, 332, 300, 7), decor_items=[decor("edge", 96, 0, 14, 888), decor("field", 1290, 0, 438, 888)]),
    spec(3, "left-panel-right-quiet", "左側紙板／右側靜場", box(136, 270, 760, 150), box(136, 450, 740, 92), box(136, 590, 700, 54), rule=box(136, 430, 210, 7), decor_items=[decor("panel", 96, 190, 900, 520), decor("field", 1180, 0, 548, 888)], title_class="serif"),
    spec(4, "split-half-left", "左右分半／內容左欄", box(112, 250, 760, 150), box(112, 438, 730, 90), box(112, 580, 680, 54), rule=box(112, 410, 230, 7), decor_items=[decor("split", 980, 0, 748, 888), decor("spine", 980, 0, 3, 888)]),
    spec(5, "lower-left-hero", "低位主標／上方留白", box(112, 500, 1120, 150), box(112, 680, 1080, 58), box(112, 760, 800, 54), rule=box(112, 654, 244, 7), decor_items=[decor("field", 1175, 0, 553, 888)]),
    spec(6, "top-masthead", "上方報告頭／下方留白", box(112, 126, 1180, 150), box(112, 310, 1100, 58), box(112, 390, 800, 54), rule=box(112, 282, 260, 7), decor_items=[decor("topband", 0, 0, 1728, 88), decor("field", 1230, 88, 498, 800)]),
    spec(7, "left-center-hero", "左側置中／右側退讓", box(180, 286, 980, 150), box(180, 468, 960, 58), box(180, 545, 800, 54), rule=box(180, 440, 244, 7), decor_items=[decor("field", 1200, 0, 528, 888)]),
    spec(8, "right-axis-open-left", "右軸主標／左側開放", box(920, 270, 690, 150), box(850, 450, 760, 92), box(1080, 590, 530, 54), rule=box(1360, 430, 244, 7), decor_items=[decor("leftfield", 0, 0, 650, 888), decor("spine", 820, 0, 4, 888)], align="right", title_size=92),
    spec(9, "center-band", "中央水平帶／主標穿場", box(150, 365, 1220, 140), box(150, 520, 1100, 58), box(150, 598, 800, 54), rule=box(150, 505, 260, 7), decor_items=[decor("band", 0, 300, 1728, 330), decor("field", 1370, 0, 358, 888)]),
    spec(10, "top-editorial-band", "上方編輯帶／主標落下", box(112, 250, 1160, 150), box(112, 435, 1100, 58), box(112, 512, 800, 54), rule=box(112, 410, 244, 7), decor_items=[decor("topband", 0, 0, 1728, 190), decor("spine", 1280, 190, 5, 698)]),
    spec(11, "bottom-anchored-band", "底部基準帶／上方呼吸", box(112, 438, 1180, 150), box(112, 620, 1100, 58), box(112, 697, 800, 54), rule=box(112, 595, 244, 7), decor_items=[decor("bottomband", 0, 730, 1728, 158), decor("field", 1290, 0, 438, 730)]),
    spec(12, "boxed-hero", "薄框主張／編輯卡片", box(156, 300, 1000, 150), box(156, 480, 950, 58), box(156, 558, 800, 54), rule=box(156, 456, 244, 7), decor_items=[decor("outline", 112, 220, 1120, 480), decor("field", 1320, 0, 408, 888)]),
    spec(13, "corner-bracket", "四角括號／不封閉框", box(210, 318, 980, 150), box(210, 500, 940, 58), box(210, 578, 800, 54), rule=box(210, 476, 244, 7), decor_items=[decor("bracket", 160, 245, 1100, 420), decor("spine", 1350, 0, 4, 888)]),
    spec(14, "double-rule-stack", "雙規則夾心／垂直堆疊", box(112, 310, 1180, 150), box(112, 500, 1100, 58), box(112, 580, 800, 54), rule=box(112, 275, 420, 5), decor_items=[decor("rule2", 112, 480, 300, 5), decor("field", 1280, 0, 448, 888)]),
    spec(15, "accent-block-hero", "實色主張塊／反白文字", box(145, 302, 1120, 150), box(145, 490, 1060, 58), box(145, 568, 800, 54), rule=box(145, 463, 244, 7), decor_items=[decor("accentblock", 96, 240, 1260, 430), decor("field", 1380, 0, 348, 888)], title_color="var(--accent-text)", subtitle_color="var(--accent-text)", speaker_color="var(--accent-text)"),
    spec(16, "left-spine-no-metadata", "左側脊線／無直排資訊", box(160, 280, 1100, 150), box(160, 462, 1050, 58), box(160, 540, 800, 54), rule=box(160, 438, 244, 7), decor_items=[decor("edge", 96, 0, 16, 888), decor("hairline", 1320, 0, 2, 888)]),
    spec(17, "index-window", "索引窗／主標入口", box(112, 305, 1120, 150), box(112, 490, 1080, 58), box(112, 568, 800, 54), rule=box(112, 463, 244, 7), decor_items=[decor("index", 112, 190, 96, 62), decor("window", 1160, 140, 430, 530)]),
    spec(18, "quote-panel", "引用欄式／左邊界承重", box(176, 300, 940, 150), box(176, 490, 900, 58), box(176, 568, 800, 54), rule=box(176, 462, 244, 7), decor_items=[decor("leftbar", 128, 245, 10, 430), decor("panelwash", 138, 245, 1040, 430), decor("field", 1320, 0, 408, 888)]),
    spec(19, "stacked-paper-blocks", "上下紙片／內容分層", box(140, 260, 1060, 150), box(140, 465, 1000, 58), box(140, 545, 800, 54), rule=box(140, 430, 244, 7), decor_items=[decor("paper1", 112, 210, 1120, 300), decor("paper2", 160, 520, 980, 160), decor("field", 1330, 0, 398, 888)]),
    spec(20, "negative-cut", "切面分界／留白挖空", box(112, 300, 1060, 150), box(112, 490, 1020, 58), box(112, 568, 800, 54), rule=box(112, 462, 244, 7), decor_items=[decor("cutfield", 0, 0, 1050, 888), decor("spine", 1080, 0, 10, 888), decor("rightfield", 1090, 0, 638, 888)]),
    spec(21, "centered-minimal", "中央極簡／取消配重", box(360, 310, 1000, 150), box(360, 492, 1000, 58), box(360, 570, 800, 54), rule=box(742, 462, 244, 7), decor_items=[decor("hairline", 96, 110, 1536, 2)], align="center", title_size=102),
    spec(22, "top-left-grid", "左上網格／大面積下留白", box(112, 132, 1120, 150), box(112, 315, 1080, 58), box(112, 392, 800, 54), rule=box(112, 286, 244, 7), decor_items=[decor("gridfield", 0, 0, 1728, 410), decor("field", 1260, 410, 468, 478)]),
    spec(23, "bottom-left-line", "左下落點／單一底線", box(112, 530, 1120, 150), box(112, 708, 1080, 58), box(112, 784, 800, 54), rule=box(112, 690, 340, 6), decor_items=[decor("bottombar", 96, 850, 1536, 8), decor("field", 1280, 0, 448, 888)]),
    spec(24, "horizontal-capsule", "水平膠囊／短句聚焦", box(180, 360, 1040, 120), box(180, 505, 1000, 58), box(180, 582, 800, 54), rule=box(180, 480, 244, 7), decor_items=[decor("capsule", 128, 300, 1200, 350), decor("field", 1390, 0, 338, 888)], title_size=90),
    spec(25, "right-rail-counterweight", "右側色軌／左側內容", box(112, 280, 1120, 150), box(112, 462, 1080, 58), box(112, 540, 800, 54), rule=box(112, 435, 244, 7), decor_items=[decor("field", 1420, 0, 308, 888), decor("rail", 1400, 0, 5, 888)]),
    spec(26, "offset-outline-hero", "偏移框景／主標跨軸", box(220, 292, 1120, 150), box(220, 478, 1060, 58), box(220, 556, 800, 54), rule=box(220, 452, 244, 7), decor_items=[decor("offsetframe", 145, 230, 1190, 450), decor("hairline", 1300, 180, 260, 3)]),
    spec(27, "three-rail-editorial", "三軌編輯場／左欄主張", box(112, 310, 940, 150), box(112, 490, 920, 58), box(112, 568, 800, 54), rule=box(112, 463, 244, 7), decor_items=[decor("railfield", 1120, 0, 170, 888), decor("railfield2", 1290, 0, 170, 888), decor("railfield3", 1460, 0, 268, 888)]),
    spec(28, "corner-frame", "角落框線／中央留白", box(180, 315, 1100, 150), box(180, 497, 1050, 58), box(180, 575, 800, 54), rule=box(180, 470, 244, 7), decor_items=[decor("cornerframe", 96, 96, 1536, 696)]),
    spec(29, "underline-stack", "多重底線／閱讀節拍", box(112, 270, 1160, 150), box(112, 468, 1120, 58), box(112, 545, 800, 54), rule=box(112, 440, 244, 7), decor_items=[decor("underline", 112, 440, 410, 4), decor("underline2", 112, 455, 300, 3), decor("underline3", 112, 468, 190, 2), decor("field", 1300, 0, 428, 888)]),
    spec(30, "quiet-field", "安靜留白／最少結構", box(112, 320, 1120, 150), box(112, 500, 1080, 58), box(112, 578, 800, 54), rule=box(112, 472, 180, 5), decor_items=[decor("hairline", 112, 610, 1536, 2)], title_size=104),
]


BACKGROUND_CSS = {
    "clinical": "background-color:var(--bg);background-image:linear-gradient(90deg,transparent 68%,color-mix(in srgb,var(--accent) 8%,var(--bg)) 68% 100%),linear-gradient(90deg,transparent 74%,color-mix(in srgb,var(--support-accent) 16%,transparent) 74% 74.4%,transparent 74.4%),linear-gradient(color-mix(in srgb,var(--accent) 2.4%,transparent) 1px,transparent 1px),linear-gradient(90deg,color-mix(in srgb,var(--accent) 2.4%,transparent) 1px,transparent 1px);background-size:100% 100%,100% 100%,64px 64px,64px 64px;box-shadow:18px 0 0 inset var(--accent)",
    "warm": "background-color:var(--bg);background-image:linear-gradient(90deg,transparent 66%,color-mix(in srgb,var(--accent) 10%,var(--bg)) 66% 100%),linear-gradient(90deg,transparent 72%,color-mix(in srgb,var(--support-accent) 18%,transparent) 72% 72.5%,transparent 72.5%),linear-gradient(color-mix(in srgb,var(--accent) 2%,transparent) 1px,transparent 1px),linear-gradient(90deg,color-mix(in srgb,var(--accent) 2%,transparent) 1px,transparent 1px);background-size:100% 100%,100% 100%,72px 72px,72px 72px;box-shadow:14px 0 0 inset var(--accent)",
    "dark": "background-color:var(--bg);background-image:linear-gradient(90deg,transparent 68%,color-mix(in srgb,var(--accent) 12%,var(--bg)) 68% 100%),linear-gradient(90deg,transparent 74%,color-mix(in srgb,var(--support-accent) 22%,transparent) 74% 74.3%,transparent 74.3%),linear-gradient(color-mix(in srgb,var(--accent) 3%,transparent) 1px,transparent 1px),linear-gradient(90deg,color-mix(in srgb,var(--accent) 3%,transparent) 1px,transparent 1px);background-size:100% 100%,100% 100%,48px 48px,48px 48px;box-shadow:18px 0 0 inset var(--accent)",
    "paper": "background-color:var(--bg);background-image:linear-gradient(90deg,transparent 70%,color-mix(in srgb,var(--accent) 7%,var(--bg)) 70% 100%),linear-gradient(color-mix(in srgb,var(--accent) 1.6%,transparent) 1px,transparent 1px),linear-gradient(90deg,color-mix(in srgb,var(--accent) 1.6%,transparent) 1px,transparent 1px);background-size:100% 100%,80px 80px,80px 80px;box-shadow:12px 0 0 inset var(--accent)",
    "plain": "background-color:var(--bg);background-image:linear-gradient(90deg,transparent 74%,color-mix(in srgb,var(--accent) 6%,var(--bg)) 74% 100%);background-size:100% 100%;box-shadow:12px 0 0 inset var(--accent)",
}


GLOBAL_CSS = r'''
#stage .slide[data-audition-id]{background-repeat:no-repeat;color:var(--text)}
.audition-frame{position:absolute;left:0;top:0;width:1728px;height:888px;overflow:visible;pointer-events:none}
.audition-frame>.el{position:absolute;pointer-events:auto;box-sizing:border-box}
.audition-title{z-index:4;margin:0;padding:0;border:0;background:transparent;font:800 104px/1.03 var(--font-heading);letter-spacing:-.055em;color:var(--text);text-align:left}
.audition-title.serif{font-family:var(--font-display);letter-spacing:-.045em}
.audition-title.right,.audition-subtitle.right,.audition-speaker.right{text-align:right}
.audition-title.center,.audition-subtitle.center,.audition-speaker.center{text-align:center}
.audition-subtitle{z-index:4;margin:0;padding:0;border:0;background:transparent;font:500 38px/1.38 var(--font-body);color:var(--muted);text-align:left}
.audition-speaker{z-index:4;margin:0;padding:0;border:0;background:transparent;font:800 36px/1 var(--font-heading);letter-spacing:.08em;color:var(--accent);text-align:left}
.audition-rule,.audition-underline,.audition-underline2,.audition-underline3,.audition-hairline,.audition-spine,.audition-edge,.audition-rail,.audition-rail2,.audition-rail3{z-index:3;padding:0;border:0;border-radius:999px;background:var(--accent)}
.audition-rule{background:linear-gradient(90deg,var(--accent) 0 72%,var(--support-accent) 72% 100%)}
.audition-underline2{background:var(--support-accent)}.audition-underline3{background:color-mix(in srgb,var(--accent) 55%,transparent)}
.audition-hairline{background:color-mix(in srgb,var(--accent) 38%,transparent)}
.audition-spine{background:color-mix(in srgb,var(--support-accent) 42%,transparent)}
.audition-edge{background:var(--accent);border-radius:0}
.audition-rail,.audition-rail2,.audition-rail3{border-radius:0;background:color-mix(in srgb,var(--accent) 8%,transparent)}
.audition-rail2{background:color-mix(in srgb,var(--support-accent) 9%,transparent)}.audition-rail3{background:color-mix(in srgb,var(--accent) 4%,transparent)}
.audition-field,.audition-leftfield,.audition-rightfield,.audition-split,.audition-gridfield,.audition-cutfield{z-index:0;border:0;border-radius:0;background:color-mix(in srgb,var(--accent) 8%,var(--bg))}
.audition-leftfield{background:color-mix(in srgb,var(--accent) 5%,var(--bg))}.audition-rightfield{background:color-mix(in srgb,var(--support-accent) 8%,var(--bg))}.audition-split{background:color-mix(in srgb,var(--accent) 4%,var(--bg))}.audition-gridfield{background-color:color-mix(in srgb,var(--accent) 3%,var(--bg));background-image:linear-gradient(color-mix(in srgb,var(--accent) 5%,transparent) 1px,transparent 1px),linear-gradient(90deg,color-mix(in srgb,var(--accent) 5%,transparent) 1px,transparent 1px);background-size:64px 64px}.audition-cutfield{background:color-mix(in srgb,var(--accent) 9%,var(--bg))}
.audition-panel,.audition-panelwash,.audition-paper1,.audition-paper2,.audition-capsule,.audition-outline,.audition-offsetframe,.audition-window,.audition-band,.audition-topband,.audition-bottomband,.audition-bottombar,.audition-accentblock{z-index:1;border:1px solid color-mix(in srgb,var(--accent) 32%,transparent);background:color-mix(in srgb,var(--surface) 88%,var(--bg));box-shadow:0 16px 34px color-mix(in srgb,var(--text) 8%,transparent)}
.audition-panelwash{background:color-mix(in srgb,var(--accent) 7%,var(--bg));border:0;border-left:10px solid var(--accent);box-shadow:none}.audition-paper1{background:color-mix(in srgb,var(--surface) 94%,var(--bg));transform:rotate(-1deg)}.audition-paper2{background:color-mix(in srgb,var(--surface) 84%,var(--accent));transform:rotate(1.2deg)}
.audition-outline{background:transparent;border:2px solid color-mix(in srgb,var(--accent) 56%,transparent);box-shadow:none}.audition-offsetframe{background:transparent;border:2px solid color-mix(in srgb,var(--support-accent) 52%,transparent);box-shadow:none}.audition-capsule{border-radius:999px;background:color-mix(in srgb,var(--surface) 88%,var(--bg));box-shadow:0 14px 34px color-mix(in srgb,var(--text) 8%,transparent)}
.audition-band,.audition-topband,.audition-bottomband,.audition-bottombar{border:0;border-radius:0;background:color-mix(in srgb,var(--accent) 7%,var(--bg));box-shadow:none}.audition-topband{background:color-mix(in srgb,var(--accent) 12%,var(--bg));border-bottom:5px solid var(--accent)}.audition-bottomband{background:color-mix(in srgb,var(--support-accent) 10%,var(--bg));border-top:4px solid var(--support-accent)}.audition-bottombar{background:var(--accent)}
.audition-accentblock{border:0;border-radius:2px;background:var(--accent);box-shadow:0 20px 40px color-mix(in srgb,var(--accent) 18%,transparent)}
.audition-bracket{z-index:2;border:3px solid var(--accent);border-right-color:transparent;border-bottom-color:transparent;background:transparent}.audition-rule2{z-index:3;background:var(--support-accent);border-radius:999px}.audition-leftbar{z-index:2;background:var(--accent);border:0}.audition-index{z-index:4;display:grid;place-items:center;border:2px solid var(--accent);color:var(--accent);font:800 28px/1 var(--font-mono)}.audition-window{background:transparent;border:1px solid color-mix(in srgb,var(--accent) 45%,transparent);box-shadow:none}.audition-window::after{content:"";position:absolute;inset:28px;border:1px solid color-mix(in srgb,var(--support-accent) 35%,transparent)}
.audition-spine.hairline{background:color-mix(in srgb,var(--accent) 32%,transparent)}
.audition-railfield{z-index:1;background:color-mix(in srgb,var(--accent) 8%,var(--bg));border:0}.audition-cornerframe{z-index:2;border:2px solid color-mix(in srgb,var(--accent) 52%,transparent);background:transparent;clip-path:polygon(0 0,24% 0,24% 2px,2px 2px,2px 24%,0 24%,0 0,100% 0,100% 24%,calc(100% - 2px) 24%,calc(100% - 2px) 2px,76% 2px,76% 0,100% 0,100% 100%,76% 100%,76% calc(100% - 2px),calc(100% - 2px) calc(100% - 2px),calc(100% - 2px) 76%,100% 76%,100% 100%,0 100%,0 76%,2px 76%,2px calc(100% - 2px),24% calc(100% - 2px),24% 100%,0 100%)}
.audition-quietfield{z-index:0;background:transparent;border:0}
'''


def style_string(item: dict[str, int]) -> str:
    return ";".join(f"{key}:{value}px" for key, value in item.items())


def element(kind: str, item: dict, *, content: str = "", fit: str = "container") -> str:
    style = style_string({key: item[key] for key in ("left", "top", "width", "height")})
    classes = f"el audition-{kind}"
    extra = " aria-hidden=\"true\"" if not content else ""
    return (
        f'<div class="{classes}" data-edit-kind="{("text" if content else "visual")}" '
        f'data-edit-fit="{fit}" data-visual-balance-ignore="true" style="{style}"{extra}>'
        f"{escape(content)}"
        "</div>"
    )


def slide_css(variant: dict) -> str:
    return (
        f'#stage .slide[data-audition-id="{variant["id"]}"]{{{BACKGROUND_CSS[variant["bg"]]}}}'
        f'#stage .slide[data-audition-id="{variant["id"]}"] .audition-title{{font-size:{variant["title_size"]}px;color:{variant["title_color"]};text-align:{variant["align"]}}}'
        f'#stage .slide[data-audition-id="{variant["id"]}"] .audition-subtitle{{font-size:{variant["subtitle_size"]}px;color:{variant["subtitle_color"]};text-align:{variant["align"]}}}'
        f'#stage .slide[data-audition-id="{variant["id"]}"] .audition-speaker{{font-size:{variant["speaker_size"]}px;color:{variant["speaker_color"]};text-align:{variant["align"]}}}'
        + (f'#stage .slide[data-audition-id="{variant["id"]}"] .audition-title{{font-family:var(--font-display)}}' if variant["title_class"] == "serif" else "")
    )


def slide_markup(variant: dict) -> str:
    number = variant["number"]
    items = [
        element("title", variant["title_box"], content=CONTENT["title"], fit="text"),
        element("subtitle", variant["subtitle_box"], content=CONTENT["subtitle"], fit="text"),
        element("speaker", variant["speaker_box"], content=CONTENT["speaker"], fit="text"),
    ]
    if variant["rule"]:
        items.append(element("rule", variant["rule"]))
    items.extend(element(item["kind"], item) for item in variant["decor"])
    frame = (
        '<div class="prod-frame diagram-frame audition-frame" data-edit-layout-only="true" '
        f'data-density="low" data-fill-ratio="0.88" data-audition-name="{escape(variant["name"], quote=True)}" '
        'style="left:0;top:0;width:1728px;height:888px;--prod-frame-height:888px">'
        + "".join(items)
        + "</div>"
    )
    active = " active" if number == 1 else ""
    return (
        f'<section class="slide{active}" id="s{number}" data-index="{number - 1}" '
        f'data-page-number="{number}" data-page-count="30" data-layout-id="{escape(variant["id"], quote=True)}" '
        f'data-audition-id="{escape(variant["id"], quote=True)}" data-production-family="cover" '
        'data-content-binding="audition-content" data-media-mode="no-image" data-media-treatment="semantic-native">'
        f'<div class="content" data-content-area="true">{frame}</div></section>'
    )


def build(base_path: Path, output_path: Path, manifest_path: Path) -> None:
    document = base_path.read_text(encoding="utf-8")
    main = '<main id="stage">' + "".join(slide_markup(variant) for variant in VARIANTS) + "</main>"
    document, replaced = re.subn(r'<main id="stage">.*?</main>', main, document, count=1, flags=re.S)
    if replaced != 1:
        raise RuntimeError("Base HTML does not contain exactly one #stage main")
    custom_css = '<style data-css-owner="renderer-base" data-css-scope="cover-layout-audition-30">\n' + GLOBAL_CSS + "\n" + "\n".join(slide_css(variant) for variant in VARIANTS) + "\n</style>"
    document, injected = re.subn(r"</head>", custom_css + "</head>", document, count=1, flags=re.I)
    if injected != 1:
        raise RuntimeError("Base HTML is missing </head>")
    document = document.replace("clinical-evidence-atlas-cover-pilot-v10", "cover-layout-audition-30")
    document = document.replace("layouts=cover-left-title-open-field", "layouts=audition-cover-30")
    document = document.replace("AI 重塑台灣勞動市場", "30 種封面版型提案", 1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8", newline="\n")
    manifest = {
        "skill": "html-pattern-slide",
        "artifact_type": "isolated-layout-audition",
        "renderer": "html",
        "content_mode": "existing-content-audition",
        "source_html_shell": base_path.relative_to(ROOT).as_posix(),
        "formal_catalog_registration": False,
        "layout_count": len(VARIANTS),
        "theme": "clinical-evidence-atlas",
        "content": CONTENT,
        "variants": [
            {"slide": row["number"], "id": row["id"], "name": row["name"]}
            for row in VARIANTS
        ],
        "qa_boundary": "proposal gallery; select individual candidates before formal Layout registration",
        "output": output_path.relative_to(ROOT).as_posix(),
        "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"output": manifest["output"], "manifest": manifest_path.relative_to(ROOT).as_posix(), "variants": len(VARIANTS)}, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    build(args.base.resolve(), args.output.resolve(), args.manifest.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
