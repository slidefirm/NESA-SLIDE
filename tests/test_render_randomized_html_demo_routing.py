from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RENDERER = PROJECT_ROOT / "scripts" / "render_randomized_html_demo.py"
MATRIX = PROJECT_ROOT / "artifacts" / "renderer-matrix" / "matrix.json"
PRESET_ID = "sepia-retail-case"
ROUTE_MATCH_LAYOUT = "cover-center-title-edge-decor"
ROUTE_MISMATCH_LAYOUT = "title-center"


def story_payload() -> dict[str, object]:
    return {
        "concept": {
            "story_id": "routing-contract-fixture",
            "visible_text_language": "en",
            "title": "CURRENT CONTENT TITLE",
            "subtitle": "Current content must remain independent from Layout fixtures.",
            "speaker": "ROUTING QA",
            "org": "FORMAL NEW-DECK",
            "toc": [
                ["Entry", "Define the content relation before choosing a Layout."],
                ["Route", "Select only a semantic candidate for the page intent."],
                ["Compose", "Bind page content after the scaffold is accepted."],
                ["Verify", "Reject route mismatches before rendering."],
                ["Record", "Keep explicit provenance in the manifest."],
                ["Close", "Preserve the accepted renderer contract."],
            ],
            "priorities": [
                ["Fail closed", "Reject semantic mismatches.", "NOW", "50%"],
                ["Keep content", "Do not read Layout-keyed copy.", "BUILD", "30%"],
                ["Record opt-in", "Mark historical compatibility.", "VERIFY", "20%"],
            ],
            "metrics": [
                ["100%", "ROUTE", "All forced routes match.", "+1"],
                ["0", "FALLBACK", "No silent fixture fallback.", "0"],
                ["1", "OPT-IN", "Compatibility is explicit.", "+1"],
            ],
            "timeline": [
                ["01", "Plan", "Resolve semantic intent."],
                ["02", "Route", "Check candidate membership."],
                ["03", "Compose", "Bind page content."],
                ["04", "Verify", "Write accepted output."],
            ],
            "quote": "A forced Layout is not permission to bypass semantic routing.",
            "attribution": "HTML ROUTING CONTRACT",
            "closing": ["Keep the route honest", "Reject mismatches before output."],
            "chapter_number": "01",
        },
        "content_plan": [
            {
                "page_id": "cover-01",
                "intent": "cover",
                "content_key": "cover",
                "source_fields": ["title", "subtitle", "speaker", "org"],
                "content_relation": "hero-claim",
            }
        ],
        "layout_content": {
            ROUTE_MATCH_LAYOUT: {
                "title": "LEGACY OVERRIDE TITLE",
                "subtitle": "This text is only legal after explicit compatibility opt-in.",
                "speaker": "LEGACY FIXTURE",
                "org": "HISTORICAL MANIFEST",
            }
        },
    }


def modules_story_payload(count: int) -> dict[str, object]:
    story = story_payload()
    priorities = [
        [
            f"MODULE {index:02d}",
            f"Module {index} remains independently readable in the fixed card slot.",
            f"M{index:02d}",
            f"{100 - index * 5}%",
        ]
        for index in range(1, count + 1)
    ]
    story["concept"]["priorities"] = priorities
    story["content_plan"] = [
        story["content_plan"][0],
        {
            "page_id": "modules-01",
            "intent": "modules",
            "content_key": "modules",
            "source_fields": ["priorities"],
            "content_relation": "module-roles",
        },
    ]
    return story


def distribution_story_payload(count: int) -> dict[str, object]:
    story = story_payload()
    story["concept"]["matrix"] = [
        [f"SIGNAL {index:02d}", f"Evidence {index} must remain in the rendered slide."]
        for index in range(1, count + 1)
    ]
    story["content_plan"] = [
        story["content_plan"][0],
        {
            "page_id": "distribution-01",
            "intent": "distribution",
            "content_key": "distribution",
            "source_fields": ["matrix"],
            "content_relation": "classified-signals",
        },
    ]
    return story


class RenderRandomizedHtmlDemoRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = (
            PROJECT_ROOT
            / "tests"
            / ".runtime"
            / f"render-routing-{uuid.uuid4().hex}"
        ).resolve()
        self.root.mkdir(parents=True)
        self.story_file = self.root / "story.json"
        self.story_file.write_text(
            json.dumps(story_payload(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def run_renderer(self, output: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(RENDERER),
                "--matrix",
                str(MATRIX),
                "--output",
                str(output),
                "--seed",
                "20260813",
                *args,
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )

    @staticmethod
    def load_manifest(output: Path) -> dict[str, object]:
        return json.loads(output.with_suffix(".manifest.json").read_text(encoding="utf-8"))

    def test_new_deck_rejects_forced_layout_route_mismatch(self) -> None:
        output = self.root / "route-mismatch.html"
        result = self.run_renderer(
            output,
            "--theme",
            PRESET_ID,
            "--story-file",
            str(self.story_file),
            "--layouts",
            ROUTE_MISMATCH_LAYOUT,
            "--content-mode",
            "new-deck",
            "--asset-policy",
            "pattern-only",
        )

        self.assertNotEqual(result.returncode, 0)
        error = result.stdout + result.stderr
        self.assertIn("Forced Layout route mismatch", error)
        self.assertIn("content_mode=new-deck", error)
        self.assertIn("route_match=false", error)
        self.assertIn("intent=cover", error)
        self.assertIn(f"layout={ROUTE_MISMATCH_LAYOUT}", error)
        self.assertFalse(output.exists())
        self.assertFalse(output.with_suffix(".manifest.json").exists())

    def test_new_deck_rejects_forced_layout_count_mismatch(self) -> None:
        output = self.root / "count-mismatch.html"
        result = self.run_renderer(
            output,
            "--theme",
            PRESET_ID,
            "--story-file",
            str(self.story_file),
            "--layouts",
            f"{ROUTE_MATCH_LAYOUT},{ROUTE_MATCH_LAYOUT}",
            "--content-mode",
            "new-deck",
            "--asset-policy",
            "pattern-only",
        )

        self.assertNotEqual(result.returncode, 0)
        error = result.stdout + result.stderr
        self.assertIn("content_mode=new-deck", error)
        self.assertIn("forced_layouts=2", error)
        self.assertIn("content_plan=1", error)
        self.assertFalse(output.exists())
        self.assertFalse(output.with_suffix(".manifest.json").exists())

    def test_story_file_does_not_auto_enable_legacy_layout_content(self) -> None:
        output = self.root / "new-deck.html"
        result = self.run_renderer(
            output,
            "--theme",
            PRESET_ID,
            "--story-file",
            str(self.story_file),
            "--layouts",
            ROUTE_MATCH_LAYOUT,
            "--content-mode",
            "new-deck",
            "--asset-policy",
            "pattern-only",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = self.load_manifest(output)
        self.assertTrue(all(item["route_match"] for item in manifest["layout_decisions"]))
        self.assertEqual(
            {item["composition_source"] for item in manifest["composition_plan"]},
            {"page-content-adapter"},
        )
        self.assertEqual(
            manifest["legacy_layout_content_compatibility"],
            {
                "enabled": False,
                "activation": "disabled",
                "manifest_marker": None,
                "preset_demo_isolated": False,
            },
        )
        html = output.read_text(encoding="utf-8")
        self.assertIn("CURRENT CONTENT TITLE", html)
        self.assertNotIn("LEGACY OVERRIDE TITLE", html)

    def test_new_deck_rejects_legacy_layout_content_opt_in(self) -> None:
        output = self.root / "legacy-opt-in.html"
        result = self.run_renderer(
            output,
            "--theme",
            PRESET_ID,
            "--story-file",
            str(self.story_file),
            "--layouts",
            ROUTE_MATCH_LAYOUT,
            "--content-mode",
            "new-deck",
            "--asset-policy",
            "pattern-only",
            "--allow-legacy-layout-content",
        )

        self.assertNotEqual(result.returncode, 0)
        error = result.stdout + result.stderr
        self.assertIn("cannot be combined", error)
        self.assertIn("content_mode=new-deck", error)
        self.assertFalse(output.exists())
        self.assertFalse(output.with_suffix(".manifest.json").exists())

    def test_explicit_empty_page_compositions_fails_closed(self) -> None:
        payload = story_payload()
        payload["page_compositions"] = {}
        self.story_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output = self.root / "empty-page-compositions.html"
        result = self.run_renderer(
            output,
            "--theme", PRESET_ID,
            "--story-file", str(self.story_file),
            "--layouts", ROUTE_MATCH_LAYOUT,
            "--content-mode", "new-deck",
            "--asset-policy", "pattern-only",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("page_compositions but it is empty", result.stdout + result.stderr)
        self.assertFalse(output.exists())

    def test_explicit_page_compositions_must_cover_every_content_plan_page(self) -> None:
        payload = modules_story_payload(3)
        payload["page_compositions"] = {
            "cover-01": {"title": "Explicit cover", "subtitle": "One authored page is not enough."}
        }
        self.story_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output = self.root / "partial-page-compositions.html"
        result = self.run_renderer(
            output,
            "--theme", PRESET_ID,
            "--story-file", str(self.story_file),
            "--layouts", f"{ROUTE_MATCH_LAYOUT},cards-1-plus-3",
            "--content-mode", "new-deck",
            "--asset-policy", "pattern-only",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing content-plan pages: modules-01", result.stdout + result.stderr)
        self.assertFalse(output.exists())

    def test_modules_adapter_matches_all_supported_low_level_capacities(self) -> None:
        for count in (2, 3, 4, 5, 6, 8):
            with self.subTest(count=count):
                self.story_file.write_text(
                    json.dumps(modules_story_payload(count), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                output = self.root / f"modules-{count}.html"
                result = self.run_renderer(
                    output,
                    "--theme",
                    PRESET_ID,
                    "--story-file",
                    str(self.story_file),
                    "--layouts",
                    f"{ROUTE_MATCH_LAYOUT},cards-1-plus-{count}",
                    "--content-mode",
                    "new-deck",
                    "--asset-policy",
                    "pattern-only",
                )

                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                manifest = self.load_manifest(output)
                self.assertEqual(manifest["composition_plan"][1]["rendered_item_count"], count)
                html = output.read_text(encoding="utf-8")
                if count == 3:
                    # cards-1-plus-3 has a dedicated renderer variant with
                    # three separately editable surfaces, rather than the
                    # old generic module-card aggregate.
                    self.assertNotIn('data-edit-composite="module-card-3"', html)
                    for index in range(1, 4):
                        self.assertIn(
                            f'data-edit-composite="cards-1plus3-{index}"',
                            html,
                        )
                else:
                    self.assertIn(
                        f'data-edit-composite="module-card-{count}"',
                        html,
                    )

    def test_modules_adapter_reroutes_to_capacity_layout_without_truncating_items(self) -> None:
        count = 5
        self.story_file.write_text(
            json.dumps(modules_story_payload(count), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        output = self.root / "modules-over-capacity.html"
        result = self.run_renderer(
            output,
            "--theme",
            PRESET_ID,
            "--story-file",
            str(self.story_file),
            "--layouts",
            f"{ROUTE_MATCH_LAYOUT},cards-1-plus-4",
            "--content-mode",
            "new-deck",
            "--asset-policy",
            "pattern-only",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = self.load_manifest(output)
        decision = manifest["layout_decisions"][1]
        composition = manifest["composition_plan"][1]
        self.assertEqual(decision["requested_layout_id"], "cards-1-plus-4")
        self.assertEqual(decision["layout_id"], "cards-1-plus-5")
        self.assertEqual(decision["selection_basis"], "content-preserving-capacity-reroute")
        self.assertEqual(composition["input_item_count"], 5)
        self.assertEqual(composition["rendered_item_count"], 5)
        self.assertFalse(composition["content_mutated"])
        html = output.read_text(encoding="utf-8")
        for index in range(1, 6):
            self.assertIn(f"MODULE {index:02d}", html)

    def test_five_distribution_items_reroute_from_matrix_to_one_plus_five(self) -> None:
        self.story_file.write_text(
            json.dumps(distribution_story_payload(5), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        output = self.root / "distribution-five.html"
        result = self.run_renderer(
            output,
            "--theme",
            PRESET_ID,
            "--story-file",
            str(self.story_file),
            "--layouts",
            f"{ROUTE_MATCH_LAYOUT},matrix-4quadrant",
            "--content-mode",
            "new-deck",
            "--asset-policy",
            "pattern-only",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = self.load_manifest(output)
        decision = manifest["layout_decisions"][1]
        composition = manifest["composition_plan"][1]
        self.assertEqual(decision["layout_id"], "cards-1-plus-5", decision)
        self.assertIn("requested_layout_id", decision, decision)
        self.assertEqual(decision["requested_layout_id"], "matrix-4quadrant")
        self.assertEqual(composition["input_item_count"], 5)
        self.assertEqual(composition["rendered_item_count"], 5)
        self.assertFalse(composition["content_mutated"])
        html = output.read_text(encoding="utf-8")
        for index in range(1, 6):
            self.assertIn(f"SIGNAL {index:02d}", html)

    def test_explicit_integration_sets_content_mutated_and_keeps_ledger(self) -> None:
        story = distribution_story_payload(4)
        story["page_compositions"] = {
            "cover-01": {
                "title": story["concept"]["title"],
                "subtitle": story["concept"]["subtitle"],
                "speaker": story["concept"]["speaker"],
                "org": story["concept"]["org"],
            },
            "distribution-01": {
                "title": "授權整合後的四象限",
                "matrix": story["concept"]["matrix"],
                "mutation_ledger": [
                    {
                        "operation": "merge-related-evidence",
                        "authorization": "user-explicit",
                        "source_items": ["A", "B"],
                        "result_item": "A+B",
                    }
                ],
            }
        }
        self.story_file.write_text(
            json.dumps(story, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        output = self.root / "distribution-authorized-mutation.html"
        result = self.run_renderer(
            output,
            "--theme",
            PRESET_ID,
            "--story-file",
            str(self.story_file),
            "--layouts",
            f"{ROUTE_MATCH_LAYOUT},matrix-4quadrant",
            "--content-mode",
            "new-deck",
            "--asset-policy",
            "pattern-only",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        composition = self.load_manifest(output)["composition_plan"][1]
        self.assertTrue(composition["content_mutated"])
        self.assertFalse(composition["content_identity_preserved"])
        self.assertEqual(composition["mutation_ledger"][0]["authorization"], "user-explicit")

    def test_preset_demo_keeps_isolated_fixture_behavior(self) -> None:
        output = self.root / "preset-demo.html"
        result = self.run_renderer(
            output,
            "--preset-demo",
            PRESET_ID,
            "--content-mode",
            "preset-demo",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = self.load_manifest(output)
        self.assertEqual(manifest["content_mode"], "preset-demo")
        self.assertTrue(manifest["preset_theme"]["legacy_case_imported"])
        self.assertTrue(manifest["legacy_layout_content_compatibility"]["preset_demo_isolated"])
        self.assertFalse(manifest["legacy_layout_content_compatibility"]["enabled"])
        self.assertEqual(
            {item["composition_source"] for item in manifest["composition_plan"]},
            {"preset-demo-layout-fixture"},
        )

    def test_preset_root_declares_resolved_none_background_pattern_for_browser_qa(self) -> None:
        output = self.root / "signal-route-atlas-pattern-only.html"
        result = self.run_renderer(
            output,
            "--theme",
            "signal-route-atlas",
            "--story-file",
            str(self.story_file),
            "--layouts",
            ROUTE_MATCH_LAYOUT,
            "--content-mode",
            "new-deck",
            "--asset-policy",
            "pattern-only",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        html = output.read_text(encoding="utf-8")
        manifest = self.load_manifest(output)
        self.assertIn('data-preset-theme="signal-route-atlas"', html)
        self.assertIn('data-background-pattern="none"', html)
        self.assertEqual(manifest["preset_theme"]["background_pattern"], "none")


if __name__ == "__main__":
    unittest.main()
