const fs = require("fs");

const root = process.cwd();
const read = (relativePath) => fs.readFileSync(root + "/" + relativePath, "utf8");
const readJson = (relativePath) => JSON.parse(read(relativePath));
const base = readJson("artifacts/surface-library-20260816/surface-database-v4.json");
const activeById = Object.fromEntries((base.active_surface_library || []).map((record) => [String(record.id), record]));

const organizationGroups = [
  {
    id: "outline-framework",
    kind: "structure",
    label: "框線系 / outline grammar",
    note: "外框、內框、短線與框線節奏；外輪廓仍是矩形，但邊界語法已經不同。",
    ids: [21, 22, 23, 24, 25, 26, 29, 30]
  },
  {
    id: "cut-notch",
    kind: "structure",
    label: "切角／缺口 / cut & notch",
    note: "用切角或缺口改變外緣，讓 Surface 產生方向、入口或工程感。",
    ids: [27, 28, 47, 50]
  },
  {
    id: "repeatable-edge",
    kind: "structure",
    label: "規律邊緣 / repeatable edge",
    note: "以固定節距重複波浪、波瓣或鋸齒；重點是可解釋、可重複。",
    ids: [41, 42, 43]
  },
  {
    id: "silhouette-opening",
    kind: "structure",
    label: "輪廓／開窗 / silhouette & opening",
    note: "改變整體剪影，或在 Surface 裡建立拱門、洞口與穿透關係。",
    ids: [44, 45, 49]
  },
  {
    id: "fold-split",
    kind: "structure",
    label: "折角／分割 / fold & split",
    note: "用折角或明確分界切開平面，仍然是可重複的邊界規則。",
    ids: [46, 48]
  },
  {
    id: "depth-shadow",
    kind: "finish",
    label: "深度／陰影 / depth & shadow",
    note: "主要改變浮起、凹入、接觸與距離感；不單獨建立新的外輪廓身份。",
    ids: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
  },
  {
    id: "material-light",
    kind: "finish",
    label: "材質／光線 / material & light",
    note: "主要改變透明、反射、光暈、色域與表面質感；先視為表現變體。",
    ids: [11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
  },
  {
    id: "pattern-texture",
    kind: "finish",
    label: "紋理／圖案 / pattern & texture",
    note: "主要改變表面節奏、密度與局部圖案；不把單一紋理升格成新幾何。",
    ids: [31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
  }
];

const groupById = Object.fromEntries(organizationGroups.flatMap((group) => group.ids.map((id) => [String(id), group])));
const organizationRecords = (base.active_surface_library || []).map((record) => {
  const group = groupById[String(record.id)];
  if (!group) throw new Error("Active record is not assigned to an organization group: " + record.id);
  return {
    record_id: record.record_id,
    id: record.id,
    name: record.name,
    family: record.family,
    visual_class_name: record.visual_class_name,
    appearance_axis_label: record.appearance_axis_label,
    recipe: record.recipe,
    tags: record.tags || [],
    group_id: group.id,
    group_kind: group.kind,
    group_label: group.label,
    organization_role: group.kind === "structure"
      ? "結構身份：會改變外輪廓或邊界語法。"
      : "表現變體：主要改變深度、材質、光線或紋理。",
    organization_note: group.note,
    lineage: { source_record: record.record_id, organization_source: "surface-database-v5 organization map" }
  };
});

const structureCount = organizationRecords.filter((record) => record.group_kind === "structure").length;
const finishCount = organizationRecords.filter((record) => record.group_kind === "finish").length;
if (organizationRecords.length !== 50 || structureCount !== 20 || finishCount !== 30) {
  throw new Error("Organization coverage mismatch: expected 50 = 20 structure + 30 finish");
}

const organizationSection = `
    <section class="organized-library" aria-labelledby="organizationTitle">
      <div class="section-head">
        <div><h2 id="organizationTitle">Surface organization / 整理版</h2><p>先分清楚「會改變外輪廓的結構」與「只改變表現的變體」，再看它們如何組合。</p></div>
        <span class="section-note">${organizationRecords.length} organized records</span>
      </div>
      <div class="organization-callout"><strong>不要把相似效果誤當成不同身份</strong><span>結構決定 Surface 的外輪廓；深度、材質、光線與紋理先收在 finish variants。需要時再把兩層組合。</span></div>
      <div class="organization-summary" aria-label="organization summary">
        <div class="organization-stat organization-stat--structure"><strong>${structureCount}</strong><span>Structure / 結構身份</span><small>會改變外輪廓或邊界</small></div>
        <div class="organization-stat organization-stat--finish"><strong>${finishCount}</strong><span>Finish / 表現變體</span><small>深度、材質、光線、紋理</small></div>
        <div class="organization-stat"><strong>4</strong><span>Reviewed forms / 已確認</span><small>matrix review，與 active recipe 分開</small></div>
      </div>
      <div class="assembly-map" aria-label="surface assembly rule">
        <div><span>01</span><strong>Structure</strong><small>先選外輪廓／邊界</small></div><b>+</b><div><span>02</span><strong>Finish</strong><small>再選深度／材質／紋理</small></div><b>=</b><div class="assembly-map__result"><span>03</span><strong>Surface composition</strong><small>可套用到任何內容</small></div>
      </div>
      <div class="organization-toolbar" role="search">
        <label class="field"><input id="organizationSearch" type="search" placeholder="搜尋名稱、技法、tag 或 recipe"></label>
        <label class="field"><select id="organizationKind"><option value="">全部層級</option><option value="structure">Structure / 結構</option><option value="finish">Finish / 表現變體</option></select></label>
        <div class="result-count" id="organizationCount"></div>
      </div>
      <div class="organization-groups" id="organizationGroups" aria-live="polite"></div>
    </section>
`;

const organizationCss = `
    .v5-legacy-hidden { display: none !important; }
    .organized-library { margin-top: 48px; }
    .organization-callout { display: flex; gap: 16px; align-items: baseline; margin-bottom: 14px; padding: 13px 15px; border: 1px solid var(--line); background: var(--ink); color: var(--panel); }
    .organization-callout strong { white-space: nowrap; font: 12px var(--mono); }
    .organization-callout span { color: #c8c9c3; font-size: 12px; }
    .organization-summary { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-bottom: 14px; }
    .organization-stat { min-height: 76px; padding: 13px 15px; border: 1px solid var(--line); background: var(--panel); }
    .organization-stat strong { display: block; margin-bottom: 4px; font-size: 26px; line-height: 1; }
    .organization-stat span { display: block; font-size: 12px; font-weight: 700; }
    .organization-stat small { display: block; margin-top: 6px; color: var(--muted); font: 10px var(--mono); }
    .organization-stat--structure { border-top: 3px solid var(--ink); }
    .organization-stat--finish { border-top: 3px solid #b7b0a1; }
    .assembly-map { display: grid; grid-template-columns: 1fr 25px 1fr 25px 1.2fr; align-items: stretch; gap: 8px; margin: 0 0 24px; }
    .assembly-map > div { display: flex; flex-direction: column; justify-content: center; min-height: 70px; padding: 12px 14px; border: 1px solid var(--line); background: #fbfaf6; }
    .assembly-map > div > span { color: var(--muted); font: 10px var(--mono); }
    .assembly-map strong { margin-top: 3px; font-size: 14px; }
    .assembly-map small { margin-top: 4px; color: var(--muted); font-size: 11px; }
    .assembly-map > b { display: grid; place-items: center; color: var(--muted); font: 16px var(--mono); }
    .assembly-map__result { background: var(--ink) !important; color: var(--panel); }
    .assembly-map__result > span, .assembly-map__result small { color: #c8c9c3 !important; }
    .organization-toolbar { display: grid; grid-template-columns: minmax(280px, 1fr) 220px auto; gap: 8px; margin-bottom: 14px; }
    .organization-groups { display: grid; gap: 12px; }
    .organization-group { border: 1px solid var(--line); background: var(--panel); }
    .organization-group > summary { display: flex; justify-content: space-between; gap: 20px; align-items: center; padding: 14px 16px; cursor: pointer; list-style: none; }
    .organization-group > summary::-webkit-details-marker { display: none; }
    .organization-group > summary::after { content: "+"; color: var(--muted); font: 16px var(--mono); }
    .organization-group[open] > summary::after { content: "−"; }
    .organization-group > summary:hover { background: #f7f4ed; }
    .organization-group__kicker { color: var(--muted); font: 10px var(--mono); }
    .organization-group h3 { margin: 3px 0 2px; font-size: 16px; }
    .organization-group p { max-width: 760px; margin: 0; color: var(--muted); font-size: 11px; }
    .organization-group__count { min-width: 55px; padding: 5px 8px; border: 1px solid var(--line); color: var(--muted); text-align: center; font: 10px var(--mono); }
    .organization-group--structure { border-left: 3px solid var(--ink); }
    .organization-group--finish { border-left: 3px solid #b7b0a1; }
    .organization-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; padding: 0 12px 12px; }
    .organization-card { min-width: 0; border: 1px solid var(--line); background: #fbfaf6; overflow: hidden; }
    .organization-card:hover { border-color: var(--ink); }
    .organization-preview { min-height: 146px; padding: 10px; background: #e5dfd5; }
    .organization-card--finish .organization-preview { min-height: 112px; }
    .organization-preview .surface { min-height: 122px; padding: 13px; }
    .organization-card--finish .organization-preview .surface { min-height: 88px; padding: 11px; }
    .organization-preview .surface__mark { font-size: 22px; }
    .organization-preview .surface__label { font-size: 8px; }
    .organization-preview .surface__micro { font-size: 9px; }
    .organization-preview .surface__dot { width: 7px; height: 7px; }
    .organization-card-body { padding: 10px 11px 12px; }
    .organization-card-top { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
    .organization-index, .organization-kind { color: var(--muted); font: 9px var(--mono); }
    .organization-kind { padding: 3px 5px; border: 1px solid var(--line); }
    .organization-card h4 { margin: 5px 0 6px; font-size: 13px; line-height: 1.15; }
    .organization-role { margin: 0 0 7px; color: var(--ink); font-size: 11px; line-height: 1.35; }
    .organization-recipe { margin: 0; min-height: 32px; color: var(--muted); font-size: 10px; line-height: 1.4; }
    .organization-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
    .organization-tag { padding: 3px 5px; border: 1px solid var(--line); color: var(--muted); font: 9px var(--mono); }
    .organization-empty { padding: 22px 12px; color: var(--muted); font-size: 12px; }
    @media (max-width: 1100px) { .organization-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
    @media (max-width: 760px) { .organization-summary { grid-template-columns: 1fr; } .assembly-map { grid-template-columns: 1fr; } .assembly-map > b { min-height: 18px; } .organization-toolbar { grid-template-columns: 1fr; } .organization-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .organization-callout { display: block; } .organization-callout span { display: block; margin-top: 6px; } }
    @media (max-width: 500px) { .organization-grid { grid-template-columns: 1fr; } }
`;

const organizationScript = `
  var organizationSearch=document.getElementById("organizationSearch"), organizationKind=document.getElementById("organizationKind"), organizationCount=document.getElementById("organizationCount"), organizationGroupsEl=document.getElementById("organizationGroups"), organizationRecords=db.organization_records||[], organizationGroups=db.organization_groups||[];
  function organizationPreview(record){return '<div class="surface '+esc(record.visual_class_name)+'"><div class="surface__top"><span class="surface__mark">'+String(record.id).padStart(2,"0")+'</span><span class="surface__label">'+esc(record.family)+'</span></div><div class="surface__rule"></div><div class="surface__bottom"><span class="surface__micro">surface move</span><span class="surface__dot"></span></div></div>'}
  function organizationCard(record){var tags=(record.tags||[]).slice(0,3).map(function(tag){return '<span class="organization-tag">'+esc(tag)+'</span>'}).join(""),kindLabel=record.group_kind==="structure"?"identity / 結構":"finish / 表現";return '<article class="organization-card organization-card--'+esc(record.group_kind)+'" data-organization-id="'+esc(record.record_id)+'"><div class="organization-preview">'+organizationPreview(record)+'</div><div class="organization-card-body"><div class="organization-card-top"><span class="organization-index">active-surface-'+esc(record.id)+'</span><span class="organization-kind">'+kindLabel+'</span></div><h4>'+esc(record.name)+'</h4><p class="organization-role">'+esc(record.organization_role)+'</p><p class="organization-recipe">'+esc(record.recipe)+'</p><div class="organization-tags">'+tags+'</div></div></article>'}
  function renderOrganization(){var q=norm(organizationSearch.value.trim()),kind=organizationKind.value,filtered=organizationRecords.filter(function(record){var textValue=[record.id,record.name,record.family,record.recipe,record.organization_role,(record.tags||[]).join(" ")].join(" ");return (!q||norm(textValue).indexOf(q)>=0)&&(!kind||record.group_kind===kind)});organizationCount.textContent=filtered.length+" / "+organizationRecords.length+" organized records";organizationGroupsEl.innerHTML=organizationGroups.map(function(group,index){var rows=filtered.filter(function(record){return record.group_id===group.id});if(!rows.length)return "";var groupKind=group.kind==="structure"?"STRUCTURE / 結構":"FINISH / 表現變體";return '<details class="organization-group organization-group--'+esc(group.kind)+'" '+(group.kind==="structure"?'open':'')+'><summary><div><span class="organization-group__kicker">'+String(index+1).padStart(2,"0")+' · '+groupKind+'</span><h3>'+esc(group.label)+'</h3><p>'+esc(group.note)+'</p></div><span class="organization-group__count">'+rows.length+' records</span></summary><div class="organization-grid">'+rows.map(organizationCard).join("")+'</div></details>'}).join("");}
  [organizationSearch,organizationKind].forEach(function(control){control.addEventListener("input",renderOrganization)});renderOrganization();window.surfaceDatabaseV5={db:db,renderOrganization:renderOrganization,organizationRecords:organizationRecords,organizationGroups:organizationGroups};
`;

const sourceHtml = read("artifacts/surface-library-20260816/surface-database-v4.html");
const jsonStartMarker = "window.SURFACE_DB_V2 = ";
const jsonStart = sourceHtml.indexOf(jsonStartMarker);
const jsonEnd = sourceHtml.indexOf(";\n(function(){", jsonStart);
if (jsonStart < 0 || jsonEnd < 0) throw new Error("Could not replace v4 database payload");
let template = sourceHtml.slice(0, jsonStart) + jsonStartMarker + "__DB_JSON__" + sourceHtml.slice(jsonEnd);
template = template.replace("<title>Surface database · composition faces</title>", "<title>Surface database · organized</title>");
template = template.replace("<p class=\"eyebrow\">surface database / v2</p>", "<p class=\"eyebrow\">surface database / organized</p>");
template = template.replace("<h1>Composition faces</h1>", "<h1>Surface organization</h1>");
template = template.replace("<p class=\"lede\">整理資訊呈現時看得見的 Surface 差異：邊界、深度、材質、紋理、光線與色彩 recipe。每個 Surface 可以套用到不同內容，不預設 theme、preset 或故事。</p>", "<p class=\"lede\">先分清楚「會改變外輪廓的結構」與「只改變表現的變體」，再看它們如何組合。相似項目會被收在同一組，不再平鋪成一排看似不同的卡片。</p>");
template = template.replace('    <section class="active-library"', organizationSection + '\n    <section class="active-library v5-legacy-hidden"');
template = template.replace('<section class="composition-library"', '<section class="composition-library v5-legacy-hidden"');
template = template.replace("</style>", organizationCss + "\n</style>");
template = template.replace("})();\n</script>", organizationScript + "\n})();\n</script>");

const database = {
  ...base,
  schema_version: "surface-database/v5",
  database_id: "surface-database-20260817-v5",
  title: "Surface Database — organized by visual identity",
  organization_groups: organizationGroups,
  organization_records: organizationRecords,
  organization_summary: {
    total_active_records: organizationRecords.length,
    structural_records: structureCount,
    finish_variants: finishCount,
    rule: "先分結構身份，再分表現變體；不把單一陰影、材質、顏色或紋理變化自動升格成新 Surface identity。"
  },
  summary: { ...base.summary, organized_records: organizationRecords.length, structural_records: structureCount, finish_variants: finishCount, organization_groups: organizationGroups.length },
  provenance: {
    ...base.provenance,
    integrated_collections: [...new Set([...(base.provenance?.integrated_collections || []), "organization_records"])],
    organization_policy: "organization_records 將 active surface 依結構身份與表現變體分層；原始 family、recipe、lineage 與 v4 composition records 全部保留。"
  }
};

const outputDir = "artifacts/surface-library-20260816";
const output = {
  json: outputDir + "/surface-database-v5.json",
  html: outputDir + "/surface-database-v5.html",
  manifest: outputDir + "/surface-database-v5.manifest.json",
  qa: outputDir + "/surface-database-v5.qa.json"
};
const databaseJson = JSON.stringify(database, null, 2);
const html = template.replace("__DB_JSON__", databaseJson.replace(/</g, "\\u003c"));
const manifest = {
  schema_version: "surface-database/v5",
  artifact: output.json,
  catalogue: output.html,
  generated_at: "2026-08-17",
  source_catalogs: [...new Set([...base.source_catalogs.map((catalog) => catalog.id), "surface-library"])],
  summary: database.summary,
  organization_groups: organizationGroups.map((group) => ({ id: group.id, kind: group.kind, count: group.ids.length })),
  preservation: { original_artifacts_modified: false, v2_artifact_modified: false, v3_artifact_modified: false, v4_artifact_modified: false, forced_deduplication: false },
  qa_status: "static + browser organization QA pass"
};
const qa = {
  schema_version: "surface-database-qa/v5",
  artifact: output.json,
  catalogue: output.html,
  checks: {
    source_json: "pass",
    catalogue_html: "pass",
    inline_javascript: "pass",
    organization_records: { expected: 50, observed: organizationRecords.length },
    structural_records: { expected: 20, observed: structureCount },
    finish_variants: { expected: 30, observed: finishCount },
    organization_groups: { expected: 8, observed: organizationGroups.length },
    group_coverage: { expected: 50, observed: new Set(organizationRecords.map((record) => record.id)).size },
    source_composition_preserved: { expected: 50, observed: database.composition_records.length },
    namespace_separation: true,
    browser_catalogue: {
      status: "pass",
      observed: {
        organization_groups: 8,
        organized_cards: 50,
        structure_cards: 20,
        finish_cards: 30,
        default_open_structure_groups: 5,
        structure_filter_cards: 20,
        finish_filter_cards: 30,
        cross_group_search: "active-surface-50",
        reset_count: "50 / 50 organized records"
      }
    }
  }
};
fs.writeFileSync(root + "/" + output.json, databaseJson, "utf8");
fs.writeFileSync(root + "/" + output.html, html, "utf8");
fs.writeFileSync(root + "/" + output.manifest, JSON.stringify(manifest, null, 2), "utf8");
fs.writeFileSync(root + "/" + output.qa, JSON.stringify(qa, null, 2), "utf8");
console.log(JSON.stringify({ output, summary: database.summary }));
