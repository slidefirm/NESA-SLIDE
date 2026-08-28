from __future__ import annotations

from pathlib import Path

from generate_theme_gallery import load_theme


ROOT = Path(__file__).resolve().parents[1]
THEMES_DIR = ROOT / "prompt_system" / "themes"
OUT_DIR = ROOT / "artifacts" / "generated-prompts" / "theme-previews"


def yaml_quote(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def typography_family(value: str) -> str:
    value = str(value or "")
    if "\n" in value:
        for line in value.splitlines():
            line = line.strip()
            if line.startswith("family:"):
                return line.split(":", 1)[1].strip().strip('"')
    if "family:" in value:
        return value.split("family:", 1)[1].splitlines()[0].strip().strip('"')
    if "Noto Serif" in value:
        return "Noto Serif TC"
    return "Noto Sans TC"


def illustration_type(value: str) -> str:
    value = str(value or "")
    for option in ["扁平插畫", "3D風格", "線條圖示", "抽象藝術", "無"]:
        if option in value:
            return option
    return "無"


def support_lines(theme: dict) -> str:
    support = theme.get("support_hexes", [])
    if not support:
        return '    support: []'
    lines = ["    support:"]
    for color in support:
        lines.extend([
            f"      - color: {yaml_quote(color)}",
            "        usage:",
            "          - 輔助底塊、弱層級面板、邊界或裝飾細節",
        ])
    return "\n".join(lines)


def prompt_for_theme(theme: dict) -> str:
    theme_id = theme["id"]
    display_name = theme["display_name"]
    support = support_lines(theme)
    mood = "、".join(theme.get("mood", []))
    deco = "、".join(theme.get("deco_names", [])[:5]) or "以邊角與外框裝飾呈現"
    heading_family = typography_family(theme.get("typography_heading", ""))
    body_family = typography_family(theme.get("typography_body", ""))
    illustration = illustration_type(theme.get("illustration_default", ""))

    return f"""page_type_and_mood:
  prompt: >
    16:9 單頁 theme preview，固定使用 cards-1-plus-3 版面。這張圖只展示「{display_name}」的視覺語言，
    不展示特定題材或業務語境；情緒關鍵字為：{mood}。

visual_base_2a:
  background:
    color: {yaml_quote(theme.get("background_color", "#FFFFFF"))}
    texture: >
      {theme.get("background_style", "乾淨背景")}。背景必須服務 1+3 模組陣列，
      讓標題區與三張平行卡片能清楚呈現同一套 theme 的色彩、材質與裝飾語彙。
    bleed: "none"

  typography:
    heading:
      color: {yaml_quote(theme.get("primary", "#111111"))}
      family: {yaml_quote(heading_family)}
      weight: "依 theme heading 指引，使用清楚的中高粗細"
      size_pt: "42-56"
    body:
      color:
        - {yaml_quote(theme.get("secondary", "#555555"))}
        - "依 theme 次層文字色彩"
      family: {yaml_quote(body_family)}
      weight: "regular / medium"
      size_pt: "18-24"
      line_spacing: "normal"

  color_system:
    primary:
      color: {yaml_quote(theme.get("primary", "#111111"))}
      usage:
        - "主標、主要結構與高權重文字"
    secondary:
      color: {yaml_quote(theme.get("secondary", "#555555"))}
      usage:
        - "次要文字、輔助線與低權重標籤"
    accent:
      color: {yaml_quote(theme.get("accent", "#999999"))}
      usage:
        - "小面積強調：線條、編號、圖示描邊、重點標記；不得作大面積填色"
{support}

  illustration_style:
    type: {yaml_quote(illustration)}
    note: >
      只允許使用抽象、圖示或線條化的視覺元素來展示 theme；不得加入具體產業場景、
      人物故事、實物照片或宣傳海報語境。

corner_decoration_2b:
  rule: >
    裝飾只能落在外框、角落、模組邊界與三張卡片之間的縫隙；不得壓住標題、
    副標與三個模組內的文字。優先使用這個 theme 的裝飾詞彙：{deco}。
  outer_frame:
    decoration: >
      沿投影片邊緣放置低干擾的 theme 裝飾，呈現此風格的邊角語言與材質特徵。
  module_edges:
    decoration: >
      三張模組卡片的外框、分隔線、編號或角標使用 accent 色與 theme 裝飾詞彙，
      讓相同 1+3 版面在不同 theme 下有清楚差異。

layout_description:
  structure: "cards-1-plus-3：上方一個主標題與副標，下方三個等寬平行模組。"
  title_region:
    horizontal_range: "8%-92%"
    vertical_range: "10%-20%"
    description: "置中主標題，文字簡短，只命名本張 theme preview。"
  body_region:
    horizontal_range: "8%-92%"
    vertical_range: "34%-76%"
    description: "三張等寬卡片並列，分別展示色彩、字體與裝飾語彙。"
  image_column: "none"
  alignment_rule: "title.centerX == safe_area.centerX；module-1.top == module-2.top == module-3.top；三個 module 寬高相同。"

content:
  title: {yaml_quote(display_name)}
  subtitle: "同一個 1+3 版面，用來檢視這套 theme 的色彩、字體、材質與裝飾。"
  modules:
    - label: "色彩秩序"
      note: "展示背景、主色、輔色與強調色的層級。"
    - label: "字體層級"
      note: "展示標題、說明文字與短標籤的比例。"
    - label: "裝飾語彙"
      note: "展示邊角、框線、圖示或紋理的使用方式。"
  visible_text_language: "所有可見文字使用繁體中文；除必要數字與 theme id 外，不出現英文。"

safe_zone_constraints:
  hard_constraint: >
    All content — title, subtitle, module labels, body text, icons, and decorative badges —
    must stay within 10%–90% of both horizontal and vertical range.
  edge_rule: "No readable element touches or crosses the slide edge."
  exception: >
    Low-contrast background texture and edge decoration may extend outside the safe zone,
    but readable content and card labels must remain inside the safe zone.

closing_design_intent:
  prompt: >
    Generate one 16:9 Traditional Chinese presentation slide preview using the cards-1-plus-3 layout.
    The slide is a neutral theme specimen for {display_name}, not a cover and not a domain-specific slide.
    Keep the same structure across all theme previews: title/subtitle on top, three equal modules below.
    Make the visual difference come from palette, typography, texture, framing, and decoration only.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted(THEMES_DIR.glob("*.yaml")):
        theme = load_theme(path)
        if not theme:
            continue
        out = OUT_DIR / f"{theme['id']}.cards-1-plus-3.assembled.yaml"
        out.write_text(prompt_for_theme(theme), encoding="utf-8")
        count += 1
        print(f"ok {theme['id']} -> {out.relative_to(ROOT)}")
    print(f"generated {count} theme preview prompts")


if __name__ == "__main__":
    main()
