from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = ROOT / "artifacts" / "deploy"


def json_response(handler: SimpleHTTPRequestHandler, status: int, payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


class LayoutGalleryHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DEPLOY_DIR), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            json_response(self, 200, {"ok": True, "service": "layout-gallery-static-server"})
            return
        if self.path.startswith("/api/codex/jobs/"):
            json_response(
                self,
                410,
                {
                    "ok": False,
                    "error": "Codex regeneration jobs were retired; use the active task's built-in image_gen workflow.",
                },
            )
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/codex/regenerate":
            json_response(self, 404, {"ok": False, "error": "not found"})
            return
        json_response(
            self,
            410,
            {
                "ok": False,
                "error": "Automatic nested Codex regeneration is retired. Use generate-image-slide and built-in image_gen in the active task.",
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the generated layout gallery locally for inspection.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), LayoutGalleryHandler)
    print(f"Layout gallery helper: http://{args.host}:{args.port}")
    print("The former /api/codex/regenerate endpoint is retired and returns HTTP 410.")
    server.serve_forever()


if __name__ == "__main__":
    main()
