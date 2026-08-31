"""Compute and verify the portable-package file manifest.

The portable package is the subset of this repository that a fresh clone needs in
order to start implementing every Skill in `.agents/skills/`. It excludes produced
artifacts, which are evidence of past work rather than the system itself.

The manifest is derived, not hand-written. Three closures feed it:

1. Python import closure, seeded from every `scripts/*.py` that a rule file, Skill,
   reference, `audit.ps1`, `package.json` or the CI workflow invokes as a command.
2. Node `require` closure over `scripts/*.cjs|mjs|js`, transitively. This catches
   shared modules such as `playwright_runtime.cjs` that no document names but that
   24 QA scripts import; omitting them breaks every browser QA run.
3. Path references written inside Skill and reference documents.

Usage:
    python scripts/portable_manifest.py --write   # regenerate the manifest
    python scripts/portable_manifest.py --check   # fail if the manifest is stale
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
MANIFEST_PATH = ROOT / "packaging" / "portable-manifest.yaml"

# Files whose text may name a script as a command to run.
COMMAND_SOURCE_GLOBS = (
    ".agents/skills/**/*.md",
    "references/*.md",
)
COMMAND_SOURCE_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "package.json",
    "prompt_system/AGENTS.md",
    "scripts/AGENTS.md",
    "scripts/audit.ps1",
    ".github/workflows/repository-audit.yml",
)

SCRIPT_COMMAND_RE = re.compile(r"scripts[/\\]([A-Za-z0-9_.\-]+\.(?:py|cjs|mjs|js|ps1))")
NODE_REQUIRE_RE = re.compile(
    r"""require\(\s*['"]\./([A-Za-z0-9_.\-]+)['"]|from\s+['"]\./([A-Za-z0-9_.\-]+)['"]"""
)

# Directories copied whole. These are the system itself, not its output.
CORE_TREES = (
    "prompt_system",
    "references",
    "src",
    ".agents/skills",
    ".codex",
    "docs",
)

# Records of past cleanup, retirement and discarded work. They document what this
# repository stopped doing; a package built from them invites an agent to treat
# abandoned approaches as current. Excluded only when nothing kept still links to
# them — build_portable_package.py fails on a dangling reference.
HISTORICAL_EXCLUSIONS = (
    "references/cleanup-ledger-20260805.md",
    "references/cleanup-ledger-20260829.md",
    "references/discarded-artifacts-20260722.md",
    "references/project-architecture-cleanup-20260726.md",
    "references/retired-project-features.md",
    "references/html-theme-lab-design-archive.md",
    "prompt_system/HANDOFF.md",
)

# Individual files the runtime reads. Everything else under artifacts/ is output.
# The three html-test assets are embedded into every rendered deck; without them
# render_randomized_html_demo raises before writing anything.
RUNTIME_DATA = (
    "artifacts/renderer-matrix/matrix.json",
    "artifacts/renderer-matrix/renderer-matrix.json",
    "artifacts/html-test/edit-mode.js",
    "artifacts/html-test/pptx-browser-export.js",
    "artifacts/html-test/pptxgen.bundle.js",
    "artifacts/qa/layout-preview-qa.jsonl",
)

# Gallery visuals. WebP is what the pages load; PNG originals are 189 MB of
# duplicate pixels and stay behind.
RUNTIME_DATA_GLOBS = (
    "artifacts/deploy/layout-previews/*.webp",
    "artifacts/deploy/layout-previews/*.svg",
    "artifacts/deploy/layout-variants/*.webp",
    "artifacts/deploy/layout-style-cases/*.webp",
)

# Gallery assets. WebP is what the pages load; PNG originals stay local.
RUNTIME_DATA_TREES = (
    "artifacts/deploy/layout-gallery.js",
    "artifacts/deploy/themes-gallery.js",
    "artifacts/deploy/renderer-cases.js",
    "artifacts/deploy/index.html",
)

# Output roots are rewritten at package time so that work done inside a package
# lands in workspace/ instead of mixing into the artifacts/ tree that shipped with
# it. Without this, a recipient cannot tell their own output from the reference
# data, which is the same confusion this package exists to avoid.
# Each entry is (path glob, literal to replace, replacement).
PATH_TRANSFORMS = (
    (
        "scripts/html_image_background_experiment.py",
        'ROOT / "artifacts" / "experiments" / "html-image-background"',
        'ROOT / "workspace" / "html-image-background"',
    ),
    (".agents/skills/*/SKILL.md", "artifacts/experiments/html-image-background", "workspace/html-image-background"),
    (".agents/skills/*/SKILL.md", "artifacts/pptx/", "workspace/pptx/"),
    (".agents/skills/*/SKILL.md", "artifacts/generated-prompts/", "workspace/generated-prompts/"),
    (".claude/skills/*/SKILL.md", "artifacts/experiments/html-image-background", "workspace/html-image-background"),
    (".claude/skills/*/SKILL.md", "artifacts/pptx/", "workspace/pptx/"),
    (".claude/skills/*/SKILL.md", "artifacts/generated-prompts/", "workspace/generated-prompts/"),
)

# The public source profile already excludes deployment-only Gallery URLs, so no
# additional content sanitization is needed when producing the portable package.
PACKAGE_SANITIZATIONS: tuple[dict, ...] = ()

# Identity written into the package's package.json. The repository's own values name
# a local QA dependency set, which is misleading once the tree is handed to someone.
PACKAGE_IDENTITY = {
    "name": "nesa-slide-portable",
    "version": "0.2.0",
    "description": "Portable AI presentation layout system: Theme and Layout core, renderer adapters and Skills.",
}

# What each Skill needs from outside the package. A recipient missing `node` should
# learn which Skills stop working, not discover it when one fails.
EXTERNAL_CAPABILITIES = (
    {
        "id": "python",
        "gate": "CPython 3.13 with the packages in requirements.txt",
        "vendored": False,
        "required_for": ["all"],
    },
    {
        "id": "model-image-generation",
        "gate": "a built-in image_gen tool, or an explicitly authorised CLI fallback",
        "vendored": False,
        "required_for": ["generate-image-slide", "html-image-slide", "slide-background-image"],
        "note": "Seven-stage YAML authoring works without it; only formal bitmap output is gated.",
    },
    {
        "id": "node",
        "gate": "Node.js 22 or newer, with npm install run inside the package",
        "vendored": False,
        "required_for": ["html-pattern-slide", "html-image-slide", "slide-background-image", "ppt-builder"],
        "note": "Browser QA scripts and the PPTX export runtime are Node programs.",
    },
    {
        "id": "browser",
        "gate": "a real local browser for Playwright-driven QA",
        "vendored": False,
        "required_for": ["html-pattern-slide", "html-image-slide", "slide-background-image"],
    },
    {
        "id": "pptx-native-builder",
        "gate": "the Codex runtime that provides the presentations artifact tool",
        "vendored": False,
        "required_for": ["ppt-builder"],
        "note": "Theme/Layout core and the PPTX adapters are portable; only the native build step is gated.",
    },
    {
        "id": "powerpoint",
        "gate": "optional desktop PowerPoint for native rendering QA",
        "vendored": False,
        "required_for": ["ppt-builder"],
        "optional": True,
    },
)

CONFIG_FILES = (
    ".gitattributes",
    ".gitignore",
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "requirements.txt",
    "package.json",
    "package-lock.json",
    ".github/workflows/repository-audit.yml",
    "demos/html/demo-deck.html",
    "demos/html/demo-deck.manifest.json",
    "demos/html/edit-mode.js",
    "demos/html/favicon.svg",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def command_sources() -> list[Path]:
    found: list[Path] = []
    for pattern in COMMAND_SOURCE_GLOBS:
        found.extend(sorted(ROOT.glob(pattern)))
    for name in COMMAND_SOURCE_FILES:
        path = ROOT / name
        if path.is_file():
            found.append(path)
    return found


def invoked_scripts() -> set[str]:
    """Script filenames named as commands by rule files, Skills or CI."""
    names: set[str] = set()
    for source in command_sources():
        for match in SCRIPT_COMMAND_RE.finditer(read_text(source)):
            names.add(match.group(1))
    return {n for n in names if (SCRIPTS / n).is_file()}


def python_import_graph() -> dict[str, set[str]]:
    modules = {p.stem for p in SCRIPTS.glob("*.py")}
    graph: dict[str, set[str]] = {}
    for path in SCRIPTS.glob("*.py"):
        deps: set[str] = set()
        try:
            tree = ast.parse(read_text(path))
        except SyntaxError:
            graph[path.stem] = deps
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    head = alias.name.split(".")[0]
                    if head in modules:
                        deps.add(head)
            elif isinstance(node, ast.ImportFrom) and node.module:
                head = node.module.split(".")[0]
                if head in modules:
                    deps.add(head)
        graph[path.stem] = deps
    return graph


def node_require_graph() -> dict[str, set[str]]:
    files = {p.name for p in SCRIPTS.iterdir() if p.suffix in {".cjs", ".mjs", ".js"}}
    graph: dict[str, set[str]] = {}
    for name in files:
        deps: set[str] = set()
        for match in NODE_REQUIRE_RE.finditer(read_text(SCRIPTS / name)):
            target = match.group(1) or match.group(2)
            for candidate in (target, f"{target}.cjs", f"{target}.js", f"{target}.mjs"):
                if candidate in files:
                    deps.add(candidate)
                    break
        graph[name] = deps
    return graph


def close_over(seeds: Iterable[str], graph: dict[str, set[str]]) -> set[str]:
    seen: set[str] = set()
    stack = [s for s in seeds if s in graph]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(graph.get(current, ()))
    return seen


# Generators for derived data the package ships. No document invokes them by name,
# so the closures cannot reach them — but a package that carries a generated file
# without its generator cannot rebuild that file after the core changes.
GENERATORS_FOR_SHIPPED_DATA = {
    "compile_renderer_matrix.py": "artifacts/renderer-matrix/matrix.json",
    "verify_renderer_matrix.py": "artifacts/renderer-matrix/matrix.json",
}


def required_scripts() -> dict[str, list[str]]:
    invoked = invoked_scripts()

    py_graph = python_import_graph()
    py_seeds = [n[:-3] for n in invoked if n.endswith(".py")]
    py_seeds += [n[:-3] for n in GENERATORS_FOR_SHIPPED_DATA if (SCRIPTS / n).is_file()]
    python = sorted(f"{m}.py" for m in close_over(py_seeds, py_graph))

    node_graph = node_require_graph()
    node_seeds = [n for n in invoked if n.endswith((".cjs", ".mjs", ".js"))]
    node = sorted(close_over(node_seeds, node_graph))

    powershell = sorted(n for n in invoked if n.endswith(".ps1"))

    # Shared modules reached only through require(); surfaced for review because
    # they are the failure mode a hand-written whitelist misses.
    shared = sorted(set(node) - set(node_seeds))

    return {
        "python": python,
        "node": node,
        "powershell": powershell,
        "node_shared_modules_not_named_in_docs": shared,
        "generators_for_shipped_data": dict(sorted(GENERATORS_FOR_SHIPPED_DATA.items())),
    }


def excluded_count() -> int:
    """Scripts on disk that the manifest does not require. Reported, never stored:
    it counts untracked files too, so it differs between a working tree and a clone."""
    scripts = required_scripts()
    included = set(scripts["python"]) | set(scripts["node"]) | set(scripts["powershell"])
    present = {p.name for p in SCRIPTS.iterdir() if p.is_file()}
    return len(present - included)


def build_manifest() -> dict:
    scripts = required_scripts()
    total = len(scripts["python"]) + len(scripts["node"]) + len(scripts["powershell"])
    return {
        "schema_version": 1,
        "generated_by": "scripts/portable_manifest.py",
        "purpose": (
            "Files a fresh clone needs in order to start implementing every Skill in "
            ".agents/skills/. Produced artifacts are excluded."
        ),
        "counts": {"scripts_required": total},
        "core_trees": list(CORE_TREES),
        "historical_exclusions": list(HISTORICAL_EXCLUSIONS),
        "path_transforms": [
            {"path": p, "from": old, "to": new} for p, old, new in PATH_TRANSFORMS
        ],
        "package_sanitizations": [dict(s) for s in PACKAGE_SANITIZATIONS],
        "package_identity": dict(PACKAGE_IDENTITY),
        "external_capabilities": [dict(c) for c in EXTERNAL_CAPABILITIES],
        "runtime_data": list(RUNTIME_DATA),
        "runtime_data_entrypoints": list(RUNTIME_DATA_TREES),
        "runtime_data_globs": list(RUNTIME_DATA_GLOBS),
        "config_files": list(CONFIG_FILES),
        "scripts": scripts,
        "generated_at_package_time": {
            ".claude/skills": (
                "Generated from .agents/skills at packaging time, never copied as a "
                "second source. .gitignore excludes .claude/, so a clone otherwise has "
                "no auto-discovered Skill; and the two mirrors have already drifted."
            )
        },
        "excluded": {
            "produced_artifacts": (
                "Everything under artifacts/ except the runtime_data entries. These "
                "record what was made, not how to make it."
            ),
            "node_modules": "Rebuilt with npm install.",
            "sites-random-layout-catalog": "Independent Git repository; see its own AGENTS.md.",
        },
        "provider_required_capabilities": {
            "image2_formal_generation": (
                "Seven-stage YAML authoring is portable; formal bitmap generation needs "
                "a model image provider."
            ),
            "pptx_native_build": (
                "Theme/Layout core and PPTX adapters are portable; the native builder "
                "currently depends on a Codex runtime."
            ),
        },
    }


def load_manifest() -> dict | None:
    if not MANIFEST_PATH.is_file():
        return None
    return yaml.safe_load(read_text(MANIFEST_PATH))


def write_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False, width=100)
    MANIFEST_PATH.write_text(text, encoding="utf-8", newline="\n")


def missing_paths(manifest: dict) -> list[str]:
    missing: list[str] = []
    for tree in manifest.get("core_trees", []):
        if not (ROOT / tree).is_dir():
            missing.append(tree)
    for group in ("runtime_data", "runtime_data_entrypoints", "config_files"):
        for item in manifest.get(group, []):
            if not (ROOT / item).exists():
                missing.append(item)
    for group in ("python", "node", "powershell"):
        for name in manifest.get("scripts", {}).get(group, []):
            if not (SCRIPTS / name).is_file():
                missing.append(f"scripts/{name}")
    # A capability that names a Skill which no longer exists tells the recipient
    # nothing useful, so treat it the same as a missing file.
    skills = {p.name for p in (ROOT / ".agents" / "skills").iterdir() if p.is_dir()}
    for capability in manifest.get("external_capabilities", []):
        for skill in capability.get("required_for", []):
            if skill != "all" and skill not in skills:
                missing.append(f"external_capabilities[{capability['id']}] -> unknown Skill {skill}")
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute or verify the portable-package file manifest."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Regenerate the manifest file.")
    mode.add_argument("--check", action="store_true", help="Fail if the manifest is stale or incomplete.")
    args = parser.parse_args()

    expected = build_manifest()

    if args.write:
        write_manifest(expected)
        print(
            f"wrote {MANIFEST_PATH.relative_to(ROOT).as_posix()}: "
            f"{expected['counts']['scripts_required']} scripts required, "
            f"{excluded_count()} present on disk but excluded"
        )
        shared = expected["scripts"]["node_shared_modules_not_named_in_docs"]
        if shared:
            print("shared Node modules reached only via require(): " + ", ".join(shared))
        return 0

    # Inside a built package the manifest describes how that package was produced,
    # not the tree it now sits in: the package deliberately carries a subset of
    # scripts, so recomputing the closure here would always look stale. The check
    # belongs to the source repository, which has no PACKAGE_INFO.json.
    if (ROOT / "PACKAGE_INFO.json").is_file():
        print("inside a built package; the manifest check applies to the source repository")
        return 0

    current = load_manifest()
    if current is None:
        print(f"MISSING {MANIFEST_PATH.relative_to(ROOT).as_posix()}", file=sys.stderr)
        return 1

    problems: list[str] = []
    if current != expected:
        problems.append("manifest is stale; rerun with --write")
    for path in missing_paths(current):
        problems.append(f"listed path does not exist: {path}")

    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1

    counts = current["counts"]
    print(
        f"verified {counts['scripts_required']} required scripts and "
        f"{len(current['core_trees'])} core trees"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
