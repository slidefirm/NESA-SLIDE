#!/usr/bin/env python3
"""Hand-authored six-direction Cover audition.

Each slide is an independent composition direction.  This is intentionally
not a parameterized 30-layout generator and it stays outside the formal
catalog until a human selects a direction for promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_HTML = ROOT / "artifacts/experiments/cover-left-title-open-field-pilot-20260821/clinical-evidence-atlas/clinical-evidence-atlas-cover-pilot-v10.html"
OUTPUT_HTML = ROOT / "artifacts/experiments/cover-left-title-open-field-pilot-20260821/clinical-evidence-atlas/cover-direction-pilot-6-20260822.html"
OUTPUT_MANIFEST = ROOT / "artifacts/experiments/cover-left-title-open-field-pilot-20260821/clinical-evidence-atlas/cover-direction-pilot-6-20260822.manifest.json"

TITLE = "AI 重塑台灣勞動市場"
SUBTITLE = "人口斷崖、任務自動化與財富雙軌化交織下的就業結構轉型"
SPEAKER = "台灣就業環境分析報告"


def style(**values: int | str) -> str:
    pairs = []
    for key, value in values.items():
        css_key = key.replace("_", "-")
        pairs.append(f"{css_key}:{value}px" if isinstance(value, int) else f"{css_key}:{value}")
    return ";".join(pairs)


def text_node(role: str, content: str, **geometry: int | str) -> str:
    return (
        f'<div class="el direction-{role}" data-edit-kind="text" data-edit-fit="text" '
        f'style="{style(**geometry)}">{escape(content)}</div>'
    )


def visual_node(kind: str, **geometry: int | str) -> str:
    return (
        f'<div class="el direction-{kind}" data-edit-kind="visual" data-edit-fit="container" '
        f'data-visual-balance-ignore="true" aria-hidden="true" style="{style(**geometry)}"></div>'
    )


def section(number: int, direction_id: str, name: str, markup: str) -> str:
    active = " active" if number == 1 else ""
    return (
        f'<section class="slide{active}" id="s{number}" data-index="{number - 1}" '
        f'data-page-number="{number}" data-page-count="6" '
        f'data-layout-id="audition-{direction_id}" data-direction-id="{direction_id}" '
        f'data-direction-name="{escape(name, quote=True)}" data-production-family="cover" '
        'data-content-binding="fixed-reference-cover" data-media-mode="no-image" '
        'data-media-treatment="semantic-native">'
        '<div class="content" data-content-area="true">'
        '<div class="prod-frame diagram-frame direction-frame" data-edit-layout-only="true" '
        f'data-direction-name="{escape(name, quote=True)}" style="left:0;top:0;width:1728px;height:888px;--prod-frame-height:888px">'
        f"{markup}</div></div></section>"
    )


def evidence_axis() -> str:
    return section(
        1,
        "evidence-axis",
        "證據軸／右側靜場",
        "".join(
            [
                visual_node("edge", left=0, top=-96, width=18, height=1080),
                visual_node("right-field", left=1175, top=-96, width=649, height=1080),
                visual_node("coral-spine", left=1279, top=-96, width=7, height=1080),
                text_node("title", TITLE, left=112, top=280, width=990, height=154),
                visual_node("rule", left=112, top=434, width=244, height=7),
                text_node("subtitle", SUBTITLE, left=112, top=463, width=1040, height=62),
                text_node("speaker", SPEAKER, left=112, top=540, width=620, height=54),
            ]
        ),
    )


def horizon() -> str:
    return section(
        2,
        "horizon-ledger",
        "地平線／低位主張",
        "".join(
            [
                visual_node("edge", left=0, top=-96, width=10, height=1080),
                visual_node("horizon-field", left=0, top=574, width=1728, height=314),
                visual_node("horizon-rule", left=112, top=662, width=1460, height=5),
                visual_node("horizon-cap", left=1320, top=634, width=252, height=33),
                text_node("title", TITLE, left=112, top=390, width=1120, height=154),
                text_node("subtitle", SUBTITLE, left=112, top=552, width=1110, height=62),
                text_node("speaker", SPEAKER, left=112, top=714, width=620, height=54),
            ]
        ),
    )


def margin_ledger() -> str:
    return section(
        3,
        "margin-ledger",
        "邊註帳本／文件欄",
        "".join(
            [
                visual_node("margin-rail", left=0, top=-96, width=260, height=1080),
                visual_node("margin-line", left=304, top=0, width=3, height=888),
                visual_node("margin-tick", left=80, top=248, width=132, height=6),
                visual_node("margin-tick", left=80, top=382, width=86, height=6),
                visual_node("margin-tick", left=80, top=516, width=132, height=6),
                visual_node("margin-tick", left=80, top=650, width=70, height=6),
                text_node("title", TITLE, left=392, top=240, width=1060, height=164),
                visual_node("rule", left=392, top=421, width=340, height=7),
                text_node("subtitle", SUBTITLE, left=392, top=455, width=1030, height=64),
                text_node("speaker", SPEAKER, left=392, top=556, width=640, height=54),
            ]
        ),
    )


def archive_frame() -> str:
    return section(
        4,
        "archive-frame",
        "檔案框景／內收主張",
        "".join(
            [
                visual_node("edge", left=0, top=-96, width=12, height=1080),
                visual_node("archive-frame", left=92, top=112, width=1290, height=640),
                visual_node("archive-corner", left=92, top=112, width=78, height=78),
                visual_node("archive-corner", left=1304, top=674, width=78, height=78),
                visual_node("right-field", left=1440, top=-96, width=384, height=1080),
                text_node("title", TITLE, left=190, top=268, width=1010, height=154),
                visual_node("rule", left=190, top=430, width=244, height=7),
                text_node("subtitle", SUBTITLE, left=190, top=470, width=1020, height=64),
                text_node("speaker", SPEAKER, left=190, top=580, width=640, height=54),
            ]
        ),
    )


def sidecar() -> str:
    return section(
        5,
        "sidecar-field",
        "側欄支撐／雙場閱讀",
        "".join(
            [
                visual_node("edge", left=0, top=-96, width=14, height=1080),
                visual_node("sidecar-field", left=1018, top=-96, width=806, height=1080),
                visual_node("sidecar-rail", left=1018, top=0, width=4, height=888),
                visual_node("sidecar-rule", left=1120, top=224, width=480, height=3),
                visual_node("sidecar-marker", left=1120, top=438, width=118, height=6),
                visual_node("sidecar-rule", left=1120, top=650, width=320, height=3),
                text_node("title", TITLE, left=112, top=270, width=824, height=164),
                visual_node("rule", left=112, top=450, width=244, height=7),
                text_node("subtitle", SUBTITLE, left=112, top=486, width=790, height=100),
                text_node("speaker", SPEAKER, left=112, top=640, width=620, height=54),
            ]
        ),
    )


def bottom_brief() -> str:
    return section(
        6,
        "bottom-brief",
        "下緣簡報／上方停頓",
        "".join(
            [
                visual_node("edge", left=0, top=-96, width=18, height=1080),
                visual_node("bottom-baseline", left=0, top=846, width=1728, height=12),
                visual_node("bottom-accent", left=112, top=818, width=440, height=5),
                visual_node("right-field", left=1360, top=-96, width=464, height=1080),
                text_node("title", TITLE, left=112, top=522, width=1170, height=164),
                visual_node("rule", left=112, top=692, width=244, height=7),
                text_node("subtitle", SUBTITLE, left=112, top=728, width=1140, height=62),
                text_node("speaker", SPEAKER, left=112, top=796, width=620, height=46),
            ]
        ),
    )


PILOT_SLIDES = [evidence_axis, horizon, margin_ledger, archive_frame, sidecar, bottom_brief]


CSS = r'''
#stage .slide[data-direction-id]{background-color:var(--bg);color:var(--text);overflow:hidden}
.direction-frame{position:absolute;left:0;top:0;width:1728px;height:888px;overflow:visible;pointer-events:none}
.direction-frame>.el{position:absolute;box-sizing:border-box;pointer-events:auto}
.direction-title{z-index:4;margin:0;padding:0;background:transparent;border:0;font:800 104px/1.03 var(--font-heading);letter-spacing:-.055em;color:var(--text)}
.direction-subtitle{z-index:4;margin:0;padding:0;background:transparent;border:0;font:500 38px/1.38 var(--font-body);color:var(--muted)}
.direction-speaker{z-index:4;margin:0;padding:0;background:transparent;border:0;font:800 36px/1 var(--font-heading);letter-spacing:.08em;color:var(--accent)}
.direction-edge{z-index:0;border:0;border-radius:0;background:var(--accent)}
.direction-right-field{z-index:0;border:0;border-radius:0;background:color-mix(in srgb,var(--accent) 8%,var(--bg))}
.direction-coral-spine{z-index:1;border:0;border-radius:0;background:color-mix(in srgb,var(--support-accent) 22%,transparent)}
.direction-rule{z-index:3;border:0;border-radius:999px;background:linear-gradient(90deg,var(--accent) 0 72%,var(--support-accent) 72% 100%)}
#stage .slide[data-direction-id="evidence-axis"]{background-image:linear-gradient(color-mix(in srgb,var(--accent) 2.4%,transparent) 1px,transparent 1px),linear-gradient(90deg,color-mix(in srgb,var(--accent) 2.4%,transparent) 1px,transparent 1px);background-size:64px 64px,64px 64px}
#stage .slide[data-direction-id="horizon-ledger"]{background-image:linear-gradient(color-mix(in srgb,var(--accent) 1.8%,transparent) 1px,transparent 1px),linear-gradient(90deg,color-mix(in srgb,var(--accent) 1.8%,transparent) 1px,transparent 1px);background-size:80px 80px}
.direction-horizon-field{z-index:0;border:0;border-radius:0;background:color-mix(in srgb,var(--accent) 6%,var(--bg))}
.direction-horizon-rule{z-index:2;border:0;border-radius:0;background:var(--accent)}
.direction-horizon-cap{z-index:2;border:0;border-radius:0;background:var(--support-accent)}
#stage .slide[data-direction-id="margin-ledger"]{background-image:linear-gradient(color-mix(in srgb,var(--accent) 1.7%,transparent) 1px,transparent 1px);background-size:100% 72px}
.direction-margin-rail{z-index:0;border:0;border-radius:0;background:color-mix(in srgb,var(--accent) 5%,var(--bg))}
.direction-margin-line{z-index:1;border:0;border-radius:0;background:color-mix(in srgb,var(--accent) 45%,transparent)}
.direction-margin-tick{z-index:2;border:0;border-radius:999px;background:var(--accent)}
#stage .slide[data-direction-id="archive-frame"]{background-image:linear-gradient(color-mix(in srgb,var(--accent) 1.6%,transparent) 1px,transparent 1px),linear-gradient(90deg,color-mix(in srgb,var(--accent) 1.6%,transparent) 1px,transparent 1px);background-size:72px 72px}
.direction-archive-frame{z-index:1;border:2px solid color-mix(in srgb,var(--accent) 42%,transparent);background:color-mix(in srgb,var(--surface) 72%,var(--bg));box-shadow:0 18px 46px color-mix(in srgb,var(--text) 7%,transparent)}
.direction-archive-corner{z-index:2;border:6px solid var(--accent);border-right:0;border-bottom:0;background:transparent}.direction-archive-corner+ .direction-archive-corner{border-color:var(--support-accent);border-left:0;border-top:0}
#stage .slide[data-direction-id="sidecar-field"]{background-image:linear-gradient(color-mix(in srgb,var(--accent) 1.8%,transparent) 1px,transparent 1px);background-size:100% 68px}
.direction-sidecar-field{z-index:0;border:0;border-radius:0;background:color-mix(in srgb,var(--accent) 7%,var(--bg))}
.direction-sidecar-rail{z-index:2;border:0;border-radius:0;background:var(--accent)}
.direction-sidecar-rule{z-index:2;border:0;border-radius:0;background:color-mix(in srgb,var(--accent) 42%,transparent)}
.direction-sidecar-marker{z-index:2;border:0;border-radius:999px;background:var(--support-accent)}
#stage .slide[data-direction-id="bottom-brief"]{background-image:linear-gradient(color-mix(in srgb,var(--accent) 1.5%,transparent) 1px,transparent 1px),linear-gradient(90deg,color-mix(in srgb,var(--accent) 1.5%,transparent) 1px,transparent 1px);background-size:96px 96px}
.direction-bottom-baseline{z-index:1;border:0;border-radius:0;background:var(--accent)}
.direction-bottom-accent{z-index:2;border:0;border-radius:999px;background:var(--support-accent)}
'''


DIRECTION_BRIEF = [
    {
        "slide": 1,
        "id": "evidence-axis",
        "name": "證據軸／右側靜場",
        "signature_composition": "左側主張群與右側無文字靜場形成一條閱讀軸。",
        "color_role": "色面只壓低右側場域，珊瑚線只標示結構分界。",
    },
    {
        "slide": 2,
        "id": "horizon-ledger",
        "name": "地平線／低位主張",
        "signature_composition": "一條水平基準線把上方思考空間與下方結論區分開。",
        "color_role": "低位淡色面只讓水平地平線有重量。",
    },
    {
        "slide": 3,
        "id": "margin-ledger",
        "name": "邊註帳本／文件欄",
        "signature_composition": "左側窄邊註欄與正文欄形成出版物式閱讀關係。",
        "color_role": "色彩只放在導讀刻度，不形成主角。",
    },
    {
        "slide": 4,
        "id": "archive-frame",
        "name": "檔案框景／內收主張",
        "signature_composition": "內收檔案框把一個命題放入可追溯的文件邊界。",
        "color_role": "色彩只標記框角與邊帶。",
    },
    {
        "slide": 5,
        "id": "sidecar-field",
        "name": "側欄支撐／雙場閱讀",
        "signature_composition": "主張保留在左側，右側是無文字的支持性資料場。",
        "color_role": "右側淡色面只能承接層次，不承擔版面本身。",
    },
    {
        "slide": 6,
        "id": "bottom-brief",
        "name": "下緣簡報／上方停頓",
        "signature_composition": "內容壓在下緣，讓上方大片留白形成決策前的停頓。",
        "color_role": "底線提供重量，右側淡場只維持平衡。",
    },
]


def build(base_html: Path, output_html: Path, output_manifest: Path) -> None:
    source = base_html.read_text(encoding="utf-8")
    stage = '<main id="stage">' + "".join(factory() for factory in PILOT_SLIDES) + "</main>"
    document, stage_count = re.subn(r'<main id="stage">.*?</main>', stage, source, count=1, flags=re.S)
    if stage_count != 1:
        raise RuntimeError("Base HTML must contain exactly one #stage main")
    document, title_count = re.subn(r"<title>.*?</title>", "<title>封面方向 Pilot 06</title>", document, count=1, flags=re.S | re.I)
    if title_count != 1:
        raise RuntimeError("Base HTML has no document title")
    owned_css = '<style data-css-owner="renderer-base" data-css-scope="cover-direction-pilot-6">\n' + CSS + "\n</style>"
    document, css_count = re.subn(r"</head>", owned_css + "</head>", document, count=1, flags=re.I)
    if css_count != 1:
        raise RuntimeError("Base HTML has no head end tag")
    document = document.replace("layouts=cover-left-title-open-field", "layouts=cover-direction-pilot-6", 1)
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(document, encoding="utf-8", newline="\n")
    manifest = {
        "skill": "design-presentations + html-pattern-slide",
        "artifact_type": "hand-authored-cover-direction-pilot",
        "renderer": "editable-html",
        "content_mode": "fixed-reference-content-for-layout-comparison",
        "formal_catalog_registration": False,
        "source_shell": base_html.relative_to(ROOT).as_posix(),
        "design_brief": {
            "visual_genre": "evidence-led editorial cover system",
            "narrative_metaphor": "一份決策簡報進入安靜、可追溯的證據場。",
            "signature_move": "清楚閱讀軸對照低資訊密度的支持場。",
            "spatial_rule": "文字群可改變錨點，但色面永遠只做支持，不取代構圖。",
            "forbidden_cliches": ["隨機色塊", "漂浮卡片", "無意義斜線", "直排 metadata", "只改座標的假變體"],
        },
        "directions": DIRECTION_BRIEF,
        "output": output_html.relative_to(ROOT).as_posix(),
        "output_sha256": hashlib.sha256(output_html.read_bytes()).hexdigest(),
        "qa_boundary": "human review of six independently authored directions before any 30-layout expansion",
    }
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"output": manifest["output"], "directions": len(DIRECTION_BRIEF)}, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=BASE_HTML)
    parser.add_argument("--output", type=Path, default=OUTPUT_HTML)
    parser.add_argument("--manifest", type=Path, default=OUTPUT_MANIFEST)
    args = parser.parse_args()
    build(args.base.resolve(), args.output.resolve(), args.manifest.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
