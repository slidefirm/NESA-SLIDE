import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pptx_variant_runtime import (  # noqa: E402
    ARTIFACT_TOOL_STAGE_PX,
    CANONICAL_STAGE_PX,
    placeholder_type,
    project_placeholders,
    resolve_variant,
    stage_font_px_to_points,
    stage_region_to_artifact,
)


class PptxVariantRuntimeTests(unittest.TestCase):
    def test_fixed_geometry_boundary_is_exact_two_thirds(self):
        self.assertEqual(CANONICAL_STAGE_PX, (1920, 1080))
        self.assertEqual(ARTIFACT_TOOL_STAGE_PX, (1280, 720))
        self.assertEqual(stage_region_to_artifact([0, 0, 1920, 1080]), [0.0, 0.0, 1280.0, 720.0])
        self.assertEqual(stage_font_px_to_points(36), 18.0)

    def test_title_alias_does_not_misclassify_executive_role(self):
        self.assertEqual(placeholder_type("headline"), "title")
        self.assertEqual(placeholder_type("title-role", {"label": "職稱 / 公司"}), "subtitle")
        self.assertEqual(placeholder_type("role"), "subtitle")

    def test_people_fixed_base_is_atomic_without_invented_variant(self):
        slots = [
            {"id": "title", "region": [8, 8, 84, 10]},
            {"id": "person-1", "region": [8, 28, 24, 62]},
            {"id": "person-2", "region": [38, 28, 24, 62]},
            {"id": "person-3", "region": [68, 28, 24, 62]},
        ]
        result = project_placeholders("people-3", slots, {"item_count": 3, "has_image": True})
        self.assertIsNone(result["selected_variant_id"])
        ids = {row["id"] for row in result["placeholder_schema"]}
        self.assertIn("person-1-photo", ids)
        self.assertIn("person-1-name", ids)
        self.assertIn("person-1-role", ids)
        self.assertIn("person-1-bio", ids)
        self.assertTrue(all(row["placeholder_type"] != "body" or row["content_kind"] == "text" for row in result["placeholder_schema"]))

    def test_explicit_incompatible_variant_fails(self):
        with self.assertRaisesRegex(ValueError, "Incompatible"):
            resolve_variant("cards-1-plus-3", {"item_count": 2}, "metric-title")

    def test_picture_and_text_are_typed_separately(self):
        slots = [
            {"id": "photo", "region": [5, 12, 28, 76]},
            {"id": "name", "region": [38, 15, 57, 13]},
            {"id": "title-role", "region": [38, 30, 57, 8]},
            {"id": "bio", "region": [38, 41, 57, 36]},
            {"id": "meta", "region": [38, 80, 57, 8]},
        ]
        result = project_placeholders("executive-bio", slots)
        by_id = {row["id"]: row for row in result["placeholder_schema"]}
        self.assertEqual(by_id["photo"]["placeholder_type"], "picture")
        self.assertEqual(by_id["name"]["placeholder_type"], "body")
        self.assertEqual(by_id["title-role"]["placeholder_type"], "subtitle")

    def test_decoration_is_excluded(self):
        slots = [
            {"id": "quote-decor", "region": [10, 15, 8, 15], "note": "裝飾性大引號"},
            {"id": "quote", "region": [12, 18, 76, 44]},
            {"id": "photo", "region": [12, 68, 11, 22]},
            {"id": "name", "region": [26, 70, 44, 8]},
            {"id": "role", "region": [26, 80, 44, 7]},
            {"id": "logo", "region": [76, 68, 14, 18]},
        ]
        result = project_placeholders("testimonial-full", slots, {"quote": "A quote"})
        self.assertNotIn("quote-decor", {row["id"] for row in result["placeholder_schema"]})
        self.assertEqual({row["placeholder_type"] for row in result["placeholder_schema"]}, {"body", "subtitle", "picture"})

    def test_testimonial_specific_card_beats_generic_centered(self):
        result = resolve_variant("testimonial-full", {"quote": "A quote", "attribution_card": True})
        self.assertEqual(result["selected_variant_id"], "card")

    def test_title_center_and_stats_contracts_follow_core_roles(self):
        title_slots = [
            {"id": "headline", "region": [10, 25, 80, 48]},
            {"id": "supporting-text", "region": [10, 76, 80, 8]},
        ]
        title_result = project_placeholders("title-center", title_slots)
        title_rows = {row["id"]: row for row in title_result["placeholder_schema"]}
        self.assertEqual(title_rows["headline"]["placeholder_type"], "title")
        self.assertEqual(title_rows["supporting-text"]["placeholder_type"], "subtitle")
        self.assertEqual(title_rows["headline"]["font_size_stage_px"], 56.0)
        self.assertEqual(title_rows["headline"]["frame_policy"], "fixed")
        self.assertEqual(title_rows["supporting-text"]["frame_policy"], "fixed")
        self.assertEqual([round(value, 4) for value in stage_region_to_artifact([192, 270, 1536, 518.4])], [128.0, 180.0, 1024.0, 345.6])
        stat_slots = [
            {"id": "eyebrow", "region": [10, 8, 80, 8]},
            {"id": "stat-1", "region": [8, 24, 24, 54]},
            {"id": "stat-2", "region": [38, 24, 24, 54]},
            {"id": "stat-3", "region": [68, 24, 24, 54]},
            {"id": "footnote", "region": [10, 84, 80, 8]},
        ]
        stat_result = project_placeholders("stats-3-row", stat_slots)
        self.assertFalse(any(row["placeholder_type"] == "title" for row in stat_result["placeholder_schema"]))
        self.assertTrue(all(row["frame_policy"] == "content-fit" for row in stat_result["placeholder_schema"] if row["placeholder_type"] == "body"))

    def test_cards_metric_is_more_specific_than_generic_fallback(self):
        content = {"item_count": 3, "items": [{"body": "42% completed"}] * 3}
        self.assertEqual(resolve_variant("cards-1-plus-3", content)["selected_variant_id"], "metric-title")

    def test_map_is_picture_and_team_members_are_atomic(self):
        map_slots = [
            {"id": "title", "region": [5, 4, 90, 8]},
            {"id": "map", "region": [5, 14, 60, 78]},
            {"id": "data-card-1", "region": [68, 14, 27, 22]},
            {"id": "data-card-2", "region": [68, 39, 27, 22]},
            {"id": "data-card-3", "region": [68, 64, 27, 22]},
        ]
        map_rows = {row["id"]: row for row in project_placeholders("map-region", map_slots)["placeholder_schema"]}
        self.assertEqual(map_rows["map"]["placeholder_type"], "picture")
        self.assertEqual(map_rows["map"]["content_kind"], "image")
        team_slots = [{"id": "title", "region": [8, 5, 84, 9]}] + [
            {"id": f"member-{index}", "region": [5, 18, 28, 36]} for index in range(1, 7)
        ]
        team_ids = {row["id"] for row in project_placeholders("team-grid", team_slots)["placeholder_schema"]}
        self.assertIn("member-1-photo", team_ids)
        self.assertIn("member-1-name", team_ids)
        self.assertIn("member-1-role", team_ids)

    def test_fullbleed_background_is_not_a_picture_placeholder(self):
        slots = [
            {"id": "title", "region": [8, 58, 72, 20]},
            {"id": "subtitle", "region": [8, 79, 62, 6]},
            {"id": "speaker", "region": [8, 87, 44, 4]},
            {"id": "org", "region": [8, 91, 44, 4]},
            {"id": "org-logo", "placement": {"default": "watermark", "watermark_region": [87, 6, 10, 8], "main_region": [8, 95, 14, 4]}},
        ]
        ids = {row["id"] for row in project_placeholders("hero-fullbleed", slots)["placeholder_schema"]}
        self.assertNotIn("hero-photo", ids)

    def test_missing_contract_fails_loudly(self):
        with self.assertRaisesRegex(ValueError, "no core slot"):
            project_placeholders("executive-bio", [{"id": "photo", "region": [0, 0, 1, 1]}])

    def test_cards_variant_order_and_typed_module_anatomy(self):
        content = {
            "items": [
                {"title": "A", "body": "This is a sufficiently long module body.", "tag": "A"},
                {"title": "B", "body": "This is another sufficiently long module body.", "tag": "B"},
                {"title": "C", "body": "This is the third sufficiently long module body.", "tag": "C"},
            ],
            "item_count": 3,
            "all_icons_resolved": True,
        }
        result = resolve_variant("cards-1-plus-3", content)
        self.assertEqual(result["selected_variant_id"], "side-icon-body")
        with self.assertRaisesRegex(ValueError, "Incompatible"):
            resolve_variant("cards-1-plus-3", {"item_count": 2}, "metric-title")


if __name__ == "__main__":
    unittest.main()
