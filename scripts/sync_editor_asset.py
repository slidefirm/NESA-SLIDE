#!/usr/bin/env python3
"""Verify or refresh the generated HTML editor compatibility asset."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "src" / "html-editor" / "edit-mode.js"
DEFAULT_COMPANION = ROOT / "artifacts" / "html-test" / "edit-mode.js"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--companion", type=Path, default=DEFAULT_COMPANION)
    parser.add_argument("--write", action="store_true", help="Refresh the generated companion asset.")
    args = parser.parse_args()

    source = args.source.resolve()
    companion = args.companion.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Canonical editor source missing: {source}")
    if args.write:
        companion.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, companion)

    source_hash = sha256(source)
    companion_hash = sha256(companion) if companion.is_file() else None
    passed = source_hash == companion_hash
    report = {
        "source": source.relative_to(ROOT).as_posix(),
        "companion": companion.relative_to(ROOT).as_posix(),
        "source_sha256": source_hash,
        "companion_sha256": companion_hash,
        "pass": passed,
        "wrote": bool(args.write),
    }
    print(json.dumps(report, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
