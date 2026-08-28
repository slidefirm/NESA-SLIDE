#!/usr/bin/env python3
"""Synchronize the shared editor asset and embedded runtime in formal HTML outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

from artifact_report_paths import portable_report_path
from html_edit_framework import EDITABLE_PLAYER_CSS, PLAYER_RUNTIME, PPTX_BROWSER_RUNTIME_BRIDGE
from html_production_renderer import normalize_generated_css_font_sizes


EMBEDDED_RE = re.compile(
    r'(<script\s+data-edit-mode-embedded="true">)(.*?)(</script>)',
    re.DOTALL,
)
PPTX_BROWSER_RE = re.compile(
    r'(<script\s+data-pptx-browser-runtime-embedded="true">)(.*?)(</script>)',
    re.DOTALL,
)
EXTERNAL_EDITOR_RE = re.compile(
    r'<script\b[^>]*\bsrc=["\'][^"\']*edit-mode\.js["\'][^>]*>',
    re.IGNORECASE,
)
CANVAS_RE = re.compile(
    r"#stage\s*\{[^}]*\bwidth\s*:\s*([0-9.]+)px\s*;[^}]*\bheight\s*:\s*([0-9.]+)px",
    re.DOTALL,
)
PLAYER_CSS_RE = re.compile(
    r"(?:\:root\{[^}]*--editor-rail-width[^}]*\}\s*)?#player\{.*?#hint\.hide\{[^}]*\}"
    r"(?:\s*@keyframes editorRailIn\{[^\n]*\}\s*@keyframes editorTopbarIn\{[^\n]*\})?",
    re.DOTALL,
)
HINT_MARKUP_RE = re.compile(r'<div\s+id="hint"[^>]*>.*?</div>', re.IGNORECASE | re.DOTALL)
STAGE_MARKUP_RE = re.compile(
    r'(?P<open><main\s+id="stage"[^>]*>)(?P<body>.*?)(?P<close></main>)',
    re.IGNORECASE | re.DOTALL,
)

PLAYER_OPEN_RE = re.compile(r'<div\s+id="player"(?P<attrs>[^>]*)>', re.IGNORECASE)
SLIDE_RAIL_HEADER_RE = re.compile(
    r'<div\s+id="slideRailHeader"[^>]*>.*?</div>',
    re.IGNORECASE | re.DOTALL,
)
SLIDE_RAIL_HEADER_MARKUP = (
    '<div id="slideRailHeader"><strong>投影片</strong><span>拖曳縮圖<br>調整頁序</span>'
    '<button id="slideRailToggle" type="button" aria-expanded="true" aria-label="收合投影片縮圖" '
    'title="收合投影片縮圖"><svg viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="m15 18-6-6 6-6"/></svg></button></div>'
)
SLIDE_RAIL_MARKUP = (
    '<aside id="slideRail" data-editor-chrome="true" aria-label="投影片縮圖">'
    + SLIDE_RAIL_HEADER_MARKUP
    + '<div id="slideThumbList"></div></aside>'
)


def replace_player_css(markup: str, html_path: Path) -> str:
    updated, count = PLAYER_CSS_RE.subn(EDITABLE_PLAYER_CSS.strip(), markup, count=1)
    if count != 1:
        raise ValueError(f"Expected one editable player CSS block in {html_path}, found {count}")
    return updated


def normalize_slide_typography(markup: str, html_path: Path) -> str:
    """Clamp generated slide typography while leaving editor chrome untouched."""

    player_css = PLAYER_CSS_RE.search(markup)
    if not player_css:
        raise ValueError(f"Editable player CSS block missing in {html_path}")
    markup = (
        normalize_generated_css_font_sizes(markup[: player_css.start()])
        + markup[player_css.start() :]
    )

    def normalize_stage(match: re.Match[str]) -> str:
        return (
            match.group("open")
            + normalize_generated_css_font_sizes(match.group("body"))
            + match.group("close")
        )

    updated, count = STAGE_MARKUP_RE.subn(normalize_stage, markup, count=1)
    if count != 1:
        raise ValueError(f"Expected one #stage in {html_path}, found {count}")
    return updated


def replace_player_runtime(markup: str, html_path: Path) -> str:
    """Replace only the player script immediately before the editor asset."""

    pptx_match = PPTX_BROWSER_RE.search(markup)
    embedded_match = EMBEDDED_RE.search(markup)
    external_match = EXTERNAL_EDITOR_RE.search(markup)
    editor_match = pptx_match or embedded_match or external_match
    if not editor_match:
        raise ValueError(f"Editor marker missing in {html_path}")
    marker_index = editor_match.start()

    prefix = markup[:marker_index]
    script_close = prefix.rfind("</script>")
    script_open = prefix.rfind("<script>", 0, script_close)
    if script_open < 0 or script_close < script_open:
        raise ValueError(f"Player runtime script missing before embedded editor in {html_path}")
    if prefix[script_close + len("</script>") :].strip():
        raise ValueError(f"Unexpected markup between player runtime and editor in {html_path}")

    canvas_match = CANVAS_RE.search(markup)
    if not canvas_match:
        raise ValueError(f"Unable to infer #stage canvas size in {html_path}")
    canvas_width, canvas_height = canvas_match.groups()
    runtime = PLAYER_RUNTIME.replace("__CW__", canvas_width).replace("__CH__", canvas_height)

    return (
        prefix[:script_open]
        + "<script>"
        + runtime
        + "</script>"
        + prefix[script_close + len("</script>") :]
        + markup[marker_index:]
    )


def ensure_editor_shell_markup(markup: str, html_path: Path) -> str:
    has_slide_rail = 'id="slideRail"' in markup

    def replace_open(match: re.Match[str]) -> str:
        attrs = match.group("attrs") or ""
        class_match = re.search(r'class="([^"]*)"', attrs, re.IGNORECASE)
        if class_match:
            classes = class_match.group(1).split()
            if "editor-shell" not in classes:
                classes.append("editor-shell")
            attrs = attrs[: class_match.start()] + f'class="{" ".join(classes)}"' + attrs[class_match.end() :]
        else:
            attrs += ' class="editor-shell"'
        if re.search(r'\bdata-ui-mode=', attrs, re.IGNORECASE):
            attrs = re.sub(r'\bdata-ui-mode="[^"]*"', 'data-ui-mode="edit"', attrs, count=1, flags=re.IGNORECASE)
        else:
            attrs += ' data-ui-mode="edit"'
        return f'<div id="player"{attrs}>' + ('' if has_slide_rail else SLIDE_RAIL_MARKUP)

    updated, count = PLAYER_OPEN_RE.subn(replace_open, markup, count=1)
    if count != 1:
        raise ValueError(f"Expected one #player root in {html_path}, found {count}")
    if has_slide_rail:
        updated, header_count = SLIDE_RAIL_HEADER_RE.subn(SLIDE_RAIL_HEADER_MARKUP, updated, count=1)
        if header_count != 1:
            raise ValueError(f"Expected one #slideRailHeader in {html_path}, found {header_count}")
    return HINT_MARKUP_RE.sub('<div id="hint" aria-hidden="true"></div>', updated, count=1)


def sync_pptx_browser_runtime(markup: str, html_path: Path, runtime: str) -> tuple[str, int]:
    escaped = runtime.replace("</script", "<\\/script")
    updated, count = PPTX_BROWSER_RE.subn(
        lambda match: match.group(1) + escaped + match.group(3),
        markup,
        count=1,
    )
    if count == 1:
        return updated, count
    editor_match = EMBEDDED_RE.search(markup) or EXTERNAL_EDITOR_RE.search(markup)
    if not editor_match:
        raise ValueError(f"Editor marker missing while embedding PPTX runtime in {html_path}")
    script = '<script data-pptx-browser-runtime-embedded="true">' + escaped + "</script>"
    return markup[: editor_match.start()] + script + markup[editor_match.start() :], 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--html-dir", type=Path, action="append", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--sync-player-runtime",
        action="store_true",
        help="Also replace the player runtime immediately before the embedded editor.",
    )
    parser.add_argument(
        "--sync-pptx-browser-runtime",
        action="store_true",
        help="Embed PptxGenJS and the native browser export adapter before the editor.",
    )
    parser.add_argument(
        "--pptxgen-source",
        type=Path,
        default=Path("artifacts/html-test/pptxgen.bundle.js"),
    )
    parser.add_argument(
        "--pptx-browser-export-source",
        type=Path,
        default=Path("artifacts/html-test/pptx-browser-export.js"),
    )
    args = parser.parse_args()

    source = args.source.resolve()
    source_text = source.read_text(encoding="utf-8")
    embedded_text = source_text.replace("</script", "<\\/script")
    pptx_runtime = ""
    pptx_runtime_sha256 = None
    if args.sync_pptx_browser_runtime:
        pptx_runtime = (
            args.pptxgen_source.resolve().read_text(encoding="utf-8")
            + "\n"
            + args.pptx_browser_export_source.resolve().read_text(encoding="utf-8")
            + "\n"
            + PPTX_BROWSER_RUNTIME_BRIDGE.strip()
            + "\n"
        )
        pptx_runtime_sha256 = hashlib.sha256(pptx_runtime.encode("utf-8")).hexdigest()
    results: list[dict[str, object]] = []

    for html_dir_arg in args.html_dir:
        html_dir = html_dir_arg.resolve()
        html_dir.mkdir(parents=True, exist_ok=True)
        directory_results: list[dict[str, object]] = []
        companion = html_dir / "edit-mode.js"
        html_paths = sorted(html_dir.glob("*.html"))
        needs_external_companion = any(
            EXTERNAL_EDITOR_RE.search(path.read_text(encoding="utf-8"))
            for path in html_paths
        )
        companion_error = None
        if source != companion.resolve() and (companion.exists() or needs_external_companion):
            try:
                shutil.copyfile(source, companion)
            except OSError as err:
                # Embedded formal outputs carry their own editor source and do
                # not depend on the convenience companion file.  Keep syncing
                # the authoritative embedded runtime, but never hide the copy
                # problem if an external-script deck actually needs it.
                companion_error = str(err)

        for html_path in html_paths:
            markup = html_path.read_text(encoding="utf-8")
            if args.sync_player_runtime:
                markup = normalize_slide_typography(markup, html_path)
                markup = replace_player_css(markup, html_path)
                markup = replace_player_runtime(markup, html_path)
                markup = ensure_editor_shell_markup(markup, html_path)
            pptx_runtime_count = 0
            if args.sync_pptx_browser_runtime:
                markup, pptx_runtime_count = sync_pptx_browser_runtime(
                    markup,
                    html_path,
                    pptx_runtime,
                )
            updated, count = EMBEDDED_RE.subn(
                lambda match: match.group(1) + embedded_text + match.group(3),
                markup,
            )
            external_count = len(EXTERNAL_EDITOR_RE.findall(updated))
            if count != 1 and external_count != 1:
                raise ValueError(
                    f"Expected one embedded or external editor in {html_path}, "
                    f"found embedded={count}, external={external_count}"
                )
            html_path.write_text(updated, encoding="utf-8")
            result = {
                "file": portable_report_path(html_path),
                "embedded_editor_count": count,
                "external_editor_count": external_count,
                "generated_text_min_px": 36 if args.sync_player_runtime else None,
                "companion_copy_error": companion_error,
                "player_runtime_synced": args.sync_player_runtime,
                "pptx_browser_runtime_count": pptx_runtime_count,
            }
            results.append(result)
            directory_results.append(result)
        if companion_error and any(item["external_editor_count"] for item in directory_results):
            raise OSError(f"Unable to sync required external editor companion in {html_dir}: {companion_error}")

    report = {
        "source": portable_report_path(source),
        "files": len(results),
        "player_runtime_synced": args.sync_player_runtime,
        "pptx_browser_runtime_synced": args.sync_pptx_browser_runtime,
        "pptx_browser_runtime_sha256": pptx_runtime_sha256,
        "results": results,
        "pass": bool(results),
    }
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
