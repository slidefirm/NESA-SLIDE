#!/usr/bin/env python3
"""Fail closed when a new-deck HTML artifact repeats page claims or bodies."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class _SlideCopyParser(HTMLParser):
    _VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.slides: list[dict[str, Any]] = []
        self._slide_stack: list[dict[str, Any]] = []
        self._skip_depth = 0
        self._tag_stack: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {key: value or "" for key, value in attrs}
        if tag == "section" and "slide" in data.get("class", "").split():
            slide = {
                "id": data.get("id", ""),
                "page_claim": _clean(data.get("data-page-claim", "")),
                "title_chunks": [],
                "body_chunks": [],
            }
            self.slides.append(slide)
            self._slide_stack.append(slide)
        classes = data.get("class", "").split()
        record: dict[str, Any] = {
            "tag": tag,
            "classes": classes,
            "capture": False,
            "title": False,
        }
        if tag not in self._VOID_TAGS:
            self._tag_stack.append(record)
        if tag in {"script", "style", "svg"}:
            if tag in {"script", "style"}:
                self._skip_depth += 1
            return
        if not self._slide_stack or self._skip_depth:
            return
        # Most Layouts expose a title/headline class. toc-*-panel-rows instead
        # uses the bold text inside its semantic toc-side-panel as the visible
        # page claim, so recognize that contract instead of false-failing a
        # complete new-deck page.
        is_toc_sidebar_heading = (
            tag in {"b", "strong", "h1", "h2", "h3"}
            and any("toc-side-panel" in item.get("classes", []) for item in self._tag_stack)
        )
        is_title = (
            any("title" in token or "headline" in token for token in classes)
            or is_toc_sidebar_heading
        )
        is_text = (
            data.get("data-edit-kind") == "text"
            or data.get("data-edit-layer") == "text"
            or tag == "text"
        )
        if is_text:
            record["capture"] = True
            record["body_index"] = len(self._slide_stack[-1]["body_chunks"])
            self._slide_stack[-1]["body_chunks"].append("")
            if is_title:
                record["title"] = True
                record["title_index"] = len(self._slide_stack[-1]["title_chunks"])
                self._slide_stack[-1]["title_chunks"].append("")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._VOID_TAGS:
            return
        record = self._tag_stack.pop() if self._tag_stack else {"tag": tag}
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "section" and self._slide_stack:
            self._slide_stack.pop()

    def handle_data(self, data: str) -> None:
        if not self._slide_stack or self._skip_depth:
            return
        slide = self._slide_stack[-1]
        capture = next((item for item in reversed(self._tag_stack) if item.get("capture")), None)
        if capture is None:
            return
        if not capture.get("title"):
            slide["body_chunks"][capture["body_index"]] += data
        title = next((item for item in reversed(self._tag_stack) if item.get("title")), None)
        if title is not None:
            slide["title_chunks"][title["title_index"]] += data


def audit(html_path: Path, manifest_path: Path | None = None) -> dict[str, Any]:
    parser = _SlideCopyParser()
    parser.feed(html_path.read_text(encoding="utf-8"))
    pages = []
    for index, slide in enumerate(parser.slides, 1):
        title = next((value for value in map(_clean, slide["title_chunks"]) if value), "")
        body = _clean(" ".join(slide["body_chunks"]))
        claim = slide["page_claim"] or title
        pages.append({
            "page": index,
            "id": slide["id"],
            "claim": claim,
            "title": title,
            "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "body_length": len(body),
        })
    claims = [page["claim"] for page in pages]
    body_hashes = [page["body_sha256"] for page in pages]
    issues: list[dict[str, Any]] = []
    if any(not claim for claim in claims):
        issues.append({"code": "missing-visible-page-claim"})
    if any(page["body_length"] <= 0 for page in pages):
        issues.append({"code": "missing-visible-page-body"})
    if len(set(claims)) != len(claims):
        issues.append({"code": "duplicate-visible-page-claim", "claims": claims})
    if len(set(body_hashes)) != len(body_hashes):
        issues.append({"code": "duplicate-visible-page-body", "body_hashes": body_hashes})
    manifest_summary: dict[str, Any] | None = None
    if manifest_path is not None:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        content_pages = manifest.get("content_pages") or []
        composition_plan = manifest.get("composition_plan") or []
        content_hashes = [str(row.get("content_sha256") or "") for row in content_pages]
        composition_hashes = [str(row.get("content_sha256") or "") for row in composition_plan]
        manifest_summary = {
            "content_page_count": len(content_pages),
            "content_hashes_unique": len(content_hashes) == len(set(content_hashes)) == len(pages),
            "composition_hashes_unique": len(composition_hashes) == len(set(composition_hashes)) == len(pages),
        }
        if not manifest_summary["content_hashes_unique"]:
            issues.append({"code": "manifest-content-hashes-not-unique"})
        if not manifest_summary["composition_hashes_unique"]:
            issues.append({"code": "manifest-composition-hashes-not-unique"})
    return {
        "schema_version": 1,
        "status": "pass" if not issues else "fail",
        "pages": pages,
        "manifest": manifest_summary,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = audit(args.html.resolve(), args.manifest.resolve() if args.manifest else None)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
