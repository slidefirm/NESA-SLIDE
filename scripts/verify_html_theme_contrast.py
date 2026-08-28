#!/usr/bin/env python3
"""Verify shared HTML Theme token contrast across the renderer matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from html_production_renderer import _contrast, theme_tokens


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--minimum", type=float, default=4.5)
    args = parser.parse_args()

    matrix = json.loads(Path(args.matrix).read_text(encoding="utf-8"))
    issues = []
    measurements = []
    for theme in matrix["themes"]:
        tokens = theme_tokens(theme)
        pairs = {
            "text/background": (tokens["text"], tokens["background"]),
            "muted/background": (tokens["muted"], tokens["background"]),
            "surface-text/surface": (tokens["surface_text"], tokens["surface"]),
            "surface-muted/surface": (tokens["surface_muted"], tokens["surface"]),
            "accent-text/accent": (tokens["accent_text"], tokens["accent"]),
        }
        theme_ratios = {name: round(_contrast(foreground, background), 3) for name, (foreground, background) in pairs.items()}
        measurements.append({"theme": theme["id"], "ratios": theme_ratios})
        for name, ratio in theme_ratios.items():
            if ratio + 0.001 < args.minimum:
                issues.append({"theme": theme["id"], "pair": name, "ratio": ratio})

    report = {
        "themes": len(matrix["themes"]),
        "minimum_contrast": args.minimum,
        "measurements": measurements,
        "issues": issues,
        "pass": bool(matrix["themes"]) and not issues,
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("themes", "minimum_contrast", "issues", "pass")}, ensure_ascii=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
