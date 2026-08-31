from __future__ import annotations

import re


_LAYOUT_FAMILY_RULES = (
    (r"^(hero|cover)", "cover"),
    (r"^chapter", "chapter"),
    (r"^closing", "closing"),
    (r"^toc", "toc"),
    (r"^(cards|icon-grid|people|team)", "modules"),
    (r"^(process|flow|timeline|gantt)", "sequence"),
    (r"^infographic", "infographic"),
    (r"^(matrix|swot|before-after|split-comparison|comparison|pricing)", "comparison"),
    (r"^(kpi|stats|dashboard)", "metrics"),
    (r"^(photo|executive|testimonial)", "media"),
    (r"^(map|heat|radar|multi-line-chart|data-annotation)", "data-viz"),
    (r"^(quote|highlight|title-center)", "statement"),
    (r"^(pyramid|funnel|cycle|org-chart)", "diagram"),
)


def layout_family(layout_id: str) -> str:
    """Return the single family name shared by adapters and HTML runtime."""

    for pattern, family in _LAYOUT_FAMILY_RULES:
        if re.search(pattern, layout_id):
            return family
    return "content"
