# HTML 生成規則

這份文件只在「把 Theme core、Layout core、HTML adapter 與當次 content manifest
渲染成 HTML 投影片」時適用。HTML 不強制先組成 Image2 使用的七段式 assembled YAML。
跨 Renderer 邊界與規則優先順序見 `references/presentation-production-contract.md`。
它**不屬於** layout YAML、不屬於 dynamic content contract、不屬於七段式格式本身。
layout 仍只負責 slot 的 `[x%, y%, w%, h%]` 與對齊規則；字級、畫布、溢位防呆一律在這層決定。

---

## 總則：固定規則 vs theme 自由 vs layout 自由

本文件的規則是「結構約束」，不是「視覺答案」。每條規則都只鎖住不能出錯的部分，
視覺表現留給 theme 與 layout 發揮。分工如下，衝突時以本表為準：

| 決策 | 誰決定 | 說明 |
|------|--------|------|
| 畫布尺寸、96px 留白帶、content 容器 | 本規則（固定） | 所有 theme / layout 一律相同 |
| 字級「角色與範圍」 | 本規則（固定） | 角色字級表的 px 範圍不可超出 |
| 字級在範圍內取哪個值 | 內容密度決定 | 內容少取上緣、內容多取下緣（規則 2、4） |
| 溢位處置、垂直分佈策略 | 本規則（固定） | 規則 3、4 |
| 裝飾元素「可以出現在哪」 | 本規則（固定） | 規則 5 的位置約束 |
| 色票、字型、質感、裝飾長什麼樣 | theme 決定 | 來自 theme 檔的 `visual_base` + `decoration_vocabulary` |
| slot 結構、對齊、內容角色、構圖錨點 | layout 決定 | 來自 layout YAML；含刻意不置中的構圖 |
| 每頁實際文案與內容多寡 | content manifest／當次內容決定 | 內容層，不受本文件管 |

---

## 規則 0：先用內容關係選 Layout

- 正式入口是 `prompt_system/renderers/html/design-method.yaml`。
- 先把內容判斷為封面、導航、比較、循環、流程、層級、優先順序、證據、分布、停頓或結尾，
  再從對應候選 Layout 中選擇；不可先挑一個普通 Grid 再硬塞內容。
- 在選 Layout 前先完成 page-keyed content object；該物件不得含 Layout ID。選定 scaffold 後，
  per-slide composition 只能讀這個物件，不得回讀完整 story 或 Layout-keyed fixture 補寫文案。
- renderer 未收到 page composition payload 時才可使用 Gallery／矩陣 fixture；new-deck 每頁都必須
  標記 `data-content-binding="page-composition"`，不得靜默退回 `layout-fixture`。
- 每頁必須寫明 `signature_composition`（招牌構圖）與 `ordinary_grid_loss`（改成普通 Grid
  會失去什麼）。如果答案是「沒有」，就不要硬加圖形。
- Theme 必須有 `best_for`、`avoid_for` 與 `signature_compositions`，避免只換色卻沒有設計差異。
- 三方向視覺預覽預設關閉；只有使用者明確要求探索，或尚未選定 Theme 且不同方向會改變閱讀方式時才啟用。
- Pattern／Effect 必須標示相容情境、效能、可讀性風險、投影安全與透明度上限。
- 跨頁 QA 至少檢查六題：骨架是否重複、頁面節奏是否有變化、招牌構圖是否符合內容、配色是否突兀、36px 文字容量是否適配，以及是否存在非預期碰撞。
  結果使用 `keep / fix / quick-win`，不使用假精準分數。

### Preset 重新製作的產製順序

- 若使用者指定 exact URL／artifact，只保存原版畫面作人工比較；不得把其 DOM、CSS、內容、Layout sequence 或 selector 當成 renderer input，也不得以其他同名 Preset 代替。
- 以 `prompt_system/renderers/html/preset-themes.yaml` 的乾淨視覺契約重新定義跨頁 `content-surface recipe` 與貫穿元素，再用當次內容製作 cover、一般內容頁、資訊密集頁三頁 pilot。recipe 應使用框線、透明度、材質、陰影／光暈、圓角或切角與留白節奏形成家族差異；禁止所有頁共用同款白色方卡，也禁止以無資訊功能的大型圓形、斜線或漂浮背景補設計感。
- pilot 與原版只比較 Theme DNA、資訊階層與材質，不匯入舊素材；方向確認後修改正式 renderer／Theme adapter，再生成不覆蓋舊版的新 artifact。
- 字型就緒後的固定產製順序為：字級下限 → layout materialize → 孤行／文字修復 → visual balance → thumbnails。visual balance 後不得再執行會改變幾何的文字修復。

### Theme／Preset 覆寫契約

- 正式 ownership 見 `references/html-css-ownership-contract.md`。Layout adapter／`renderer-base` 唯一擁有幾何；Theme／Preset CSS 只能改變色彩、Pattern、材質、字體家族／字重、陰影與既有 background layer 的表面 paint。
- Theme／Preset 的 composition 建議必須在 Layout materialize 前解析成 Layout／variant；appearance CSS 不得使用 `data-layout-id`、`data-composition-variant`、頁碼／順序 selector、`.content`、`.el`、固定位置、寬高、Grid／Flex、gap、padding、margin、對齊、transform、overflow、writing mode、font-size、line-height 或 `!important`。
- 具有明確中心軸的內容必須由 data-edit-align-contract="center-axis" 或等價的 Layout contract 固定中心；Preset 不能以 CSS 修正座標。
- 具有 data-visual-surface-role 的元件必須成對維護 surface 與 ink。覆寫 background layer 的材質時，同一個語意規則也要驗證前景文字；不得把 accent 背景改成深色 surface，卻保留 accent-text 的墨色。
- Semantic contract 只做驗證，不得在 Theme／Preset CSS 後附加位置修正。Build 先跑 `scripts/html_css_ownership.py`；Browser QA 再比較 materialize 後開關 appearance 前後的 `.content`／`.el` 幾何，超過 0.5px 直接 fail。

### Layout 的圖片能力屬性

內容語意 icon 與 Layout 的責任邊界見 `references/svg-icon-generation-rules.md`：icon 必須由 content manifest／semantic slot 指定，可作為可替換、可編輯的內容 layer，但不得反向決定 Layout、欄列數、slot geometry 或內容排序。

### 可見文案必須有來源

- 投影片上的文字不是背景 Pattern。每個可見字串必須來自當次 content manifest，或是 renderer
  依內容結構在本簡報語言中產生的必要語意標籤；不得由 Theme、Preset、Layout 名稱或 renderer
  metadata 推導裝飾性英文。
- `speaker`、`org`、`kicker`、`eyebrow`、`meta`、`footer`、`attribution`、`caption` 與
  `panel-label` 一律選填。來源缺少或值為空時，整個 DOM 物件省略，不得輸出空殼，也不得補入
  `Lab`、`Studio`、`Concept`、`Profile`、`Demo`、`Wayfinding`、年份或其他看似設計的 filler。
- 繁中簡報的純英文可見短語預設不允許；數字／階段代碼、量測單位、email、URL、常見技術縮寫，
  或 content manifest 明確列入 `allowed_latin_terms` 的正式名稱除外。中英雙語簡報應明確宣告語言，
  不得靠 renderer 猜測。
- 正式 renderer source 先以 `scripts/html_visible_copy.py --renderer-source` 檢查寫死文字；產物再以
  `scripts/html_visible_copy.py --html ... --story ...` 驗證實際可見文案。任一失敗都阻擋產出，
  不能靠 QA 後處理刪字。

- 每個 `prompt_system/layouts/*.yaml` 必須直接宣告 `media_requirement`：`no-image` 或 `with-image`。這是 Layout Core 的正式能力欄位；HTML catalog 只保留相容投影，不是第二份分類來源。
- `no-image` 包含文字、表格、流程、資料結構與 HTML 原生／語意圖示；例如 `icon-grid-6` 不因為有圖示格就算圖片型。`with-image` 代表原構圖成立需要照片、插圖、地圖或人物等外部視覺素材。
- HTML 產製必須宣告 `asset_policy`。`pattern-only` 只能選 `no-image`；`image-planned` 代表交付前會補上真實圖片，因此可選兩類 Layout。未宣告時預設 `pattern-only`。
- `image-planned` 可以在製作中暫用單純填色佔位，但使用 `with-image` 的正式交付必須補齊真實素材；不得用 HTML、SVG 或 CSS 仿畫圖片冒充完成。
- 需要檢查分類時可用同一 seed 與內容分別輸出兩份 HTML；manifest 必須記錄 `asset_policy`、每頁 `media_requirement`、eligible pool、rendering policy 與各類數量。

### 圖片背景 HTML 的上游路由

- 新建 HTML 且使用者要求逐頁圖片背景、滿版／半版圖片構圖或 image-led HTML 時，先使用 `.agents/skills/html-image-slide/SKILL.md` 完成圖片意圖、SAFE ZONE、素材 provenance 與逐頁 handoff，再進入 `html-pattern-slide`。
- 新建 image-aware HTML 的 `asset_policy=image-planned` 必須在 Layout 選擇前宣告；`layout-selection=dynamic` 或明確的逐頁 Layout 決策也必須在 renderer 呼叫前確定。不得先以 `pattern-only` 鎖定一般版面，再用 raster 背景補救不相容的構圖。
- 已有可編輯 HTML 且只要求附加／替換背景時，使用 `.agents/skills/slide-background-image/SKILL.md`，從 browser-measured occupancy 開始；保留來源 HTML 的 Layout、內容與幾何，不重新選版或重生前景。
- `image-planned` 仍是混合候選池：內容關係不需要圖片的頁面可使用 `no-image`，需要照片／插圖／地圖／人物構圖的頁面才使用 `with-image`。只有「每頁都是圖片主導」才使用全頁 `with-image` 分流。
- 這條路由只改變 Layout 決策的輸入，不改變 HTML 可編輯性；背景仍須在前景量測後逐頁生成、內嵌與驗證，不能把整頁 HTML flatten 成圖片。

### 數據圖表只由 Python 資料契約產生

- 趨勢圖、長條／折線組合圖、資料註解圖、熱圖、雷達圖與其他數據圖表的權威來源是
  結構化 `ChartDataContract`；HTML renderer 與 demo 不得自行計算 plot 座標後拼接
  `<polyline>`、`<rect>`、`<circle>`、`<polygon>` 等 chart marks。
- 正式路徑固定為 `ChartDataContract → scripts/python_chart_renderer.py → deterministic inline SVG`。
  SVG 只是可選取的 semantic visual-layer 投影，數值、系列、單位、domain 與註解仍以資料契約為準。
- Python SVG 必須保留 `data-python-generated="true"`、`data-python-chart-engine="matplotlib"`、
  `data-python-chart-family`、Matplotlib version、`data-chart-spec-sha256`、`role="img"` 與
  `data-css-owner="renderer-base"`；不得包含 PNG／`<image>`／canvas 或把數值只留在 path 裡。
- 圖表標題、takeaway、來源與需要獨立編輯的敘事註解優先保留為 native HTML；Python chart 本體
  作為一個 visual layer，不把每條線誤稱為可即時編輯的資料物件。
- 流程箭頭、循環線、matrix 軸、map outline 與 connector 是 Layout 的結構幾何，不屬於數據圖表，
  可繼續由 renderer 使用 SVG path；它們不得承載只有圖表資料契約才知道的數值 mark。
- build-time Python SVG 不等於 live data editor。若未來支援即時改數值，正式路徑必須是
  `editor data table → localhost Python endpoint → SVG replacement → undo/redo/save/export`；
  `file://` 不得假裝可以直接重跑 Python。
- QA 必須驗證每個 production chart family 都帶 Python provenance、相同輸入輸出相同 SVG、
  無手寫 chart SVG source、無 raster fallback、字級／overflow／accessibility 合格，並保留 data hash。

## 規則 1：固定畫布 1920×1080 + 絕對定位

### 畫布

- 每一頁是一個 1920×1080 的固定容器：`position: relative; width: 1920px; height: 1080px; overflow: hidden;`
- 16:9，與專案 SVG wireframe（480×270）同比例，座標可直接換算。
- 整個畫布用 `transform: scale()` 縮放去貼合視窗；**縮放只發生在最外層 wrapper**，畫布內部一律維持 1920×1080 的絕對像素。

### 定位

- 畫布、`.content`、`.el` 模組根與已物化的 layout frame 使用 `position: absolute` 與絕對 px；`data-edit-layer` 不以這句推導定位方式，而是必須另外宣告 `data-edit-position="absolute"` 或 `"flow"`。
- 禁用 `rem` / `vw` / `vh` / `%` 字級。原因：固定畫布上百分比與視窗單位會讓字級漂移、行數不可預測，溢位防呆就失效。
- slot 的百分比座標換算成 px：

  ```
  x_px = x% × 19.2      (1920 / 100)
  y_px = y% × 10.8      (1080 / 100)
  w_px = w% × 19.2
  h_px = h% × 10.8
  ```

  例：slot region `[8, 58, 72, 20]` → `left:153.6px; top:626.4px; width:1382.4px; height:216px;`

### 邊界

- 內容不可碰到畫布邊緣；遵守 layout 的 `safe_area`。
- 禁用 `overflow: auto / scroll`、負 margin、用 transform 藏溢位。畫布固定，被裁掉的內容就是消失。

### 內容容器（content container）— 必須實作，不可省略

「主要訊息不落在畫布邊界地帶」不能只靠每個 slot 的 px 數字算對，必須在 HTML 結構上鎖死：

- 每張 `.slide` 除了畫布本身，一定要再包一層 `.content` 容器，代表內容安全框。
- `.content` 的 px 框是**從畫布邊界固定內縮的 px 值**，四邊一律內縮 96px，不用任何百分比或 slot 座標換算，所有 layout 共用同一組數字：

  ```
  MARGIN = 96px   （四邊固定，不隨 layout 或 slot 變動）

  content_left_px   = MARGIN                       = 96px
  content_top_px    = MARGIN                       = 96px
  content_width_px  = 1920 − MARGIN × 2            = 1728px
  content_height_px = 1080 − MARGIN × 2            = 888px
  ```

- 這一層跟 layout YAML 的 `slot` 百分比、`safe_area` 欄位無關——不要用 slot 聯集去反推 margin，也不要用 `x% × 19.2` 去算 `.content` 的框。`.content` 的框永遠是上面這四個固定數字，每張投影片都一樣。
- slot 的 % 座標換算出來的 px，如果超出 `.content` 的範圍（小於 96 或大於 1824／972），代表這個 layout 的內容跑出安全框，要在 36px 下限以上調整字級、擴大容器或砍內容，而不是放大 `.content`。
- 所有「主要訊息」元素（標題、內文、章節文字、圖表數據、KPI 數字……）都必須落在 `.content` 的座標樹內；可以是 `.content` 的直接子元素，也可以位於標記 `data-edit-layout-only="true"` 的 layout frame 之下，但不得位於 Content Area 外。可選取模組的座標一律相對其最近的 layout frame／`.content` 原點物化。
- 裝飾元素（邊角裝飾、logo 浮水印、背景紋理、貫穿全版的細線）維持 `.slide` 的直接子元素，可以貼齊或超出這層邊界，不受 `.content` 限制。頁碼或簡報名稱只有在 content manifest 明確把它們列為觀眾資訊時才可同樣處理；Theme 名稱、Layout id、renderer 頁序等開發 metadata 不得生成為可見投影片物件。

### 初始物件樹與語意模組契約

- renderer 首次開啟時只輸出兩種可選取單位：獨立 `.el`，以及 semantic module 群組。
  主標、副標、正文、註解、結論、來源與其他鬆散內容各自維持獨立 `.el`；不得為了定位或整體置中
  自動包成標題群組、內容大群組、額外群組或整頁群組。
- **定位層與編輯層分離**：生成時先量測 Content Area 內所有可見內容的聯集，求出一組 `dx／dy`
  完成整體水平／垂直置中。這個聯集只是一筆幾何計算，不是 DOM 群組；位移可由既有的
  `data-edit-layout-only="true"` centering frame 承接，但 frame 不得進入物件清單、hit-test、marquee、
  selection frame、context menu 或 group member set。
- **可見聯集物化的錨點守則**：物化 `left`／`top` 時，CSS `translate`／`transform` 只能生效一次。
  若物件使用 `left:50%`、`left:864px;translate:-50%` 或等價中心軸錨點，要嘛保留錨點並補償
  translate，要嘛改寫成正規化座標並清掉 translate；不得把已包含 transform 的
  `getBoundingClientRect()` 再直接寫回，造成二次置中。
- 這項幾何檢查必須等 `document.fonts.ready` 與 layout runtime materialize 完成後執行；
  `data-layout-ready="true"` 時，所有主要內容的可見 bounds 必須仍在 Content Area 內，預期中心軸
  偏差不得超過 2px。只看原始 inline style 或靜態 HTML 不算通過。
- 垂直排列的主標與副標可以位於同一個不可選取的 `title-flow-stack[data-edit-layout-only="true"]`
  內，以正常排版流相鄰並使用小型 spacing token；主標、副標本身仍各自是 `.el`。主標換行時，
  副標由排版流自然下移，不得以固定 Y 座標製造大段空白。
- `title-flow-stack` 的共用責任只包含垂直順序、內容高度與子物件 flow；水平對齊與 Layout-specific
  gap 由各 Layout renderer 明確宣告，不在共用 class 設定全域預設值。
- 使用 `title-flow-stack` 的 renderer 必須輸出 `data-layout-flow-align="start|center|end"`。`title-center`
  的 headline、分隔線與 supporting-text 一律使用 `center`，並各自標記
  `data-edit-align-contract="center-axis"`，讓 materialize 前後都維持同一中心軸。
- 若主標與副標之間存在規則線、徽章、icon 或其他設計物件，該物件可以是 stack 內的獨立 `.el`
  flow item。只有明確宣告為 overlay 的裝飾可以使用 absolute；overlay 與文字 glyph bounds 相交時，
  視為 blocking collision。
- `.content[data-content-area]` 是 renderer 的內部座標系與對齊參考，不是編輯物件。
- Grid／Flex 可以使用滿寬、滿高 slot 計算列高與欄寬，但 slot 必須標記
  `data-edit-layout-only="true"` 且不得是 `.el`、edit layer 或 composite。slot 裡真正承載內容的
  獨立物件或 semantic module 才可選取。
- 卡片、流程節點、指標、圖表模組等「拆開後會失去單一資訊單位」的多層物件，AI 生成時預設為
  semantic module。外層使用帶有 `data-edit-composite` 的 `.el[data-edit-structure="module"]`，並作為唯一 editable root；
  直接子層只使用 `data-edit-layer`，取消群組或進入「編輯單件」後才成為直接操作層；
  多個同級 module 彼此獨立，不再由 renderer 自動包成內容大群組。`data-edit-composite` 只是幾何標記，
  編輯介面一律顯示為一般「群組」。
- 背景色塊不得直接畫在群組容器上；必須獨立成第一個 `data-edit-layer="background"` 子層。
- 第一個 background layer 不能只是結構占位：它必須以 `position:absolute; inset:0` 或等價幾何填滿模組，並實際擁有畫面上可見的 fill、border、radius 與 shadow；父容器僅負責 layout geometry，視覺上保持透明。父容器有底色、但 background layer 零尺寸或透明，build-time validator 必須拒絕。
  純 Open 模組可使用透明背景層維持一致物件結構，但不得把透明 slot 的外框冒充可見模組邊界。
- 所有承載內容語意或內容表面的可見物件都必須可選取，包括文字、數字、圖示、資料圖層、
  連接線、卡片底板、色塊與模組背景。投影 CSS 可讓背景層使用 `pointer-events:none`，但 editor
  必須以直接子層的幾何範圍補做 hit-test；小群組取消後，點擊沒有文字覆蓋的底板區必須選到
  `data-edit-layer="background"`，不得回選 Content Area 或失去選取。
- 文字方塊預設 `data-edit-vertical-align="center"`。固定高度文字框以垂直置中呈現；auto-height／flow
  文字自然貼合。不得設定全域水平對齊，水平 left／center／right 由 Layout 與語意個別決定。
- 垂直置中是 renderer、共用 CSS、editor state 與儲存格式的共同契約。每個 AI 生成文字層都
  必須明確輸出該 attribute；取消／重新群組、undo／redo、存檔與重新載入都必須保留。
  只有使用者手動選擇靠上或靠下時才可改寫。
- 文字、icon、數字等可調整內容各自使用 `data-edit-layer="text|icon|metric"`，並以 `data-edit-position` 明確宣告 absolute 或 flow；目前 production adapter 對可自由編輯的 layer 預設 materialize 為 absolute，只有明確需要撐開父容器的內容才使用 flow。
- 一般點擊命中正式群組的任何子物件時，一律選取該位置最外層正式群組；群組已選取後，再點成員或群組框內空白仍維持整組，
  不得以第二次點擊或其他隱性狀態進入子物件。正式群組的完整可見聯集外框（包含成員間 gap／空白）都是群組命中範圍。
- 選取 AI 生成群組時，只顯示整組的大外框與控制點；**不顯示每個內層物件的「定位方框」**
  （避免畫面雜亂）。持續進入下一層必須明確按「編輯單件」；按住 `Ctrl`／`Cmd` 的單次點擊則可暫時直接命中群組內物件。
- AI 生成群組與手動群組共用同一套群組工具：群組、取消群組、編輯單件、上一層群組、
  巢狀群組、復原／重做、草稿與匯出。取消 AI 生成群組時可保留 renderer 外層容器以維持
  物化幾何，但命中與工具列必須切換成可直接選取內層；重新群組後恢復整組優先。
  取消完成當下必須選取該層全部直接成員；外層群組框消失，改以多選聯集框與各成員細框
  表示目前範圍。內層小群組仍保持完整，使用者可立即重新群組或批次操作。
- layout-only frame 是排版座標與 visual-balance 的輔助層，不是群組：它不得是 `.el`、`data-edit-layer` 或 `data-edit-composite`，本身不可命中；若以 `pointer-events:none` 讓 frame 穿透，必須明確恢復其後代 `.el` 的 `pointer-events:auto`，確保真實滑鼠仍可選取內容模組。
- layout-only frame 的存在不得計入群組層級：一般點擊命中鬆散物件時只選該 `.el`；命中 semantic
  module 時先選 module，按「編輯單件」才進入其背景／文字／資料圖層。frame 不得讓選取結果
  升級成透明大群組或同型物件多選。
- 手動群組的上下側縮放必須把水平範圍相交的 leaf semantic modules 放進同一 collision set；先重分配 spacing／padding／Y，再依實際 glyph bounds 縮小 font-size 與 line-height。若已無安全容量，限制外框，不得讓子模組互撞或溢出。
- 正式群組的對齊是「整組聯集框 → 投影片 1920×1080 邊界 → 單一 dx／dy → 全部成員」，不得把成員各自對齊到群組內部；alignment 與 group／ungroup 都必須和 selection snapshot 一起進 history。
- 進入「編輯單件」後，點擊同層其他直接子物件必須維持目前階層；遇到子群組時仍將該子群組視為單一物件，
  必須再次按「編輯單件」才可再進一層，並以「上一層群組」一次返回一層。
- 「編輯單件」狀態中的 pointer-down 與 drag target 必須是目前選取的直接子層。`editableRoot(selectedEl)` 只提供群組脈絡，不能用來取代實際拖曳目標；只有選取模式明確為整組時，才可保留父模組拖曳。選取框顯示子層、實際卻移動父層或背景，一律不得通過。
- 群組使用四角控制點縮放時，必須以外層做整體視覺比例縮放，讓背景、文字、圖表、padding 與 gap 一起縮放；不得逐層改寫 `width` / `height` 後觸發 Flex、Grid 或文字重新排版。
- 群組與複合元件左右側拖曳時，須同步更新成員 X 位置、根框與直接子層框寬；向內縮先消耗文字框左右留白、padding、gap 與子物件間距並維持目前行數。成員邊界確實容納不下時，才縮窄文字框並自然重排；若重排後仍發生文字越界或碰撞，字級與行高才按同一比例縮小。禁止對含文字父層使用非等比 `scaleX` 扭曲字形。
- 群組與複合元件上下側拖曳時，先同步改變根框、背景／底板與需跟隨容器之直接子層的高度，再按比例壓縮 padding、gap 與子物件間距，並依既有垂直對齊重新分配 Y。只有在空白已不足、文字即將越界或互撞時，才讓字級與行高按同一比例接手縮小；不得使用 `scaleY` 壓扁字形，也不得讓裁切或重疊成為壓縮結果。越界與互撞必須在 `document.fonts.ready` 後依實際 glyph bounds 判定，不得使用 materialize 為選取或對齊保留的透明文字框外框代替字形；透明框相交但字形仍有安全間距時，不得誤觸發縮字。
- generated composite 的單一群組側邊縮放也必須走與 manual group 相同的 post-fit boundary check：先用 leaf semantic modules 做碰撞與內容適配，再以 Content Area 夾住最後聯集；不能讓 fitter 透過增高子模組或把整群往上推來保留原 bottom，造成外框空白或越界。
- 重新群組後的 leaf semantic modules 必須視為同一個碰撞集合；群組可縮小的下限包含各模組內容下限與相鄰模組的基本 collision clearance。若再縮會造成水平範圍相交的相鄰模組互撞，必須限制群組外框，不得只讓每個模組各自通過文字邊界檢查。
- 左右／上下側邊控制點每次 drag 都是單一軸與一筆 history：左右只改 width，上下只改 height；
  背景、底板、群組選取框與必要的直接子層必須同步改同一軸。只有四角控制點可以鎖定長寬比
  做整體縮放。深入選取後才只調整該圖層。
- 所有群組必須支援階層：`Ctrl+G` 可把物件或既有群組再包成新的外層群組；`Ctrl+Shift+G` 只移除目前最外層，內部子群組不得被拆散。
- `Ctrl+Shift+G` 與右鍵取消群組都不得遞迴：解除外層手動群組後，直接子層的 semantic module、
  其尺寸與相對位置全部保留；再次對特定 module 取消，才拆成 background／text／data layers。
  每解除一層只建立一筆可獨立 undo／redo 的 history。
- renderer 產出的語意模組必須標記 `data-edit-structure="module"`，build-time validator 必須檢查：容器同時具備 `.el` 與 `data-edit-composite`，而且第一個直接子層是絕對定位的 `data-edit-layer="background"`。違反任一條時停止生成，不得留待人工 REVIEW 才發現。
- Browser REVIEW 必須實際驗證初始命中與逐層取消群組：鬆散標題／副標／正文各自可選；semantic
  module 普通點擊選整組，按「編輯單件」後才可選背景／文字圖層。只計算 `.el` 或 layer 數量、
  不執行點擊與取消群組，不得判定為通過。
- 群組外框所包含的可見成員必須與群組工具的作用集合一致。字級、行高、字距、粗體、對齊與文字色彩操作應展開所有成員後，套用到其可見 `text`／`metric` 子層；不得漏掉同群組的 footer、caption 或結論句。背景色只在下鑽選中單一 background layer 時修改，避免混合群組把底板與文字同時改色。
- Browser REVIEW 還必須實際拖曳 east／west 與 north／south 控制點並比對前後 computed state：一般縮放區間應先縮 padding／gap／子物件間距並維持字級；壓過內容安全高度或寬度後，必須證明 font-size 與 line-height 同比縮小、字形沒有非等比扭曲，而且沒有 clipping／overflow／overlap。四角縮放另案驗證。

### Semantic module 範例

```html
<div class="el card" data-edit-structure="module" data-edit-composite="card">
  <div class="card-bg" data-edit-layer="background" data-edit-position="absolute"></div>
  <div class="card-title" data-edit-layer="text" data-edit-position="flow">標題</div>
  <div class="card-body" data-edit-layer="text" data-edit-position="flow">內文</div>
</div>
```

### QA 執行契約：只檢查，不在同一輪修正

- 正式 QA 只讀取受測 HTML、source、manifest 與 runtime 狀態；允許新增的輸出只有 QA report、
  screenshot 與隔離的暫時瀏覽器資料。不得覆寫受測 HTML、修改 CSS／renderer／manifest、重新生成，
  或因失敗自動重試到通過。
- save／export 類互動必須攔截寫入，或在明確標記的 disposable copy 上執行；原始 artifact 的檢查前後
  hash 必須一致。
- 發現問題時，報告規則、頁碼／selector、可觀察證據與初步分類後結束該輪。修正是另一個實作步驟：
  修改 canonical source 或通則、產出新 artifact，再執行全新 QA。不得在同一個 QA pass 內形成
  「檢查→局部補丁→再檢查」的自動回圈。

### 禁止半版分割（不可省略）

`.content` 永遠是完整的 1728px 全寬，**不可以**為了塞裝飾面板而把它切成左右兩半
（例如只給內容 960px、右側 768px 讓給一塊裝飾色塊）。半版分割等於把裝飾的份量
拉到跟內容一樣重，違反「裝飾是氣氛、不是訊息」的精神（規則 5），也會讓文字內容
的可用寬度縮水近半，非必要地犧牲易讀性。

裝飾需要更多視覺份量時，用規則 5 的密度上限（1–3 組）跟背景層去做，不要用
「把內容擠到半邊」這個手法。照片類 layout（`photo-left-overlay-title-right`、
`cover-photo-frame` 等）本來就有照片佔較大區域的 slot 結構，那是 layout 本身定義的
內容角色（照片是內容，不是裝飾），跟這裡說的「為了裝飾而分割」是兩回事，不算
違規。

```html
<div class="slide" id="s1" style="...">
  <!-- 裝飾層：可貼邊，在 .content 之外 -->
  <div class="el decor-corner" style="left:1804px; top:56px; ...">...</div>

  <!-- 內容容器：固定四邊內縮 96px，每張投影片都一樣 -->
  <div class="content" style="position:absolute; left:96px; top:96px;
    width:1728px; height:888px;">
    <div class="el title" style="position:absolute; left:{title_x_px - 96}px;
      top:{title_y_px - 96}px; width:{title_w_px}px; height:{title_h_px}px;">{title}</div>
    <!-- 其餘主要元素比照辦理，都是 slot_px − 96 -->
  </div>
</div>
```

這一層是結構性保證，不是視覺裝飾——目的是讓「內容跑到邊界」在架構上不可能發生，而不是每次靠手算留白。

### 留白帶（margin band）的正式定義

`.content` 以外的四邊 96px 環帶稱為**留白帶**。它有明確的身分，不是剩下來的空白：

- 留白帶是**可選的裝飾與觀眾 metadata 區**：只有 content manifest 明確要求的頁碼、來源、mono 小標籤、chrome 細線或邊角裝飾才住在這裡（詳見規則 5）。renderer 的 Theme／Layout／索引資訊一律留在 `data-*`、manifest 或 player chrome。
- 留白帶**永遠不放主要訊息**：任何讀者必須讀到才能理解這頁的文字，都不允許出現在留白帶。
- 留白帶允許空著。空的留白帶本身就是設計的一部分，不需要塞東西。

---

## 規則 2：字級規範

字級綁定 1920×1080 畫布。先依 `page_type` + slot 的 `weight` 對應到「角色」，再從角色取 px。

### 文字方向（text orientation）

- AI 生成的可見文字預設一律使用 `horizontal-tb`；「垂直排列」只表示物件沿 y 軸堆疊，
  不等於旋轉字形或改用直排 writing mode。
- 只有 Layout Core 明確宣告某個文字 slot 的方向語意時，renderer-base／Layout adapter 才能
  使用其他 writing mode 或把文字旋轉 90°。Theme、Preset、Style Case 與 design dialect
  不得自行引入直向文字。
- 目前 release 的 Layout Core 沒有任何直向文字 slot，因此 source、生成 HTML 與打包 Gate
  都必須驗證 `vertical-*` writing mode 與文字 `rotate(±90deg)` 為 0。
- 書脊、側欄、時間軸與「vertical」命名 Layout 以水平短標、欄線、Grid/Flex 與物件位置建立方向；
  不把主要內容、metadata、聯絡資訊、章節號或比較 bridge 轉成直排。

### 字重語意（font-weight）

這裡的「字重／粗細」是 `font-weight`，與 `font-size`（字級大小）分開管理。字族由
Theme／Style Case 選擇；字重由文字的語意角色決定，不得因為換了字族就把標題、
小標與說明全部套成同一個粗細。

語意 token 固定如下：

| 語意 token | CSS weight | 使用方式 |
|---|---:|---|
| `heavy` | 900 | 核心標題、封面主標、關鍵數字與主要結論 |
| `bold` | 700 | 模組標題、比較欄標籤、需要明確分組的短句 |
| `normal` | 400 | 小標、一般標籤、來源與輔助資訊 |
| `light` | 300 | 說明、內文、補充敘述；投影或對比不足時回退至 400 |
| `medium` | 500 | 小尺寸 caption、工具性標籤或需要提高投影辨識度的文字 |

`heavy`、`bold`、`normal`、`light` 是語意名稱，不是 Layout Core 的
`weight: hero|primary|secondary|tertiary`。Renderer 必須先把 Layout／content 的語意角色
解析成 typography token，再輸出數字型 `font-weight`；不得把兩種 `weight` 混為同一欄位。

字族能力限制：

- `Noto Sans TC` 與 `Noto Serif TC` 可使用 `300–900`；標題預設使用 `heavy=900`。
- `Roboto Mono` 可使用 `300–700`，只用於編號、座標、工具列與等寬訊息；不得把它當成
  `heavy=900` 的標題字。Mono 需要強調時最多使用 `700`，若需要真正 Heavy，改用
  `Noto Sans TC` 或 `Noto Serif TC`。
- 不得依賴瀏覽器 faux bold／synthetic weight 假造缺少的字重。若目標字族不具備目標字重，
  必須依上述規則改用可用字重或改用支援該字重的字族。
- `opacity`、較深的文字顏色或更大的字級不能冒充 `light`、`normal` 或 `heavy`；驗收要看
  實際 computed `font-family` 與 `font-weight`。

### 角色字級表

| 角色 | px 範圍 | font-weight | line-height | 用途 |
|------|---------|-------------|-------------|------|
| display | 120–180 | 900 (`heavy`) | 1.05 | 封面主標、整頁金句 |
| section | 88–120 | 800–900 (`heavy`) | 1.10 | 章節大標 |
| page-title | 52–80 | 800–900 (`heavy`) | 1.15 | 內容頁標題 |
| module-title | 36–52 | 700 (`bold`) | 1.20 | 模組 / 卡片標題 |
| subtitle | 36–44 | 400 (`normal`) | 1.30 | 副標、framing 句 |
| body | 36–40 | 300 (`light`)，必要時 400 | 1.35–1.50 | 內文、說明 |
| caption | 36–40 | 400 (`normal`)，必要時 500 | 1.20–1.35 | 標籤、來源、編號小字 |
| mega-number | 160–360 | 900 (`heavy`) | 1.00 | 裝飾用大型數字 |

AI 生成硬下限：投影片視覺層的所有文字不得小於 36px。這個下限在 renderer 寫出 CSS／inline style 時落實，不能只靠載入後臨時放大。編輯器介面文字不屬於投影片視覺層。

手動編輯例外：使用者進入編輯模式後可以主動把字級調到 36px 以下；儲存或匯出時必須保留該手動值，不得重新套用 AI 生成下限。

### 36px Composition 適配（先選 scaffold，再驗證）

36px 是 AI 產製的字級下限，也是當頁 composition 的 blocking 驗證；它不是 Layout eligibility
constraint。renderer 先依內容關係選擇閱讀 scaffold，再把已完成的 page content 交給當頁 composition 重排。
Layout 名稱或舊 recipe 的項目數只可作相容提示，不得用來預先排除 Layout 或刪除內容。

每個已 materialize 的 composition 至少要檢查：

- primary items 是否未因 Layout 名稱或舊數量提示被刪除，且欄列結構已依實際數量重算。
- 每個文字容器扣除 padding、編號、icon、軸線與相鄰欄位後的淨寬。
- 依正式字體、36px 下限與角色 line-height 預估的行數和文字高度。
- 標題、副標、模組標題、內文與列點各自的高度預算，以及彼此的最小 gap。
- 固定規則線、分隔線、背景層與文字可見邊界之間是否會相交。

### 可視容器的基本內容內距

- 表格儲存格、卡片、色塊、徽章與其他具有可視邊界的容器，必須使用依文字角色縮放的
  content-inset token；不得讓文字 glyph bounds 直接貼住背景、邊框或裁切邊界。
- content inset 使用相對字級的 spacing token，不以單一固定 px 套用所有元件。密度較高的表格可以
  使用較小 token，但不得降為零。
- 色條、icon、編號、缺口等 leading ornament 必須在一般 content inset 之外另外保留空間；
  ornament 自身的寬度不得冒充文字內距。
- leading ornament 的讓位量必須由同一個元件 token 同時控制 ornament painted bounds 與內容起點。
  同列模組需要欄位對齊時，所有列一律保留該組 ornament 的最大 painted width，再加上角色
  content-inset token；不得只替被遮住的單列補一個一次性 `left` 或 margin。
- 空間不足時先調整欄寬、容器尺寸、文案或裝飾，不得把 content inset 壓到低於角色 token。

### 座標軸與端點標籤的保留空間

- Matrix／chart 的 plot field、軸線與端點標籤必須是三組可分辨的幾何。plot field 只能使用扣除
  label band 後的剩餘範圍；端點標籤不得以負 margin、重疊定位或合併成一個跨象限文字框壓在
  plot field 上。
- 水平軸與垂直軸的每一個端點都必須保留獨立 label object。正式字體與 36px 下限套用後，
  renderer 必須用實際 glyph bounds 驗證 label 留在自己的 label band，且不與象限內容、
  plot border、軸線或其他端點標籤相交。
- label band 的厚度由端點文字實際尺寸與角色 spacing token 推導；不得為所有 Matrix
  寫死同一組座標。Theme 可以改變標籤方向、對齊與線條語彙，但不能取消這段保留空間。

若 composition 不通過，處置順序如下：

1. 在同一 scaffold 內改用相容的 composition recipe、header placement 或欄列結構。
2. 在 1728×888 Content Area 內擴大既有內容區，或降低非必要的 padding／gap；content inset 與標題基本 spacing token 不得降為零，也不得新增第二個 Content Area。
3. 精簡文案或拆成新頁，並重新執行容量檢查；不得只為符合 Layout 名稱減少項目。
4. 角色字級原本高於範圍下緣時，可以在維持視覺層級的前提下降低，但不得低於 36px。
5. 只有正式字體與 Browser 幾何驗證仍失敗時，才改用另一個語意相容 scaffold。

項目數改變時，Grid／Flex 的列數、列高與內部文字幾何必須一起重算。禁止讓容器使用
`grid-auto-rows` 增加新列，內部標題與內文卻仍沿用只適用舊列高的固定 `top`。

所有量測必須等待 `document.fonts.ready`。正式字體完成後若出現文字／文字、
文字／物件、文字／規則線碰撞，或任何容器 overflow、clipping，該頁必須阻擋輸出；
「字級已達 36px」不能作為接受跑版的理由。

### weight → 角色對應（依 page_type）

| page_type | hero | primary | secondary | tertiary |
|-----------|------|---------|-----------|----------|
| 封面 / 引言 | display | module-title | subtitle | caption |
| 章節頁 | section | module-title | subtitle | caption |
| 內容頁（目錄 / 模組 / 圖表 / 圖文）| page-title | module-title | body | caption |

實際 px 由溢位防呆（規則 3）在範圍內收斂；範圍上緣是「內容塞得下時的理想值」，下緣是「塞不下時可退到的底線」。

---

## 規則 3：垂直預算公式（溢位防呆）

寫 JSX / HTML 前先算，不靠事後裁切。

### 公式

每個 slot 是一個垂直預算盒。盒內文字堆疊的高度必須塞進 slot 的 px 高度：

```
region_h_px = (slot.h% / 100) × 1080

block_h = Σ_each_line( font_px × line_height )
        + Σ_gaps( 元素間距 )
        + padding_top + padding_bottom

要求： block_h ≤ region_h_px
```

換行也算行：一段文字若會折成 N 行，就用 N 計入。中文每行可容字數 ≈ `slot_w_px / font_px`。

### 塞不下時的處置順序

1. 回到當頁 composition，在同一 scaffold 內改用相容的 recipe／header placement／欄列結構。
2. 在 Content Area 內擴大既有內容區，或降低非必要的 padding／gap；不得犧牲 content inset 與標題基本 spacing token。
3. 仍不行 → 減少行數：縮短文案（砍字，不是縮成更小字）。
4. 還是不行 → 把這塊內容移到新的一頁。
5. 角色字級原本高於範圍下緣時才可向下收斂，但不得低於 AI 生成硬下限 36px；調整後必須重新量測。

永遠不要用捲動或裁切換取「塞進去」的假象。

### 列點補充規則（沿用內容設計規則）

- 一頁是「標題 + 內文」**或**「標題 + ≤5 條短列點」，不可兩者並存。
- 每條列點必須單行不折行；會折行就砍字或拆頁。

---

## 規則 4：垂直空間分佈（避免重心偏上）

規則 3 解決「內容太多塞不下」；這條解決反過來的問題——內容實際高度明顯小於
`.content` 容器高度（888px）時，不能放任內容照最小尺寸從頂部往下疊、疊完就停，
底下留一大塊死空間。那樣整頁視覺重心會全部堆在上半部。

### 判斷時機

寫完一頁的 HTML 後，檢查：`Σ 內容區塊高度 + Σ 目前間距` 是否明顯小於
`.content` 的 888px（例如少了 150px 以上）。是，就要用下面策略之一處理，
不能讓多出來的空間直接變成疊在最底下的死白。

### 三種分佈策略（依內容性質選用，可疊加）

1. **均勻拉開間距** —— 適合列表 / 多節點內容（TOC 列表、process steps、
   卡片陣列）。把目標範圍內的剩餘高度平均分配到各元素之間的 gap（或用
   `justify-content: space-between` / `space-evenly`），讓內容均勻分佈，
   但不得無條件一路撐到 Content Area 邊線。

2. **整體垂直置中** —— 適合單一訊息 / 稀疏內容（quote、單一大標題、
   封面型頁面）。把整塊內容（標題＋內文）視為一個整體單位，在容器內
   垂直置中，上下留白對稱，而不是貼齊容器頂部。

3. **放大元素本身** —— 適合字級、icon、卡片本身有彈性空間的內容。
   不夠高就把該角色的字級/icon 尺寸/卡片高度取到角色字級表（規則 2）
   的**上緣**，而不是只取下緣塞好塞滿就好。規則 2 說的「上緣是理想值、
   下緣是塞不下時的底線」——內容偏少時就該取上緣，不要預設取下緣。

### 選用建議

列表型內容優先用策略 1（均勻分佈），可以同時搭配策略 3（字級/卡片
一起取上緣）；單一訊息型內容用策略 2（整體置中）。三者不互斥。

### 自動擴張的柔性上限

- Content Area 仍固定為 1728×888，不得修改。
- 稀疏或一般密度內容，自動擴張先以 Content Area 高度的 **82–88%** 為目標，
  並在 Content Area 內垂直置中，保留上下呼吸空間。
- 中密度內容可放寬到約 **90–93%**；高密度內容為避免溢位可到 **95–100%**。
- 這是內容組合框的柔性上限，不是新增或縮小 Content Area。只有內容確實需要時
  才接近安全邊界，不能因為「有空間」就把卡片、圖表或列表硬拉滿。

### 水平使用率與標題／內文平衡

- 標題群組與內文群組要共同形成重心，不能只把標題排好後讓多列內文全部縮在左半。
- 當內文包含 3 個以上同級模組、且空白側沒有明確圖像／色帶／資料圖形 counterweight 時，
  可見內文聯集應使用 Content Area 寬度至少 68%。不足時先拉寬欄位、增加合理 column gap、
  調整 composition variant 或重新分配欄寬；不得用不可選取的透明大框虛增使用率。
- 刻意的偏置構圖可以例外，但 manifest 必須記錄 counterweight／anchor，Browser QA 要量測真正可見物件。

### 重心驗收標準

分佈完成後，用實際幾何驗證（preview_eval 量測，不憑感覺）：

```
top_gap    = 第一個內容區塊.top − content.top(96)
bottom_gap = content.bottom(984) − 最後一個內容區塊.bottom

要求： |top_gap − bottom_gap| ≤ 100px
```

也就是內容整體的上下留白差不得超過 100px。超過就回頭重新分配 gap 或位置。

HTML runtime 必須在字體載入與 auto-layout materialize 完成後，量測真正可見的圖文子物件
（不以 `.prod-frame` 宣告高度、透明 slot 或 SVG connector 畫布代替），再移動既有
`.prod-frame` 讓上下 gap 平衡。這一步不得新增第二個置中容器；初次物化後即固定為數值座標，
使用者後續自由編輯時不自動回排。

**layout 例外**：若 layout YAML 的 `visual_balance` 明確定義了偏置構圖
（例如 `hero-fullbleed` 的文字集中左下、`chapter-number-bg-left-title-rule`
的大數字偏右），則以 layout 的構圖錨點為準，不套用置中驗收。這是 layout
的發揮空間——本規則只防「沒有理由的重心偏上」，不禁止「有意圖的不對稱」。

---

## 規則 5：裝飾性元素規範

### 內容語意 icon 的例外邊界

- 本節禁止的是裝飾性 SVG／圖示包；已宣告、承載內容語意的 icon 可進入 `no-image` 的內容 slot。
- 語意 icon 必須可選取、可替換，並位於 semantic module 的 `data-edit-layer="icon"` 或 `data-edit-layer="visual"`；不得只放在 pseudo-element、背景或不可命中的容器中。
- Icon 不得承擔 Layout 幾何責任：不得由 icon 自身 bounds 反向改寫 grid、stack、欄列數、slot geometry 或內容排序。
- renderer 不得為了填補留白、建立風格或自動湊數而加入 icon；沒有 icon 時，文字與其他內容仍應成立。
- 來源、recipe、跨 Renderer 投影與 QA 依 `references/svg-icon-generation-rules.md` 執行。

裝飾是「氣氛」，不是「訊息」。這條規則鎖住裝飾的**位置與職責**；
裝飾的**視覺長相**（顏色、線條粗細、形狀語彙）完全由 theme 決定，
取自 theme 檔的 `decoration_vocabulary`；Theme 不保存 renderer geometry。

### HTML 預設手法：Pattern 與陰影優先

- HTML 的預設資產政策固定為 `pattern-and-geometry-only`：投影片內容不得載入裝飾性照片、
  插畫、SVG、圖示包、貼圖、Image2 preview 或投影片截圖。輔助設計只使用文字、色彩、
  CSS Pattern、線、圓、弧、矩形與其他基礎幾何。
- 只有使用者明確要求，而且照片或媒體本身就是必讀內容證據時，才可使用 Layout 已宣告的
  內容媒體 slot；這不是 Theme 裝飾，也不得被 renderer 自動補入。
- 背景深度優先使用 Pattern、漸層、噪點、光暈、透明度與 `box-shadow` / `text-shadow`。
- 漸層、光暈與 Glow 預設只用在背景、Pattern、線條或容器層。承載資訊的文字使用單一實色墨色；不使用
  `background-clip:text`、透明字體填色、`mix-blend-mode`、外發光或彩色漸層字。強調可用穩定的單一 accent 色，不得犧牲字形邊界與可讀性。
- 純 HTML 風格案例不得把 Image2 preview、參考投影片截圖或其他 raster 圖片複製進輸出後
  當作背景；風格差異必須由 CSS 背景層、材質、字體、陰影與資訊構圖本身建立。
- Raster 圖片只在內容本身就是照片、人物、產品或場景證據，且選中的 HTML-safe Layout
  明確包含照片語意 slot 時才可使用；不得為了「有設計感」而把圖片當成不可控制的構圖底板。
- 不得因畫面四周留白，就新增沒有資訊功能的圓球、色片、角框、貼紙、巨大幾何塊或漂浮底板。
- 背景 Pattern 應直接存在 `.slide` 的背景繪製層，不要拆成大量可選取的裝飾物件。
- 純環境 Pattern 不得是 `.el`，也不得出現在編輯命中、群組或匯出內容物件中。
- 一般 HTML Theme 的環境背景預設由「可重複的低對比 CSS Pattern＋至多兩個非常淡的
  漸層／光暈」構成。不得把山丘、人物輪廓、花瓣、道路、器物、建築或其他可辨識場景
  當成通用背景；這類圖形會和內容競爭，只有內容本身需要解讀該圖時才可進入正式媒體 slot。
- 淺色頁的環境 Pattern／漸層單層 alpha 原則上不得高於 `.12`，深色頁不得高於 `.16`；
  若仍能一眼辨認為獨立大型圖形，而不是均勻材質或光影，就必須刪除或再降低對比。
- `.slide` 的環境背景若出現 `data:image/svg+xml`、`background-image:url(...)` 或其他
  場景式嵌入圖片，Browser QA 必須判定失敗；已宣告、具內容證據用途的媒體 slot 不在此限。
- 陰影用來說明前後層級；卡片與內容面板可有陰影，但避免以厚重硬偏移陰影冒充版面結構。
- 實體 Shape 只保留三種用途：承載內容、表示資訊關係、提供可操作的容器邊界。答不出用途的 Shape 一律刪除。
- 封面與章節頁若需要視覺重量，先調整 Pattern 密度、局部光暈、文字比例與群組位置，
  不以四角裝飾補重量。

Theme 的色彩與材質不能代替構圖差異。正式 HTML 案例還必須從
`prompt_system/renderers/html/design-dialects.yaml` 取得專屬 composition 與至少三種 technique，
並按 `references/html-design-technique-library.md` 的界線實作。驗收時要分開統計 Theme、
Layout 序列、內容主題與 design dialect，不得只因配色不同就判定為不同設計。

### 組合變化不是換皮

- 每頁的最終畫面至少由五個可分離決策組成：
  `semantic composition × composition variant × header placement × surface treatment × Theme Pattern`。
- 組合採固定種子，必須能重建同一結果；「可重現」不等於「所有頁一樣」。manifest 要逐頁記錄
  `composition_variant`、`header_mode` 與 `surface_mode`。
- 連續內容頁不得重複完全相同的三項組合。單一 Theme 中的標題位置與內容表面各至少要出現
  三種；只把同一個「標題＋兩欄方塊＋橫線」骨架換色，直接判定不合格。
- 卡片不是預設容器。內容可依語意使用 Open、Marker、Banded 或 Soft Field；若沒有明確容器
  需求，優先使用開放欄位、軸線、節點、留白與文字層級，不把每一段內容都塞進矩形。
- 同層級模組仍須維持相同寬高與內部重心；隨機只改整體排列和表面語法，不得破壞層級一致性。
- 固定種子只負責在語意相容的 scaffold 候選中重建同一結果；當頁 composition 必須在正式字體下
  保留 primary items 並通過 36px、無碰撞與可讀性驗證，不能把 seed 選出的 recipe 視為不可更換。

### 位置約束（固定，不分 theme）

裝飾元素只允許出現在三種位置：

1. **留白帶內**（四邊 96px 環帶）：邊角裝飾、chrome 細線、頁碼、mono 小標籤、
   logo 浮水印。可以貼齊畫布邊緣。
2. **背景層**（z-index 低於所有內容）：滿版紋理（網格、點陣、色暈）、
   半版色塊面板、大型 ghost 數字。可以滿版出血。
3. **內容區塊之間的結構線**：列與列的分隔線、欄與欄的 divider——
   這類「兼具結構功能」的線條允許進入 `.content`，但只能是線，
   不能是搶眼的色塊。

除此之外，裝飾不得插進內容區塊內部、不得壓在文字上（背景層在文字下方是允許的，
但要確保對比度不影響可讀性）。

### 職責約束（固定，不分 theme）

- 裝飾**不承載必讀訊息**。把裝飾全部刪掉，這一頁的內容必須仍然完整可懂。
- 頁碼、章節代號、簡報名稱只有在 content manifest 明確要求給觀眾看時，才允許放在留白帶，
  並使用 caption 角色以下的字級。Theme display name、Layout id、renderer index 等開發 metadata
  必須只存在 `data-theme`、`data-layout-id`、`data-page-number`、manifest 或 transient player chrome，
  不得常駐在投影片視覺層。
- 強調色紀律：theme 的 accent 色在裝飾上只能用於**線條、描邊、小面積標記**，
  不得大面積填色（半版面板這種例外要由 theme 的 `decoration_vocabulary` 明確定義）。

### 密度約束（固定，不分 theme）

- 一頁的裝飾元素（背景紋理除外）以 **1–3 組**為上限。裝飾詞彙表裡的招式
  不要全部用上——選出跟這一頁 page_type 相配的少數幾個。
- 每一組裝飾都要能回答「它在呼應內容的什麼」（例如左側刻度對齊三列章節的
  節奏、面板節點數對應章節數）。答不出來的裝飾就刪掉。

### page_type 開關（給 Layout／content manifest 發揮）

參考編輯設計慣例：不是每種頁面都配同一套裝飾。

| page_type | 建議裝飾配置 |
|-----------|--------------|
| 封面 / 章節頁 / 金句頁 | 無 chrome，讓字面呼吸；只用背景層裝飾 + 至多一組邊角裝飾 |
| 內容頁（目錄 / 模組 / 圖表 / 流程） | 預設 chromeless；content manifest 明確要求時才加觀眾 chrome + 結構線 |
| 結尾頁 | 比照封面，chromeless |

「chrome」指留白帶內的頂部/底部細線與觀眾 metadata 標籤組合，不包含 player toolbar。
renderer 不得自行注入 chrome；只有 content manifest 或 deck-level art direction 明確要求時才啟用，
而且同一份 deck 內容頁要嘛全有、要嘛全無，不能有的頁有、有的頁沒有。

### theme 的發揮空間（明確保留）

以下仍由 theme 層自由決定，但必須服從上面的 Pattern／陰影優先原則：

- 裝飾的視覺語彙：細線 vs 柔光、規律網格 vs 有機 Pattern、科技節點 vs 紙張噪點
- 背景紋理的樣式與密度（網格 / 點陣 / 色暈 / 無）
- 邊框哲學：hairline 編輯風或柔和陰影層次；若使用粗框或硬陰影，必須是內容容器本身的語意，
  不得拿來包住整頁或填補四角
- 已由 content manifest 啟用時，chrome 的具體樣式（線的顏色粗細、標籤字體、擺左擺右）

---

## 規則 6：編輯模式（可隨意調整）— 標準內建功能，不可省略

### 每頁背景遮罩與混合群組工具

- 頂部的「投影片樣式」面板提供目前頁面的遮罩顏色與透明度拉桿；設定必須以 `.slide` 的 `id` 個別保存，不得用單一全域值套用所有頁面。
- 遮罩只能作為 `.slide::before` 背景層，使用 `data-editor-slide-mask-color`、`data-editor-slide-mask-opacity` 與 `--editor-slide-mask-*` 保存；不得改寫文字、圖形或群組成員的既有 inline style、尺寸、位置與 stacking order。
- 遮罩的顏色、透明度、Undo／Redo、local draft 與 HTML 匯出必須維持一致；透明度為 0 時不啟用可見遮罩。
- 群組同時包含圖形與文字時，字級、字體、文字色等文字工具只展開到可見 `text`／`metric` 成員；圖形與 `background` layer 必須保持原有呈現。沒有可見文字成員的純圖形群組，文字工具維持 disabled。

共用編輯器原稿是 `src/html-editor/edit-mode.js`。正式自包含交付要把同版本 runtime
內嵌在 `</body>` 前；本機開發版也可以使用同目錄相容副本：

```html
<script src="edit-mode.js"></script>
</body>
```

本機相容副本 `artifacts/html-test/edit-mode.js` 由 `scripts/sync_editor_asset.py --write`
從 canonical source 產生；不得直接修改。它跟本機渲染出的 HTML 放在同一個目錄，
靠檔案已經存在的 `#stage`／`.el`／`#barInner` 慣例自動掛載，不需要額外設定。
若 `#stage` 或 `#barInner` 不存在（不是本專案的 player shell），它會自動不掛載，
不會報錯。

正式 renderer 不得只輸出 `data-edit-*` 標記就宣稱可編輯。每一份生成的簡報 HTML
必須同時具備：

- `#canvasBox`、`#stage`、`#barInner`、`#hint` 完整 player shell
- 每張 `.slide` 穩定且唯一的 `id`（供草稿、歷史與匯出定位）
- 與 HTML 同目錄的 `edit-mode.js`
- 可見的編輯工具列，並在開檔後成功建立 `window.EditMode`
- 正式 Layout 的 `.el` 必須從透明、零 padding、零邊框的中性基底開始；只有卡片、
  色塊、徽章與其他真正的視覺容器，才可明確加入背景、邊框、圓角或 padding。
  不得讓純文字繼承通用卡片外觀，以免可選取邊界、版面留白與實際文字內容不一致。
- 沒有背景或邊框的純文字物件必須使用 `data-edit-fit="text"`，以
  `width: max-content; height: auto` 貼合實際文字，原 layout slot 只保留為 `max-width`
  與 `max-height`；卡片、色塊、圖表、徽章與裝飾性大型文字等具有視覺面積的物件，
  則使用 `data-edit-fit="container"` 維持其設計邊界。兩者不得混用
- AI 生成群組內的 `data-edit-layer="text"` 與 `data-edit-layer="metric"`
  在單獨選取時，選取框必須依 `Range.getBoundingClientRect()` 取得實際文字範圍；
  不得沿用父容器的欄寬、左右定位範圍或整列寬度。第一次選取群組時可以顯示
  完整色塊邊界，再次點入文字層後只能框住文字本身
- `data-edit-layer` 只描述編輯能力，不得兼作定位開關。每一個 edit layer 必須另外宣告
  `data-edit-position="absolute"` 或 `"flow"`；renderer 遇到缺漏或未知值必須停止生成。
  可自由放置的文字、背景與 visual layer 使用 `absolute`；條列項目、表格儲存格、
  卡片內文與其他必須撐開父容器的巢狀文字使用 `flow`，並保留在正常排版流。
- 貼著語意模組邊緣的裝飾性 visual layer 必須用正向的關係宣告：目前支援
  `data-edit-anchor="bottom"`。這表示該線條／色帶的垂直位置由父模組的下緣負責，
  而不是由某一次編輯留下的 transform 矩陣負責。renderer 產出宣告後，父模組改變高度時，
  editor 必須先重新解析父模組下緣，再套用一般的水平／垂直 reflow；不得把舊的暫時 transform
  當成新位置。Theme／Preset 只負責外觀，不得用 CSS 偷改這個幾何關係。
- `data-edit-anchor` 是 Layout／renderer／editor 共用的語意，不是額外的裝飾 class。
  新產出的 visual layer 若採用貼邊關係，必須明確帶上宣告；既有沒有宣告但仍使用
  `bottom` CSS 的舊稿可由 editor 的相容判讀維持可編輯，重新產生後則應回到明確宣告。
  若線條是刻意跨出模組、需要裁切或 bleed，應使用獨立的 visual surface 與相應的 overflow
  契約，不得假裝成 contained 的 edge anchor。
- 結構線若由 `border-top`／`border-bottom` 產生，該列高度必須包含 flow 文字的實際高度與
  padding。不得讓文字 absolute 脫離排版流，再由已塌縮的 `<li>`、row 或 panel 畫分隔線；
  任何線段與文字 glyph box 相交都記為 blocking collision。
- 置中版型只保留一個 `data-content-area` 作為內容座標與排列範圍；文字物件直接放在
  Content Area 中以內容尺寸排版，不得把固定寬度的置中 slot 當成可選取文字框，
  也不得為每個文字物件再建立一層對齊容器。
- 所有 `data-edit-layout-only="true"` 容器在編輯模式中必須完全不可選：點擊空白應 deselect／marquee，
  不得顯示控制點、成員框或物件右鍵選單；其內部 `.el` 子群組仍可正常點選與編輯。

`scripts/capture_html_matrix.cjs` 會把上述任一缺件記為 `edit-framework` QA 失敗；
因此任一 renderer 重新生成 HTML 時，都不能再把編輯框架洗掉。
`data-edit-fit="text"` 的物件若比實際文字多出過大空白，則記為
`text-boundary` QA 失敗。
Content Area 的直接文字子物件若沒有 `data-edit-fit="text"`，則記為
`text-fit-contract` QA 失敗。

設計驗收與編輯功能驗收必須分開：設計截圖一律切換到投影模式並隱藏工具列、提示與
選取框，再只看投影片本身；編輯框架、控制點、群組與快捷鍵則由獨立的互動 QA 驗證。
Browser QA 尚有未豁免問題時，Visual Review 與整體 Theme Lab 不得標記為 pass。
Browser QA 必須包含通用的可見物件碰撞檢查，不得只驗證特定 radial diagram 或只檢查
物件是否仍位於投影片內。文字／文字、文字／模組、文字／規則線的 unintended overlap，
以及 AI 生成文字小於 36px，都必須是 blocking issue。

Theme 的 accent 必須分成「圖形色」與「文字色」兩種用途：線條、色塊、底紋可以保留
原始品牌色；凡是承載資訊的 accent 文字，必須依它實際落在頁面底色或卡片材質上，
改用通過對比檢查的 `accent-ink` 或 `surface-accent-ink`。不得為了維持色票原值，犧牲
數字、標籤、步驟與狀態文字的可讀性。

### 初始自動排版與自由編輯

- `data-auto-layout` Content Area 可在首次載入時使用 Flex / Grid 計算內容尺寸、間距與重心。
- 載入完成後必須立刻將結果 materialize 成每個 `.el` 的數值型
  `left / top / width / height`，並標記 `data-layout-materialized="true"`。
- materialize 後 `.el` 物件根改為 absolute positioning；拖曳、縮放、改字與儲存都不得觸發
  物件之間的自動回排。物件內標記 `data-edit-position="flow"` 的巢狀文字仍維持父容器內的
  正常排版流，不得在 materialize 時改成 absolute。
- 使用 Google Fonts 的簡報必須等待 `document.fonts.ready` 後才 materialize；不得先用 fallback
  字體計算座標，再讓正式字體改變字寬、行高與文字框邊界。
- materialize 讀取 `getBoundingClientRect()` 時，必須把瀏覽器的 stage scale 除回
  1920×1080 邏輯座標；不得把目前視窗縮放後的尺寸直接寫回 Layout。
- materialize 寫回的 `left / top / width / height` 必須等於**寫回後實際可見的幾何**。
  初始定位只能來自 Layout／`renderer-base`；Theme／Preset appearance 禁止位置宣告與 `!important`。
  不得用同等優先級覆蓋來維持兩套座標，否則草稿、復原與重載都會跑版。
- 只有使用者明確要求重新套用 Layout 時，才可呼叫 `window.reapplyAutoLayout()` 重算初始排版。
- 手動拖曳、縮放、改字或改行後，系統不得在背景偷偷重排整頁。允許的自動行為只限於目前文字框內的自然換行與溢位防護。
- `window.reapplyAutoLayout()` 的語意是「重新套用當前 Layout」：會先丟棄該範圍內已 materialize 的手動幾何，恢復初始 Layout 樣式，再量測、置中與 materialize。界面必須明確命名為重新套版，不得假裝成無害的「整理」。
- 重新套版必須是單一可復原操作，並在執行前保留一筆編輯歷史；不得在每次文字輸入、縮放或重新整理視窗時自動呼叫。
- QA 若發現 auto-layout 尚未 materialize，或直接子物件仍不是 absolute geometry，記為
  `layout-materialization` 失敗。
- Layout 必須依內容密度選擇字級、圖表尺寸、區塊高度與間距；短文案、少項目時應
  主動放大內容並收緊區塊關係，不得沿用高密度尺寸後再以 `space-between`
  把少量內容撐滿 Content Area。
- Before / After 、對比、流程與卡片群等複合版型，各資訊區塊要先形成緊密的
  視覺群組，再把整組置中於 Content Area；不得以等距作為置中的唯一判斷。
- 稀疏的 2×2 指標、狀態或原則模組，不得因 Layout 提供較高 slot 就把每張 Surface 拉滿。
  每個模組先由可見文字、角色 content inset 與必要結構線決定 block size；整組再依實際
  module union 置中。若內容只需要緊湊的兩列，應收合 group，而不是用 `1fr` 把標題與說明
  拉到卡片兩端。
- 漏斗、金字塔、雷達與置中組織圖等具有明確垂直中心軸的圖解，標題群必須與圖解
  共用中心軸；不得讓標題貼左、圖解置中，形成兩套互相競爭的構圖。
- 漏斗每一層應以「階段說明＋主要數字」形成左右重量；次要轉換率放在主要數字下方，
  不得再用一個無標籤色塊或方形徽章塞在最右側。最窄層仍必須保留不發生文字碰撞的最低寬度。
- 橫向列式版型（例如編號｜標題｜說明｜狀態）必須把每一列視為一個單位：各欄位的
  **實際內容框**共用同一條垂直中心線。說明即使換成兩行，也要以整段文字的實際高度
  置中；不得為不同欄位各自猜一組固定 `top` 值，也不得靠加高透明文字框假裝置中。

### 文字階層與卡片重心

- 有主標與副標的投影片，主標文字量不得大於副標；主標負責短主張，副標負責完整說明。
- 副標的實際呈現寬度必須大於主標，且基準字級不得低於 32px；必要時縮短主標或放大副標，
  不得只用一行小灰字應付。
- Before／After、現況／目標、問題／解法等比較欄位的語意標籤必須視為模組標題：
  字級至少比同卡內文大 6px、字重至少 700，且字重必須高於內文；不得套用 caption 階層。
- 卡片內的文字群組可維持靠左，但整組內容的垂直中心必須接近卡片中心，不得全部擠在頂端。
- 卡片編號的字級不得小於卡片標題；標題越短，編號可以越大，作為卡片的第一視覺錨點。
- 卡片字級必須依同頁卡片數分密度級距：2–4 張使用大型階層、5 張使用中型階層、
  6–8 張才使用緊湊階層；不得因 4 張卡片被標記為 compact 就把其中三張縮成次要資訊。
- 上述失敗分別記為 `title-subtitle-copy`、`title-subtitle-width`、`subtitle-hierarchy`、
  `contrast-label-hierarchy`、`card-content-balance` 與 `card-number-hierarchy`。

### 它做什麼

- 預設直接進入修改模式；工具列的模式按鈕會依目前狀態顯示「投影 (E)」或
  「編輯 (E)」。這個按鈕只能切換編輯交互、物件虛框、選取框與控制點，不得呼叫
  `requestFullscreen()`、`exitFullscreen()` 或任何會改變視窗大小的 API。全螢幕狀態必須與
  編輯／投影狀態完全獨立，只由 `F`、全螢幕按鈕或瀏覽器 Escape 控制
- 編輯模式固定顯示左側縮圖欄與上方編輯工具列；不是把編輯按鈕塞進投影浮動列。
  復原、重做、匯出與存檔整合於上方編輯列，模式切換入口置於編輯列末端；
  即使瀏覽器已全螢幕，只要仍在編輯模式，選取框、控制點與選取工具列就必須保持可見、可操作。
- 左側縮圖欄與上方編輯工具列採並排幾何：`#slideRail` 必須固定 `top:0; bottom:0`，工具列則從
  rail 右緣開始。不得再用 topbar 高度替 rail 增加上方 padding／margin；`#slideRailHeader` 貼齊
  viewport 頂端，`#slideThumbList` 緊接 header 並延伸到 viewport 底端。
- 左側縮圖必須反映實際投影片內容與目前頁；允許用 drag-and-drop 重新排序。排序完成後必須同步
  更新縮圖編號、player counter 與 `#stage` 內 `.slide` DOM 順序，並納入 100 步復原／重做、
  local draft 與匯出 HTML。
- 投影模式的工具列只保留「上一頁、頁碼、下一頁、全螢幕、回到編輯模式」；復原、
  重做、匯出、存檔、選取提示與其他編輯控制全部隱藏。回到編輯模式後，
  可用的編輯控制必須完整恢復。模式切換不得改變瀏覽器視窗、DPR、全螢幕狀態或投影片內部
  1920×1080 幾何；編輯模式可以針對扣除上方工具列與左側縮圖欄後的工作區，重新計算最外層
  viewer 的等比預覽，但不得造成投影片內容 reflow 或改寫物件座標。
- 投影模式按 `Escape` 必須回到編輯模式。若按鍵同時讓瀏覽器退出全螢幕，須等待或容忍
  該瀏覽器 transition 後再恢復編輯 chrome；非全螢幕投影也必須直接生效。編輯模式中的
  `Escape` 維持既有語意：先結束文字編輯，其次取消目前選取，不得切換回投影模式。
- 切換進投影模式時，工具列必須立即隱藏，不得先停留數秒。只有游標進入視窗底部
  112px 感應帶時才顯示；游標離開感應帶後短暫緩衝再收起。隱藏時工具列不得攔截點擊，
  且顯示／隱藏不得觸發 layout reflow、viewport resize 或 stage scale 重算。
- 工具列不提供常駐「說明」按鈕，投影片底部與右下角也不顯示操作教學句或狀態 readout；
  編輯狀態由固定 topbar、選取工具列、外框與控制點表達，不再疊加灰色文字提示。
- 上方主編輯列另有五顆檔案／操作按鈕：「復原 (Ctrl+Z)」「重做 (Ctrl+Y)」
  「匯出調整後 HTML (X)」「匯出 PPTX」與一顆共用存檔按鈕；不顯示歷史版本按鈕或 `H` 快捷鍵。
  共用存檔按鈕的位置、大小與圖示不因狀態改變：尚未綁定時以橘色顯示「綁定並存檔」，
  可直接寫回時以綠色顯示「儲存進度」。畫面不另加第二顆存檔按鈕、常駐說明或檔名小字；
  綁定檔名只放在按鈕的 tooltip。
- 點擊任一未群組 `.el` 預設選取單一物件；若它位於正式群組內，普通點擊先解析到最外層正式群組，
  並由該群組完整外框攔截命中。持續進入下一層使用「編輯單件」狀態；按住 Shift 點擊或框選可多選目前允許階層的物件。
- 按住 `Ctrl`／`Cmd` 點擊屬於明確、暫時的群組穿透：直接選取游標下最內層可編輯物件；命中文字時，
  同一次點擊直接進入 `contenteditable`。放開修飾鍵後，普通點擊仍選最外層正式群組；不得修改群組路徑、取消群組或建立持續的深入範圍。
- 純文字物件與 `data-edit-layer="text|metric"` 的 pointer hit-test 必須使用文字節點逐行的
  `Range.getClientRects()`，不得沿用橫跨整列的 DOM layout box。游標落在同一水平線但已超出
  實際 glyph line box 時，必須先繼續檢查同一語意模組的下層 background layer 與其他可見物件；
  若沒有其他命中，才視為空白點擊並允許取消選取或開始框選，不得再回退成選取該文字或透明定位容器。
- 編輯模式的選取工具以獨立浮動視窗呈現，不得合併或停駐在上方主編輯列，也不得改變主編輯列高度。
  浮動視窗固定於 viewport，但定位基準必須是目前選取範圍：優先放在選取範圍上方，空間不足時
  改放下方，並沿選取範圍水平中心對齊；只有在兩側空間都不足時才能在工作區內縮避讓。不得固定
  停靠在主編輯列下方或畫面底部。沒有選取時隱藏。選取後所有功能持續顯示；目前目標不支援的功能必須 disabled 並以半透明表示，
  上述 workspace 內縮避讓的唯一例外是：兩側皆無法容納完整面板時，改用 compact chrome-safe 模式，
  暫置於 editor topbar 已保留但未被主工具列占用的區域；不得增加 topbar 高度、覆蓋 canvas 或遮住選取框，空間恢復後必須回到一般浮動定位。
  不得整列消失。為控制介面密度，不顯示群組成員數量，也不提供文字框寬數字欄；文字框寬仍以
  左右控制點直接調整。文字可啟用字級、粗體、對齊與文字色；
  `data-edit-layer="background"` 才啟用背景色；圖形只啟用實際可用的物件操作。群組外框的權威
  成員集合若含可見 `text`／`metric` layer，字級、行高、字距、粗體、對齊與文字色彩工具必須
  啟用，並展開套用到完整文字子集合，包括 footer、caption 與結論句；只有不含可見文字的群組
  才停用文字工具。
  標籤必須區分「文字／圖形／背景／群組」；AI 生成群組與手動群組使用同一個群組標籤，
  禁止顯示「複合元件」或按了無效的控制項。
  單選時四角+四邊出現
  8 個控制點；多選時保留一個包住全部成員的外層選取框與 8 個控制點，並同時以較細的
  實線顯示每個成員自己的視覺邊界。成員框不得額外顯示控制點，也不得以元素原始配置框
  取代 `data-edit-fit="text"` 的實際文字邊界。群組與文字物件拖曳四角控制點時，
  都必須鎖定長寬比，字級、行距、字距、padding、gap 與內容一起等比例縮放；不得橫向或
  縱向拉伸。
  群組與複合元件左右側拖曳須同步更新每個成員的 X 位置、根框與直接子層框寬；向內縮先消耗
  文字框左右留白、padding、gap 與子物件間距並鎖住目前行數，只有成員邊界確實容納不下時才
  縮窄文字框並自然換行；若仍將越界或互撞，字級與行高才按同一比例縮小。禁止在含文字父層
  套用非等比 `scaleX`。
  群組與複合元件上下側拖曳須同步改變根框、背景／底板與需跟隨容器之直接子層高度；第一階段
  壓縮 padding、gap 與子物件間距並依既有垂直對齊重新分配 Y，第二階段才在文字即將越界或
  互撞時同比縮小字級與行高。禁止使用 `scaleY`。文字物件本身的四個側邊控制點仍只調整框架：
  左右只改框寬、不改字級，框高依實際文字更新；上下只改框高，不改框寬、字級或行距。
  Primitive Shape 同樣遵循左右只改寬、上下只改高；只有四角控制點執行等比縮放。
  點空白處或按 Escape 會取消選取；沒有選取任何物件、也沒有正在輸入文字時，
  上下左右四個方向鍵都會切換投影片；選取物件後，方向鍵改為微調物件位置
- 單純文字方塊的上／中／下垂直對齊使用 `display:flex; flex-direction:column` 搭配
  `justify-content` 實作，不得只設定普通 block 元素不會可靠生效的 `align-content`
- 拖任一控制點時按住 Ctrl／Cmd：改由物件中心向外或向內操作；四角仍等比例縮放，群組
  四邊仍從中心對稱執行同一套 staged content-aware resize，不得跳過空白壓縮階段，也不得用
  `scaleX`／`scaleY` 非等比扭曲成員內容
- 開啟編輯模式後：每個 `.el` 可拖曳移動（滑鼠位移除以目前縮放比例，換算回
  1920×1080 的絕對 px，不管畫面被縮放成多小都準）、文字元素可直接點擊修改
- 文字進入 `contenteditable` 後仍須顯示貼合目前文字框的選取邊框；打字時可隱藏縮放控制點，
  但不得隱藏邊框，且輸入造成換行或高度改變後邊框須在下一個 animation frame 內更新
- 文字輸入造成自然換行、硬換行或內容寬度改變時，水平定位必須遵循目前 `text-align`：
  置左固定左緣、置中固定中心、置右固定右緣，不得因重新量測文字框而改變構圖中心
- 文字編輯模式必須提供 PowerPoint／Canva 式智慧對齊輔助線：文字框的左／中／右或
  上／中／下錨點對到投影片中心、Content Area 邊界／中線或其他物件錨點時，顯示貫穿
  投影片的暫時直線或橫線。輔助線只負責提示，不得在打字時擅自搬動文字；離開文字編輯、
  取消選取、切到投影或匯出／儲存時必須消失，且不得寫入投影片內容 DOM。
- 文字斷行必須區分「自然換行」與作者指定的 `<br>` 硬換行：
  - 初始生成可使用 `text-wrap: balance` / `pretty` 改善標題節奏，也可在量測後於合適標點加入 `<br>`。
  - Browser REVIEW 必須依正式字體的實際 line boxes 檢查末行；中文段落或標題換行後若
    末行只剩 1–2 個中文字，一律記為 `text-orphan-tail`，不得只靠肉眼略過。
  - `text-orphan-tail` 的處置順序是：先擴寬文字框或移到更合理的語意斷點，再精簡不影響
    意思的文案，最後才在角色範圍內動態縮小字級；AI 生成結果仍不得低於 36px。三者都
    無法解決時必須拆頁或更換 Layout，不得帶著孤字通過 QA。
  - 文字框左右側控制點一旦改變框寬，該文字框必須切換為自然換行；框變寬時，
    沒有 `<br>` 的文字應自動補回上一行，不得繼續強制平衡斷行。
  - 角落比例縮放只改變整體視覺比例，保留縮放前的行數與斷點。
  - 群組左右側拖曳同步改變成員與子層框寬；向內縮先消耗文字框左右留白、padding、gap 與
    子物件間距並保留目前行數，成員邊界無法容納時才自然換行，仍不足時才同比縮小字級與行高。
  - 群組上下側拖曳先改根框與底板高度、壓縮 padding、gap 與子物件間距並依既有垂直對齊
    重新分配 Y；只有文字即將越界或互撞時，字級與行高才同比縮小。不得裁切、重疊或使用
    `scaleY` 繼續縮框。
  - `<br>` 必須永久保留；編輯模式中，每個真實 `<br>` 後方顯示淡色 `↵` 提示。
    提示是編輯器 overlay，不得寫入文案 DOM、影響文字量測，也不得出現在投影、匯出或儲存的 HTML 中。
- 拖曳中即時顯示目前元素的畫布座標
- 選取一個或多個可調字級的文字元素時，選取提示會顯示 `[-] [px 輸入] [+]` 字級控制；
  多選且字級不同時，以主要物件字級加 `+` 顯示，例如 `12+`，不得把整組控制隱藏。
  輸入新數字時一次套用到所有已選文字物件；
  也可用 `[` / `]` 微調 1px、`Shift+[` / `Shift+]` 微調 5px。群組內若有不同字級子層，仍以
  主要文字字級加 `+` 顯示；輸入新值時套用到權威成員集合內的全部可見 `text`／`metric` layer，
  不得因 mixed state 隱藏控制或漏掉 footer、caption、結論句。
  角落或群組使用 transform 等比縮放時，字級欄必須在拖曳中即時顯示
  `基礎 CSS 字級 × 累積視覺縮放倍率` 的實際 px；undo/redo 快照仍保存基礎字級，避免重複縮放
- 同一個選取提示必須提供字體家族選擇器。單件文字以 inline `font-family` 保存；群組或多選則展開
  權威成員集合中的可見 `text`／`metric` layer 後統一套用。字體家族必須進入 dirty state、
  undo／redo、草稿、HTML 匯出與重新載入；選擇「沿用 Preset」時移除該物件的 inline override。
- 上方主編輯列的「投影片樣式」面板提供整份預設字體與本頁背景色。整份預設字體只覆寫根節點的
  `--font-display`、`--font-heading`、`--font-body`，保留 `--font-mono` 與既有單件字體 override；
  本頁背景只寫 active `.slide` 的 `background-color`，不得使用 `background` shorthand 清除
  Preset 的 Pattern、漸層或背景圖片。兩種 document／slide-level 操作都必須可 undo／redo、保存草稿與匯出。
- 字體與顏色控制的 editor chrome 由 shared editor 擁有，但其 surface、ink、border、focus 與色票
  必須消費目前 Preset 已投影的 computed tokens：`--bg`、`--surface`、`--text`、`--muted`、
  `--accent`、`--support-accent`；深色與淺色 Preset 均須先做對比保護。只有舊 artifact 缺少 tokens
  時才可退回中性色與既有畫面取樣，不得在 editor 內另維護一份 Preset id 對照表。
- `data-edit-fit="text"` 的自動文字框調整字級時，框寬須依字級比例同步成長，並依左／中／右
  對齊維持原本錨點；只要 Content Area 仍放得下，就必須優先保留目前行數，不得因增加 1px
  立即換行。只有使用者已用左右控制點指定固定框寬，或成長後確實碰到 Content Area 邊界時，
  才允許依目前框寬自然換行。多選與群組內文字要逐一套用同一原則。
- 同一張投影片內若有相同角色的文字元素但字級不一致，選取提示會顯示 advisory
  提醒與「套用到同類元素」按鈕；它只提示、不阻擋操作，也不會自動改動其他元素
- 多選物件或既有群組後按 `Ctrl+G` / `Cmd+G` 建立新群組；按 `Ctrl+Shift+G` /
  `Cmd+Shift+G` 取消目前最外層群組。群組可以再次被群組，取消時逐層拆解。浮動選取工具列
  顯示「群組／編輯單件／上一層群組」；「取消群組」由物件右鍵選單提供，快捷鍵不是唯一入口。
- 群組動作只在選取**2 個以上物件**時可用。選取單一物件或單一群組時，「群組」必須
  停用（`selectionCanGroup()` 回傳 false，`groupSelection()` 直接擋下），不得把單一群組
  再包成一層外層群組——那只會產生「群組中只有一個物件」的困惑。既有群組之間的巢狀
  仍可透過「多選 2 個以上（其中含群組）再 Ctrl+G」達成。
- 取消群組後必須保留全部成員的多選狀態：手動群組與 **AI 生成群組**一致，
  `ungroupSelection()` 完成後 `setSelection(members, …)` 選取全部成員，不得塌回單一主要
  內層。使用者才能立即對整組成員重新群組或操作。
- 群組結構與選取狀態必須寫入同一筆 history。取消群組後按 `Ctrl+Z`／`Cmd+Z` 時，除了恢復群組結構，
  還必須立即釋放子物件多選並恢復「選取整組」；redo 則再次恢復全部直接成員的多選。選取框、
  成員標示、工具列與控制點必須在同一次 undo／redo 內同步更新，不得等到下一次點擊才刷新。
- **組成群組後只選取新群組本身**（單一群組狀態），不得停留在原本的多選成員狀態；
  `groupSelection()` 完成後選取結果是那一個新群組。與「取消群組＝全選成員」對稱。
- **全螢幕時選取框、控制點、選取工具列必須照常顯示**。這些 overlay 若 append 到
  `document.body`，必須讓全螢幕對 `document.documentElement`（而非 `#player`）觸發，
  或把 overlay append 進全螢幕元素內；否則全螢幕會看不到控制點。
- **框選（marquee）必須能從投影片兩側的 letterbox 空白區起始**，不限於畫布上：
  起點只要落在 `#player` 內、且不在編輯 chrome（`#slideRail`／`#bar`／按鈕／`[id^=edit-]`）
  上即可開始圈選。
- **群組背景必須是獨立的 `data-edit-layer="background"` 子層並填滿容器（`position:absolute;inset:0`），
  容器本身背景透明**；填色用 CSS 寫死、不要用載入後 runtime 搬移（runtime 會在編輯時
  短暫閃爍、且群組外框會縮到只框住內容而非整個色塊）。這樣群組外框才會涵蓋整張卡、
  背景也才是可獨立選取／移動的物件。
- 編輯模式右鍵點擊可編輯物件時顯示物件操作選單。若右鍵命中目前多選中的任一物件，
  必須保留全部已選物件並顯示「組成群組」；不得先把多選退回單選。此命令呼叫同一個
  `groupSelection()` 路徑，完成後立即切換成選取新群組。「取消群組」必須呼叫同一個
  `ungroupSelection()` 路徑，保留最外層取消、巢狀群組、歷史與匯出狀態。投影模式
  不建立或攔截這個右鍵選單。
- 物件對齊工具必須同時支援單選、正式群組與一般多選：只選一個物件，或選到一個正式群組時，
  靠左、水平置中、靠右、靠上、垂直置中與靠下都以完整 1920×1080 投影片為邊界。正式群組
  必須視為單一邏輯物件，先以整組聯集框計算一次位移，再把相同位移套用到所有成員；不得把
  群組成員各自對齊到群組內部而造成堆疊。尚未組成群組的一般多選，才以目前選取範圍為對齊
  邊界。所有對齊只修改物件的 `left`／`top` 定位，不得改變相對位置、寬度、高度、字級、
  transform 或斷行。水平／垂直等距分布不適用於單一正式群組；一般多選仍須至少三個物件，
  未達數量時按鈕必須 disabled。
- 編輯模式內支援最多 100 次 in-session undo/redo：拖曳、縮放、文字編輯、字級微調都可以用
  `Ctrl+Z` / `Cmd+Z` 復原，`Ctrl+Y` 或 `Ctrl+Shift+Z` 重做。這組操作狀態只存在於目前
  瀏覽器 session，重新整理頁面後會自然清空，且不提供獨立歷史版本面板
- 「匯出調整後 HTML」把目前 DOM（含新座標、改過的文字）存成新的 .html 檔案
  下載，純瀏覽器端完成，不需要伺服器
- 「匯出 PPTX」把目前 edited DOM 的文字、stage-space geometry、computed style、圖片與
  Theme／Layout 身分整理成 manifest，再交給 HTML 內嵌的 PptxGenJS browser adapter，直接在
  瀏覽器記憶體中建立並下載 `.pptx`。輸出必須保留可用的 Custom Layout → slide 關係；文字、
  色塊與圖片優先轉為原生可編輯物件，不得用整頁 screenshot 代替。此路徑必須在 `file://`、
  靜態網站與 localhost 都可用，不得要求使用者另開本機 server。`dev_server.py` 的
  `/__export-pptx` → `@oai/artifact-tool` 僅保留作開發備援與交叉 QA，不是正式操作的前置條件。
- Every formal HTML artifact must embed both `PptxGenJS` and `PptxBrowserExport` in a `data-pptx-browser-runtime-embedded="true"` script, record the runtime SHA-256 in its manifest, and fail static validation when either runtime is missing.
- 共用存檔按鈕與 `Ctrl+S` 使用同一路徑。在 `localhost`／`127.0.0.1` 的
  `dev_server.py` 環境，按鈕直接顯示綠色「儲存進度」，並透過 `/__save` 覆寫目前 URL
  對應的巢狀 HTML 路徑。開發伺服器仍可在寫回前保留內部安全備份，但不提供歷史版本 UI。
- 在 `localhost`／`127.0.0.1` 的可寫入 dev server 上，編輯停止約 1.5 秒後自動走同一個 `/__save`，因此不必先手動按存檔才能留下目前 HTML 與 `.history/` 快照；手動存檔仍保留作為立即保存入口。
- 在公開靜態網站或直接雙擊開檔時，尚未取得 File System Access file handle 前，按鈕以橘色
  顯示「綁定並存檔」。第一次按下後開啟系統選檔視窗；使用者選定 HTML 並完成寫入後，runtime
  必須把 handle 存入 IndexedDB，並把穩定識別碼寫入 HTML 根元素。綁定成功後，同一顆按鈕
  原地改為綠色「儲存進度」，之後按鈕或 `Ctrl+S` 直接寫回該檔案。
- 重新開啟 HTML 時，runtime 依根元素識別碼找回 handle。handle 不存在、權限明確被拒絕、
  寫入失敗或使用者取消重新選檔時，按鈕必須回到橘色「綁定並存檔」，並用既有暫時狀態列說明
  原因；不得維持綠色或宣稱已儲存。瀏覽器不支援 File System Access API 時，可以保留一般
  HTML 下載作為備援，但按鈕仍維持未綁定狀態。「匯出調整後 HTML」繼續負責另存副本。
- 只看成品時，在網址加上 `?preview=1`。此模式保留原介面與同一顆存檔按鈕，但標記為
  `read-only-preview`；按鈕與 `Ctrl+S` 都不得送出 `/__save`、開啟選檔器或改寫 HTML，
  只用既有暫時狀態列提示「預覽模式不會修改檔案」。
- 未按存檔前，編輯內容每隔約 1.5 秒會自動存進瀏覽器 `localStorage` 當草稿；
  下次打開同一個網址若偵測到草稿會提示「發現未儲存的草稿，要恢復嗎？」
- `file://`、公開靜態網站與 `read-only-preview` 不會因自動追蹤而開啟選檔視窗或改寫檔案；這些情境仍只自動保留 `localStorage` 草稿，真正寫回 HTML 需使用者手動觸發並完成檔案綁定。
- 草稿 key 必須包含 HTML 本身的 `data-deck-revision`。同一路徑重新生成新版本後，舊 revision
  的草稿不得提示或套用，舊版 path-only 草稿也必須清除，避免把舊座標灌進新 Theme/Layout。
- runtime 另保留最近 100 筆 `commit / undo / redo` 診斷紀錄（只記物件 key 與幾何摘要），
  並由 `window.EditMode.diagnostics()` 讀取；這是除錯資料，不增加投影片或工具列上的 UI。

### 跟規則 1–5 的關係：生成時是硬規則，編輯時是參考線

規則 1–5（96px 內容容器、字級範圍、溢位防呆、垂直分佈、裝飾位置）在**生成
當下**必須遵守，不可違反。但使用者用編輯模式手動調整之後，這些規則**不會
擋下**使用者的操作——編輯模式允許把元素拖進留白帶、拖出安全框、字級改到
角色範圍外。這是刻意的：生成是自動化流程要保證品質下限，手動編輯是人的
決定要保留最大自由度，兩者不是同一個場景。

### 目前不做的部分（刻意留白，等有需要再補）

- 拖曳/編輯時不做規則 1–5 的即時硬性檢查或阻擋（例如拖進留白帶跳警告），先求
  「能自由調整」。目前只有同頁同角色字級不一致的 advisory 提示，且必須由使用者
  主動按「套用到同類元素」才會改動其他元素
- 存回原始 HTML 檔案不會回寫進七段式 YAML、Theme Core 或 Layout Core，
  若之後重新用 AI 生成同一個輸出路徑，手動存檔的調整會被蓋掉；要沉澱成規則，
  仍需人工把確認後的幾何整理進 Layout／Composition／renderer-base，外觀整理進 Theme
- 開發伺服器的內部安全備份（`.history/`）不做自動清除或數量上限，也不暴露成使用者介面

---

## 與既有規則的關係

- 不覆蓋 [project-format-guide.md](project-format-guide.md) 的七段式文法，也不覆蓋各 layout 的 slot 與對齊規則。
- 「主副標底色擇一」「TOC 同字級」「封面 logo 浮水印」等內容設計規則仍適用，本層只負責把它們落到具體 px。

---

## Google Fonts 字體系統

HTML 不得各自寫一套字體 URL 或以作業系統字體當主字體。Theme 仍可用
「無襯線」「高對比襯線」「打字機字」等語意描述，但 HTML Renderer 必須統一正規化為：

- `Noto Sans TC`：黑體主標、內文與一般 UI。
- `Noto Serif TC`：襯線主標、編輯感內容與展示數字。
- `Roboto Mono`：編號、座標、工具列與等寬訊息；中文字形回退到 `Noto Sans TC`。

三套核心字體的 Google Fonts CSS2 請求必須包含可實際使用的字重：

| 字族 | 必須載入的字重 | 禁止用途 |
|---|---|---|
| `Noto Sans TC` | 300、400、500、600、700、800、900 | 無 |
| `Noto Serif TC` | 300、400、500、600、700、800、900 | 無 |
| `Roboto Mono` | 300、400、500、600、700 | 不得承擔 800／900 Heavy 標題 |

每份 HTML 的 `<head>` 必須只有一組 Google Fonts CSS2 請求，用多個
`family=` 參數合併三個 family，並同時包含：

- `preconnect` 到 `fonts.googleapis.com` 與 `fonts.gstatic.com`。
- `display=swap`，避免字體下載期間文字完全不顯示。
- `--font-heading`、`--font-body`、`--font-mono`、`--font-display` 四個角色變數。

禁止使用 CSS `@import`、禁止 Layout 自己追加字體連結，也禁止把
`Georgia`、`Microsoft JhengHei`、`Consolas` 等系統字體當成第一順位。系統字體只能放在
Google Font 後面作為斷網或載入失敗時的最後 fallback。

---

## 版型 HTML 渲染模式

各版型族群的 HTML 結構模板、特殊元素（環形 SVG、座標軸、遮罩色塊、照片 placeholder）見：
→ [html-layout-patterns.md](html-layout-patterns.md)

渲染任何版型時，先查快速對照表找族群，再套用對應模板。

## 可群組拉伸模組的幾何所有權（撰寫規則）

這是 HTML renderer 的輸出規則，不是 QA 建議。

### 正確結構

columns、timeline、metrics、index 等同級模組，應由每個 `.el[data-edit-structure="module"]` 自己成為直接 grid／flex item：

```html
<div class="column-grid" data-edit-layout-only="true">
  <article class="el column-item"
    data-edit-structure="module"
    data-edit-composite="...">
    <div data-edit-layer="background" data-edit-position="absolute"></div>
    <div data-edit-layer="text" data-edit-position="flow">...</div>
  </article>
</div>
```

### 禁止結構

不得用一個會產生實體 box 的 layout-only slot 包住可編輯模組：

```html
<div class="column-grid" data-edit-layout-only="true">
  <div class="column-slot" data-edit-layout-only="true">
    <article class="el column-item" data-edit-structure="module">...</article>
  </div>
</div>
```

這會造成幾何所有權分裂：grid 控制 slot，編輯器控制 article。結果通常是整組可以移動，但拉伸時只有內層卡片被延長，外層排列、間距或定位仍維持舊值。

### 例外

wrapper 若只供語意或 CSS selector 使用，必須不產生 layout box（例如等效於 `display: contents`），且需有對應 browser interaction test。沒有明確例外契約時，一律採直接 grid／flex item。

### 產出閘門

- 每個 semantic module 必須具備 `.el`、`data-edit-structure="module"` 與 `data-edit-composite`。
- 模組第一個直接子層必須為 `data-edit-layer="background"` 且使用 `data-edit-position="absolute"`。
- renderer 必須在寫檔前驗證上述結構；違反即停止產出。
- QA 只負責重演 move、水平延長、垂直延長、角落等比縮放與 undo／redo，不得用 QA 修補錯誤 markup。
本專案的群組幾何驗證命令：

```powershell
node scripts\qa_html_group_resize_ownership.cjs `
  --url <http://127.0.0.1:7392/.../deck.html> `
  --report <artifact-dir>\group-resize-qa.json `
  --screenshot <artifact-dir>\group-resize-qa.png
```
## 語意模組互動契約與產製順序（撰寫規則）

1. `.el[data-edit-structure="module"]` 的 DOM box 是選取框、碰撞與群組幾何的權威來源；內部文字或 metric layer 只負責內容，不可縮小外框。
2. 移動單一模組時，模組本身建立獨立 stacking context 並整體提升 `z-index`；位置與 `z-index` 必須由同一筆 move history 保存，確保 Undo／Redo 可逆。
3. 側邊把手是 staged content-aware resize：先改變每個模組的 frame，並優先壓縮 padding、gap 與子物件間距；只有文字即將越界或互撞後，才讓字級與行高按同一比例接手縮小。自動縮字的底線必須由拖曳開始時的文字角色尺寸與實際 glyph bounds 推導，不得用頁面特例的固定字級；到達可讀性底線後，應夾住該軸的最小內容尺寸，不得繼續縮字、裁切或重疊。使用者直接操作字級控制時不受此自動底線限制。不得用 `scaleX`／`scaleY` 扭曲字形；角落把手仍使用整體等比例 visual scale。
4. `visual`／`background` layer 不是文字物件。文字對齊程式不得替它們設定 `display:flex` 或覆蓋 Theme 的 `display:none`。
5. 最終 layout pipeline 順序固定為 `font minimum → materialize → orphan repair → font-ready group fit → visual balance → thumbnails`。任何會改變文字或模組幾何的步驟都必須發生在 visual balance 之前；title flow stack 不得在字型就緒前物化。
6. Browser release gate 必須覆蓋 index、columns、map、metrics、timeline、ledger 等所有實際 semantic module family，並驗證完整模組 union、四邊延長、極限壓縮時由空白階段切換到字級階段、四角等比縮放、移動重疊、單件子層拖曳不得帶動父背景、祖先裁切、Undo 與 Redo。
   涉及重新群組或側邊縮放時，還必須逐對驗證水平範圍相交的相鄰 semantic modules 維持非負間距，不能只檢查 glyph 是否留在各自模組內。
7. 可移動的 semantic module 從自身到 `.slide` 之間不得被中間祖先以 `overflow:hidden`／`clip` 裁切；版面若需要圓角或表面邊界，應由獨立 background layer 表現。`.slide` 是唯一預設的最終裁切邊界，刻意裁切必須另以明確資料屬性宣告並通過互動 QA。
8. 有色底板、邊框或狀態面的頁尾結論框若構成完整資訊單位，renderer 必須將它輸出為直接擁有幾何的 `.el[data-edit-structure="module"]`，具備 `data-edit-composite`，且第一個直接子層是實際承載底色與邊框的 background layer；這樣才能和相鄰模組一起延長、縮放、群組與 Undo／Redo。
9. 使用者把 semantic module 與同層物件重新組成手動群組時，側邊縮放不得把 module 外殼視為不可分割的原子。editor 必須沿每個選取成員向下解析到直接擁有可見幾何的 leaf semantic module，以及 composite 直接擁有的 visual／background surface，以這些 leaf boxes 建立群組聯集、內容容量與 resize history；外層 manual group 只保留群組脈絡，不得阻斷子模組與其表面同步縮放。Browser release gate 必須重演「選取多個 module／同層物件 → 手動群組 → 四邊縮放 → Undo／Redo → 取消外層群組」，不可只測單一 module 的捷徑。
