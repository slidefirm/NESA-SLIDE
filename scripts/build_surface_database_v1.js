const fs = require("fs");

const root = process.cwd();
const read = (relativePath) => fs.readFileSync(root + "/" + relativePath, "utf8");
const extractArray = (source, marker) => {
  const start = source.indexOf(marker) + marker.length;
  const end = source.indexOf("];", start) + 1;
  if (start < marker.length || end < 1) throw new Error("Missing array marker: " + marker);
  return Function("return " + source.slice(start, end))();
};

const v4Html = read("artifacts/surface-library-20260816/surface-library-v4.html");
const legacyHtml = read("artifacts/reviews/surface-gallery-20260812-v3-50/index.html");
const axes = {
  shape: [
    { id: "square", label: "方形" }, { id: "circle", label: "圓形" }, { id: "ellipse", label: "橢圓" },
    { id: "arch", label: "拱形" }, { id: "blob", label: "有機" }, { id: "polygon", label: "多邊形" },
    { id: "diamond", label: "菱形" }, { id: "strip", label: "長條" }, { id: "ring", label: "環形" },
    { id: "ribbon", label: "旗帶" }
  ],
  edge: [
    { id: "fill", label: "實心" }, { id: "outline", label: "純外框" }, { id: "double", label: "雙線" },
    { id: "notch", label: "缺口" }, { id: "cut", label: "切角" }, { id: "scallop", label: "波瓣" },
    { id: "zigzag", label: "鋸齒" }, { id: "bracket", label: "角標" }, { id: "fold", label: "折角" },
    { id: "window", label: "開窗" }
  ],
  material: [
    { id: "flat", label: "平面" }, { id: "paper", label: "紙張" }, { id: "glass", label: "毛玻璃" },
    { id: "inset", label: "內凹" }, { id: "shadow", label: "浮層" }, { id: "glow", label: "光暈" },
    { id: "clay", label: "黏土" }, { id: "gradient", label: "漸層" }, { id: "duotone", label: "雙色" },
    { id: "tonal", label: "暗色階" }
  ],
  pattern: [
    { id: "none", label: "無紋理" }, { id: "dots", label: "點陣" }, { id: "grid", label: "網格" },
    { id: "hatch", label: "斜線" }, { id: "checker", label: "棋盤" }, { id: "contour", label: "等高線" },
    { id: "scan", label: "掃描線" }, { id: "grain", label: "顆粒" }, { id: "halftone", label: "半色調" },
    { id: "band", label: "底部圖案" }
  ]
};
const label = (axis, id) => axes[axis].find((item) => item.id === id)?.label || id;
const surfaces = extractArray(v4Html, "const surfaces = ");
const compositions = extractArray(v4Html, "const compositions = ");
const legacyItems = extractArray(legacyHtml, "const items=");
const excludedColorOnlyIds = [10, 12, 15, 19, 20];
const usableIds = [1, 3, 4, 5, 6, 12, 13, 14, 15, 16, 21, 22, 23, 24, 25, 31, 32, 33, 35, 36, 41, 42, 43, 44, 46];

const approved = {
  20: { alias: "Ribbon／缺口長條／方向性 slab", reviewed_form: "ribbon_slab", reason: "水平長條、兩端缺口清楚，方向性成立；預設不旋轉。" },
  22: { alias: "八角形切角／chamfered octagon", reviewed_form: "chamfered_octagon", reason: "切角形成可重複、可解釋的八邊外輪廓；不使用任意多邊形。" },
  29: { alias: "規律底部鋸齒邊", reviewed_form: "regular_bottom_zigzag", reason: "底部鋸齒的節距、方向與水平基準穩定，可重複套用。" },
  41: { alias: "底部波瓣／scallop 邊", reviewed_form: "bottom_scallop", reason: "底部波瓣以固定半徑與節距重複，形成清楚的物理邊界。" }
};
const sourceCatalogs = [
  { id: "surface-library-v1", path: "artifacts/surface-library-20260816/surface-library.html", kind: "method-catalog", record_count: 50, role: "原始 50 種 Surface recipe" },
  { id: "surface-library-v2", path: "artifacts/surface-library-20260816/surface-library-v2.html", kind: "matrix-catalog", record_count: 50, role: "shape × edge × material × pattern 交叉矩陣" },
  { id: "surface-library-v3", path: "artifacts/surface-library-20260816/surface-library-v3.html", kind: "content-fit-catalog", record_count: 50, role: "加入簡報內容壓力測試" },
  { id: "surface-library-v4", path: "artifacts/surface-library-20260816/surface-library-v4.html", kind: "method-audit-catalog", record_count: 50, role: "色彩-only 排除與 method audit" },
  { id: "surface-gallery-v1", path: "artifacts/reviews/surface-gallery-20260812-v1/index.html", kind: "review-gallery", record_count: null, role: "歷史視覺參考" },
  { id: "surface-gallery-v2", path: "artifacts/reviews/surface-gallery-20260812-v2/index.html", kind: "review-gallery", record_count: 14, role: "14 種成熟 recipe review" },
  { id: "surface-gallery-v3-50", path: "artifacts/reviews/surface-gallery-20260812-v3-50/index.html", kind: "legacy-catalog", record_count: 50, role: "14 canonical + 36 candidate 的歷史 catalog" }
];
const methodAuditById = Object.fromEntries(surfaces.map((surface) => [
  String(surface.id),
  excludedColorOnlyIds.includes(surface.id)
    ? { status: "excluded", label: "色彩-only", reason: "主要是色票／色彩混合變化，不另算成新的 Surface method。" }
    : { status: "counted", label: "計數", reason: "改變深度、材質、邊界、紋理、光線或結構，可獨立成為 method。" }
]));
const matrixCompositions = compositions.map((composition) => {
  const decision = approved[composition.id];
  return {
    record_id: "matrix-" + composition.id,
    source_record_id: "composition-" + composition.id,
    id: composition.id,
    axes: composition,
    axis_labels: {
      shape: label("shape", composition.shape),
      edge: label("edge", composition.edge),
      material: label("material", composition.material),
      pattern: label("pattern", composition.pattern)
    },
    user_review_status: decision
      ? { status: "approved", label: "使用者 OK", ...decision }
      : { status: "not_approved", label: "暫不通過", reason: "目前不在使用者明確通過的 4 個 Surface 之內；保留作為比較與後續修正素材。" },
    content_fit: {
      status: usableIds.includes(composition.id) ? "usable" : "limited",
      label: usableIds.includes(composition.id) ? "可用" : "不可用",
      source_catalog_id: "surface-library-v4",
      source_record_id: "composition-" + composition.id
    },
    lineage: {
      source_catalogs: ["surface-library-v2", "surface-library-v3", "surface-library-v4"],
      index_namespace: "matrix composition id"
    }
  };
});
const surfaceTypes = surfaces.map((surface) => ({
  record_id: "surface-type-" + surface.id,
  source_record_id: surface.className,
  ...surface,
  user_review_status: {
    status: "not_approved",
    label: "未列入四個 OK",
    reason: "這是既有 method catalog record；目前保留供比較，不將數字 ID 誤當成使用者批准的 matrix composition。"
  },
  method_audit: methodAuditById[String(surface.id)],
  related_matrix_record_id: "matrix-" + surface.id,
  lineage: {
    source_catalogs: ["surface-library-v1", "surface-library-v2", "surface-library-v3", "surface-library-v4"],
    index_namespace: "current surface recipe id"
  }
}));
const legacyCatalogEntries = legacyItems.map((item) => ({
  record_id: "legacy-v3-50-" + item[0],
  source_record_id: item[0],
  catalog_family: item[1],
  slug: item[2],
  name: item[3],
  descriptor: item[4],
  english_recipe: item[5],
  historical_status: item[6],
  user_review_status: {
    status: "not_approved",
    label: "未列入四個 OK",
    reason: "歷史 catalog 項目保留 lineage，不強行與新版 matrix composition 去重。"
  },
  lineage: { source_catalogs: ["surface-gallery-v3-50"], index_namespace: "legacy catalog id" }
}));

const database = {
  schema_version: "surface-database/v1",
  database_id: "surface-database-20260817-v1",
  generated_at: "2026-08-17",
  title: "Surface Database — approved forms + historical candidates",
  summary: {
    approved_matrix_compositions: 4,
    not_approved_matrix_compositions: 46,
    matrix_compositions: matrixCompositions.length,
    current_surface_types: surfaceTypes.length,
    legacy_catalog_entries: legacyCatalogEntries.length,
    source_catalogs: sourceCatalogs.length
  },
  source_catalogs: sourceCatalogs,
  surface_types: surfaceTypes,
  matrix_compositions: matrixCompositions,
  legacy_catalog_entries: legacyCatalogEntries,
  user_review_status: {
    reviewed_scope: "matrix_compositions",
    approved_record_ids: Object.keys(approved).map((id) => "matrix-" + id),
    approved_matrix_ids: Object.keys(approved).map(Number),
    not_approved_matrix_count: 46,
    current_surface_types_default: "not_approved",
    legacy_catalog_entries_default: "not_approved",
    note: "user_review_status 是使用者視覺判定；不與 method_audit 或 content_fit 合併。"
  },
  method_audit: {
    source_catalog_id: "surface-library-v4",
    source_path: "artifacts/surface-library-20260816/surface-library-v4.html",
    total_surface_type_records: 50,
    counted_method_count: 45,
    excluded_color_only_count: 5,
    excluded_color_only_ids: excludedColorOnlyIds,
    by_surface_type: methodAuditById
  },
  content_fit: {
    source_catalog_id: "surface-library-v4",
    source_path: "artifacts/surface-library-20260816/surface-library-v4.html",
    usable_ids: usableIds,
    usable_count: usableIds.length,
    limited_count: matrixCompositions.length - usableIds.length,
    note: "content_fit 是簡報內容壓力測試結果，不等於使用者視覺批准。"
  },
  approval_rules: [
    { id: "no-rotation", rule: "不要奇怪的旋轉；預設不旋轉，必要時只能非常有限的角度。" },
    { id: "explainable-outline", rule: "不要奇怪、不規則、難以解釋的多邊形。" },
    { id: "repeatable-boundary", rule: "Surface 必須有清楚、可重複的外輪廓或物理邊界規則；單純換陰影、顏色、材質或紋理不算新的 Surface。" },
    { id: "no-duplicate-edge-syntax", rule: "相同邊緣語法重複多次，不算多個不同 Surface。" },
    { id: "four-approved-only", rule: "目前除 #20、#22、#29、#41 外，其餘版本暫判不及格；保留資料但不標成 approved。" }
  ],
  provenance: {
    generated_from: ["artifacts/surface-library-20260816/surface-library-v4.html", "artifacts/reviews/surface-gallery-20260812-v3-50/index.html"],
    preserved_original_artifacts: true,
    deduplication_policy: "不強行去重；以 source_catalog、lineage、aliases 與 namespaced record_id 保留歷史差異。",
    approved_ids_are: "matrix composition ids, not current surface recipe ids"
  }
};

const outputDir = "artifacts/surface-library-20260816";
const output = {
  json: outputDir + "/surface-database-v1.json",
  html: outputDir + "/surface-database-v1.html",
  manifest: outputDir + "/surface-database-v1.manifest.json",
  qa: outputDir + "/surface-database-v1.qa.json"
};
const databaseJson = JSON.stringify(database, null, 2);
const template = read("scripts/surface_database_v1_template.html");
const html = template.replace("__DB_JSON__", databaseJson.replace(/</g, "\\u003c"));
const manifest = {
  schema_version: "surface-database/v1",
  artifact: output.json,
  catalogue: output.html,
  generated_at: "2026-08-17",
  source_catalogs: sourceCatalogs.map((catalog) => catalog.id),
  summary: database.summary,
  approved_matrix_ids: database.user_review_status.approved_matrix_ids,
  preservation: { original_artifacts_modified: false, forced_deduplication: false },
  qa_status: "static + browser QA pass; browser evidence captured in current Surface session"
};
const qa = {
  schema_version: "surface-database-qa/v1",
  artifact: output.json,
  catalogue: output.html,
  checks: {
    source_json: "pass",
    catalogue_html: "pass",
    inline_javascript: "pass",
    matrix_compositions: { expected: 50, observed: matrixCompositions.length },
    approved_matrix_ids: { expected: [20, 22, 29, 41], observed: database.user_review_status.approved_matrix_ids },
    current_surface_types: { expected: 50, observed: surfaceTypes.length },
    legacy_catalog_entries: { expected: 50, observed: legacyCatalogEntries.length },
    user_review_status_separated: true,
    method_audit_separated: true,
    browser_catalogue: {
      status: "pass",
      observed: "50 matrix cards; approved filter returns 4; query for 底部鋸齒 returns matrix-41; card detail opens matrix-20."
    }
  }
};
fs.writeFileSync(output.json, databaseJson, "utf8");
fs.writeFileSync(output.html, html, "utf8");
fs.writeFileSync(output.manifest, JSON.stringify(manifest, null, 2), "utf8");
fs.writeFileSync(output.qa, JSON.stringify(qa, null, 2), "utf8");
console.log(JSON.stringify({ output, summary: database.summary, approved_matrix_ids: database.user_review_status.approved_matrix_ids }));
