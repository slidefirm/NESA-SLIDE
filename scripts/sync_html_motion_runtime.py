#!/usr/bin/env python3
"""Synchronize the canonical presentation motion runtime into HTML outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from artifact_report_paths import portable_report_path
from html_motion_runtime import (
    motion_runtime_manifest,
    motion_runtime_root_attributes,
    motion_runtime_script,
    motion_runtime_style,
)


MOTION_STYLE_RE = re.compile(
    r'<style\b(?=[^>]*\bdata-motion-runtime-style=)[^>]*>.*?</style>',
    re.IGNORECASE | re.DOTALL,
)
MOTION_SCRIPT_RE = re.compile(
    r'<script\b(?=[^>]*\bdata-motion-runtime=)[^>]*>.*?</script>',
    re.IGNORECASE | re.DOTALL,
)
HTML_OPEN_RE = re.compile(r'<html\b(?P<attrs>[^>]*)>', re.IGNORECASE)


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def update_root_attributes(markup: str, html_path: Path) -> str:
    match = HTML_OPEN_RE.search(markup)
    if not match:
        raise ValueError(f"HTML root missing in {html_path}")
    attrs = match.group("attrs")
    for name in ("data-motion-runtime", "data-motion-source-sha256"):
        attrs = re.sub(rf'\s{name}="[^"]*"', "", attrs, count=1, flags=re.IGNORECASE)
    attrs = attrs.rstrip() + " " + motion_runtime_root_attributes()
    return markup[: match.start()] + "<html" + attrs + ">" + markup[match.end() :]


def update_html(html_path: Path) -> dict[str, object]:
    markup = html_path.read_text(encoding="utf-8")
    markup, style_count = MOTION_STYLE_RE.subn(
        lambda _match: motion_runtime_style(), markup, count=1
    )
    markup, script_count = MOTION_SCRIPT_RE.subn(
        lambda _match: motion_runtime_script(), markup, count=1
    )
    if style_count != 1 or script_count != 1:
        raise ValueError(
            f"Expected one motion style and script in {html_path}; "
            f"found style={style_count}, script={script_count}"
        )
    markup = update_root_attributes(markup, html_path)
    html_path.write_text(markup, encoding="utf-8")
    return {
        "file": portable_report_path(html_path),
        "motion_style_count": style_count,
        "motion_script_count": script_count,
        "html_sha256": digest_text(markup),
    }


def update_manifest(manifest_path: Path, editor_source: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    editor_text = editor_source.read_text(encoding="utf-8")
    editor_sha256 = digest_text(editor_text)
    editor_source_path = portable_report_path(editor_source)
    editable_dom = manifest.setdefault("editable_dom", {})
    editable_dom["editor_source"] = editor_source_path
    editable_dom["editor_sha256"] = editor_sha256
    # Keep the legacy top-level fields aligned for consumers that still read
    # them while the formal contract reads editable_dom.*.
    manifest["editor_source"] = editor_source_path
    manifest["editor_sha256"] = editor_sha256
    html_runtime = manifest.setdefault("html_runtime", {})
    html_runtime["motion_runtime_embedded"] = True
    html_runtime["motion_runtime"] = motion_runtime_manifest()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "file": portable_report_path(manifest_path),
        "editor_sha256": editor_sha256,
        "motion_runtime": html_runtime["motion_runtime"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--editor-source", type=Path, required=True)
    parser.add_argument("--html-dir", type=Path, action="append", required=True)
    parser.add_argument("--manifest", type=Path, action="append", default=[])
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    editor_source = args.editor_source.resolve()
    html_results: list[dict[str, object]] = []
    manifest_results: list[dict[str, object]] = []
    for html_dir_arg in args.html_dir:
        html_dir = html_dir_arg.resolve()
        for html_path in sorted(html_dir.glob("*.html")):
            html_results.append(update_html(html_path))
    for manifest_arg in args.manifest:
        manifest_results.append(update_manifest(manifest_arg.resolve(), editor_source))

    report = {
        "editor_source": portable_report_path(editor_source),
        "editor_sha256": digest_text(editor_source.read_text(encoding="utf-8")),
        "motion_runtime": motion_runtime_manifest(),
        "html_files": html_results,
        "manifests": manifest_results,
        "pass": bool(html_results) and all(
            item["motion_style_count"] == 1 and item["motion_script_count"] == 1
            for item in html_results
        ),
    }
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
