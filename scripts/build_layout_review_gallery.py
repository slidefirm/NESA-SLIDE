from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path

from html_font_system import google_fonts_head


ROOT = Path(__file__).resolve().parents[1]
QA_LOG = ROOT / "artifacts" / "qa" / "layout-preview-qa.jsonl"
QA_FAILS_DIR = ROOT / "artifacts" / "qa" / "layout-preview-fails"
DEPLOY_REVIEW_DIR = ROOT / "artifacts" / "deploy" / "review"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def normalize_layout_id(record: dict) -> str:
    layout_id = str(record.get("layout_id", ""))
    if "-legacy-" in layout_id:
        layout_id = layout_id.split("-legacy-", 1)[0]
    return layout_id


def record_image(record: dict) -> str | None:
    for key in ("actual_image_path", "fail_path", "image_path", "image"):
        value = record.get(key)
        if value:
            return str(value)
    return None


def image_label(name: str, layout_id: str) -> str:
    stem = Path(name).stem
    prefix = f"{layout_id}-legacy-20260706-"
    if stem.startswith(prefix):
        return stem.removeprefix(prefix)
    return stem


def fail_checks(record: dict) -> list[str]:
    checks = record.get("checks") or {}
    return [name for name, status in checks.items() if status == "fail"]


def discover_candidates(layout_id: str) -> list[dict]:
    candidates: dict[str, dict] = {}
    for path in sorted(QA_FAILS_DIR.glob(f"{layout_id}*.png"), key=lambda item: item.stat().st_mtime):
        candidates[path.name] = {
            "source": path,
            "status": "fail",
            "notes": "",
            "failed_items": [],
        }

    for record in read_jsonl(QA_LOG):
        if normalize_layout_id(record) != layout_id:
            continue
        image_value = record_image(record)
        if not image_value:
            continue
        source = ROOT / image_value
        if not source.exists():
            source = QA_FAILS_DIR / Path(image_value).name
        if not source.exists():
            continue
        name = source.name
        candidates[name] = {
            "source": source,
            "status": str(record.get("status", "needs-review")),
            "notes": str(record.get("notes", "")),
            "failed_items": record.get("failed_items") or fail_checks(record),
        }

    return list(candidates.values())


def status_text(status: str) -> str:
    if status == "pass":
        return "自動通過"
    if status in {"approved", "human-approved"}:
        return "人工通過"
    if status == "fail":
        return "待人工審核"
    return "待審核"


def card_html(candidate: dict, copied_name: str, layout_id: str) -> str:
    status = html.escape(status_text(candidate["status"]))
    raw_status = html.escape(candidate["status"])
    label = html.escape(image_label(copied_name, layout_id))
    filename = html.escape(copied_name)
    notes = html.escape(candidate.get("notes") or "未通過自動 QA，但保留給人工判斷。")
    failed = candidate.get("failed_items") or []
    failed_html = ""
    if failed:
        chips = "".join(f"<span>{html.escape(str(item))}</span>" for item in failed[:8])
        failed_html = f'<div class="checks">{chips}</div>'
    return f"""
<article class="card" data-status="{raw_status}">
  <div class="image-wrap"><img src="{filename}" alt="{label}" loading="lazy"></div>
  <div class="meta">
    <div class="row"><strong>{label}</strong><span class="badge">{status}</span></div>
    <code>{filename}</code>
    {failed_html}
    <p>{notes}</p>
  </div>
</article>"""


def build_layout_review(layout_id: str) -> Path:
    candidates = discover_candidates(layout_id)
    out_dir = DEPLOY_REVIEW_DIR / layout_id
    out_dir.mkdir(parents=True, exist_ok=True)

    candidate_names = {candidate["source"].name for candidate in candidates}
    for old in out_dir.glob("*.png"):
        if old.name not in candidate_names:
            old.unlink()

    cards: list[str] = []
    manifest: list[dict] = []
    for candidate in candidates:
        source = candidate["source"]
        dest = out_dir / source.name
        if source.resolve() != dest.resolve():
            shutil.copy2(source, dest)
        cards.append(card_html(candidate, dest.name, layout_id))
        manifest.append(
            {
                "file": dest.name,
                "status": candidate["status"],
                "failed_items": candidate.get("failed_items") or [],
                "notes": candidate.get("notes") or "",
            }
        )

    (out_dir / "manifest.json").write_text(
        json.dumps({"layout_id": layout_id, "candidates": manifest}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    title = f"{layout_id} 人工審核"
    description = (
        "自動 QA 未通過的候選圖會保留在這裡並標記狀態，不再直接退回或丟棄。"
        "人工確認後，再決定是否併入主 layout gallery。"
    )
    cards_html = "\n".join(cards) or '<p class="empty">目前沒有待審核候選。</p>'
    page = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
{google_fonts_head()}
<style>
  :root {{
    --font-heading: "Noto Sans TC", "Microsoft JhengHei", system-ui, sans-serif;
    --font-body: "Noto Sans TC", "Microsoft JhengHei", system-ui, sans-serif;
    --font-mono: "Roboto Mono", "Noto Sans TC", ui-monospace, Consolas, monospace;
    --font-display: "Noto Serif TC", "PMingLiU", serif;
    font-family: var(--font-body);
    color: #182230;
    background: #f4f7fb;
  }}
  body {{ margin: 0; padding: 28px; }}
  header {{ max-width: 1180px; margin: 0 auto 22px; }}
  h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }}
  p {{ margin: 0; color: #526174; line-height: 1.6; }}
  .grid {{
    max-width: 1180px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
    gap: 18px;
  }}
  .card {{
    background: #fff;
    border: 1px solid #dbe4ef;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 8px 24px rgba(20, 30, 45, .08);
  }}
  .image-wrap {{ aspect-ratio: 16 / 9; background: #e9eef5; display: grid; place-items: center; }}
  img {{ width: 100%; height: 100%; object-fit: contain; display: block; }}
  .meta {{ padding: 12px 14px 14px; display: flex; flex-direction: column; gap: 8px; }}
  .row {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
  strong {{ font-size: 15px; }}
  code {{ font-family: var(--font-mono); font-size: 12px; color: #5f7084; white-space: normal; word-break: break-all; }}
  .badge {{
    flex: 0 0 auto;
    padding: 4px 8px;
    border-radius: 999px;
    background: #fff4d6;
    color: #7a4b00;
    font-size: 12px;
    font-weight: 700;
  }}
  .checks {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .checks span {{
    padding: 3px 7px;
    border-radius: 999px;
    background: #eef2f7;
    color: #526174;
    font-size: 11px;
  }}
  .meta p {{ font-size: 12px; }}
  .empty {{ max-width: 1180px; margin: 0 auto; }}
</style>
</head>
<body>
<header>
  <h1>{html.escape(title)}</h1>
  <p>{html.escape(description)}</p>
</header>
<main class="grid">
{cards_html}
</main>
</body>
</html>
"""
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a per-layout human review page for preview candidates.")
    parser.add_argument("layout_id")
    args = parser.parse_args()
    out_dir = build_layout_review(args.layout_id)
    print(f"Built review page: {out_dir}")


if __name__ == "__main__":
    main()
