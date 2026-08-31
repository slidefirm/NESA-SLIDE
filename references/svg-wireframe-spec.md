# SVG Wireframe 照片佔位符規範

## 核心原則

照片區域必須用「灰底 + X 對角線」表示，讓觀看者一眼區分「這裡是照片」vs「這裡是白底文字區」。
禁止用 ellipse、漸層、深淺灰色分區來模擬照片質感。

---

## 全版照片（Full-bleed）

整張投影片底色為照片，X 線從投影片四角畫到四角。

```svg
<!-- Step 1: 白色外框（固定） -->
<rect width="480" height="270" fill="#FFFFFF"/>
<rect x="1.5" y="1.5" width="477" height="267" rx="18" fill="#FFFFFF" stroke="#DCE2EA" stroke-width="2"/>

<!-- Step 2: 全版照片 X 佔位符 -->
<rect x="1.5" y="1.5" width="477" height="267" rx="18" fill="#EEF2F6"/>
<line x1="1.5"   y1="1.5"   x2="478.5" y2="268.5" stroke="#D3DAE4" stroke-width="1.2"/>
<line x1="478.5" y1="1.5"   x2="1.5"   y2="268.5" stroke="#D3DAE4" stroke-width="1.2"/>

<!-- Step 3: 內容層疊在 X 上方 -->
```

適用版型：`hero-fullbleed`、`hero-fullbleed-brand-footer`、`cover-photo-overlay-block`、
`chapter-fullbleed-overlay-title`、`closing-photo-overlay-contact`

---

## 半版照片（Half-page photo）

投影片底色保持白色，X 只畫在照片矩形內（X 線從照片矩形的四個角連線，不是投影片四角）。

```svg
<!-- Step 1: 白色外框（固定） -->
<rect width="480" height="270" fill="#FFFFFF"/>
<rect x="1.5" y="1.5" width="477" height="267" rx="18" fill="#FFFFFF" stroke="#DCE2EA" stroke-width="2"/>

<!-- Step 2: 半版照片 X 佔位符（右半為例：x=216, y=0, w=264, h=270） -->
<rect x="216" y="0" width="264" height="270" fill="#EEF2F6"/>
<line x1="216" y1="0"   x2="480" y2="270" stroke="#D3DAE4" stroke-width="1.2"/>
<line x1="480" y1="0"   x2="216" y2="270" stroke="#D3DAE4" stroke-width="1.2"/>

<!-- Step 3: 左側白底文字區，正常放元素 -->
```

適用版型：`cover-photo-frame`、`cover-photo-frame-reverse`、`chapter-text-left-photo-brand`、
`photo-left-overlay-title-right`

---

## 照片上的遮罩色塊（Overlay block）

半透明色塊疊在 X 圖層上方，表示 AI prompt 中的 overlay block 概念。

```svg
<rect x="24" y="32" width="250" height="175" fill="#C4B89A" rx="3" opacity="0.88"/>
```

- 顏色：`#C4B89A`（暖沙色，與 X 底色形成對比）
- 透明度：`0.82–0.90`（不要完全遮住 X，微微露出表示半透明）
- 位置與尺寸：對應 YAML 中的 `overlay_spec.region`

---

## 快速判斷表

| 情境 | X 範圍 | 投影片底色 |
|------|--------|-----------|
| 全幅照片 | 整張投影片 | `#EEF2F6` |
| 左半照片 | 左半矩形 | 白色 |
| 右半照片 | 右半矩形 | 白色 |
| 裱框照片（帶白邊） | 照片內框矩形 | 白色 |
| 無照片 | 不畫 X | 白色 |

---

## 顏色常數

| 用途 | 顏色值 |
|------|--------|
| 照片底色 | `#EEF2F6` |
| X 對角線 | `#D3DAE4` stroke-width 1.2 |
| 遮罩色塊 | `#C4B89A` |
| 文字佔位大標 | `#D2D9E3` / `#C9D0DA` |
| 文字佔位內文 | `#E0E6EE` / `#D4D9E0` |
| 投影片邊框 | `#DCE2EA` stroke-width 2 |
