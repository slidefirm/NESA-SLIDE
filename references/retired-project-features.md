# 已退出 active tree 的功能與產物

本專案不建立 `archive/` 資料夾。以下內容已從正式入口、部署輸出或版本追蹤樹退出；如需取回，請從 Git tag `checkpoint/pre-html-design-cleanup-20260720` 或 commit `37783275fd6bef15914b2f04f5cc1984466e2898` 還原。

新增或擴大此清單前，必須先以 `python scripts\check_active_artifact_references.py <target>` 證明目標未被正式 Gallery 或追蹤中的 JSON／YAML manifest 引用；回報 `BLOCKED` 的項目不得列為退出或清理對象。

| 已退出項目 | 原因 | 現在的正式做法 |
| --- | --- | --- |
| `artifacts/renderer-matrix/html/` 與 `pptx/` | 批次可重建，不應當成 active source | 需要時由 renderer matrix 腳本重建，不進 Git |
| `artifacts/qa/html-production/` 的大量截圖與臨時報表 | 舊報表曾有 issue 數與 pass 狀態不一致，且容量過大 | 保留 QA 腳本；精選 Theme Lab 保留 contact sheet 與驗收報表 |
| 根目錄舊 `edit-mode.js` | 與正式版不同步，容易用錯 | 唯一正式來源是 `src/html-editor/edit-mode.js`；`artifacts/html-test/edit-mode.js` 是產生副本 |
| 根目錄問卷分析腳本與中間檔 | 屬單次分析，與簡報 renderer 無引用關係 | 需要時從 checkpoint 取回 |
| `artifacts/html-test/` 下過期的單次 Demo | 與正式 Theme Lab 和 acceptance demo 重複 | 保留 `deck.html`/`deck.yaml`、`dev_server.py`、`test_dev_server.py` 與產生的 `edit-mode.js` 相容副本 |

此次退出不會刪除 `prompt_system/`、`references/`、`skills/`、`scripts/` 的核心生成能力，也不會動 Theme/Layout core。
