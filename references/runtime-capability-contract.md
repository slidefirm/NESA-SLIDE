# Runtime Capability Contract

NESA-SLIDE packages repository-local Skills, source, adapters and references. It does not vendor Codex- or Windows-managed capabilities.

| Capability | Gate | Release interpretation |
| --- | --- | --- |
| Built-in `image_gen` | Generate one requested raster asset at a time and inspect it | Missing or failed output makes the image-dependent artifact partial. Do not substitute PIL, SVG, Canvas or a local renderer. |
| Python | Use a system-selected CPython 3.13 with PyYAML 6.0.3 | Required for repository scripts and validation. Codex bundled Python is not sufficient; a dry run is not visual proof. |
| Node.js | Use `RUNTIME_NODE`, `RUNTIME_NODE_MODULES` and `RUNTIME_BIN_DIR` returned by Codex `load_workspace_dependencies` | Required for browser QA and `@oai/artifact-tool` builders. System Node is not an accepted substitute. |
| Browser | Serve the actual local artifact over HTTP and record real interaction evidence | Static HTML validation cannot replace editor, save, download/reopen or projection evidence. |
| PowerPoint | Create Custom Layouts, inspect OOXML and render every slide in native PowerPoint | A PPTX without Master → Layout → Slide evidence remains partial. |
| `@oai/artifact-tool` | Import it from a JavaScript ES module via the supplied runtime | Required for Codex-native PPTX creation; do not use `python-pptx`. |

The release checker may mark a capability as available, unavailable or unverified. Availability is a prerequisite, not proof that every output built with that capability passed visual review.

## Runtime selection check

Before a production run, assign the system-selected Python executable to `NESA_PYTHON`, obtain the three `RUNTIME_*` values from Codex `load_workspace_dependencies`, then run `CHECK_SYSTEM.ps1`. The check requires PyYAML `6.0.3`, verifies that the supplied Codex runtime contains `@oai/artifact-tool`, and intentionally does not fall back to a system Node executable. It is a capability Gate only; each browser and PowerPoint artifact still needs its own evidence.

For `slide-background-image`, local independent semantic images are runtime inputs, not decorative background substitutes. `prepare-deck` stages every relative or `file:` `<img data-semantic-image="true">` into the isolated `workspace/html-image-background/<run>/semantic-assets/` directory by SHA-256, preserves byte provenance in `run.json`, and rewrites neutral and mask-page references for their different directory depths. A missing, unsupported or remote semantic source is a blocking error; manual asset-copy workarounds are not portable evidence.

`apply-deck` then embeds each staged semantic image as a data URL in the final independent `<img>` while retaining its staged relative source and SHA-256 metadata. This is required for `file://` PPTX browser export to create semantic native picture objects; it does not convert the image into a raster background or remove its alt/crop/focal contract.
