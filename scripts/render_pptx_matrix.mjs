import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

function argsOf(argv) {
  const out = { themes: [] };
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    const value = argv[i + 1];
    if (key === "--theme") { out.themes.push(value); i += 1; }
    else if (key === "--matrix") { out.matrix = value; i += 1; }
    else if (key === "--output-dir") { out.outputDir = value; i += 1; }
    else if (key === "--preview-dir") { out.previewDir = value; i += 1; }
    else if (key === "--inspect-dir") { out.inspectDir = value; i += 1; }
    else if (key === "--limit-layouts") { out.limitLayouts = Number(value); i += 1; }
    else if (key === "--selection-manifest") { out.selectionManifest = value; i += 1; }
  }
  if (!out.matrix || !out.outputDir) throw new Error("--matrix and --output-dir are required");
  return out;
}

function sampleText(role) {
  if (role === "decoration") return "";
  if (role === "title") return "清楚的重點標題";
  if (role === "subtitle") return "用一句話補充背景與用途";
  if (role === "picture") return "圖片內容區";
  if (role === "chart") return "數據視覺區";
  if (role === "table") return "比較資訊區";
  return "重點內容";
}

function contentText(selectionSlide, row, rowIndex = 0) {
  const content = selectionSlide?.content && typeof selectionSlide.content === "object"
    ? selectionSlide.content
    : {};
  const role = row.placeholder_type;
  if (["picture", "chart", "table"].includes(role)) return "";
  const key = row.id || row.source_slot_id;
  const aliases = {
    headline: ["headline", "title"],
    "supporting-text": ["supporting-text", "subtitle"],
    body: ["body", "intro", "description"],
    quote: ["quote", "headline"],
  };
  const candidates = [key, row.source_slot_id, ...(aliases[key] || [])].filter(Boolean);
  for (const candidate of candidates) {
    const value = content[candidate];
    if (typeof value === "string" && value.trim()) return value;
    if (Array.isArray(value) && value.length) return value.map((item) => typeof item === "string" ? item : JSON.stringify(item)).join("\n");
  }
  if (row.optional) return "";
  const moduleMatch = String(key).match(/^module[-_](\d+)[-_](label|body)$/i);
  if (moduleMatch) {
    const moduleIndex = Number(moduleMatch[1]) - 1;
    const item = Array.isArray(content.items) ? content.items[moduleIndex] : null;
    if (item && typeof item === "object") {
      return moduleMatch[2].toLowerCase() === "label"
        ? item.title || item.label || item.tag || ""
        : item.body || item.description || "";
    }
    const lines = typeof content.body === "string"
      ? content.body.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
      : [];
    if (lines[moduleIndex]) {
      const [label, body] = lines[moduleIndex].split(/\s*→\s*/, 2);
      return moduleMatch[2].toLowerCase() === "label" ? label : (body || label);
    }
  }
  const numbered = String(key).match(/(?:chapter|item|module|stage|step|metric|priority|quadrant)[-_]?(\d+)/i);
  if (numbered) {
    const index = Number(numbered[1]) - 1;
    const listValue = content.items || content.chapters || content.stages || content.stats || content.quadrants || content.priorities;
    if (Array.isArray(listValue) && listValue[index] != null) {
      const item = listValue[index];
      if (typeof item === "string") return item;
      if (typeof item === "object") return item.title || item.label || item.body || item.value || "";
    }
    if (typeof content["toc-content"] === "string") {
      const lines = content["toc-content"].split(/\r?\n/).filter((line) => line.trim());
      if (lines[index]) return lines[index];
    }
  }
  if (/left[-_]content/i.test(String(key)) || /right[-_]content/i.test(String(key))) {
    const metrics = Object.keys(content)
      .filter((candidate) => /^metric[-_]\d+$/i.test(candidate))
      .sort()
      .map((candidate) => content[candidate])
      .filter((value) => typeof value === "string");
    if (metrics.length) {
      const midpoint = Math.ceil(metrics.length / 2);
      return metrics.slice(/left[-_]content/i.test(String(key)) ? 0 : midpoint, /left[-_]content/i.test(String(key)) ? midpoint : undefined).join("\n");
    }
  }
  if (/before[-_]header|left[-_]label/i.test(String(key))) return content.before_header || content.left_label || "Before";
  if (/after[-_]header|right[-_]label/i.test(String(key))) return content.after_header || content.right_label || "After";
  if (/before[-_]content/i.test(String(key))) return content.before_content || content.body || "";
  if (/after[-_]content/i.test(String(key))) return content.after_content || content.body || "";
  if (String(key).toLowerCase() === "speaker" && content.meta) return content.meta;
  if (role === "title") return content.title || content.headline || "";
  if (role === "subtitle") return content.subtitle || content.intro || content.support || "";
  if (role === "body") return content.body || content.description || content.intro || "";
  return sampleText(role);
}

function fontSize(row) {
  // Catalog owns the canonical stage px. Artifact-tool receives the same
  // scale as geometry: 1920px stage -> 1280px artifact stage.
  return Number(row.font_size_stage_px || 24) * (2 / 3);
}

function placeholderType(role) {
  if (role === "decoration") return "content";
  return ["title", "subtitle", "body", "picture", "chart", "table"].includes(role) ? role : "body";
}

function stageRegionToArtifact(region) {
  // Canonical stage is 1920x1080; artifact-tool is exactly 1280x720.
  // Percent regions therefore map through one explicit 2/3 boundary.
  const [x, y, w, h] = region;
  return { left: x * 19.2 * (2 / 3), top: y * 10.8 * (2 / 3), width: w * 19.2 * (2 / 3), height: h * 10.8 * (2 / 3) };
}

function addSurface(layout, surface, theme, index) {
  if (!Array.isArray(surface?.region) || surface.region.length !== 4) {
    throw new Error(`Invalid PPTX Surface region at index ${index}`);
  }
  const position = stageRegionToArtifact(surface.region);
  const geometry = surface.shape === "rect" ? "rect" : "roundRect";
  const fill = surface.fill || theme.colors.surface;
  const lineFill = surface.line_fill || "none";
  const lineWidth = Number(surface.line_width || 0);
  const shape = layout.shapes.add({
    geometry,
    name: `surface-${surface.id || index}`,
    position,
    fill,
    line: { style: "solid", fill: lineFill, width: lineWidth },
  });
  if (surface.transparency != null && shape.fill && typeof shape.fill === "object") {
    shape.fill.transparency = Number(surface.transparency);
  }
  return shape;
}

function placeholderRows(spec) {
  if (spec.pptx?.placeholder_schema?.length) return spec.pptx.placeholder_schema;
  return spec.slots
    .filter((slot) => slot.pptx?.placeholder_type !== "decoration")
    .map((slot) => ({ id: slot.id, source_slot_id: slot.id, placeholder_type: slot.pptx?.placeholder_type || slot.semantic_role, content_kind: slot.pptx?.placeholder_type === "picture" ? "image" : "text", region: slot.region }));
}

function placeholderIndices(rows) {
  const counts = new Map();
  return rows.map((row) => {
    const type = placeholderType(row.placeholder_type);
    const index = counts.get(type) || 0;
    counts.set(type, index + 1);
    return index;
  });
}

function addPlaceholder(layout, theme, row, index) {
  const role = row.placeholder_type;
  const position = stageRegionToArtifact(row.region);
  // Shape-based placeholders preserve one stable name per atomic slot in the
  // exported OOXML. The inline collection API currently normalizes duplicate
  // body names during export, which collapses otherwise distinct slots.
  const item = layout.shapes.addPlaceholder(row.id);
  item.placeholder.type = placeholderType(role);
  item.placeholder.index = index;
  item.position = position;
  item.fill = "none";
  item.line = { style: "solid", fill: "none", width: 0 };
  // Layout owns the empty placeholder frame. Sample copy belongs only to the
  // populated slide so PowerPoint Reset cannot resurrect diagnostic text.
  item.text = "";
  item.text.style = {
    fontSize: fontSize(row),
    color: role === "subtitle" ? theme.colors.secondary : theme.colors.primary,
    bold: role === "title",
    alignment: role === "title" ? "left" : "center",
    verticalAlignment: "middle",
    typeface: theme.typography?.heading?.family || theme.typography?.body?.family || "Noto Sans TC",
  };
  return item;
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function addBackground(layout, selection, role, projectRoot) {
  const selected = selection?.background_selection?.selected;
  const backgroundRole = selected?.roles?.find((item) => item.id === role);
  if (!backgroundRole?.asset) throw new Error("Selection manifest has no ready background asset for role: " + role);
  const assetPath = path.isAbsolute(backgroundRole.asset)
    ? backgroundRole.asset
    : path.resolve(projectRoot, backgroundRole.asset);
  const bytes = await fs.readFile(assetPath);
  const dataUrl = `data:image/png;base64,${Buffer.from(bytes).toString("base64")}`;
  const image = layout.images.add({
    dataUrl,
    fit: "fill",
    alt: `${selected.background_set_id} ${role} background`,
    name: `background-${role}`,
  });
  image.position = { left: 0, top: 0, width: 1280, height: 720 };
  return true;
}

async function buildTheme(theme, layouts, options) {
  const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
  const master = deck.masters.add(`theme--${theme.id}`);
  const slides = [];
  const layoutMap = new Map();
  const layoutSpecs = [];
  for (const spec of layouts) {
    const layoutName = spec.pptx?.layout_name || `layout--${spec.id}`;
    if (!layoutMap.has(layoutName)) {
      const layout = deck.layouts.add(layoutName);
      layout.setParentLayoutId(master.id);
      if (options.selection) {
        const role = spec._selection?.background_role || "content-a";
        await addBackground(layout, options.selection, role, options.projectRoot);
      }
      (spec.pptx?.surfaces || []).forEach((surface, index) => addSurface(layout, surface, theme, index));
      const rows = placeholderRows(spec);
      const indices = placeholderIndices(rows);
      rows.forEach((row, index) => addPlaceholder(layout, theme, row, indices[index]));
      layoutMap.set(layoutName, layout);
      layoutSpecs.push({ spec, layout, rows });
    }
  }

  for (const [layoutIndex, spec] of layouts.entries()) {
    const layoutName = spec.pptx?.layout_name || `layout--${spec.id}`;
    const entry = layoutSpecs.find((item) => item.layout === layoutMap.get(layoutName));
    const layout = layoutMap.get(layoutName);
    const rows = entry?.rows || placeholderRows(spec);
    const slide = deck.slides.add();
    slide.setLayout(layout);
    slide.background.fill = theme.colors.background;
    const selectionSlide = spec._selection;
    // Fill inherited placeholders on the slide; do not add visible duplicate
    // shapes that mask the actual editable Placeholder.
    const indices = placeholderIndices(rows);
    rows.forEach((row, rowIndex) => {
      let target;
      try { target = slide.placeholders.getItem(row.id); } catch (_) { target = null; }
      target ||= slide.placeholders.getAll().find((item) => (
        item.placeholder.type === placeholderType(row.placeholder_type)
        && item.placeholder.index === indices[rowIndex]
      ));
      if (target) target.text = contentText(selectionSlide, row, rowIndex);
    });
    const footer = slide.shapes.add({
      geometry: "textbox",
      name: `footer-${layoutIndex + 1}`,
      position: { left: 24, top: 690, width: 1232, height: 18 },
      fill: "none",
      line: { style: "solid", fill: "none", width: 0 },
    });
    footer.text = `${String(layoutIndex + 1).padStart(2, "0")} / ${String(layouts.length).padStart(2, "0")}   ${spec.id}   ·   ${theme.id}`;
    footer.text.style = { fontSize: 11, color: theme.colors.secondary, typeface: "Noto Sans TC", alignment: "right" };
    slides.push(slide);
  }

  await fs.mkdir(options.outputDir, { recursive: true });
  const outPath = options.outputPath || path.join(options.outputDir, `${options.deckId || theme.id}.pptx`);
  const pptx = await PresentationFile.exportPptx(deck);
  await pptx.save(outPath);
  let manifestPath = null;
  if (options.selection) {
    manifestPath = options.manifestOutput || path.join(options.outputDir, `${options.deckId || theme.id}.manifest.json`);
    const projectRoot = options.projectRoot || process.cwd();
    const relative = (filePath) => path.relative(projectRoot, filePath).split(path.sep).join("/");
    await fs.writeFile(manifestPath, `${JSON.stringify({
      ...options.selection,
      artifact: relative(outPath),
      selection_manifest: relative(path.resolve(options.selectionManifest)),
      renderer: {
        id: "pptx",
        engine: "@oai/artifact-tool",
        fidelity: "hybrid",
        native_editable_content: true,
        raster_fallbacks: [],
      },
      materialized_layouts: [...layoutMap.keys()],
      generated_at: new Date().toISOString(),
    }, null, 2)}\n`, "utf8");
  }

  if (options.inspectDir) {
    await fs.mkdir(options.inspectDir, { recursive: true });
    const inspection = await deck.inspect({ kind: "slide,layout", maxChars: 2000000 });
    await fs.writeFile(path.join(options.inspectDir, `${options.deckId || theme.id}.ndjson`), inspection.ndjson, "utf8");
  }
  if (options.previewDir) {
    const themePreviewDir = options.selection ? options.previewDir : path.join(options.previewDir, theme.id);
    await fs.mkdir(themePreviewDir, { recursive: true });
    for (const [index, slide] of slides.entries()) {
      await writeBlob(path.join(themePreviewDir, `slide-${String(index + 1).padStart(3, "0")}.png`), await deck.export({ slide, format: "png", scale: 1 }));
    }
  }
  return { theme: theme.id, slides: slides.length, output: outPath, manifest: manifestPath };
}

async function main() {
  const options = argsOf(process.argv);
  const matrix = JSON.parse(await fs.readFile(options.matrix, "utf8"));
  if (options.selectionManifest) {
    const selectionPath = path.resolve(options.selectionManifest);
    const selection = JSON.parse(await fs.readFile(selectionPath, "utf8"));
    if (selection.kind !== "pptx_random_selection_manifest") throw new Error("Invalid PPTX selection manifest kind");
    if (!selection.background_selection || selection.background_selection.status !== "ready") {
      throw new Error("PPTX randomized build requires a ready background set; generation-required cannot silently fall back");
    }
    const themeId = selection.theme_selection?.selected;
    const theme = matrix.themes.find((item) => item.id === themeId);
    if (!theme) throw new Error(`Selection manifest references unknown Theme: ${themeId}`);
    if (!selection.background_selection.selected || selection.background_selection.selected.theme_id !== themeId) {
      throw new Error("Selection manifest background Theme does not match selected PPTX Theme");
    }
    const layoutById = new Map(matrix.layouts.map((item) => [item.id, item]));
    const selectedLayouts = (selection.slides || []).map((row) => {
      const base = layoutById.get(row.layout_id);
      if (!base) throw new Error(`Selection manifest references unknown Layout: ${row.layout_id}`);
      return {
        ...base,
        _selection: row,
        pptx: {
          ...(base.pptx || {}),
          layout_name: row.layout_name || base.pptx?.layout_name || `layout--${base.id}`,
          selected_variant_id: row.selected_variant_id,
          variant_candidates: row.variant_candidates || base.pptx?.variant_candidates || [],
          placeholder_schema: row.placeholder_schema || base.pptx?.placeholder_schema || [],
          surfaces: row.surfaces || base.pptx?.surfaces || [],
        },
      };
    });
    if (!selectedLayouts.length) throw new Error("Selection manifest contains no slides");
    // Selection manifests live at artifacts/pptx/manifests; three parents
    // resolve back to the repository root used by portable asset paths.
    const projectRoot = path.resolve(path.dirname(selectionPath), "..", "..", "..");
    const selectionOptions = {
      ...options,
      selection,
      deckId: selection.deck_id || `pptx-random-${selection.seed}`,
      projectRoot,
      outputDir: options.outputDir,
      previewDir: options.previewDir,
      inspectDir: options.inspectDir,
    };
    const result = await buildTheme(theme, selectedLayouts, selectionOptions);
    console.log(JSON.stringify({ ...result, seed: selection.seed, randomized_dimensions: selection.randomized_dimensions }));
    return;
  }
  const selected = new Set(options.themes);
  const themes = matrix.themes.filter((theme) => selected.size === 0 || selected.has(theme.id));
  const layouts = matrix.layouts.slice(0, options.limitLayouts || matrix.layouts.length);
  const results = [];
  for (const theme of themes) {
    results.push(await buildTheme(theme, layouts, options));
    console.log(JSON.stringify(results.at(-1)));
  }
  console.log(JSON.stringify({ themes: themes.length, layoutsPerTheme: layouts.length, slides: themes.length * layouts.length }));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
