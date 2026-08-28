import sys
import unittest
import zipfile
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_renderer_matrix import pptx_structure  # noqa: E402


def _shape(name: str, type_name: str, idx: int) -> str:
    return f'''<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:nvSpPr><p:cNvPr id="{idx + 2}" name="{name}"/><p:cNvSpPr/><p:nvPr><p:ph type="{type_name}" idx="{idx}"/></p:nvPr></p:nvSpPr></p:sp>'''


class VerifyRendererMatrixTests(unittest.TestCase):
    def test_ooxml_placeholder_types_names_indices_and_relationship(self):
        layout_xml = '<p:sldLayout xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld name="layout--typed"><p:spTree>' + ''.join([
            _shape("title", "title", 0),
            _shape("photo", "pic", 1),
            _shape("chart", "chart", 2),
            _shape("table", "tbl", 3),
        ]) + '</p:spTree></p:cSld></p:sldLayout>'
        master_xml = '<p:sldMaster xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld name="theme--demo"/></p:sldMaster>'
        slide_xml = '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld/></p:sld>'
        rel_xml = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/></Relationships>'
        expected = [{
            "id": "typed",
            "pptx": {
                "layout_name": "layout--typed",
                "placeholder_schema": [
                    {"id": "title", "placeholder_type": "title"},
                    {"id": "photo", "placeholder_type": "picture"},
                    {"id": "chart", "placeholder_type": "chart"},
                    {"id": "table", "placeholder_type": "table"},
                ],
            },
            "slots": [],
        }]
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("ppt/slideLayouts/slideLayout1.xml", layout_xml)
            archive.writestr("ppt/slideMasters/slideMaster1.xml", master_xml)
            archive.writestr("ppt/slides/slide1.xml", slide_xml)
            archive.writestr("ppt/slides/_rels/slide1.xml.rels", rel_xml)
        buffer.seek(0)
        with zipfile.ZipFile(buffer, "r") as archive:
            result = pptx_structure(archive, "demo", expected)
        self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()
