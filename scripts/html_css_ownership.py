#!/usr/bin/env python3
"""Validate CSS ownership for editable HTML presentations.

Layout geometry and Theme/Preset appearance are deliberately separate.  This
module is dependency-free so catalog loaders, renderers, and CI can all reject
an appearance stylesheet before it is allowed to reach a deck.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


APPEARANCE_OWNERS = {"theme-appearance", "preset-appearance"}
KNOWN_STYLE_OWNERS = APPEARANCE_OWNERS | {
    "renderer-base",
    "editor-chrome",
    "legacy-demo-override",
    "background-experiment",
}

# Appearance may replace these renderer-neutral paint/type tokens.  Geometry
# variables are intentionally absent: an appearance stylesheet cannot smuggle
# a width, gap, coordinate, or transform into Layout CSS through var().
ALLOWED_CUSTOM_PROPERTIES = {
    "--bg",
    "--primary",
    "--secondary",
    "--accent",
    "--support-accent",
    "--surface",
    "--text",
    "--muted",
    "--surface-text",
    "--surface-muted",
    "--accent-ink",
    "--surface-accent-ink",
    "--accent-text",
    "--font-heading",
    "--font-body",
    "--font-mono",
    "--font-display",
}

# These declarations paint an existing box or text run.  They do not choose a
# Layout, create/remove boxes, or change the box model used for materialization.
ALLOWED_APPEARANCE_PROPERTIES = {
    "color",
    "background",
    "background-color",
    "background-image",
    "background-position",
    "background-repeat",
    "background-size",
    "background-blend-mode",
    "border-color",
    "border-top-color",
    "border-right-color",
    "border-bottom-color",
    "border-left-color",
    "border-radius",
    "box-shadow",
    "text-shadow",
    "opacity",
    "filter",
    "backdrop-filter",
    "-webkit-backdrop-filter",
    "mix-blend-mode",
    "isolation",
    "clip-path",
    "mask-image",
    "mask-size",
    "mask-position",
    "-webkit-mask-image",
    "-webkit-mask-size",
    "-webkit-mask-position",
    "font-family",
    "font-weight",
    "font-style",
    "letter-spacing",
    "text-transform",
    "text-decoration",
    "text-decoration-color",
    "text-decoration-style",
    "text-decoration-thickness",
    "text-underline-offset",
    "-webkit-text-fill-color",
    "fill",
    "fill-opacity",
    "stroke",
    "stroke-opacity",
    "stroke-width",
    "stroke-dasharray",
    "stroke-linecap",
    "stroke-linejoin",
    "outline-color",
    "outline-style",
    "accent-color",
}

# Border thickness is allowed only on the dedicated visual background layer.
# The project-wide border-box rule keeps the module root geometry unchanged.
BACKGROUND_LAYER_BORDER_PROPERTIES = {
    "border",
    "border-top",
    "border-right",
    "border-bottom",
    "border-left",
    "border-width",
    "border-top-width",
    "border-right-width",
    "border-bottom-width",
    "border-left-width",
    "border-style",
    "border-top-style",
    "border-right-style",
    "border-bottom-style",
    "border-left-style",
}

FORBIDDEN_SELECTOR_PATTERNS = (
    (re.compile(r"\[\s*data-layout-id\b", re.I), "layout-id-selector"),
    (re.compile(r"\[\s*data-composition-variant\b", re.I), "composition-variant-selector"),
    (re.compile(r"\[\s*data-recipe\b", re.I), "recipe-selector"),
    (re.compile(r"\[\s*data-production-family\b", re.I), "production-family-selector"),
    (re.compile(r"\[\s*data-page-number\b", re.I), "page-number-selector"),
    (re.compile(r":nth-(?:child|last-child|of-type|last-of-type)\s*\(", re.I), "slide-order-selector"),
    (re.compile(r"#s\d+\b", re.I), "slide-id-selector"),
    (re.compile(r"(^|[\s>+~,])\.content(?=$|[\s>+~,.#:\[])", re.I), "content-container-selector"),
    (re.compile(r"(^|[\s>+~,])\.el(?=$|[\s>+~,.#:\[])", re.I), "editable-root-selector"),
    (re.compile(r"(^|[\s>+~,])\.layout-content-area(?=$|[\s>+~,.#:\[])", re.I), "layout-frame-selector"),
    (re.compile(r"(^|[\s>+~,])\*(?=$|[\s>+~,.#:\[])", re.I), "universal-selector"),
)

_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_RULE_RE = re.compile(r"(?P<selector>[^{}]+)\{(?P<body>[^{}]*)\}", re.S)
_STYLE_TAG_RE = re.compile(r"<style\b(?P<attrs>[^>]*)>(?P<css>.*?)</style\s*>", re.I | re.S)
_OWNER_RE = re.compile(r"\bdata-css-owner\s*=\s*(['\"])(?P<owner>.*?)\1", re.I | re.S)
_CONTENT_MODE_RE = re.compile(r"\bdata-content-mode\s*=\s*(['\"])(?P<mode>.*?)\1", re.I | re.S)
_THEME_KIND_RE = re.compile(r"\bdata-theme-kind\s*=\s*(['\"])(?P<kind>.*?)\1", re.I | re.S)


def _issue(source: str, code: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"source": source, "code": code, "detail": detail, **extra}


def _split_declarations(body: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(body):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == ";" and depth == 0:
            parts.append(body[start:index])
            start = index + 1
    parts.append(body[start:])
    return [part.strip() for part in parts if part.strip()]


def validate_appearance_css(css: str, *, source: str = "appearance-css") -> list[dict[str, Any]]:
    """Return blocking ownership issues for one Theme/Preset stylesheet."""

    issues: list[dict[str, Any]] = []
    cleaned = _COMMENT_RE.sub("", css)
    if re.search(r"!\s*important\b", cleaned, re.I):
        issues.append(_issue(source, "important-forbidden", "Appearance CSS may not use !important"))
    if cleaned.count("{") != cleaned.count("}"):
        issues.append(_issue(source, "unbalanced-braces", "CSS braces are not balanced"))

    consumed = []
    for match in _RULE_RE.finditer(cleaned):
        consumed.append((match.start(), match.end()))
        selector = match.group("selector").strip()
        body = match.group("body")
        if not selector:
            continue
        if selector.startswith("@"):
            issues.append(_issue(source, "at-rule-forbidden", selector, selector=selector))
            continue
        for pattern, code in FORBIDDEN_SELECTOR_PATTERNS:
            if pattern.search(selector):
                issues.append(_issue(source, code, selector, selector=selector))

        background_layer = ".diagram-node-bg" in selector or "data-edit-layer=\"background\"" in selector or "data-edit-layer='background'" in selector
        for declaration in _split_declarations(body):
            if ":" not in declaration:
                issues.append(_issue(source, "invalid-declaration", declaration, selector=selector))
                continue
            raw_property, value = declaration.split(":", 1)
            property_name = raw_property.strip().lower()
            value = value.strip()
            if property_name.startswith("--"):
                if property_name not in ALLOWED_CUSTOM_PROPERTIES:
                    issues.append(
                        _issue(
                            source,
                            "geometry-or-unknown-custom-property",
                            property_name,
                            selector=selector,
                            property=property_name,
                        )
                    )
                continue
            if property_name in BACKGROUND_LAYER_BORDER_PROPERTIES:
                if not background_layer:
                    issues.append(
                        _issue(
                            source,
                            "border-box-owned-by-layout",
                            property_name,
                            selector=selector,
                            property=property_name,
                        )
                    )
                continue
            if property_name not in ALLOWED_APPEARANCE_PROPERTIES:
                issues.append(
                    _issue(
                        source,
                        "property-not-appearance",
                        property_name,
                        selector=selector,
                        property=property_name,
                    )
                )
            for variable in re.findall(r"var\(\s*(--[\w-]+)", value, re.I):
                if variable not in ALLOWED_CUSTOM_PROPERTIES:
                    issues.append(
                        _issue(
                            source,
                            "geometry-or-unknown-variable-reference",
                            variable,
                            selector=selector,
                            property=property_name,
                        )
                    )

    if cleaned.strip() and not consumed:
        issues.append(_issue(source, "no-css-rules", "No parseable CSS rules found"))
    return issues


def assert_appearance_css(css: str, *, source: str = "appearance-css") -> None:
    issues = validate_appearance_css(css, source=source)
    if issues:
        summary = "; ".join(f"{row['code']}: {row['detail']}" for row in issues[:12])
        if len(issues) > 12:
            summary += f"; +{len(issues) - 12} more"
        raise ValueError(f"CSS ownership violation in {source}: {summary}")


def validate_html_document_text(
    markup: str,
    *,
    source: str = "html-document",
    content_mode: str | None = None,
) -> list[dict[str, Any]]:
    """Validate owned style blocks and new-deck isolation in rendered HTML."""

    issues: list[dict[str, Any]] = []
    if content_mode is None:
        mode_match = _CONTENT_MODE_RE.search(markup)
        content_mode = mode_match.group("mode") if mode_match else None
    kind_match = _THEME_KIND_RE.search(markup)
    theme_kind = kind_match.group("kind") if kind_match else None
    owners: list[str] = []
    style_matches = list(_STYLE_TAG_RE.finditer(markup))
    if not style_matches:
        issues.append(_issue(source, "missing-style-block", "No style block found"))
        return issues

    for index, match in enumerate(style_matches, 1):
        attrs = match.group("attrs")
        css = match.group("css")
        owner_match = _OWNER_RE.search(attrs)
        owner = owner_match.group("owner").strip() if owner_match else ""
        block_source = f"{source}#style-{index}"
        if not owner:
            issues.append(_issue(block_source, "unowned-style-block", "Every generated style block needs data-css-owner"))
            continue
        owners.append(owner)
        if owner not in KNOWN_STYLE_OWNERS:
            issues.append(_issue(block_source, "unknown-style-owner", owner))
            continue
        if owner in APPEARANCE_OWNERS:
            issues.extend(validate_appearance_css(css, source=block_source))
        preset_selector_allowed = owner == "preset-appearance" or (
            content_mode == "preset-demo" and owner == "legacy-demo-override"
        )
        if "data-preset-theme" in css and not preset_selector_allowed:
            issues.append(
                _issue(
                    block_source,
                    "preset-selector-outside-preset-owner",
                    f"data-preset-theme selector is owned by {owner}",
                )
            )
        if "data-style-case" in css and content_mode != "preset-demo":
            issues.append(_issue(block_source, "legacy-style-case-in-new-deck", "Style Case CSS is demo-only"))

    if content_mode == "new-deck" and "legacy-demo-override" in owners:
        issues.append(_issue(source, "legacy-demo-owner-in-new-deck", "new-deck cannot load legacy demo CSS"))
    if content_mode == "new-deck" and theme_kind == "html-preset" and "preset-appearance" not in owners:
        issues.append(_issue(source, "missing-preset-appearance-owner", "HTML Preset new-deck needs an owned appearance stylesheet"))
    return issues


def validate_manifest_data(data: dict[str, Any], *, source: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if data.get("content_mode") != "new-deck":
        return issues
    preset = data.get("preset_theme") or {}
    legacy_source = str(preset.get("source", ""))
    if "style_cases/" in legacy_source or "html-theme-lab" in legacy_source:
        issues.append(_issue(source, "legacy-preset-source-in-new-deck", legacy_source))
    example_reference = data.get("example_reference")
    if example_reference:
        issues.append(_issue(source, "example-reference-in-new-deck", str(example_reference)))
    return issues


def _self_test() -> dict[str, Any]:
    valid = """
html[data-preset-theme="safe"]{--bg:#fff;--text:#111;--accent:#067;--font-body:'Noto Sans TC'}
html[data-preset-theme="safe"] .slide{background-color:var(--bg);background-image:radial-gradient(circle,rgba(0,0,0,.04) 1px,transparent 1px)}
html[data-preset-theme="safe"] .diagram-node-bg{background:var(--surface);border-color:var(--accent);border-radius:18px;box-shadow:0 10px 24px rgba(0,0,0,.08)}
html[data-preset-theme="safe"] .prod-title{color:var(--text);font-family:var(--font-body);font-weight:800}
"""
    invalid = {
        "layout-selector": 'html[data-preset-theme="x"] [data-layout-id="title-center"]{color:red}',
        "geometry": 'html[data-preset-theme="x"] .prod-title{left:100px;width:900px}',
        "important": 'html[data-preset-theme="x"] .prod-title{color:red!important}',
        "broad-root": 'html[data-preset-theme="x"] .content{color:red}',
        "layout-variable": 'html[data-preset-theme="x"]{--gap:24px;color:#111}',
    }
    valid_issues = validate_appearance_css(valid, source="self-test-valid")
    failures: list[str] = []
    if valid_issues:
        failures.append(f"valid sample rejected: {valid_issues}")
    for name, css in invalid.items():
        if not validate_appearance_css(css, source=f"self-test-{name}"):
            failures.append(f"invalid sample accepted: {name}")
    if failures:
        raise AssertionError("; ".join(failures))
    return {"pass": True, "valid_cases": 1, "invalid_cases": len(invalid)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--css", type=Path)
    parser.add_argument("--html", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--source", default="command-line")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(_self_test(), ensure_ascii=False))
        return 0
    if bool(args.css) == bool(args.html):
        parser.error("choose exactly one of --css or --html")

    issues: list[dict[str, Any]] = []
    if args.css:
        issues.extend(validate_appearance_css(args.css.read_text(encoding="utf-8"), source=str(args.css)))
    else:
        markup = args.html.read_text(encoding="utf-8")
        manifest_data: dict[str, Any] | None = None
        manifest_path = args.manifest
        if manifest_path is None:
            candidate = args.html.with_suffix(".manifest.json")
            if candidate.is_file():
                manifest_path = candidate
        if manifest_path and manifest_path.is_file():
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        content_mode = str(manifest_data.get("content_mode")) if manifest_data else None
        issues.extend(validate_html_document_text(markup, source=str(args.html), content_mode=content_mode))
        if manifest_data is not None:
            issues.extend(validate_manifest_data(manifest_data, source=str(manifest_path)))
    payload = {"pass": not issues, "issues": issues}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
