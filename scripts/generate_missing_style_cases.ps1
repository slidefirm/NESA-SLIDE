$ErrorActionPreference = "Stop"

$items = @(
  @{layout='cards-1-plus-2'; slug='startup-gradient'; display='1+2 雙模組：新創漸層策略'; title='成長引擎\n雙核心'; subtitle='獲客與留存作為兩個主要模組'; body='用鮮明但克制的色彩，把兩個支柱拉開層次，形成新創感。'; mood='vibrant startup gradient'; bg='#FFF8F1'; accent='#FF6B35'; support='#5B4BFF'; image='none'; decor='柔和漸層、玻璃卡與微光邊'; principle='中心主題明確，左右兩張卡片像產品戰略模組。'}
  @{layout='cards-1-plus-3'; slug='sustainability-earth'; display='1+3 三模組：永續實作地圖'; title='永續轉型\n三步驟'; subtitle='盤點、試點、擴散'; body='帶自然材質與土色系，像一本永續行動手冊的摘要頁。'; mood='earthy sustainability'; bg='#F5F1E8'; accent='#7A8B5B'; support='#B77B57'; image='none'; decor='紙感紋理、壓印小圖示與淡色分隔'; principle='溫和自然，不要企業制式綠色海報感。'}
  @{layout='cards-1-plus-4'; slug='brutalist-orange'; display='1+4 四模組：粗獷決策板'; title='決策框架\n四個槓桿'; subtitle='用四張卡片拆開策略重點'; body='把畫面做得大膽、直接、強對比，像設計海報混合策略頁。'; mood='brutalist editorial'; bg='#F7F2EA'; accent='#FF6A00'; support='#111111'; image='none'; decor='粗線框、對位標尺與不對稱留白'; principle='要有態度，但文字仍清楚可讀。'}
  @{layout='cards-1-plus-5'; slug='playful-education'; display='1+5 五模組：教學遊戲化'; title='學習路徑\n五個練習'; subtitle='從理解到實作的循序任務'; body='用友善但不幼稚的配色，像高質感教育工具包。'; mood='playful education'; bg='#FFFDF7'; accent='#5FB0A8'; support='#F2B544'; image='none'; decor='圓角貼紙、小箭頭與淡色底紋'; principle='童趣一點，但仍然適合成年人工作坊。'}
  @{layout='cards-1-plus-6'; slug='neutral-luxury'; display='1+6 六模組：作品集總覽'; title='方法庫\n六個場景'; subtitle='用六個模組展示服務能力'; body='像設計顧問作品集的服務頁，安靜、細緻、帶質感。'; mood='neutral luxury portfolio'; bg='#F6F2EE'; accent='#9B7B6F'; support='#2F2A28'; image='none'; decor='極細分隔線、留白與柔霧底'; principle='高級、克制、適合顧問與作品集語境。'}
  @{layout='cards-1-plus-8'; slug='mission-control'; display='1+8 八模組：營運指揮台'; title='營運節奏\n八個指標'; subtitle='把複雜系統拆成八個穩定模組'; body='像一張深色控制台，但不要變成科幻 UI。'; mood='dark mission control'; bg='#0F1722'; accent='#59C3C3'; support='#F4B860'; image='none'; decor='細格線、發光分隔與低彩資訊塊'; principle='資訊密度高，但仍要像簡報而不是軟體介面。'}
  @{layout='chapter-opener'; slug='cinematic-crimson'; display='章節過場：深紅電影感'; title='第二章\n把流程接起來'; subtitle='從零散工具走向有節奏的系統'; body='這是一張換氣頁，要有戲劇感，但資訊不多。'; mood='cinematic chapter divider'; bg='#F5EFE9'; accent='#8C1C13'; support='#2E2A2A'; image='none'; decor='大色塊、細線與低對比章節編號'; principle='像一本高級書的章節頁。'}
  @{layout='comparison-table'; slug='mint-lab'; display='比較表格：實驗室薄荷'; title='工具比較\n哪個適合你'; subtitle='用清楚的表格結構比較三種方案'; body='表格頁要理性，但視覺上像現代產品評測頁。'; mood='mint product lab'; bg='#F7FFFC'; accent='#4CBFA6'; support='#1F3A3D'; image='none'; decor='淡色列底、精準線條與小標籤'; principle='理性、清爽、像高品質評測卡。'}
  @{layout='dashboard-overview'; slug='executive-emerald'; display='Dashboard：高階綠金分析'; title='營運總覽'; subtitle='本季關鍵指標與風險訊號'; body='像高階營運 review 封面，深綠加淡金，專業但不僵硬。'; mood='executive analytics'; bg='#F3F5F2'; accent='#1F6B5C'; support='#B99A5E'; image='none'; decor='細格網、數字標尺與柔和卡片陰影'; principle='要有 boardroom 感，但仍然明亮。'}
  @{layout='flow-stages-3'; slug='industrial-yellow'; display='三階段流程：工業黃黑'; title='導入流程\n三個階段'; subtitle='準備、落地、優化'; body='流程頁要有方向感，視覺像精密作業指引。'; mood='industrial guidance'; bg='#FAF7F0'; accent='#D9A404'; support='#242424'; image='none'; decor='箭頭、標號圓點與工程式細線'; principle='乾淨、俐落、稍微工業。'}
  @{layout='gantt-roadmap'; slug='cobalt-product-launch'; display='時程路線圖：鈷藍產品發佈'; title='產品上線\nRoadmap'; subtitle='以月份與工作流對齊整體進度'; body='像產品 launch 計畫頁，理性清楚但不無聊。'; mood='cobalt roadmap'; bg='#F6F8FC'; accent='#3366CC'; support='#F28C28'; image='none'; decor='月曆格線、淡色區段標記與細小里程碑旗標'; principle='讓時間軸容易讀，也有產品團隊感。'}
  @{layout='kpi-scorecards'; slug='fintech-neon'; display='KPI 指標卡：金融科技夜色'; title='本月 KPI'; subtitle='效率、品質、留存與成長'; body='像現代 fintech 指標看板，深底搭配明亮螢光點綴。'; mood='fintech minimal dark'; bg='#10151F'; accent='#4DFFA6'; support='#7BDFF2'; image='none'; decor='微光框線、數據膠囊與細線網格'; principle='科技感強，但仍然像簡報靜態頁。'}
  @{layout='matrix-4quadrant'; slug='sticky-note-workshop'; display='四象限矩陣：便條工作坊'; title='優先矩陣'; subtitle='把點子放進可討論的四象限'; body='像實體工作坊牆面，帶一點便條與手作感。'; mood='hands-on workshop'; bg='#FCFAF4'; accent='#F39C6B'; support='#4D7EA8'; image='none'; decor='紙張邊緣、膠帶感與手寫小標'; principle='討論感要強，但版面不能亂。'}
  @{layout='process-flow'; slug='notebook-handdrawn'; display='流程步驟圖：筆記本手繪'; title='執行流程'; subtitle='把抽象方法變成可照做的步驟'; body='用手繪箭頭與筆記感，像教練現場畫給你看。'; mood='hand-drawn notebook'; bg='#FFFDF8'; accent='#3F6E8C'; support='#B55D3D'; image='none'; decor='手繪箭頭、底線與筆記符號'; principle='親切、有方法感、像真人帶領。'}
  @{layout='quote-focus'; slug='poetic-ink'; display='金句聚焦：墨色詩意'; title='不是更會用工具\n而是更知道為什麼要做'; subtitle=''; body='這頁是情緒停頓點，要像一本書的引用頁。'; mood='poetic monochrome'; bg='#FAF8F2'; accent='#1E1E1E'; support='#8E8A84'; image='none'; decor='極淡墨痕、引號與頁邊微記號'; principle='強烈聚焦句子本身，裝飾很輕。'}
  @{layout='recommendation-stack'; slug='consulting-burgundy'; display='建議堆疊：顧問酒紅'; title='建議方向'; subtitle='先做、再做、最後做'; body='像顧問提案摘要頁，三到五層建議清楚堆疊。'; mood='consulting premium'; bg='#F7F2F3'; accent='#7B2D43'; support='#4D4B4B'; image='none'; decor='酒紅標籤、細線與小型序號'; principle='穩重、可信、決策導向。'}
  @{layout='split-comparison'; slug='blue-terracotta'; display='左右對比：藍陶雙面'; title='兩種做法\n差在哪'; subtitle='把舊流程與新流程並排比較'; body='左右兩邊像兩個性格不同的系統，色調拉開。'; mood='balanced duality'; bg='#F7F4EF'; accent='#486D9C'; support='#C46E4E'; image='none'; decor='左右分色、細線框與對照標籤'; principle='對比明顯但不廉價。'}
  @{layout='strategic-priorities'; slug='field-map-green'; display='策略優先級：野戰地圖綠'; title='接下來最重要的事'; subtitle='用優先級排出資源順序'; body='像一張現代化策略地圖，冷靜、務實、方向清楚。'; mood='strategic field map'; bg='#F2F4EE'; accent='#5C7A54'; support='#CC8B3C'; image='none'; decor='地圖式細線、標記點與淡色區塊'; principle='有戰略感，但維持商務簡報可讀性。'}
  @{layout='swot-quadrant'; slug='paper-board'; display='SWOT：紙本分析板'; title='SWOT 分析'; subtitle='優勢、風險、機會與限制'; body='像顧問把四張紙貼在牆上討論，結構清楚。'; mood='paper workshop board'; bg='#FCFAF6'; accent='#6E8B74'; support='#C97A56'; image='none'; decor='紙片陰影、別針感與淡格線'; principle='理性架構加上人手工作感。'}
  @{layout='timeline-milestones'; slug='museum-chronology'; display='里程碑時間軸：博物館年表'; title='關鍵里程碑'; subtitle='把重要節點講成一條值得走讀的故事線'; body='像展覽牆上的 chronology，節制優雅。'; mood='museum chronology'; bg='#F8F5F0'; accent='#7E5C3E'; support='#2F3A40'; image='none'; decor='細點線、年份標牌與留白'; principle='歷程感強，不像專案表格。'}
  @{layout='title-center'; slug='luxury-invitation'; display='全版大字：邀請函風'; title='下一個問題是\n你想保留什麼'; subtitle=''; body='像一張高級講座邀請函，純粹、中心聚焦。'; mood='luxury invitation'; bg='#FBF7F1'; accent='#A8845D'; support='#1F1F1F'; image='none'; decor='中心對位線、燙金感小記號與極淡邊飾'; principle='留白大、氣質強、不要俗豔。'}
  @{layout='toc-3'; slug='civic-pastel'; display='目錄 1+3：公民柔彩'; title='三個章節\n一起走完'; subtitle='從觀察、整理到協作'; body='像 civic innovation 工作坊的暖色導覽頁。'; mood='civic pastel'; bg='#F9F7F2'; accent='#6FA3A4'; support='#E7A97E'; image='none'; decor='圓角卡、柔色底與點狀節奏'; principle='親民、成熟、有公共設計感。'}
  @{layout='toc-3-vertical'; slug='red-editorial'; display='目錄 1+3 直向：紅色編輯'; title='三段推進\n清楚開場'; subtitle='像一本專題雜誌的章節導覽'; body='直向版做得更像出版頁，不像一般 agenda。'; mood='red editorial'; bg='#FBF6F4'; accent='#A63D40'; support='#333333'; image='none'; decor='細紅線、章節碼與頁邊註記'; principle='俐落、文字感強。'}
  @{layout='toc-4'; slug='calm-workshop'; display='目錄 1+4：安定工作坊'; title='四個章節\n完成一次升級'; subtitle='從收集到回顧，形成完整工作流'; body='這是一張溫和的人本工作坊導覽頁，節奏清楚、好開講。'; mood='warm workshop'; bg='#F4F2EE'; accent='#D98C8C'; support='#2C2C2C'; image='none'; decor='很淡的角落記號與紙感'; principle='清楚、溫和、門檻不高。'}
  @{layout='toc-4-image-left'; slug='field-note-doc'; display='目錄 1+4 左插圖：田野筆記'; title='跟著這張圖\n進入四個章節'; subtitle='左邊有情境插圖，右邊是清楚章節卡'; body='像研究員的 field note 導覽頁。'; mood='documentary field note'; bg='#FAF7F0'; accent='#8B6F47'; support='#4A5A52'; image='left'; decor='紙膠帶、註記箭頭與淡手寫元素'; principle='圖在左，文字區一律左對齊。'}
  @{layout='toc-4-vertical'; slug='clean-modernist'; display='目錄 1+4 直向：現代主義'; title='四個模組\n垂直展開'; subtitle='適合節奏明確、一步步往下讀的開場'; body='像現代設計書的目錄頁，乾淨、理性。'; mood='modernist clean'; bg='#F7F7F4'; accent='#355C7D'; support='#C06C84'; image='none'; decor='細線網格與極簡章節碼'; principle='現代主義排版感。'}
  @{layout='toc-5'; slug='sticky-board-color'; display='目錄 1+5：彩色便條板'; title='五個模組\n快速上手'; subtitle='像 workshop 牆上的五張便條'; body='適合比較活潑、互動感強的課程導覽。'; mood='colorful sticky board'; bg='#FCFAF5'; accent='#F4A261'; support='#6D9DC5'; image='none'; decor='便條陰影、膠帶角與小圖釘'; principle='活潑但不能凌亂。'}
  @{layout='toc-5-vertical'; slug='rose-beige'; display='目錄 1+5 直向：玫瑰米色'; title='五段內容\n穩穩往下'; subtitle='柔和但成熟，像女性創業課程封面'; body='讓垂直目錄也能有溫柔而專業的氣質。'; mood='rose beige editorial'; bg='#FBF4F1'; accent='#C97B84'; support='#6B5B53'; image='none'; decor='淡花瓣感線條與細小標籤'; principle='柔和、成熟、有一致節奏。'}
  @{layout='toc-6'; slug='tech-operations'; display='目錄 1+6：科技營運'; title='六個站點\n串成系統'; subtitle='偏理性、偏執行、適合 ops / product'; body='像一場產品營運工作坊的 agenda。'; mood='tech operations'; bg='#F5F8FB'; accent='#2D6A8A'; support='#F08A5D'; image='none'; decor='淡網格、節點線與小型標號'; principle='清楚、效率感、帶點產品團隊語氣。'}
  @{layout='toc-6-vertical'; slug='light-playful-systems'; display='目錄 1+6 直向：輕盈系統感'; title='六個章節\n逐步完成'; subtitle='像教學平台的課程模組索引'; body='清楚、友善、略帶數位學習介面感。'; mood='light learning system'; bg='#FAFCFF'; accent='#7A9E9F'; support='#F2C14E'; image='none'; decor='圓角面板、柔色框與小點狀節拍'; principle='明亮、好懂、不像企業文件。'}
  @{layout='toc-8'; slug='dark-modular-grid'; display='目錄 1+8：深色模組網格'; title='八個模組\n完整工具箱'; subtitle='偏高密度、適合產品與技術訓練'; body='像一張模組化系統導覽頁。'; mood='dark modular'; bg='#111827'; accent='#60A5FA'; support='#F59E0B'; image='none'; decor='發光格線、模組框與暗色層次'; principle='密度高但仍整齊。'}
)

foreach ($item in $items) {
  $promptPath = "artifacts/generated-prompts/$($item.layout).$($item.slug).assembled.yaml"
  $stylePath = "prompt_system/style_cases/$($item.layout).$($item.slug).yaml"

  $prompt = @"
page_type_and_mood:
  prompt: >
    生成一張 16:9 的簡報示意圖，套用既有的 $($item.layout) 結構。
    主題方向是「$($item.title)」，整體氣質為 $($item.mood)。
    這不是通用模板示意，而是一張可直接放進 gallery 展示的風格案例頁。

visual_base_2a:
  background:
    color: "$($item.bg)"
    texture: "依主題加入對應材質，但保持簡報可讀性"
    bleed: "full"

  typography:
    heading:
      color: "$($item.support)"
      family: "style-appropriate display or editorial CJK"
      weight: "semibold"
      size_pt: "26-38"
    body:
      color:
        - "$($item.support)"
        - "$($item.accent)"
      family: "clean readable sans-serif"
      weight: "regular"
      size_pt: "12-18"
      line_spacing: "generous"

  color_system:
    primary:
      color: "$($item.support)"
      usage:
        - "main title"
        - "core labels"
    secondary:
      color: "$($item.accent)"
      usage:
        - "accent markers"
        - "supporting emphasis"
    support:
      - color: "$($item.bg)"
        usage:
          - "background field"

corner_decoration_2b:
  rule: >
    裝飾必須服務這個 layout 的閱讀節奏，不可搶走主要內容注意力。
  top_left:
    decoration: >
      $($item.decor)
  top_right:
    decoration: >
      依版型需要決定是否保留留白或加入極低密度平衡元素。
  bottom_left:
    decoration: >
      可有很淡的收尾記號或頁面感標記。
  bottom_right:
    decoration: >
      保持克制，不形成厚重邊框。

layout_description:
  structure: >
    完整遵循既有的 $($item.layout) 版型結構，只更換內容與風格語彙。
  title_region:
    horizontal_range: "10%-90%"
    vertical_range: "12%-42%"
    description: "標題區依版型節奏配置，維持主要閱讀重心。"
  body_region:
    horizontal_range: "10%-90%"
    vertical_range: "40%-86%"
    description: "說明與模組內容依既有版型排列。"
  image_column: "$($item.image)"
  alignment_rule: "follow existing $($item.layout) alignment rules"

content:
  title: "$($item.title)"
  subtitle:
    text: "$($item.subtitle)"
    style_hint: "依這張風格案例決定副標的份量與表現方式"
  body:
    arrangement: "依既有 layout 的資訊組織方式呈現"
    text: "$($item.body)"

safe_zone_constraints:
  hard_constraint: >
    所有主要資訊元素都必須完整落在 10%-90% safe zone 內。
  edge_rule: "只有低優先級背景與裝飾可略微貼近邊界。"
  exception: >
    若版型本身包含滿版照片或邊緣視覺，仍不得影響主要文字可讀性。

closing_design_intent:
  prompt: >
    讓這張圖像一個真正有個性的 layout showcase，而不是重複套皮。
    視覺方向關鍵詞：$($item.mood)。
    核心原則：$($item.principle)
"@

  $style = @"
id: $($item.layout).$($item.slug)
layout_id: $($item.layout)
display_name: $($item.display)
source_note: "Codex-generated style case based on the existing $($item.layout) layout."

visual_base_2a:
  background:
    color: "$($item.bg)"
    texture: "style-specific material treatment"
    mood: "$($item.mood)"

  typography:
    title:
      family: "style-appropriate CJK display"
      weight: "600-800"
      treatment: "title styling tailored to the concept"
    subtitle_panel:
      family: "clean or theme-matched sans-serif"
      weight: "400-700"
      treatment: "subtitle styling tailored to the concept"
    speaker_meta:
      family: "clean readable sans-serif"
      weight: "400-500"
      treatment: "supporting content follows the layout rhythm"

  image_language:
    style: "$($item.mood)"
    treatment: "generated specifically to suit this layout showcase"

  color_system:
    base: "$($item.bg)"
    primary_text: "$($item.support)"
    secondary_text: "$($item.accent)"
    accent: "$($item.accent)"
    support: "$($item.support)"

corner_decoration_2b:
  decor_mode: "layout-aware unique accents"
  vocabulary:
    - id: primary-accent
      visual: "$($item.decor)"
      placement: "layout-dependent"
      density: "low-to-medium"

composition_notes:
  case_preview: "artifacts/deploy/layout-style-cases/$($item.layout).$($item.slug).png"
  source_layout: "$($item.layout)"
  source_asset: "$promptPath"
  principle: "$($item.principle)"
"@

  Set-Content -Path $promptPath -Value $prompt -Encoding UTF8
  Set-Content -Path $stylePath -Value $style -Encoding UTF8
}

Write-Output "Generated $($items.Count) prompt/style-case pairs"
