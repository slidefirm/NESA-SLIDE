# Prompt System — 交接文件
> 給 Codex 或下一位協作者的說明

> **歷史快照，不能當目前操作手冊。** 本文保留早期設計背景與待辦，裡面的 Theme／Layout
> 數量、目錄、schema、優先順序與部署項目已經過時。現在的 source of truth 是
> `prompt_system/AGENTS.md`、`prompt_system/README.md`、`references/renderer-adapter-contract.md`
> 與各 renderer 的 repo-local Skill。需要目前數量時請直接盤點 YAML 或執行
> `scripts/audit.ps1`；不要依本文的「4 Themes」「3 Layouts」或舊待辦做修改。

---

## 這個系統在做什麼

把一張投影片的「視覺設計」拆成媒介無關的 theme/layout core，再透過 renderer
adapters 投影成 Image2、HTML、PPTX 各自需要的輸入；圖片生成 prompt 只是其中一種
downstream 輸出。

目前目標：
- 先整理好 YAML 核心架構
- 讓 `PPTX / 圖片簡報 / HTML` 共用 theme/layout core 語意，但各自使用適合媒介的 manifest
- 現階段仍保留 image generation prompt 的組裝模板，但它不再是唯一目標

第三條輸出路線已定義為 `PPTX`：由 `.agents/skills/ppt-builder/` 將 Art Direction、Theme／Layout core、PPTX adapter、content manifest 與可選的已編輯 HTML 轉成可編輯 PowerPoint，並建立 theme master、layout family 與 placeholders。assembled YAML 只可作為可選內容來源，不是 PPTX 的必要 runtime payload。詳細規則見 `references/pptx-generation-rules.md`。

三 renderer adapters 已由 `scripts/generate_renderer_adapters.py` 自動補齊；契約見
`references/renderer-adapter-contract.md`。修改正式 theme/layout 後必須重跑產生器並執行
`--check`，不得手動複製 core 色碼或 slot 座標。

---

## 系統架構

```
prompt_system/
├── themes/          ← 共通視覺規則；內含 2A 與 2B
├── layouts/         ← 版面骨架定義
├── design_elements/ ← reusable 構件語彙
├── specs/           ← 新的 YAML-first 核心模板
├── assembly_template.txt  ← 圖片生成用組裝公式
└── analysis/        ← 參考資料（從真實簡報分析出來的）
```

### 4 層說明

| 層 | 目錄 | 負責什麼 | 範例 |
|----|------|----------|------|
| Layer 1 | layouts/ | 版面骨架：slot 位置、對齊規則、視覺平衡 | `chapter-opener.yaml` |
| Layer 2A | themes/ 的 `visual_base` | 視覺基底：背景色、字體、情緒 | `dark-circuit.yaml` |
| Layer 2B | themes/ 的 `decoration_system` / `decoration_vocabulary` | 裝飾詞彙：可用的裝飾元素清單 | 每個 theme 的 vocabulary |
| Layer 2.5 | design_elements/ | 可重用構件：節點卡、箭頭、stage chip、avatar frame | `observed_elements.catalog.yaml` |
| Layer 3 | dynamic content contract | 每次組裝時決定 `content` 欄位與文字 | 不留存靜態檔 |
| Core Spec | specs/ | 跨媒介 slide spec 模板 | `slide.spec.template.yaml` |
| Validation | specs/ | 輸出後檢查清單與結果欄位 | `validation.checklist.template.yaml` |

### 重要規則

- Theme 和 Layout 完全獨立，任意組合
- `theme` 是大集合，`2A` 與 `2B` 都屬於 theme 的子層
- 2B 的裝飾元素從 vocabulary 挑選，不預先指定到特定版型
- 所有主要內容（標題、正文、圖表、標籤）必須在 10%–90% 範圍內
- 裝飾元素可使用最外側 10% 邊界區域，但不能侵犯主內容
- 對齊與視覺重量屬於必要規則，不是附加備註
- 標題系統必須明確宣告是 `centered_header` 或 `content_anchored_left`
- 若頁面是文字主導 + 側邊插圖，插圖只能是 supporting visual，不可壓縮文字主內容空間
- image prompt 轉譯時不可直接輸出 `x=...`、`y=...` 這類機械座標字串
- 檢查層目前先建成規格，不代表已實作自動檢測器

---

## 現有檔案清單

### Themes（4 個）
| 檔案 | 對應簡報 | 視覺特徵 |
|------|----------|----------|
| `dark-circuit.yaml` | 01 Claude Code | 黑底+橘色強調+電路板線條 |
| `brand-editorial.yaml` | 02 排版實戰班 | 金褐色+深灰+品牌排版風 |
| `corporate-blue.yaml` | 03 丹尼 Day1 | 白底+深藍+旋轉菱形點陣 |
| `teal-tech.yaml` | 04 丹尼 Day2 | 淺灰底+靛藍綠+電路端點+散點 |

### Themes（2026-06-12 外部模板新增）
| 檔案 | 來源模板 | 視覺特徵 |
|------|----------|----------|
| `grainy-editorial.yaml` | Brown Minimalist / Minimalist Business | 紙感顆粒、出版風、暖米白 |
| `brutal-grunge.yaml` | Brutal Grunge Portfolio | 深灰粗獷、黑白攝影、框景 |
| `soft-organic-education.yaml` | Elegant Education / elegant-workplan | 柔和有機塊、教育工具包感 |
| `clinical-report.yaml` | Formal Case Report / Vocational Guidance | 白底藍灰、正式報告 |
| `workshop-human.yaml` | Mental Health Workshop | 人本攝影、工作坊粗字 |
| `lavender-media-kit.yaml` | Professional Media Kit | 淡紫品牌包、中心構圖 |
| `festive-patterned.yaml` | Stuttgarter Weindorf XL | 黑奶油金、節慶圖騰 |
| `clean-tech-business.yaml` | Technology Company Business Plan | 白底科技商務、扁平插圖 |
| `paper-collage-vintage.yaml` | Vintage Torn Paper Agency | 撕紙拼貼、懷舊 agency |
| `warm-editorial-portfolio.yaml` | Gamma / Slidesgo quote & portfolio observation | 暖白 grain、編輯作品集感 |

### Layouts（3 個）
| 檔案 | 中文名 | 用途 |
|------|--------|------|
| `hero-fullbleed.yaml` | 全版底圖封面 | 封面、開場 |
| `chapter-opener.yaml` | 章節過場 | 每章節開頭 |
| `matrix-4quadrant.yaml` | 四象限矩陣 | 比較/分類頁 |

### Layouts（2026-06-12 外部模板新增）
| 檔案 | 中文名 | 用途 |
|------|--------|------|
| `cover-photo-frame.yaml` | 框景封面 | 作品集/活動/agency 封面 |
| `quote-focus.yaml` | 金句聚焦 | 問句頁、金句頁、節奏頁 |
| `gantt-roadmap.yaml` | 時程路線圖 | 專案規劃、甘特、roadmap |
| `team-roster.yaml` | 團隊名單 | 多人介紹、about us |
| `swot-quadrant.yaml` | SWOT 四象限 | 明確語意的四格比較 |
| `customer-journey.yaml` | 客戶旅程 | 使用者流程、campaign path、journey map |
| `org-structure.yaml` | 組織結構圖 | 組織層級、部門 ownership、reporting lines |
| `process-flow.yaml` | 流程步驟圖 | SOP、方法論、工作流程、flow explanation |
| `kpi-scorecards.yaml` | KPI 指標卡 | 週報、月報、summary metrics |
| `dashboard-overview.yaml` | Dashboard 總覽 | analytics、QBR、review 頁 |
| `comparison-table.yaml` | 比較表格 | benchmark、pricing、feature comparison |
| `problem-solution-bridge.yaml` | 問題解法橋接 | 現況痛點到解法提案 |
| `recommendation-stack.yaml` | 建議堆疊 | recommendation、proposal summary |
| `strategic-priorities.yaml` | 策略優先級 | next steps、focus areas、priority ranking |
| `case-study-proof.yaml` | 案例證據頁 | challenge / solution / proof |
| `findings-cluster.yaml` | 發現群組頁 | research findings、insight synthesis |
| `annual-highlights.yaml` | 年度亮點回顧 | annual report、impact recap |
| `onboarding-path.yaml` | Onboarding 路徑 | 30/60/90、adoption、new hire path |
| `workshop-run-of-show.yaml` | 工作坊節奏表 | facilitation agenda、session flow |
| `learning-module.yaml` | 學習模組頁 | training / education 單元 |
| `media-kit-overview.yaml` | Media Kit 總覽 | partner-facing media kit、brand deck |
| `campaign-architecture.yaml` | Campaign 架構頁 | audience、tactics、goal、KPI |
| `event-recap-storyboard.yaml` | Event Recap 故事板 | 活動亮點、成效與回饋回顧 |
| `competitive-landscape.yaml` | 競爭定位圖 | pitch deck、market positioning、battlecard |
| `maturity-ladder.yaml` | 成熟度階梯 | AI maturity、digital transformation、adoption maturity |
| `go-to-market-motion.yaml` | GTM 動作系統 | product launch、growth strategy、go-to-market |
| `proposal-value-stack.yaml` | 提案價值堆疊 | sales proposal、service proposal、solution deck |
| `pricing-packages.yaml` | 方案定價欄 | SaaS pricing、service packages、tier comparison |
| `battlecard-compare.yaml` | Battlecard 對比頁 | sales enablement、why-us comparison、objection handling |
| `account-plan-brief.yaml` | 帳戶規劃摘要 | strategic account planning、customer plan |
| `pipeline-health-review.yaml` | 漏斗健康檢視 | sales pipeline review、forecast health |
| `business-review-rhythm.yaml` | 商務回顧節奏頁 | QBR、EBR、executive review |
| `customer-success-plan.yaml` | Customer Success 計畫圖 | shared success plan、implementation-to-renewal blueprint |
| `adoption-journey.yaml` | Adoption 推進旅程 | product adoption、post-go-live enablement |
| `renewal-readiness.yaml` | 續約準備度 | renewal planning、retention review、expansion readiness |
| `implementation-rollout-map.yaml` | 導入 rollout 地圖 | software rollout、deployment plan、implementation execution |
| `customer-education-track.yaml` | 客戶教育路徑 | academy roadmap、learning progression、certification path |
| `partner-enablement-kit.yaml` | 夥伴啟用工具包 | partner onboarding、channel enablement、reseller activation |
| `field-enablement-readiness.yaml` | Field Enablement 準備度 | field readiness、sales kickoff、partner field activation |
| `certification-ladder.yaml` | 認證階梯 | certification path、level progression、qualification |
| `community-learning-loop.yaml` | 社群學習循環 | community of practice、peer learning、recurring sessions |
| `advocacy-program-map.yaml` | 倡議計畫地圖 | evangelism、advocacy initiative、outreach program |
| `ambassador-journey.yaml` | Ambassador 成長旅程 | ambassador program、champion development、volunteer advocate |
| `community-ops-rhythm.yaml` | 社群營運節奏 | community operations、engagement cadence、practice rhythm |
| `ecosystem-relations-map.yaml` | 生態系關係圖 | ecosystem strategy、stakeholder map、community collaboration network |
| `ambassador-metrics-board.yaml` | Ambassador 成效板 | ambassador review、advocacy metrics、program scorecard |
| `volunteer-ops-cadence.yaml` | 志工營運節奏 | volunteer operations、support cadence、coverage planning |
| `membership-value-journey.yaml` | 會員價值旅程 | membership lifecycle、community progression、belonging journey |
| `donor-engagement-lifecycle.yaml` | 捐助互動生命週期 | donor lifecycle、stewardship flow、fundraising relationship |
| `governance-committee-model.yaml` | 治理委員會模型 | governance operating model、board committee、decision framework |
| `investor-update-brief.yaml` | Investor Update 摘要頁 | investor update、board review、executive brief、quarter snapshot |
| `team-bulletin.yaml` | Team Bulletin 佈告頁 | internal digest、team update、newsletter、round-up |
| `annual-meeting-brief.yaml` | Annual Meeting 摘要頁 | AGM、association annual meeting、member-facing governance recap |
| `fundraising-campaign-brief.yaml` | Fundraising Campaign 摘要頁 | fundraising campaign、charity gala、donor ask、sponsorship brief |
| `association-member-update.yaml` | Association Member Update | member digest、committee round-up、association update、program recap |

### Schemas（與 layouts 一對一對應，已隨新增版型同步擴充）

### Design Elements
| 檔案 | 用途 |
|------|------|
| `observed_elements.catalog.yaml` | 把 stage chip、connector、reporting line、node card、avatar frame 等可重用構件正式命名 |

### 2026-06-12 第十七輪擴充摘要

- analysis
  - `analysis/web_presentation_observation_round17_20260612.md`
- layouts
  - `investor-update-brief`
  - `team-bulletin`
- themes
  - `boardroom-premium`
- design elements
  - `headline-metric-band`
  - `variance-flag`
  - `runway-chip`
  - `board-ask-card`
  - `capital-allocation-bar`
  - `confidence-arrow`
  - `bulletin-stamp`
  - `issue-date-tag`
  - `update-divider`
  - `spotlight-frame`
  - `swatch-stack`
  - `logo-safezone-box`
  - `voice-pillar-chip`

### 2026-06-12 第十八輪擴充摘要

- analysis
  - `analysis/web_presentation_observation_round18_20260612.md`
- layouts
  - `annual-meeting-brief`
  - `fundraising-campaign-brief`
  - `association-member-update`
- themes
  - `community-fundraising`
- design elements
  - `attendance-chip`
  - `motion-card`
  - `agenda-ribbon`
  - `committee-update-tile`
  - `event-calendar-strip`
  - `giving-thermometer`
  - `donor-tier-band`
  - `impact-story-callout`
  - `impact-proof-badge`
  - `pledge-cta`

---

## 目前的兩層輸出

### A. 核心 slide spec（現在優先）

優先維護 `specs/` 所定義的 YAML 核心結構，目的是先建立一份 renderer 無關的 page spec。

這份 spec 至少應包含：

- `theme_ref`
- `layout`
- `design_elements`
- `content`
- `content_safe_zone`
- `composition_rules`
- `decoration_application`
- `validation`

### B. 圖片生成 prompt（舊流程仍保留）

當需要圖片簡報時，再把核心 spec 轉成 7 段 prompt。

## 組裝流程（7 段公式）

詳見 `assembly_template.txt`，摘要如下：

```
[1] 頁面類型+情緒（一句話）
[2] 視覺基底（2A visual_base → 自然語言）
[3] 角落裝飾（2B decoration_vocabulary → 選取後填入各角落）
[4] 版型說明（layout 空間描述）
[5] 內容（dynamic content contract 欄位填好）
[6] 安全區約束（固定句，每次都貼）
[7] 結尾設計意圖（theme.closing_statement）
```

---

## 待完成項目

### 高優先

- [ ] **01/02/03 設計手法分析**：Sonnet agent 被中途停止，尚未產出完整報告
  - 04 的分析已存 `analysis/04_design_analysis.md`，可參考格式
  - 需要補跑（02 有 399 張，建議分段或用 haiku）

- [ ] **更新 2B decoration_vocabulary**：目前 themes 的 vocabulary 基於 haiku 抽樣分析
  - 等 01/02/03 完整分析完成後，對照更新各 theme 的 vocabulary 描述

### 中優先

- [ ] **新增 layouts**：從 04 分析發現的真實版型尚未建檔
  - `title-center`（全版大字/金句頁）
  - `grid-cards`（上標題+下方卡片網格）
  - `split-comparison`（左右對比）
  - `task-panel`（實作練習頁，深底+白卡+計時器）
  - `diagram-flow`（流程圖頁）

- [ ] **驗證 dynamic content contract**：確認新 layouts 可由 AI 依任務即時決定 `content` 欄位

- [ ] **assembly_template 測試**：用現有 4 個 theme × 4 個 layout 各組裝一個完整 prompt 驗證

### 低優先

- [ ] **layout_catalog.html 更新**：網站展示版型，部署到 Cloudflare Pages
- [ ] **Downloads 模板第二輪深挖**：目前已分析封面與前 3 張代表頁，之後可再抽中段內容頁與圖表頁
- [ ] **網路模板後續觀察**：目前正式庫已涵蓋 gantt / team / swot / journey / org / process flow / KPI / dashboard / table / problem-solution / recommendation / priorities / case-study / findings / annual-highlights / onboarding / workshop / learning-module / media-kit / campaign / event-recap / competitive-landscape / maturity-ladder / go-to-market-motion / proposal-value-stack / pricing-packages / battlecard-compare / account-plan-brief / pipeline-health-review / business-review-rhythm / customer-success-plan / adoption-journey / renewal-readiness / implementation-rollout-map / customer-education-track / partner-enablement-kit / field-enablement-readiness / certification-ladder / community-learning-loop / advocacy-program-map / ambassador-journey / community-ops-rhythm / ecosystem-relations-map / ambassador-metrics-board / volunteer-ops-cadence / membership-value-journey / donor-engagement-lifecycle / governance-committee-model / investor-update-brief / team-bulletin / annual-meeting-brief / fundraising-campaign-brief / association-member-update；之後可再補 Canva 與更多 public affairs / volunteer recruitment / advocacy fundraising 類版型

---

## 已知規則與例外

1. `hero-fullbleed` 版型不使用 [3] 角落裝飾，改用 theme 的 overlay/gradient 描述
2. `dark-circuit` theme 的 `dot-grid-bg` 裝飾永遠存在（density: always），不需在 [3] 列出
3. 版型的 `safe_area` 和裝飾的 10% margin zone 是同一個概念的兩種描述方式

---

## 分析資料來源

```
jpg輸出/
├── 01_Claude code入門指南/   162 張
├── 02_排版實戰班/            399 張
├── 03_丹尼Day1/              159 張
└── 04_丹尼Day2/              173 張
```

所有 theme YAML 均基於對這 4 份真實簡報的視覺分析產出。
