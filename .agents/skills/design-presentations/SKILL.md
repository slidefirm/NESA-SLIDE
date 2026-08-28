---
name: design-presentations
description: Plan, art-direct, produce, or QA a presentation with one renderer-neutral design framework, then route the work to image-based slides, an editable web/HTML deck, or an editable PPTX without bundled assets, presets, themes, layouts, or templates. Use when the user asks to create, redesign, structure, art-direct, or evaluate a deck and wants the visual direction derived from their content instead of a fixed template. On first use, ask the user to choose 圖片式簡報、網頁式簡報、或 PPTX 簡報 before selecting a renderer, unless the current request already states exactly one.
---

# 簡報設計框架

使用同一套設計決策流程規劃簡報，再依使用者選擇切換成圖片、網頁或 PPTX。只提供方法與驗收底線；不要假設任何內建素材、Theme、Layout、Preset、字型、圖片或母片。

## 1. 先確認輸出形式

在研究風格、選擇工具、寫完整大綱或產生檔案前，先確認 renderer。

- 若本次訊息尚未明確指定，使用可用的結構化提問介面；若沒有，直接詢問：
  **「這次想做哪一種簡報？請選一個：圖片式簡報、網頁式簡報、PPTX 簡報。」**
- 用一句話說明差異：圖片式重視每頁完整視覺；網頁式重視瀏覽器呈現與語意結構；PPTX 重視 PowerPoint 原生可編輯性。
- 把這個問題視為阻擋式 Gate；收到答案前不要替使用者選擇，也不要開始產製。
- 若使用者已在同一訊息明確指定其中一種，確認該選擇後直接繼續，不要重複詢問。
- 若使用者要求多種格式，先請他指定主要格式；其餘格式只能在各自 renderer 下重新適配，不要直接轉檔冒充完成。

## 2. 補齊設計任務

確認格式後，只詢問會實質影響結果的缺項；每輪最多三題。優先取得：

1. 溝通目標、受眾與使用情境。
2. 內容來源、預計頁數／時間，以及必須保留的主張或資料。
3. 品牌限制、語言、畫面比例、截止時間與可用素材。

若資訊足以安全推進，採最保守的合理假設並明示。涉及可能變動的產品名、日期、數字、法規或高風險事實時，先以官方或第一方來源查證，再鎖定敘事。

## 3. 建立共用設計核心

依下列順序工作，不要先選版型再補風格理由：

```text
Story
→ Art Direction Brief
→ Scene Grammar
→ Theme + Layout
→ Renderer Handoff
→ Technical QA
→ Perceptual QA
```

### Story 與內容契約

- 先定義一句核心主張、受眾需要採取的行動與敘事弧線。
- 為每頁記錄：`slide_id`、`scene_role`、單一主要訊息、證據、內容關係、密度與必要媒體。
- 把每次簡報內容視為當次輸入；不要把文案永久綁進 Theme 或 Layout。

### Art Direction Brief

在多頁 deck 中至少定義：

- `visual_genre`：整體視覺類型。
- `narrative_metaphor`：能推導設計決策的一句概念，不只寫「高級、現代、好看」。
- `signature_move`：全簡報唯一主要招牌手法，以及可接受的變體。
- `spatial_rule`：主要錨點、閱讀軸、裁切邏輯、留白與對齊。
- `typography_role`：字體在敘事中的角色、層級方法與字族政策。
- `color_behavior`：主色與強調色各自負責什麼工作。
- `edge_behavior`：畫面邊緣保持安靜、滿版、裁切或跨頁延續。
- `asset_family`：若需要素材，限定一致的主素材家族與用途，保留來源與授權。
- `forbidden_cliches`：至少列出四個本案要避開的俗套。

外部案例只能借用方法，不要複製其版面或表面造型。使用者提供的品牌規範或素材屬於本案輸入，不得包回本 Skill。

### Scene Grammar

- 以 `hero`、`index-or-map`、`evidence`、`relationship`、`pause-or-close` 組織跨頁節奏。
- 為每頁指定 1–5 的視覺強度、主要焦點與招牌手法變體。
- 完整 deck 至少安排一個強度不高於 2 的停頓與一個不低於 4 的高峰；同一 scene role 不要連續超過三頁。
- 新方向先用封面、一般內容頁、資訊密集頁做三頁 pilot。使用者未要求中途確認時，把 pilot 當成內部 Gate，通過後再擴成全套。

### Theme、Layout 與 Content 分工

- 用 Theme 定義色彩角色、字體角色、材質、Pattern、內容表面、陰影與裝飾語彙；不要綁死固定版面。
- 用 Layout 定義內容角色、空間關係、safe area、閱讀順序、對齊、視覺重心與裝飾區；不要放具體配色、風格情緒或單次文案。
- 先判斷比較、流程、循環、層級、證據、優先順序或結論等內容關係，再設計相應構圖。循環不能用線性卡片列代替，流程必須有明確方向。
- 不得先從既有 Theme／Layout 名單挑選設計方向。先依內容完成 Art Direction、scene grammar 與構圖需求，再對正式 core 做 coverage check。
- 語意結構完全吻合時可重用 core；部分吻合時延伸既有規格或建立變體；無法完整表達時新增可追溯的 Theme、Layout 或 renderer recipe。不得為了避免新增規格而犧牲設計方向。
- 重用 Layout 只代表沿用資訊結構，不代表沿用既有視覺；Theme、內容表面與招牌手法仍依本案 Art Direction 決定。

## 4. 套用共用排版原則

- 預設使用 16:9，保留穩定安全邊界；若使用者指定其他比例則依其要求。
- 以實際可見的內容群組計算重心，不用巨大透明框或無意義滿版容器假裝置中。
- 稀疏內容先收合再放大、置中；資訊增加時才向外擴張。非對稱版面必須有合理視覺配重。
- 主標負責短主張，副標負責完整說明；關鍵數字至少與所屬標題同等醒目。
- 先量測再換行；優先在語意標點附近斷行，避免孤字、極短詞或上下失衡。
- 裝飾必須支持敘事、資訊分組或閱讀方向。不要用等寬圓角卡片牆、無功能漂浮色塊、通用紫橘漸層或右側制式插圖填空。
- 同一 deck 的標題位置、內容表面、構圖與密度要有節奏差異；只換顏色不算版面變化。

## 5. 依選擇進入單一 Renderer 分支

### 圖片式簡報

- 把每頁視為完整 16:9 點陣視覺，優先保護整體構圖與藝術指導一致性；不要宣稱其內容可原生編輯。
- 為每頁建立完整生成規格：頁型與情緒、視覺基底、角落／邊緣行為、構圖描述、文字內容、安全區與收尾意圖。
- 在要求七段式 assembled YAML 的環境中，使用既定七段結構；不要把它當成 HTML 或 PPTX 的共同 payload。
- 只使用使用者提供、已授權或可追溯的素材；需要 AI 生圖時使用當前環境正式提供的影像生成能力。
- 逐頁生成與檢查，不要並行製作同一套正式圖。檢查文字正確、留白、裁切、風格一致、敘事節奏與招牌手法。

### 網頁式簡報

- 建立固定比例的 HTML stage；預設 1920×1080。只有外層 viewer 可等比縮放，投影片內部不要依 viewport reflow。
- 保留語意化 DOM、獨立文字與視覺模組；不要把整頁做成背景圖。若沒有編輯器 runtime，不要宣稱具備完整拖拉編輯能力。
- 先以 Flex／Grid 等方式計算，再在需要自由操作時物化幾何。排版容器與可編輯內容要分離。
- 預設以字體、色彩、Pattern、漸層、噪點、陰影與基礎幾何建立環境層；照片或插圖只在它們是必要內容、使用者明確要求且已有合法來源時加入。
- 若是新建 HTML 且使用者要求圖片背景、滿版／半版圖片構圖或 image-led HTML，先啟用 `.agents/skills/html-image-slide/SKILL.md`：先宣告 `asset_policy=image-planned`、逐頁圖片角色與 SAFE ZONE，再選 Layout；完成 handoff 後才交給 `html-pattern-slide` 產生可編輯前景。若使用者提供既有 HTML 且只要附加／替換背景，改用 `.agents/skills/slide-background-image/SKILL.md`，保留原始 Layout、內容與幾何，不重新選版。
- HTML 不必先產生圖片式 assembled YAML。以 Art Direction、Theme、Layout 與 content manifest 直接建立 renderer handoff。
- 用實際瀏覽器逐頁檢查字體載入、錯誤換行、overflow、clipping、碰撞、縮放、鍵盤操作與投影模式；有編輯功能時實際操作驗證。

### PPTX 簡報

- 預設交付真正可編輯的 PowerPoint：文字、形狀、圖表與內容物件使用 native objects。
- 建立 Theme／Slide Master、實體 Custom Layout 與 Placeholder；不要只在一般 slide 上複製固定物件。
- 若使用生成背景，只允許材質、漸層、光影與抽象裝飾；不得把文字、數字、卡片、圖表、表格或 Placeholder 外框烘焙進背景。
- 把背景放在 Custom Layout，把可編輯內容留在 slide。不要用整頁截圖或圖片化文字冒充 PPTX。
- 以實際內容高度收合文字與內容群組，再放入可用區；PowerPoint 手動大改文字後不保證自動 reflow，必要時重新生成。
- 直接檢查 PPTX package／XML 的 master → layout → slide 關係、Placeholder 與 native object；再用 PowerPoint 原生渲染逐頁檢查裁切、重疊與錯誤換行。

## 6. 完成與回報

若使用者要求成品，不要停在設計說明；使用當前可用工具產出實際 artifact。工具或 runtime 不足時，清楚標示缺口，不要把規格稿宣稱為完成品。

最終逐項回報：

1. 使用者選擇的輸出形式與需求。
2. 實際 artifact 路徑或連結。
3. 對應的內容／設計／renderer source 或 manifest。
4. 已執行的 renderer-specific QA 與可觀察結果。
5. 未驗證項目與原因。

沒有實際 artifact 與對應 QA 證據時，只能標記為設計規格或 partial。未經使用者明確授權，不要部署、上傳、發送、push 或修改遠端共享狀態。
