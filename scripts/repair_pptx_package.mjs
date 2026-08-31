import fs from "node:fs/promises";
import JSZip from "jszip";

const OOXML_TYPES = {
  title: "title",
  subtitle: "subTitle",
  body: "body",
  picture: "pic",
  chart: "chart",
  table: "tbl",
  content: "body",
};

function inferPlaceholderType(name) {
  const key = String(name || "").toLowerCase();
  if (/(^|[-_])(title|headline)([-_]|$)/.test(key) || key === "title" || key === "headline") return "title";
  if (/(subtitle|subheading|supporting|speaker|org|meta|label)/.test(key)) return "subtitle";
  if (/(picture|photo|image|logo|hero)/.test(key)) return "picture";
  if (/(chart|graph)/.test(key)) return "chart";
  if (/(table|tbl)/.test(key)) return "table";
  return "body";
}

function replacePlaceholderTag(block, type, index) {
  const tagMatch = block.match(/<p:ph\b[^>]*\/>/);
  if (!tagMatch) return block;
  const oldTag = tagMatch[0];
  const attrs = (oldTag.match(/<p:ph\b([^>]*)\/>/)?.[1] || "")
    .replace(/\s+(?:type|idx)="[^"]*"/g, "")
    .trim();
  const suffix = attrs ? ` ${attrs}` : "";
  const nextTag = `<p:ph type="${OOXML_TYPES[type] || OOXML_TYPES.body}" idx="${index}"${suffix} />`;
  return block.replace(oldTag, nextTag);
}

function shapeName(block) {
  return block.match(/<p:cNvPr\b[^>]*\bname="([^"]*)"/)?.[1] || "";
}

function patchPart(xml, mapping) {
  let index = 0;
  return xml.replace(/<p:sp>[\s\S]*?<\/p:sp>/g, (block) => {
    if (!block.includes("<p:ph")) return block;
    const name = shapeName(block);
    const info = mapping.get(name) || { type: inferPlaceholderType(name), index: index++ };
    index = Math.max(index, Number(info.index) + 1);
    return replacePlaceholderTag(block, info.type, info.index);
  });
}

function extractLayoutMapping(xml) {
  const mapping = new Map();
  let index = 0;
  for (const block of xml.match(/<p:sp>[\s\S]*?<\/p:sp>/g) || []) {
    if (!block.includes("<p:ph")) continue;
    const name = shapeName(block);
    if (!name) continue;
    const type = inferPlaceholderType(name);
    mapping.set(name, { type, index });
    index += 1;
  }
  return mapping;
}

function layoutTarget(relXml) {
  const match = relXml.match(/<Relationship\b[^>]*Type="[^"]*\/slideLayout"[^>]*Target="([^"]+)"/);
  if (!match) return null;
  const target = match[1].replace(/^\//, "");
  return target.startsWith("ppt/") ? target : `ppt/slides/${target}`;
}

function repairContentTypes(xml) {
  let next = xml.replace(
    /<Default Extension="xml" ContentType="application\/vnd\.openxmlformats-package\.core-properties\+xml"\s*\/>/,
    '<Default Extension="xml" ContentType="application/xml" />',
  );
  if (!/PartName="\/docProps\/core\.xml"/.test(next)) {
    next = next.replace(
      /<\/Types>/,
      '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml" /></Types>',
    );
  }
  return next;
}

function relationshipBaseDir(relPath) {
  if (relPath === "_rels/.rels") return "";
  return relPath.replace(/\/\_rels\/[^/]+\.rels$/, "");
}

function repairRelationships(relPath, xml) {
  const base = relationshipBaseDir(relPath).split("/").filter(Boolean);
  return xml.replace(/(<Relationship\b[^>]*\bTarget=")([^"]+)(")/g, (full, prefix, target, suffix) => {
    if (!target.startsWith("/")) return full;
    const targetParts = target.replace(/^\//, "").split("/").filter(Boolean);
    const common = Math.min(base.length, targetParts.length);
    let shared = 0;
    while (shared < common && base[shared] === targetParts[shared]) shared += 1;
    const up = new Array(base.length - shared).fill("..");
    const down = targetParts.slice(shared);
    const relative = [...up, ...down].join("/") || ".";
    return `${prefix}${relative}${suffix}`;
  });
}

export async function repairPptxPackage(filePath) {
  const input = await fs.readFile(filePath);
  const zip = await JSZip.loadAsync(input);
  const layoutMappings = new Map();

  const layoutEntries = Object.keys(zip.files)
    .filter((name) => /^ppt\/slideLayouts\/slideLayout\d+\.xml$/.test(name))
    .sort((a, b) => Number(a.match(/(\d+)\.xml$/)?.[1]) - Number(b.match(/(\d+)\.xml$/)?.[1]));
  for (const name of layoutEntries) {
    const xml = await zip.file(name).async("string");
    const mapping = extractLayoutMapping(xml);
    layoutMappings.set(name, mapping);
    zip.file(name, patchPart(xml, mapping));
  }

  const slideEntries = Object.keys(zip.files)
    .filter((name) => /^ppt\/slides\/slide\d+\.xml$/.test(name))
    .sort((a, b) => Number(a.match(/(\d+)\.xml$/)?.[1]) - Number(b.match(/(\d+)\.xml$/)?.[1]));
  for (const name of slideEntries) {
    const relName = name.replace("ppt/slides/", "ppt/slides/_rels/") + ".rels";
    const relXml = zip.file(relName) ? await zip.file(relName).async("string") : "";
    const target = layoutTarget(relXml);
    const mapping = (target && layoutMappings.get(target)) || new Map();
    const xml = await zip.file(name).async("string");
    zip.file(name, patchPart(xml, mapping));
  }

  const contentTypes = zip.file("[Content_Types].xml");
  if (contentTypes) {
    zip.file("[Content_Types].xml", repairContentTypes(await contentTypes.async("string")));
  }

  for (const name of Object.keys(zip.files).filter((entry) => entry.endsWith(".rels"))) {
    const rel = zip.file(name);
    if (!rel) continue;
    zip.file(name, repairRelationships(name, await rel.async("string")));
  }

  const output = await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
  await fs.writeFile(filePath, output);
  return { filePath, layouts: layoutEntries.length, slides: slideEntries.length };
}

if (process.argv[1] && process.argv[1].endsWith("repair_pptx_package.mjs")) {
  const target = process.argv[2];
  if (!target) throw new Error("Usage: node repair_pptx_package.mjs <pptx>");
  console.log(JSON.stringify(await repairPptxPackage(target)));
}
