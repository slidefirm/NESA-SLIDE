# Taxonomy Guide

這兩份 taxonomy 是新的 YAML 核心入口：

- `page_role.taxonomy.yaml`
- `content_pattern.taxonomy.yaml`

## 使用順序

1. 先判斷這頁在整份 deck 中扮演什麼角色：`page_role`
2. 再判斷這頁的內容骨架：`content_pattern`
3. 再根據兩者去選 `layout_strategy`
4. 最後才落到具體的 `layout_variant`

## 為什麼要拆兩層

- `page_role` 解決的是「這頁要完成什麼溝通任務」
- `content_pattern` 解決的是「這頁內容數量與關係長什麼樣」

例子：

- 同樣是 `1 + 3`，可以是 `speaker_intro`，也可以是 `takeaway`
- 同樣是 `chapter_opener`，其內容骨架通常是 `chapter-marker`

## 與 layout 的關係

這兩層都不是 layout。

- `page_role` 不是版型
- `content_pattern` 不是版型
- 它們只是幫你把版型選擇往前移到更穩定的語意層

這樣系統才不會永遠從「34 種模板卡片」反推。
