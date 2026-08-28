from __future__ import annotations

import copy
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import html_production_renderer as renderer  # noqa: E402


class NoteBarAlignmentTests(unittest.TestCase):
    def test_note_bars_use_flow_text_instead_of_fixed_top_offsets(self) -> None:
        cases = (
            ("org-note", "org-note", "center", lambda: renderer._org_chart(copy.deepcopy(renderer.DIAGRAM_CONTENT["org-chart"]))),
            ("comparison-note", "compare-note", "center", lambda: renderer._comparison_table(copy.deepcopy(renderer.COMPARISON_CONTENT["comparison-table"]))),
            ("recommendation-rationale", "content-rationale", "left", lambda: renderer._recommendation_stack(copy.deepcopy(renderer.CONTENT_CONTENT["recommendation-stack"]))),
            ("strategic-impact-note", "content-impact-note", "left", lambda: renderer._strategic_priorities(copy.deepcopy(renderer.CONTENT_CONTENT["strategic-priorities"]))),
            ("flow-takeaway", "sequence-takeaway", "left", lambda: renderer._flow_stages_three(copy.deepcopy(renderer.SEQUENCE_CONTENT["flow-stages-3"]))),
            ("process-note", "sequence-note", "center", lambda: renderer._process_flow(copy.deepcopy(renderer.SEQUENCE_CONTENT["process-flow"]))),
        )

        for composite, class_name, expected_alignment, render in cases:
            with self.subTest(composite=composite):
                markup = render()
                self.assertRegex(
                    markup,
                    rf'data-edit-composite="{composite}"[^>]*class="[^"]*{class_name}[^"]*"|class="[^"]*{class_name}[^"]*"[^>]*data-edit-composite="{composite}"',
                )
                start = markup.index(f'data-edit-composite="{composite}"')
                fragment = markup[start:start + 1200]
                self.assertIn('data-edit-position="flow"', fragment)
                self.assertIn(f'data-edit-horizontal-align="{expected_alignment}"', fragment)
                self.assertNotRegex(fragment, r'data-edit-layer="text"[^>]*\btop:\d+px')

    def test_note_bar_css_reuses_kpi_alignment_contract(self) -> None:
        css = renderer.PRODUCTION_CSS
        for class_name in (
            "org-note",
            "compare-note",
            "content-rationale",
            "content-impact-note",
            "sequence-takeaway",
            "sequence-note",
        ):
            with self.subTest(class_name=class_name):
                self.assertIn(f".{class_name}[data-edit-horizontal-align=\"left\"]", css)
                self.assertIn(f".{class_name}[data-edit-horizontal-align=\"center\"]", css)
                self.assertIn(f".{class_name}[data-edit-horizontal-align=\"right\"]", css)
                self.assertIn(f".diagram-node.{class_name}>[data-edit-position=\"flow\"]", css)

        self.assertIn(
            ".org-note,.compare-note,.content-rationale,.content-impact-note,.sequence-takeaway,.sequence-note{display:flex;align-items:center",
            css,
        )


if __name__ == "__main__":
    unittest.main()
