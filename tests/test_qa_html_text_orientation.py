from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import qa_html_text_orientation as audit  # noqa: E402


class HtmlTextOrientationAuditTests(unittest.TestCase):
    def test_horizontal_text_passes(self) -> None:
        self.assertEqual(
            audit.scan_text(
                "<style>.label{writing-mode:horizontal-tb;transform:none}</style>",
                path_label="valid.html",
            ),
            [],
        )

    def test_vertical_writing_mode_fails(self) -> None:
        issues = audit.scan_text(
            "<style>.label{writing-mode:vertical-rl}</style>",
            path_label="invalid.html",
        )
        self.assertEqual([issue["kind"] for issue in issues], ["vertical-writing-mode"])

    def test_right_angle_rotation_fails(self) -> None:
        issues = audit.scan_text(
            ".label{transform:rotate(-90deg)}",
            path_label="invalid.css",
        )
        self.assertEqual([issue["kind"] for issue in issues], ["right-angle-text-rotation"])

    def test_inline_svg_text_right_angle_rotation_fails(self) -> None:
        issues = audit.scan_text(
            '<svg><text transform="rotate(-90 54 298)">指標值（0–100）</text></svg>',
            path_label="invalid-inline-chart.html",
        )
        self.assertEqual(
            [issue["kind"] for issue in issues],
            ["svg-text-right-angle-rotation"],
        )


if __name__ == "__main__":
    unittest.main()
