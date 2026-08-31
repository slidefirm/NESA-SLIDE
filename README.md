# NESA-SLIDE

NESA-SLIDE 是由 Slide Firm 維護的開源 AI 簡報製作系統。它把 Story、Art Direction、Theme、Layout 與 renderer adapter 分成可檢查的層次，分別支援 Image2 圖片、可編輯 HTML 與原生可編輯 PPTX 的工作流程。

> NESA-SLIDE is an open-source AI presentation production system maintained by Slide Firm. It keeps Story, Art Direction, Theme, Layout, and renderer adapters as separate, inspectable layers for Image2, editable HTML, and native-editable PPTX workflows.

[線上體驗 HTML DEMO](https://slidefirm.github.io/NESA-SLIDE/) · [下載 v0.2.0](https://github.com/slidefirm/NESA-SLIDE/releases/tag/v0.2.0) · [版本紀錄](CHANGELOG.md)

## v0.2.0 Public DEMO

- 36 個 Theme、75 個 Layout、43 個 HTML style cases。
- 7 支 repository-local Skills：`design-presentations`、`slide-outline-planner`、`generate-image-slide`、`html-image-slide`、`html-pattern-slide`、`ppt-builder`、`slide-background-image`。
- 333 個 renderer adapters，以及 36×75 的 renderer registry。
- 一份 8 頁、可導覽與可編輯文字的 HTML DEMO。
- 可重現的 portable ZIP、來源資訊與 SHA-256 完整性帳本。

這是公開 DEMO 的正式版本，不代表所有外部能力都已全面驗收。完整 HTML/PPTX 視覺矩陣、Image2 正式生圖、macOS 與原生 PowerPoint 渲染仍受外部環境或人工 QA 限制。

## 三步驟開始使用

### 1. 準備環境

- Windows 10/11
- CPython 3.13+
- Node.js 22+
- Chrome、Edge 或 Chromium

```powershell
python -m pip install -r requirements.txt
npm ci --ignore-scripts
python CHECK_SYSTEM.py
```

### 2. 開啟 DEMO

下載 portable ZIP 後，雙擊 `OPEN_DEMO.cmd`；也可以直接開啟：

```text
demos/html/demo-deck.html
```

### 3. 產生一份新 HTML 簡報

```powershell
python scripts/render_randomized_html_demo.py --output workspace/my-deck.html --theme brand-editorial
```

所有個人輸出都應放在 `workspace/`。不要把輸出寫回 `prompt_system/`、`references/`、`.agents/skills/` 或隨包附帶的 `artifacts/`。

## 專案結構

- `prompt_system/`：Theme、Layout、Preset 與 renderer adapter 的正式規格。
- `.agents/skills/`：7 支 Skill 的唯一原稿。
- `src/html-editor/`：HTML 編輯器的 canonical source。
- `scripts/`：產生、檢查、QA 與 portable package 工具。
- `demos/html/`：GitHub Pages 與 portable package 使用的公開 DEMO。
- `artifacts/`：隨版本保留的 runtime、Gallery 與 QA 證據；不是使用者工作區。
- `workspace/`：本機產出位置；Git 只保留說明檔。

## 能力邊界

- Image2 正式生圖需要外部模型影像 provider；系統不內附模型或 API token。
- 原生 PPTX 建置需要支援的 Codex presentation runtime；PowerPoint 桌面版是額外的原生渲染 QA 能力。
- GitHub Pages 是靜態展示：可以瀏覽、編輯與下載，但不能把修改直接寫回 GitHub。
- HTML、PPTX 與 Image2 共用 Theme／Layout 語意，但不共用同一個 runtime payload。

完整契約請讀 `AGENTS.md`、`references/presentation-production-contract.md` 與各 Skill 的 `SKILL.md`。

## 驗證

```powershell
python scripts/portable_manifest.py --check
npm run audit --silent
python scripts/build_portable_package.py --output ..\NESA-SLIDE-v0.2.0-portable --version 0.2.0 --zip ..\NESA-SLIDE-v0.2.0-portable.zip
```

`PASS` 代表對應的自動化 Gate 通過；環境外部能力與尚未產生的完整視覺矩陣會保留為 `WARN`，不得改稱全面產品驗收。

## License

First-party source and demo material are licensed under the [MIT License](LICENSE), copyright Slide Firm. Third-party software and assets retain their own notices in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and adjacent license files.

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
