#!/usr/bin/env python3
"""Render the 2026-08-05 Preset regeneration batch with QA-safe adapters."""

from __future__ import annotations

import sys

import render_randomized_html_demo as renderer


PRESET_IDS = (
    "sepia-retail-case",
    "dark-ai-city",
    "dark-city-network-report",
    "moonlit-herbarium-atlas",
    "clinical-evidence-atlas",
    "signal-route-atlas",
    "scent-veil-launch",
    "ai-operations-signal",
    "folio-signal-ledger",
    "after-dark-veil",
)


def _replace_required(css: str, preset_id: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        if old not in css:
            raise ValueError(f"Expected Preset adapter selector missing: {preset_id}")
        css = css.replace(old, new, 1)
    return css


def _apply_contract_adapters() -> None:
    profiles = renderer.PRESET_THEME_PROFILES

    profiles["moonlit-herbarium-atlas"]["css"] = _replace_required(
        profiles["moonlit-herbarium-atlas"]["css"],
        "moonlit-herbarium-atlas",
        [
            (
                'html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-area',
                'html[data-style-case="moonlit-herbarium-atlas"] [data-layout-id="cover-center-title-edge-decor"]:not([data-composition-variant="centered-signal-hero"]) .cover-center-area',
            ),
        ],
    )

    profiles["after-dark-veil"]["css"] = _replace_required(
        profiles["after-dark-veil"]["css"],
        "after-dark-veil",
        [
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
    )

    profiles["scent-veil-launch"]["css"] += r'''
html[data-style-case="scent-veil-launch"]{--bg:#FAF4F6;--surface:#FFFDFE;--text:#4D3545;--muted:#876D7D;--accent:#AD496F;--accent-ink:#8D3558;--surface-accent-ink:#8D3558;--accent-text:#FFFDFE;--surface-text:#4D3545;--surface-muted:#876D7D;--support-accent:#C99CA9}
html[data-style-case="scent-veil-launch"] [data-edit-kind="text"],html[data-style-case="scent-veil-launch"] [data-edit-layer="text"]{color:#4D3545!important;text-shadow:none!important}
html[data-style-case="scent-veil-launch"] [data-edit-layer="metric"],html[data-style-case="scent-veil-launch"] :is(.module-number,.sequence-number,.metric-strip-value,.metric-panel-value){color:#8D3558!important}
html[data-style-case="scent-veil-launch"] [data-visual-surface-role="accent"] [data-edit-kind="text"],html[data-style-case="scent-veil-launch"] [data-visual-surface-role="accent"] [data-edit-layer="text"]{color:var(--accent-text)!important}
html[data-style-case="scent-veil-launch"] [data-visual-surface-role="accent"] [data-edit-layer="metric"]{color:var(--accent-text)!important}
'''

    profiles["dark-city-network-report"]["css"] += r'''
html[data-style-case="dark-city-network-report"] [data-layout-id="cover-center-title-edge-decor"] .cover-center-org,html[data-style-case="dark-city-network-report"] [data-layout-id="timeline-milestones"] .timeline-milestone>span,html[data-style-case="dark-city-network-report"] [data-layout-id="quote-focus"] .statement-focus-attribution{color:#245D7C!important}
html[data-style-case="dark-city-network-report"] [data-layout-id="quote-focus"] .statement-focus-rail-line{background:#245D7C!important}
'''

    profiles["after-dark-veil"]["css"] += r'''
html[data-style-case="after-dark-veil"] [data-layout-id="comparison-table"] .compare-table .header.recommended{color:#0B0D12!important}
'''

    for preset_id in PRESET_IDS:
        profiles[preset_id]["css"] += (
            f'html[data-style-case="{preset_id}"] [data-layout-id="cycle-hub-6"] '
            '.cycle-hub .diagram-node-bg{border-radius:50%!important}\n'
        )


if __name__ == "__main__":
    _apply_contract_adapters()
    raise SystemExit(renderer.main())
