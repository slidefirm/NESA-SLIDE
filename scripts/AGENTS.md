# Script Rules

These rules apply only to `scripts/` and its descendants.

- Determine which renderer and artifact contract a script serves before editing it; do not generalize Image2, HTML, or PPTX behavior across renderer boundaries.
- Preserve the existing language, module structure, CLI naming, exit-code behavior, and output format unless the task requires a change.
- CLI scripts must expose required inputs through arguments, provide useful `--help`, reject missing or invalid inputs clearly, and avoid hard-coded user paths, credentials, quotas, ports, or dates.
- A local renderer may be used for diagnostics or explicitly local previews, but its output must never be labeled as formal model-generated Image2 output.
- Scripts that can delete, deploy, publish, or modify shared state must perform explicit target and authorization gates. Do not add dirty-worktree bypasses.
- For input validation changes, test at least one valid and one invalid case. For Browser QA scripts, use a local HTTP URL plus task-specific report, profile, page, and selector arguments; a no-argument startup failure is not a passing QA result.
- Run the narrowest relevant unit, syntax, fixture, or integration checks first. Do not reformat unrelated scripts or regenerate unrelated artifacts.
