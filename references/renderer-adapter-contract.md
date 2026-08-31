# Renderer Adapter Contract

跨 Renderer 的規則優先順序與已驗收生產底線見
`references/presentation-production-contract.md`；本文件只定義 core 到 adapter 的投影關係。

本專案的共用層是 `prompt_system/themes/` 與 `prompt_system/layouts/`。Image2、HTML、
PPTX 不必共用同一份 runtime payload，但必須由同一份 core YAML 自動投影。

```text
Theme Core + Layout Core + Content
                 |
       +---------+---------+
       |         |         |
    Image2      HTML          PPTX
    adapter     adapter       adapter
       |         |             |
 assembled     render     background-set +
 YAML          manifest   master/layout manifest
```

## Source of truth

- `prompt_system/themes/*.yaml`：色彩角色、字型語意、mood、illustration 與裝飾語彙。
- `prompt_system/layouts/*.yaml`：`media_requirement`、slot、safe area、alignment、visual balance 與裝飾區域。
- `prompt_system/renderers/`：由 core 自動生成的 renderer adapter，不得手動複製 core
  色碼或座標。

Theme Core 不得保存 `html_spec`、`pptx_spec`、`layout_overrides` 或其他 renderer／Layout
幾何。Theme 只提供跨 Renderer 的色彩、字體語意、材質與裝飾語彙；精確位置、尺寸、
字級與行高必須由 Layout、逐頁 Composition 與 renderer-base materialize。

每個正式 Layout 必須直接提供 `media_requirement`、`slots`、`safe_area`、`alignment_rules` 與
`visual_balance`。這五項是共用 Core 契約，不得由 Renderer adapter 以通用 fallback
補值；缺少任何一項時，adapter generation 必須直接失敗。

## Adapter 規則

1. Adapter 以 `source_ref`、`geometry_ref`、`token_ref` 指向 core 欄位。
2. HTML 與 PPTX 的精調值只能作 renderer override，不得改寫 core 語意。
3. Image2 adapter 產生七段式 assembled YAML；assembled YAML 不是 HTML/PPTX 的通用 payload。
4. HTML adapter 產生 CSS token、component 與 1920x1080 slot manifest。
5. PPTX adapter 產生 theme master、六角色 Image2 background-set、layout 與 placeholder manifest。
6. 每個 adapter 必須記錄 core path 與 SHA-256，供 stale 檢查。
7. HTML adapter 必須區分 Layout slot、鬆散 edit object 與 semantic module：slot 或置中 frame
   可標記 `data-edit-layout-only="true"`，但不得是 `.el`，也不得成為可選群組。標題、副標、正文、
   註解與來源等鬆散內容各自是同層 `.el`；只有本來就必須共同移動、縮放與刪除的資訊單位，
   才使用單一 `.el[data-edit-structure="module"][data-edit-composite]` 根節點。module 根節點是唯一
   editable root，內層 `data-edit-layer` 不得再標成 `.el`；不得為定位產生 title、content 或整頁群組。
8. 固定高度文字方塊的 HTML adapter 預設垂直置中；水平對齊仍由 Layout Core 的 alignment rules 決定。
9. Core／Layout 標成 `anchored-edge` 的裝飾 visual，HTML adapter 必須以
   `data-edit-anchor="bottom"` 保留父模組下緣關係；PPTX adapter 必須把同一關係寫成父模組內
   的 native shape 幾何。這個 metadata 是共用語意，不得由 Theme／Preset appearance CSS
   重新宣告位置。
10. Layout adapter 必須引用 Core 的 `media_requirement`。`no-image` 可供所有素材策略使用；
    `with-image` 只有在本次簡報的素材策略會提供或產生真實圖片時才可被選用。HTML 的正式
    策略名稱是 `pattern-only` 與 `image-planned`，不得只因 renderer 是 HTML 就一律排除圖片 Layout。

## 產生與驗證

```powershell
python scripts\generate_renderer_adapters.py
python scripts\generate_renderer_adapters.py --check
```

`--check` 會在 adapter 缺少、來源 hash 過期或內容不是 generator 的確定性輸出時失敗。

## 覆蓋要求

每個正式 theme 與 layout 都必須各有三份 adapter：

- `prompt_system/renderers/image2/themes|layouts/`
- `prompt_system/renderers/html/themes|layouts/`
- `prompt_system/renderers/pptx/themes|layouts/`

Adapter 存在代表 renderer 已具備 baseline mapping；人工視覺 QA 通過後，才代表該組合
已完成 renderer-specific tuning。

## 全矩陣試產

正式驗收以 `artifacts/renderer-matrix/matrix.json` 當次編譯出的 Theme、Layout 與
`combinations_per_renderer` 數量為一個完整 renderer matrix：

- HTML：每個 Theme 一份 catalog、每個 Theme × Layout 組合一張 slide，逐張 browser
  screenshot 與 overflow 檢查。
- PPTX：每個 Theme 一份 catalog、每個 Theme × Layout 組合一張 slide，逐張 PowerPoint
  原生 PNG render，並檢查指定 Theme master、六個背景角色、全部邏輯 layout mapping、
  slides 與 Placeholder。

唯一 renderer matrix 存於 `artifacts/renderer-matrix/matrix.json`。QA 若需留存
summary，必須由當次驗收明確產生；不得再複製一份 matrix 到 `artifacts/qa/`。
