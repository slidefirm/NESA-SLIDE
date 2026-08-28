import hashlib
import json
from pathlib import Path
import subprocess
import unittest
import uuid


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "qa_html_text_geometry.cjs"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def remove_if_present(path: Path) -> None:
    path.unlink(missing_ok=True)


def temporary_test_path(label: str, suffix: str) -> Path:
    token = uuid.uuid4().hex
    return Path(__file__).resolve().parent / f".tmp-text-geometry-{label}-{token}{suffix}"


def fixture(body: str) -> str:
    return f"""<!doctype html>
<html lang="en" data-layout-ready="true">
<head>
  <meta charset="utf-8">
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; width: 100%; height: 100%; }}
    #stage {{ position: relative; width: 1920px; height: 1080px; }}
    .slide {{ position: absolute; inset: 0; width: 1920px; height: 1080px; }}
    .metric-kpi-card {{ position: absolute; left: 100px; top: 100px; width: 500px; height: 240px; }}
    [data-edit-layer="background"] {{ position: absolute; inset: 0; border: 1px solid black; }}
    [data-edit-layer="text"], [data-edit-layer="metric"] {{ position: absolute; margin: 0; font: 32px/1 Arial, sans-serif; white-space: nowrap; }}
    .good-title {{ left: 24px; top: 24px; }}
    .good-body {{ left: 24px; top: 104px; }}
    .bad-overlap-a {{ left: 20px; top: 20px; }}
    .bad-overlap-b {{ left: 28px; top: 24px; }}
    .bad-outside {{ left: 460px; top: 190px; }}
  </style>
</head>
<body>
  <div id="stage">
    <section class="slide" data-page-number="1" data-layout-id="fixture-layout">
      {body}
    </section>
  </div>
</body>
</html>
"""


GOOD_MODULE = """
<article class="metric-kpi-card" data-edit-structure="module" data-edit-composite="good-card">
  <div data-edit-layer="background"></div>
  <strong class="good-title" data-edit-layer="text">Readable title</strong>
  <p class="good-body" data-edit-layer="text">Body stays inside its card.</p>
</article>
"""


BAD_MODULE = """
<article class="metric-kpi-card" data-edit-structure="module" data-edit-composite="bad-card">
  <div data-edit-layer="background"></div>
  <strong class="bad-overlap-a" data-edit-layer="text">OVERLAP</strong>
  <span class="bad-overlap-b" data-edit-layer="metric">12345</span>
  <p class="bad-outside" data-edit-layer="text">OUTSIDE</p>
</article>
"""


class HtmlTextGeometryGateTests(unittest.TestCase):
    maxDiff = None

    def run_gate(self, html: Path, report: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["node", str(SCRIPT), "--file", str(html), "--report", str(report)],
            cwd=PROJECT_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=120,
            check=False,
        )

    def test_good_fixture_passes_and_input_hash_is_unchanged(self) -> None:
        html = temporary_test_path("good", ".html")
        report = temporary_test_path("good-report", ".json")
        self.addCleanup(remove_if_present, report)
        self.addCleanup(remove_if_present, html)
        html.write_text(fixture(GOOD_MODULE), encoding="utf-8")
        before = sha256(html)

        completed = self.run_gate(html, report)

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertEqual(sha256(html), before)
        payload = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["fileSha256"], before)
        self.assertEqual(payload["fileSha256After"], before)
        self.assertTrue(payload["inputUnchanged"])
        self.assertEqual(payload["checks"]["textOutsideModule"], 0)
        self.assertEqual(payload["checks"]["textLayerOverlap"], 0)
        self.assertEqual(payload["issues"], [])

    def test_overflow_and_overlap_fixture_fails_without_changing_input(self) -> None:
        html = temporary_test_path("bad", ".html")
        report = temporary_test_path("bad-report", ".json")
        self.addCleanup(remove_if_present, report)
        self.addCleanup(remove_if_present, html)
        html.write_text(fixture(BAD_MODULE), encoding="utf-8")
        before = sha256(html)

        completed = self.run_gate(html, report)

        self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
        self.assertEqual(sha256(html), before)
        payload = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "fail")
        self.assertTrue(payload["inputUnchanged"])
        contracts = {issue["contract"] for issue in payload["issues"]}
        self.assertEqual(contracts, {"text-outside-module", "text-layer-overlap"})
        self.assertGreaterEqual(payload["checks"]["textOutsideModule"], 1)
        self.assertGreaterEqual(payload["checks"]["textLayerOverlap"], 1)
        for issue in payload["issues"]:
            self.assertEqual(issue["page"], "1")
            self.assertEqual(issue["layout"], "fixture-layout")
            self.assertEqual(issue["composite"], "bad-card")
            self.assertIn("module", issue["selectors"])
            self.assertIn("primary", issue["selectors"])
            self.assertIn("primary", issue["summaries"])
            self.assertIn("module", issue["rects"])
            self.assertIn("primaryGlyph", issue["rects"])
        overlap_issue = next(issue for issue in payload["issues"] if issue["contract"] == "text-layer-overlap")
        self.assertGreater(overlap_issue["overlap"]["x"], 2)
        self.assertGreater(overlap_issue["overlap"]["y"], 2)

    def test_runtime_error_uses_exit_code_two(self) -> None:
        missing = temporary_test_path("missing", ".html")
        report = temporary_test_path("runtime-report", ".json")
        self.addCleanup(remove_if_present, report)

        completed = self.run_gate(missing, report)

        self.assertEqual(completed.returncode, 2)
        payload = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "runtime-error")


if __name__ == "__main__":
    unittest.main()
