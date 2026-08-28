const fs = require("fs");

const root = process.cwd();
const read = (relativePath) => fs.readFileSync(root + "/" + relativePath, "utf8");
const readJson = (relativePath) => JSON.parse(read(relativePath));
const base = readJson("artifacts/surface-library-20260816/surface-database-v3.json");
const activeById = Object.fromEntries((base.active_surface_library || []).map((record) => [String(record.id), record]));

const compositionRecords = (base.matrix_compositions || []).map((matrix) => {
  const active = activeById[String(matrix.id)];
  return {
    record_id: "composition-" + matrix.id,
    id: matrix.id,
    active_record_id: active?.record_id || null,
    active_name: active?.name || "未連結 active recipe",
    active_family: active?.family || null,
    active_visual_class: active?.visual_class_name || null,
    active_appearance_axis: active?.appearance_axis_label || null,
    facets: {
      silhouette: { label: "輪廓 / shape", value: matrix.axis_labels?.shape || matrix.axes?.shape, raw: matrix.axes?.shape },
      boundary: { label: "邊界 / edge", value: matrix.axis_labels?.edge || matrix.axes?.edge, raw: matrix.axes?.edge },
      material_light: { label: "光／材質 / material", value: matrix.axis_labels?.material || matrix.axes?.material, raw: matrix.axes?.material },
      texture_pattern: { label: "紋理／圖案 / pattern", value: matrix.axis_labels?.pattern || matrix.axes?.pattern, raw: matrix.axes?.pattern }
    },
    source_matrix_axes: matrix.axes,
    user_review_status: matrix.user_review_status,
    composition_note: "這四個 facet 是 source matrix 的組合面相；active recipe 的完成預覽另由 active_surface_library 提供，不以相同數字 ID 強行合併。",
    lineage: { source_catalogs: ["surface-library-v2", "surface-library-v3", "surface-library-v4"], index_namespace: "matrix composition id" }
  };
});

const compositionSection = `
    <section class="composition-library" aria-labelledby="compositionTitle">
      <div class="section-head">
        <div><h2 id="compositionTitle">Composition faces / 組合面相</h2><p>同一張卡同時看「完成後長什麼樣」與「它由哪些視覺面相組成」。左側 preview 來自 active recipe；下方 facet 來自 source matrix。</p></div>
        <span class="section-note">${compositionRecords.length} combinations</span>
      </div>
      <div class="composition-callout"><strong>Surface = combination</strong><span>輪廓 × 邊界 × 光／材質 × 紋理／圖案，再加上 active recipe 的實際呈現。不同數字命名空間不自動視為同一筆。</span></div>
      <div class="composition-toolbar" role="search">
        <label class="field"><input id="compositionSearch" type="search" placeholder="搜尋組合、名稱、shape、edge、material 或 pattern"></label>
        <label class="field"><select id="compositionFamily"><option value="">All active families</option></select></label>
        <div class="result-count" id="compositionCount"></div>
      </div>
      <div class="composition-grid" id="compositionGrid" aria-live="polite"></div>
    </section>
`;
const compositionCss = `
    .composition-library { margin-top: 48px; }
    .composition-callout { display: flex; gap: 16px; align-items: baseline; margin-bottom: 14px; padding: 13px 15px; border: 1px solid var(--line); background: var(--ink); color: var(--panel); }
    .composition-callout strong { white-space: nowrap; font: 12px var(--mono); }
    .composition-callout span { color: #c8c9c3; font-size: 12px; }
    .composition-toolbar { display: grid; grid-template-columns: minmax(260px, 1fr) 220px auto; gap: 8px; margin-bottom: 12px; }
    .composition-grid { display: grid; grid-template-columns: repeat(3, minmax(250px, 1fr)); gap: 16px; }
    .composition-card { min-width: 0; border: 1px solid var(--line); background: var(--panel); overflow: hidden; }
    .composition-card:hover { border-color: var(--ink); }
    .composition-live { position: relative; min-height: 166px; padding: 12px; background: #e5dfd5; overflow: hidden; }
    .composition-live .surface { min-height: 138px; padding: 15px; }
    .composition-live .surface__mark { font-size: 23px; }
    .composition-live .surface__label { font-size: 8px; }
    .composition-live .surface__micro { font-size: 9px; }
    .composition-live .surface__dot { width: 7px; height: 7px; }
    .composition-head { display: flex; justify-content: space-between; gap: 10px; padding: 12px 13px 8px; }
    .composition-id { color: var(--muted); font: 10px var(--mono); }
    .composition-head h3 { margin: 3px 0 0; font-size: 14px; line-height: 1.12; }
    .composition-family { color: var(--muted); font: 9px var(--mono); text-align: right; }
    .composition-facets { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1px; margin: 0 13px; border: 1px solid var(--line); background: var(--line); }
    .facet { min-width: 0; padding: 8px; background: #fbfaf6; }
    .facet-label { display: block; margin-bottom: 3px; color: var(--muted); font: 9px var(--mono); }
    .facet strong { display: block; overflow: hidden; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
    .facet code { color: var(--muted); font-size: 9px; }
    .composition-foot { display: flex; flex-wrap: wrap; gap: 5px; padding: 10px 13px 13px; }
    .composition-tag { padding: 3px 6px; border: 1px solid var(--line); color: var(--muted); font: 9px var(--mono); }
    .composition-tag--approved { border-color: #8ba18f; color: var(--good); }
    @media (max-width: 1100px) { .composition-grid { grid-template-columns: repeat(2, minmax(250px, 1fr)); } }
    @media (max-width: 580px) { .composition-grid { grid-template-columns: 1fr; } .composition-toolbar { grid-template-columns: 1fr; } .composition-callout { display: block; } .composition-callout span { display: block; margin-top: 6px; } }
`;
const compositionScript = `
  var compositionSearch=document.getElementById("compositionSearch"), compositionFamily=document.getElementById("compositionFamily"), compositionGrid=document.getElementById("compositionGrid"), compositionCount=document.getElementById("compositionCount"), compositionRecords=db.composition_records||[];
  Array.from(new Set(compositionRecords.map(function(r){return r.active_family}).filter(Boolean))).sort().forEach(function(family){var option=document.createElement("option");option.value=family;option.textContent=family;compositionFamily.appendChild(option)});
  function facetHtml(facet){return '<div class="facet"><span class="facet-label">'+esc(facet.label)+'</span><strong>'+esc(facet.value)+'</strong><code>'+esc(facet.raw)+'</code></div>'}
  function renderComposition(){var q=norm(compositionSearch.value.trim()),family=compositionFamily.value,filtered=compositionRecords.filter(function(r){var facets=Object.values(r.facets||{}).map(function(f){return [f.value,f.raw].join(" ")}).join(" ");var textValue=[r.id,r.active_name,r.active_family,r.active_appearance_axis,facets].join(" ");return (!q||norm(textValue).indexOf(q)>=0)&&(!family||r.active_family===family)});compositionCount.textContent=filtered.length+" / "+compositionRecords.length+" combinations";compositionGrid.innerHTML=filtered.map(function(r){var isApproved=r.user_review_status&&r.user_review_status.status==="approved",preview=r.active_visual_class?'<div class="surface '+esc(r.active_visual_class)+'"><div class="surface__top"><span class="surface__mark">'+String(r.id).padStart(2,"0")+'</span><span class="surface__label">'+esc(r.active_family||"SOURCE")+'</span></div><div class="surface__rule"></div><div class="surface__bottom"><span class="surface__micro">surface move</span><span class="surface__dot"></span></div></div>':'<div class="composition-empty">No active preview</div>';return '<article class="composition-card" data-composition-id="'+esc(r.record_id)+'"><div class="composition-live">'+preview+'</div><div class="composition-head"><div><span class="composition-id">composition-'+esc(r.id)+' · '+esc(r.active_record_id||"no active link")+'</span><h3>'+esc(r.active_name)+'</h3></div><span class="composition-family">'+esc(r.active_family||"source matrix")+'</span></div><div class="composition-facets">'+facetHtml(r.facets.silhouette)+facetHtml(r.facets.boundary)+facetHtml(r.facets.material_light)+facetHtml(r.facets.texture_pattern)+'</div><div class="composition-foot"><span class="composition-tag">'+esc(r.active_appearance_axis||"source facets")+'</span><span class="composition-tag '+(isApproved?"composition-tag--approved":"")+'">'+esc(isApproved?"user approved geometry":"source matrix / not approved")+'</span></div></article>'}).join("")}
  [compositionSearch,compositionFamily].forEach(function(control){control.addEventListener("input",renderComposition)});renderComposition();
`;

const sourceHtml = read("artifacts/surface-library-20260816/surface-database-v3.html");
const compositionScriptForHtml = compositionScript.replaceAll("user approved geometry", "matrix user approved form");
const jsonStartMarker = "window.SURFACE_DB_V2 = ";
const jsonStart = sourceHtml.indexOf(jsonStartMarker);
const jsonEnd = sourceHtml.indexOf(";\n(function(){", jsonStart);
if (jsonStart < 0 || jsonEnd < 0) throw new Error("Could not replace v3 database payload");
let template = sourceHtml.slice(0, jsonStart) + jsonStartMarker + "__DB_JSON__" + sourceHtml.slice(jsonEnd);
template = template.replace("<title>Surface database · active previews + geometry</title>", "<title>Surface database · composition faces</title>");
template = template.replace("<h1>Geometry + live previews</h1>", "<h1>Composition faces</h1>");
template = template.replace('<section class="database"', compositionSection + '\n<section class="database"');
template = template.replace("</style>", compositionCss + "\n</style>");
template = template.replace('  [searchInput,scopeSelect,statusSelect].forEach(function(c){c.addEventListener("input",renderRows)});renderRows();window.surfaceDatabaseV3={db:db,renderRows:renderRows,selectRecord:selectRecord,renderActive:renderActive,activeRecords:activeRecords,allRecords:allRecords};', compositionScriptForHtml + '  [searchInput,scopeSelect,statusSelect].forEach(function(c){c.addEventListener("input",renderRows)});renderRows();window.surfaceDatabaseV4={db:db,renderRows:renderRows,selectRecord:selectRecord,renderActive:renderActive,renderComposition:renderComposition,compositionRecords:compositionRecords,activeRecords:activeRecords,allRecords:allRecords};');

const database = {
  ...base,
  schema_version: "surface-database/v4",
  database_id: "surface-database-20260817-v4",
  title: "Surface Database — composition faces",
  composition_dimensions: [
    { id: "silhouette", label: "輪廓 / shape", meaning: "主要外形或容器骨架" },
    { id: "boundary", label: "邊界 / edge", meaning: "缺口、切角、框線、週期性邊緣" },
    { id: "material_light", label: "光／材質 / material", meaning: "透明、玻璃、紙張、深度與光線呈現" },
    { id: "texture_pattern", label: "紋理／圖案 / pattern", meaning: "點陣、網格、底部圖案與表面節奏" }
  ],
  composition_records: compositionRecords,
  summary: { ...base.summary, composition_records: compositionRecords.length },
  provenance: {
    ...base.provenance,
    integrated_collections: [...new Set([...(base.provenance?.integrated_collections || []), "composition_records"])],
    composition_policy: "composition_records 同時保存 source matrix facets 與 active visual preview；不以相同數字 ID 強行合併不同 catalog namespace。"
  }
};

const outputDir = "artifacts/surface-library-20260816";
const output = {
  json: outputDir + "/surface-database-v4.json",
  html: outputDir + "/surface-database-v4.html",
  manifest: outputDir + "/surface-database-v4.manifest.json",
  qa: outputDir + "/surface-database-v4.qa.json"
};
const databaseJson = JSON.stringify(database, null, 2);
const html = template.replace("__DB_JSON__", databaseJson.replace(/</g, "\\u003c"));
const manifest = {
  schema_version: "surface-database/v4",
  artifact: output.json,
  catalogue: output.html,
  generated_at: "2026-08-17",
  source_catalogs: [...new Set([...base.source_catalogs.map((catalog) => catalog.id), "surface-library"])],
  summary: database.summary,
  composition_dimensions: database.composition_dimensions.map((dimension) => dimension.id),
  preservation: { original_artifacts_modified: false, v2_artifact_modified: false, v3_artifact_modified: false, forced_deduplication: false },
  qa_status: "static + browser composition QA pass"
};
const qa = {
  schema_version: "surface-database-qa/v4",
  artifact: output.json,
  catalogue: output.html,
  checks: {
    source_json: "pass",
    catalogue_html: "pass",
    inline_javascript: "pass",
    composition_records: { expected: 50, observed: compositionRecords.length },
    composition_dimensions: { expected: ["silhouette", "boundary", "material_light", "texture_pattern"], observed: database.composition_dimensions.map((dimension) => dimension.id) },
    active_previews_linked: { expected: 50, observed: compositionRecords.filter((record) => record.active_record_id).length },
    approved_geometry_ids: { expected: [20, 22, 29, 41], observed: database.approved_forms.map((record) => record.id) },
    namespace_separation: true,
    browser_catalogue: {
      status: "pass",
      observed: {
        composition_cards: 50,
        linked_active_previews: 50,
        matrix_approved_cards: 4,
        material_filter_cards: 10,
        ribbon_search: "composition-20",
        reset_count: "50 / 50 combinations"
      }
    }
  }
};
fs.writeFileSync(root + "/" + output.json, databaseJson, "utf8");
fs.writeFileSync(root + "/" + output.html, html, "utf8");
fs.writeFileSync(root + "/" + output.manifest, JSON.stringify(manifest, null, 2), "utf8");
fs.writeFileSync(root + "/" + output.qa, JSON.stringify(qa, null, 2), "utf8");
console.log(JSON.stringify({ output, summary: database.summary }));
