# HTML 版型渲染模式參考

讀取時機：AI 在將 Theme core、Layout core、HTML adapter 與當次 content manifest 渲染成 HTML 時，從本文件查出目標 Layout 所在的「族群」，
套用對應的 HTML 模式。本文件補充 `html-generation-rules.md` 的三條通用規則，兩份一起讀。

座標換算永遠是：`x_px = x% × 19.2`、`y_px = y% × 10.8`、`w_px = w% × 19.2`、`h_px = h% × 10.8`。

## Typography token precedence

本文件後面的 HTML 片段主要示意 Layout 幾何與閱讀順序；片段中的數字型
`font-weight` 不是另一份字重規範。實際 renderer 必須依
`references/html-generation-rules.md` 的語意 token materialize：核心標題使用
`heavy`、小標使用 `normal`、說明／內文使用 `light`，並依字族能力套用必要的 fallback。
若本文件的舊片段數值與 typography token 不一致，以 `html-generation-rules.md` 為準。

## 所有族群共用的物件樹

本文件後面的片段只說明視覺排列；正式 renderer 必須再套用以下物件結構，且本節優先於舊片段中
把 slot 直接寫成 `.el` 的簡化示例：

1. `.content[data-content-area]`：固定 1728×888 的內部座標系，不是編輯物件。
2. `[data-edit-layout-only="true"]`：Grid／Flex／整體置中的排版 frame，可以滿寬或滿高，但不是
   `.el`，也不參與 hit-test、marquee、物件清單或群組。
3. 獨立 `.el`：主標、副標、正文、結構線、註解、結論、行動句與來源各自可選，不因定位而自動組群。
4. `.el[data-edit-structure="module"]`：semantic module 群組，只用於「拆開後會失去單一資訊單位」
   的卡片、流程節點、指標或圖表；第一個直接子層是背景，後續才是標籤、標題、內文或資料圖層。

renderer 可量測所有可見內容的聯集並把單一 `dx／dy` 寫到 layout-only centering frame；這個量測聯集
不是編輯群組。初始開啟時只看得到上述獨立 `.el` 與 semantic module。取消 semantic module 後才進入
background／text／data layers；使用者手動建立的巢狀群組仍逐層取消。文字框預設垂直置中。

## 全域水平對齊繼承契約

每張 production slide 必須先由主標建立 `left`、`center` 或 `right` 水平對齊模式。
surface module 根節點、其中的 text／metric layers、獨立總結與 takeaway 全數繼承同一模式；
不得再由 Theme／Preset 或個別 component CSS 改成另一種對齊。

唯一例外是「圓形容器內的數字」的字形對齊：這類 metric 必須使用 `.circle-number-metric`，
並保留 `data-edit-horizontal-align="center"`；但圓形容器本身仍必須與所屬 semantic module
共享中心軸，不得停在卡片左上角。`circle-number-exception` 只描述圓內字形，不豁免父模組幾何。
renderer 必須在 slide root 記錄 `data-page-horizontal-align`，並在一般內容寫入
`data-edit-alignment-source="page-title"`；圓形數字則寫入 `circle-number-exception`，供 Browser QA 驗證。

Layout／renderer variant 可以讓 semantic module 宣告自己的內部閱讀軸，但必須是明示契約，
不是個別 CSS 偷改：module root 使用 `data-module-interior-align="left|center|right"`，仍以
`page-title` 對齊整個模組；只有該 module 內的 text／metric layers 使用相同的
`data-edit-horizontal-align` 與 `data-edit-alignment-source="module-interior"`。Browser QA 必須
驗證所有 module-interior layers 與最近 module root 的宣告一致；沒有宣告時仍一律繼承頁面主標。

對一列滿寬的 Open／Banded 模組，應使用「layout-only slot + 內層小群組」，不能讓滿寬 slot 變成
可選取定位框。對 3 個以上同級模組、且空白側沒有 counterweight 的版面，可見內文聯集至少使用
Content Area 寬度 68%；這是可見內容幾何，不以透明外框或不可見 slot 計算。

每個語意模組的底板／背景必須是 module group 的第一個直接 `data-edit-layer="background"` 子層，
不得只畫在父容器 background 或 `::before`／`::after`。因此解除 module group 後，文字、資料層與
底板都可以各自選取；純定位 slot、Content Area 與非內容裝飾 pseudo-element 才不可選。
該背景子層必須填滿模組並實際承接可見 fill／border／radius／shadow；父容器只擁有 grid／flex item
的幾何，不得另畫一份不可選的底板。footer、caption 或結論句若不屬於同一資訊單位，就保持為群組外
的獨立 `.el`；若它本身有完整底板與內部層級，則建立自己的 semantic module。

側邊控制點是內容感知的框架單軸調整，不得用 `scaleX`／`scaleY` 扭曲文字。往內拖時先消耗
padding、gap 與層間距；水平縮放接著讓文字框自然回流，垂直縮放接著壓縮行距；只有在內容即將
碰撞或溢出時，才等比例調整 font-size 與 line-height。若最低可用內容仍塞不下，控制點必須停在
最後一個合法尺寸；完成內容 fit 後，還要用實際可見聯集再次夾進 Content Area，不得因最低內容
高度回彈而讓選取框反向變大或越界。四角控制點才執行鎖定長寬比的整體縮放。

---

## 族群 A：封面類（cover / hero）

成員：`hero-fullbleed`、`hero-fullbleed-brand-footer`、`cover-center-title-edge-decor`、
`cover-photo-frame`、`cover-photo-frame-reverse`、`cover-photo-overlay-block`

### A1 滿版背景 + 左下文字（hero-fullbleed、hero-fullbleed-brand-footer）

`speaker`、`org` 與其他 metadata 是選填內容，不是用來補滿畫面的裝飾槽。只有當次
content manifest 明確提供、且對觀眾有用時才輸出對應 DOM；缺少時整個物件省略，renderer
不得自創組織名、英文 kicker、年份、版本、Concept／Lab／Studio 等填充文字。

```html
<!-- 背景：CSS background 或 gradient，不需要 img 標籤 -->
<div class="slide" id="s{N}" style="background: {bg_css};">
  <!-- 底部 scrim 加深文字對比 -->
  <div class="el" style="left:0;top:540px;width:1280px;height:540px;
    background:linear-gradient(28deg,rgba(0,0,0,.7) 0%,rgba(0,0,0,0) 68%);">
  </div>
  <!-- 主標 slot title [8,58,72,20] -->
  <div class="el title" style="left:153.6px;top:626.4px;width:1382.4px;height:216px;">
    {title}
  </div>
  <!-- 副標 subtitle [8,79,62,6] -->
  <div class="el subtitle" style="left:153.6px;top:853.2px;width:1190.4px;height:64.8px;">
    {subtitle}
  </div>
  <!-- speaker [8,87,44,4] -->
  <div class="el speaker" style="left:153.6px;top:939.6px;width:844.8px;height:43.2px;">
    {speaker}
  </div>
  <!-- org [8,91,44,4] -->
  <div class="el org" style="left:153.6px;top:982.8px;width:844.8px;height:43.2px;">
    {org}
  </div>
  <!-- logo 浮水印 watermark_region [87,6,10,8] -->
  <div class="el logo-wm" style="left:1670.4px;top:64.8px;width:192px;height:86.4px;
    opacity:0.4;">logo</div>
</div>
```

`hero-fullbleed-brand-footer` 差異：底部加一道滿版色帶（`left:0; bottom:0; width:1920px; height:~80px`），品牌色。

### A2 置中文字 + 邊角裝飾（cover-center-title-edge-decor）

```html
<div class="slide" id="s{N}" style="background:{bg_css};">
  <!-- 裝飾元素：邊角幾何，position absolute，opacity .4~.6 -->
  <div class="el decor-tl" style="left:0;top:0;width:480px;height:360px; ..."></div>
  <div class="el decor-tr" style="left:1440px;top:0;width:480px;height:360px; ..."></div>
  <div class="el decor-bl" style="left:0;top:720px;width:300px;height:360px; ..."></div>
  <div class="el decor-br" style="left:1620px;top:720px;width:300px;height:360px; ..."></div>

  <!-- 置中文字堆疊 title [18,30,64,22] -->
  <div class="el title" style="left:345.6px;top:324px;width:1228.8px;height:237.6px;
    text-align:center;">
    {title}
  </div>
  <!-- subtitle [28,56,44,7] -->
  <div class="el subtitle" style="left:537.6px;top:604.8px;width:844.8px;height:75.6px;
    text-align:center;">
    {subtitle}
  </div>
  <!-- speaker [30,66,40,5] -->
  <div class="el speaker" style="left:576px;top:712.8px;width:768px;height:54px;
    text-align:center;">
    {speaker}
  </div>
</div>
```

### A2b 置中文字 + 雙線外框（cover-center-title-double-frame）

- 使用情境：純 Pattern 封面，需要安靜、完整的頁面邊界，但不使用照片或插畫。
- 外框由 renderer-base 在四邊 96px 留白帶內畫出兩道 hairline；它是環境層，不能被選取，
  也不改變 `.content` 或中央文字群的幾何。
- 主標、副標與選填署名維持獨立 `.el`，共享同一中心軸；外框移除後內容仍須完整可懂。
- Theme 只可透過既有色彩 token 改變框線色彩／透明度，不得改寫兩圈 inset、線寬或完整性。
- 不加入 Logo、照片、SVG 場景或四角貼紙；雙線外框本身就是唯一招牌 Pattern。

### A3 半版照片封面（cover-photo-frame / cover-photo-frame-reverse）

```html
<!-- cover-photo-frame：左圖右文 -->
<div class="slide" id="s{N}" style="background:{bg_css};">
  <!-- 照片區 hero-photo [0,0,40,100] → 768×1080 -->
  <div class="el photo-zone" style="left:0;top:0;width:768px;height:1080px;
    background:{photo_or_placeholder}; background-size:cover; background-position:center;">
    <!-- 若無圖：只保留純色或低對比漸層填色，不加入 SVG、X 線、文字或假圖。 -->
  </div>
  <!-- 接縫裝飾（可選） -->
  <div class="el seam" style="left:760px;top:0;width:2px;height:1080px;
    background:{accent_color};opacity:.5;"></div>

  <!-- 右欄文字，所有元素共享 left:921.6px（slot x=48, left edge） -->
  <div class="el title" style="left:921.6px;top:237.6px;width:921.6px;height:216px;">
    {title}
  </div>
  <div class="el subtitle" style="left:921.6px;top:475.2px;width:921.6px;height:108px;">
    {subtitle}
  </div>
  <div class="el speaker" style="left:921.6px;top:691.2px;width:806.4px;height:64.8px;">
    {speaker}
  </div>
  <div class="el org" style="left:921.6px;top:766.8px;width:806.4px;height:54px;">
    {org}
  </div>
</div>
```

`cover-photo-frame-reverse` 將照片移到右側（right:0; left 改為 1152px）、文字欄改 left=0。

### A4 滿版照片 + 遮罩色塊（cover-photo-overlay-block）

```html
<div class="slide" id="s{N}">
  <!-- 全版底圖 -->
  <div class="el" style="inset:0;width:1920px;height:1080px;
    background:{photo_or_placeholder}; background-size:cover;"></div>
  <!-- 遮罩色塊 overlay，用 layout YAML 定義的 overlay 區 -->
  <div class="el overlay" style="left:{ox}px;top:{oy}px;width:{ow}px;height:{oh}px;
    background:{accent_color};opacity:.85;"></div>
  <!-- 文字壓在遮罩上 -->
  <div class="el title" style="...;color:#fff;">{title}</div>
</div>
```

---

## 族群 B：引言類（quote / title-center）

成員：`title-center`、`quote-focus`

### B1 全版大字（title-center）

```html
<div class="slide" id="s{N}" style="background:{bg_css};">
  <div class="title-flow-stack statement-center-area"
    data-edit-layout-only="true"
    data-auto-layout="vertical-stack"
    data-layout-flow-align="center"
    style="left:{stack_x}px;top:{stack_y}px;width:{stack_w}px;height:{stack_h}px;">
    <div class="el headline" data-edit-align-contract="center-axis"
      style="width:max-content;height:auto;max-width:{headline_max_w}px;">
      {headline}
    </div>
    <div class="el statement-rule" data-edit-align-contract="center-axis"
      style="width:{rule_w}px;height:{rule_h}px;"></div>
    <div class="el sup-text" data-edit-align-contract="center-axis"
      style="width:max-content;height:auto;max-width:{support_max_w}px;">
      {supporting_text}
    </div>
  </div>
</div>
```

`title-flow-stack` 只提供依內容高度向下排列的 scaffold，不決定水平對齊。`title-center` 必須以
`data-layout-flow-align="center"` 明確宣告中心軸；headline、分隔線與 supporting-text 的寬高由
實際內容決定，但三者的 `centerX` 必須一致。需要靠左的頁首由其他 Layout 明確使用 `start`，
不得以共用 flow class 改變本 Layout 的中心軸。

### B2 金句聚焦（quote-focus）

```html
<div class="slide" id="s{N}" style="background:{bg_css};">
  <!-- 大引號裝飾（side-mark [72,20,16,48]）→ left:1382 top:216 w:307 h:518 -->
  <div class="el side-mark" style="left:1382.4px;top:216px;width:307.2px;height:518.4px;
    font-size:320px; font-family:serif; color:{accent}; opacity:.12;
    display:flex;align-items:flex-start;justify-content:center;
    line-height:1; user-select:none;">
    "
  </div>
  <!-- quote [12,24,76,34] → left:230 top:259 w:1459 h:367 -->
  <div class="el quote" style="left:230.4px;top:259.2px;width:1459.2px;height:367.2px;
    font-size:{display~section range}px; font-weight:700; line-height:1.1;">
    {quote}
  </div>
  <!-- attribution [12,62,40,8] → left:230 top:669 w:768 h:86 -->
  <div class="el attr" style="left:230.4px;top:669.6px;width:768px;height:86.4px;
    font-size:{caption}px; opacity:.65;">
    {attribution}
  </div>
</div>
```

---

## 族群 C：章節頁（chapter）

成員：`chapter-opener`、`chapter-number-bg-left-title-rule`、
`chapter-text-left-photo-brand`、`chapter-fullbleed-overlay-title`

### C1 章節過場（chapter-opener）

```html
<div class="slide" id="s{N}" style="background:{bg_css};">
  <!-- 上方全寬 accent rule（structural） -->
  <div class="el rule-top" style="left:192px;top:{title_top-24}px;width:1536px;height:3px;
    background:{accent_color};"></div>

  <!-- chapter-label [10,30,50,6] → left:192 top:324 w:960 h:64.8 -->
  <div class="el ch-label" style="left:192px;top:324px;width:960px;height:64.8px;
    font-size:{caption}px; font-weight:600; letter-spacing:.2em; text-transform:uppercase;">
    {chapter_label}
  </div>
  <!-- accent-bar [10,38,8,1.5] → left:192 top:410 w:153.6 h:16.2 -->
  <div class="el accent-bar" style="left:192px;top:410.4px;width:153.6px;height:4px;
    background:{accent_color};"></div>
  <!-- title [10,42,80,30] → left:192 top:453 w:1536 h:324 -->
  <div class="el title" style="left:192px;top:453.6px;width:1536px;height:324px;
    font-size:{section range}px; font-weight:700; line-height:1.1;">
    {title}
  </div>
  <!-- 下方全寬 accent rule（structural） -->
  <div class="el rule-bot" style="left:192px;top:{title_bottom+16}px;width:1536px;height:1.5px;
    background:{accent_color};"></div>
  <!-- subtitle [10,75,58,8] → left:192 top:810 w:1113 h:86 -->
  <div class="el subtitle" style="left:192px;top:810px;width:1113.6px;height:86.4px;
    font-size:{subtitle}px;">
    {subtitle}
  </div>
</div>
```

### C2 章節數字背景（chapter-number-bg-left-title-rule）

```html
<div class="slide" id="s{N}" style="background:{bg_css};">
  <!-- 背景大數字 chapter-number-bg [51,17,35,62] → left:979 top:183 w:672 h:669 -->
  <div class="el ch-num-bg" style="left:979.2px;top:183.6px;width:672px;height:669.6px;
    font-size:600px; font-weight:900; color:{accent_color}; opacity:.08;
    display:flex;align-items:center;justify-content:center;
    line-height:1; user-select:none; overflow:hidden;">
    {chapter_number}
  </div>
  <!-- chapter-label [5,23,30,8] → left:96 top:248 w:576 h:86 -->
  <div class="el ch-label" style="left:96px;top:248.4px;width:576px;height:86.4px;
    font-size:{caption}px; letter-spacing:.15em; text-transform:uppercase;">
    {chapter_label}
  </div>
  <!-- title [5,38,60,28] → left:96 top:410 w:1152 h:302 -->
  <div class="el title" style="left:96px;top:410.4px;width:1152px;height:302.4px;
    font-size:{section range}px; font-weight:700; line-height:1.1;">
    {title}
  </div>
  <!-- subtitle [5,72,62,8] → left:96 top:777 w:1190 h:86 -->
  <div class="el subtitle" style="left:96px;top:777.6px;width:1190.4px;height:86.4px;">
    {subtitle}
  </div>
  <!-- 右側細裝飾條 side-decor [94,3,1,94] → left:1804 top:32 w:19 h:1015 -->
  <div class="el side-decor" style="left:1804.8px;top:32.4px;width:19.2px;height:1015.2px;
    background:{accent_color}; opacity:.3;"></div>
</div>
```

### C3 左文右照 + 品牌遮罩（chapter-text-left-photo-brand）

```html
<div class="slide" id="s{N}" style="background:{bg_css};">
  <!-- 右側照片 photo_right [45,0,55,100] → left:864 top:0 w:1056 h:1080 -->
  <div class="el photo-r" style="left:864px;top:0;width:1056px;height:1080px;
    background:{placeholder}; background-size:cover; background-position:center;">
    <!-- placeholder 只表達已填入的媒體區，不模擬照片內容。 -->
  </div>
  <!-- 品牌遮罩 brand_overlay [53,30,32,40] → left:1017 top:324 w:614 h:432；橫跨圖文邊界 -->
  <div class="el brand-ov" style="left:1017.6px;top:324px;width:614.4px;height:432px;
    background:{accent_color}; opacity:.72;"></div>

  <!-- 左文字欄，共用 left:192px -->
  <div class="el title" style="left:192px;top:324px;width:729.6px;height:151.2px;
    font-size:{section}px; font-weight:700;">{title}</div>
  <div class="el body" style="left:192px;top:518.4px;width:691.2px;height:237.6px;
    font-size:{body}px; line-height:1.5;">{body}</div>
</div>
```

### C4 滿版照片 + 左上遮罩標題 + 右側數字欄（chapter-fullbleed-overlay-title）

```html
<div class="slide" id="s{N}">
  <!-- 全版照片 -->
  <div class="el photo-full" style="left:0;top:0;width:1920px;height:1080px;
    background:{placeholder}; background-size:cover;">
    <!-- placeholder 只使用純色或低對比漸層填滿既有 media slot。 -->
  </div>
  <!-- 右側實色數字欄 number_panel [82,0,18,100] → left:1574 w:346 h:1080 -->
  <div class="el num-panel" style="left:1574.4px;top:0;width:345.6px;height:1080px;
    background:{accent_color};display:flex;align-items:center;justify-content:center;">
    <span style="font-size:280px;font-weight:900;color:rgba(255,255,255,.25);
      writing-mode:horizontal-tb;user-select:none;">{chapter_number}</span>
  </div>
  <!-- 左上半透明遮罩 title_overlay [5,8,32,24] → left:96 top:86 w:614 h:259 -->
  <div class="el title-ov" style="left:96px;top:86.4px;width:614.4px;height:259.2px;
    background:rgba(0,0,0,.62); padding:32px 40px; box-sizing:border-box;">
    <div style="font-size:{section}px;font-weight:700;color:#fff;line-height:1.1;">
      {title}
    </div>
  </div>
</div>
```

---

## 族群 D：目錄 TOC（toc-*）

### D1 橫排等寬卡片（toc-3、toc-4、toc-5、toc-6、toc-8）

通用模板，N 從 layout YAML 的 chapter-1 ~ chapter-N slot 算出。

```html
<div class="slide" id="s{N}" style="background:{bg_css};">
  <!-- title [8,10,84,10] → left:153 top:108 w:1612 h:108 -->
  <div class="el title" style="left:153.6px;top:108px;width:1612.8px;height:108px;
    text-align:{center|left};font-size:{page-title}px;font-weight:700;">
    {title}
  </div>

  <!-- 每個 chapter 卡：slot region 直接換算 px，等寬等高 -->
  <!-- toc-3 示例：chapter-1 [8,28,24,56] → left:153 top:302 w:460 h:604 -->
  <div class="el ch-card" style="left:153.6px;top:302.4px;width:460.8px;height:604.8px;
    background:{card_bg}; border-radius:12px; padding:40px 36px;
    box-sizing:border-box; overflow:hidden;">
    <div class="ch-num" style="font-size:{mega-number light}px;font-weight:900;
      color:{accent};line-height:1;">{num}</div>
    <div class="ch-title" style="margin-top:16px;font-size:{module-title}px;
      font-weight:600;line-height:1.2;">{chapter_title}</div>
    <div class="ch-body" style="margin-top:12px;font-size:{body}px;
      line-height:1.5;opacity:.7;">{chapter_desc}</div>
  </div>
  <!-- 第 2、3 ... 張卡片依序換 left 值 -->
</div>
```

間距邏輯：`gap = (chapter-2.left - (chapter-1.left + chapter-1.width)) × 19.2`，保持各卡等距。

### D2 垂直堆疊（toc-3-vertical、toc-4-vertical、toc-5-vertical、toc-6-vertical）

與 D1 相同結構，但 slot 改為垂直排列（y 方向遞增），每行 = `{title + desc}` 橫向全展開。

```html
<!-- 示例：toc-3-vertical，每行含左側編號 + 右側標題 desc -->
<div class="el ch-row" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;
  display:flex; align-items:center; gap:32px;">
  <div class="ch-num" style="flex:0 0 120px; font-size:{section}px; font-weight:900;
    color:{accent};">{num}</div>
  <div class="ch-text" style="flex:1;">
    <div class="ch-title" style="font-size:{module-title}px;font-weight:600;">{ch_title}</div>
    <div class="ch-body" style="font-size:{body}px;opacity:.7;margin-top:8px;">{ch_desc}</div>
  </div>
</div>
```

### D3 左側色欄 + 大數字 + 右側文字行（toc-5-number-panel-left）

```html
<div class="slide" id="s{N}" style="background:{bg_css};">
  <!-- 左側色欄 number_panel [4,0,33,100] → left:76.8 top:0 w:633.6 h:1080 -->
  <div class="el num-panel" style="left:76.8px;top:0;width:633.6px;height:1080px;
    background:{accent_color};"></div>

  <!-- 5 個大數字：number-N [4,6+18N,30,17] → 換算後各佔 183.6px 高 -->
  <!-- number-1 [4,6,30,17] → left:76.8 top:64.8 w:576 h:183.6 -->
  <div class="el num" style="left:76.8px;top:64.8px;width:576px;height:183.6px;
    display:flex;align-items:center;justify-content:center;
    font-size:{mega-number}px;font-weight:900;color:rgba(255,255,255,.3);line-height:1;">
    01
  </div>
  <!-- number-2 [4,24,30,17] → top:259.2 …… 依此類推 -->

  <!-- 5 個章節文字行：chapter-N [38,8+18N,54,14] -->
  <!-- chapter-1 [38,8,54,14] → left:729.6 top:86.4 w:1036.8 h:151.2 -->
  <div class="el ch-row" style="left:729.6px;top:86.4px;width:1036.8px;height:151.2px;
    display:flex;flex-direction:column;justify-content:center; padding:0 24px;">
    <div class="ch-title" style="font-size:{module-title}px;font-weight:600;">{ch_title}</div>
    <div class="ch-desc" style="font-size:{body}px;opacity:.65;margin-top:8px;">{ch_desc}</div>
  </div>
  <!-- chapter-2 [38,26,54,14] → top:280.8 …… -->
</div>
```

### D4 左側主文面板 + 右側 3 欄（toc-3-panel-left）

```html
<div class="slide" id="s{N}" style="background:{bg_css};">
  <!-- 左面板 panel_left [4,8,33,82] → left:76.8 top:86.4 w:633.6 h:885.6 -->
  <div class="el panel" style="left:76.8px;top:86.4px;width:633.6px;height:885.6px;
    background:{panel_bg}; padding:56px 48px; box-sizing:border-box;">
    <div style="font-size:{section}px;font-weight:700;">{panel_title}</div>
    <div style="font-size:{body}px;margin-top:24px;opacity:.75;">{panel_desc}</div>
  </div>
  <!-- chapter-1 [41,8,18,82] → left:787.2 top:86.4 w:345.6 h:885.6 -->
  <!-- chapter-2 [61,8,18,82] → left:1171.2 top:86.4 w:345.6 h:885.6 -->
  <!-- chapter-3 [80,8,17,82] → left:1536 top:86.4 w:326.4 h:885.6 -->
  <div class="el ch-card" style="left:787.2px;top:86.4px;width:345.6px;height:885.6px;
    background:{card_bg}; padding:40px 28px; box-sizing:border-box; border-radius:8px;">
    ...
  </div>
</div>
```

### D5 面板列（toc-N-panel-rows、toc-N-panel-grid）

每行 = `[number | title | desc]` 三欄橫排，padding 左右一致，水平分隔線區隔各行。

```html
<div class="el ch-row" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;
  display:flex; align-items:center; border-bottom:1px solid rgba(0,0,0,.1);">
  <div style="flex:0 0 160px; font-size:{section}px; font-weight:900;
    color:{accent};">{num}</div>
  <div style="flex:1;">
    <div style="font-size:{module-title}px;font-weight:600;">{ch_title}</div>
    <div style="font-size:{body}px;opacity:.65;margin-top:6px;">{ch_desc}</div>
  </div>
</div>
```

---

## 族群 E：模組陣列（cards-1-plus-N / cycle-hub）

### E1 等寬卡片陣列（cards-1-plus-2 ～ cards-1-plus-8）

cards-1-plus-3 的 HTML 內部配方只保留
`icon-title-body`、`metric-title`、`label-rule-body`、`side-icon-body` 四支，canonical catalog 為
`prompt_system/renderers/html/layout-variants/cards-1-plus-3.yaml`。其餘 cards-1-plus-N 遵循相同
slot 原則，region 由 Layout YAML 直接換算。

- `icon-title-body` 不宣告 module-interior 軸；卡內標題與內文直接繼承頁面主標的左／中／右對齊。
- `metric-title` 固定閱讀順序為「資料來源 → 指標名稱 → 數字 → 背景說明」，不讓觀眾先看數字再猜它代表什麼。
- `label-rule-body` 保持「標籤 → 分隔線 → 標題 → 內文」的左對齊證據卡。
- `side-icon-body` 的長文段落以兩個全形空白（U+3000）開頭，只影響正文首行，不影響標題。

```html
<div class="el card" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;
  background:#fff; border-radius:20px; padding:48px 40px;
  box-shadow:0 20px 48px rgba(0,0,0,.07); box-sizing:border-box; overflow:hidden;">
  <!-- 頂飾條 -->
  <div style="position:absolute;left:0;top:0;width:100%;height:6px;
    background:{accent_color};"></div>
  <div class="num" style="font-size:{section}px;font-weight:900;color:{accent};">{num}</div>
  <div class="mtitle" style="font-size:{module-title}px;font-weight:600;margin-top:16px;">
    {module_title}
  </div>
  <div class="mbody" style="font-size:{body}px;line-height:1.5;margin-top:12px;opacity:.7;">
    {module_body}
  </div>
</div>
```

`cards-1-plus-8`：卡片較小，字級取範圍下緣；確認溢位防呆（規則 3）。

### E2 環形中心輪（cycle-hub-6）

```html
<div class="slide" id="s{N}" style="background:{bg_css};">
  <!-- 圓環 SVG，cx=960 cy=540，半徑=37%×1080/2≈400px（以投影片較短邊算）；
       實際：ring_layout.radius_pct=37，以中心點 (960,540) 算，半徑 = 37%×1080×0.5 = 199.8 → 取 200px
       或：用投影片寬度較短邊 = 1080，radius_px = 1080 × 0.37 / 2 ≈ 200px -->
  <svg style="position:absolute;left:0;top:0;width:1920px;height:1080px;"
    xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
    <!-- 描邊圓環 -->
    <circle cx="960" cy="540" r="400" fill="none"
      stroke="{accent_color}" stroke-width="1.5" opacity=".35"/>
    <!-- 6 個圖示圓，60° 間隔；起點 12 o'clock（角度 -90°） -->
    <!-- 角度公式：θ_n = -90 + n*60（deg），x = 960 + 400*cos(θ)，y = 540 + 400*sin(θ） -->
    <!-- item-1（12點）: x=960, y=140 -->
    <circle cx="960" cy="140" r="44" fill="{accent_color}" opacity=".9"/>
    <!-- item-4（2點）: x=1306, y=340 -->
    <circle cx="1306" cy="340" r="44" fill="{accent_color}" opacity=".9"/>
    <!-- item-5（4點）: x=1306, y=740 -->
    <circle cx="1306" cy="740" r="44" fill="{accent_color}" opacity=".9"/>
    <!-- item-6（6點）: x=960, y=940 -->
    <circle cx="960" cy="940" r="44" fill="{accent_color}" opacity=".9"/>
    <!-- item-3（8點）: x=614, y=740 -->
    <circle cx="614" cy="740" r="44" fill="{accent_color}" opacity=".9"/>
    <!-- item-2（10點）: x=614, y=340 -->
    <circle cx="614" cy="340" r="44" fill="{accent_color}" opacity=".9"/>
    <!-- 連接線（可選）：各圖示圓心到中心 -->
  </svg>

  <!-- 中心輪轂 hub_title [36,42,28,16] → left:691.2 top:453.6 w:537.6 h:172.8 -->
  <!-- 輪心只有這一個文字物件：無底色面板、無描邊、無陰影，環線在文字後方保持完整 -->
  <!-- 最多兩行、每行 ≤6 個中文字；說明句交給六個 item，不要在這裡加副標 -->
  <div class="el hub-title" style="left:691.2px;top:453.6px;width:537.6px;height:172.8px;
    text-align:center;font-size:{section}px;font-weight:700;">{hub_title}</div>

  <!-- 左欄三項，右對齊，item-1/2/3 各有 slot region -->
  <!-- item-1 [4,14,25,24] → left:76.8 top:151.2 w:480 h:259.2；文字右對齊（向圓心靠攏） -->
  <div class="el item" style="left:76.8px;top:151.2px;width:480px;height:259.2px;
    text-align:right;display:flex;flex-direction:column;justify-content:center;padding-right:24px;">
    <div style="font-size:{module-title}px;font-weight:600;">{item_title}</div>
    <div style="font-size:{body}px;opacity:.7;margin-top:8px;">{item_desc}</div>
  </div>
  <!-- item-2 [4,40,25,24] → top:432 -->
  <!-- item-3 [4,66,25,24] → top:712.8 -->

  <!-- 右欄三項，左對齊 -->
  <!-- item-4 [71,14,25,24] → left:1363.2 top:151.2 w:480 h:259.2；文字左對齊 -->
  <div class="el item" style="left:1363.2px;top:151.2px;width:480px;height:259.2px;
    text-align:left;display:flex;flex-direction:column;justify-content:center;padding-left:24px;">
    ...
  </div>
</div>
```

圖示圓座標精算表（半徑 400px，以 1920×1080 中心 960,540 為原點）：

| 位置 | 時鐘 | 角度 | cx | cy |
|------|------|------|----|----|
| item-1 | 12點 | -90° | 960 | 140 |
| item-4 | 2點 | -30° | 1306 | 340 |
| item-5 | 4點 | 30° | 1306 | 740 |
| item-6 | 6點 | 90° | 960 | 940 |
| item-3 | 8點 | 150° | 614 | 740 |
| item-2 | 10點 | 210° | 614 | 340 |

---

## 族群 F：對比 / 分析（comparison / quadrant）

### F1 左右對比（split-comparison）

```html
<div class="slide" id="s{N}" style="background:{bg_css};">
  <!-- title [10,10,80,12] → left:192 top:108 w:1536 h:129.6；置中 -->
  <div class="el title" style="left:192px;top:108px;width:1536px;height:129.6px;
    text-align:center;font-size:{page-title}px;font-weight:700;">{title}</div>

  <!-- 中央分隔線（x=46%~54% 中間）→ left:883.2 top:324 w:1 h:648 -->
  <div class="el divider" style="left:883.2px;top:280.8px;width:2px;height:691.2px;
    background:{accent_color};opacity:.35;"></div>

  <!-- 左側 left-label [10,26,36,8] → left:192 top:280.8 w:691.2 h:86.4 -->
  <div class="el l-label" style="left:192px;top:280.8px;width:691.2px;height:86.4px;
    font-size:{comparison-label = max(44px, body + 6px)};font-weight:800;">{left_label}</div>
  <!-- left-content [10,36,36,52] → left:192 top:388.8 w:691.2 h:561.6 -->
  <div class="el l-content" style="left:192px;top:388.8px;width:691.2px;height:561.6px;
    font-size:{body}px;line-height:1.6;">{left_content}</div>

  <!-- 右側 right-label [54,26,36,8] → left:1036.8 top:280.8 w:691.2 h:86.4 -->
  <div class="el r-label" style="left:1036.8px;top:280.8px;width:691.2px;height:86.4px;
    font-size:{comparison-label = max(44px, body + 6px)};font-weight:800;">{right_label}</div>
  <!-- right-content [54,36,36,52] → left:1036.8 top:388.8 w:691.2 h:561.6 -->
  <div class="el r-content" style="left:1036.8px;top:388.8px;width:691.2px;height:561.6px;
    font-size:{body}px;line-height:1.6;">{right_content}</div>
</div>
```

`left_label`／`right_label` 若承載 Before／After、現況／目標、問題／解法等狀態語意，
屬於比較模組的第一層標題，不是 caption。兩側內容群組完成後，必須量測實際可見邊界，
再將整組水平、垂直置中於 Content Area。

### F1b 自由資訊圖像舞台（infographic-stage）

這個 Layout 只保留標題區與一個完整展示舞台，不規定雙區、欄數、模組數量、拓樸或
takeaway 位置。使用它的前提是 page-keyed content manifest 已帶有完整 Composition：
內容意圖、閱讀路徑、招牌構圖、普通網格會失去什麼，以及實際 scene objects。

- Layout 只擁有標題與舞台外框；scene 內幾何由每頁 Composition 擁有。
- 模組、文字、指標、connector、軸線與註解可依內容自由組合，不能由 renderer 補成固定模板。
- semantic module 預設整組選取，第一個 direct child 是 background layer；內層仍可 drill-in 編輯。
- connector 必須是可獨立選取的 loose object，並位於相關模組後方。
- Theme／Preset 只能改變色彩、材質、字體、陰影與線條語氣，不得改寫 scene geometry。

### F2 四象限矩陣（matrix-4quadrant / swot-quadrant）

矩陣用 SVG／CSS 畫軸，象限用 semantic module。`matrix` slot 是「軸標籤帶＋plot field」
的總範圍，不可把四個端點標籤直接壓進象限。renderer 必須先以正式字體量測四個獨立
axis label，再從總範圍扣除對應 label band，剩下的矩形才是 matrix frame 與四個象限。
Theme 可讓垂直端點標籤旋轉或水平排列，但不得把 axis_top／axis_bottom 合併成同一個文字物件。

```html
<div class="slide" id="s{N}" style="background:{bg_css};">
  <!-- title [10,5,80,12] → left:192 top:54 w:1536 h:129.6 -->
  <div class="el title" style="left:192px;top:54px;width:1536px;height:129.6px;
    text-align:center;font-size:{page-title}px;">{title}</div>

  <!-- 矩陣 SVG，matrix [12,22,76,68] → left:230 top:237 w:1459 h:734.4 -->
  <svg style="position:absolute;left:230.4px;top:237.6px;width:1459.2px;height:734.4px;"
    xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1459.2 734.4">
    <defs>
      <marker id="arr" markerUnits="userSpaceOnUse" markerWidth="18" markerHeight="18"
        viewBox="0 0 18 18" refX="16" refY="9" orient="auto-start-reverse">
        <path d="M2,2 L16,9 L2,16 Z" fill="{accent}"/>
      </marker>
    </defs>
    <!-- 水平軸 -->
    <line x1="0" y1="367.2" x2="1459.2" y2="367.2" stroke="{accent}" stroke-width="3"
      marker-start="url(#arr)" marker-end="url(#arr)"/>
    <!-- 垂直軸 -->
    <line x1="729.6" y1="0" x2="729.6" y2="734.4" stroke="{accent}" stroke-width="3"
      marker-start="url(#arr)" marker-end="url(#arr)"/>
    <!-- 軸標籤使用四個獨立 HTML edit objects，SVG 只畫 plot 與軸線。 -->
    <text x="729.6" y="24" text-anchor="middle" font-size="28" fill="{accent}">{axis_top}</text>
    <text x="729.6" y="724" text-anchor="middle" font-size="28" fill="{accent}">{axis_bot}</text>
    <text x="24" y="367.2" text-anchor="start" font-size="28" fill="{accent}">{axis_left}</text>
    <text x="1435" y="367.2" text-anchor="end" font-size="28" fill="{accent}">{axis_right}</text>
  </svg>

  <!-- 四個象限 div（overlay 在 SVG 上方）；座標相對於 slide -->
  <!-- quad_tl [13,24,33,24] → left:249.6 top:259.2 w:633.6 h:259.2 -->
  <div class="el quad" style="left:249.6px;top:259.2px;width:633.6px;height:259.2px;
    padding:24px;display:flex;align-items:center;">
    <span style="font-size:{module-title}px;font-weight:600;">{quad_tl_content}</span>
  </div>
  <!-- quad_tr [54,24,33,24] → left:1036.8 top:259.2 → hero_accent，字級大 2.5 倍 -->
  <div class="el quad hero-accent" style="left:1036.8px;top:259.2px;width:633.6px;height:259.2px;
    background:{accent_light};border-radius:8px;padding:24px;">
    <span style="font-size:{module-title×2.5 capped}px;font-weight:700;">{quad_tr}</span>
  </div>
  <!-- quad_bl / quad_br 同理 -->
</div>
```

`swot-quadrant` 與 `matrix-4quadrant` 結構相同，四個象限標籤改為 S/W/O/T。

Browser QA 必須以 glyph bounds 驗證四個 axis label 均落在各自 label band，且不與
任何 `.matrix-item`、matrix frame 或其他 axis label 相交。

---

## 族群 G：流程 / 時間軸

### G1 步驟流程（process-flow / flow-stages-3）

3–6 個節點的水平流程必須以實際節點數決定欄數，不得使用固定 4 欄導致第 5、6 個節點
自動換列。節點必須留在 `steps` region 同一列內，並與下方 `note` region 保持正間距。

流程連接器是 HTML renderer 的建構不變量，不是每份 deck 的人工 QA 項目：

- 短距離節點 gap 使用同一個 user-space `viewBox` 內的箭身與開放式 chevron，不使用 SVG marker。
- 若長距離或曲線連接器必須使用 marker，必須明確宣告 `markerUnits="userSpaceOnUse"`、
  `viewBox`、`refX` 與 `refY`；不得使用會隨 `stroke-width` 放大的預設 marker 單位。
- 箭頭頭部沿閱讀軸的長度最多占 gap 的 40%，至少保留 60% gap 作為可辨識箭身，
  且箭頭幾何不得超出 connector SVG 或侵入相鄰節點。

```html
<!-- steps [8,34,84,40] → left:153.6 top:367.2 w:1612.8 h:432 -->
<!-- 水平流程：N 個等寬節點 + 箭頭連接 -->
<div class="el steps-wrap" style="left:153.6px;top:367.2px;width:1612.8px;height:432px;
  display:flex;align-items:center;gap:0;">
  <!-- 每個 step node -->
  <div class="step-node" style="flex:1;height:320px;background:{card_bg};
    border-radius:16px;padding:36px 28px;box-sizing:border-box;position:relative;">
    <div style="font-size:72px;font-weight:900;color:{accent};opacity:.15;
      line-height:1;user-select:none;">{step_num}</div>
    <div style="font-size:{module-title}px;font-weight:600;margin-top:8px;">{step_title}</div>
    <div style="font-size:{body}px;margin-top:12px;opacity:.7;">{step_desc}</div>
  </div>
  <!-- 箭頭連接（兩節點之間） -->
  <div style="flex:0 0 56px;display:flex;align-items:center;justify-content:center;">
    <svg width="40" height="24" viewBox="0 0 40 24">
      <path d="M0,12 L32,12 M24,4 L32,12 L24,20" stroke="{accent}"
        stroke-width="2.5" fill="none" stroke-linecap="round"/>
    </svg>
  </div>
  <!-- 下一個 step node ... -->
</div>
```

### G2 里程碑時間軸（timeline-milestones）

此 Layout 使用置中的單一標題，不設副標 slot；時間軸模組不建立包覆式 Surface，
只保留軸線、節點、日期、里程碑標題與短註解。

```html
<!-- milestones [10,32,80,26] → left:192 top:345.6 w:1536 h:280.8 -->
<!-- 橫向時間線 + 菱形節點 -->
<svg style="position:absolute;left:192px;top:432px;width:1536px;height:194.4px;"
  xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1536 194.4">
  <!-- 主時間線 -->
  <line x1="0" y1="97.2" x2="1536" y2="97.2" stroke="{accent}" stroke-width="2.5"/>
  <!-- 節點菱形（N 個，等距） -->
  <!-- 每個節點：x = i/(N-1)*1536，上方日期，下方菱形，底部標題 -->
  <polygon points="256,77 276,97 256,117 236,97" fill="{accent}"/>
  <text x="256" y="56" text-anchor="middle" font-size="24" fill="{fg_muted}">{date}</text>
</svg>
<!-- milestone-notes [8,62,84,16] → left:153.6 top:669.6 w:1612.8 h:172.8 -->
<!-- 文字說明平均分佈，centerX 對齊對應節點 -->
<div class="el notes" style="left:153.6px;top:669.6px;width:1612.8px;height:172.8px;
  display:flex;align-items:flex-start;">
  <div style="flex:1;text-align:center;font-size:{body}px;">{note_1}</div>
  <div style="flex:1;text-align:center;font-size:{body}px;">{note_2}</div>
  ...
</div>
```

### G3 甘特圖（gantt-roadmap）

此版型複雜，建議用 `<table>` 或 SVG 繪製橫條，每行 = 一個任務：

```html
<div class="el gantt" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px; overflow:hidden;">
  <table style="width:100%;border-collapse:collapse;table-layout:fixed;">
    <tr>
      <td style="width:28%;padding:8px 16px;font-size:{body}px;">{task}</td>
      <td colspan="{N_cols}" style="position:relative;">
        <!-- 橫條 -->
        <div style="position:absolute;left:{start_col_pct}%;width:{duration_pct}%;
          height:28px;top:6px;background:{accent};border-radius:4px;"></div>
      </td>
    </tr>
  </table>
</div>
```

---

## 族群 H：數據 / 看板

### H1 KPI 指標卡（kpi-scorecards）

這個 Layout 只顯示主標，不輸出副標；scorecard surface 也不顯示順序編號。
每張 surface 內的 value、label、meaning 與 delta 必須沿用主標的水平對齊模式：
主標置中時，surface 內容也在各自卡片內置中。
下方 takeaway 為 optional；缺少時連 surface 一起省略。有內容時，去除空白後必須介於
18–44 個字元；少於 18 個字元的卡片註解不得當作整頁總結，大於 44 個字元則應精簡或改用其他 Layout。

若指標內容是短詞、狀態或原則，而不是需要大面積展示的長數字，scorecard surface 必須
使用 content-driven block size：value／label／meaning 先形成緊密文字群，卡片高度由該群組、
角色 content inset 與必要結構線推導。多張卡片再以可見 module union 垂直置中，不得以
`grid-template-rows:auto 1fr` 或 `space-between` 把稀疏文字推到卡片上下兩端。

```html
<!-- scorecards [8,34,84,34] → left:153.6 top:367.2 w:1612.8 h:367.2 -->
<!-- N 張等寬等高卡，3–6 張 -->
<div class="el scorecard-wrap" style="left:153.6px;top:367.2px;width:1612.8px;height:367.2px;
  display:flex;gap:24px;align-items:stretch;">
  <div class="sc-card" style="flex:1;background:#fff;border-radius:16px;
    padding:36px 32px;box-shadow:0 12px 32px rgba(0,0,0,.07);
    display:flex;flex-direction:column;justify-content:space-between;overflow:hidden;text-align:center;">
    <div style="font-size:{caption}px;font-weight:500;opacity:.55;">{metric_label}</div>
    <div style="font-size:{mega-number}px;font-weight:900;color:{accent};line-height:1;">
      {value}
    </div>
    <div style="font-size:{caption}px;color:{trend_color};">{trend} {change}</div>
  </div>
</div>
<!-- takeaway [8,74,84,12] → left:153.6 top:799.2 w:1612.8 h:129.6 -->
<div class="el takeaway" style="left:153.6px;top:799.2px;width:1612.8px;height:129.6px;
  font-size:{subtitle}px;opacity:.65;">{takeaway}</div>
```

---

## 族群 I：圖文（photo + text）

### I2 左框圖 + 右遮罩標題（photo-left-overlay-title-right）

```html
<!-- photo_left [4,3,48,94] → left:76.8 top:32.4 w:921.6 h:1015.2；白邊框 -->
<div class="el photo-l" style="left:76.8px;top:32.4px;width:921.6px;height:1015.2px;
  background:{placeholder};background-size:cover;background-position:center;
  outline:8px solid #fff;border-radius:4px;overflow:hidden;">
  <!-- placeholder 不加入 SVG、X 線、icon 或說明文字。 -->
</div>
<!-- title_overlay [55,27,40,28] → left:1056 top:291.6 w:768 h:302.4；遮罩色塊 -->
<div class="el title-ov" style="left:1056px;top:291.6px;width:768px;height:302.4px;
  background:rgba(0,0,0,.55);padding:32px 40px;box-sizing:border-box;border-radius:8px;">
  <div style="font-size:{section}px;font-weight:700;color:#fff;">{title}</div>
</div>
<!-- body [55,62,38,20] → left:1056 top:669.6 w:729.6 h:216 -->
<div class="el body" style="left:1056px;top:669.6px;width:729.6px;height:216px;
  font-size:{body}px;line-height:1.5;">{body}</div>
```

### I3 閉幕頁（closing-photo-overlay-contact）

```html
<div class="slide" id="s{N}">
  <!-- 全版底圖 -->
  <div class="el photo-full" style="left:0;top:0;width:1920px;height:1080px;
    background:{placeholder};background-size:cover;">
    <!-- placeholder 只使用純色或低對比漸層填滿既有 media slot。 -->
  </div>
  <!-- 左側文字遮罩 overlay [8,24,42,54] → left:153.6 top:259.2 w:806.4 h:583.2 -->
  <div class="el text-ov" style="left:153.6px;top:259.2px;width:806.4px;height:583.2px;
    background:rgba(0,0,0,.65);padding:48px 52px;box-sizing:border-box;border-radius:8px;">
    <div class="el closing-title" style="font-size:{section}px;font-weight:700;color:#fff;">
      {closing_title}
    </div>
    <div style="font-size:{body}px;color:rgba(255,255,255,.8);margin-top:24px;line-height:1.6;">
      {body}
    </div>
  </div>
  <!-- 右側社群圖示欄 social_icons [50,28,12,44] → left:960 top:302.4 w:230.4 h:475.2 -->
  <!-- icon zone [48,24,14,54] → left:921.6 top:259.2 w:268.8 h:583.2 -->
  <div class="el icon-ov" style="left:921.6px;top:259.2px;width:268.8px;height:583.2px;
    background:rgba(0,0,0,.5);padding:36px 24px;box-sizing:border-box;
    display:flex;flex-direction:column;align-items:center;gap:28px;border-radius:8px;">
    <!-- 每個社群 icon 圓形 -->
    <div style="width:64px;height:64px;border-radius:50%;background:{accent};
      display:flex;align-items:center;justify-content:center;">
      <!-- SVG icon 或文字 -->
    </div>
  </div>
</div>
```

---

## 照片 placeholder 規範（全局）

無法取得實際圖片時，保留 Layout 已宣告的媒體位置與尺寸，但只用純色或低對比漸層表示
「已填入」的區域：

- 不加入 SVG、X 線、icon、文字標籤或任何仿照片內容。
- placeholder 不改變 media slot 的幾何，也不新增可選取的裝飾物件。
- 真圖只有在使用者提供或明確要求、且該媒體是內容證據時才載入。

---

## 快速對照表

| 版型 ID | 族群 | 關鍵 HTML 技術 |
|---------|------|----------------|
| hero-fullbleed / hero-fullbleed-brand-footer | A1 | CSS gradient bg + text lower-left |
| cover-center-title-edge-decor | A2 | centered text + corner divs |
| cover-center-title-double-frame | A2b | centered text + double hairline frame |
| cover-photo-frame / reverse | A3 | photo div (40%) + text column |
| cover-photo-overlay-block | A4 | photo div + overlay div |
| title-center | B1 | flex center headline |
| quote-focus | B2 | large quote + decorative " |
| chapter-opener | C1 | accent rule lines + label + title |
| chapter-number-bg-left-title-rule | C2 | ghost number + left title |
| chapter-text-left-photo-brand | C3 | left text + right photo + brand overlay |
| chapter-fullbleed-overlay-title | C4 | full photo + right solid panel + title overlay |
| toc-3/4/5/6/8 | D1 | equal-width chapter cards |
| toc-*-vertical | D2 | flex row per chapter |
| toc-5-number-panel-left | D3 | left color panel + numbers + right rows |
| toc-3-panel-left | D4 | left panel div + 3 narrow cards |
| toc-*-panel-rows / grid | D5 | flex rows with border-bottom |
| cards-1-plus-N | E1 | equal cards + top accent bar |
| cycle-hub-6 | E2 | SVG ring + 6 circles + left/right text |
| split-comparison | F1 | two columns + center divider |
| infographic-stage | F1b | title band + page-authored open composition stage |
| matrix-4quadrant / swot-quadrant | F2 | SVG axes + 4 quad divs |
| process-flow / flow-stages-3 | G1 | flex steps + one independent `.el` SVG arrow per gap |
| timeline-milestones | G2 | SVG timeline + milestone notes |
| gantt-roadmap | G3 | table or SVG bars |
| kpi-scorecards | H1 | flex metric cards + mega number |
| photo-left-overlay-title-right | I2 | framed photo left + overlay right |
| closing-photo-overlay-contact | I3 | full photo + two overlay divs |
