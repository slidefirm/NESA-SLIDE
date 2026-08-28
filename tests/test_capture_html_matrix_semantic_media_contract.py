from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CaptureHtmlMatrixSemanticMediaContractTests(unittest.TestCase):
    def test_image_planned_semantic_photo_is_checked_not_silently_allowed(self) -> None:
        source = (ROOT / "scripts" / "capture_html_matrix.cjs").read_text(encoding="utf-8")
        for token in (
            "semantic-image-contract",
            "assetPolicy === 'image-planned'",
            "slide.dataset.imageVariant === 'photo'",
            "image.naturalWidth > 0",
            "image.naturalHeight > 0",
            ".cover-media-field,.toc-image-field,.closing-photo-field",
            "image.dataset.imageProvenance",
            "image.dataset.semanticImageSource",
            "image.dataset.semanticImageSha256",
        ):
            self.assertIn(token, source)

    def test_intrinsic_text_frame_allowance_stays_scoped_to_no_scroll_frames(self) -> None:
        source = (ROOT / "scripts" / "capture_html_matrix.cjs").read_text(encoding="utf-8")
        self.assertIn("const intrinsicTextFrame", source)
        self.assertIn("el.dataset.editFit === 'text'", source)
        self.assertIn("el.scrollWidth <= el.clientWidth + 1", source)
        self.assertIn("el.scrollHeight <= el.clientHeight + 1", source)
        self.assertIn("const intrinsicWidthAllowance", source)

    def test_direct_page_text_roots_have_a_browser_collision_gate(self) -> None:
        source = (ROOT / "scripts" / "capture_html_matrix.cjs").read_text(encoding="utf-8")
        self.assertIn("page-text-root-overlap", source)
        self.assertIn('.prod-frame > .el[data-edit-kind="text"]', source)
        self.assertIn("overlapHeight > 0.5", source)


if __name__ == "__main__":
    unittest.main()
