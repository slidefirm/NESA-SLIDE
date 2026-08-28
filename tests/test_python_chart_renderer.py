from __future__ import annotations

import re
import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import html_production_renderer as renderer
from render_theme_demo_html import render_chart as render_theme_demo_chart
from python_chart_renderer import (
    render_annotation_line_chart_svg,
    render_dashboard_combo_chart_svg,
    render_heat_map_chart_svg,
    render_highlight_line_chart_svg,
    render_line_chart_svg,
    render_multi_line_chart_svg,
    render_radar_chart_svg,
)


LABELS = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
SERIES = [
    ("完整試香停留", [41, 49, 55, 64, 73, 82, 91]),
    ("能說出香氣主張", [35, 42, 52, 59, 68, 76, 85]),
    ("十四日回訪率", [29, 37, 45, 56, 63, 71, 80]),
]


class PythonChartRendererTests(unittest.TestCase):
    def test_matplotlib_svg_is_deterministic_theme_aware_and_vector(self) -> None:
        first = render_multi_line_chart_svg(LABELS, SERIES)
        second = render_multi_line_chart_svg(LABELS, SERIES)

        self.assertEqual(first, second)
        self.assertIn('data-python-chart-engine="matplotlib"', first)
        self.assertIn('data-python-generated="true"', first)
        self.assertIn('<style data-css-owner="renderer-base"', first)
        self.assertRegex(first, r'data-chart-spec-sha256="[0-9a-f]{64}"')
        self.assertIn('viewBox="0 0 1728 580"', first)
        self.assertIn('id="python-series-1"', first)
        self.assertIn('id="python-series-2"', first)
        self.assertIn('id="python-series-3"', first)
        self.assertIn("var(--accent)", first)
        self.assertIn("var(--support-accent)", first)
        self.assertIn("var(--surface-muted)", first)
        self.assertIn("完整試香停留", first)
        self.assertIn("指標值（0–100）", first)
        self.assertNotIn("<metadata", first)
        self.assertNotIn("<image", first)
        self.assertNotIn("data:image", first)
        self.assertNotIn("<canvas", first)
        self.assertNotRegex(
            first,
            r'<(?:text|tspan)\b[^>]*\btransform="[^"]*rotate\(\s*[+-]?(?:90|270)(?:deg)?(?=[\s,)])',
        )

        font_sizes = [float(value) for value in re.findall(r"font-size:\s*([0-9.]+)px", first)]
        self.assertTrue(font_sizes)
        self.assertGreaterEqual(min(font_sizes), renderer.GENERATED_TEXT_MIN_PX)

    def test_invalid_series_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "two or three series"):
            render_multi_line_chart_svg(LABELS, SERIES[:1])
        with self.assertRaisesRegex(ValueError, "values for"):
            render_multi_line_chart_svg(LABELS, [("錯誤資料", [1, 2, 3]), SERIES[1]])
        with self.assertRaisesRegex(ValueError, "0-100 domain"):
            render_multi_line_chart_svg(LABELS, [("超出範圍", [0, 20, 40, 60, 80, 100, 120]), SERIES[1]])

    def test_production_multi_line_layout_uses_python_svg(self) -> None:
        markup = renderer._multi_line_chart({"title": "測試", "labels": LABELS, "series": SERIES})
        self.assertIn('data-chart-renderer="python-matplotlib-svg"', markup)
        self.assertIn('data-python-chart-engine="matplotlib"', markup)
        self.assertIn('data-edit-layer="visual"', markup)
        self.assertNotIn("dataviz-ylabels", markup)
        self.assertNotIn("dataviz-xlabels", markup)
        self.assertNotIn("dataviz-legend", markup)

    def test_each_python_chart_family_is_deterministic_and_tagged(self) -> None:
        cases = {
            "dashboard-combo": lambda: render_dashboard_combo_chart_svg(
                LABELS, SERIES[0][1]
            ),
            "highlight-line": lambda: render_highlight_line_chart_svg(
                LABELS, SERIES[0][1], focus_indices=(1, 3, 6)
            ),
            "annotation-line": lambda: render_annotation_line_chart_svg(
                LABELS, SERIES[0][1]
            ),
            "heat-map": lambda: render_heat_map_chart_svg(
                ["證據", "驗收", "回寫"],
                [[5, 4, 3], [4, 3, 2], [3, 2, 1]],
            ),
            "radar": lambda: render_radar_chart_svg(
                ["證據", "假設", "驗收", "回寫"],
                [("導入前", [2, 3, 2, 1]), ("導入後", [5, 4, 5, 3])],
            ),
            "theme-demo-line": lambda: render_line_chart_svg(
                LABELS,
                SERIES[:2],
                family="theme-demo-line",
                width=1500,
                height=600,
                domain=(0, 100),
            ),
        }
        for family, render in cases.items():
            with self.subTest(family=family):
                first = render()
                second = render()
                self.assertEqual(first, second)
                self.assertIn(f'data-python-chart-family="{family}"', first)
                self.assertIn('data-python-chart-engine="matplotlib"', first)
                self.assertRegex(first, r'data-chart-spec-sha256="[0-9a-f]{64}"')
                self.assertIn('<style data-css-owner="renderer-base"', first)
                self.assertNotIn("<metadata", first)
                self.assertNotIn("<image", first)
                self.assertNotIn("<canvas", first)
                self.assertNotRegex(
                    first,
                    r'<(?:text|tspan)\b[^>]*\btransform="[^"]*rotate\(\s*[+-]?(?:90|270)(?:deg)?(?=[\s,)])',
                )

    def test_all_production_data_chart_layouts_use_python_projection(self) -> None:
        cases = {
            "dashboard-combo": renderer._dashboard_overview(
                renderer.METRICS_CONTENT["dashboard-overview"]
            ),
            "highlight-line": renderer._highlight_callout(
                renderer.STATEMENT_CONTENT["highlight-callout"]
            ),
            "annotation-line": renderer._data_annotation(
                renderer.DATAVIZ_CONTENT["data-annotation"]
            ),
            "heat-map": renderer._heat_map(renderer.DATAVIZ_CONTENT["heat-map"]),
            "multi-line": renderer._multi_line_chart(
                renderer.DATAVIZ_CONTENT["multi-line-chart"]
            ),
            "radar": renderer._radar_chart(renderer.DATAVIZ_CONTENT["radar-chart"]),
        }
        for family, markup in cases.items():
            with self.subTest(family=family):
                self.assertIn('data-chart-renderer="python-matplotlib-svg"', markup)
                self.assertIn(f'data-python-chart-family="{family}"', markup)
                self.assertIn('data-python-chart-engine="matplotlib"', markup)

        legacy_markup = (
            '<svg class="metric-chart"',
            '<svg class="statement-chart"',
            'class="dataviz-grid"',
            'class="dataviz-points"',
            'class="radar-web"',
            'class="radar-series',
            'class="heat-cell',
        )
        source = (SCRIPTS_DIR / "html_production_renderer.py").read_text(encoding="utf-8")
        demo_source = (SCRIPTS_DIR / "render_theme_demo_html.py").read_text(encoding="utf-8")
        for token in legacy_markup:
            self.assertNotIn(token, source)
        self.assertNotIn("<polyline", demo_source)
        self.assertNotIn(".chart-grid", demo_source)
        self.assertNotIn(".series-a", demo_source)
        self.assertNotIn(".points.series", demo_source)
        self.assertIn("render_line_chart_svg", demo_source)

        for selector in (
            ".metric-chart line",
            ".statement-grid",
            ".dataviz-ylabels",
            ".dataviz-legend",
            ".heat-cell",
            ".radar-web",
            ".radar-series",
        ):
            self.assertNotIn(selector, renderer.PRODUCTION_CSS)

    def test_invalid_non_line_chart_contracts_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "row width"):
            render_heat_map_chart_svg(["A", "B"], [[1]])
        with self.assertRaisesRegex(ValueError, "1-5 domain"):
            render_heat_map_chart_svg(["A", "B"], [[1, 6]])
        with self.assertRaisesRegex(ValueError, "0-5 domain"):
            render_radar_chart_svg(
                ["A", "B", "C"], [("invalid", [1, 2, 6])]
            )

    def test_theme_demo_chart_uses_python_projection(self) -> None:
        markup = render_theme_demo_chart(
            {
                "title": "趨勢",
                "labels": LABELS,
                "series": [
                    {"name": name, "values": values}
                    for name, values in SERIES[:2]
                ],
                "note": "資料來源",
            },
            {},
        )
        self.assertIn('data-chart-renderer="python-matplotlib-svg"', markup)
        self.assertIn('data-python-chart-family="theme-demo-line"', markup)
        self.assertNotIn("<polyline", markup)


if __name__ == "__main__":
    unittest.main()
