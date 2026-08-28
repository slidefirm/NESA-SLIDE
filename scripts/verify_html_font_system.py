#!/usr/bin/env python3
"""Verify the shared Google Fonts contract across generated HTML catalogs."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from html_font_system import GOOGLE_FONT_REGISTRY, theme_font_contract


FONT_LINK_RE = re.compile(
    r'<link\b[^>]*data-font-system="google-fonts-css2"[^>]*href="([^"]+)"[^>]*>',
    re.IGNORECASE,
)
REQUIRED_VARIABLES = ("--font-heading", "--font-body", "--font-mono", "--font-display")
FORBIDDEN_PRIMARY_PATTERNS = (
    re.compile(r"font-family\s*:\s*Georgia\b", re.IGNORECASE),
    re.compile(r"font-family\s*:\s*ui-monospace\b", re.IGNORECASE),
    re.compile(r"font-family\s*:\s*Consolas\b", re.IGNORECASE),
    re.compile(r"font-family\s*:\s*[\"']?Microsoft JhengHei\b", re.IGNORECASE),
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_markup(markup: str, label: str) -> list[dict[str, str | int]]:
    issues: list[dict[str, str | int]] = []
    links = FONT_LINK_RE.findall(markup)
    if len(links) != 1:
        issues.append({"target": label, "issue": "google-font-stylesheet-count", "actual": len(links)})
        return issues

    url = html.unescape(links[0])
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "fonts.googleapis.com" or parsed.path != "/css2":
        issues.append({"target": label, "issue": "google-font-stylesheet-url"})
    query = parse_qs(parsed.query)
    families = {item.split(":", 1)[0].replace("+", " ") for item in query.get("family", [])}
    if families != set(GOOGLE_FONT_REGISTRY):
        issues.append({
            "target": label,
            "issue": "google-font-family-set",
            "actual": ", ".join(sorted(families)),
        })
    if query.get("display") != ["swap"]:
        issues.append({"target": label, "issue": "font-display-swap"})

    for origin in ("https://fonts.googleapis.com", "https://fonts.gstatic.com"):
        pattern = rf'<link\b[^>]*rel="preconnect"[^>]*href="{re.escape(origin)}"[^>]*>'
        if len(re.findall(pattern, markup, flags=re.IGNORECASE)) != 1:
            issues.append({"target": label, "issue": "font-preconnect", "origin": origin})
    for variable in REQUIRED_VARIABLES:
        if variable not in markup:
            issues.append({"target": label, "issue": "font-role-variable", "variable": variable})
    if "font-family:var(--font-body)" not in markup.replace(" ", ""):
        issues.append({"target": label, "issue": "body-font-role"})
    if "@import" in markup:
        issues.append({"target": label, "issue": "css-font-import"})
    for pattern in FORBIDDEN_PRIMARY_PATTERNS:
        if pattern.search(markup):
            issues.append({"target": label, "issue": "system-font-used-as-primary", "pattern": pattern.pattern})
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--html-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--extra-html", action="append", default=[])
    args = parser.parse_args()

    matrix = load_json(Path(args.matrix).resolve())
    html_dir = Path(args.html_dir).resolve()
    output = Path(args.output).resolve()
    themes = {item["id"]: item for item in matrix["themes"]}
    files = sorted(html_dir.glob("*.html"))
    issues: list[dict[str, str | int]] = []

    if {path.stem for path in files} != set(themes):
        issues.append({"target": str(html_dir), "issue": "theme-file-coverage", "actual": len(files)})

    mapping: dict[str, dict[str, str]] = {}
    for theme_id, theme in themes.items():
        contract = theme_font_contract(theme)
        mapping[theme_id] = {
            "heading": contract["heading_family"],
            "body": contract["body_family"],
            "mono": contract["mono_family"],
            "display": contract["display_family"],
        }
        if contract["heading_family"] not in GOOGLE_FONT_REGISTRY or contract["body_family"] not in GOOGLE_FONT_REGISTRY:
            issues.append({"target": theme_id, "issue": "unregistered-theme-font"})

    checked = []
    for path in [*files, *(Path(item).resolve() for item in args.extra_html)]:
        checked.append(str(path))
        if not path.exists():
            issues.append({"target": str(path), "issue": "missing-html"})
            continue
        issues.extend(check_markup(path.read_text(encoding="utf-8"), str(path)))

    report = {
        "pass": not issues,
        "registered_families": list(GOOGLE_FONT_REGISTRY),
        "themes": len(themes),
        "catalogs": len(files),
        "checked_html": len(checked),
        "theme_mapping": mapping,
        "issues": issues,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
