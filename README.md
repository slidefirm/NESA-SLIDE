# NESA-SLIDE

**給 Codex 與 Claude Code 使用的開源 AI 簡報製作系統。**

NESA-SLIDE 把內容規劃、視覺方向、版面設計與輸出流程整理成專案 Skills，能製作 Image2 圖片式簡報、一般可編輯 HTML、含圖片的可編輯 HTML，以及原生可編輯 PPTX。

## 安裝方式

先把下面這段提示詞交給 Codex 或 Claude Code：

```text
請將 NESA-SLIDE 準備成可在本機開啟的專案。

Repository：
https://github.com/slidefirm/NESA-SLIDE

請將 repository clone 到適合長期保存專案的位置。若無法確定下載位置，先詢問我；若已有同名資料夾，請勿覆寫或刪除，先確認它是否為同一個 repository。

Clone 完成後，請確認專案根目錄包含：

- README.md
- AGENTS.md
- .agents/skills/

最後請告訴我：

1. Clone 是否成功
2. NESA-SLIDE 專案資料夾的完整絕對路徑
3. 接下來應在 Codex 或 Claude Code 開啟哪個資料夾
```

## 簡報製作方式

以下四種成品各有對應的 Skill。你可以直接指定 Skill，也可以把範例提示詞貼給 Agent。

### 純圖片簡報

Image2 將每一頁製作成完整的 16:9 圖片，適合重視視覺完整度、不需要個別編輯頁面物件的場合。

#### [DEMO1：VoltGo City 新款電動機車發表會](https://slidefirm.github.io/NESA-SLIDE/image2/voltgo-city/voltgo-city-image2.pdf)

![VoltGo City 新款電動機車發表會六頁總覽](demos/readme-montages/image2/voltgo-city-3x2.jpg)

#### [DEMO2：2027 港灣城市爵士音樂節招商提案](https://slidefirm.github.io/NESA-SLIDE/image2/jazz-festival-2027/jazz-festival-2027-image2.pdf)

![2027 港灣城市爵士音樂節招商提案六頁總覽](demos/readme-montages/image2/jazz-festival-2027-3x2.jpg)

#### [DEMO3：珊瑚礁復育年度募款簡報](https://slidefirm.github.io/NESA-SLIDE/image2/coral-reef-annual/coral-reef-annual-image2.pdf)

![珊瑚礁復育年度募款簡報六頁總覽](demos/readme-montages/image2/coral-reef-annual-3x2.jpg)

使用 Skill：[`generate-image-slide`](.agents/skills/generate-image-slide/SKILL.md)

```text
請先規劃一份關於「我的主題」的 10 頁簡報，再使用 generate-image-slide Skill 逐頁產生 Image2 圖片式投影片。
```

### 純 HTML 簡報

以下三份 Demo 都是 8 頁、可直接在瀏覽器播放與編輯的完整簡報。

#### [DEMO1：新任店長內訓簡報](https://slidefirm.github.io/NESA-SLIDE/store-manager-30-60-90/store-manager-30-60-90.html)

![新任店長內訓簡報六頁總覽](demos/readme-montages/html-pattern/store-manager-30-60-90-3x2.jpg)

#### [DEMO2：社區大樓防災說明會](https://slidefirm.github.io/NESA-SLIDE/building-disaster-48h/building-disaster-48h.html)

![社區大樓防災說明會六頁總覽](demos/readme-montages/html-pattern/building-disaster-48h-3x2.jpg)

#### [DEMO3：舊車站再利用提案](https://slidefirm.github.io/NESA-SLIDE/station-market-weekend/station-market-weekend.html)

![舊車站再利用提案六頁總覽](demos/readme-montages/html-pattern/station-market-weekend-3x2.jpg)

使用 Skill：[`html-pattern-slide`](.agents/skills/html-pattern-slide/SKILL.md)

```text
請使用 html-pattern-slide Skill，製作一份關於「我的主題」的 10 頁可編輯 HTML 簡報。
```

### 圖片背景 HTML 簡報

以下三份 Demo 以照片支撐實際提案內容，同時保留可編輯文字、物件、播放與 HTML 儲存功能。

#### [DEMO1：台東海岸旅宿品牌提案](https://slidefirm.github.io/NESA-SLIDE/taitung-coast-lodge/demo.html)

![台東海岸旅宿品牌提案六頁總覽](demos/readme-montages/html-image/taitung-coast-lodge-3x2.jpg)

#### [DEMO2：流浪動物認養日活動企劃](https://slidefirm.github.io/NESA-SLIDE/adoption-day/demo.html)

![流浪動物認養日活動企劃六頁總覽](demos/readme-montages/html-image/adoption-day-3x2.jpg)

#### [DEMO3：春季草莓烘焙新品上市計畫](https://slidefirm.github.io/NESA-SLIDE/spring-strawberry-launch/demo.html)

![春季草莓烘焙新品上市計畫六頁總覽](demos/readme-montages/html-image/spring-strawberry-launch-3x2.jpg)

使用 Skill：[`html-image-slide`](.agents/skills/html-image-slide/SKILL.md)

```text
請使用 html-image-slide Skill，製作一份關於「我的主題」的 10 頁可編輯 HTML 簡報，讓照片或插圖成為主要構圖，並保留文字與物件的可編輯性。
```

### PPTX 簡報

以下三份 Demo 都是 8 頁、保留原生文字、形狀、圖表與版面的可編輯 PowerPoint。

#### [DEMO1：FlowPilot 2026 Q2 營運回顧](demos/pptx/flowpilot-2026-q2-clean.pptx)

![FlowPilot 2026 Q2 營運回顧六頁總覽](demos/readme-montages/pptx/flowpilot-2026-q2-clean-3x2.jpg)

#### [DEMO2：區域醫院門診等候時間改善提案](demos/pptx/regional-hospital-waiting-pilot-clean.pptx)

![區域醫院門診等候時間改善提案六頁總覽](demos/readme-montages/pptx/regional-hospital-waiting-pilot-clean-3x2.jpg)

#### [DEMO3：消費電子製造商供應商雙源策略](demos/pptx/consumer-electronics-dual-source-clean.pptx)

![消費電子製造商供應商雙源策略六頁總覽](demos/readme-montages/pptx/consumer-electronics-dual-source-clean-3x2.jpg)

使用 Skill：[`ppt-builder`](.agents/skills/ppt-builder/SKILL.md)

```text
請使用 ppt-builder Skill，製作一份關於「我的主題」的 10 頁原生可編輯 PPTX。文字、形狀與版面必須能在 PowerPoint 中繼續編輯，不要把整頁做成圖片。
```

## 其他 Skills

| Skill | 什麼時候使用 |
| --- | --- |
| [`design-presentations`](.agents/skills/design-presentations/SKILL.md) | 還沒決定輸出格式，或需要先規劃整份簡報的視覺方向與跨頁節奏。 |
| [`slide-outline-planner`](.agents/skills/slide-outline-planner/SKILL.md) | 只需要大綱、逐頁內容、講稿或版面建議，還不需要產出成品。 |
| [`slide-background-image`](.agents/skills/slide-background-image/SKILL.md) | 已經有 HTML，只需要新增、替換或檢查逐頁圖片背景。 |

## License

本專案採用 [MIT License](LICENSE) 開源。
