import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pptx_background_runtime import (  # noqa: E402
    REQUIRED_ROLES,
    _validate_set,
    resolve_background_set,
)


class PptxBackgroundRuntimeTests(unittest.TestCase):
    def test_explicit_set_selection_records_provenance(self):
        result = resolve_background_set("clean-tech-business", "clean-tech-business", require_assets=False)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["background_set_id"], "clean-tech-business")
        self.assertEqual(result["source_manifest"], "prompt_system/pptx_background_sets/clean-tech-business.yaml")
        self.assertEqual(result["selection_basis"], "explicit-background-set")
        self.assertIn("roles", result)

    def test_fresh_generated_set_is_explicit_generation_required_in_clean_release(self):
        result = resolve_background_set("brand-editorial", "fresh-mineral-editorial-20260827", require_assets=True)
        self.assertEqual(result["status"], "generation-required")
        self.assertEqual(result["background_set_id"], "fresh-mineral-editorial-20260827")
        self.assertIn(result["selection_basis"], {"explicit-set-missing", "invalid-background-set"})
        self.assertEqual(result["generation_plan"]["roles"], list(REQUIRED_ROLES))
        self.assertEqual(result["generation_plan"]["renderer"], "image2")
        self.assertNotIn("roles", result)

    def test_second_fresh_set_keeps_its_identity_when_generation_is_required(self):
        result = resolve_background_set("brand-editorial", "fresh-inkprint-20260828", require_assets=True)
        self.assertEqual(result["status"], "generation-required")
        self.assertEqual(result["background_set_id"], "fresh-inkprint-20260828")
        self.assertEqual(result["generation_plan"]["roles"], list(REQUIRED_ROLES))
        self.assertNotIn("roles", result)

    def test_missing_set_is_generation_required_without_brand_editorial_fallback(self):
        result = resolve_background_set("new-theme", "new-theme-fresh", require_assets=False)
        self.assertEqual(result["status"], "generation-required")
        self.assertEqual(result["background_set_id"], "new-theme-fresh")
        self.assertNotIn("brand-editorial", str(result))
        self.assertEqual(result["generation_plan"]["roles"], list(REQUIRED_ROLES))

    def test_theme_mismatch_is_rejected(self):
        result = resolve_background_set("clean-tech-business", "brand-editorial", require_assets=False)
        self.assertEqual(result["status"], "generation-required")
        self.assertEqual(result["selection_basis"], "explicit-set-theme-mismatch")

    def test_six_role_validation_is_required(self):
        data = {"theme_id": "demo", "theme_ref": "prompt_system/themes/demo.yaml", "roles": [{"id": role, "asset": f"assets/{role}.png"} for role in REQUIRED_ROLES[:-1]]}
        result = _validate_set("demo", "demo", ROOT / "demo.yaml", data, require_assets=False)
        self.assertEqual(result["status"], "generation-required")
        self.assertTrue(any("roles=" in issue for issue in result["issues"]))


if __name__ == "__main__":
    unittest.main()
