# HTML 簡報設計方法盤點與突破路線

日期：2026-07-26

## 研究問題

為什麼目前的簡報即使符合 Content Area、36px 字級、群組與溢位規則，仍常出現
「手動用 HTML 刻、線條不自然、像 AI Slop」的感覺？國外成熟品牌、出版與動態識別
的方法中，有哪些可被轉成 YAML-first 簡報系統的規則？

## 一、現有系統值得保留的能力

### 1. Renderer 邊界清楚

Theme、Layout、Content、HTML assembly 與 Editor Contract 已分層。這使後續可以新增
藝術指導層，而不用推翻現有 renderer。

### 2. 生成安全規則完整

- 固定 1920×1080 與 1728×888 Content Area。
- AI 生成文字不得小於 36px。
- Title Group 與 Content Group 分離。
- 孤字換行、溢位、對比、群組、匯出與投影模式已有正式規格。

### 3. Layout 已嘗試以語意選擇

現有 `design-method.yaml` 會區分 comparison、cycle、process、hierarchy、evidence 等資訊關係，
而不是只用頁面數或卡片數選 Layout。這個方向是正確的。

### 4. 已開始接受有來源的圖像

`assembly-catalog.yaml` 已將 raster asset 改為 `provenance-tracked-opt-in`，並允許
`licensed-archival-crop`。這是從純 CSS 裝飾走向真正 art direction 的必要條件。

## 二、反覆失敗的根因

### 根因 A：有組裝選項，沒有藝術方向

目前 catalog 可以選 composition、background、surface、depth、typography、component，
但這些是「如何畫」，不是「為何這樣畫」。

例如 `contour-field + pearl-haze + frosted-pearl` 可以合法組合，卻沒有回答：

- 這份簡報為什麼需要等高線？
- 等高線和故事中的哪個概念相連？
- 如果拿掉，內容或品牌意義損失了什麼？

缺少這一層時，組裝器只能從可用技法中挑東西補滿畫面。

### 根因 B：舊規格對圖像過度保守

`html-composition-assembly-research.md` 明確寫著「不用照片、點陣圖片或不可控的裝飾物件
承擔 HTML 構圖」；`html-generation-rules.md` 又以 Pattern、漸層、噪點、光暈、
shadow 為預設手法。這在早期有助於穩定輸出，但也迫使 renderer 用 CSS 模擬所有氣氛，
形成目前最明顯的「手刻 HTML」外觀。

新 catalog 已允許有來源的 archival crop，表示現在需要正式收斂這個矛盾：

> 不禁止圖像；禁止的是沒有來源、沒有角色、不能安全裁切與不能編輯的圖像。

### 根因 C：Layout catalog 仍有大量卡片母型

`html-layout-patterns.md` 中，TOC、cards-1-plus-N、KPI、流程與比較都有大量 card-first
範例。即使 Theme 改變，框架仍容易回到：

```text
標題
副標
等寬卡片 2–4 張
```

Theme 只改變色彩、圓角、陰影與表面，不會真正改變閱讀經驗。

### 根因 D：裝飾被定義成「內容之外的東西」

現有規格把裝飾限制在留白帶、背景層或結構線。位置限制是合理的，但如果設計流程在
排完內容後才問「周圍要放什麼」，那些元素自然會像貼上去的。

成熟系統更常見的做法是讓一個主概念同時決定：

- 字體行為。
- 圖像裁切。
- Grid。
- 邊緣。
- Motion。
- 圖形或 icon。

也就是沒有獨立的「裝飾階段」。

### 根因 E：QA 偏向技術正確

現有 QA 擅長抓：

- 溢位。
- 36px 下限。
- 對比。
- 孤字換行。
- Content Area。
- 群組與編輯契約。
- 連續頁骨架重複。

但尚未正式抓：

- 主視覺焦點是否落在正確位置。
- 邊緣是否比內容更吵。
- 留白是不是有意義，而不是剩餘空間。
- 來源不同的插畫是否混在一起。
- 視覺元素是否能說明概念來源。
- 是否出現典型 AI cliche。
- 同一份 deck 是否有張力與停頓。

### 根因 F：生成與挑選被當成同一件事

現在通常要求模型直接完成一份 deck。成熟的 generative identity 則把流程拆成：

1. 建立有限規則。
2. 產生大量變體。
3. 策展、比較、挑選。
4. 將選中的方向擴展。

缺少第 3 步，生成器會選最安全、最平均、最像模板的答案。

## 三、國外案例：可轉用的方法

### Pentagram — MoMA

來源：[MoMA identity](https://www.pentagram.com/work/moma)

官方案例強調固定 logo 位置、強 grid、戲劇化裁圖與一張主圖；跨多張應用時，
圖像與文字、彩色與黑白形成節奏。

可轉用規則：

- 每頁最多一個影像焦點。
- 裁圖是一級構圖決策，不是圖片塞進 slot。
- Deck-wide consistency 來自固定 anchor 與 crop logic，不是重複同一張底板。

### Pentagram — Cooper Hewitt

來源：[Cooper Hewitt identity](https://www.pentagram.com/news/cooper-hewitt-a-democratic-design-identity)

官方案例以 wordmark 和字體為強錨點，六欄 grid 可因內容組合成不同結構；
各 sub-brand 有不同表情，但仍共享系統。

可轉用規則：

- Grid 應該是組合工具，不是固定模板。
- Typography 可以承擔 identity，不必每頁都有插畫。
- 同一 deck 可有不同 scene density，但保持 anchor、type system 與色彩邏輯一致。

### Pentagram — New York Botanical Garden

來源：[NYBG identity](https://www.pentagram.com/work/new-york-botanical-garden)

案例以 gallery-like whitespace、wordmark、攝影與清楚 typography 平衡研究機構與自然題材。

可轉用規則：

- 自然題材不等於藤蔓、圓弧或花邊。
- 留白是讓影像呼吸的展覽空間。
- 一張有品質的圖像比多個象徵性 SVG 更有效。

### Pentagram — Garden Museum

來源：[Garden Museum identity](https://www.pentagram.com/work/garden-museum)

其有機形狀不是隨機 blob，而是從 Roberto Burle Marx 的景觀作品推導，形成可縮放的
完整詞彙。

可轉用規則：

- 形狀可以不完美，但必須有共同來源。
- 全套只使用一個形狀家族。
- 同一母形可透過 scale、crop、rotation 與 composition 產生變化。

### Fable — Strategy-centric identity

來源：[Fable](https://fable.design/)、[The Factory Cafe](https://www.fable.sg/factory/)、
[The Balance Company](https://www.fable.sg/the-balance-company/)、
[P+A Projects](https://www.fable.sg/pa-projects/)

Fable 把輸出定義為 strategic narratives 與 disciplined artistry 的延伸。
其案例常從品牌故事提煉一個可持續擴張的 grid、字體或符號。

可轉用規則：

- 先寫一句 narrative metaphor，再選視覺。
- Grid、字體與符號應共享同一幾何邏輯。
- 簡報的「邊緣裝飾」如果有需要，也應該是母題的延伸，而不是外加素材。

### DIA — Chaumont Biennale

來源：[Chaumont Biennale](https://dia.tv/project/chaumont-biennale/)

DIA 以自訂工具生成 meme 與 kinetic type 的意外組合，再進行挑選。

可轉用規則：

- Generative 不等於隨機；輸入與變異範圍必須被藝術方向限制。
- renderer 應先產出方向候選，不應直接把第一個合法結果當成正式 deck。
- 將「挑選」明文化為 workflow stage。

### DIA — Mailchimp

來源：[Mailchimp](https://dia.tv/project/mailchimp/)

當原插畫系統需要每次個別 art direction、無法擴張時，DIA 直接移除插畫層，
統一 typography，改以產品行為與 motion 建立個性。

可轉用規則：

- 外部插畫不是必選項。
- 若素材家族不能覆蓋完整 deck，就改用 type-led 或 image-led 系統。
- 個性不應依賴 decorative flourish。

### Studio Dumbar — Modyfi

來源：[Modyfi identity](https://studiodumbar.com/work/modyfi)

核心符號是會持續變化的 M；相同的 layer 與 angle 邏輯延伸到 grid、layout、shape、
number 與 icon。

可轉用規則：

- Signature move 必須能跨越多種元件，而不是只出現在封面。
- 一個母形可控制 layout、數字、icon 與 motion。
- 變化由規則產生，而不是每頁添加新裝飾。

### Figma — Auto Layout / Variables

來源：[Auto Layout](https://help.figma.com/hc/en-us/articles/360040451373-Guide-to-auto-layout)、
[Variables and modes](https://help.figma.com/hc/en-us/articles/14506821864087-Overview-of-variables-collections-and-modes)

Figma 將內容驅動尺寸、固定尺寸、Fill、Hug、min/max 與 variable mode 分開處理。

可轉用規則：

- 先區分內容驅動、容器驅動與固定視覺三種物件。
- Art direction 也可有 mode，例如 editorial-dense、editorial-airy、dark-exhibit，
  而不是產生新的 Theme fork。
- Layout adaptation 應回應內容量，而不是只調小字級。

### Component Gallery

來源：[Component Gallery](https://component.gallery/)

其元件定義都先說明功能，例如 Quote 是引用、Accordion 是展開資訊、Tabs 是減少 clutter；
元件有角色，不是表面風格。

可轉用規則：

- `card` 不是一個 page style，而是「需要獨立資訊邊界」時才使用的容器。
- 每個 component recipe 必須加上 `semantic_role` 與 `avoid_when`。

> 導入狀態（2026-07-26）：Phase 1 schema、驗證器與共用 handoff 已移至
> `prompt_system/art_direction/`；HTML 已能讀取 Theme／Layout sequence 與 scene metadata。
> 自動實作 signature move、三方向 contact sheet 比較與完整 Perceptual QA 仍屬後續工作。

## 四、新方法：Art Direction First

### 新公式

```text
HTML Deck =
  Story Architecture
  + Art Direction Brief
  + Reference Packet
  + Scene Grammar
  + Asset Family
  + Theme Tokens
  + Layout Constraints
  + Editor Contract
  + Perceptual QA
```

### Art Direction Brief 欄位

| 欄位 | 要回答的問題 |
|---|---|
| `visual_genre` | 這份作品屬於哪一種視覺出版物或場景？ |
| `narrative_metaphor` | 所有視覺從哪一句概念長出來？ |
| `reference_family` | 哪 3–5 個案例共享同一方向？ |
| `signature_move` | 全套最有辨識度、可重複變形的動作是什麼？ |
| `spatial_rule` | 主要 anchor、閱讀軸、crop 與留白怎麼運作？ |
| `asset_family` | 使用什麼來源一致的影像、插畫或 icon？ |
| `edge_behavior` | 邊緣是安靜、滿版、裁切、穿越還是作為索引？ |
| `typography_role` | 字體是主角、旁白、索引還是資料標記？ |
| `color_behavior` | 色彩是分類、情緒、時間、風險還是純品牌？ |
| `forbidden_cliches` | 這個方向明確禁止什麼？ |

### Reference Packet

每個方向固定包含：

1. 兩個同類型官方 case study。
2. 一個跨領域參考，例如雜誌、展覽、唱片、建築或動態識別。
3. 一個可合法使用的 asset source。
4. 一個反例，說明最容易滑向什麼俗套。
5. 一段「只借方法，不複製造型」的轉譯說明。

Pinterest、Godly、SiteInspire、Land-book 與 Minimal Gallery 可用來發現案例，
但只作 reference discovery；真正採用前要回到原作者或官方 case study。

## 五、Scene Grammar：不要再從卡片數量開始

每份 deck 先由五種 scene role 組成，再選 Layout：

### 1. Hero

- 一句主張。
- 一個主焦點。
- 可使用主圖、巨型 typography 或單一母形。
- 不使用平均分配的多卡片。

### 2. Index / Map

- 告訴觀眾怎麼讀。
- 可使用 column、spine、route、chapter field。
- 不預設每一章都需要有底板。

### 3. Evidence

- 證據、資料、案例或材料。
- 圖像、數據與註解應有明確主次。
- 最多一個主指標或主圖，其餘為支援。

### 4. Relationship

- 比較、流程、循環、層級、因果。
- 版面必須直接顯示關係，不用等高卡片掩蓋關係。

### 5. Pause / Close

- 控制節奏、形成記憶。
- 留白可以明顯增加。
- 不需為了填滿 Content Area 而加裝飾。

## 六、Asset-native composition

每個外部素材必須先被指定角色：

| 角色 | 定義 | 編輯性 |
|---|---|---|
| `primary-subject` | 封面或關鍵頁主視覺 | 獨立可移動物件 |
| `evidence-image` | 案例、照片、文件、材料 | 獨立可裁切物件 |
| `atmospheric-crop` | 低對比、只提供場域 | 背景層，不命中 |
| `identity-motif` | 從主概念推導的母形 | 可縮放群組 |
| `utility-icon` | 導向或語意標示 | 單一 icon family |

硬規則：

- 一份 deck 最多兩個素材家族。
- 同頁只允許一個主視覺家族。
- 來源、作者、授權、下載網址、在地檔案與修改方式必須寫入 manifest。
- 不混用不同線寬、端點、比例的 icon 庫。
- `atmospheric-crop` 不得承載必讀資訊。

## 七、實驗矩陣

### Pilot A：Artifact-led Editorial

- 主體：public-domain museum / archive 圖像。
- Signature move：單張圖跨邊裁切，文字使用固定 anchor。
- 失敗警訊：變成復古 scrapbook、素材與內容無關。

### Pilot B：Motif-led Identity

- 主體：一個由 narrative metaphor 推導的母形。
- Signature move：同一母形在不同 scene 中縮放、切片、翻轉與組合。
- 失敗警訊：母形只變成角落貼紙。

### Pilot C：Kinetic Typography

- 主體：variable font 的寬度、重量、方向或節奏。
- Signature move：主張的語意轉變直接反映在字形行為。
- 失敗警訊：只是把字拉長、傾斜或加 outline。

### Pilot D：Documentary Field Guide

- 主體：照片／標本／註記／索引。
- Signature move：圖像與註解共享一條觀察軸。
- 失敗警訊：退化為 dashboard 或卡片牆。

### 每個 Pilot 的最小驗證範圍

只做三頁：

1. Cover / Hero。
2. Comparison 或 Relationship。
3. Evidence 或 Data。

至少兩位人工 reviewer 選出方向後，才擴成完整 deck。

## 八、後續路線

### Phase 1：Research gate

- 將 `Art Direction Brief` 與 `Reference Packet` 做成 YAML schema。
- 建立 reference-only 與 reusable-assets 的分流。
- 任何 deck 在 schema 未通過前不得進 renderer。

### Phase 2：Visual audition

- 同一內容產生 3 個方向，每個方向只做 3 頁。
- 以 contact sheet 比較，不用單頁放大時的局部漂亮掩蓋跨頁問題。
- 人工通過一個方向。

### Phase 3：Renderer integration

- 只為通過的方向建立 adapter。
- 將 signature move 實作為可重用規則，而不是另存一份成品 HTML。
- 保留現有 Editor Contract、36px 下限與 Content Area。

### Phase 4：Perceptual QA

- 在現有 technical QA 後新增視覺品質門檻。
- 詳見 `20260726-perceptual-qa-proposal.md`。

## 九、這次研究的直接決策

1. 保留 YAML-first 與現有 renderer 邊界。
2. 不再把更多 Theme／Pattern 視為主要解法。
3. 新增 Art Direction Brief，位置在 Story 與 Layout 之間。
4. 所有外部素材先進 provenance catalog，再進 deck。
5. 生成與挑選拆成兩個階段。
6. 先做 3×3 的方向試演，不直接做完整十頁。
7. QA 從「不壞」擴展到「焦點、節奏、來源一致、非俗套」。
