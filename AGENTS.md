# 專案 AI Agent 規則

## Clone 後的第一個動作

- 使用者要求建立、製作、重做簡報或投影片時，先讀 `.agents/skills/create-presentation/SKILL.md`；它是唯一對外前門，再由它路由到大綱、設計與 renderer Skill。
- 只有環境能力缺失時才執行 `npm run setup`；一般快速檢查使用 `npm run doctor`。
- 所有使用者成品寫入 `workspace/<project-id>/`，不得覆寫 shipped demo、Gallery 或 framework source。
- 不要要求使用者理解 Theme／Layout／adapter／manifest 才能開始；先完成他要的簡報，再於交付時說明必要邊界。

## 專案定位

這是一個以 `prompt_system/` 的 Theme／Layout core 為共同語意來源的 AI 簡報版型庫。Image2、HTML、PPTX 必須各自經過 renderer adapter；只有 Image2 正式生圖強制使用七段式 assembled YAML。HTML／PPTX 可直接使用 Art Direction、Theme／Layout core、renderer adapter 與 content manifest，不得把 assembled YAML 當成三種 renderer 的共同 runtime payload。

已驗收的共用 Theme/Layout 架構、HTML 編輯契約、排版重心與 PPTX 母片流程見 `references/presentation-production-contract.md`。根 `AGENTS.md` 負責 repository-wide 路由與安全邊界；reference 負責 renderer 契約；Skill 負責可重複程序。三者不一致時先停止受衝突影響的狀態變更，修正 canonical source，不得用籠統優先順序掩蓋差異。

## 任務語意與完成條件

- 開始實作前，先把使用者要求中的關鍵交付語意轉成可觀察完成條件，例如「隨機」「使用 Preset」「重新製作」「可編輯」「PPTX」「發布到指定網址」。不得只以檔案存在、程式執行成功或單一 QA 通過代替需求完成。
- 最終回報必須逐項對應：使用者要求、實際 artifact、相關 manifest／source、驗證證據與未驗證項目。任何關鍵項目未驗證時，必須標為 partial／未驗證，不得宣稱完整完成。
- 多頁 HTML deck 必須依共用契約完成 Art Direction Brief 與 scene grammar，再選 Theme／Layout。重新設計 Preset 或採用尚未驗收的新方向時，先完成 cover、一般內容頁、資訊密集頁三頁 pilot；若使用者未要求中途確認，可把 pilot 當成內部 Gate，通過後再擴成完整 deck。

## HTML Preset 內容模式

- HTML／Preset 生成預設使用 new-deck 模式：先建立或抽取全新簡報內容，再依內容關係選擇 Layout；不得自動沿用 Preset 的 example_story、example_layouts 或固定展示稿。
- Reusable Preset 的正式定義不得保存 `source_style_case`、舊 HTML／CSS、example story、example layouts、固定文案、文字替換表或任意 CSS。舊案例只可留在隔離的 Gallery／demo source；new-deck renderer 不得讀取。
- 測試新風格／轉換是另一條流程：沿用使用者提供的既有內容或明確的 content manifest，只改要測試的 Theme／Layout／renderer；不得自動改用 Preset 展示內容。
- preset-demo 只在使用者明確要求「展示 Preset 預設內容／範例」「查看 Preset 展示稿」等語意時使用；此模式才可以鎖定 Preset 的示範故事與頁面序列。
- 「使用新的 Preset」本身不等於「使用 Preset 預設內容」；若使用者沒有明確要求展示內容，仍以 new-deck 為準。
- renderer 入口必須能辨識並在 manifest 記錄 content_mode。new-deck 不得出現來自 Preset 範例的 forced-layout；preset-demo 必須記錄被鎖定的故事與 Layout。
- Agent 不得把 --style-case／--preset-demo 當成一般新簡報的快捷入口；這些參數只對應 preset-demo。


詳細步驟、命令與 QA 範例放在 repo-local Skill 或正式 reference；不要在多處複製同一流程。

| 任務 | 正式入口 |
|---|---|
| 投影片大綱、Content Plan 與 Layout 對應 | `.agents/skills/slide-outline-planner/SKILL.md` |
| Theme／Layout core、schema、renderer adapter | `prompt_system/AGENTS.md`、`prompt_system/README.md`、`references/renderer-adapter-contract.md` |
| HTML PRESET 名稱、公開狀態與 Gallery 順序 | `prompt_system/presets/catalog.yaml`、`scripts/html_preset_registry.py` |
| HTML CSS ownership 與幾何不變 Gate | `references/html-css-ownership-contract.md`、`scripts/html_css_ownership.py`、`scripts/qa_html_css_geometry_invariant.cjs`、`scripts/qa_html_css_preset_matrix.py` |
| 七段式 assembled YAML | `.agents/skills/generate-image-slide/SKILL.md` |
| Image2 正式預覽與 QA | `references/image2-preview-workflow.md` |
| HTML Pattern 產製、編輯器與 Browser QA | `.agents/skills/html-pattern-slide/SKILL.md`、`references/presentation-production-contract.md` |
| 新建含圖片版型的可編輯 HTML | `.agents/skills/html-image-slide/SKILL.md`、`.agents/skills/html-pattern-slide/SKILL.md`、`references/html-generation-rules.md` |
| 既有 HTML 的逐頁圖片背景與 PPTX 背景匯出 | `.agents/skills/slide-background-image/SKILL.md`、`references/pptx-generation-rules.md` |
| 可編輯 PPTX | `.agents/skills/ppt-builder/SKILL.md`、`references/pptx-generation-rules.md` |
| Layout catalog 部署 | `references/layout-catalog-deployment.md` |
| Artifact 清理 | `references/artifact-cleanup-workflow.md` |
| 可攜包：清單、建置、同步與 clone 驗收 | `references/portable-package-contract.md`、`packaging/portable-manifest.yaml`、`scripts/portable_manifest.py`、`scripts/build_portable_package.py`、`scripts/smoke_test_portable_package.py` |

- 任務符合 Skill 描述時，優先使用 `.agents/skills/` 的 repo-local 版本。
- 巢狀 `AGENTS.md` 只有在 Codex 從該子目錄或其下層啟動時才會自動載入；從 repository 根目錄工作時，依上表主動讀取對應正式入口。

## 隨機與 Image2 預覽

- 隨機生成必須保留可重現 manifest，並依 `references/presentation-production-contract.md` 與對應 repo-local Skill 驗證；不得把 Agent 固定挑選後的結果宣稱為隨機。
- Image2 正式預覽必須由完整七段式 assembled YAML 驅動，並依 `references/image2-preview-workflow.md` 保留來源 hash、實際輸出與 QA ledger。
- Image2 預設遵循目前 `imagegen` Skill 使用內建 `image_gen`；不得為了呼叫同一能力再啟動巢狀 `codex exec`。CLI／API fallback 只有在使用者明確指定，或內建工具不可用且使用者確認後才能使用。
- 不得以 PIL、SVG、HTML canvas、`scripts/render_*.py` 或其他 local renderer 冒充正式模型生圖；正式生成或 QA 未成功時直接標為未完成。
- 憑證只放在使用者環境、受控 secret store 或已被 Git 忽略的本機檔案；不得把 API key 或 token 寫入追蹤檔案。

## 部署、清理與讀取範圍

- 未經使用者明確授權，不部署、發布、push、建立或合併 PR，也不修改其他遠端或共享狀態。
- 部署不得用 `--commit-dirty=true` 掩蓋混合工作樹；依 `references/layout-catalog-deployment.md` 從乾淨、經核准的 deploy snapshot 或隔離 worktree 發布。
- 使用者提供 exact URL／host/path 時，該完整網址本身是交付物；發布後直接驗證該網址與本機核准 artifact 的內容一致性。
- 清理前依 `references/artifact-cleanup-workflow.md` 執行 `scripts/check_active_artifact_references.py`。回報 `BLOCKED` 的目標不得刪除；引用或可重建性不明時停止並詢問。
- 初始探索優先讀取 `prompt_system/`、`references/`、`.agents/skills/`、`scripts/` 與使用者指定的 artifact；任務需要時可讀取其他直接相關目錄、設定與程式碼。
- 未有明確任務需求時，不遞迴掃描 `artifacts/generated-prompts/staging/`、runtime log、review candidate 或 HTML history。
- 專案不以 `archive/` 保存歷史版本；正式歷史由 Git 追溯。不得只因檔名含 `legacy`、`old` 或日期較早就判斷可刪除。
- Gallery 的規格 source 是正式 layout／theme／style-case YAML 與 gallery manifest；被 manifest 或頁面直接或間接引用的 preview、HTML、CSS、JS、字型與下載檔仍是 active dependency。

## HTML 與 PPTX 交付底線

- HTML 必須保留可編輯語意結構；renderer 撰寫、semantic group、resize、產製順序與 Browser QA 以 `html-pattern-slide` Skill 和正式 reference 為準，根規則不重複其細節。
- 新建含圖片版型的 HTML 時，先由 `html-image-slide` 在 Layout 生成前完成 `image-planned` handoff，再交給 `html-pattern-slide`；已有 HTML 只要附加／替換背景時，使用 `slide-background-image` 並保留原本 Layout／前景；一般無圖片 HTML 仍維持 `pattern-only` 預設。
- HTML Layout／Theme／Preset 的 CSS 必須有明確 owner。Theme／Preset appearance 不得設定 Layout 幾何或使用 `!important`；source ownership 或 Browser geometry invariant 任一失敗時，不得把 artifact 描述為完成。
- 共用 editor 的 canonical source 是 `src/html-editor/edit-mode.js`；`artifacts/html-test/edit-mode.js` 只是本機相容副本。修改後先執行 `scripts/sync_editor_asset.py --write`，交付包含 embedded editor 時，再依 `html-pattern-slide` Skill 執行同步與 source-hash 驗證。
- 重新製作或改版必須修改正式 renderer／Theme adapter 後產出新 artifact；不得只在舊 HTML 上換皮，也不得覆蓋已交付版本。
- PPTX 預設交付真正可編輯的 PowerPoint。必須檢查 package/XML、Slide Master、實體 Custom Layout、Placeholder、native text／shape，並以 PowerPoint 原生渲染逐頁 QA；整頁截圖或背景圖不能冒充可編輯 PPTX。
- 沒有實際 artifact 與對應 QA 證據時，不得把規格、程式、dry run 或 canonical source 測試宣稱為完成交付。

## 同工作樹與提交防護

- 此專案常有多個 Agent 共用同一工作樹。修改 canonical editor、renderer、manifest 或 deploy artifact 前後，必須重新檢查目標檔案的 Git 狀態與 hash／mtime；檔案仍由其他程序持續改寫時，停止 stage／commit 並先建立明確 handoff 或 checkpoint。
- 大型混合工作樹禁止使用 `git add -A`。只能以明確路徑或 `git add -p` 做主題式暫存，並在 commit 前檢查 `git diff --cached --name-status`、`--stat` 與 `--check`。

## 內容事實驗證

- 簡報涉及產品名稱、版本、日期、公司規模、法規、醫療、資安或其他可能變動的外部事實時，必須先以官方／第一方來源驗證，再鎖定標題與敘事。未完成查證的內容須標為未驗證，不得因使用者提供了簡稱或舊名稱就直接沿用。

## Artifact 路徑可攜性

- 追蹤進 Git 的 JSON manifest 與 QA report，專案內路徑一律使用 repository-relative POSIX path；不得寫死 `C:\Users\...`、`C:/Users/...` 或 `file:///C:/Users/...`。
- 產製或更新報告後，執行 `python scripts/normalize_artifact_report_paths.py --fix`，並以不帶 `--fix` 的檢查模式作為提交前 Gate。

## 使用者指出錯誤時

1. 先檢查實際 artifact、規則、契約、程式與執行結果，以可觀察證據說明症狀與根因。
2. 判斷屬於規則衝突／缺口、程式或設定缺陷、流程不穩定，或未遵守既有規則；證據不足時標為暫定判斷。
3. 修改方向明確、風險低且未擴張範圍時，直接修正並驗證。只有不同方向會實質改變結果、風險或範圍時才詢問使用者。
4. 只有規則確有缺口、互相衝突或問題反覆發生時才更新正式規則；若是實作缺陷，修正程式或設定並補回歸驗證，不強制先新增規則。
