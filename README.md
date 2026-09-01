# NESA-SLIDE

**把 Story、Art Direction、Theme、Layout 與 renderer 分開管理的 AI 簡報製作系統。**

NESA-SLIDE 由 Slide Firm 維護，分別支援 Image2 圖片式簡報、可編輯 HTML 與原生可編輯 PPTX。三種輸出共用內容與設計語意，但各自使用適合的 renderer 與驗證流程。

[開啟 8 頁可編輯 HTML 案例](https://slidefirm.github.io/NESA-SLIDE/demo-deck.html) · [下載 v0.2.0 portable package](https://github.com/slidefirm/NESA-SLIDE/releases/download/v0.2.0/NESA-SLIDE-v0.2.0-portable.zip) · [版本紀錄](CHANGELOG.md)

## 先看一份實際成品

線上案例展示固定 1920×1080 畫布、文字與物件編輯、鍵盤換頁、播放模式與 HTML 下載。

### [查看 8 頁可編輯 HTML 案例](https://slidefirm.github.io/NESA-SLIDE/demo-deck.html)

GitHub Pages 是靜態展示。你可以在瀏覽器編輯並下載成品，但修改不會直接寫回 GitHub。案例只用來展示系統能力，不會成為新簡報的固定內容或版型。

## 開始使用

### 1. 下載並解壓 portable package

[下載 NESA-SLIDE v0.2.0](https://github.com/slidefirm/NESA-SLIDE/releases/download/v0.2.0/NESA-SLIDE-v0.2.0-portable.zip)

套件內含 36 個 Theme、75 個 Layout、43 個 HTML style cases、7 支專案 Skills，以及產製與驗證所需的程式和規範。

### 2. 檢查環境

Windows 可以直接執行 `CHECK_SYSTEM.cmd`，或在終端機執行：

```powershell
python -m pip install -r requirements.txt
npm ci --ignore-scripts
python CHECK_SYSTEM.py
```

基礎環境需求：

- Windows 10／11；
- CPython 3.13+；
- Node.js 22+；
- Chrome、Edge 或 Chromium。

### 3. 交給 Agent 製作簡報

在 Codex 或 Claude Code 開啟解壓後的資料夾，再於需求中寫出要使用的 Skill。例如：

```text
請使用 html-pattern-slide Skill，參考案例 https://slidefirm.github.io/NESA-SLIDE/demo-deck.html，幫我製作一份關於「我的主題」的 10 頁可編輯 HTML 簡報。
```

Codex 會從 `.agents/skills/` 讀取專案 Skill；Claude Code 依 `CLAUDE.md` 導向相同的正式 Skill 與規範。所有新成品都應放在 `workspace/<project-id>/`。

## 支援的輸出格式

| 輸出 | 對應 Skill | 適合情境 |
| --- | --- | --- |
| 可編輯 HTML | `html-pattern-slide` | 一般網頁式簡報；文字與物件保持可編輯。 |
| 含圖片的可編輯 HTML | `html-image-slide` | 照片、插圖、半版圖或滿版圖會影響主要構圖。 |
| 原生可編輯 PPTX | `ppt-builder` | 需要 PowerPoint 原生文字、形狀、母片與版面。 |
| Image2 圖片式簡報 | `generate-image-slide` | 每頁以完整點陣視覺呈現，重視整體畫面與藝術指導。 |

如果尚未決定輸出格式，先使用 `design-presentations`，讓 Agent 依使用情境確認要製作圖片式簡報、網頁式簡報或 PPTX。

## 7 個專案 Skills

| Skill | 使用時機 |
| --- | --- |
| `design-presentations` | 尚未決定輸出格式，或需要建立／檢查 Art Direction、構圖系統與跨頁視覺節奏。 |
| `slide-outline-planner` | 只需要簡報大綱、逐頁 Content Plan、講稿或 Layout 對應，尚未要產出成品。 |
| `html-pattern-slide` | 製作、修改或 QA 一般可編輯 HTML 簡報；圖片不是主要版面結構。 |
| `html-image-slide` | 新建以照片、插圖、半版圖或滿版圖為主要構圖的可編輯 HTML 簡報。 |
| `slide-background-image` | 已經有可編輯 HTML，只需要逐頁新增、替換或檢查圖片背景。 |
| `ppt-builder` | 製作原生文字、形狀、母片與版面可編輯的 PowerPoint（PPTX）。 |
| `generate-image-slide` | 製作 Image2 圖片式投影片，或產生本專案使用的七段式 assembled YAML。 |

## 能力邊界

- Image2 正式生圖需要外部模型影像 provider；套件不包含模型或 API token。
- 原生 PPTX 需要相容的 presentation runtime；PowerPoint 桌面版是額外的原生渲染 QA 能力。
- HTML、PPTX 與 Image2 共用 Theme／Layout 語意，但不共用同一個 runtime payload。
- v0.2.0 Public DEMO 不代表完整 HTML／PPTX 視覺矩陣、macOS 或所有外部能力都已全面驗收。

## 專案結構

| 路徑 | 內容 |
| --- | --- |
| `.agents/skills/` | 7 支專案 Skills 的正式來源。 |
| `CLAUDE.md` | Claude Code 的專案入口與 Skill 路由。 |
| `prompt_system/` | Theme、Layout、Preset 與 renderer adapters。 |
| `src/html-editor/` | 可編輯 HTML 的共用 editor source。 |
| `scripts/` | 簡報產製、QA 與 portable package 工具。 |
| `demos/html/` | GitHub Pages 與 portable package 使用的公開案例。 |
| `artifacts/` | 隨版本保留的 runtime、Gallery 與 QA 證據。 |
| `workspace/` | 個人簡報的工作資料與交付成品。 |

不要把個人輸出寫回 `prompt_system/`、`references/`、`.agents/skills/` 或隨包附帶的 `artifacts/`。

## 驗證與維護

```powershell
python scripts/portable_manifest.py --check
npm run audit --silent
```

`PASS` 只代表對應的自動化 Gate 通過；外部能力或尚未執行的人工視覺 QA 仍會保留為 `WARN`。

框架開發、Skill 維護與發布流程請讀 [CONTRIBUTING.md](CONTRIBUTING.md)、[AGENTS.md](AGENTS.md) 與 [SECURITY.md](SECURITY.md)。

## License

First-party source and demo material are licensed under the [MIT License](LICENSE), copyright Slide Firm. Third-party software and assets retain their own notices in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and adjacent license files.
