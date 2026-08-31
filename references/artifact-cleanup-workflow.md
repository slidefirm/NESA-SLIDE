# Active Artifact Cleanup

Treat cleanup as dependency analysis, not filename-based deletion.

## Scope and Authorization

1. Resolve each exact target and report whether it is a file or directory.
2. A name containing `legacy`, `old`, a date, or an ignored or untracked status is not deletion evidence.
3. Removing an entire file or directory requires explicit user authorization. Prefer a recoverable move to an approved `To_delete/` location, and never stage or deploy that holding area.

## Repository Retention Policy

- Keep canonical code, prompt rules, Theme/Layout sources, manifests for current formal deliverables, and the QA evidence required to verify those deliverables in Git.
- Treat repository-root `.history/` and `tmp/` as local runtime scratch. They must be ignored by Git and must not become a second source of truth.
- Superseded experiment batches such as `base` / `v2` / `v3` may be removed only after a newer approved `final` batch exists and the dependency gate passes.
- Large generated artifacts that are neither an active Gallery dependency nor a current formal deliverable belong in a recoverable sibling `To_delete/` batch, not in a repository `archive/` folder.
- Every recoverable cleanup batch records its exact source, recovery location, file count, byte count, authorization, and `delete_after` date. Use a minimum seven-day recovery window unless the user explicitly requests immediate permanent removal.
- Expiry is not permission to skip verification. Before permanent removal, resolve the exact holding paths again and confirm that no new active reference or recovery request exists.

## Dependency Gate

Run the repository guard before removal:

```powershell
python scripts\check_active_artifact_references.py <cleanup-target> [<cleanup-target> ...]
```

- Never remove a target reported as `BLOCKED`.
- If a directory mixes active and inactive content, split it into exact file targets and act only on confirmed inactive files.
- Treat direct and transitive Gallery, HTML, or tracked JSON／YAML manifest references to previews, HTML, CSS, JS, SVG, fonts, sources, and downloads as active dependencies.
- If reference status, rebuildability, or scope remains unclear, stop and ask the user.

## Verify and Report

After an authorized cleanup, rerun the dependency check and relevant gallery or renderer validation. Report original paths, recovery paths, removed file counts and sizes, validation evidence, and the recovery procedure.

## Portable Artifact Paths

- Tracked JSON manifests and QA reports must store repository-owned paths as repository-relative POSIX paths, for example `artifacts/qa/report.json`.
- Do not commit `C:\Users\...`, `C:/Users/...`, `file:///C:/Users/...`, or another machine-specific repository root into an artifact report.
- After generating or refreshing reports, run `python scripts/normalize_artifact_report_paths.py --fix`, then use `python scripts/normalize_artifact_report_paths.py` as the commit gate.
