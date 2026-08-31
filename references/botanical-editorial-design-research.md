# Botanical Editorial Design Research

## 研究目的

避免月夜標本觀測誌繼續依賴手繪曲線、任意邊框與重複卡片，改用成熟國外植物機構品牌常見的編輯設計方法，並建立可追溯授權的素材來源。

## 主要參考

### Pentagram — New York Botanical Garden

- 來源：https://www.pentagram.com/work/new-york-botanical-garden
- 可轉用原則：
  - 以清楚 wordmark、強字級與 gallery-like whitespace 建立機構感。
  - 植物影像與字體互相配合，不把象徵性溫室圖案重複放到每一頁。
  - 插畫只用在必要的 Hero 或特殊應用，不作為通用邊框。

### Pentagram — Royal Botanic Gardens, Kew

- 來源：https://www.pentagram.com/work/the-royal-botanical-gardens-kew
- 可轉用原則：
  - 將歷史植物插畫重新裁切、放大與編排，而不是另畫裝飾線。
  - 以有歷史感的影像配合實用、清楚的文字系統，平衡 heritage 與 science。

### Pentagram — Garden Museum

- 來源：https://www.pentagram.com/work/garden-museum
- 可轉用原則：
  - 避免直接、字面化的花卉裝飾。
  - 自然形狀若要使用，應是少量、明確、可縮放的整體語彙，不是零散的曲線貼紙。

### BP&O — New York Botanical Garden identity review

- 來源：https://bpando.org/2024/02/22/new-york-botanical-garden-branding-2024-wolff-olins/
- 可轉用原則：
  - 植物題材不必只使用傳統綠色；可用一個高辨識 accent 建立 contemporary botanical character。
  - 字級、字重與圖像裁切要形成直接、明確的對比。

### Component Gallery

- 來源：https://component.gallery/
- 可轉用原則：
  - 卡片是有明確互動或資訊邊界的元件，不是所有內容的預設容器。
  - 比較、索引、時間序列可優先使用 row、rule、column 與 typographic hierarchy。

## 採用素材

### Matricaria chamomilla, Köhler's Medizinal-Pflanzen, Plate 64

- 來源：https://commons.wikimedia.org/wiki/File:K%C3%B6hler%27s_Medizinal-Pflanzen_in_naturgetreuen_Abbildungen_mit_kurz_erläuterndem_Texte_(Plate_64)_BHL303694.jpg
- 原始典藏：Biodiversity Heritage Library / Missouri Botanical Garden's Rare Books Collection
- 年代：1887
- 授權：Public domain、PD-old-70-expired、PD-scan
- 專案檔案：`prompt_system/renderers/html/assets/external/moonlit-herbarium-atlas/matricaria-chamomilla-koehler-plate-64.jpg`
- 使用方式：Hero 主圖、深色頁面漸隱圖版、內容頁單側低透明裁切。

## 已確立的設計準則

1. 裝飾線不得自行畫成藤蔓、弧線或任意括號；直線只用於分隔可比較資訊。
2. 邊緣設計優先使用有來源的成品圖版裁切，且每頁最多一側、低密度使用。
3. Hero 圖像視為可移動主體物件；低透明 edge crop 視為背景裝飾。
4. 卡片只在資訊真的需要獨立表面時使用；索引、四象限、時間序列與 metrics 優先採開放式 grid。
5. 一份簡報最多集中使用一到兩組來源一致的圖像，不混用風格不一致的素材庫。
6. 所有外部圖像必須記錄作者、來源、授權、在地檔案與修改方式。
7. 文字仍使用單一 `Noto Sans TC` 字族；標題與小標以字級、字重和色彩建立層次。
8. AI 生成文字維持 36px 下限，REVIEW 必須檢查孤字換行、對比、內容置中與圖像是否侵犯文字區。
