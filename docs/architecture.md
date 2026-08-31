# 專案架構總覽

本專案是 YAML-first 的 AI 簡報版型庫。核心原則是：可重複利用的組合要件放在 `prompt_system/` 與 `references/`，兩個 Gallery 與生成成品放在 `artifacts/`。歷史資料不留在 active tree，需要追溯時使用 Git history。

## 核心層級

1. Reusable building blocks
   - `prompt_system/layouts/`：正式 layout 結構，描述 slot、safe area、alignment、visual balance。
   - `prompt_system/themes/`：可重複套用的視覺語言、色彩、字體、裝飾系統。
   - `prompt_system/presets/catalog.yaml`：PRESET 身分、能力、公開狀態與 Gallery 順序的唯一名冊。
   - `src/html-editor/`：共用 HTML 編輯器原稿；產生到 `artifacts/` 的副本不是反向來源。
   - `prompt_system/style_cases/`：layout + theme 的可重複示範組合，用來展示某個版型如何被風格化。
   - `references/`：生成規則、HTML renderer 規則、QA loop 等流程規範。
   - `.agents/skills/`：本專案專用 Skill，例如 `generate-image-slide`、`html-pattern-slide`、`html-image-slide` 與 `ppt-builder`。

2. Generated showcase artifacts
   - `artifacts/generated-prompts/`：生成出的 assembled YAML，是單次輸出的 prompt payload，不是 reusable template。
   - `artifacts/deploy/layout-previews/`：正式 layout 網站使用的已生成 preview。
   - `artifacts/deploy/*.html`、`artifacts/deploy/*.js`：可部署網站成品。
   - `artifacts/qa/layout-preview-qa.jsonl`：正式 preview 的人工/事後 QA 紀錄。

3. Minimal reference assets
   - `prompt_system/reference_assets/`：只有 style case 明確引用、無法再生的少量來源圖片。

## 主要流程

### 已驗收生產契約

跨 Image2、HTML、PPTX 的共用邊界、排版重心、Renderer 分工與 QA 契約見
`references/presentation-production-contract.md`。本文件只說明專案目錄與主要流程，不重複實作規則。

### 圖片式 layout preview

正式流程必須遵守 AGENTS.md：

1. 用 `generate-image-slide` 產生七段式 assembled YAML。
2. 完整讀取 assembled YAML。
3. 由目前工作的 Codex 直接使用內建 `image_gen`，並讓工具讀取完整設計規格；不要從腳本再啟動巢狀 `codex exec`。
4. 輸出穩定 PNG 到 preview 目錄。
5. 依 `references/preview-qa-loop.md` 寫入 QA record。
6. 需要公開時再 build gallery 與 deploy。

重要邊界：assembled YAML 是圖片式簡報 preview 的 payload，不是 HTML/PPT renderer 的通用中介格式。

### Main gallery

- 入口：`python scripts/generate_layout_gallery.py`
- 輸入：`prompt_system/layouts/`、`prompt_system/style_cases/`、本次組裝時動態決定的 content contract
- 輸出：`artifacts/deploy/layout-gallery.js` 與 `artifacts/deploy/layout-previews/`
- 注意：舊版 gallery metadata 曾記錄內容規格路徑；目前 content contract 不留存為靜態檔。
- 建議部署前檢查：`python scripts/verify_layout_preview_qa.py --warn-only`

### Theme gallery

- 入口：`python scripts/generate_theme_gallery.py`
- 輸入：`prompt_system/themes/`、`prompt_system/style_cases/`、`prompt_system/presets/catalog.yaml` 與正式 theme previews
- 輸出：`artifacts/deploy/themes-gallery.js`
- PRESET 卡片先依 registry 決定 17 個公開項目與順序，再讀 Theme Lab 案例或 reusable Preset 實作；不得再以兩份來源的先後順序猜公開名單。

### HTML renderer

- 入口 skill：`.agents/skills/html-pattern-slide/SKILL.md`
- 規則：`references/html-generation-rules.md`、`references/html-layout-patterns.md`、`references/html-css-ownership-contract.md`
- 本地測試：`artifacts/html-test/dev_server.py`
- 互動編輯原稿：`src/html-editor/edit-mode.js`

HTML renderer 要直接依照 layout/theme/content 規則產 HTML，不應被圖片 preview 的 assembled YAML 流程綁死。
其中 Layout／renderer-base 是幾何的唯一 owner；Theme／Preset 只提供外觀 token。new-deck 不讀取舊案例的內容、版型序列或 CSS，並以關閉外觀 CSS 前後的幾何不變測試作為 release gate。

`src/html-editor/edit-mode.js` 是唯一 canonical editor source；
`artifacts/html-test/edit-mode.js` 是供既有本機流程使用的產生副本，兩者由
`scripts/sync_editor_asset.py` 做 hash 檢查。正式 HTML 內嵌 editor 時仍必須驗證 source hash；
其他成品中的 `edit-mode.js` 都是投影副本，不得反向修改後當成新原稿。歷史交付保留原 hash，
不為了搬原稿位置而批次改寫。

### PRESET 與 Layout Gallery

- Layout Gallery 展示全部正式 Layout 的圖片預覽，維持已驗收的 image-only 卡片。
- PRESET 展示區可包含完整 Theme Lab 案例與可重複使用的 HTML 視覺 recipe；registry 會明確標出兩者能力，與 Layout 是不同資料面與回復範圍。案例只供展示／比較，不是 new-deck 的 runtime source。
- HTML／PPTX 案例可放在獨立「輸出案例」區，不在 Layout 卡片加入下載或案例連結。

## 不建議再新增的混淆模式

- 不要把 `artifacts/deploy/*.png` 當成 reusable design source。
- 不要把 local renderer 產出的 SVG/PIL/canvas preview 說成 Codex/Image2 正式生圖。
- 不要只抽 `closing_design_intent` 當正式生圖 prompt。
- 不要讓 batch script 以巢狀 `codex exec` 代替目前工作的內建 `image_gen`。
- 不要把 generated logs、pid、runtime cache 納入日常 commit。
- 不要在 repo 內建立 archive；歷史追溯交給 Git。
- 一次性 patch／probe 放在 `tools/migrations/`，不得混回正式 `scripts/` 根目錄。

部署規則只維護在 `references/layout-catalog-deployment.md`。沒有本次明確授權、乾淨核准
snapshot 與 exact URL 驗證時，不執行部署，也不得用 `--commit-dirty=true` 掩蓋混合工作樹。

## 漸進式治理工具

- `scripts/verify_layout_preview_qa.py`：只讀 preview 目錄與 QA JSONL，檢查每張 preview 的最新 QA 是否為 `pass`。
- 預設模式會在缺 QA 或最新非 pass 時 exit 1；若只是盤點現況，使用 `--warn-only`。
- 目前不自動接入部署流程，避免突然影響既有系統運行。
