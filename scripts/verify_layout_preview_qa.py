from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class QaState:
    layout_id: str
    status: str
    timestamp: str
    image: str
    image_sha256: str
    layout_sha256: str


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_path(value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else ROOT / path).resolve()


def layout_id_from_preview(path: Path) -> str:
    name = path.stem
    for suffix in ("-codex", "-image2"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def load_latest_qa(path: Path) -> dict[str, QaState]:
    latest: dict[str, QaState] = {}
    if not path.exists():
        return latest

    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at {path}:{line_no}: {exc}") from exc

        layout_id = str(record.get("layout_id", "")).strip()
        if not layout_id:
            continue
        state = QaState(
            layout_id=layout_id,
            status=str(record.get("status", "")).strip(),
            timestamp=str(record.get("timestamp", "")).strip(),
            image=str(record.get("image", "")).strip(),
            image_sha256=str(record.get("image_sha256", "")).strip(),
            layout_sha256=str(record.get("layout_sha256", "")).strip(),
        )
        current = latest.get(layout_id)
        if current is None or state.timestamp >= current.timestamp:
            latest[layout_id] = state
    return latest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check that each preview is the exact file covered by its latest pass or approval."
    )
    parser.add_argument(
        "--preview-dir",
        default="artifacts/deploy/layout-previews",
        help="Directory containing generated preview images.",
    )
    parser.add_argument(
        "--qa-log",
        default="artifacts/qa/layout-preview-qa.jsonl",
        help="QA JSONL path.",
    )
    parser.add_argument(
        "--layout-dir",
        default="prompt_system/layouts",
        help="Canonical Layout directory used to detect missing main previews.",
    )
    parser.add_argument(
        "--pattern",
        default="*-codex.png",
        help="Preview file glob. Use '*-codex.png' for main gallery.",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Print failures but exit 0.",
    )
    args = parser.parse_args()

    preview_dir = Path(args.preview_dir)
    qa_log = Path(args.qa_log)
    layout_dir = Path(args.layout_dir)
    previews = sorted(preview_dir.glob(args.pattern))
    latest = load_latest_qa(qa_log)

    expected_layout_ids = {path.stem for path in layout_dir.glob("*.yaml")}
    preview_layout_ids = {layout_id_from_preview(path) for path in previews}
    missing_previews = sorted(expected_layout_ids - preview_layout_ids)
    missing: list[str] = []
    failing: list[str] = []
    passing: list[str] = []

    for preview in previews:
        layout_id = layout_id_from_preview(preview)
        state = latest.get(layout_id)
        if state is None:
            missing.append(layout_id)
        elif state.status not in {"pass", "approved"}:
            failing.append(f"{layout_id} ({state.status})")
        elif not state.image or project_path(state.image) != preview.resolve():
            failing.append(f"{layout_id} (QA image mismatch: {state.image or 'missing image path'})")
        elif state.image_sha256 and state.image_sha256 != sha256_file(preview):
            failing.append(f"{layout_id} (QA image hash mismatch)")
        elif state.layout_sha256 and state.layout_sha256 != sha256_file(layout_dir / f"{layout_id}.yaml"):
            failing.append(f"{layout_id} (Layout source changed after QA)")
        else:
            passing.append(layout_id)

    print(f"Preview files: {len(previews)}")
    print(f"Preview missing: {len(missing_previews)}")
    print(f"QA pass: {len(passing)}")
    print(f"QA missing: {len(missing)}")
    print(f"QA latest non-pass: {len(failing)}")

    if missing_previews:
        print("\nMissing previews:")
        for layout_id in missing_previews:
            print(f"- {layout_id}")

    if missing:
        print("\nMissing QA:")
        for layout_id in missing:
            print(f"- {layout_id}")

    if failing:
        print("\nQA validation failures:")
        for item in failing:
            print(f"- {item}")

    if (missing_previews or missing or failing) and not args.warn_only:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
