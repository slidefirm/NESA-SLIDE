#!/usr/bin/env python3
"""Generate and archive the formal editable HTML Theme Lab demos."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from render_authored_html_deck import build as build_authored  # noqa: E402
from html_theme_lab_catalog import (  # noqa: E402
    BASE_CATALOG,
    EXTENSION_CATALOG,
    load_catalog,
)


DEFAULT_CATALOG = BASE_CATALOG
DEFAULT_EXTENSION_CATALOG = EXTENSION_CATALOG
DEFAULT_MATRIX = ROOT / "artifacts" / "renderer-matrix" / "matrix.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "theme-demos" / "html-theme-lab"
EXPECTED_THEME_COUNT = 14


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_catalog(catalog: dict) -> None:
    themes = catalog.get("themes", [])
    if len(themes) != EXPECTED_THEME_COUNT:
        raise ValueError(
            f"HTML Theme Lab requires exactly {EXPECTED_THEME_COUNT} themes, found {len(themes)}"
        )
    ids = [row["theme_id"] for row in themes]
    if len(set(ids)) != len(ids):
        raise ValueError("HTML Theme Lab theme_id values must be unique")
    for field in ("pattern", "material", "color_blocks"):
        values = [row[field] for row in themes]
        if len(set(values)) != len(values):
            raise ValueError(f"HTML Theme Lab {field} descriptions must be unique")
    decoration_sets = [tuple(row["decorations"]) for row in themes]
    if len(set(decoration_sets)) != len(decoration_sets):
        raise ValueError("HTML Theme Lab decoration sets must be unique")
    story_ids = [row.get("topic", {}).get("id") for row in themes]
    if any(not value for value in story_ids) or len(set(story_ids)) != len(story_ids):
        raise ValueError("HTML Theme Lab requires one unique story_id per Theme")
    sequences = [tuple(slide["layout_id"] for slide in row.get("slides", [])) for row in themes]
    if any(len(sequence) < 10 for sequence in sequences):
        raise ValueError("Every authored HTML Theme Lab deck must contain at least 10 slides")
    if len(set(sequences)) != len(sequences):
        raise ValueError("HTML Theme Lab layout sequences must be unique")
    architectures = [tuple(slide["composition"] for slide in row["slides"]) for row in themes]
    if len(set(architectures)) != len(architectures):
        raise ValueError("HTML Theme Lab narrative architecture sequences must be unique")
    signatures = [row.get("signature") for row in themes]
    if any(not value for value in signatures) or len(set(signatures)) != len(signatures):
        raise ValueError("Every authored Theme requires one unique, subject-grounded signature")


def build_lab(
    catalog_path: Path,
    extension_catalog_path: Path | None,
    matrix_path: Path,
    output: Path,
    preserve_theme_ids: set[str] | None = None,
) -> dict:
    catalog = load_catalog(catalog_path, extension_catalog_path)
    validate_catalog(catalog)
    preserved = set(preserve_theme_ids or ())
    catalog_theme_ids = {row["theme_id"] for row in catalog["themes"]}
    unknown_preserved = preserved - catalog_theme_ids
    if unknown_preserved:
        raise ValueError(f"Unknown preserved Theme ids: {sorted(unknown_preserved)}")
    html_dir = output / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    for stale in [*html_dir.glob("*.html"), *html_dir.glob("*.manifest.json")]:
        theme_id = (
            stale.name.removesuffix(".manifest.json")
            if stale.name.endswith(".manifest.json")
            else stale.stem
        )
        if theme_id in preserved:
            continue
        stale.unlink()

    rows: list[dict] = []
    layout_sequences: set[tuple[str, ...]] = set()
    architecture_sequences: set[tuple[str, ...]] = set()
    story_ids: set[str] = set()
    for spec in sorted(catalog["themes"], key=lambda row: row["order"]):
        theme_id = spec["theme_id"]
        html_path = html_dir / f"{theme_id}.html"
        manifest_path = html_path.with_suffix(".manifest.json")
        if theme_id in preserved:
            if not html_path.is_file() or not manifest_path.is_file():
                raise FileNotFoundError(
                    f"Preserved Theme requires existing HTML and manifest: {theme_id}"
                )
            generated = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            generated = build_authored(spec, html_path)
        # Preserve means byte-for-byte preservation of a previously accepted
        # artifact. Do not force a legacy manifest through the newest renderer
        # checks, otherwise a targeted two-Theme rebuild silently expands into
        # a full collection rewrite.
        if spec.get("publish", True) and theme_id not in preserved:
            decisions = generated.get("design_decisions", [])
            variants = {row.get("composition_variant") for row in decisions}
            headers = {row.get("header_mode") for row in decisions}
            surfaces = {row.get("surface_mode") for row in decisions}
            if len(decisions) != len(spec["slides"]):
                raise ValueError(f"Public Theme is missing per-slide design decisions: {theme_id}")
            if len(variants) < 7 or len(headers) < 3 or len(surfaces) < 3:
                raise ValueError(
                    f"Public Theme lacks real composition rhythm: {theme_id}; "
                    f"variants={len(variants)}, headers={len(headers)}, surfaces={len(surfaces)}"
                )
            if generated.get("asset_provenance"):
                raise ValueError(f"Public Theme must be pattern/geometry-only: {theme_id}")
            html = html_path.read_text(encoding="utf-8").lower()
            if 'data-asset-policy="pattern-geometry-only"' not in html:
                raise ValueError(f"Public Theme has the wrong asset policy: {theme_id}")
            styles = html.split("<style>", 1)[1].split("</style>", 1)[0]
            for marker in ("data:image", "background-image:url("):
                if marker in styles:
                    raise ValueError(f"Public Theme contains forbidden CSS asset marker {marker}: {theme_id}")
        sequence = tuple(generated["layouts"])
        if sequence in layout_sequences:
            raise ValueError(f"Duplicate layout sequence generated for {theme_id}: {sequence}")
        layout_sequences.add(sequence)
        architecture = tuple(generated["architecture"])
        if architecture in architecture_sequences:
            raise ValueError(f"Duplicate narrative architecture generated for {theme_id}: {architecture}")
        architecture_sequences.add(architecture)
        story_id = generated["topic"]["id"]
        if story_id in story_ids:
            raise ValueError(f"Duplicate content topic generated for {theme_id}: {story_id}")
        story_ids.add(story_id)
        rows.append({
            **spec,
            "topic": generated["topic"],
            "theme": generated["theme"],
            "layouts": generated["layouts"],
            "architecture": generated["architecture"],
            "slide_count": len(generated["layouts"]),
            "source_html": html_path.relative_to(ROOT).as_posix(),
            "source_manifest": html_path.with_suffix(".manifest.json").relative_to(ROOT).as_posix(),
            "public_path": f"theme-html-lab/{theme_id}/",
            "design_dialect": generated["theme"]["design_dialect"],
            "composition": generated["theme"]["composition"],
            "techniques": generated["theme"]["techniques"],
            "assembly": generated["html_assembly"],
            "asset_provenance": generated.get("asset_provenance", []),
            "design_decisions": generated.get("design_decisions", []),
            "style_sha256": sha256_text(json.dumps({
                "signature": spec["signature"],
                "palette": spec["palette"],
                "typography": spec["typography"],
                "pattern": spec["pattern"],
            }, ensure_ascii=False, sort_keys=True)),
            "html_sha256": hashlib.sha256(html_path.read_bytes()).hexdigest(),
        })

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    archive = {
        "version": catalog["version"],
        "id": catalog["id"],
        "generated_at": now,
        "title": catalog["title"],
        "description": catalog["description"],
        "public_path": catalog["public_path"],
        "asset_base_url": catalog["asset_base_url"],
        "counts": {
            "themes": len(rows),
            "unique_patterns": len({row["pattern"] for row in rows}),
            "unique_materials": len({row["material"] for row in rows}),
            "unique_color_block_systems": len({row["color_blocks"] for row in rows}),
            "unique_decoration_sets": len({tuple(row["decorations"]) for row in rows}),
            "unique_layout_sequences": len(layout_sequences),
            "unique_architecture_sequences": len(architecture_sequences),
            "unique_content_topics": len(story_ids),
            "unique_design_dialects": len({row["design_dialect"] for row in rows}),
            "unique_compositions": len({row["composition"] for row in rows}),
            "unique_techniques": len({technique for row in rows for technique in row["techniques"]}),
            "unique_assembly_signatures": len({
                (row["assembly"]["id"], row["theme"]["signature"]) for row in rows
            }),
        },
        "themes": rows,
    }
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / "theme-lab-archive.json"
    archive_path.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {
        "themes": len(rows),
        "slides": sum(row["slide_count"] for row in rows),
        "unique_layout_sequences": len(layout_sequences),
        "unique_architecture_sequences": len(architecture_sequences),
        "unique_content_topics": len(story_ids),
        "unique_design_dialects": archive["counts"]["unique_design_dialects"],
        "unique_compositions": archive["counts"]["unique_compositions"],
        "unique_techniques": archive["counts"]["unique_techniques"],
        "preserved_themes": sorted(preserved),
        "output": output.relative_to(ROOT).as_posix(),
        "archive": archive_path.relative_to(ROOT).as_posix(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--extension-catalog", type=Path, default=DEFAULT_EXTENSION_CATALOG)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--preserve-theme",
        action="append",
        default=[],
        help="Keep an existing Theme HTML and manifest unchanged while rebuilding the lab.",
    )
    args = parser.parse_args()
    build_lab(
        args.catalog.resolve(),
        args.extension_catalog.resolve() if args.extension_catalog else None,
        args.matrix.resolve(),
        args.output.resolve(),
        set(args.preserve_theme),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
