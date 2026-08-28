import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PptxFinalizerContractTests(unittest.TestCase):
    def test_reflow_filters_typed_non_text_members(self):
        source = (ROOT / "scripts" / "finalize_pptx_background_master.ps1").read_text(encoding="utf-8")
        self.assertIn("$nonTextPlaceholderTypes = @('picture', 'chart', 'table')", source)
        self.assertIn("if ($members.Count -eq 0)", source)
        self.assertIn("$gapTotal", source)
        self.assertIn("$memberSpec.type", source)

    def test_title_subtitle_are_fixed_even_for_legacy_manifests_and_layout_is_empty(self):
        source = (ROOT / "scripts" / "finalize_pptx_background_master.ps1").read_text(encoding="utf-8")
        self.assertIn("[string]$memberSpec.type -in @('title', 'subtitle')", source)
        self.assertIn("$shape.TextFrame.TextRange.Text = ''", source)
        self.assertNotIn('$shape.TextFrame.TextRange.Text = "[$($placeholder.name)]"', source)
        self.assertIn("$fixedFrameMembers", source)
        self.assertIn("frame_policy -eq 'fixed'", source)

    def test_layout_geometry_is_authoritative_by_default(self):
        source = (ROOT / "scripts" / "finalize_pptx_background_master.ps1").read_text(encoding="utf-8")
        self.assertIn("$Manifest.reset_policy -ne 'legacy-reflow'", source)
        self.assertIn("$styleName -eq 'metric' -and [string]$manifest.reset_policy -eq 'legacy-reflow'", source)

    def test_placeholder_vertical_anchor_and_surface_layer_are_explicit(self):
        source = (ROOT / "scripts" / "finalize_pptx_background_master.ps1").read_text(encoding="utf-8")
        self.assertIn("$Shape.TextFrame.VerticalAnchor = 3", source)
        self.assertIn("$Shape.TextFrame2.VerticalAnchor = 3", source)
        self.assertIn("function Add-LayoutSurfaces", source)
        self.assertIn("surface--$($Role.id)--$($surface.id)", source)

    def test_per_page_selection_dispatches_to_powerpoint_native_finalizer(self):
        source = (ROOT / "scripts" / "finalize_pptx_background_master.ps1").read_text(encoding="utf-8")
        helper = (ROOT / "scripts" / "finalize_pptx_selection_master.ps1").read_text(encoding="utf-8")
        self.assertIn("[string]$SelectionManifest", source)
        self.assertIn("finalize_pptx_selection_master.ps1", source)
        self.assertIn("$layout.Shapes.AddPlaceholder", helper)
        self.assertIn("$master.CustomLayouts.Add", helper)
        self.assertIn("Copy-SeedNativeObjects", helper)
        self.assertIn("$msoPlaceholder = 14", helper)
        self.assertIn("$presentation.SaveAs($outputPath, $ppSaveAsOpenXMLPresentation)", helper)
        self.assertIn("layout-authoritative", helper)
        self.assertIn("flatten it before arithmetic", helper)
        self.assertIn("Materialize scalars first", helper)
        self.assertIn("native-text-powerpoint-api-limit", helper)
        self.assertIn("PowerPoint only permits one ppPlaceholderTitle", helper)
        self.assertIn("function Test-ShapeHasChart", helper)
        self.assertNotIn("has_chart = (try", helper)
        self.assertIn("$msoChart = 3", helper)
        self.assertIn("$msoTable = 19", helper)
        self.assertIn("$presentation.Slides.Item($pageIndex + 1)", helper)
        self.assertIn("[void]$source.Copy()", helper)
        self.assertIn("for ($attempt = 1; $attempt -le 3", helper)
        self.assertIn("$candidate.Delete()", helper)
        self.assertIn("Native copy failed after 3 attempts", helper)
        self.assertIn("source_type = $expectedType", helper)
        self.assertIn("function Test-NativeSeedOwnsPlaceholderContent", helper)
        self.assertIn("native-seed-children", helper)
        self.assertIn("process-node-*", helper)
        self.assertIn("score-label-*", helper)


if __name__ == "__main__":
    unittest.main()
