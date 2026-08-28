#!/usr/bin/env python3
"""Regenerate the 14 authored Presets for the v6 image-background pipeline.

This is a deliberately scoped adapter around ``render_authored_html_deck.build``.
It does not copy or patch a previously rendered deck.  Before the current
renderer builds each deck, it adapts only three evidence-backed CSS conflicts:

* Scent Veil's retired raster paper field and blocking background ``!important``;
* AI Operations' non-semantic full-slide circle; and
* Tide Signal's non-semantic ellipse field and full-slide pseudo decorations.

The editable player is still produced by the current renderer and embeds the
current canonical ``src/html-editor/edit-mode.js`` source.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import render_authored_html_deck as renderer  # noqa: E402
from build_html_theme_lab import validate_catalog  # noqa: E402
from html_theme_lab_catalog import (  # noqa: E402
    BASE_CATALOG,
    EXTENSION_CATALOG,
    load_catalog,
)


DEFAULT_OUTPUT = (
    ROOT
    / "artifacts"
    / "experiments"
    / "html-image-background"
    / "html-preset-regeneration-20260813-v6"
    / "regenerated-source"
    / "authored"
)
ADAPTER_REVISION = "html-image-background-v6-authored-r1"
CONTENT_MODE = "new-deck"
CONTENT_ORIGIN = "existing-content"
RENDER_PURPOSE = "test-style"
EXPECTED_THEME_COUNT = 14
EXPECTED_SLIDE_COUNT = 146

EDITOR_SOURCE = ROOT / "src" / "html-editor" / "edit-mode.js"
RENDERER_SOURCE = ROOT / "scripts" / "render_authored_html_deck.py"
ADAPTER_SOURCE = ROOT / "scripts" / "render_v6_authored_presets.py"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _drop_exact_rule(css: str, selector: str) -> tuple[str, dict[str, Any]]:
    pattern = re.compile(re.escape(selector) + r"\s*\{[^{}]*\}", re.DOTALL)
    matches = list(pattern.finditer(css))
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one CSS rule for {selector!r}, found {len(matches)}"
        )
    match = matches[0]
    source = match.group(0)
    adapted = css[: match.start()] + css[match.end() :]
    return adapted, {
        "selector": selector,
        "operation": "drop-rule",
        "source_sha256": _sha256_text(source),
        "result": "removed",
    }


def _rewrite_exact_rule(
    css: str,
    selector: str,
    transform: Callable[[str], str],
) -> tuple[str, dict[str, Any]]:
    pattern = re.compile(
        r"(?P<selector>" + re.escape(selector) + r")\s*\{(?P<body>[^{}]*)\}",
        re.DOTALL,
    )
    matches = list(pattern.finditer(css))
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one CSS rule for {selector!r}, found {len(matches)}"
        )
    match = matches[0]
    source = match.group(0)
    source_body = match.group("body")
    result_body = transform(source_body)
    if result_body == source_body:
        raise ValueError(f"CSS adapter made no change for {selector}")
    replacement = f"{selector}{{{result_body}}}"
    adapted = css[: match.start()] + replacement + css[match.end() :]
    return adapted, {
        "selector": selector,
        "operation": "rewrite-rule",
        "source_sha256": _sha256_text(source),
        "result_sha256": _sha256_text(replacement),
    }


def _rewrite_scent_v4_background(body: str) -> str:
    result, background_count = re.subn(
        r"background\s*:\s*#FAF7F8\s*!important\s*;?",
        "background-color:#FAF7F8;",
        body,
        count=1,
        flags=re.IGNORECASE,
    )
    result, image_count = re.subn(
        r"background-image\s*:\s*none\s*!important\s*;?",
        "background-image:none;",
        result,
        count=1,
        flags=re.IGNORECASE,
    )
    if background_count != 1 or image_count != 1:
        raise ValueError(
            "Scent V4 clean-background rule drifted; expected background and "
            "background-image declarations were not found"
        )
    return result


def _rewrite_scent_raster_background(body: str) -> str:
    result, color_count = re.subn(
        r"background-color\s*:\s*#FAF7F8\s*!important\s*;?",
        "background-color:#FAF7F8;",
        body,
        count=1,
        flags=re.IGNORECASE,
    )
    result, raster_count = re.subn(
        r"background-image\s*:\s*url\(\s*[\"']assets/scent-paper-field-v1\.png[\"']\s*\)\s*!important\s*;?",
        "background-image:none;",
        result,
        count=1,
        flags=re.IGNORECASE,
    )
    removed_counts: dict[str, int] = {}
    for property_name in ("background-repeat", "background-position", "background-size"):
        result, count = re.subn(
            rf"{property_name}\s*:\s*[^;}}]+\s*!important\s*;?",
            "",
            result,
            count=1,
            flags=re.IGNORECASE,
        )
        removed_counts[property_name] = count
    if color_count != 1 or raster_count != 1 or set(removed_counts.values()) != {1}:
        raise ValueError(
            "Scent raster rule drifted; expected color, raster, repeat, position, "
            f"and size declarations were not found: {removed_counts}"
        )
    return result


def _adapt_theme_css(theme_id: str, source_css: str) -> tuple[str, list[dict[str, Any]]]:
    css = source_css
    actions: list[dict[str, Any]] = []

    if theme_id == "ai-operations-signal":
        css, action = _drop_exact_rule(
            css,
            'html[data-theme-id="ai-operations-signal"] .slide:before',
        )
        actions.append(action)

    if theme_id == "tide-signal-observatory":
        for selector in (
            'html[data-theme-id="tide-signal-observatory"] .slide',
            'html[data-theme-id="tide-signal-observatory"] .slide:before',
            'html[data-theme-id="tide-signal-observatory"] .slide:after',
        ):
            css, action = _drop_exact_rule(css, selector)
            actions.append(action)

    if theme_id == "scent-veil-launch":
        selector_transforms: tuple[tuple[str, Callable[[str], str]], ...] = (
            (
                'html[data-theme-id="scent-veil-launch"] .slide[data-recipe^="scent-v4-"]',
                _rewrite_scent_v4_background,
            ),
            (
                'html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v5"] .slide[data-recipe^="scent-v4-"]',
                _rewrite_scent_raster_background,
            ),
            (
                'html[data-theme-id="scent-veil-launch"][data-html-assembly="preset-explicit-recipe-v6"] .slide[data-recipe^="scent-v4-"]',
                _rewrite_scent_raster_background,
            ),
        )
        for selector, transform in selector_transforms:
            css, action = _rewrite_exact_rule(css, selector, transform)
            actions.append(action)
        if "assets/scent-paper-field-v1.png" in css:
            raise ValueError("Scent adapter left the retired raster asset in Theme CSS")

    return css, actions


def _manifest_has_absolute_path(value: Any) -> list[str]:
    issues: list[str] = []

    def walk(node: Any, trail: str) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                walk(child, f"{trail}.{key}" if trail else str(key))
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{trail}[{index}]")
        elif isinstance(node, str):
            if re.match(r"^[A-Za-z]:[\\/]", node) or node.startswith("file://"):
                issues.append(f"{trail}={node}")
            if "\\" in node:
                issues.append(f"{trail}=backslash:{node}")

    walk(value, "")
    return issues


def _extract_embedded_editor(document: str) -> str:
    match = re.search(
        r'<script\s+data-edit-mode-embedded="true">(?P<source>.*?)</script>',
        document,
        re.DOTALL,
    )
    if not match:
        raise ValueError("Generated HTML is missing the embedded editor source")
    return match.group("source").replace("<\\/script", "</script")


def _player_markup_adapter(
    original: Callable[[str, int, int], str],
    metadata: dict[str, str],
) -> Callable[[str, int, int], str]:
    def wrapped(slides_html: str, canvas_width: int, canvas_height: int) -> str:
        markup = original(slides_html, canvas_width, canvas_height)
        marker = '<div id="player" class="editor-shell" data-ui-mode="edit"'
        if markup.count(marker) != 1:
            raise ValueError("Current editable player root marker drifted")
        attributes = "".join(
            f' data-{name}="{html.escape(value, quote=True)}"'
            for name, value in metadata.items()
        )
        return markup.replace(marker, marker + attributes, 1)

    return wrapped


def _annotate_fresh_renderer_document(document: str) -> tuple[str, str]:
    """Add scoped ownership metadata to a document just returned by build()."""

    style_marker = "<style>"
    if document.count(style_marker) != 1:
        raise ValueError(
            "Current authored renderer style marker drifted; expected one unowned block"
        )
    document = document.replace(
        style_marker,
        '<style data-css-owner="renderer-base">',
        1,
    )
    revision_match = re.search(r'data-deck-revision="[0-9a-f]{20}"', document)
    if not revision_match:
        raise ValueError("Current authored renderer deck revision marker drifted")
    revisionless = (
        document[: revision_match.start()]
        + 'data-deck-revision="__V6_REVISION__"'
        + document[revision_match.end() :]
    )
    revision = _sha256_text(revisionless)[:20]
    document = revisionless.replace("__V6_REVISION__", revision, 1)
    return document, revision


def _static_validate_deck(
    *,
    theme_id: str,
    slide_count: int,
    output_path: Path,
    manifest: dict[str, Any],
    editor_source: str,
    editor_sha256: str,
) -> dict[str, Any]:
    document = output_path.read_text(encoding="utf-8")
    issues: list[str] = []
    expected_content_source = manifest["content_source"]
    manifest_path = output_path.with_suffix(".manifest.json")

    rendered_slide_count = len(
        re.findall(r'<section\s+class="slide(?:\s|\")', document)
    )
    if rendered_slide_count != slide_count:
        issues.append(
            f"slide-count expected={slide_count} actual={rendered_slide_count}"
        )

    embedded_editor = _extract_embedded_editor(document)
    embedded_sha256 = _sha256_text(embedded_editor)
    if embedded_editor != editor_source or embedded_sha256 != editor_sha256:
        issues.append(
            f"embedded-editor expected={editor_sha256} actual={embedded_sha256}"
        )

    required_html_markers = {
        f'data-editor-source-sha256="{editor_sha256}"': "editor hash",
        f'data-content-source="{expected_content_source}"': "content source",
        'data-content-mode="new-deck"': "content mode",
        'data-content-origin="existing-content"': "content origin",
        'data-render-purpose="test-style"': "render purpose",
        'data-preset-demo="false"': "preset-demo exclusion",
        f'data-render-adapter-revision="{ADAPTER_REVISION}"': "adapter revision",
        'data-asset-policy="pattern-geometry-only"': "asset policy",
    }
    for marker, label in required_html_markers.items():
        if marker not in document:
            issues.append(f"missing-html-{label}: {marker}")

    forbidden_markers = (
        "assets/scent-paper-field-v1.png",
        'data-content-mode="preset-demo"',
        "file:///",
    )
    for marker in forbidden_markers:
        if marker in document:
            issues.append(f"forbidden-html-marker: {marker}")

    if manifest.get("content_mode") != CONTENT_MODE:
        issues.append(f"manifest-content-mode={manifest.get('content_mode')!r}")
    if manifest.get("content_origin") != CONTENT_ORIGIN:
        issues.append(f"manifest-content-origin={manifest.get('content_origin')!r}")
    if manifest.get("render_purpose") != RENDER_PURPOSE:
        issues.append(f"manifest-render-purpose={manifest.get('render_purpose')!r}")
    if manifest.get("preset_demo") is not False:
        issues.append(f"manifest-preset-demo={manifest.get('preset_demo')!r}")
    if manifest.get("adapter_revision") != ADAPTER_REVISION:
        issues.append(f"manifest-adapter-revision={manifest.get('adapter_revision')!r}")
    if manifest.get("editor", {}).get("source_sha256") != editor_sha256:
        issues.append("manifest-editor-hash-mismatch")
    if manifest.get("output") != _repo_path(output_path):
        issues.append(f"manifest-output={manifest.get('output')!r}")
    if manifest.get("manifest") != _repo_path(manifest_path):
        issues.append(f"manifest-self-path={manifest.get('manifest')!r}")
    if manifest.get("asset_provenance"):
        issues.append("source deck unexpectedly carries asset provenance")
    issues.extend(_manifest_has_absolute_path(manifest))

    deck_revision_match = re.search(r'data-deck-revision="([0-9a-f]{20})"', document)
    if not deck_revision_match:
        issues.append("missing-deck-revision")
    elif deck_revision_match.group(1) != manifest.get("deck_revision"):
        issues.append("deck-revision-manifest-mismatch")

    return {
        "theme_id": theme_id,
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "slides": rendered_slide_count,
        "html": _repo_path(output_path),
        "manifest": _repo_path(manifest_path),
        "html_sha256": _sha256_path(output_path),
        "manifest_sha256": _sha256_path(manifest_path),
        "embedded_editor_sha256": embedded_sha256,
    }


def build_collection(output: Path) -> dict[str, Any]:
    output = output.resolve()
    try:
        output.relative_to(ROOT)
    except ValueError as error:
        raise ValueError(f"Output must stay inside the repository: {output}") from error

    catalog = load_catalog(BASE_CATALOG, EXTENSION_CATALOG)
    validate_catalog(catalog)
    themes = sorted(catalog["themes"], key=lambda row: row["order"])
    if len(themes) != EXPECTED_THEME_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_THEME_COUNT} authored Presets, found {len(themes)}"
        )
    expected_slides = sum(len(spec["slides"]) for spec in themes)
    if expected_slides != EXPECTED_SLIDE_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_SLIDE_COUNT} authored slides, found {expected_slides}"
        )

    output.mkdir(parents=True, exist_ok=True)
    qa_dir = output / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)

    editor_source = EDITOR_SOURCE.read_text(encoding="utf-8")
    editor_sha256 = _sha256_path(EDITOR_SOURCE)
    renderer_sha256_before = _sha256_path(RENDERER_SOURCE)
    editor_sha256_before = editor_sha256
    adapter_sha256 = _sha256_path(ADAPTER_SOURCE)

    original_css = dict(renderer.REDESIGN_THEME_CSS)
    original_player_markup = renderer.editable_player_markup
    css_audit: dict[str, list[dict[str, Any]]] = {}
    for spec in themes:
        theme_id = spec["theme_id"]
        adapted_css, actions = _adapt_theme_css(theme_id, original_css[theme_id])
        renderer.REDESIGN_THEME_CSS[theme_id] = adapted_css
        css_audit[theme_id] = actions

    records: list[dict[str, Any]] = []
    static_reports: list[dict[str, Any]] = []
    try:
        for source_spec in themes:
            spec = copy.deepcopy(source_spec)
            theme_id = spec["theme_id"]
            content_source = str(spec["_content_source"])
            spec["_asset_policy"] = "pattern-geometry-only"
            spec["_asset_provenance"] = []
            spec["_background_pattern"] = "clean-foreground-awaiting-model-raster"

            metadata = {
                "editor-source-sha256": editor_sha256,
                "content-source": content_source,
                "content-mode": CONTENT_MODE,
                "content-origin": CONTENT_ORIGIN,
                "render-purpose": RENDER_PURPOSE,
                "preset-demo": "false",
                "render-adapter-revision": ADAPTER_REVISION,
            }
            renderer.editable_player_markup = _player_markup_adapter(
                original_player_markup,
                metadata,
            )

            html_path = output / f"{theme_id}.html"
            generated = renderer.build(spec, html_path)
            manifest_path = html_path.with_suffix(".manifest.json")
            fresh_document, deck_revision = _annotate_fresh_renderer_document(
                html_path.read_text(encoding="utf-8")
            )
            html_path.write_text(
                fresh_document,
                encoding="utf-8",
                newline="\n",
            )
            generated["deck_revision"] = deck_revision
            embedded_editor = _extract_embedded_editor(
                fresh_document
            )
            embedded_editor_sha256 = _sha256_text(embedded_editor)
            generated.update(
                {
                    "manifest": _repo_path(manifest_path),
                    "content_mode": CONTENT_MODE,
                    "content_origin": CONTENT_ORIGIN,
                    "render_purpose": RENDER_PURPOSE,
                    "preset_demo": False,
                    "adapter_revision": ADAPTER_REVISION,
                    "scoped_adapter": {
                        "entrypoint": _repo_path(ADAPTER_SOURCE),
                        "revision": ADAPTER_REVISION,
                        "source_sha256": adapter_sha256,
                        "css_actions": css_audit[theme_id],
                        "post_patch_old_html": False,
                    },
                    "editor": {
                        "canonical_source": _repo_path(EDITOR_SOURCE),
                        "source_sha256": editor_sha256,
                        "embedded_sha256": embedded_editor_sha256,
                        "companion": _repo_path(output / "edit-mode.js"),
                    },
                    "renderer": {
                        "canonical_source": _repo_path(RENDERER_SOURCE),
                        "source_sha256": renderer_sha256_before,
                        "build_function": "render_authored_html_deck.build",
                    },
                }
            )
            manifest_path.write_text(
                json.dumps(generated, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )

            static_report = _static_validate_deck(
                theme_id=theme_id,
                slide_count=len(spec["slides"]),
                output_path=html_path,
                manifest=generated,
                editor_source=editor_source,
                editor_sha256=editor_sha256,
            )
            static_reports.append(static_report)
            records.append(
                {
                    "theme_id": theme_id,
                    "slides": len(spec["slides"]),
                    "content_source": content_source,
                    "content_mode": CONTENT_MODE,
                    "content_origin": CONTENT_ORIGIN,
                    "render_purpose": RENDER_PURPOSE,
                    "preset_demo": False,
                    "html": _repo_path(html_path),
                    "manifest": _repo_path(manifest_path),
                    "html_sha256": static_report["html_sha256"],
                    "manifest_sha256": static_report["manifest_sha256"],
                    "static_status": static_report["status"],
                    "css_actions": css_audit[theme_id],
                }
            )
    finally:
        renderer.REDESIGN_THEME_CSS.clear()
        renderer.REDESIGN_THEME_CSS.update(original_css)
        renderer.editable_player_markup = original_player_markup

    renderer_sha256_after = _sha256_path(RENDERER_SOURCE)
    editor_sha256_after = _sha256_path(EDITOR_SOURCE)
    if renderer_sha256_after != renderer_sha256_before:
        raise RuntimeError("Canonical authored renderer changed during scoped generation")
    if editor_sha256_after != editor_sha256_before:
        raise RuntimeError("Canonical editor changed during scoped generation")

    companion_path = output / "edit-mode.js"
    if not companion_path.is_file():
        raise FileNotFoundError(f"Current renderer did not emit {companion_path}")
    companion_sha256 = _sha256_path(companion_path)
    if companion_sha256 != editor_sha256:
        raise ValueError(
            f"Companion editor hash mismatch: {companion_sha256} != {editor_sha256}"
        )

    static_status = (
        "pass"
        if all(report["status"] == "pass" for report in static_reports)
        else "fail"
    )
    static_qa = {
        "generated_at": _utc_now(),
        "adapter_revision": ADAPTER_REVISION,
        "status": static_status,
        "counts": {
            "themes": len(records),
            "slides": sum(record["slides"] for record in records),
            "passed": sum(report["status"] == "pass" for report in static_reports),
            "failed": sum(report["status"] != "pass" for report in static_reports),
        },
        "editor": {
            "canonical_source": _repo_path(EDITOR_SOURCE),
            "canonical_sha256": editor_sha256,
            "companion": _repo_path(companion_path),
            "companion_sha256": companion_sha256,
        },
        "reports": static_reports,
    }
    static_qa_path = qa_dir / "static-and-editor-hash.json"
    static_qa_path.write_text(
        json.dumps(static_qa, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    batch_manifest = {
        "generated_at": _utc_now(),
        "skill": "html-pattern-slide",
        "adapter_revision": ADAPTER_REVISION,
        "adapter": {
            "entrypoint": _repo_path(ADAPTER_SOURCE),
            "source_sha256": adapter_sha256,
        },
        "renderer": {
            "entrypoint": _repo_path(RENDERER_SOURCE),
            "source_sha256_before": renderer_sha256_before,
            "source_sha256_after": renderer_sha256_after,
            "build_function": "render_authored_html_deck.build",
        },
        "editor": static_qa["editor"],
        "catalog_sources": [
            _repo_path(BASE_CATALOG),
            _repo_path(EXTENSION_CATALOG),
        ],
        "content_mode": CONTENT_MODE,
        "content_origin": CONTENT_ORIGIN,
        "render_purpose": RENDER_PURPOSE,
        "preset_demo": False,
        "output_root": _repo_path(output),
        "counts": {
            "themes": len(records),
            "slides": sum(record["slides"] for record in records),
        },
        "static_qa": {
            "status": static_status,
            "report": _repo_path(static_qa_path),
        },
        "themes": records,
    }
    absolute_issues = _manifest_has_absolute_path(batch_manifest)
    if absolute_issues:
        raise ValueError(f"Batch manifest contains non-portable paths: {absolute_issues}")
    batch_path = output / "v6-authored-batch-manifest.json"
    batch_path.write_text(
        json.dumps(batch_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    result = {
        "status": static_status,
        "adapter_revision": ADAPTER_REVISION,
        "themes": len(records),
        "slides": sum(record["slides"] for record in records),
        "output_root": _repo_path(output),
        "batch_manifest": _repo_path(batch_path),
        "static_qa": _repo_path(static_qa_path),
        "editor_sha256": editor_sha256,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if static_status != "pass":
        raise SystemExit(1)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_collection(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
