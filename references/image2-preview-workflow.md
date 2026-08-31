# Image2 Preview Workflow

Generate formal bitmap previews with the current built-in image generation path and preserve enough evidence to reproduce and review each result.

## Preconditions

1. Use `$generate-image-slide` to create `artifacts/generated-prompts/staging/<id>.assembled.yaml`.
2. Read the complete file, confirm all seven top-level sections exist, and record its path and SHA-256. Do not summarize only `closing_design_intent`.
3. Confirm the requested output path and whether this is a new version or an explicitly authorized replacement.

## Generate

1. Follow the current `$imagegen` Skill and use the built-in `image_gen` tool by default.
2. Provide the full seven-section specification in a structured prompt, including layout, hierarchy, palette, typography, safe zone, and closing design intent.
3. Do not start a nested `codex exec` merely to call the same image capability, and do not place the YAML into a single-line shell command.
4. Do not substitute PIL, SVG, HTML canvas, `scripts/render_*.py`, or another local renderer for formal model generation.
5. Copy the stable generated PNG into the approved workspace preview directory. Preserve earlier accepted versions unless the user explicitly requests replacement.

CLI or direct-API fallback is allowed only when the user explicitly requests it, or when the built-in tool is unavailable and the user confirms the fallback. Authentication failure means formal generation is incomplete.

## QA Loop

1. Inspect the actual image at full resolution.
2. Apply `references/preview-qa-loop.md` and append the evidence to `artifacts/qa/layout-preview-qa.jsonl`.
3. Regenerate only failed checks, for at most two automatic iterations.
4. Preserve failed candidates as `needs-review` or `fail` under `artifacts/deploy/review/<layout-id>/`.
5. Add a preview to the main gallery only when the latest record is `pass` or contains explicit human approval.

Report the assembled YAML path and hash, final PNG path, generator path used, QA ledger entry, iteration count, and every unverified item.
