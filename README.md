# NESA-SLIDE

**給 Codex 與 Claude Code 直接 clone 使用的 AI 簡報製作系統。**

NESA-SLIDE 可以製作四種簡報：一般可編輯 HTML、含圖片的可編輯 HTML、原生可編輯 PPTX，以及 Image2 圖片式簡報。內容規劃、視覺方向、版面與輸出流程都由專案內的 Skills 處理。

[查看 8 頁可編輯 HTML 案例](https://slidefirm.github.io/NESA-SLIDE/demo-deck.html) · [瀏覽 GitHub repository](https://github.com/slidefirm/NESA-SLIDE)

## 直接交給 AI

直接把下面這段貼給 Codex 或 Claude Code，再替換主題、頁數與輸出格式：

```text
請 clone https://github.com/slidefirm/NESA-SLIDE，進入專案後讀取 AGENTS.md 與對應的 NESA-SLIDE Skill，幫我製作一份關於「我的主題」的 10 頁簡報，輸出為「可編輯 HTML／含圖片的可編輯 HTML／原生可編輯 PPTX／Image2 圖片式簡報」。
```

AI 會自行 clone repository、檢查環境並選擇正確的製作流程。新成品會放在 `workspace/<project-id>/`。

如果還沒決定格式，可以請 AI 先使用 `design-presentations`，依受眾、使用方式與後續編輯需求協助選擇。

## 四種製作方式

| 想要的成果 | 使用的 Skill | 適合情境 | 可以這樣要求 AI |
| --- | --- | --- | --- |
| **一般可編輯 HTML** | `html-pattern-slide` | 一般網頁式簡報；文字與物件可編輯，也能播放、換頁與保存 HTML。 | 「製作一份 10 頁可編輯 HTML 簡報。」 |
| **含圖片的可編輯 HTML** | `html-image-slide` | 照片或插圖是版面重點；圖片、文字與物件需要分開編輯。 | 「製作一份以人物照片為主要構圖的可編輯 HTML 簡報。」 |
| **原生可編輯 PPTX** | `ppt-builder` | 需要在 PowerPoint 繼續修改文字、形狀、母片與版面。 | 「製作成原生可編輯 PPTX，不要把整頁做成圖片。」 |
| **Image2 圖片式簡報** | `generate-image-slide` | 重視完整畫面、風格一致與視覺衝擊；不要求頁面物件可個別編輯。 | 「製作一份 10 頁 Image2 圖片式簡報。」 |

## 成品案例

### [8 頁可編輯 HTML 案例](https://slidefirm.github.io/NESA-SLIDE/demo-deck.html)

案例包含固定 1920×1080 畫布、文字與物件編輯、鍵盤換頁、播放模式與 HTML 保存。案例只用來展示系統能力；AI 會依你的內容重新規劃，不會直接套用案例文案。

其他三種輸出可以直接複製上表的需求範例，交給 AI 依你的主題產生。

## 專案內的 7 個 Skills

| Skill | 什麼時候使用 |
| --- | --- |
| `design-presentations` | 還沒決定輸出格式，或需要先規劃整份簡報的視覺方向與跨頁節奏。 |
| `slide-outline-planner` | 只需要大綱、逐頁內容、講稿或版面建議，還不需要產出成品。 |
| `html-pattern-slide` | 製作或修改一般可編輯 HTML 簡報。 |
| `html-image-slide` | 新建以照片或插圖為主要構圖的可編輯 HTML 簡報。 |
| `slide-background-image` | 已經有 HTML，只需要新增、替換或檢查逐頁背景。 |
| `ppt-builder` | 製作原生可編輯 PowerPoint。 |
| `generate-image-slide` | 製作 Image2 圖片式投影片或七段式生成 YAML。 |

Codex 從 `.agents/skills/` 讀取 Skills；Claude Code 依 `CLAUDE.md` 導向相同的正式規範。

## 使用前需要知道

- 可編輯 HTML 可以直接在瀏覽器使用；實際功能以成品的瀏覽器檢查結果為準。
- Image2 需要 AI 環境提供影像生成能力。
- 原生 PPTX 需要相容的簡報產製環境；若要做最終版面檢查，還需要 PowerPoint。
- 部分 macOS 與外部產製能力尚未在所有實際環境完整驗證。

## 給維護者

| 路徑 | 內容 |
| --- | --- |
| `.agents/skills/` | 7 個專案 Skills。 |
| `prompt_system/` | 視覺方向、Theme、Layout 與各輸出格式的轉接規格。 |
| `src/html-editor/` | HTML 編輯器原始碼。 |
| `scripts/` | 產製、檢查與 QA 工具。 |
| `demos/html/` | 公開 HTML 案例。 |
| `workspace/` | 使用者的新專案與交付成品。 |

個人輸出只放在 `workspace/`，不要寫回 Skill、規格或案例目錄。

```powershell
npm run audit --silent
```

開發、測試與發布流程請讀 [CONTRIBUTING.md](CONTRIBUTING.md)、[AGENTS.md](AGENTS.md) 與 [SECURITY.md](SECURITY.md)。

## License

First-party source and demo material are licensed under the [MIT License](LICENSE), copyright Slide Firm. Third-party software and assets retain their own notices in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and adjacent license files.
