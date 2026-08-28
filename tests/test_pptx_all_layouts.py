import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compile_renderer_matrix import RETIRED_LAYOUT_IDS, layout_record  # noqa: E402
from pptx_variant_runtime import ALLOWED_PLACEHOLDER_TYPES  # noqa: E402


class PptxAllLayoutsTests(unittest.TestCase):
    def test_every_active_layout_has_a_typed_pptx_projection(self):
        paths = sorted(
            path
            for path in (ROOT / "prompt_system" / "layouts").glob("*.yaml")
            if path.stem not in RETIRED_LAYOUT_IDS
        )
        adapter_paths = sorted(
            path
            for path in (ROOT / "prompt_system" / "renderers" / "pptx" / "layouts").glob("*.yaml")
            if path.stem not in RETIRED_LAYOUT_IDS
        )
        records = [layout_record(path) for path in paths]
        self.assertGreater(len(records), 0)
        self.assertEqual([path.stem for path in paths], [path.stem for path in adapter_paths])
        missing = [record["id"] for record in records if not record["pptx"]["placeholder_schema"]]
        self.assertEqual(missing, [])
        for record in records:
            rows = record["pptx"]["placeholder_schema"]
            self.assertTrue(all(row["placeholder_type"] in ALLOWED_PLACEHOLDER_TYPES for row in rows))
            self.assertTrue(
                all(
                    row["frame_policy"] == "fixed"
                    for row in rows
                    if row["placeholder_type"] in {"title", "subtitle"}
                )
            )


if __name__ == "__main__":
    unittest.main()
