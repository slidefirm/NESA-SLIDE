# Contributing

Please make focused changes and preserve the separation between Theme, Layout, Content, Composition and renderer adapters.

1. Do not edit generated renderer adapters as the primary source; update the canonical core and regenerate or run the adapter check.
2. Keep user workspace output under `workspace/`. Do not commit generated previews, cached browser state, logs or personal data.
3. Run the relevant direct tests first. For packaging changes, run the dependency closure, two deterministic builds, hash-ledger verification and the license/absolute-path/secret scans.
4. HTML changes must retain the fixed 1920×1080 stage, one 96/96/1728/888 Content Area, materialized editable objects and CSS ownership gates.
5. PPTX changes must preserve Master → Custom Layout → Slide, typed placeholders and native foreground objects. A whole-slide image is never evidence of editability.

Do not publish, deploy, push or create a release without explicit maintainer authorization.
