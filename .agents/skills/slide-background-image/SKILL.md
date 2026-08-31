---
name: slide-background-image
description: Generate, inspect, and attach one raster image background per HTML presentation slide by measuring actual foreground occupancy, either directly for an existing deck or as the required downstream stage of html-image-slide and HTML-sourced ppt-builder workflows. Preserve editable foreground objects and export backgrounds into PPTX slide layouts.
---

# HTML Image Background

將圖片背景視為可選的獨立 **Raster** 視覺層：前景 HTML 仍保留文字、卡片、圖表、流程、獨立照片／插圖與編輯器語意；Raster 只填補每頁實際留下的空間，不得把整頁截圖當成背景，也不得充當語意照片／插圖。

## Scope and contract

- 使用者直接要求圖片背景、生成背景、填補留白或替換背景時啟用本 Skill；上游 `html-image-slide` 的預設 `background_mode=auto`，以及 HTML 來源 `ppt-builder` 的預設 hybrid 背景路徑，也必須啟用本 Skill。這些上游 Skill 的明確呼叫已包含本機背景產製授權，不得再次把「要不要生圖」當成阻擋問題。
- 本 Skill 以已有可編輯 HTML 為輸入；若任務是新建或重新選擇含圖片的 Layout，先使用 `html-image-slide`，不要在這裡處理內容或版型路由。
- 本 Skill 只生成或套用抽象 Raster 背景。若上游 `with-image` 頁面選擇 `image_variant=photo`，上游必須先把獨立的、對應主張的 `semantic_photo` 放進 HTML 圖片區；本 Skill 不得生成、重畫、合併或取代它。
- 每頁先量測真實 HTML 前景，再生成對應的 16:9 raster asset；不要用同一張圖硬套所有頁面。
- 逐頁 composite QA 必須把「背景明暗」與「前景 surface／文字色」一起驗證；不能只確認背景已嵌入。
  深色實際 surface 使用淺色 ink，淺色實際 surface 使用深色 ink；透明 surface 必須先以實際 composited 底色判讀，
  不得用 Preset 的 accent-text 靜態推測取代對比檢查。
- 背景不得含文字、字母、數字、Logo、假卡片、假圖表、UI、可辨識物件或模仿前景內容的形狀；只有下方 SAFE ZONE contract 明確授權的 2B 邊緣／角落／接縫幾何可例外使用。這個例外只適用於生成的 raster 背景像素；HTML 前景仍不得用 CSS、inline SVG、pseudo-element 或可編輯 HTML 重畫同一 2B。
- 前景 DOM、`.el`、semantic module、`window.EditMode`、Undo/Redo 與 HTML 編輯能力不得被 flatten 或裁切掉。
- 產物先留在 `workspace/html-image-background/` 隔離目錄；`run.json` 的 `needs-review`、`source_was_modified: false` 與 `production_integration: false` 必須如實保留，除非另有正式核准流程。

### Upstream orchestration contract

- 接到 `html-image-slide` handoff 時，從已通過 foreground QA 的 HTML 開始；不得重新選 Story、Theme、Layout、Preset 或 Composition。`image_variant=photo` 時，來源 HTML 的 `semantic_photo` 必須已是獨立可選取物件，並被 browser measurement 視為 protected foreground。
- 接到 HTML 來源 `ppt-builder` handoff 時，若每頁已具有完整、內嵌且 QA 通過的 `data-pptx-background-image`，只驗證並沿用；若缺漏，先完成本 Skill，再把 final HTML／DOM manifest 交回 `ppt-builder`。
- 上游必須提供來源 HTML、renderer manifest、`background_mode`、逐頁 image role／safe-zone profile、`image_variant` 與素材 provenance。Photo 頁另需提供獨立 `semantic_photo` 的來源／hash／alt 與 page-claim brief；缺少必要量測輸入時才可停止並回報，不得靜默跳過背景階段。
- 本 Skill 回傳的正式狀態是 `masks-ready`、`images-ready`、`applied` 或 `qa-pass`；只有 `qa-pass` 可讓上游完成整項圖片交付。

## Layout-aware SAFE ZONE contract

SAFE ZONE is a slide-specific design contract, not one fixed rectangle reused for every slide. Resolve it from the measured HTML foreground, the selected `layout_id`, the `scene_role`, and the actual visual role of each image or content block.

Keep these two concepts separate:

- `protected_foreground_zone`: the measured `occupied_boxes` plus the measurement halo. High-frequency details, lines, recognizable shapes, fake text, and fake UI must not enter this zone.
- `semantic_safe_zone`: the layout-specific region where the generated background must support readability, focal hierarchy, and the intended composition. It is not necessarily identical to `occupied_boxes`, and it is not automatically blank.

Every slide prompt and run record must identify:

- `safe_zone_profile`: one of `content`, `half-image`, or `full-bleed` (or a project-approved named profile).
- `semantic_safe_regions`: regions that need a quiet, readable, or image-aware treatment.
- `free_design_regions`: regions where 2A material and 2B decoration may be composed.
- `forbidden_regions`: measured foreground, image focal subject, text overlay area, and any layout-specific exclusion.
- `profile_rationale`: why the profile was selected from the layout and scene role.

### Required SAFE ZONE profiles

- `content`: the body content area is a designed SAFE ZONE. Use low-frequency 2A material, tonal variation, and readable contrast around or behind the content; every slide must also show a restrained but distinguishable 2B edge/corner treatment in a named or profile-default free design region. Do not reduce the page to an unintentional empty rectangle or a texture-only fallback.
- `half-image`: resolve the text panel, image panel, split boundary, and image focal area separately. The text side needs a stable readable field; the image side must protect the real image subject and crop; every slide must show 2B as a controlled image-side edge treatment or seam accent. Do not place generic corner ornaments over the image subject or invent a second image, chart, or focal object.
- `full-bleed`: treat the full-slide image or dominant visual as the primary composition. The SAFE ZONE is the text-overlay/readability window, not a generic central box. Keep that window low-detail and contrast-safe, preserve the image focal subject, and use a visible image-aware edge treatment in one or two outer zones. Full-bleed may suppress generic corners, but it may not silently suppress 2B or fall back to texture-only; do not layer an unrelated paper frame or four-corner decoration over the visual.

The SAFE ZONE itself may receive a corresponding background design. “Protected” means that the design must remain subordinate and readable; it does not mean that the region must be visually empty. Only low-amplitude base material may cross a protected foreground zone, while semantic details must remain in the profile's permitted design regions.

### 2A / 2B prompt assembly

For every slide, assemble the image prompt from three explicit inputs:

1. `visual_base_2a`: background material, palette, tonal range, texture, lighting, and mood.
2. `corner_decoration_2b`: a required, visible profile-specific edge, corner, seam, or image-aware treatment. The location and primitive may change by profile; the 2B layer itself is not optional. Content pages use edge/corner details, half-image pages use image-side or split-boundary details, and full-bleed pages use image-aware edge treatment instead of generic corners.
3. `safe_zone_constraints`: the profile's semantic safe regions, protected foreground, image focal exclusions, and forbidden content.

2B details must always be concrete: name the zone, shape vocabulary, approximate scale, color/opacity range, and relationship to the foreground. If the layout has no `decoration` block, use the profile default recipe; do not omit 2B. Do not describe 2B as “barely perceptible” texture only, and do not force the same four-corner treatment onto every layout. These primitives are raster-background pixels only; they must never be materialized as editable HTML/CSS/SVG decoration.

At normal viewing size, a reviewer must be able to distinguish the low-frequency 2A material from the 2B edge/corner/seam treatment. For light backgrounds, 2B should normally be at least 15–20% visible opacity; for dark backgrounds, use a stronger 30%+ treatment unless contrast evidence requires another value. If the raster reads as texture, gradient, or a broad color field only, it fails this contract and must be regenerated.

If the layout or scene role cannot be classified confidently, record `safe_zone_profile: needs-review`, keep the background conservative, and do not claim layout-aware compliance.

## Workflow

1. 先用 `html-pattern-slide` 產生或選定可編輯 HTML，並確認 Theme／Layout／內容已經穩定。若是新建含圖片版型，先使用 `html-image-slide` 完成 Layout。Photo 頁必須先附上獨立 `semantic_photo`，再開始量測；不要把背景實驗當成版型、內容或照片插圖的替代品。

2. 建立逐頁量測 run：

   ```powershell
   python scripts/html_image_background_experiment.py prepare-deck `
     --input <source.html> `
     --run-dir workspace/html-image-background/<run-id>
   ```

   在瀏覽器載入 run 產生的 `mask-pages/`，等待 `document.documentElement.dataset.htmlImageBackgroundMasksReady` 或依頁面執行 mask script，保存 `masks.json`。每筆 record 必須保留 slide index、scene role、layout id 與 1920×1080 的 `occupied_boxes`。

3. 將每頁 record 交給內建 `imagegen` 逐張生成 Raster 背景，或套用使用者提供且已授權的 raster asset。使用 `prompts/slide-###-imagegen-prompt.txt` 作為限制，輸出檔名固定為 `slide-001.png`、`slide-002.png`……；Raster 只在候選 open zones 放置低對比材質、色場或抽象構圖。Photo 頁的 `semantic_photo` 是另一份既有資產，Raster 不得重畫它的主體。生成後逐張檢查前景對比、裁切與語意，不得以 PIL、SVG、Canvas 或 CSS 假冒模型生圖。

4. 將圖片套到隔離 HTML：

   ```powershell
   python scripts/html_image_background_experiment.py materialize-deck `
     --run-dir workspace/html-image-background/<run-id> `
     --masks-json workspace/html-image-background/<run-id>/masks.json

   python scripts/html_image_background_experiment.py apply-deck `
     --run-dir workspace/html-image-background/<run-id> `
     --background-dir <directory-containing-slide-001-to-slide-NNN-images>
   ```

   `apply-deck` 必須將每張圖片以 data URL 內嵌到對應 `.slide` 的 CSS `background-image`，並另外寫入
   `data-pptx-background-image="true"` 與相對來源 metadata；這樣單一 `file://` HTML 仍帶著圖片，
   不必依賴相鄰檔案或本機 server。原始 HTML 不得被改寫。

5. 逐頁驗證編輯前景：背景在最底層，文字與卡片仍可單獨選取；流程箭頭、圖片與 semantic module 的 selection frame 不得被背景攔截。至少檢查瀏覽器畫面、縮圖、投影模式與一個實際拖曳／Undo 操作。

## PPTX export contract

HTML 的 slide-level raster background 必須進入 `EditMode.buildPptxManifest()` 的 `slide.backgroundImage.dataUrl`，再由內嵌 `PptxBrowserExport` 寫入該頁專用的 child-layout/master image object。內容物件仍以 native text、shape、line、table 或 picture 輸出。

- 背景圖片放在 `ppt/slideLayouts/` 對應的 layout，不要重複放進 `ppt/slides/` 的一般物件清單。
- 有 raster background 時，匯出分級是 `hybrid`：背景是圖片，前景內容仍可編輯；沒有 raster background 時才可標成 `native-only`。
- `file://` HTML 不應把相對圖片的讀取責任留給瀏覽器：`apply-deck` 必須先嵌入 data URL；
  browser adapter 仍可對同源外部圖片嘗試 `fetch()`／已載入圖片 fallback，但不得讓 PPTX 遺失已嵌入的背景。
- 匯出失敗時保留 manifest／QA 證據，不要用整頁 screenshot 或把背景誤當成一般可選前景圖片補洞。

## QA

對實際隔離成品執行：

```powershell
node scripts/qa_html_repeat_group.cjs `
  --html workspace/html-image-background/<run-id>/final.html `
  --report workspace/html-image-background/<run-id>/qa/object-tree.json

node scripts/qa_html_pptx_browser_export.cjs `
  --html workspace/html-image-background/<run-id>/final.html `
  --output workspace/html-image-background/<run-id>/qa/exported.pptx `
  --report workspace/html-image-background/<run-id>/qa/pptx-export.json

node scripts/qa_html_delete_and_mask.cjs `
  --html workspace/html-image-background/<run-id>/final.html `
  --report workspace/html-image-background/<run-id>/qa/delete-mask-regression.json
```

通過條件：每頁有正確 Raster 背景 asset；HTML foreground 沒有被取代；Photo 頁的獨立 `semantic_photo` 仍存在、可選取且與 Raster 為不同資產；PPTX package 的 layout XML 含預期背景圖片關係；slide XML 沒有因背景而增加整頁 `<p:pic>`；前景文字仍是 native text；沒有 fidelity overlay；`run.json` 的視覺人工審查狀態仍被正確回報。
