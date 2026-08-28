# HTML Theme Lab 設計歸檔

Theme Lab 採內容先行的組裝流程；2026-07 的視覺重構進一步統一可讀性底線，但保留每套主題的內容、敘事架構、字體與配色語氣：

`Subject → Narrative → Composition Variant → Header Placement → Surface Treatment → Theme Pattern → Editor`

正式機器可讀內容：

- 原始三套：`prompt_system/demos/html-theme-lab.json`
- 延伸十一套：`prompt_system/demos/html-theme-lab-extensions.json`

正式生成器：`scripts/render_authored_html_deck.py`

生成結果與 hash：`artifacts/theme-demos/html-theme-lab/theme-lab-archive.json`

## 十三個公開 Theme 與一個未公開測試稿

| Theme | 實際主題 | 組裝語法 | 主要設計技巧 |
|---|---|---|---|
| `line-argument-journal` | 夜間照護公共服務 | 線性論證誌 | 襯線主張、酒紅證據規則、編輯式留白、無圖片論證 |
| `signal-route-atlas` | 跨部門產品訊號路由 | 訊號軌道路線圖 | 窄體營運層級、雙色狀態規則、決策循環、冷霧資訊面 |
| `field-index-manual` | 傳統市場數位交接 | 田野索引手冊 | 灰綠紙色、交接索引碼、維護台帳、清楚欄位分隔 |

原始三份 Theme 各有 12 頁完整內容；三份內容主題、敘事架構、Composition Grammar 與技巧集合皆不同，共用的只有 1920×1080 Content Area、編輯器契約、投影控制與 QA 標準。

原始三套保留 12 頁；延伸十一套各有 10 頁，來源庫共 14 套、146 頁。其中
`moonlit-herbarium-atlas` 在 `prompt_system/presets/catalog.yaml` 標記為 `draft`，公開 Theme Lab 為 13 套、136 頁。
公開的十三套不是換色版本：每頁會另外產生可重現的 composition variant、header placement
與 surface treatment，再套入 Theme Pattern。

| Theme | 實際主題 | 視覺系統 |
|---|---|---|
| `tide-signal-observatory` | 海岸感測網 | 深海高對比、觀測列、決策黃標 |
| `craft-archive-editions` | 工藝記憶地圖 | 暖紙、編目列、硃紅校樣 |
| `incident-command-redline` | 資安事件指揮 | 黑色戰情底、紅色狀態線、決策台帳 |
| `harbor-ribbon-program` | 港灣光節 | 日光紙色、海港藍字、珊瑚橘規則 |
| `neighborhood-newsroom-proof` | 社區新聞室 | 新聞紙、欄目、校樣線、更正流程 |
| `scent-veil-launch` | 香氛上市 | 柔白底、梅紫襯線字、細緻留白 |
| `restoration-blueprint-ledger` | 老屋修復 | 測繪紙、深藍字、銅色修訂註記 |
| `ai-operations-signal` | AI 工作流導入 | 深綠運營面板、酸綠／藍色治理訊號 |
| `brave-classroom-contours` | 勇敢教室 | 暖白底、低壓圓角資訊面、橘綠色標 |
| `night-transit-wayfinding` | 夜間交通韌性 | 深夜底、站點索引、琥珀／青色導引 |
| `moonlit-herbarium-atlas` | 城市授粉者微棲地 | 未公開測試稿；不在十三份公開重建與發布範圍 |

十三套公開 HTML 遵守四項視覺底線：AI 生成文字最小 36px；投影片內容使用
`pattern-and-geometry-only`，圖片、插畫、SVG 與 image URL 數量為 0；內容群組在
1728×888 Content Area 中維持水平與垂直重心；每份至少使用三種標題位置與三種內容表面。
固定種子只用來重建相同結果，不允許所有 Theme 共用「標題＋兩欄方塊＋橫線」骨架。

## 重建與 QA

```powershell
python scripts\build_html_theme_lab.py --preserve-theme moonlit-herbarium-atlas
node scripts\capture_html_matrix.cjs --html-dir artifacts\theme-demos\html-theme-lab\html --output-dir artifacts\theme-demos\html-theme-lab\qa\screenshots --report artifacts\theme-demos\html-theme-lab\qa\capture-report.json
python scripts\verify_embedded_editor.py --source src\html-editor\edit-mode.js --html-dir artifacts\theme-demos\html-theme-lab\html --output artifacts\theme-demos\html-theme-lab\qa\editor-sync.json
python scripts\build_renderer_case_site.py
python scripts\build_html_theme_lab_subpage.py
python scripts\verify_html_theme_lab.py
```

## 發布

發布不是 Theme Lab 重建流程的一部分。只有使用者針對本次工作明確授權後，才依
`references/layout-catalog-deployment.md` 從乾淨、經核准的 deploy snapshot／隔離 worktree
發布案例站與主站；不得使用 `--commit-dirty=true`。發布後必須驗證使用者指定的完整
host／path，並比對本機核准 artifact。

公開入口：`https://master.layout-catalog.pages.dev/theme-html-lab/`
