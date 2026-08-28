from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from migrate_html_typography_floor import migrate_text  # noqa: E402


class TypographyMigrationTests(unittest.TestCase):
    def test_body_title_and_page_title_keep_distinct_floors(self) -> None:
        source = (
            ".card>p{font:500 20px/1.4 sans-serif}"
            ".card>b{font-size:30px}"
            ".prod-title{font:800 48px/1 sans-serif}"
        )
        migrated, changes = migrate_text(source)
        self.assertIn("36px", migrated)
        self.assertIn("42px", migrated)
        self.assertIn("52px", migrated)
        self.assertEqual(len(changes), 3)

    def test_existing_larger_type_is_preserved(self) -> None:
        source = ".card>b{font-size:58px}.card>p{font-size:40px}"
        migrated, changes = migrate_text(source)
        self.assertEqual(migrated, source)
        self.assertEqual(changes, [])


if __name__ == "__main__":
    unittest.main()
