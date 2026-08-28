from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import html_production_renderer as renderer  # noqa: E402
from html_cards_1plus3_variants import (  # noqa: E402
    CARDS_1PLUS3_VARIANT_IDS,
    render_cards_1plus3_variant,
)


ICON_FAMILY = {
    "family_id": "test-family",
    "generation_mode": "per-deck-batch",
    "registry": {"A": "a", "B": "b", "C": "c"},
    "icons": [
        {"id": "a", "primitives": '<circle cx="12" cy="12" r="8"/>'},
        {"id": "b", "primitives": '<rect x="4" y="4" width="16" height="16" rx="2"/>'},
        {"id": "c", "primitives": '<path d="M4 12h16M12 4v16"/>'},
    ],
}


class CardsOnePlusThreeVariantTests(unittest.TestCase):
    def content_for(self, variant_id: str) -> dict:
        base = {
            "title": "三個平行重點",
            "subtitle": "同一個 Layout 依內容形狀改變內部配方。",
            "icon_family": ICON_FAMILY,
        }
        if variant_id == "icon-title-body":
            body = "這是一段超過二十個字、可測試內容驅動卡片高度的完整說明。"
            return {**base, "items": [["甲", body, "A"], ["乙", body, "B"], ["丙", body, "C"]]}
        if variant_id == "side-icon-body":
            body = "這是一段超過三十六個字的較長說明，用來驗證左側圖示與右側長文能在同一個模組內自然排版。"
            return {**base, "items": [["甲", body, "A"], ["乙", body, "B"], ["丙", body, "C"]]}
        if variant_id == "metric-title":
            return {**base, "items": [["甲", "70% 指標說明", "A"], ["乙", "80% 指標說明", "B"], ["丙", "90% 指標說明", "C"]]}
        return {**base, "items": [["甲", "一般說明", "標籤一"], ["乙", "一般說明", "標籤二"], ["丙", "一般說明", "標籤三"]]}

    def test_only_four_approved_variants_render_three_semantic_modules(self) -> None:
        self.assertEqual(
            CARDS_1PLUS3_VARIANT_IDS,
            ("icon-title-body", "metric-title", "label-rule-body", "side-icon-body"),
        )
        for variant_id in CARDS_1PLUS3_VARIANT_IDS:
            with self.subTest(variant=variant_id):
                markup, resolved = render_cards_1plus3_variant(
                    self.content_for(variant_id), variant_id
                )
                self.assertEqual(resolved, variant_id)
                self.assertEqual(markup.count('class="el diagram-node cards-1plus3-surface'), 3)
                expected_left_modules = 0 if variant_id == "icon-title-body" else 3
                self.assertEqual(
                    markup.count('data-module-interior-align="left"'), expected_left_modules
                )
                self.assertIn(f'data-layout-variant-id="{variant_id}"', markup)
                self.assertNotIn("module-number", markup)

    def test_icon_variants_use_deck_local_inline_svg(self) -> None:
        markup, _ = render_cards_1plus3_variant(
            self.content_for("icon-title-body"), "icon-title-body"
        )
        self.assertEqual(markup.count('data-icon-role="semantic"'), 3)
        self.assertNotIn("module-icon-shape", markup)

    def test_icon_title_body_inherits_centered_page_title(self) -> None:
        markup, _ = renderer._module_cards_1plus3_variant(
            self.content_for("icon-title-body"), "icon-title-body"
        )
        materialized = renderer.materialize_editable_production_markup(markup, "center")
        self.assertNotIn('data-edit-alignment-source="module-interior"', materialized)
        self.assertNotIn('data-module-interior-align="left"', materialized)
        self.assertIn('data-edit-alignment-source="page-title"', materialized)
        self.assertIn('data-edit-horizontal-align="center"', materialized)

    def test_icon_title_body_also_inherits_left_page_title(self) -> None:
        markup, _ = render_cards_1plus3_variant(
            self.content_for("icon-title-body"), "icon-title-body"
        )
        materialized = renderer.materialize_editable_production_markup(markup, "left")
        self.assertNotIn('data-edit-alignment-source="module-interior"', materialized)
        self.assertNotIn('data-module-interior-align="left"', materialized)
        self.assertIn('data-edit-alignment-source="page-title"', materialized)
        self.assertIn('data-edit-horizontal-align="left"', materialized)

    def test_metric_variant_uses_source_label_value_context_reading_order(self) -> None:
        markup, _ = render_cards_1plus3_variant(
            self.content_for("metric-title"), "metric-title"
        )
        first_source = markup.index("cards-1plus3-head-row")
        first_title = markup.index("cards-1plus3-title")
        first_metric = markup.index("cards-1plus3-metric")
        first_body = markup.index("cards-1plus3-body")
        self.assertLess(first_source, first_title)
        self.assertLess(first_title, first_metric)
        self.assertLess(first_metric, first_body)

    def test_side_icon_long_body_starts_with_two_ideographic_spaces(self) -> None:
        markup, _ = render_cards_1plus3_variant(
            self.content_for("side-icon-body"), "side-icon-body"
        )
        self.assertEqual(markup.count('class="cards-1plus3-body"'), 3)
        self.assertEqual(markup.count('>　　這是一段'), 3)


if __name__ == "__main__":
    unittest.main()
