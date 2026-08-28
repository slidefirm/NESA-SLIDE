from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterator


DIMENSION_ALIASES = {
    "topic": {"topic", "content-topic"},
    "content": {"content", "story", "story-structure", "content-structure"},
    "layout-sequence": {"layout", "layouts", "layout-sequence"},
    "theme": {"theme", "preset", "theme-decoration-profile"},
}


def walk_values(value: Any) -> Iterator[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_values(child)


def normalized_dimensions(manifest: dict[str, Any]) -> set[str]:
    raw = manifest.get("randomized_dimensions")
    if not isinstance(raw, list):
        return set()
    return {str(value).strip().lower() for value in raw if str(value).strip()}


def has_dimension(dimensions: set[str], required: str) -> bool:
    accepted = DIMENSION_ALIASES.get(required, {required})
    return bool(dimensions.intersection(accepted))


def has_candidate_pool_evidence(manifest: dict[str, Any]) -> bool:
    keys = {
        "candidate_pool",
        "candidate_pools",
        "candidate_pool_version",
        "candidate_pool_versions",
        "randomization_pool",
        "randomization_pools",
    }
    return any(isinstance(value, dict) and keys.intersection(value) for value in walk_values(manifest))


def forced_layout_sources(manifest: dict[str, Any]) -> tuple[int, int]:
    layout_sources: list[str] = []
    for value in walk_values(manifest):
        if not isinstance(value, dict):
            continue
        source = value.get("source")
        if isinstance(source, str) and "layout" in source.lower():
            layout_sources.append(source.strip().lower())
    forced = sum(source == "forced-layout" for source in layout_sources)
    return forced, len(layout_sources)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate reproducible randomization evidence in an HTML deck manifest."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--require-dimension",
        action="append",
        default=[],
        choices=sorted(DIMENSION_ALIASES),
        help="Randomization dimension that must be represented; may be repeated.",
    )
    parser.add_argument(
        "--require-preset",
        action="store_true",
        help="Require theme.kind=html-preset and a non-empty preset/theme id.",
    )
    parser.add_argument(
        "--allow-missing-pool",
        action="store_true",
        help="Permit legacy manifests without candidate-pool evidence.",
    )
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}

    seed = manifest.get("seed")
    checks["seed_present"] = seed is not None and str(seed).strip() != ""

    dimensions = normalized_dimensions(manifest)
    checks["randomized_dimensions_nonempty"] = bool(dimensions)
    for required in args.require_dimension:
        checks[f"dimension_{required}"] = has_dimension(dimensions, required)

    checks["candidate_pool_evidence"] = (
        args.allow_missing_pool or has_candidate_pool_evidence(manifest)
    )

    if has_dimension(dimensions, "layout-sequence"):
        forced, total = forced_layout_sources(manifest)
        checks["layout_sequence_not_all_forced"] = total == 0 or forced < total

    if args.require_preset:
        theme = manifest.get("theme")
        checks["html_preset_kind"] = (
            isinstance(theme, dict)
            and str(theme.get("kind", "")).strip().lower() == "html-preset"
        )
        checks["preset_id_present"] = (
            isinstance(theme, dict)
            and bool(str(theme.get("id", "")).strip())
        )

    passed = all(checks.values())
    payload = {
        "manifest": manifest_path.as_posix(),
        "status": "PASS" if passed else "FAIL",
        "dimensions": sorted(dimensions),
        "checks": checks,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
