# Cleanup Ledger — 2026-08-05

- Authorized by user: 2026-08-05
- Recovery window: 7 days
- Delete after: 2026-08-12 (Asia/Taipei)
- Holding root: sibling `../To_delete/`
- Permanent deletion gate: resolve the exact paths again, confirm no recovery request, and rerun the relevant reference checks before removal.

| Original location | Recovery location under `../To_delete/` | Files | Bytes |
|---|---|---:|---:|
| `.history/` | `project-cleanup-20260805/.history/` | 22 | 11,248,245 |
| `artifacts/html-preset-regeneration-20260805/` | `project-cleanup-20260805/html-preset-regeneration-20260805/` | 194 | 15,591,521 |
| `artifacts/html-preset-regeneration-20260805-v2/` | `project-cleanup-20260805/html-preset-regeneration-20260805-v2/` | 208 | 16,310,248 |
| `artifacts/html-preset-regeneration-20260805-v3/` | `project-cleanup-20260805/html-preset-regeneration-20260805-v3/` | 275 | 23,601,871 |
| `tmp/` | `project-cleanup-20260805/tmp/` | 719 | 171,755,434 |
| `artifacts/qa/html-pptx-export/dev-server-7401.out.log` | `project-cleanup-20260805/artifacts/qa/html-pptx-export/dev-server-7401.out.log` | 1 | 129 |
| one-off `scripts/*v2*`, `scripts/*v3*` Preset regeneration helpers | `project-cleanup-20260805/scripts/obsolete-preset-v2-v3/` | 27 | 160,389 |
| untracked nested writeback and `random-deck-2008` test outputs | `project-cleanup-20260805/artifacts/html-test/untracked-leftovers-20260805/` | 3 | 2,094,687 |
| `tmp/slide-outline-planner-codex-publish-20260801/` | `slide-outline-planner-codex-publish-20260801-20260805/` | 32 | 56,792 |
| sibling worktree `../過往PPT彙整-refactor-v2/` | `過往PPT彙整-refactor-v2-20260805/` | 2,369 | 813,108,818 |

Total held for recovery: 3,850 files, 1,053,928,134 bytes.

## Recovery

- For `.history/`, Preset batches, `tmp/`, the server log, one-off Preset scripts, or untracked HTML test outputs, move the exact item from the holding batch back to its original relative location before the delete-after date.
- For the outline-planner publish copy, move the independent repository back to its original `tmp/` path and restore the Git link only if it is intentionally reintroduced.
- The refactor-v2 folder remains a locked Git worktree on branch `codex/refactor-v2`. Unlock it and use `git worktree move` to restore the original sibling path.
