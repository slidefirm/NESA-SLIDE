# scripts 目錄說明

`scripts/` 只保留正式 Gallery、YAML 圖片生成、QA 與必要支援工具。

## Active entrypoints

- `generate_layout_gallery.py`：建立 main layout gallery。
- `verify_layout_gallery_triptychs.py`：部署前強制檢查每個 Layout 恰有三個存在、內容不同且非 SVG 藍圖的案例；任一素材被刪除即以非零狀態阻止發布。
- `check_active_artifact_references.py`：清理前檢查候選路徑是否仍被正式 Gallery 或追蹤中的 JSON／YAML manifest 引用；有 active dependency 時回報 `BLOCKED` 並以非零狀態阻止整體刪除。
- `generate_theme_gallery.py`：建立 theme gallery。
- `generate_theme_preview_prompts.py`：建立 theme preview 的 assembled YAML。
- `log_layout_preview_qa.py`：寫入 preview QA JSONL，並記錄實際圖片與 Layout source 的 SHA-256。
- `generate_image2_from_yaml.ps1`：Image2 API fallback，需完整 assembled YAML。
- `gen_from_assembled_yamls.ps1`：已退休的相容入口；會直接停止並指向目前的內建 `image_gen` 與乾淨部署流程，不再生圖或部署。
- `verify_layout_preview_qa.py`：只讀 preview 與 QA JSONL，檢查正式 preview 是否齊全、
  最新 QA 是否通過，以及 QA 的圖片路徑、圖片 SHA-256、Layout source SHA-256
  是否仍對應目前檔案。
- `generate_renderer_adapters.py`：由正式 theme/layout core 確定性產生 Image2、HTML、PPTX
  adapters；使用 `--check` 驗證當次 core 對應的全部 adapter 是否完整且未過期。
- `art_direction.py`：驗證 Story 與 Theme／Layout 之間的 Art Direction，
  並產生三種 renderer 共用的 handoff；`--require-approved` 是正式輸出的人工 gate。
- `compile_renderer_matrix.py`：解析 core + adapters，依當次 registry 建立 renderer matrix JSON。
- `render_html_matrix.py`：每個 Theme 產生一份包含全部 Layout 的 HTML catalog。
- `render_pptx_matrix.mjs`：以 artifact-tool 每個 Theme 產生一份包含全部 Layout 的可編輯 PPTX catalog。
- `pptx_randomization.py`：以 seed 從語意 Layout pool、相容 Variant 與可用背景組建立可重播的 PPTX selection manifest。
- `render_pptx_matrix.mjs --selection-manifest`：消費上述 selection manifest，輸出單一隨機選擇的可編輯 PPTX deck。
- `capture_html_matrix.cjs`：用 Chrome/Edge 逐張截圖並檢查 HTML overflow。
- `render_pptx_matrix_with_powerpoint.ps1`：用本機 PowerPoint 原生匯出全部 PPTX slides。
- `verify_renderer_matrix.py`：核對 Theme/Layout 覆蓋、PPTX master/layout/slide 結構與全部 QA 圖片。

## Support utilities

- `convert_deploy_png_to_webp.py`：為 Gallery 產生 WebP。
- `build_layout_review_gallery.py`：為尚未解決的 QA candidate 建立 review 頁。
- `layout_gallery_codex_server.py`：只供本機檢視 Gallery 的靜態 server；舊 Codex 自動重生端點已停用並回傳 HTTP 410。
- `paths.py`：共用路徑常數。
