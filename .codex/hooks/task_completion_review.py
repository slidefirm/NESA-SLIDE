"""Codex Stop hook for a proposal-only project governance review."""

from __future__ import annotations

import json
import sys


REVIEW_REASON = """【專案收尾審查：只提出候選，不要自行執行】
請在最終回覆前回顧本次任務中實際出現的衝突、錯誤、未完成或未驗證項目、重複摩擦，以及為了繼續工作而採用的 workaround。請在最終回覆新增「收尾改善候選」段落，分成以下三類：
1. 目前系統潛在問題：說明根因、可觀察證據與影響。
2. 建議修改專案規則／Skill：指出精確檔案位置、修改意圖、預期效果與驗證方式；若根因是實作缺陷，不要只新增規則。
3. 建議新增記憶：只提出可跨任務重用的偏好、決策或陷阱，並說明適用範圍與可能過時性。
每項都要標示證據，沒有候選時明確寫「未發現」。候選不是本次任務的自動交付：不要修改 AGENTS.md、.agents/skills、任何規則／Skill 檔案或記憶檔案，也不要建立、提交或發送治理變更。最後請明確詢問使用者要不要執行哪些候選；在使用者同意前維持只讀建議。"""


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = None

    # Fail open if Codex changes the input shape; the hook must not deadlock a task.
    if not isinstance(payload, dict) or payload.get("stop_hook_active") is True:
        print(json.dumps({"continue": True}, ensure_ascii=False))
        return 0

    print(
        json.dumps(
            {"decision": "block", "reason": REVIEW_REASON},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
