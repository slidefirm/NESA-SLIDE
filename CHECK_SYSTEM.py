#!/usr/bin/env python3
"""Check this package on the machine that received it.

Answers three questions the recipient cannot answer by reading files:

    integrity     did every shipped file arrive intact
    environment   is the interpreter and its libraries what the package expects
    capabilities  which Skills are usable here, and which are gated by something
                  this machine does not have

Exit code is 0 when nothing required is missing. Optional capabilities that are
absent are reported but do not fail the run.

Usage:
    python CHECK_SYSTEM.py
    python CHECK_SYSTEM.py --json
    python CHECK_SYSTEM.py --skip-integrity     # faster on a large package
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUMS = ROOT / "SHA256SUMS.txt"
MANIFEST = ROOT / "packaging" / "portable-manifest.yaml"
EXPECTED_PYTHON = (3, 13)

OK, WARN, FAIL = "OK", "WARN", "FAIL"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_integrity(skip: bool) -> dict:
    if skip:
        return {"name": "integrity", "status": WARN, "detail": "skipped"}
    if not SUMS.is_file():
        return {
            "name": "integrity",
            "status": WARN,
            "detail": "source checkout; SHA256SUMS.txt is generated in the portable release",
        }
    bad: list[str] = []
    missing: list[str] = []
    total = 0
    for line in SUMS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        total += 1
        path = ROOT / rel
        if not path.is_file():
            missing.append(rel)
        elif sha256_file(path) != digest:
            bad.append(rel)
    if missing or bad:
        detail = f"{len(missing)} missing, {len(bad)} altered, of {total}"
        sample = (missing + bad)[:3]
        if sample:
            detail += " — " + ", ".join(sample)
        return {"name": "integrity", "status": FAIL, "detail": detail}
    return {"name": "integrity", "status": OK, "detail": f"{total} files verified"}


def check_python() -> list[dict]:
    rows = []
    version = sys.version_info[:2]
    rows.append({
        "name": "python",
        "status": OK if version >= EXPECTED_PYTHON else WARN,
        "detail": f"{platform.python_version()} (expected {EXPECTED_PYTHON[0]}.{EXPECTED_PYTHON[1]} or newer)",
    })
    requirements = ROOT / "requirements.txt"
    wanted = []
    if requirements.is_file():
        for line in requirements.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                wanted.append(line.split("==")[0].strip())
    import importlib.util

    aliases = {"beautifulsoup4": "bs4", "Pillow": "PIL", "PyYAML": "yaml"}
    absent = [n for n in wanted if importlib.util.find_spec(aliases.get(n, n.lower())) is None]
    rows.append({
        "name": "python packages",
        "status": OK if not absent else FAIL,
        "detail": "all present" if not absent else "missing: " + ", ".join(absent) + " — run: pip install -r requirements.txt",
    })
    return rows


def tool_version(executable: str, *args: str) -> str | None:
    path = shutil.which(executable)
    if not path:
        return None
    try:
        proc = subprocess.run([path, *args], capture_output=True, text=True, timeout=30)
        return (proc.stdout or proc.stderr).strip().splitlines()[0]
    except Exception:
        return path


def check_node() -> list[dict]:
    node = tool_version("node", "--version")
    rows = [{
        "name": "node",
        "status": OK if node else WARN,
        "detail": node or "not found — Browser QA and the PPTX export runtime need Node 22+",
    }]
    modules = ROOT / "node_modules"
    rows.append({
        "name": "node_modules",
        "status": OK if modules.is_dir() else WARN,
        "detail": "installed" if modules.is_dir() else "not installed — run: npm install",
    })
    return rows


def check_browser() -> dict:
    candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ]
    found = next((c for c in candidates if c.exists()), None)
    if found is None and shutil.which("chromium"):
        found = Path(shutil.which("chromium"))
    return {
        "name": "browser",
        "status": OK if found else WARN,
        "detail": str(found) if found else "no local Chrome/Edge/Chromium found — Browser QA cannot run",
    }


def capability_rows(env: dict[str, str]) -> list[dict]:
    """Map declared external capabilities onto what this machine actually has."""
    try:
        import yaml
    except ImportError:
        return [{"name": "capabilities", "status": WARN, "detail": "PyYAML missing; cannot read the manifest"}]
    if not MANIFEST.is_file():
        return [{"name": "capabilities", "status": WARN, "detail": "manifest missing"}]
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for capability in manifest.get("external_capabilities", []):
        cid = capability["id"]
        optional = bool(capability.get("optional"))
        state = env.get(cid)
        if state is None:
            status, detail = WARN, "cannot be detected here; " + capability["gate"]
        elif state == OK:
            status, detail = OK, "available"
        else:
            status = WARN if optional else FAIL
            detail = "unavailable — gates: " + ", ".join(capability["required_for"])
        rows.append({"name": f"capability: {cid}", "status": status, "detail": detail})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Check this package and the machine it is on.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output.")
    parser.add_argument("--skip-integrity", action="store_true", help="Skip the file hash verification.")
    args = parser.parse_args()

    rows: list[dict] = [check_integrity(args.skip_integrity)]
    rows.extend(check_python())
    rows.extend(check_node())
    rows.append(check_browser())

    by_name = {r["name"]: r["status"] for r in rows}
    env = {
        "python": by_name.get("python", FAIL),
        "node": by_name.get("node", WARN),
        "browser": by_name.get("browser", WARN),
    }
    rows.extend(capability_rows(env))

    if args.json:
        print(json.dumps({"root": str(ROOT), "checks": rows}, ensure_ascii=False, indent=2))
    else:
        width = max(len(r["name"]) for r in rows)
        print(f"package: {ROOT}\n")
        for row in rows:
            print(f"{row['name'].ljust(width)}  {row['status']:<4}  {row['detail']}")
        print()
        failed = [r["name"] for r in rows if r["status"] == FAIL]
        print("RESULT: " + ("FAIL — " + ", ".join(failed) if failed else "OK"))
        if not failed:
            next_document = "START_HERE.md" if (ROOT / "START_HERE.md").is_file() else "README.md"
            print(f"\n下一步：讀 {next_document}")

    return 1 if any(r["status"] == FAIL for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
