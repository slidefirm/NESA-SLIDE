import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "qa_html_edit_interactions.cjs"
EDITOR = ROOT / "src" / "html-editor" / "edit-mode.js"
SCRIPTS = ROOT / "scripts"


class HtmlEditInteractionsExportHarnessTests(unittest.TestCase):
    def test_browser_download_branch_is_forced_before_html_load(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("await page.addInitScript", source)
        self.assertIn('Object.defineProperty(window, "showSaveFilePicker"', source)
        self.assertIn("window.__qaBrowserDownloadExportHarness = true", source)
        self.assertIn("result.exportDownloadHarness.pass", source)

    def test_semantic_fallbacks_cover_new_deck_modules_and_non_before_after_text(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn(".toc-image-row", source)
        self.assertIn('[data-edit-structure="module"][data-edit-composite]', source)
        self.assertIn('[data-edit-kind="text"][data-edit-fit="text"]', source)
        self.assertIn("const featureNA", source)
        self.assertIn("applicable: false", source)

    def test_compact_toolbar_collapses_secondary_chrome_without_canvas_reflow(self) -> None:
        source = EDITOR.read_text(encoding="utf-8")
        self.assertIn("const compactToolbar", source)
        self.assertIn("const compactIconButtons", source)
        self.assertIn("barInner.clientWidth <= 760", source)
        self.assertIn("title and aria-label", source)

    def test_manual_group_hit_priority_beats_only_same_point_overlay_candidates(self) -> None:
        source = EDITOR.read_text(encoding="utf-8")
        self.assertIn("const manualGroupTarget = targets.find", source)
        self.assertIn("!additiveSelection && !directGroupSelection && !currentGroupEditScope()", source)
        self.assertIn("targets.unshift(manualGroupTarget)", source)

    def test_semantic_deck_harness_reports_applicability_instead_of_layout_class_false_failures(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("const featureNA", source)
        self.assertIn("applicable: false", source)
        self.assertIn("const applicableChecks = interactionChecks.filter", source)
        self.assertIn("applicableChecks.every((check) => check.pass)", source)
        self.assertIn("semanticModulesBySlide", source)
        self.assertIn("sameSlideCandidates", source)

    def test_ungrouped_semantic_layer_is_tested_before_group_state_is_restored(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("direct semantic layers are editable", source)
        self.assertIn("Clear it before testing one direct text layer", source)
        self.assertIn("const restoredGroupState", source)

    def test_every_browser_download_export_harness_explicitly_forces_the_fallback(self) -> None:
        harnesses = {
            path.name: path.read_text(encoding="utf-8")
            for path in SCRIPTS.glob("qa_html_*.cjs")
            if "EditMode.export" in path.read_text(encoding="utf-8")
            and "waitForEvent" in path.read_text(encoding="utf-8")
            and "download" in path.read_text(encoding="utf-8")
        }
        self.assertEqual(
            set(harnesses),
            {
                "qa_html_adaptive_axis_roundtrip.cjs",
                "qa_html_edit_interactions.cjs",
                "qa_html_font_background_controls.cjs",
                "qa_html_selection_panel_placement.cjs",
                "qa_html_slide_mask.cjs",
                "qa_html_textbox_background_dropdown.cjs",
            },
        )
        for name, source in harnesses.items():
            with self.subTest(harness=name):
                self.assertIn("showSaveFilePicker", source)
                self.assertIn("__qaBrowserDownloadExportHarness", source)

        save_export = (SCRIPTS / "qa_html_save_export.cjs").read_text(encoding="utf-8")
        self.assertIn("__qaBrowserDownloadExportHarness", save_export)
        self.assertIn("exportDownloadFallbackForced", save_export)

    def test_file_system_access_harnesses_keep_explicit_picker_stubs(self) -> None:
        for name in ("qa_html_file_binding.cjs", "qa_html_direct_overwrite.cjs"):
            source = (SCRIPTS / name).read_text(encoding="utf-8")
            with self.subTest(harness=name):
                self.assertIn("showSaveFilePicker", source)
                self.assertIn("async", source)

    def test_save_export_accepts_the_documented_browser_download_feedback(self) -> None:
        source = (SCRIPTS / "qa_html_save_export.cjs").read_text(encoding="utf-8")
        self.assertIn("已(?:下載)?另存", source)
        self.assertIn("exportFeedbackNonEmpty", source)
        editor = EDITOR.read_text(encoding="utf-8")
        self.assertIn("saveAsOpened", editor)
        self.assertIn("exportDone", editor)

    def test_pptx_browser_export_uses_the_stable_save_menu_contract(self) -> None:
        source = (SCRIPTS / "qa_html_pptx_browser_export.cjs").read_text(encoding="utf-8")
        self.assertIn("#edit-save-menu-toggle", source)
        self.assertIn("#edit-save-menu", source)
        self.assertIn("pptxSaveMenuTogglePresent", source)
        self.assertIn("pptxMenuOpened", source)
        self.assertNotIn('document.querySelectorAll("#barInner button")', source)

    def test_pptx_browser_export_requires_four_semantic_slide_pictures(self) -> None:
        source = (SCRIPTS / "qa_html_pptx_browser_export.cjs").read_text(encoding="utf-8")
        self.assertIn("semanticPictureAudit", source)
        self.assertIn("semanticPicturesOnSlides", source)
        self.assertIn("slidePictureObjects === 4", source)
        self.assertIn("data-semantic-image-source", source)

    def test_svg_text_projection_uses_metrics_anchor_and_nonshrinking_single_line_contract(self) -> None:
        editor = EDITOR.read_text(encoding="utf-8")
        exporter = (ROOT / "artifacts" / "html-test" / "pptx-browser-export.js").read_text(encoding="utf-8")
        harness = (SCRIPTS / "qa_html_pptx_browser_export.cjs").read_text(encoding="utf-8")
        self.assertIn("function pptxSvgTextPosition", editor)
        self.assertIn("node.getComputedTextLength()", editor)
        self.assertIn("pptxSvgTextAnchor", editor)
        self.assertIn("safeWidth = glyphWidth * 1.18", editor)
        self.assertIn("singleLine: textProjection.measured", editor)
        self.assertIn("fit: textProjection.measured ? 'none' : 'shrink'", editor)
        self.assertIn("fit: singleLine ? 'none' : 'shrink'", exporter)
        self.assertIn("wrap: !singleLine", exporter)
        self.assertIn("svgTextProjectionAudit", harness)
        for label in ("100", "R1", "指標值（0–100）"):
            with self.subTest(label=label):
                self.assertIn(label, harness)
        self.assertIn("noShrinkAutofit", harness)
        self.assertIn("svgTextProjection: svgTextProjection.pass", harness)


if __name__ == "__main__":
    unittest.main()
