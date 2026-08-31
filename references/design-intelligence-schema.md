# 自建簡報設計智能：研究欄位與生成契約

## 目的

本文件定義如何從公開設計案例中研究「設計方法」，再轉成專案自己的簡報生成規則。
研究來源不等於素材來源；任何來源網站的圖片、Logo、插畫、圖示、品牌字型、
元件程式碼或原始 `DESIGN.md` 都不得直接併入正式簡報。

硬性目標：

1. 全部視覺輸出由本專案自建。
2. 不使用既定素材或第三方成品圖。
3. 不把使用者上傳素材當作產生合格簡報的必要條件。
4. 外部案例只提供欄位分布、比例關係、構圖語法、視覺手法與反模式。

## Refero Styles 全量研究結果

研究工具在 2026-07-27 依公開 sitemap 分析 1,290 個 Style 頁，成功 1,290、失敗 0。
原始頁面、圖片與 DESIGN.md 全文均未保存。

### 幾乎固定的核心結構

| 正規化欄位 | 覆蓋率 |
|---|---:|
| Identity / Theme | 100% |
| Colors | 100% |
| Typography | 100% |
| Spacing | 100% |
| Shape | 100% |
| Layout | 100% |
| Components | 100% |
| Do rules | 100% |
| Don't rules | 100% |
| Agent prompt | 100% |
| Implementation tokens | 100% |
| Imagery | 99.6% |
| Surfaces | 98.5% |
| Elevation | 95.6% |

Voice、Iconography、Accessibility、Motion 的覆蓋率分別約為 35.4%、25.0%、20.9%、
8.2%，因此適合作為選配欄位，不應成為每個簡報 Preset 的必要欄位。

### 每份設計的中位複雜度

| 指標 | 中位數 |
|---|---:|
| 色彩 token | 10 |
| 字型 token | 5 |
| 間距 token | 11 |
| 圓角值 | 7 |
| 元件描述 | 12 |
| Do rules | 7 |
| Don't rules | 7 |

這些數字描述網站設計系統的複雜度，不直接成為簡報 token 數。簡報 Preset 應再壓縮成：

- 5–7 個語意色彩角色，而不是複製約 10 個來源色碼。
- 1–2 個字體 voice，並強制符合 AI 生成文字至少 36px。
- 4–6 個可重複使用的簡報元件原語。
- 5–7 條真正可驗證的 Do / Don't。

### 最終採用的自建共通架構

1. `art_direction`：氣氛、視覺隱喻、明暗模式與設計原則。
2. `color_roles`：Canvas、Surface、Text、Muted、Accent、Border。
3. `type_hierarchy`：字體 voice、大小比例、粗細、Tracking、Leading。
4. `spatial_rhythm`：安全區、內容寬度、欄距、留白比例、密度。
5. `geometry`：圓角家族、線寬、容器與分隔語言。
6. `surface_depth`：底色、Pattern、漸層、邊線、陰影與層次規則。
7. `layout_grammar`：Grid、對齊、對稱性、滿版／裁切／邊緣錨定。
8. `decorative_grammar`：裝飾家族、位置、頻率、對比與禁區。
9. `component_grammar`：Card、Metric、Table、Timeline、Diagram、Quote、Callout。
10. `focal_generator`：文字、資料圖、程序式 SVG 插畫或圖解的選擇規則。
11. `constraints`：Do / Don't 與素材獨立性限制。
12. `qa_contract`：36px、孤字換行、群組結構、縮放、溢出與裝飾碰撞檢查。

## 研究來源的角色

| 來源類型 | 代表來源 | 可研究內容 | 不可直接取用 |
|---|---|---|---|
| 結構化設計系統 | Refero Styles | 色彩角色、字體層級、間距、形狀、元件、Do/Don't | 品牌 token、原始 DESIGN.md、圖片與品牌資產 |
| 視覺案例庫 | Minimal Gallery、Recent | 構圖、留白、視覺重心、裁切、節奏、邊緣處理 | 截圖、攝影、插畫、Logo |
| 元件案例庫 | 21st.dev、Uiverse | 元件比例、狀態層級、表面與邊線處理 | 原始元件程式碼與識別性造型 |
| 動態案例庫 | MotionSites | 入場節奏、層次順序、靜態關鍵畫面 | 影片、Shader、3D 素材與品牌動畫 |

### 其他網站的實際抽取範圍

- `Recent`：只抽取 Web Interface、Branding、Product、Typography、Motion、
  Illustration、3D、Editorial、Print、Packaging 等「視覺領域」標籤，以及案例的構圖觀察；
  不取得作品檔。
- `Minimal Gallery`：只抽取網站類型與產業標籤，用來判斷某種視覺語法適合哪類內容；
  不以熱門度直接決定簡報風格。
- `21st.dev`：只研究適合轉譯為投影片的類別，例如 Backgrounds、Borders、
  Comparisons、Features、Galleries、Gradients、Heroes、Stats & KPIs、Steppers、
  Timelines、Cards、Charts、Tables、Grids & Bento；Button、Form、Navigation、
  Loader 等互動元件不列入簡報視覺原語。
- `Uiverse`：以 Patterns、Cards 與少量狀態標記作為 CSS 幾何研究；Button、Input、
  Toggle、Checkbox 與 Loader 不進入簡報 renderer。
- `MotionSites`：只研究畫面進場順序與層次，不允許讓影片、WebGL、Shader 或 3D
  成為投影片成立的必要條件；任何動態想法都必須先有靜態 1920×1080 關鍵畫面。

## 第一層：來源正規化欄位

這一層只描述觀察到的設計規則，不直接描述投影片。

```yaml
design_observation:
  identity:
    source_type: structured-style | visual-gallery | component-gallery | motion-gallery
    source_id: string
    source_url: string
    observed_at: ISO-8601
  art_direction:
    theme: light | dark | mixed
    mood_tags: [string]
    metaphor_tags: [string]
    design_principles: [string]
  color_system:
    canvas_roles: [neutral-dark | neutral-light | tinted]
    surface_levels: integer
    accent_strategy: none | single | paired | multicolor
    contrast_strategy: high | medium | soft
    gradient_strategy: none | atmospheric | structural
  typography:
    voice_count: integer
    display_voice: serif | sans | mono | mixed
    body_voice: serif | sans | mono
    hierarchy_method: size | weight | family-contrast | color | spacing
    tracking: tight | neutral | loose
    leading: tight | neutral | open
  spacing:
    density: compact | balanced | spacious
    base_rhythm: integer
    negative_space_ratio: low | medium | high
  geometry:
    corner_language: sharp | subtle | rounded | pill | mixed
    stroke_language: none | hairline | standard | heavy
    container_language: open | ruled | card | panel | mixed
  depth:
    elevation_language: flat | border-led | soft-shadow | layered-shadow | glow
  layout_grammar:
    alignment: left | center | right | mixed
    grid: free | modular | columns-2 | columns-3 | columns-4 | editorial
    symmetry: symmetric | asymmetric | tension-balanced
    edge_behavior: contained | bleed | crop | anchored-edge
    focal_strategy: type-led | data-led | diagram-led | illustration-led
  decorative_grammar:
    motif_family: none | line | dot | grid | contour | texture | geometric | organic
    placement_zone: edge | corner | gutter | background | focal
    frequency: rare | restrained | repeated
    contrast: whisper | supporting | signature
  component_grammar:
    primitives: [card, badge, quote, table, timeline, diagram, metric, callout]
    separation: whitespace | rule | fill | border | elevation
  imagery_policy:
    dependency: none | optional | essential
    role: none | focal | supporting | texture
  motion_grammar:
    dependency: none | optional | essential
    sequence: [string]
  constraints:
    do: [normalized-rule]
    dont: [normalized-rule]
```

當 `layout_grammar.edge_behavior` 使用 `anchored-edge` 時，具體 renderer adapter 必須把
「貼著哪個父模組邊緣」轉成可驗證的語意 metadata，而不是只留在 CSS 選擇器裡。HTML 目前
以 `data-edit-anchor="bottom"` 表達下緣貼齊；這個關係會回到 editor reflow 與 Browser QA，
也讓 PPTX adapter 能用同一個父模組關係產生 native shape 幾何。

## 第二層：簡報生成欄位

第二層把研究結果轉成 1920×1080 簡報可執行規則。這裡不得保存來源品牌名稱，
而是保存專案自己的生成參數。

```yaml
slide_design_dna:
  preset_id: string
  canvas:
    mode: light | dark | mixed
    surface_count: 1..4
    pattern_family: none | dot | grid | contour | grain | ruled
    pattern_opacity: 0.00..0.16
    gradient_count: 0..2
  typography:
    family_policy: single-family | serif-sans-pair | sans-mono-pair
    generated_min_size_px: 36
    title_weight: 600..800
    subtitle_weight: 500..700
    body_weight: 300..500
    title_to_body_ratio: 1.5..2.8
    line_length_chars_zh: 12..26
  composition:
    title_group_separate: true
    content_group_separate: true
    content_vertical_alignment: center
    safe_area_px: {top: 72, right: 96, bottom: 72, left: 96}
    grid_family: modular | editorial | columns-2 | columns-3 | columns-4
    negative_space_ratio: 0.12..0.42
  geometry:
    radius_family: sharp | subtle | rounded | pill
    stroke_width_px: 0..4
    shadow_level: none | subtle | layered
  decoration:
    generated_only: true
    external_asset_allowed: false
    user_upload_required: false
    allowed_primitives: [css-pattern, css-gradient, svg-path, svg-symbol, html-shape]
    max_signature_motifs_per_slide: 1
    content_overlap_allowed: false
    edge_decoration_reserved: true
  illustration:
    generated_only: true
    source: procedural-svg
    visual_weight_max: 0.32
    editable_group_required: true
  responsive_editing:
    background_scales_with_group: true
    ungroup_preserves_independent_objects: true
    title_and_content_are_separate_groups: true
  qa:
    orphan_line_max_chars_zh: 2
    auto_shrink_floor_px: 36
    random_decorative_shape_forbidden: true
    copied_asset_forbidden: true
    external_runtime_dependency_forbidden: true
```

## 衍生規則

### 可以學習

- 色彩「角色」與用量比例，例如單一強調色只佔小面積。
- 標題與內文之間的比例、粗細與家族對比。
- 留白、欄寬、對齊與邊緣張力。
- Pattern、Hairline、Surface、Shadow 的使用條件。
- 卡片、表格、時間軸與圖解的分隔方式。
- 哪些效果明確被列為 Do / Don't。

### 不可搬運

- 來源網站的色碼組合原封不動複製。
- 來源品牌專用字型、Logo、圖片、插畫或圖示。
- Uiverse、21st.dev 等網站的元件原始碼直接貼入 renderer。
- 截圖、影片、3D 場景或 Shader 當作簡報背景。
- 只因案例中有圓、Blob 或漸層，就把它變成無語意裝飾。

## 研究與生成的隔離

研究工具輸出只能包含：

- 正規化欄位。
- 欄位覆蓋率。
- 數量、比例與布林手法標記。
- 經人工重新命名後的設計 archetype。

研究工具不得保存：

- 完整 `DESIGN.md`。
- 原始 HTML。
- 來源圖片 URL 的下載內容。
- 第三方元件程式碼。
- 品牌識別性資產。

正式 renderer 只能讀取經過人工審核的 `slide_design_dna`，不得在生成投影片時連線到
Refero、Minimal Gallery、Recent、21st.dev、Uiverse 或 MotionSites。
