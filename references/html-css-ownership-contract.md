# HTML CSS Ownership Contract

本契約只處理「CSS 誰可以改什麼」以及「如何證明 CSS 不會讓版面跑掉」。
文字容量與 36px 下限仍由既有 typography gate 管理，不在本契約重複定義。

## 一句話原則

**Layout 決定盒子在哪裡、佔多大；Theme／Preset 只決定既有盒子看起來像什麼。**

如果一段 CSS 同時負責位置與外觀，或需要靠另一段晚載入的 `!important` 把它拉回去，
就表示 ownership 已經失效，renderer 必須停止產製。

## Preset 的資料邊界

可重用 Preset 的 canonical source 是
`prompt_system/renderers/html/preset-themes.yaml`，其中只能保存：

- 色票與對比 token
- 字體家族、字重與文字效果
- 背景 Pattern、材質、陰影、透明度與表面語彙
- component recipe 與不綁 Layout 的 semantic visual role

下列資料不得出現在 reusable Preset 定義，也不得被 new-deck runtime 間接載入：

- `source_style_case`、舊 HTML／CSS／截圖或舊 artifact
- `example_story`、`content`、固定文案或文字替換表
- `example_layouts`、`layouts`、`layout_id` 或 forced-layout sequence
- 一整段可任意覆寫 DOM 的 CSS

Theme Lab／Style Case 可以留作 Gallery 或歷史證據，但只屬於 demo source。
只有使用者明確要求 `preset-demo` 時，才可走隔離的 demo route；demo route 的內容、Layout
與 CSS 不得被標記為 reusable，也不得進入 new-deck manifest。

## CSS ownership

| Owner | 可以決定 | 不可以決定 |
|---|---|---|
| `renderer-base`／Layout adapter | slot、position、inset、寬高、Grid／Flex、gap、padding、margin、對齊、transform、overflow、writing-mode、字級與行高、materialized geometry | Preset 身分、故事內容 |
| `theme-appearance` | core Theme 的色彩、Pattern、材質、背景、表面 paint、字體家族／字重、陰影與文字效果 | Layout selector、頁碼 selector、幾何屬性、`!important` |
| `preset-appearance` | Preset 自己的外觀 token 與 semantic surface paint | 內容、Layout、固定座標、Layout 變體、DOM 顯示／隱藏、`!important` |
| `editor-chrome` | 編輯器與 player UI | 投影片內容幾何 |

可見文字預設一律使用 `horizontal-tb`。`renderer-base`／Layout adapter 只有在 Layout Core
明確宣告對應文字 slot 的方向語意時，才可使用其他 writing mode 或把文字旋轉 90°；
Theme、Preset 與 design dialect 不得自行引入直向文字。目前 release 的 Layout Core
沒有任何這類授權，因此產製與打包 Gate 應以「0 個直向文字」驗收。

Theme／Preset 可以建議 `composition` 或 `surface` 語彙，但 renderer 必須在選 Layout 時先把建議
解析成相容的 Layout／composition variant。Layout 一旦 materialize，Theme／Preset 不得再靠 CSS
改變 composition。

## Appearance CSS 的硬性 Gate

`theme-appearance` 與 `preset-appearance` 必須在寫入 artifact 前通過
`scripts/html_css_ownership.py`。以下任一項都屬 blocking failure：

- selector 使用 `data-layout-id`、`data-composition-variant`、`data-recipe`、
  `data-production-family`、頁碼、slide id 或 `:nth-*`
- selector 直接控制 `.content`、`.el`、layout-only frame 或 universal `*`
- 宣告 position／inset／top／right／bottom／left、寬高、display、Grid／Flex、gap、
  padding、margin、align／justify、transform／translate／rotate／scale、overflow、
  writing-mode、text-align、font-size、line-height、white-space 等版面屬性
- 使用 `!important`、插入 pseudo content，或顯示／隱藏 Layout 物件
- 以自訂 CSS variable 間接傳入座標、尺寸、gap 或其他幾何值
- 將 border thickness 寫在 semantic module 根；若要改邊框，只能寫在已存在、
  `box-sizing:border-box` 的 background layer

Validator 必須拒絕不合規輸入，不能靜默刪掉宣告後繼續生成，否則 artifact 與 source 會失去一致性。

## Cascade 與 materialize 順序

固定順序如下：

1. 載入正式字體與完整內容。
2. `renderer-base` 依 Layout core、content density 與已解析的 composition variant 建立幾何。
3. `theme-appearance` 與 `preset-appearance` 套用 paint／type token；兩者都沒有幾何權限。
4. 等待 `document.fonts.ready`，再 materialize `.content` 與 `.el` 的數值幾何。
5. materialize 後不得再附加修正位置的 Theme／Preset CSS；semantic contract 只驗證，不代替修正。
6. 編輯器只讀取 materialized geometry；使用者明確「重新套版」時才重新跑 Layout。

每個生成的 `<style>` 都要有 `data-css-owner`。new-deck 不接受未標 ownership 的 style block，
也不接受 `legacy-demo-override`。

## Rule-level acceptance

要宣稱「CSS ownership 已通過」，必須同時有以下證據：

1. Preset catalog 驗證：reusable Preset 無舊內容、舊 Layout、Style Case source 或任意 CSS。
2. Source CSS 驗證：所有 Theme／Preset appearance CSS 通過靜態 ownership validator。
3. Artifact 驗證：new-deck HTML 每個 style block 都有合法 owner，manifest 無 demo reference。
4. Browser geometry invariant：在 Layout ready 後記錄每個 `.content`／`.el` 的 computed geometry，
   暫時停用 appearance styles，再比較位置與尺寸；任何超過 0.5px 的差異都 fail。
5. Browser collision／overflow QA 另行通過；靜態 ownership pass 不能代替視覺與互動驗收。

修改本契約、reusable Preset catalog、appearance CSS generator 或 materialize 流程時，不能只測目前成品：
必須把同一組 regression Layout 逐一套用到**全部 reusable Preset**，每個組合都通過靜態 gate 與
Browser geometry invariant。一般只改單份內容時，才可只驗該份 artifact。

這個 Gate 的目的不是保證 CSS 永遠不會寫錯，而是保證不合規 CSS 無法被當成正式成品交付。
