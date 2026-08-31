# HTML 設計方法來源與授權邊界

## 結論

本專案只吸收公開文件中可抽象描述的工作方法，所有規格、YAML、Python、HTML、CSS 與 QA
均在本專案內重新設計與撰寫。沒有複製下列專案的程式碼、模板、Prompt、圖像、字型或其他素材，
因此目前不把第三方程式碼併入本專案的 MIT 授權範圍。

若未來真的引入第三方程式碼或素材，必須在合併前另做授權審核，保留原作者著作權與授權聲明，
並視需要新增 `THIRD_PARTY_NOTICES.md`。僅看過某個專案，不代表可以把它的實作直接貼入本專案。

## 採用的抽象方法

| 來源 | 只參考的方法 | 本專案的獨立實作 |
|---|---|---|
| [frontend-slides](https://github.com/zarazhangrui/frontend-slides) | 先看少量視覺方向再決定 | `visual_checkpoint`，預設關閉，只有明確探索時才啟用 |
| [huashu-design](https://github.com/alchaincyf/huashu-design) | 提早展示、簡化檢查 | 四題 `keep / fix / quick-win` deck review |
| [visual-explainer](https://github.com/nicobailon/visual-explainer) | 依內容關係分流 | `content_routing` 將比較、循環、層級、證據等意圖映射到本專案 Layout |
| [guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) | 敘事與分析用途要分流 | 只保留用途分流概念；不採用 WebGL，也不引入其 AGPL-3.0 程式碼或素材 |
| [html-ppt-skill](https://github.com/lewislulu/html-ppt-skill) | Presenter workspace 的需求方向 | 暫緩，不在本輪實作 |
| [open-slide](https://github.com/1weiho/open-slide) | 物件留言集中交給 AI 修改 | 暫緩，不在本輪實作 |
| [slide-writer](https://github.com/FeeiCN/slide-writer) | Theme 標示適用／不適用情境 | `theme_selection_profiles.best_for / avoid_for` |
| [ppt-agent-skill](https://github.com/Akxan/ppt-agent-skill) | 常見失敗類型與跨頁節奏 | 四題 deck review 的骨架重複、節奏與構圖適配檢查 |
| [skills-slides](https://github.com/nghiahsgs/skills-slides) | Pattern／Effect 的使用標籤 | 相容情境、效能、可讀性風險、投影安全與透明度上限 |
| [next-slide](https://github.com/codesstar/next-slide) | 簡單風格分類與招牌構圖 | 每種內容意圖都有 `signature_composition` 與 `ordinary_grid_loss` |

## 明確不採用

- 不複製任何第三方原始碼、CSS、Prompt 或模板。
- 不採用 WebGL 作為簡報背景或互動依賴。
- 不把三方向預覽變成每次生成前的強制步驟。
- 不在本輪加入講稿、計時器、下一頁預覽或物件留言給 AI。
- 不用雷達圖或假精準分數取代人工設計判斷。

## 本專案授權

本專案根目錄的 `LICENSE` 使用 MIT License。MIT 允許使用、修改、散布與再授權，
但散布本專案程式碼或其重要部分時，必須保留原始著作權與授權聲明。
