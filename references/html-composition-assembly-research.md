# HTML 簡報組裝系統研究

## 目的

本研究不是要替換既有 renderer，也不是把外部簡報框架整套搬入專案。目標是整理
可直接改善本專案的設計方法，建立一個可被生成器驗證的 HTML 組裝層，使每份簡報的
差異同時存在於內容、版面、背景 Pattern、文字構圖、資訊元件與深度模型，而不只換色。

## 十個 GitHub 參考專案

| 專案 | 觀察到的方法 | 專案採用方式 |
|---|---|---|
| [reveal.js](https://github.com/hakimel/reveal.js) | HTML 原生 slide、巢狀結構、Auto-Animate、可插拔 API | 保留原生 DOM 與可自包含輸出；頁面狀態與轉場不綁死內容結構 |
| [Slidev](https://github.com/slidevjs/slidev) | Theme 套件化、Vue 元件、UnoCSS、Mermaid、Presenter Mode | Theme、Pattern、Component 與 Layout 分離；資料圖表維持可編輯 DOM/SVG |
| [Marp](https://github.com/marp-team/marp) | 內容先行、Theme CSS、單一來源多輸出 | 故事內容與視覺 recipe 分離；同一份內容可換不同 HTML assembly |
| [Spectacle](https://github.com/FormidableLabs/spectacle) | React component composition、layout primitives、live code | 用具名 component recipe 組裝頁面，不把視覺差異全部塞進 Theme token |
| [impress.js](https://github.com/impress/impress.js) | 以 CSS transform 建立空間敘事；內容位置本身就是故事 | 只吸收「空間關係要有語意」；不採用誇張 3D 導航，以免影響編輯與輸出穩定性 |
| [WebSlides](https://github.com/webslides/WebSlides) | 大量可重用 HTML layout pattern、固定閱讀節奏 | Layout adapter 保留明確 slot 與閱讀順序，但不限制內容只能套單一模板 |
| [Shower](https://github.com/shower/shower) | 輕量 HTML engine、Theme 與 engine 分離、可列印 | 投影 shell 與 slide content 分離；投影控制列不改變畫布縮放 |
| [Bespoke.js](https://github.com/bespokejs/bespoke) | 極小 core、plugin/theme 模組化、背景狀態可插拔 | 將背景 Pattern、surface、depth、type treatment 做成可組裝 profile |
| [DeckDeckGo](https://github.com/deckgo/deckdeckgo) | Web Components、rich templates、drag/resize/rotate、PWA editor | 編輯能力維持共用 runtime；視覺元件遵守相同 `data-edit-*` 契約 |
| [open-slide](https://github.com/1weiho/open-slide) | Agent-native、固定 1920×1080、Inspector、skills、靜態輸出 | 採用固定設計畫布、agent-readable assembly recipe、QA/Inspector 回圈；不改成 React-only |

## 結論：本專案需要的不是更多 Theme，而是組裝層

Theme 只回答品牌長相；Layout 只回答資訊放在哪裡。完整 HTML 畫面還需要回答：

1. 本頁使用哪一種背景場域與 Pattern。
2. 內容區要採對稱、偏軸、書脊、軌道、剖面或有機場域等構圖方法。
3. 卡片是平面、玻璃、紙張、印刷、輪廓線或無框資訊帶。
4. 標題如何對齊、換行、與副標建立寬度和重量關係。
5. 數據、流程、比較與引用要用哪一種 component treatment。
6. 內容密度不足時要放大與收合，而不是把框硬撐滿 Content Area。

因此正式公式改為：

```text
HTML Slide = Story Content
           + Theme Adapter
           + Layout Adapter
           + Composition Profile
           + Background Pattern
           + Surface / Depth Profile
           + Typography Treatment
           + Component Recipe
           + Editor Contract
```

## 不採用的做法

- 不用照片、點陣圖片或不可控的裝飾物件承擔 HTML 構圖。
- 不把每一頁都做成相同等高卡片陣列。
- 不靠螢光字、漸層字或奇怪文字外框假裝有設計感。
- 不讓周圍硬質裝飾侵入 Content Area；優先使用 gradient、pattern、shadow 與留白。
- 不讓投影 shell、編輯面板或工具列改變 slide scale。
- 不讓組裝 recipe 取代 Theme/Layout；它只負責兩者之間尚未被描述的視覺關係。

## 已確認的 Preset / Theme / Layout 決策

- 好看且通過人工驗收的案例，不再當成只能生一次的 Style Case，而是登錄為可獨立選擇的 **HTML Preset Theme**。
- Preset Theme 只綁定視覺語言，不綁定內容或 Layout；歷史案例的內容與頁序只作為參考範例。
- 自動 Theme 選擇先只從已驗收 Preset 抽取；其他 Theme 仍可手動指定，但在配色重新驗收前不進入預設隨機池。
- Layout catalog 完整公開；自動推薦可依 HTML 穩定度排序，但不得藏起可手動選取的 Layout。

## 實作入口

- 組裝 catalog：`prompt_system/renderers/html/assembly-catalog.yaml`
- PRESET 身分／公開 registry：`prompt_system/presets/catalog.yaml`
- 可重複套用的 Preset Theme 實作：`prompt_system/renderers/html/preset-themes.yaml`
- Layout 可見性與自動選擇池：`prompt_system/renderers/html/layout-catalog.yaml`
- 載入與驗證：`scripts/html_assembly.py`
- Preset Theme 驗證：`scripts/html_preset_themes.py`
- PRESET registry 與 Gallery 一致性：`scripts/html_preset_registry.py`
- 實際生成：`scripts/render_randomized_html_demo.py`
- 三份已驗收案例規格：`prompt_system/demos/html-theme-lab.json`
- 十份延伸案例規格：`prompt_system/demos/html-theme-lab-extensions.json`
- 編輯與匯出 runtime 原稿：`src/html-editor/edit-mode.js`
