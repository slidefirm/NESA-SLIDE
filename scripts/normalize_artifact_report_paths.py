#!/usr/bin/env python3
"""Normalize repository-owned absolute paths in tracked artifact JSON reports."""

from __future__ import annotations

import argparse
import codecs
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
ROOT_NATIVE = str(ROOT).rstrip("\\/")
ROOT_POSIX = ROOT.as_posix().rstrip("/")
ROOT_URI = ROOT.as_uri().rstrip("/")
SKIP_PREFIXES = (
    "artifacts/generated-prompts/staging/",
    "artifacts/deploy/review/",
)


def tracked_json_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "artifacts/**/*.json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    paths = result.stdout.decode("utf-8", errors="strict").split("\0")
    return [
        ROOT / path
        for path in paths
        if path and not path.startswith(SKIP_PREFIXES)
    ]


JSON_STRING_PATTERN = re.compile(r'"(?:\\.|[^"\\])*"')
REPOSITORY_URI_PATTERNS = (
    re.compile(re.escape(ROOT_URI) + r"(?P<rest>/[^\r\n)]*)?"),
    re.compile(re.escape(f"file:///{ROOT_POSIX}") + r"(?P<rest>[\\/][^\r\n)]*)?"),
)
REPOSITORY_PATH_PATTERNS = (
    re.compile(re.escape(ROOT_NATIVE) + r"(?P<rest>[\\/][^\r\n)]*)?"),
    re.compile(re.escape(ROOT_POSIX) + r"(?P<rest>[\\/][^\r\n)]*)?"),
)
USER_URI_PATTERN = re.compile(
    r"file:///[A-Za-z]:/Users/[^/\r\n)]+(?P<rest>/[^\r\n)]*)?",
    re.IGNORECASE,
)
USER_PATH_PATTERN = re.compile(
    r"[A-Za-z]:[\\/]Users[\\/][^\\/\r\n)]+(?P<rest>[\\/][^\r\n)]*)?",
    re.IGNORECASE,
)


def decode_json(data: bytes) -> tuple[str, str]:
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode("utf-16"), "utf-16"
    if data.startswith(codecs.BOM_UTF8):
        return data.decode("utf-8-sig"), "utf-8-sig"
    return data.decode("utf-8"), "utf-8"


def relative_replacement(match: re.Match[str]) -> str:
    rest = (match.group("rest") or "").replace("\\", "/").lstrip("/")
    return rest or "."


def relative_uri_replacement(match: re.Match[str]) -> str:
    rest = unquote(match.group("rest") or "").replace("\\", "/").lstrip("/")
    return rest or "."


def user_home_replacement(match: re.Match[str]) -> str:
    rest = unquote(match.group("rest") or "").replace("\\", "/").lstrip("/")
    temp_prefix = "appdata/local/temp/"
    if rest.casefold().startswith(temp_prefix):
        return "local-temp://" + rest[len(temp_prefix):]
    return "user-home://" + (rest or ".")


def normalize_decoded_string(value: str) -> str:
    normalized = value
    for _ in range(8):
        previous = normalized
        for pattern in REPOSITORY_URI_PATTERNS:
            normalized = pattern.sub(relative_uri_replacement, normalized)
        for pattern in REPOSITORY_PATH_PATTERNS:
            normalized = pattern.sub(relative_replacement, normalized)
        normalized = USER_URI_PATTERN.sub(user_home_replacement, normalized)
        normalized = USER_PATH_PATTERN.sub(user_home_replacement, normalized)
        if normalized == previous:
            break
    return normalized


def normalize_text(value: str) -> str:
    def normalize_string_token(match: re.Match[str]) -> str:
        original_token = match.group(0)
        original_value = json.loads(original_token)
        normalized_value = normalize_decoded_string(original_value)
        if normalized_value == original_value:
            return original_token
        return json.dumps(normalized_value, ensure_ascii=False)

    return JSON_STRING_PATTERN.sub(normalize_string_token, value)


def normalize_file(path: Path, *, fix: bool) -> bool:
    original_bytes = path.read_bytes()
    original, encoding = decode_json(original_bytes)
    json.loads(original)
    normalized = normalize_text(original)
    json.loads(normalized)
    changed = normalized != original
    if changed and fix:
        path.write_bytes(normalized.encode(encoding))
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="Rewrite affected tracked artifact JSON files.")
    args = parser.parse_args()

    changed: list[str] = []
    errors: list[dict[str, str]] = []
    for path in tracked_json_files():
        try:
            if normalize_file(path, fix=args.fix):
                changed.append(path.relative_to(ROOT).as_posix())
        except (OSError, UnicodeError, json.JSONDecodeError) as err:
            errors.append({"file": path.relative_to(ROOT).as_posix(), "error": str(err)})

    report = {
        "mode": "fix" if args.fix else "check",
        "changed": len(changed),
        "files": changed,
        "errors": errors,
        "pass": not errors and (args.fix or not changed),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
