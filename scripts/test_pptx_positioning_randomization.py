from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).with_name("pptx_randomization.py")
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("pptx_randomization_under_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CompositionOffsetPassThroughTests(unittest.TestCase):
    def test_direct_offset(self) -> None:
        value = {"dx": 0, "dy": 9, "basis": "visible-union-center"}
        self.assertEqual(MODULE.composition_offset_for_page({"composition_offset_percent": value}, 3), value)

    def test_nested_composition_plan_offset(self) -> None:
        value = {"dx": -2, "dy": 4}
        page = {"composition_plan": {"composition_offset_percent": value}}
        self.assertEqual(MODULE.composition_offset_for_page(page, 2), value)

    def test_missing_offset(self) -> None:
        self.assertIsNone(MODULE.composition_offset_for_page({}, 1))

    def test_invalid_offset_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "slide 4 composition_offset_percent must be a mapping"):
            MODULE.composition_offset_for_page({"composition_offset_percent": 9}, 4)


if __name__ == "__main__":
    unittest.main()
