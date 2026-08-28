#!/usr/bin/env python3
"""Compact only generated deck copy so the fresh stories fit 36px HTML slots."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROW_KEYS = {
    "items", "steps", "cards", "priorities", "recommendations", "stats",
    "rows", "callouts", "kpis", "milestones", "quadrants",
}
PRESERVE_KEYS = {
    "story_id", "preset_id", "content_mode", "speaker", "org", "attribution",
    "mark", "footer", "eyebrow", "number", "metric", "tag", "allocation",
    "value", "delta", "label", "columns", "axes", "bars", "labels",
}
PROSE_KEYS = {
    "body", "note", "rationale", "impact", "takeaway", "footnote", "bridge",
    "intro", "quote", "support", "subtitle", "headline", "title", "insight",
}


def _han_count(value: str) -> int:
    return len(re.findall(r"\p{Han}", value)) if False else sum("\u4e00" <= char <= "\u9fff" for char in value)


def _compact_text(value: str, limit: int) -> str:
    value = re.sub(r"\s+", " ", value.replace("\n", " ")).strip()
    if _han_count(value) <= limit:
        return value
    parts = [part for part in re.split(r"(?<=[，。！？；：,.!?;:])", value) if part]
    chosen = ""
    for part in parts:
        candidate = chosen + part
        if not chosen or _han_count(candidate) <= limit:
            chosen = candidate
        else:
            break
    if not chosen:
        chosen = value[: max(1, limit - 1)]
    chosen = chosen.strip()
    if _han_count(chosen) > limit:
        han_seen = 0
        chars: list[str] = []
        for char in chosen:
            chars.append(char)
            if "\u4e00" <= char <= "\u9fff":
                han_seen += 1
            if han_seen >= max(1, limit - 1):
                break
        chosen = "".join(chars).rstrip("，。！？；：,.!?;:") + "…"
    elif chosen and chosen[-1] not in "，。！？；：,.!?;:…" and value[-1:] in "。！？!?":
        chosen += value[-1]
    return chosen


def _compact(value: Any, *, key: str | None = None, row_index: int | None = None) -> Any:
    if isinstance(value, dict):
        return {child_key: _compact(child, key=child_key) for child_key, child in value.items()}
    if isinstance(value, list):
        row_mode = key in ROW_KEYS
        compacted: list[Any] = []
        for index, child in enumerate(value):
            child_row_index = index if row_mode else None
            compacted.append(_compact(child, key=key, row_index=child_row_index))
        return compacted
    if not isinstance(value, str) or not value.strip() or key in PRESERVE_KEYS:
        return value
    if not re.search(r"[\u4e00-\u9fff]", value):
        return value
    if row_index is not None:
        if row_index == 0:
            return value
        if row_index == 1:
            return _compact_text(value, 16)
        return _compact_text(value, 18)
    if key in {"body", "note", "rationale", "impact", "takeaway", "footnote", "bridge"}:
        return _compact_text(value, 18)
    if key in {"subtitle", "support", "intro"}:
        return _compact_text(value, 24)
    if key == "quote":
        return _compact_text(value, 28)
    if key in {"title", "headline"}:
        return _compact_text(value, 22)
    if _han_count(value) > 24:
        return _compact_text(value, 18)
    return value


def compact_sources(root: Path) -> int:
    source_dir = root / "source"
    files = sorted(source_dir.glob("*.story.json"))
    if len(files) != 10:
        raise ValueError(f"expected 10 generated story files, found {len(files)}")
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        regeneration = payload.get("regeneration") or {}
        if regeneration.get("content_mode") != "new-deck" or not regeneration.get("fresh_content"):
            raise ValueError(f"not a fresh new-deck source: {path}")
        payload["layout_content"] = _compact(payload.get("layout_content") or {}, key="layout_content")
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(files)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    count = compact_sources(args.root.resolve())
    print(json.dumps({"root": str(args.root.resolve()), "story_files": count, "pass": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
