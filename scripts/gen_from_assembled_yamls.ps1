# Retired compatibility entrypoint.
#
# This script previously started another Codex process, called a missing gallery
# builder and deployed from a mixed worktree. Those actions conflict with the
# current Image2 and deployment contracts, so the entrypoint now fails safely.

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

throw @"
scripts\gen_from_assembled_yamls.ps1 has been retired and did not generate or deploy anything.

Use the current workflow instead:
1. Build one seven-section YAML with .agents\skills\generate-image-slide\SKILL.md.
2. In the active Codex task, generate the preview with the built-in image_gen tool.
3. Record Image2 QA with references\image2-preview-workflow.md.
4. Rebuild the gallery with scripts\generate_layout_gallery.py.
5. Deploy only after explicit authorization, from a clean approved snapshot, by following references\layout-catalog-deployment.md.
"@
