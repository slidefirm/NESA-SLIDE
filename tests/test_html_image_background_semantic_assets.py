import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts import html_image_background_experiment as experiment


class SemanticAssetStagingTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace = experiment.ROOT / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        self.temp_root = Path(tempfile.mkdtemp(prefix="semantic-stage-", dir=workspace))
        self.run_dir = experiment.EXPERIMENT_ROOT / self.temp_root.name
        self.source_dir = self.temp_root / "source"
        self.source_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        for path in (self.temp_root, self.run_dir):
            if path.exists():
                shutil.rmtree(path)

    def _write_deck(self, src: str) -> Path:
        html = self.source_dir / "deck.html"
        html.write_text(
            '<html><head><title>test</title></head><body><main id="stage">'
            '<section class="slide" id="s1" data-index="0" data-image-variant="photo" '
            'data-page-claim="fictional claim"><img data-semantic-image="true" '
            f'src="{src}" alt="fictional semantic image"></section>'
            "</main></body></html>",
            encoding="utf-8",
        )
        return html

    def _prepare(self, html: Path) -> None:
        experiment.prepare_deck(
            SimpleNamespace(input=str(html), run_dir=str(self.run_dir))
        )

    def test_stages_relative_semantic_asset_for_neutral_and_mask_page(self) -> None:
        asset = self.source_dir / "semantic-images" / "photo.png"
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(b"model-native-semantic-photo")
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        self._prepare(self._write_deck("semantic-images/photo.png"))

        relative_ref = f"semantic-assets/{digest}.png"
        staged = self.run_dir / relative_ref
        self.assertTrue(staged.is_file())
        self.assertEqual(staged.read_bytes(), asset.read_bytes())
        self.assertIn(f"src=\"{relative_ref}\"", (self.run_dir / "neutral.html").read_text(encoding="utf-8"))
        self.assertIn(f"src=\"{relative_ref}\"", (self.run_dir / "mask.html").read_text(encoding="utf-8"))
        mask_page = self.run_dir / "mask-pages" / "mask-001.html"
        self.assertIn(f"src=\"../{relative_ref}\"", mask_page.read_text(encoding="utf-8"))
        self.assertTrue((mask_page.parent / ".." / relative_ref).resolve().is_file())

        manifest = json.loads((self.run_dir / "run.json").read_text(encoding="utf-8"))
        record = manifest["semantic_assets"][0]
        self.assertEqual(record["sha256"], digest)
        self.assertEqual(record["relative_ref"], relative_ref)
        self.assertFalse(Path(record["staged"]).is_absolute())
        self.assertNotIn(str(self.temp_root), json.dumps(manifest))

        inlined, embedded = experiment._inline_staged_semantic_assets(
            (self.run_dir / "neutral.html").read_text(encoding="utf-8"),
            semantic_assets=manifest["semantic_assets"],
            run_dir=self.run_dir,
        )
        self.assertIn('src="data:image/png;base64,', inlined)
        self.assertIn(f'data-semantic-image-source="{relative_ref}"', inlined)
        self.assertIn(f'data-semantic-image-sha256="{digest}"', inlined)
        self.assertEqual(embedded, [{"source": relative_ref, "staged": record["staged"], "sha256": digest}])

    def test_missing_relative_semantic_asset_fails_loudly(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "Semantic image asset is missing"):
            self._prepare(self._write_deck("semantic-images/missing.png"))


if __name__ == "__main__":
    unittest.main()
