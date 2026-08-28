"""Run the existing v6 QA command contract for a disjoint Preset shard.

The full v6 orchestrator is intentionally serial so it can produce one
canonical ledger.  This helper keeps the exact same inventory and command
implementation but runs a user-selected, disjoint subset, allowing browser
QA to finish without a single process timeout.  It writes only QA reports,
captures, PPTX exports, and a shard report; it never rewrites HTML sources.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import qa_v6_background_batch as batch


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run v6 HTML image-background QA for a Preset shard")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Validate and list the shard command plan")
    mode.add_argument("--write", action="store_true", help="Run the shard QA commands and write a report")
    parser.add_argument("--batch-plan", required=True)
    parser.add_argument("--job-queue", required=True)
    parser.add_argument("--presets", required=True, help="Comma-separated Preset ids")
    parser.add_argument("--repo-root", default=str(batch.REPO_ROOT))
    parser.add_argument("--output", required=True, help="Repository-relative shard report path")
    return parser


def _resolve(repo_root: Path, value: str, label: str) -> Path:
    return batch._resolve_cli_path(repo_root, value, label)


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    batch_plan = _resolve(repo_root, args.batch_plan, "batch plan")
    job_queue = _resolve(repo_root, args.job_queue, "job queue")
    output = _resolve(repo_root, args.output, "shard report")
    wanted = [item.strip() for item in args.presets.split(",") if item.strip()]
    if not wanted or len(wanted) != len(set(wanted)):
        raise batch.BatchQaError(["--presets must contain unique non-empty Preset ids"])

    inventory = batch._static_inventory(
        repo_root=repo_root,
        batch_plan_path=batch_plan,
        job_queue_path=job_queue,
    )
    by_preset = {str(deck["preset"]): deck for deck in inventory["decks"]}
    missing = [preset for preset in wanted if preset not in by_preset]
    if missing:
        raise batch.BatchQaError([f"unknown Presets in shard: {missing}"])

    executor = batch._default_executor
    decks: list[dict[str, Any]] = []
    commands: list[dict[str, Any]] = []
    for preset in wanted:
        deck = by_preset[preset]
        final_html = batch._resolve_repo_path(repo_root, deck["final_html"], f"final HTML for {preset}")
        specs = batch._commands_for_deck(deck, repo_root)
        results = []
        if args.write:
            for spec in specs:
                results.append(
                    batch._invoke(
                        spec,
                        repo_root=repo_root,
                        final_html=final_html,
                        expected_slides=int(deck["slide_count"]),
                        executor=executor,
                    )
                )
        else:
            results = [batch._planned(spec) for spec in specs]
        commands.extend(results)
        decks.append(
            {
                "preset": preset,
                "slide_count": deck["slide_count"],
                "source_html": deck["source_html"],
                "source_html_sha256": deck["source_html_sha256"],
                "source_manifest": deck["source_manifest"],
                "run_manifest": deck["run_manifest"],
                "final_html": deck["final_html"],
                "final_html_sha256": batch._sha256(final_html),
                "human_review": deck["human_review"],
                "commands": [result["command_id"] for result in results],
            }
        )

    failures = [row for row in commands if row.get("status") == "fail"]
    blocked = [row for row in commands if row.get("status") == "blocked"]
    partial = [row for row in commands if row.get("status") == "partial"]
    payload = {
        "schema_version": "html-image-background-v6-qa-shard/v1",
        "mode": "write" if args.write else "check",
        "presets": wanted,
        "preset_count": len(decks),
        "slide_count": sum(int(deck["slide_count"]) for deck in decks),
        "classification": "fail" if failures else ("partial" if partial or blocked or not args.write else "pass"),
        "summary": {
            "commands": len(commands),
            "passed": sum(row.get("status") == "pass" for row in commands),
            "partial": len(partial),
            "blocked": len(blocked),
            "failed": len(failures),
            "planned": sum(row.get("status") == "planned" for row in commands),
        },
        "decks": decks,
        "commands": commands,
    }
    batch._write_json_atomic(output, payload)
    print(json.dumps({"status": payload["classification"], "output": batch._relative(output, repo_root, "shard report"), "summary": payload["summary"]}, ensure_ascii=False, indent=2))
    return 1 if payload["classification"] == "fail" else 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except batch.BatchQaError as exc:
        print(json.dumps({"status": "fail", "errors": exc.errors}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
