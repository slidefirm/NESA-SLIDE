# 2026-07-22 專案清理紀錄

本輪把 735 個不再屬於正式入口的檔案移到本機忽略目錄：

`artifacts/discarded/2026-07-22/`

總大小約 36.73 MB。此目錄不提交、不部署，保留在本機供短期回查。

| 分類 | 檔案數 | 說明 |
|---|---:|---|
| `html-style-case-examples-qa` | 139 | 重複的 contact sheet、畫面擷取與互動除錯輸出 |
| `html-test-one-offs` | 17 | 已退休的一次性 HTML Demo；正式 `deck.html`、`deck.yaml`、`edit-mode.js` 與測試工具保留原位 |
| `legacy-qa` | 117 | 舊 Dark AI City 視覺、幾何與背景驗證輸出 |
| `local-dependencies/node_modules` | 462 | 為本輪 headless QA 暫時安裝的 Playwright 套件，可由 npm 重新取得 |

舊版 Theme Lab 的正式追蹤檔沒有複製到 discard；它們由 Git history 保存，active 路徑只保留第三版三個完整 Theme 及最新 QA。
