# SVG Icon Generation Rules

> Status: active / canonical
>
> 本文件定義專案自有 SVG 語意圖示的按需生成、解析、驗收與跨 Renderer 交付規則。
> 預設做法是「每份 deck 先收集全部 icon intent，再一次生成同一家族」，不是維護持續膨脹的全域 icon library。

## 1. 目的與適用範圍

SVG icon 在本專案中是「承載內容語意的向量圖層」，不是裝飾素材，也不是把整套外部 icon library 搬進來的方式。

本規則涵蓋：

- 從既有 SVG 解析出 viewBox、幾何、圖層、樣式與來源 provenance。
- 以受限的幾何 recipe 生成新的、專案自有的語意圖示。
- 將同一份 icon manifest 投影到 HTML 與可編輯 PPTX。
- 保留 Image2、HTML、PPTX 各自的 renderer 邊界。

本規則不授權重新發布外部 icon library，也不把外部 icon 的整套 path 當成訓練資料來產生近似的競爭圖示庫。

### 1.1 內容 icon 與 Layout element 的邊界

- Icon 可以作為內容的一部分：例如功能、狀態、流程節點、圖例、媒體類型或驗收標記。
- Icon 必須由 content manifest／semantic slot 明確要求；renderer 不得為了填補留白或製造風格自動加入。
- Icon 的語意與 visual layer 可被替換、移除與編輯，但不得反過來決定 Layout、欄列數、slot geometry、safe area 或內容排序。
- Layout core 擁有版面幾何；Theme 擁有 icon 的色彩與外觀 token；icon recipe 只擁有自身的幾何與語意圖層。
- 沒有 icon 時，文字與其他內容仍應成立；不能把 icon 的存在設為 Layout 的必要條件，除非 Layout 明確宣告該 slot 是必填內容。

這個邊界是「內容語意 icon」與「裝飾性 icon／圖示包」的區分依據；跨 Renderer 的投影細節見第 6 節。

### 1.2 預設產製模式：每份 deck 一次生成整套

- Icon 生成發生在 deck build-time，不發生在 HTML 開啟、投影、編輯、儲存或匯出時。
- 先掃描當次 content manifest 的全部 `icon_intents`，去重後一次生成完整家族；不得一個 icon 呼叫一次，或讓同一語意在同一 deck 反覆重畫。
- 同一批次共用 family grammar、canonical grid、stroke token、corner language、optical size、negative-space 與 detail-density 目標。
- 輸出預設放在該 deck 的 `assets/icons/`，並以 deck-local manifest 保存 recipe、來源、hash、量測與 QA；不自動寫入全域 registry。
- 下一份 deck 可以依新的 Theme／Art Direction 重新生成；只有使用者明確要求「升級為共用素材」時，才進行 shared asset promotion。
- 正式 renderer 只消費已生成且有 manifest 的 SVG。若 build-time 尚無合格 icon，Layout 必須降級到無 icon 的文字配方，不能在 runtime 偷畫佔位圖形。

## 2. 外部 SVG 與專案自有 SVG 必須分流

每個 icon 必須先標記 `source.kind`：

| source.kind | 用途 | 是否可以生成 recipe |
| --- | --- | --- |
| `project-authored` | 當次 deck 或專案自己設計的 icon | 可以；deck-local recipe 是當次正式來源，升級共用素材需另行核准 |
| `external-licensed` | 單獨引用、經授權的外部 icon | 可以解析與正規化，但不可把整套外部圖示重製成競爭 library |
| `generated-from-recipe` | 由專案 recipe 確定性生成 | 可以；recipe 與 generator version 是正式來源 |

對 Remix Icon 的安全用法是：選取個別、具內容語意的 icon，保留 `icon_id`、官方 URL、版本／commit、授權版本與 SHA-256；不要把完整 Remix Icon collection 轉成我們自己的同款 icon set。Remix Icon 的目前授權允許把個別 icon 放入網站、簡報與商業產品，也允許修改外觀；但禁止把 icon 作為主要價值重新販售、製作競爭 icon library，或拿來當品牌識別。這是工程邊界，不是法律意見；正式商用仍應由專案負責人確認授權適用性。

## 3. 解析與正規化（deconstruct / normalize）

解析器可以拆解完整 SVG，但「拆解」的目的必須是可驗證的結構化，不是去除來源後做近似仿製。

### 3.1 必須保留

- `viewBox` 與原始寬高比例。
- 所有可見幾何：`path`、`line`、`polyline`、`polygon`、`rect`、`circle`、`ellipse`。
- `fill-rule`、`clip-rule`、`stroke-linecap`、`stroke-linejoin`、`stroke-miterlimit`。
- 圖層順序、可見性、幾何 transform 的原始值與正規化後值。
- 外部來源的 `source.url`、`source.icon_id`、`source.version`、`source.license`、`source.sha256`。

### 3.2 正規化動作

1. 將 SVG XML 解析成 AST，不以 regex 直接改寫 path。
2. 將 CSS class／presentation attribute 展開成明確的 layer style。
3. 將 transform flatten 到幾何座標，輸出固定的小數精度（建議 3 位）。
4. 將所有座標轉到 canonical viewBox；不得保留未解析的百分比或 `em` 幾何。
5. 計算 visible bounds、ink bounds、optical center 與 safe area。
6. 移除 script、事件 handler、外部 URL、`foreignObject`、嵌入 raster 與未鎖定的 font 依賴。
7. 保留原始檔 hash；正規化輸出另算 `normalized_sha256`，不可覆蓋原始來源。

### 3.3 相容性分級

| profile | 允許 | 目標 |
| --- | --- | --- |
| `portable` | solid fill／stroke、基本 shape、path、有限 `clipPath` | HTML + native PPTX |
| `html-rich` | gradient、mask、filter、blend、symbol reference | HTML；PPTX 必須 warning，不得假裝 native |
| `reject` | script、外部 href、foreignObject、嵌入 raster、未解析 CSS／font | 不得進正式 icon registry |

`portable` 是正式跨 Renderer 預設。`html-rich` 只能作 HTML audition 或明確標記的非 PPTX 內容；不得以整張 raster 圖掩蓋失敗。

### 3.4 可自動推回與不可自動推回

解析器可以可靠地推回：

- XML 節點樹、primitive 類型、path command、transform 與 layer 順序。
- visible bounds、ink bounds、幾何中心、候選對稱軸與重複幾何。
- fill／stroke token、線寬、cap／join、鏤空規則與輸出複雜度。

解析器不能只靠幾何可靠地推回：

- icon 的真正內容語意與閱讀名稱。
- 哪一條線是必要 detail、哪一條只是作者的裝飾。
- 原作者的 optical balance 意圖、品牌限制或商標使用脈絡。

因此 `role`、`icon_id`、`semantic_tags` 與 `optical_center` 需要由人指定或由 AI 產生候選後人工確認；不能把模型猜測當成正式 provenance。

## 4. 專案自有 icon 的生成 grammar

### 4.0 Family-first contract

同一份 deck 的 icon 必須先定義 family，再畫個別圖示。Family manifest 至少包含：

- `family_id`、`deck_id`、`generation_mode: per-deck-batch` 與規範版本。
- 全部 `icon_intents`、去重後的 icon id、語意名稱與內容來源。
- 共用 `viewBox`、safe area、stroke、linecap／linejoin、corner language 與 primitive budget。
- `target_optical_size`、每個 icon 的 `optical_center`、`ink_bounds` 與 density 分級。
- 16／24／48／96px contact sheet，以及整套 family 的 perceptual QA 結果。

同一套 icon 要一起生成、一起並排看、一起修正。只有單一 icon 通過安全區，不能代表 family 已完成。

### 4.1 Canonical geometry

- 預設 canvas 為 `24 × 24` unit，輸出使用 `viewBox="0 0 24 24"`；需要較細節的來源先在 `48 × 48` 編輯，再 canonicalize 到 24。
- safe area 預設為 `[2, 2, 22, 22]`；任何可見墨線不得越界。
- generator 必須記錄 `optical_center`，不可只用幾何 bounding-box 中心。
- icon 不得依賴 CSS transform 才能對齊；生成完成後所有幾何需已 materialize。
- 最小可辨識 feature 建議不小於 `2 × stroke_width`；小於此值必須合併、放大或刪除。

### 4.2 允許的 primitive

正式 recipe 只使用下列 primitive：

- `line`、`polyline`、`path`：輪廓、連接線、箭頭與曲線。
- `rect`、`roundRect`、`circle`、`ellipse`、`polygon`：容器、節點、徽章與基礎幾何。
- `cutout`：以 `fill-rule="evenodd"` 或相反色的明確 path 表示鏤空。

每個 icon 最多使用：

- 1 個 primary silhouette。
- 3 個 secondary details。
- 1 個 state marker（例如 check、plus、warning）。
- 2 種 stroke width；`detail` 不得大於 `primary`。
- 12 個可見 primitive；超過時必須標記 `complexity: review`。

這些是可讀性與 PPTX 可編輯性的預設上限，不是禁止複雜圖示的絕對限制；超限 icon 必須有人工 review 記錄。

### 4.2.1 Recipe operation grammar

生成器不直接拼接任意 SVG 字串，而是先執行可重現的幾何 operations，再輸出 normalized SVG。operations 的最小集合如下：

| operation | 作用 |
| --- | --- |
| `anchor` | 在 canonical grid 宣告命名座標，例如 `top`、`center`、`baseline` |
| `shape` | 由基本 primitive 建立輪廓或 detail |
| `mirror` | 依宣告的 symmetry axis 複製幾何；不得事後用 CSS transform |
| `offset` | 對 path 做固定 unit 的內縮／外擴；結果必須 materialize |
| `round` | 對指定 corner 或 stroke join 套用固定半徑 |
| `cutout` | 建立 `evenodd` 鏤空或明確的負形 |
| `mark` | 加入唯一 state marker；只允許一個 primary state |
| `emit` | 依 layer order、style token 與 precision 輸出 SVG |

範例（語意示意，不是任何外部 icon 的 path 複製）：

```yaml
recipe:
  family: shield
  grid: 24
  symmetry: vertical
  anchors:
    top: [12, 3]
    shoulder_left: [5, 7]
    shoulder_right: [19, 7]
    base: [12, 21]
  operations:
    - op: shape
      id: body
      primitive: path
      role: silhouette
      points: [top, shoulder_left, base, shoulder_right]
    - op: mirror
      source: body
      axis: x=12
    - op: mark
      id: state
      role: state-marker
      kind: check
    - op: emit
      precision: 3
```

`points`、`kind` 等高階參數必須由 generator 實作轉成 path；manifest 不應混入 renderer-specific CSS 或簡報 Theme 色碼。

### 4.3 Style tokens

```yaml
style:
  mode: line | fill | duotone
  primary_color: currentColor
  secondary_color: currentColor
  stroke:
    primary: 2
    detail: 1.5
    linecap: round
    linejoin: round
  fill_rule: nonzero | evenodd
  opacity:
    primary: 1
    secondary: 0.72
```

- 正式 icon 預設使用 `currentColor`；Theme 才負責實際顏色。
- 不得在 recipe 寫死簡報 Theme 的 hex 色碼。
- `line` icon 使用 `fill="none"`；`fill` icon 的實心面必須仍有清楚的 silhouette。
- 同一 icon 不得同時混用尖角與圓角語法，除非 recipe 明確宣告語意差異。
- 不使用 filter、shadow、blur 製造基本辨識度；這些屬於外部 presentation layer。

### 4.4 Semantic layer contract

每個 primitive 必須有語意角色，不得只有無意義的 path 編號：

```yaml
layers:
  - id: body
    role: silhouette
    primitive: path
  - id: detail-1
    role: detail
    primitive: line
  - id: state
    role: state-marker
    primitive: path
```

允許的 role：`silhouette`、`detail`、`connector`、`state-marker`、`cutout`、`badge`。

HTML 投影時，icon 外層必須位於真正可選取的 semantic module 內，並標記：

```html
<div class="el icon-module"
     data-edit-structure="module"
     data-edit-composite="icon-module"
     data-icon-id="content.security">
  <div data-edit-layer="background"></div>
  <svg data-edit-layer="visual"
       data-icon-role="semantic"
       viewBox="0 0 24 24"
       aria-hidden="true">…</svg>
</div>
```

`svg` 是 visual layer；不可把圖示塞進 CSS pseudo-element，否則 editor 與 hit-test 無法獨立選取。

## 5. Deck-local icon family manifest

預設不建立全域 registry。每份 deck 保存一份 family manifest；renderer 以 `registry` 只做「本 deck 的 tag／intent → icon id」解析：

```yaml
schema_version: deck-icon-family/v1
family_id: alzheimer-care-line-v1
deck_id: alzheimer-care-variants
generation_mode: per-deck-batch
source:
  kind: project-authored
  license: project-owned
canvas:
  viewBox: [0, 0, 24, 24]
  safeArea: [2, 2, 22, 22]
style:
  mode: line
  tokenSet: svg-icon-default-v1
registry:
  MEMORY: memory
  SAFETY: safety
icons:
  - id: memory
    file: assets/icons/memory.svg
    semantic_tags: [MEMORY]
    optical_center: [12, 12]
    optical_size: [18, 18]
    recipe: {family: memory-loop, symmetry: vertical, complexity: simple}
    renderers: {html: inline-svg, pptx: native-path-or-shape, image2: semantic-prompt-only}
    qa: {source_sha256: null, normalized_sha256: null}
```

這個 `registry` 只屬於當次 deck，不是長期 icon library。外部 icon 的 `recipe` 預設為 `null`，並以 `source.icon_id` 與受控的 normalized SVG 作為來源；專案自有 icon 則保存可再生成的 recipe。

## 6. 三個 Renderer 的投影規則

### HTML

- 正式輸出使用 inline SVG，禁止 CDN、未鎖版 webfont 或外部 `<use>` 依賴。
- icon 僅能進入已宣告的內容 slot；`pattern-only` 的 `no-image` Layout 可使用語意 icon，但不可自動撒入裝飾 icon。
- icon 的顏色、尺寸與旋轉由 Theme／module token 控制；Layout 只擁有 slot geometry，不能由 icon bounds 反向選版或改寫版面骨架。
- icon 必須作為 semantic module 的可選取 `visual`／`icon` layer；不得只放在 CSS pseudo-element、背景或不可命中的裝飾容器中。
- 任何 icon 替換、顏色變更、移動、縮放與 undo／redo 都必須落在 editor snapshot。

### PPTX

- `portable` icon 優先轉成 native shape、line 或 freeform path，並保留 group／layer 語意。
- `html-rich` icon 必須在 manifest 寫入 approximation warning；不能以 PNG 冒充可編輯 icon。
- 必須檢查 PPTX package/XML、native object 數量、group 關係與 PowerPoint 原生渲染。

### Image2

- Image2 使用 `icon.intent`、`family`、`style` 等語意提示，不把 HTML SVG 或 assembled YAML 當成共用 runtime payload。
- 正式 Image2 preview 仍由完整七段式 assembled YAML 驅動；SVG recipe 只能作語意來源或後續可編輯 renderer 的參考。

## 7. 驗收 Gate

一套 deck-local icon family 只有在下列條件全部通過後，才能被正式 renderer 消費：

1. XML／AST parse 成功，沒有 script、外部資源或未鎖定字型。
2. viewBox、safe area、visible bounds、optical center 可計算。
3. `portable` icon 沒有未處理 filter／mask／blend；若是 `html-rich`，warning 已記錄。
4. 在 16、24、48、96 px 顯示時仍可辨識，沒有細線消失、鏤空堵塞或邊界裁切。
5. HTML inline render、Theme recolor、editor visual-layer selection 與 export 通過。
6. PPTX native conversion、XML 檢查與 PowerPoint 原生渲染通過；否則標為 `partial`。
7. manifest 有來源、授權、版本、hash 與 generator version；輸出可重現。
8. 每個 icon 都能回答「它承載哪一個內容語意」，不能只有裝飾理由。
9. 全 family 並排時，optical size、center、stroke density、detail count 與 negative space 沒有明顯離群值。
10. Contact sheet 與 artifact manifest 指向同一批 SVG hash；重新開啟或匯出不會重新生成。

## 8. 正式呼叫與保存流程

```text
Content Plan / page composition
→ 收集並去重 icon_intents
→ 讀取本規範與當次 Art Direction
→ 一次生成完整 SVG family
→ scripts/validate_svg_icon_family.cjs
→ 16/24/48/96px contact sheet + perceptual QA
→ deck-local manifest 鎖定 hash
→ HTML / PPTX adapter 消費已鎖定輸出
```

- 生成規範本身是 canonical source；每次生成的 SVG、contact sheet 與 family manifest 是該 deck 的 artifact。
- HTML-only 任務可以在 HTML inline／editor／export Gate 通過後交付，但 PPTX native conversion 必須標為未驗證或 partial。
- 不得因某次生成結果好看，就自動把 SVG 回流為全域資產；shared promotion 是另一個需要使用者明確授權的工作。
