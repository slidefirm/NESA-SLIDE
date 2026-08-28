from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRAMEWORK = PROJECT_ROOT / "scripts" / "html_edit_framework.py"


class SemanticTextStackRuntimeTests(unittest.TestCase):
    def test_runtime_resolves_stack_after_fonts_and_before_geometry_freeze(self) -> None:
        source = FRAMEWORK.read_text(encoding="utf-8")

        self.assertIn("const MIN_SEMANTIC_TEXT_STACK_GAP=16", source)
        self.assertIn("function resolveSemanticTextStacks(root)", source)
        self.assertIn("function resetSemanticTextStacks(root)", source)
        self.assertIn(
            ".el[data-edit-structure=\"module\"],.el[data-edit-composite]",
            source,
        )
        self.assertLess(
            source.index("repairGeneratedTextOrphans(stage);\n    resolveSemanticTextStacks(stage);"),
            source.index("freezeTextFitGeometry(stage);"),
        )

    def test_reapply_layout_restores_then_resolves_stack_geometry(self) -> None:
        source = FRAMEWORK.read_text(encoding="utf-8")
        reset_index = source.index("resetSemanticTextStacks(scope);")
        resolve_index = source.index("resolveSemanticTextStacks(scope);")

        self.assertLess(reset_index, resolve_index)

    def test_vertical_stack_materialization_preserves_visual_glyph_gap_before_rules(self) -> None:
        source = FRAMEWORK.read_text(encoding="utf-8")
        self.assertIn("function normalizeVerticalStackVisualGaps(area,boxes)", source)
        self.assertIn("const minTop=previous.top+previous.height+minGap", source)
        self.assertIn("normalizeVerticalStackVisualGaps(area,children.map", source)
        self.assertLess(
            source.index("normalizeVerticalStackVisualGaps(area,children.map"),
            source.index("area.classList.add('layout-materialized')"),
        )


if __name__ == "__main__":
    unittest.main()
