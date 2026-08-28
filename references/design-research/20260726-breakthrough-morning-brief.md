# HTML 簡報設計突破：晨間摘要

日期：2026-07-26

## 先講結論

我找到的突破不是「再換一批比較漂亮的 SVG」，而是要改變設計流程的順序。

目前大致是：

```text
內容 → Layout → Theme → 補 Pattern／線條／SVG → QA
```

建議改為：

```text
內容 → Art Direction Brief → Reference Packet → Scene Grammar
     → Asset Family → Layout → Theme Tokens → Perceptual QA
```

差別在於：以後不再先把內容排好，最後才思考怎麼「裝飾」；而是先決定這份簡報
要像哪一種出版物、展覽、品牌系統或視覺敘事，再讓字體、裁圖、留白、線條、
動態與版面都從同一個概念長出來。

## 為什麼現在容易看起來像 AI Slop

現有系統其實很擅長「不要壞掉」：

- 有固定 Content Area、36px 下限、孤字換行與溢位檢查。
- Theme、Layout、Content、Editor Contract 分得很清楚。
- 有大量 composition、surface、pattern 與 component recipe。

但它缺少「為什麼要長這樣」的上游決策：

- `editorial-spine`、`contour-field`、`paper-grain` 這些名稱是技法，不是藝術方向。
- 系統知道一條線不能壓到文字，卻不知道這條線有沒有存在的理由。
- 系統知道卡片要置中，卻不知道這頁其實根本不應該使用卡片。
- QA 能抓錯位，抓不到「安全、完整，但平庸」。
- 舊研究禁止點陣與照片承擔構圖，新規則又允許有來源的 archival crop，方向互相衝突。

因此真正的問題是：

> 規則的完整度很高，但藝術指導的明確度很低。

## 國外案例給出的共同答案

這次沒有只看 Pinterest 截圖，而是以設計工作室與機構的官方 case study 為主。

### 1. 一套設計只需要少數強元素

[Pentagram 的 MoMA 系統](https://www.pentagram.com/work/moma)不是堆很多裝飾，
而是固定 logo 位置、強 grid、戲劇化裁圖與一張主圖。變化來自圖像與文字的關係，
不是每頁重新發明邊框。

### 2. 視覺母語必須能解釋

[Fable](https://fable.design/)把自己定位為 strategy-centric、narrative-driven；
它的案例常從品牌故事推導 grid、字體或圖形，而不是先挑一種漂亮風格。
例如 [The Factory Cafe](https://www.fable.sg/factory/)以輸送帶作為整套識別的母題，
[The Balance Company](https://www.fable.sg/the-balance-company/)則以 27×27 grid
統一 logo、字體與溝通物。

### 3. 系統化不是做得更像模板

[Cooper Hewitt](https://www.pentagram.com/news/cooper-hewitt-a-democratic-design-identity)
用強 wordmark、字體、色彩與可重組的六欄 grid 建立規則，但不同內容仍可有不同密度、
欄位與表情。規則提供骨架，不是把所有頁面壓成同一種卡片。

### 4. Generative design 的價值是製造意外，再由人選

[DIA 的 Chaumont Biennale](https://dia.tv/project/chaumont-biennale/)使用自訂工具產生
人工難以逐一做出的變體；重點不是「全自動」，而是讓系統產生大量有邊界的意外，
最後再策展與挑選。

### 5. 裝飾層如果不能擴張，寧可刪掉

[DIA 的 Mailchimp 系統重整](https://dia.tv/project/mailchimp/)直接移除難以規模化的
插畫層，統一 typography，改用與產品行為相關的 motion identity。這證明成熟設計不是
裝飾越多越好，而是每一層都要能穩定工作。

## 建議新增的核心層：Art Direction Brief

每份簡報在選 Layout 前，先回答以下欄位：

```yaml
visual_genre: editorial / institutional / field-guide / kinetic / documentary / ...
narrative_metaphor: 一句能說明整套視覺從哪裡長出來的話
reference_family: 3–5 個同方向案例，不混搭互斥風格
signature_move: 全套只需要 1 個最有辨識度的動作
spatial_rule: 對齊、裁切、留白與閱讀軸
asset_family: 照片／歷史圖版／插畫／icon／無圖
edge_behavior: 四周要留白、滿版、裁切、跨邊或完全安靜
typography_role: 字體是主角、旁白、索引或資料標記
forbidden_cliches: 這份簡報禁止出現的 AI 慣用語彙
```

其中 `signature_move` 只能有一個主角。例如：

- 一張圖跨頁裁切。
- 字體與照片互相遮擋。
- 一條由資料驅動的連續軸。
- 同一個幾何母形在不同頁面縮放、裁切、反轉。
- 兩種字重沿閱讀路徑逐步轉換。

不是同時放光暈、玻璃卡、細線、圓圈、漸層、插畫與 pattern。

## 下一輪最值得做的四個實驗

不要立刻再生成一套十頁簡報。先用同一份內容各做三張代表頁：

| 方向 | 核心方法 | 要驗證的問題 |
|---|---|---|
| Artifact-led Editorial | 公版典藏圖像 + 強裁切 + 出版 grid | 圖像能否取代手刻裝飾並保有可編輯性 |
| Motif-led Identity | 一個由主題推導的母形，跨頁重組 | 能否有辨識度但不變成重複貼紙 |
| Kinetic Typography | 字重、字寬、方向與節奏承擔表情 | 沒有插畫時是否仍能明顯好看 |
| Documentary Field Guide | 照片／標本／註記 + 大留白 | 資訊密度高時能否仍像編輯設計而非 dashboard |

每個方向只做：

1. 封面。
2. 一頁比較或關係頁。
3. 一頁證據或數據頁。

通過後才擴展到完整 deck。

## 明確暫停的做法

- 不再用「四周補幾條線」當設計感。
- 不把 Pattern、Glow、Shadow 當作預設深度。
- 不預設每一頁都需要卡片底板。
- 不從大型混合素材站直接抓 SVG；先確認素材家族與授權。
- 不把 Pinterest、Awwwards 或社群截圖當成可以直接使用的素材。
- 不讓單一 AI 一次從內容直接跳到完整十頁成品，略過方向選擇。

## 明天如果只做一件事

先實作 `Art Direction Brief + Reference Packet` 的選擇關卡，不動 renderer。

只有當這一關能穩定產生三個彼此真的不同、可以說清楚來源與設計理由的方向，
才值得把其中一個方向接回 HTML renderer。

## 本輪範圍確認

- 已完成：方法盤點、國外案例研究、素材授權分級、全新流程、實驗矩陣、審美 QA 提案。
- 沒有進行：修改任何既有 HTML 簡報、Preset、Theme、renderer 或部署輸出。

