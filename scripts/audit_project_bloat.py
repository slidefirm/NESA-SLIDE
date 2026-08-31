#!/usr/bin/env python3
"""Read-only artifact-size and duplication audit.

The script never deletes files. It is intended to make cleanup decisions
evidence-based and to keep generated experiments from silently accumulating.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return {
        value.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        for value in result.stdout.split(b"\0")
        if value
    }


def ignored_files(paths: list[str]) -> set[str]:
    if not paths:
        return set()
    result = subprocess.run(
        ["git", "check-ignore", "-z", "--stdin"],
        cwd=ROOT,
        check=False,
        input=b"\0".join(path.encode("utf-8") for path in paths) + b"\0",
        capture_output=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    return {
        value.decode("utf-8", errors="surrogateescape").replace("\\", "/")
        for value in result.stdout.split(b"\0")
        if value
    }


def is_directory_link(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction and is_junction())


def file_rows(root: Path, tracked: set[str]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    directory_links: list[str] = []
    if not root.exists():
        return rows, directory_links
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        retained_dirs = []
        for dirname in dirnames:
            child = current_path / dirname
            if is_directory_link(child):
                directory_links.append(child.relative_to(ROOT).as_posix())
            else:
                retained_dirs.append(dirname)
        dirnames[:] = retained_dirs
        for filename in filenames:
            path = current_path / filename
            relative = path.relative_to(ROOT).as_posix()
            rows.append(
                {
                    "path": relative,
                    "bytes": path.stat().st_size,
                    "tracked": relative in tracked,
                    "ignored": False,
                }
            )
    return rows, directory_links


def top_level_summary(rows: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, int]] = defaultdict(lambda: {
        "files": 0,
        "bytes": 0,
        "tracked_files": 0,
        "ignored_files": 0,
    })
    for row in rows:
        parts = row["path"].split("/")
        if not parts or parts[0] != prefix:
            continue
        name = parts[1] if len(parts) > 1 else "(root)"
        bucket = buckets[name]
        bucket["files"] += 1
        bucket["bytes"] += row["bytes"]
        bucket["tracked_files"] += int(row["tracked"])
        bucket["ignored_files"] += int(row["ignored"])
    result = []
    for name, bucket in buckets.items():
        result.append({
            "name": name,
            **bucket,
            "megabytes": round(bucket["bytes"] / 1024 / 1024, 2),
        })
    return sorted(result, key=lambda item: item["bytes"], reverse=True)


def duplicate_named_assets(rows: list[dict[str, Any]], filename: str) -> list[dict[str, Any]]:
    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if Path(row["path"]).name != filename:
            continue
        path = ROOT / row["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        by_hash[digest].append(row)
    duplicates = []
    for digest, matches in by_hash.items():
        if len(matches) < 2:
            continue
        total = sum(item["bytes"] for item in matches)
        duplicates.append({
            "sha256": digest,
            "copies": len(matches),
            "total_bytes": total,
            "megabytes": round(total / 1024 / 1024, 2),
            "paths": [item["path"] for item in matches],
        })
    return sorted(duplicates, key=lambda item: item["total_bytes"], reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--top", type=int, default=30)
    args = parser.parse_args()

    tracked = tracked_files()
    artifact_rows, artifact_links = file_rows(ROOT / "artifacts", tracked)
    experiment_rows, experiment_links = file_rows(ROOT / "experiments", tracked)
    rows = artifact_rows + experiment_rows
    ignored = ignored_files([row["path"] for row in rows])
    for row in rows:
        row["ignored"] = row["path"] in ignored
    ignored_untracked = [
        row for row in rows
        if row["ignored"] and not row["tracked"]
    ]
    ignored_untracked.sort(key=lambda item: item["bytes"], reverse=True)
    report = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "root": str(ROOT),
        "read_only": True,
        "scope": ["artifacts/", "experiments/"],
        "totals": {
            "files": len(rows),
            "bytes": sum(row["bytes"] for row in rows),
            "megabytes": round(sum(row["bytes"] for row in rows) / 1024 / 1024, 2),
            "tracked_files": sum(int(row["tracked"]) for row in rows),
            "ignored_untracked_files": len(ignored_untracked),
            "ignored_untracked_megabytes": round(
                sum(row["bytes"] for row in ignored_untracked) / 1024 / 1024,
                2,
            ),
        },
        "artifact_top_level": top_level_summary(artifact_rows, "artifacts"),
        "experiment_top_level": top_level_summary(experiment_rows, "experiments"),
        "largest_ignored_untracked": ignored_untracked[: args.top],
        "duplicate_edit_mode_assets": duplicate_named_assets(artifact_rows, "edit-mode.js"),
        "directory_links_not_counted": sorted(artifact_links + experiment_links),
        "notes": [
            "Ignored and untracked does not automatically mean disposable; verify rebuildability first.",
            "Before cleanup, run check_active_artifact_references.py; a legacy name or old date does not make a referenced asset disposable.",
            "Repeated deploy and formal preview assets are reported but never deleted by this script.",
            "Experiment raw QA, save sandboxes, and runtime history should be regenerated on demand.",
            "Directory junctions and symlinks are listed but their target contents are not counted as project bytes.",
        ],
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["totals"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
