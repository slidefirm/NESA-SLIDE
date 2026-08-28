from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RENDERER = PROJECT_ROOT / "scripts" / "render_randomized_html_demo.py"
EDITOR_SOURCE = PROJECT_ROOT / "src" / "html-editor" / "edit-mode.js"
OUTPUT_ROOT = (
    PROJECT_ROOT
    / "artifacts"
    / "experiments"
    / "html-image-background"
    / "html-preset-regeneration-20260813-v6"
    / "regenerated-source"
    / "core"
)
SOURCE_ROOT = (
    PROJECT_ROOT
    / "artifacts"
    / "experiments"
    / "html-preset-regeneration-20260812-v1"
    / "new-deck"
)

PRESETS = (
    "clinical-evidence-atlas",
    "dark-ai-city",
    "dark-city-network-report",
    "sepia-retail-case",
)

FINAL_LAYOUTS = {
    "clinical-evidence-atlas": (
        "cover-center-title-edge-decor",
        "toc-5-panel-grid",
        "recommendation-stack",
        "split-comparison",
        "dashboard-overview",
        "process-flow",
        "quote-focus",
        "title-center",
    ),
    "dark-ai-city": (
        "cover-center-title-edge-decor",
        "toc-6-vertical",
        "recommendation-stack",
        "before-after",
        "stats-3-row",
        "process-flow",
        "quote-focus",
        "title-center",
    ),
    "dark-city-network-report": (
        "cover-center-title-edge-decor",
        "toc-6-vertical",
        "strategic-priorities",
        "split-comparison",
        "multi-line-chart",
        "process-flow",
        "quote-focus",
        "title-center",
    ),
    "sepia-retail-case": (
        "cover-center-title-edge-decor",
        "toc-6",
        "strategic-priorities",
        "split-comparison",
        "kpi-scorecards",
        "gantt-roadmap",
        "quote-focus",
        "title-center",
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def portable(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def source_manifest_path(preset: str) -> Path:
    return SOURCE_ROOT / preset / f"{preset}-new-deck.manifest.json"


def content_hashes(manifest: dict[str, Any]) -> dict[str, str]:
    return {
        str(page["page_id"]): str(page["content_sha256"])
        for page in manifest.get("content_pages", [])
    }


def validate_source(preset: str, source_path: Path, source: dict[str, Any]) -> tuple[str, int]:
    if source.get("content_mode") != "new-deck":
        raise ValueError(f"{preset}: source manifest is not new-deck")
    if source.get("theme", {}).get("id") != preset:
        raise ValueError(f"{preset}: source theme id does not match")
    if source.get("preset_theme", {}).get("id") != preset:
        raise ValueError(f"{preset}: source preset id does not match")
    content_source = str(source.get("content_source", ""))
    if not content_source.startswith("built-in:"):
        raise ValueError(f"{preset}: expected an explicit built-in story source")
    story_id = content_source.removeprefix("built-in:")
    if source.get("topic", {}).get("id") != story_id:
        raise ValueError(f"{preset}: source topic and story id diverge")
    if not source.get("content_pages"):
        raise ValueError(f"{preset}: source content manifest has no pages")
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    return story_id, int(source["seed"])


def assert_portable_strings(value: Any, *, label: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert_portable_strings(child, label=f"{label}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            assert_portable_strings(child, label=f"{label}[{index}]")
        return
    if isinstance(value, str) and (
        value.startswith("file://")
        or value.startswith("C:\\")
        or value.startswith("C:/")
    ):
        raise ValueError(f"absolute path in manifest at {label}: {value}")


def render_one(preset: str) -> dict[str, Any]:
    source_path = source_manifest_path(preset)
    source = read_json(source_path)
    story_id, seed = validate_source(preset, source_path, source)
    layouts = FINAL_LAYOUTS[preset]
    if len(layouts) != len(source["content_pages"]):
        raise ValueError(f"{preset}: final Layout sequence does not match page count")

    deck_dir = OUTPUT_ROOT / preset
    deck_dir.mkdir(parents=True, exist_ok=True)
    output_html = deck_dir / "final.html"
    command = [
        sys.executable,
        str(RENDERER),
        "--output",
        str(output_html),
        "--seed",
        str(seed),
        "--theme",
        preset,
        "--story",
        story_id,
        "--layouts",
        ",".join(layouts),
        "--content-mode",
        "new-deck",
        "--asset-policy",
        "pattern-only",
    ]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"{preset}: renderer failed ({completed.returncode})\n{stderr.strip()}"
        )

    output_manifest = output_html.with_suffix(".manifest.json")
    sidecar_editor = deck_dir / "edit-mode.js"
    generated = read_json(output_manifest)
    editor_hash = sha256(EDITOR_SOURCE)
    renderer_hash = sha256(RENDERER)

    if generated.get("content_mode") != "new-deck":
        raise ValueError(f"{preset}: renderer did not preserve new-deck mode")
    if "example_reference" in generated:
        raise ValueError(f"{preset}: preset-demo provenance leaked into new-deck output")
    if generated.get("theme", {}).get("id") != preset:
        raise ValueError(f"{preset}: generated theme id does not match")
    if generated.get("content_source") != f"built-in:{story_id}":
        raise ValueError(f"{preset}: generated story source does not match")
    if content_hashes(generated) != content_hashes(source):
        raise ValueError(f"{preset}: current renderer changed the requested source content")
    if generated.get("editable_dom", {}).get("editor_sha256") != editor_hash:
        raise ValueError(f"{preset}: embedded editor is not the current canonical editor")
    if not sidecar_editor.is_file() or sha256(sidecar_editor) != editor_hash:
        raise ValueError(f"{preset}: editor sidecar does not match the canonical editor")

    generated["v6_regeneration"] = {
        "mode": "current-renderer-regeneration",
        "content_mode": "new-deck",
        "source_usage": "content-story-and-seed-only",
        "runtime_inputs_excluded": [
            "source-html",
            "source-css",
            "source-layout-sequence",
            "preset-demo",
        ],
        "layout_selection": {
            "mode": "current-catalog-explicit-diversity-remediation",
            "reason": "initial current-resolver attempt failed the deck-level repeated-skeleton gate",
            "source_layout_sequence_not_used": True,
            "prior_auto_attempt_manifest": portable(deck_dir / f"{preset}.manifest.json"),
            "prior_auto_attempt_qa": portable(deck_dir / "qa" / "design-method.json"),
        },
        "source_manifest": portable(source_path),
        "source_manifest_sha256": sha256(source_path),
        "source_story": f"built-in:{story_id}",
        "preset": preset,
        "layout_sequence": list(generated.get("layouts", [])),
        "renderer": {
            "entrypoint": portable(RENDERER),
            "sha256": renderer_hash,
        },
        "editor": {
            "source": portable(EDITOR_SOURCE),
            "sha256": editor_hash,
            "sidecar": portable(sidecar_editor),
        },
        "output_html": portable(output_html),
        "output_manifest": portable(output_manifest),
        "image_background_attached": False,
    }
    assert_portable_strings(generated, label=preset)
    write_json(output_manifest, generated)

    return {
        "preset": preset,
        "html": portable(output_html),
        "manifest": portable(output_manifest),
        "pages": len(generated.get("layouts", [])),
        "story": story_id,
        "layouts": generated.get("layouts", []),
        "editor_sha256": editor_hash,
        "renderer_sha256": renderer_hash,
    }


def main() -> int:
    if not RENDERER.is_file():
        raise FileNotFoundError(RENDERER)
    if not EDITOR_SOURCE.is_file():
        raise FileNotFoundError(EDITOR_SOURCE)
    results = [render_one(preset) for preset in PRESETS]
    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
