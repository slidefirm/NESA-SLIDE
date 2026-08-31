# Layouts Library

每個 Layout Core 都必須宣告 `media_requirement`：

- `no-image`：文字、表格、流程、資料結構或原生語意圖示即可完成；`icon-grid-6` 屬於此類。
- `with-image`：構圖成立需要照片、插圖、地圖或人物等真實視覺素材。

這個欄位只描述 Layout 的素材需求；是否可被選用，仍由本次簡報的素材策略決定。

這份清單整理目前 `prompt_system/layouts/` 的版型骨架。

## 既有 layouts

- `hero-fullbleed`
- `chapter-opener`
- `matrix-4quadrant`
- `title-center`
- `grid-cards`
- `split-comparison`

## 2026-06-12 新增 layouts（來自 Downloads 模板分析）

- `cover-photo-frame`
  - 適合作品集 / 活動 / agency 類封面
  - 典型形式：左側大標 + 右側被框起來的照片窗口

- `quote-focus`
  - 適合金句頁、提問頁、呼吸頁
  - 典型形式：一句大字主導全頁，配極少量 attribution

## 2026-06-12 網路觀察新增 layouts

- `gantt-roadmap`
  - 來自 Beautiful.ai `Gantt Chart` 與 roadmap 類模板
  - 適合專案規劃、產品路線圖、時程安排

- `team-roster`
  - 來自 Beautiful.ai / Canva 的 team / about us 類模板
  - 適合多人介紹，不等於單一人物 profile

- `swot-quadrant`
  - 來自 Beautiful.ai `SWOT`
  - 比泛四象限更明確的語意比較頁

## 2026-06-12 網路觀察第二輪新增 layouts

- `customer-journey`
  - 來自 Beautiful.ai 高頻 `Journey`
  - 適合客戶旅程、使用者流程、campaign path

- `org-structure`
  - 來自 Beautiful.ai `Org Chart` 與 Slidesgo organizational charts
  - 適合組織層級、部門結構、ownership map

- `process-flow`
  - 來自 Beautiful.ai `Process Diagram / Flowchart` 與 Slidesgo process diagrams
  - 適合 SOP、方法論、流程教學頁

## 2026-06-12 網路觀察第三輪新增 layouts

- `kpi-scorecards`
  - 來自 Beautiful.ai / Slidesgo KPI 類模板
  - 適合週報、月報、QBR 的摘要數字頁

- `dashboard-overview`
  - 來自 Beautiful.ai `Data Dashboard` 與 Gamma reporting / review 類模板
  - 適合多圖表摘要、performance overview、analytics review

- `comparison-table`
  - 來自 Beautiful.ai `Table Slide` 與 Slidesgo table / comparative table 類模板
  - 適合 benchmark、pricing、feature matrix、數據對照

## 2026-06-12 網路觀察第四輪新增 layouts

- `problem-solution-bridge`
  - 來自 Slidesgo `Problem vs Solution` 與 Gamma 的 problem / proposal 類模板觀察
  - 適合現況痛點到解法橋接

- `recommendation-stack`
  - 來自 Gamma `Client Recommendation`、`Executive Summary` 類模板觀察
  - 適合建議排序、行動建議、proposal summary

- `strategic-priorities`
  - 來自 Gamma `Strategic Priorities Framework` 與 Slidesgo strategy infographics
  - 適合 priority ranking、next steps、focus areas

## 2026-06-12 網路觀察第五輪新增 layouts

- `case-study-proof`
  - 來自 Beautiful.ai case study + Gamma case study / impact report 模板觀察
  - 適合 challenge / solution / proof 型案例頁

- `findings-cluster`
  - 來自 Gamma `UX Research Findings` 與 report 類模板觀察
  - 適合研究摘要、insight synthesis、diagnostic findings

- `annual-highlights`
  - 來自 Slidesgo annual report + Gamma impact / review 類模板
  - 適合年度亮點、成果 recap、impact report

## 2026-06-12 網路觀察第六輪新增 layouts

- `onboarding-path`
  - 來自 Gamma onboarding + Beautiful.ai 30-60-90 類模板
  - 適合 new hire、client onboarding、adoption plan

- `workshop-run-of-show`
  - 來自 Gamma workshop facilitation + Slidesgo workshop 類模板
  - 適合工作坊節奏表、facilitation agenda、session flow

- `learning-module`
  - 來自 Beautiful.ai training / education + Slidesgo education 類模板
  - 適合課程模組、training unit、teaching segment

## 2026-06-12 網路觀察第七輪新增 layouts

- `media-kit-overview`
  - 來自 Beautiful.ai media kit + marketing 類模板
  - 適合 partner-facing media kit、brand partnership deck

- `campaign-architecture`
  - 來自 Gamma event marketing + Slidesgo campaign / social 類模板
  - 適合 campaign goal、audience、tactics、KPI 的組裝頁

- `event-recap-storyboard`
  - 來自 Beautiful.ai event recap + Slidesgo event 類模板
  - 適合活動亮點、gallery、成效與回饋回顧

## 2026-06-12 網路觀察第八輪新增 layouts

- `competitive-landscape`
  - 來自 pitch deck 競品定位與 SlideModel competition landscape 類頁面
  - 適合 market positioning、battlecard、differentiation 頁

- `maturity-ladder`
  - 來自 SlideModel AI transformation roadmap + Slidesgo maturity model infographics
  - 適合 AI maturity、process maturity、digital transformation

- `go-to-market-motion`
  - 來自 Pitch Deck Coach growth strategy + Beautiful.ai product launch / GTM 類模板
  - 適合 acquisition / retention / innovation、launch plan、growth engine

## 2026-06-12 網路觀察第九輪新增 layouts

- `proposal-value-stack`
  - 來自 Beautiful.ai sales proposal + Gamma client proposal 類頁面
  - 適合 sales proposal、service proposal、solution pitch

- `pricing-packages`
  - 來自 Slidesgo pricing table + product pricing pitch deck
  - 適合 SaaS pricing、service package、tier comparison

- `battlecard-compare`
  - 來自 Beautiful.ai sales battlecard / technology sales proposal 類頁面
  - 適合 objection handling、competitor response、why-us comparison

## 2026-06-12 網路觀察第十輪新增 layouts

- `account-plan-brief`
  - 來自 Beautiful.ai KAM + EBR / customer business review 脈絡
  - 適合 strategic account planning、customer plan、relationship motion

- `pipeline-health-review`
  - 來自 Beautiful.ai sales pipeline review + QBR 管理脈絡
  - 適合 forecast review、pipeline health、revenue risk discussion

- `business-review-rhythm`
  - 來自 Gamma quarterly business review + EBR framework
  - 適合 client-facing QBR、internal QBR、executive review cadence

## 2026-06-12 網路觀察第十一輪新增 layouts

- `customer-success-plan`
  - 來自 Dock / EverAfter / Miro 的 success plan 與 lifecycle 素材
  - 適合 shared success plan、implementation-to-renewal blueprint

- `adoption-journey`
  - 來自 Gamma digital customer success lifecycle + adoption / onboarding 脈絡
  - 適合 product adoption、post-go-live usage enablement、activation progress

- `renewal-readiness`
  - 來自 renewal deck / retention 對話框架
  - 適合 renewal planning、retention review、expansion readiness

## 2026-06-12 網路觀察第十二輪新增 layouts

- `implementation-rollout-map`
  - 來自 implementation PowerPoint templates 與 rollout / workstream 類素材
  - 適合 software rollout、deployment plan、implementation execution

- `customer-education-track`
  - 來自 customer education / academy / certification 類素材
  - 適合 learning path、customer academy、education progression

- `partner-enablement-kit`
  - 來自 Gamma partner enablement deck + enablement resource 類框架
  - 適合 partner onboarding、channel enablement、reseller activation

## 2026-06-12 網路觀察第十三輪新增 layouts

- `field-enablement-readiness`
  - 來自 sales enablement kickoff 與 field readiness 素材
  - 適合 field enablement、sales readiness、partner field activation

- `certification-ladder`
  - 來自 certification program / learning path / credential progression 素材
  - 適合 level-based academy、qualification path、program certification

- `community-learning-loop`
  - 來自 community of practice / peer-learning / recurring session 脈絡
  - 適合 community learning、practice rhythm、member participation loop

## 2026-06-12 網路觀察第十四輪新增 layouts

- `advocacy-program-map`
  - 來自 advocacy / outreach / evangelism program 脈絡
  - 適合 developer evangelism、advocacy initiative、outreach programs

- `ambassador-journey`
  - 來自 ambassador program / volunteer ambassador 發展脈絡
  - 適合 ambassador growth、champion program、advocate development

- `community-ops-rhythm`
  - 來自 community of practice / community ops / recurring engagement 節奏
  - 適合 community operations、engagement cadence、practice program rhythm

## 2026-06-12 網路觀察第十五輪新增 layouts

- `ecosystem-relations-map`
  - 來自 ecosystem mapping / stakeholder landscape / service design network 素材
  - 適合 ecosystem strategy、community collaboration network、stakeholder map

- `ambassador-metrics-board`
  - 來自 ambassador / outreach / advocacy measurement 脈絡
  - 適合 ambassador performance review、reach and engagement scorecard

- `volunteer-ops-cadence`
  - 來自 volunteer / community ops / support cadence 素材
  - 適合 volunteer operations、coverage planning、support rhythm

## 2026-06-12 網路觀察第十六輪新增 layouts

- `membership-value-journey`
  - 來自 membership program / community progression / belonging journey 素材
  - 適合 membership growth、member lifecycle、community participation journey

- `donor-engagement-lifecycle`
  - 來自 donor lifecycle / fundraising touchpoint / stewardship flow 脈絡
  - 適合 donor engagement、fundraising relationship development、stewardship and retention

- `governance-committee-model`
  - 來自 governance presentation / board and committee / oversight operating model 素材
  - 適合 governance structure、committee ownership、decision and escalation framework

## 2026-06-12 網路觀察第十七輪新增 layouts

- `investor-update-brief`
  - 來自 Beautiful.ai `Investor Update` + Gamma board / investment committee 類頁面
  - 適合 investor update、board review、executive brief、quarter snapshot

- `team-bulletin`
  - 來自 Beautiful.ai `Team Bulletin` + Slidesgo `Scoops Newsletter` / `Interactive Bulletin Board`
  - 適合 internal digest、team update、newsletter、round-up

## 2026-06-12 網路觀察第十八輪新增 layouts

- `annual-meeting-brief`
  - 來自 Slidesgo `Annual General Meeting` / `Special Annual Meeting` / HOA annual meeting
  - 適合 AGM、association annual meeting、member-facing governance recap

- `fundraising-campaign-brief`
  - 來自 Slidesgo charity event / nonprofit marketing / gala fundraising 類模板
  - 適合 fundraising campaign、charity gala、donor ask、sponsorship brief

- `association-member-update`
  - 來自 association / community / annual meeting 類模板觀察
  - 適合 member digest、committee round-up、association update、program recap

## 更新方向

- `quote-focus` 幫助我們把 `title-center` 再拆細，區分「章節過場」與「一句話節奏頁」
- `cover-photo-frame` 補足封面頁中「照片窗口」這個很常見但原本沒被命名的結構
- `gantt-roadmap`、`team-roster`、`swot-quadrant` 補足 AI 簡報工具常見的 smart layouts
- 第二輪補進 `customer-journey`、`org-structure`、`process-flow`，避免 layout library 只偏向封面與圖文，而缺少商務簡報的中段框架頁
- 第三輪補進 `kpi-scorecards`、`dashboard-overview`、`comparison-table`，讓 reporting / dashboard / benchmark 類頁面不必再借用通用圖文版型
- 第四輪補進 `problem-solution-bridge`、`recommendation-stack`、`strategic-priorities`，讓提案與顧問式論證頁有正式骨架，而不是退回一般 split 或 bullets
- 第五輪補進 `case-study-proof`、`findings-cluster`、`annual-highlights`，讓成果證明、研究摘要與年度回顧也有獨立頁型
- 第六輪補進 `onboarding-path`、`workshop-run-of-show`、`learning-module`，讓教學、帶領與 onboarding 場景也有正式結構
- 第七輪補進 `media-kit-overview`、`campaign-architecture`、`event-recap-storyboard`，讓對外溝通、活動與品牌展示也有獨立頁型
- 第八輪補進 `competitive-landscape`、`maturity-ladder`、`go-to-market-motion`，讓 pitch、product strategy 與 transformation 類頁面也有正式骨架
- 第九輪補進 `proposal-value-stack`、`pricing-packages`、`battlecard-compare`，讓 proposal、pricing 與 sales enablement 類頁面也有正式骨架
- 第十輪補進 `account-plan-brief`、`pipeline-health-review`、`business-review-rhythm`，讓 account management、pipeline review 與 QBR / EBR 也有正式骨架
- 第十一輪補進 `customer-success-plan`、`adoption-journey`、`renewal-readiness`，讓 onboarding-to-renewal 的 customer lifecycle 也有正式骨架
- 第十二輪補進 `implementation-rollout-map`、`customer-education-track`、`partner-enablement-kit`，讓 rollout、education 與 partner activation 也有正式骨架
- 第十三輪補進 `field-enablement-readiness`、`certification-ladder`、`community-learning-loop`，讓 field readiness、credential progression 與社群學習節奏也有正式骨架
- 第十四輪補進 `advocacy-program-map`、`ambassador-journey`、`community-ops-rhythm`，讓 outreach、ambassador 與 community ops 也有正式骨架
- 第十五輪補進 `ecosystem-relations-map`、`ambassador-metrics-board`、`volunteer-ops-cadence`，讓 ecosystem、program metrics 與 volunteer operations 也有正式骨架
- 第十六輪補進 `membership-value-journey`、`donor-engagement-lifecycle`、`governance-committee-model`，讓 membership、donor stewardship 與 governance operating model 也有正式骨架
- 第十七輪補進 `investor-update-brief`、`team-bulletin`，讓 investor / board 與 internal bulletin 也有正式骨架
- 第十八輪補進 `annual-meeting-brief`、`fundraising-campaign-brief`、`association-member-update`，讓 annual meeting、fundraising strategy 與 association member update 也有正式骨架
