# 簡報生產契約

這份文件整理目前已驗收的共用架構、排版原則與 Renderer 邊界。
它是跨 Image2、HTML、PPTX 的總覽；細節分別交給對應的 Renderer 規則。

## 文件分工

| 文件 | 唯一責任 |
| --- | --- |
| 本文件 | 跨 Renderer 的共同原則、優先順序與驗收底線 |
| `references/project-format-guide.md` | 七段式 assembled YAML 的格式 |
| `prompt_system/art_direction/README.md` | Story 與 Theme／Layout 之間的 Art Direction、scene grammar 與人工 gate |
| `references/renderer-adapter-contract.md` | Theme/Layout core 如何投影到三種 Renderer |
| `references/html-generation-rules.md` | HTML 畫布、文字、編輯器與輸出規則 |
| `references/svg-icon-generation-rules.md` | 內容語意 SVG icon 的來源、生成 grammar、解析與跨 Renderer 投影 |
| `references/html-layout-patterns.md` | HTML 各類資訊關係的排版模式 |
| `references/html-design-technique-library.md` | HTML 構圖方言、CSS 技法與使用界線 |
| `prompt_system/renderers/html/design-method.yaml` | HTML 內容關係分流、Theme 適用性、招牌構圖與跨頁 QA |
| `references/html-design-method-provenance.md` | 外部研究來源、採用範圍與授權邊界 |
| `references/pptx-generation-rules.md` | 可編輯 PPTX 的生成與驗收規則 |
| `references/pptx-background-master-workflow.md` | Image2 無字底圖與 PowerPoint 母片的實作流程 |
| `references/preview-qa-loop.md` | 正式 Image2 layout preview 的 QA 循環 |

新增規則時，先放進唯一負責的文件；其他文件只加連結，不複製同一段規則。

## 規則優先順序

1. 使用者當次明確指示。
2. `AGENTS.md` 的正式生圖、QA 與部署強制規則。
3. 本文件的跨 Renderer 生產契約。
4. `references/html-generation-rules.md`、`references/html-layout-patterns.md`、
   `references/pptx-generation-rules.md` 的 Renderer 細節。
5. Renderer adapter、demo 與 artifact。這些是投影或產物，不得反過來覆寫 core 規則。

若規則似乎矛盾，先依上述順序判斷；不要同時加上兩套互相拉扯的補償邏輯。

## 一句話架構

**一份內容，共用同一套 Theme 與 Layout core；Image2、HTML、PPTX 各自使用專屬 adapter 與 runtime payload。**

### Core 責任

- Art Direction 負責「整份作品往哪裡走」：敘事隱喻、參考方法、招牌手法、
  素材家族、場景節奏、禁用俗套與感知 QA。它位於 Story 之後、
  Theme／Layout 選擇之前，不得綁死成另一份 Layout 或 Theme fork。
- Theme 負責「長得像誰」：色彩、字體、材質、裝飾語彙與品牌氣氛。
- Layout 負責「怎麼讀」：slot、safe area、閱讀順序、對齊、視覺重心與資訊關係。
- Content 是每份簡報的當次輸入，不與某個 Layout 永久綁定。
- Content Plan 先建立 page id、實際文案、語意關係與內容 hash；正式 page content 不得包含
  `layout_id`、Layout-keyed copy 或由 Layout 名稱推導的項目數限制。
- Layout 選定後才建立逐頁 Composition Plan。Composition 可以重排欄列、間距與 renderer view model，
  但只能讀已完成的 page content，不得回讀完整 story 再補文案，也不得改寫 Gallery fixture store。
- `layout_content` 只保留給使用者明確提供的歷史 content manifest 相容入口；manifest 必須標成
  `legacy-layout-content-compatibility`。Preset demo 與 Gallery fixture 也必須走各自明示的隔離路徑。
- Renderer adapter 只負責把 core 語意投影到特定輸出，不是第二套 Theme/Layout 庫。

### HTML Preset Theme

- `prompt_system/presets/catalog.yaml` 是 PRESET 身分、能力、公開狀態與 Gallery 順序的唯一 registry。Theme Lab JSON 只保存隔離的案例內容；`prompt_system/renderers/html/preset-themes.yaml` 只保存乾淨、可重複套用的 HTML 視覺契約。
- PRESET Gallery 可以同時展示完整 Theme Lab 案例與可重複套用的 Preset Theme，但兩者必須用 capability 明確區分。只有 `reusable-preset` 可以被 renderer 當成可套用 Theme；`theme-lab-case` 本身只是案例證據。
- 經過人工驗收的 HTML 風格方向可重新整理成 **HTML Preset Theme**，作為可獨立選取、可重複套用的 Theme 身分；提升時必須重寫成視覺 token／recipe，不能把舊案例本身當 runtime source。
- Preset Theme 可繼承一個 Theme core 的穩定 token，但要有自己的精選配色、HTML assembly recipe、Pattern、陰影、材質與字體規則。
- Preset Theme 不得綁定內容、故事或 Layout；同一 Preset Theme 必須可套用到不同的 HTML Layout。
- Reusable Preset 定義不得出現 `source_style_case`、`example_story`、`example_layouts`、`content`、`layouts`、文字替換表或任意 CSS。舊 HTML、CSS、截圖與 artifact 只能作比較證據，new-deck 不得載入。
- HTML Preset Theme 預設只屬於 HTML renderer scope；不因此自動新增 Image2 或 PPTX adapter。只有使用者明確要求跨 Renderer 時才進行晉級。

### HTML Preset 重新製作

- 「重新製作」表示用當次內容重新建立頁面層級、構圖、content surface、跨頁節奏與互動結構，不是對既有 HTML 換色、覆寫 CSS 或批次轉換 DOM。指定的 exact URL／artifact 只能用於人工比較，不得成為 renderer runtime input；交付時保留舊版並另產生可辨識的新版本。
- 正式實作前先獨立寫出新的 `component recipe` 與跨頁貫穿元素；至少定義框線、透明度、材質、陰影／光暈、圓角或切角、留白與密度變體。不得複製舊 DOM、舊 selector、舊版 Layout sequence 或固定文案。
- 先完成 cover、一般內容頁、資訊密集頁三頁 pilot，只比較 Theme DNA、資訊階層、內容表面與背景材質；比較結果不能回填成舊 CSS import。三種密度未通過前不得擴張成完整 deck。
- 使用者確認方向後，先修改正式 renderer／Theme adapter，再生成版本化 artifact 與縮圖。不得覆蓋已交付版本，也不得把 artifact-only patch 回填成正式規格。

### HTML Theme／Preset 覆寫契約

- 完整 ownership 見 `references/html-css-ownership-contract.md`。Layout adapter／`renderer-base` 唯一擁有位置、寬高、Grid／Flex、gap、padding、margin、對齊、transform、overflow、writing mode、字級與行高；Theme／Preset 只擁有 appearance。
- Theme／Preset 可以提出不對稱構圖或 surface 的語意建議，但必須在 Layout 選擇階段解析成相容的 composition variant。materialize 後不得用 Layout-scoped selector 或晚載入 CSS 重排。
- `theme-appearance`／`preset-appearance` 不得使用 `data-layout-id`、`data-composition-variant`、頁碼／順序 selector、`.content`、`.el`、幾何 property、幾何 custom property 或 `!important`。
- 中心軸、surface／ink 與其他 semantic contract 必須用 computed style 驗證；semantic guard 只能回報 fail，不得在 Theme／Preset CSS 後附加另一組幾何規則把錯誤硬拉回去。
- 每個 style block 都要標記 `data-css-owner`。new-deck 生成前執行 source ownership validator，產出後再執行 Browser geometry invariant；任一 `.content`／`.el` 在開關 appearance 前後位移或尺寸差超過 0.5px，都屬 blocking failure。

### YAML 邊界

- Image2 正式生圖必須使用七段式 assembled YAML，並完整讀取後生圖。
- Art Direction 不新增 assembled YAML 的第八段；它依
  `references/project-format-guide.md` 的對應規則，合併到七個既有區段。
- HTML 與 PPTX 不強制先生成 assembled YAML；它們可以直接讀取
  Art Direction + Theme core + Layout core + renderer adapter + content manifest。
- 三種輸出共用的是語意來源，不是同一份 runtime 檔案。

### 隨機生成的可重現契約

- 隨機生成必須先聲明哪些維度隨機、哪些維度固定；manifest 至少記錄 seed、`randomized_dimensions`、候選池或其版本與抽選結果。
- 「由 Agent 自行選一個題目」不等於可驗證的隨機生成。當使用者只說隨機內容時，預設讓題目、敘事／內容結構與 Layout sequence 進入抽選；Theme／Preset 是否參與必須明示。
- 若 `randomized_dimensions` 為空、所有 Layout 都是 forced，或無法依 manifest 重現抽選，不得把產物標記為 random。
- Core Theme 與 HTML Preset 的身分必須寫入 manifest；要求 Preset 時不得靜默退回 Core Theme。
- 正式隨機 HTML 交付必須通過 `scripts/validate_randomized_html_manifest.py`；legacy manifest 可明確使用 `--allow-missing-pool` 做相容性檢查，但不得因此宣稱符合新的可重現契約。

### Art Direction Gate

- 多頁 deck 應先完成 Art Direction Brief 與 scene grammar，再依 scene role 選 Layout；
  不得先挑一排 Layout，最後才補一段風格形容詞。
- `ready-for-audition` 只能製作方向試演，不得標記為正式成品或部署。
- 只有 `approved-for-renderer`，且 machine 為 `pass`、human 為 `approved`，
  才能進正式 renderer 與發布流程。
- 外部案例只借方法；renderer handoff 不傳入參考圖版面、第三方截圖或未驗證素材。
- Technical QA 通過後仍需 Perceptual QA；機器只負責攔截，最終方向由人選定。

## 共用排版原則

### Content Area 是定位基準

- Content Area 必須在畫布中水平、垂直置中，並保留穩定安全邊界。
- 內容應直接以 Content Area 為定位參考；可以使用不可選取的 layout-only frame 管理既有版型幾何，但不得新增可選取、只為了置中的透明外層群組。
- 文字框的可選邊界要貼合文字實際尺寸；不得因為對齊而留下過大的透明空框。
- Content Area 只存在於生成與對齊計算，不屬於編輯物件。進入編輯模式後，物件清單、hit-test、
  選取框與右鍵選單都必須排除 Content Area；不得顯示或選到定位區外框。
- **定位與編輯是兩層契約**：renderer 可以先量測 Content Area 內所有可見內容的聯集，求出一組
  `dx／dy` 完成整體水平／垂直置中；這個聯集只是一筆幾何計算，不是編輯群組。位移可由既有、
  不可選取的 `data-edit-layout-only="true"` frame 承接，但首次開啟時不得因此多出任何可選取外框。
- 標題、副標、正文、註解、來源等鬆散內容各自維持獨立 `.el`；只有「拆開後就失去單一資訊單位」
  的卡片、流程節點、指標、圖表模組等，才輸出為 semantic module 群組。
- 可見聯集收合後，子物件原本的置中錨點只能生效一次；計算並寫回座標時，必須補償
  `translate`／`transform`，或先清除再使用正規化座標。必須以 `document.fonts.ready` 與 layout
  materialize 後的 computed bounding box 驗收，避免標題被二次置中推到畫布外。
- Grid／Flex 可以保留滿寬或滿高的排版 slot，但這類容器只能標記
  `data-edit-layout-only="true"`，不得同時是 `.el`、`data-edit-layer` 或 `data-edit-composite`。
  它只負責定位；真正可選取的是 slot 內有視覺或語意的子群組。
- 投影片分成 Content Area 與外圍留白帶。主要標題、正文、圖表、卡片與流程不得放在外圍；
  外圍只允許背景 Pattern、裝飾性文字、觀眾需要的頁碼／章節代號與其他非主要內容。

### 重心以「可見內容聯集」計算

- 主標、副標、正文、圖表或卡片先以實際可見邊界形成量測聯集，再判斷整體重心；量測聯集不得成為可選取群組。
- 稀疏內容先收合到實際尺寸，然後在可用區域內垂直置中。
- 內容較多時才向上下擴張；不得一開始就把色塊或群組撐滿 Content Area。
- 一般密度的自動擴張以 Content Area 高度的 82–88% 為柔性上限。
- 標題區與內文區必須共同平衡；內文為多列、多欄或多節點結構時，應在不破壞可讀性的前提下
  均勻使用可用寬高。不得把多個同級模組全部壓在左半，而在右半留下沒有構圖理由的大面積空白。
- 不對稱版面可以靠左或靠右，但另一側必須有圖像、材質、色帶或其他視覺重量來平衡。
  若另一側沒有明確 counterweight，主要內文的可見幾何應使用 Content Area 寬度的至少 68%。

### 文字階層

- 主標文字量不得大於副標；主標負責短主張，副標負責完整說明。
- 副標可用寬度應大於或至少等於主標，不得用過小字級撐出階層。
- 關鍵數字至少與所屬標題等大；文字較少時，數字應更大。
- Before／After、現況／目標、問題／解法等語意狀態標籤屬於模組標題，不是 caption；
  必須至少比同卡內文大 6px，且使用 700 以上字重。
- 卡片內可左對齊，但文字群的垂直中心要接近卡片中心。
- 固定高度文字方塊的預設垂直對齊為置中；auto-height／flow 文字框因無多餘高度，視同自然貼合。
  水平對齊不設全域預設，由 Layout／語意決定，renderer 不得擅自全部置左或置中。
- 每個 AI 生成文字層都必須明確輸出 `data-edit-vertical-align="center"`，並由共用 CSS 與編輯器
  套用相同的垂直置中語意；取消／重新群組、undo／redo、存檔與重新載入後都必須保留。
  只有使用者手動改為靠上或靠下時才覆寫此預設。

### 語意斷行

- 一行放得下時不得因為看到逗點就主動斷行。
- 只有量測後確定需要兩行以上，才優先尋找接近視覺中點的逗點、分號、冒號或句號作為斷點。
- 標點斷點必須讓前後兩段都保有足夠長度；標點太靠近句首、句尾，或斷開後上下明顯失衡時，維持自然換行。
- 不得留下單一字或極短詞孤立成行；作者已明確指定的換行則原樣保留。
- HTML 初始排版可使用平衡換行；使用者左右拉動文字框後改用自然換行，
  但文案中真實存在的 `<br>` 始終是作者指定斷點，不得與瀏覽器自然換行混為一談。
- HTML 四角比例縮放保留原始斷行；群組左右側調整先消耗成員內既有的左右留白，並維持各文字框目前行數。
  只有新根框已無法容納目前文字框跨度時，才把文字框限制在成員邊界內並啟用自然換行；不得因第一個像素的內縮立即換行，
  也不得改變字形比例。編輯模式可以淡色 `↵` overlay 標示 `<br>`，該圖示不得變成
  文案內容或出現在投影輸出。

### 資訊關係決定圖形

- 循環關係必須使用循環圖，不得以一排卡片代替。
- 線性流程使用連續節點與明確閱讀方向。
- `process-flow` 的 3–6 個水平節點必須依實際數量動態分欄，保持同一列，
  不得因固定 4 欄而讓第 5、6 步掉到 Note 區域。
- 線性流程的箭頭屬於 renderer 建構契約：箭頭頭部沿閱讀軸的長度不得超過節點間距的 40%，
  箭頭頭部不得遮住主要箭身或侵入節點；renderer 必須以明確座標單位 materialize，
  不得依賴會隨線寬隱式放大的預設 marker 單位。

### HTML 裝飾以環境層為主

- HTML 的背景層優先使用 Pattern、漸層、噪點、光暈與陰影建立深度。
- HTML 預設採 `pattern-and-geometry-only`：不得自動加入照片、插畫、裝飾性 SVG、
  圖示包、貼圖、Image2 preview 或投影片截圖。輔助設計只使用文字、色彩、Pattern
  與基礎幾何；只有使用者明確要求的必讀內容媒體可以進入已宣告的內容 slot。
- 內容語意 icon 是內容層的例外，不是環境裝飾：只有 content manifest／semantic slot 明確要求的 icon 才可進入投影片。Icon 可以被替換、移除與編輯，但不得反向決定 Layout、欄列數、slot geometry 或內容排序。詳細規則見 `references/svg-icon-generation-rules.md`。
- 內容 icon 預設採 per-deck family generation：在 build-time 收集整份 deck 的 icon intents，一次生成同一家族 SVG 並鎖定 deck-local manifest；HTML 開啟、編輯、投影與匯出時不得重新生成，也不得自動擴張成全域 icon library。

### HTML 先判斷內容關係，再選 Layout

- HTML 不以「這頁要放幾個框」作為第一個判斷；先辨識比較、循環、流程、層級、優先順序、
  證據或結論等內容關係，再依 `prompt_system/renderers/html/design-method.yaml` 選 Layout。
- 正式順序為 `Content Plan → Layout scaffold → per-slide Composition → renderer materialize`。
  Layout scaffold 只提供閱讀區域、方向、錨點與視覺重心；實際內容物件與 hash 在選版前已固定。
- 每頁必須有一個招牌構圖。若改成普通 Grid 就會失去差異方向、循環、層級、時間或主次等語意，
  代表招牌構圖有存在價值；若什麼都不會失去，就應簡化。
- Theme 選擇必須同時看 `best_for` 與 `avoid_for`，不得只因配色接近就套用。
- 每頁還要分別決定 composition variant、標題位置與內容表面；固定種子只負責讓結果可重建，
  不得讓十三份 Theme 共用同一個卡片／線條骨架。實際組合必須寫入 manifest。
- Pattern／Effect 必須標示相容情境、效能與可讀性風險；配色驗收問題固定寫成「配色是否突兀？」。
- 背景可使用漸層與光暈，但資訊文字預設使用單一實色；不使用漸層字、透明填色、混色模式或外發光製造字體變色。
- HTML-only 風格案例不得把 Image2 預覽圖或參考截圖當背景；除非照片本身是內容證據且
  Layout 明確要求照片 slot，否則 raster asset 不得參與構圖。
- 不得為了填補四周留白，額外加入無資訊功能的圓形、色塊、角框、貼紙或漂浮底板。
- 實體圖形只有在承載資訊關係、容器邊界或操作語意時才可出現；純氣氛裝飾不得成為可選取物件。

## HTML 生產契約

- 畫布固定 1920×1080；正式 Content Area 為 1728×888，四邊內縮 96px。
- AI 生成的投影片視覺文字最小為 36px，必須直接寫入產出 CSS／inline style；使用者手動編輯可低於 36px，儲存與匯出不得把手動值升回 36px。
- Layout 是閱讀方向、區域、錨點與視覺重心的 scaffold，不是項目數 schema。Layout 名稱或舊 recipe
  中的數量只可作相容提示；不得在選版前以項目數排除 Layout，也不得為符合名稱刪除內容。
- requested Layout 無法完整承載 primary items 時，Composition 必須保留原始內容並改用容量相容的
  1+N／其他語意相容 Layout，manifest 同時記錄 requested 與 resolved Layout。只有使用者明確授權
  才可摘要、合併或改寫內容；此時 `content_mutated` 必須為 true 並附 mutation ledger。
- 36px 是當頁 composition materialize 後的 blocking 驗證。renderer 必須依實際項目數、扣除
  padding 後的文字淨寬、正式字體行數與可用高度重算欄列與文字幾何，再做 Browser 檢查。
- 若 36px 文字在選定 scaffold 中放不下，依序在同一 scaffold 改用相容 composition recipe 或
  標題位置、調整 Content Area 內既有內容區尺寸與間距、精簡文案或拆頁；只有實際幾何仍失敗時
  才改用另一個語意相容 scaffold。不得把字縮到 36px 以下，也不得保留
  overflow、clipping、線條穿字或文字／物件重疊。
- 使用 Flex／Grid 計算初始排版時，項目數改變必須同步重算列數、列高與所有內部文字位置。
  不得讓 `grid-auto-rows` 自動新增列，卻繼續沿用只適用原列高的固定 `top` 座標。
- 可編輯性與 CSS 定位是兩個不同契約。每個 `data-edit-layer` 都必須另外宣告
  `data-edit-position="absolute"` 或 `"flow"`；不得因為文字可編輯，就一律套用
  `position:absolute`。卡片、面板與整列等 `.el` 物件根可以物化為 absolute geometry，
  但條列、表格儲存格及模組內文等巢狀文字必須以 `flow` 保留在父容器的正常排版流，
  讓父列高度、分隔線與後續內容依文字實際高度計算。
- 跨 renderer 的貼邊視覺採同一個正向語意：Layout／Art Direction 若把裝飾線或色帶定義為
  `anchored-edge`，HTML adapter 以 `data-edit-anchor="bottom"` 保留「跟著父模組下緣」的
  關係，editor 在父框改變後重新求解；PPTX adapter 則把同一段關係 materialize 成父模組
  內的 native shape 座標。兩者都不得把一次編輯產生的暫時 transform／座標快照當成新的
  設計來源。
- 每份生成的 HTML 都必須包含共用編輯框架，不可生成只能投影的特例檔。
- 投影片視覺層只保留觀眾需要的內容；Theme display name、Layout id、renderer 頁序等開發資訊
  只存在 `data-*` 與 manifest，不得生成右上角標籤或角落頁尾。觀眾頁碼若有需要，必須由
  content manifest 明確啟用；一般頁序由 player counter 提供。
- 投影／編輯模式切換不得改變瀏覽器視窗尺寸、DPR、全螢幕狀態或投影片內部的
  1920×1080 幾何。編輯模式可以針對扣除固定工具列與縮圖欄後的工作區，重新計算最外層
  viewer fit；這只改變整張畫布的等比預覽比例，不得讓投影片內容 reflow 或改寫物件座標。
- 編輯模式固定使用兩區 editor chrome：左側縮圖欄、上方主編輯工具列。左側縮圖可拖曳調整
  頁序；拖曳完成後縮圖編號、player counter 與實際投影片 DOM 順序必須同步更新，而且排序
  必須可復原、重做、保存草稿與匯出。復原與重做必須直接整合在這條上方編輯工具列，
  不得留在投影浮動列；模式切換入口置於編輯列末端，讓使用者清楚知道目前正在編輯或投影。
- 這兩區是並排而非上下堆疊：左側縮圖欄固定從 viewport 頂端延伸到底端，上方工具列從縮圖欄
  右緣開始。縮圖欄不得再以 topbar 高度增加 `padding-top`、`margin-top` 或等價空白；其 header
  必須貼齊 viewport 頂端，縮圖清單緊接 header 並使用到底端的全部剩餘高度。
- 物件選取工具不得合併到上方主編輯工具列，也不得增加主工具列高度；選取物件後才以獨立
  浮動視窗顯示。浮動視窗固定於 viewport，但定位基準必須是目前選取範圍：優先貼在選取範圍
  上方，空間不足時改放下方，並沿選取範圍水平中心對齊；只有在兩側空間都不足時才能在工作區
  內縮避讓。不得把面板固定停靠在主工具列下方或畫面底部。所有必要功能保持可見；目前選取
  目標不支援的功能 disabled 並以半透明呈現。
  上述工作區內縮避讓的唯一例外是：兩側皆無法容納完整面板時，改用 compact chrome-safe 模式，暫置於 editor topbar 已保留但未被主工具列占用的區域；
  面板仍須與主工具列分離，不得增加 topbar 高度，也不得覆蓋 canvas 或選取框；空間恢復後必須回到一般浮動定位。
  浮動視窗不顯示群組成員數量，也不提供文字框寬數字欄；文字框寬仍由左右控制點直接調整。
- 編輯模式即使位於瀏覽器全螢幕，選取物件後仍必須顯示外框、控制點與選取工具列；
  全螢幕不得被當成投影模式的同義詞。
- 投影模式只顯示上一頁、頁碼、下一頁、全螢幕與返回編輯入口；所有編輯、檔案
  與選取提示控制都必須隱藏，回到編輯模式後再恢復可用的編輯控制。
- 投影模式按 `Escape` 必須返回編輯模式；若瀏覽器當下為全螢幕，先讓瀏覽器退出全螢幕，
  再恢復固定 topbar、縮圖欄與編輯交互。編輯模式中的 `Escape` 仍只結束文字編輯或取消選取。
- 進入投影模式時，投影工具列預設完全隱藏；游標進入畫面底部感應帶時才浮出，離開感應帶後
  自動收起。顯示與隱藏只能使用 `opacity`、`transform` 與 `pointer-events`，不得改變畫布、
  Content Area、viewport 或 player scale。
- 投影與編輯工具列都不放常駐「說明」按鈕，也不在投影片底部或右下角疊放操作提示；
  編輯狀態只由固定 editor chrome、選取外框、控制點與選取工具列表達。
- 初始排版可使用 Flex/Grid 計算；排版完成後必須物化為可自由移動、縮放的物件。
- 一般 Content Area 在字體載入與物化後，必須以實際可見子物件邊界校正上下重心；不得只把
  一個宣告高度的外框置中。校正只能移動既有 frame，不得再包一層隱形置中容器。
- 文字與群組（包含 AI 生成時就建立的群組）的四角控制點放大縮小時必須鎖定長寬比；背景、文字、圖表、padding 與 gap
  同比例縮放，不得橫向拉寬、縱向拉高或觸發意外換行。
  群組與複合元件的左右側控制點採 staged content-aware resize：同步更新成員水平位置、根框與直接子層寬度；向內縮時先消耗左右留白、padding、gap 與子物件間距並鎖住目前行數。成員邊界確實容納不下時才縮窄文字框並自然換行；若仍將越界或互撞，字級與行高才按同一比例縮小。禁止在含文字的父層套用非等比 `scaleX`。
  群組與複合元件的上下側控制點同樣採兩階段壓縮：第一階段只調整框高、背景／底板、padding、gap 與子物件間距，並依既有垂直對齊重新分配 Y；第二階段只在文字即將越界或互撞時啟動，讓字級與行高按同一比例縮小。越界與互撞須在正式字體就緒後依實際 glyph bounds 判定，不得用 materialize 後為選取或對齊保留的透明文字框外框代替字形。不得使用 `scaleY` 壓扁字形，也不得以裁切、重疊或溢出換取更小外框。
- 群組側邊把手的自動縮字必須保留拖曳開始時的文字層級：可讀性底線依原字級比例與正式字體 glyph bounds 推導，不得為單頁寫死 px 特例。任一成員到達底線後，editor 必須夾住整群的相關軸尺寸，不得讓其他成員繼續被壓到難以辨識。這是自動 resize 的保護；使用者以字級欄直接指定數值時，系統仍必須保留該手動值。
  文字物件的四個側邊控制點只調整框架：左右只改框寬並保留原字級，文字框高度依實際內容更新；
  上下只改框高，不改框寬、字級或行距。Primitive Shape 仍可單軸縮放。
  左右／上下側邊控制點的每次 pointer drag 都必須只產生一次單軸調整與一筆 history：左右只改
  width， 上下只改 height；背景色塊、底板與群組選取框必須和容器同步改變同一軸。只有四角控制點
  才能做鎖定長寬比的整體縮放。
- 自動貼合文字框調整字級時，框寬要隨字級同步成長並維持原對齊錨點；Content Area 尚有空間時
  優先保留目前行數。使用者已手動指定框寬，或確實碰到 Content Area 邊界時，才允許自然換行。
  這項行為必須同時適用單選、多選與群組內文字。
- `Ctrl+G` 建立群組，`Ctrl+Shift+G` 只解除最外層；既有群組可再包成新群組。
- renderer 的初始物件樹只有兩種可選取單位：獨立 `.el`，以及 semantic module 群組。
  標題、副標、正文、註解、來源與其他鬆散內容不得為了定位而自動包成 `title-group`、
  `content-group`、`extra-group` 或整頁群組。
- semantic module 的判準是「拆開後會失去單一資訊單位」：例如同一卡片的底板、編號、小標、
  內文與狀態線，或同一流程節點的形狀、標籤與文字。module 外層是唯一 editable root；直接子層只標記
  `data-edit-layer`，取消群組或進入「編輯單件」後才轉成直接操作層。多個同級 module 預設仍是彼此獨立的群組，
  不再由 renderer 自動包成一個內容大群組。
- layout-only centering frame 可以承接整體 `dx／dy`，但不得是 `.el`、edit layer、composite、
  hit-test target、marquee member 或群組成員；首次開啟時使用者只能選到 frame 內的獨立物件或 semantic module。
- semantic module 進入「編輯單件」後，pointer-down 與 drag target 必須保持為目前選取的直接子層；
  `editableRoot` 只可提供群組脈絡。只有選取模式明確為整組時才可拖曳父模組。編輯器不得顯示
  子層選取框，卻在拖曳開始時把目標升級成父模組或連帶移動背景。
- semantic module 的外框必須貼合自己的可見子物件聯集；不得用整個 Content Area、固定滿寬帶、
  layout-only frame 或透明大框充當群組邊界。
- AI 生成的卡片、流程節點、圖表模組等多層物件預設就是 semantic module；內部可以保留
  `data-edit-composite` 作為 renderer 的幾何標記，但介面只呈現一般「群組」。取消該群組後，
  才拆成背景與文字／資料圖層；使用者仍可用 `Ctrl+G` 建立更多層手動巢狀群組。
- 巢狀群組的解除必須逐層進行，不能遞迴解散：外層手動群組解除後，直接子層的 semantic module
  仍維持群組身分、相對位置與尺寸。一次取消群組是一筆 history，不得把多層解散合併成同一筆操作。
- 取消 semantic module 或手動群組後，原容器可留在 DOM 維持幾何，但不得繼續顯示舊群組聯集框，
  也不得成為可命中的空殼；選取狀態必須切換成全部直接成員的多選，並以多選聯集框與成員細框
  清楚表示範圍。
- 群組／取消群組的 history 必須連同選取快照一起復原：undo 取消群組時立即回到整組選取，
  redo 時回到全部直接成員多選；選取框、成員框、工具列與控制點必須同步刷新，不能保留前一狀態。
- semantic module 與同層 footer／caption／其他物件重新組成手動群組後，外層 manual group 只提供巢狀群組脈絡，
  不得成為側邊縮放的原子幾何。editor 必須向下解析到實際擁有可見幾何的 leaf semantic modules，以及 composite 直接擁有的 visual／background surfaces，
  再以 leaf 聯集進行內容感知縮放與 history；不得只改 composite 外框而讓內層模組停在原位，造成控制點看似鎖死。
- manual group 進行垂直側邊縮放時，水平範圍相交的 leaf semantic modules 必須共同參與碰撞解算；群組最小高度包含各 member 的內容下限與相鄰 member 的基本 collision clearance。若已到下限，必須限制外框，不得允許相鄰模組重疊。
- 包含多個 leaf semantic module 的手動群組在每一次側邊縮放後，都必須以 Content Area 再次夾住實際 leaf 聯集；adaptive fit 若造成子模組變高或聯集上移，必須改用內容縮放／外框限制消除越界，不得產生超出 Content Area 的空白外框。
- renderer 產出的可視語意模組須標記 `data-edit-structure="module"`，並由 build-time validator 強制要求 `.el`、`data-edit-composite` 與第一個直接子層 `data-edit-layer="background"`。Browser QA 還必須實際驗證：普通點擊鎖定單一 semantic module；按一次「編輯單件」才進入其背景／文字圖層；「上一層群組」返回 module。單純檢查畫面、碰撞或 layer 數量不足以通過。
- 可視底板的 fill、border、radius、shadow 必須由上述第一個 `background layer` 實際擁有，且該 layer 必須具有覆蓋模組內容框的非零幾何；模組容器本身須保持視覺透明。只放置零尺寸或透明的名義 background，再把外觀畫在 `<li>`、`.ledger`、`.card` 等父容器上，視為 renderer 結構錯誤，因為取消群組後無法獨立命中與編輯底板。
- 正式群組的「外框成員集合」同時也是群組操作的權威集合。群組文字工具必須展開所有可見成員中的 `data-edit-layer="text"`／`metric` 後統一套用，包含直接掛在內容群組下的 footer、caption 或結論句；不得讓某成員被群組外框包住、可隨群組移動，卻被排除在群組字級、行高、字距、粗體、對齊與文字色彩操作之外。混合背景與文字的群組使用文字工具時只修改文字子集合；背景須先下鑽為單件後再修改底色。
- 所有承載內容語意或內容表面的物件都必須可選取：文字、數字、圖示、資料圖層、連接線、卡片
  底板、色塊與模組背景都必須是 `.el` 群組或明確的 `data-edit-layer`。模組背景必須是小群組的
  第一個直接子層；即使投影 CSS 使用 `pointer-events:none`，編輯器也必須以幾何 hit-test 在
  小群組解除後命中該背景。只有純排版 slot、Content Area 定位框與不承載內容的裝飾 pseudo-element
  可以不可選取。
- 文字與 metric layer 的 pointer hit-test 必須使用實際 glyph line rects，而不是整個透明 DOM box。
  游標落在文字 DOM 框內、但不在任何 glyph rect 上時，hit-test 必須繼續向下檢查同一模組的
  background layer；若下層沒有可選物件，才視為空白點擊。不得讓透明文字區永久遮住底板。
- 群組必須依「一個完整資訊單位」而非矩形範圍建立。流程節點的底板、標籤與文字可構成一個
  semantic module；跨節點的流程線、獨立註解或結論句維持獨立 `.el`，除非使用者手動將它們組群。
- 正式群組的完整可見聯集外框（包含成員間 gap／空白）都是該群組的命中範圍；普通點擊命中任何後代時，
  一律維持該位置最外層正式群組，不得以重複點擊隱性進入子物件。浮動選取工具列直接提供
  「群組／編輯單件／上一層群組」；每按一次「編輯單件」只開放下一層，每按一次「上一層群組」只返回一層。
  「取消群組」移到物件右鍵選單，並保留 `Ctrl+Shift+G`／`Cmd+Shift+G`。
- 按住 `Ctrl`／`Cmd` 點擊是另一個明確但暫時的深入入口：直接命中游標下最內層可編輯物件；若為文字，
  同一次點擊進入文字編輯。放開修飾鍵後，普通點擊仍回到整組優先；不得因此取消群組、改寫群組路徑或留下持續 edit scope。
- 編輯模式在物件上按右鍵時，必須顯示物件操作選單。右鍵命中目前多選範圍內的任一物件時，
  必須保留整個多選，不得退回單選；選單顯示「組成群組」，並沿用 `groupSelection()` 的巢狀群組、
  復原／重做與選取整組邏輯。「取消群組」沿用相同的最外層取消、巢狀群組與復原／重做邏輯。
  非群組物件可隱藏取消群組，投影模式不得攔截瀏覽器右鍵。
- 正式群組選取時只顯示一個外層整體選取框與控制點，不顯示子物件細框；進入「編輯單件」後才顯示該層物件框。
  未建立正式群組的多選則保留外層聯集框、控制點與每個成員自己的細邊框。
- 未建立正式群組的多選仍視為暫時操作群組。從任一已選成員開始拖曳時，所有已選成員必須維持
  相對位置同步位移；整次拖曳只建立一筆 batch history，undo／redo 必須一次還原或重做全部成員。
- 文字編輯中仍須保留貼合文字框的可見選取邊框；可隱藏 resize handles，但不得連邊框一起消失。
- 文字編輯造成自然換行、硬換行或內容寬度改變時，必須依目前 `text-align` 保持水平錨點：
  置左固定左緣、置中固定中心、置右固定右緣，不得一換行就讓整個文字框漂移。
- 文字編輯、拖曳或調框時，對齊投影片中心、Content Area 或其他物件錨點須顯示
  PowerPoint／Canva 式暫時直線／橫線；輔助線不可寫入內容、不可出現在投影與匯出結果。
- 物件對齊時，單選與正式群組都以完整 1920×1080 投影片為基準。正式群組視為一個邏輯
  物件，以整組聯集框計算單一位移並同步套用到所有成員，保留成員相對位置；只有尚未組成
  群組的一般多選，才以目前選取範圍為對齊基準。
- 浮動選取視窗依目標能力顯示：文字、圖形、背景與群組使用不同狀態標籤；AI 生成群組與手動群組
  使用同一個「群組」狀態，不得再顯示「複合元件」，
  且所有控制項保持可見；不適用的控制項必須 disabled 並以半透明表示，禁止保留可按下卻沒有結果的工具。
- 多選文字物件時字級控制不得消失；若字級不一致，以主要物件字級加 `+` 顯示（例如 `12+`），
  輸入新數字時一次套用到所有已選文字物件。文字或群組經四角等比縮放後，
  字級欄必須即時顯示縮放後的實際視覺 px，而不是 transform 前的 CSS 原始字級；歷史快照仍保存
  未乘視覺倍率的基礎字級，避免復原／重做重複套用縮放。
- 選取視窗的字體家族、主編輯列的整份預設字體與 active slide 背景色都是 editor user override：
  單件／群組字體寫入文字節點，整份預設字體只覆寫根節點的 `--font-display`、`--font-heading`、
  `--font-body` 並保留 `--font-mono`，背景只寫 `.slide.style.backgroundColor` 以保留 Pattern／gradient。
  element、document 與 slide 三種狀態都必須納入 undo／redo、草稿與 HTML 匯出。
- Preset 仍擁有初始 palette 與 font roles；shared editor 只能讀取已投影的 computed tokens 生成
  contrast-safe chrome 與色票，不得回寫 canonical Preset、修改 Layout 幾何或維護第二份 Preset 色表。
- in-session undo/redo 上限為 100 次。
- 字體系統使用 Google Fonts CSS2，同一份 HTML 只發出一組合併請求。

詳細規則：

- `references/html-generation-rules.md`
- `references/html-layout-patterns.md`

## PPTX 生產契約

- 正式預設為 `Image2 底圖 + native Placeholder` 的 hybrid PPTX，不是整頁壓平圖片。
- 每個 Theme 先準備六張無字底圖：`cover`、`toc`、`content-a`、`content-b`、
  `content-c`、`qa`。
- 底圖只能包含材質、漸層、光影、抽象形狀與邊角裝飾；禁止文字、數字、logo、
  假卡片、圖表、表格、面板、內容框與 Placeholder 外框。
- `blank_regions`、`decoration_zones` 與 Placeholder 必須在生圖前宣告，不得生圖後才猜空白位置。
- 背景圖必須位於 PowerPoint Custom Layout，一般 slide 只保留可編輯內容。
- 主標、副標、正文等 `content_groups` 要先根據實際文字高度縮合 Placeholder，
  再將整組於可用區域垂直置中。
- 文字需要多行時，先套用共用「語意斷行」規則；PPTX adapter 可在合適標點後加入軟換行，
  但不得把所有逗點轉成換行。
- 母片建立與內容填入在同一次建檔完成；不依賴不穩定的 saved-template re-import。
- 目前自訂 Custom Layout 底圖與 Placeholder 最後由 PowerPoint 原生物件模型寫入。
- PowerPoint 中手動大幅改字不會像 HTML 即時 reflow；需要重新執行生成器才會重算整組重心。

詳細規則：

- `references/pptx-generation-rules.md`
- `references/pptx-background-master-workflow.md`

## QA 契約

### 共用交付證據

- Release 判定必須同時對應任務語意、實際 artifact、source／manifest、renderer-specific QA 與未驗證項目；單一測試通過或檔案存在不能代表整項任務完成。
- 關鍵要求未驗證時狀態只能是 partial／未驗證。發布任務還必須驗證使用者指定的 exact URL／branch alias；部署命令成功不能替代公開網址內容證據。
- 任何 QA 腳本必須以文件列出的完整參數與可取得的 runtime 執行。缺少依賴、錯誤 profile、錯誤頁碼／selector 或只檢查函式存在，都只能記為未執行或失敗。
- QA 是 report-only Gate：同一次檢查只讀取 artifact、source、manifest 與 runtime 狀態，只能新增 QA report、
  screenshot 或隔離的暫時瀏覽器資料；不得覆寫受測 artifact、修改 renderer／CSS／manifest、重新進入
  生成器，或因失敗自動重試到通過。需要驗證 save／export 時，必須攔截寫入或使用明確的 disposable copy。
- QA 失敗時記錄規則、頁碼／selector、可觀察證據與初步分類後停止。修正必須另開實作步驟，修改
  canonical source 或正式規則、產出新 artifact，再啟動一輪新的 QA；不得把「檢查→現場補丁→再檢查」包成同一輪。

### Image2

- 每張正式圖必須有完整 assembled YAML。
- 生圖必須依序執行，不得並發。
- 依 `references/preview-qa-loop.md` 記錄 pass、needs-review 或 fail。

### HTML

- HTML 自動選版必須先經過 `prompt_system/renderers/html/layout-catalog.yaml`；共用核心
  Layout 仍保留給 Image2 / PPTX，但照片承擔主要構圖重量的半圖半文版型不得進入
  HTML 自動選版池。HTML-safe catalog 是 renderer scope，不得反向刪除共用 Layout。
- HTML Layout catalog 對使用者與模型必須完整公開所有 core Layout；自動選版依本次 `asset_policy`
  過濾。`with-image` 在 `pattern-only` 下不可選，在 `image-planned` 下可正常自動或明確指定，
  不得再把它定義成全域 `manual-only`。
- 全頁無 unintended overlap、clipping、overflow 與錯誤換行。
- 每頁必須在 `document.fonts.ready` 與初始 materialize 完成後，重新量測所有 AI 生成文字。
  任一可見文字小於 36px、超出自己的容器、與非背景物件碰撞，或被規則線／分隔線穿越，
  都是阻擋發布的 QA failure；不能只檢查是否仍位於 1920×1080 畫布內。
- 上下重心依可見內容聯集驗收，不比較 layout-only 外框；無 counterweight 的多模組頁也要檢查可見內容是否
  使用 Content Area 至少 68% 的寬度，避免沒有理由的半頁空白。
- Browser QA 必須確認 `[data-edit-layout-only="true"]` 本身不會出現在物件選取、marquee、右鍵選單、
  群組成員框或物件清單中；承接整體置中的 frame 必須保持不可選取。
- Browser QA 必須各自拖曳一次 east／west 與 north／south 控制點並量測兩個區間：一般區間先縮 padding／gap／子物件間距，字級維持不變；極限壓縮區間在文字將越界或互撞後，font-size 與 line-height 必須同比縮小。左右仍只改 width、上下仍只改 height，背景／底板與選取框同步改變指定軸，且任何區間都不得產生 clipping／overflow／overlap。只檢查函式存在或 CSS attribute 不算通過。
- 重新群組的 Browser QA 還必須逐對量測水平範圍相交之相鄰 semantic modules 的間距，不能只證明文字留在自己的 module 內。
- Browser QA 必須確認初始物件樹沒有 renderer 生成的 `title-group`、`content-group`、`extra-group`
  或整頁可選取群組，也沒有已退役的重複群組屬性、API 或工具列；標題、副標與鬆散內容可分別選取。
- Browser QA 必須對至少一個 semantic module 執行一次取消群組，分別點擊其文字與空白底板區，
  確認兩者都能命中各自圖層。任何可見內容
  只能靠 CSS pseudo-element 或容器 background 呈現、因而無法被選取，都視為阻擋發布。
- 投影截圖不得出現 renderer 自動注入的 Theme 名稱、Layout id 或角落頁碼。
- 稀疏內容不得無理由撐滿 Content Area。
- 背景裝飾不得以無資訊功能的硬質幾何圖形填滿四周；應以 Pattern、材質與陰影建立層次。
- `pattern-only` 與一般 Theme Lab 不得出現裝飾性圖片、插畫、SVG 或圖示包，圖片與外部媒體數量必須為 0；`image-planned` 只可加入內容所需且有來源紀錄的真實圖片。
- 上述限制針對裝飾性資產；已宣告、承載內容語意且可選取的 icon 不視為裝飾圖示包，但仍須遵守 `references/svg-icon-generation-rules.md` 的來源、可編輯與跨 Renderer Gate。
- 同一份 HTML 中，標題位置、內容表面與構圖變體必須有可辨識的跨頁變化；只換 Theme 色彩不算版面變化。
- 編輯框架、群組、縮放、存檔、匯出、復原／重做與模式切換必須實際操作驗證。
- 修改 canonical `src/html-editor/edit-mode.js` 後，先以 `scripts/sync_editor_asset.py --write` 更新 `artifacts/html-test/edit-mode.js` 相容副本；凡交付範圍包含 embedded editor，仍必須執行同步與 source-hash 驗證。Canonical source 通過不代表所有 self-contained HTML 已更新。
- 流程、循環、比較等關係必須使用正確語意圖形。

### HTML Layout 的媒體能力分流

- `prompt_system/layouts/*.yaml#media_requirement` 是所有 renderer 共用的正式分類來源；HTML catalog 只能投影並驗證，不得另存一份會漂移的判斷。`no-image` 包含文字、表格、流程、資料結構與原生語意圖示；`with-image` 代表構圖需要真實外部視覺素材。
- HTML 預設 `asset_policy=pattern-only`，只能從 `no-image` 選版。只有明確宣告 `asset_policy=image-planned`，表示交付前會補圖，才可自動或強制選用 `with-image`。
- 新建圖片背景 HTML 時，`.agents/skills/html-image-slide/SKILL.md` 是 Layout 生成前的獨立上游入口；它先產生圖片意圖與 handoff，再由 `html-pattern-slide` 消費。不得先完成 `pattern-only` Layout 才回頭附加圖片。
- 已有可編輯 HTML 只要附加／替換背景時，使用 `.agents/skills/slide-background-image/SKILL.md`；它從 foreground measurement 開始，保留來源 Layout、內容與幾何，不重新選版。
- `html-image-slide` handoff 至少要保留 `asset_policy`、`layout_selection`、逐頁 `image_role`／`safe_zone_profile`、素材 provenance 與預期的 `media_requirement`；`slide-background-image` 則要保留來源 HTML 與背景 run provenance。
- `with-image` 的壓力測試可只保留圖片區位置並用單純填色佔位；正式交付不得用 HTML、SVG 或 CSS 仿畫圖片，也不得在真實素材尚未補齊時宣稱完成。

### PPTX

- 檢查 master → Custom Layout → slide 關係、Placeholder 數量與可編輯性。
- 必須直接檢查 `.pptx` package/XML，分開報告母片功能、實體 Custom Layout 數量與 logical Layout adapter 覆蓋；不得從 YAML 的 `layout_name` 推論實體 layout 已建立。
- 背景圖只存在 Custom Layout，不得重複放在一般 slide。
- 逐頁用 PowerPoint 原生渲染檢查錯誤換行、裁切、重疊與文字邊界。
- 對有 `content_groups` 的版型，驗收實際內容群組中心與目標 region 中心。

## 反回歸清單

以下情況一律視為規則退步：

- 為了置中輸出可選取的固定外層群組；不可選取的 layout-only centering frame 不在此限。
- 以巨大文字框邊界代替文字實際邊界。
- 把 Grid／Flex 排版 slot、Content Area 或其他定位容器暴露成可選取 `.el`。
- renderer 為標題、副標、正文、註解或整頁內容自動建立 `title-group`、`content-group`、`extra-group` 或其他定位用群組。
- 群組外框包含 footer／caption／結論句，但群組文字工具未同步修改該文字，或 Undo／Redo 只還原部分文字成員。
- 可見底板畫在父容器，第一個 background layer 為零尺寸、透明占位或沒有承接 fill／border／shadow，導致下鑽後底板不可選。
- 少量內容自動撐到 Content Area 邊線。
- HTML 為了製造設計感，在四周堆疊無資訊功能的圓形、角塊、色條或漂浮底板。
- HTML 自動補入照片、插畫、裝飾性 SVG、圖示包、Image2 preview 或投影片截圖。
- 不同 Theme 或連續內容頁只換配色，仍使用同一組卡片、橫線與兩欄骨架。
- 循環關係被畫成線性卡片列表。
- 5 個流程節點因固定 4 欄掉到第二列。
- 5 筆內容套入只支援 2×2 的四格變體，再以自動新增列掩蓋容量不符。
- 為了保留既定構圖，把 36px 文字硬塞進過窄欄位、固定高度或固定 `top` 座標，造成穿線、重疊或裁切。
- HTML 缺少編輯框架，或投影／編輯切換改變視窗縮放。
- 群組四角縮小時文字先換行，而不是連同文字一起縮放。
- 群組左右拖曳只移動外框或成員位置，沒有同步改變成員與直接子層框寬。
- 群組左右拖曳以父層非等比 `scaleX` 拉伸文字字形。
- 群組向內拖曳從第一個像素就同比縮窄貼字文字框，尚未消耗左右留白便造成新增換行。
- 群組上下側拖曳未先消耗 padding、gap 與子物件間距，就直接縮小字級或行高。
- 群組上下壓縮後文字重疊、超出根框，或以 `scaleY` 壓扁字形。
- 以左右或上下側邊控制點拖曳時，整組仍等比縮放、另一軸跟著改變，或在內容容量尚足時就同步縮小字級／行高。
- 以四角放大群組或文字時出現水平／垂直非等比例拉伸。
- 受測 artifact 或 editor 仍出現已退役的重複群組屬性、API、同步選取工具或 `+`／`-` 控制。
- 外層手動群組取消後連帶拆散內層 semantic module，沒有保留直接子群組。
- 模組底板或背景在小群組取消後仍無法選取，或點擊空白底板區又命中整個 Content Area。
- PPTX 以整頁截圖冒充可編輯檔。
- PPTX 底圖內已經含有文字、卡片、圖表或 Placeholder 外框。
- 要求 HTML/PPTX 無條件載入 Image2 assembled YAML。

## 已驗收範例

- 三路共用內容驗收：`artifacts/acceptance-demos/brand-editorial-triple-route/`
- HTML：`artifacts/acceptance-demos/brand-editorial-triple-route/html/brand-editorial-triple-route-demo.html`
- PPTX Image2 底圖母片：`artifacts/pptx-backgrounds/brand-editorial/brand-editorial-background-master-demo-balanced.pptx`

## HTML renderer 的群組幾何產製契約

群組互動是否正確，首先由 HTML 撰寫結構決定，不得把責任推給事後 QA。

1. 整體水平／垂直置中由不可選取的 layout-only centering frame 承接單一 `dx／dy`；frame 不得成為 `.el`、群組或 hit-test target。
2. 每個 semantic module 必須直接擁有自己的 grid／flex 幾何，並具備 `.el`、`data-edit-structure="module"`、`data-edit-composite` 與 background-first children；中間不得存在有尺寸、會分裂幾何所有權的 layout-only slot。
3. 標題、副標、正文、註解與來源維持獨立 `.el`；只有單一卡片、節點、指標或圖表等完整資訊單位可以是 renderer 生成群組。
4. 任何有色底板、邊框或狀態面的頁尾結論框，若屬於一個完整資訊單位，必須是獨立 semantic module，由第一個直接 background layer 實際承載視覺表面。
5. side handle 的既有「延長」語意與 corner handle 的「等比縮放」語意不得因單一 deck 特例而改寫全域 editor。若某一頁與其他頁表現不同，先比對 DOM 結構與幾何所有權，再修 renderer。
6. 改版必須由正式 renderer 產出新版本 artifact，保留舊版本；禁止以複製舊 HTML 後局部補丁冒充重新製作。
7. build-time validator 是產製閘門；Browser QA 是 report-only 交付證據。兩者都要有，但 QA 不替代撰寫規則，也不得修補受測 markup。
### HTML semantic module 的選取、層級與 resize 契約

- renderer 產生的 semantic module 外框是 selection geometry 的唯一權威；editor 不得退化成內部文字 bounds。
- side handles 一律執行 staged content-aware resize：空白與間距先縮、文字碰到容量門檻後字級與行高再同比縮小；corner handles 一律執行 proportional visual scale。兩種行為不得因頁型或 Generated／Formal Group 模式而分歧。
- Release QA 必須實際進入至少一個 AI 生成 module 的「編輯單件」，拖曳文字／數字子層並量測：子層位移、父模組與 background layer 不動、選取框仍貼合子層，Undo／Redo 只還原或重播該子層操作。
- 可移動 semantic module 的中間祖先不得裁切內容；除非元素明確宣告為刻意裁切容器，否則從 module 到 `.slide` 的祖先都必須保持 `overflow:visible`。Release QA 必須逐層檢查 clipping ancestor，不得只檢查中心點 paint order。
- 被移動的 semantic module 必須以整個模組為單位提升 stacking level，並把 `z-index` 納入 move Undo／Redo。
- `visual`／`background` layer 不得走 text-edit display／alignment 邏輯；Theme 隱藏狀態必須在 edit mode 保留。
- renderer 的最後幾何步驟依序為 materialize、文字／孤行修復、visual balance；完成 balance 後不可再改變內容 bounds。
- HTML Release evidence 必須保存同一版 artifact 的 manifest（含 editor source hash）、static validator 結果、真實瀏覽器互動回歸（group／ungroup／resize／align／undo／redo）與投影截圖 QA。任何舊 fixture、錯誤 selector 或不適用的 legacy profile 只能標為 stale／未執行，不得把 aggregate fail 或未跑誤報為 pass。
- Release QA 必須跑跨頁 semantic-group matrix，不得只驗證單一 columns fixture。
