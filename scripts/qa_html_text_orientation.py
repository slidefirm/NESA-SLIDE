#!/usr/bin/env python3
"""Reject vertical or right-angle-rotated text in release HTML sources/artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
TEXT_EXTENSIONS = {".css", ".html", ".js", ".cjs", ".mjs", ".md", ".py", ".yaml", ".yml"}
DEFAULT_SOURCES = (
    ROOT / "scripts" / "html_production_renderer.py",
    ROOT / "scripts" / "render_randomized_html_demo.py",
    ROOT / "scripts" / "render_theme_demo_html.py",
)
PATTERNS = (
    (
        "vertical-writing-mode",
        re.compile(r"writing-mode\s*:\s*(?:vertical-rl|vertical-lr|sideways-rl|sideways-lr)", re.I),
    ),
    (
        "right-angle-text-rotation",
        re.compile(
            r"(?:transform\s*:|transform\s*=)[^;\r\n>]*rotate\(\s*[+-]?(?:90|270)deg\s*\)"
            r"|rotate\s*:\s*[+-]?(?:90|270)deg",
            re.I,
        ),
    ),
    (
        "svg-text-right-angle-rotation",
        re.compile(
            r"<(?:text|tspan)\b[^>]*\btransform\s*=\s*[\"'][^\"']*?"
            r"rotate\(\s*[+-]?(?:90|270)(?:deg)?(?=[\s,)])",
            re.I,
        ),
    ),
)


def portable(path: Path, *, root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return resolved.name


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_text(text: str, *, path_label: str) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for kind, pattern in PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            issues.append(
                {
                    "path": path_label,
                    "line": line_number,
                    "kind": kind,
                    "match": match.group(0),
                    "excerpt": line.strip()[:500],
                }
            )
    return issues


def scan_path(path: Path, *, root: Path) -> list[dict[str, object]]:
    resolved = path.resolve()
    if resolved == SELF or not resolved.is_file() or resolved.suffix.lower() not in TEXT_EXTENSIONS:
        return []
    return scan_text(
        resolved.read_text(encoding="utf-8", errors="replace"),
        path_label=portable(resolved, root=root),
    )


def ledger_paths(ledger: Path, *, root: Path) -> list[Path]:
    paths: list[Path] = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^[0-9a-f]{64}  (.+)$", line)
        if match:
            paths.append(root / Path(match.group(1)))
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit horizontal text-orientation contract")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--source", action="append", type=Path, default=[])
    parser.add_argument("--html", action="append", type=Path, default=[])
    parser.add_argument("--release-ledger", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    candidates = [path if path.is_absolute() else root / path for path in args.source]
    if not candidates:
        candidates.extend(DEFAULT_SOURCES)
    candidates.extend(path if path.is_absolute() else root / path for path in args.html)
    if args.release_ledger:
        ledger = args.release_ledger if args.release_ledger.is_absolute() else root / args.release_ledger
        candidates.extend(ledger_paths(ledger, root=root))

    unique = sorted({path.resolve() for path in candidates if path.exists()}, key=lambda item: item.as_posix())
    issues = [issue for path in unique for issue in scan_path(path, root=root)]
    report = {
        "schema_version": 1,
        "status": "pass" if not issues else "fail",
        "contract": "visible-text-horizontal-only",
        "checked_files": len(unique),
        "checked": [
            {"path": portable(path, root=root), "sha256": sha256(path)}
            for path in unique
            if path.is_file()
        ],
        "issues": issues,
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        report_path = args.report if args.report.is_absolute() else root / args.report
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
