# Portable Package Contract

可攜包是「clone 之後可以直接開始實作所有 Skill」的那個子集。它包含系統本身，不包含系統做過的東西。

判斷標準只有一條：**這個檔案是「怎麼做」的知識，還是「做過什麼」的紀錄？**
前者進包，後者留在本地。`prompt_system/` 的 Theme 與 Layout 是前者；
`artifacts/experiments/` 底下四萬六千個檔案是後者。

## 檔案清單由程式推導，不由人手維護

清單在 `packaging/portable-manifest.yaml`，由 `scripts/portable_manifest.py` 產生。

```powershell
python scripts/portable_manifest.py --write   # 重新產生
python scripts/portable_manifest.py --check   # 失效時失敗
```

`--check` 是 `scripts/audit.ps1` 的一項 Gate。清單與實際相依不一致時 audit 會 FAIL。

### 為什麼不能用手寫清單

腳本之間有三種相依，只看其中一種就會漏：

1. Python `import`：`generate_renderer_adapters.py` 匯入 `pptx_variant_runtime.py`。
2. 文件指令：`references/` 與 Skill 文件裡以命令形式出現的腳本。
3. Node `require`：這一種完全不出現在任何文件裡。`playwright_runtime.cjs` 被 24 支
   QA 腳本 require、`html_qa_selection.cjs` 被 6 支 require。漏掉它們，所有 Browser QA
   都會在新環境失敗，而清單看起來卻是完整的。

產生器把三種閉包都算完再取聯集，並把「只透過 require 才到得了」的共用模組
單獨列在 `scripts.node_shared_modules_not_named_in_docs`，讓審閱者看得見這一類。

## 驗收靠 clone，不靠開發工作樹

開發工作樹的 audit 全綠不代表包是好的。本專案多個 Gate 以檔案位元組計算 sha256，
而工作樹可能帶有從未進入 Git 的本地狀態。實例：`scripts/pptx_variant_runtime.py`
在 2026-08-28 之前未被追蹤，但 `generate_renderer_adapters.py` 匯入它——
當時任何新 clone 都會 ImportError，開發機卻完全正常。

```powershell
python scripts/smoke_test_portable_package.py
python scripts/smoke_test_portable_package.py --workdir D:\tmp\probe --keep
python scripts/smoke_test_portable_package.py --skip audit render
```

各階段與其回答的問題：

| 階段 | 問題 |
|---|---|
| `clone` | 這個 ref 能不能完整取出 |
| `path_lengths` | 最長路徑是否留下足夠的目標前綴空間 |
| `line_endings` | 取出的文字檔是不是 LF，位元組指紋 Gate 才會成立 |
| `manifest` | 清單列的東西是不是真的都在 |
| `imports` | 相依閉包對不對 |
| `skill_refs` | Skill 文件寫的每個專案路徑解不解得開 |
| `audit` | 完整體檢有沒有 FAIL |
| `render` | 能不能真的產出一份可編輯 HTML |

## Windows 路徑長度

Windows 路徑上限 260 字元。`path_lengths` 報告最長的被追蹤路徑，以及扣掉它之後
還剩多少字元給目標目錄。剩餘空間低於 80 字元時報 WARN：那代表 clone 到
使用者暫存目錄之類的較深位置會失敗，而 clone 到短路徑卻會成功——同一個 repo
在兩個地方行為不同，這是可攜性缺陷。

長路徑集中在產物目錄（`artifacts/html-presentations`、`deliverables`、
`deploy-snapshots`、`experiments`），可攜包本來就不收錄它們。

## 建置與同步

```powershell
python scripts/build_portable_package.py --output <目標目錄>
python scripts/build_portable_package.py --check  <既有套件目錄>
```

建置時會做三件清單以外的事：

1. 由 `.agents/skills` 產生 `.claude/skills`。
2. 對 `historical_exclusions` 中「仍被保留文件引用」的檔案寫入說明存根，
   而非直接移除——否則引用它的文件會指向不存在的路徑。存根會說明
   原因並指向目前的 source of truth。
3. 寫入 `PACKAGE_INFO.json`：來源 commit、分支、工作樹是否乾淨，
   以及每個檔案的 sha256。

`--check` 以該帳本逐檔比對主系統現況，輸出 `changed` / `missing` /
`added` / `no-longer-needed` / `stale-manifest`。主系統改動後不必記得要同步哪些檔案，
跑一次就有清單。從不乾淨的工作樹建置會發出警告，因為帳本無法追溯到某個 commit。

## 能力邊界

包含在可攜包內、但不代表能在任何環境完成的兩件事：

- **Image2 正式生圖**：七段式 YAML 組裝、Theme/Layout core 與 Image2 adapter 都可攜；
  正式 bitmap 生成需要模型影像 provider。
- **PPTX 原生產出**：Theme/Layout core 與 PPTX adapter 可攜；
  目前的原生 builder 依賴 Codex runtime。

這兩項在 manifest 的 `provider_required_capabilities` 記錄。
可攜包的說明文件必須照實標示，不得寫成「clone 完即可完整使用」。

## Agent Skill 鏡射

`.agents/skills/` 是唯一原稿；`.claude/skills/` 是由它產生的 checked-in mirror，讓
Claude Code 在 clone 後可以立即自動發現專案 Skills。兩份內容不得獨立維護。

修改 `.agents/skills/` 後執行 `npm run sync:skills`；提交與發布前執行
`npm run check:skills`。Portable package 建置仍會重新產生 mirror，避免把漂移帶入成品。

產生後應以 hash parity 驗證兩邊一致。

## 排除項目

| 目標 | 理由 |
|---|---|
| `artifacts/` 除 manifest 列出者外全部 | 產物與證據，不是系統 |
| `node_modules/` | 以 `npm install` 重建 |
| `sites-random-layout-catalog/` | 獨立 Git repository，見其自身 AGENTS.md |
| `tmp/`、`artifacts/archive/`、`artifacts/discarded/` | 已被 gitignore，僅存在於本地 |
