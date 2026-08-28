#!/usr/bin/env python3
"""靜態檔案伺服器 + HTML 編輯模式的存檔與 PPTX 匯出 API（純標準庫）。"""
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


MAX_JSON_BODY_BYTES = 64 * 1024 * 1024


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


class PptxExporter:
    """把瀏覽器送來的 edited-DOM manifest 交給 artifact-tool builder。"""

    def __init__(
        self,
        repo_root: Path | None = None,
        node_executable: str | None = None,
        converter_path: Path | None = None,
        timeout_seconds: int = 180,
    ):
        self.repo_root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
        self.node_executable = node_executable or shutil.which("node") or "node"
        self.converter_path = (
            converter_path
            or self.repo_root / "artifacts" / "pptx" / "builders" / "export-html-manifest.mjs"
        ).resolve()
        self.runtime_dir = self.repo_root / "artifacts" / "pptx"
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def safe_file_name(value: str) -> str:
        name = Path(str(value or "edited-presentation.pptx")).name
        if not name.lower().endswith(".pptx"):
            name += ".pptx"
        safe = "".join(ch if ch.isalnum() or ch in "._- " else "-" for ch in name).strip(" .-")
        return safe or "edited-presentation.pptx"

    def export(self, manifest: dict) -> dict:
        slides = manifest.get("slides") if isinstance(manifest, dict) else None
        if not isinstance(slides, list) or not slides:
            raise ValueError("manifest.slides must contain at least one slide")
        if len(slides) > 200:
            raise ValueError("manifest contains more than 200 slides")
        if not self.converter_path.is_file():
            raise FileNotFoundError("PPTX converter not found: " + str(self.converter_path))

        file_name = self.safe_file_name(manifest.get("fileName", "edited-presentation.pptx"))
        with tempfile.TemporaryDirectory(prefix="html-pptx-export-") as tmp_value:
            tmp_dir = Path(tmp_value)
            manifest_path = tmp_dir / "manifest.json"
            output_path = tmp_dir / file_name
            qa_path = tmp_dir / "qa.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            env = os.environ.copy()
            env.setdefault("HOME", str(Path.home()))
            completed = subprocess.run(
                [
                    self.node_executable,
                    str(self.converter_path),
                    "--input",
                    str(manifest_path),
                    "--output",
                    str(output_path),
                    "--qa",
                    str(qa_path),
                ],
                cwd=str(self.runtime_dir),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                check=False,
            )
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout or "unknown artifact-tool error").strip()
                raise RuntimeError(detail[-4000:])
            if not output_path.is_file():
                raise RuntimeError("artifact-tool finished without producing a PPTX file")
            qa = json.loads(qa_path.read_text(encoding="utf-8")) if qa_path.is_file() else {}
            return {
                "bytes": output_path.read_bytes(),
                "file_name": file_name,
                "qa": qa,
            }


def make_handler(store: HtmlStore, pptx_exporter: PptxExporter | None = None):
    pptx_exporter = pptx_exporter or PptxExporter()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(store.serve_dir), **kwargs)

        def log_message(self, fmt, *args):
            pass

        def end_headers(self):
            # 本機開發伺服器：一律禁用瀏覽器快取，避免改完 edit-mode.js 重新整理
            # 卻還是吃到舊版的問題（deck.html 的 <script src="edit-mode.js"> 沒有
            # cache-busting query string，靠 HTTP 快取語意很容易讓瀏覽器沿用舊檔）。
            self.send_header("Cache-Control", "no-store, must-revalidate")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            super().end_headers()

        def _json_response(self, code: int, obj: dict) -> None:
            data = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _binary_response(self, code: int, data: bytes, file_name: str, qa: dict) -> None:
            self.send_response(code)
            self.send_header(
                "Content-Type",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )
            self.send_header("Content-Length", str(len(data)))
            self.send_header(
                "Content-Disposition",
                "attachment; filename=\"presentation.pptx\"; filename*=UTF-8''" + quote(file_name),
            )
            self.send_header("X-PPTX-Slides", str(qa.get("slideCount", "")))
            self.send_header("X-PPTX-Layouts", str(qa.get("layouts", "")))
            self.end_headers()
            self.wfile.write(data)

        def _read_json_body(self) -> dict:
            length = int(self.headers.get("Content-Length", 0))
            if length > MAX_JSON_BODY_BYTES:
                raise ValueError("request body exceeds 64 MB")
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
            elif self.path == "/__export-pptx":
                self._handle_export_pptx()
            else:
                self._json_response(404, {"error": "not found"})

        def do_OPTIONS(self):
            self.send_response(204)
            self.end_headers()

        def _handle_history(self):
            query = self.path.split("?", 1)[1] if "?" in self.path else ""
            params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            path = params.get("path", "").strip()
            if not path:
                self._json_response(400, {"error": "missing path parameter"})
                return
            from urllib.parse import unquote
            name = Path(unquote(path)).name
            self._json_response(200, {"snapshots": store.list_snapshots(name)})

        def _handle_save(self):
            try:
                body = self._read_json_body()
                snap = store.save(body["path"], body["html"])
            except KeyError as err:
                self._json_response(400, {"error": "missing required field: " + str(err.args[0])})
                return
            except ValueError as err:
                self._json_response(400, {"error": str(err)})
                return
            self._json_response(200, {"ok": True, "snapshot": snap})

        def _handle_revert(self):
            try:
                body = self._read_json_body()
                store.revert(body["path"], body["snapshot"])
            except KeyError as err:
                self._json_response(400, {"error": "missing required field: " + str(err.args[0])})
                return
            except ValueError as err:
                self._json_response(400, {"error": str(err)})
                return
            except FileNotFoundError as err:
                self._json_response(404, {"error": "snapshot not found: " + str(err)})
                return
            self._json_response(200, {"ok": True})

        def _handle_export_pptx(self):
            try:
                manifest = self._read_json_body()
                result = pptx_exporter.export(manifest)
            except (KeyError, json.JSONDecodeError, ValueError) as err:
                self._json_response(400, {"error": str(err)})
                return
            except FileNotFoundError as err:
                self._json_response(503, {"error": str(err)})
                return
            except subprocess.TimeoutExpired:
                self._json_response(504, {"error": "PPTX export timed out"})
                return
            except RuntimeError as err:
                self._json_response(500, {"error": str(err)})
                return
            self._binary_response(200, result["bytes"], result["file_name"], result["qa"])

    return Handler


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7392
    directory = Path(__file__).resolve().parent
    if "--directory" in sys.argv:
        idx = sys.argv.index("--directory")
        directory = Path(sys.argv[idx + 1]).resolve()
    store = HtmlStore(directory)
    handler_cls = make_handler(store)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
    print(
        "Serving {} at port {} (with /__save /__history /__revert /__export-pptx)".format(
            directory, port
        )
    )
    httpd.serve_forever()


if __name__ == "__main__":
    main()
