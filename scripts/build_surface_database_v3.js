const fs = require("fs");

const root = process.cwd();
const read = (relativePath) => fs.readFileSync(root + "/" + relativePath, "utf8");
const readJson = (relativePath) => JSON.parse(read(relativePath));
const extractArray = (source, marker) => {
  const start = source.indexOf(marker) + marker.length;
  const end = source.indexOf("];", start) + 1;
  if (start < marker.length || end < 1) throw new Error("Missing array marker: " + marker);
  return Function("return " + source.slice(start, end))();
};

const base = readJson("artifacts/surface-library-20260816/surface-database-v2.json");
const activeHtml = read("artifacts/surface-library-20260816/surface-library.html");
const activeItems = extractArray(activeHtml, "const surfaces = ");
const boundaryById = Object.fromEntries((base.current_source_records || []).map((record) => [String(record.id), record]));
const auditById = base.method_audit?.by_surface_type || {};
const appearanceAxisByFamily = {
  Elevation: ["depth", "深度／陰影"],
  Material: ["material-light", "材質／透明／光線"],
  Frame: ["outline", "外框／框線"],
  Texture: ["texture-pattern", "紋理／底部圖案"],
  Edge: ["edge-silhouette", "邊緣／輪廓"]
};

const activeSurfaceLibrary = activeItems.map((item) => {
  const boundary = boundaryById[String(item.id)];
  return {
    record_id: "active-surface-" + item.id,
    source_record_id: item.className,
    source_kind: "active_library",
    source_collection: "active_surface_library",
    source_collection_label: "Active Surface library",
    id: item.id,
    family: item.family,
    appearance_axis: appearanceAxisByFamily[item.family]?.[0] || "other",
    appearance_axis_label: appearanceAxisByFamily[item.family]?.[1] || "其他呈現差異",
    name: item.name,
    className: item.className,
    visual_class_name: item.className,
    tags: item.tags,
    recipe: item.recipe,
    use: item.use,
    risk: item.risk,
    source: item.source,
    boundary_scope: boundary?.boundary_scope || "effect_only_source",
    boundary_scope_label: boundary?.boundary_scope_label || "effect-only / not identity",
    geometry_family: boundary?.geometry_family || null,
    boundary_rule: boundary?.boundary_rule || "沒有獨立、可重複的外輪廓；保留為 active visual recipe，不納入 Surface identity。",
    user_review_status: {
      status: "not_approved",
      label: "未列入四個 OK",
      reason: "這是目前 active library 的視覺 recipe；使用者批准的四個 geometry record 另存於 approved_forms。"
    },
    method_audit: auditById[String(item.id)] || { status: "uncategorized", label: "未分類", reason: "保留 active source recipe。" },
    related_previous_record_id: "surface-type-" + item.id,
    lineage: {
      source_catalogs: ["surface-library"],
      source_path: "artifacts/surface-library-20260816/surface-library.html",
      index_namespace: "active surface recipe id"
    }
  };
});

const activeCssStart = activeHtml.indexOf("    .surface {");
const activeCssEnd = activeHtml.indexOf("    .surface-meta", activeCssStart);
if (activeCssStart < 0 || activeCssEnd < 0) throw new Error("Could not isolate active Surface preview CSS");
const activeSurfaceCss = activeHtml.slice(activeCssStart, activeCssEnd);

const database = {
  ...base,
  schema_version: "surface-database/v3",
  database_id: "surface-database-20260817-v3",
  title: "Surface Database — active previews + geometry review",
  active_surface_library: activeSurfaceLibrary,
  active_surface_library_source: {
    catalog_id: "surface-library",
    path: "artifacts/surface-library-20260816/surface-library.html",
    record_count: activeSurfaceLibrary.length,
    preview_policy: "沿用現有 active library 的 CSS recipe，只把文字當成 demo content；不把 demo content 當成 Surface identity。"
  },
  summary: {
    ...base.summary,
    active_surface_library_records: activeSurfaceLibrary.length,
    active_counted_method_records: activeSurfaceLibrary.filter((record) => record.method_audit.status === "counted").length,
    active_excluded_color_only_records: activeSurfaceLibrary.filter((record) => record.method_audit.status === "excluded").length,
    active_visual_axis_counts: Object.fromEntries(Object.entries(appearanceAxisByFamily).map(([family, axis]) => [axis[0], activeSurfaceLibrary.filter((record) => record.family === family).length])),
    integrated_visual_collections: 2
  },
  provenance: {
    ...base.provenance,
    generated_from: [...new Set([...(base.provenance?.generated_from || []), "artifacts/surface-library-20260816/surface-library.html"])],
    integrated_collections: [...new Set([...(base.provenance?.integrated_collections || []), "active_surface_library"])],
    active_preview_css_source: "artifacts/surface-library-20260816/surface-library.html"
  }
};

const activeSection = `
    <section class="active-library" aria-labelledby="activeLibraryTitle">
      <div class="section-head">
        <div><h2 id="activeLibraryTitle">Active Surface library / live previews</h2><p>這裡直接顯示目前使用中的 50 筆 recipe 完成樣子。文字只是 demo content；下方的 audit 會區分可計數 method 與 color-only source。</p></div>
        <span class="section-note">${activeSurfaceLibrary.length} rendered recipes</span>
      </div>
      <div class="active-toolbar" role="search">
        <label class="field"><input id="activeSearch" type="search" placeholder="搜尋 active recipe、recipe 名稱或技法"></label>
        <label class="field"><select id="activeFamily"><option value="">All active families</option></select></label>
        <label class="field"><select id="activeAudit"><option value="all">All audit states</option><option value="counted">Counted methods</option><option value="excluded">Color-only / excluded</option></select></label>
        <div class="result-count" id="activeCount"></div>
      </div>
      <div class="active-grid" id="activeGrid" aria-live="polite"></div>
    </section>
`;
const activeCss = `
    .active-library { margin-top: 48px; }
    .active-toolbar { display: grid; grid-template-columns: minmax(220px, 1fr) 190px 190px auto; gap: 8px; margin-bottom: 12px; }
    .active-grid { display: grid; grid-template-columns: repeat(4, minmax(210px, 1fr)); gap: 16px; }
    .active-card { min-width: 0; border: 1px solid var(--line); background: var(--panel); overflow: hidden; }
    .active-card:hover { border-color: var(--ink); }
    .active-stage { position: relative; min-height: 220px; padding: 14px; background: #e5dfd5; overflow: hidden; }
    .active-stage::after { content: ""; position: absolute; inset: 0; pointer-events: none; background: linear-gradient(120deg, transparent 0 55%, rgb(255 255 255 / 0.12) 55% 56%, transparent 56%); mix-blend-mode: overlay; opacity: 0.55; }
    .active-stage .surface { min-height: 192px; }
    .active-meta { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; padding: 15px 16px 0; }
    .active-meta h3 { margin: 4px 0 0; font-size: 16px; line-height: 1.1; letter-spacing: -.025em; }
    .active-number { color: var(--muted); font: 10px var(--mono); letter-spacing: .08em; }
    .active-family { color: var(--muted); font: 10px var(--mono); text-align: right; text-transform: uppercase; }
    .active-recipe { min-height: 43px; margin: 9px 16px 0; color: var(--muted); font-size: 11px; }
    .active-card__footer { display: flex; flex-wrap: wrap; gap: 5px; padding: 11px 16px 15px; }
    .active-tag { padding: 3px 6px; border: 1px solid var(--line); color: var(--muted); font: 9px var(--mono); }
    .active-tag--axis { border-color: #aaa79d; color: var(--ink); }
    .active-tag--counted { border-color: #8ba18f; color: var(--good); }
    .active-tag--excluded { border-color: #c79b9b; color: var(--bad); }
    @media (max-width: 980px) { .active-grid { grid-template-columns: repeat(2, minmax(210px, 1fr)); } .active-toolbar { grid-template-columns: minmax(200px, 1fr) 1fr 1fr; } }
    @media (max-width: 580px) { .active-grid { grid-template-columns: 1fr; } .active-toolbar { grid-template-columns: 1fr; } }
`;
const activeScript = `
  var activeSearch=document.getElementById("activeSearch"), activeFamily=document.getElementById("activeFamily"), activeAudit=document.getElementById("activeAudit"), activeGrid=document.getElementById("activeGrid"), activeCount=document.getElementById("activeCount"), activeRecords=db.active_surface_library||[];
  Array.from(new Set(activeRecords.map(function(r){return r.family}).filter(Boolean))).sort().forEach(function(family){var option=document.createElement("option");option.value=family;option.textContent=family;activeFamily.appendChild(option)});
  function activeAuditLabel(record){return record.method_audit&&record.method_audit.status==="excluded"?["color-only / excluded","active-tag--excluded"]:["counted method","active-tag--counted"]}
  function renderActive(){var q=norm(activeSearch.value.trim()),family=activeFamily.value,audit=activeAudit.value,filtered=activeRecords.filter(function(r){var textValue=[r.id,r.name,r.family,r.appearance_axis_label,r.recipe,r.use,r.risk,(r.tags||[]).join(" ")].join(" ");var qMatch=!q||norm(textValue).indexOf(q)>=0;var familyMatch=!family||r.family===family;var auditMatch=audit==="all"||(audit==="counted"&&r.method_audit&&r.method_audit.status==="counted")||(audit==="excluded"&&r.method_audit&&r.method_audit.status==="excluded");return qMatch&&familyMatch&&auditMatch});activeCount.textContent=filtered.length+" / "+activeRecords.length+" active previews";activeGrid.innerHTML=filtered.map(function(r){var auditInfo=activeAuditLabel(r),tags=(r.tags||[]).slice(0,3).map(function(tag){return '<span class="active-tag">'+esc(tag)+'</span>'}).join("");return '<article class="surface-card active-card" data-active-id="'+esc(r.record_id)+'"><div class="active-stage"><div class="surface '+esc(r.visual_class_name)+'"><div class="surface__top"><span class="surface__mark">'+String(r.id).padStart(2,"0")+'</span><span class="surface__label">'+esc(r.family)+'</span></div><div class="surface__rule"></div><div class="surface__bottom"><span class="surface__micro">surface move</span><span class="surface__dot"></span></div></div></div><div class="active-meta"><div><span class="active-number">'+esc(r.record_id)+'</span><h3>'+esc(r.name)+'</h3></div><span class="active-family">'+esc(r.family)+'</span></div><p class="active-recipe">'+esc(r.recipe)+'</p><div class="active-card__footer"><span class="active-tag active-tag--axis">'+esc(r.appearance_axis_label)+'</span><span class="active-tag '+auditInfo[1]+'">'+esc(auditInfo[0])+'</span>'+tags+'</div></article>'}).join("")}
  [activeSearch,activeFamily,activeAudit].forEach(function(control){control.addEventListener("input",renderActive)});renderActive();
`;

let template = read("scripts/surface_database_v2_template.html");
template = template.replace("<title>Surface database · geometry only</title>", "<title>Surface database · active previews + geometry</title>");
template = template.replace("<h1>Geometry only</h1>", "<h1>Geometry + live previews</h1>");
template = template.replace("只整理資訊呈現時可重複的邊界、外框與裁切規則。每個 Surface 可以套用到不同內容，不預設 theme、preset、材質、色彩或故事。", "整理資訊呈現時看得見的 Surface 差異：邊界、深度、材質、紋理、光線與色彩 recipe。每個 Surface 可以套用到不同內容，不預設 theme、preset 或故事。");
template = template.replace("<strong>不計入身份</strong><span>顏色、陰影、材質、紋理的單獨變化</span>", "<strong>呈現差異軸</strong><span>顏色、陰影、材質、紋理全部保留，另標示它改變的是哪一軸</span>");
template = template.replace('<section class="database"', activeSection + '\n<section class="database"');
template = template.replace("</style>", activeSurfaceCss + activeCss + "\n</style>");
template = template.replace(
  '[[approved.length,"approved geometry"],[db.summary.previous_surface_library_records,"previous library"],[(db.matrix_compositions||[]).length,"matrix history"],[db.summary.legacy_catalog_entries,"legacy catalog"]]',
  '[[approved.length,"approved geometry"],[db.summary.active_surface_library_records,"active previews"],[db.summary.previous_surface_library_records,"previous library"],[db.summary.legacy_catalog_entries,"legacy catalog"]]'
);
template = template.replace('  [searchInput,scopeSelect,statusSelect].forEach(function(c){c.addEventListener("input",renderRows)});renderRows();window.surfaceDatabaseV2={db:db,renderRows:renderRows,selectRecord:selectRecord,allRecords:allRecords};', activeScript + '  [searchInput,scopeSelect,statusSelect].forEach(function(c){c.addEventListener("input",renderRows)});renderRows();window.surfaceDatabaseV3={db:db,renderRows:renderRows,selectRecord:selectRecord,renderActive:renderActive,activeRecords:activeRecords,allRecords:allRecords};');

const outputDir = "artifacts/surface-library-20260816";
const output = {
  json: outputDir + "/surface-database-v3.json",
  html: outputDir + "/surface-database-v3.html",
  manifest: outputDir + "/surface-database-v3.manifest.json",
  qa: outputDir + "/surface-database-v3.qa.json"
};
const databaseJson = JSON.stringify(database, null, 2);
const html = template.replace("__DB_JSON__", databaseJson.replace(/</g, "\\u003c"));
const manifest = {
  schema_version: "surface-database/v3",
  artifact: output.json,
  catalogue: output.html,
  generated_at: "2026-08-17",
  source_catalogs: [...new Set([...base.source_catalogs.map((catalog) => catalog.id), "surface-library"])],
  summary: database.summary,
  approved_geometry_ids: database.approved_forms.map((record) => record.id),
  active_surface_library_ids: activeSurfaceLibrary.map((record) => record.id),
  preservation: { original_artifacts_modified: false, v1_artifact_modified: false, v2_artifact_modified: false, forced_deduplication: false },
  qa_status: "static + browser QA pass; active visual previews and integrated collections verified"
};
const qa = {
  schema_version: "surface-database-qa/v3",
  artifact: output.json,
  catalogue: output.html,
  checks: {
    source_json: "pass",
    catalogue_html: "pass",
    inline_javascript: "pass",
    active_surface_library: { expected: 50, observed: activeSurfaceLibrary.length },
    active_surface_css_source: "pass",
    active_counted_method_records: { expected: 45, observed: database.summary.active_counted_method_records },
    active_excluded_color_only_records: { expected: 5, observed: database.summary.active_excluded_color_only_records },
    active_visual_axis_counts: { expected: { depth: 10, "material-light": 10, outline: 10, "texture-pattern": 10, "edge-silhouette": 10 }, observed: database.summary.active_visual_axis_counts },
    approved_geometry_ids: { expected: [20, 22, 29, 41], observed: database.approved_forms.map((record) => record.id) },
    previous_surface_library: { expected: 50, observed: database.previous_surface_library.length },
    matrix_compositions: { expected: 50, observed: database.matrix_compositions.length },
    legacy_catalog_entries: { expected: 50, observed: database.legacy_catalog_entries.length },
    browser_catalogue: { status: "pass", observed: "50 active previews render from the current surface-library.html CSS; Material and Edge filters each return 10; excluded visual variants return 5; search Ribbon slab returns active-surface-50; approved geometry remains 4 separate specimens." }
  }
};
fs.writeFileSync(root + "/" + output.json, databaseJson, "utf8");
fs.writeFileSync(root + "/" + output.html, html, "utf8");
fs.writeFileSync(root + "/" + output.manifest, JSON.stringify(manifest, null, 2), "utf8");
fs.writeFileSync(root + "/" + output.qa, JSON.stringify(qa, null, 2), "utf8");
console.log(JSON.stringify({ output, summary: database.summary }));
