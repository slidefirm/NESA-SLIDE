# Art Direction Core

這個目錄是 Story 與 Theme／Layout 選擇之間的共用藝術指導層。
它不是新 Theme、不是 Layout fork，也不是 HTML 專用設定。

## 正式流程

```text
Story
→ Art Direction Brief
→ Reference Packet
→ Scene Grammar
→ 人工選定方向
→ Theme／Layout
→ Image2、HTML 或 PPTX
→ Technical QA
→ Perceptual QA
```

## 檔案

- `schema.yaml`：正式欄位、enum 與 gate。
- `template.yaml`：新專案可填寫的空白模板。
- `examples/`：可驗證的示範；不是可直接複製內容的 Theme。
- `scripts/art_direction.py`：驗證、產生跨 Renderer handoff。

## 狀態

- `draft`：還在填寫，不得進正式 renderer。
- `ready-for-audition`：可以製作三頁方向試演，但不得正式發布。
- `approved-for-renderer`：machine 與 human gate 都通過，可進正式 renderer。
- `rejected`：保留原因，但不得繼續生成。

## Renderer 邊界

- Image2 仍使用原本七段式 assembled YAML。Art Direction 只合併進七個既有區段，
  不增加第八個 top-level section。
- HTML 可從 Art Direction 選取 Theme／Layout sequence，並把 scene role、
  visual intensity 與 signature move variant 寫進 HTML `data-*` 與 manifest。
- PPTX 把相同 handoff 寫入 deck manifest，並以可編輯 master、layout、
  placeholder 與素材 provenance 實作。

## Gate

```powershell
python scripts\art_direction.py prompt_system\art_direction\examples\midnight-field-notes.yaml
python scripts\art_direction.py <brief.yaml> --require-approved --emit-handoff <handoff.json>
```

未通過 `--require-approved` 的方向可以試演，但不得標記為正式成品或部署。
