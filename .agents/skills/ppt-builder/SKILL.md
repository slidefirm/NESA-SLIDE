---
name: ppt-builder
description: Build an editable PPTX from this project's Art Direction, Theme and Layout core, PPTX adapters, content manifest, and optional edited HTML or assembled YAML. Generate or validate text-free raster backgrounds by default while keeping foreground content native; use for PowerPoint, PPTX export, masters, custom layouts, placeholders, or native PowerPoint QA.
---

# PPT Builder

將本專案的 Art Direction、Theme／Layout core、PPTX adapters 與內容轉成可編輯 PPTX。HTML 可提供已調整內容與幾何；assembled YAML 可提供內容，但兩者都不是必要的共同 runtime payload。

## 執行前環境 Gate

正式建檔前先呼叫 `load_workspace_dependencies`，只使用回傳的 bundled Node runtime、Node
modules 與 binary 目錄。不要改用 system／global／repo-local Node，也不要自行安裝套件；若
`@oai/artifact-tool` 或其中一個 runtime path 不可用，建檔應停止並回報 blocker。

在 conversation-specific 的 `$TMP_DIR` 建立 `node_modules` junction／symlink 指向 bundled
modules，並將 `RUNTIME_NODE`、`RUNTIME_NODE_MODULES`、`RUNTIME_BIN_DIR` 設為回傳的絕對路徑。
正式 JavaScript builder 必須從 `@oai/artifact-tool` 建立 `Presentation` 並匯出 `.pptx`；第一個
create/edit authoring command 前，依 Presentations skill 成功執行一次
`mark_artifact_operation_started.mjs`。所有 intermediate builder、preview、inspection 與 QA
檔案放在 `$TMP_DIR`，只有正式 PPTX、builder、manifest 與 QA report 放到交付路徑。

## 必讀

1. `references/pptx-generation-rules.md`
2. `references/project-format-guide.md`
3. 目標 Theme／Layout core、PPTX adapters、content manifest，以及任務實際提供的 HTML 或 assembled YAML
4. 若 deck 有 Art Direction，讀取並驗證 `prompt_system/art_direction/` handoff
5. `prompt_system/renderers/pptx/themes/<theme-id>.yaml`
6. `prompt_system/renderers/pptx/layouts/<layout-id>.yaml`
7. 若有 HTML 輸入，再讀 `references/html-generation-rules.md`
8. Presentations skill 的 `artifact_tool/API_QUICK_START.md`、`artifact_tool/api/API_DOCS.md`、`artifact_tool/api/references/master.spec.md`、`artifact_tool/api/references/layout.spec.md`
9. HTML 來源需要逐頁 raster 背景時，讀取並執行 `.agents/skills/slide-background-image/SKILL.md`
10. 原生 PPTX／content-manifest 路徑使用 hybrid 背景時，讀取 `references/pptx-background-master-workflow.md`
11. 正式直接 PPTX 的 Custom Layout 背景／Surface 收尾使用 `scripts/finalize_pptx_layouts.ps1`；
    定位合約 QA 使用 `scripts/qa_pptx_positioning_contract.py`

## Variant-first Placeholder materialization

正式 PPTX 流程固定為「Content → Layout → 相容 PPTX Layout Variant → typed Placeholder → Slide」。
內容形狀有歧義時選 Variant，不回頭修改 canonical Layout。讀取並使用
`prompt_system/renderers/pptx/layout-variants/catalog.yaml` 與共用
`scripts/pptx_variant_runtime.py`；manifest 記錄候選、選定 Variant、選擇依據與完整
`placeholder_schema`。固定 anatomy 使用 base projection；人物、模組、見證等 composite slot
必須拆成可單獨編輯的 `title`／`subtitle`／`body`／`picture`／`chart`／`table`，裝飾與背景不冒充
內容 Placeholder。Variant catalog 不是 Layout 白名單；沒有 bespoke Variant 的 active Layout
必須由 PPTX adapter 的 `slot_entries` 產生 typed baseline projection，不能輸出空白 Layout。
正式 builder 統一使用 1920×1080 canonical stage 到 1280×720 artifact-tool
stage 的 `2/3` 換算，title/subtitle frame 與字級在 Variant 選定後固定。`placeholder_schema` 的
title/subtitle `frame_policy=fixed` 會阻止 finalizer 對包含它的 content group 重新定位、縮放、fit
或重排；其他文字欄位使用 `content-fit`，舊 manifest 缺欄位時才沿用 legacy reflow。
正式 manifest 預設 `reset_policy=layout-authoritative`：Slide 只填內容，不改寫 Placeholder 幾何；
只有明確指定 `legacy-reflow` 才允許 Slide 層文字 fit。Reset 前後的 Layout／Slide geometry 必須一致。
PPTX Surface 使用 manifest `surfaces` materialize 成 child Layout 的原生 shape layer，位於
raster background 與 Placeholder 之間；它可以有 fill、transparency、line 與 roundRect 幾何，
但不得以整頁圖片或 HTML screenshot 取代。

所有文字 Placeholder 預設 `verticalAlignment: middle`（垂直置中）；水平對齊依 Layout 的
`alignment_rules`，不能由 builder 以內容長度臨時改軸。每個 Placeholder 必須有 stable name、
typed role、deterministic index 與固定 stage-space frame。若同一 type 有多個槽（例如多個
subtitle／body），仍要保留各自的 name 與 unique OOXML `p:ph` index；不得讓 artifact-tool 的
collection normalization 把它們合併成一個槽。背景與裝飾永遠不是內容 Placeholder。

尺寸換算只有一個邊界：共用 canonical stage `1920×1080` 進入 artifact-tool `1280×720` 時
一次乘 `2/3`；不要在 Layout、Variant、Slide 或 finalizer 內再 fit、round、依文字高度重算
title／subtitle frame。若文字真的放不下，先縮短內容或改選相容 Variant／Layout；不能靠 Reset
後的自動 reflow 掩蓋幾何錯誤。

## Resolved positioning Gate

正式直接 PPTX 路徑統一使用 `scripts/pptx_positioning.mjs`。每個 Layout Placeholder 必須同步建立
一個 Slide-local Placeholder，兩者使用相同 stable name、type、全 Layout 唯一 index 與 resolved
geometry；Slide 不得只填隱含繼承框，也不得另外畫一個普通 textbox 遮住空 Placeholder。文字 style
固定使用明確 insets／wrap／autoFit policy，不能依 Artifact Tool 或 PowerPoint 預設值猜測。

逐頁需要額外定位時，在 content／selection manifest 寫入 `composition_offset_percent`：至少包含
`dx`、`dy` 與 `basis`；整體置中還要保存原始 visible union、原中心與 target center。Renderer 將
offset 恰好套用一次，並同步位移 Layout Surface、rule、Layout Placeholder 與 Slide-local
Placeholder；背景、Theme token、寬高、字級與內容不得一起改變。未宣告 offset 時固定為 0；不同
offset 的頁面必須 materialize 成不同 Custom Layout。

整體置中以標題、副標與主要內容 Surface 的可見聯集為準。先在 declared Content Area 內求一筆
dx／dy，再透過 manifest 傳入 renderer；不可逐物件手調，也不可新增可選取的透明置中群組。正式
回歸必須用同一 locked contract 做 A/B：除定位策略／offset 外，Content、Theme、Layout、Variant、
background set、12px PPTX 圓角、字體、Surface、母片與 finalizer 完全相同。未位移頁面的
PowerPoint native render hash 必須不變；位移頁要檢查 source → Layout → Slide geometry、Reset、
overflow、背景 hash 與圓角 adjustment。

若使用者要求隨機 PPTX，先執行 `scripts/pptx_randomization.py` 建立可重播的 selection
manifest，再把它交給 `scripts/render_pptx_matrix.mjs --selection-manifest`。Seed 實際控制
Layout sequence 與相容 Variant；Theme 只有在明確 `--random-theme` 時才加入抽選，所有 draw
都必須寫回 manifest。

隨機不是檔名上的文字，而是可觀察的 seeded draw：候選 pool、PRNG state、`u`、index、selected
result 與 `randomized_dimensions` 都必須留在 manifest；相同 seed 必須重播相同的 Layout／Variant／
背景，換 seed 才能看到差異。預設固定 Theme；只有 `--random-theme` 明確開啟時才抽 Theme，且
候選必須有同 Theme 的 ready background set。背景風格要變化時使用 `--random-background`，它抽的
是完整六角色 background set，不是在每頁偷偷換一張舊圖。

標準入口形狀如下（路徑依當次 `$TMP_DIR`／deck name 替換）：

```powershell
python scripts\pptx_randomization.py `
  --content <content-manifest.json> `
  --seed <integer> `
  --random-background `
  --output artifacts\pptx\manifests\<deck>.selection.json

$RUNTIME_NODE scripts\render_pptx_matrix.mjs `
  --matrix artifacts\renderer-matrix\renderer-matrix.json `
  --selection-manifest artifacts\pptx\manifests\<deck>.selection.json `
  --output-dir <TMP_DIR>\output `
  --preview-dir <TMP_DIR>\previews `
  --inspect-dir <TMP_DIR>\inspect
```

`--style-case`、`--preset-demo` 或 Preset 的 example story 不是一般新 deck 的隨機入口；除非
使用者明確要求展示範例，否則內容先走 `new-deck`，再依內容語意抽 Layout。

## Background routing

- `background_mode=auto` 是本 Skill 的預設，正式輸出目標為 `hybrid`：無字 raster 背景位於 master／child layout，文字、表格、圖表、shape、內容圖片與 Placeholder 維持 native editable。只有使用者明確要求「不要生成圖片／native-only」時才使用 `background_mode=native-only`。
- **HTML 來源**：`background_mode=auto` 時先檢查來源 manifest 的 `asset_policy`、每頁 `media_requirement`、`data-pptx-background-image` 與內嵌 data URL。只要來源是 image-aware、存在 `with-image` Layout、或使用者要求圖片背景，而背景未達 `qa-pass`，就必須先執行 `slide-background-image`；不得直接把 placeholder、純色或未套圖 HTML 匯出成完成 PPTX。
- **原生 content manifest／無 HTML 來源**：沒有 HTML foreground 可供量測，不得錯誤呼叫 `slide-background-image`。依 `references/pptx-background-master-workflow.md` 建立或解析六角色 Image2 background set，逐張生成與 QA，再由 PowerPoint 原生物件模型寫入 child layouts。
- 已有通過 QA、Theme 相符且 provenance 完整的背景資產可直接沿用；不得為了「自動生圖」無條件重生相同資產。
- 新 deck 預設先以 `scripts/pptx_background_runtime.py` 解析 Theme-compatible background set；若沒有明確指定、Theme-compatible 且 `qa-pass` 的既有 set，狀態必須是 `generation-required` 並建立新的六角色 set。不得靜默回退到 `brand-editorial` 或其他 Theme 的舊資產。只有使用者明確要求重用，或既有 set 已通過相同 Theme 的 QA/provenance Gate，才可重用。
- 背景 set 必須先由 `prompt_system/pptx_background_sets/{set-id}.yaml` 宣告六個角色
  `cover / toc / content-a / content-b / content-c / qa`、`blank_regions`、
  `decoration_zones` 與 Theme 對應，再用內建 `image_gen` 逐張生成無字 PNG。不得用 PIL、SVG、
  HTML canvas、`render_*.py` 或其他 local renderer 冒充模型生圖；每張底圖都要驗證無文字、無
  logo、無假卡片／假圖表／Placeholder 外框，且高對比裝飾不侵入 blank region。
- 同 Theme 已有完整 provenance、asset hash 與 `qa-pass` 的 set 可以沿用；沒有就維持
  `generation-required` 並建立新的 set。Resolver 不得把失敗或缺圖的 set 靜默降級成舊的
  `brand-editorial` 背景。每次抽選與生成都要記錄 `background_set_id`、source manifest、seed、
  selection basis、逐角色 asset provenance 與 QA。
- `background_mode=auto` 的背景階段失敗時，輸出只能是 partial／audition；不得靜默降級為 `native-only`、純色母片、HTML 截圖或一般 slide 上的全頁圖片。
- deck manifest 必須保存 `background_pipeline`：`mode`、來源類型、目前狀態、背景 Skill／background-set handoff hash、逐頁或逐角色 asset provenance 與 QA report。狀態至少區分 `not-started → assets-ready → layouts-applied → qa-pass`；只有 `qa-pass` 可通過正式完成 Gate。

## 實作限制

- 依使用入口選擇 JavaScript builder：Codex／專案正式建檔使用 `@oai/artifact-tool`；HTML 編輯器的一鍵匯出使用內嵌 PptxGenJS browser adapter。
- 兩條路徑必須消費同一份 content／DOM manifest，並產生相同的 master、layout、placeholder 與 native-editable 契約；不得因工具不同降低交付標準。
- 禁止使用 `python-pptx` 或整頁 screenshot 作正式預設輸出。PptxGenJS 只允許用於上述 HTML 編輯器的一鍵匯出情境。
- 每個 theme 建立 master；每個 layout family 建立 child layout 與 placeholders；slide 必須連結 layout。
- renderer 以 theme/layout core 與 PPTX adapters 組成 manifest；既有 `pptx_spec` 只能作
  renderer override，不得直接套用 `html_spec`。
- 有 Art Direction 時，deck manifest 必須保留 direction id、source hash、scene role、
  visual intensity、signature move variant 與素材 provenance。Layout 必須在 scene role
  之後選擇，且不得把招牌手法烘焙成不可編輯的整頁圖片。
- PPTX 若採 `freeform-composition` 模式，content manifest 必須同時保存 1920×1080
  stage-space 的逐頁 Composition Plan：每個可見物件的 semantic role、穩定 id、geometry、
  z-order、text style、layer 與 placeholder policy。這是 HTML 級自由構圖的正式輸入，
  不是 builder 內部再寫一份座標表。
- `freeform-composition` 的定位約束由 renderer materialize：Content Area、safe area、
  background blank region、邊界留白、可見內容聯集的水平／垂直重心、物件碰撞與文字容量
  都必須在輸出前檢查。Theme 只提供 paint/token；Layout 只提供閱讀結構與約束；Composition
  才提供該頁的實際幾何。
- 每個不同的 Composition Plan 建立一個可追溯的 Custom Layout；背景與重複 chrome 放在
  layout/master，可編輯文字以 layout Placeholder 繼承到 slide。不能建立一個空
  Placeholder，再把真正可見文字另外畫成未關聯的普通文字框。
- `source_hashes` 只證明來源版本，不能證明 runtime 有消費來源。QA 必須另外比對
  source geometry／tokens 與 materialized layout／placeholder／slide XML；任一 mapping
  缺失時只能標為 partial。
- HTML 轉換前先產生 DOM manifest，記錄文字、geometry、computed style、transform、z-index、image source 與 semantic role。
- 前景物件採 `native` 優先；整份 PPTX 的正式預設是 `hybrid`。`native-only` 只在使用者明確要求無生成背景時使用，`flat` 只能用於 debug。
- `@oai/artifact-tool` 匯出後必須檢查並視需要執行 `scripts/repair_pptx_package.mjs <pptx>`：
  它會把 package Content Types／relationships 正規化，並將 named Placeholder 的 OOXML
  `p:ph type`／`idx` 與 manifest 對齊。PowerPoint 無法開啟、關係指向錯誤、或 duplicate／
  missing `p:ph` 時，不能把 artifact-tool export 當成完成品。
- Artifact Tool 沒有穩定保留 Custom Layout 背景／Surface 時，正式 Windows／PowerPoint 路徑必須在
  package repair 後執行 `scripts/finalize_pptx_layouts.ps1`。Finalizer 只能讀 selection manifest 的
  background role、Surface、12px 圓角與 composition offset，不得自行挑 Theme、背景或重算幾何；
  無法取得 PowerPoint 原生收尾時狀態只能是 partial。

## 流程

1. 驗證 Art Direction gate，以及 content manifest、Theme／Layout core、PPTX adapters 與可選 HTML／assembled YAML 的頁數和引用一致；記錄 `background_mode` 與來源類型。
2. 完成背景 Gate：`background_mode=auto` 的 HTML 來源依上節執行／驗證 `slide-background-image`，無 HTML 來源建立／驗證六角色 Image2 background set；背景狀態未達 `qa-pass` 時不得進入正式完成路徑。`background_mode=native-only` 則記錄使用者的明確要求與 skip reason，不執行 raster 背景流程。
3. 從 content manifest、core 與 adapters 建立 deck manifest；若有 HTML，合併使用者編輯後的文字、stage-space geometry 與已內嵌背景；若有 assembled YAML，只擷取本次需要的內容欄位。
4. 建立 theme master、color map、背景與共用 chrome。
5. 建立 layout family、Surface、rules、placeholders 與固定結構，連結 parent master；依 Composition
   Plan 套用一次 `composition_offset_percent`，raster 背景只放在 master／child layout。
6. 建立 slides 並以 `slide.setLayout(layout)` 指派；以相同 name／type／index／resolved geometry
   materialize Slide-local Placeholder，再填入可編輯內容。
7. 匯出 PPTX 與 layout inspection JSON。
8. 執行 package repair／normalization；需要 Custom Layout 圖片／Surface 的 Windows 正式路徑再執行
   `scripts/finalize_pptx_layouts.ps1`，接著用 PowerPoint／LibreOffice 原生 renderer render 全部
   投影片；逐頁檢查 clipping、overflow、錯誤換行、字型替代與 unintended overlap。
9. 執行 `slides_test.py`，並依每頁 `placeholder_schema` 做 master → child layout → slide 的
   OOXML exact check：`p:ph` type count、named id、index、slide relationship 均須一致，
   `pic`／`tbl` 要正規化為 `picture`／`table`。檢查背景圖片只在 master／child layout，
   一般 slide 不得重複放全頁背景圖。
10. 以同一頁的 Reset 前／後 layout JSON 或 OOXML 幾何做 pixel-exact 比對；title／subtitle
    的固定 frame 不得移動、縮放、fit 或被 Slide 層 reflow。若 native render 或 reset／
    placeholder check 不能取得證據，標為 partial／未驗證，不得寫成 pass。
11. 對有額外定位的頁面驗證 manifest visible union／target center／dx／dy；未宣告 offset 的頁面
    必須保持原 native render hash。Layout 與 Slide Placeholder geometry 誤差不得超過 1px。
12. 執行 `scripts/qa_pptx_positioning_contract.py`，直接檢查 package 內 Layout／Slide xfrm、Placeholder
    name／type／idx、背景 hash、Surface adjustment、slide→layout relationship 與 slide-level image。
13. 產生 QA ledger，逐頁列出 fidelity、背景來源、Custom Layout、raster fallback、
    native-editable 證據、random draw 與未驗證項目。

### Freeform composition mode

當使用者要求接近 HTML 的自由排版時，使用 `mode: freeform-composition`：

1. 先鎖定 Content Plan、Art Direction、Theme token 與 Layout scaffold；再為每頁建立
   Composition Plan，不把逐頁座標塞回 Theme 或 Layout core。
2. 以 1920×1080 stage-space 物化所有文字、圖片、shape、connector 與群組；PPTX 轉換只做
   `x/144`、`y/144`、`w/144`、`h/144` 的單一座標換算，不重新猜測 HTML 幾何。
3. Layout 建立與 Composition Plan 同步產生 named Placeholder；所有可見文字都必須能由
   stable slot id 找到對應的 Placeholder 或明確的 native text object。
4. 以實際文字高度收合內容群組，再在 declared Content Area 內置中；透明定位框只能是
   layout-only 計算資料，不能成為可選取的內容物件。
5. 每頁執行 safe-area、邊界留白、overlap、overflow、title wrapping、重心與
   master → layout → slide 關係檢查；任一項未通過不得宣稱母片合格。

## 輸出

- 正式 PPTX：`workspace/pptx/<deck-name>.pptx`
- renderer source：`workspace/pptx/builders/<deck-name>.mjs`
- manifest：`workspace/pptx/manifests/<deck-name>.json`
- QA：`artifacts/qa/pptx/<deck-name>.json`

不得把 scratch preview 或 layout JSON 當成正式交付物。

## Completion boundary

- `background_mode=auto`：背景資產已生成或驗證、實際寫入 master／child layouts、一般 slide 沒有重複全頁背景圖、前景保持 native editable，並且 PowerPoint 原生渲染與 package/XML QA 通過，才算完成。
- 所有正式路徑：Layout／Slide 必須有一一對應的 named typed Placeholder 與相同 resolved geometry；
  有 `composition_offset_percent` 時，Surface、rule 與兩層 Placeholder 必須同步位移，未位移頁不得產生
  外觀差異。任一項未驗證只能標為 partial。
- HTML 來源若仍停在 `image-planned`、placeholder-fill、`planned-not-materialized` 或缺少背景 data URL，只能標為 partial；不得將它描述為完成的圖片 PPTX。
- `background_mode=native-only`：必須保存使用者明確要求與無 raster fallback 的證據；仍需完成 master、Custom Layout、Placeholder、native object 與渲染 QA。OOXML Gate 必須依 `pptx.placeholder_schema` 精確比對每個 `p:ph` 的 type count、named id、index 與 slide→layout relationship（`pic`／`tbl` 需正規化），不能只以 Placeholder 存在作為通過證據。
