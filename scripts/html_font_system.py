#!/usr/bin/env python3
"""Shared Google Fonts contract for generated HTML presentations."""

from __future__ import annotations

import html
from typing import Any
from urllib.parse import quote_plus


GOOGLE_FONT_REGISTRY: dict[str, dict[str, str]] = {
    "Noto Sans TC": {
        "weights": "300;400;500;600;700;800;900",
        "stack": '"Noto Sans TC","Microsoft JhengHei",system-ui,sans-serif',
    },
    "Noto Serif TC": {
        "weights": "300;400;500;600;700;800;900",
        "stack": '"Noto Serif TC","PMingLiU",serif',
    },
    "Roboto Mono": {
        "weights": "300;400;500;600;700",
        "stack": '"Roboto Mono","Noto Sans TC",ui-monospace,Consolas,monospace',
    },
}


def resolve_google_font_family(value: str | None) -> str:
    """Normalize prose-like Theme font descriptions to an allowed family."""
    source = str(value or "")
    lowered = source.lower()
    if "monospace" in lowered or "打字機" in source or "等寬" in source:
        return "Roboto Mono"
    if "無襯線" in source or "黑體" in source or "sans" in lowered or "microsoft yahei" in lowered:
        return "Noto Sans TC"
    if "noto serif tc" in lowered or "serif" in lowered or "襯線" in source:
        return "Noto Serif TC"
    return "Noto Sans TC"


def css_font_stack(family: str) -> str:
    if family not in GOOGLE_FONT_REGISTRY:
        raise ValueError(f"Unsupported HTML font family: {family}")
    return GOOGLE_FONT_REGISTRY[family]["stack"]


def google_fonts_url(families: list[str] | tuple[str, ...] | set[str]) -> str:
    ordered = [family for family in GOOGLE_FONT_REGISTRY if family in set(families)]
    specs = []
    for family in ordered:
        encoded = quote_plus(family)
        weights = GOOGLE_FONT_REGISTRY[family]["weights"]
        specs.append(f"family={encoded}:wght@{weights}")
    if not specs:
        raise ValueError("At least one registered Google Font is required")
    return "https://fonts.googleapis.com/css2?" + "&".join(specs) + "&display=swap"


def theme_font_contract(theme: dict[str, Any] | None = None) -> dict[str, str]:
    theme = theme or {}
    typography = theme.get("typography") or {}
    heading = resolve_google_font_family((typography.get("heading") or {}).get("family"))
    body = resolve_google_font_family((typography.get("body") or {}).get("family"))
    required = {heading, body, "Noto Sans TC", "Noto Serif TC", "Roboto Mono"}
    return {
        "heading_family": heading,
        "body_family": body,
        "mono_family": "Roboto Mono",
        "display_family": "Noto Serif TC",
        "heading_stack": css_font_stack(heading),
        "body_stack": css_font_stack(body),
        "mono_stack": css_font_stack("Roboto Mono"),
        "display_stack": css_font_stack("Noto Serif TC"),
        "url": google_fonts_url(required),
    }


def google_fonts_head(theme: dict[str, Any] | None = None) -> str:
    contract = theme_font_contract(theme)
    url = html.escape(contract["url"], quote=True)
    return (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link rel="stylesheet" data-font-system="google-fonts-css2" href="{url}">'
    )
