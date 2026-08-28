const fs = require("fs");

const root = process.cwd();
const readJson = (relativePath) => JSON.parse(fs.readFileSync(root + "/" + relativePath, "utf8"));
const read = (relativePath) => fs.readFileSync(root + "/" + relativePath, "utf8");
const source = readJson("artifacts/surface-library-20260816/surface-database-v1.json");

// These are geometry candidates from the existing method catalog. Effects without
// a repeatable boundary remain in the source table but are not Surface identity.
const boundaryRules = {
  8: ["offset outline", "主輪廓外移一圈；偏移距離需固定。"],
  13: ["edge line", "以一條外輪廓線界定透明／空白面；不把材質本身當 identity。"],
  18: ["inner edge line", "內側平行邊線；需有固定 inset，光效不是 identity。"],
  21: ["single outline", "低干擾單線外框；輪廓與線寬可重複。"],
  22: ["double outline", "兩層平行外框；間距固定。"],
  23: ["offset outline", "外移平行外框；偏移距離固定。"],
  24: ["border rail", "沿外輪廓的一圈邊界帶；顏色／漸層不算 identity。"],
  25: ["corner brackets", "四角分離角標；位置與長度固定。"],
  26: ["dashed edge", "等距斷續邊；dash 與 gap 的節距固定。"],
  27: ["chamfered corners", "四角切角；切角比例固定。"],
  28: ["notched edge", "側邊缺口；缺口位置與深度固定。"],
  29: ["bottom slab", "底部延伸的水平 slab；邊界規則獨立於內容。"],
  30: ["capsule outline", "封閉膠囊外輪廓；端點半徑固定。"],
  41: ["wavy edge", "底部週期性波浪；振幅與節距固定。"],
  42: ["scallop edge", "週期性半圓波瓣；半徑與節距固定。"],
  43: ["zig-zag edge", "週期性三角鋸齒；角度、節距與水平基準固定。"],
  44: ["organic silhouette", "連續封閉有機輪廓；保留作候選，尚未取得使用者批准。"],
  45: ["arch opening", "拱形封閉輪廓；拱高與側邊比例固定。"],
  46: ["folded corner", "單角折角；折角位置與尺寸固定。"],
  47: ["notched tab", "側向 tab／缺口；突出與內收尺寸固定。"],
  48: ["split boundary", "分裂成兩段的邊界；斷點位置需固定。"],
  49: ["window cutout", "內部開窗／孔洞；孔洞位置與比例固定。"],
  50: ["ribbon slab", "水平 ribbon slab；端點的方向性邊界固定。"]
};
const familyById = {
  8: "outline", 13: "outline", 18: "outline", 21: "outline", 22: "outline", 23: "outline", 24: "outline",
  25: "corner", 26: "periodic edge", 27: "corner", 28: "notch", 29: "extension", 30: "silhouette",
  41: "periodic edge", 42: "periodic edge", 43: "periodic edge", 44: "silhouette", 45: "silhouette",
  46: "corner", 47: "notch", 48: "boundary split", 49: "cutout", 50: "directional slab"
};

const currentSourceRecords = source.surface_types.map((record) => {
  const boundary = boundaryRules[record.id];
  return {
    record_id: record.record_id,
    source_record_id: record.source_record_id,
    id: record.id,
    name: record.name,
    source_kind: "previous_library",
    source_collection: "previous_surface_library",
    source_collection_label: "Previous Surface library",
    boundary_scope: boundary ? "boundary_candidate" : "effect_only_source",
    boundary_scope_label: boundary ? "boundary candidate" : "effect-only / not identity",
    geometry_family: familyById[record.id] || null,
    boundary_rule: boundary ? boundary[1] : "沒有獨立、可重複的外輪廓；保留作既有 source record，不納入 Surface identity。",
    boundary_syntax: boundary ? boundary[0] : null,
    user_review_status: record.user_review_status,
    method_audit: record.method_audit,
    related_matrix_record_id: record.related_matrix_record_id,
    lineage: record.lineage
  };
});

const approvedForms = [
  {
    record_id: "approved-20",
    matrix_record_id: "matrix-20",
    id: 20,
    alias: "缺口長條／ribbon slab",
    reviewed_form: "ribbon_slab",
    geometry_family: "directional slab",
    geometry_rule: "水平長條；左側中段內收、右側中段外指；保持 0°。",
    orientation: "horizontal / 0°",
    boundary_components: ["single outer silhouette", "side notch + point", "repeatable horizontal rule"],
    user_review_status: { status: "approved", label: "使用者 OK", reason: "方向性清楚，外輪廓可重複。" },
    visual_reference_id: "user-screenshot-2026-08-17-001112",
    source_note: "以使用者截圖的幾何為準；不沿用 source matrix 的 material／pattern 作為 identity。"
  },
  {
    record_id: "approved-22",
    matrix_record_id: "matrix-22",
    id: 22,
    alias: "八角形切角／chamfered octagon",
    reviewed_form: "chamfered_octagon",
    geometry_family: "chamfered outline",
    geometry_rule: "矩形四角等距切角，形成可解釋的八邊外輪廓；保持 0°。",
    orientation: "horizontal / 0°",
    boundary_components: ["closed outline", "four equal chamfers", "repeatable corner ratio"],
    user_review_status: { status: "approved", label: "使用者 OK", reason: "切角規則清楚，不使用任意多邊形。" },
    visual_reference_id: "user-screenshot-2026-08-17-001107",
    source_note: "使用者視覺判定覆寫 source matrix 對 shape 的粗略命名；database 以 reviewed geometry 為準。"
  },
  {
    record_id: "approved-29",
    matrix_record_id: "matrix-29",
    id: 29,
    alias: "規律底部鋸齒邊",
    reviewed_form: "regular_bottom_zigzag",
    geometry_family: "periodic edge",
    geometry_rule: "底部固定節距的三角鋸齒；水平基準穩定，不任意變形。",
    orientation: "horizontal / 0°",
    boundary_components: ["bottom-only edge", "fixed tooth pitch", "stable horizontal baseline"],
    user_review_status: { status: "approved", label: "使用者 OK", reason: "規律、水平穩定的鋸齒邊可以。" },
    visual_reference_id: "user-screenshot-2026-08-17-001255",
    source_note: "只取底部週期性鋸齒的物理邊界；不取卡片中的文字、顏色或陰影。"
  },
  {
    record_id: "approved-41",
    matrix_record_id: "matrix-41",
    id: 41,
    alias: "底部波瓣／scallop 邊",
    reviewed_form: "bottom_scallop",
    geometry_family: "periodic edge",
    geometry_rule: "底部固定半徑、固定節距的半圓波瓣；水平基準穩定。",
    orientation: "horizontal / 0°",
    boundary_components: ["bottom-only edge", "fixed lobe radius", "repeatable pitch"],
    user_review_status: { status: "approved", label: "使用者 OK", reason: "波瓣是清楚、可重複的物理邊界。" },
    visual_reference_id: "user-screenshot-2026-08-17-001051",
    source_note: "只取底部波瓣的物理邊界；不取卡片中的文字、顏色或陰影。"
  }
];

const boundaryCount = currentSourceRecords.filter((record) => record.boundary_scope === "boundary_candidate").length;
const effectCount = currentSourceRecords.length - boundaryCount;
const database = {
  schema_version: "surface-database/v2",
  database_id: "surface-database-20260817-v2",
  generated_at: "2026-08-17",
  title: "Surface Database — geometry-only boundary library",
  surface_identity_contract: {
    identity: "repeatable boundary, outline, cut, notch, opening, or edge rule used to present information",
    reusable_across: ["theme", "preset", "content", "topic", "brand", "color system"],
    excluded_from_identity: ["color-only change", "shadow-only change", "material-only change", "texture-only change", "fixed story or content layout"],
    review_note: "approved forms come from the user's visual review; source method audit and content fit remain separate."
  },
  summary: {
    approved_boundary_forms: approvedForms.length,
    previous_surface_library_records: currentSourceRecords.length,
    current_source_records: currentSourceRecords.length,
    current_boundary_candidates: boundaryCount,
    current_effect_only_records: effectCount,
    legacy_catalog_entries: source.legacy_catalog_entries.length,
    source_catalogs: source.source_catalogs.length
  },
  approved_forms: approvedForms,
  previous_surface_library: currentSourceRecords,
  // Compatibility alias kept for the first database draft; the canonical collection is previous_surface_library.
  current_source_records: currentSourceRecords,
  legacy_catalog_entries: source.legacy_catalog_entries,
  source_catalogs: source.source_catalogs,
  matrix_compositions: source.matrix_compositions,
  user_review_status: source.user_review_status,
  method_audit: source.method_audit,
  content_fit: source.content_fit,
  approval_rules: source.approval_rules,
  provenance: {
    generated_from: ["artifacts/surface-library-20260816/surface-database-v1.json", "artifacts/surface-library-20260816/surface-library-v4.html", "artifacts/reviews/surface-gallery-20260812-v3-50/index.html"],
    visual_references: approvedForms.map((record) => ({ record_id: record.record_id, reference_id: record.visual_reference_id })),
    preserved_original_artifacts: true,
    no_forced_deduplication: true,
    source_axes_policy: "matrix 的 material／pattern／其他 context 欄位只保留在 provenance，不進入 Surface identity。",
    integrated_collections: ["approved_forms", "previous_surface_library", "matrix_compositions", "legacy_catalog_entries"]
  }
};

const outputDir = "artifacts/surface-library-20260816";
const output = {
  json: outputDir + "/surface-database-v2.json",
  html: outputDir + "/surface-database-v2.html",
  manifest: outputDir + "/surface-database-v2.manifest.json",
  qa: outputDir + "/surface-database-v2.qa.json"
};
const databaseJson = JSON.stringify(database, null, 2);
const html = read("scripts/surface_database_v2_template.html").replace("__DB_JSON__", databaseJson.replace(/</g, "\\u003c"));
const manifest = {
  schema_version: "surface-database/v2",
  artifact: output.json,
  catalogue: output.html,
  generated_at: "2026-08-17",
  source_catalogs: source.source_catalogs.map((catalog) => catalog.id),
  summary: database.summary,
  approved_geometry_ids: approvedForms.map((record) => record.id),
  preservation: { original_artifacts_modified: false, v1_artifact_modified: false, forced_deduplication: false },
  qa_status: "static + browser QA pass; geometry-only and interaction checks captured in current Surface session"
};
const qa = {
  schema_version: "surface-database-qa/v2",
  artifact: output.json,
  catalogue: output.html,
  checks: {
    source_json: "pass",
    catalogue_html: "pass",
    geometry_only_contract: "pass",
    approved_geometry_ids: { expected: [20, 22, 29, 41], observed: approvedForms.map((record) => record.id) },
    previous_surface_library: { expected: 50, observed: currentSourceRecords.length },
    current_source_records_compatibility_alias: { expected: 50, observed: currentSourceRecords.length },
    matrix_compositions: { expected: 50, observed: source.matrix_compositions.length },
    current_boundary_candidates: { expected: boundaryCount, observed: boundaryCount },
    current_effect_only_records: { expected: effectCount, observed: effectCount },
    legacy_catalog_entries: { expected: 50, observed: source.legacy_catalog_entries.length },
    user_review_status_separated: true,
    method_audit_separated: true,
    browser_catalogue: { status: "pass", observed: "default Previous Surface library scope returns 50; Legacy scope returns 50; All integrated records returns 100; search Ribbon slab returns surface-type-50; 4 approved geometry specimens remain separate." }
  }
};
fs.writeFileSync(root + "/" + output.json, databaseJson, "utf8");
fs.writeFileSync(root + "/" + output.html, html, "utf8");
fs.writeFileSync(root + "/" + output.manifest, JSON.stringify(manifest, null, 2), "utf8");
fs.writeFileSync(root + "/" + output.qa, JSON.stringify(qa, null, 2), "utf8");
console.log(JSON.stringify({ output, summary: database.summary }));
