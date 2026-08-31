# 素材分類與生命週期

整理素材時，先判斷它是「會重複利用的組合要件」還是「用來展示的成品」。這個判斷比檔案格式更重要。

## 可重複利用的組合要件

這類檔案是未來生成的 source of truth，應該維持乾淨、可讀、可版本化。

| 類型 | 位置 | 用途 | 管理原則 |
| --- | --- | --- | --- |
| Layout | `prompt_system/layouts/` | 定義結構、slot、safe zone、alignment | 不放具體配色與單次文案 |
| Theme | `prompt_system/themes/` | 定義可重複使用的視覺語言 | 不綁定單一 layout 成品 |
| Style case | `prompt_system/style_cases/` | 展示 layout + theme 的可重複組合 | 可指向 preview，但 preview 不是 source |
| Dynamic content contract | 組裝時即時決定 | 宣告本次 `content` 欄位與重複項目，不留存為靜態檔 | 不與 layout 永久一對一綁定 |
| 生成規則 | `references/`、`skills/`、`AGENTS.md` | 規範 agent 與 renderer 行為 | 比單次 artifact 優先 |
| HTML renderer source | `src/html-editor/edit-mode.js` | 共用 HTML 編輯器原稿 | 修改後產生相容副本並對交付物做 hash 驗證 |
| HTML local test asset | `artifacts/html-test/edit-mode.js`、`artifacts/html-test/dev_server.py` | HTML 預覽與相容工具 | `edit-mode.js` 是產生副本，不是原稿 |

## 展示用成品

這類檔案用來看結果、部署網站、回溯 QA。它們可以保存，但不應被拿來反推成下一次生成的唯一規格。

| 類型 | 位置 | 用途 | 管理原則 |
| --- | --- | --- | --- |
| Assembled YAML | `artifacts/generated-prompts/` | 單次圖片式 preview 的完整 prompt payload | 是輸出，不是 template |
| Main preview image | `artifacts/deploy/layout-previews/` | layout 網站正式預覽圖 | 需要 QA pass 才應部署 |
| Gallery bundle | `artifacts/deploy/*.html`、`artifacts/deploy/*.js` | 可部署網站 | 由 scripts 生成，不手改 generated JS |
| QA record | `artifacts/qa/layout-preview-qa.jsonl` | 記錄每張正式 preview 的檢查結果 | 應補齊 coverage 與最後 pass |
| HTML demo/output | `artifacts/html-test/`、`artifacts/html-edit-preview-deploy/` | HTML renderer 測試或 demo 成品 | 不與 Image2 preview 混用 |

## 必要參考素材

| 類型 | 位置 | 用途 | 管理原則 |
| --- | --- | --- | --- |
| Style-case source | `prompt_system/reference_assets/` | 無法再生且被 YAML 明確引用的來源圖片 | 只保留實際引用檔案 |

## 判斷規則

- 如果檔案會被未來多次組合使用，它是 reusable building block。
- 如果檔案代表某次生成、某次部署、某次測試結果，它是 showcase artifact。
- 如果外部素材未被 active YAML 明確引用，就不留在 repo。
- 如果檔案是 log、pid、cache、timestamped runtime output，預設不應 commit。
- 如果只是歷史版本，使用 Git history，不另建 archive。
