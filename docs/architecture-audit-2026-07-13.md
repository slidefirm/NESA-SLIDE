# 簡報系統架構與功能稽核（2026-07-13）

## 結論

目前系統的核心方向是正確的：Theme、Layout 與三種 Renderer 已經有清楚分工，
31 個 Theme、81 個 Layout 與 336 份 Renderer adapter 也能確定性編譯。

但「規格覆蓋」與「正式產線完成」目前混在同一個完成度敘事裡：

- HTML 是完成度最高的一條路徑，31 × 81 結構與視覺矩陣都已建立，編輯框架也能實際操作。
- Image2 的 adapter 已完整，但主 Gallery 只有 52 / 81 個 Layout 有目前版本的正式 Image2 preview。
- PPTX 的 31 × 81 matrix 證明原生 Placeholder 與 Custom Layout 結構可建立；
  Image2 六底圖 + 母片的正式 hybrid 流程目前只完成 `brand-editorial` 1 / 31 個 Theme。
- QA 工具很多，但缺少統一入口、來源新鮮度檢查與部署硬閘門，因此舊報告仍可能顯示 pass。

建議先修「完成度與發布可信度」，再擴充更多視覺資產，最後才拆大型 Renderer。

## 本次存檔點

- 分支：`feat/html-edit-mode-select-resize-persist`
- 分析前 checkpoint：`093506c7b396ce0d094d658a6b508226d6fca98f`
- 訊息：`checkpoint: save presentation system before architecture audit`
- checkpoint 只納入正式專案內容；根目錄 7 個 questionnaire / stray 檔案維持未追蹤，未混入簡報系統。

## 架構現況

```text
Theme core (31) ─┬─ Image2 theme adapters (31)
                 ├─ HTML theme adapters   (31)
                 └─ PPTX theme adapters   (31)

Layout core (81) ┬─ Image2 layout adapters (81)
                 ├─ HTML layout adapters   (81)
                 └─ PPTX layout adapters   (81)

Content manifest ──> Renderer-specific composition ──> Image2 / HTML / PPTX
```

正確的共同來源是：

- Theme 決定「長得像誰」：色彩、字體、材質、裝飾語彙。
- Layout 決定「怎麼讀」：slot、資訊關係、閱讀順序與視覺重心。
- Adapter 只描述某 Renderer 如何落地，不得成為第二份 Theme / Layout。
- assembled YAML 是 Image2 的完整 payload，不是 HTML / PPTX 必須共同載入的通用格式。

## 已驗證項目

### Theme / Layout / Adapter

- Theme core：31。
- Layout core：81。
- Renderer adapters：336，`generate_renderer_adapters.py --check` 通過。
- 重新編譯的 renderer matrix 與現有 `matrix.json` hash 相同。
- 每條 Renderer 的理論組合數：31 × 81 = 2,511。

### HTML

- 31 份 Theme catalog，每份 81 張，共 2,511 張。
- 目前 31 份 matrix HTML 全部嵌入同一份最新 editor source，hash 驗證通過。
- production contract check：2,511 / 2,511 通過。
- 現有 full visual evidence：2,511 張 screenshot、36 張代表性 contact sheet、4 個 editor frame check。
- 本次重新執行三份互動驗收：
  - `brand-editorial-layout-demo.html`：通過。
  - `brand-editorial-triple-route-demo.html`：通過。
  - `product-signal-loop-engineering-demo.html`：通過。
- 等比例縮放現在會保持：
  - 長寬比一致；
  - 文字視覺比例一致；
  - 不新增換行；
  - 垂直中心位移約 0；
  - Undo / Redo、draft restore、export / reopen 正常。

### PPTX matrix

- 31 份 PPTX，每份 81 張，結構檢查無錯誤。
- 每份檔案實際為 81 個自訂 Layout + 1 個函式庫預設 Layout，共 82。
- 每份檔案實際為 1 個自訂 Theme master + 1 個函式庫預設 master，共 2。
- 因此 82 / 2 是 artifact-tool 的預設結構，不代表多出一個正式 Layout 或 Theme。

### Image2 preview

- 主 preview 目錄有 52 張目前版 `*-codex.png`，52 張最新 QA 全部為 pass。
- Theme preview 為 31 / 31。
- 但這不等於 81 個 Layout 全部已有目前版正式 preview，詳見下方缺口。

## 主要缺口與風險

### P0-1：Gallery 與 Layout core 不一致

核心庫有 81 個 Layout，但正式 `layout-gallery.js` 只有 75 個；下列 6 個被
`generate_layout_gallery.py` 的 `EXCLUDED_IDS` 硬排除：

- `brand-guideline-core`
- `left-text-right-image`
- `photo-grid-gallery`
- `single-column`
- `toc-list`
- `toc-number-grid`

另外 75 個已公開 Layout 中，只有 52 個有目前版 Image2 preview；另外 23 個完全依賴
legacy variants。換句話說，目前正式 Image2 Layout preview 的實際新版本覆蓋是
52 / 81（64.2%），不是 81 / 81。

更重要的是，Gallery generator 強制每個 Layout 必須有 3 張輪播圖，並直接讀取
`layout-variants/*-legacy-*`。這與專案規則「歷史版本回 Git 查、Gallery active source
不得由歷史 preview 反推」互相矛盾。

建議：

1. 移除 `EXCLUDED_IDS`，81 個正式 Layout 必須全部進 Gallery。
2. 把三張輪播改成語意角色，而不是歷史版本配額，例如：
   `current Image2`、`structure SVG`、`style case`。
3. 依序補完缺少的 29 張目前版 preview（23 個 legacy-only + 6 個 excluded），逐張走 YAML 與 QA。

### P0-2：部署流程有斷點，而且 QA 不是硬閘門

- `AGENTS.md` 與 `gen_from_assembled_yamls.ps1` 都呼叫
  `scripts/build_staging_gallery.py`，但檔案不存在。
- `docs/architecture.md` 建議用 `verify_layout_preview_qa.py --warn-only`，
  但專案規則要求主 Gallery 必須 strict pass。
- `generate_layout_gallery.py`、`generate_theme_gallery.py` 與實際 `wrangler pages deploy`
  之間沒有一個統一、不可略過的驗證入口。

建議新增單一 `scripts/deploy_gallery.ps1`：

1. adapter `--check`；
2. matrix 重新編譯與差異檢查；
3. strict preview QA；
4. Gallery build；
5. WebP 轉換與 reference check；
6. 最後才允許 Wrangler deploy。

任何一步失敗都停止，不保留 `--warn-only` 的正式部署入口。

### P0-3：QA 報告沒有「新鮮度」概念

目前最新 editor source 的 hash 與 13 個 family `editor-hash.json` 不同，但
`verify_html_production_completion.py` 只檢查這些舊 JSON 的 `pass` 欄位，仍會回報
`production_complete: true`。視覺報告也早於最新 editor source。

這不是代表現在畫面有錯，而是代表「pass」沒有證明它驗的是目前版本。

建議所有 QA report 至少記錄並驗證：

- Git commit；
- Theme / Layout / adapter manifest hash；
- Renderer source hash；
- editor source hash；
- 直接輸入檔 hash；
- 產物 hash；
- 產生時間與工具版本。

只要任一來源 hash 不同，狀態應變成 `stale`，不能繼續顯示 `pass`。

### P0-4：PPTX 的兩條路徑被當成同一種完成度

目前 31 × 81 PPTX matrix 使用純程式化 Theme 色彩、Placeholder 與可見測試物件，
它證明的是 native structure coverage。

使用者指定的正式預設則是 hybrid：每個 Theme 先用 Image2 產生六張無字底圖，再以
PowerPoint master / child layout 放入 Placeholder。這條流程目前只有
`brand-editorial` 的六張底圖、六個 Custom Layout 與 QA 證據，覆蓋 1 / 31（3.2%）。

建議把狀態拆成兩個獨立指標：

- `native_structure_coverage = 31 / 31`
- `hybrid_background_master_coverage = 1 / 31`

在 31 個 Theme 的六底圖與 master set 未完成前，不應把 PPTX 說成全面完成 hybrid。

### P1-1：共用 editor source 放在 artifacts

正式 HTML editor source 是 `artifacts/html-test/edit-mode.js`，但它其實是產品程式碼，
不是測試產物。每次改動後還要同步 4 份 `edit-mode.js` 與 34 份嵌入式 HTML。

目前 editor 約 137 KB，嵌入 34 份 HTML，單是重複 editor 就約 4.5 MB，且每次小改動
都會讓 30 多個大型 HTML 出現相同 diff。

建議：

- source 移到 `src/html-editor/`；
- 開發／QA 版本使用單一 external bundle；
- 只有「獨立交付 HTML」的 export/build 步驟才 inline embed；
- 產物由 build 生成，不手動同步。

### P1-2：HTML Renderer 與 editor 已成為單體檔案

- `html_production_renderer.py`：2,108 行、82 個函式。
- `edit-mode.js`：3,404 行、約 138 個函式。
- HTML 規則文件合計 1,308 行，責任分散在 production contract、generation rules、
  layout patterns 與程式碼。

建議先依責任拆模組，不改輸出：

- Renderer：core geometry、family renderers、theme tokens、content fitting、serialization。
- Editor：selection、geometry、text editing、grouping、history、persistence、export、toolbar。
- 規則：一份 machine-checkable contract + 各 Renderer 只記例外。

### P1-3：依賴與測試無法在專案根目錄直接重現

根目錄沒有 `package.json`、lockfile、`pyproject.toml`、`requirements.txt` 或 CI workflow。
從根目錄直接 resolve `@oai/artifact-tool` 會失敗；Playwright QA 也必須額外借用 Codex
runtime 並手動補 `NODE_PATH`。

建議：

- 建立根目錄 Node / Python dependency manifest 與 lock；
- 提供 `scripts/bootstrap.ps1`；
- 提供 `scripts/audit.ps1`，統一執行 syntax、adapter、matrix、HTML interaction、PPTX structure、preview QA；
- CI 至少執行不需要 PowerPoint / Image2 的 deterministic checks；
- Windows + PowerPoint 的 hybrid QA 另外標為 platform job。

### P1-4：PPTX hybrid QA 仍偏人工

現有 `pptx-background-master-qa.json` 證明 `brand-editorial` 六張 layout background、
21 個 Placeholder 與內容群組置中皆通過；但沒有對應的正式 verifier source，且
`generic_slides_test` 被標為 not applicable。

建議建立 `verify_pptx_background_master.py`，直接檢查：

- 六個角色齊全；
- 背景只存在 child layout；
- slide 不重複底圖；
- Placeholder 數量與 manifest 一致；
- content group 中心誤差；
- PowerPoint render 圖片尺寸與非空白；
- 實際文字 overflow。

### P2-1：產物與 Git 維護成本偏高

- `artifacts/deploy` 約 230.6 MiB。
- HTML full matrix screenshots 約 133.3 MiB。
- renderer matrix HTML + PPTX 約 23.7 MiB。
- Git 目前約 14,058 個 loose objects（220 MiB），pack 約 1.35 GiB，且曾出現暫存 garbage 警告。

建議把可重建產物分成：

- Git 追蹤：規格、少量代表性 evidence、發布 manifest。
- Git 忽略：完整 matrix screenshot、暫存 PNG、runtime cache。
- 發布保存：Cloudflare / release artifact，靠 manifest hash 回溯。

執行 Git maintenance 前應先備份並確認沒有其他 Agent 共用工作樹，不直接執行破壞性 prune。

## 建議實施順序

### 第一階段：讓完成度可信

1. 修復 Gallery 81 / 81 覆蓋模型，停止依賴 legacy 配額。
2. 補回 `build_staging_gallery.py` 或以單一 deploy script 取代所有舊引用。
3. 將 strict QA 接到部署前硬閘門。
4. QA report 加入 source / artifact hash 與 stale 判定。
5. 建立根目錄 dependency lock 與 `audit.ps1`。

### 第二階段：補齊正式產線

1. 逐張補完 29 個缺少的目前版 Layout preview。
2. 為剩餘 30 個 Theme 建立六背景角色與 hybrid PPTX master set。
3. 建立 PPTX hybrid 自動 verifier 與 Theme preview QA log。
4. 建立一份真正共用同一 content manifest 的三路 canonical acceptance suite。

### 第三階段：降低維護成本

1. 將 editor source 移出 artifacts，建立正式 bundle / embed build。
2. 拆分 HTML renderer 與 editor 單體檔案。
3. 合併重複規則，將可機器驗證部分轉成 schema / assertions。
4. 清理可重建產物與 Git objects。

## 這次已直接修正的 HTML 問題

文字、群組與 Composite 現在統一採用等比例 visual transform：

- 側邊控制點不再把文字橫向拉寬；
- 不再因為改寫 width / font-size 觸發換行；
- inline / flex 文字從自身中心縮放；
- absolute 物件保留可移動錨點；
- 測試新增 aspect ratio、行數、文字墨跡比例與中心位移判定；
- QA selector 改為以語意能力尋找可編輯目標，不再要求每份 Demo 都出現完全相同的元件。
