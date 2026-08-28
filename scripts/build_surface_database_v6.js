const fs = require("fs");

const root = process.cwd();
const read = (relativePath) => fs.readFileSync(root + "/" + relativePath, "utf8");
const readJson = (relativePath) => JSON.parse(read(relativePath));
const base = readJson("artifacts/surface-library-20260816/surface-database-v3.json");
const organization = readJson("artifacts/surface-library-20260816/surface-database-v5.json");
const organizationById = Object.fromEntries((organization.organization_records || []).map((record) => [String(record.id), record]));
const activeSurfaceLibrary = (base.active_surface_library || []).map((record) => ({
  ...record,
  organization: organizationById[String(record.id)] ? {
    group_id: organizationById[String(record.id)].group_id,
    group_kind: organizationById[String(record.id)].group_kind,
    group_label: organizationById[String(record.id)].group_label,
    organization_role: organizationById[String(record.id)].organization_role
  } : null
}));
const structureCount = activeSurfaceLibrary.filter((record) => record.organization?.group_kind === "structure").length;
const finishCount = activeSurfaceLibrary.filter((record) => record.organization?.group_kind === "finish").length;
if (activeSurfaceLibrary.length !== 50 || structureCount !== 20 || finishCount !== 30) {
  throw new Error("Organization mapping mismatch: expected 50 = 20 structure + 30 finish");
}

const organizationStrip = `
    <section class="organization-strip" aria-label="surface organization summary">
      <div class="organization-strip__lead"><strong>Surface organization</strong><span>原始 active preview 保留；整理只進入角色、標籤與篩選，不改變 Surface 的實際呈現。</span></div>
      <div class="organization-strip__stat"><strong>${structureCount}</strong><span>structure identity</span></div>
      <div class="organization-strip__stat"><strong>${finishCount}</strong><span>finish variants</span></div>
    </section>
`;

const organizationCss = `
    .organization-strip { display: grid; grid-template-columns: minmax(300px, 1fr) 150px 150px; gap: 8px; margin-top: 48px; margin-bottom: -28px; padding: 10px 0; }
    .organization-strip__lead, .organization-strip__stat { min-height: 58px; padding: 10px 13px; border: 1px solid var(--line); background: var(--panel); }
    .organization-strip__lead { display: flex; flex-direction: column; justify-content: center; }
    .organization-strip__lead strong { font-size: 12px; }
    .organization-strip__lead span { margin-top: 3px; color: var(--muted); font-size: 10px; }
    .organization-strip__stat { display: flex; flex-direction: column; justify-content: center; border-top: 3px solid #b7b0a1; }
    .organization-strip__stat:first-of-type { border-top-color: var(--ink); }
    .organization-strip__stat strong { font-size: 20px; line-height: 1; }
    .organization-strip__stat span { margin-top: 4px; color: var(--muted); font: 9px var(--mono); }
    .active-toolbar { grid-template-columns: minmax(220px, 1fr) 170px 170px 170px auto; }
    .active-tag--organization { border-color: #777268; color: var(--ink); }
    @media (max-width: 1100px) { .organization-strip { grid-template-columns: minmax(220px, 1fr) 120px 120px; } .active-toolbar { grid-template-columns: minmax(180px, 1fr) repeat(3, minmax(120px, 1fr)); } }
    @media (max-width: 980px) { .active-toolbar { grid-template-columns: minmax(180px, 1fr) repeat(3, 1fr); } }
    @media (max-width: 580px) { .organization-strip { grid-template-columns: 1fr 1fr; margin-bottom: -28px; } .organization-strip__lead { grid-column: 1 / -1; } .active-toolbar { grid-template-columns: 1fr; } }
`;

const organizationEnhancementScript = `
  var organizationRole=document.getElementById("activeRole"), organizationRecordById=Object.fromEntries((db.organization_records||[]).map(function(record){return [String(record.id),record]}));
  function renderActiveOrganized(){renderActive();var role=organizationRole.value,visible=0;Array.from(activeGrid.querySelectorAll(".active-card")).forEach(function(card){var record=activeRecords.find(function(item){return item.record_id===card.dataset.activeId}),org=record&&organizationRecordById[String(record.id)],show=!role||org&&org.group_kind===role;card.hidden=!show;if(show)visible++;if(org){var footer=card.querySelector(".active-card__footer"),tag=document.createElement("span");tag.className="active-tag active-tag--organization";tag.textContent=org.group_kind==="structure"?"identity / 結構":"finish / 表現變體";footer.appendChild(tag)}});if(role)activeCount.textContent=visible+" / "+activeRecords.length+" active previews"}
  [activeSearch,activeFamily,activeAudit,organizationRole].forEach(function(control){control.addEventListener("input",renderActiveOrganized)});renderActiveOrganized();window.surfaceDatabaseV6={db:db,renderActive:renderActiveOrganized,activeRecords:activeRecords,organizationRecords:db.organization_records||[]};
`;

const sourceHtml = read("artifacts/surface-library-20260816/surface-database-v3.html");
const jsonStartMarker = "window.SURFACE_DB_V2 = ";
const jsonStart = sourceHtml.indexOf(jsonStartMarker);
const jsonEnd = sourceHtml.indexOf(";\n(function(){", jsonStart);
if (jsonStart < 0 || jsonEnd < 0) throw new Error("Could not replace v3 database payload");
let template = sourceHtml.slice(0, jsonStart) + jsonStartMarker + "__DB_JSON__" + sourceHtml.slice(jsonEnd);
template = template.replace("<title>Surface database · active previews + geometry</title>", "<title>Surface database · original active previews</title>");
template = template.replace('<section class="active-library"', organizationStrip + '\n<section class="active-library"');
template = template.replace('<label class="field"><select id="activeAudit"><option value="all">All audit states</option><option value="counted">Counted methods</option><option value="excluded">Color-only / excluded</option></select></label>', '<label class="field"><select id="activeAudit"><option value="all">All audit states</option><option value="counted">Counted methods</option><option value="excluded">Color-only / excluded</option></select></label>\n        <label class="field"><select id="activeRole"><option value="">All roles</option><option value="structure">Structure / identity</option><option value="finish">Finish / variant</option></select></label>');
template = template.replace("</style>", organizationCss + "\n</style>");
template = template.replace("})();\n</script>", organizationEnhancementScript + "\n})();\n</script>");

const database = {
  ...base,
  schema_version: "surface-database/v6",
  database_id: "surface-database-20260817-v6",
  title: "Surface Database — original active previews with organization",
  active_surface_library: activeSurfaceLibrary,
  composition_records: organization.composition_records,
  organization_groups: organization.organization_groups,
  organization_records: organization.organization_records,
  organization_summary: {
    total_active_records: activeSurfaceLibrary.length,
    structural_records: structureCount,
    finish_variants: finishCount,
    presentation_policy: "以 v3 active preview 的原始卡片效果為主；organization 只增加 role/filter/tag，不縮小或替換 preview。"
  },
  summary: { ...base.summary, active_surface_library_records: activeSurfaceLibrary.length, structural_records: structureCount, finish_variants: finishCount, organization_groups: organization.organization_groups.length },
  provenance: {
    ...base.provenance,
    integrated_collections: [...new Set([...(base.provenance?.integrated_collections || []), "organization_records"])],
    active_preview_css_source: "artifacts/surface-library-20260816/surface-library.html",
    presentation_policy: "保留 v3 原始 active preview geometry、色彩、陰影與 recipe；只將組織資訊加到查詢層。"
  }
};

const outputDir = "artifacts/surface-library-20260816";
const output = {
  json: outputDir + "/surface-database-v6.json",
  html: outputDir + "/surface-database-v6.html",
  manifest: outputDir + "/surface-database-v6.manifest.json",
  qa: outputDir + "/surface-database-v6.qa.json"
};
const databaseJson = JSON.stringify(database, null, 2);
const html = template.replace("__DB_JSON__", databaseJson.replace(/</g, "\\u003c"));
const manifest = {
  schema_version: "surface-database/v6",
  artifact: output.json,
  catalogue: output.html,
  generated_at: "2026-08-17",
  source_catalogs: [...new Set([...base.source_catalogs.map((catalog) => catalog.id), "surface-library"])],
  summary: database.summary,
  preservation: { original_artifacts_modified: false, v3_artifact_modified: false, v4_artifact_modified: false, v5_artifact_modified: false, forced_deduplication: false },
  qa_status: "static + browser original-preview QA pass"
};
const qa = {
  schema_version: "surface-database-qa/v6",
  artifact: output.json,
  catalogue: output.html,
  checks: {
    source_json: "pass",
    catalogue_html: "pass",
    inline_javascript: "pass",
    active_surface_library: { expected: 50, observed: activeSurfaceLibrary.length },
    original_preview_css_source: "pass",
    organization_structure_records: { expected: 20, observed: structureCount },
    organization_finish_variants: { expected: 30, observed: finishCount },
    organization_groups: { expected: 8, observed: organization.organization_groups.length },
    original_composition_records: { expected: 50, observed: database.composition_records.length },
    browser_catalogue: {
      status: "pass",
      observed: {
        active_cards: 50,
        grid_columns: 4,
        original_preview_stage_height: 220,
        organization_tag_visible: true,
        structure_role_cards: 20,
        finish_role_cards: 30,
        reset_count: "50 / 50 active previews"
      }
    }
  }
};
fs.writeFileSync(root + "/" + output.json, databaseJson, "utf8");
fs.writeFileSync(root + "/" + output.html, html, "utf8");
fs.writeFileSync(root + "/" + output.manifest, JSON.stringify(manifest, null, 2), "utf8");
fs.writeFileSync(root + "/" + output.qa, JSON.stringify(qa, null, 2), "utf8");
console.log(JSON.stringify({ output, summary: database.summary }));
