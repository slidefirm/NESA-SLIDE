#!/usr/bin/env python3
"""Build deterministic NESA-SLIDE source or portable release folders.

The builder operates only on a staged source tree. It refuses to reuse an
output folder, records a closure report, and creates a hash ledger without
embedding a wall-clock build timestamp.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover - surfaced as a capability gate
    raise SystemExit("PyYAML is required; install requirements.txt before building.") from exc


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys instead of silently using the last value."""


def _construct_unique_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"Duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping)


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".cjs",
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}
REQUIRED_SKILLS = (
    "design-presentations",
    "slide-outline-planner",
    "generate-image-slide",
    "html-image-slide",
    "html-pattern-slide",
    "ppt-builder",
    "slide-background-image",
)
DYNAMIC_CATALOG_DIRS = (
    "prompt_system/art_direction",
    "prompt_system/layouts",
    "prompt_system/presets",
    "prompt_system/pptx_background_sets",
    "prompt_system/renderers",
    "prompt_system/themes",
    "src/html-editor",
)
EXTERNAL_CAPABILITIES = (
    "browser",
    "codex-image-gen",
    "node",
    "powerpoint",
    "presentations-artifact-tool",
    "python",
)
EXPECTED_CATALOG_COUNTS = {
    "themes": 36,
    "active_layouts": 75,
    "adapters": 333,
    "html_preset_definitions": 37,
    "html_auto_select_presets": 4,
}
REQUIRED_ARTIFACT_RUNTIME = {
    "artifacts/html-test/edit-mode.js",
    "artifacts/html-test/pptxgen.bundle.js",
    "artifacts/html-test/pptx-browser-export.js",
    "artifacts/html-test/dev_server.py",
    "artifacts/html-test/test_dev_server.py",
    "artifacts/pptx/runtime/package.json",
    "artifacts/renderer-matrix/matrix.json",
}
RELEVANT_TESTS_MANIFEST = "release/relevant-tests.txt"
PRESENTATIONS_EXTERNAL_DOCS = {
    "references/layout.spec.md",
    "references/master.spec.md",
}
PORTABLE_PATH_REPLACEMENTS = (
    ("artifacts/generated-prompts/", "workspace/generated-prompts/"),
    ("artifacts/html-presentations/", "workspace/html-presentations/"),
    ("artifacts/pptx-backgrounds/", "workspace/pptx-backgrounds/"),
    ("artifacts/pptx/", "workspace/pptx/"),
    ("artifacts/qa/", "workspace/qa/"),
    ("artifacts/experiments/", "workspace/"),
    ("artifacts/deploy/", "workspace/deploy/"),
)


def posix(path: Path) -> str:
    return path.as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.load(handle, Loader=UniqueKeyLoader)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def read_relevant_tests(root: Path = ROOT) -> tuple[str, ...]:
    """Read the exact source-release unittest inventory.

    The source package deliberately ships only release-facing tests.  Keeping
    this list separate from the parent monorepo prevents gallery/history
    fixtures from silently becoming a public release gate.
    """

    manifest = root / RELEVANT_TESTS_MANIFEST
    if not manifest.is_file():
        raise FileNotFoundError(f"Missing relevant test manifest: {RELEVANT_TESTS_MANIFEST}")
    tests = tuple(
        line.strip().replace("\\", "/")
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if not tests:
        raise ValueError("release/relevant-tests.txt must declare at least one test")
    if len(set(tests)) != len(tests):
        raise ValueError("release/relevant-tests.txt contains duplicate test paths")
    for relative in tests:
        if not relative.startswith("tests/test_") or not relative.endswith(".py"):
            raise ValueError(f"Invalid release test path: {relative}")
        if not (root / relative).is_file():
            raise FileNotFoundError(f"Release test does not exist: {relative}")
    return tests


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def path_is_excluded(relative: str, patterns: Iterable[str]) -> bool:
    candidate = PurePosixPath(relative)
    return any(
        fnmatch.fnmatch(relative, pattern)
        or candidate.match(pattern)
        or (pattern.startswith("**/") and fnmatch.fnmatch(relative, pattern[3:]))
        for pattern in patterns
    )


def copy_root(source_root: Path, destination_root: Path, entry: str, excludes: list[str]) -> None:
    source = source_root / entry
    if not source.exists():
        raise FileNotFoundError(f"Package manifest references missing entry: {entry}")
    if source.is_file():
        if not path_is_excluded(entry, excludes):
            target = destination_root / entry
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        return
    for child in sorted(source.rglob("*"), key=lambda item: posix(item.relative_to(source_root))):
        if not child.is_file():
            continue
        relative = posix(child.relative_to(source_root))
        if path_is_excluded(relative, excludes):
            continue
        target = destination_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(child, target)


def ensure_skill_contract(destination_root: Path) -> list[str]:
    missing = []
    skill_root = destination_root / ".agents" / "skills"
    present = {item.name for item in skill_root.iterdir() if item.is_dir()} if skill_root.exists() else set()
    for skill in REQUIRED_SKILLS:
        skill_file = skill_root / skill / "SKILL.md"
        openai_file = skill_root / skill / "agents" / "openai.yaml"
        if not skill_file.is_file():
            missing.append(posix(skill_file.relative_to(destination_root)))
        if not openai_file.is_file():
            missing.append(posix(openai_file.relative_to(destination_root)))
    unexpected = sorted(present - set(REQUIRED_SKILLS))
    if unexpected:
        missing.extend(f"unexpected-skill:{skill}" for skill in unexpected)
    return missing


def sanitize_source_snapshot(destination_root: Path) -> None:
    snapshot = destination_root / "release" / "source-allowlist-snapshot.json"
    if not snapshot.is_file():
        return
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    data["source_root"] = "."
    data["portable_path_policy"] = "repository-relative-posix"
    write_json(snapshot, data)


def transform_portable_paths(destination_root: Path) -> list[dict[str, str]]:
    transformed: list[dict[str, str]] = []
    for path in sorted(destination_root.rglob("*"), key=lambda item: posix(item.relative_to(destination_root))):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = posix(path.relative_to(destination_root))
        if relative.startswith(("artifacts/", "release/")):
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated = original
        for source, replacement in PORTABLE_PATH_REPLACEMENTS:
            updated = updated.replace(source, replacement)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            transformed.append(
                {
                    "path": posix(path.relative_to(destination_root)),
                    "operation": "artifact-output-path-to-workspace",
                }
            )
    write_json(
        destination_root / "release" / "portable-path-transforms.json",
        {"schema_version": 1, "transforms": transformed},
    )
    return transformed


def normalize_reference(raw: str) -> str | None:
    candidate = raw.strip().strip("`'\"()[]{}<>.,;:")
    if not candidate:
        return None
    candidate = candidate.split("#", 1)[0]
    candidate = candidate.replace("\\", "/")
    candidate = re.sub(r"/\*.*$", "", candidate)
    if candidate.startswith("./"):
        candidate = candidate[2:]
    if candidate.startswith((".agents/", "artifacts/", "prompt_system/", "references/", "scripts/", "src/", "workspace/")):
        return candidate.rstrip("/")
    return None


PATH_REFERENCE = re.compile(
    r"(?<![A-Za-z0-9_.-])((?:\.agents|artifacts|prompt_system|references|scripts|src|workspace)/[A-Za-z0-9_./@+()\-\u4e00-\u9fff]+)"
)
JS_IMPORT = re.compile(r"(?:from|require\()\s*[\"']([^\"']+)[\"']")
PY_IMPORT = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_.]*)", re.MULTILINE)


def local_import_targets(path: Path, text: str, destination_root: Path) -> set[str]:
    targets: set[str] = set()
    if path.suffix == ".py":
        for module in PY_IMPORT.findall(text):
            if module.startswith("scripts."):
                targets.add(module.replace(".", "/") + ".py")
            elif module.startswith("src."):
                targets.add(module.replace(".", "/") + ".py")
            else:
                base = module.split(".", 1)[0]
                candidates = (
                    path.parent / f"{base}.py",
                    destination_root / "scripts" / f"{base}.py",
                    destination_root / f"{base}.py",
                )
                for candidate in candidates:
                    if candidate.is_file():
                        targets.add(posix(candidate.relative_to(destination_root)))
                        break
    if path.suffix in {".js", ".mjs", ".cjs"}:
        for module in JS_IMPORT.findall(text):
            if not module.startswith("."):
                continue
            candidate = (path.parent / module).resolve()
            for possible in (candidate, candidate.with_suffix(".js"), candidate.with_suffix(".mjs"), candidate.with_suffix(".cjs")):
                try:
                    relative = possible.relative_to(destination_root.resolve())
                except ValueError:
                    continue
                if possible.exists():
                    targets.add(posix(relative))
                    break
    return targets


def build_closure(destination_root: Path, profile: str) -> dict[str, Any]:
    records: dict[str, dict[str, Any]] = {}
    missing: set[str] = set()
    queue: list[str] = []
    visited: set[str] = set()

    def add_required(relative: str, reason: str) -> None:
        relative = normalize_reference(relative) or relative
        if relative.startswith("workspace"):
            records.setdefault(
                relative,
                {"path": relative, "classification": "output-placeholder", "reason": reason},
            )
            return
        if relative.startswith("artifacts/") and relative not in REQUIRED_ARTIFACT_RUNTIME:
            records.setdefault(
                "workspace/" + relative.removeprefix("artifacts/"),
                {
                    "path": "workspace/" + relative.removeprefix("artifacts/"),
                    "classification": "output-placeholder",
                    "reason": f"generated-artifact-ref:{reason}",
                },
            )
            return
        if relative.startswith("prompt_system/pptx_background_sets/") and not (destination_root / relative).exists():
            records.setdefault(
                "workspace/pptx-background-sets/" + Path(relative).name,
                {
                    "path": "workspace/pptx-background-sets/" + Path(relative).name,
                    "classification": "output-placeholder",
                    "reason": f"generation-required-background-set:{reason}",
                },
            )
            return
        target = destination_root / relative
        if not target.exists():
            if relative.startswith("scripts/") and not Path(relative).suffix:
                records.setdefault(
                    relative,
                    {"path": relative, "classification": "output-placeholder", "reason": f"non-concrete-pattern:{reason}"},
                )
                return
            missing.add(relative)
            return
        if target.is_dir():
            for child in sorted(target.rglob("*"), key=lambda item: posix(item.relative_to(destination_root))):
                if child.is_file():
                    add_required(posix(child.relative_to(destination_root)), f"dynamic-catalog:{relative}")
            return
        records.setdefault(
            relative,
            {"path": relative, "classification": "required", "reason": reason},
        )
        if target.suffix.lower() in TEXT_SUFFIXES and relative not in visited:
            queue.append(relative)

    def add_external(path: str, reason: str) -> None:
        records.setdefault(
            f"external:{path}",
            {"path": path, "classification": "external-capability", "reason": reason},
        )

    def resolve_inline_reference(source_relative: str, target: str) -> tuple[str | None, str | None]:
        source = destination_root / source_relative
        skill_local = source.parent / target
        if source_relative.startswith(".agents/skills/") and skill_local.exists():
            return posix(skill_local.relative_to(destination_root)), None
        if source_relative.startswith(".agents/skills/ppt-builder/") and target in PRESENTATIONS_EXTERNAL_DOCS:
            return None, "presentations-skill-docs"
        return target, None

    for skill in REQUIRED_SKILLS:
        add_required(f".agents/skills/{skill}/SKILL.md", "skill-entrypoint")
        add_required(f".agents/skills/{skill}/agents/openai.yaml", "skill-metadata")
    for runtime_asset in sorted(REQUIRED_ARTIFACT_RUNTIME):
        add_required(runtime_asset, "runtime-allowlist")
    for directory in DYNAMIC_CATALOG_DIRS:
        add_required(directory, "dynamic-catalog")
    add_required("workspace", "portable-output-root")

    while queue:
        relative = queue.pop()
        if relative in visited:
            continue
        visited.add(relative)
        path = destination_root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in PATH_REFERENCE.findall(text):
            target = normalize_reference(match)
            if target:
                resolved, external = resolve_inline_reference(relative, target)
                if external:
                    add_external(target, f"{external}:{relative}")
                elif resolved:
                    add_required(resolved, f"inline-ref:{relative}")
        for target in local_import_targets(path, text, destination_root):
            add_required(target, f"local-import:{relative}")

    for capability in EXTERNAL_CAPABILITIES:
        records.setdefault(
            f"external:{capability}",
            {
                "path": capability,
                "classification": "external-capability",
                "reason": "system-managed capability; not vendored",
            },
        )
    ordered_records = [records[key] for key in sorted(records)]
    return {
        "schema_version": 2,
        "profile": profile,
        "entrypoints": [f".agents/skills/{skill}/SKILL.md" for skill in REQUIRED_SKILLS],
        "dynamic_catalog_dirs": list(DYNAMIC_CATALOG_DIRS),
        "external_capabilities": list(EXTERNAL_CAPABILITIES),
        "output_placeholders": ["workspace"],
        "records": ordered_records,
        "missing": sorted(missing),
        "pass": not missing,
    }


def catalog_counts(destination_root: Path) -> dict[str, int]:
    renderer_manifest = read_yaml(destination_root / "prompt_system" / "renderers" / "manifest.yaml")
    stats = renderer_manifest.get("counts", {})
    presets = read_yaml(destination_root / "prompt_system" / "presets" / "catalog.yaml")
    preset_themes = read_yaml(destination_root / "prompt_system" / "renderers" / "html" / "preset-themes.yaml")
    themes = preset_themes.get("themes", {})
    counts = {
        "themes": len(list((destination_root / "prompt_system" / "themes").glob("*.yaml"))),
        "active_layouts": int(stats.get("layouts", 0)),
        "adapters": int(stats.get("total_adapters", 0)),
        "html_preset_definitions": len(presets.get("entries", [])),
        "html_auto_select_presets": sum(
            1 for value in themes.values() if isinstance(value, dict) and value.get("auto_select") is True
        ),
    }
    if counts != EXPECTED_CATALOG_COUNTS:
        raise ValueError(f"Live catalog baseline drift: expected {EXPECTED_CATALOG_COUNTS}, actual {counts}")
    return counts


def release_manifest(destination_root: Path, profile: str, version: str, transforms: list[dict[str, str]]) -> dict[str, Any]:
    showcase_manifest = json.loads((destination_root / "showcase-manifest.json").read_text(encoding="utf-8"))
    showcase_rows = showcase_manifest.get("showcases") if isinstance(showcase_manifest.get("showcases"), list) else []
    return {
        "schema_version": 3,
        "package": "NESA-SLIDE",
        "version": version,
        "profile": profile,
        "supported_environment": "Codex Desktop on Windows",
        "license": "MIT",
        "copyright": "Slide Firm",
        "catalog_baseline": catalog_counts(destination_root),
        "skills": list(REQUIRED_SKILLS),
        "workspace_output_root": "workspace",
        "source_release_tests": RELEVANT_TESTS_MANIFEST,
        "source_snapshot": "release/source-allowlist-snapshot.json",
        "portable_path_transforms": transforms,
        "showcase_delivery": {
            "manifest": "showcase-manifest.json",
            "schema_version": showcase_manifest.get("schema_version"),
            "status": showcase_manifest.get("status"),
            "case_count": len(showcase_rows),
            "cases": [
                {
                    "id": item.get("id"),
                    "renderer": item.get("renderer"),
                    "page_count": item.get("page_count"),
                    "artifacts": item.get("artifacts"),
                    "qa_status": item.get("qa_status"),
                    "runtime_hashes": item.get("runtime_hashes"),
                }
                for item in showcase_rows if isinstance(item, dict)
            ],
        },
        "determinism": {
            "build_timestamp": "omitted",
            "inventory_order": "lexicographic-posix",
            "hash_algorithm": "sha256",
        },
        "manual_visual_matrix_boundary": "Not claimed: 36 themes x 75 active layouts is not manually visually accepted by this release manifest.",
    }


def prepare_workspace(destination_root: Path) -> None:
    workspace = destination_root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "README.md").write_text(
        "# Workspace\n\nThis directory is intentionally empty in a release package. "
        "Place generated decks, QA reports, PNGs and local run state here. Do not commit user workspace output.\n",
        encoding="utf-8",
    )


def validate_package_manifest(manifest: dict[str, Any], profile: str) -> tuple[dict[str, Any], list[str]]:
    if manifest.get("schema_version") != 1:
        raise ValueError("release/package-manifest.yaml must declare schema_version: 1")
    profile_key = f"{profile}_profile"
    profile_data = manifest.get(profile_key)
    if not isinstance(profile_data, dict):
        raise ValueError(f"release/package-manifest.yaml is missing mapping {profile_key}")
    include_roots = profile_data.get("include_roots")
    excludes = profile_data.get("exclude_globs")
    workspace = profile_data.get("workspace")
    if not isinstance(include_roots, list) or not include_roots or not all(isinstance(item, str) for item in include_roots):
        raise ValueError(f"{profile_key}.include_roots must be a non-empty string list")
    if not isinstance(excludes, list) or not all(isinstance(item, str) for item in excludes):
        raise ValueError(f"{profile_key}.exclude_globs must be a string list")
    if not isinstance(workspace, dict) or workspace.get("path") != "workspace":
        raise ValueError(f"{profile_key}.workspace.path must be workspace")
    for other in ("source_profile", "portable_profile"):
        if other not in manifest or not isinstance(manifest[other], dict):
            raise ValueError(f"release/package-manifest.yaml is missing mapping {other}")
    return profile_data, list(excludes)


def validate_relevant_test_contract(destination_root: Path, profile: str, relevant_tests: tuple[str, ...]) -> None:
    packaged = {
        posix(path.relative_to(destination_root))
        for path in (destination_root / "tests").glob("test_*.py")
    } if (destination_root / "tests").is_dir() else set()
    declared = set(relevant_tests)
    if profile == "source":
        if packaged != declared:
            raise RuntimeError(
                "Source release test inventory differs from release/relevant-tests.txt: "
                f"expected={sorted(declared)}, actual={sorted(packaged)}"
            )
    elif packaged:
        raise RuntimeError("Portable runtime must not package source unittest files")


def write_hash_ledgers(destination_root: Path) -> int:
    excluded = {"release-files.sha256", "SHA256SUMS.txt"}
    entries: list[tuple[str, str]] = []
    for path in sorted(destination_root.rglob("*"), key=lambda item: posix(item.relative_to(destination_root))):
        if not path.is_file():
            continue
        relative = posix(path.relative_to(destination_root))
        if relative in excluded or relative.startswith("workspace/"):
            continue
        entries.append((relative, sha256_file(path)))
    body = "".join(f"{digest}  {relative}\n" for relative, digest in entries)
    (destination_root / "release-files.sha256").write_text(body, encoding="utf-8")
    (destination_root / "SHA256SUMS.txt").write_text(body, encoding="utf-8")
    return len(entries)


def deterministic_zip(source_root: Path, archive: Path) -> None:
    if archive.exists():
        raise FileExistsError(f"Refusing to overwrite archive: {archive}")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(source_root.rglob("*"), key=lambda item: posix(item.relative_to(source_root))):
            if not path.is_file():
                continue
            relative = posix(path.relative_to(source_root))
            info = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes())


def build(profile: str, version: str, output: Path, archive: Path | None) -> dict[str, Any]:
    source_manifest = read_yaml(ROOT / "release" / "package-manifest.yaml")
    if version != str(source_manifest.get("version")):
        raise ValueError(f"Requested version {version} does not match package manifest {source_manifest.get('version')}")
    profile_data, excludes = validate_package_manifest(source_manifest, profile)
    relevant_tests = read_relevant_tests(ROOT)
    listed_tests = tuple(entry for entry in profile_data["include_roots"] if entry.startswith("tests/"))
    if "tests" in profile_data["include_roots"]:
        raise ValueError("Package profiles must not include the entire tests directory")
    if profile == "source" and set(listed_tests) != set(relevant_tests):
        raise ValueError("source_profile test entries must exactly match release/relevant-tests.txt")
    if profile == "portable" and listed_tests:
        raise ValueError("portable_profile must not include source unittest files")
    if output.exists():
        raise FileExistsError(f"Refusing to reuse output path: {output}")
    output.mkdir(parents=True, exist_ok=False)
    for entry in profile_data.get("include_roots", []):
        copy_root(ROOT, output, str(entry), excludes)
    validate_relevant_test_contract(output, profile, relevant_tests)
    sanitize_source_snapshot(output)
    prepare_workspace(output)
    transforms: list[dict[str, str]] = []
    if profile == "portable":
        transforms = transform_portable_paths(output)
    else:
        write_json(output / "release" / "portable-path-transforms.json", {"schema_version": 1, "transforms": []})
    missing_skill_contract = ensure_skill_contract(output)
    closure = build_closure(output, profile)
    closure["missing"] = sorted(set(closure["missing"]) | set(missing_skill_contract))
    closure["pass"] = not closure["missing"]
    write_json(output / "skill-dependency-closure.json", closure)
    if closure["missing"]:
        raise RuntimeError("Skill dependency closure has missing entries: " + ", ".join(closure["missing"][:8]))
    capabilities = json.loads((output / "release" / "external-capabilities.json").read_text(encoding="utf-8"))
    showcases = json.loads((output / "release" / "showcase-manifest.json").read_text(encoding="utf-8"))
    sanitizations = json.loads((output / "release" / "source-release-sanitizations.json").read_text(encoding="utf-8"))
    write_json(output / "external-capabilities.json", capabilities)
    write_json(output / "showcase-manifest.json", showcases)
    write_json(output / "release-sanitizations.json", sanitizations)
    write_json(output / "release-manifest.json", release_manifest(output, profile, version, transforms))
    ledger_entries = write_hash_ledgers(output)
    if archive is not None:
        deterministic_zip(output, archive)
    return {
        "pass": True,
        "profile": profile,
        "version": version,
        "output": posix(output),
        "archive": posix(archive) if archive else None,
        "ledger_entries": ledger_entries,
        "closure_missing": closure["missing"],
        "catalog_baseline": catalog_counts(output),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("source", "portable"), required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--zip", dest="archive", type=Path)
    args = parser.parse_args()
    try:
        result = build(args.profile, args.version, args.output.resolve(), args.archive.resolve() if args.archive else None)
    except Exception as exc:
        print(json.dumps({"pass": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
