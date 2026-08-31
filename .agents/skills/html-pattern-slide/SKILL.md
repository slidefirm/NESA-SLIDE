---
name: html-pattern-slide
description: Render, regenerate, edit, or QA an editable 1920x1080 HTML presentation using this project's shared Art Direction, Theme core, Layout core, HTML adapters, Pattern-based visual surfaces, and content. Use for ordinary HTML decks, Theme Lab cases, randomized demos, presentation previews, editor behavior, projection controls, layout balance, or renderer regression checks. Use html-image-slide when images affect the new Layout structure.
---

# HTML Pattern Slide

使用本 Skill 產生、重建或驗收可自由編輯的 1920×1080 HTML 簡報。把 Theme、Layout、內容、HTML renderer 與編輯器視為不同層；不要把畫面先做成不可編輯的圖片，也不要用單一固定版面只換顏色。

## 1. 先讀正式來源

執行前依序讀取：

0. 若是新建 HTML 且使用者要求圖片背景、滿版／半版圖片構圖或 image-led HTML，先讀取
   `.agents/skills/html-image-slide/SKILL.md`，完成 image-aware Layout handoff；本 Skill 是下游
   foreground renderer。若是已有 HTML 只要附加／替換背景，改讀
   `.agents/skills/slide-background-image/SKILL.md`，保留原始 Layout、內容與幾何，不要求重新選版。
1. `references/presentation-production-contract.md`
2. 若 deck 有 Art Direction，讀取 `prompt_system/art_direction/README.md` 與目標 brief
3. `references/html-generation-rules.md`
4. `references/html-css-ownership-contract.md`
5. `references/html-layout-patterns.md`
6. `references/renderer-adapter-contract.md`
7. `prompt_system/renderers/html/design-method.yaml`
8. `prompt_system/presets/catalog.yaml`
9. `prompt_system/renderers/html/preset-themes.yaml`、`layout-catalog.yaml` 與 `assembly-catalog.yaml`
10. 選定 Theme 的 core 與 HTML adapter
11. 每個選定 Layout 的 core 與 HTML adapter
12. 使用者指定的內容、artifact 或既有 HTML

若正式來源彼此不一致，停止受衝突影響的狀態變更，指出差異並修正對應的 canonical source；不得用籠統的優先順序掩蓋衝突。

### 圖片背景 handoff 的下游責任

- `html-image-slide` 先決定圖片角色、SAFE ZONE、素材 provenance 與圖片頁的 Layout 意圖；本 Skill 再依 handoff 產生可編輯的 HTML foreground。
- 新建 image-aware HTML 路徑必須在 Layout 決策前宣告 `asset_policy=image-planned`。預設使用 `layout-selection=dynamic`，讓 `prompt_system/renderers/html/design-method.yaml#image_candidate_extensions` 的 `with-image` 候選有機會被選到；若 handoff 已有逐頁 Layout，則保留明確決策並驗證其 `media_requirement`。
- `slide-background-image` 不重新執行既有 HTML 的 Layout routing；它只量測、生成／選取背景與隔離套用，原始 Layout、內容與幾何由來源 HTML 保持不變。
- `image-planned` 是混合候選池，不代表每頁都要放照片。流程、表格、數據等內容仍可選 `no-image`；只有使用者明確要求全 deck image-led 時，才使用 `--media-mode with-image`。
- `html-image-slide` 的 renderer manifest 必須保留 `asset_policy`、`layout_selection`、每頁 `media_requirement`、候選池與實際選定 Layout；`slide-background-image` 則保留來源 HTML 與背景 run 的 provenance。

## 2. 共用 Theme/Layout，不強迫 YAML

- 以 Theme core 決定品牌語氣、色彩、字體、材質、Pattern、陰影與整體氣氛。
- 以 Layout core 決定資訊關係、閱讀順序、欄位結構與語意圖形。
- 有 Art Direction 時先決定 scene role，再依 handoff 選 Theme／Layout。方向未經人工通過時，
  只可生成 audition，不得描述或部署為正式成品。
- 以 HTML adapters 把共用 Theme/Layout 轉成 HTML 可編輯結構。
- 以 content manifest 或使用者內容填入標題、副標、正文、數字與圖表資料。
- 不要把 HTML 專用規則寫回 Theme core 或 Layout core。
- 不要要求 HTML 先產生 assembled YAML。assembled YAML 是 Image2 的必要輸入，對 HTML 只是可選的內容來源。
- 同一份 deck 的每頁必須在內容、架構、Layout 與設計要素上形成差異；禁止只換顏色、標題或卡片數量。
- 經過人工驗收的好看案例只能作設計證據；要成為可獨立選取的 **HTML Preset Theme**，必須重新寫成不含舊內容、舊 Layout、舊 CSS 或 Style Case source 的乾淨視覺契約。
- Preset Theme 只綁定配色、字體、Pattern、材質、陰影與 component recipe，不綁定內容或 Layout。HTML Preset 不自動補 Image2 / PPTX adapter。
- PRESET Gallery 的名稱、公開狀態與順序只讀 `prompt_system/presets/catalog.yaml`。標記為 `theme-lab-case` 的展示案例不等於可重複套用的 Preset Theme；只有具備 `reusable-preset` 能力才可進入 Theme 選擇流程。

- HTML／Preset 生成的預設 content mode 是 new-deck：先產生或抽取全新簡報內容，再依內容關係選 Layout；不得自動使用 Preset 的 example story、example layouts 或固定展示稿。
- 測試新風格／轉換是另一條流程：沿用使用者提供的既有內容或明確的 content manifest，只改要測試的 Theme／Layout／renderer；不得自動改用 Preset 展示內容。
- preset-demo 只在使用者明確要求展示 Preset 預設內容／範例或查看 Preset 展示稿時啟用；這時才可以鎖定 Preset 的示範故事與頁面序列。
- 只說「使用新的 Preset」不代表要使用 Preset 預設內容；沒有展示／測試／轉換語意時，一律維持 new-deck。
- 產生 HTML 時要在 manifest 記錄 content_mode；new-deck 不得帶入 Preset 範例的 forced-layout，preset-demo 則要留下 example reference。
- 產生器自動抽選 Theme 時，預設只從已驗收 Preset 抽取；舊 Theme 可明確指定，但配色未重新驗收前不進入隨機池。
- 每個 Layout Core 都必須宣告 `media_requirement`。HTML 未明確指定時使用 `asset_policy=pattern-only`，只能選 `no-image`；若交付前會補上真實圖片，使用 `asset_policy=image-planned`，才可自動或明確指定 `with-image`。兩類仍須完整可見，不得把 `with-image` 定義成全域 `manual-only`。
- 使用者要求依既有 Preset「重新製作」時，exact URL／artifact 只用於人工比較；不得把舊 DOM、CSS、內容或 Layout sequence 當 runtime input。保留舊版，並由正式 renderer／Theme adapter 以當次內容產生新版本。
- 重新製作前獨立寫出一套可跨頁延續的 content-surface recipe，包括框線、透明度、材質、陰影／光暈、圓角或切角與留白節奏。它必須服務資訊分組，不得退化成所有頁共用的白色方卡，也不得用無資訊功能的巨大圓形、斜線或漂浮底層冒充貫穿元素。
- 全套生成前先比較原版與 cover、一般內容頁、資訊密集頁三頁 pilot；若三頁尚未證明同一 Preset 能適應不同內容密度，不得直接擴張到整份 deck。

### Theme／Preset 覆寫的語意邊界

- Layout adapter／`renderer-base` 唯一擁有 position、inset、寬高、Grid／Flex、gap、padding、margin、對齊、transform、overflow、writing mode、font-size 與 line-height。Preset CSS 只擁有 appearance。
- Preset 的 composition 建議必須在選 Layout 時解析；appearance CSS 禁止 `data-layout-id`、`data-composition-variant`、頁碼／順序 selector、`.content`、`.el`、幾何 property、幾何 custom property與 `!important`。
- 中心堆疊的可見成員要由 Layout 共享一個中心軸；不要用 Preset CSS 微調 left／translate 來「看起來差不多」。
- 內容表面與前景字色必須成對驗證。若元件標記 data-visual-surface-role="accent"，其背景與 accent-text 必須在 computed style 中保持可讀配對。
- Semantic guards 只能驗證，不能在 Preset CSS 後追加幾何修正。正式 QA 必須先跑 source ownership gate，再執行 Browser geometry invariant 與 `scripts/qa_html_visual_contract.cjs`。
- 若本次修改 reusable Preset、appearance generator、CSS ownership 或 materialize 流程，必須用固定內容與 regression Layout 集合跑完所有 reusable Preset；不得拿單一 Preset 通過代替全域回歸。

## 3. 畫布、Content Area 與周圍留白

### 固定畫布

- 使用 `#stage` / `.slide` 作為 1920×1080 固定座標畫布。
- 只允許最外層 viewer 依視窗等比縮放；不得讓投影片內部因 viewport 改變而 reflow。
- 編輯／投影切換不得改變瀏覽器視窗、DPR、全螢幕狀態或投影片內部幾何。
  編輯模式可以針對扣除固定工具列與縮圖欄後的工作區，重新計算最外層 viewer fit；
  這只能等比縮放整張畫布，不得觸發內容 reflow 或改寫物件座標。

### 唯一 Content Area

- 每頁只能有一個主內容容器：`.content[data-content-area]`。
- 固定幾何為：
  - `left: 96px`
  - `top: 96px`
  - `width: 1728px`
  - `height: 888px`
- 所有主要文字、圖表、流程、卡片、比較欄與圖片都以此 Content Area 定位。
- 不要再建立透明的「置中容器」、第二層 content wrapper 或滿版群組來協助對齊。
- Content Area 外側的 96px 邊帶保留給頁碼、頁首、品牌標記、背景材質與播放器 chrome，也可以保持空白。
- 裝飾不得侵入主要閱讀區，也不得讓四周安全留白消失。

### 以視覺群組置中

- 把頁面所有可見內容的聯集當成一次性的量測集合，計算相對 Content Area 的單一 `dx／dy`，完成水平與垂直置中。
- 位移由 `data-edit-layout-only="true"` 的 centering frame 承接。它不是 `.el`、不是 composite、不能被點選，也不出現在物件清單；置中後不得留下可選取的整頁、標題或內容大群組。
- 標題、副標、獨立內文、註解與來源保持各自的 `.el`；只有本身就是一個操作單位的卡片、流程節點、圖表模組等 semantic module 保持群組。
- 短內容要收合並適度放大，使內容彼此緊鄰；不要把少量內容硬拉到 Content Area 邊界。
- 內容增加時才向上下擴張，並保留安全留白。
- 一般內容的視覺高度以 Content Area 的 82–88% 為目標。
- 中高密度內容可使用 90–93%。
- 只有高密度資料頁才可使用 95–100%，並先降低間距，再考慮縮小字級。
- 對稱圖形與標題共用中心軸。
- 非對稱版面要在另一側提供足夠的文字、數字、圖片、色塊、陰影或 Pattern 作為視覺配重。
- 不要把標題孤立在左上，也不要把主圖形機械式塞在正中央而忽略整頁重心。

## 4. 文字、數字與可選取邊界

### 字體系統

- 只用一個 Google Fonts CSS2 request 載入字體。
- 預設載入 `Noto Sans TC`、`Noto Serif TC`、`Roboto Mono`。
- 在 `document.fonts.ready` 後再量測、定位與 materialize。
- 若離線字體載入失敗，提供合理的 system font fallback，避免版面崩壞。

### 建議字級

- Display：120–180px
- Section title：88–120px
- Page title：52–80px
- Module title：36–52px
- Subtitle：36–44px
- Body：36–40px
- Caption / label：36–40px
- Mega number：160–360px

AI 生成的投影片視覺文字一律不得低於 36px；塞不下時先擴大容器、縮短文案或拆頁，不得再縮字。這個限制只管生成結果，使用者在編輯模式中仍可手動調到 36px 以下，儲存／匯出必須保留手動值。

### 文字階層

- 主標文字量不得比副標多；主標只保留最核心命題。
- 副標的視覺寬度應不小於主標，字級不得低於 32px。
- 關鍵數字至少與對應標題等大；文字較短時，數字應更大。
- Before／After、現況／目標、問題／解法等語意狀態標籤屬於模組標題，不是 caption；
  字級至少比同卡內文大 6px、字重至少 700，且必須重於內文。
- 卡片可左對齊，但卡片內的數字、標題與說明要形成垂直重心。
- 卡片編號或核心數字不得小於卡片標題。
- 先用字級、行距、欄寬與段落間距建立層級，不要靠大量框線補救。

### 語意斷行

- 只有實測寬度不足時才換行。
- 必須換成兩行時，優先選擇接近視覺中點的逗點、頓號、分號或語意分界。
- 不要每逢標點都換行。
- 不要留下單字、短尾巴或不平衡的孤行。
- 群組四角縮放時同步等比縮放文字並保留斷行；群組左右邊界拖曳則改變文字框寬度並允許自然重排，
  不得用父層 `scaleX` 拉伸字形。

### 選取邊界必須符合內容

- 純文字物件使用 `data-edit-fit="text"`，寬高以實際文字內容為準。
- 不要讓文字選取框橫跨整個 Content Area，也不要保留多餘的透明 padding。
- 視覺容器、卡片、圖表與群組使用 `data-edit-fit="container"`。
- AI 生成群組內的混合文字、行內元素或數字，使用 `Range.getBoundingClientRect()` 測量實際可見邊界。
- 文字物件的 resize handle、拖曳框與命中區都必須跟隨實際邊界更新。

## 5. 視覺設計原則

- 先依 `design-method.yaml` 判斷內容關係，再選 Layout；不可先挑普通 Grid 再硬塞內容。
- 每頁要有一個 `signature_composition`，並回答「改成普通 Grid 會失去什麼」。若沒有損失，就應簡化。
- Theme 選擇同時檢查 `best_for` 與 `avoid_for`；不要只因配色相近就套用。
- 三方向視覺預覽預設關閉，只有使用者明確要求探索或尚未選定 Theme 時才啟用。
- 優先使用 Pattern、漸層、材質、Noise、Glow、Shadow 與透明度形成深度。
- Pattern／Effect 必須有相容情境、效能、可讀性風險、投影安全與透明度上限標籤。
- HTML 不要在四周硬塞無資訊意義的幾何底形、邊角裝飾或漂浮色塊。
- 實體圖形只用於承載資訊、分組、表達關係或支援互動。
- 每頁控制在 1–3 組裝飾語彙，避免堆滿。
- 圓形循環、漏斗、時間軸、流程、組織圖等語意結構必須使用對應圖形；不要全部降級成同款卡片網格。
- 相同 Layout 在不同 Theme 下應保留資訊關係，但允許材質、形狀語彙、陰影、Pattern 與節奏改變。
- 同一 deck 要混合不同資訊架構，例如封面、目錄、1+2、1+3、對比、流程、循環、數據、人物、結論與 QA。
- 不要只追求平均分布；若平均分布造成空洞，應動態放大內容或改用更適合的 Layout。

## 6. 生成後必須可自由編輯

### Materialize

- 把可編輯物件輸出為具有固定數值幾何的 `.el`。
- Materialize 後不得依賴 flex/grid 自動 reflow 來維持最終位置。
- 手動拖曳、縮放、改字後，不得在背景自動重排整頁；只允許目前文字框內自然換行與溢位保護。
- `window.reapplyAutoLayout()` 是「重新套用 Layout」，會捨棄目標範圍的手動幾何後再 materialize。只能由使用者明確觸發，並且必須是一步可復原操作。
- 背景、文字、數字、圖表、圖片、裝飾與連接線分成可辨識的 layer。
- 背景 layer 先建立並置於最底層。
- HTML 交付時不得把整頁 flatten 成圖片。

### 群組

- 先問「這些層是否共同表達一個資訊單位」。答案為是時才輸出 semantic module 群組，例如同一卡片的數字、小標、內文、背景與底線；標題、副標與一般內容不因位置接近而成組。
- semantic module 使用 `.el[data-edit-structure="module"][data-edit-composite]`，第一個直接子層是 background layer；module 是唯一 editable root，內層以 `data-edit-layer` 表示，取消群組、進入「編輯單件」或按住 `Ctrl`／`Cmd` 暫時穿透時才成為直接操作層。使用者介面只稱它為「群組」，不另設 Composite 功能。
- 初次開啟時只有 semantic module 與使用者手動建立的群組保持群組狀態；centering frame、Content Area 與 layout-only 容器永遠不可選。
- AI 生成群組與手動群組在一般點擊中一律視為單一物件；群組已選取後，再點成員或群組框內空白仍須維持整組，
  不得以重複點擊隱性進入子物件。
- 正式群組的完整外框（包含成員之間的 gap／空白）都是群組命中範圍；同一位置有子物件或未群組背景時，群組優先。
- 「編輯單件」是持續進入下一層的正式模式；巢狀群組每次只進一層，並以「上一層群組」逐層返回。
- 按住 `Ctrl`／`Cmd` 點擊屬於明確、暫時的深入操作：直接選取游標下的群組內物件；若命中文字，
  同一次點擊直接進入文字編輯。放開修飾鍵後，普通點擊仍選整組；此操作不得取消群組、改寫群組路徑或建立持續的深入範圍。
- 以 `Ctrl+G` 建立群組，以 `Ctrl+Shift+G` 取消最外層群組。
- 允許把既有群組再次包成新群組，保留 PowerPoint 式巢狀群組。
- semantic module 與手動群組共用取消群組、重新群組、巢狀群組、復原／重做、草稿與匯出行為；取消 semantic module 時可以保留 renderer 外殼，但必須改為直接命中內層物件。
- 選取工具列直接提供「群組／取消群組／編輯單件／上一層群組」，不可只靠快捷鍵或隱性點擊。
- 單選顯示八個 resize handles。
- 正式群組選取時只顯示外層總選取框與 handles，不顯示子物件細框；進入「編輯單件」後才顯示該層物件框。
- 尚未建立正式群組的多選同時顯示外層聯集框、handles 與每個原始物件的細框。
- 文字編輯中仍顯示貼合文字框的選取邊框；可隱藏 resize handles，但不得隱藏邊框。
- 選取工具以獨立浮動視窗呈現，不得合併到上方主工具列或改變其高度；選取後顯示全部功能，
  並依物件位置在主工具列下方或畫面底部避讓。依實際目標切換 enabled／disabled 狀態，
  不可用的功能以半透明保留。浮動視窗不顯示群組成員數量或文字框寬數字欄；文字啟用字級、
  粗體、對齊與文字顏色，框寬仍由左右控制點調整；
  圖形啟用物件操作；背景層才啟用背景色。群組第一次選整體時，若權威成員集合含可見
  `text`／`metric` layer，字級、行高、字距、粗體、對齊與文字色彩工具必須啟用並套用到完整
  文字子集合，包括 footer、caption 與結論句；只有不含可見文字的群組才停用文字工具。
- 選取標籤要明確顯示「文字／圖形／背景／群組」；semantic module 與手動群組使用同一個「群組」標籤，
  不得再顯示「複合元件」。
- 任何可見控制項都必須對目前選取物件實際生效；禁止出現按了沒有反應的假控制項。

### 縮放

- 文字、群組與圖片的四角控制點預設等比縮放。
- 拖曳四角 handle 時同步縮放位置、尺寸、字級、行距、stroke、陰影與內距。
- 群組與複合元件的左右側控制點採兩階段內容感知框架寬度調整：同步更新成員水平位置、根框與
  直接子層寬度，向內縮時先消耗左右留白、padding、gap 與子物件間距並鎖住目前行數；確實容納
  不下時才縮窄文字框並自然換行，若仍將越界或互撞，字級與行高才按同一比例縮小。禁止在含文字
  的父層套用非等比 `scaleX`。
- 群組與複合元件的上下側控制點採自適應高度調整：先壓縮／展開 padding、gap、行高與
  子層垂直位置；只有文字即將重疊、超出根框時才動態縮小字級，禁止用 `scaleY` 壓扁字形。
- 禁止以四角縮放時只拉寬或只拉高而造成文字、圓形、圖片或群組變形。
- 四角縮放不得改變斷行；左右側調整文字框寬度時則應使用自然換行。
- 按住 `Ctrl` 或 `Cmd` 時以中心點等比縮放。
- 文字物件左右側控制點專門調整文字框寬度，不改字級，框高依實際內容更新。
- 文字物件上下側控制點專門調整文字框高度，不改框寬、字級或行距；只有四角控制點會等比縮放文字內容。
- 文字編輯造成換行或內容寬度改變時，依目前 `text-align` 保持水平錨點：置左固定左緣、置中固定中心、置右固定右緣。
- 明確標示為 primitive 的單一線條或形狀可做單軸縮放。

### 字級控制

- 單選文字顯示畫面上的實際視覺 px；角落或群組等比縮放後，數值必須即時乘上累積視覺倍率，不得停留在 transform 前的 CSS 基礎字級。
- 多選文字且字級相同時顯示共同字級；字級不同時顯示主要物件字級加 `+`，例如 `12+`。
- 多選輸入新字級時一次套用到所有已選文字物件，不得因 mixed state 隱藏控制。
- 歷史快照與匯出狀態保存基礎 CSS 字級及 transform，不得把視覺 px 回寫後又重複套用 transform。

### 復原與重做

- undo 與 redo 各支援最多 100 個狀態。
- 拖曳、縮放、文字修改、群組、取消群組與圖片插入都必須可復原。

## 7. 編輯模式與投影模式

### 編輯模式

- 所有生成的 HTML 預設載入 `window.EditMode`，並可直接進入編輯模式。
- 至少支援拖曳、文字編輯、位置與尺寸讀值、字級控制、方向鍵微調、多選、群組、縮放、復原、重做、匯出與存檔。
- 使用 localStorage 保存本機草稿；在 `localhost`／`127.0.0.1` 的可寫入 dev server 上，編輯停止約 1.5 秒後也會自動透過 `/__save` 寫回 HTML 並保留 `.history/` 快照。`file://`、公開靜態網站與唯讀預覽只做草稿保護，不自動開啟選檔視窗。
- 固定顯示左側投影片縮圖欄與上方編輯工具列；縮圖可拖曳重排頁序，縮圖編號、player counter
  與 `.slide` DOM 順序必須同步，而且排序納入復原／重做、草稿與匯出。
- 復原、重做、匯出與存檔整合於上方編輯工具列；模式切換入口置於工具列末端，
  不得讓編輯命令混入投影浮動列。
- 編輯模式即使位於瀏覽器全螢幕，選取物件後仍必須顯示外框、控制點與選取工具列。
- 選取工具列可作為 topbar 下方的 editor chrome；不得覆寫投影片內容或成為匯出後的投影片元素。
- 不在投影片底部或右下角顯示操作教學句、灰色提示或狀態 readout。

### 投影模式

- 投影 toolbar 只保留上一頁、頁碼、下一頁、全螢幕與返回編輯。
- 投影模式按 `Escape` 必須返回編輯模式；若瀏覽器正處於全螢幕，先退出全螢幕再恢復
  topbar、縮圖欄與編輯交互。編輯模式中的 `Escape` 仍只結束文字編輯或取消選取。
- 不顯示 Help、永久說明、歷史、存檔、匯出、復原、重做或編輯工具。
- toolbar 預設隱藏。
- 滑鼠進入畫面底部 112px 感應區時顯示 toolbar。
- 滑鼠離開後短暫延遲再隱藏，避免操作時閃爍。
- toolbar 隱藏時不得攔截點擊。
- toolbar 顯示或隱藏不得造成畫布縮放、跳動、位移或 reflow。
- 編輯／投影切換與瀏覽器全螢幕是兩件事；切換模式不得自動放大或縮小視窗。
- 投影模式不得顯示左側縮圖欄、上方編輯列、選取框或控制點。

## 8. 使用正式入口生成

優先使用：

```powershell
python scripts\render_randomized_html_demo.py `
  --output artifacts\html-test\deck.html `
  --art-direction <art-direction.yaml> `
  --theme <theme-id> `
  --story <story-id> `
  --asset-policy <pattern-only|image-planned> `
  --layouts <layout-id-1>,<layout-id-2>,... `
  --seed <integer>
```

可依任務調整參數，但輸出必須包含：

- player、canvasBox、stage 與多張獨立 slide
- 每頁恰好一個 `.content[data-content-area]`
- Materialized `.el` 物件
- Google Fonts 與 fallback
- HTML 旁的 `edit-mode.js`
- 內嵌編輯器、投影 toolbar 與模式切換
- Theme、Layout、內容與 renderer 來源 manifest
- 有 Art Direction 時，manifest 與每頁 `data-*` 必須保留 direction id、scene role 與 visual intensity
- 每頁不同的內容、架構、版面與設計語彙

如果正式入口尚未支援某項規則，先修 renderer 或 adapter，不要在單一 artifact 內以一次性 CSS 補丁掩蓋。

## 9. 正式 QA

完成後依任務範圍執行：

```powershell
python scripts\generate_renderer_adapters.py --check
python scripts\art_direction.py <art-direction.yaml>
python -m py_compile scripts\art_direction.py scripts\render_randomized_html_demo.py scripts\html_design_method.py scripts\html_css_ownership.py scripts\qa_html_design_method.py
python scripts\html_css_ownership.py --self-test
python scripts\html_visible_copy.py --renderer-source scripts\html_production_renderer.py
python scripts\html_visible_copy.py --html <deck.html> --story <story.json> --report artifacts/qa/<deck>-visible-copy.json
python scripts\qa_html_text_orientation.py --html <deck.html> --report artifacts/qa/<deck>-text-orientation.json
python scripts\html_preset_themes.py
python scripts\html_design_method.py
python scripts\qa_html_design_method.py --manifest <deck.manifest.json>
python scripts\html_css_ownership.py --html <deck.html> --manifest <deck.manifest.json>
node scripts\capture_html_matrix.cjs
node scripts\qa_html_css_geometry_invariant.cjs --file <deck.html> --report artifacts/qa/<deck>-css-geometry.json
python scripts\qa_html_css_preset_matrix.py --matrix-dir <preset-matrix-dir> --capture-report <capture-report.json> --report <matrix-summary.json>
node scripts\qa_html_visual_contract.cjs --file <deck.html> --report artifacts/qa/<deck>-visual-contract.json
node scripts\qa_html_presentation_toolbar.cjs
node scripts\qa_html_edit_interactions.cjs
node scripts\qa_html_repeat_group.cjs --html <deck.html> --report artifacts/qa/<deck>-initial-object-tree.json
node scripts\qa_html_group_axis_resize.cjs
node scripts\qa_html_group_adaptive_vertical_resize.cjs
node scripts\qa_html_text_frame_semantics.cjs
node scripts\qa_html_group_resize_ownership.cjs --url http://127.0.0.1:7392/<deck.html> --report artifacts/qa/<deck>-group-resize.json --slide-index <index> --expected-modules <count> --grid-selector <selector> --module-selector <selector>
node scripts\qa_html_background_group_text.cjs
node scripts\qa_html_font_background_controls.cjs --url http://127.0.0.1:7392/<deck.html> --report artifacts/qa/<deck>-font-background-controls.json
node scripts\qa_html_semantic_group_matrix.cjs --url http://127.0.0.1:7392/<deck.html> --report artifacts/qa/<deck>-semantic-group-matrix.json --profile-file references/html-semantic-group-qa-profile.example.json
```

- 使用本機 HTTP server 驗收，預設 port 為 7392；不要只用 `file://` 判斷互動是否正常。
- 目前 release 的 Layout Core 沒有直向文字 slot；source 與 artifact 的 `vertical-*` writing mode
  或文字 `rotate(±90deg)` 任一命中都屬 blocking failure。垂直排列必須以 Grid／Flex／座標完成，
  不得旋轉 glyph。
- `html_css_ownership.py` 或 CSS geometry invariant 未通過時，artifact 直接視為未完成；不得靠後置 `!important` 或 semantic guard 修正後放行。
- 上述 group QA 的 URL、report、profile、頁碼與 selectors 必須對應實際 deck；無參數啟動失敗不算 QA 結果。
- 逐頁檢查 overflow、重疊、裁切、過小文字、空洞色塊、失衡、語意錯版與裝飾侵入。
- 跨頁設計檢查只用四題：骨架是否重複、節奏是否有變化、招牌構圖是否符合內容、配色是否突兀；輸出 `pass / fail / observe` 與證據，不要用假精準分數。
- 有 Art Direction 時，另外檢查裝飾是否有來源、素材家族是否一致、卡片是否有語意邊界、
  signature move 是否可見、scene rhythm 與 visual intensity 是否有停頓和峰值。
- 分別檢查編輯模式固定 topbar／縮圖欄、縮圖拖曳排序、全螢幕編輯選取框、投影模式、toolbar 自動隱藏、多選、semantic module、巢狀手動群組、100 步歷史與等比縮放。
- 使用實際滑鼠操作驗證底部 112px 感應區，不要只檢查 DOM。
- QA 預設為 `report-only`：只能讀取 artifact／source／manifest，並寫入 report、截圖或暫時的瀏覽器狀態；不得覆寫受測 HTML、改 manifest、呼叫 renderer 重生、追加 CSS 修補或自動重試。存檔／匯出測試必須使用攔截器或隔離副本。
- 未通過時記錄規則、頁碼、selector、可觀察證據與 `implementation-rule / content-layout / manual-review` 分類，將 artifact 標為未完成後結束本次 QA。
- 真正修正另開實作步驟，優先改 canonical renderer、editor、Theme／Layout 或 validator，再產生新 artifact 做全新 QA；不得在同一 QA pass 裡「檢查 → 回修 → 再檢查」。

## 10. 反回歸底線

交付前確認沒有下列問題：

- HTML 沒有編輯框架或 `window.EditMode`
- 頁面缺少 `data-content-area`，或存在第二個置中容器
- Content Area 外框被當成實際物件選取
- 文字框遠大於文字內容
- 主標比副標更長，或副標太小、太窄
- 數字小於對應標題
- 稀疏內容被拉滿到 Content Area 邊界
- 整頁重心貼上、貼左或缺乏配重
- 循環、漏斗、流程等語意圖形被替換成同款卡片
- 周圍堆疊僵硬、無功能的裝飾圖形
- 多選時看不到個別物件邊框
- 群組四角縮放造成拉寬、拉高、變形或非預期換行
- 群組左右拖曳時只有外框或成員位置改變，沒有同步調整成員與子層框寬
- 群組左右拖曳對含文字父層套用 `scaleX`，造成字形變寬或變窄
- 群組上下壓縮時尚未耗盡 padding、gap、行高與層間距就先縮小字級
- 群組上下壓縮後文字重疊、超出根框，或以 `scaleY` 壓扁字形
- 群組外框包含 footer、caption 或結論句，但群組文字工具沒有同步修改它們
- 文字 DOM 框的透明區攔截點擊，導致下層 background layer 無法選取
- 編輯／投影切換造成視窗或投影片縮放
- 投影模式仍顯示 Help、說明文字或編輯功能
- toolbar 隱藏後仍攔截操作
- HTML 被錯誤要求先生成 Image2 assembled YAML
