# 任務完成收尾審查 Hook

這個專案 hook 綁定 Codex 的 `Stop` 事件。模型第一次準備結束任務時，hook 會要求它回顧本次工作中的衝突、問題、未驗證項目與流程摩擦，並在最終回覆提出三類候選：

- 目前系統潛在問題
- 專案規則／Skill 的修改建議
- 建議新增的記憶

它是 proposal-only：不會自行修改規則、Skill、記憶、Git 或遠端狀態。最終回覆必須把候選交給使用者決定；只有使用者明確同意後，才另開後續修改流程。

`task_completion_review.py` 會在第一次 `Stop` 回合回傳 `decision: block`，讓 Codex 只續談一次；讀到 `stop_hook_active: true` 時放行，避免無限續談。若 hook 輸入格式異常，則採 fail-open，讓任務正常結束。

Codex 需要先對新 hook 做 review/trust；可在 CLI 使用 `/hooks` 檢查並信任目前這份 hook。修改 hook 定義後，需重新 review/trust。
