# Contributing

Please keep changes focused and preserve the separation between Theme, Layout, Content, Composition, and renderer adapters.

1. Update canonical Theme/Layout sources, then regenerate adapters; do not hand-edit generated adapters as the primary change.
2. Keep personal output under `workspace/`. Do not commit generated decks, cached browser state, logs, credentials, or personal data.
3. Run the most direct tests first, then `npm run audit --silent`; do not refresh generated artifacts or QA reports unless they are part of the change.
4. HTML changes must retain editable semantic objects and pass CSS ownership, geometry, interaction, and export checks.
5. PPTX claims require native objects and package/XML verification; a whole-slide image is not evidence of editability.

Publishing, force-pushing, tagging, and releases require explicit maintainer authorization.
