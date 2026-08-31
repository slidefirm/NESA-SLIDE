# Prompt System Rules

These rules apply only to `prompt_system/` and its descendants.

## Sources and Boundaries

- Read `prompt_system/README.md`, the relevant schema, and `references/renderer-adapter-contract.md` before changing a core or adapter.
- Theme and Layout core are the shared semantic source. Renderer adapters project that source into Image2, HTML, or PPTX; they are not a second source of truth.
- Art Direction controls deck-level scene grammar and renderer handoff. It does not replace Theme or Layout core.
- Previews, generated prompts, manifests, and deployed HTML are artifacts, not sources from which to reverse-engineer new core rules.
- Layout describes content roles, spatial relationships, regions, weights, alignment, and decoration zones. It must not contain concrete palette, texture, typography mood, or one-off content fields.
- Theme describes visual language and must not encode a fixed content layout.
- Content fields are transient manifest or assembly decisions; do not create persistent per-layout content schemas unless the architecture explicitly adds that contract.

## Renderer Separation

- Image2 formal generation uses seven-section assembled YAML as a one-off output.
- HTML and PPTX use their own adapters and content manifests; neither requires assembled YAML as a shared runtime payload.
- Never copy HTML-only, PPTX-only, or Image2-only behavior into another renderer without updating that renderer's contract and tests.

## Changes and Validation

- Modify the canonical core or schema first, then regenerate or check affected adapters. Do not bulk-patch generated adapters as the primary change.
- Keep schema and adapter changes minimal and compatible with existing IDs unless the task explicitly requires a migration.
- Run the most direct schema, adapter-generation, and renderer validation for the changed files. Record any renderer not exercised as unverified.
