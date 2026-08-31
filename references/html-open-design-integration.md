# Open Design 與 Open Slide 對 HTML 簡報系統的採用決策

## 兩個工具在解什麼問題

- Open Design 把設計系統與設計方法拆開。Theme 不只是一組顏色，而是可攜的字體、色彩、元件、設計規則與 craft 原則。
- Open Slide 把投影片視為任意 React composition。固定的是 1920×1080 舞台、縮放、導覽、檢查與匯出，內容結構由每頁自己決定。

參考：

- https://github.com/nexu-io/open-design
- https://github.com/nexu-io/open-design/blob/main/docs/skills-protocol.md
- https://github.com/1weiho/open-slide
- https://github.com/anthropics/claude-code/blob/main/plugins/frontend-design/skills/frontend-design/SKILL.md

## 舊版為什麼看起來都一樣

舊版的 Theme Lab 雖然有不同 Theme 與 Layout 名稱，最終仍由同一個 `html_production_renderer.py` 產生同一種 DOM 骨架：標題、副標與固定元件。Theme 只在最後套字體、顏色與表面效果，所以 metadata 很多樣，畫面卻仍像同一份簡報換皮。

真正的根因不是 Theme 數量不足，而是 Composition Grammar 只有一套。

## 採用

1. 內容先行：先決定 Subject 與 Narrative，再選 Theme 與 Composition。
2. Theme 帶設計方法：字體、配色之外，還要包含 signature、composition grammar 與 craft technique。
3. Layout 表示資訊關係，不表示固定卡片：比較、流程、循環、矩陣、台帳都可有不同 DOM 實作。
4. 一個鮮明手法就夠：線、路線、索引籤等元素必須承載內容語意，不做無意義裝飾。
5. 執行層共用：固定 1920×1080 舞台、Content Area、編輯、投影、復原與 QA。
6. 兩階段設計：先規劃內容與版面線框，再建立視覺語法並逐頁自我檢查。

## 不採用

1. 不把 HTML Renderer 全面改成 React；目前原生 HTML/CSS 的部署與編輯契約仍較穩定。
2. 不允許任意自由構圖突破 Content Area、安全留白與可編輯契約。
3. 不把設計自由誤解成每頁堆滿裝飾；陰影、Pattern、線條與幾何必須有結構作用。
4. 不再以大量一次性 Theme 名稱掩蓋相同 DOM，也不把正式案例退回只換色的 preset。

## 正式 HTML Assembly

`Subject → Narrative → Signature → Composition → Theme → Editor`

- Subject：實際議題、觀眾與單一任務。
- Narrative：完整故事線與每頁角色。
- Signature：一個可辨識且有意義的視覺動作。
- Composition：把內容關係轉成 DOM 與空間關係。
- Theme：色彩、字體、表面、線條與節奏。
- Editor：統一掛上選取、群組、縮放、復原、投影與匯出。

Theme Lab 第三版用三份 12 頁完整簡報驗證這套方法，不再用十多份換膚案例製造假多樣性。
