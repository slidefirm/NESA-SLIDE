from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = ROOT / "artifacts" / "deploy"
MANIFESTS = {
    DEPLOY_DIR / "layout-gallery.js": "window.LAYOUT_GALLERY = ",
    DEPLOY_DIR / "themes-gallery.js": "window.THEME_GALLERY = ",
    DEPLOY_DIR / "renderer-cases.js": "window.RENDERER_CASES = ",
}
REQUIRED_ENTRYPOINTS = (
    DEPLOY_DIR / "index.html",
)
OPTIONAL_ENTRYPOINTS = (
    DEPLOY_DIR / "theme-html-lab" / "index.html",
)
TEXT_DEPENDENCY_SUFFIXES = {".html", ".htm", ".css", ".js", ".mjs", ".cjs", ".json"}
STRUCTURED_REFERENCE_SUFFIXES = {".json", ".yaml", ".yml"}
STRUCTURED_SKIP_PREFIXES = (
    "artifacts/generated-prompts/staging/",
    "artifacts/deploy/review/",
)
ATTRIBUTE_REFERENCE_RE = re.compile(
    r"""(?:src|href|poster|data-src|data-href)\s*=\s*["']([^"'<>]+)["']""",
    re.IGNORECASE,
)
SRCSET_RE = re.compile(r"""srcset\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
CSS_URL_RE = re.compile(r"""url\(\s*["']?([^"'\)]+)["']?\s*\)""", re.IGNORECASE)
CSS_IMPORT_RE = re.compile(
    r"""@import\s+(?:url\(\s*)?["']([^"']+)["']""",
    re.IGNORECASE,
)
JS_REFERENCE_RE = re.compile(
    r"""(?:\bfrom\s*|\bimport\s*\(|\brequire\s*\(|\bfetch\s*\(|\bnew\s+URL\s*\()\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
REPOSITORY_PATH_RE = re.compile(
    r"(?P<path>(?:artifacts|prompt_system|references|scripts)[\\/][^\s\"'`<>#,\]}]+)",
    re.IGNORECASE,
)


def load_js_payload(path: Path, prefix: str) -> Any:
    text = path.read_text(encoding="utf-8").strip()
    if not text.startswith(prefix) or not text.endswith(";"):
        raise ValueError(f"Unexpected manifest wrapper: {path}")
    return json.loads(text[len(prefix) : -1])


def string_values(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from string_values(child)


def clean_reference(value: str) -> str | None:
    reference = unquote(value.split("#", 1)[0].split("?", 1)[0].strip())
    if not reference or reference.startswith(
        ("http://", "https://", "//", "data:", "mailto:", "javascript:", "blob:")
    ):
        return None
    return reference


def within_root(path: Path) -> bool:
    root = ROOT.resolve()
    return path == root or root in path.parents


def resolve_reference(value: str, owner: Path) -> Path | None:
    reference = clean_reference(value)
    if reference is None:
        return None

    normalized = reference.replace("/", "\\")
    reference_path = Path(normalized)
    candidates: list[Path] = []
    if reference.startswith("/"):
        candidates.append(DEPLOY_DIR / normalized.lstrip("\\"))
    elif reference.startswith(("artifacts/", "prompt_system/", "references/", "scripts/")):
        candidates.append(ROOT / reference_path)
    else:
        candidates.append(owner.parent / reference_path)
        if owner.parent != DEPLOY_DIR:
            candidates.append(DEPLOY_DIR / reference_path)

    for candidate in candidates:
        resolved = candidate.resolve()
        if not within_root(resolved):
            continue
        if resolved.is_file():
            return resolved
        index_path = resolved / "index.html"
        if resolved.is_dir() and index_path.is_file():
            return index_path.resolve()
    return None


def discover_text_references(path: Path) -> Iterator[str]:
    if path.suffix.lower() not in TEXT_DEPENDENCY_SUFFIXES:
        return

    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".json":
        try:
            yield from string_values(json.loads(text))
        except json.JSONDecodeError:
            return
        return

    if path.suffix.lower() in {".html", ".htm"}:
        yield from ATTRIBUTE_REFERENCE_RE.findall(text)
        for srcset in SRCSET_RE.findall(text):
            for candidate in srcset.split(","):
                value = candidate.strip().split(" ", 1)[0]
                if value:
                    yield value

    yield from CSS_URL_RE.findall(text)
    yield from CSS_IMPORT_RE.findall(text)
    if path.suffix.lower() in {".html", ".htm", ".js", ".mjs", ".cjs"}:
        yield from JS_REFERENCE_RE.findall(text)


def active_references() -> dict[Path, set[str]]:
    protected: dict[Path, set[str]] = defaultdict(set)
    pending: deque[tuple[Path, str]] = deque()

    def protect(path: Path, source: str) -> None:
        resolved = path.resolve()
        is_new = resolved not in protected
        protected[resolved].add(source)
        if is_new and resolved.suffix.lower() in TEXT_DEPENDENCY_SUFFIXES:
            pending.append((resolved, source))

    for manifest_path, prefix in MANIFESTS.items():
        if not manifest_path.is_file():
            raise FileNotFoundError(manifest_path)
        manifest_name = manifest_path.relative_to(ROOT).as_posix()
        protect(manifest_path, manifest_name)
        payload = load_js_payload(manifest_path, prefix)
        for value in string_values(payload):
            resolved = resolve_reference(value, manifest_path)
            if resolved is not None:
                protect(resolved, manifest_name)

    for entrypoint in REQUIRED_ENTRYPOINTS:
        if not entrypoint.is_file():
            raise FileNotFoundError(entrypoint)
        protect(entrypoint, entrypoint.relative_to(ROOT).as_posix())

    # The full development repository carries the deployed Theme Lab tree, while
    # the clone-first public source profile intentionally omits those large,
    # rebuildable deployment artifacts. Protect the Theme Lab transitively when
    # it is present, but do not make unrelated cleanup checks fail when it is not.
    for entrypoint in OPTIONAL_ENTRYPOINTS:
        if entrypoint.is_file():
            protect(entrypoint, entrypoint.relative_to(ROOT).as_posix())

    while pending:
        owner, root_source = pending.popleft()
        owner_name = owner.relative_to(ROOT).as_posix()
        for value in discover_text_references(owner):
            resolved = resolve_reference(value, owner)
            if resolved is not None:
                protect(resolved, f"{root_source} -> {owner_name}")

    return protected


def tracked_structured_sources() -> Iterator[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    for relative in result.stdout.decode("utf-8", errors="strict").split("\0"):
        if not relative or relative.startswith(STRUCTURED_SKIP_PREFIXES):
            continue
        path = ROOT / relative
        if path.suffix.lower() in STRUCTURED_REFERENCE_SUFFIXES and path.is_file():
            yield path.resolve()


def discover_structured_references(path: Path) -> Iterator[str]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if path.suffix.lower() == ".json":
        try:
            yield from string_values(json.loads(text))
        except json.JSONDecodeError:
            return
        return
    for match in REPOSITORY_PATH_RE.finditer(text):
        yield match.group("path").rstrip(".)")


def tracked_manifest_references() -> dict[Path, set[Path]]:
    references: dict[Path, set[Path]] = defaultdict(set)
    for owner in tracked_structured_sources():
        for value in discover_structured_references(owner):
            resolved = resolve_reference(value, owner)
            if resolved is not None:
                references[resolved].add(owner)
    return references


def resolve_candidate(value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Block cleanup targets containing files referenced directly or "
            "transitively by active Gallery entrypoints or by tracked JSON/YAML manifests."
        )
    )
    parser.add_argument("paths", nargs="+", help="File or directory cleanup candidates to check.")
    parser.add_argument("--show", type=int, default=20, help="Maximum protected references shown per target.")
    args = parser.parse_args()

    protected = active_references()
    manifest_references = tracked_manifest_references()
    blocked = False
    for raw_candidate in args.paths:
        candidate = resolve_candidate(raw_candidate)
        matches: dict[Path, set[str]] = defaultdict(set)
        for path, sources in protected.items():
            if path == candidate or candidate in path.parents:
                matches[path].update(sources)
        for path, owners in manifest_references.items():
            if path != candidate and candidate not in path.parents:
                continue
            outside_owners = {
                owner for owner in owners
                if owner != candidate and candidate not in owner.parents
            }
            matches[path].update(
                "tracked:" + owner.relative_to(ROOT).as_posix()
                for owner in outside_owners
            )
            if not matches[path]:
                del matches[path]
        if not matches:
            print(f"PASS {raw_candidate}: no active Gallery or tracked manifest references found")
            continue

        blocked = True
        print(f"BLOCKED {raw_candidate}: contains {len(matches)} active referenced files")
        for path in sorted(matches)[: args.show]:
            sources = ", ".join(sorted(matches[path]))
            print(f"- {path.relative_to(ROOT).as_posix()} <- {sources}")
        if len(matches) > args.show:
            print(f"- ... and {len(matches) - args.show} more")

    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
