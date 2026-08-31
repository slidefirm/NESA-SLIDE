# Prompt System

`prompt_system/` 是本專案的 reusable building blocks 目錄。這裡只放未來會重複組合的 layout、theme、style case、規格與必要 reference assets。

## 目錄角色

- `layouts/`：正式 layout library。定義 `media_requirement`、slot、region、safe area、alignment、visual balance 與結構語意。
- `themes/`：可重複使用的視覺語言。管理 palette、typography、texture、decoration vocabulary。
- `presets/catalog.yaml`：HTML PRESET 身分、能力、公開狀態與 Gallery 順序的唯一名冊。完整案例只留在 `demos/`；`renderers/html/preset-themes.yaml` 只保存可重複套用的外觀設計要素，不得保存舊內容、版型序列或案例 CSS。
- `art_direction/`：多頁 deck 的敘事隱喻、參考方法、招牌手法、素材家族、scene grammar 與人工 gate。
- `style_cases/`：layout + theme 的示範組合。可指向 preview，但 preview 圖不是 source of truth。
- `content` 欄位：由 AI 在每次組裝七段式 YAML 時依素材、layout 與溝通任務即時決定，不在 `prompt_system/` 留存靜態內容規格。
- `reference_assets/`：style case 明確引用且無法再生的少量來源圖片。
- `design_elements/`：可重複使用的設計元素語彙。
- `specs/`：早期或補充規格。
- `assembly_template.txt`：prompt assembly 參考模板。
- `renderers/`：由 core theme/layout 自動生成的 Image2、HTML、PPTX adapter；不是第二套 source of truth。
- `renderers/html/layout-variants/`：HTML Layout adapter 的 renderer-specific composition 變體來源；只保存內容帶狀結構、選擇條件與降級路徑，不保存 Theme 外觀、單次文案或跨 renderer Layout 幾何。
- `HANDOFF.md`：歷史 handoff 與工作備忘。

## Layer 邊界

- Layout 只描述結構與空間，不放單次文案或具體視覺風格。
- HTML new-deck 先建立不含 Layout 身分的 page content，再選擇 Layout scaffold；逐頁 composition
  只把既有內容投影到 scaffold 並重算幾何，不得回頭從 Layout ID 取得或改寫文案。
- `layout_content` 與 renderer 內的 Layout-keyed copy 只屬歷史 manifest／Gallery fixture 相容入口，
  不得成為 new-deck 的正式 content schema。
- Theme 描述視覺語言，不綁死單一 layout。
- Art Direction 位於 Story 與 Theme／Layout 選擇之間，不是第四種 renderer，
  也不得另存為綁死內容的 Theme 或 Layout fork。
- 「2A」一詞有兩個所在，注意別混用：theme 檔內的 `visual_base` 段是素材
  「來源」；七段式 assembled YAML 的 `visual_base_2a` 段是組裝後的「輸出」。
  兩者結構不同，對應表在 `references/project-format-guide.md`。
  回答素材庫問題時讀這裡（`prompt_system/`），不要拿組裝成品或
  `artifacts/` 內容代答。
- Style case 展示 layout 和 theme 如何組合，但不應取代 layout/theme 本身。
- HTML 的 Layout／renderer-base 獨占位置、尺寸、排列與 overflow；Theme／Preset 只可改色彩、字體家族、字重與不改變盒模型的表面效果。完整可執行規則見 `references/html-css-ownership-contract.md`。
- Assembled YAML 是生成後的單次 prompt payload，預設放在 `artifacts/generated-prompts/`，不放回 `prompt_system/` 當模板。
- 三種輸出共用的是 Art Direction、theme/layout core 語意，不強迫共用同一份 runtime payload。Adapter contract 見
  `references/renderer-adapter-contract.md`，產生器為 `scripts/generate_renderer_adapters.py`。
- 裝飾線／色帶若屬於父模組的 `anchored-edge` 關係，也必須沿這條共用語意走：HTML 使用
  `data-edit-anchor="bottom"` 交給 editor 回流，其他 renderer 由 adapter materialize 成父模組內
  的 native 幾何；詳細契約見 `references/html-generation-rules.md`。
- 目前已驗收的跨 Renderer 生產原則、排版重心、HTML 編輯契約與 PPTX 母片流程統一整理在
  `references/presentation-production-contract.md`。

## 與 renderer 的關係

- 圖片式 preview：core + Image2 adapter 組成七段式 assembled YAML，再以其作為完整設計規格；Image2 本身會產生完整影像，因此可選 `no-image` 與 `with-image` Layout。
- HTML renderer：Art Direction + core + HTML adapter 組成 HTML render manifest，再依 `references/html-generation-rules.md` 與 `references/html-layout-patterns.md` 產 HTML。
- HTML 內容語意 icon 在 build-time 依 `references/svg-icon-generation-rules.md` 逐 deck 一次生成完整 family；renderer 只讀取已鎖定的 deck-local manifest，不在 runtime 生圖，也不預設維護全域 icon registry。
- HTML 的 `pattern-only` 素材策略只能選 `media_requirement: no-image`；若交付前會補上真實圖片，必須明確使用 `image-planned`，才能選用 `with-image` Layout。
- PRESET Gallery：先由 `presets/catalog.yaml` 決定公開名單與順序，再依每筆能力讀取 Theme Lab 案例或 reusable Preset 實作；Gallery 可展示案例，但 new-deck 產製不得把案例內容、版型序列或 CSS 帶回成品。
- PPTX renderer：Art Direction + core + PPTX adapter 組成 master/layout/placeholder manifest，再依 `.agents/skills/ppt-builder/` 與 `references/pptx-generation-rules.md` 建立可編輯 PPTX。HTML 只可作使用者編輯結果與幾何校準來源，不可整頁截圖冒充可編輯 PPTX。

詳細架構請看 `docs/architecture.md` 與 `docs/asset-taxonomy.md`。
