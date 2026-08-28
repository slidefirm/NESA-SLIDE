from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from html_visible_copy import audit_renderer_source, audit_visible_copy  # noqa: E402
import html_production_renderer as renderer  # noqa: E402


class VisibleCopyTests(unittest.TestCase):
    def test_traditional_chinese_deck_accepts_codes_and_approved_names(self) -> None:
        html = '''<main><section class="slide"><div>凌晨兩點，回家的路要能被接住</div>
        <span>N01</span><span>AI</span><span>NESA</span></section></main>'''
        report = audit_visible_copy(html, allowed_latin_terms=["NESA"])
        self.assertEqual(report["status"], "pass")

    def test_traditional_chinese_deck_rejects_decorative_english_filler(self) -> None:
        html = '''<main><section class="slide"><div>凌晨兩點</div>
        <span>NIGHT TRANSFER LAB</span></section></main>'''
        report = audit_visible_copy(html)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["issues"][0]["text"], "NIGHT TRANSFER LAB")

    def test_renderer_source_has_no_hardcoded_latin_visible_copy(self) -> None:
        source = (SCRIPTS / "html_production_renderer.py").read_text(encoding="utf-8")
        report = audit_renderer_source(source)
        self.assertEqual(report["status"], "pass", report["issues"])

    def test_optional_cover_metadata_is_omitted_instead_of_filled(self) -> None:
        markup = renderer._hero_fullbleed_brand(
            {"title": "凌晨兩點", "subtitle": "把回家的路接起來"}
        )
        self.assertNotIn("cover-hero-speaker", markup)
        self.assertNotIn("cover-hero-org", markup)

    def test_map_caption_is_source_backed_and_optional(self) -> None:
        content = {
            "title": "三個必要節點",
            "locations": [
                ("站點一", "01", "說明一"),
                ("站點二", "02", "說明二"),
                ("站點三", "03", "說明三"),
            ],
        }
        without_caption = renderer._map_with_cards(content, True)
        self.assertNotIn("map-caption", without_caption)
        with_caption = renderer._map_with_cards(
            {**content, "map_caption": "夜間轉乘觀察區"}, True
        )
        self.assertIn("夜間轉乘觀察區", with_caption)


if __name__ == "__main__":
    unittest.main()
