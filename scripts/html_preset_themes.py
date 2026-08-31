#!/usr/bin/env python3
"""Load and validate HTML-only preset themes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

try:
    from html_css_ownership import assert_appearance_css
    from html_preset_registry import load_preset_registry
except ModuleNotFoundError:  # package-style imports used by tests and notebooks
    from .html_css_ownership import assert_appearance_css
    from .html_preset_registry import load_preset_registry


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "prompt_system" / "renderers" / "html" / "preset-themes.yaml"
CORE_THEMES = ROOT / "prompt_system" / "themes"

FORBIDDEN_REUSABLE_FIELDS = {
    "source_style_case",
    "source_html",
    "source_css",
    "example_story",
    "example_layouts",
    "story",
    "layouts",
    "layout_id",
    "content",
    "text_replacements",
    "css",
}
ALLOWED_REUSABLE_FIELDS = {
    "display_name",
    "base_theme",
    "scope",
    "pure_html",
    "auto_select",
    "design_dialect",
    "composition",
    "techniques",
    "palette",
    "typography",
    "background_pattern",
    "background_graphics",
    "visual_asset_policy",
    "background_asset",
    "continuity_element",
    "surface",
}

IMAGE_BACKGROUND_POLICY = "generated-raster-background-opt-in"
IMAGE_BACKGROUND_GRAPHICS = "safe-zone-minimal-raster"
IMAGE_BACKGROUND_SAFE_PRESET_COHORT = (
    "line-argument-journal",
    "signal-route-atlas",
    "field-index-manual",
    "tide-signal-observatory",
    "craft-archive-editions",
    "incident-command-redline",
    "harbor-ribbon-program",
    "neighborhood-newsroom-proof",
    "scent-veil-launch",
    "restoration-blueprint-ledger",
    "ai-operations-signal",
    "brave-classroom-contours",
    "night-transit-wayfinding",
    "sepia-retail-case",
    "dark-ai-city",
    "dark-city-network-report",
    "clinical-evidence-atlas",
    "moonlit-herbarium-atlas",
)
FORBIDDEN_IMAGE_BACKGROUND_PATTERN = re.compile(
    r"(?:radial-gradient|repeating-radial-gradient|ellipse|orbit|ring|arc)",
    re.IGNORECASE,
)

PATTERN_PAINT = {
    "none": "background-image:none",
    "paper-grain": (
        "background-image:radial-gradient(circle,color-mix(in srgb,var(--text) 7%,transparent) 0 1px,transparent 1.5px);"
        "background-size:6px 6px"
    ),
    "circuit-nodes": (
        "background-image:radial-gradient(circle,color-mix(in srgb,var(--accent) 28%,transparent) 0 1px,transparent 1.6px);"
        "background-size:24px 24px"
    ),
    "engineering-grid": (
        "background-image:linear-gradient(color-mix(in srgb,var(--accent) 8%,transparent) 1px,transparent 1px),"
        "linear-gradient(90deg,color-mix(in srgb,var(--accent) 8%,transparent) 1px,transparent 1px);"
        "background-size:48px 48px"
    ),
    "coordinate-map-stock": (
        "background-image:linear-gradient(color-mix(in srgb,var(--support-accent) 6%,transparent) 1px,transparent 1px),"
        "linear-gradient(90deg,color-mix(in srgb,var(--support-accent) 6%,transparent) 1px,transparent 1px);"
        "background-size:72px 72px"
    ),
    "herbarium-ink-wash": (
        "background-image:radial-gradient(ellipse at 4% 12%,color-mix(in srgb,var(--support-accent) 10%,transparent),transparent 31%),"
        "radial-gradient(ellipse at 96% 88%,color-mix(in srgb,var(--accent) 7%,transparent),transparent 28%);"
        "background-size:100% 100%"
    ),
    "generated-paper-field": (
        "background-image:radial-gradient(circle at 82% 22%,color-mix(in srgb,var(--accent) 14%,transparent),transparent 28%),"
        "radial-gradient(circle at 12% 82%,color-mix(in srgb,var(--support-accent) 16%,transparent),transparent 32%),"
        "linear-gradient(120deg,rgba(255,255,255,.75),transparent 48%);"
        "background-size:100% 100%"
    ),
    "fine-ledger-grid": (
        "background-image:linear-gradient(color-mix(in srgb,var(--text) 4%,transparent) 1px,transparent 1px),"
        "linear-gradient(90deg,color-mix(in srgb,var(--text) 4%,transparent) 1px,transparent 1px);"
        "background-size:64px 64px"
    ),
    "nocturne-ambient": (
        "background-image:radial-gradient(circle at 15% 20%,color-mix(in srgb,var(--accent) 14%,transparent),transparent 28%),"
        "radial-gradient(circle at 85% 80%,color-mix(in srgb,var(--support-accent) 10%,transparent),transparent 30%);"
        "background-size:100% 100%"
    ),
    "woven-geometry": (
        "background-image:linear-gradient(135deg,color-mix(in srgb,var(--accent) 8%,transparent) 25%,transparent 25% 50%,color-mix(in srgb,var(--accent) 8%,transparent) 50% 75%,transparent 75%),"
        "linear-gradient(45deg,color-mix(in srgb,var(--support-accent) 7%,transparent) 25%,transparent 25% 50%,color-mix(in srgb,var(--support-accent) 7%,transparent) 50% 75%,transparent 75%);"
        "background-size:56px 56px"
    ),
    "ivory-arc-frame": (
        "background-image:"
        "radial-gradient(circle at -2% -8%,transparent 0 238px,color-mix(in srgb,var(--text) 12%,transparent) 239px 241px,transparent 242px),"
        "radial-gradient(circle at 103% 108%,transparent 0 300px,color-mix(in srgb,var(--text) 12%,transparent) 301px 303px,transparent 304px),"
        "linear-gradient(to bottom,transparent 0 28px,color-mix(in srgb,var(--text) 12%,transparent) 28px 30px,transparent 30px calc(100% - 30px),color-mix(in srgb,var(--text) 12%,transparent) calc(100% - 30px) calc(100% - 28px),transparent calc(100% - 28px));"
        "background-size:100% 100%"
    ),
}

# Legacy engine.  Presets that have not yet declared `surface.binding: v2` keep
# rendering through this table so their published appearance stays byte-stable
# while the shape/material vocabulary below is rolled out preset by preset.
SURFACE_PAINT = {
    "editorial-rule": "background:color-mix(in srgb,var(--surface) 88%,var(--bg));border-color:color-mix(in srgb,var(--accent) 46%,transparent);border-radius:2px",
    "ink-column": "background:color-mix(in srgb,var(--surface) 76%,transparent);border-color:color-mix(in srgb,var(--text) 22%,transparent);border-radius:0",
    "circuit-glass": "background:color-mix(in srgb,var(--surface) 78%,transparent);border-color:color-mix(in srgb,var(--accent) 58%,transparent);border-radius:6px;backdrop-filter:blur(10px)",
    "transfer-map-sheet": "background:color-mix(in srgb,var(--surface) 90%,var(--bg));border-color:color-mix(in srgb,var(--support-accent) 48%,transparent);border-radius:4px",
    "veil-pane": "background:color-mix(in srgb,var(--surface) 62%,transparent);border-color:color-mix(in srgb,var(--accent) 28%,transparent);border-radius:42px 12px 42px 12px;backdrop-filter:blur(14px)",
    "signal-strip": "background:color-mix(in srgb,var(--surface) 68%,var(--bg));border-color:color-mix(in srgb,var(--accent) 48%,transparent);border-radius:0",
    "ledger-sheet": "background:color-mix(in srgb,var(--surface) 88%,var(--bg));border-color:color-mix(in srgb,var(--text) 28%,transparent);border-radius:0",
    "night-glass": "background:color-mix(in srgb,var(--surface) 76%,transparent);border-color:color-mix(in srgb,var(--text) 18%,transparent);border-radius:24px;backdrop-filter:blur(16px)",
    "open-hairline-sheet": "background:color-mix(in srgb,var(--surface) 58%,transparent);border-color:color-mix(in srgb,var(--text) 20%,transparent);border-radius:0",
}

SURFACE_BINDING_V2 = "v2"

# v2 shape vocabulary.  A shape owns the outline and the border structure only:
# which edges exist, how the corners behave, how much ground the module keeps.
# It never paints texture (that is the material) and never paints a drop shadow
# (that is the depth profile), so the three layers can compose in any order.
#
# These shapes are meant to be read as one set, so they share a deliberately
# small grammar.  Every shape stays inside it:
#   - square corners unless the subject itself asks for a soft one
#   - border weights drawn from 1 / 2 / 3 / 5 / 6 / 8 / 9 px only
#   - border colour is always a mix of --text, --accent or --support-accent
#   - corner cuts are 18 / 22 / 26 px only
#   - no shadow and no background-image here; those layers own themselves
SURFACE_SHAPE_PAINT = {
    # Squared publication paper carrying one heavy rule on the leading edge.
    "editorial-rule": (
        "background:color-mix(in srgb,var(--surface) 88%,var(--bg));"
        "border-width:0;"
        "border-top:5px solid color-mix(in srgb,var(--accent) 62%,transparent);"
        "border-radius:0"
    ),
    # Low-opacity paper column anchored by a heavy ink spine on the reading edge.
    "ink-column": (
        "background:color-mix(in srgb,var(--surface) 76%,transparent);"
        "border-color:color-mix(in srgb,var(--text) 24%,transparent);"
        "border-width:1px;border-left-width:6px;border-radius:0"
    ),
    # Dark glass held by a luminous accent hairline, squared rather than soft.
    "circuit-glass": (
        "background:color-mix(in srgb,var(--surface) 78%,transparent);"
        "border-color:color-mix(in srgb,var(--accent) 58%,transparent);"
        "border-width:1px;border-radius:0;backdrop-filter:blur(10px)"
    ),
    # Ticket stock: printed rules top and bottom, tear-off edges left and right.
    "transfer-map-sheet": (
        "background:color-mix(in srgb,var(--surface) 90%,var(--bg));"
        "border-color:color-mix(in srgb,var(--support-accent) 58%,transparent);"
        "border-width:2px;border-style:solid dashed;border-radius:0"
    ),
    # Asymmetric translucent pane: the only shape with a diagonal corner rhythm.
    "veil-pane": (
        "background:color-mix(in srgb,var(--surface) 62%,transparent);"
        "border-color:color-mix(in srgb,var(--accent) 28%,transparent);"
        "border-width:1px;border-radius:42px 12px 42px 12px;backdrop-filter:blur(14px)"
    ),
    # No enclosure at all: content sits on one signal rule.
    "signal-strip": (
        "background:color-mix(in srgb,var(--surface) 46%,transparent);"
        "border-width:0;"
        "border-bottom:4px solid color-mix(in srgb,var(--accent) 70%,transparent);"
        "border-radius:0"
    ),
    # Ledger sheet: ink rules top and bottom with one clipped filing corner.
    "ledger-sheet": (
        "background:color-mix(in srgb,var(--surface) 88%,var(--bg));"
        "border-width:0;"
        "border-top:2px solid color-mix(in srgb,var(--text) 46%,transparent);"
        "border-bottom:2px solid color-mix(in srgb,var(--text) 46%,transparent);"
        "border-radius:0 0 14px 0"
    ),
    # Rounded night glass, the softest shape in the vocabulary.
    "night-glass": (
        "background:color-mix(in srgb,var(--surface) 76%,transparent);"
        "border-color:color-mix(in srgb,var(--text) 18%,transparent);"
        "border-width:1px;border-radius:24px;backdrop-filter:blur(16px)"
    ),
    # Almost no ground: four ink hairlines and the paper showing through.
    "open-hairline-sheet": (
        "background:color-mix(in srgb,var(--surface) 74%,var(--bg));"
        "border-color:color-mix(in srgb,var(--text) 20%,transparent);"
        "border-width:1px;border-radius:0"
    ),
    # Two ink lines down the binding edge, the way a stitched archive volume
    # carries its signature marks.
    "bindery-spine": (
        "background:color-mix(in srgb,var(--surface) 82%,var(--bg));"
        "border-width:0;"
        "border-left:9px double color-mix(in srgb,var(--text) 46%,transparent);"
        "border-radius:0"
    ),
    # Newspaper column rules: the sides are the structure, top and bottom stay
    # open so copy reads as one running column.
    "proof-column": (
        "background:color-mix(in srgb,var(--surface) 70%,transparent);"
        "border-color:color-mix(in srgb,var(--text) 28%,transparent);"
        "border-style:solid;border-width:0 1px;border-radius:0"
    ),
    # An operations rail: one status edge down the side, one handoff line under
    # it, and nothing enclosing the content.
    "console-rail": (
        "background:color-mix(in srgb,var(--surface) 40%,transparent);"
        "border-width:0;"
        "border-left:5px solid var(--accent);"
        "border-bottom:1px solid color-mix(in srgb,var(--text) 26%,transparent);"
        "border-radius:0"
    ),
    # A platform sign blade: square colour band on the approach edge, rounded
    # on the far edge, the way transit wayfinding panels point.
    "wayfinding-blade": (
        "background:color-mix(in srgb,var(--surface) 84%,var(--bg));"
        "border-width:0;"
        "border-left:8px solid var(--accent);"
        "border-radius:0 22px 22px 0;backdrop-filter:blur(6px)"
    ),
    # A broadsheet masthead: a doubled rule across the top and nothing else.
    "masthead-rule": (
        "background:color-mix(in srgb,var(--surface) 90%,var(--bg));"
        "border-width:0;"
        "border-top:7px double color-mix(in srgb,var(--accent) 68%,transparent);"
        "border-radius:0"
    ),
    # Cut-corner command plate with a hard edge on every side.
    "industrial-plate": (
        "background:color-mix(in srgb,var(--surface) 94%,var(--bg));"
        "border-color:color-mix(in srgb,var(--accent) 72%,transparent);"
        "border-width:3px;border-radius:0;"
        "clip-path:polygon(0 0,calc(100% - 22px) 0,100% 22px,100% 100%,22px 100%,0 calc(100% - 22px))"
    ),
    # Poster stock: one thick printed keyline and a single clipped corner.
    "screenprint-panel": (
        "background:color-mix(in srgb,var(--surface) 96%,var(--bg));"
        "border-color:color-mix(in srgb,var(--text) 82%,transparent);"
        "border-width:6px;border-radius:0;"
        "clip-path:polygon(0 0,100% 0,100% calc(100% - 26px),calc(100% - 26px) 100%,0 100%)"
    ),
    # Drawing-section glass: opposite corners cut, hairline edge, half ground.
    "glass-section": (
        "background:color-mix(in srgb,var(--surface) 66%,transparent);"
        "border-color:color-mix(in srgb,var(--support-accent) 52%,transparent);"
        "border-width:1px;border-radius:0;backdrop-filter:blur(6px);"
        "clip-path:polygon(18px 0,100% 0,100% calc(100% - 18px),calc(100% - 18px) 100%,0 100%,0 18px)"
    ),
    # Hand-cut learning card: uneven radii, no keyline at all.
    "organic-card": (
        "background:color-mix(in srgb,var(--surface) 92%,var(--bg));"
        "border-width:0;border-radius:34px 12px 30px 14px"
    ),
    # Torn paper: the bottom edge is nibbled away by a mask.
    "torn-paper": (
        "background:color-mix(in srgb,var(--surface) 92%,var(--bg));"
        "border-width:0;border-radius:0;"
        "mask-image:radial-gradient(circle at 50% 100%,transparent 0 7px,#000 7.5px);"
        "mask-size:22px 22px;mask-position:0 100%;"
        "-webkit-mask-image:radial-gradient(circle at 50% 100%,transparent 0 7px,#000 7.5px);"
        "-webkit-mask-size:22px 22px;-webkit-mask-position:0 100%"
    ),
    # Frosted pearl: wide soft radius, barely-there edge, heavy blur.
    "frosted-pearl": (
        "background:color-mix(in srgb,var(--surface) 58%,transparent);"
        "border-color:color-mix(in srgb,var(--text) 10%,transparent);"
        "border-width:1px;border-radius:22px;backdrop-filter:blur(18px)"
    ),
}

# v2 material families.  A material only paints texture on top of whatever
# ground the shape established, so it can never change the outline.  Texture
# alpha stays at or below the 25% ceiling the background pattern policy uses.
MATERIAL_PAINT = {
    "matte": (
        "background-image:linear-gradient(180deg,color-mix(in srgb,var(--text) 5%,transparent),transparent 44%);"
        "background-size:100% 100%;background-blend-mode:multiply"
    ),
    "grain": (
        "background-image:radial-gradient(circle,color-mix(in srgb,var(--text) 9%,transparent) 0 1px,transparent 1.4px);"
        "background-size:5px 5px;background-blend-mode:multiply"
    ),
    "newsprint": (
        "background-image:radial-gradient(circle,color-mix(in srgb,var(--text) 8%,transparent) 0 .8px,transparent 1.1px);"
        "background-size:3px 3px;background-blend-mode:multiply"
    ),
    "fiber": (
        "background-image:repeating-linear-gradient(24deg,color-mix(in srgb,var(--text) 8%,transparent) 0 1px,transparent 1px 9px);"
        "background-size:100% 100%;background-blend-mode:multiply"
    ),
    "laid": (
        "background-image:repeating-linear-gradient(180deg,color-mix(in srgb,var(--text) 6%,transparent) 0 1px,transparent 1px 7px);"
        "background-size:100% 100%;background-blend-mode:multiply"
    ),
    "glass": (
        "background-image:linear-gradient(128deg,color-mix(in srgb,#ffffff 10%,transparent),transparent 38%,color-mix(in srgb,var(--accent) 8%,transparent));"
        "background-size:100% 100%;background-blend-mode:screen"
    ),
    "metal": (
        "background-image:repeating-linear-gradient(180deg,color-mix(in srgb,var(--text) 12%,transparent) 0 1px,transparent 1px 4px);"
        "background-size:100% 100%;background-blend-mode:overlay"
    ),
    "screenprint": (
        "background-image:radial-gradient(circle,color-mix(in srgb,var(--accent) 11%,transparent) 0 2.4px,transparent 3px);"
        "background-size:11px 11px;background-blend-mode:multiply"
    ),
    "blueprint": (
        "background-image:linear-gradient(color-mix(in srgb,var(--support-accent) 10%,transparent) 1px,transparent 1px),"
        "linear-gradient(90deg,color-mix(in srgb,var(--support-accent) 10%,transparent) 1px,transparent 1px);"
        "background-size:18px 18px;background-blend-mode:multiply"
    ),
    "map": (
        "background-image:linear-gradient(color-mix(in srgb,var(--support-accent) 12%,transparent) 1px,transparent 1px),"
        "linear-gradient(90deg,color-mix(in srgb,var(--support-accent) 12%,transparent) 1px,transparent 1px);"
        "background-size:40px 40px;background-blend-mode:multiply"
    ),
}

# Every material id declared by a Preset resolves to exactly one family.  The id
# stays the design-facing name; the family is what the renderer can actually
# paint.  An unmapped id is a build failure, not a silent no-texture fallback.
MATERIAL_FAMILY = {
    # published cohort
    "cold-proof-paper": "newsprint",
    "cold-newsprint-proof": "newsprint",
    "warm-retail-grain": "grain",
    "warm-archive-stock": "fiber",
    "celadon-file-paper": "laid",
    "night-civic-broadsheet": "laid",
    "clinical-matte-sheet": "matte",
    "matte-observation-board": "matte",
    "low-glare-wayfinding-board": "matte",
    "matte-command-board": "metal",
    "ops-console-board": "metal",
    "daylight-program-stock": "screenprint",
    "parchment-blueprint-sheet": "blueprint",
    "ink-on-warm-map-stock": "map",
    "translucent-perfume-paper": "glass",
    "urban-night-glass": "glass",
    "matte-learning-paper": "grain",
    # draft cohort, mapped now so a later binding flip needs no new plumbing
    "rice-paper-matte": "grain",
    "dawn-paper": "grain",
    "warm-editorial-paper": "grain",
    "charcoal-stage-paper": "grain",
    "warm-ivory-editorial-paper": "grain",
    "civic-matte-stock": "matte",
    "matte-clay-paper": "matte",
    "observatory-blackboard": "matte",
    "saline-lab-sheet": "matte",
    "mineral-paper": "laid",
    "field-notebook-paper": "laid",
    "archival-cardstock": "laid",
    "moss-fiber-paper": "fiber",
    "ink-garden-stock": "fiber",
    "rose-fiber-paper": "fiber",
    "dark-translucent-glass": "glass",
    "frosted-research-sheet": "glass",
    "graphite-workpaper": "metal",
    "dark-screenprint-paper": "screenprint",
}

# The six semantic surface roles.  A role never changes the shape; it only
# states how much ground and which edge that kind of module keeps, so every
# module in one Preset still reads as the same material family.
SURFACE_ROLES = ("panel", "index", "metric", "timeline", "ledger", "statement")

# Ground-only defaults.  These three roles are about how much presence a module
# has, so they only move the fill: no shape ever loses its edges or its corner
# rhythm to a role, which is what keeps one Preset reading as one family.
SURFACE_ROLE_DELTA = {
    "panel": "",
    "index": "background:color-mix(in srgb,var(--surface) 52%,transparent)",
    "metric": "",
    "timeline": "",
    "ledger": "background:color-mix(in srgb,var(--surface) 96%,var(--bg))",
    "statement": "background:color-mix(in srgb,var(--surface) 40%,transparent)",
}

# `metric` and `timeline` have no safe shared form: a single accent top rule for
# every metric module put all seventeen Presets back on the same card.  So each
# shape states them in its own language -- metric leans on that shape's own
# signature edge, timeline opens the enclosure along the reading direction.
SURFACE_SHAPE_ROLE_DELTA = {
    "editorial-rule": {
        "metric": "border-top-width:9px",
        "timeline": (
            "background:color-mix(in srgb,var(--surface) 26%,transparent);"
            "border-top-width:2px"
        ),
    },
    "ink-column": {
        "metric": "border-left-width:12px",
        "timeline": (
            "background:color-mix(in srgb,var(--surface) 26%,transparent);"
            "border-width:0;"
            "border-left:3px solid color-mix(in srgb,var(--text) 34%,transparent)"
        ),
    },
    "circuit-glass": {
        "metric": "border-width:2px;border-color:var(--accent)",
        "timeline": (
            "background:color-mix(in srgb,var(--surface) 30%,transparent);"
            "border-width:0;"
            "border-left:2px solid color-mix(in srgb,var(--accent) 70%,transparent)"
        ),
    },
    "transfer-map-sheet": {
        "metric": "border-top-width:6px",
        "timeline": (
            "background:color-mix(in srgb,var(--surface) 34%,var(--bg));"
            "border-style:solid none;border-width:2px 0"
        ),
    },
    "veil-pane": {
        "metric": "border-width:2px;border-color:color-mix(in srgb,var(--accent) 62%,transparent)",
        "timeline": "background:color-mix(in srgb,var(--surface) 34%,transparent)",
    },
    "signal-strip": {
        # Weight belongs on the bottom rule, never on a new top edge.
        "metric": "border-bottom-width:9px;border-bottom-color:var(--accent)",
        "timeline": (
            "background:color-mix(in srgb,var(--surface) 22%,transparent);"
            "border-bottom-width:2px"
        ),
    },
    "ledger-sheet": {
        "metric": "border-top-width:6px;border-top-color:color-mix(in srgb,var(--accent) 78%,transparent)",
        "timeline": (
            "background:color-mix(in srgb,var(--surface) 30%,var(--bg));"
            "border-bottom-width:0"
        ),
    },
    "night-glass": {
        "metric": "border-width:2px;border-color:color-mix(in srgb,var(--accent) 58%,transparent)",
        "timeline": (
            "background:color-mix(in srgb,var(--surface) 34%,transparent);"
            "border-width:0;"
            "border-bottom:2px solid color-mix(in srgb,var(--accent) 52%,transparent)"
        ),
    },
    "open-hairline-sheet": {
        "metric": "border-top-width:5px;border-top-color:color-mix(in srgb,var(--text) 52%,transparent)",
        "timeline": (
            "background:color-mix(in srgb,var(--surface) 30%,transparent);"
            "border-width:0;"
            "border-bottom:1px solid color-mix(in srgb,var(--text) 32%,transparent)"
        ),
    },
    "industrial-plate": {
        # The cut corners live on the border, so the plate edge always survives.
        "metric": "border-width:5px",
        "timeline": (
            "background:color-mix(in srgb,var(--surface) 40%,transparent);border-width:2px"
        ),
    },
    "screenprint-panel": {
        "metric": "border-color:color-mix(in srgb,var(--accent) 86%,transparent)",
        "timeline": (
            "background:color-mix(in srgb,var(--surface) 44%,transparent);border-width:3px"
        ),
    },
    "glass-section": {
        "metric": "border-width:2px;border-color:color-mix(in srgb,var(--accent) 66%,transparent)",
        "timeline": "background:color-mix(in srgb,var(--surface) 30%,transparent)",
    },
    "organic-card": {
        # No keyline to lean on, so presence comes from the ground itself.
        "metric": "background:color-mix(in srgb,var(--accent) 12%,var(--surface))",
        "timeline": "background:color-mix(in srgb,var(--surface) 34%,transparent)",
    },
    "torn-paper": {
        "metric": "background:color-mix(in srgb,var(--accent) 10%,var(--surface))",
        "timeline": "background:color-mix(in srgb,var(--surface) 40%,transparent)",
    },
    "frosted-pearl": {
        "metric": "border-width:2px;border-color:color-mix(in srgb,var(--accent) 52%,transparent)",
        "timeline": "background:color-mix(in srgb,var(--surface) 34%,transparent)",
    },
    "bindery-spine": {
        "metric": "border-left-width:15px",
        "timeline": (
            "background:color-mix(in srgb,var(--surface) 30%,transparent);"
            "border-left:3px solid color-mix(in srgb,var(--text) 40%,transparent)"
        ),
    },
    "proof-column": {
        "metric": "border-width:0 5px;border-color:color-mix(in srgb,var(--accent) 62%,transparent)",
        "timeline": (
            "background:color-mix(in srgb,var(--surface) 28%,transparent);"
            "border-width:0 0 0 1px"
        ),
    },
    "console-rail": {
        "metric": "border-left-width:10px",
        "timeline": (
            "background:color-mix(in srgb,var(--surface) 24%,transparent);"
            "border-left-width:2px"
        ),
    },
    "wayfinding-blade": {
        "metric": "border-left-width:14px",
        "timeline": (
            "background:color-mix(in srgb,var(--surface) 36%,transparent);"
            "border-left-width:3px"
        ),
    },
    "masthead-rule": {
        "metric": "border-top-width:11px",
        "timeline": (
            "background:color-mix(in srgb,var(--surface) 28%,transparent);"
            "border-top-width:3px;border-top-style:solid"
        ),
    },
}

DEPTH_PAINT = {
    "editorial-flat": "box-shadow:none",
    "product-flat": "box-shadow:none",
    "technical-glass": "box-shadow:0 16px 38px color-mix(in srgb,var(--text) 9%,transparent)",
    "paper-stack": "box-shadow:0 14px 32px color-mix(in srgb,var(--text) 9%,transparent)",
    "restrained-luminous-paper": "box-shadow:0 24px 60px color-mix(in srgb,var(--text) 9%,transparent),inset 0 1px rgba(255,255,255,.82)",
    "ledger-flat": "box-shadow:0 10px 24px color-mix(in srgb,var(--text) 7%,transparent)",
    "nocturne-float": "box-shadow:0 22px 68px color-mix(in srgb,#000 32%,transparent)",
}


def _rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        raise ValueError(f"Preset palette color must be #RGB or #RRGGBB: {hex_color}")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _luminance(hex_color: str) -> float:
    channels = []
    for value in _rgb(hex_color):
        channel = value / 255
        channels.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(left: str, right: str) -> float:
    a, b = sorted((_luminance(left), _luminance(right)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _best_ink(background: str, candidates: list[str]) -> str:
    return max(candidates, key=lambda value: _contrast(background, value))


LEGACY_SURFACE_FALLBACK = (
    "background:color-mix(in srgb,var(--surface) 84%,var(--bg));"
    "border-color:color-mix(in srgb,var(--accent) 36%,transparent);border-radius:8px"
)


def resolve_material_family(theme_id: str, material_id: str) -> str:
    """Map a Preset's design-facing material name onto a paintable family."""

    family = MATERIAL_FAMILY.get(material_id)
    if family is None:
        raise ValueError(
            f"{theme_id}: surface.material {material_id!r} has no material family; "
            "add it to MATERIAL_FAMILY instead of letting the texture disappear"
        )
    return family


def _build_surface_rules(
    theme_id: str,
    surface: dict[str, Any],
    surface_id: str,
    scope: str,
) -> tuple[str, list[str]]:
    """Return the base `.diagram-node-bg` paint plus any semantic role rules.

    Presets that have not opted into `surface.binding: v2` keep the legacy
    single-rule paint so their published appearance does not move.
    """

    if str(surface.get("binding") or "") != SURFACE_BINDING_V2:
        return SURFACE_PAINT.get(surface_id, LEGACY_SURFACE_FALLBACK), []

    shape_css = SURFACE_SHAPE_PAINT.get(surface_id)
    if shape_css is None:
        raise ValueError(
            f"{theme_id}: surface {surface_id!r} has no v2 shape paint; "
            "a declared surface must never fall back to a generic card"
        )
    material_id = str(surface.get("material") or "")
    if not material_id:
        raise ValueError(f"{theme_id}: surface.binding v2 requires surface.material")
    material_css = MATERIAL_PAINT[resolve_material_family(theme_id, material_id)]

    variants = surface.get("semantic_variants") or {}
    if not isinstance(variants, dict):
        raise ValueError(
            f"{theme_id}: surface.semantic_variants must map role -> variant name"
        )
    unknown = sorted(set(variants) - set(SURFACE_ROLES))
    if unknown:
        raise ValueError(f"{theme_id}: unknown surface roles {unknown}")

    shape_roles = SURFACE_SHAPE_ROLE_DELTA.get(surface_id, {})
    rules: list[str] = []
    for role in SURFACE_ROLES:
        if role == "panel" or role not in variants:
            continue
        delta = shape_roles.get(role, SURFACE_ROLE_DELTA[role])
        if not delta:
            continue
        # The delta may reset `background`, so the material is re-applied after
        # it; depth is intentionally omitted so the base rule keeps owning it.
        rules.append(
            f'{scope} [data-surface-role="{role}"]>.diagram-node-bg'
            f"{{{shape_css};{delta};{material_css}}}"
        )
    return f"{shape_css};{material_css}", rules


def build_preset_appearance_css(
    theme_id: str,
    theme: dict[str, Any],
    assembly_recipe: dict[str, Any],
) -> str:
    """Build appearance-only CSS from Preset tokens, never from an old case."""

    palette = theme["palette"]
    accent_text = _best_ink(
        palette["accent"],
        [palette["background"], palette["text"], "#000000", "#ffffff"],
    )
    scope = f'html[data-preset-theme="{theme_id}"]'
    surface_text = _best_ink(
        palette["surface"],
        [palette["text"], palette["background"], "#000000", "#ffffff"],
    )
    surface_muted = (
        palette["muted"]
        if _contrast(palette["muted"], palette["surface"]) >= 4.5
        else _best_ink(palette["surface"], [palette["muted"], surface_text, "#000000", "#ffffff"])
    )
    variables = {
        "--bg": palette["background"],
        "--primary": palette["text"],
        "--secondary": palette["muted"],
        "--accent": palette["accent"],
        "--support-accent": palette["support"],
        "--surface": palette["surface"],
        "--text": palette["text"],
        "--muted": palette["muted"],
        "--surface-text": surface_text,
        "--surface-muted": surface_muted,
        "--accent-ink": _best_ink(palette["background"], [palette["accent"], palette["text"]]),
        "--surface-accent-ink": _best_ink(palette["surface"], [palette["accent"], palette["text"]]),
        "--accent-text": accent_text,
    }
    typography = theme.get("typography") or {}
    if typography.get("display"):
        variables["--font-display"] = json.dumps(str(typography["display"]), ensure_ascii=False)
        variables["--font-heading"] = variables["--font-display"]
    if typography.get("body"):
        variables["--font-body"] = json.dumps(str(typography["body"]), ensure_ascii=False)
    if typography.get("utility"):
        variables["--font-mono"] = json.dumps(str(typography["utility"]), ensure_ascii=False)

    image_background_mode = theme.get("visual_asset_policy") == IMAGE_BACKGROUND_POLICY
    pattern_id = (
        "none"
        if image_background_mode
        else str(theme.get("background_pattern") or assembly_recipe["background_pattern"])
    )
    surface = theme.get("surface") or {}
    if not isinstance(surface, dict):
        surface = {"default": surface}
    surface_id = str(surface.get("default") or assembly_recipe["surface"])
    if not surface_id or surface_id == "None":
        surface_id = str(assembly_recipe["surface"])
    depth_id = str(assembly_recipe["depth"])
    pattern_css = PATTERN_PAINT.get(pattern_id, "background-image:none")
    if image_background_mode and FORBIDDEN_IMAGE_BACKGROUND_PATTERN.search(pattern_css):
        raise ValueError(
            f"{theme_id}: image-background mode cannot emit symbolic ambient pattern paint"
        )
    depth_css = DEPTH_PAINT.get(depth_id, "box-shadow:none")
    surface_css, role_rules = _build_surface_rules(theme_id, surface, surface_id, scope)
    role_css = "\n".join(role_rules)
    if role_css:
        role_css += "\n"
    variable_css = ";".join(f"{name}:{value}" for name, value in variables.items())
    css = f"""
{scope}{{{variable_css}}}
{scope} .slide{{color:var(--text);background-color:var(--bg);{pattern_css}}}
{scope} .diagram-node-bg{{{surface_css};{depth_css}}}
{role_css}{scope} :is(.prod-title,.cover-center-title,.cover-split-title,.statement-focus-quote,.statement-center-headline){{color:var(--text);font-family:var(--font-display);font-weight:800;letter-spacing:-.025em;text-shadow:none}}
{scope} :is(.prod-subtitle,.cover-center-subtitle,.statement-center-support){{color:var(--muted);font-family:var(--font-body)}}
{scope} :is(.chapter-brand-overlay,.media-overlay-title,.cover-overlay-block,.cover-overlay-accent) > .diagram-node-bg{{background:var(--surface);background-image:none;border-top:5px solid var(--accent);backdrop-filter:none}}
{scope} :is(.chapter-brand-overlay,.media-overlay-title,.cover-overlay-block,.cover-overlay-accent) > :is(span,b,em){{color:var(--surface-text)}}
{scope} [data-visual-surface-role="accent"]>.diagram-node-bg{{background:var(--accent);background-image:none;border-color:transparent}}
{scope} [data-visual-surface-role="none"]>.diagram-node-bg{{background:none;border-width:0;border-color:transparent;border-radius:inherit;box-shadow:none}}
""".strip()
    assert_appearance_css(css, source=f"preset:{theme_id}")
    return css


def load_html_preset_theme_catalog(path: Path = DEFAULT_CATALOG) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    themes = data.get("themes") or {}
    core_ids = {item.stem for item in CORE_THEMES.glob("*.yaml")}
    issues: list[str] = []

    if data.get("schema_version") != 2:
        issues.append("schema_version must be 2")
    runtime_contract = data.get("runtime_contract") or {}
    expected_runtime_contract = {
        "css_owner": "preset-appearance",
        "content_source": "caller-only",
        "layout_source": "layout-core-only",
        "legacy_case_import": "forbidden",
        "embedded_css": "forbidden",
        "layout_selectors": "forbidden",
        "geometry_properties": "forbidden",
        "important": "forbidden",
    }
    if runtime_contract != expected_runtime_contract:
        issues.append("runtime_contract must enforce appearance-only Preset isolation")
    if not themes:
        issues.append("themes must be a non-empty object")
    for theme_id, theme in themes.items():
        if not isinstance(theme, dict):
            issues.append(f"{theme_id}: theme must be an object")
            continue
        if theme_id in core_ids:
            issues.append(f"{theme_id}: preset id collides with a core theme")
        if theme.get("base_theme") not in core_ids:
            issues.append(f"{theme_id}: unknown base_theme {theme.get('base_theme')}")
        if theme.get("scope") != "html-only" or theme.get("pure_html") is not True:
            issues.append(f"{theme_id}: preset must be html-only and pure_html")
        forbidden_fields = sorted(FORBIDDEN_REUSABLE_FIELDS & set(theme))
        if forbidden_fields:
            issues.append(f"{theme_id}: reusable Preset contains demo/runtime fields {forbidden_fields}")
        unknown_fields = sorted(set(theme) - ALLOWED_REUSABLE_FIELDS)
        if unknown_fields:
            issues.append(f"{theme_id}: unknown reusable Preset fields {unknown_fields}")
        if not theme.get("design_dialect") or not theme.get("composition"):
            issues.append(f"{theme_id}: design_dialect and composition are required")
        if len(theme.get("techniques") or []) < 3:
            issues.append(f"{theme_id}: at least three HTML techniques are required")
        if theme_id in IMAGE_BACKGROUND_SAFE_PRESET_COHORT:
            if theme.get("visual_asset_policy") != IMAGE_BACKGROUND_POLICY:
                issues.append(
                    f"{theme_id}: fixed image-background cohort must explicitly use "
                    f"visual_asset_policy={IMAGE_BACKGROUND_POLICY}"
                )
            if theme.get("background_pattern") != "none":
                issues.append(
                    f"{theme_id}: fixed image-background cohort must set background_pattern to none"
                )
            if theme.get("background_graphics") != IMAGE_BACKGROUND_GRAPHICS:
                issues.append(
                    f"{theme_id}: fixed image-background cohort must use "
                    f"background_graphics={IMAGE_BACKGROUND_GRAPHICS}"
                )
        elif theme.get("visual_asset_policy") == IMAGE_BACKGROUND_POLICY:
            if theme.get("background_pattern") != "none":
                issues.append(
                    f"{theme_id}: image-background Preset must set background_pattern to none"
                )
            if theme.get("background_graphics") != IMAGE_BACKGROUND_GRAPHICS:
                issues.append(
                    f"{theme_id}: image-background Preset must use "
                    f"background_graphics={IMAGE_BACKGROUND_GRAPHICS}"
                )
        palette = theme.get("palette") or {}
        required_colors = {"background", "surface", "text", "muted", "accent", "support"}
        if not required_colors.issubset(palette):
            issues.append(f"{theme_id}: incomplete curated palette")

    missing_image_background_presets = sorted(
        set(IMAGE_BACKGROUND_SAFE_PRESET_COHORT) - set(themes)
    )
    if missing_image_background_presets:
        issues.append(
            "fixed image-background cohort is missing Presets "
            f"{missing_image_background_presets}"
        )

    policy = data.get("selection_policy") or {}
    if policy.get("random_hue_mutation") != "forbidden":
        issues.append("selection_policy.random_hue_mutation must be forbidden")
    content_policy = data.get("content_policy") or {}
    if content_policy.get("default_mode") != "new-deck":
        issues.append("content_policy.default_mode must be new-deck")
    if content_policy.get("preset_demo_mode") != "explicit-only":
        issues.append("content_policy.preset_demo_mode must be explicit-only")
    if content_policy.get("demo_source") != "external-isolated-route-only":
        issues.append("content_policy.demo_source must be external-isolated-route-only")
    if content_policy.get("reusable_preset_demo_fields") != "forbidden":
        issues.append("content_policy.reusable_preset_demo_fields must be forbidden")
    if issues:
        raise ValueError("HTML preset theme catalog invalid: " + "; ".join(issues))

    if path.resolve() == DEFAULT_CATALOG.resolve():
        registry = load_preset_registry(check_gallery=False)
        registry_themes = {
            row["id"]: row
            for row in registry["entries"]
            if "reusable-preset" in row["capabilities"]
        }
        if set(themes) != set(registry_themes):
            raise ValueError("HTML preset theme catalog does not match the Preset registry")
        for theme_id, theme in themes.items():
            theme["display_name"] = registry_themes[theme_id]["display_name"]
        data["registry"] = "prompt_system/presets/catalog.yaml"

    data["counts"] = {
        "presets": len(themes),
        "auto_select": sum(1 for theme in themes.values() if theme.get("auto_select")),
    }
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()
    data = load_html_preset_theme_catalog(args.catalog.resolve())
    try:
        from html_assembly import resolve_html_assembly
    except ModuleNotFoundError:  # package-style imports used by tests and notebooks
        from .html_assembly import resolve_html_assembly
    for theme_id, theme in data["themes"].items():
        assembly = resolve_html_assembly(theme_id)
        build_preset_appearance_css(theme_id, theme, assembly["recipe"])
    print(json.dumps({"id": data["id"], **data["counts"], "css_contracts": len(data["themes"]), "pass": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
