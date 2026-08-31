# 設計方法突破研究索引

本資料夾整理 2026-07-26 對 HTML 簡報設計方法的外部研究。這一輪只研究方法、
國外案例、素材授權與後續驗收方式，沒有修改任何簡報畫面或 renderer。

## 建議閱讀順序

1. [`20260726-breakthrough-morning-brief.md`](20260726-breakthrough-morning-brief.md)
   - 給決策者看的短版結論。
   - 說明這次真正找到的突破、下一輪應先做什麼、暫時不應做什麼。
2. [`20260726-method-audit-and-roadmap.md`](20260726-method-audit-and-roadmap.md)
   - 現有方法盤點、國外案例研究、失敗根因、全新流程與實驗矩陣。
3. [`20260726-reference-catalog.yaml`](20260726-reference-catalog.yaml)
   - 可供後續程式或人工查詢的來源目錄。
   - 明確區分「只能參考」與「可實際使用的素材」。
4. Art Direction 研究原型已升級為正式
   [`prompt_system/art_direction/schema.yaml`](../../prompt_system/art_direction/schema.yaml)。
   - 舊 `proposal-only` YAML 已刪除，避免和正式欄位同時存在。
   - 正式版本另有模板、驗證器、renderer handoff 與人工 gate。
5. [`20260726-perceptual-qa-proposal.md`](20260726-perceptual-qa-proposal.md)
   - 補足現有 QA 只會抓溢位、字級與孤字，卻抓不到「看起來很像 AI／手刻 HTML」的缺口。

## 一句話結論

目前的系統不是缺少更多 Pattern 或 SVG，而是缺少一層位於 Story 與 Layout 之間的
**Art Direction Brief**：它要先決定視覺類型、參考家族、主導素材、招牌動作、
邊緣行為與禁止使用的陳腔，renderer 才能避免回到卡片、細線、光暈與任意裝飾。
