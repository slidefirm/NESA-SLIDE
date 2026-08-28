from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from html_design_method import load_html_design_method, resolve_layout_plan  # noqa: E402
from html_layout_family import layout_family  # noqa: E402


def content_plan(*intents: str) -> list[dict[str, object]]:
    return [
        {
            "page_index": index,
            "page_id": f"page-{index + 1:02d}",
            "intent": intent,
            "content_key": intent,
            "source_fields": [],
            "content_relation": intent,
            "content_item_count": None,
        }
        for index, intent in enumerate(intents)
    ]


class HtmlLayoutDiversityTests(unittest.TestCase):
    def test_design_method_declares_diverse_default(self) -> None:
        method = load_html_design_method()
        self.assertEqual(method["layout_diversity_policy"]["default_selection"], "diverse")
        self.assertTrue(method["layout_diversity_policy"]["no_consecutive_repeat"])

    def test_html_adapters_use_the_shared_layout_family_mapping(self) -> None:
        adapter_root = PROJECT_ROOT / "prompt_system" / "renderers" / "html" / "layouts"
        for path in sorted(adapter_root.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            self.assertEqual(
                data.get("family"),
                layout_family(str(data.get("layout_id", ""))),
                path.name,
            )

    def test_diverse_selection_replays_and_avoids_consecutive_duplicates(self) -> None:
        plan = content_plan(
            "comparison",
            "comparison",
            "statement",
            "statement",
            "evidence",
            "evidence",
            "evidence",
        )
        first = resolve_layout_plan(
            {},
            random.Random(20260821),
            content_plan=plan,
            asset_policy="pattern-only",
            layout_selection="diverse",
        )
        replay = resolve_layout_plan(
            {},
            random.Random(20260821),
            content_plan=plan,
            asset_policy="pattern-only",
            layout_selection="diverse",
        )
        first_ids = [decision["layout_id"] for decision in first]
        replay_ids = [decision["layout_id"] for decision in replay]
        self.assertEqual(first_ids, replay_ids)
        self.assertTrue(all(left != right for left, right in zip(first_ids, first_ids[1:])))
        self.assertGreaterEqual(len(set(first_ids)), 5)
        self.assertTrue(
            all(
                decision["selection_basis"] == "semantic-candidates-seeded-diverse"
                for decision in first
            )
        )

    def test_forced_consecutive_duplicate_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "consecutive duplicate"):
            resolve_layout_plan(
                {},
                random.Random(20260821),
                forced_layouts=["split-comparison", "split-comparison"],
                content_plan=content_plan("comparison", "comparison"),
                asset_policy="pattern-only",
                layout_selection="diverse",
            )

    def test_authored_preferred_consecutive_duplicate_is_rejected(self) -> None:
        plan = content_plan("comparison", "comparison")
        plan[0]["preferred_layout"] = "split-comparison"
        plan[1]["preferred_layout"] = "split-comparison"
        with self.assertRaisesRegex(ValueError, "consecutive duplicate"):
            resolve_layout_plan(
                {},
                random.Random(20260821),
                content_plan=plan,
                asset_policy="pattern-only",
                layout_selection="preferred",
            )


if __name__ == "__main__":
    unittest.main()
