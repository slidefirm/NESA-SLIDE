# Design Elements Library

這一層是從 `theme` 與 `layout` 中間抽出來的 reusable vocabulary。

目的不是取代 theme，也不是取代 layout，而是把常見的小型構件正式命名，方便：

- 圖片簡報 prompt 組裝
- HTML / PPTX renderer 對應
- 版型描述不再反覆手寫「小圓點、箭頭、節點卡、職稱膠囊」

## 這層負責什麼

- 小型結構件
- 連接件
- 標籤件
- 人物資訊件
- 節奏與導引件

## 這層不負責什麼

- 不定義整頁視覺世界觀：那是 `themes/`
- 不定義整頁版面骨架：那是 `layouts/`
- 不直接填內容欄位：那是每次組裝時的 dynamic content contract

## 目前檔案

- `observed_elements.catalog.yaml`
  - 根據 Beautiful.ai / Gamma / Slidesgo / 過往模板觀察整理出的 reusable element catalog

## 建議使用順序

1. 先選 `theme`
2. 再選 `layout`
3. 再由 layout / theme 決定需要哪些 `design_elements`
4. 最後把本次 dynamic content contract 的內容填進去

## 核心原則

- element 是 vocabulary，不是每次都必須全部使用
- element 的存在應該服務資訊理解，不是增加裝飾噪音
- 同一頁若已有大型插圖或主圖，應避免再堆疊過多 icon / micro-illustration
