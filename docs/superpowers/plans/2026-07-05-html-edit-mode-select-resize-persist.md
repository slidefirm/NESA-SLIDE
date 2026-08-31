# HTML 編輯模式：圈選 + 拖曳縮放 + 存檔/版本回朔 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 `artifacts/html-test/edit-mode.js`（掛在所有本專案生成的 HTML 簡報上的共用編輯元件）支援「點擊圈選元素 → 顯示 8 個控制點 → 拖角落等比縮放 / 拖邊線單向縮放，字級跟著縮放」，並新增「存回原始 HTML 檔案」「版本回朔」「瀏覽器草稿自動存檔」，讓調整結果能真正被記錄下來，不會關掉分頁就消失。

**Architecture:** 新增一支本地小伺服器 `artifacts/html-test/dev_server.py`（取代 `.claude/launch.json` 裡的 `python -m http.server`），在原本純靜態檔案服務之外加三個 API（`/__save`、`/__history`、`/__revert`），存檔前一律先把舊內容備份成時間戳記快照。`edit-mode.js` 擴充選取狀態、拉伸控制點、字級縮放、異動記錄格式，並呼叫上述三個 API 完成存檔與回朔；另外用 `localStorage` 做防丟失的草稿自動存檔。所有變更集中在這兩個檔案，不新增 script 標籤、不改動個別簡報 HTML。

**Tech Stack:** 純 Python 標準庫（`http.server`、`json`、`shutil`、`pathlib`、`unittest`）＋純瀏覽器端 vanilla JS（無建置流程、無框架），跟專案既有慣例一致。

## Global Constraints

- 只擴充 `artifacts/html-test/edit-mode.js` 這一個共用檔案供所有簡報 HTML 引用；不新增 `<script>` 標籤、不修改個別簡報 HTML 檔案本身。
- `dev_server.py` 只能用 Python 標準庫，不新增任何套件依賴（不使用 pip 安裝任何東西）。
- 不做多選、不做長寬比鎖定開關（角落固定等比、邊線固定單方向）、不處理巢狀子元素各自縮放字級、不做拖曳時的即時規則檢查（不擋使用者把元素拖出安全框或字級範圍）。
- 存回原始 HTML 檔案 ≠ 寫回七段式 YAML 或 theme 檔 `layout_overrides`；這條限制維持不變，不在本次範圍內處理。
- 版本備份（`.history/` 目錄）不做自動清除或數量上限。
- 靜態檔案服務行為（port 7392、serve `artifacts/html-test` 目錄）必須跟現有 `python -m http.server` 完全等價，不能造成既有測試頁（`deck.html` 等）無法開啟。
- 沒有連上本地伺服器時（例如直接雙擊開 HTML 檔案），存檔／版本回朔要顯示提示訊息並靜默失敗，不能拋錯讓既有的「匯出新檔」「異動清單」功能跟著壞掉。

---

## Task 1: `dev_server.py` — 檔案存取核心邏輯（HtmlStore）

**Files:**
- Create: `artifacts/html-test/dev_server.py`
- Test: `artifacts/html-test/test_dev_server.py`

**Interfaces:**
- Produces: `class HtmlStore` in `dev_server.py`，建構子 `HtmlStore(serve_dir: pathlib.Path)`；方法 `safe_target_path(rel_path: str) -> Path`（非法路徑丟 `ValueError`）、`snapshot(target: Path) -> str`（回傳時間戳記字串）、`list_snapshots(name: str) -> list[str]`（新到舊排序）、`save(rel_path: str, html: str) -> str | None`（回傳這次存檔前建立的快照時間戳記，若原檔不存在則回傳 `None`）、`revert(rel_path: str, snapshot_ts: str) -> None`（找不到快照丟 `FileNotFoundError`）。

- [ ] **Step 1: 寫失敗的測試**

建立 `artifacts/html-test/test_dev_server.py`：

```python
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dev_server import HtmlStore


class HtmlStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = HtmlStore(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_safe_target_path_accepts_plain_filename(self):
        target = self.store.safe_target_path("deck.html")
        self.assertEqual(target, (self.tmp / "deck.html").resolve())

    def test_safe_target_path_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            self.store.safe_target_path("../outside.html")

    def test_safe_target_path_rejects_absolute_path(self):
        with self.assertRaises(ValueError):
            self.store.safe_target_path("/etc/passwd")

    def test_save_new_file_has_no_snapshot(self):
        snap = self.store.save("deck.html", "<html>v1</html>")
        self.assertIsNone(snap)
        self.assertEqual((self.tmp / "deck.html").read_text(encoding="utf-8"), "<html>v1</html>")

    def test_save_existing_file_creates_snapshot_of_old_content(self):
        (self.tmp / "deck.html").write_text("<html>v1</html>", encoding="utf-8")
        snap = self.store.save("deck.html", "<html>v2</html>")
        self.assertIsNotNone(snap)
        snapshots = self.store.list_snapshots("deck.html")
        self.assertEqual(snapshots, [snap])
        snap_path = self.tmp / ".history" / "deck.html" / (snap + ".html")
        self.assertEqual(snap_path.read_text(encoding="utf-8"), "<html>v1</html>")
        self.assertEqual((self.tmp / "deck.html").read_text(encoding="utf-8"), "<html>v2</html>")

    def test_list_snapshots_empty_when_none_exist(self):
        self.assertEqual(self.store.list_snapshots("nope.html"), [])

    def test_list_snapshots_newest_first(self):
        (self.tmp / "deck.html").write_text("<html>v1</html>", encoding="utf-8")
        snap1 = self.store.save("deck.html", "<html>v2</html>")
        snap2 = self.store.save("deck.html", "<html>v3</html>")
        self.assertEqual(self.store.list_snapshots("deck.html"), [snap2, snap1])

    def test_revert_restores_snapshot_and_backs_up_current(self):
        (self.tmp / "deck.html").write_text("<html>v1</html>", encoding="utf-8")
        snap1 = self.store.save("deck.html", "<html>v2</html>")
        self.store.revert("deck.html", snap1)
        self.assertEqual((self.tmp / "deck.html").read_text(encoding="utf-8"), "<html>v1</html>")
        snapshots = self.store.list_snapshots("deck.html")
        self.assertEqual(len(snapshots), 2)

    def test_revert_missing_snapshot_raises(self):
        (self.tmp / "deck.html").write_text("<html>v1</html>", encoding="utf-8")
        with self.assertRaises(FileNotFoundError):
            self.store.revert("deck.html", "does-not-exist")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試，確認因為 `dev_server.py` 還不存在而失敗**

Run: `python -m unittest artifacts/html-test/test_dev_server.py -v`
Expected: `ModuleNotFoundError: No module named 'dev_server'`（或 import 失敗）

- [ ] **Step 3: 實作 `HtmlStore`**

建立 `artifacts/html-test/dev_server.py`：

```python
#!/usr/bin/env python3
"""靜態檔案伺服器 + HTML 編輯模式的存檔／版本回朔 API（純標準庫）。"""
import http.server
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


class HtmlStore:
    """負責在 serve_dir 底下安全地讀寫 HTML 檔案，並管理 .history/ 快照。"""

    def __init__(self, serve_dir: Path):
        self.serve_dir = serve_dir.resolve()
        self.history_dir = self.serve_dir / ".history"

    def safe_target_path(self, rel_path: str) -> Path:
        if not rel_path or rel_path.startswith("/") or rel_path.startswith("\\"):
            raise ValueError("invalid path: " + repr(rel_path))
        if ".." in Path(rel_path).parts:
            raise ValueError("invalid path: " + repr(rel_path))
        target = (self.serve_dir / rel_path).resolve()
        if target != self.serve_dir and self.serve_dir not in target.parents:
            raise ValueError("invalid path: " + repr(rel_path))
        return target

    def snapshot(self, target: Path) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        dest_dir = self.history_dir / target.name
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(target, dest_dir / (ts + ".html"))
        return ts

    def list_snapshots(self, name: str):
        dest_dir = self.history_dir / name
        if not dest_dir.exists():
            return []
        return sorted((p.stem for p in dest_dir.glob("*.html")), reverse=True)

    def save(self, rel_path: str, html: str):
        target = self.safe_target_path(rel_path)
        snap = None
        if target.exists():
            snap = self.snapshot(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        return snap

    def revert(self, rel_path: str, snapshot_ts: str) -> None:
        target = self.safe_target_path(rel_path)
        src = self.history_dir / target.name / (snapshot_ts + ".html")
        if not src.exists():
            raise FileNotFoundError(snapshot_ts)
        if target.exists():
            self.snapshot(target)
        shutil.copyfile(src, target)


if __name__ == "__main__":
    pass
```

- [ ] **Step 4: 執行測試，確認全部通過**

Run: `python -m unittest artifacts/html-test/test_dev_server.py -v`
Expected: `OK`，7 個測試全部 PASS

- [ ] **Step 5: Commit**

```bash
git add artifacts/html-test/dev_server.py artifacts/html-test/test_dev_server.py
git commit -m "feat(html-test): add HtmlStore for HTML save/snapshot/revert"
```

---

## Task 2: `dev_server.py` — HTTP handler 與存檔／歷史／回朔 API

**Files:**
- Modify: `artifacts/html-test/dev_server.py`
- Test: `artifacts/html-test/test_dev_server.py`

**Interfaces:**
- Consumes: `HtmlStore`（Task 1）
- Produces: `make_handler(store: HtmlStore) -> type`，回傳一個 `http.server.BaseHTTPRequestHandler` 子類別；`__main__` 進入點接受 `sys.argv = [script, port, "--directory", dir]`。API 合約：
  - `POST /__save` body `{"path": str, "html": str}` → 200 `{"ok": true, "snapshot": str|null}`；非法路徑 → 400 `{"error": str}`
  - `GET /__history?path=<name>` → 200 `{"snapshots": [str, ...]}`
  - `POST /__revert` body `{"path": str, "snapshot": str}` → 200 `{"ok": true}`；快照不存在 → 404 `{"error": str}`

- [ ] **Step 1: 寫失敗的測試**

在 `artifacts/html-test/test_dev_server.py` 檔尾（`if __name__ == "__main__":` 之前）加入：

```python
import http.client
import json as json_module
import threading
import time

from dev_server import HtmlStore, make_handler


class HttpApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "index.html").write_text("<html>hello</html>", encoding="utf-8")
        self.store = HtmlStore(self.tmp)
        handler_cls = make_handler(self.store)
        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), handler_cls)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.05)

    def tearDown(self):
        self.httpd.shutdown()
        self.thread.join(timeout=2)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _request(self, method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        headers = {"Content-Type": "application/json"} if body is not None else {}
        payload = json_module.dumps(body).encode("utf-8") if body is not None else None
        conn.request(method, path, body=payload, headers=headers)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        parsed = json_module.loads(data) if data else None
        return res.status, parsed

    def test_static_file_still_served(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        conn.request("GET", "/index.html")
        res = conn.getresponse()
        body = res.read()
        conn.close()
        self.assertEqual(res.status, 200)
        self.assertIn(b"hello", body)

    def test_save_overwrites_and_returns_snapshot(self):
        status, data = self._request("POST", "/__save", {"path": "index.html", "html": "<html>v2</html>"})
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertIsNotNone(data["snapshot"])
        self.assertEqual((self.tmp / "index.html").read_text(encoding="utf-8"), "<html>v2</html>")

    def test_save_rejects_path_traversal(self):
        status, data = self._request("POST", "/__save", {"path": "../evil.html", "html": "x"})
        self.assertEqual(status, 400)
        self.assertIn("error", data)

    def test_history_lists_snapshots_after_save(self):
        self._request("POST", "/__save", {"path": "index.html", "html": "<html>v2</html>"})
        status, data = self._request("GET", "/__history?path=index.html")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["snapshots"]), 1)

    def test_revert_restores_previous_content(self):
        status, data = self._request("POST", "/__save", {"path": "index.html", "html": "<html>v2</html>"})
        snap = data["snapshot"]
        status, data = self._request("POST", "/__revert", {"path": "index.html", "snapshot": snap})
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertEqual((self.tmp / "index.html").read_text(encoding="utf-8"), "<html>hello</html>")
```

同時把檔案最上面的 import 區塊改成也 import `http.client`, `threading`, `time`（見上方程式碼已含 `import` 語句，直接貼在檔尾即可，Python 允許在檔案中段 import）。

- [ ] **Step 2: 執行測試，確認因為 `make_handler` 還不存在而失敗**

Run: `python -m unittest artifacts/html-test/test_dev_server.py -v`
Expected: `ImportError: cannot import name 'make_handler'`

- [ ] **Step 3: 實作 `make_handler` 與主程式進入點**

把 `artifacts/html-test/dev_server.py` 的 `if __name__ == "__main__": pass` 替換成：

```python
def make_handler(store: HtmlStore):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(store.serve_dir), **kwargs)

        def log_message(self, fmt, *args):
            pass

        def _json_response(self, code: int, obj: dict) -> None:
            data = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_json_body(self) -> dict:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            return json.loads(raw)

        def do_GET(self):
            if self.path.startswith("/__history"):
                self._handle_history()
            else:
                super().do_GET()

        def do_POST(self):
            if self.path == "/__save":
                self._handle_save()
            elif self.path == "/__revert":
                self._handle_revert()
            else:
                self._json_response(404, {"error": "not found"})

        def _handle_history(self):
            query = self.path.split("?", 1)[1] if "?" in self.path else ""
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            path = params.get("path", "")
            from urllib.parse import unquote
            name = Path(unquote(path)).name
            self._json_response(200, {"snapshots": store.list_snapshots(name)})

        def _handle_save(self):
            try:
                body = self._read_json_body()
                snap = store.save(body["path"], body["html"])
            except ValueError as err:
                self._json_response(400, {"error": str(err)})
                return
            self._json_response(200, {"ok": True, "snapshot": snap})

        def _handle_revert(self):
            try:
                body = self._read_json_body()
                store.revert(body["path"], body["snapshot"])
            except ValueError as err:
                self._json_response(400, {"error": str(err)})
                return
            except FileNotFoundError as err:
                self._json_response(404, {"error": "snapshot not found: " + str(err)})
                return
            self._json_response(200, {"ok": True})

    return Handler


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7392
    directory = Path(__file__).resolve().parent
    if "--directory" in sys.argv:
        idx = sys.argv.index("--directory")
        directory = Path(sys.argv[idx + 1]).resolve()
    store = HtmlStore(directory)
    handler_cls = make_handler(store)
    httpd = http.server.ThreadingHTTPServer(("", port), handler_cls)
    print("Serving {} at port {} (with /__save /__history /__revert)".format(directory, port))
    httpd.serve_forever()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 執行測試，確認全部通過**

Run: `python -m unittest artifacts/html-test/test_dev_server.py -v`
Expected: `OK`，12 個測試全部 PASS

- [ ] **Step 5: 手動起服務確認靜態檔案行為不變**

Run: `python artifacts/html-test/dev_server.py 7399 --directory artifacts/html-test`
再開一個終端機執行：`curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:7399/deck.html`
Expected: `200`。確認完後 `Ctrl+C` 關掉這個手動啟動的伺服器。

- [ ] **Step 6: Commit**

```bash
git add artifacts/html-test/dev_server.py artifacts/html-test/test_dev_server.py
git commit -m "feat(html-test): add /__save /__history /__revert endpoints to dev_server"
```

---

## Task 3: `.claude/launch.json` 改用 `dev_server.py`

**Files:**
- Modify: `.claude/launch.json`

**Interfaces:**
- Consumes: `artifacts/html-test/dev_server.py`（Task 2 已完成）

- [ ] **Step 1: 修改 html-test 設定**

把 `.claude/launch.json` 裡 `"name": "html-test"` 這個 configuration 的 `runtimeArgs` 從：

```json
"runtimeArgs": ["-m", "http.server", "7392", "--directory", "artifacts/html-test"]
```

改成：

```json
"runtimeArgs": ["artifacts/html-test/dev_server.py", "7392", "--directory", "artifacts/html-test"]
```

（`runtimeExecutable` 維持 `"python"` 不變，`port` 維持 `7392` 不變。）

- [ ] **Step 2: 驗證設定檔仍是合法 JSON**

Run: `python -c "import json; json.load(open('.claude/launch.json', encoding='utf-8-sig'))"`
Expected: 無輸出、無報錯（`utf-8-sig` 是因為這份檔案開頭有 BOM）

- [ ] **Step 3: Commit**

```bash
git add .claude/launch.json
git commit -m "chore(html-test): switch launch config to dev_server.py"
```

---

## Task 4: `edit-mode.js` — 選取模型

**Files:**
- Modify: `artifacts/html-test/edit-mode.js`

**Interfaces:**
- Produces: 模組層變數 `selectedEl`；函式 `selectElement(el: HTMLElement): void`、`deselectElement(): void`。後續 Task 5、6、7、8、9 都會用到 `selectedEl` 跟這兩個函式。

- [ ] **Step 1: 在既有 drag 狀態變數旁邊加入選取狀態**

用 Edit 工具，把：

```js
  let editMode = false;
  let dragEl = null, dragStartX = 0, dragStartY = 0, elStartLeft = 0, elStartTop = 0, dragScale = 1;
```

換成：

```js
  let editMode = false;
  let dragEl = null, dragStartX = 0, dragStartY = 0, elStartLeft = 0, elStartTop = 0, dragScale = 1;
  let selectedEl = null;
```

- [ ] **Step 2: 修改 `applyEditableState`，讓被選取的元素外框不一樣**

把：

```js
  function applyEditableState() {
    const active = document.querySelector('.slide.active');
    if (!active) return;
    active.querySelectorAll('.el').forEach((el) => {
      if (editMode) {
        el.style.outline = '1px dashed rgba(63,208,232,.55)';
        el.style.cursor = 'move';
        if (el.children.length === 0 || el.textContent.trim().length > 0) {
          el.setAttribute('contenteditable', 'true');
        }
      } else {
        el.style.outline = '';
        el.style.cursor = '';
        el.removeAttribute('contenteditable');
      }
    });
  }
```

換成：

```js
  function applyEditableState() {
    const active = document.querySelector('.slide.active');
    if (!active) return;
    active.querySelectorAll('.el').forEach((el) => {
      if (editMode) {
        el.style.outline = (el === selectedEl) ? '2px solid #3FD0E8' : '1px dashed rgba(63,208,232,.55)';
        el.style.cursor = 'move';
        if (el.children.length === 0 || el.textContent.trim().length > 0) {
          el.setAttribute('contenteditable', 'true');
        }
      } else {
        el.style.outline = '';
        el.style.cursor = '';
        el.removeAttribute('contenteditable');
      }
    });
  }

  function selectElement(el) {
    if (selectedEl === el) return;
    selectedEl = el;
    applyEditableState();
  }

  function deselectElement() {
    if (!selectedEl) return;
    selectedEl = null;
    applyEditableState();
  }
```

（`repositionHandles()` 會在 Task 5 加入 `selectElement`/`deselectElement` 裡，這一步先不引用它，避免現在就出現未定義的函式呼叫。）

- [ ] **Step 3: 讓 `toggleEditMode(false)` 時一併清掉選取**

把：

```js
  function toggleEditMode(force) {
    editMode = force === undefined ? !editMode : force;
    applyEditableState();
    readout.style.display = editMode ? 'block' : 'none';
    if (editMode) setReadout(HINT_TEXT);
    if (editBtn) editBtn.style.color = editMode ? '#3FD0E8' : '';
    if (exportBtn) exportBtn.style.opacity = editMode ? '1' : '.35';
    if (!editMode) changesPanel.style.display = 'none';
    document.dispatchEvent(new CustomEvent('editmodechange', { detail: { editMode } }));
  }
```

換成：

```js
  function toggleEditMode(force) {
    editMode = force === undefined ? !editMode : force;
    if (!editMode) selectedEl = null;
    applyEditableState();
    readout.style.display = editMode ? 'block' : 'none';
    if (editMode) setReadout(HINT_TEXT);
    if (editBtn) editBtn.style.color = editMode ? '#3FD0E8' : '';
    if (exportBtn) exportBtn.style.opacity = editMode ? '1' : '.35';
    if (!editMode) changesPanel.style.display = 'none';
    document.dispatchEvent(new CustomEvent('editmodechange', { detail: { editMode } }));
  }
```

- [ ] **Step 4: 加入「選取／取消選取」的 mousedown 監聽（跟既有拖曳 mousedown 是分開的兩個監聽器）**

在既有的拖曳 `mousedown` 監聽器（`document.addEventListener('mousedown', (e) => { if (!editMode) return; const el = e.target.closest('.el'); ...`）**之前**插入一段新的監聽器：

```js
  document.addEventListener('mousedown', (e) => {
    if (!editMode) return;
    const el = e.target.closest('.el');
    if (el) {
      selectElement(el);
    } else {
      deselectElement();
    }
  });

```

- [ ] **Step 5: 加入 Escape 取消選取的快捷鍵**

把：

```js
  window.addEventListener('keydown', (e) => {
    if (isTypingContext()) return;
    if (e.key === 'e' || e.key === 'E') toggleEditMode();
    if ((e.key === 'x' || e.key === 'X') && editMode) exportHtml();
    if ((e.key === 'r' || e.key === 'R') && editMode) toggleChangesPanel();
  });
```

換成：

```js
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && editMode) { deselectElement(); return; }
    if ((e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === ' ') && editMode) deselectElement();
    if (isTypingContext()) return;
    if (e.key === 'e' || e.key === 'E') toggleEditMode();
    if ((e.key === 'x' || e.key === 'X') && editMode) exportHtml();
    if ((e.key === 'r' || e.key === 'R') && editMode) toggleChangesPanel();
  });
```

- [ ] **Step 6: 瀏覽器手動驗證**

用 `preview_start` 確認 `html-test` 伺服器已啟動，開啟
`http://127.0.0.1:7392/deck.html`，用 `preview_eval` 執行：

```js
(() => {
  window.EditMode.toggle(true);
  const title = document.querySelector('.slide.active .el.title');
  title.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: 10, clientY: 10 }));
  window.dispatchEvent(new MouseEvent('mouseup'));
  const outline = title.style.outline;
  document.body.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: 5, clientY: 5 }));
  const outlineAfterDeselect = title.style.outline;
  return { outlineWhenSelected: outline, outlineAfterDeselect: outlineAfterDeselect };
})()
```

Expected: `outlineWhenSelected` 是 `"2px solid rgb(63, 208, 232)"`（或等效寫法），
`outlineAfterDeselect` 變回 `"1px dashed rgba(63, 208, 232, 0.55)"`。

- [ ] **Step 7: Commit**

```bash
git add artifacts/html-test/edit-mode.js
git commit -m "feat(edit-mode): add single-element selection state"
```

---

## Task 5: `edit-mode.js` — 拉伸控制點與縮放邏輯

**Files:**
- Modify: `artifacts/html-test/edit-mode.js`

**Interfaces:**
- Consumes: `selectedEl`、`selectElement`、`deselectElement`（Task 4）；`getScale()`、`originalPositions`、`elementLabel()`、`setReadout()`、`HINT_TEXT`（既有）
- Produces: `originalSizes`（WeakMap，供 Task 6/7 使用）、`repositionHandles(): void`、`recordChange(el: HTMLElement): void`（供 Task 4 的 move-drag 跟本 task 的 resize 共用，取代原本寫死在 mouseup 裡的重複邏輯）

- [ ] **Step 1: 加入 handles 覆蓋層與 resize 狀態變數**

在 `const originalPositions = new WeakMap();` 那一段旁邊，把：

```js
  const originalPositions = new WeakMap();
  const changedElements = new Set();
```

換成：

```js
  const originalPositions = new WeakMap();
  const originalSizes = new WeakMap();
  const changedElements = new Set();

  let resizeEl = null, resizeHandle = null, resizeScale = 1;
  let resizeStartX = 0, resizeStartY = 0;
  let resizeStartLeft = 0, resizeStartTop = 0, resizeStartW = 0, resizeStartH = 0;
  const MIN_SIZE = 20;

  const HANDLE_POSITIONS = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'];
  const HANDLE_CURSORS = {
    nw: 'nwse-resize', n: 'ns-resize', ne: 'nesw-resize', e: 'ew-resize',
    se: 'nwse-resize', s: 'ns-resize', sw: 'nesw-resize', w: 'ew-resize'
  };
  const HANDLE_SIZE = 10;
  const handles = {};
  HANDLE_POSITIONS.forEach((pos) => {
    const h = document.createElement('div');
    h.className = 'edit-resize-handle';
    h.dataset.handle = pos;
    h.style.cssText = 'position:fixed; width:' + HANDLE_SIZE + 'px; height:' + HANDLE_SIZE + 'px; ' +
      'background:#3FD0E8; border:1px solid #0B1220; border-radius:2px; z-index:102; ' +
      'display:none; cursor:' + HANDLE_CURSORS[pos] + ';';
    document.body.appendChild(h);
    handles[pos] = h;
  });

  function showHandles() { HANDLE_POSITIONS.forEach((p) => { handles[p].style.display = 'block'; }); }
  function hideHandles() { HANDLE_POSITIONS.forEach((p) => { handles[p].style.display = 'none'; }); }

  function repositionHandles() {
    if (!selectedEl) { hideHandles(); return; }
    const r = selectedEl.getBoundingClientRect();
    const half = HANDLE_SIZE / 2;
    const points = {
      nw: [r.left, r.top], n: [r.left + r.width / 2, r.top], ne: [r.right, r.top],
      e: [r.right, r.top + r.height / 2], se: [r.right, r.bottom], s: [r.left + r.width / 2, r.bottom],
      sw: [r.left, r.bottom], w: [r.left, r.top + r.height / 2]
    };
    HANDLE_POSITIONS.forEach((p) => {
      const xy = points[p];
      handles[p].style.left = (xy[0] - half) + 'px';
      handles[p].style.top = (xy[1] - half) + 'px';
    });
    showHandles();
  }
```

- [ ] **Step 2: 讓 `selectElement`/`deselectElement` 呼叫 `repositionHandles`/`hideHandles`**

把 Task 4 加入的：

```js
  function selectElement(el) {
    if (selectedEl === el) return;
    selectedEl = el;
    applyEditableState();
  }

  function deselectElement() {
    if (!selectedEl) return;
    selectedEl = null;
    applyEditableState();
  }
```

換成：

```js
  function selectElement(el) {
    if (selectedEl === el) return;
    selectedEl = el;
    applyEditableState();
    repositionHandles();
  }

  function deselectElement() {
    if (!selectedEl) return;
    selectedEl = null;
    applyEditableState();
    hideHandles();
  }
```

- [ ] **Step 3: 加入共用的 `recordChange`，並讓既有的 move-drag mouseup 改用它**

把既有的：

```js
  window.addEventListener('mouseup', () => {
    if (dragEl) {
      const orig = originalPositions.get(dragEl);
      const curLeft = parseFloat(dragEl.style.left) || 0;
      const curTop = parseFloat(dragEl.style.top) || 0;
      if (orig && (Math.abs(curLeft - orig.left) > 0.5 || Math.abs(curTop - orig.top) > 0.5)) {
        changedElements.add(dragEl);
      } else {
        changedElements.delete(dragEl); // 拖回原位就不算異動
      }
      if (changesBtn) changesBtn.style.opacity = changedElements.size ? '1' : '.35';
      setReadout(HINT_TEXT);
    }
    dragEl = null;
  });
```

換成：

```js
  const textDirty = new WeakSet();

  function recordChange(el) {
    const origPos = originalPositions.get(el);
    const origSize = originalSizes.get(el);
    const curLeft = parseFloat(el.style.left) || 0;
    const curTop = parseFloat(el.style.top) || 0;
    const curW = parseFloat(el.style.width) || 0;
    const curH = parseFloat(el.style.height) || 0;
    const posChanged = !!origPos && (Math.abs(curLeft - origPos.left) > 0.5 || Math.abs(curTop - origPos.top) > 0.5);
    const sizeChanged = !!origSize && (Math.abs(curW - origSize.width) > 0.5 || Math.abs(curH - origSize.height) > 0.5);
    if (posChanged || sizeChanged || textDirty.has(el)) {
      changedElements.add(el);
    } else {
      changedElements.delete(el); // 拖回/縮回原狀就不算異動
    }
    if (changesBtn) changesBtn.style.opacity = changedElements.size ? '1' : '.35';
  }

  window.addEventListener('mouseup', () => {
    if (dragEl) {
      recordChange(dragEl);
      setReadout(HINT_TEXT);
    }
    dragEl = null;
  });
```

- [ ] **Step 4: 讓 move-drag 拖曳時控制點跟著移動**

把既有 move-drag 的 `mousemove` 監聽器：

```js
  window.addEventListener('mousemove', (e) => {
    if (!editMode || !dragEl) return;
    const dx = (e.clientX - dragStartX) / dragScale;
    const dy = (e.clientY - dragStartY) / dragScale;
    const newLeft = Math.round(elStartLeft + dx);
    const newTop = Math.round(elStartTop + dy);
    dragEl.style.left = newLeft + 'px';
    dragEl.style.top = newTop + 'px';
    const label = dragEl.className.replace('el', '').trim() || dragEl.tagName.toLowerCase();
    setReadout(label + '\nleft: ' + newLeft + 'px\ntop:  ' + newTop + 'px');
  });
```

換成：

```js
  window.addEventListener('mousemove', (e) => {
    if (!editMode || !dragEl) return;
    const dx = (e.clientX - dragStartX) / dragScale;
    const dy = (e.clientY - dragStartY) / dragScale;
    const newLeft = Math.round(elStartLeft + dx);
    const newTop = Math.round(elStartTop + dy);
    dragEl.style.left = newLeft + 'px';
    dragEl.style.top = newTop + 'px';
    const label = dragEl.className.replace('el', '').trim() || dragEl.tagName.toLowerCase();
    setReadout(label + '\nleft: ' + newLeft + 'px\ntop:  ' + newTop + 'px');
    if (dragEl === selectedEl) repositionHandles();
  });
```

- [ ] **Step 5: 加入 resize 的拖曳邏輯與控制點的 mousedown 監聽**

在 `recordChange` 函式後面（`window.addEventListener('mouseup', ...)` 那個 move-drag 區塊之後）插入：

```js
  function startResize(handlePos, el, e) {
    e.preventDefault();
    e.stopPropagation();
    resizeEl = el;
    resizeHandle = handlePos;
    resizeScale = getScale();
    const stageRect = stage.getBoundingClientRect();
    const elRect = el.getBoundingClientRect();
    resizeStartLeft = Math.round((elRect.left - stageRect.left) / resizeScale);
    resizeStartTop = Math.round((elRect.top - stageRect.top) / resizeScale);
    resizeStartW = Math.round(elRect.width / resizeScale);
    resizeStartH = Math.round(elRect.height / resizeScale);
    resizeStartX = e.clientX;
    resizeStartY = e.clientY;
    if (!originalPositions.has(el)) {
      originalPositions.set(el, { left: resizeStartLeft, top: resizeStartTop });
    }
    if (!originalSizes.has(el)) {
      const fontPx = parseFloat(getComputedStyle(el).fontSize) || 0;
      originalSizes.set(el, { width: resizeStartW, height: resizeStartH, fontSize: fontPx });
    }
  }

  HANDLE_POSITIONS.forEach((pos) => {
    handles[pos].addEventListener('mousedown', (e) => {
      if (!editMode || !selectedEl) return;
      startResize(pos, selectedEl, e);
    });
  });

  function applyFontScale(el, handlePos, newW, newH) {
    const orig = originalSizes.get(el);
    if (!orig || !orig.fontSize) return;
    const isCorner = handlePos.length === 2;
    let scale;
    if (isCorner) {
      scale = newW / orig.width;
    } else if (handlePos === 'e' || handlePos === 'w') {
      scale = newW / orig.width;
    } else {
      scale = newH / orig.height;
    }
    el.style.fontSize = Math.max(1, orig.fontSize * scale).toFixed(1) + 'px';
  }

  window.addEventListener('mousemove', (e) => {
    if (!editMode || !resizeEl) return;
    const dx = (e.clientX - resizeStartX) / resizeScale;
    const dy = (e.clientY - resizeStartY) / resizeScale;
    let newLeft = resizeStartLeft, newTop = resizeStartTop;
    let newW = resizeStartW, newH = resizeStartH;
    const isCorner = resizeHandle.length === 2;
    if (isCorner) {
      const proposedW = resizeStartW + (resizeHandle.indexOf('e') >= 0 ? dx : (resizeHandle.indexOf('w') >= 0 ? -dx : 0));
      const proposedH = resizeStartH + (resizeHandle.indexOf('s') >= 0 ? dy : (resizeHandle.indexOf('n') >= 0 ? -dy : 0));
      const scaleW = proposedW / resizeStartW;
      const scaleH = proposedH / resizeStartH;
      const scale = Math.abs(scaleW - 1) >= Math.abs(scaleH - 1) ? scaleW : scaleH;
      newW = Math.max(MIN_SIZE, Math.round(resizeStartW * scale));
      newH = Math.max(MIN_SIZE, Math.round(resizeStartH * scale));
      if (resizeHandle.indexOf('w') >= 0) newLeft = Math.round(resizeStartLeft + (resizeStartW - newW));
      if (resizeHandle.indexOf('n') >= 0) newTop = Math.round(resizeStartTop + (resizeStartH - newH));
    } else {
      if (resizeHandle === 'e') { newW = Math.max(MIN_SIZE, Math.round(resizeStartW + dx)); }
      if (resizeHandle === 'w') {
        newW = Math.max(MIN_SIZE, Math.round(resizeStartW - dx));
        newLeft = Math.round(resizeStartLeft + (resizeStartW - newW));
      }
      if (resizeHandle === 's') { newH = Math.max(MIN_SIZE, Math.round(resizeStartH + dy)); }
      if (resizeHandle === 'n') {
        newH = Math.max(MIN_SIZE, Math.round(resizeStartH - dy));
        newTop = Math.round(resizeStartTop + (resizeStartH - newH));
      }
    }
    resizeEl.style.left = newLeft + 'px';
    resizeEl.style.top = newTop + 'px';
    resizeEl.style.width = newW + 'px';
    resizeEl.style.height = newH + 'px';
    applyFontScale(resizeEl, resizeHandle, newW, newH);
    repositionHandles();
    setReadout(elementLabel(resizeEl) + '\nwidth:  ' + newW + 'px\nheight: ' + newH + 'px');
  });

  window.addEventListener('mouseup', () => {
    if (resizeEl) {
      recordChange(resizeEl);
      setReadout(HINT_TEXT);
      resizeEl = null;
      resizeHandle = null;
    }
  });

  window.addEventListener('resize', () => { if (selectedEl) repositionHandles(); });
```

- [ ] **Step 6: 瀏覽器手動驗證 — 角落等比縮放**

用 `preview_eval` 執行（延續 Task 4 驗證用的同一個 `deck.html`）：

```js
(() => {
  window.EditMode.toggle(true);
  const title = document.querySelector('.slide.active .el.title');
  title.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: 10, clientY: 10 }));
  window.dispatchEvent(new MouseEvent('mouseup'));
  const before = title.getBoundingClientRect();
  const seHandle = document.querySelector('.edit-resize-handle[data-handle="se"]');
  const handleRect = seHandle.getBoundingClientRect();
  seHandle.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: handleRect.left, clientY: handleRect.top }));
  window.dispatchEvent(new MouseEvent('mousemove', { clientX: handleRect.left + 100, clientY: handleRect.top + 50 }));
  const widthDuringDrag = title.style.width;
  const heightDuringDrag = title.style.height;
  window.dispatchEvent(new MouseEvent('mouseup'));
  return { widthDuringDrag: widthDuringDrag, heightDuringDrag: heightDuringDrag, fontSizeAfter: title.style.fontSize };
})()
```

Expected: `widthDuringDrag`/`heightDuringDrag` 都比原尺寸大（角落拖曳同步放大寬跟高），
`fontSizeAfter` 不是空字串，且數值比原本的 computed font-size 大（等比放大）。

- [ ] **Step 7: 瀏覽器手動驗證 — 邊線單向縮放**

```js
(() => {
  const title = document.querySelector('.slide.active .el.title');
  const beforeH = title.style.height;
  const eHandle = document.querySelector('.edit-resize-handle[data-handle="e"]');
  const handleRect = eHandle.getBoundingClientRect();
  eHandle.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: handleRect.left, clientY: handleRect.top }));
  window.dispatchEvent(new MouseEvent('mousemove', { clientX: handleRect.left + 80, clientY: handleRect.top }));
  const widthDuringDrag = title.style.width;
  const heightDuringDrag = title.style.height;
  window.dispatchEvent(new MouseEvent('mouseup'));
  return { heightUnchanged: heightDuringDrag === beforeH, widthChanged: widthDuringDrag !== beforeH };
})()
```

Expected: `heightUnchanged: true`（只拖 e 控制點，高度不變）。

- [ ] **Step 8: Commit**

```bash
git add artifacts/html-test/edit-mode.js
git commit -m "feat(edit-mode): add corner/edge resize handles with font-size scaling"
```

---

## Task 6: `edit-mode.js` — 異動清單擴充 width/height/font-size

**Files:**
- Modify: `artifacts/html-test/edit-mode.js`

**Interfaces:**
- Consumes: `originalPositions`、`originalSizes`（Task 5）、`changedElements`、`elementLabel()`（既有）

- [ ] **Step 1: 改寫 `buildChangesText`**

把：

```js
  function buildChangesText() {
    if (changedElements.size === 0) return '（目前沒有元素被移動過）';
    const lines = [];
    changedElements.forEach((el) => {
      const orig = originalPositions.get(el);
      const curLeft = Math.round(parseFloat(el.style.left) || 0);
      const curTop = Math.round(parseFloat(el.style.top) || 0);
      lines.push(elementLabel(el) + '：left ' + orig.left + 'px→' + curLeft + 'px' +
        '，top ' + orig.top + 'px→' + curTop + 'px' +
        '（Δx=' + (curLeft - orig.left) + ', Δy=' + (curTop - orig.top) + '）');
    });
    return lines.join('\n');
  }
```

換成：

```js
  function buildChangesText() {
    if (changedElements.size === 0) return '（目前沒有元素被移動過）';
    const lines = [];
    changedElements.forEach((el) => {
      const origPos = originalPositions.get(el);
      const origSize = originalSizes.get(el);
      const parts = [elementLabel(el)];
      if (origPos) {
        const curLeft = Math.round(parseFloat(el.style.left) || 0);
        const curTop = Math.round(parseFloat(el.style.top) || 0);
        parts.push('left ' + origPos.left + 'px→' + curLeft + 'px');
        parts.push('top ' + origPos.top + 'px→' + curTop + 'px');
      }
      if (origSize) {
        const curW = Math.round(parseFloat(el.style.width) || origSize.width);
        const curH = Math.round(parseFloat(el.style.height) || origSize.height);
        const curFont = Math.round(parseFloat(el.style.fontSize) || origSize.fontSize);
        parts.push('width ' + origSize.width + 'px→' + curW + 'px');
        parts.push('height ' + origSize.height + 'px→' + curH + 'px');
        parts.push('font-size ' + Math.round(origSize.fontSize) + 'px→' + curFont + 'px');
      }
      if (!origPos && !origSize) parts.push('文字已修改');
      lines.push(parts.join('，'));
    });
    return lines.join('\n');
  }
```

- [ ] **Step 2: 瀏覽器手動驗證**

延續 Task 5 驗證用的頁面（已經對 title 做過一次角落縮放），用 `preview_eval` 執行：

```js
window.EditMode.showChanges(true);
document.getElementById('edit-changes-panel').innerText
```

Expected: 輸出的文字裡包含 `width`、`height`、`font-size` 三個欄位，且箭頭前後數字不同（反映 Task 5 驗證步驟做過的縮放）。

- [ ] **Step 3: Commit**

```bash
git add artifacts/html-test/edit-mode.js
git commit -m "feat(edit-mode): include width/height/font-size in change list"
```

---

## Task 7: `edit-mode.js` — 元素識別鍵（給存檔/草稿用）

**Files:**
- Modify: `artifacts/html-test/edit-mode.js`

**Interfaces:**
- Produces: `elementKey(el: HTMLElement): string | null`（格式 `"<slideId>::<index>"`）、`elementByKey(key: string): HTMLElement | null`。供 Task 9 使用。

- [ ] **Step 1: 加入識別鍵函式**

在 `buildChangesText` 函式後面（`toggleChangesPanel` 之前）插入：

```js
  function elementKey(el) {
    const slide = el.closest('.slide');
    if (!slide || !slide.id) return null;
    const els = slide.querySelectorAll('.el');
    const idx = Array.prototype.indexOf.call(els, el);
    if (idx < 0) return null;
    return slide.id + '::' + idx;
  }

  function elementByKey(key) {
    const parts = key.split('::');
    const slideId = parts[0];
    const idx = parseInt(parts[1], 10);
    const slide = document.getElementById(slideId);
    if (!slide) return null;
    const els = slide.querySelectorAll('.el');
    return els[idx] || null;
  }
```

- [ ] **Step 2: 瀏覽器手動驗證**

`elementKey`/`elementByKey` 是模組內部函式（刻意不掛到 `window.EditMode`，只給
Task 9 的草稿功能內部呼叫），用等效邏輯手動驗證 round-trip 是否正確：

```js
(() => {
  const slide = document.querySelector('.slide.active');
  const title = slide.querySelector('.el.title');
  const els = slide.querySelectorAll('.el');
  const idx = Array.prototype.indexOf.call(els, title);
  const key = slide.id + '::' + idx;
  const parts = key.split('::');
  const found = document.getElementById(parts[0]).querySelectorAll('.el')[parseInt(parts[1], 10)];
  return { key: key, roundTripMatches: found === title };
})()
```

Expected: `roundTripMatches: true`。

- [ ] **Step 3: Commit**

```bash
git add artifacts/html-test/edit-mode.js
git commit -m "feat(edit-mode): add slide+index identity key helpers"
```

---

## Task 8: `edit-mode.js` — 存檔與版本回朔 UI

**Files:**
- Modify: `artifacts/html-test/edit-mode.js`

**Interfaces:**
- Consumes: `/__save`、`/__history`、`/__revert`（Task 2 的 API 合約）
- Produces: `saveToServer(): Promise<object|null>`、`toggleHistoryPanel(force?: boolean): Promise<void>`，掛在 `window.EditMode.save` / `window.EditMode.showHistory`

- [ ] **Step 1: 加入 `sanitizedHtml`／`currentFilePath`／`saveToServer`**

在 `exportHtml` 函式後面插入：

```js
  function sanitizedClone() {
    const clone = document.documentElement.cloneNode(true);
    clone.querySelectorAll('.el').forEach((el) => {
      el.removeAttribute('contenteditable');
      el.style.outline = '';
      el.style.cursor = '';
    });
    ['#edit-readout', '#edit-changes-panel', '#edit-history-panel', '#edit-draft-prompt'].forEach((sel) => {
      const n = clone.querySelector(sel);
      if (n) n.remove();
    });
    clone.querySelectorAll('.edit-resize-handle').forEach((n) => n.remove());
    return clone;
  }

  function currentFilePath() {
    return location.pathname.split('/').pop() || 'index.html';
  }

  async function saveToServer() {
    const path = currentFilePath();
    const html = '<!DOCTYPE html>\n' + sanitizedClone().outerHTML;
    try {
      const res = await fetch('/__save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: path, html: html })
      });
      if (!res.ok) throw new Error('save failed');
      const data = await res.json();
      clearDraft();
      setReadout('已儲存 ' + new Date().toLocaleTimeString());
      setTimeout(() => setReadout(editMode ? HINT_TEXT : ''), 1500);
      return data;
    } catch (err) {
      setReadout('未偵測到本地伺服器，無法儲存');
      setTimeout(() => setReadout(editMode ? HINT_TEXT : ''), 1500);
      return null;
    }
  }
```

- [ ] **Step 2: 讓既有的 `exportHtml` 重用 `sanitizedClone`（去重複）**

把：

```js
  function exportHtml() {
    const clone = document.documentElement.cloneNode(true);
    clone.querySelectorAll('.el').forEach((el) => {
      el.removeAttribute('contenteditable');
      el.style.outline = '';
      el.style.cursor = '';
    });
    const staleReadout = clone.querySelector('#edit-readout');
    if (staleReadout) staleReadout.remove();
    const html = '<!DOCTYPE html>\n' + clone.outerHTML;
    const blob = new Blob([html], { type: 'text/html' });
```

換成：

```js
  function exportHtml() {
    const html = '<!DOCTYPE html>\n' + sanitizedClone().outerHTML;
    const blob = new Blob([html], { type: 'text/html' });
```

- [ ] **Step 3: 加入歷史版本面板與 `toggleHistoryPanel`**

在 `saveToServer` 函式後面插入：

```js
  const historyPanel = document.createElement('div');
  historyPanel.id = 'edit-history-panel';
  historyPanel.style.cssText = 'position:fixed; right:16px; top:16px; z-index:101; ' +
    'background:rgba(10,14,20,.95); color:#E6EAF0; font:12px/1.6 ui-monospace,"SF Mono",Menlo,monospace; ' +
    'padding:14px 16px; border-radius:8px; display:none; max-width:420px; max-height:70vh; overflow:auto; ' +
    'border:1px solid rgba(63,208,232,.3); box-shadow:0 12px 32px rgba(0,0,0,.5);';
  document.body.appendChild(historyPanel);

  async function toggleHistoryPanel(force) {
    const show = force === undefined ? historyPanel.style.display === 'none' : force;
    if (!show) { historyPanel.style.display = 'none'; return; }
    historyPanel.innerHTML = '';
    const title = document.createElement('div');
    title.textContent = '歷史版本';
    title.style.cssText = 'font-weight:700; margin-bottom:8px; color:#3FD0E8;';
    historyPanel.appendChild(title);
    const path = currentFilePath();
    let snapshots = [];
    try {
      const res = await fetch('/__history?path=' + encodeURIComponent(path));
      if (!res.ok) throw new Error('history failed');
      const data = await res.json();
      snapshots = data.snapshots || [];
    } catch (err) {
      const msg = document.createElement('div');
      msg.textContent = '未偵測到本地伺服器，無法讀取版本紀錄';
      historyPanel.appendChild(msg);
      historyPanel.style.display = 'block';
      return;
    }
    if (snapshots.length === 0) {
      const msg = document.createElement('div');
      msg.textContent = '（目前沒有任何存檔快照）';
      historyPanel.appendChild(msg);
    } else {
      snapshots.forEach((ts) => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex; justify-content:space-between; align-items:center; gap:12px; padding:4px 0;';
        const label = document.createElement('span');
        label.textContent = ts;
        const revertBtn = document.createElement('button');
        revertBtn.textContent = '還原';
        revertBtn.style.cssText = 'background:#3FD0E8; color:#0B1220; border:0; border-radius:6px; ' +
          'padding:4px 10px; font:12px ui-monospace,monospace; font-weight:700; cursor:pointer;';
        revertBtn.onclick = async () => {
          if (!confirm('確定要還原到 ' + ts + ' 這個版本嗎？目前狀態會先自動存檔備份。')) return;
          try {
            const res = await fetch('/__revert', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ path: path, snapshot: ts })
            });
            if (!res.ok) throw new Error('revert failed');
            location.reload();
          } catch (err) {
            alert('還原失敗：未偵測到本地伺服器');
          }
        };
        row.append(label, revertBtn);
        historyPanel.appendChild(row);
      });
    }
    historyPanel.style.display = 'block';
  }
```

- [ ] **Step 4: 加入 Ctrl/Cmd+S、H 快捷鍵**

把 Task 4 修改過的 keydown 監聽器：

```js
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && editMode) { deselectElement(); return; }
    if ((e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === ' ') && editMode) deselectElement();
    if (isTypingContext()) return;
    if (e.key === 'e' || e.key === 'E') toggleEditMode();
    if ((e.key === 'x' || e.key === 'X') && editMode) exportHtml();
    if ((e.key === 'r' || e.key === 'R') && editMode) toggleChangesPanel();
  });
```

換成：

```js
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && editMode) { deselectElement(); return; }
    if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
      if (editMode) { e.preventDefault(); saveToServer(); }
      return;
    }
    if ((e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === ' ') && editMode) deselectElement();
    if (isTypingContext()) return;
    if (e.key === 'e' || e.key === 'E') toggleEditMode();
    if ((e.key === 'x' || e.key === 'X') && editMode) exportHtml();
    if ((e.key === 'r' || e.key === 'R') && editMode) toggleChangesPanel();
    if ((e.key === 'h' || e.key === 'H') && editMode) toggleHistoryPanel();
  });
```

- [ ] **Step 5: 加入工具列按鈕，並擴充 `window.EditMode`**

先把按鈕變數宣告（`let editBtn = null, exportBtn = null, changesBtn = null;`）
改成也宣告 save/history 按鈕變數：

```js
  let editBtn = null, exportBtn = null, changesBtn = null, saveBtn = null, historyBtn = null;
```

再把：

```js
  editBtn = makeBtn(ICON_EDIT, '編輯模式 (E)', () => toggleEditMode());
  exportBtn = makeBtn(ICON_EXPORT, '匯出調整後 HTML (X)', () => { if (editMode) exportHtml(); });
  changesBtn = makeBtn(ICON_CHANGES, '座標異動清單 (R)', () => { if (editMode) toggleChangesPanel(); });
  exportBtn.style.opacity = '.35';
  changesBtn.style.opacity = '.35';
  barInner.append(makeDivider(), editBtn, exportBtn, changesBtn);

  window.EditMode = { toggle: toggleEditMode, export: exportHtml, showChanges: toggleChangesPanel };
})();
```

換成：

```js
  const ICON_SAVE = '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>';
  const ICON_HISTORY = '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>';

  editBtn = makeBtn(ICON_EDIT, '編輯模式 (E)', () => toggleEditMode());
  exportBtn = makeBtn(ICON_EXPORT, '匯出調整後 HTML (X)', () => { if (editMode) exportHtml(); });
  changesBtn = makeBtn(ICON_CHANGES, '座標異動清單 (R)', () => { if (editMode) toggleChangesPanel(); });
  saveBtn = makeBtn(ICON_SAVE, '儲存 (Ctrl+S)', () => { if (editMode) saveToServer(); });
  historyBtn = makeBtn(ICON_HISTORY, '歷史版本 (H)', () => { if (editMode) toggleHistoryPanel(); });
  exportBtn.style.opacity = '.35';
  changesBtn.style.opacity = '.35';
  saveBtn.style.opacity = '.35';
  historyBtn.style.opacity = '.35';
  barInner.append(makeDivider(), editBtn, exportBtn, changesBtn, saveBtn, historyBtn);

  window.EditMode = {
    toggle: toggleEditMode,
    export: exportHtml,
    showChanges: toggleChangesPanel,
    save: saveToServer,
    showHistory: toggleHistoryPanel
  };
})();
```

再把 Task 4 Step 3 修改過的 `toggleEditMode`：

```js
  function toggleEditMode(force) {
    editMode = force === undefined ? !editMode : force;
    if (!editMode) selectedEl = null;
    applyEditableState();
    readout.style.display = editMode ? 'block' : 'none';
    if (editMode) setReadout(HINT_TEXT);
    if (editBtn) editBtn.style.color = editMode ? '#3FD0E8' : '';
    if (exportBtn) exportBtn.style.opacity = editMode ? '1' : '.35';
    if (!editMode) changesPanel.style.display = 'none';
    document.dispatchEvent(new CustomEvent('editmodechange', { detail: { editMode } }));
  }
```

換成：

```js
  function toggleEditMode(force) {
    editMode = force === undefined ? !editMode : force;
    if (!editMode) { selectedEl = null; hideHandles(); }
    applyEditableState();
    readout.style.display = editMode ? 'block' : 'none';
    if (editMode) setReadout(HINT_TEXT);
    if (editBtn) editBtn.style.color = editMode ? '#3FD0E8' : '';
    if (exportBtn) exportBtn.style.opacity = editMode ? '1' : '.35';
    if (changesBtn) changesBtn.style.opacity = (editMode && changedElements.size) ? '1' : '.35';
    if (saveBtn) saveBtn.style.opacity = editMode ? '1' : '.35';
    if (historyBtn) historyBtn.style.opacity = editMode ? '1' : '.35';
    if (!editMode) { changesPanel.style.display = 'none'; historyPanel.style.display = 'none'; }
    document.dispatchEvent(new CustomEvent('editmodechange', { detail: { editMode } }));
  }
```

（這裡引用了 `hideHandles()` 跟 `historyPanel`，兩者都已經在本 Task 前面的 Step 1、3 定義過，
放心在這一步引用不會有未定義的問題——`function` 宣告在 IIFE 內會整體 hoist。）

注意：這一步引用了 `clearDraft()`，但那個函式要到 Task 9 才會定義。先在 `saveToServer` 上方（Step 1 插入的程式碼之前）加一個暫時的空函式，避免 Task 9 完成前執行期報錯：

```js
  function clearDraft() {}
```

（Task 9 會把這個暫時定義換成真正的實作，用 Edit 工具整段取代即可。）

- [ ] **Step 6: 手動起 `dev_server.py` 並驗證存檔**

用 `preview_start` 確認伺服器是 `dev_server.py`（Task 3 已切換），開啟
`http://127.0.0.1:7392/deck.html`，用 `preview_eval`：

```js
(async () => {
  window.EditMode.toggle(true);
  const title = document.querySelector('.slide.active .el.title');
  title.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: 10, clientY: 10 }));
  window.dispatchEvent(new MouseEvent('mousemove', { clientX: 40, clientY: 10 }));
  window.dispatchEvent(new MouseEvent('mouseup'));
  const data = await window.EditMode.save();
  return data;
})()
```

Expected: 回傳 `{ ok: true, snapshot: "..." }`（第一次存檔若原檔已存在會有快照時間戳記）。
用 `preview_network` 確認有一筆 `POST /__save` 回傳狀態碼 200。
用 Read 工具讀 `artifacts/html-test/deck.html`，確認 title 的 `left` 值已經是新的座標。
確認 `artifacts/html-test/.history/deck.html/` 目錄下多了一個快照檔案。

- [ ] **Step 7: 手動驗證版本回朔**

```js
(async () => {
  const before = await (await fetch('/__history?path=deck.html')).json();
  return before;
})()
```

用 `preview_click` 或 `preview_eval` 觸發 `window.EditMode.showHistory(true)`，用
`preview_snapshot` 確認面板列出至少一筆時間戳記跟「還原」按鈕。

- [ ] **Step 8: Commit**

```bash
git add artifacts/html-test/edit-mode.js
git commit -m "feat(edit-mode): wire save-to-server and version history panel"
```

---

## Task 9: `edit-mode.js` — localStorage 草稿自動存檔

**Files:**
- Modify: `artifacts/html-test/edit-mode.js`

**Interfaces:**
- Consumes: `elementKey`/`elementByKey`（Task 7）、`changedElements`、`textDirty`（Task 5）
- Produces: 真正的 `clearDraft()`（取代 Task 8 的暫時空函式）、`scheduleDraftSave(): void`、`checkDraftOnLoad(): void`

- [ ] **Step 1: 把 Task 8 的暫時 `clearDraft` 換成完整草稿邏輯**

把：

```js
  function clearDraft() {}
```

換成：

```js
  let draftTimer = null;
  function draftKey() { return 'edit-draft:' + location.pathname; }

  function scheduleDraftSave() {
    if (draftTimer) clearTimeout(draftTimer);
    draftTimer = setTimeout(saveDraftNow, 1500);
  }

  function saveDraftNow() {
    const entries = [];
    document.querySelectorAll('.slide').forEach((slide) => {
      slide.querySelectorAll('.el').forEach((el, idx) => {
        if (!changedElements.has(el)) return;
        entries.push({
          key: slide.id + '::' + idx,
          left: el.style.left, top: el.style.top,
          width: el.style.width, height: el.style.height,
          fontSize: el.style.fontSize,
          text: el.getAttribute('contenteditable') === 'true' ? el.innerHTML : null
        });
      });
    });
    if (entries.length === 0) { clearDraft(); return; }
    localStorage.setItem(draftKey(), JSON.stringify({ savedAt: Date.now(), entries: entries }));
  }

  function clearDraft() {
    localStorage.removeItem(draftKey());
  }

  function applyDraft(entries) {
    entries.forEach((entry) => {
      const el = elementByKey(entry.key);
      if (!el) return;
      if (entry.left) el.style.left = entry.left;
      if (entry.top) el.style.top = entry.top;
      if (entry.width) el.style.width = entry.width;
      if (entry.height) el.style.height = entry.height;
      if (entry.fontSize) el.style.fontSize = entry.fontSize;
      if (entry.text !== null && entry.text !== undefined) el.innerHTML = entry.text;
      changedElements.add(el);
    });
    if (changesBtn) changesBtn.style.opacity = changedElements.size ? '1' : '.35';
  }

  function checkDraftOnLoad() {
    const raw = localStorage.getItem(draftKey());
    if (!raw) return;
    let draft;
    try {
      draft = JSON.parse(raw);
    } catch (err) {
      localStorage.removeItem(draftKey());
      return;
    }
    const prompt = document.createElement('div');
    prompt.id = 'edit-draft-prompt';
    prompt.style.cssText = 'position:fixed; left:50%; top:16px; transform:translateX(-50%); z-index:103; ' +
      'background:rgba(10,14,20,.95); color:#E6EAF0; font:13px ui-monospace,"SF Mono",Menlo,monospace; ' +
      'padding:10px 16px; border-radius:8px; display:flex; gap:12px; align-items:center; ' +
      'border:1px solid rgba(63,208,232,.3); box-shadow:0 12px 32px rgba(0,0,0,.5);';
    const text = document.createElement('span');
    text.textContent = '發現未儲存的草稿（' + new Date(draft.savedAt).toLocaleString() + '）';
    const restoreBtn = document.createElement('button');
    restoreBtn.textContent = '恢復';
    restoreBtn.style.cssText = 'background:#3FD0E8; color:#0B1220; border:0; border-radius:6px; padding:4px 10px; font-weight:700; cursor:pointer;';
    const discardBtn = document.createElement('button');
    discardBtn.textContent = '捨棄';
    discardBtn.style.cssText = 'background:transparent; color:#E6EAF0; border:1px solid rgba(255,255,255,.3); border-radius:6px; padding:4px 10px; cursor:pointer;';
    restoreBtn.onclick = () => { applyDraft(draft.entries); prompt.remove(); };
    discardBtn.onclick = () => { clearDraft(); prompt.remove(); };
    prompt.append(text, restoreBtn, discardBtn);
    document.body.appendChild(prompt);
  }
```

- [ ] **Step 2: 讓 move-drag / resize / 文字編輯都會觸發草稿排程**

把 Task 5 的：

```js
  window.addEventListener('mouseup', () => {
    if (dragEl) {
      recordChange(dragEl);
      setReadout(HINT_TEXT);
    }
    dragEl = null;
  });
```

換成：

```js
  window.addEventListener('mouseup', () => {
    if (dragEl) {
      recordChange(dragEl);
      setReadout(HINT_TEXT);
      scheduleDraftSave();
    }
    dragEl = null;
  });
```

把 Task 5 的：

```js
  window.addEventListener('mouseup', () => {
    if (resizeEl) {
      recordChange(resizeEl);
      setReadout(HINT_TEXT);
      resizeEl = null;
      resizeHandle = null;
    }
  });
```

換成：

```js
  window.addEventListener('mouseup', () => {
    if (resizeEl) {
      recordChange(resizeEl);
      setReadout(HINT_TEXT);
      scheduleDraftSave();
      resizeEl = null;
      resizeHandle = null;
    }
  });
```

在這兩段後面（`window.addEventListener('resize', ...)` 之後）加入文字編輯的監聽：

```js
  document.addEventListener('input', (e) => {
    if (!editMode) return;
    const el = e.target.closest ? e.target.closest('.el') : null;
    if (!el || el.getAttribute('contenteditable') !== 'true') return;
    textDirty.add(el);
    changedElements.add(el);
    if (changesBtn) changesBtn.style.opacity = '1';
    scheduleDraftSave();
  });
```

- [ ] **Step 3: 頁面載入時檢查草稿**

在 `window.EditMode = {...}` 那行**之前**加入：

```js
  checkDraftOnLoad();

```

- [ ] **Step 4: 瀏覽器手動驗證 — 草稿存下跟恢復**

```js
(() => {
  window.EditMode.toggle(true);
  const title = document.querySelector('.slide.active .el.title');
  title.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, clientX: 10, clientY: 10 }));
  window.dispatchEvent(new MouseEvent('mousemove', { clientX: 60, clientY: 10 }));
  window.dispatchEvent(new MouseEvent('mouseup'));
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(localStorage.getItem('edit-draft:' + location.pathname));
    }, 1700);
  });
})()
```

Expected: 回傳一段 JSON 字串，`entries` 陣列裡有一筆包含剛剛拖曳過的 title 的 `key`、`left`。

接著用 `preview_eval` 執行 `location.reload()`，reload 後用 `preview_snapshot` 確認畫面上
出現「發現未儲存的草稿」的提示列，點擊「恢復」後用 `preview_eval` 確認
`document.querySelector('.slide.active .el.title').style.left` 等於草稿裡記錄的值。

- [ ] **Step 5: Commit**

```bash
git add artifacts/html-test/edit-mode.js
git commit -m "feat(edit-mode): add localStorage draft autosave with restore prompt"
```

---

## Task 10: 更新 `references/html-generation-rules.md` 規則 6 說明

**Files:**
- Modify: `references/html-generation-rules.md`

- [ ] **Step 1: 更新規則 6 內容**

把規則 6 章節中「它做什麼」清單裡的項目：

```
- 工具列多三顆按鈕：「編輯模式 (E)」「匯出調整後 HTML (X)」「座標異動清單 (R)」
```

換成：

```
- 工具列多五顆按鈕：「編輯模式 (E)」「匯出調整後 HTML (X)」「座標異動清單 (R)」
  「儲存 (Ctrl+S)」「歷史版本 (H)」
- 點擊任一 `.el` 可圈選（同時只能選一個），四角+四邊出現 8 個控制點：拖角落等比
  縮放（字級跟著等比縮放）、拖邊線單方向縮放（只改寬或只改高，字級跟著該軸縮放）；
  點空白處、按 Escape、或用方向鍵／空白鍵換頁都會取消選取
- 「儲存 (Ctrl+S)」：把目前調整寫回原始 HTML 檔案（透過 `dev_server.py` 的
  `/__save`），存檔前自動把舊內容備份到 `.history/` 目錄；沒有連上本地伺服器時
  （例如直接雙擊開檔）會提示「未偵測到本地伺服器」，不影響其他功能
- 「歷史版本 (H)」：列出這個檔案目前所有存檔快照，可選一筆還原；還原前一樣會
  先備份目前狀態，所以還原本身也可以再復原
- 未按存檔前，編輯內容每隔約 1.5 秒會自動存進瀏覽器 `localStorage` 當草稿；
  下次打開同一個網址若偵測到草稿會提示「發現未儲存的草稿，要恢復嗎？」
```

同時把「目前不做的部分（刻意留白，等有需要再補）」段落裡：

```
- 拖曳/編輯時不做即時規則檢查或警告（例如拖進留白帶跳提示），先求「能自由
  調整」，提示機制之後有需要再加
```

保留不動（這條依然成立），但在它下面補一條：

```
- 存回原始 HTML 檔案不會回寫進七段式 YAML 或 theme 檔的 `layout_overrides`，
  若之後重新用 AI 生成同一個輸出路徑，手動存檔的調整會被蓋掉；要沉澱成規則，
  仍需人工透過「座標異動清單」抄進 theme 檔
- 版本快照（`.history/`）不做自動清除或數量上限
```

- [ ] **Step 2: Commit**

```bash
git add references/html-generation-rules.md
git commit -m "docs: update rule 6 for select/resize/save/history capabilities"
```

---

## Task 11: 端對端瀏覽器驗證

**Files:**
- 不修改檔案，只驗證 Task 1–10 的成果整合起來是否正常運作。

- [ ] **Step 1: 起服務**

確認 `.claude/launch.json` 的 `html-test` 設定已指向 `dev_server.py`（Task 3），用
`preview_start` 啟動，開啟 `http://127.0.0.1:7392/deck.html`。

- [ ] **Step 2: 選取與控制點螢幕像素大小驗證（縮放不受 stage scale 影響）**

用 `preview_resize` 把視窗改成很小的尺寸（例如 400×300，讓 `#stage` 的 scale 明顯小於 1），
選取一個元素後用 `preview_eval`：

```js
(() => {
  const seHandle = document.querySelector('.edit-resize-handle[data-handle="se"]');
  const rect = seHandle.getBoundingClientRect();
  return { width: rect.width, height: rect.height };
})()
```

Expected: `width`/`height` 都還是 10（不會因為 `#stage` 縮小而跟著縮成不到 10px）。

- [ ] **Step 3: 完整流程走一遍**

依序：`preview_click` 或 `preview_eval` 開啟編輯模式 → 選取一個卡片元素 → 拖角落控制點
放大 → 拖邊線控制點只加高 → 按 `R` 打開異動清單，用 `preview_snapshot` 確認清單裡
同時列出 left/top/width/height/font-size → 按 `Ctrl+S` 存檔 → 用 `preview_network`
確認 `POST /__save` 回傳 200 → 按 `H` 打開歷史版本 → 用 `preview_snapshot` 確認至少
一筆快照且有「還原」按鈕。

- [ ] **Step 4: 無伺服器情境**

用 `preview_eval` 執行 `fetch('/__save', {method:'POST', body: '{}'}).catch(() => 'offline-like')`
的替代方式較難模擬真正離線，改用直接檢查程式碼路徑：暫時把
`window.fetch` 覆寫成永遠 reject 的版本，確認 `saveToServer()` 走進 catch 分支、
`readout` 顯示「未偵測到本地伺服器，無法儲存」而不是拋出未捕捉的例外：

```js
(async () => {
  const original = window.fetch;
  window.fetch = () => Promise.reject(new Error('offline'));
  const result = await window.EditMode.save();
  window.fetch = original;
  return { result: result, readoutText: document.getElementById('edit-readout').textContent };
})()
```

Expected: `result: null`，`readoutText` 包含「未偵測到本地伺服器」。

- [ ] **Step 5: 回報結果**

跟使用者回報：選取/縮放/字級縮放是否符合預期、異動清單格式、存檔與版本回朔
是否正常運作、草稿自動存檔是否在 reload 後正確提示，以及有沒有觀察到任何
既有功能（拖曳移動、文字編輯、匯出新檔、換頁）因為這次改動而跟著壞掉。
