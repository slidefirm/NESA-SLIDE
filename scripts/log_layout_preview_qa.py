import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Append a layout preview QA result.")
    parser.add_argument("--layout-id", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--iteration", required=True, type=int)
    parser.add_argument("--status", required=True, choices=("pass", "fail"))
    parser.add_argument("--checks-json")
    parser.add_argument(
        "--check",
        action="append",
        default=[],
        help="Repeatable check in name=pass|fail form.",
    )
    parser.add_argument("--notes", default="")
    parser.add_argument(
        "--output",
        default="artifacts/qa/layout-preview-qa.jsonl",
    )
    args = parser.parse_args()

    checks = json.loads(args.checks_json) if args.checks_json else {}
    if not isinstance(checks, dict):
        raise ValueError("--checks-json must contain a JSON object")
    for item in args.check:
        name, separator, result = item.partition("=")
        if not separator or result not in {"pass", "fail"}:
            raise ValueError("--check must use name=pass or name=fail")
        checks[name] = result
    if not checks:
        raise ValueError("Provide --checks-json or at least one --check")

    image_path = Path(args.image)
    resolved_image = image_path if image_path.is_absolute() else ROOT / image_path
    resolved_image = resolved_image.resolve()
    if not resolved_image.is_file():
        raise FileNotFoundError(f"QA image does not exist: {resolved_image}")
    layout_path = ROOT / "prompt_system" / "layouts" / f"{args.layout_id}.yaml"
    if not layout_path.is_file():
        raise FileNotFoundError(f"Canonical Layout does not exist: {layout_path}")
    try:
        recorded_image = resolved_image.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        recorded_image = resolved_image.as_posix()

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "layout_id": args.layout_id,
        "image": recorded_image,
        "image_sha256": sha256_file(resolved_image),
        "layout_sha256": sha256_file(layout_path),
        "iteration": args.iteration,
        "status": args.status,
        "checks": checks,
        "notes": args.notes,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
