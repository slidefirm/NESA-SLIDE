# HTML editor source

`edit-mode.js` 是共用 HTML 編輯器的唯一原稿。請只修改這裡，不要直接修改
`artifacts/` 內的副本或已交付 HTML 中的內嵌版本。

修改後先同步本機相容副本：

```powershell
python scripts\sync_editor_asset.py --write
```

接著依 `html-pattern-slide` Skill，把新版本同步到本次交付範圍並執行 source-hash、
Browser 互動與下載重開 QA。歷史交付物保留原 hash，不做全庫批次覆寫。
