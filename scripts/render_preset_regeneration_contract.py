#!/usr/bin/env python3
"""Render regeneration decks with the current Preset semantic contract."""

from __future__ import annotations

import sys

import render_randomized_html_demo as renderer


def _scope_non_center_cover_overrides() -> None:
    replacements = {
        "moonlit-herbarium-atlas": [
            (
                'html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-area',
                'html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cover-center-title-edge-decor"]:not([data-composition-variant="centered-signal-hero"]) .cover-center-area',
            ),
        ],
        "after-dark-veil": [
            (
                'html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-area',
                'html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"]:not([data-composition-variant="centered-signal-hero"]) .cover-center-area',
            ),
            (
                'html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"] :is(.cover-center-title,.cover-center-subtitle,.cover-center-speaker,.cover-center-org)',
                'html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"]:not([data-composition-variant="centered-signal-hero"]) :is(.cover-center-title,.cover-center-subtitle,.cover-center-speaker,.cover-center-org)',
            ),
            (
                'html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-title',
                'html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"]:not([data-composition-variant="centered-signal-hero"]) .cover-center-title',
            ),
            (
                'html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-subtitle',
                'html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"]:not([data-composition-variant="centered-signal-hero"]) .cover-center-subtitle',
            ),
            (
                'html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"] :is(.cover-center-speaker,.cover-center-org)',
                'html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"]:not([data-composition-variant="centered-signal-hero"]) :is(.cover-center-speaker,.cover-center-org)',
            ),
            (
                'html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-org',
                'html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"]:not([data-composition-variant="centered-signal-hero"]) .cover-center-org',
            ),
            (
                'html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-rule',
                'html[data-style-case="after-dark-veil"] [data-layout-id="cover-center-title-edge-decor"]:not([data-composition-variant="centered-signal-hero"]) .cover-center-rule',
            ),
        ],
    }
    for preset_id, pairs in replacements.items():
        css = renderer.PRESET_THEME_PROFILES[preset_id]["css"]
        for old, new in pairs:
            if old not in css:
                raise ValueError(f"Expected cover adapter selector missing: {preset_id}")
            css = css.replace(old, new, 1)
        renderer.PRESET_THEME_PROFILES[preset_id]["css"] = css


if __name__ == "__main__":
    _scope_non_center_cover_overrides()
    raise SystemExit(renderer.main())
