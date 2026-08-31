#!/usr/bin/env python3
"""Verify formal HTML outputs embed the current shared editor with no external dependency."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from artifact_report_paths import portable_report_path


EMBEDDED_RE = re.compile(r'<script\s+data-edit-mode-embedded="true">(.*?)</script>', re.DOTALL)
EXTERNAL_RE = re.compile(r'<script\s+[^>]*src=["\']edit-mode\.js["\'][^>]*>\s*</script>', re.IGNORECASE)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--html-dir", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source_path = Path(args.source).resolve()
    source_text = source_path.read_text(encoding="utf-8")
    source_hash = digest(source_text)
    files: list[Path] = []
    for directory in args.html_dir:
        files.extend(sorted(Path(directory).resolve().glob("*.html")))

    issues: list[dict[str, object]] = []
    matched = 0
    for html_path in files:
        markup = html_path.read_text(encoding="utf-8")
        embedded = EMBEDDED_RE.findall(markup)
        external = bool(EXTERNAL_RE.search(markup))
        if len(embedded) != 1:
            issues.append({"file": portable_report_path(html_path), "issue": "embedded-editor-count", "count": len(embedded)})
            continue
        embedded_source = embedded[0].replace("<\\/script", "</script")
        embedded_hash = digest(embedded_source)
        if embedded_hash != source_hash:
            issues.append({
                "file": portable_report_path(html_path),
                "issue": "embedded-editor-hash",
                "expected": source_hash,
                "actual": embedded_hash,
            })
        elif external:
            issues.append({"file": portable_report_path(html_path), "issue": "external-editor-dependency"})
        else:
            matched += 1

    report = {
        "source": portable_report_path(source_path),
        "source_sha256": source_hash,
        "files": len(files),
        "matched": matched,
        "issues": issues,
        "pass": bool(files) and matched == len(files) and not issues,
    }
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
