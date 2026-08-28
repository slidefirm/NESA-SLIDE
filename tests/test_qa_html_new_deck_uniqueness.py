from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from qa_html_new_deck_uniqueness import audit  # noqa: E402


class NewDeckUniquenessTests(unittest.TestCase):
    def _write(self, name: str, content: str) -> Path:
        path = ROOT / "tests" / ".runtime" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.addCleanup(path.unlink)
        return path

    def test_distinct_visible_page_claims_and_bodies_pass(self) -> None:
        html = self._write(
            "new-deck-unique.html",
            '<section class="slide" id="s1"><div class="prod-title" data-edit-kind="text">主張一</div><p data-edit-layer="text">正文一</p></section>'
            '<section class="slide" id="s2"><div class="prod-title" data-edit-kind="text">主張二</div><p data-edit-layer="text">正文二</p></section>',
        )
        report = audit(html)
        self.assertEqual(report["status"], "pass", report["issues"])

    def test_duplicate_visible_claim_fails(self) -> None:
        html = self._write(
            "new-deck-duplicate.html",
            '<section class="slide" id="s1"><div class="prod-title" data-edit-kind="text">同一主張</div><p data-edit-layer="text">正文一</p></section>'
            '<section class="slide" id="s2"><div class="prod-title" data-edit-kind="text">同一主張</div><p data-edit-layer="text">正文二</p></section>',
        )
        self.assertIn("duplicate-visible-page-claim", [row["code"] for row in audit(html)["issues"]])

    def test_duplicate_visible_body_fails(self) -> None:
        html = self._write(
            "new-deck-duplicate-body.html",
            '<section class="slide" id="s1"><div class="prod-title" data-edit-kind="text">主張一</div><p data-edit-layer="text">同一正文</p></section>'
            '<section class="slide" id="s2"><div class="prod-title" data-edit-kind="text">主張二</div><p data-edit-layer="text">同一正文</p></section>',
        )
        self.assertIn("duplicate-visible-page-body", [row["code"] for row in audit(html)["issues"]])

    def test_missing_visible_body_fails(self) -> None:
        html = self._write(
            "new-deck-missing-body.html",
            '<section class="slide" id="s1"><div class="prod-title" data-edit-kind="text">只有標題</div></section>',
        )
        self.assertIn("missing-visible-page-body", [row["code"] for row in audit(html)["issues"]])

    def test_toc_side_panel_semantic_heading_is_a_visible_page_claim(self) -> None:
        html = self._write(
            "new-deck-toc-side-panel.html",
            '<section class="slide" id="s1">'
            '<div class="el toc-side-panel">'
            '<span data-edit-layer="text">決策地圖</span>'
            '<b data-edit-layer="text">四種訊號，決定一個 AI 試行能不能往下走</b>'
            '<p data-edit-layer="text">正文一</p>'
            '</div></section>',
        )
        report = audit(html)
        self.assertEqual(report["status"], "pass", report["issues"])
        self.assertEqual(report["pages"][0]["title"], "四種訊號，決定一個 AI 試行能不能往下走")
