# 大綱內容與 Layout 對應契約

本契約只描述 Markdown 大綱與共用 Layout core 的對應，不要求先選 renderer，也不代表已完成任何 renderer-specific QA。

## 目錄

1. 畫面內容形式
2. Layout 候選起點
3. 每頁輸出格式
4. Coverage gap

## 1. 畫面內容形式

投影片可見內容依語意選擇格式。metadata、研究筆記與 Layout 說明可以使用清單，但不要因此把可見內容也改成列點。

| content form | 適用內容 | 建議 Markdown 表達 |
|---|---|---|
| statement | 單一主張、問句、結論、CTA | 一至三行完整句 |
| narrative | 因果解釋、情境、案例背景 | 一至兩段短文，搭配一個 pull quote 或結論 |
| question-answer | 暖場、疑問與解析 | 問題區＋答案區 |
| comparison | 前後、方案 A/B、差異 | 雙欄或比較表 |
| sequence | 流程、時程、教學步驟 | 編號節點與方向關係 |
| cycle | 回饋、反覆、循環因果 | 節點＋回到起點的關係說明 |
| hierarchy | 組織、層級、能力成熟度 | 父子層級或金字塔文字 |
| metrics | KPI、趨勢、證據 | 大數字、標籤、變化與一句解讀 |
| table-chart | benchmark、資料分布、圖表 | 欄列定義、資料點與 chart insight |
| quote-case | 引言、見證、案例片段 | 完整引言／情境／結果／出處 |
| media-led | 人物、照片證據、地圖或產品視覺 | 媒體規格＋caption＋必要來源 |

visible_content 應是可直接上投影片的文字或資料結構，不要只寫「放一張流程圖」或「補三個重點」。

## 2. Layout 候選起點

下表只是發現候選的入口。選定前必須打開當前 prompt_system/layouts/{id}.yaml 驗證，不得把此表當成靜態 registry。

| content relation | 初始候選 |
|---|---|
| single-proposition / pause | quote-focus、title-center、highlight-callout |
| reading-path | 從 HTML catalog 或 core 中查找 toc-* |
| parallel-modules | cards-1-plus-*、icon-grid-6、stats-3-row |
| state-change / comparison | before-after、split-comparison、comparison-table |
| ordered-path | process-flow、flow-stages-3、timeline-milestones、timeline-vertical、gantt-roadmap |
| cycle | cycle-hub-6 |
| hierarchy | pyramid、org-chart |
| ranked-decision | strategic-priorities、recommendation-stack |
| measurable-proof | kpi-scorecards、stats-3-row、dashboard-overview、multi-line-chart、data-annotation、heat-map |
| position-and-cluster | matrix-4quadrant、swot-quadrant、heat-map |
| image-led | 只從符合本次 asset policy 的 with-image Layout 選擇 |

Layout ID 中的數量不是內容上限。若語意相符但容量不足，先記錄 composition 調整或拆頁需求；不要刪除 primary content，也不要杜撰 cards-1-plus-7 之類不存在的 ID。

## 3. 每頁輸出格式

每頁依下列順序呈現。只有「畫面內容」欄位會依 content form 改變格式。

~~~markdown
# Slide N｜主張式標題

**頁面任務**
scene_role: evidence
page_role: data_insight
content_pattern: 1-plus-data
page_goal: 讓受眾看見決策所依賴的主要證據

**核心訊息**
一句可被講者說出口、也能被證據支持的結論。

**畫面內容（form: metrics）**
72%｜主要指標名稱｜較去年 +11pp
18 天｜第二指標名稱｜從 31 天縮短
結論：改善集中在導入後第二階段，而非第一階段。

**證據與來源**
資料年份、母體、限制、來源名稱與 URL；若未查證，標示 [需人工補充]。

<!-- 口語講稿：補足背景、轉場、解釋與限制，不逐字朗讀畫面。 -->

**Layout 對應**
content_relation: measurable-proof
primary_layout: kpi-scorecards
alternatives: stats-3-row、dashboard-overview
media_requirement: no-image
slot_mapping: title ← 主張式標題；scorecards ← 兩個指標；takeaway ← 結論
fit_reason: 數字是第一閱讀層，結論位於第二閱讀層
composition_note: 依兩個指標重算欄寬，不製造第三個空卡
renderer_status: not-selected；outline-only
validation: Layout core source checked；renderer 與 visual QA 不在本階段
~~~

比較頁可讓畫面內容直接使用雙欄表；流程頁可使用編號節點；敘事頁可使用短段落；金句頁只留完整句與出處。不要再加一層不必要的「重點列點」。

畫面內容的其他合法變體：

~~~markdown
**畫面內容（form: narrative）**
團隊並不是缺少資料，而是每個決策節點都在使用不同版本的資料。

真正的成本不是多做一次報表，而是無法知道哪一個判斷可以被重現。

**畫面內容（form: comparison）**
| 現況 | 目標 |
|---|---|
| 每個部門各自定義成功 | 共用一組決策指標 |
| 事後解釋偏差 | 決策當下保留依據 |

**畫面內容（form: sequence）**
01 定義問題 → 02 建立共同證據 → 03 做出決策 → 04 記錄結果
~~~

## 4. Coverage gap

沒有合適 Layout 時使用：

~~~markdown
**Layout coverage gap**
existing_layout_id: none
missing_semantics: 需要同時表達三層因果與回饋路徑，現有線性流程會丟失閉環
required_slots: title、cause-layer、mechanism-layer、outcome-layer、feedback-loop、note
spatial_relationship: 三層由左至右，結果回連到第一層
media_requirement: no-image
renderer_scope: renderer-neutral-outline
next_step: 補充可追溯 Layout core，或調整內容分頁
~~~

Coverage gap 是大綱規劃結果，不代表已新增 Layout。只有後續進入實際產製時，才檢查 adapters 與 renderer QA。
