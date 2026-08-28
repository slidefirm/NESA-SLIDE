import unittest

from scripts import html_image_background_experiment as experiment


class HtmlImageBackgroundMaskContractTests(unittest.TestCase):
    def test_outline_is_counted_only_when_it_is_actually_drawn(self) -> None:
        scripts = (
            experiment.MASK_SCRIPT,
            experiment.PER_SLIDE_MASK_SCRIPT,
            experiment.SINGLE_SLIDE_MASK_SCRIPT,
        )
        for script in scripts:
            self.assertIn("const hasOutline", script)
            self.assertIn("style.outlineStyle !== 'none'", script)
            self.assertIn("alphaOf(style.outlineColor) > 0.04", script)
            self.assertNotIn(
                "|| parseFloat(style.outlineWidth) > 0",
                script,
            )


if __name__ == "__main__":
    unittest.main()
