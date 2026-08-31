# Themes Library

這份清單是目前 `prompt_system/themes/` 的 reusable theme library。

> 命名提醒：本目錄的「2A」指 theme 檔內的 `visual_base` 段（素材來源）；
> 七段式 assembled YAML 的 `visual_base_2a` 是它的「輸出」，兩者結構不同。
> 對應規則的唯一權威版本在 `references/project-format-guide.md` 的
> 「素材層 theme → 本格式的對應規則」。

## Theme 檔標準結構（schema）

每個 theme 檔必須符合以下形狀。原則：身分欄位釘死、字級留活。

```yaml
id: kebab-case-id
display_name: 中文顯示名
source: 來源說明

# ── Layer 2A: 視覺基底 ──
visual_base:
  background_style: 一句自然語言（材質與氛圍）
  background_color: "#XXXXXX"

  color_palette:
    primary:   { hex: "#XXXXXX", use: 用途 }
    secondary: { hex: "#XXXXXX", use: 用途 }
    surface:   { hex: "#XXXXXX", use: 主要資訊表面（選填） }
    accent:    { hex: "#XXXXXX", use: 用途（小面積強調） }
    support:
      - { hex: "#XXXXXX", use: 用途 }

  typography:
    heading:
      family: "字體家族"          # 身分欄位，釘死，組裝時直接帶入
      weight: "粗細"              # 身分欄位，釘死
      size_hint: "字級傾向描述"    # 只寫傾向（如「取角色範圍上緣」），不寫死數字
      note: "其餘性格描述"         # 選填：對比、氣質等
    body:
      family: "字體家族"
      weight: "粗細"
      size_hint: "字級傾向 + 行距傾向"
      note: "選填"

  illustration_style:
    default: "扁平插畫 / 3D風格 / 線條圖示 / 抽象藝術 / 無"   # 五選一
    note: 使用時機說明；單頁組裝時可依內容覆寫

  mood: [情緒標籤]

# ── Layer 2B: 裝飾詞彙 ──
decoration_vocabulary:
  - name: kebab-case-name
    visual: 視覺描述
    placement: 放置位置
    density: always / high / medium / low

closing_statement: >
  英文收尾原則，一段話。
```

`surface` 是主要資訊表面的語意角色；需要卡片、圖表底或模組表面時，優先使用它。
`support` 只描述流程線、狀態節點、圖示或少量輔助訊號，不能因為色彩對比高就自動升格成大面積 surface。
未宣告 `surface` 的舊 Theme 才允許由 renderer 以 support 作相容 fallback。

為什麼字級不寫死：具體 px/pt 由每頁組裝時依 size_hint + 角色字級範圍
（`references/html-generation-rules.md`）+ 本頁內容量現算，Theme 只管傾向。
已確認滿意、要原樣重現的幾何數值，應提升到 Layout／Composition／renderer-base 的
正式來源與回歸測試；不得寫回 Theme Core。

## 既有 themes

- `dark-circuit`：暗黑電路板，來自 Claude Code 類科技簡報
- `brand-editorial`：品牌排版風，來自排版實戰班
- `corporate-blue`：白底深藍企業風
- `teal-tech`：淺灰底藍綠科技風

## 2026-07-03 新增：跨格式 Theme 試點

- `tech-navy`：科技深藍，冷色調 cyan 強調色，低調有序
  - 來自 html-pattern-slide 實驗（toc-3-vertical 企業 AI 導入路線圖 demo）
  - 三種輸出只共用 `visual_base`、`decoration_vocabulary` 與 `closing_statement`
    的視覺語意；renderer-specific 幾何由各自的 Layout／Composition materialize，
    不在 Theme Core 保存 `html_spec`、`pptx_spec` 或 `layout_overrides`。

## 2026-06-12 新增 themes（來自 Downloads 模板分析）

- `grainy-editorial`
  - 對應：Brown Minimalist Grainy Pitch Deck / Minimalist Business Slides XL
  - 關鍵字：紙感、顆粒、出版、極簡

- `brutal-grunge`
  - 對應：Brutal Grunge Portfolio
  - 關鍵字：粗獷、框景、黑白攝影、作品集

- `soft-organic-education`
  - 對應：Elegant Education Pack / elegant-workplan
  - 關鍵字：教育、有機塊、柔和、友善

- `clinical-report`
  - 對應：Formal Style Case Report / Vocational Guidance Process
  - 關鍵字：正式、藍灰、報告、流程教學

- `workshop-human`
  - 對應：Mental Health in the Workplace Workshop
  - 關鍵字：工作坊、人本、攝影、粗字

- `lavender-media-kit`
  - 對應：Professional Media Kit
  - 關鍵字：淡紫、媒體包、品牌感、中心構圖

- `festive-patterned`
  - 對應：Stuttgarter Weindorf XL
  - 關鍵字：節慶、圖騰、文化活動、黑金奶油

- `clean-tech-business`
  - 對應：Technology Company Business Plan
  - 關鍵字：白底科技商務、提案、扁平插圖

- `paper-collage-vintage`
  - 對應：Vintage Torn Paper Aesthetic Agency XL
  - 關鍵字：撕紙、膠帶、拼貼、復古 agency

- `warm-editorial-portfolio`
  - 對應：Gamma / Slidesgo 的編輯式作品集與 quote 類模板觀察
  - 關鍵字：暖白、grainy photo、作品集、編輯感

- `executive-analytics`
  - 對應：Beautiful.ai reporting / dashboard + Gamma review / benchmark 類模板
  - 關鍵字：KPI、dashboard、QBR、報告、決策感

- `strategy-consulting`
  - 對應：Gamma strategy / consulting + Slidesgo strategy / problem-solution 類模板
  - 關鍵字：顧問、提案、建議排序、問題解法、策略聚焦

- `impact-report`
  - 對應：Gamma case study / impact report / research findings + Beautiful.ai case study
  - 關鍵字：成果展示、案例、研究發現、年度回顧、可信敘事

- `facilitation-learning`
  - 對應：Gamma workshop facilitation / onboarding + Beautiful.ai training & onboarding
  - 關鍵字：工作坊、教學、onboarding、learning module、帶領感

- `brand-activation`
  - 對應：Gamma event marketing + Beautiful.ai media kit / event recap / marketing
  - 關鍵字：campaign、event、media kit、品牌展示、CTA

- `product-strategy-signal`
  - 對應：Beautiful.ai product launch / roadmap + SlideModel AI transformation roadmap + Gamma pitch / market sizing
  - 關鍵字：product strategy、pitch、transformation、positioning、成長訊號

- `sales-conversion`
  - 對應：Beautiful.ai sales proposal / battlecard / KAM + Gamma proposal flows + Slidesgo pricing
  - 關鍵字：proposal、pricing、battlecard、成交推進、ROI

- `operating-review`
  - 對應：Beautiful.ai sales pipeline review + Gamma QBR + EBR framework
  - 關鍵字：QBR、EBR、pipeline health、account review、營運節奏

- `customer-lifecycle`
  - 對應：Dock / EverAfter success plan + adoption lifecycle + renewal deck
  - 關鍵字：customer success、adoption、renewal、value realization、lifecycle

- `enablement-operations`
  - 對應：partner enablement deck + implementation plan + customer education patterns
  - 關鍵字：implementation、education、partner enablement、rollout、readiness

- `learning-community`
  - 對應：field enablement kickoff + certification program + community learning structures
  - 關鍵字：field readiness、certification、community learning、practice、progression

- `advocacy-network`
  - 對應：advocacy / ambassador / community outreach program structures
  - 關鍵字：advocacy、ambassador、community ops、outreach、trust

- `ecosystem-civic`
  - 對應：ecosystem mapping + ambassador measurement + volunteer operations patterns
  - 關鍵字：ecosystem、stakeholder network、ops coverage、community metrics

- `mission-governance`
  - 對應：nonprofit governance + donor lifecycle + mission-driven oversight structures
  - 關鍵字：membership、donor stewardship、governance、committee、trust

- `boardroom-premium`
  - 對應：Beautiful.ai investor update / investor presentation + Gamma investment committee / board roadmap
  - 關鍵字：board brief、investor update、premium neutral、decision clarity、confidence

- `community-fundraising`
  - 對應：Slidesgo AGM / HOA annual meeting + charity event / nonprofit marketing + Gamma nonprofit funding proposal
  - 關鍵字：association、annual meeting、fundraising、member trust、warm civic

## 使用原則

- theme 只定義共通視覺世界觀，不直接綁死頁面版型
- `2A` 與 `2B` 都寫在 theme 內
- theme 可以被多種 layout 重用
- 若外部模板只是配色不同、結構相近，優先收斂成同一個 reusable theme，而不是一模板一檔案
