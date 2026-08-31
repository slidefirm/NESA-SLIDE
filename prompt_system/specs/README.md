# YAML Core Spec

這個目錄放的是新的核心 YAML 規格模板。

重點不是直接生成圖片，而是先定義一份跨媒介共用的 slide spec：

- `theme.template.yaml`: 共通視覺規則模板
- `slide.spec.template.yaml`: 單頁投影片核心規格模板
- `page_role.taxonomy.yaml`: 頁面角色分類
- `content_pattern.taxonomy.yaml`: 內容骨架分類
- `TAXONOMY_README.md`: taxonomy 使用方式
- `validation.checklist.template.yaml`: 檢查層模板
- `examples/`: 依新架構整理的實例頁面
  - `historical-editorial.theme.yaml`
  - `historical-medical-slide.yaml`

## 設計原則

- `theme` 是大集合，`2A` 與 `2B` 都在 theme 裡
- `layout` 描述頁面主要架構與元素關係，不只是座標
- `layout.module_style` 可標記模組語言，例如 `editorial-module`
- `layout.title_alignment_mode` 要明確指定：不是置中，就是錨定到主內容左緣
- `content` 先保留語意角色，不急著綁死到 renderer 細節
- `constraints` 是必要層，負責對齊、視覺重量、主從、間距與內容保護區
- `constraints.visual_exclusivity_rules` 可用來避免雙側同時出現互相搶戲的視覺主體
- `constraints.visual_budget_rules` 用來限制輔助插圖的版面權重，避免側邊插圖壓縮文字閱讀空間
- `constraints.prompt_translation_rules` 用來約束 image prompt 的寫法，避免把座標數字直接變成畫面文字
- `validation` 是輸出後檢查層，負責記錄這一頁是否通過版面品質檢查

## 近期新增的高價值原則

- 若一頁是「文字主導 + 側邊輔助插圖」，插圖只能支撐敘事，不能吃掉主內容的寬度與主導權。
- 標題系統只能採兩種穩定模式：
  - `centered_header`：主標與副標一起水平置中，底下模組也應跟著建立對稱秩序。
  - `content_anchored_left`：主標與副標一起對齊到主內容模組的左緣，而不是漂浮在頁面左側與內容區之間。
- 給圖片模型的 prompt 不應直接寫 `x=8%`、`y=88%` 這種機械座標，應改寫成自然空間描述。

## 目前範圍

目前先整理 YAML 結構，不處理 HTML、PPTX 或圖片 renderer 的具體實作。

## 檢查層

檢查層已先建檔，但目前先作為規格與紀錄層使用，暫時不宣稱已有完整自動檢測能力。

目前預設要檢查四件事：

- 周圍 10% 安全區是否沒有包含主要訊息
- 內容是否確實對齊到既定網格或中心軸
- 畫面是否出現文字、圖像、裝飾之間的視覺重疊
- 文字是否因字級過小或節奏過密而難以閱讀

未來 renderer 的分工應該是：

- `PPTX`: 把 spec 轉成文字框、圖片框、形狀與裝飾
- `Image`: 把 spec 轉成 assembled image prompt
- `HTML`: 把 spec 轉成版面與 CSS token
