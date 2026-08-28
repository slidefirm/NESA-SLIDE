# NESA-SLIDE

NESA-SLIDE is a Windows and Codex Desktop-oriented, open-source presentation production runtime maintained by Slide Firm. It keeps Story, Art Direction, Theme, Layout and renderer adapters as separate, inspectable layers so Image2, editable HTML and native-editable PPTX do not pretend to share one runtime payload.

Version `0.1.0` ships seven repository-local Skills:

- `design-presentations`
- `slide-outline-planner`
- `generate-image-slide`
- `html-image-slide`
- `html-pattern-slide`
- `ppt-builder`
- `slide-background-image`

The package is designed for Codex Desktop on Windows. It deliberately does not include a Claude plugin.

## What is included

The source profile includes the seven Skills, shared Theme/Layout core, renderer adapters, runtime scripts, references, the explicit release test suite in `release/relevant-tests.txt`, and Windows CI. The portable profile keeps the same runtime closure while excluding Git history, tests, caches, logs, experiments and user workspace output.

All first-party source and Showcase material is MIT licensed by Slide Firm. Third-party notices remain in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and alongside retained third-party assets.

## Quick start

Use the package from a writable local folder. In Codex Desktop, point the task at the folder, then use the matching local Skill. Generated working material belongs under `workspace/`; do not write artifacts back into `prompt_system/`, `references/` or the Skill directories.

To build a deterministic release folder from a source checkout:

```powershell
python scripts\build_nesa_release.py --profile portable --version 0.1.0 --output ..\NESA-SLIDE-v0.1.0
```

Use `--zip <path>` to additionally produce a deterministic ZIP archive. A build refuses to reuse a non-empty output directory.

## Runtime boundaries

- Image generation uses Codex's built-in `image_gen` capability one asset at a time; it is not vendored.
- Native PowerPoint creation uses the system-managed `@oai/artifact-tool` and Windows PowerPoint capability; neither is vendored.
- Browser QA, Node.js and Python are capability gates, not bundled executable dependencies. Repository scripts use a system-selected CPython 3.13 with PyYAML 6.0.3; Codex bundled Python is not sufficient.
- Browser and PPTX work must use `RUNTIME_NODE`, `RUNTIME_NODE_MODULES` and `RUNTIME_BIN_DIR` returned by Codex `load_workspace_dependencies`; system Node is not a substitute for `@oai/artifact-tool` work.
- `workspace/` is intentionally an output placeholder and is not hashed as part of the release ledger.

Set `NESA_PYTHON` to the selected Python executable and run `CHECK_SYSTEM.ps1` after loading the Codex runtime paths. This confirms capability availability only; it does not replace artifact QA.

See [references/runtime-capability-contract.md](references/runtime-capability-contract.md) for the exact capability checks and the release evidence boundary.

## Verification

Every built profile contains:

- `release-manifest.json` (schema v3)
- `skill-dependency-closure.json` (schema v2)
- `external-capabilities.json`
- `showcase-manifest.json`
- `release-files.sha256` and `SHA256SUMS.txt`

The closure report must have `missing: []`. A clean hash ledger proves package inventory, not visual acceptance of the complete 36 Theme × 75 Layout matrix. That full matrix remains outside the v0.1.0 manual-review claim.
