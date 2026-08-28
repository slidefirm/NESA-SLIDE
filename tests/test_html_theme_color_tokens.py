from __future__ import annotations

import pathlib
import sys
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compile_renderer_matrix import theme_record  # noqa: E402
import html_production_renderer as production  # noqa: E402


class HtmlThemeColorTokenTests(unittest.TestCase):
    def test_theme_core_contains_no_renderer_or_layout_geometry(self) -> None:
        forbidden = {"html_spec", "pptx_spec", "layout_overrides"}
        for path in sorted((ROOT / "prompt_system/themes").glob("*.yaml")):
            with self.subTest(theme=path.stem):
                theme = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertFalse(
                    forbidden & set(theme),
                    f"{path.name} contains Theme-owned renderer/Layout geometry",
                )

    def test_dark_circuit_keeps_surface_separate_from_support_signal(self) -> None:
        theme = theme_record(ROOT / "prompt_system/themes/dark-circuit.yaml")

        self.assertEqual(theme["colors"]["surface"], "#232B40")
        self.assertEqual(theme["colors"]["support"], ["#89CFF0"])

        tokens = production.theme_tokens(theme)
        self.assertEqual(tokens["surface"], "#232B40")
        self.assertEqual(tokens["support_accent"], "#89CFF0")
        self.assertEqual(tokens["surface_text"], "#FFFFFF")
        self.assertNotIn("#66BB6A", tokens.values())


if __name__ == "__main__":
    unittest.main()
