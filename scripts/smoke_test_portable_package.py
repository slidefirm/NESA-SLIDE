"""Clone this repository into an isolated directory and prove it can still work.

A green audit inside the development worktree does not show that a fresh clone is
usable: several gates hash file bytes, and a working tree can carry local state that
never reaches Git. This script answers the question a package actually depends on —
after `git clone`, can someone start implementing every Skill?

Stages, each independently reported:

    clone            git clone of the requested ref into an empty directory
    path_lengths     longest tracked path leaves room for a real destination prefix
    line_endings     tracked text files check out as LF, so byte-hash gates match
    manifest         packaging/portable-manifest.yaml lists nothing that is missing
    imports          every required Python entry point imports
    skill_refs       every project path named by a Skill document resolves
    audit            scripts/audit.ps1 reports no FAIL
    render           an editable HTML deck is produced end to end

Usage:
    python scripts/smoke_test_portable_package.py
    python scripts/smoke_test_portable_package.py --workdir D:/tmp/probe --keep
    python scripts/smoke_test_portable_package.py --skip audit render
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_REL = "packaging/portable-manifest.yaml"
STAGES = ("clone", "path_lengths", "line_endings", "manifest", "imports", "skill_refs", "audit", "render")

# Windows caps a path at 260 characters unless every consumer opts into long paths.
# A repository whose longest tracked path leaves too little room cannot be cloned
# into an ordinary destination, which is a portability defect rather than a warning.
WINDOWS_PATH_LIMIT = 260
MIN_PREFIX_BUDGET = 80

# Entry points that must import in a clean checkout. A failure here means the
# dependency closure is wrong, which is invisible until someone clones.
IMPORT_ENTRYPOINTS = (
    "render_randomized_html_demo",
    "html_production_renderer",
    "generate_renderer_adapters",
    "generate_layout_gallery",
    "html_preset_registry",
    "art_direction",
    "pptx_variant_runtime",
    "compile_renderer_matrix",
)

SKILL_PATH_RE = re.compile(
    r"(?:^|[\s`'\"(\[])((?:scripts|references|prompt_system|src|docs|tools|\.agents)/[A-Za-z0-9_./\-]+)"
)

# A tracked text file expected to be pure LF after checkout.
LINE_ENDING_PROBES = (
    "prompt_system/themes/advocacy-network.yaml",
    "prompt_system/renderers/image2/themes/advocacy-network.yaml",
    "scripts/generate_renderer_adapters.py",
)


class Result:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []
        self.failed = False

    def add(self, stage: str, ok: bool, detail: str, *, fatal: bool = True) -> None:
        status = "PASS" if ok else ("FAIL" if fatal else "WARN")
        if not ok and fatal:
            self.failed = True
        self.rows.append((stage, status, detail))

    def report(self) -> int:
        width = max(len(s) for s, _, _ in self.rows)
        print()
        for stage, status, detail in self.rows:
            print(f"{stage.ljust(width)}  {status:<4}  {detail}")
        print()
        print("SMOKE TEST: " + ("FAIL" if self.failed else "PASS"))
        return 1 if self.failed else 0


def run(cmd: list[str], cwd: Path, timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace"
    )


def current_ref(source: Path) -> str:
    proc = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], source, timeout=60)
    ref = proc.stdout.strip()
    if not ref or ref == "HEAD":
        raise SystemExit("source is in detached HEAD; pass --ref explicitly")
    return ref


def stage_clone(result: Result, source: Path, target: Path, ref: str) -> bool:
    # core.longpaths is set for this command only; it never touches the user config.
    proc = run(
        ["git", "-c", "core.longpaths=true", "clone", "--quiet", "--single-branch",
         "--branch", ref, str(source), str(target)],
        ROOT,
    )
    if proc.returncode != 0:
        result.add("clone", False, (proc.stderr or proc.stdout).strip()[:160])
        return False
    count = sum(1 for p in target.rglob("*") if p.is_file() and ".git" not in p.parts)
    result.add("clone", True, f"{ref} -> {count} files")
    return True


def stage_path_lengths(result: Result, target: Path) -> None:
    proc = run(["git", "-c", "core.quotepath=false", "ls-files"], target, timeout=300)
    paths = [line for line in proc.stdout.splitlines() if line]
    if not paths:
        result.add("path_lengths", False, "no tracked files reported")
        return
    longest = max(paths, key=len)
    budget = WINDOWS_PATH_LIMIT - len(longest)
    owner = "/".join(longest.split("/")[:2])
    detail = f"longest {len(longest)} chars in {owner}; destination prefix budget {budget}"
    result.add("path_lengths", budget >= MIN_PREFIX_BUDGET, detail, fatal=False)


def stage_line_endings(result: Result, target: Path) -> None:
    offenders = []
    for rel in LINE_ENDING_PROBES:
        path = target / rel
        if not path.is_file():
            offenders.append(f"{rel} missing")
            continue
        if b"\r" in path.read_bytes():
            offenders.append(rel)
    result.add(
        "line_endings",
        not offenders,
        "all probes are LF" if not offenders else "CR found in: " + ", ".join(offenders),
    )


def stage_manifest(result: Result, target: Path) -> None:
    manifest_path = target / MANIFEST_REL
    if not manifest_path.is_file():
        result.add("manifest", False, f"{MANIFEST_REL} not in the clone")
        return
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    missing: list[str] = []
    for tree in manifest.get("core_trees", []):
        if not (target / tree).is_dir():
            missing.append(tree)
    for group in ("runtime_data", "runtime_data_entrypoints", "config_files"):
        for item in manifest.get(group, []):
            if not (target / item).exists():
                missing.append(item)
    for group in ("python", "node", "powershell"):
        for name in manifest.get("scripts", {}).get(group, []):
            if not (target / "scripts" / name).is_file():
                missing.append(f"scripts/{name}")
    total = manifest.get("counts", {}).get("scripts_required", "?")
    result.add(
        "manifest",
        not missing,
        f"{total} scripts + core trees present" if not missing else f"{len(missing)} missing: " + ", ".join(missing[:5]),
    )


def stage_imports(result: Result, target: Path) -> None:
    code = "import sys; sys.path.insert(0, 'scripts');" + "".join(
        f" import {name};" for name in IMPORT_ENTRYPOINTS
    )
    proc = run([sys.executable, "-c", code], target, timeout=600)
    ok = proc.returncode == 0
    detail = f"{len(IMPORT_ENTRYPOINTS)} entry points import" if ok else (proc.stderr or "").strip().splitlines()[-1][:150]
    result.add("imports", ok, detail)


def stage_skill_refs(result: Result, target: Path) -> None:
    skills_dir = target / ".agents" / "skills"
    if not skills_dir.is_dir():
        result.add("skill_refs", False, ".agents/skills missing")
        return
    missing: list[str] = []
    checked = 0
    for doc in sorted(skills_dir.rglob("*.md")):
        text = doc.read_text(encoding="utf-8", errors="replace")
        for match in SKILL_PATH_RE.finditer(text):
            rel = match.group(1).rstrip(".,;:`)")
            if "*" in rel:
                continue
            checked += 1
            candidates = [target / rel, doc.parent / rel]
            if not any(c.exists() for c in candidates):
                missing.append(f"{doc.relative_to(skills_dir).as_posix()} -> {rel}")
    unique = sorted(set(missing))
    result.add(
        "skill_refs",
        not unique,
        f"{checked} references resolve across {len(list(skills_dir.iterdir()))} Skills"
        if not unique
        else f"{len(unique)} unresolved: " + "; ".join(unique[:4]),
    )


def stage_audit(result: Result, target: Path) -> None:
    proc = run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "scripts/audit.ps1"], target, timeout=2400)
    text = proc.stdout + proc.stderr
    match = re.search(r"Audit summary: PASS=(\d+) WARN=(\d+) FAIL=(\d+)", text)
    if not match:
        result.add("audit", False, "no audit summary in output")
        return
    passed, warned, failed = (int(g) for g in match.groups())
    detail = f"PASS={passed} WARN={warned} FAIL={failed}"
    if failed:
        # Name the failing checks; a bare count cannot be acted on.
        names = [
            line.split("FAIL")[0].strip()
            for line in text.splitlines()
            if re.search(r"\sFAIL\s", line) and not line.startswith("Audit summary")
        ]
        unique = list(dict.fromkeys(n for n in names if n))
        if unique:
            detail += " -> " + "; ".join(unique[:4])
    result.add("audit", failed == 0, detail)


def stage_render(result: Result, target: Path, theme: str, seed: int) -> None:
    out = target / "smoke-deck.html"
    proc = run(
        [sys.executable, "scripts/render_randomized_html_demo.py",
         "--output", str(out), "--seed", str(seed), "--theme", theme],
        target,
        timeout=1800,
    )
    if not out.is_file():
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        result.add("render", False, tail[-1][:150] if tail else "no output produced")
        return
    html = out.read_text(encoding="utf-8", errors="replace")
    slides = html.count('class="slide"')
    editor = "edit-mode" in html or "editMode" in html
    ok = slides > 0 and editor
    result.add("render", ok, f"{slides} slides, editor embedded={editor}, {out.stat().st_size // 1024} KB")


def main() -> int:
    parser = argparse.ArgumentParser(description="Clone this repository and verify a fresh checkout is usable.")
    parser.add_argument("--source", default=str(ROOT), help="Repository to clone (default: this repository).")
    parser.add_argument("--ref", default=None, help="Branch to clone (default: the source's current branch).")
    parser.add_argument("--workdir", default=None, help="Empty directory for the clone (default: a temporary directory).")
    parser.add_argument("--keep", action="store_true", help="Keep the clone after the run.")
    parser.add_argument("--theme", default="brand-editorial", help="Theme for the render stage.")
    parser.add_argument("--seed", type=int, default=20260831, help="Seed for the render stage.")
    parser.add_argument("--skip", nargs="*", default=[], choices=STAGES, help="Stages to skip.")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    if not (source / ".git").exists():
        print(f"not a Git repository: {source}", file=sys.stderr)
        return 2

    ref = args.ref or current_ref(source)
    temporary = args.workdir is None
    workdir = Path(args.workdir).resolve() if args.workdir else Path(tempfile.mkdtemp(prefix="portable-smoke-"))
    target = workdir / "clone"
    if target.exists():
        print(f"target already exists: {target}", file=sys.stderr)
        return 2

    result = Result()
    try:
        if "clone" in args.skip:
            print("clone cannot be skipped", file=sys.stderr)
            return 2
        if not stage_clone(result, source, target, ref):
            return result.report()

        for stage, fn in (
            ("path_lengths", lambda: stage_path_lengths(result, target)),
            ("line_endings", lambda: stage_line_endings(result, target)),
            ("manifest", lambda: stage_manifest(result, target)),
            ("imports", lambda: stage_imports(result, target)),
            ("skill_refs", lambda: stage_skill_refs(result, target)),
            ("audit", lambda: stage_audit(result, target)),
            ("render", lambda: stage_render(result, target, args.theme, args.seed)),
        ):
            if stage in args.skip:
                result.add(stage, True, "skipped", fatal=False)
                continue
            fn()

        return result.report()
    finally:
        if args.keep:
            print(f"clone kept at {target}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)
            if temporary:
                print("clone removed")


if __name__ == "__main__":
    raise SystemExit(main())
