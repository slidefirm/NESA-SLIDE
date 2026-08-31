# NESA-SLIDE

**直接交給 Codex 或 Claude Code 的 AI 簡報工作區。** Agent clone 後會自動讀到專案 Skills，依你的內容選擇 Theme、Layout 與輸出格式，完成簡報與 QA。

> An agent-native presentation workspace for Codex and Claude Code. Clone it, describe the deck, and let the project Skills handle planning, design, rendering, and verification.

[線上 HTML DEMO](https://slidefirm.github.io/NESA-SLIDE/) · [GitHub Releases](https://github.com/slidefirm/NESA-SLIDE/releases) · [MIT License](LICENSE)

## 直接交給 Codex / Claude Code

把下面這句貼給 Agent，再把主題換成你要的內容：

```text
請 clone https://github.com/slidefirm/NESA-SLIDE，進入專案後幫我做一份關於「我的主題」的簡報。
```

Agent 會：

1. clone 並進入 NESA-SLIDE；
2. 自動使用 `create-presentation` Skill；
3. 必要時執行 `npm run setup`；
4. 把成品寫入 `workspace/<project-id>/`；
5. 驗證後交付可開啟的 HTML、PPTX 或圖片。

Codex 由 `.agents/skills/` 發現 Skills；Claude Code 由 `.claude/skills/` 發現同一組鏡射。兩邊的 `create-presentation` 都是唯一前門。

## 自己 clone

```bash
git clone https://github.com/slidefirm/NESA-SLIDE
cd NESA-SLIDE
npm run setup
```

然後直接對 Agent 說：

```text
幫我做一份 10 頁、給主管看的 AI 導入提案，交付可編輯 HTML。
```

## 常用命令

| Command | 用途 |
| --- | --- |
| `npm run setup` | 安裝 Node／Python 專案依賴並檢查 Agent Skills。 |
| `npm run doctor` | 快速檢查 Python、Node、瀏覽器與外部能力。 |
| `npm run demo` | 在 `http://127.0.0.1:7394/` 開啟內附 HTML DEMO。 |
| `npm run dev` | `demo` 的別名，方便熟悉 Open-Slide 類工作流的使用者。 |
| `npm run audit` | 執行目前平台可用的專案 Gate。 |
| `npm run check:skills` | 確認 Codex 與 Claude Code 的 Skills 完全一致。 |

## 輸出格式

- **Editable HTML** — 預設格式；可編輯文字、物件、下載 HTML，並支援瀏覽器 PPTX 匯出。
- **Native-editable PPTX** — 使用原生文字與形狀；需要相容的 presentation runtime。
- **Image2 slides** — 依七段式 YAML 正式生圖；需要模型影像 provider。

三種格式共用 Theme／Layout 語意，但各自使用合適的 renderer，不用整頁截圖冒充可編輯成品。

## 工作區結構

- `.agents/skills/`：Codex 使用的 canonical Skills。
- `.claude/skills/`：由 canonical Skills 產生並提交的 Claude Code mirror。
- `prompt_system/`：36 Themes、75 Layouts 與 renderer adapters。
- `workspace/`：你的所有簡報成品；框架檔案不會和輸出混在一起。
- `demos/html/`：可直接瀏覽的 8 頁可編輯 DEMO。

## 支援與能力邊界

主要流程使用 Node.js 22+ 與 Python 3.13+，設計為可在 macOS 與 Windows 的 coding agent 工作區執行。Windows 已完成實機驗證；macOS 路徑與工具選擇已納入，但仍需要真機驗收。

Image2、原生 PPTX 建置與 PowerPoint 原生渲染屬外部能力。缺少其中一項時，Agent 應清楚標示受影響的輸出，不會把規格檢查冒充完成成品。

## 更新 Skills

`.agents/skills/` 是唯一原稿。修改後執行：

```bash
npm run sync:skills
npm run check:skills
```

## License

First-party source and demos are licensed under the [MIT License](LICENSE), copyright Slide Firm. Third-party notices are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
