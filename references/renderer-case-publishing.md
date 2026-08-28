# HTML／PPTX 案例發布流程

## 架構

- 主站 `layout-catalog` 只保留 Layout／Theme 圖片與 `renderer-cases.js` 輕量 manifest。
- HTML runtime、`edit-mode.js`、PPTX 與少量案例預覽獨立部署到
  `layout-renderer-cases.pages.dev`。
- 主站若需要案例入口，只能放在獨立的「輸出案例」區。已驗收的 Layout Gallery 卡片
  維持 image-only，不顯示 HTML／PPTX 連結，也不複製重量資產。

案例來源由 `prompt_system/demos/renderer-case-catalog.json` 管理。HTML、PPTX 仍各自讀取
Theme/Layout core 與 renderer 規則；本 manifest 只負責發布，不是新的 Theme/Layout 庫。

## 建置

```powershell
python scripts\build_renderer_case_site.py
```

輸出：

- 獨立案例站：`artifacts/renderer-cases-deploy/`
- 主站輕量 manifest：`artifacts/deploy/renderer-cases.js`

建置時會驗證：

- 每個來源檔都存在；
- HTML 的實際 `data-layout-id` 與 catalog 宣告完全一致；
- HTML 旁的 `edit-mode.js` 一起複製；
- 來源檔案大小與每個公開 URL 寫入 manifest。

## 部署 Gate

建立 Pages 專案與部署都會改變遠端狀態，只有使用者針對本次工作明確授權後才可執行。
先依 `references/layout-catalog-deployment.md` 建立乾淨、經核准的 deploy snapshot 或隔離
worktree；不得從混合工作樹發布，也不得使用 `--commit-dirty=true`。

只有在使用者明確要求建立新專案，且確認 project name／production branch 後，才可執行：

```powershell
npx wrangler pages project create layout-renderer-cases --production-branch main
```

從已驗證的乾淨目錄部署案例站：

```powershell
npx wrangler pages deploy <verified-renderer-cases-deploy-dir> `
  --project-name layout-renderer-cases
```

若本次也已獲准更新主站，再從另一個已驗證的乾淨目錄部署：

```powershell
npx wrangler pages deploy <verified-layout-catalog-deploy-dir> `
  --project-name layout-catalog
```

## 驗收

1. `https://layout-renderer-cases.pages.dev/manifest.json` 可讀取。
2. 每個 HTML URL 能建立 `window.EditMode`，且 `?slide=N` 能直接開到對應 Layout。
3. 每個 PPTX URL 回傳正確 MIME，檔案大小與 manifest 一致。
4. 若主站有「輸出案例」區，該區可開啟所有外部連結。
5. Layout Gallery 卡片仍為 image-only，沒有 HTML／PPTX 按鈕或下載連結。
6. 對使用者指定的完整 URL 比對本機核准 artifact 的內容或 SHA-256；不能只用 Wrangler
   成功訊息當作發布證據。
