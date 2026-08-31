# HTML 簡報設計技法庫

本文件定義 HTML renderer 可以使用的設計手段。Theme 仍然負責品牌色彩、字體與質感 token；Layout 仍然負責資訊關係與槽位；design dialect 只在 HTML renderer 內決定構圖、空間層次與 CSS 表現方法。

正式機器可讀規格是 `prompt_system/renderers/html/design-dialects.yaml`。

## 組合原則

1. 每個 Theme 必須有一個獨立 design dialect，不得只更改配色或陰影。
2. 每個 dialect 至少使用三種 CSS 技法，而且必須改變構圖語意：對齊方向、閱讀軸、空間層次、裁切語言或書寫方向至少一項。
3. 內容、Layout 序列、Theme 材質與 design dialect 為四個獨立變數，驗收時必須分開計數。
4. 不以四周浮貼無語意幾何物件填滿版面。優先使用 Pattern、遮罩、混合、投影、排版節奏與留白。
5. 所有特效都必須依附在可編輯 DOM 元素上；編輯器開啟時，選取框與文字實際邊界不得被特效擴大。
6. 預設只能使用 Pattern 與基礎幾何輔助設計，不自動加入照片、插畫、裝飾性 SVG、圖示包或貼圖。
7. Design dialect 之外還要分離 composition variant、header placement 與 surface treatment；
   卡片只是一種 surface，不是所有內容的共同骨架。

## 技法與使用界線

| 技法 | 適合用途 | 限制 |
| --- | --- | --- |
| CSS Grid / Subgrid | 出版欄線、工程剖面、訊號軸 | 內容實際高度先量測，再將辨識好的欄位物件化 |
| 水平書脊線／側欄索引 | 書脊、側欄、軸線標示 | 文字維持 `horizontal-tb`；用 Grid、欄線與水平短標建立方向 |
| `text-wrap: balance/pretty/stable` | 標題平衡斷行、正文可讀性、編輯時穩定換行 | `balance` 只給短標題；`stable` 給 `contenteditable` |
| `clip-path` | 工業斜切、織帶、工程切角 | 不得裁到文字安全區；縮放後仍要可選取 |
| `mask-image` | 紙邊、柔焦、準漸隱去 | 提供 `-webkit-mask-image`；遮罩只做視覺，不改變 DOM 邊界 |
| `mix-blend-mode` / `background-blend-mode` | 發光訊號、油墨、Pattern 疊合 | 只用在可預測的 stacking context，不讓文字對比依賴背景巧合 |
| `backdrop-filter` | 磨砂玻璃與柔光層 | 必須保留實色、半透明備援，不將所有卡片都玻璃化 |
| `transform-style: preserve-3d` | 工業透視、層板深度 | 避免在同一個 3D 父層使用會打平子層的 opacity、filter、clip/mask 與 blend |
| `shape-outside` | 圖文繞排與自然曲線文案 | 僅對 float 生效，所以只用在靜態圖文模組，不用在自由縮放群組 |
| Repeating gradients | 網格、等高線、織紋、點陣 | 強度必須低於主內容，不建立多餘可選取裝飾物件 |

## 官方參考

- [MDN: CSS Grid subgrid](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Grid_layout/Subgrid)
- [MDN: text-wrap](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/text-wrap)
- [MDN: clipping / clip-path](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Masking/Clipping)
- [MDN: mask-image](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/mask-image)
- [MDN: mix-blend-mode](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/mix-blend-mode)
- [MDN: background-blend-mode](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/background-blend-mode)
- [MDN: backdrop-filter](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/backdrop-filter)
- [MDN: transform-style](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/transform-style)
- [MDN: CSS Shapes](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Shapes)

## 驗收條件

- 公開 Theme Lab 必須有 13 個不重複 design dialect 與 13 種不重複 composition。
- 技法集合不少於 20 種，每個 Theme 至少三種。
- 內容主題、Layout 序列、敘事 architecture 與 design dialect 都必須各自唯一。
- 每份公開 Theme 至少使用三種 header placement、三種 surface treatment，並逐頁在 manifest
  記錄 composition variant；連續頁不得重複完全相同的組合。
- 公開 Theme Lab 的投影片內容必須是零照片、零插畫、零 SVG、零 data image、零外部 image URL。
- Browser QA 有未豁免 issue 時不得宣告 pass；目前公開 Theme Lab 視覺審查必須實際覆蓋 136 頁。
