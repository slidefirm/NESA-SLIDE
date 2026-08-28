#!/usr/bin/env python3
"""Deterministic Python/Matplotlib chart rendering for editable HTML decks.

The output is inline SVG rather than PNG.  The SVG remains one selectable
visual layer inside the HTML semantic module while text and the page title
stay native HTML objects.
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Sequence


CHART_WIDTH = 1728
CHART_HEIGHT = 580
CHART_CONTRACT: dict[str, Any] = {
    "analytical_question": "三項指標在連續試作輪次中的走勢如何？",
    "takeaway": "三項指標同步上升，完整試香停留持續領先。",
    "family": "trend",
    "variant": "multi-series-line-with-markers",
    "renderer": "python-matplotlib-svg",
    "domain": [0, 100],
    "palette_policy": "two-roots-plus-neutral-with-marker-and-line-style",
}

CHART_FAMILY_CONTRACTS: dict[str, dict[str, Any]] = {
    "dashboard-combo": {
        "family": "comparison",
        "variant": "compact-bar-line",
        "renderer": "python-matplotlib-svg",
        "domain": [0, 100],
    },
    "highlight-line": {
        "family": "trend",
        "variant": "single-line-focus-markers",
        "renderer": "python-matplotlib-svg",
    },
    "annotation-line": {
        "family": "trend",
        "variant": "single-line-external-annotations",
        "renderer": "python-matplotlib-svg",
        "domain": [0, 100],
    },
    "heat-map": {
        "family": "distribution",
        "variant": "discrete-five-level-heat-map",
        "renderer": "python-matplotlib-svg",
        "domain": [1, 5],
    },
    "radar": {
        "family": "profile",
        "variant": "multi-series-radar",
        "renderer": "python-matplotlib-svg",
        "domain": [0, 5],
    },
    "theme-demo-line": {
        "family": "trend",
        "variant": "theme-demo-two-series-line",
        "renderer": "python-matplotlib-svg",
        "domain": [0, 100],
    },
}

_FONT_CANDIDATES = (
    Path(r"C:\Windows\Fonts\NotoSansTC-VF.ttf"),
    Path(r"C:\Windows\Fonts\SourceHanSansTW-Regular.otf"),
    Path(r"C:\Windows\Fonts\msjh.ttc"),
)

# Matplotlib needs concrete colors while plotting.  They are replaced with
# inherited Theme tokens before the SVG enters the HTML artifact.
_COLOR_TOKENS = {
    "#a10f0f": "var(--accent)",
    "#0fa10f": "var(--support-accent)",
    "#0f0fa1": "var(--surface-muted)",
    "#101112": "var(--surface-text)",
    "#202122": "color-mix(in srgb,var(--surface-text) 18%,transparent)",
    "#303132": "color-mix(in srgb,var(--surface-text) 54%,transparent)",
    "#f0f0f0": "var(--surface)",
    "#fafafa": "var(--accent-text)",
    "#e1b8b8": "color-mix(in srgb,var(--accent) 8%,var(--surface))",
    "#cc8e8e": "color-mix(in srgb,var(--accent) 18%,var(--surface))",
    "#b16464": "color-mix(in srgb,var(--accent) 32%,var(--surface))",
    "#963a3a": "color-mix(in srgb,var(--accent) 52%,var(--surface))",
    "#7b1010": "var(--accent)",
}


_RIGHT_ANGLE_SVG_TEXT_ROTATION = re.compile(
    r"<(?:text|tspan)\b[^>]*\btransform\s*=\s*[\"'][^\"']*?"
    r"rotate\(\s*[+-]?(?:90|270)(?:deg)?(?=[\s,)])",
    re.I,
)


def _load_matplotlib() -> tuple[Any, Any, Any]:
    config_dir = Path(tempfile.gettempdir()) / "nesa-slide-matplotlib"
    config_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(config_dir))
    try:
        import matplotlib
    except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
        raise RuntimeError(
            "Python chart rendering requires Matplotlib; run "
            "`python -m pip install -r requirements.txt` before rendering."
        ) from exc

    matplotlib.use("svg", force=True)
    from matplotlib import font_manager
    from matplotlib import pyplot as plt

    return matplotlib, font_manager, plt


def _font_properties(font_manager: Any, *, size: float) -> Any:
    for path in _FONT_CANDIDATES:
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            return font_manager.FontProperties(fname=str(path), size=size)
    return font_manager.FontProperties(family="sans-serif", size=size)


def _normalise_chart_data(
    labels: Sequence[str],
    series: Sequence[tuple[str, Sequence[float]]],
) -> tuple[list[str], list[tuple[str, list[float]]]]:
    clean_labels = [str(label).strip() for label in labels]
    if len(clean_labels) < 3:
        raise ValueError("multi-line chart requires at least three ordered labels")
    if not 2 <= len(series) <= 3:
        raise ValueError("multi-line chart requires two or three series")

    clean_series: list[tuple[str, list[float]]] = []
    for name, raw_values in series:
        values = [float(value) for value in raw_values]
        if len(values) != len(clean_labels):
            raise ValueError(
                f"series {name!r} has {len(values)} values for {len(clean_labels)} labels"
            )
        if any(not math.isfinite(value) for value in values):
            raise ValueError(f"series {name!r} contains a non-finite value")
        if any(value < 0 or value > 100 for value in values):
            raise ValueError(f"series {name!r} must stay within the declared 0-100 domain")
        clean_series.append((str(name).strip(), values))
    return clean_labels, clean_series


def _strip_and_tokenise_svg(
    raw_svg: str,
    *,
    family: str,
    spec_sha256: str,
    matplotlib_version: str,
    aria_label: str,
) -> str:
    svg = raw_svg[raw_svg.index("<svg") :]
    svg = re.sub(r"<metadata>.*?</metadata>", "", svg, count=1, flags=re.S)
    svg = re.sub(
        r"<style(?=\s|>)",
        '<style data-css-owner="renderer-base"',
        svg,
    )
    svg = re.sub(r"\swidth=\"[^\"]+\"", "", svg, count=1)
    svg = re.sub(r"\sheight=\"[^\"]+\"", "", svg, count=1)
    attrs = (
        'class="python-matplotlib-chart" '
        'data-edit-layer="visual" data-edit-position="absolute" '
        'data-python-generated="true" data-python-chart-engine="matplotlib" '
        f'data-python-chart-family="{html.escape(family, quote=True)}" '
        f'data-python-chart-version="{html.escape(matplotlib_version, quote=True)}" '
        f'data-chart-spec-sha256="{spec_sha256}" role="img" '
        f'aria-label="{html.escape(aria_label, quote=True)}" '
    )
    svg = re.sub(r"<svg\s+", "<svg " + attrs, svg, count=1)
    for source, target in _COLOR_TOKENS.items():
        svg = re.sub(re.escape(source), target, svg, flags=re.I)
    return svg.strip()


def _spec_sha256(spec: dict[str, Any]) -> str:
    spec_json = json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(spec_json.encode("utf-8")).hexdigest()


def _figure_to_svg(
    fig: Any,
    *,
    plt: Any,
    matplotlib_version: str,
    family: str,
    spec: dict[str, Any],
    aria_label: str,
) -> str:
    output = io.StringIO()
    fig.savefig(
        output,
        format="svg",
        transparent=True,
        metadata={"Date": None, "Creator": "Python Matplotlib chart renderer"},
    )
    plt.close(fig)
    raw_svg = output.getvalue()
    if _RIGHT_ANGLE_SVG_TEXT_ROTATION.search(raw_svg):
        raise RuntimeError(
            "Python chart renderer emitted a right-angle SVG text rotation; "
            "visible chart text must remain horizontal."
        )
    return _strip_and_tokenise_svg(
        raw_svg,
        family=family,
        spec_sha256=_spec_sha256(spec),
        matplotlib_version=matplotlib_version,
        aria_label=aria_label,
    )


def _normalise_series_data(
    labels: Sequence[str],
    series: Sequence[tuple[str, Sequence[float]]],
    *,
    minimum_labels: int,
    minimum_series: int,
    maximum_series: int,
    domain: tuple[float, float] | None,
) -> tuple[list[str], list[tuple[str, list[float]]]]:
    clean_labels = [str(label).strip() for label in labels]
    if len(clean_labels) < minimum_labels:
        raise ValueError(f"chart requires at least {minimum_labels} ordered labels")
    if not minimum_series <= len(series) <= maximum_series:
        raise ValueError(
            f"chart requires {minimum_series} to {maximum_series} series"
        )

    clean_series: list[tuple[str, list[float]]] = []
    for name, raw_values in series:
        values = [float(value) for value in raw_values]
        if len(values) != len(clean_labels):
            raise ValueError(
                f"series {name!r} has {len(values)} values for {len(clean_labels)} labels"
            )
        if any(not math.isfinite(value) for value in values):
            raise ValueError(f"series {name!r} contains a non-finite value")
        if domain is not None:
            low, high = domain
            if any(value < low or value > high for value in values):
                raise ValueError(
                    f"series {name!r} must stay within the declared {low:g}-{high:g} domain"
                )
        clean_series.append((str(name).strip(), values))
    return clean_labels, clean_series


def render_multi_line_chart_svg(
    labels: Sequence[str],
    series: Sequence[tuple[str, Sequence[float]]],
    *,
    width: int = CHART_WIDTH,
    height: int = CHART_HEIGHT,
) -> str:
    """Render a deterministic, Theme-aware multi-series line chart as SVG."""

    clean_labels, clean_series = _normalise_chart_data(labels, series)
    spec = {
        "contract": CHART_CONTRACT,
        "labels": clean_labels,
        "series": clean_series,
        "size": [width, height],
    }

    matplotlib, font_manager, plt = _load_matplotlib()
    font_36 = _font_properties(font_manager, size=36)
    series_colors = ["#a10f0f", "#0fa10f", "#0f0fa1"]
    line_styles: list[Any] = ["-", "-", (0, (7, 5))]
    markers = ["o", "s", "D"]
    marker_faces = [series_colors[0], "none", "none"]

    rc = {
        "svg.fonttype": "none",
        "svg.hashsalt": "python-matplotlib-chart-v1",
        "axes.unicode_minus": False,
    }
    with matplotlib.rc_context(rc):
        fig, ax = plt.subplots(figsize=(width / 72, height / 72), dpi=72)
        fig.patch.set_alpha(0)
        ax.set_facecolor("none")
        fig.subplots_adjust(left=0.09, right=0.975, bottom=0.20, top=0.77)

        x_values = list(range(len(clean_labels)))
        for index, (name, values) in enumerate(clean_series):
            line, = ax.plot(
                x_values,
                values,
                label=name,
                color=series_colors[index],
                linewidth=7,
                linestyle=line_styles[index],
                marker=markers[index],
                markersize=13,
                markerfacecolor=marker_faces[index],
                markeredgecolor=series_colors[index],
                markeredgewidth=3,
                solid_capstyle="round",
                solid_joinstyle="round",
                zorder=4 - index,
            )
            line.set_gid(f"python-series-{index + 1}")

        ax.set_xlim(-0.15, len(clean_labels) - 0.70)
        ax.set_ylim(0, 100)
        ax.set_xticks(x_values, clean_labels)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.tick_params(axis="both", which="both", length=0, pad=16, colors="#101112")
        for tick in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
            tick.set_fontproperties(font_36)
            tick.set_color("#101112")

        ax.set_xlabel("試作輪次", fontproperties=font_36, labelpad=18, color="#101112")
        # A vertical y-axis label produces SVG rotate(-90 ...) text.  That is
        # neither allowed by the visible-text contract nor portable to the
        # native PPTX browser exporter, so keep the metric label horizontal in
        # the chart's upper-left reading zone instead.
        ax.text(
            0,
            1.02,
            "指標值（0–100）",
            transform=ax.transAxes,
            fontproperties=font_36,
            color="#101112",
            ha="left",
            va="bottom",
        )
        ax.yaxis.grid(True, color="#202122", linewidth=2)
        ax.xaxis.grid(False)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#303132")
            ax.spines[side].set_linewidth(2)

        legend = ax.legend(
            loc="lower center",
            bbox_to_anchor=(0.5, 1.06),
            ncol=len(clean_series),
            frameon=False,
            prop=font_36,
            handlelength=2.5,
            columnspacing=2.0,
            handletextpad=0.7,
            borderaxespad=0,
        )
        for text in legend.get_texts():
            text.set_color("#101112")

        return _figure_to_svg(
            fig,
            plt=plt,
            matplotlib_version=matplotlib.__version__,
            family="multi-line",
            spec=spec,
            aria_label="多序列趨勢折線圖",
        )


def render_line_chart_svg(
    labels: Sequence[str],
    series: Sequence[tuple[str, Sequence[float]]],
    *,
    family: str,
    width: int,
    height: int,
    domain: tuple[float, float] | None = None,
    focus_indices: Sequence[int] = (),
    show_tick_labels: bool = False,
    show_legend: bool = False,
    aria_label: str = "趨勢折線圖",
) -> str:
    """Render a deterministic line chart for a production HTML chart family."""

    clean_labels, clean_series = _normalise_series_data(
        labels,
        series,
        minimum_labels=3,
        minimum_series=1,
        maximum_series=3,
        domain=domain,
    )
    all_values = [value for _, values in clean_series for value in values]
    if domain is None:
        low = min(0.0, min(all_values))
        high = max(0.0, max(all_values))
    else:
        low, high = domain
    if math.isclose(low, high):
        high = low + 1.0

    valid_focus = sorted({int(index) for index in focus_indices if 0 <= int(index) < len(clean_labels)})
    spec = {
        "contract": CHART_FAMILY_CONTRACTS.get(
            family,
            {"family": "trend", "variant": family, "renderer": "python-matplotlib-svg"},
        ),
        "labels": clean_labels,
        "series": clean_series,
        "domain": [low, high],
        "focus_indices": valid_focus,
        "size": [width, height],
        "show_tick_labels": show_tick_labels,
        "show_legend": show_legend,
    }

    matplotlib, font_manager, plt = _load_matplotlib()
    font_36 = _font_properties(font_manager, size=36)
    colors = ["#a10f0f", "#0fa10f", "#0f0fa1"]
    line_styles: list[Any] = ["-", "-", (0, (7, 5))]
    markers = ["o", "s", "D"]
    rc = {
        "svg.fonttype": "none",
        "svg.hashsalt": "python-matplotlib-chart-v2",
        "axes.unicode_minus": False,
    }
    with matplotlib.rc_context(rc):
        fig, ax = plt.subplots(figsize=(width / 72, height / 72), dpi=72)
        fig.patch.set_alpha(0)
        ax.set_facecolor("none")
        fig.subplots_adjust(
            left=0.075 if show_tick_labels else 0.035,
            right=0.985,
            bottom=0.20 if show_tick_labels else 0.055,
            top=0.78 if show_legend else 0.96,
        )

        x_values = list(range(len(clean_labels)))
        for index, (name, values) in enumerate(clean_series):
            line, = ax.plot(
                x_values,
                values,
                label=name,
                color=colors[index],
                linewidth=7 if index == 0 else 6,
                linestyle=line_styles[index],
                marker=markers[index],
                markersize=11,
                markerfacecolor="#f0f0f0" if index else colors[index],
                markeredgecolor=colors[index],
                markeredgewidth=3,
                solid_capstyle="round",
                solid_joinstyle="round",
                zorder=4 - index,
            )
            line.set_gid(f"python-series-{index + 1}")

        ax.set_xlim(-0.15, len(clean_labels) - 0.70)
        ax.set_ylim(low, high)
        tick_values = [low + (high - low) * index / 4 for index in range(5)]
        ax.set_yticks(tick_values)
        ax.yaxis.grid(True, color="#202122", linewidth=2)
        ax.xaxis.grid(False)
        ax.set_axisbelow(True)
        ax.set_xticks(x_values)
        if show_tick_labels:
            ax.set_xticklabels(clean_labels)
            ax.set_yticklabels([f"{value:g}" for value in tick_values])
            for tick in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
                tick.set_fontproperties(font_36)
                tick.set_color("#101112")
            ax.tick_params(axis="both", which="both", length=0, pad=14)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color("#303132")
                ax.spines[side].set_linewidth(2)
        else:
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            ax.tick_params(axis="both", which="both", length=0)
            for spine in ax.spines.values():
                spine.set_visible(False)

        for marker_number, point_index in enumerate(valid_focus, 1):
            value = clean_series[0][1][point_index]
            focus = ax.scatter(
                [point_index],
                [value],
                s=760,
                facecolor="#f0f0f0",
                edgecolor="#0fa10f",
                linewidth=5,
                zorder=8,
            )
            focus.set_gid(f"python-focus-{marker_number}")
            text = ax.text(
                point_index,
                value,
                str(marker_number),
                ha="center",
                va="center",
                color="#101112",
                fontproperties=font_36,
                zorder=9,
            )
            text.set_gid(f"python-focus-label-{marker_number}")

        if show_legend:
            legend = ax.legend(
                loc="lower center",
                bbox_to_anchor=(0.5, 1.06),
                ncol=len(clean_series),
                frameon=False,
                prop=font_36,
                handlelength=2.5,
                columnspacing=2.0,
                handletextpad=0.7,
                borderaxespad=0,
            )
            for text in legend.get_texts():
                text.set_color("#101112")

        return _figure_to_svg(
            fig,
            plt=plt,
            matplotlib_version=matplotlib.__version__,
            family=family,
            spec=spec,
            aria_label=aria_label,
        )


def render_dashboard_combo_chart_svg(
    labels: Sequence[str],
    values: Sequence[float],
    *,
    width: int = 1000,
    height: int = 240,
) -> str:
    clean_labels, clean_series = _normalise_series_data(
        labels,
        [("value", values)],
        minimum_labels=3,
        minimum_series=1,
        maximum_series=1,
        domain=(0, 100),
    )
    clean_values = clean_series[0][1]
    spec = {
        "contract": CHART_FAMILY_CONTRACTS["dashboard-combo"],
        "labels": clean_labels,
        "values": clean_values,
        "size": [width, height],
    }
    matplotlib, _, plt = _load_matplotlib()
    rc = {
        "svg.fonttype": "none",
        "svg.hashsalt": "python-matplotlib-chart-v2",
        "axes.unicode_minus": False,
    }
    with matplotlib.rc_context(rc):
        fig, ax = plt.subplots(figsize=(width / 72, height / 72), dpi=72)
        fig.patch.set_alpha(0)
        ax.set_facecolor("none")
        fig.subplots_adjust(left=0.01, right=0.99, bottom=0.04, top=0.96)
        x_values = list(range(len(clean_labels)))
        bars = ax.bar(
            x_values,
            clean_values,
            width=0.46,
            color="#a10f0f",
            alpha=0.24,
            edgecolor="#a10f0f",
            linewidth=2,
            zorder=2,
        )
        for index, patch in enumerate(bars, 1):
            patch.set_gid(f"python-bar-{index}")
        line, = ax.plot(
            x_values,
            clean_values,
            color="#0fa10f",
            linewidth=6,
            solid_capstyle="round",
            solid_joinstyle="round",
            zorder=4,
        )
        line.set_gid("python-series-1")
        baseline = ax.axhline(0, color="#202122", linewidth=2, zorder=1)
        baseline.set_gid("python-baseline")
        ax.set_xlim(-0.55, len(clean_labels) - 0.45)
        ax.set_ylim(0, 100)
        ax.axis("off")
        return _figure_to_svg(
            fig,
            plt=plt,
            matplotlib_version=matplotlib.__version__,
            family="dashboard-combo",
            spec=spec,
            aria_label="指標趨勢長條與折線組合圖",
        )


def render_highlight_line_chart_svg(
    labels: Sequence[str],
    values: Sequence[float],
    *,
    focus_indices: Sequence[int],
    width: int = 1040,
    height: int = 410,
) -> str:
    numeric = [float(value) for value in values]
    high = max(max(numeric, default=1.0), 1.0)
    return render_line_chart_svg(
        labels,
        [("value", numeric)],
        family="highlight-line",
        width=width,
        height=height,
        domain=(0, high),
        focus_indices=focus_indices,
        aria_label="關鍵轉折點趨勢折線圖",
    )


def render_annotation_line_chart_svg(
    labels: Sequence[str],
    values: Sequence[float],
    *,
    width: int = 1728,
    height: int = 580,
) -> str:
    return render_line_chart_svg(
        labels,
        [("value", values)],
        family="annotation-line",
        width=width,
        height=height,
        domain=(0, 100),
        aria_label="制度改動與指標趨勢折線圖",
    )


def render_heat_map_chart_svg(
    columns: Sequence[str],
    values: Sequence[Sequence[float]],
    *,
    width: int = 1416,
    height: int = 600,
) -> str:
    clean_columns = [str(column).strip() for column in columns]
    clean_values = [[float(value) for value in row] for row in values]
    if len(clean_columns) < 2:
        raise ValueError("heat map requires at least two columns")
    if not clean_values:
        raise ValueError("heat map requires at least one row")
    if any(len(row) != len(clean_columns) for row in clean_values):
        raise ValueError("heat map row width must match the column count")
    if any(
        not math.isfinite(value) or value < 1 or value > 5
        for row in clean_values
        for value in row
    ):
        raise ValueError("heat map values must stay within the declared 1-5 domain")

    spec = {
        "contract": CHART_FAMILY_CONTRACTS["heat-map"],
        "columns": clean_columns,
        "values": clean_values,
        "size": [width, height],
    }
    matplotlib, font_manager, plt = _load_matplotlib()
    font_36 = _font_properties(font_manager, size=36)
    rc = {
        "svg.fonttype": "none",
        "svg.hashsalt": "python-matplotlib-chart-v2",
        "axes.unicode_minus": False,
    }
    with matplotlib.rc_context(rc):
        fig, ax = plt.subplots(figsize=(width / 72, height / 72), dpi=72)
        fig.patch.set_alpha(0)
        ax.set_facecolor("none")
        fig.subplots_adjust(left=0, right=1, bottom=0, top=0.82)
        heat_colors = ["#e1b8b8", "#cc8e8e", "#b16464", "#963a3a", "#7b1010"]
        for row_index, row in enumerate(clean_values):
            for column_index, value in enumerate(row):
                patch = matplotlib.patches.Rectangle(
                    (column_index - 0.5, row_index - 0.5),
                    1,
                    1,
                    facecolor=heat_colors[int(round(value)) - 1],
                    edgecolor="#303132",
                    linewidth=1,
                )
                patch.set_gid(f"python-heat-cell-bg-{row_index + 1}-{column_index + 1}")
                ax.add_patch(patch)
        ax.set_xlim(-0.5, len(clean_columns) - 0.5)
        ax.set_ylim(len(clean_values) - 0.5, -0.5)
        ax.set_aspect("auto")
        ax.set_xticks(list(range(len(clean_columns))), clean_columns)
        ax.xaxis.tick_top()
        ax.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False, length=0, pad=18)
        for tick in ax.get_xticklabels():
            tick.set_fontproperties(font_36)
            tick.set_color("#101112")
        ax.set_yticks([])
        for row_index, row in enumerate(clean_values):
            for column_index, value in enumerate(row):
                text = ax.text(
                    column_index,
                    row_index,
                    f"{value:g}",
                    ha="center",
                    va="center",
                    color="#fafafa" if value >= 4 else "#101112",
                    fontproperties=font_36,
                    fontweight=900,
                )
                text.set_gid(f"python-heat-cell-{row_index + 1}-{column_index + 1}")
        for spine in ax.spines.values():
            spine.set_visible(False)
        return _figure_to_svg(
            fig,
            plt=plt,
            matplotlib_version=matplotlib.__version__,
            family="heat-map",
            spec=spec,
            aria_label="五級成熟度熱圖",
        )


def render_radar_chart_svg(
    axes: Sequence[str],
    series: Sequence[tuple[str, Sequence[float]]],
    *,
    width: int = 700,
    height: int = 660,
) -> str:
    clean_axes, clean_series = _normalise_series_data(
        axes,
        series,
        minimum_labels=3,
        minimum_series=1,
        maximum_series=3,
        domain=(0, 5),
    )
    spec = {
        "contract": CHART_FAMILY_CONTRACTS["radar"],
        "axes": clean_axes,
        "series": clean_series,
        "size": [width, height],
    }
    matplotlib, _, plt = _load_matplotlib()
    colors = ["#0fa10f", "#a10f0f", "#0f0fa1"]
    rc = {
        "svg.fonttype": "none",
        "svg.hashsalt": "python-matplotlib-chart-v2",
        "axes.unicode_minus": False,
    }
    with matplotlib.rc_context(rc):
        fig = plt.figure(figsize=(width / 72, height / 72), dpi=72)
        fig.patch.set_alpha(0)
        ax = fig.add_subplot(111, projection="polar")
        ax.set_facecolor("none")
        fig.subplots_adjust(left=0.04, right=0.96, bottom=0.04, top=0.96)
        count = len(clean_axes)
        theta = [index * 2 * math.pi / count for index in range(count)]
        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_ylim(0, 5)
        ax.set_xticks(theta)
        ax.set_xticklabels([])
        ax.set_yticks([1, 2, 3, 4, 5])
        ax.set_yticklabels([])
        ax.grid(color="#202122", linewidth=2)
        ax.spines["polar"].set_color("#303132")
        ax.spines["polar"].set_linewidth(2)
        closed_theta = theta + [theta[0]]
        for index, (name, values) in enumerate(clean_series):
            closed_values = values + [values[0]]
            line, = ax.plot(
                closed_theta,
                closed_values,
                color=colors[index],
                linewidth=6,
                solid_joinstyle="round",
                label=name,
                zorder=4 - index,
            )
            line.set_gid(f"python-series-{index + 1}")
            fill = ax.fill(
                closed_theta,
                closed_values,
                color=colors[index],
                alpha=0.16 if index == 0 else 0.20,
                zorder=2 - index,
            )[0]
            fill.set_gid(f"python-series-fill-{index + 1}")
        return _figure_to_svg(
            fig,
            plt=plt,
            matplotlib_version=matplotlib.__version__,
            family="radar",
            spec=spec,
            aria_label="多序列能力雷達圖",
        )
