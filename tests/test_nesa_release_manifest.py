from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml

from scripts.build_nesa_release import (
    UniqueKeyLoader,
    read_relevant_tests,
    read_yaml,
    validate_package_manifest,
)
from scripts import html_image_background_experiment


class ReleaseManifestValidationTests(unittest.TestCase):
    def test_current_profiles_are_explicit_nonempty_mappings(self) -> None:
        manifest = read_yaml(Path("release/package-manifest.yaml"))
        for profile in ("source", "portable"):
            data, excludes = validate_package_manifest(manifest, profile)
            self.assertGreater(len(data["include_roots"]), 0)
            self.assertIsInstance(excludes, list)
            self.assertEqual(data["workspace"]["path"], "workspace")

    def test_missing_profile_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "portable_profile"):
            validate_package_manifest(
                {
                    "schema_version": 1,
                    "source_profile": {"include_roots": ["README.md"], "exclude_globs": [], "workspace": {"path": "workspace"}},
                },
                "source",
            )

    def test_empty_include_roots_is_rejected(self) -> None:
        manifest = {
            "schema_version": 1,
            "source_profile": {"include_roots": [], "exclude_globs": [], "workspace": {"path": "workspace"}},
            "portable_profile": {"include_roots": ["README.md"], "exclude_globs": [], "workspace": {"path": "workspace"}},
        }
        with self.assertRaisesRegex(ValueError, "include_roots"):
            validate_package_manifest(manifest, "source")

    def test_duplicate_yaml_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate YAML key"):
            yaml.load("schema_version: 1\nschema_version: 1\n", Loader=UniqueKeyLoader)

    def test_background_runtime_uses_workspace_output_root(self) -> None:
        self.assertEqual(
            html_image_background_experiment.EXPERIMENT_ROOT,
            html_image_background_experiment.ROOT / "workspace" / "html-image-background",
        )

    def test_source_release_test_inventory_is_explicit_and_portable_is_test_free(self) -> None:
        manifest = read_yaml(Path("release/package-manifest.yaml"))
        declared = set(read_relevant_tests())
        source_entries = set(manifest["source_profile"]["include_roots"])
        portable_entries = set(manifest["portable_profile"]["include_roots"])
        self.assertNotIn("tests", source_entries)
        self.assertEqual({entry for entry in source_entries if entry.startswith("tests/")}, declared)
        self.assertFalse({entry for entry in portable_entries if entry.startswith("tests/")})

    def test_runtime_contract_declares_selected_python_and_coded_node_boundary(self) -> None:
        capabilities = __import__("json").loads(Path("release/external-capabilities.json").read_text(encoding="utf-8"))
        runtime = capabilities["runtime_contract"]
        self.assertEqual(runtime["python"]["pyyaml_version"], "6.0.3")
        self.assertFalse(runtime["python"]["bundled_python_sufficient"])
        self.assertFalse(runtime["node"]["system_node_allowed"])
        self.assertEqual(runtime["verification_script"], "CHECK_SYSTEM.ps1")
        check_source = Path("CHECK_SYSTEM.ps1").read_text(encoding="utf-8")
        self.assertIn("RUNTIME_NODE", check_source)
        self.assertIn("RUNTIME_NODE_MODULES", check_source)
        self.assertIn("RUNTIME_BIN_DIR", check_source)
        self.assertIn("PyYAML 6.0.3", check_source)

    def test_showcase_manifest_records_four_formal_cases_with_portable_paths(self) -> None:
        manifest = json.loads(Path("release/showcase-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 2)
        self.assertEqual(len(manifest["showcases"]), 4)
        self.assertTrue(all(item["page_count"] == 10 for item in manifest["showcases"]))
        for item in manifest["showcases"]:
            rendered = json.dumps(item, ensure_ascii=False)
            self.assertTrue(item["delivery_path"].startswith("showcase/"))
            self.assertNotIn("C:\\", rendered)
            self.assertNotIn("file:///", rendered)
            self.assertTrue(item["runtime_hashes"])
        d_case = next(item for item in manifest["showcases"] if item["id"].startswith("D-"))
        self.assertEqual(d_case["qa_status"], "pass-with-disclosed-external-tool-limitation")


if __name__ == "__main__":
    unittest.main()
