import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from qa_pptx_master_aware_overflow import audit_pptx  # noqa: E402


PRESENTATION = '''<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldSz cx="1000" cy="500"/></p:presentation>'''
SLIDE = '''<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="1" name="native"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="20" y="20"/><a:ext cx="100" cy="40"/></a:xfrm></p:spPr></p:sp></p:spTree></p:cSld></p:sld>'''
LAYOUT = '''<p:sldLayout xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="2" name="ph--title"/><p:cNvSpPr/><p:nvPr><p:ph type="title" idx="1"/></p:nvPr></p:nvSpPr><p:spPr><a:xfrm><a:off x="40" y="30"/><a:ext cx="600" cy="80"/></a:xfrm></p:spPr></p:sp></p:spTree></p:cSld></p:sldLayout>'''
MASTER = '''<p:sldMaster xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree><p:pic><p:nvPicPr><p:cNvPr id="3" name="__PPTX_BG__cover"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="1000" cy="500"/></a:xfrm></p:spPr></p:pic></p:spTree></p:cSld></p:sldMaster>'''
RELS_SLIDE = '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml" Id="rId1"/></Relationships>'''
RELS_LAYOUT = '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml" Id="rId1"/></Relationships>'''


class MasterAwareOverflowTests(unittest.TestCase):
    def write_package(self, path: Path, *, slide_xml: str = SLIDE) -> None:
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("ppt/presentation.xml", PRESENTATION)
            archive.writestr("ppt/slides/slide1.xml", slide_xml)
            archive.writestr("ppt/slides/_rels/slide1.xml.rels", RELS_SLIDE)
            archive.writestr("ppt/slideLayouts/slideLayout1.xml", LAYOUT)
            archive.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", RELS_LAYOUT)
            archive.writestr("ppt/slideMasters/slideMaster1.xml", MASTER)

    def test_inherited_layout_and_master_boxes_are_checked_without_false_overflow(self):
        with tempfile.TemporaryDirectory() as directory:
            pptx = Path(directory) / "inside.pptx"
            self.write_package(pptx)
            result = audit_pptx(pptx)
        self.assertTrue(result["pass"])
        self.assertEqual(result["slides"][0]["placeholder_bbox_count"], 1)
        self.assertEqual(result["virtual_padding"]["percent"], 5.0)

    def test_slide_owned_shape_outside_canvas_fails(self):
        outside = SLIDE.replace('x="20" y="20"', 'x="-1" y="20"')
        with tempfile.TemporaryDirectory() as directory:
            pptx = Path(directory) / "outside.pptx"
            self.write_package(pptx, slide_xml=outside)
            result = audit_pptx(pptx)
        self.assertFalse(result["pass"])
        self.assertEqual(result["overflow"][0]["owner"], "slide")


if __name__ == "__main__":
    unittest.main()
