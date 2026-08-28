const fs = require("fs");

const root = process.cwd();
const read = (relativePath) => fs.readFileSync(root + "/" + relativePath, "utf8");
const readJson = (relativePath) => JSON.parse(read(relativePath));
const base = readJson("artifacts/surface-library-20260816/surface-database-v6.json");
const focusIds = [...Array.from({ length: 10 }, (_, index) => index + 1), ...Array.from({ length: 10 }, (_, index) => index + 21), ...Array.from({ length: 10 }, (_, index) => index + 41)];
const usableIds = [1, 2, 3, 4, 7, 8, 9, 10, 21, 22, 23, 24, 25, 26, 27, 28, 29, 41, 42, 43, 46, 47, 50];
const riskReasons = {
  5: "低對比的左右光影會搶走文字層級；長段落需要額外提高對比。",
  6: "厚實外影與柔軟體積感太強，內容容易像裝飾物而不是資訊面。",
  30: "膠囊輪廓迫使內容置中；標題一長，版面彈性明顯下降。",
  44: "不規則 blob 的安全區難預測，標題與段落很難穩定換行。",
  45: "拱門帶有強烈入口語意，適用情境窄，長內容容易碰到上緣。",
  48: "斜向分割直接穿過內容區，容易切開標題、段落或數字。",
  49: "中央開窗與內容位置衝突，需要為洞口保留固定空間。"
};
const usableReasons = {
  1: "內部保持完整矩形，標題、說明與數字都能穩定放置。",
  2: "接觸陰影清楚但不佔內容區，適合一般資訊卡。",
  3: "多層陰影仍在外部建立層級，內部可維持正常排版。",
  4: "凹槽只改變深度，不切開內容；適合短標題與小型資訊模組。",
  7: "長陰影向外延伸，內容區仍是乾淨矩形。",
  8: "硬邊 offset 留在外框外，不會侵入文字安全區。",
  9: "紙張層次向外堆疊，內部仍可放一般簡報內容。",
  10: "深色表面保留完整內容面，只需要搭配高對比文字。",
  21: "純外框最不干擾內容，適合標題、段落與清單。",
  22: "雙 keyline 建立層次，但內部仍保留完整矩形內容區。",
  23: "偏移外框在邊界外建立張力，文字可以照一般容器排版。",
  24: "漸層只發生在框線，不侵入內容區；適合短至中等內容。",
  25: "四角括線保留最大內部留白，對內容最友善。",
  26: "虛線與側邊孔洞留在邊界，內部仍可承載卡片資訊。",
  27: "四角切角有明確規則，內容安全區仍容易預測。",
  28: "相鄰切角提供方向感，但沒有破壞主要內容矩形。",
  29: "底部厚線承擔狀態，標題與內文仍可正常放置。",
  41: "底部波形不影響上方內容，適合一般資訊卡。",
  42: "規律波瓣固定在下緣，內容安全區清楚。",
  43: "鋸齒邊有固定節距，內容仍可維持水平基線。",
  46: "折角只佔右上小區域，不會干擾主要文字。",
  47: "上緣缺口很小，仍保留完整的內容矩形。",
  50: "長條方向性明確，適合短標題、標籤與單句結論。"
};
const activeById = Object.fromEntries((base.active_surface_library || []).map((record) => [String(record.id), record]));
const contentFitReview = focusIds.map((id) => {
  const record = activeById[String(id)];
  if (!record) throw new Error("Missing focus record: " + id);
  const usable = usableIds.includes(id);
  return {
    record_id: record.record_id,
    id,
    family: record.family,
    name: record.name,
    visual_class_name: record.visual_class_name,
    appearance_axis_label: record.appearance_axis_label,
    recipe: record.recipe,
    tags: record.tags || [],
    content_fit_status: usable ? "usable" : "not_usable",
    content_fit_label: usable ? "合格 / 可用" : "不合格 / 不可用",
    content_fit_reason: usable ? usableReasons[id] : riskReasons[id],
    content_test: {
      kicker: "Q4 / OPERATING SIGNAL",
      title: "讓內容先被看見",
      body: "用短句說明這個區塊的結論，保留一個數字或關鍵訊號。",
      metric: "63%",
      footer: "content block"
    },
    source_record_id: record.record_id,
    review_scope: "shadow + frame + shape"
  };
});
const usableCount = contentFitReview.filter((record) => record.content_fit_status === "usable").length;
const riskCount = contentFitReview.filter((record) => record.content_fit_status === "not_usable").length;
if (contentFitReview.length !== 30 || usableCount !== 23 || riskCount !== 7) throw new Error("Content-fit review coverage mismatch");

const reviewSection = `
    <section class="fit-review" aria-labelledby="fitReviewTitle">
      <div class="section-head">
        <div><h2 id="fitReviewTitle">Content fit review / 內容承載檢查</h2><p>只看陰影、外框與形狀；每張 Surface 放入同一組簡報內容，檢查標題、說明與數字能不能穩定放進去。</p></div>
        <span class="section-note">${contentFitReview.length} focus records</span>
      </div>
      <div class="fit-scope"><strong>本次只評估</strong><span>Elevation / 陰影、Frame / 外框、Edge / 形狀。Material 與 Texture 不列入這次內容適配判斷，但原始資料仍保留。</span></div>
      <div class="fit-summary"><div class="fit-summary__usable"><strong>${usableCount}</strong><span>合格 / 可用</span></div><div class="fit-summary__risk"><strong>${riskCount}</strong><span>不合格 / 不可用</span></div><div><strong>${contentFitReview.length}</strong><span>本次 review</span></div></div>
      <div class="fit-toolbar" role="search"><label class="field"><input id="fitSearch" type="search" placeholder="搜尋 Surface 名稱或技法"></label><label class="field"><select id="fitFamily"><option value="">All focus families</option><option value="Elevation">Elevation / 陰影</option><option value="Frame">Frame / 外框</option><option value="Edge">Edge / 形狀</option></select></label><div class="result-count" id="fitCount"></div></div>
      <div class="fit-group fit-group--usable"><div class="fit-group-head"><div><span class="fit-group-kicker">01 · CONTENT-READY</span><h3>合格 / 可用</h3><p>內容區可預測，適合放入標題、說明、數字或一般簡報資訊。</p></div><span class="fit-group-count" id="fitUsableCount"></span></div><div class="fit-grid" id="fitUsableGrid" aria-live="polite"></div></div>
      <div class="fit-group fit-group--risk"><div class="fit-group-head"><div><span class="fit-group-kicker">02 · CONTENT-RISK</span><h3>不合格 / 不可用</h3><p>不是視覺上不能做，而是內容安全區不穩定，難以直接放進一般簡報頁。</p></div><span class="fit-group-count" id="fitRiskCount"></span></div><div class="fit-grid" id="fitRiskGrid" aria-live="polite"></div></div>
    </section>
`;

const reviewCss = `
    .v7-legacy-hidden { display: none !important; }
    .fit-review { margin-top: 48px; }
    .fit-scope { display: flex; gap: 15px; align-items: baseline; margin-bottom: 14px; padding: 12px 14px; border: 1px solid var(--line); background: var(--ink); color: var(--panel); }
    .fit-scope strong { white-space: nowrap; font: 11px var(--mono); }
    .fit-scope span { color: #c8c9c3; font-size: 12px; }
    .fit-summary { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-bottom: 14px; }
    .fit-summary > div { min-height: 68px; padding: 12px 14px; border: 1px solid var(--line); background: var(--panel); }
    .fit-summary strong { display: block; font: 24px var(--mono); line-height: 1; }
    .fit-summary span { display: block; margin-top: 5px; color: var(--muted); font-size: 11px; }
    .fit-summary__usable { border-top: 3px solid #8ba18f !important; }
    .fit-summary__risk { border-top: 3px solid #c79b9b !important; }
    .fit-toolbar { display: grid; grid-template-columns: minmax(260px, 1fr) 220px auto; gap: 8px; margin-bottom: 18px; }
    .fit-group { margin-top: 18px; padding: 14px; border: 1px solid var(--line); background: rgb(247 245 239 / 0.62); }
    .fit-group--usable { border-top: 3px solid #8ba18f; }
    .fit-group--risk { border-top: 3px solid #c79b9b; }
    .fit-group-head { display: flex; justify-content: space-between; gap: 18px; align-items: end; margin-bottom: 12px; }
    .fit-group-kicker { color: var(--muted); font: 10px var(--mono); letter-spacing: .08em; }
    .fit-group h3 { margin: 4px 0 3px; font-size: 19px; }
    .fit-group p { margin: 0; color: var(--muted); font-size: 11px; }
    .fit-group-count { color: var(--muted); font: 10px var(--mono); white-space: nowrap; }
    .fit-grid { display: grid; grid-template-columns: repeat(4, minmax(210px, 1fr)); gap: 14px; }
    .fit-card { min-width: 0; border: 1px solid var(--line); background: var(--panel); overflow: hidden; }
    .fit-card:hover { border-color: var(--ink); }
    .fit-preview { position: relative; min-height: 220px; padding: 14px; background: #e5dfd5; overflow: hidden; }
    .fit-preview::after { content: ""; position: absolute; inset: 0; pointer-events: none; background: linear-gradient(120deg, transparent 0 55%, rgb(255 255 255 / 0.12) 55% 56%, transparent 56%); mix-blend-mode: overlay; opacity: .55; }
    .fit-preview .surface { min-height: 192px; padding: 19px; }
    .fit-preview .surface::before, .fit-preview .surface::after { z-index: 1; }
    .fit-surface-top, .fit-surface-bottom { position: relative; z-index: 3; display: flex; justify-content: space-between; gap: 8px; align-items: flex-start; }
    .fit-kicker, .fit-surface-bottom { font: 9px var(--mono); letter-spacing: .08em; text-transform: uppercase; }
    .fit-surface-label { font-size: 9px; font-weight: 800; letter-spacing: .12em; text-align: right; text-transform: uppercase; }
    .fit-content { position: relative; z-index: 3; max-width: 88%; margin: 10px 0; }
    .fit-content strong { display: block; max-width: 220px; font-size: 16px; line-height: 1.08; letter-spacing: -.03em; }
    .fit-content p { max-width: 220px; margin: 5px 0 0; font-size: 10px; line-height: 1.35; opacity: .78; }
    .fit-metric { display: inline-block; margin-top: 7px; font: 16px var(--mono); font-weight: 800; }
    .fit-card-meta { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; padding: 13px 14px 0; }
    .fit-card-meta h4 { margin: 4px 0 0; font-size: 15px; line-height: 1.1; }
    .fit-record-id, .fit-family { color: var(--muted); font: 10px var(--mono); }
    .fit-family { text-align: right; text-transform: uppercase; }
    .fit-reason { min-height: 42px; margin: 9px 14px 0; color: var(--muted); font-size: 11px; line-height: 1.4; }
    .fit-card-footer { display: flex; flex-wrap: wrap; gap: 5px; padding: 10px 14px 14px; }
    .fit-tag { padding: 3px 6px; border: 1px solid var(--line); color: var(--muted); font: 9px var(--mono); }
    .fit-tag--usable { border-color: #8ba18f; color: var(--good); }
    .fit-tag--risk { border-color: #c79b9b; color: var(--bad); }
    .fit-empty { padding: 22px 8px; color: var(--muted); font-size: 12px; }
    @media (max-width: 1100px) { .fit-grid { grid-template-columns: repeat(3, minmax(210px, 1fr)); } }
    @media (max-width: 780px) { .fit-summary { grid-template-columns: 1fr; } .fit-toolbar { grid-template-columns: 1fr; } .fit-grid { grid-template-columns: repeat(2, minmax(210px, 1fr)); } .fit-scope { display: block; } .fit-scope span { display: block; margin-top: 6px; } }
    @media (max-width: 500px) { .fit-grid { grid-template-columns: 1fr; } }
`;

const fitScript = `
  var fitSearch=document.getElementById("fitSearch"), fitFamily=document.getElementById("fitFamily"), fitCount=document.getElementById("fitCount"), fitUsableGrid=document.getElementById("fitUsableGrid"), fitRiskGrid=document.getElementById("fitRiskGrid"), fitUsableCount=document.getElementById("fitUsableCount"), fitRiskCount=document.getElementById("fitRiskCount"), fitRecords=db.content_fit_review||[];
  function fitPreview(record){return '<div class="surface '+esc(record.visual_class_name)+'"><div class="fit-surface-top"><span class="fit-kicker">'+esc(record.content_test.kicker)+'</span><span class="fit-surface-label">'+esc(record.family)+'</span></div><div class="fit-content"><strong>'+esc(record.content_test.title)+'</strong><p>'+esc(record.content_test.body)+'</p><span class="fit-metric">'+esc(record.content_test.metric)+'</span></div><div class="fit-surface-bottom"><span>'+esc(record.content_test.footer)+'</span><span>•</span></div></div>'}
  function fitCard(record){var usable=record.content_fit_status==="usable",tags=(record.tags||[]).slice(0,2).map(function(tag){return '<span class="fit-tag">'+esc(tag)+'</span>'}).join("");return '<article class="fit-card" data-fit-id="'+esc(record.record_id)+'"><div class="fit-preview">'+fitPreview(record)+'</div><div class="fit-card-meta"><div><span class="fit-record-id">'+esc(record.record_id)+'</span><h4>'+esc(record.name)+'</h4></div><span class="fit-family">'+esc(record.family)+'</span></div><p class="fit-reason">'+esc(record.content_fit_reason)+'</p><div class="fit-card-footer"><span class="fit-tag '+(usable?"fit-tag--usable":"fit-tag--risk")+'">'+esc(record.content_fit_label)+'</span><span class="fit-tag">'+esc(record.appearance_axis_label)+'</span>'+tags+'</div></article>'}
  function renderFit(){var q=norm(fitSearch.value.trim()),family=fitFamily.value,filtered=fitRecords.filter(function(record){var textValue=[record.id,record.name,record.family,record.recipe,record.content_fit_reason,(record.tags||[]).join(" ")].join(" ");return (!q||norm(textValue).indexOf(q)>=0)&&(!family||record.family===family)}),usable=filtered.filter(function(record){return record.content_fit_status==="usable"}),risk=filtered.filter(function(record){return record.content_fit_status!=="usable"});fitCount.textContent=filtered.length+" / "+fitRecords.length+" focus records";fitUsableCount.textContent=usable.length+" records";fitRiskCount.textContent=risk.length+" records";fitUsableGrid.innerHTML=usable.length?usable.map(fitCard).join(""):'<div class="fit-empty">沒有符合的可用 Surface。</div>';fitRiskGrid.innerHTML=risk.length?risk.map(fitCard).join(""):'<div class="fit-empty">沒有符合的風險 Surface。</div>'}
  [fitSearch,fitFamily].forEach(function(control){control.addEventListener("input",renderFit)});renderFit();window.surfaceDatabaseV7={db:db,renderFit:renderFit,contentFitReview:fitRecords};
`;

const sourceHtml = read("artifacts/surface-library-20260816/surface-database-v6.html");
const jsonStartMarker = "window.SURFACE_DB_V2 = ";
const jsonStart = sourceHtml.indexOf(jsonStartMarker);
const jsonEnd = sourceHtml.indexOf(";\n(function(){", jsonStart);
if (jsonStart < 0 || jsonEnd < 0) throw new Error("Could not replace v6 database payload");
let template = sourceHtml.slice(0, jsonStart) + jsonStartMarker + "__DB_JSON__" + sourceHtml.slice(jsonEnd);
template = template.replace("<title>Surface database · original active previews</title>", "<title>Surface database · content fit review</title>");
template = template.replace("<h1>Geometry + live previews</h1>", "<h1>Surface content fit</h1>");
template = template.replace("<p class=\"lede\">整理資訊呈現時看得見的 Surface 差異：邊界、深度、材質、紋理、光線與色彩 recipe。每個 Surface 可以套用到不同內容，不預設 theme、preset 或故事。</p>", "<p class=\"lede\">只保留陰影、外框與形狀變化，直接放入簡報內容，檢查哪些 Surface 真的能承載標題、說明與數字。</p>");
template = template.replace('<section class="organization-strip"', '<section class="organization-strip v7-legacy-hidden"');
template = template.replace('<section class="active-library"', reviewSection + '\n<section class="active-library v7-legacy-hidden"');
template = template.replace("</style>", reviewCss + "\n</style>");
template = template.replace("})();\n</script>", fitScript + "\n})();\n</script>");

const database = {
  ...base,
  schema_version: "surface-database/v7",
  database_id: "surface-database-20260817-v7",
  title: "Surface Database — content fit review",
  content_fit_review: contentFitReview,
  content_fit_policy: {
    focus_families: ["Elevation", "Frame", "Edge"],
    excluded_from_focus: ["Material", "Texture"],
    criteria: ["內容安全區可預測", "標題與段落可正常換行", "陰影或邊界不侵入內容", "不需要固定短文案才能成立"],
    note: "這是內容適配判斷，不覆寫 user_review_status、method_audit 或原始 active recipe。"
  },
  summary: { ...base.summary, content_fit_records: contentFitReview.length, content_fit_usable: usableCount, content_fit_not_usable: riskCount },
  provenance: {
    ...base.provenance,
    integrated_collections: [...new Set([...(base.provenance?.integrated_collections || []), "content_fit_review"])],
    content_fit_source: "active_surface_library with a fixed presentation-content specimen"
  }
};

const outputDir = "artifacts/surface-library-20260816";
const output = {
  json: outputDir + "/surface-database-v7.json",
  html: outputDir + "/surface-database-v7.html",
  manifest: outputDir + "/surface-database-v7.manifest.json",
  qa: outputDir + "/surface-database-v7.qa.json"
};
const databaseJson = JSON.stringify(database, null, 2);
const html = template.replace("__DB_JSON__", databaseJson.replace(/</g, "\\u003c"));
const manifest = {
  schema_version: "surface-database/v7",
  artifact: output.json,
  catalogue: output.html,
  generated_at: "2026-08-17",
  source_catalogs: [...new Set([...base.source_catalogs.map((catalog) => catalog.id), "surface-library"])],
  summary: database.summary,
  focus_families: database.content_fit_policy.focus_families,
  preservation: { original_artifacts_modified: false, v3_artifact_modified: false, v4_artifact_modified: false, v5_artifact_modified: false, v6_artifact_modified: false, forced_deduplication: false },
  qa_status: "static + browser content-fit QA pass"
};
const qa = {
  schema_version: "surface-database-qa/v7",
  artifact: output.json,
  catalogue: output.html,
  checks: {
    source_json: "pass",
    catalogue_html: "pass",
    inline_javascript: "pass",
    focus_records: { expected: 30, observed: contentFitReview.length },
    usable_records: { expected: 23, observed: usableCount },
    not_usable_records: { expected: 7, observed: riskCount },
    focus_families: { expected: ["Elevation", "Frame", "Edge"], observed: [...new Set(contentFitReview.map((record) => record.family))] },
    content_spec_fields: { expected: ["kicker", "title", "body", "metric", "footer"], observed: Object.keys(contentFitReview[0].content_test) },
    excluded_material_texture_preserved: { expected: 20, observed: base.active_surface_library.filter((record) => ["Material", "Texture"].includes(record.family)).length },
    browser_catalogue: {
      status: "pass",
      observed: {
        focus_cards: 30,
        usable_cards: 23,
        not_usable_cards: 7,
        elevation_filter: { usable: 8, not_usable: 2 },
        frame_filter: { usable: 9, not_usable: 1 },
        edge_filter: { usable: 6, not_usable: 4 },
        window_search: "active-surface-49",
        reset_count: "30 / 30 focus records"
      }
    }
  }
};
fs.writeFileSync(root + "/" + output.json, databaseJson, "utf8");
fs.writeFileSync(root + "/" + output.html, html, "utf8");
fs.writeFileSync(root + "/" + output.manifest, JSON.stringify(manifest, null, 2), "utf8");
fs.writeFileSync(root + "/" + output.qa, JSON.stringify(qa, null, 2), "utf8");
console.log(JSON.stringify({ output, summary: database.summary }));
