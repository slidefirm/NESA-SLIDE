# NESA-SLIDE

**把這個 GitHub 連結交給 Codex 或 Claude Code，就可以開始做簡報。**

> Give this repository to Codex or Claude Code. The agent clones the workspace, prepares what it needs, and creates the presentation.

## 唯一使用方式

把下面這句貼給 Codex 或 Claude Code，再把主題換成你要的內容：

```text
請 clone https://github.com/slidefirm/NESA-SLIDE，進入專案後幫我做一份關於「我的主題」的簡報。
```

就這樣。你不需要先：

- 下載或解壓 ZIP；
- 安裝 NESA-SLIDE plugin；
- 自己執行 npm／Python 安裝命令；
- 選擇 renderer、manifest 或內部工作流程。

Agent 會自行 clone、檢查環境、使用 `create-presentation` Skill，並把成品放在 `workspace/<project-id>/`。

## 可以要求的格式

- **可編輯 HTML**：預設格式，可編輯文字與物件，也能下載 HTML。
- **可編輯 PPTX**：使用原生文字與形狀；需要相容的 presentation runtime。
- **Image2 圖片簡報**：需要模型影像能力。
- **含圖片的 HTML**：由 Agent 規劃圖片，再組成可編輯 HTML。

直接在同一句需求中指定即可，例如：

```text
請 clone https://github.com/slidefirm/NESA-SLIDE，做一份 10 頁、給主管看的 AI 導入提案，交付可編輯 HTML。
```

## 線上 DEMO

[開啟 8 頁可編輯 HTML DEMO](https://slidefirm.github.io/NESA-SLIDE/)

DEMO 只是讓你先看編輯與播放介面；正式使用仍是把 GitHub repo 交給 Agent。

## Agent discovery

- Codex：`.agents/skills/create-presentation`
- Claude Code：`.claude/skills/create-presentation`

兩邊使用同一份工作流程並由 CI 驗證內容一致。Theme、Layout、renderer 與 QA 都由 Skill 內部處理，不需要使用者先理解。

## 維護者

框架開發、Skill 同步與發布流程請讀 [CONTRIBUTING.md](CONTRIBUTING.md) 與 [AGENTS.md](AGENTS.md)。這些不是一般使用者的開始步驟。

## License

MIT © Slide Firm. Third-party notices are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
