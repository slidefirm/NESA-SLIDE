# Claude 專案入口

這個檔案只負責把 Claude 類工具導向本專案的正式規格，不再另外複製一套命令與數量。
專案規則、正式 reference 或 repo-local Skill 更新時，以那些來源為準；不要在本檔另寫平行版本。

## 必讀順序

1. `AGENTS.md`
2. `prompt_system/AGENTS.md` 與 `prompt_system/README.md`
3. 本次 renderer 對應的正式入口：
   - Image2：`.agents/skills/generate-image-slide/SKILL.md`、`references/image2-preview-workflow.md`
   - HTML Pattern：`.agents/skills/html-pattern-slide/SKILL.md`
   - PPTX：`.agents/skills/ppt-builder/SKILL.md`
   - 部署：`references/layout-catalog-deployment.md`

## Source 路由

- Theme／Layout／style case 的定義與目前數量：讀 `prompt_system/`，不要用 `artifacts/` 反推。
- 七段式 assembled YAML：只供 Image2 的單次輸出；格式見 `references/project-format-guide.md`。
- HTML／PPTX：直接讀 core、各自 adapter 與 content manifest，不把 assembled YAML 當共同 runtime payload。
- Gallery、預覽、HTML、PPTX 與 QA 報告：位於 `artifacts/`，屬成品或證據。

## 不可混用的舊做法

- 正式 Image2 生圖由目前工作的 Codex 直接呼叫內建 `image_gen`，不從腳本啟動巢狀 `codex exec`。
- Layout Gallery 保留圖片式卡片；HTML／PPTX 案例放在獨立案例區，不在 Layout 卡片加連結。
- `scripts/generate_layout_gallery.py` 的 `EXCLUDED_IDS` 目前為空；Gallery 應覆蓋全部正式 Layout。
- 發布必須取得本次明確授權，並從乾淨、核准的 snapshot 或隔離 worktree 執行；不得使用 `--commit-dirty=true`。

要確認目前實際數量與缺口，執行 `powershell -ExecutionPolicy Bypass -File scripts\audit.ps1`，
不要把舊交接文件或歷史 audit 的數字當成今天的狀態。
