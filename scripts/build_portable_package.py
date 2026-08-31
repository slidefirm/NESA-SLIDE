"""Build a standalone package from packaging/portable-manifest.yaml, and compare one
back against this repository.

The package is what another agent should be handed: the generation rules and the
code that applies them, without the 34 GB of produced artifacts, abandoned
experiments and retired-work records that surround them here. An agent reading
those would treat approaches this project already dropped as if they were current.

Two behaviours, because a package that cannot be re-synced rots:

    --output DIR    build the package
    --check DIR     compare a built package against the current repository

`--check` reads the ledger written at build time and reports, per file, whether the
repository has moved on. That turns "sync the demo after changing the main system"
from something a person has to remember into a list a tool produces.

Usage:
    python scripts/build_portable_package.py --output dist/slide-system-demo
    python scripts/build_portable_package.py --check  dist/slide-system-demo
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "packaging" / "portable-manifest.yaml"
ASSETS_DIR = ROOT / "packaging" / "package-assets"
LEDGER_NAME = "PACKAGE_INFO.json"
SYNC_NOTE_NAME = "SYNC.md"
SUMS_NAME = "SHA256SUMS.txt"

# Copied verbatim into the package root. These serve the recipient, not the build.
PACKAGE_ASSETS = ("CHECK_SYSTEM.py", "CHECK_SYSTEM.cmd", "OPEN_DEMO.cmd")
START_HERE_TEMPLATE = "START_HERE.md.template"

# Never copied, whatever a tree sweep would otherwise pick up.
SKIP_DIR_NAMES = {".git", "__pycache__", ".history", ".runtime", "node_modules"}
SKIP_SUFFIXES = {".pyc", ".pyo"}

# Used to detect links from kept documents into excluded ones.
DOC_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".txt"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        raise SystemExit(f"missing {MANIFEST_PATH.relative_to(ROOT).as_posix()}; run portable_manifest.py --write")
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def git_describe() -> dict:
    def git(*args: str) -> str:
        proc = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True)
        return proc.stdout.strip()

    dirty = bool(git("status", "--porcelain"))
    return {
        "commit": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "commit_time": git("show", "-s", "--format=%cI", "HEAD"),
        "worktree_clean": not dirty,
    }


def should_skip(path: Path) -> bool:
    if any(part in SKIP_DIR_NAMES for part in path.parts):
        return True
    return path.suffix in SKIP_SUFFIXES


def selected_files(manifest: dict) -> list[str]:
    """Repository-relative POSIX paths the package contains, in a stable order."""
    excluded = set(manifest.get("historical_exclusions", []))
    chosen: set[str] = set()

    for tree in manifest.get("core_trees", []):
        base = ROOT / tree
        if not base.is_dir():
            raise SystemExit(f"core tree missing: {tree}")
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            if should_skip(path.relative_to(ROOT)) or rel in excluded:
                continue
            chosen.add(rel)

    for name in manifest.get("scripts", {}).get("python", []) + manifest.get("scripts", {}).get(
        "node", []
    ) + manifest.get("scripts", {}).get("powershell", []):
        rel = f"scripts/{name}"
        if not (ROOT / rel).is_file():
            raise SystemExit(f"required script missing: {rel}")
        chosen.add(rel)

    for group in ("runtime_data", "runtime_data_entrypoints", "config_files"):
        for rel in manifest.get(group, []):
            if not (ROOT / rel).is_file():
                raise SystemExit(f"required file missing: {rel}")
            chosen.add(rel)

    for pattern in manifest.get("runtime_data_globs", []):
        matches = sorted(ROOT.glob(pattern))
        if not matches:
            raise SystemExit(f"glob matched nothing: {pattern}")
        for path in matches:
            if path.is_file():
                chosen.add(path.relative_to(ROOT).as_posix())

    chosen.add("packaging/portable-manifest.yaml")
    return sorted(chosen)


def referenced_exclusions(files: list[str], excluded: list[str]) -> dict[str, list[str]]:
    """Excluded files that a kept document still points at, mapped to their referrers.

    These cannot simply vanish: the referring document would then name a file that
    is not there. They are replaced by a stub instead, so the reference resolves and
    the reader learns why the content is absent.

    The manifest is not a referrer. Listing what it excludes is its job.
    """
    if not excluded:
        return {}
    names = {Path(rel).name: rel for rel in excluded}
    pattern = re.compile("|".join(re.escape(n) for n in names))
    found: dict[str, list[str]] = {}
    for rel in files:
        if Path(rel).suffix not in DOC_SUFFIXES or rel == "packaging/portable-manifest.yaml":
            continue
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        for match in set(pattern.findall(text)):
            found.setdefault(names[match], []).append(rel)
    return {k: sorted(v) for k, v in sorted(found.items())}


def write_exclusion_stub(package: Path, rel: str, referrers: list[str]) -> None:
    target = package / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    referrer_lines = "\n".join(f"- `{r}`" for r in referrers)
    target.write_text(
        f"""# 此檔案未包含在本套件中

原路徑：`{rel}`

這是主系統的歷史紀錄——過往清理、已退役功能或已捨棄的做法。內容可能包含
與現況不符的數量、目錄結構或流程，不可作為操作依據。

之所以保留這個檔案而非直接移除，是因為下列文件仍然引用它：

{referrer_lines}

需要目前狀態時，請讀 `prompt_system/AGENTS.md`、`prompt_system/README.md`
與 `references/` 底下的正式契約，或直接盤點 YAML。
""",
        encoding="utf-8",
        newline="\n",
    )


def apply_path_transforms(package: Path, manifest: dict) -> dict[str, list[str]]:
    """Rewrite output roots so work inside the package lands in workspace/.

    Applied after copying, and deliberately not reflected in the ledger hashes:
    the ledger records what the source looks like, so --check keeps comparing
    source against source rather than reporting every rewritten file as changed.
    """
    applied: dict[str, list[str]] = {}
    for rule in manifest.get("path_transforms", []):
        pattern, old, new = rule["path"], rule["from"], rule["to"]
        for path in sorted(package.glob(pattern)):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if old not in text:
                continue
            path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
            rel = path.relative_to(package).as_posix()
            applied.setdefault(rel, []).append(f"{old} -> {new}")
    return applied


def apply_sanitizations(package: Path, manifest: dict) -> list[dict]:
    """Strip content that describes something the package does not carry.

    A rule that matches nothing is an error, not a no-op: it means the source moved
    and the package would ship the very content the rule exists to remove.
    """
    applied: list[dict] = []
    for rule in manifest.get("package_sanitizations", []):
        target = package / rule["path"]
        if not target.is_file():
            raise SystemExit(f"sanitization target missing: {rule['path']}")
        pattern = re.compile(rule["remove_lines_matching"])
        lines = target.read_text(encoding="utf-8").splitlines()
        kept = [line for line in lines if not pattern.match(line)]
        removed = len(lines) - len(kept)
        if removed == 0:
            raise SystemExit(
                f"sanitization matched nothing in {rule['path']}: {rule['remove_lines_matching']}"
            )
        target.write_text("\n".join(kept) + "\n", encoding="utf-8", newline="\n")
        applied.append({"path": rule["path"], "removed_lines": removed, "reason": rule["reason"]})
    return applied


def apply_package_identity(package: Path, manifest: dict, version: str) -> dict | None:
    """Rename package.json for the package. The repository's own name and version
    describe a local QA dependency set, which misleads once handed to someone."""
    identity = manifest.get("package_identity")
    target = package / "package.json"
    if not identity or not target.is_file():
        return None
    data = json.loads(target.read_text(encoding="utf-8"))
    before = {k: data.get(k) for k in identity}
    identity = dict(identity)
    identity["version"] = version
    data.update(identity)
    data.pop("private", None)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    lock_target = package / "package-lock.json"
    if lock_target.is_file():
        lock = json.loads(lock_target.read_text(encoding="utf-8"))
        lock["name"] = identity["name"]
        lock["version"] = version
        root_package = lock.get("packages", {}).get("")
        if isinstance(root_package, dict):
            root_package["name"] = identity["name"]
            root_package["version"] = version
        lock_target.write_text(
            json.dumps(lock, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return {"before": before, "after": dict(identity), "lockfile_updated": lock_target.is_file()}


def purge_build_residue(package: Path) -> int:
    """Remove caches produced while building inside the package.

    Rendering the demo imports the packaged scripts, which writes __pycache__. Those
    files are build residue, not content, and must not reach the checksum list.
    """
    removed = 0
    for path in sorted(package.rglob("*.pyc")):
        path.unlink()
        removed += 1
    for directory in sorted(package.rglob("__pycache__"), reverse=True):
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    return removed


def create_workspace(package: Path) -> None:
    workspace = package / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "README.md").write_text(
        """# workspace

在這個套件裡做出來的東西一律寫在這裡。

`artifacts/` 底下是隨套件出貨的參考資料——版型預覽、渲染 runtime、QA 帳本——
不是工作區。兩者混在一起之後，就分不出哪些是原本就有的、哪些是你做的，
而那正是這個套件想避免的狀況。

Skill 文件裡的輸出路徑已在打包時改寫指向這裡，改寫紀錄見
`PACKAGE_INFO.json` 的 `path_transforms`。
""",
        encoding="utf-8",
        newline="\n",
    )


def verify_demo(package: Path) -> list[str]:
    """Verify that the committed, QA-approved demo was copied into the package.

    Rendering at package time writes wall-clock metadata and makes two builds from
    the same commit differ. End-to-end rendering remains a release Gate, while the
    shipped demo is the exact committed artifact that passed browser QA.
    """
    demo_dir = package / "demos" / "html"
    required = ("demo-deck.html", "demo-deck.manifest.json", "edit-mode.js", "favicon.svg")
    missing = [name for name in required if not (demo_dir / name).is_file()]
    if missing:
        raise SystemExit("committed demo files missing from package: " + ", ".join(missing))
    produced = [p.relative_to(package).as_posix() for p in sorted(demo_dir.rglob("*")) if p.is_file()]
    return produced


def write_checksums(package: Path) -> int:
    """Hashes of the files as shipped, for the recipient to verify delivery.

    Distinct from the ledger in PACKAGE_INFO.json, which records source hashes for
    comparing the package back against the repository.
    """
    lines: list[str] = []
    for path in sorted(package.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(package).as_posix()
        if rel in {SUMS_NAME}:
            continue
        lines.append(f"{sha256_file(path)}  {rel}")
    (package / SUMS_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return len(lines)


def copy_package_assets(package: Path) -> list[str]:
    copied: list[str] = []
    for name in PACKAGE_ASSETS:
        source = ASSETS_DIR / name
        if not source.is_file():
            raise SystemExit(f"package asset missing: {source.relative_to(ROOT).as_posix()}")
        shutil.copy2(source, package / name)
        copied.append(name)
    return copied


def write_start_here(
    package: Path,
    describe: dict,
    generated_at: str,
    version: str,
    file_count: int,
    megabytes: float,
) -> None:
    template = (ASSETS_DIR / START_HERE_TEMPLATE).read_text(encoding="utf-8")
    themes = len(list((package / "prompt_system" / "themes").glob("*.yaml")))
    layouts = len(list((package / "prompt_system" / "layouts").glob("*.yaml")))
    skills = len([p for p in (package / ".agents" / "skills").iterdir() if p.is_dir()])
    (package / "START_HERE.md").write_text(
        template.format(
            theme_count=themes,
            layout_count=layouts,
            skill_count=skills,
            version=version,
            commit=describe["commit"],
            generated_at=generated_at,
            file_count=file_count,
            megabytes=megabytes,
        ),
        encoding="utf-8",
        newline="\n",
    )


def mirror_claude_skills(package: Path) -> list[str]:
    """Produce .claude/skills from .agents/skills.

    Kept as a build step rather than a second checked-in copy: .gitignore excludes
    .claude/, so a clone otherwise exposes no auto-discovered Skill, and the two
    mirrors drift the moment both are maintained by hand.
    """
    source = package / ".agents" / "skills"
    target = package / ".claude" / "skills"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    return sorted(p.relative_to(package).as_posix() for p in target.rglob("*") if p.is_file())


def write_sync_note(package: Path, describe: dict) -> None:
    text = f"""# 與主系統同步

這份包由主系統的 `scripts/build_portable_package.py` 產生。

- 來源 commit：`{describe['commit']}`
- 來源分支：`{describe['branch']}`

## 主系統改動之後

在主系統執行：

```powershell
python scripts\\build_portable_package.py --check <這份包的路徑>
```

它會逐檔比對 `{LEDGER_NAME}` 記錄的 sha256 與主系統現況，列出：

- `changed`：主系統改過，這份包還是舊的
- `missing`：主系統已刪除
- `added`：主系統新增且清單要求，但這份包沒有
- `stale-manifest`：清單本身需要重新產生

確認清單後重新建置即可覆蓋。不要在這份包裡直接改檔案——
改了之後 `--check` 會把你的修改報成 `changed`，無法分辨是誰動的。

## 這份包不包含什麼

已產出的 artifact、實驗紀錄、歷史清理與退役文件都不在其中。
排除清單見 `packaging/portable-manifest.yaml` 的 `historical_exclusions`
與 `excluded` 兩節。

## 能力邊界

`packaging/portable-manifest.yaml` 的 `provider_required_capabilities` 記錄了
兩件事在這份包裡只能做到組裝、不能完成產出：Image2 正式生圖需要模型影像
provider，PPTX 原生產出需要 Codex runtime。HTML 產製與編輯不受此限。
"""
    (package / SYNC_NOTE_NAME).write_text(text, encoding="utf-8", newline="\n")


def package_stats(package: Path) -> tuple[int, float]:
    files = [path for path in package.rglob("*") if path.is_file() and path.name != SUMS_NAME]
    total_bytes = sum(path.stat().st_size for path in files)
    return len(files), round(total_bytes / 1024 / 1024, 1)


def create_deterministic_zip(package: Path, destination: Path, force: bool) -> str:
    if destination.exists():
        if not force:
            raise SystemExit(f"zip already exists: {destination} (use --force)")
        destination.unlink()
    destination.parent.mkdir(parents=True, exist_ok=True)
    root_name = package.name
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in package.rglob("*") if p.is_file()):
            rel = path.relative_to(package).as_posix()
            info = zipfile.ZipInfo(f"{root_name}/{rel}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.flag_bits |= 0x800
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return sha256_file(destination)


def build(output: Path, force: bool, version: str, zip_path: Path | None) -> int:
    manifest = load_manifest()
    describe = git_describe()
    if not describe["commit"]:
        raise SystemExit("release build requires a Git commit")
    if not describe["worktree_clean"]:
        raise SystemExit("release build refused: Git worktree is not clean")
    if output.exists():
        if not force:
            print(f"output already exists: {output} (use --force)", file=sys.stderr)
            return 2
        shutil.rmtree(output)

    files = selected_files(manifest)
    stubbed = referenced_exclusions(files, manifest.get("historical_exclusions", []))

    ledger: dict[str, str] = {}
    total_bytes = 0
    for rel in files:
        source = ROOT / rel
        destination = output / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        ledger[rel] = sha256_file(source)
        total_bytes += source.stat().st_size

    for rel, referrers in stubbed.items():
        write_exclusion_stub(output, rel, referrers)

    generated = mirror_claude_skills(output)
    transformed = apply_path_transforms(output, manifest)
    sanitized = apply_sanitizations(output, manifest)
    identity = apply_package_identity(output, manifest, version)
    create_workspace(output)
    assets = copy_package_assets(output)
    demo = verify_demo(output)
    residue = purge_build_residue(output)
    generated_at = describe["commit_time"]
    write_start_here(output, describe, generated_at, version, 0, 0.0)

    info = {
        "schema_version": 1,
        "generated_by": "scripts/build_portable_package.py",
        "generated_at": generated_at,
        "release_version": version,
        "source": describe,
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "counts": {
            "copied_files": len(files),
            "generated_files": len(generated),
            "stubbed_exclusions": len(stubbed),
            "transformed_files": len(transformed),
            "sanitized_files": len(sanitized),
            "demo_files": len(demo),
            "purged_build_residue": residue,
            "megabytes": round(total_bytes / 1024 / 1024, 1),
        },
        "generated_paths": generated,
        "package_assets": assets,
        "demo_paths": demo,
        "stubbed_exclusions": stubbed,
        "path_transforms": transformed,
        "sanitizations": sanitized,
        "package_identity": identity,
        "files": ledger,
    }
    (output / LEDGER_NAME).write_text(
        json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    write_sync_note(output, describe)
    shipped_file_count, shipped_megabytes = package_stats(output)
    write_start_here(
        output,
        describe,
        generated_at,
        version,
        shipped_file_count,
        shipped_megabytes,
    )
    total_shipped = write_checksums(output)
    if total_shipped != shipped_file_count:
        raise SystemExit(
            f"package count mismatch: START_HERE={shipped_file_count}, checksums={total_shipped}"
        )
    zip_sha256 = create_deterministic_zip(output, zip_path, force) if zip_path else None

    print(f"built {output}")
    print(f"  copied    {len(files)} files ({info['counts']['megabytes']} MB)")
    print(f"  generated {len(generated)} files under .claude/skills")
    print(f"  rewrote   {len(transformed)} file(s) to write output into workspace/")
    print(f"  sanitized {len(sanitized)} file(s) of deployment-only content")
    print(f"  demo      {len(demo)} file(s) under demos/html")
    print(f"  purged    {residue} build-residue file(s)")
    print(f"  checksums {total_shipped} shipped files in {SUMS_NAME}")
    if zip_path:
        print(f"  zip       {zip_path} ({zip_sha256})")
    if stubbed:
        print(f"  stubbed   {len(stubbed)} excluded file(s) still referenced: "
              + ", ".join(stubbed))
    print(f"  source    {describe['branch']} @ {describe['commit'][:12]}"
          + ("" if describe["worktree_clean"] else "  (worktree not clean)"))
    if not describe["worktree_clean"]:
        print("  warning: built from a dirty worktree; the ledger cannot be traced to a commit")
    return 0


def check(package: Path) -> int:
    ledger_path = package / LEDGER_NAME
    if not ledger_path.is_file():
        print(f"not a package: {ledger_path} missing", file=sys.stderr)
        return 2
    info = json.loads(ledger_path.read_text(encoding="utf-8"))
    recorded: dict[str, str] = info["files"]

    manifest = load_manifest()
    expected = set(selected_files(manifest))

    changed: list[str] = []
    missing: list[str] = []
    for rel, digest in sorted(recorded.items()):
        source = ROOT / rel
        if not source.is_file():
            missing.append(rel)
        elif sha256_file(source) != digest:
            changed.append(rel)

    added = sorted(expected - set(recorded))
    dropped = sorted(set(recorded) - expected)
    stale_manifest = sha256_file(MANIFEST_PATH) != info.get("manifest_sha256")

    print(f"package  {package}")
    print(f"built    {info['generated_at']} from {info['source']['branch']} @ {info['source']['commit'][:12]}")
    print(f"repo     {git_describe()['commit'][:12]}")
    print()

    def show(label: str, items: list[str]) -> None:
        print(f"{label:<20}{len(items)}")
        for item in items[:12]:
            print(f"    {item}")
        if len(items) > 12:
            print(f"    ... {len(items) - 12} more")

    show("changed", changed)
    show("missing", missing)
    show("added", added)
    show("no-longer-needed", dropped)
    print(f"{'stale-manifest':<20}{stale_manifest}")
    print()

    drifted = bool(changed or missing or added or dropped or stale_manifest)
    print("SYNC: " + ("DRIFT" if drifted else "IN SYNC"))
    return 1 if drifted else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify a standalone package of this system.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", help="Directory to build the package into.")
    mode.add_argument("--check", dest="check_dir", help="Existing package to compare against this repository.")
    parser.add_argument("--force", action="store_true", help="Replace an existing output directory.")
    parser.add_argument(
        "--version",
        help="Package version. Defaults to packaging/portable-manifest.yaml package_identity.version.",
    )
    parser.add_argument("--zip", dest="zip_path", help="Also write a deterministic ZIP archive.")
    args = parser.parse_args()

    if args.output:
        manifest = load_manifest()
        version = args.version or str(manifest.get("package_identity", {}).get("version", ""))
        if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version):
            parser.error(f"invalid version: {version!r}")
        zip_path = Path(args.zip_path).resolve() if args.zip_path else None
        return build(Path(args.output).resolve(), args.force, version, zip_path)
    if args.zip_path or args.version:
        parser.error("--version and --zip are only valid with --output")
    return check(Path(args.check_dir).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
