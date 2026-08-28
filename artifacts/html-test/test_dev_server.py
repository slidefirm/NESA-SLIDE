import http.client
import json as json_module
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dev_server import HtmlStore, PptxExporter


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

    def test_pptx_file_name_is_sanitized(self):
        self.assertEqual(PptxExporter.safe_file_name("../bad:name.pptx"), "bad-name.pptx")


import http.server
from dev_server import make_handler


class FakePptxExporter:
    def export(self, manifest):
        if not manifest.get("slides"):
            raise ValueError("manifest.slides must contain at least one slide")
        return {
            "bytes": b"PK\x03\x04fake-pptx",
            "file_name": "edited-deck.pptx",
            "qa": {"slideCount": len(manifest["slides"]), "layouts": 1},
        }


class HttpApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "index.html").write_text("<html>hello</html>", encoding="utf-8")
        self.store = HtmlStore(self.tmp)
        handler_cls = make_handler(self.store, FakePptxExporter())
        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), handler_cls)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.05)

    def tearDown(self):
        self.httpd.shutdown()
        self.thread.join(timeout=2)
        self.httpd.server_close()
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

    def _raw_request(self, method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        headers = {"Content-Type": "application/json"} if body is not None else {}
        payload = json_module.dumps(body).encode("utf-8") if body is not None else None
        conn.request(method, path, body=payload, headers=headers)
        res = conn.getresponse()
        data = res.read()
        result = {
            "status": res.status,
            "content_type": res.getheader("Content-Type"),
            "disposition": res.getheader("Content-Disposition"),
            "slides": res.getheader("X-PPTX-Slides"),
            "data": data,
        }
        conn.close()
        return result

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

    def test_save_missing_html_key_returns_400(self):
        status, data = self._request("POST", "/__save", {"path": "index.html"})
        self.assertEqual(status, 400)
        self.assertIn("error", data)
        self.assertIn("html", data["error"])

    def test_revert_missing_snapshot_key_returns_400(self):
        status, data = self._request("POST", "/__revert", {"path": "index.html"})
        self.assertEqual(status, 400)
        self.assertIn("error", data)
        self.assertIn("snapshot", data["error"])

    def test_history_missing_path_parameter_returns_400(self):
        status, data = self._request("GET", "/__history")
        self.assertEqual(status, 400)
        self.assertIn("error", data)
        self.assertIn("path", data["error"])

    def test_export_pptx_returns_download(self):
        result = self._raw_request(
            "POST",
            "/__export-pptx",
            {"title": "Deck", "slides": [{"id": "s1", "elements": []}]},
        )
        self.assertEqual(result["status"], 200)
        self.assertTrue(result["data"].startswith(b"PK"))
        self.assertIn("presentationml.presentation", result["content_type"])
        self.assertIn("edited-deck.pptx", result["disposition"])
        self.assertEqual(result["slides"], "1")

    def test_export_pptx_rejects_empty_slide_list(self):
        status, data = self._request("POST", "/__export-pptx", {"slides": []})
        self.assertEqual(status, 400)
        self.assertIn("manifest.slides", data["error"])


if __name__ == "__main__":
    unittest.main()
