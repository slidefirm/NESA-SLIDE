import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pptx_randomization import DEFAULT_CONTENT, DEFAULT_MATRIX, build_selection, _load_json  # noqa: E402


class PptxRandomizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = _load_json(DEFAULT_MATRIX)
        cls.content = _load_json(DEFAULT_CONTENT)

    def test_defaults_use_packaged_current_matrix_and_release_fixture(self):
        self.assertEqual(DEFAULT_MATRIX, ROOT / "artifacts" / "renderer-matrix" / "matrix.json")
        self.assertEqual(DEFAULT_CONTENT, ROOT / "release" / "fixtures" / "pptx-randomization-content.json")
        self.assertTrue(DEFAULT_MATRIX.is_file())
        self.assertTrue(DEFAULT_CONTENT.is_file())

    def test_same_seed_replays_identical_selection(self):
        first = build_selection(self.matrix, seed=20260827, content=self.content, random_background=True)
        second = build_selection(self.matrix, seed=20260827, content=self.content, random_background=True)
        self.assertEqual(first, second)
        self.assertTrue(first["randomized_dimensions"])
        self.assertEqual(first["fixed_dimensions"]["slide_count"], len(first["slides"]))
        self.assertEqual(first["background_selection"]["status"], "generation-required")
        self.assertFalse(first["fixed_dimensions"]["background_randomized"])

    def test_different_seed_changes_layout_sequence(self):
        first = build_selection(self.matrix, seed=20260827, content=self.content)
        second = build_selection(self.matrix, seed=20260828, content=self.content)
        self.assertNotEqual(
            [row["layout_id"] for row in first["slides"]],
            [row["layout_id"] for row in second["slides"]],
        )

    def test_clean_release_background_randomization_is_generation_required(self):
        first = build_selection(self.matrix, seed=20260827, content=self.content, random_background=True)
        second = build_selection(self.matrix, seed=20260831, content=self.content, random_background=True)
        for result in (first, second):
            self.assertEqual(result["background_selection"]["status"], "generation-required")
            self.assertIsNone(result["background_selection"]["selected"])
            self.assertEqual(result["background_selection"]["selection_basis"], "generation-required")
            self.assertNotIn("background-set", result["randomized_dimensions"])

    def test_variant_selection_is_seeded_when_a_variant_layout_is_drawn(self):
        result = build_selection(self.matrix, seed=20260833, content=self.content)
        self.assertTrue(result["variant_draws"])
        selected = next(row for row in result["slides"] if row["layout_id"] == "cards-1-plus-3")
        self.assertEqual(selected["selected_variant_id"], "label-rule-body")
        self.assertIn("pptx-variant", result["randomized_dimensions"])

    def test_selection_is_not_a_forced_layout_sequence(self):
        result = build_selection(self.matrix, seed=11, content=self.content)
        self.assertEqual(result["randomized_dimensions"], ["layout-sequence", "pptx-variant"])
        self.assertTrue(all(row["selection_basis"] in {"fixed-base-projection", "content-match-priority", "explicit-compatible-override"} for row in result["slides"]))
        self.assertTrue(all(row["layout_id"] in {layout["id"] for layout in self.matrix["layouts"]} for row in result["slides"]))

    def test_theme_randomization_requires_a_ready_background_set(self):
        fixed = build_selection(self.matrix, seed=19, content=self.content)
        self.assertFalse(fixed["fixed_dimensions"]["theme_randomized"])
        with self.assertRaisesRegex(ValueError, "requires at least one Theme-compatible ready background set"):
            build_selection(self.matrix, seed=19, content=self.content, random_theme=True)


if __name__ == "__main__":
    unittest.main()
