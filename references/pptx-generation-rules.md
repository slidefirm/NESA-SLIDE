# PPTX 生成規則

這份文件只在把 assembled YAML、專案 HTML 簡報或 PPTX 背景母片規格轉成可編輯 PPTX 時適用。
跨 Renderer 的共用排版與驗收底線見 `references/presentation-production-contract.md`。

## Source of truth

### PPTX Variant boundary

PPTX 先依內容選擇既有 Layout，再由 `prompt_system/renderers/pptx/layout-variants/catalog.yaml`
選擇相容的 renderer-specific Variant。Variant 是投影層，不能回寫或改造
`prompt_system/layouts/*.yaml`；固定 anatomy 使用 base projection，複合 anatomy 才拆成
atomic placeholders。每頁 manifest 必須保存 `variant_candidates`、`selected_variant_id`、
`selection_basis` 與 `placeholder_schema`。若傳入 `layout_variant_id`，不相容時必須失敗。

Variant catalog 不是 Layout 白名單。所有未列入 bespoke Variant 的 active Layout，必須從對應
PPTX adapter 的 `slot_entries` 建立 renderer-owned baseline projection；因此選 Layout 時不能因
「沒有專用 Variant」而退回空白投影片。只有已標記 retired 的 Layout 不進入正式 registry。

PPTX Placeholder 只使用 `title`、`subtitle`、`body`、`picture`、`chart`、`table` 六種型別。
背景圖與裝飾不建立 `picture`／內容 Placeholder；人物卡、模組卡等 composite slot 必須在
選定 Variant 的 projection 中拆成可單獨編輯的原子欄位。`title-role`、`role` 等人物職稱
欄位是 `subtitle`，不是頁面 `title`。
`placeholder_schema.frame_policy` 對 `title`／`subtitle` 預設為 `fixed`；finalizer 不得對含有
固定 frame 成員的 content group 重新定位、縮放、fit 或重排。其他文字欄位預設為 `content-fit`，
舊 manifest 沒有此欄位時才沿用既有 reflow 行為。
正式輸出預設 `reset_policy: layout-authoritative`：Slide 只填入 Placeholder 內容，不改寫其
幾何；`legacy-reflow` 僅能由 manifest 明確 opt-in。這使 PowerPoint Reset 前後維持相同的
Placeholder x/y/w/h，避免最後回到 Layout 預設框。

PPTX 可以使用 Surface，但 Surface 必須是 renderer-owned 的原生 shape layer：由 manifest 的
`surfaces` 宣告 region、shape、fill、transparency 與 line，寫入 child Layout，位於背景圖與
Placeholder 之間。Surface 不得用整頁圖片或 HTML 截圖冒充；沒有被選定的 Surface 不得出現在
該頁 Layout。

PPTX renderer 的主要來源依序為：

1. 內容 manifest 的實際文字、素材、layout id 與 theme id；
2. `prompt_system/layouts/{layout-id}.yaml` 與對應 PPTX layout adapter；
3. `prompt_system/themes/{theme-id}.yaml` 與對應 PPTX theme adapter；
4. 若使用 `freeform-composition`，內容 manifest 內的逐頁 Composition Plan、stage-space
   geometry 與 constraint ledger；
5. PPTX renderer 的正式 Composition Plan 與 native object materialization 規則；
6. HTML DOM/CSS 的實際文字、圖片來源與最終幾何，僅作校準與使用者編輯結果的輸入。

### PPTX seeded randomization

需要隨機 PPTX 時，先由 `scripts/pptx_randomization.py` 產生 selection manifest，再由
`scripts/render_pptx_matrix.mjs --selection-manifest` 建檔。`seed` 會實際抽選語意 Layout
sequence，並在存在多個相容候選時抽選 PPTX Variant；相同 seed 必須得到相同 Layout／Variant
與背景選擇，不同 seed 才能形成可觀察差異。manifest 必須保存每次 draw 的 pool、state、index、
選定結果與 `randomized_dimensions`，不能只在輸出檔名寫一個 random 字樣。Theme 預設固定；只有
明確使用 `--random-theme` 才將 Theme 放入抽選，而且候選必須有 Theme-compatible ready background。

assembled YAML 是 Image2 的 downstream payload，不是 PPTX 的必要通用輸入。若任務同時有
assembled YAML，可以讀取其中內容，但 theme/layout 身分與結構仍以 core + adapter 為準。

禁止把整頁 HTML 截圖當成唯一投影片內容。PPTX 的正式預設改為 `Image2 背景 + native Placeholder`：
背景視覺可以 rasterize，但標題、正文、表格、圖表、基本 shape 與內容圖片必須維持原生可編輯物件。

## Image2 背景母片流程

每個 Theme 先生成六張 16:9 無字底圖：

1. `cover`
2. `toc`
3. `content-a`（左側留白）
4. `content-b`（右側留白）
5. `content-c`（中央大留白）
6. `qa`

底圖只能包含照片、材質、漸層、光影、抽象形狀與邊角裝飾。禁止任何文字、字母、數字、
logo 字樣、假卡片、假圖表、內容框、格線、面板或 Placeholder 外框。

`prompt_system/pptx_background_sets/{theme-id}.yaml` 必須在生成前宣告 `blank_regions`、
`decoration_zones` 與 Placeholder；不得生成後才靠肉眼猜空白位置。七段式 prompt 由
`scripts/generate_pptx_background_prompts.py` 產生，正式 PNG 仍依 Image2 QA 流程逐張生成與檢查。

當次 registry 的全部邏輯 Layout 透過 PPTX adapter 的 `background_role` 投影到上述六種母片角色；
內容語意仍來自 core Layout，但視覺底圖不隨 Layout 數量重複複製。實際數量以
`prompt_system/layouts/*.yaml` 與 `artifacts/renderer-matrix/matrix.json` 的當次一致性檢查為準，
不得把歷史 audit 的數字當成固定常數。

垂直重心不以固定大型文字框的上邊緣計算。對宣告 `content_groups` 的版型，必須先取得
實際文字高度、縮合各 Placeholder，再連同層級間距將整組內容於可用區域垂直置中。
文字較少時向中央收合；文字較多時才向上下擴張。

標題與副標的斷行也必須先量測。若一行可容納就不插入換行；只有確定需要多行，且標點
落在全文約 34%–66% 的平衡區間內、斷開後兩側都能放入可用寬度時，才在該標點後加入
軟換行。沒有合適標點時保留 PowerPoint 自然換行，不得把所有逗點一律轉成換行。

## 三層母片模型

使用 renderer 建立 seed deck，並用 PowerPoint 原生物件模型寫入真正的
master/layout 關係：

- Master：每個 theme 一個，管理 color map 與共用字體語意。
- Layout：六個 Image2 背景角色掛到 theme master；背景圖片放在 child layout，並管理 placeholders。
- Slide：只放該頁內容與必要 override，並以 `slide.setLayout(layout)` 連結版面。

同 theme 的多張投影片不得各自複製相同頁首、頁尾或背景物件冒充母片。背景圖片不得放在
一般 slide；必須放在 child layout，讓一般編輯模式無法誤選。由於目前 saved-template
re-import 路徑不穩，且 `@oai/artifact-tool` 匯出 Custom Layout 圖片並不可靠，母片底圖、
Placeholder 與示範內容必須由 PowerPoint 原生物件模型在同一次建檔中完成。

## HTML-like Freeform Composition

固定的六種 Image2 background role 只代表一套背景資產家族，不代表 PPTX 每頁只能使用六種
固定構圖。當 deck manifest 宣告 `mode: freeform-composition` 時：

- Master 管理 Theme 的色彩、字體語意與全域 chrome；
- Custom Layout 管理該頁 Composition 的 background、safe area 投影與 named Placeholder；
- Slide 依 Layout 放入 native text、shape、connector、image、table 或 chart；
- Composition Plan 使用 1920×1080 stage-space，明確保存每個物件的 id、role、geometry、
  z-order、文字樣式與可見內容聯集；
- 內容群組先以實際文字高度收合，再在 Content Area 內計算重心與邊界留白；
- 每個 visible text slot 必須直接 materialize 成對應 Placeholder 或有明確 provenance 的
  native text object，不能用空 Placeholder 加另一個無關文字框冒充可編輯欄位。

這條路徑保留 HTML 級的逐頁構圖自由度，但仍以 PPTX 的 Master → Custom Layout → Slide
關係承接共用規則。不同 Composition 可以建立不同 Custom Layout；不得為了減少 Layout
數量而把不相容的幾何塞進同一個固定版型。

## 兩條正式建檔路徑

- **Codex／專案正式建檔**：使用 JavaScript ES module 與 `@oai/artifact-tool`，由專案來源建立、重建或批次驗收 PPTX。
- **HTML 編輯器一鍵匯出**：使用 `edit-mode.js` 內嵌的 PptxGenJS browser adapter，在瀏覽器中讀取使用者編輯後的 DOM manifest 並下載 PPTX。

兩條路徑必須消費同一份 content／DOM manifest，並遵守相同的 master、Custom Layout、Placeholder、
native object 與 QA 契約。工具只由使用入口決定；不得把其中一條路徑的能力或限制誤套到另一條，
也不得使用整頁 screenshot、fidelity overlay 或圖片化文字降低可編輯性。

## HTML 逐頁圖片背景匯出

逐頁生成圖片背景由 `.agents/skills/slide-background-image/SKILL.md` 管理。新建含圖片版型的
HTML 先使用 `.agents/skills/html-image-slide/SKILL.md` 完成 Layout handoff，再把 foreground
交給背景 Skill。已有可編輯 HTML 只要附加／替換背景時，直接使用背景 Skill 並保留原本 Layout
與前景。每頁背景都必須依實際 foreground occupied region 量測，再生成或套用一張 16:9 raster。
圖片只補足或支撐相容的視覺區域，不能重畫文字、卡片、箭頭、圖表或其他可編輯前景。

HTML final artifact 必須把背景資產內嵌成 data URL（並可保留相鄰的原始圖片副本作為 provenance）。
這是為了讓 `file://` 成品與瀏覽器匯出路徑不依賴本機 server，也讓 `edit-mode.js` 能在建立 DOM
manifest 時取得 `backgroundImage.dataUrl`。PPTX browser adapter 必須為每一頁建立對應的 child
layout，將該頁圖片放在 layout/master 的最底層；slide XML 不得放置這張背景圖，前景文字、shape、
圖片與表格仍須以原生物件輸出。

QA 必須同時證明：HTML 每頁只有一張對應背景、manifest 每頁都有 raster data URL、PPTX package
的圖片位於 child layout/master 而非一般 slide、PowerPoint 原生渲染逐頁成功，且沒有 fidelity overlay。

## HTML 到 PPTX 的映射

HTML 應優先使用 renderer 已存在的語意標記：`.slide`、`.el`、`data-edit-composite`、`data-edit-layer`。每個可轉換節點必須有穩定名稱；若缺少名稱，轉換器以 slide index、DOM path 與角色產生 deterministic id。

HTML 編輯器的一鍵匯出正式路徑使用 `edit-mode.js → 內嵌 PptxGenJS browser adapter → browser download`。
瀏覽器負責量測使用者編輯後的 stage-space geometry 與 computed style，再於同一頁面記憶體內
建立 Custom Layout、slides 與原生物件；因此 `file://`、公開靜態站與 localhost 都不得依賴
另行啟動本機 server。`edit-mode.js → /__export-pptx → @oai/artifact-tool` 保留為開發備援與
交叉 QA 路徑；兩個 adapter 都必須消費同一份 DOM manifest，不得改變 YAML／HTML renderer 邊界。

匯出必須採 native-editable 模式，不得加入整頁 screenshot、fidelity overlay 或其他覆蓋可編輯物件的
全頁圖片。DOM manifest 固定使用 1920×1080 CSS pixel 座標系統；每個節點的 left、top、width、height、
rotation 與 DOM paint order 必須直接換算成 PowerPoint 原生物件。SVG 應拆成 editable line、ellipse、
custom geometry 與 text；只有 HTML 原本就是 `<img>` 或 CSS `url(...)` 圖片時，才可保留為可移動、
可裁切的 PowerPoint picture object。無法一對一表達的 CSS 效果必須回報 approximation warning，
不得以整頁或大面積 raster 圖層掩蓋差異。

瀏覽器與 PowerPoint 即使使用同一字型，單行文字的 glyph metrics 仍可能略有差異。DOM 已實際排成
單行的文字框，匯出時必須保留 `wrap=false` 並預留少量字寬安全量，不得讓頁面標題多出尾字孤行。
CSS `border-radius:999px` 的寬形標籤屬於 capsule，必須映射為 PowerPoint rounded rectangle；
只有接近正圓或明確 percentage radius 的形狀才映射為 ellipse，避免橢圓內部文字區造成短標籤換行。

| HTML / DOM | PPTX |
|---|---|
| 純文字節點 | textbox |
| 背景色、邊框、圓角 | native shape |
| `<img>` / CSS background-image | image，保留 crop |
| `<table>` | native table |
| SVG line / circle / path / text | native line、ellipse、custom geometry、textbox |
| 複合 `.el` | group 語意；子層各自轉成物件 |
| filter、blend、複雜 mask | native approximation，並產生 warning；禁止整頁 raster fallback |
| animation、hover、互動控制 | 不輸出；必要時寫入 speaker notes |

## 幾何換算

專案 HTML 固定畫布為 1920×1080；PPTX 固定為 13.333×7.5 inch。

```text
x_in = x_px / 144
y_in = y_px / 144
w_in = w_px / 144
h_in = h_px / 144
font_pt = font_px * 0.5
```

正式 `@oai/artifact-tool` builder 的唯一 stage boundary 是 1920×1080 → 1280×720，所有
位置與尺寸固定乘以 `2/3`；不得在各 builder 另外 fit、round 或依 Placeholder 高度重算
title/subtitle。Variant 選定後，title/subtitle frame 與 role font 固定。

讀取 `getBoundingClientRect()` 前必須移除 player scale 的影響，使用 1920×1080 stage 座標。CSS transform、旋轉、crop 與 z-index 必須寫入中介 manifest，不得只取未變形的 layout box。

## 轉換保真分級

- `native`：文字、shape、圖片、表格皆為 PPTX 原生可編輯物件。
- `hybrid`：Image2 底圖 rasterize，主要內容與 Placeholder 原生可編輯；這是正式預設。
- `flat`：整頁 rasterize；只允許作 debug/對照，不得作正式預設輸出。

每頁必須在 QA ledger 記錄分級、fallback 物件與原因。

## QA

正式交付前必須：

1. 用 LibreOffice/PowerPoint renderer 將所有投影片輸出 PNG；
2. 逐頁檢查 clipping、overflow、字型替代、錯誤換行與 unintended overlap；
3. 執行 `slides_test.py`；
4. 依每個 Layout 的 `pptx.placeholder_schema` 檢查 master → layout → slide 關係，並在 OOXML
   `p:sp/p:ph` 逐一比對 Placeholder 的 exact type count、named id 與 index；`pic`／`tbl`
   等 PowerPoint type 必須正規化後仍與 `picture`／`table` schema 一致，不能只檢查「有 Placeholder」；
5. 對照 HTML screenshot，記錄位置與尺寸差異；
6. 確認文字、圖片、表格與基本圖形可在 PowerPoint 中個別選取。
7. 確認六張底圖完全無文字、無假內容結構，且高對比圖形未侵入 `blank_regions`。
8. 確認背景圖片只存在於 child layout，不存在於一般 slide 物件清單。

`freeform-composition` 額外必須驗證：

9. Composition Plan 的每個可見物件都有 materialized 對應，且沒有 source-only 或
   orphaned placeholder；
10. 逐頁的可見內容聯集位於 declared Content Area，四邊留白符合 constraint ledger，
    內容群組的實際中心落在目標 region 內；
11. 同一份 stage-space geometry 經 renderer 轉換後，PPTX layout JSON、OOXML 與渲染影像
    的座標／層級仍可追溯；source hash PASS 不得單獨取代這項檢查。

正式輸出不得只依 contact sheet 判定通過。
