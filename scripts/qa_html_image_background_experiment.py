#!/usr/bin/env python3
"""Focused regression tests for html_image_background_experiment.py."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import html_image_background_experiment as experiment
from html_css_ownership import validate_html_document_text

ROOT = Path(__file__).resolve().parents[1]
BROWSER_CASCADE_QA = ROOT / "scripts" / "qa_html_image_background_cascade.cjs"


def _nonportable_manifest_strings(value: object, location: str = "run") -> list[str]:
    issues: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            issues.extend(_nonportable_manifest_strings(item, f"{location}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            issues.extend(_nonportable_manifest_strings(item, f"{location}[{index}]"))
    elif isinstance(value, str):
        if (
            value.lower().startswith("file:///")
            or re.match(r"^[A-Za-z]:[\\/]", value)
            or Path(value).is_absolute()
        ):
            issues.append(f"{location}: absolute {value!r}")
        if "\\" in value:
            issues.append(f"{location}: backslash {value!r}")
    return issues


def _selector_specificity(selector: str) -> tuple[int, int, int]:
    """Small specificity parser for the intentionally simple regression selectors."""
    without_strings = re.sub(r"(['\"]).*?\1", "", selector)
    id_count = len(re.findall(r"(?<!\\)#[A-Za-z0-9_-]+", without_strings))
    class_or_attribute_count = len(re.findall(r"(?<!\\)\.[A-Za-z0-9_-]+", without_strings))
    class_or_attribute_count += len(re.findall(r"\[[^\]]+\]", without_strings))
    type_count = len(
        re.findall(
            r"(?:^|[\s>+~])([A-Za-z][A-Za-z0-9_-]*)",
            re.sub(r"\[[^\]]+\]", "", without_strings),
        )
    )
    return id_count, class_or_attribute_count, type_count


def _style_rule_selector(html: str, style_id: str) -> str:
    style_match = re.search(
        rf'<style\b(?=[^>]*\bid="{re.escape(style_id)}")[^>]*>(.*?)</style\s*>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if not style_match:
        raise AssertionError(f"Missing style block: {style_id}")
    css = re.sub(r"/\*.*?\*/", "", style_match.group(1), flags=re.DOTALL)
    rule_match = re.search(r"([^{}]+)\{", css, re.DOTALL)
    if not rule_match:
        raise AssertionError(f"Missing CSS rule in style block: {style_id}")
    return rule_match.group(1).strip()


def _css_declarations(body: str) -> list[str]:
    """Split declarations without treating data-URL semicolons as separators."""
    declarations: list[str] = []
    start = 0
    quote: str | None = None
    escaped = False
    parenthesis_depth = 0
    for index, char in enumerate(body):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "(":
            parenthesis_depth += 1
        elif char == ")" and parenthesis_depth:
            parenthesis_depth -= 1
        elif char == ";" and parenthesis_depth == 0:
            declaration = body[start:index].strip()
            if declaration:
                declarations.append(declaration)
            start = index + 1
    tail = body[start:].strip()
    if tail:
        declarations.append(tail)
    return declarations


def _css_declaration_value(body: str, property_name: str) -> str | None:
    for declaration in _css_declarations(body):
        if ":" not in declaration:
            continue
        name, value = declaration.split(":", 1)
        if name.strip().lower() == property_name.lower():
            return value.strip()
    return None


def _fixture_background_winner(html: str) -> tuple[str, str, tuple[int, int, int]]:
    """Resolve background-image for the fixture using specificity then source order."""
    candidates = []
    source_order = 0
    for style_match in re.finditer(r"<style\b[^>]*>(.*?)</style\s*>", html, re.IGNORECASE | re.DOTALL):
        css = re.sub(r"/\*.*?\*/", "", style_match.group(1), flags=re.DOTALL)
        for rule_match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css, re.DOTALL):
            background_image = _css_declaration_value(rule_match.group(2), "background-image")
            if background_image is None:
                continue
            for selector in rule_match.group(1).split(","):
                selector = selector.strip()
                if "slide" not in selector or "#other" in selector:
                    continue
                source_order += 1
                candidates.append(
                    (
                        _selector_specificity(selector),
                        source_order,
                        selector,
                        background_image,
                    )
                )
    if not candidates:
        raise AssertionError("No matching background-image declarations found")
    specificity, _, selector, value = max(candidates, key=lambda row: (row[0], row[1]))
    return selector, value, specificity


class HtmlImageBackgroundExperimentTests(unittest.TestCase):
    def setUp(self) -> None:
        external_root = os.environ.get("HTML_IMAGE_BACKGROUND_QA_ROOT")
        if external_root:
            case_slug = hashlib.sha256(self._testMethodName.encode("utf-8")).hexdigest()[:12]
            self.case_root = Path(external_root) / case_slug
            self.case_root.mkdir(parents=True, exist_ok=False)
            self.addCleanup(self._cleanup_case_root)
        else:
            self.temp_dir = tempfile.TemporaryDirectory(prefix="html-image-background-qa-")
            self.addCleanup(self.temp_dir.cleanup)
            self.case_root = Path(self.temp_dir.name)
        self.repository_root = self.case_root / "repository"
        self.repository_root.mkdir()
        self.root = self.repository_root / "html-image-background"
        self.root.mkdir(parents=True)
        self.original_root = experiment.ROOT
        self.original_experiment_root = experiment.EXPERIMENT_ROOT
        experiment.ROOT = self.repository_root
        experiment.EXPERIMENT_ROOT = self.root
        self.addCleanup(self._restore_roots)

    def _restore_roots(self) -> None:
        experiment.ROOT = self.original_root
        experiment.EXPERIMENT_ROOT = self.original_experiment_root

    def _cleanup_case_root(self) -> None:
        shutil.rmtree(self.case_root, ignore_errors=True)

    @staticmethod
    def _image(path: Path, size: tuple[int, int], color: str = "#f2efe5") -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", size, color).save(path)
        return path

    @staticmethod
    def _cascade_fixture_html() -> str:
        return f"""<!doctype html><html data-content-mode="new-deck" data-theme-kind="html-preset" data-preset-theme="cascade-fixture"><head>
<style data-css-owner="renderer-base">#stage{{width:1920px;height:1080px}}.slide{{width:1920px;height:1080px}}</style>
<style id="fixture-preset-background" data-css-owner="preset-appearance">
html[data-preset-theme="cascade-fixture"] body #stage > section.slide.preset-surface {{
  background-color: #122333;
  background-image: linear-gradient(#122333, #244566);
}}
</style>
{experiment.NEUTRAL_STYLE}
</head><body><main id="stage"><section class="slide preset-surface" id="s1" data-index="0" data-scene-role="cover" data-layout-id="cover-center-title-edge-decor" data-existing-metadata="preserve-me" data-pptx-background-image="false" data-pptx-background-image-src="./old.png" data-pptx-background-image-embedded="false"></section></main></body></html>"""

    def _prepared_apply_run(
        self,
        model_size: tuple[int, int],
        *,
        cascade_fixture: bool = False,
    ) -> tuple[Path, Path, Path]:
        run_dir = self.root / "apply-run"
        background_dir = self.root / "model-output"
        run_dir.mkdir(parents=True)
        background_dir.mkdir(parents=True)
        reference = self._image(run_dir / "reference.png", (1920, 1080))
        mask = self._image(run_dir / "mask.png", (1920, 1080), "white")
        model_output = self._image(background_dir / "slide-001.png", model_size, "#e9e4d8")
        neutral_html = self._cascade_fixture_html() if cascade_fixture else """<!doctype html><html><head>
<style data-css-owner="renderer-base">#stage{width:1920px;height:1080px}.slide{width:1920px;height:1080px}</style>
</head><body><main id="stage"><section class="slide" id="s1" data-index="0"></section></main></body></html>"""
        (run_dir / "neutral.html").write_text(neutral_html, encoding="utf-8")
        palette_contract = {
            "palette_tokens": {"--bg": "#F2EFE5", "--ink": "#102A36"},
            "foreground_colors": ["rgb(16, 42, 54)"],
            "minimum_contrast_ratios": {"normal_text": 4.5, "large_text": 3.0},
        }
        record = {
            "index": 0,
            "id": "s1",
            "scene_role": "cover",
            "layout_id": "cover-center-title-edge-decor",
            "source_reference": str(reference),
            "reference_screenshot": str(reference),
            "mask": str(mask),
            "palette_contrast_contract": palette_contract,
            "imagegen_inputs": [
                {
                    "order": 1,
                    "role": "actual-clean-foreground-screenshot",
                    "priority": "highest",
                    "path": str(reference),
                },
                {
                    "order": 2,
                    "role": "occupancy-mask-guidance-only",
                    "priority": "secondary",
                    "path": str(mask),
                },
            ],
            "generation_ready": True,
            "generation_mode": "texture-only",
            "post_generation_cutout": False,
        }
        (run_dir / "run.json").write_text(
            json.dumps({"slide_records": [record]}, indent=2),
            encoding="utf-8",
        )
        return run_dir, background_dir, model_output

    def _prepared_single_apply_run(self) -> tuple[Path, Path, Path]:
        run_dir = self.root / "single-apply-run"
        run_dir.mkdir(parents=True)
        background = self._image(self.root / "single-model-output.png", (1672, 941), "#e9e4d8")
        mask = self._image(run_dir / "protected-mask.png", (1920, 1080), "white")
        (run_dir / "neutral.html").write_text(self._cascade_fixture_html(), encoding="utf-8")
        (run_dir / "run.json").write_text(
            json.dumps({"mode": "html-image-background-experiment"}, indent=2),
            encoding="utf-8",
        )
        return run_dir, background, mask

    def test_prompt_contract_uses_ambient_material_and_fail_closed_rules(self) -> None:
        prompt = experiment.PER_SLIDE_PROMPT
        lowered = prompt.lower()
        self.assertIn("edge-to-edge ambient material", lowered)
        self.assertIn("image 1 is the actual clean foreground screenshot", lowered)
        self.assertIn("image 2 is the occupancy mask", lowered)
        self.assertIn("96px protected halo", lowered)
        self.assertIn("320x240px", lowered)
        self.assertIn("texture-only mode", lowered)
        self.assertIn("occupancy-mask shape", lowered)
        self.assertNotIn("background illustration", lowered)
        self.assertNotIn("main decorative detail", lowered)
        for forbidden in ("rings", "arcs", "grids", "compass", "cutouts", "blur patches"):
            self.assertIn(forbidden, lowered)
        for script in (
            experiment.MASK_SCRIPT,
            experiment.PER_SLIDE_MASK_SCRIPT,
            experiment.SINGLE_SLIDE_MASK_SCRIPT,
        ):
            self.assertIn("const GUARD = 96", script)
            self.assertIn("hasProtectedPseudo", script)
            self.assertIn("boxShadow", script)
            self.assertIn("textShadow", script)
            self.assertIn("outlineWidth", script)

    def test_photo_variant_requires_an_independent_semantic_image(self) -> None:
        photo_html = """<!doctype html><html><body><main id="stage">
<section class="slide" id="s1" data-image-variant="photo" data-photo-brief="在市場攤位前分類廚餘的店主">
  <img data-semantic-image="true" src="data:image/png;base64,AA==" alt="店主在市場攤位前分類廚餘">
</section></main></body></html>"""
        contract = experiment._semantic_photo_contract(
            photo_html,
            "s1",
            slide_number=1,
        )
        self.assertEqual(contract["image_variant"], "photo")
        self.assertEqual(contract["photo_brief"], "在市場攤位前分類廚餘的店主")
        self.assertEqual(
            contract["semantic_photos"],
            [{"alt": "店主在市場攤位前分類廚餘", "source_kind": "data-url"}],
        )

        missing_image_html = """<!doctype html><html><body><main id="stage">
<section class="slide" id="s1" data-image-variant="photo" data-photo-brief="市場店主"></section>
</main></body></html>"""
        with self.assertRaisesRegex(ValueError, "no independent"):
            experiment._semantic_photo_contract(
                missing_image_html,
                "s1",
                slide_number=1,
            )

    def test_raster_variant_rejects_a_semantic_image(self) -> None:
        valid_raster_html = """<!doctype html><html><body><main id="stage">
<section class="slide" id="s1" data-image-variant="raster"></section>
</main></body></html>"""
        self.assertEqual(
            experiment._semantic_photo_contract(
                valid_raster_html,
                "s1",
                slide_number=1,
            ),
            {"image_variant": "raster", "semantic_photos": []},
        )

        raster_html = """<!doctype html><html><body><main id="stage">
<section class="slide" id="s1" data-image-variant="raster">
  <img data-semantic-image="true" src="data:image/png;base64,AA==" alt="不應存在的插圖">
</section></main></body></html>"""
        with self.assertRaisesRegex(ValueError, "is Raster"):
            experiment._semantic_photo_contract(
                raster_html,
                "s1",
                slide_number=1,
            )

    def test_materialize_photo_page_records_independent_photo_contract(self) -> None:
        run_dir = self.root / "photo-materialize-run"
        run_dir.mkdir(parents=True)
        source = run_dir / "source.html"
        source.write_text(
            """<!doctype html><html><head><style>:root{--bg:#102E2B;--ink:#F4EBDD}</style></head>
<body><main id="stage"><section class="slide" id="s1" data-image-variant="photo"
data-photo-brief="市場攤位前分類廚餘的店主"><img data-semantic-image="true"
src="./semantic-photo.png" alt="店主在市場攤位前分類廚餘"></section></main></body></html>""",
            encoding="utf-8",
        )
        reference = self._image(run_dir / "clean-reference.png", (1920, 1080), "#102e2b")
        (run_dir / "run.json").write_text(
            json.dumps({"source_html": str(source)}),
            encoding="utf-8",
        )
        masks_path = run_dir / "masks.json"
        masks_path.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "index": 0,
                            "id": "s1",
                            "scene_role": "cover",
                            "layout_id": "cover-photo-frame",
                            "reference_screenshot": str(reference),
                            "measurement_guard_px": 96,
                            "measurement_uncertain": False,
                            "palette_tokens": {"--bg": "#102E2B", "--ink": "#F4EBDD"},
                            "foreground_colors": ["rgb(244, 235, 221)"],
                            "occupied_boxes": [{"x": 0, "y": 0, "w": 1920, "h": 1080}],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        experiment.materialize_deck(
            argparse.Namespace(run_dir=str(run_dir), masks_json=str(masks_path))
        )

        manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        record = manifest["slide_records"][0]
        self.assertEqual(record["image_variant"], "photo")
        self.assertEqual(
            record["semantic_photo_contract"]["photo_brief"],
            "市場攤位前分類廚餘的店主",
        )
        self.assertEqual(
            record["semantic_photo_contract"]["semantic_photos"],
            [{"alt": "店主在市場攤位前分類廚餘", "source_kind": "src"}],
        )
        prompt = experiment._resolve_manifest_path(
            record["prompt"],
            run_dir=run_dir,
            label="photo prompt",
        ).read_text(encoding="utf-8")
        self.assertIn("Photo-page contract", prompt)
        self.assertIn("Generate only the abstract Raster beneath it", prompt)

    def test_dense_or_uncertain_page_has_no_open_zone(self) -> None:
        dense = [{"x": 0, "y": 0, "w": 1920, "h": 1080}]
        self.assertEqual(
            experiment._candidate_open_zones(dense, measurement_uncertain=False),
            [],
        )
        sparse = [{"x": 0, "y": 0, "w": 1200, "h": 1080}]
        self.assertEqual(experiment._candidate_open_zones(sparse), [])
        verified = experiment._candidate_open_zones(sparse, measurement_uncertain=False)
        self.assertTrue(any(zone["w"] >= 320 and zone["h"] >= 240 for zone in verified))

    def test_materialize_records_reference_before_mask_and_profile_2b_fallback(self) -> None:
        run_dir = self.root / "materialize-run"
        run_dir.mkdir(parents=True)
        source = run_dir / "source.html"
        source.write_text(
            '<html><head><style>:root{--bg:#102E2B;--ink:#F4EBDD;--muted:#B7C4BD}</style></head></html>',
            encoding="utf-8",
        )
        reference = self._image(run_dir / "clean-reference.png", (1920, 1080), "#102e2b")
        (run_dir / "run.json").write_text(
            json.dumps({"source_html": str(source)}),
            encoding="utf-8",
        )
        masks = {
            "records": [
                {
                    "index": 0,
                    "id": "s1",
                    "scene_role": "cover",
                    "layout_id": "title-center",
                    "reference_screenshot": str(reference),
                    "measurement_guard_px": 96,
                    "measurement_uncertain": False,
                    "palette_tokens": {"--bg": "#102E2B", "--ink": "#F4EBDD"},
                    "foreground_colors": ["rgb(244, 235, 221)"],
                    "occupied_boxes": [{"x": 0, "y": 0, "w": 1920, "h": 1080}],
                }
            ]
        }
        masks_path = run_dir / "masks.json"
        masks_path.write_text(json.dumps(masks), encoding="utf-8")

        experiment.materialize_deck(
            argparse.Namespace(run_dir=str(run_dir), masks_json=str(masks_path))
        )

        manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        record = manifest["slide_records"][0]
        self.assertEqual(record["generation_mode"], "profile-2b-plus-low-frequency-material")
        self.assertEqual(record["open_zone_candidates"], [])
        self.assertEqual(record["measurement_guard_px"], 96)
        self.assertFalse(record["post_generation_cutout"])
        self.assertEqual(
            [row["role"] for row in record["imagegen_inputs"]],
            ["actual-clean-foreground-screenshot", "occupancy-mask-guidance-only"],
        )
        self.assertEqual(record["scene_role"], "cover")
        self.assertEqual(record["palette_contrast_contract"]["palette_tokens"]["--bg"], "#102E2B")
        prompt = experiment._resolve_manifest_path(
            record["prompt"],
            run_dir=run_dir,
            label="test prompt",
        ).read_text(encoding="utf-8")
        self.assertLess(prompt.index("Image 1 source"), prompt.index("Image 2 source"))
        self.assertIn("none; use the profile 2B edge/corner/seam zones only", prompt)

    def test_materialize_apply_and_resume_write_only_portable_manifest_paths(self) -> None:
        source_dir = self.repository_root / "source"
        source_dir.mkdir()
        source = source_dir / "deck.html"
        source.write_text(
            """<!doctype html><html><head><style>:root{--bg:#102E2B;--ink:#F4EBDD}</style></head>
<body><main id="stage"><section class="slide" id="s1" data-index="0"></section></main></body></html>""",
            encoding="utf-8",
        )
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        run_dir = self.root / "portable-roundtrip"
        experiment.prepare_deck(
            argparse.Namespace(input=str(source), run_dir=str(run_dir))
        )

        # Exercise legacy run.json and capture payload input while requiring all
        # subsequent writes to migrate to the portable contract.
        prepared = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        prepared["source_html"] = str(source.resolve())
        (run_dir / "run.json").write_text(json.dumps(prepared), encoding="utf-8")
        reference = self._image(run_dir / "references" / "legacy-reference.png", (1920, 1080), "#102e2b")
        masks_path = run_dir / "masks.json"
        masks_path.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "index": 0,
                            "id": "s1",
                            "scene_role": "cover",
                            "layout_id": "title-center",
                            "source_reference": str(reference.resolve()),
                            "reference_screenshot": str(reference.resolve()),
                            "measurement_guard_px": 96,
                            "measurement_uncertain": False,
                            "palette_tokens": {"--bg": "#102E2B", "--ink": "#F4EBDD"},
                            "foreground_colors": ["rgb(244, 235, 221)"],
                            "occupied_boxes": [{"x": 0, "y": 0, "w": 1920, "h": 1080}],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        experiment.materialize_deck(
            argparse.Namespace(run_dir=str(run_dir), masks_json=str(masks_path))
        )

        external_model_dir = self.case_root / "external-model"
        external_model_dir.mkdir()
        external_model = self._image(
            external_model_dir / "slide-001.png",
            (1672, 941),
            "#e9e4d8",
        )
        apply_args = argparse.Namespace(
            run_dir=str(run_dir),
            background_dir=str(external_model.parent),
        )
        experiment.apply_deck(apply_args)
        experiment.apply_deck(apply_args)  # Resume from the newly portable run.json.

        manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(_nonportable_manifest_strings(manifest), [])
        self.assertEqual(
            manifest["path_contract"],
            {
                "base": "repository-root",
                "format": "repository-relative-posix",
                "external_paths_recorded": False,
            },
        )
        record = manifest["slide_records"][0]
        self.assertNotIn("source_path", record["model_output_provenance"])
        self.assertEqual(
            record["model_output_provenance"]["external_source"]["basename"],
            "slide-001.png",
        )
        self.assertEqual(
            record["preserved_model_output"]["external_source"]["basename"],
            "slide-001.png",
        )
        self.assertTrue(
            experiment._resolve_manifest_path(
                record["background"],
                run_dir=run_dir,
                label="portable background",
            ).is_file()
        )
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), source_hash)

    def test_invalid_aspect_ratio_is_rejected_before_copy_or_final(self) -> None:
        run_dir, background_dir, _ = self._prepared_apply_run((1600, 1000))
        with self.assertRaisesRegex(ValueError, "expected 16:9"):
            experiment.apply_deck(
                argparse.Namespace(run_dir=str(run_dir), background_dir=str(background_dir))
            )
        self.assertFalse((run_dir / "final.html").exists())
        self.assertFalse((run_dir / "backgrounds").exists())

    def test_model_native_raster_is_embedded_offline_with_provenance(self) -> None:
        run_dir, background_dir, model_output = self._prepared_apply_run((1672, 941))
        source_hash = hashlib.sha256(model_output.read_bytes()).hexdigest()
        experiment.apply_deck(
            argparse.Namespace(run_dir=str(run_dir), background_dir=str(background_dir))
        )

        final_html = (run_dir / "final.html").read_text(encoding="utf-8")
        self.assertIn('data-pptx-background-image="true"', final_html)
        self.assertIn('data-pptx-background-image-embedded="true"', final_html)
        self.assertIn('data-pptx-background-image-src="./backgrounds/slide-001.png"', final_html)
        self.assertIn('background-image: url("data:image/png;base64,', final_html)
        self.assertIn("background-size: contain", final_html)
        self.assertNotIn("!important", final_html)
        self.assertNotIn('background-image: url("./backgrounds/', final_html)
        data_match = re.search(r'background-image: url\("data:image/png;base64,([^"\)]+)', final_html)
        self.assertIsNotNone(data_match)
        embedded_hash = hashlib.sha256(base64.b64decode(data_match.group(1))).hexdigest()
        self.assertEqual(embedded_hash, source_hash)
        self.assertEqual(validate_html_document_text(final_html), [])

        manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        record = manifest["slide_records"][0]
        provenance = record["model_output_provenance"]
        self.assertEqual(provenance["dimensions"], {"width": 1672, "height": 941})
        self.assertEqual(provenance["sha256"], source_hash)
        self.assertLessEqual(
            provenance["aspect_ratio_relative_error"],
            provenance["aspect_ratio_tolerance"],
        )
        self.assertEqual(record["scene_role"], "cover")
        self.assertTrue(
            experiment._resolve_manifest_path(
                record["source_reference"], run_dir=run_dir, label="source reference"
            ).is_file()
        )
        self.assertTrue(
            experiment._resolve_manifest_path(
                record["mask"], run_dir=run_dir, label="mask"
            ).is_file()
        )
        self.assertEqual(_nonportable_manifest_strings(manifest), [])
        self.assertIn("palette_tokens", record["palette_contrast_contract"])
        self.assertFalse(record["post_generation_cutout"])
        self.assertEqual(record["slide_mapping"]["method"], "css-uniform-contain")
        self.assertFalse(record["slide_mapping"]["crop"])
        self.assertFalse(record["slide_mapping"]["non_uniform_stretch"])
        self.assertFalse(record["slide_mapping"]["content_reconstruction"])
        self.assertFalse(record["slide_mapping"]["adapted_copy_created"])
        self.assertFalse(manifest["post_generation_cutout"])

    def test_apply_deck_final_selector_wins_neutral_and_preset_cascade(self) -> None:
        run_dir, background_dir, _ = self._prepared_apply_run(
            (1672, 941),
            cascade_fixture=True,
        )
        experiment.apply_deck(
            argparse.Namespace(run_dir=str(run_dir), background_dir=str(background_dir))
        )

        final_html = (run_dir / "final.html").read_text(encoding="utf-8")
        final_selector = _style_rule_selector(
            final_html,
            "html-image-background-per-slide-experiment-final",
        )
        neutral_selector = "html body #stage > section.slide"
        preset_selector = 'html[data-preset-theme="cascade-fixture"] body #stage > section.slide.preset-surface'
        self.assertEqual(final_selector, "html body #stage > section.slide#s1")
        self.assertGreater(_selector_specificity(final_selector), _selector_specificity(neutral_selector))
        self.assertGreater(_selector_specificity(final_selector), _selector_specificity(preset_selector))
        winner_selector, winner_value, _ = _fixture_background_winner(final_html)
        self.assertEqual(winner_selector, final_selector)
        self.assertTrue(winner_value.startswith('url("data:image/png;base64,'))
        self.assertEqual(validate_html_document_text(final_html), [])

        slide_tag = re.search(r'<section\b[^>]*\bid="s1"[^>]*>', final_html, re.IGNORECASE)
        self.assertIsNotNone(slide_tag)
        self.assertIn('data-existing-metadata="preserve-me"', slide_tag.group(0))
        self.assertIn('data-scene-role="cover"', slide_tag.group(0))
        self.assertIn('data-layout-id="cover-center-title-edge-decor"', slide_tag.group(0))
        self.assertIn('data-pptx-background-image="true"', slide_tag.group(0))
        self.assertIn('data-pptx-background-image-embedded="true"', slide_tag.group(0))
        self.assertIn('data-pptx-background-image-src="./backgrounds/slide-001.png"', slide_tag.group(0))

        manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        record = manifest["slide_records"][0]
        self.assertEqual(record["scene_role"], "cover")
        self.assertEqual(record["layout_id"], "cover-center-title-edge-decor")
        self.assertEqual(record["id"], "s1")

    def test_single_apply_uses_the_same_exact_selector_and_pptx_contract(self) -> None:
        run_dir, background, mask = self._prepared_single_apply_run()
        experiment.apply_background(
            argparse.Namespace(
                run_dir=str(run_dir),
                background=str(background),
                mask=str(mask),
            )
        )

        final_html = (run_dir / "final.html").read_text(encoding="utf-8")
        final_selector = _style_rule_selector(
            final_html,
            "html-image-background-experiment-final",
        )
        self.assertEqual(final_selector, "html body #stage > section.slide#s1")
        winner_selector, winner_value, _ = _fixture_background_winner(final_html)
        self.assertEqual(winner_selector, final_selector)
        self.assertTrue(winner_value.startswith('url("data:image/png;base64,'))
        self.assertNotIn("!important", _style_rule_selector(final_html, "html-image-background-experiment-final"))
        self.assertEqual(validate_html_document_text(final_html), [])
        slide_tag = re.search(r'<section\b[^>]*\bid="s1"[^>]*>', final_html, re.IGNORECASE)
        self.assertIsNotNone(slide_tag)
        self.assertIn('data-existing-metadata="preserve-me"', slide_tag.group(0))
        self.assertIn('data-pptx-background-image="true"', slide_tag.group(0))
        self.assertIn('data-pptx-background-image-embedded="true"', slide_tag.group(0))
        self.assertIn('data-pptx-background-image-src="./background.png"', slide_tag.group(0))

    @unittest.skipUnless(
        os.environ.get("HTML_IMAGE_BACKGROUND_BROWSER_QA") == "1",
        "Set HTML_IMAGE_BACKGROUND_BROWSER_QA=1 to run computed-style browser QA",
    )
    def test_browser_computed_background_matches_live_slide_and_thumbnail_clone(self) -> None:
        run_dir, background_dir, _ = self._prepared_apply_run(
            (1672, 941),
            cascade_fixture=True,
        )
        experiment.apply_deck(
            argparse.Namespace(run_dir=str(run_dir), background_dir=str(background_dir))
        )
        report_path = run_dir / "browser-cascade.json"
        result = subprocess.run(
            [
                "node",
                str(BROWSER_CASCADE_QA),
                "--html",
                str(run_dir / "final.html"),
                "--report",
                str(report_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=(result.stdout or "") + (result.stderr or ""))
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["checks"]["liveSlideUsesEmbeddedRaster"])
        self.assertTrue(report["checks"]["thumbnailCloneUsesSameEmbeddedRaster"])
        self.assertEqual(report["live"]["backgroundImage"], report["thumbnailClone"]["backgroundImage"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
