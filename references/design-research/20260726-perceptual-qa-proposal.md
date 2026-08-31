# Perceptual QA 提案

日期：2026-07-26

## 目的

現有 QA 繼續負責字級、孤字、溢位、對比、Content Area、群組、存檔與投影。
本提案新增一層「看起來是否像經過藝術指導」的 QA，避免技術正確卻視覺平庸。

P3、P4、P5、P7、D2、D3 所需的宣告欄位現已進入正式 Art Direction schema 與
renderer handoff；目前只能驗證 manifest 與 scene plan 是否完整。對實際輸出畫面進行
saliency、edge density、卡片必要性與 signature move 可見性的自動／人工驗收，
仍屬本提案的後續工作。

## 一、單頁檢查

### P1：焦點正確

問題：第一眼看到的是否為主張、主數字或主視覺？

建議量測：

- 產生低解析 saliency map。
- 最高 saliency 區域必須與 `primary_focus_bbox` 有交集。
- 若最高 saliency 落在裝飾、頁碼或邊緣圖形，標記 `focus-misdirected`。

### P2：邊緣密度

問題：四周是否比內容更吵？

建議量測：

- 比較外圍 10% 環帶與 Content Area 中央區的高頻 edge density。
- 除非 `edge_behavior=full-bleed`，外圍密度不得高於中央主內容的 1.3 倍。
- 超過時標記 `edge-noise-dominant`。

### P3：裝飾來源

問題：每個非語意視覺是否有來源與角色？

必填：

- `motif_origin`
- `visual_role`
- `source_or_rule`

缺一即標記 `unmotivated-decoration`。

### P4：素材家族一致

問題：是否混用了不同插畫、icon 或照片風格？

建議規則：

- 一份 deck 最多兩個 asset family。
- 一頁最多一個 illustration family。
- icon stroke、cap、corner 與 viewBox 規格必須一致。
- 不一致標記 `asset-family-mismatch`。

### P5：卡片必要性

問題：移除底板後，資訊關係是否仍然清楚？

判定：

- 若只是為了分欄或對齊，不應使用 card surface。
- 卡片必須有 `semantic_boundary`：可獨立比較、選擇、操作或閱讀。
- 沒有理由標記 `card-without-boundary`。

### P6：留白品質

問題：留白是有意義的視覺停頓，還是排版剩下來的洞？

人工 review：

- 留白是否推動焦點？
- 是否形成明確閱讀方向？
- 是否只集中在內容沒填滿的一側？

失敗標記 `accidental-whitespace`。

### P7：Signature move 可見

問題：這頁是否仍屬於這份 deck 的藝術方向？

每份 Art Direction Brief 必須提供：

- `signature_move`
- `allowed_variations`
- `minimum_presence`

若整頁只剩 Theme 色票與通用 Layout，標記 `signature-absent`。

## 二、跨頁檢查

### D1：骨架相似度

目前已有「連續頁是否重複骨架」的人工問題，建議加入半自動量測：

- 將主要物件 bbox 正規化成 32×18 occupancy map。
- 計算連續頁 pairwise similarity。
- 超過 0.82 且連續三頁時標記 `skeleton-repetition`。
- Hero、Pause、Close 可排除。

### D2：場景節奏

十頁 deck 建議至少包含：

- 1–2 Hero / Pause。
- 1 Index / Map。
- 2–4 Evidence。
- 2–4 Relationship。
- 1 Close。

若連續四頁都是相同 scene role，標記 `scene-rhythm-flat`。

### D3：視覺強度曲線

每頁標記 `visual_intensity` 1–5：

- 1：大留白、單一主張。
- 3：一般內容。
- 5：高密度資料或強主視覺。

十頁不應全部落在 3–4；至少要有一次明顯停頓與一次峰值。
否則標記 `intensity-flatline`。

### D4：色彩任務

每個 accent 必須屬於：

- 分類。
- 狀態。
- 時間。
- 風險。
- 品牌。
- 單一情緒焦點。

同一色彩跨頁角色改變時標記 `color-semantics-drift`。

### D5：素材敘事連續

若使用影像：

- 主體、時代、攝影／插畫語言與裁圖策略要一致。
- 不因找不到圖就突然換另一套 illustration library。
- 中途改用另一素材家族必須由 scene role 或章節轉折解釋。

無法解釋標記 `asset-narrative-break`。

## 三、AI Slop 反模式清單

出現任兩項就必須人工 review：

- 大量等寬圓角卡片。
- 紫藍或橘紫漸層光暈沒有語意。
- 裝飾性同心圓、blob、弧線或網格與主題無關。
- 每張卡片都有小 icon、短標題、兩行內文。
- 玻璃面板、陰影與 outline 同時出現。
- 線條終點沒有對齊任何 anchor。
- 封面右側放一張泛用插畫，左側固定三行大標。
- 同一頁同時有 pattern、glow、grain、shadow 與 floating shapes。
- 以過多 badge、pill 或 status chip 假裝資訊層級。
- 素材與文案看似相關，但沒有共享同一個敘事概念。

標記：`ai-cliche-cluster`。

## 四、Reference Delta Review

正式 visual review 不問「像不像參考圖」，而問：

1. 借了哪一個方法？
2. 這個方法如何被內容重新解釋？
3. 哪些表面造型刻意沒有複製？
4. 目前畫面是否仍可辨識出自己的 narrative metaphor？

若只能回答「顏色、字體、圓角很像」，標記 `surface-copy-only`。

## 五、建議評分

每個方向滿分 100：

| 面向 | 分數 |
|---|---:|
| 故事與視覺概念連結 | 20 |
| 焦點與閱讀順序 | 15 |
| Typography | 15 |
| Asset family 與來源 | 15 |
| Scene variety 與跨頁節奏 | 15 |
| Signature move | 10 |
| 投影可讀性 | 10 |

硬性淘汰條件：

- 有未解決的授權。
- 文字小於 36px（非使用者手動編輯）。
- 孤字、溢位或對比失敗。
- `unmotivated-decoration` 超過兩項。
- `ai-cliche-cluster` 未經人工通過。

## 六、導入順序

1. 先將 P3、P4、P5、P7 做成 manifest 必填欄位。
2. 再實作 D1、D2、D3 的 contact-sheet 分析。
3. 最後評估 saliency 與 edge-density 自動化。
4. 所有機器分數只負責攔截與提示，最終藝術方向仍由人工選擇。
