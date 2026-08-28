# PPTX Image2 背景母片工作流

跨 Renderer 的規則優先順序與 PPTX 生產契約見
`references/presentation-production-contract.md`；本文件只保留背景母片的實作順序。

## 目的

把「視覺完成度」與「內容可編輯性」拆開：

- Image2 負責無字、無內容結構的品牌底圖。
- PowerPoint master/layout 負責 Placeholder 與可編輯內容。
- Theme core 仍是色彩、字體、材質與裝飾語彙的來源。
- Layout core 仍是內容語意來源，但 PPTX 會投影到六個背景角色。

## 六個背景角色

| role | 用途 | 主要空白方向 |
| --- | --- | --- |
| `cover` | 封面、章節開場 | 左側或中央主文區 |
| `toc` | 目錄、章節地圖 | 中央大區域 |
| `content-a` | 一般內文 | 左側 |
| `content-b` | 一般內文 | 右側 |
| `content-c` | 流程、比較、圖表、長文 | 中央大區域 |
| `qa` | KPI、QA、驗收、數據摘要 | 中央大區域 |

## Fresh background selection

正式 PPTX 入口先使用 `scripts/pptx_background_runtime.py` 解析 `theme_id`、可選的
`background_set_id` 或 runtime manifest。Resolver 會驗證 Theme 一致性、六個角色與素材，
並記錄 `background_set_id`、`source_manifest`、`selection_basis`、seed 與 provenance。
找不到相容 set 時回傳 `generation-required` 與新的六角色生成計畫；不得默默回退至
`brand-editorial` 或其他 Theme 的舊底圖。只有使用者明確要求重用，或相同 Theme 的既有 set
已有 `qa-pass` 與完整 provenance，才可重用。

## 正式順序

1. 建立 `prompt_system/pptx_background_sets/{theme-id}.yaml`。
2. 先宣告每張底圖的 `blank_regions`、`decoration_zones` 與 Placeholder。
3. 執行：

   ```powershell
   python scripts\generate_pptx_background_prompts.py `
     --background-set prompt_system\pptx_background_sets\brand-editorial.yaml `
     --runtime-output artifacts\pptx-backgrounds\brand-editorial\runtime-manifest.json
   ```

4. 依六份 assembled YAML 逐張用 Image2 生成 PNG；禁止並發。
5. 逐張檢查：
   - 完全無文字、字母、數字與 logo 字樣。
   - 完全無假卡片、圖表、表格、內容框與 UI 面板。
   - `blank_regions` 內沒有高對比物件或密集紋理。
   - 裝飾集中在 `decoration_zones`，且整體重心平衡。
6. 先執行 `scripts/build_pptx_background_master.mjs` 建立 PPTX seed deck。
7. 再用 PowerPoint 原生物件模型建立真正的 Custom Layout、母片底圖與 Placeholder：

   ```powershell
   scripts\finalize_pptx_background_master.ps1 `
     -InputPptx artifacts\pptx-backgrounds\brand-editorial\brand-editorial-background-master-demo.pptx `
     -RuntimeManifest artifacts\pptx-backgrounds\brand-editorial\runtime-manifest.json `
     -OutputPptx artifacts\pptx-backgrounds\brand-editorial\brand-editorial-background-master-demo-final.pptx `
     -PreviewDir artifacts\pptx-backgrounds\brand-editorial\powerpoint-preview
   ```

8. 檢查 PPTX 壓縮結構：六張底圖必須寫在 `ppt/slideLayouts/`，一般 `ppt/slides/`
   不得重複放入背景圖。
9. 用 PowerPoint 渲染六張 demo slides，逐頁檢查並執行 `slides_test.py`。

## Per-page typed selection mode

當一份 deck 的每頁已經由 PPTX Variant adapter 解析出不同的 `placeholder_schema`，使用同一個
`finalize_pptx_background_master.ps1` 加上 `-SelectionManifest`。這會交由
`finalize_pptx_selection_master.ps1` 在 PowerPoint COM 中重建每頁的 Custom Layout、layout-only
background 與 exact typed Placeholder；artifact-tool seed 內已建立的 native chart、table、picture
會逐頁複製到新 Slide，不能用文字框或整頁圖片代替。selection manifest 必須保存候選、選定
Layout／Variant、typed schema、reset policy 與原生物件的來源 payload。

PowerPoint COM 對同一 Custom Layout 的 `title` 與 `subtitle` 各只允許一個 Placeholder；若 Variant
合法地有第二個這類語意 slot，finalizer 必須保留第一個 typed Placeholder，並將其餘 slot 以同一個
schema region、named provenance 與 `native-text-powerpoint-api-limit` materialization 寫進 Slide。不得將
它改成 `body` Placeholder、移位、隱藏或以整頁圖片補償；QA 需列出這個 API 限制與每個 mapping。

## 重要邊界

- 底圖是背景，不是整頁簡報；底圖不能含任何真正內容。
- Placeholder 幾何必須來自 manifest，不做圖片完成後的自動空白偵測。
- 有宣告 `content_groups` 的版型，必須先根據實際文字高度縮合 Placeholder，再將整組內容於
  group region 內垂直置中；不得將每個文字框各自置中。
- 背景圖放在 child layout，不放在一般 slide，也不依賴 saved-template re-import。
- 目前 `@oai/artifact-tool` 可描述 layout，但匯出時不會穩定寫入 Custom Layout 圖片；
  因此最後寫入必須交給 PowerPoint 原生物件模型，不得把空白 layout 當成成功。
- 最終分級為 `hybrid`：背景 raster，內容 native editable。
- 若底圖 QA 未通過，PPTX builder 必須停止，不得用純色或 HTML 截圖假裝正式底圖。
