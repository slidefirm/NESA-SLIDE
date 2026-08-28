import hashlib
from pathlib import Path
import sys
import unittest
import uuid


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from generate_renderer_adapters import source_sha256


class SourceHashLineEndingTests(unittest.TestCase):
    def test_source_hash_normalizes_crlf_and_lone_cr_to_lf(self) -> None:
        fixture = PROJECT_ROOT / "workspace" / f".tmp-source-hash-{uuid.uuid4().hex}.yaml"
        try:
            fixture.write_bytes(b"first\r\nsecond\rthird\n")

            expected = hashlib.sha256(b"first\nsecond\nthird\n").hexdigest()
            self.assertEqual(source_sha256(fixture), expected)
        finally:
            fixture.unlink(missing_ok=True)
