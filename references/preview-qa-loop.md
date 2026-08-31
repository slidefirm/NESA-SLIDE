# Layout Preview QA Loop

每張正式 Layout Preview 都必須完成以下迴圈：

1. 依七段式 assembled YAML 生成圖片。
2. 檢查圖片，而不是只檢查 Prompt。
3. 將結果寫入 `artifacts/qa/layout-preview-qa.jsonl`。
4. 若有失敗項，只針對失敗項調整 YAML 或 Image2 Prompt 後重生。
5. 最多自動修正兩輪；仍未通過時保留紀錄並交由人工判斷。

## 必查項目

- `title_alignment`：標題軸線是否符合 Layout 與內容統攝範圍。
- `title_content_separation`：標題區與內容區是否有至少 5% 高度的前景淨空。
- `vertical_balance`：內容群組是否過高或過低；上下留白是否失衡。
- `information_hierarchy`：同級資訊是否同權，主從關係是否有語意依據。
- `visual_base_2a`：背景、字體、色彩與材質是否完整，而非空白底板。
- `decoration_2b`：邊角裝飾是否存在、服務構圖且不侵入內容。
- `text_accuracy`：必要文字是否正確、清楚且未被裁切。

## 標題對齊判斷

- 標題統攝整張投影片：對齊整體內容群組的中心軸。
- 標題只統攝單一欄位：對齊該欄位的閱讀軸。
- 不得因為左側圖形較醒目，就把全頁標題錯誤對齊左欄。
- Layout 未指定時：短標題（預估寬度 <35%）預設靠左；中標題（35%-72%）且統攝整頁時置中。
- 長標題（>72%）應先拆成語意完整的主標與副標；若仍以極小字或任意換行硬塞，`title_alignment` 判定為失敗。

## 紀錄格式

使用：

```powershell
python scripts/log_layout_preview_qa.py `
  --layout-id pyramid-3 `
  --image artifacts/deploy/layout-previews/pyramid-3-codex.png `
  --iteration 1 `
  --status fail `
  --check title_alignment=fail `
  --check vertical_balance=fail `
  --notes "標題錯誤對齊左欄；內容群組可下移以改善底部留白"
```
