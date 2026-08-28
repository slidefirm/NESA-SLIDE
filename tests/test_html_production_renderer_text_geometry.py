from __future__ import annotations

import copy
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import html_production_renderer as renderer  # noqa: E402


class _TagCollector(HTMLParser):
    def __init__(self, markup: str) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.feed(markup)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {name: value or "" for name, value in attrs}))

    def with_class(self, class_name: str) -> list[dict[str, str]]:
        return [
            attrs
            for _, attrs in self.tags
            if class_name in attrs.get("class", "").split()
        ]


def _style_box(attrs: dict[str, str]) -> dict[str, float]:
    declarations = {}
    for declaration in attrs.get("style", "").split(";"):
        if ":" not in declaration:
            continue
        name, value = declaration.split(":", 1)
        declarations[name.strip()] = value.strip()
    box = {}
    for name in ("left", "top", "width", "height"):
        value = declarations.get(name, "")
        if value == "0":
            box[name] = 0.0
            continue
        match = re.fullmatch(r"(-?\d+(?:\.\d+)?)px", value)
        if match:
            box[name] = float(match.group(1))
    return box


def _css_rule(selector: str) -> str:
    match = re.search(re.escape(selector) + r"\{([^}]*)\}", renderer.PRODUCTION_CSS)
    if not match:
        raise AssertionError(f"Missing CSS rule: {selector}")
    return match.group(1)


def _font_px(selector: str) -> float:
    rule = _css_rule(selector)
    match = re.search(r"(?:font-size|font)\s*:[^;}]*?(\d+(?:\.\d+)?)px", rule)
    if not match:
        raise AssertionError(f"Missing px font size for {selector}: {rule}")
    return float(match.group(1))


class ProductionRendererTextGeometryTests(unittest.TestCase):
    def assert_inside_content_area(self, attrs: dict[str, str]) -> None:
        box = _style_box(attrs)
        self.assertEqual(set(box), {"left", "top", "width", "height"}, attrs)
        self.assertGreaterEqual(box["left"], 0)
        self.assertGreaterEqual(box["top"], 0)
        self.assertLessEqual(box["left"] + box["width"], renderer.CONTENT_W + 0.01)
        self.assertLessEqual(box["top"] + box["height"], renderer.CONTENT_H + 0.01)

    def test_renderer_font_floor_is_source_assertion_and_preserves_hierarchy(self) -> None:
        legal = ".card>b{font-size:42px}.card>p{font-size:36px}"
        self.assertEqual(renderer.normalize_generated_css_font_sizes(legal), legal)
        with self.assertRaisesRegex(ValueError, "migrate the owning Layout geometry"):
            renderer.normalize_generated_css_font_sizes(".card>p{font-size:20px}")

        for title_selector, body_selector in (
            (".map-data-card>b", ".map-data-card>p"),
            (".module-card>b", ".module-card>p"),
            (".toc-nav-card>b", ".toc-nav-card>p"),
            (".metric-card-label", ".metric-card-note"),
            (".metric-stat-label", ".metric-stat-note"),
            (".swot-label", ".swot-card li"),
        ):
            self.assertGreaterEqual(
                _font_px(title_selector),
                _font_px(body_selector) + 6,
                (title_selector, body_selector),
            )

    def test_split_comparison_two_line_rows_fit_at_the_font_floor(self) -> None:
        rule = _css_rule(".split-panel li b")
        self.assertIn("font:650 36px/1.2", rule)
        self.assertIn("text-wrap:balance", rule)
        self.assertEqual(_font_px(".split-panel li b"), renderer.GENERATED_TEXT_MIN_PX)
        self.assertLessEqual(2 * 36 * 1.2, 88)

    def test_map_cards_recompute_geometry_from_36px_note_capacity(self) -> None:
        content = {
            "title": "三個必要節點",
            "locations": [
                ("繼續觀察", "01", "先從真正離開工作的時間開始。"),
                ("立即推進", "02", "先守住醫療、照護與夜班者不能繞開的節點。"),
                ("保留彈性", "03", "標出最後可轉乘的班次與出口。"),
            ],
        }
        markup = renderer._map_with_cards(content, True)
        cards = _TagCollector(markup).with_class("map-data-card")
        self.assertEqual(len(cards), 3)
        boxes = [_style_box(card) for card in cards]
        self.assertTrue(all(box["width"] == 553 for box in boxes))
        self.assertTrue(all(box["height"] >= 209 for box in boxes))
        for first, second in zip(boxes, boxes[1:]):
            self.assertGreaterEqual(second["top"] - (first["top"] + first["height"]), 12)

    def test_cover_photo_speaker_and_org_keep_a_real_vertical_gap(self) -> None:
        content = {
            "title": "虛構標題",
            "subtitle": "虛構副標",
            "speaker": "虛構資料聲明",
            "org": "虛構計畫室",
        }
        tags = _TagCollector(renderer._cover_photo_frame(content, "right"))
        speaker = _style_box(tags.with_class("cover-split-speaker")[0])
        org = _style_box(tags.with_class("cover-split-org")[0])
        self.assertGreaterEqual(org["top"] - speaker["top"], 60)

    def test_map_placeholder_remains_a_layer_not_a_nested_edit_root(self) -> None:
        content = copy.deepcopy(renderer.DATAVIZ_CONTENT["map-spotlight"])
        markup = renderer._map_with_cards(content, True)
        placeholder = renderer.apply_media_placeholder_policy(markup, "map-spotlight", "placeholder-fill")
        self.assertIn('class="media-placeholder-fill map-media-placeholder"', placeholder)
        self.assertNotIn('class="el media-placeholder-fill map-media-placeholder"', placeholder)

    def test_cycle_uses_canonical_three_by_three_slots_and_one_loop(self) -> None:
        content = copy.deepcopy(renderer.DIAGRAM_CONTENT["cycle-hub-6"])
        markup = renderer._cycle(content)
        tags = _TagCollector(markup)

        self.assertEqual(len(tags.with_class("cycle-callout-left")), 3)
        self.assertEqual(len(tags.with_class("cycle-callout-right")), 3)
        self.assertNotIn("cycle-callout-top", markup)
        self.assertNotIn("cycle-callout-bottom", markup)
        self.assertEqual(markup.count('data-cycle-slot="item-'), 6)
        self.assertEqual(markup.count('data-cycle-loop="true"'), 1)
        self.assertIn('data-cycle-order="clockwise-01-02-03-04-05-06"', markup)
        self.assertIn('data-cycle-geometry="circle"', markup)
        self.assertEqual(markup.count('data-cycle-arc="'), 6)
        self.assertIn('class="cycle-ring"', markup)
        nodes = tags.with_class("cycle-node")
        self.assertEqual(len(nodes), 6)
        self.assertEqual(
            [node.get("data-cycle-position") for node in nodes],
            ["upper-right", "right-middle", "lower-right", "lower-left", "left-middle", "upper-left"],
        )
        self.assertEqual([node.get("data-cycle-order") for node in nodes], [str(index) for index in range(1, 7)])
        self.assertEqual(sum(node.get("data-cycle-start") == "true" for node in nodes), 1)
        callouts = tags.with_class("cycle-callout")
        self.assertEqual([item.get("data-cycle-order") for item in callouts], [str(index) for index in range(1, 7)])
        for attrs in tags.with_class("cycle-callout"):
            self.assert_inside_content_area(attrs)
        self.assertNotIn("diagram-hub-body", markup)
        self.assertIn('data-visual-surface-role="none"', markup)

        for selector in (
            ".diagram-hub-title",
            ".cycle-node .diagram-no",
            ".cycle-callout .diagram-node-title",
            ".cycle-callout .diagram-node-body",
        ):
            self.assertGreaterEqual(_font_px(selector), renderer.GENERATED_TEXT_MIN_PX)

        invalid = copy.deepcopy(content)
        invalid["items"] = invalid["items"][:-1]
        with self.assertRaisesRegex(ValueError, "exactly six items"):
            renderer._cycle(invalid)

    def test_page_title_alignment_propagates_with_circle_number_exception(self) -> None:
        cycle = renderer.materialize_editable_production_markup(
            renderer._cycle(copy.deepcopy(renderer.DIAGRAM_CONTENT["cycle-hub-6"]))
        )
        tags = _TagCollector(cycle)

        for class_name in ("diagram-node-title", "diagram-node-body", "diagram-hub-title"):
            records = tags.with_class(class_name)
            self.assertTrue(records)
            self.assertTrue(
                all(item.get("data-edit-horizontal-align") == "center" for item in records)
            )
            self.assertTrue(
                all(item.get("data-edit-alignment-source") == "page-title" for item in records)
            )

        circle_numbers = tags.with_class("circle-number-metric")
        self.assertEqual(len(circle_numbers), 6)
        self.assertTrue(
            all(item.get("data-edit-horizontal-align") == "center" for item in circle_numbers)
        )
        self.assertTrue(
            all(
                item.get("data-edit-alignment-source") == "circle-number-exception"
                for item in circle_numbers
            )
        )

    def test_left_title_alignment_propagates_to_surface_layers(self) -> None:
        markup = renderer._dashboard_overview(
            copy.deepcopy(renderer.METRICS_CONTENT["dashboard-overview"])
        )
        tags = _TagCollector(markup)

        title = tags.with_class("prod-title")[0]
        self.assertEqual(title.get("data-edit-title-align"), "left")
        self.assertEqual(title.get("data-edit-horizontal-align"), "left")
        for class_name in ("metric-strip-label", "metric-strip-value", "metric-strip-delta"):
            records = tags.with_class(class_name)
            self.assertTrue(records)
            self.assertTrue(
                all(item.get("data-edit-horizontal-align") == "left" for item in records)
            )
            self.assertTrue(
                all(item.get("data-edit-alignment-source") == "page-title" for item in records)
            )

    def test_process_flow_numbers_declare_parent_center_axis(self) -> None:
        markup = renderer.materialize_editable_production_markup(
            renderer._process_flow(copy.deepcopy(renderer.SEQUENCE_CONTENT["process-flow"]))
        )
        tags = _TagCollector(markup)
        numbers = tags.with_class("circle-number-metric")
        self.assertEqual(len(numbers), 5)
        self.assertTrue(
            all(item.get("data-edit-align-contract") == "parent-center-axis" for item in numbers)
        )

    def test_before_after_uses_paired_causal_rows_without_synthetic_chart(self) -> None:
        content = copy.deepcopy(renderer.COMPARISON_CONTENT["before-after"])
        content["bridge"] = "不應輸出"
        content["rail_label"] = "不應輸出"
        markup = renderer._before_after(content)
        tags = _TagCollector(markup)

        headers = tags.with_class("compare-state-header")
        rows = tags.with_class("compare-pair-row")
        self.assertEqual(len(headers), 2)
        self.assertEqual(len(rows), len(content["before"][3]))
        self.assertEqual(
            [row.get("data-comparison-pair-index") for row in rows],
            [str(index) for index in range(1, len(rows) + 1)],
        )
        self.assertNotIn("compare-signal", markup)
        self.assertNotIn("compare-rail", markup)
        self.assertNotIn("compare-panel", markup)
        self.assertNotIn("data-orphan-intentional", markup)
        self.assertNotIn("不應輸出", markup)
        self.assertIn("display:flex", _css_rule(".compare-state-header"))
        self.assertIn("gap:12px", _css_rule(".compare-state-header"))
        self.assertIn("grid-template-columns", _css_rule(".compare-pair-row"))
        self.assertIn("font:650 40px/1.2", _css_rule(".compare-pair-before,.compare-pair-after"))
        self.assertIn(
            '.diagram-node.compare-state-header>[data-edit-position="flow"]',
            renderer.PRODUCTION_CSS,
        )
        self.assertIn(
            '.diagram-node.compare-pair-row>[data-edit-position="flow"]',
            renderer.PRODUCTION_CSS,
        )

    def test_strategic_priorities_do_not_apply_index_based_surface_emphasis(self) -> None:
        content = copy.deepcopy(renderer.CONTENT_CONTENT["strategic-priorities"])
        markup = renderer._strategic_priorities(content)
        cards = _TagCollector(markup).with_class("content-priority-card")

        self.assertEqual(len(cards), len(content["priorities"]))
        self.assertEqual([card.get("data-card-index") for card in cards], [str(index) for index in range(1, len(cards) + 1)])
        self.assertTrue(all(not any(token.startswith("priority-") for token in card.get("class", "").split()) for card in cards))
        self.assertNotIn("priority-1", renderer.PRODUCTION_CSS)
        self.assertNotIn("priority-2", renderer.PRODUCTION_CSS)

    def test_dashboard_uses_flow_geometry_and_three_two_line_insight_rows(self) -> None:
        content = copy.deepcopy(renderer.METRICS_CONTENT["dashboard-overview"])
        markup = renderer._dashboard_overview(content)
        tags = _TagCollector(markup)

        self.assertIn('data-layout-flow-id="dashboard-header"', markup)
        self.assertIn('data-layout-follow="dashboard-header"', markup)
        self.assertEqual(markup.count("<li>"), 3)
        for class_name in ("metric-kpi-strip", "metric-chart-panel", "metric-insight"):
            records = tags.with_class(class_name)
            self.assertEqual(len(records), 1)
            self.assert_inside_content_area(records[0])

        for class_name in ("metric-panel-kicker", "metric-panel-title", "metric-insight-title"):
            for attrs in tags.with_class(class_name):
                self.assertEqual(attrs.get("data-edit-position"), "flow")

        self.assertIn("position:relative", _css_rule(".metric-chart-panel"))
        self.assertIn("display:flex", _css_rule(".metric-insight"))
        self.assertIn("repeat(3,minmax(0,1fr))", _css_rule(".metric-insight ul"))

        for selector in (
            ".dashboard-footnote",
            ".metric-strip-label",
            ".metric-strip-value",
            ".metric-strip-delta",
            ".metric-panel-kicker",
            ".metric-panel-title",
            ".metric-panel-value",
            ".metric-chart-labels span",
            ".metric-insight-title",
            ".metric-insight li span",
            ".metric-insight li b",
        ):
            self.assertGreaterEqual(_font_px(selector), renderer.GENERATED_TEXT_MIN_PX)

        insight_height = _style_box(tags.with_class("metric-insight")[0])["height"]
        vertical_padding = 22 + 14
        kicker_height = 36
        title_height = 36 * 1.15
        title_gap = 8
        list_gap = 14
        per_row = (
            insight_height
            - vertical_padding
            - kicker_height
            - title_height
            - title_gap
            - list_gap
        ) / 3
        self.assertGreaterEqual(per_row, 2 * 36 * 1.22)

        invalid = copy.deepcopy(content)
        invalid["insight"] = (*invalid["insight"][:2], invalid["insight"][2] + ["extra"])
        with self.assertRaisesRegex(ValueError, "exactly three insight rows"):
            renderer._dashboard_overview(invalid)

    def test_kpi_scorecards_keep_notes_and_deltas_editable_at_36px(self) -> None:
        content = copy.deepcopy(renderer.METRICS_CONTENT["kpi-scorecards"])
        markup = renderer._kpi_scorecards(content)
        tags = _TagCollector(markup)

        self.assertIn('data-layout-flow-id="kpi-header"', markup)
        self.assertEqual(len(tags.with_class("prod-subtitle")), 0)
        self.assertEqual(len(tags.with_class("metric-card-index")), 0)
        title = tags.with_class("prod-title")[0]
        self.assertEqual(title.get("data-edit-align-contract"), "center-axis")
        self.assertEqual(title.get("data-edit-horizontal-align"), "center")
        cards = tags.with_class("metric-kpi-card")
        self.assertEqual(len(cards), 4)
        for attrs in cards:
            self.assert_inside_content_area(attrs)
        self.assert_inside_content_area(tags.with_class("metric-takeaway")[0])

        for class_name in ("metric-card-note", "metric-card-delta"):
            records = tags.with_class(class_name)
            self.assertEqual(len(records), 4)
            self.assertTrue(all(item.get("data-edit-position") == "absolute" for item in records))
            self.assertTrue(
                all(item.get("data-edit-horizontal-align") == "center" for item in records)
            )

        takeaway_text = [
            attrs
            for _, attrs in tags.tags
            if attrs.get("data-edit-layer") == "text"
            and attrs.get("data-edit-position") == "flow"
        ][-1]
        self.assertEqual(takeaway_text.get("data-edit-horizontal-align"), "center")
        self.assertEqual(takeaway_text.get("data-edit-alignment-source"), "page-title")

        for selector in (
            ".metric-card-value",
            ".metric-card-label",
            ".metric-card-note",
            ".metric-card-delta",
            ".metric-takeaway span",
        ):
            self.assertGreaterEqual(_font_px(selector), renderer.GENERATED_TEXT_MIN_PX)

        six_card_content = copy.deepcopy(content)
        six_card_content["cards"] = content["cards"] + [
            ("91%", "完成驗收", "兩個團隊已完成回寫", "↑ 8pt"),
            ("12", "停止理由", "每一筆都保留決策證據", "↑ 4"),
        ]
        six_markup = renderer._kpi_scorecards(six_card_content)
        six_cards = _TagCollector(six_markup).with_class("metric-kpi-card")
        self.assertEqual(len(six_cards), 6)
        for attrs in six_cards:
            self.assert_inside_content_area(attrs)

        card_height = _style_box(cards[0])["height"]
        required_height = (
            28 * 2
            + 72 * 0.96
            + 36 * 1.15
            + 2 * 36 * 1.22
            + 36
            + 4 * 10
        )
        self.assertLessEqual(required_height, card_height)

    def test_kpi_background_keeps_full_module_bounds_behind_content(self) -> None:
        rule = _css_rule('.metric-kpi-card[data-edit-structure="module"]>.diagram-node-bg')
        self.assertIn("inset:0", rule)
        self.assertIn("z-index:0", rule)
        content_rule = _css_rule(".metric-kpi-card>[data-edit-layer]")
        self.assertIn("left:28px", content_rule)
        self.assertIn("right:28px", content_rule)
        self.assertIn("text-align:center", content_rule)
        self.assertIn("top:144px", _css_rule(".metric-card-label"))
        delta_rule = _css_rule(".metric-card-delta")
        self.assertIn("left:28px", delta_rule)
        self.assertIn("right:28px", delta_rule)
        centered_takeaway_rule = _css_rule('.metric-takeaway[data-edit-horizontal-align="center"]')
        self.assertIn("justify-content:center", centered_takeaway_rule)

    def test_kpi_takeaway_is_optional_and_enforces_content_length(self) -> None:
        content = copy.deepcopy(renderer.METRICS_CONTENT["kpi-scorecards"])

        without_takeaway = copy.deepcopy(content)
        without_takeaway.pop("takeaway")
        markup = renderer._kpi_scorecards(without_takeaway)
        self.assertEqual(len(_TagCollector(markup).with_class("metric-takeaway")), 0)

        empty_takeaway = copy.deepcopy(content)
        empty_takeaway["takeaway"] = "  "
        markup = renderer._kpi_scorecards(empty_takeaway)
        self.assertEqual(len(_TagCollector(markup).with_class("metric-takeaway")), 0)

        short_takeaway = copy.deepcopy(content)
        short_takeaway["takeaway"] = "五個傳統市場"
        with self.assertRaisesRegex(ValueError, "18 to 44 non-whitespace characters"):
            renderer._kpi_scorecards(short_takeaway)

        long_takeaway = copy.deepcopy(content)
        long_takeaway["takeaway"] = "總" * 45
        with self.assertRaisesRegex(ValueError, "18 to 44 non-whitespace characters"):
            renderer._kpi_scorecards(long_takeaway)

    def test_timeline_milestones_rejects_enclosing_surface_paint(self) -> None:
        content = copy.deepcopy(renderer.SEQUENCE_CONTENT["timeline-milestones"])
        markup = renderer._timeline_milestones(content)
        timeline = _TagCollector(markup).with_class("sequence-timeline")

        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0].get("data-visual-surface-role"), "none")
        self.assertEqual(len(_TagCollector(markup).with_class("prod-subtitle")), 0)
        self.assertIn(".sequence-timeline .diagram-node-bg{border:0;background:transparent}", renderer.PRODUCTION_CSS)

    def test_left_title_open_field_cover_omits_vertical_metadata(self) -> None:
        content = copy.deepcopy(renderer.COVER_CONTENT["cover-left-title-open-field"])
        markup = renderer._cover_left_title_open_field(content)
        tags = _TagCollector(markup)

        self.assertIn('data-visual-balance="left-title-open-field"', markup)
        self.assertNotIn('data-visual-balance="content-bounds"', markup)
        self.assertEqual(len(tags.with_class("cover-left-title-stack")), 1)
        self.assertEqual(len(tags.with_class("cover-left-open-field-base")), 0)
        self.assertEqual(len(tags.with_class("cover-left-open-field-surface")), 0)
        self.assertEqual(len(tags.with_class("cover-left-open-field-spine")), 0)
        for class_name in ("cover-left-title", "cover-left-rule", "cover-left-subtitle", "cover-left-speaker"):
            self.assertEqual(len(tags.with_class(class_name)), 1)
        self.assertNotIn("cover-center-org", markup)
        self.assertNotIn("writing-mode", markup)
        self.assertGreaterEqual(_font_px(".cover-left-title"), renderer.GENERATED_TEXT_MIN_PX)
        self.assertGreaterEqual(_font_px(".cover-left-subtitle"), renderer.GENERATED_TEXT_MIN_PX)
        layout_css = _css_rule('#stage .slide[data-layout-id="cover-left-title-open-field"]')
        self.assertIn("background-image", layout_css)
        self.assertIn("var(--bg)", layout_css)
        self.assertIn("box-shadow", layout_css)

    def test_center_title_double_frame_cover_owns_two_margin_band_frames(self) -> None:
        content = copy.deepcopy(renderer.COVER_CONTENT["cover-center-title-double-frame"])
        markup = renderer._cover_center_title_double_frame(content)
        tags = _TagCollector(markup)

        self.assertIn('data-visual-balance="center-title-double-frame"', markup)
        self.assertEqual(len(tags.with_class("cover-frame-title-stack")), 1)
        for class_name in (
            "cover-frame-title",
            "cover-frame-rule",
            "cover-frame-subtitle",
            "cover-frame-speaker",
            "cover-frame-org",
        ):
            self.assertEqual(len(tags.with_class(class_name)), 1)
        self.assertGreaterEqual(_font_px(".cover-frame-title"), renderer.GENERATED_TEXT_MIN_PX)
        self.assertGreaterEqual(_font_px(".cover-frame-subtitle"), renderer.GENERATED_TEXT_MIN_PX)
        self.assertIn('#stage .slide[data-layout-id="cover-center-title-double-frame"]::before', renderer.PRODUCTION_CSS)
        self.assertIn('#stage .slide[data-layout-id="cover-center-title-double-frame"]::after', renderer.PRODUCTION_CSS)
        self.assertIn("inset:18px;border:2px solid", renderer.PRODUCTION_CSS)
        self.assertIn("inset:38px;border:1px solid", renderer.PRODUCTION_CSS)

    def test_toc_panel_grid_fails_closed_when_content_exceeds_capacity(self) -> None:
        content = {
            "title": "四個章節",
            "intro": "每個章節保留一個清楚入口",
            "footer": "READING MAP",
            "items": [
                (f"{index:02d}", f"章節 {index}", "章節說明")
                for index in range(1, 7)
            ],
        }
        layout = {"id": "toc-4-panel-grid", "family": "toc"}
        with self.assertRaisesRegex(ValueError, "4 chapter slots but received 6"):
            renderer.render_production_layout(layout, content)

        content["items"] = content["items"][:4]
        markup = renderer.render_production_layout(layout, content)
        self.assertIsNotNone(markup)
        self.assertEqual(len(_TagCollector(markup or "").with_class("toc-panel-grid-card")), 4)

    def test_recommendation_stack_fills_the_stack_for_actual_row_count(self) -> None:
        content = copy.deepcopy(renderer.CONTENT_CONTENT["recommendation-stack"])
        content["recommendations"] = content["recommendations"][:3]
        markup = renderer._recommendation_stack(content)
        tags = _TagCollector(markup)
        stack = tags.with_class("content-rec-stack")
        rows = tags.with_class("content-rec-row")

        self.assertEqual(len(stack), 1)
        self.assertEqual(len(rows), 3)
        stack_height = _style_box(stack[0])["height"]
        row_heights = [_style_box(row)["height"] for row in rows]
        row_tops = [_style_box(row)["top"] for row in rows]
        self.assertAlmostEqual(stack_height, sum(row_heights), places=2)
        self.assertAlmostEqual(row_heights[0], 448 / 3, places=2)
        self.assertEqual(row_tops, [0.0, round(448 / 3, 3), round(2 * 448 / 3, 3)])
        self.assertEqual([row.get("data-row-count") for row in rows], ["3"] * 3)

        four_markup = renderer._recommendation_stack(renderer.CONTENT_CONTENT["recommendation-stack"])
        four_rows = _TagCollector(four_markup).with_class("content-rec-row")
        self.assertEqual(len(four_rows), 4)
        self.assertTrue(all(_style_box(row)["height"] == 112.0 for row in four_rows))

        invalid = copy.deepcopy(content)
        invalid["recommendations"] = invalid["recommendations"][:1]
        with self.assertRaisesRegex(ValueError, "two to five recommendation rows"):
            renderer._recommendation_stack(invalid)


if __name__ == "__main__":
    unittest.main()
