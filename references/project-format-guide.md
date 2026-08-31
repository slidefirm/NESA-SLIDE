# Assembled Prompt YAML — 格式定義

這份文件定義 `generate-image-slide` skill 的唯一正確輸出格式。
**每次執行 skill 必須先讀這份文件，不可跳過。**

這份文件只提供「結構（形狀）」。它刻意不放任何填好內容的完整範例——
填好的檔會連內容與風格一起被模仿，那是污染源。版面槽與裝飾 zone
一律由該 layout 的 `prompt_system/layouts/<id>.yaml` 當下宣告為準；
`content` 欄位則由 AI 依本次素材、版型與溝通任務即時決定，不留存為
可重複套用的靜態內容規格。所有值每頁現寫。

---

## Art Direction 如何進入七段式 YAML

多頁 deck 若提供 `prompt_system/art_direction/` 規格，先執行：

```powershell
python scripts\art_direction.py <art-direction.yaml>
```

Art Direction 是 deck-level 輸入，不增加第八個 top-level section。組裝單頁時依下表
合併到原本七段：

| Art Direction | 七段式落點 |
| --- | --- |
| `visual_genre`、scene role、visual intensity | `page_type_and_mood` |
| `typography_role`、`color_behavior`、`asset_family` | `visual_base_2a` |
| `signature_move`、`edge_behavior` | `corner_decoration_2b`，但只能使用 Layout 宣告的 zone |
| `spatial_rule`、當頁 scene role | `layout_description`，並據此選 Layout |
| Story 內容 | `content` |
| Layout safe area 與 renderer 底線 | `safe_zone_constraints`，Art Direction 不得覆蓋 |
| `narrative_metaphor`、`forbidden_cliches` | `closing_design_intent` |

合併優先序：

1. Layout 的 slot、safe area、alignment 與 visual balance。
2. Art Direction 的跨頁方向與當頁 scene role。
3. Theme 的色彩、字體、材質與裝飾語彙。

若 Art Direction 要求的招牌手法和 Layout 安全區或閱讀順序衝突，必須換 Layout
或退回方向修正；不得用越界、縮小文字或新增 fallback 硬塞。

---

## 七段式 YAML 結構（區段固定，槽動態，值現寫）

七個區段與其文法固定不變。`corner_decoration_2b` 內的 zone 依 layout 展開；
`content` 內的欄位依本次 transient content contract 展開。下方用 `<...>`
標示「依當次組裝決策展開、值現寫」之處。

```yaml
page_type_and_mood:
  prompt: >
    （一句話描述頁面類型 + 情緒，每頁現寫）

visual_base_2a:
  background:
    color: "#XXXXXX"
    texture: >
      （背景材質與氛圍，自然語言段落）
    bleed: "full"

  typography:
    heading:
      color: "#XXXXXX"
      family: "字體族名稱"
      weight: "ultra-bold / bold / medium"
      size_pt: "XX-XX"
    body:
      color:
        - "#XXXXXX"
        - "描述性色名"
      family: "字體族名稱"
      weight: "medium / regular"
      size_pt: "XX-XX"
      line_spacing: "generous / normal / tight"

  color_system:
    primary:
      color: "#XXXXXX"
      usage:
        - "用途"
    secondary:
      color: "#XXXXXX"
      usage:
        - "用途"
    accent:
      color: "#XXXXXX"
      usage:
        - "用途（小面積強調：線條、編號、圖示描邊、重點標記；不得作大面積填色）"
    support:
      - color: "#XXXXXX"
        usage:
          - "用途"

  illustration_style:
    type: "扁平插畫"   # 選項：扁平插畫 / 3D風格 / 線條圖示 / 抽象藝術 / 無
    note: >
      （說明本頁插圖的使用方式與風格指引，無插圖時填「無」即可）

corner_decoration_2b:
  # 從該 layout 的 decoration 區展開。
  # zone 的名稱與數量以 layout 宣告為準（可能是四角、底帶、側條，
  # 或 design_zone 的具名子區），不是固定四角。
  # design_zone 預設「開放可設計」，禁止預設留白 / 無額外圖形。
  rule: >
    （整體裝飾約束：型態 / opacity 範圍 / 色彩限制 / 不得侵入 text safe zone，
     取自 layout 的 decoration.free_zone.rule，每頁現寫）
  <zone_from_layout>:
    decoration: >
      （此 zone 的裝飾描述，每頁現寫）

layout_description:
  structure: "（版型結構一句話，取自 layout）"
  title_region:
    horizontal_range: "XX%-XX%"
    vertical_range: "XX%-XX%"
    description: "（標題區說明）"
  body_region:
    horizontal_range: "XX%-XX%"
    vertical_range: "XX%-XX%"
    description: "（正文區說明）"
  image_column: "none / left / right"
  alignment_rule: "（對齊規則，取自 layout 的 alignment_rules）"

content:
  # 一個本次 content contract 欄位一個欄位，集合由 AI 依素材、layout 與溝通任務即時決定。
  # 例：title / subtitle / modules / metrics / phases / closing_note… 不留存為靜態檔。
  <field_from_current_content_contract>: "（實際值，每頁現寫）"

safe_zone_constraints:
  hard_constraint: >
    All content — titles, diagrams, labels, icons — must stay within
    10%–90% of both horizontal and vertical range.
  edge_rule: "No element touches or crosses the slide edge."
  exception: >
    （例外，例如底紋可滿版、滿版圖可出血，在此說明）

closing_design_intent:
  prompt: >
    （收尾設計意圖，說明整體畫面的視覺原則與最終印象，每頁現寫）
```

---

## 關鍵規則（文法層，固定）

### 必須用結構化子欄位的區段
- `visual_base_2a.background` — 不可用單一 `>` 字串
- `visual_base_2a.typography` — heading / body 各自展開
- `visual_base_2a.color_system` — primary / secondary / accent / support 各自展開
- `visual_base_2a.illustration_style` — 必須有 `type`（四選一或「無」）與 `note`；無插圖時 type 填「無」，note 可留一句說明
- `corner_decoration_2b` — 必須用具名 zone 子鍵，每個含 `decoration: >` 塊；
  zone 取自 layout 的 decoration，不可寫成 `vocabulary:` 列表（那是 style_case 格式）
- `layout_description` — 必須有 `structure` + region 子欄位，不可用單一 `>` 字串
- `safe_zone_constraints` — 必須有 `hard_constraint` / `edge_rule` / `exception` 子鍵

### 必須用 `prompt: >` 包裝的區段
- `page_type_and_mood.prompt`
- `closing_design_intent.prompt`

---

## 素材層 theme → 本格式的對應規則（組裝時必讀）

`visual_base_2a` 的值來自本次選定 theme 檔（`prompt_system/themes/<id>.yaml`）
的 `visual_base` 段。兩層結構刻意不同——素材層語意化、組合層結構化——
翻譯不得即興，逐欄規則如下：

| theme（素材層） | visual_base_2a（本格式） | 規則 |
|---|---|---|
| `background_color` | `background.color` | 直接帶入 |
| `background_style` | `background.texture` | 擴寫成自然語言段落 |
| （由 layout 決定，非 theme） | `background.bleed` | fullbleed 類 layout（如 `hero-fullbleed`、封面滿版疊字）填 `"full"`；一般內容頁背景為容器內鋪色，填 `"none"` |
| `color_palette.primary.hex / use` | `color_system.primary.color / usage` | hex→color、use→usage，值不得改 |
| `color_palette.secondary` | `color_system.secondary` | 同上 |
| `color_palette.accent` | `color_system.accent` | 同上；accent 只作小面積強調，不得升級為大面積填色 |
| `color_palette.support[]` | `color_system.support[]` | 同上，列表逐項 |
| `typography.*.family / weight` | `typography.*.family / weight` | 直接帶入，不得換家族或粗細（身分欄位） |
| `typography.*.size_hint` | `typography.*.size_pt` | 依 size_hint 傾向 + 角色字級範圍 + 本頁內容量「現算數字」；每頁可不同 |
| `illustration_style.default / note` | `illustration_style.type / note` | 預設帶入 default；單頁可依內容覆寫（如無圖素材改「無」），覆寫理由寫進 note |
| `mood` | `page_type_and_mood.prompt` | 作為情緒詞彙來源之一，與本頁頁面類型合寫 |
| `decoration_vocabulary` | `corner_decoration_2b` | 刻意不逐欄對應：AI 依 layout 宣告的 zone 自由選用與分配詞彙（這是設計空間，不是缺陷） |

釘死與留活的邊界：

- 釘死（不得偏離 theme）：色票 hex、色彩角色、字體家族、粗細、illustration 預設風格。
- 留活（每頁現算）：具體字級數字、裝飾詞彙的 zone 分配、`content` 全部欄位。

相容備註：若遇到 typography 仍是單行散文的舊 theme 檔（尚未結構化），
先從散文解析出家族與粗細再帶入，不可自行發明；解析不出來時停下回報。

---

## decoration：prescribe 與 free_zone 都來自 layout

裝飾的兩種寫法都定義在該 layout 的 `decoration` 區，不是由輸出目標二選一：

- `decoration.design_zone` — 可設計範圍 = 整個版面扣掉 protected（受保護的實際文字框）。
  protected 只圈文字框，文字側的邊角與縫隙仍屬可設計區。預設開放，不預設留白。
- `decoration.prescribe` — 精準細節（細線、點陣、分隔線、轉角記號、色塊）。
  PPT / HTML 需要它；圖片生成也需要它（細節不靠 free_zone 自己長出來）。
- `decoration.free_zone` — 大色塊 / 大形狀 / 背景的自由構圖約束（型態 + opacity + 色彩限制）。

組裝 prompt 的 `corner_decoration_2b` 由這三者渲染而成：prescribe 的細節 + free_zone
的大結構疊加，落在 design_zone 內。兩者是疊加，不是取代。

free_zone 的六種型態（在 `rule` 中指定）：

| 型態 | 說明 | 適用場景 |
|------|------|----------|
| 環繞 | 四邊連成一圈，沿全周延伸 | 封面、強框景感 |
| 四角 | 僅四角，邊緣不延伸 | 目錄、內容頁，不搶主體 |
| 左右兩側 | 左右各一條垂直裝飾帶 | 左文右圖類 |
| 上下兩側 | 頂部與底部各一條水平帶 | 章節過場、標題頁 |
| 左下右上 | 對角線配置 | 非對稱設計感 |
| 左上右下 | 對角線配置 | 非對稱設計感 |

opacity：白底 40–60%，深色底 60–80%。

---

## 內容設計規則（產 YAML 前必檢查）

這幾條是使用者在實作中確立的硬規則，與格式同等重要。

### 1. 主標與副標底色擇一（已確立）

主標與副標只能擇一使用底色（色塊或膠囊），不可兩個同時加底色。

- 色塊與膠囊都是「讓文字在白底上站出來」的手法，兩個都用等於互相抵銷，層次反而消失。
- 主標夠大（60pt+ 超粗）→ 大字本身就是視覺重量，不需底色；副標可用膠囊補強。
- 主標用底色色塊 → 副標改細字，不加膠囊。
- 反映在 `content.title` 與 `content.subtitle` 的 `style_hint`：兩者不可同時出現
  「capsule label」或「background block」。

### 2. TOC 版型章節標題與小標同字級（觀察中）

目錄（TOC）版型內，每一列的章節標題（heading）與副標（subheading）必須同字級。

- TOC 列應整排等重，不是強調某一行。區分兩者靠粗細（weight）或顏色，不靠字級。
- `typography.heading.size_pt` 與 `typography.body.size_pt` 在 TOC 版型設為相同範圍。
- 目前確認適用 `toc-3-vertical`，其他 TOC 版型尚在觀察。

### 3. 封面 logo 放置：角落浮水印為預設（已確立）

封面的 `org_logo` 有兩個位置，由「標題是否提及該單位」決定：

- 預設 → 角落浮水印：小尺寸、低不透明度，落在不干擾主文與圖片的角落
  （layout 的 `org-logo.watermark_region`）。不進主 metadata 堆疊。
- 例外 → 主位置：只有當標題文字本身提及該單位（單位名出現在 `content.title`）時，
  才把 logo 放到 `org-logo.main_region`，正常尺寸、與 org 並列。
- 反映在輸出：預設時 logo 以「角落浮水印」描述出現；標題提及單位時才在主 metadata 區描述 logo。
- 判斷依據是 title 的文字內容，不是 org 欄位有沒有填。org 幾乎都會填，但那不觸發主位置。

### 4. 視覺權重必須對應資訊階層（已確立）

視覺權重只能來自資訊階層，不可只是為了排版好看。

- 同級資訊不得使用明顯不同的視覺權重。
- 明顯不同的視覺權重必須代表 `primary` / `supporting` 的語意階層。
- 若 layout 的 `visual_balance.method` 是 `equal-modules`，所有 modules 必須等寬、等高、等字級、等色彩權重。
- 若 layout 使用大卡 + 小卡、上方總綱 + 下方拆解、左側主張 + 右側證據，則大卡 slot 必須明確標示為 `role: primary` 或 `weight: primary`，小卡必須標示為 `role: supporting` 或 `weight: supporting`。
- 不得把同級項目放進不等大小卡片，只因為畫面看起來比較有變化。
- 產 YAML 與生圖前必須先判斷：這些模組是「平行關係」還是「主從關係」？

判斷規則：

- 平行關係：使用等寬、等高、同一列或同一網格、同級字級與色彩權重。
- 主從關係：才允許使用大卡 + 小卡、上方總綱 + 下方拆解、左側主張 + 右側證據。

對 `cards-1-plus-*` 特別注意：

- `visual_balance.method: equal-modules` 表示 title 是 framing，modules 彼此平行，不可把第一張 module 放大成主張卡。
- 若要做「一個主張 + N 個支撐」，應使用或新增明確命名的 `primary-support` 類 layout，而不是套用 equal-modules 的 `cards-1-plus-*`。

### 5. 標題對齊由結構與語意決定（已確立）

標題不得使用固定比例或隨機方式分配靠左與置中。判斷優先序如下：

1. Layout 的 `alignment_rules` 有明確指定時，必須服從 Layout，不得由通用 Prompt 覆蓋。
2. Layout 未指定時，才依內容角色、閱讀動線與構圖對稱性判斷。
3. Layout 未指定時，依標題的預估渲染寬度選擇預設處理；字數只作為次要參考。

標題長度分級：

- 短標題：預估寬度小於 safe area 的 35%，預設靠左。不得為了填滿寬度而過度放大。
- 中標題：預估寬度介於 safe area 的 35%-72%，若統攝整頁則預設水平置中。
- 長標題：預估寬度超過 safe area 的 72%，先做語意拆分，不直接縮字或任意斷行。

長標題拆分規則：

- 主標保留核心主張、結論或關鍵名詞。
- 副標承接背景、範圍、方法、對象或補充說明。
- 不得只按字數從中間切開；拆分後兩者必須各自語意完整。
- 若主標置中，短副標應與主標共用中心軸。

例外與覆寫：

- 封面、章節頁、中央宣告與 Layout 明確指定置中的版型，不受短標題靠左預設限制。
- 標題只統攝單一欄位時，應對齊該欄位閱讀軸，而不是整頁置中。
- 等寬卡片不會自動觸發置中；仍需判斷標題統攝範圍與整體視覺中心。

### 6. 標題區塊與內容區塊必須分離（已確立）

標題區塊包含主標、副標、標題底線、章節碼與附著於標題的裝飾；內容區塊包含圖表、卡片、圖片、標籤、連接線及其陰影。兩者必須是可辨識的獨立垂直區域。

- `title_region` 與主要 `body_region` 不得重疊，也不得首尾相接。
- 一般資訊頁必須保留至少投影片高度 5% 的過渡留白帶。
- 計算方式：`content_top - title_bottom >= 5%`。
- 標題底線與標題裝飾必須完整留在 `title_region`，不可伸入過渡留白帶。
- 內容圖表、卡片、連接線、標籤與陰影不可進入標題區或過渡留白帶。
- 空間不足時，優先降低內容密度、縮短文字或縮小內容群組；不得向上擠壓標題。
- 過渡留白帶是「前景淨空」，不是視覺真空；低對比的 2A 背景紋理、漸層與連續色場可以穿過。
- 不得為了區隔標題與內容而刪除整張投影片的 2A／2B。2B 應留在 Layout 宣告的邊角區，但高對比裝飾不得進入過渡留白帶。
- 封面與滿版疊字頁可依 Layout 明確例外，但例外必須由 Layout 宣告，不可由生圖模型自行判斷。

### 7. 純色背景不得單獨存在，必須搭配可視裝飾或漸層/材質（已確立）

`visual_base_2a.background` 不可以是一片沒有任何深淺變化的平塗色，單獨佔滿版面。純色本身不是問題，「純色卻沒有任何搭配」才是問題——沒有裝飾、沒有深淺，讀者的眼睛就找不到留白帶在哪裡，即使數字上的 safe zone 是對的，畫面看起來也會像貼著邊緣。

判斷順序：

1. 這頁背景是純色嗎？→ 是，下一步；否（本身已是漸層/材質/照片），跳過本條。
2. 版面是否有足夠空間放大型圖片或裝飾（例如封面、章節頁、留白充裕的 layout）？
   - 有 → 純色底必須搭配可視的圖片、幾何裝飾或色塊構圖，不能只交一片平塗色。
   - 沒有（例如資訊密集的數據頁、卡片頁，沒有大面積可設計區）→ 改用漸層（gradient）或材質紋理（grain、dot-grid、極淡格線等）取代純色平塗，讓背景本身帶有可視的深淺變化。
3. 不論哪一種，`corner_decoration_2b` 的 opacity 不得低到「實質等於無」（例如 5–8% 幾乎不可見）。至少要達到可視最低限：白底 15–20% 起、深色底更高。低於這個下限等同於沒寫裝飾。

反映在輸出：`visual_base_2a.background.texture` 必須具體描述深淺變化的來源（漸層方向、材質類型或搭配的裝飾），不能只寫顏色本身；`corner_decoration_2b` 的每個 zone 的 opacity 都要落在可視範圍內。

---

## style_case 格式 vs 本格式

| 項目 | style_case (歸檔用) | assembled prompt YAML (本格式) |
|------|---------------------|-------------------------------|
| 用途 | 歸檔使用者參考圖 | 產生圖片或 slide 的組裝 prompt |
| corner_decoration_2b | `vocabulary:` 列表 | 具名 zone 子鍵（取自 layout decoration） |
| layout_description | `composition_notes:` | `structure + region 子欄位` |
| page_type_and_mood | 無此欄位 | 必填，含 `prompt:` 子鍵 |
| closing_design_intent | `principle:` 在 composition_notes 內 | 獨立欄位，含 `prompt:` 子鍵 |
