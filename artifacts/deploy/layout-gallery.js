window.LAYOUT_GALLERY = {
  "count": 74,
  "categories": [
    "內容分區",
    "圖文 / 人物",
    "圖表類型",
    "封面",
    "引言 / 焦點句",
    "目錄",
    "章節頁",
    "結尾 / CTA"
  ],
  "gallery_categories": [
    "封面",
    "目錄",
    "內容",
    "圖表",
    "資訊圖像",
    "特定版面"
  ],
  "slide_roles": [
    "封面",
    "目錄",
    "章節頁",
    "內容頁",
    "結尾頁"
  ],
  "title_relations": [
    "上標｜下內容",
    "左標｜右內容",
    "右標｜左內容",
    "標題置中",
    "標題疊合"
  ],
  "content_flows": [
    "單一主體",
    "左右分區",
    "橫向排列",
    "直向排列",
    "網格排列",
    "流程路徑",
    "階層／環形"
  ],
  "layouts": [
    {
      "id": "before-after",
      "title": "比較 前後對比",
      "category": "圖表類型",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "比較 / 決策",
      "structure": "2-way split",
      "position_family": "左右對分",
      "title_relation": "上標｜下內容",
      "content_flow": "左右分區",
      "composition": "左 before｜右 after",
      "variant": "前後對比圖",
      "chart_family": "比較 / 決策",
      "chart_type": "前後對比圖",
      "summary": "前後對比圖；構圖採「左 before｜右 after」，不再視為一般 1 + N 卡片。",
      "slot_count": 4,
      "preview": "layout-previews/before-after.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/before-after-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/before-after-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/before-after-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/before-after.yaml"
    },
    {
      "id": "cards-1-plus-2",
      "title": "卡片組 1+2",
      "category": "內容分區",
      "gallery_category": "內容",
      "slide_role": "內容頁",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 2",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "橫向排列",
      "composition": "上 1｜下 2 橫排",
      "variant": "左右雙模組",
      "chart_family": null,
      "chart_type": null,
      "summary": "1 + 2 的「上 1｜下 2 橫排」變體；相同 N 值仍可延伸成上下、左右或不同網格。",
      "slot_count": 4,
      "preview": "layout-previews/cards-1-plus-2.svg",
      "codex_preview": "layout-previews/cards-1-plus-2-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/cards-1-plus-2-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/cards-1-plus-2-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/cards-1-plus-2-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/cards-1-plus-2.startup-gradient.png",
      "style_case_title": "1+2 雙模組：新創漸層策略",
      "yaml_path": "prompt_system/layouts/cards-1-plus-2.yaml"
    },
    {
      "id": "cards-1-plus-3",
      "title": "卡片組 1+3",
      "category": "內容分區",
      "gallery_category": "內容",
      "slide_role": "內容頁",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 3",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "橫向排列",
      "composition": "上 1｜下 3 橫排",
      "variant": "左中右三模組",
      "chart_family": null,
      "chart_type": null,
      "summary": "1 + 3 的「上 1｜下 3 橫排」變體；相同 N 值仍可延伸成上下、左右或不同網格。",
      "slot_count": 5,
      "preview": "layout-previews/cards-1-plus-3.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/cards-1-plus-3-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/cards-1-plus-3-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/cards-1-plus-3-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/cards-1-plus-3.sustainability-earth.png",
      "style_case_title": "1+3 三模組：永續實作地圖",
      "yaml_path": "prompt_system/layouts/cards-1-plus-3.yaml"
    },
    {
      "id": "cards-1-plus-4",
      "title": "卡片組 1+4",
      "category": "內容分區",
      "gallery_category": "內容",
      "slide_role": "內容頁",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 4",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上 1｜下 2×2",
      "variant": "2x2 模組網格",
      "chart_family": null,
      "chart_type": null,
      "summary": "1 + 4 的「上 1｜下 2×2」變體；相同 N 值仍可延伸成上下、左右或不同網格。",
      "slot_count": 6,
      "preview": "layout-previews/cards-1-plus-4.svg",
      "codex_preview": "layout-previews/cards-1-plus-4-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/cards-1-plus-4-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/cards-1-plus-4-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/cards-1-plus-4-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/cards-1-plus-4.brutalist-orange.png",
      "style_case_title": "1+4 四模組：粗獷決策板",
      "yaml_path": "prompt_system/layouts/cards-1-plus-4.yaml"
    },
    {
      "id": "cards-1-plus-5",
      "title": "卡片組 1+5",
      "category": "內容分區",
      "gallery_category": "內容",
      "slide_role": "內容頁",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 5",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上 1｜下 3+2",
      "variant": "3 上 2 下",
      "chart_family": null,
      "chart_type": null,
      "summary": "1 + 5 的「上 1｜下 3+2」變體；相同 N 值仍可延伸成上下、左右或不同網格。",
      "slot_count": 7,
      "preview": "layout-previews/cards-1-plus-5.svg",
      "codex_preview": "layout-previews/cards-1-plus-5-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/cards-1-plus-5-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/cards-1-plus-5-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/cards-1-plus-5-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/cards-1-plus-5.playful-education.png",
      "style_case_title": "1+5 五模組：教學遊戲化",
      "yaml_path": "prompt_system/layouts/cards-1-plus-5.yaml"
    },
    {
      "id": "cards-1-plus-6",
      "title": "卡片組 1+6",
      "category": "內容分區",
      "gallery_category": "內容",
      "slide_role": "內容頁",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 6",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上 1｜下 3×2",
      "variant": "3x2 模組網格",
      "chart_family": null,
      "chart_type": null,
      "summary": "1 + 6 的「上 1｜下 3×2」變體；相同 N 值仍可延伸成上下、左右或不同網格。",
      "slot_count": 8,
      "preview": "layout-previews/cards-1-plus-6.svg",
      "codex_preview": "layout-previews/cards-1-plus-6-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/cards-1-plus-6-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/cards-1-plus-6-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/cards-1-plus-6-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/cards-1-plus-6.neutral-luxury.png",
      "style_case_title": "1+6 六模組：作品集總覽",
      "yaml_path": "prompt_system/layouts/cards-1-plus-6.yaml"
    },
    {
      "id": "cards-1-plus-8",
      "title": "卡片組 1+8",
      "category": "內容分區",
      "gallery_category": "內容",
      "slide_role": "內容頁",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 8",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上 1｜下 4×2",
      "variant": "4×2 模組網格",
      "chart_family": null,
      "chart_type": null,
      "summary": "1 + 8 的「上 1｜下 4×2」變體；相同 N 值仍可延伸成上下、左右或不同網格。",
      "slot_count": 10,
      "preview": "layout-previews/cards-1-plus-8.svg",
      "codex_preview": "layout-previews/cards-1-plus-8-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/cards-1-plus-8-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/cards-1-plus-8-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/cards-1-plus-8-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/cards-1-plus-8.mission-control.png",
      "style_case_title": "1+8 八模組：營運指揮台",
      "yaml_path": "prompt_system/layouts/cards-1-plus-8.yaml"
    },
    {
      "id": "chapter-fullbleed-overlay-title",
      "title": "章節 滿版照片 遮罩標題",
      "category": "章節頁",
      "gallery_category": "特定版面",
      "slide_role": "章節頁",
      "subgroup": "滿版內容｜標題疊合",
      "structure": "1 + 1",
      "position_family": "滿版內容｜標題疊合",
      "title_relation": "標題疊合",
      "content_flow": "單一主體",
      "composition": "滿版照片｜左上標題＋右側章節號",
      "variant": "滿版照片 + 遮罩標題 + 數字欄",
      "chart_family": null,
      "chart_type": null,
      "summary": "用來切段、換氣與建立節奏。",
      "slot_count": 2,
      "preview": "layout-previews/chapter-fullbleed-overlay-title.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/chapter-fullbleed-overlay-title-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/chapter-fullbleed-overlay-title-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/chapter-fullbleed-overlay-title-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/chapter-fullbleed-overlay-title.yaml"
    },
    {
      "id": "chapter-number-bg-left-title-rule",
      "title": "章節 數字背景 左標",
      "category": "章節頁",
      "gallery_category": "特定版面",
      "slide_role": "章節頁",
      "subgroup": "左內容｜右視覺",
      "structure": "1 + 1",
      "position_family": "左內容｜右視覺",
      "title_relation": "左標｜右內容",
      "content_flow": "左右分區",
      "composition": "左主標｜右側大型章節號",
      "variant": "背景章節數字 + 左側大標",
      "chart_family": null,
      "chart_type": null,
      "summary": "用來切段、換氣與建立節奏。",
      "slot_count": 6,
      "preview": "layout-previews/chapter-number-bg-left-title-rule.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/chapter-number-bg-left-title-rule-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/chapter-number-bg-left-title-rule-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/chapter-number-bg-left-title-rule-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/chapter-number-bg-left-title-rule.editorial-classic.png",
      "style_case_title": "章節數字背景左標：紙本編輯風",
      "yaml_path": "prompt_system/layouts/chapter-number-bg-left-title-rule.yaml"
    },
    {
      "id": "chapter-opener",
      "title": "章節 純文字過場",
      "category": "章節頁",
      "gallery_category": "特定版面",
      "slide_role": "章節頁",
      "subgroup": "置中焦點",
      "structure": "1 + 1",
      "position_family": "置中焦點",
      "title_relation": "標題置中",
      "content_flow": "單一主體",
      "composition": "中央章節標記｜置中主標",
      "variant": "章節標記 + 大標題",
      "chart_family": null,
      "chart_type": null,
      "summary": "用來切段、換氣與建立節奏。",
      "slot_count": 4,
      "preview": "layout-previews/chapter-opener.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/chapter-opener-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/chapter-opener-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/chapter-opener-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/chapter-opener.cinematic-crimson.png",
      "style_case_title": "章節過場：深紅電影感",
      "yaml_path": "prompt_system/layouts/chapter-opener.yaml"
    },
    {
      "id": "chapter-text-left-photo-brand",
      "title": "章節 左文右圖 品牌遮罩",
      "category": "章節頁",
      "gallery_category": "特定版面",
      "slide_role": "章節頁",
      "subgroup": "左內容｜右視覺",
      "structure": "1 + 1",
      "position_family": "左內容｜右視覺",
      "title_relation": "左標｜右內容",
      "content_flow": "左右分區",
      "composition": "左標題與內文｜右滿版照片",
      "variant": "文字左 + 照片右 + 品牌遮罩",
      "chart_family": null,
      "chart_type": null,
      "summary": "用來切段、換氣與建立節奏。",
      "slot_count": 4,
      "preview": "layout-previews/chapter-text-left-photo-brand.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/chapter-text-left-photo-brand-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/chapter-text-left-photo-brand-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/chapter-text-left-photo-brand-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/chapter-text-left-photo-brand.yaml"
    },
    {
      "id": "closing-photo-overlay-contact",
      "title": "結尾 滿版照片 聯絡資訊",
      "category": "結尾 / CTA",
      "gallery_category": "特定版面",
      "slide_role": "結尾頁",
      "subgroup": "滿版內容｜標題疊合",
      "structure": "1 + 1",
      "position_family": "滿版內容｜標題疊合",
      "title_relation": "標題疊合",
      "content_flow": "單一主體",
      "composition": "滿版照片｜左側結尾與聯絡資訊",
      "variant": "滿版照片 + 聯絡遮罩",
      "chart_family": null,
      "chart_type": null,
      "summary": "用結尾主張與聯絡資訊收束內容，保持單一明確行動。",
      "slot_count": 3,
      "preview": "layout-previews/closing-photo-overlay-contact.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/closing-photo-overlay-contact-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/closing-photo-overlay-contact-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/closing-photo-overlay-contact-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/closing-photo-overlay-contact.yaml"
    },
    {
      "id": "comparison-table",
      "title": "比較 表格式",
      "category": "圖表類型",
      "gallery_category": "圖表",
      "slide_role": "內容頁",
      "subgroup": "比較 / 決策",
      "structure": "1 + 1",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上標題｜下比較表",
      "variant": "表格式比較",
      "chart_family": "比較 / 決策",
      "chart_type": "比較表",
      "summary": "比較表；構圖採「上標題｜下比較表」，不再視為一般 1 + N 卡片。",
      "slot_count": 4,
      "preview": "layout-previews/comparison-table.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/comparison-table-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/comparison-table-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/comparison-table-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/comparison-table.mint-lab.png",
      "style_case_title": "比較表格：實驗室薄荷",
      "yaml_path": "prompt_system/layouts/comparison-table.yaml"
    },
    {
      "id": "cover-center-title-double-frame",
      "title": "封面 純 Pattern 中央標題雙線外框",
      "category": "封面",
      "gallery_category": "封面",
      "slide_role": "封面",
      "subgroup": "置中焦點｜雙線外框",
      "structure": "1 + 1",
      "position_family": "置中焦點｜雙線外框",
      "title_relation": "標題置中",
      "content_flow": "單一主體",
      "composition": "置中主標｜雙線外框",
      "variant": "雙線外框 + 置中主標",
      "chart_family": null,
      "chart_type": null,
      "summary": "用來建立第一眼主題與氣氛，但主標仍應是主角。",
      "slot_count": 4,
      "preview": "layout-previews/cover-center-title-double-frame.svg",
      "codex_preview": "layout-previews/cover-center-title-double-frame-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/cover-center-title-double-frame-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/cover-center-title-double-frame-legacy-20260829-b.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/cover-center-title-double-frame-legacy-20260829-a.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/cover-center-title-double-frame.yaml"
    },
    {
      "id": "cover-center-title-edge-decor",
      "title": "封面 素色 中心標題",
      "category": "封面",
      "gallery_category": "封面",
      "slide_role": "封面",
      "subgroup": "置中焦點",
      "structure": "1 + 1",
      "position_family": "置中焦點",
      "title_relation": "標題置中",
      "content_flow": "單一主體",
      "composition": "置中主標｜下副標與署名",
      "variant": "素色背景 + 置中標題",
      "chart_family": null,
      "chart_type": null,
      "summary": "用來建立第一眼主題與氣氛，但主標仍應是主角。",
      "slot_count": 5,
      "preview": "layout-previews/cover-center-title-edge-decor.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/cover-center-title-edge-decor-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/cover-center-title-edge-decor-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/cover-center-title-edge-decor-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/cover-center-title-edge-decor.yaml"
    },
    {
      "id": "cover-left-title-open-field",
      "title": "封面 左軸主標開放留白",
      "category": "封面",
      "gallery_category": "封面",
      "slide_role": "封面",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 1",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "單一主體",
      "composition": "上 1｜下 N（通用變體）",
      "variant": "通用變體",
      "chart_family": null,
      "chart_type": null,
      "summary": "用來建立第一眼主題與氣氛，但主標仍應是主角。",
      "slot_count": 3,
      "preview": "layout-previews/cover-left-title-open-field.svg",
      "codex_preview": "layout-previews/cover-left-title-open-field-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/cover-left-title-open-field-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/cover-left-title-open-field-legacy-20260822-terracotta.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/cover-left-title-open-field-legacy-20260822-dark-ai-city.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/cover-left-title-open-field.yaml"
    },
    {
      "id": "cover-photo-frame-reverse",
      "title": "封面 半版 左文右圖",
      "category": "封面",
      "gallery_category": "封面",
      "slide_role": "封面",
      "subgroup": "左內容｜右視覺",
      "structure": "1 + 1",
      "position_family": "左內容｜右視覺",
      "title_relation": "左標｜右內容",
      "content_flow": "左右分區",
      "composition": "左主標與署名｜右照片",
      "variant": "左文右圖",
      "chart_family": null,
      "chart_type": null,
      "summary": "用來建立第一眼主題與氣氛，但主標仍應是主角。",
      "slot_count": 6,
      "preview": "layout-previews/cover-photo-frame-reverse.svg",
      "codex_preview": "layout-previews/cover-photo-frame-reverse-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/cover-photo-frame-reverse-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/cover-photo-frame-reverse-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/cover-photo-frame-reverse-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/cover-photo-frame-reverse.ai-workflow-cover.png",
      "style_case_title": "半版封面(文字左側)：AI 工作流右圖封面",
      "yaml_path": "prompt_system/layouts/cover-photo-frame-reverse.yaml"
    },
    {
      "id": "cover-photo-frame",
      "title": "封面 半版 左圖右文",
      "category": "封面",
      "gallery_category": "封面",
      "slide_role": "封面",
      "subgroup": "左視覺｜右內容",
      "structure": "1 + 1",
      "position_family": "左視覺｜右內容",
      "title_relation": "右標｜左內容",
      "content_flow": "左右分區",
      "composition": "左照片｜右主標與署名",
      "variant": "左圖右文",
      "chart_family": null,
      "chart_type": null,
      "summary": "用來建立第一眼主題與氣氛，但主標仍應是主角。",
      "slot_count": 6,
      "preview": "layout-previews/cover-photo-frame.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/cover-photo-frame-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/cover-photo-frame-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/cover-photo-frame-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/cover-photo-frame.sepia-retail-case.jpg",
      "style_case_title": "半版封面(文字右側)：便利店結帳案例",
      "yaml_path": "prompt_system/layouts/cover-photo-frame.yaml"
    },
    {
      "id": "cover-photo-overlay-block",
      "title": "封面 滿版照片 文字色塊",
      "category": "封面",
      "gallery_category": "封面",
      "slide_role": "封面",
      "subgroup": "滿版內容｜標題疊合",
      "structure": "1 + 1",
      "position_family": "滿版內容｜標題疊合",
      "title_relation": "標題疊合",
      "content_flow": "單一主體",
      "composition": "滿版照片｜左側色塊標題",
      "variant": "全幅照片 + 半透明色塊標題",
      "chart_family": null,
      "chart_type": null,
      "summary": "用來建立第一眼主題與氣氛，但主標仍應是主角。",
      "slot_count": 2,
      "preview": "layout-previews/cover-photo-overlay-block.svg",
      "codex_preview": "layout-previews/cover-photo-overlay-block-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/cover-photo-overlay-block-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/cover-photo-overlay-block-legacy-20260706-fill3-04-approved.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/cover-photo-overlay-block-legacy-20260706-fill3-03-approved.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/cover-photo-overlay-block.yaml"
    },
    {
      "id": "cover-upper-center-stack-meta-lower-right",
      "title": "封面 上方置中堆疊・右下資訊",
      "category": "封面",
      "gallery_category": "封面",
      "slide_role": "封面",
      "subgroup": "上方置中｜右下資訊",
      "structure": "1 + 2",
      "position_family": "上方置中｜右下資訊",
      "title_relation": "標題置中",
      "content_flow": "左右分區",
      "composition": "上方主副標｜左下焦點＋右下資訊",
      "variant": "上方置中堆疊 + 大留白",
      "chart_family": null,
      "chart_type": null,
      "summary": "用來建立第一眼主題與氣氛，但主標仍應是主角。",
      "slot_count": 3,
      "preview": "layout-previews/cover-upper-center-stack-meta-lower-right.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/cover-upper-center-stack-meta-lower-right-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/cover-upper-center-stack-meta-lower-right-variant-v3-b.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/cover-upper-center-stack-meta-lower-right-legacy-v2.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/cover-upper-center-stack-meta-lower-right.yaml"
    },
    {
      "id": "cycle-hub-6",
      "title": "圖表 環形輻射 1+6",
      "category": "圖表類型",
      "gallery_category": "資訊圖像",
      "slide_role": "內容頁",
      "subgroup": "結構 / 關係",
      "structure": "1 + 6",
      "position_family": "中央主題｜兩側內容",
      "title_relation": "上標｜下內容",
      "content_flow": "階層／環形",
      "composition": "中央 1｜左右各 3",
      "variant": "環形輪幅 + 中心主題",
      "chart_family": "結構 / 關係",
      "chart_type": "環形關係圖",
      "summary": "環形關係圖；構圖採「中央 1｜左右各 3」，不再視為一般 1 + N 卡片。",
      "slot_count": 7,
      "preview": "layout-previews/cycle-hub-6.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/cycle-hub-6-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/cycle-hub-6-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/cycle-hub-6-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/cycle-hub-6.yaml"
    },
    {
      "id": "dashboard-overview",
      "title": "數據 儀表板總覽",
      "category": "圖表類型",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "數據圖表",
      "structure": "1 + 3",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上標題｜下 KPI、主圖與洞察",
      "variant": "總覽儀表板",
      "chart_family": "數據圖表",
      "chart_type": "儀表板",
      "summary": "儀表板；構圖採「上標題｜下 KPI、主圖與洞察」，不再視為一般 1 + N 卡片。",
      "slot_count": 6,
      "preview": "layout-previews/dashboard-overview.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/dashboard-overview-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/dashboard-overview-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/dashboard-overview-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/dashboard-overview.executive-emerald.png",
      "style_case_title": "Dashboard：高階綠金分析",
      "yaml_path": "prompt_system/layouts/dashboard-overview.yaml"
    },
    {
      "id": "data-annotation",
      "title": "圖表 折線 + 事件標注",
      "category": "圖表類型",
      "gallery_category": "圖表",
      "slide_role": "內容頁",
      "subgroup": "數據圖表",
      "structure": "1 + 1",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "單一主體",
      "composition": "上標題｜下趨勢圖＋事件標注",
      "variant": "事件標注趨勢圖",
      "chart_family": "數據圖表",
      "chart_type": "事件標注趨勢圖",
      "summary": "事件標注趨勢圖；構圖採「上標題｜下趨勢圖＋事件標注」，不再視為一般 1 + N 卡片。",
      "slot_count": 5,
      "preview": "layout-previews/data-annotation.svg",
      "codex_preview": "layout-previews/data-annotation-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/data-annotation-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/data-annotation-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/data-annotation-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/data-annotation.yaml"
    },
    {
      "id": "executive-bio",
      "title": "人物 高層完整介紹",
      "category": "圖文 / 人物",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "左視覺｜右內容",
      "structure": "1 + N",
      "position_family": "左視覺｜右內容",
      "title_relation": "右標｜左內容",
      "content_flow": "左右分區",
      "composition": "左照片｜右姓名、職稱與簡介",
      "variant": "圖文人物混排",
      "chart_family": null,
      "chart_type": null,
      "summary": "用「左照片｜右姓名、職稱與簡介」安排人物、照片與文字，讓主次關係一眼可讀。",
      "slot_count": 5,
      "preview": "layout-previews/executive-bio.svg",
      "codex_preview": "layout-previews/executive-bio-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/executive-bio-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/executive-bio-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/executive-bio-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/executive-bio.yaml"
    },
    {
      "id": "flow-stages-3",
      "title": "流程 三階段",
      "category": "圖表類型",
      "gallery_category": "資訊圖像",
      "slide_role": "內容頁",
      "subgroup": "流程 / 時間",
      "structure": "1 + 3",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "流程路徑",
      "composition": "上 1｜下 3 階段",
      "variant": "內容型階段卡",
      "chart_family": "流程 / 時間",
      "chart_type": "階段流程圖",
      "summary": "階段流程圖；構圖採「上 1｜下 3 階段」，不再視為一般 1 + N 卡片。",
      "slot_count": 6,
      "preview": "layout-previews/flow-stages-3.svg",
      "codex_preview": "layout-previews/flow-stages-3-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/flow-stages-3-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/flow-stages-3-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/flow-stages-3-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/flow-stages-3.industrial-yellow.png",
      "style_case_title": "三階段流程：工業黃黑",
      "yaml_path": "prompt_system/layouts/flow-stages-3.yaml"
    },
    {
      "id": "funnel-4",
      "title": "圖表 四層漏斗",
      "category": "圖表類型",
      "gallery_category": "資訊圖像",
      "slide_role": "內容頁",
      "subgroup": "流程 / 時間",
      "structure": "1 + 4",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "流程路徑",
      "composition": "上 1｜下 4 層漏斗",
      "variant": "漏斗圖",
      "chart_family": "流程 / 時間",
      "chart_type": "漏斗圖",
      "summary": "漏斗圖；構圖採「上 1｜下 4 層漏斗」，不再視為一般 1 + N 卡片。",
      "slot_count": 5,
      "preview": "layout-previews/funnel-4.svg",
      "codex_preview": "layout-previews/funnel-4-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/funnel-4-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/funnel-4-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/funnel-4-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/funnel-4.yaml"
    },
    {
      "id": "gantt-roadmap",
      "title": "時間軸 甘特路線",
      "category": "圖表類型",
      "gallery_category": "資訊圖像",
      "slide_role": "內容頁",
      "subgroup": "流程 / 時間",
      "structure": "1 + sequence",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "流程路徑",
      "composition": "上標題｜下任務欄＋時間帶",
      "variant": "甘特時間帶",
      "chart_family": "流程 / 時間",
      "chart_type": "甘特圖",
      "summary": "甘特圖；構圖採「上標題｜下任務欄＋時間帶」，不再視為一般 1 + N 卡片。",
      "slot_count": 6,
      "preview": "layout-previews/gantt-roadmap.svg",
      "codex_preview": "layout-previews/gantt-roadmap-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/gantt-roadmap-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/gantt-roadmap-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/gantt-roadmap-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/gantt-roadmap.cobalt-product-launch.png",
      "style_case_title": "時程路線圖：鈷藍產品發佈",
      "yaml_path": "prompt_system/layouts/gantt-roadmap.yaml"
    },
    {
      "id": "heat-map",
      "title": "圖表 熱力矩陣",
      "category": "圖表類型",
      "gallery_category": "圖表",
      "slide_role": "內容頁",
      "subgroup": "數據圖表",
      "structure": "1 + 1",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上標題｜下熱力矩陣",
      "variant": "熱力矩陣",
      "chart_family": "數據圖表",
      "chart_type": "熱力矩陣",
      "summary": "熱力矩陣；構圖採「上標題｜下熱力矩陣」，不再視為一般 1 + N 卡片。",
      "slot_count": 4,
      "preview": "layout-previews/heat-map.svg",
      "codex_preview": "layout-previews/heat-map-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/heat-map-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/heat-map-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/heat-map-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/heat-map.yaml"
    },
    {
      "id": "hero-fullbleed-brand-footer",
      "title": "主視覺 滿版照片 品牌底欄",
      "category": "封面",
      "gallery_category": "封面",
      "slide_role": "封面",
      "subgroup": "滿版內容｜標題疊合",
      "structure": "1 + 1",
      "position_family": "滿版內容｜標題疊合",
      "title_relation": "標題疊合",
      "content_flow": "單一主體",
      "composition": "滿版照片｜左側主標＋品牌底欄",
      "variant": "滿版背景 + 左側文字欄",
      "chart_family": null,
      "chart_type": null,
      "summary": "用來建立第一眼主題與氣氛，但主標仍應是主角。",
      "slot_count": 5,
      "preview": "layout-previews/hero-fullbleed-brand-footer.svg",
      "codex_preview": "layout-previews/hero-fullbleed-brand-footer-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/hero-fullbleed-brand-footer-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/hero-fullbleed-brand-footer-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/hero-fullbleed-brand-footer-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/hero-fullbleed-brand-footer.dark-ai-city.png",
      "style_case_title": "滿版封面(文字左側)：AI 城市夜景",
      "yaml_path": "prompt_system/layouts/hero-fullbleed-brand-footer.yaml"
    },
    {
      "id": "hero-fullbleed",
      "title": "主視覺 滿版照片 標題左下",
      "category": "封面",
      "gallery_category": "封面",
      "slide_role": "封面",
      "subgroup": "滿版內容｜標題疊合",
      "structure": "1 + 1",
      "position_family": "滿版內容｜標題疊合",
      "title_relation": "標題疊合",
      "content_flow": "單一主體",
      "composition": "滿版照片｜左下主標",
      "variant": "滿版背景 + 左下文字",
      "chart_family": null,
      "chart_type": null,
      "summary": "用來建立第一眼主題與氣氛，但主標仍應是主角。",
      "slot_count": 5,
      "preview": "layout-previews/hero-fullbleed.svg",
      "codex_preview": "layout-previews/hero-fullbleed-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/hero-fullbleed-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/hero-fullbleed-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/hero-fullbleed-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/hero-fullbleed.dark-city-network-report.png",
      "style_case_title": "滿版封面(文字左下)：暗色城市網路報告",
      "yaml_path": "prompt_system/layouts/hero-fullbleed.yaml"
    },
    {
      "id": "highlight-callout",
      "title": "圖表 側欄重點",
      "category": "圖表類型",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "數據圖表",
      "structure": "1 + 4",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "左右分區",
      "composition": "上標題｜左主圖＋右 3 重點",
      "variant": "主圖標注",
      "chart_family": "數據圖表",
      "chart_type": "主圖標注",
      "summary": "主圖標注；構圖採「上標題｜左主圖＋右 3 重點」，不再視為一般 1 + N 卡片。",
      "slot_count": 5,
      "preview": "layout-previews/highlight-callout.svg",
      "codex_preview": "layout-previews/highlight-callout-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/highlight-callout-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/highlight-callout-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/highlight-callout-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/highlight-callout.yaml"
    },
    {
      "id": "icon-grid-6",
      "title": "圖示 六格",
      "category": "內容分區",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 6",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上 1｜下 3×2",
      "variant": "內容模組",
      "chart_family": null,
      "chart_type": null,
      "summary": "1 + 6 的「上 1｜下 3×2」變體；相同 N 值仍可延伸成上下、左右或不同網格。",
      "slot_count": 7,
      "preview": "layout-previews/icon-grid-6.svg",
      "codex_preview": "layout-previews/icon-grid-6-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/icon-grid-6-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/icon-grid-6-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/icon-grid-6-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/icon-grid-6.yaml"
    },
    {
      "id": "kpi-scorecards",
      "title": "數據 KPI 計分卡",
      "category": "圖表類型",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "數據圖表",
      "structure": "1 + 4",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上標題｜下 4 指標",
      "variant": "指標卡片",
      "chart_family": "數據圖表",
      "chart_type": "KPI 計分卡",
      "summary": "KPI 計分卡；構圖採「上標題｜下 4 指標」，不再視為一般 1 + N 卡片。",
      "slot_count": 3,
      "preview": "layout-previews/kpi-scorecards.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/kpi-scorecards-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/kpi-scorecards-legacy-20260706.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/kpi-scorecards-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/kpi-scorecards.fintech-neon.png",
      "style_case_title": "KPI 指標卡：金融科技夜色",
      "yaml_path": "prompt_system/layouts/kpi-scorecards.yaml"
    },
    {
      "id": "map-region",
      "title": "地圖 區域著色",
      "category": "圖表類型",
      "gallery_category": "資訊圖像",
      "slide_role": "內容頁",
      "subgroup": "地圖",
      "structure": "1 + 4",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "左右分區",
      "composition": "上標題｜左地圖＋右 3 數據",
      "variant": "區域著色地圖",
      "chart_family": "地圖",
      "chart_type": "區域著色地圖",
      "summary": "區域著色地圖；構圖採「上標題｜左地圖＋右 3 數據」，不再視為一般 1 + N 卡片。",
      "slot_count": 5,
      "preview": "layout-previews/map-region.svg",
      "codex_preview": "layout-previews/map-region-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/map-region-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/map-region-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/map-region-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/map-region.yaml"
    },
    {
      "id": "map-spotlight",
      "title": "地圖 城市標注",
      "category": "圖表類型",
      "gallery_category": "資訊圖像",
      "slide_role": "內容頁",
      "subgroup": "地圖",
      "structure": "1 + 4",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "左右分區",
      "composition": "上標題｜左地圖＋右 3 據點",
      "variant": "據點標注地圖",
      "chart_family": "地圖",
      "chart_type": "據點標注地圖",
      "summary": "據點標注地圖；構圖採「上標題｜左地圖＋右 3 據點」，不再視為一般 1 + N 卡片。",
      "slot_count": 5,
      "preview": "layout-previews/map-spotlight.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/map-spotlight-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/map-spotlight-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/map-spotlight-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/map-spotlight.yaml"
    },
    {
      "id": "matrix-4quadrant",
      "title": "矩陣 四象限",
      "category": "圖表類型",
      "gallery_category": "資訊圖像",
      "slide_role": "內容頁",
      "subgroup": "比較 / 決策",
      "structure": "1 + 4",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上標題｜下 2×2 象限",
      "variant": "四象限定位",
      "chart_family": "比較 / 決策",
      "chart_type": "四象限矩陣",
      "summary": "四象限矩陣；構圖採「上標題｜下 2×2 象限」，不再視為一般 1 + N 卡片。",
      "slot_count": 10,
      "preview": "layout-previews/matrix-4quadrant.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/matrix-4quadrant-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/matrix-4quadrant-legacy-20260706-fill3-04.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/matrix-4quadrant-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/matrix-4quadrant.sticky-note-workshop.png",
      "style_case_title": "四象限矩陣：便條工作坊",
      "yaml_path": "prompt_system/layouts/matrix-4quadrant.yaml"
    },
    {
      "id": "multi-line-chart",
      "title": "圖表 多線折線",
      "category": "圖表類型",
      "gallery_category": "圖表",
      "slide_role": "內容頁",
      "subgroup": "數據圖表",
      "structure": "1 + 1",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "單一主體",
      "composition": "上標題｜下多線趨勢圖",
      "variant": "多線折線圖",
      "chart_family": "數據圖表",
      "chart_type": "多線折線圖",
      "summary": "多線折線圖；構圖採「上標題｜下多線趨勢圖」，不再視為一般 1 + N 卡片。",
      "slot_count": 5,
      "preview": "layout-previews/multi-line-chart.svg",
      "codex_preview": "layout-previews/multi-line-chart-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/multi-line-chart-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/multi-line-chart-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/multi-line-chart-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/multi-line-chart.yaml"
    },
    {
      "id": "org-chart",
      "title": "組織架構圖 三層",
      "category": "圖表類型",
      "gallery_category": "資訊圖像",
      "slide_role": "內容頁",
      "subgroup": "結構 / 關係",
      "structure": "1 + hierarchy",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "階層／環形",
      "composition": "上標題｜下 1→3 階層",
      "variant": "組織架構圖",
      "chart_family": "結構 / 關係",
      "chart_type": "組織架構圖",
      "summary": "組織架構圖；構圖採「上標題｜下 1→3 階層」，不再視為一般 1 + N 卡片。",
      "slot_count": 6,
      "preview": "layout-previews/org-chart.svg",
      "codex_preview": "layout-previews/org-chart-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/org-chart-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/org-chart-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/org-chart-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/org-chart.yaml"
    },
    {
      "id": "people-3",
      "title": "人物 三人並列",
      "category": "圖文 / 人物",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 3",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "橫向排列",
      "composition": "上 1｜下 3 人並列",
      "variant": "圖文人物混排",
      "chart_family": null,
      "chart_type": null,
      "summary": "用「上 1｜下 3 人並列」安排人物、照片與文字，讓主次關係一眼可讀。",
      "slot_count": 4,
      "preview": "layout-previews/people-3.svg",
      "codex_preview": "layout-previews/people-3-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/people-3-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/people-3-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/people-3-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/people-3.yaml"
    },
    {
      "id": "photo-left-overlay-title-right",
      "title": "圖文 左圖右標題",
      "category": "圖文 / 人物",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "左視覺｜右內容",
      "structure": "1 + 1",
      "position_family": "左視覺｜右內容",
      "title_relation": "右標｜左內容",
      "content_flow": "左右分區",
      "composition": "左照片｜右疊合標題與內文",
      "variant": "裱框照片左 + 遮罩標題右",
      "chart_family": null,
      "chart_type": null,
      "summary": "用「左照片｜右疊合標題與內文」安排人物、照片與文字，讓主次關係一眼可讀。",
      "slot_count": 3,
      "preview": "layout-previews/photo-left-overlay-title-right.svg",
      "codex_preview": "layout-previews/photo-left-overlay-title-right-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/photo-left-overlay-title-right-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/photo-left-overlay-title-right-legacy-20260706-fill3-04.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/photo-left-overlay-title-right-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/photo-left-overlay-title-right.yaml"
    },
    {
      "id": "pricing-3col",
      "title": "定價 三欄方案",
      "category": "圖表類型",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "比較 / 決策",
      "structure": "1 + 3",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "橫向排列",
      "composition": "上標題｜下 3 方案",
      "variant": "方案比較",
      "chart_family": "比較 / 決策",
      "chart_type": "方案比較",
      "summary": "方案比較；構圖採「上標題｜下 3 方案」，不再視為一般 1 + N 卡片。",
      "slot_count": 4,
      "preview": "layout-previews/pricing-3col.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/pricing-3col-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/pricing-3col-variant-codex-20260722.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/pricing-3col-legacy-20260706.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/pricing-3col.yaml"
    },
    {
      "id": "process-flow",
      "title": "流程 步驟橫向",
      "category": "圖表類型",
      "gallery_category": "資訊圖像",
      "slide_role": "內容頁",
      "subgroup": "流程 / 時間",
      "structure": "1 + sequence",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "流程路徑",
      "composition": "上標題｜下橫向步驟",
      "variant": "線性步驟",
      "chart_family": "流程 / 時間",
      "chart_type": "線性流程圖",
      "summary": "線性流程圖；構圖採「上標題｜下橫向步驟」，不再視為一般 1 + N 卡片。",
      "slot_count": 4,
      "preview": "layout-previews/process-flow.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/process-flow-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/process-flow-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/process-flow-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/process-flow.notebook-handdrawn.png",
      "style_case_title": "流程步驟圖：筆記本手繪",
      "yaml_path": "prompt_system/layouts/process-flow.yaml"
    },
    {
      "id": "pyramid",
      "title": "圖表 金字塔",
      "category": "圖表類型",
      "gallery_category": "資訊圖像",
      "slide_role": "內容頁",
      "subgroup": "結構 / 關係",
      "structure": "1 + N",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "階層／環形",
      "composition": "上標題｜下 3–5 層金字塔",
      "variant": "3–5 層階梯金字塔",
      "chart_family": "結構 / 關係",
      "chart_type": "金字塔圖",
      "summary": "金字塔圖；構圖採「上標題｜下 3–5 層金字塔」，不再視為一般 1 + N 卡片。",
      "slot_count": "4–7",
      "preview": "layout-previews/pyramid.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/pyramid-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/pyramid-legacy-3-layer.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/pyramid-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/pyramid.yaml"
    },
    {
      "id": "quote-attribution-3",
      "title": "語錄 三則引言",
      "category": "引言 / 焦點句",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 3",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "橫向排列",
      "composition": "上 1｜下 3 則引言",
      "variant": "通用變體",
      "chart_family": null,
      "chart_type": null,
      "summary": "用整頁呈現單一句子的重量，讓觀眾停下來感受一個主張或金句。",
      "slot_count": 4,
      "preview": "layout-previews/quote-attribution-3.svg",
      "codex_preview": "layout-previews/quote-attribution-3-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/quote-attribution-3-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/quote-attribution-3-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/quote-attribution-3-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/quote-attribution-3.yaml"
    },
    {
      "id": "quote-focus",
      "title": "語錄 大字聚焦",
      "category": "引言 / 焦點句",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "置中焦點",
      "structure": "1 + 1",
      "position_family": "置中焦點",
      "title_relation": "標題置中",
      "content_flow": "單一主體",
      "composition": "置中引言｜下方署名",
      "variant": "大字句焦點",
      "chart_family": null,
      "chart_type": null,
      "summary": "用整頁呈現單一句子的重量，讓觀眾停下來感受一個主張或金句。",
      "slot_count": 3,
      "preview": "layout-previews/quote-focus.svg",
      "codex_preview": "layout-previews/quote-focus-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/quote-focus-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/quote-focus-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/quote-focus-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/quote-focus.poetic-ink.png",
      "style_case_title": "金句聚焦：墨色詩意",
      "yaml_path": "prompt_system/layouts/quote-focus.yaml"
    },
    {
      "id": "radar-chart",
      "title": "圖表 雷達",
      "category": "圖表類型",
      "gallery_category": "圖表",
      "slide_role": "內容頁",
      "subgroup": "數據圖表",
      "structure": "1 + 2",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "左右分區",
      "composition": "上標題｜左雷達圖＋右圖例",
      "variant": "雷達圖",
      "chart_family": "數據圖表",
      "chart_type": "雷達圖",
      "summary": "雷達圖；構圖採「上標題｜左雷達圖＋右圖例」，不再視為一般 1 + N 卡片。",
      "slot_count": 3,
      "preview": "layout-previews/radar-chart.svg",
      "codex_preview": "layout-previews/radar-chart-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/radar-chart-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/radar-chart-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/radar-chart-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/radar-chart.yaml"
    },
    {
      "id": "recommendation-stack",
      "title": "策略 建議堆疊",
      "category": "圖表類型",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "比較 / 決策",
      "structure": "comparison",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "直向排列",
      "composition": "上標題｜下建議堆疊",
      "variant": "建議優先序",
      "chart_family": "比較 / 決策",
      "chart_type": "建議優先序",
      "summary": "建議優先序；構圖採「上標題｜下建議堆疊」，不再視為一般 1 + N 卡片。",
      "slot_count": 4,
      "preview": "layout-previews/recommendation-stack.svg",
      "codex_preview": "layout-previews/recommendation-stack-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/recommendation-stack-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/recommendation-stack-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/recommendation-stack-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/recommendation-stack.consulting-burgundy.png",
      "style_case_title": "建議堆疊：顧問酒紅",
      "yaml_path": "prompt_system/layouts/recommendation-stack.yaml"
    },
    {
      "id": "split-comparison",
      "title": "比較 左右分割",
      "category": "圖表類型",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "比較 / 決策",
      "structure": "1 + 2",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "左右分區",
      "composition": "上標題｜下左右對分",
      "variant": "左右分屏",
      "chart_family": "比較 / 決策",
      "chart_type": "左右對比",
      "summary": "左右對比；構圖採「上標題｜下左右對分」，不再視為一般 1 + N 卡片。",
      "slot_count": 5,
      "preview": "layout-previews/split-comparison.svg",
      "codex_preview": "layout-previews/split-comparison-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/split-comparison-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/split-comparison-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/split-comparison-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/split-comparison.blue-terracotta.png",
      "style_case_title": "左右對比：藍陶雙面",
      "yaml_path": "prompt_system/layouts/split-comparison.yaml"
    },
    {
      "id": "stats-3-row",
      "title": "數據 三欄大數字",
      "category": "圖表類型",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "數據圖表",
      "structure": "1 + 3",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "橫向排列",
      "composition": "上說明｜下 3 指標",
      "variant": "大數字指標",
      "chart_family": "數據圖表",
      "chart_type": "大數字指標",
      "summary": "大數字指標；構圖採「上說明｜下 3 指標」，不再視為一般 1 + N 卡片。",
      "slot_count": 5,
      "preview": "layout-previews/stats-3-row.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/stats-3-row-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/stats-3-row-variant-codex-20260722.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/stats-3-row-legacy-20260706.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/stats-3-row.yaml"
    },
    {
      "id": "strategic-priorities",
      "title": "策略 優先順序",
      "category": "圖表類型",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "比較 / 決策",
      "structure": "comparison",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "直向排列",
      "composition": "上標題｜下策略優先序",
      "variant": "策略優先序",
      "chart_family": "比較 / 決策",
      "chart_type": "策略優先序",
      "summary": "策略優先序；構圖採「上標題｜下策略優先序」，不再視為一般 1 + N 卡片。",
      "slot_count": 4,
      "preview": "layout-previews/strategic-priorities.svg",
      "codex_preview": "layout-previews/strategic-priorities-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/strategic-priorities-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/strategic-priorities-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/strategic-priorities-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/strategic-priorities.field-map-green.png",
      "style_case_title": "策略優先級：野戰地圖綠",
      "yaml_path": "prompt_system/layouts/strategic-priorities.yaml"
    },
    {
      "id": "swot-quadrant",
      "title": "矩陣 SWOT",
      "category": "圖表類型",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "比較 / 決策",
      "structure": "1 + 4",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上標題｜下 2×2 SWOT",
      "variant": "4 格分類",
      "chart_family": "比較 / 決策",
      "chart_type": "SWOT 矩陣",
      "summary": "SWOT 矩陣；構圖採「上標題｜下 2×2 SWOT」，不再視為一般 1 + N 卡片。",
      "slot_count": 6,
      "preview": "layout-previews/swot-quadrant.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/swot-quadrant-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/swot-quadrant-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/swot-quadrant-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/swot-quadrant.paper-board.png",
      "style_case_title": "SWOT：紙本分析板",
      "yaml_path": "prompt_system/layouts/swot-quadrant.yaml"
    },
    {
      "id": "team-grid",
      "title": "人物 團隊格 6人",
      "category": "圖文 / 人物",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 6",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上 1｜下 3×2 人物",
      "variant": "圖文人物混排",
      "chart_family": null,
      "chart_type": null,
      "summary": "用「上 1｜下 3×2 人物」安排人物、照片與文字，讓主次關係一眼可讀。",
      "slot_count": 7,
      "preview": "layout-previews/team-grid.svg",
      "codex_preview": "layout-previews/team-grid-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/team-grid-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/team-grid-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/team-grid-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/team-grid.yaml"
    },
    {
      "id": "testimonial-full",
      "title": "見證 全版引言",
      "category": "引言 / 焦點句",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 1",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "直向排列",
      "composition": "上引言｜下人物與署名",
      "variant": "通用變體",
      "chart_family": null,
      "chart_type": null,
      "summary": "用整頁呈現單一句子的重量，讓觀眾停下來感受一個主張或金句。",
      "slot_count": 6,
      "preview": "layout-previews/testimonial-full.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/testimonial-full-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/testimonial-full-variant-b-codex-20260722.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/testimonial-full-legacy-20260706-batch2.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/testimonial-full.yaml"
    },
    {
      "id": "timeline-milestones",
      "title": "時間軸 橫向里程碑",
      "category": "圖表類型",
      "gallery_category": "資訊圖像",
      "slide_role": "內容頁",
      "subgroup": "流程 / 時間",
      "structure": "1 + sequence",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "流程路徑",
      "composition": "上標題｜下橫向里程碑",
      "variant": "節點時間線",
      "chart_family": "流程 / 時間",
      "chart_type": "橫向時間軸",
      "summary": "橫向時間軸；構圖採「上標題｜下橫向里程碑」，不再視為一般 1 + N 卡片。",
      "slot_count": 3,
      "preview": "layout-previews/timeline-milestones.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/timeline-milestones-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/timeline-milestones-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/timeline-milestones-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/timeline-milestones.museum-chronology.png",
      "style_case_title": "里程碑時間軸：博物館年表",
      "yaml_path": "prompt_system/layouts/timeline-milestones.yaml"
    },
    {
      "id": "timeline-vertical",
      "title": "時間軸 縱向",
      "category": "圖表類型",
      "gallery_category": "資訊圖像",
      "slide_role": "內容頁",
      "subgroup": "流程 / 時間",
      "structure": "1 + sequence",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "流程路徑",
      "composition": "上標題｜下 4–5 段縱向時間軸",
      "variant": "縱向時間軸",
      "chart_family": "流程 / 時間",
      "chart_type": "縱向時間軸",
      "summary": "縱向時間軸；構圖採「上標題｜下 4–5 段縱向時間軸」，不再視為一般 1 + N 卡片。",
      "slot_count": 6,
      "preview": "layout-previews/timeline-vertical.svg",
      "codex_preview": "layout-previews/timeline-vertical-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/timeline-vertical-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/timeline-vertical-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/timeline-vertical-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/timeline-vertical.yaml"
    },
    {
      "id": "title-center",
      "title": "標題 全版置中",
      "category": "引言 / 焦點句",
      "gallery_category": "特定版面",
      "slide_role": "內容頁",
      "subgroup": "置中焦點",
      "structure": "1 + 1",
      "position_family": "置中焦點",
      "title_relation": "標題置中",
      "content_flow": "單一主體",
      "composition": "置中主標｜下輔助文字",
      "variant": "置中大標",
      "chart_family": null,
      "chart_type": null,
      "summary": "用整頁呈現單一句子的重量，讓觀眾停下來感受一個主張或金句。",
      "slot_count": 2,
      "preview": "layout-previews/title-center.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/title-center-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/title-center-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/title-center-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/title-center.luxury-invitation.png",
      "style_case_title": "全版大字：邀請函風",
      "yaml_path": "prompt_system/layouts/title-center.yaml"
    },
    {
      "id": "toc-3-panel-left",
      "title": "目錄 1+3 左側面板",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "左 1｜右 N",
      "structure": "1 + 3",
      "position_family": "左 1｜右 N",
      "title_relation": "左標｜右內容",
      "content_flow": "橫向排列",
      "composition": "左 1｜右 3 欄",
      "variant": "左側主文 + 三章節卡",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「左 1｜右 3 欄」建立章節層級與閱讀順序。",
      "slot_count": 4,
      "preview": "layout-previews/toc-3-panel-left.svg",
      "codex_preview": "layout-previews/toc-3-panel-left-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/toc-3-panel-left-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/toc-3-panel-left-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-3-panel-left-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/toc-3-panel-left.civic-pastel.png",
      "style_case_title": "目錄 1+3 左側主文：公民柔彩",
      "yaml_path": "prompt_system/layouts/toc-3-panel-left.yaml"
    },
    {
      "id": "toc-3-panel-rows",
      "title": "目錄 1+3 面板列",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "左 1｜右 N",
      "structure": "1 + 3",
      "position_family": "左 1｜右 N",
      "title_relation": "左標｜右內容",
      "content_flow": "直向排列",
      "composition": "左 1｜右 3 列",
      "variant": "左側主文 + 三列橫排",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「左 1｜右 3 列」建立章節層級與閱讀順序。",
      "slot_count": 4,
      "preview": "layout-previews/toc-3-panel-rows.svg",
      "codex_preview": "layout-previews/toc-3-panel-rows-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/toc-3-panel-rows-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/toc-3-panel-rows-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-3-panel-rows-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/toc-3-panel-rows.red-editorial.png",
      "style_case_title": "目錄 1+3 左側主文列：紅色編輯風",
      "yaml_path": "prompt_system/layouts/toc-3-panel-rows.yaml"
    },
    {
      "id": "toc-3-vertical",
      "title": "目錄 1+3 直向",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 3",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "直向排列",
      "composition": "上 1｜下 3 直列",
      "variant": "直向三行",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「上 1｜下 3 直列」建立章節層級與閱讀順序。",
      "slot_count": 4,
      "preview": "layout-previews/toc-3-vertical.svg",
      "codex_preview": "layout-previews/toc-3-vertical-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/toc-3-vertical-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/toc-3-vertical-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-3-vertical-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/toc-3-vertical.yaml"
    },
    {
      "id": "toc-3",
      "title": "目錄 1+3 橫排",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 3",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "橫向排列",
      "composition": "上 1｜下 3 欄",
      "variant": "三欄章節卡",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「上 1｜下 3 欄」建立章節層級與閱讀順序。",
      "slot_count": 4,
      "preview": "layout-previews/toc-3.svg",
      "codex_preview": "layout-previews/toc-3-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/toc-3-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/toc-3-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-3-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/toc-3.yaml"
    },
    {
      "id": "toc-4-image-left",
      "title": "目錄 1+4 左圖",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "左視覺｜右內容",
      "structure": "1 + 4",
      "position_family": "左視覺｜右內容",
      "title_relation": "右標｜左內容",
      "content_flow": "左右分區",
      "composition": "左圖｜右標題＋4 格",
      "variant": "左插圖右 2×2",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「左圖｜右標題＋4 格」建立章節層級與閱讀順序。",
      "slot_count": 6,
      "preview": "layout-previews/toc-4-image-left.svg",
      "codex_preview": "layout-previews/toc-4-image-left-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/toc-4-image-left-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/toc-4-image-left-legacy-20260706-fill3-05.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-4-image-left-legacy-20260706-fill3-04.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/toc-4-image-left.field-note-doc.png",
      "style_case_title": "目錄 1+4 左插圖：田野筆記",
      "yaml_path": "prompt_system/layouts/toc-4-image-left.yaml"
    },
    {
      "id": "toc-4-panel-grid",
      "title": "目錄 1+4 面板格",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "左 1｜右 N",
      "structure": "1 + 4",
      "position_family": "左 1｜右 N",
      "title_relation": "左標｜右內容",
      "content_flow": "網格排列",
      "composition": "左 1｜右 2×2",
      "variant": "左側主文 + 2×2 格",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「左 1｜右 2×2」建立章節層級與閱讀順序。",
      "slot_count": 5,
      "preview": "layout-previews/toc-4-panel-grid.svg",
      "codex_preview": "layout-previews/toc-4-panel-grid-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/toc-4-panel-grid-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/toc-4-panel-grid-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-4-panel-grid-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/toc-4-panel-grid.calm-workshop.png",
      "style_case_title": "目錄 1+4 左側主文格：工作坊暖調",
      "yaml_path": "prompt_system/layouts/toc-4-panel-grid.yaml"
    },
    {
      "id": "toc-4-panel-rows",
      "title": "目錄 1+4 面板列",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "左 1｜右 N",
      "structure": "1 + 4",
      "position_family": "左 1｜右 N",
      "title_relation": "左標｜右內容",
      "content_flow": "直向排列",
      "composition": "左 1｜右 4 列",
      "variant": "左側主文 + 四列橫排",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「左 1｜右 4 列」建立章節層級與閱讀順序。",
      "slot_count": 5,
      "preview": "layout-previews/toc-4-panel-rows.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/toc-4-panel-rows-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/toc-4-panel-rows-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-4-panel-rows-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/toc-4-panel-rows.clean-modernist.png",
      "style_case_title": "目錄 1+4 左側主文列：簡潔現代",
      "yaml_path": "prompt_system/layouts/toc-4-panel-rows.yaml"
    },
    {
      "id": "toc-4-vertical",
      "title": "目錄 1+4 直向",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 4",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "直向排列",
      "composition": "上 1｜下 4 直列",
      "variant": "直向四行",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「上 1｜下 4 直列」建立章節層級與閱讀順序。",
      "slot_count": 5,
      "preview": "layout-previews/toc-4-vertical.svg",
      "codex_preview": "layout-previews/toc-4-vertical-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/toc-4-vertical-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/toc-4-vertical-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-4-vertical-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/toc-4-vertical.yaml"
    },
    {
      "id": "toc-4",
      "title": "目錄 1+4 兩排兩列",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 4",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上 1｜下 2×2",
      "variant": "2×2 章節卡",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「上 1｜下 2×2」建立章節層級與閱讀順序。",
      "slot_count": 5,
      "preview": "layout-previews/toc-4.svg",
      "codex_preview": "layout-previews/toc-4-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/toc-4-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/toc-4-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-4-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/toc-4.yaml"
    },
    {
      "id": "toc-5-number-panel-left",
      "title": "目錄 1+5 數字左欄",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "左 1｜右 N",
      "structure": "1 + 5",
      "position_family": "左 1｜右 N",
      "title_relation": "左標｜右內容",
      "content_flow": "直向排列",
      "composition": "左索引｜右 5 列",
      "variant": "左側數字欄 + 五列章節",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「左索引｜右 5 列」建立章節層級與閱讀順序。",
      "slot_count": 10,
      "preview": "layout-previews/toc-5-number-panel-left.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/toc-5-number-panel-left-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/toc-5-number-panel-left-variant-codex-20260722.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-5-number-panel-left-legacy-20260706-batch2.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/toc-5-number-panel-left.yaml"
    },
    {
      "id": "toc-5-panel-grid",
      "title": "目錄 1+5 面板格",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "左 1｜右 N",
      "structure": "1 + 5",
      "position_family": "左 1｜右 N",
      "title_relation": "左標｜右內容",
      "content_flow": "網格排列",
      "composition": "左 1｜右 3+2",
      "variant": "左側主文 + 3+2 格",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「左 1｜右 3+2」建立章節層級與閱讀順序。",
      "slot_count": 6,
      "preview": "layout-previews/toc-5-panel-grid.svg",
      "codex_preview": "layout-previews/toc-5-panel-grid-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/toc-5-panel-grid-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/toc-5-panel-grid-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-5-panel-grid-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/toc-5-panel-grid.sticky-board-color.png",
      "style_case_title": "目錄 1+5 左側主文格：便利貼彩色",
      "yaml_path": "prompt_system/layouts/toc-5-panel-grid.yaml"
    },
    {
      "id": "toc-5-panel-rows",
      "title": "目錄 1+5 面板列",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "左 1｜右 N",
      "structure": "1 + 5",
      "position_family": "左 1｜右 N",
      "title_relation": "左標｜右內容",
      "content_flow": "直向排列",
      "composition": "左 1｜右 5 列",
      "variant": "左側主文 + 五列橫排",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「左 1｜右 5 列」建立章節層級與閱讀順序。",
      "slot_count": 6,
      "preview": "layout-previews/toc-5-panel-rows.svg",
      "codex_preview": "layout-previews/toc-5-panel-rows-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/toc-5-panel-rows-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/toc-5-panel-rows-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-5-panel-rows-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/toc-5-panel-rows.rose-beige.png",
      "style_case_title": "目錄 1+5 左側主文列：玫瑰米彩",
      "yaml_path": "prompt_system/layouts/toc-5-panel-rows.yaml"
    },
    {
      "id": "toc-5-vertical",
      "title": "目錄 1+5 直向",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 5",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "直向排列",
      "composition": "上 1｜下 5 直列",
      "variant": "直向五行",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「上 1｜下 5 直列」建立章節層級與閱讀順序。",
      "slot_count": 6,
      "preview": "layout-previews/toc-5-vertical.svg",
      "codex_preview": "layout-previews/toc-5-vertical-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/toc-5-vertical-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/toc-5-vertical-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-5-vertical-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/toc-5-vertical.yaml"
    },
    {
      "id": "toc-5",
      "title": "目錄 1+5 上三下二",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 5",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上 1｜下 3+2",
      "variant": "3+2 章節卡",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「上 1｜下 3+2」建立章節層級與閱讀順序。",
      "slot_count": 6,
      "preview": "layout-previews/toc-5.svg",
      "codex_preview": null,
      "preview_status": "stale-qa",
      "preview_variants": [
        {
          "src": "layout-previews/toc-5-codex.webp",
          "label": "既有案例 · QA 已失效",
          "kind": "stale-qa"
        },
        {
          "src": "layout-variants/toc-5-variant-codex-20260722.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-5-legacy-20260706-batch2.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/toc-5.yaml"
    },
    {
      "id": "toc-6-panel-rows",
      "title": "目錄 1+6 面板列",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "左 1｜右 N",
      "structure": "1 + 6",
      "position_family": "左 1｜右 N",
      "title_relation": "左標｜右內容",
      "content_flow": "直向排列",
      "composition": "左 1｜右 6 列",
      "variant": "左側主文 + 六列橫排",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「左 1｜右 6 列」建立章節層級與閱讀順序。",
      "slot_count": 7,
      "preview": "layout-previews/toc-6-panel-rows.svg",
      "codex_preview": "layout-previews/toc-6-panel-rows-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/toc-6-panel-rows-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/toc-6-panel-rows-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-6-panel-rows-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/toc-6-panel-rows.light-playful-systems.png",
      "style_case_title": "目錄 1+6 左側主文列：明亮活潑系統",
      "yaml_path": "prompt_system/layouts/toc-6-panel-rows.yaml"
    },
    {
      "id": "toc-6-vertical",
      "title": "目錄 1+6 直向",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 6",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "直向排列",
      "composition": "上 1｜下 6 直列",
      "variant": "直向六行",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「上 1｜下 6 直列」建立章節層級與閱讀順序。",
      "slot_count": 7,
      "preview": "layout-previews/toc-6-vertical.svg",
      "codex_preview": "layout-previews/toc-6-vertical-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/toc-6-vertical-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/toc-6-vertical-legacy-20260706-fill3-01.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-6-vertical-legacy-20260626.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": null,
      "style_case_title": null,
      "yaml_path": "prompt_system/layouts/toc-6-vertical.yaml"
    },
    {
      "id": "toc-6",
      "title": "目錄 1+6 兩排三列",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 6",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上 1｜下 3×2",
      "variant": "3×2 章節卡",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「上 1｜下 3×2」建立章節層級與閱讀順序。",
      "slot_count": 7,
      "preview": "layout-previews/toc-6.svg",
      "codex_preview": "layout-previews/toc-6-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/toc-6-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/toc-6-legacy-20260706-fill3-03.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-6-legacy-20260706-fill3-02.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/toc-6.tech-operations.png",
      "style_case_title": "目錄 1+6：科技營運",
      "yaml_path": "prompt_system/layouts/toc-6.yaml"
    },
    {
      "id": "toc-8",
      "title": "目錄 1+8 兩排四列",
      "category": "目錄",
      "gallery_category": "目錄",
      "slide_role": "目錄",
      "subgroup": "上 1｜下 N",
      "structure": "1 + 8",
      "position_family": "上 1｜下 N",
      "title_relation": "上標｜下內容",
      "content_flow": "網格排列",
      "composition": "上 1｜下 4×2",
      "variant": "4×2 章節卡",
      "chart_family": null,
      "chart_type": null,
      "summary": "目錄用途；以「上 1｜下 4×2」建立章節層級與閱讀順序。",
      "slot_count": 9,
      "preview": "layout-previews/toc-8.svg",
      "codex_preview": "layout-previews/toc-8-codex.webp",
      "preview_status": "approved",
      "preview_variants": [
        {
          "src": "layout-previews/toc-8-codex.webp",
          "label": "正式預覽",
          "kind": "current"
        },
        {
          "src": "layout-variants/toc-8-legacy-20260706-fill3-02.webp",
          "label": "設計變體 A",
          "kind": "variant"
        },
        {
          "src": "layout-variants/toc-8-legacy-20260706-fill3-01.webp",
          "label": "設計變體 B",
          "kind": "variant"
        }
      ],
      "style_case_preview": "layout-style-cases/toc-8.dark-modular-grid.png",
      "style_case_title": "目錄 1+8：深色模組網格",
      "yaml_path": "prompt_system/layouts/toc-8.yaml"
    }
  ]
};
