#!/usr/bin/env python3
"""Audit audience-visible HTML slide copy and renderer string literals.

Traditional-Chinese decks may contain numbers, compact schedule codes, common
technical acronyms, or explicitly approved proper names.  They must not gain
Latin-only filler merely because a Layout has a kicker, caption, or metadata
slot.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable


DEFAULT_ALLOWED_LATIN_TERMS = {
    "AI",
    "API",
    "CSS",
    "HTML",
    "KPI",
    "PPTX",
    "QA",
    "SRT",
    "SVG",
    "SWOT",
    "URL",
}

_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_EMAIL_OR_URL_RE = re.compile(r"(?:https?://|www\.|\b[^\s@]+@[^\s@]+\.[^\s@]+)", re.I)
_COMPACT_CODE_RE = re.compile(
    r"(?:[A-Z]{0,3}\d{1,4}[A-Z]{0,3}|\d+(?:\.\d+)?(?:pt|px|m|km|cm|mm|kg|g|s|ms|h|d|°C))",
    re.I,
)
_TEMPLATE_FIELD_RE = re.compile(r"\{[^{}]*\}")
_SPACE_RE = re.compile(r"\s+")
_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def _normalise(value: str) -> str:
    return _SPACE_RE.sub(" ", value).strip()


class _VisibleTextParser(HTMLParser):
    def __init__(self, *, slides_only: bool) -> None:
        super().__init__(convert_charrefs=True)
        self.slides_only = slides_only
        self.slide_depth = 0
        self.ignored_depth = 0
        self.tag_stack: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: value or "" for name, value in attrs}
        classes = set(attr_map.get("class", "").split())
        if tag == "section" and "slide" in classes:
            self.slide_depth += 1
        elif self.slide_depth and tag not in _VOID_TAGS:
            self.slide_depth += 1
        if tag in {"script", "style", "template", "noscript"}:
            self.ignored_depth += 1
        self.tag_stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        return

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "template", "noscript"} and self.ignored_depth:
            self.ignored_depth -= 1
        if self.slide_depth:
            self.slide_depth -= 1
        if self.tag_stack:
            self.tag_stack.pop()

    def handle_data(self, data: str) -> None:
        if self.ignored_depth:
            return
        if self.slides_only and not self.slide_depth:
            return
        value = _normalise(data)
        if value:
            self.text.append(value)


def extract_visible_slide_text(document: str) -> list[str]:
    parser = _VisibleTextParser(slides_only=True)
    parser.feed(document)
    return parser.text


def _allowed_phrase(value: str, allowed_terms: set[str]) -> bool:
    if _EMAIL_OR_URL_RE.search(value):
        return True
    compact = re.sub(r"[\s·/,:;()\[\]{}._-]+", "", value)
    if compact and _COMPACT_CODE_RE.fullmatch(compact):
        return True
    canonical = value.upper()
    if re.fullmatch(r"[A-Z]", canonical):
        return True
    if canonical in allowed_terms:
        return True
    words = re.findall(r"[A-Za-z][A-Za-z0-9+.-]*", value)
    return bool(words) and all(word.upper() in allowed_terms for word in words)


def audit_visible_copy(
    document: str,
    *,
    language: str = "zh-Hant",
    allowed_latin_terms: Iterable[str] = (),
) -> dict[str, Any]:
    text = extract_visible_slide_text(document)
    allowed = DEFAULT_ALLOWED_LATIN_TERMS | {
        _normalise(str(value)).upper()
        for value in allowed_latin_terms
        if _normalise(str(value))
    }
    issues: list[dict[str, str]] = []
    latin_only: list[str] = []
    if language.lower() in {"zh-hant", "zh-tw", "traditional-chinese"}:
        for raw in text:
            value = _normalise(_TEMPLATE_FIELD_RE.sub("", raw))
            if not value or not _LATIN_RE.search(value) or _CJK_RE.search(value):
                continue
            latin_only.append(value)
            if not _allowed_phrase(value, allowed):
                issues.append(
                    {
                        "code": "unapproved-latin-only-visible-copy",
                        "text": value,
                        "detail": (
                            "繁中簡報的純英文可見文字必須是明確允許的正式名稱或必要縮寫；"
                            "裝飾性英文、Layout filler 與 renderer metadata 不得自動出現。"
                        ),
                    }
                )
    return {
        "status": "pass" if not issues else "fail",
        "language": language,
        "allowed_latin_terms": sorted(allowed),
        "visible_text_count": len(text),
        "latin_only_visible_text": latin_only,
        "issues": issues,
    }


def assert_visible_copy(
    document: str,
    *,
    language: str = "zh-Hant",
    allowed_latin_terms: Iterable[str] = (),
) -> dict[str, Any]:
    report = audit_visible_copy(
        document,
        language=language,
        allowed_latin_terms=allowed_latin_terms,
    )
    if report["issues"]:
        preview = "; ".join(row["text"] for row in report["issues"][:12])
        raise ValueError(f"Generated HTML violates visible-copy policy: {preview}")
    return report


def _template_text(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if not isinstance(node, ast.JoinedStr):
        return None
    parts: list[str] = []
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            parts.append(value.value)
        elif isinstance(value, ast.FormattedValue):
            parts.append("{value}")
    return "".join(parts)


def audit_renderer_source(source: str) -> dict[str, Any]:
    """Reject Latin-only text nodes hardcoded inside renderer HTML templates."""

    tree = ast.parse(source)
    issues: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for node in ast.walk(tree):
        template = _template_text(node)
        if not template or "<" not in template or ">" not in template or "</" not in template:
            continue
        # Joined f-strings are frequently split inside attributes.  Parsing
        # those fragments as standalone HTML makes attribute tails look like
        # text.  A renderer-owned literal is relevant only when it is already
        # enclosed by a complete `>text<` pair in the source template.
        for raw in re.findall(r">([^<>]+)<", template):
            value = _normalise(_TEMPLATE_FIELD_RE.sub("", raw))
            if not value or not _LATIN_RE.search(value) or _CJK_RE.search(value):
                continue
            if _allowed_phrase(value, DEFAULT_ALLOWED_LATIN_TERMS):
                continue
            key = (getattr(node, "lineno", 0), value)
            if key in seen:
                continue
            seen.add(key)
            issues.append(
                {
                    "code": "hardcoded-latin-visible-copy",
                    "line": getattr(node, "lineno", 0),
                    "text": value,
                    "detail": "Visible renderer text must come from page content and be optional when absent.",
                }
            )
    return {"status": "pass" if not issues else "fail", "issues": issues}


def _story_policy(path: Path | None) -> tuple[str, list[str]]:
    if path is None:
        return "zh-Hant", []
    payload = json.loads(path.read_text(encoding="utf-8"))
    concept = payload.get("concept") if isinstance(payload, dict) else None
    if not isinstance(concept, dict):
        return "zh-Hant", []
    return (
        str(concept.get("visible_text_language") or "zh-Hant"),
        [str(value) for value in concept.get("allowed_latin_terms") or []],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html")
    parser.add_argument("--story")
    parser.add_argument("--renderer-source")
    parser.add_argument("--language", default=None)
    parser.add_argument("--allow-latin", action="append", default=[])
    parser.add_argument("--report")
    args = parser.parse_args()

    if bool(args.html) == bool(args.renderer_source):
        parser.error("Provide exactly one of --html or --renderer-source")
    if args.renderer_source:
        report = audit_renderer_source(Path(args.renderer_source).read_text(encoding="utf-8"))
    else:
        language, allowed = _story_policy(Path(args.story) if args.story else None)
        report = audit_visible_copy(
            Path(args.html).read_text(encoding="utf-8"),
            language=args.language or language,
            allowed_latin_terms=allowed + list(args.allow_latin),
        )
    if args.report:
        output = Path(args.report)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
