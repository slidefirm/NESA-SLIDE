---
name: slide-outline-planner
description: 為本專案規劃完整 Markdown 投影片大綱。當使用者要求製作簡報大綱、deck 結構、演講內容、逐頁 Content Plan，或要讓內容對應專案既有 Layout 素材時使用。保留資訊收集、目標調整、受眾分析、內容規劃、資料研究與逐頁大綱六階段；投影片畫面內容可使用主張、段落、比較、流程、時間軸、數據、表格、引言、案例或媒體主導形式，不強制列點，並在內容鎖定後以現有 Layout core 驗證版面建議。本 Skill 只產出大綱，不要求先選 Image2、HTML 或 PPTX；實際產製另交給對應 renderer Skill。
---

# 專案投影片大綱規劃師

把使用者的主題轉成可直接使用的 Markdown 投影片大綱。先完成內容，再從共用 Layout core 選擇版面骨架；不要從 Layout 名稱反推文案，也不要把 Markdown 列點當成唯一的投影片內容形式。

## 完成條件

交付必須同時包含：

1. 核心目標、受眾判斷、簡報類型與 Story Line。
2. 每頁已寫出的實際畫面內容、證據與口語講稿。
3. 每頁的 scene role、page role、content pattern、內容關係、密度與必要媒體。
4. 經專案 source 驗證的主要 Layout ID、候選 ID、slot mapping 與適配理由。
5. 找不到語意相符 Layout 時的 coverage gap；不得虛構已存在的 Layout ID。
6. 已查證、待補充與尚未驗證項目的清楚界線。

固定交付 Markdown 大綱與 renderer-neutral 的 Layout 指引，不宣稱已產生 HTML、PPTX、圖片或 renderer handoff。

## 啟動時讀取

開始規劃前：

1. 讀取本 Skill 的 references/presentation-types.md。
2. 讀取本 Skill 的 references/outline-output-contract.md。
3. 讀取 prompt_system/specs/page_role.taxonomy.yaml、prompt_system/specs/content_pattern.taxonomy.yaml 與 prompt_system/specs/TAXONOMY_README.md，作為內容語意詞彙；它們不是 Layout。
4. 選 Layout 前讀取 references/presentation-production-contract.md 的 Content Plan、Art Direction 與 Layout 規則。
5. 依內容關係逐一讀取候選 prompt_system/layouts/{layout-id}.yaml。

不要一次載入全部 Layout YAML。先依內容關係找出少量候選，再逐一讀取候選檔案。

只有使用者在大綱完成後明確要求實際產製，才另讀 .agents/skills/design-presentations/SKILL.md 與對應 renderer Skill；不要把下游 renderer Gate 帶回本大綱流程。

## 階段 0：收集基本資訊

收集或從使用者內容合理推斷四個基本項目：

- 簡報主題與已有內容來源。
- 目標受眾與使用情境。
- 預計時長或頁數。
- 希望聽眾產生的改變或行動。

品牌、語言、必留主張與現有素材只在使用者已提供或確實影響內容時補充。不要詢問輸出格式或 renderer。每輪最多詢問三題；可以安全推斷時採保守假設並明示。資訊已足夠時不要重問，直接連續執行其餘階段。

## 階段 1：調整核心目標

把初步目標改寫成一句可觀察的核心目標，確認它：

- 包含聽眾簡報後可採取的行動。
- 說明希望形成的認知改變。
- 能直接回推必要內容。
- 符合時長、受眾動機與決策權限。

## 階段 2：分析受眾

依序產出：

1. 熟悉程度 Level 1–5 的判斷，以及 5 項節奏建議。
2. 基層、主管或決策階層的主要關注點，以及 5 項內容取捨。
3. 5 組痛點 → 價值主張，涵蓋當前痛苦、未來風險與可得價值。

把分析轉成具體的語言深度、證據密度、互動方式與 CTA，不要停在人物誌形容詞。

## 階段 3：規劃內容與敘事

1. 從 references/presentation-types.md 選擇主要簡報類型；跨類型時以主要目的為準。
2. 建立 3–5 個章節與 3–5 句 Story Line。
3. 為每章列出 5 個需要回答的資訊任務。這些是研究與論證目標，不是投影片上必須出現的五個列點。
4. 建立 Art Direction Brief 與 scene grammar；多頁 deck 至少安排一個低強度停頓與一個高強度高峰。
5. 先建立不含 Layout ID 的逐頁 Content Plan。每頁至少記錄：
   - slide_id
   - scene_role
   - page_role
   - content_pattern
   - page_goal
   - primary_message
   - evidence
   - content_relation
   - density
   - required_media
   - visible_content
   - speaker_notes

visible_content 必須寫成觀眾真正會看到的內容。依語意選擇短主張、段落、問答、比較表、步驟、時間軸、數據組、圖表規格、引言、案例區塊或媒體＋說明；不要為了格式整齊一律改成破折號列點。

content_pattern 只能使用 taxonomy 中存在的 ID。若沒有合適項目，標示 taxonomy coverage gap 並描述缺少的語意，不要冒充既有 ID。

## 階段 4：研究與參考資料庫

1. 從資訊任務挑出最需要外部證據的項目，設計最多 10 個單一目標搜尋提示詞；不為湊數製造無用搜尋。
2. 使用可用的瀏覽工具查證。產品、版本、日期、公司規模、法規、醫療、資安與其他可能變動的事實，優先使用官方或第一方來源。
3. 可安全平行時平行搜尋；只有環境允許且使用者已授權代理工作時才使用 subagents。
4. 每筆資料保留核心洞察、客觀證據、年份、來源名稱與真實 URL。找不到時標示 [需人工補充]。
5. 按章節與 slide_id 歸檔；證據必須能直接支撐該頁 primary_message。

不得虛構數據、來源或 URL，也不要把搜尋摘要當成已完成的投影片文字。

## 階段 5：生成逐頁大綱並對應 Layout

先鎖定每頁 visible_content，再執行 Layout routing：

1. 判斷內容關係：單一主張、閱讀路徑、平行模組、比較／狀態轉換、流程、循環、層級、優先順序、證據、分布、引言或下一步。
2. 從 prompt_system/layouts 依內容關係取得候選；沒有已確認的真實媒體時，優先使用 media_requirement: no-image。
3. 逐一打開候選 prompt_system/layouts/{layout-id}.yaml，確認 id、media_requirement、slots、safe_area、alignment_rules 與 visual_balance。
4. 將既有 visible_content 欄位映射到實際 slots，記錄 fit reason、需要的 composition 調整與替代候選。
5. 若沒有完整語意匹配，保留原內容並輸出 coverage gap 與新 Layout brief。不得刪除內容、改寫論點或虛構 ID 來硬套版型。

Layout 名稱中的數量只是一種相容提示，不是內容 schema。內容較多時先調整同一 scaffold 的 composition、間距或分頁；不得為了符合 cards-1-plus-N 而刪除 primary items。

逐頁使用 references/outline-output-contract.md 的格式。畫面內容區可以是段落、表格、編號流程、數據或其他合適結構；只有內容本身真的是清單時才使用列點。

本階段不要詢問 renderer、執行 renderer 指令或檢查 adapter。若使用者之後要求產製，再由對應 Skill 依已完成大綱建立 content manifest、計算 content hash 並驗證 renderer coverage。

## 最終檢查

交付前確認：

- 每頁只有一個可清楚說出的主要訊息，標題是主張而非空泛章名。
- 內容形式由語意決定，沒有把所有頁面壓成 bullet wall 或等寬卡片牆。
- Content Plan 在 Layout 選擇前已完成，Layout 沒有回頭生成或刪改內容。
- 所有 Layout ID 都存在於 prompt_system/layouts，且素材需求符合本次策略。
- 每頁 primary content 都有 slot mapping；找不到時已標記 coverage gap。
- scene role 與視覺強度形成節奏，同一 role 不連續超過三頁。
- 外部事實有來源，未查證內容沒有被寫成確定事實。
- 交付只宣稱為 Markdown 大綱；未選 renderer、未產製 artifact、未做視覺 QA。

最後依序交付：規劃摘要、Story Line、章節、研究資料庫、逐頁大綱、Layout coverage summary、未驗證項目。
