#!/usr/bin/env python3
"""Read-only integrity checks for a built NESA-SLIDE release folder."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ABSOLUTE_PATH = re.compile(r"(?:[A-Za-z]:[\\/]|file:///)")
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)(?:openai|github|api)[_-]?key\s*[:=]\s*[^\s\"']+"),
)
REQUIRED_FILES = (
    "LICENSE",
    "README.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "THIRD_PARTY_NOTICES.md",
    "CHECK_SYSTEM.ps1",
    "release-manifest.json",
    "skill-dependency-closure.json",
    "external-capabilities.json",
    "showcase-manifest.json",
    "release-files.sha256",
    "SHA256SUMS.txt",
)
REQUIRED_SKILLS = {
    "design-presentations",
    "slide-outline-planner",
    "generate-image-slide",
    "html-image-slide",
    "html-pattern-slide",
    "ppt-builder",
    "slide-background-image",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, issues: list[str]) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(f"invalid-json:{path.name}:{exc}")
        return {}
    if not isinstance(data, dict):
        issues.append(f"invalid-json-object:{path.name}")
        return {}
    return data


def parse_ledger(path: Path, issues: list[str]) -> dict[str, str]:
    entries: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            digest, relative = raw.split("  ", 1)
        except ValueError:
            issues.append(f"invalid-ledger-line:{raw}")
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or not relative:
            issues.append(f"invalid-ledger-entry:{raw}")
            continue
        entries[relative] = digest
    return entries


def check(root: Path) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            issues.append(f"missing-required:{relative}")
    if issues:
        return {"pass": False, "issues": issues, "warnings": warnings}

    release_manifest = load_json(root / "release-manifest.json", issues)
    closure = load_json(root / "skill-dependency-closure.json", issues)
    external = load_json(root / "external-capabilities.json", issues)
    showcases = load_json(root / "showcase-manifest.json", issues)
    if release_manifest.get("schema_version") != 3:
        issues.append("release-manifest-schema-not-v3")
    if closure.get("schema_version") != 2 or closure.get("missing") != [] or closure.get("pass") is not True:
        issues.append("dependency-closure-not-pass")
    if not isinstance(external.get("external_capabilities"), list):
        issues.append("external-capabilities-invalid")
    runtime_contract = external.get("runtime_contract")
    if not isinstance(runtime_contract, dict):
        issues.append("external-runtime-contract-invalid")
    else:
        node_contract = runtime_contract.get("node")
        python_contract = runtime_contract.get("python")
        if not isinstance(node_contract, dict) or node_contract.get("system_node_allowed") is not False:
            issues.append("external-node-runtime-contract-invalid")
        if not isinstance(python_contract, dict) or python_contract.get("pyyaml_version") != "6.0.3" or python_contract.get("bundled_python_sufficient") is not False:
            issues.append("external-python-runtime-contract-invalid")
        if runtime_contract.get("verification_script") != "CHECK_SYSTEM.ps1":
            issues.append("external-runtime-check-script-invalid")
    if not isinstance(showcases.get("showcases"), list):
        issues.append("showcase-manifest-invalid")
    skills_root = root / ".agents" / "skills"
    present = {entry.name for entry in skills_root.iterdir() if entry.is_dir()} if skills_root.is_dir() else set()
    if present != REQUIRED_SKILLS:
        issues.append(f"skill-set-mismatch:{sorted(present)}")
    for skill in REQUIRED_SKILLS:
        if not (skills_root / skill / "SKILL.md").is_file():
            issues.append(f"missing-skill-entry:{skill}")

    ledger = parse_ledger(root / "release-files.sha256", issues)
    sums = (root / "SHA256SUMS.txt").read_text(encoding="utf-8")
    if sums != (root / "release-files.sha256").read_text(encoding="utf-8"):
        issues.append("ledger-files-differ")
    if any(relative.startswith("workspace/") for relative in ledger):
        issues.append("workspace-is-hashed")
    for relative, expected in ledger.items():
        target = root / relative
        if not target.is_file():
            issues.append(f"ledger-missing-file:{relative}")
        elif sha256(target) != expected:
            issues.append(f"ledger-mismatch:{relative}")

    profile = release_manifest.get("profile")
    forbidden = (".git", "node_modules", ".cache", ".history", "artifacts/experiments")
    if profile == "portable":
        forbidden += ("tests", ".github")
    for relative in forbidden:
        if (root / relative).exists():
            issues.append(f"forbidden-path:{relative}")

    license_text = (root / "LICENSE").read_text(encoding="utf-8")
    if "MIT License" not in license_text or "Slide Firm" not in license_text:
        issues.append("license-boundary-invalid")

    json_targets = [
        root / "release-manifest.json",
        root / "skill-dependency-closure.json",
        root / "external-capabilities.json",
        root / "showcase-manifest.json",
        root / "release-sanitizations.json",
    ]
    for target in json_targets:
        if target.is_file() and ABSOLUTE_PATH.search(target.read_text(encoding="utf-8")):
            issues.append(f"absolute-path-in-json:{target.name}")

    for target in root.rglob("*"):
        if not target.is_file() or target.suffix.lower() not in {".json", ".md", ".py", ".js", ".mjs", ".cjs", ".yaml", ".yml", ".txt"}:
            continue
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                issues.append(f"possible-secret:{target.relative_to(root).as_posix()}")
                break

    if "manual_visual_matrix_boundary" not in release_manifest:
        warnings.append("manual-matrix-boundary-not-stated")
    return {
        "pass": not issues,
        "profile": profile,
        "issues": sorted(set(issues)),
        "warnings": sorted(set(warnings)),
        "ledger_entries": len(ledger),
        "closure_missing": closure.get("missing"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    result = check(args.root.resolve())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
