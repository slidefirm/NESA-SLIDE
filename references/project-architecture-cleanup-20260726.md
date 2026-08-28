# 專案架構整理紀錄 — 2026-07-26

## 結論

這次沒有重寫正式 renderer，也沒有把 Art Direction 試作加入任何正式規則。

## 2026-07-27 更正：active dependency 不得當成歷史紀錄清除

前一輪整理曾把 `artifacts/deploy/layout-variants/` 依資料夾名稱與時間誤判為歷史輪播素材，忽略 `artifacts/deploy/layout-gallery.js` 仍直接引用其中檔案。這個判斷錯誤已更正：183 個素材已還原，目前有 152 個檔案是正式 Gallery 的 active dependency。

之後任何「清空歷史／多餘紀錄」任務，都必須先執行：

```powershell
python scripts\check_active_artifact_references.py <cleanup-target>
```

只要回報 `BLOCKED`，就不可刪除整個目標。檢查範圍包含正式 Gallery 與追蹤中的 JSON／YAML manifest；檔名含 `legacy`、資料較舊、ignored 或可由 Git 找回，都不能取代實際引用檢查。
實際完成兩件事：

1. 把新的三份 HTML 試作收斂成一個可重建、可退出的 experiment。
2. 清掉已確認可重建的舊 runtime 與本輪 QA 暫存，並新增只讀稽核工具，避免同類資料再次無聲累積。

## 本輪實際刪除

| 路徑 | 性質 | 檔案數 | 大小 | 恢復方式 |
|---|---|---:|---:|---|
| `artifacts/experiments/html-image-background/random-market-signal-20260706/` | Git 未追蹤、已 ignore 的舊背景實驗 runtime | 1,465 | 92.44MB | 由 `scripts/html_image_background_experiment.py` 重建 |
| `artifacts/experiments/art-direction-pilots-20260726/qa/raw/` | 21 張瀏覽器 raw screenshot | 21 | 15.40MB | 由 experiment `qa.cjs` 重建 |
| `artifacts/experiments/art-direction-pilots-20260726/qa/save-sandbox/` | 存檔／匯出測試副本 | 2 | 0.26MB | 重新執行 save/export QA |

合計刪除 1,488 個可重建檔案，實際約 108.10MB。

這些檔案不是移到資源回收筒，而是直接刪除；但都能由保留的 source／QA runner 重建。

## 新的 experiment 邊界

### Source

`experiments/art-direction-pilots-20260726/`

- `README.md`
- `design-briefs.json`
- `build.py`
- `qa.cjs`

### 精簡交付

`artifacts/experiments/art-direction-pilots-20260726/`

- 三份 HTML。
- 一份共用 `edit-mode.js`。
- 零照片、零插畫、零 SVG 的 Pattern／Geometry-only 視覺。
- manifest。
- 精簡 QA JSON 與 contact sheet。

### 可重建暫存

下列路徑已加入 `.gitignore`：

- `artifacts/experiments/*/qa/raw/`
- `artifacts/experiments/*/qa/save-sandbox/`
- `artifacts/experiments/*/.history/`
- `artifacts/experiments/*/qa/.history/`

## 容量稽核結果

使用：

```powershell
python scripts\audit_project_bloat.py `
  --output artifacts\qa\project-architecture-audit-20260726.json
```

目前結果（不沿 Windows Junction 計入外部 runtime）：

- 3,024 個實體檔案。
- 約 890.25MB。
- 其中約 171.74MB 是 ignored / untracked。
- 4 個 directory Junction 被獨立列出，不把 target 誤算成專案副本。

目前最大區塊：

| 區塊 | 大小 | 本輪處理 |
|---|---:|---|
| `artifacts/deploy/` | 363.36MB | 保留；包含正式部署輸出與 review／staging 證據 |
| `artifacts/pptx-backgrounds/` | 301.74MB | 保留；正式 PPTX 背景來源 |
| `artifacts/theme-demos/` | 64.44MB | 保留；正式 HTML Theme Lab |
| `artifacts/renderer-cases-deploy/` | 44.38MB | 保留；可再確認是否仍需本地 deploy scratch |
| `artifacts/discarded/` | 35.03MB | 保留；未在本輪擴張刪除權限 |

## 稽核中避免的一次誤刪

初步掃描曾把 `artifacts/pptx/node_modules` 與
`artifacts/pptx/runtime/node_modules` 算成 132MB 重複依賴。

實際檢查後確認其中包含指向共用 Codex runtime 的 Windows Junction，不是專案內兩份完整副本。
稽核器已改成：

- 不沿 Junction 或 symlink 計算容量。
- 把 directory links 另外列在 `directory_links_not_counted`。
- 不提供 delete 選項，保持 read-only。

## 仍可再做，但本輪沒有直接執行

1. 逐一確認 `renderer-cases-deploy/` 是否仍有使用者需要的本地預覽。
2. 為 `discarded/` 建立明確 retention window，再決定是否刪除。
3. 正式 renderer 未來可考慮把重複嵌入的 `edit-mode.js` 改為共享資產；本輪只在隔離試作採用，沒有改正式輸出契約。
4. `deploy/review` 與 staging 圖依 AGENTS.md 必須保留未通過候選，不應用一般清理腳本自動刪除。

## 未修改的正式來源

- `prompt_system/renderers/html/preset-themes.yaml`
- `prompt_system/renderers/html/layout-catalog.yaml`
- `prompt_system/renderers/html/assembly-catalog.yaml`
- 正式 Theme Lab gallery
