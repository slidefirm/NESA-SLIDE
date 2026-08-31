const fs = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");
const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    const key = argv[index];
    const value = argv[index + 1];
    if (key === "--manifest") { out.manifest = value; index += 1; }
    else if (key === "--icon-dir") { out.iconDir = value; index += 1; }
    else if (key === "--report") { out.report = value; index += 1; }
  }
  if (!out.manifest || !out.iconDir || !out.report) {
    throw new Error("--manifest, --icon-dir and --report are required");
  }
  return out;
}

const FORBIDDEN_ATTRS = ["transform", "filter", "style", "mask", "clip-path"];
const ALLOWED_PRIMITIVES = new Set(["path", "line", "polyline", "polygon", "rect", "circle", "ellipse"]);

async function main() {
  const options = argsOf(process.argv);
  const manifestPath = path.resolve(options.manifest);
  const iconDir = path.resolve(options.iconDir);
  const reportPath = path.resolve(options.report);
  const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
  const canonical = manifest.canonical || {};
  const safe = canonical.safe_area || [2, 2, 22, 22];
  const maxPrimitives = Number(canonical.max_primitives || 12);
  const entries = Array.isArray(manifest.icons) ? manifest.icons : [];
  if (!entries.length) throw new Error("icon family manifest has no icons");

  const sources = [];
  const wrappers = [];
  for (const entry of entries) {
    const filePath = path.resolve(iconDir, entry.file);
    const source = await fs.readFile(filePath, "utf8");
    sources.push({
      id: entry.id,
      file: path.relative(process.cwd(), filePath).replaceAll("\\", "/"),
      sha256: crypto.createHash("sha256").update(source).digest("hex"),
      source,
    });
    wrappers.push(`<div data-icon-id="${entry.id}">${source}</div>`);
  }

  const { chromium } = loadPlaywright();
  console.error("icon-family-qa: launching browser");
  const browser = await chromium.launch({
    headless: true,
    executablePath: browserExecutable(),
    timeout: 30000,
  });
  console.error("icon-family-qa: browser ready");
  let measured;
  try {
    const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
    await page.setContent(`<!doctype html><body>${wrappers.join("")}</body>`, {
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });
    measured = [];
    for (const entry of entries) {
      console.error(`icon-family-qa: measuring ${entry.id}`);
      const result = await page.evaluate(({ id, forbidden }) => {
      const wrapper = document.querySelector(`[data-icon-id="${id}"]`);
      const svg = wrapper?.querySelector("svg");
      if (!svg) return { id, missing: true, parts: [], ink: null, root: {} };
      const rootStroke = Number.parseFloat(svg.getAttribute("stroke-width") || "0");
      const parts = [...svg.children].filter((node) => node instanceof SVGGeometryElement).map((node) => {
        const box = node.getBBox();
        const ownStroke = node.getAttribute("stroke-width");
        const strokeNone = node.getAttribute("stroke") === "none";
        const strokeWidth = strokeNone ? 0 : Number.parseFloat(ownStroke || String(rootStroke));
        const pad = strokeWidth / 2;
        return {
          tag: node.tagName,
          strokeWidth,
          badAttrs: forbidden.filter((name) => node.hasAttribute(name)),
          ink: [box.x - pad, box.y - pad, box.x + box.width + pad, box.y + box.height + pad],
        };
      });
      const ink = parts.reduce(
        (bounds, part) => [
          Math.min(bounds[0], part.ink[0]),
          Math.min(bounds[1], part.ink[1]),
          Math.max(bounds[2], part.ink[2]),
          Math.max(bounds[3], part.ink[3]),
        ],
        [Infinity, Infinity, -Infinity, -Infinity],
      ).map((value) => Math.round(value * 1000) / 1000);
      return {
        id,
        missing: false,
        root: {
          viewBox: svg.getAttribute("viewBox"),
          fill: svg.getAttribute("fill"),
          stroke: svg.getAttribute("stroke"),
          strokeWidth: rootStroke,
          linecap: svg.getAttribute("stroke-linecap"),
          linejoin: svg.getAttribute("stroke-linejoin"),
          badAttrs: forbidden.filter((name) => svg.hasAttribute(name)),
          externalRefs: [...svg.querySelectorAll("[href],[xlink\\:href]")].length,
        },
        parts,
        ink,
        };
      }, { id: entry.id, forbidden: FORBIDDEN_ATTRS });
      measured.push(result);
    }
  } finally {
    await Promise.race([
      browser.close(),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]);
  }
  console.error("icon-family-qa: measurement complete");

  const entryById = new Map(entries.map((entry) => [entry.id, entry]));
  const icons = measured.map((icon) => {
    const entry = entryById.get(icon.id) || {};
    const issues = [];
    if (icon.missing) issues.push("missing-svg");
    if (!icon.missing) {
      if (icon.root.viewBox !== "0 0 24 24") issues.push(`viewBox ${icon.root.viewBox}`);
      if (icon.root.fill !== "none") issues.push(`root fill ${icon.root.fill}`);
      if (icon.root.stroke !== "currentColor") issues.push(`root stroke ${icon.root.stroke}`);
      if (icon.root.strokeWidth !== 2) issues.push(`root stroke-width ${icon.root.strokeWidth}`);
      if (icon.root.linecap !== "round" || icon.root.linejoin !== "round") issues.push("cap-or-join-not-round");
      if (icon.root.externalRefs) issues.push("external-reference");
      if (icon.root.badAttrs.length) issues.push(`root forbidden attrs ${icon.root.badAttrs.join(",")}`);
      if (icon.parts.length > maxPrimitives) issues.push(`primitives ${icon.parts.length} > ${maxPrimitives}`);
      const invalidPrimitives = icon.parts.filter((part) => !ALLOWED_PRIMITIVES.has(part.tag)).map((part) => part.tag);
      if (invalidPrimitives.length) issues.push(`invalid primitives ${[...new Set(invalidPrimitives)].join(",")}`);
      const badAttrs = icon.parts.flatMap((part) => part.badAttrs);
      if (badAttrs.length) issues.push(`forbidden attrs ${[...new Set(badAttrs)].join(",")}`);
      if (icon.ink[0] < safe[0] || icon.ink[1] < safe[1] || icon.ink[2] > safe[2] || icon.ink[3] > safe[3]) {
        issues.push(`ink outside safe area: ${icon.ink.join(",")}`);
      }
    }
    if (!Array.isArray(entry.optical_center) || entry.optical_center.length !== 2) issues.push("missing-optical-center");
    if (!Array.isArray(entry.optical_size) || entry.optical_size.length !== 2) issues.push("missing-optical-size");
    return {
      id: icon.id,
      file: entry.file,
      source_sha256: sources.find((source) => source.id === icon.id)?.sha256 || null,
      primitives: icon.parts.length,
      ink_bounds: icon.ink,
      ink_size: icon.ink ? [icon.ink[2] - icon.ink[0], icon.ink[3] - icon.ink[1]].map((value) => Math.round(value * 1000) / 1000) : null,
      optical_center: entry.optical_center || null,
      optical_size: entry.optical_size || null,
      issues,
    };
  });

  const spans = icons.filter((icon) => icon.ink_size).map((icon) => Math.max(...icon.ink_size));
  const familySpanRatio = Math.max(...spans) / Math.min(...spans);
  const familyIssues = [];
  if (familySpanRatio > 1.2) familyIssues.push(`optical span ratio ${familySpanRatio.toFixed(3)} > 1.2`);
  const failing = icons.filter((icon) => icon.issues.length).map((icon) => icon.id);
  const status = failing.length || familyIssues.length ? "fail" : "pass";
  const report = {
    schema_version: "svg-icon-family-qa/v1",
    manifest: path.relative(process.cwd(), manifestPath).replaceAll("\\", "/"),
    family_id: manifest.family_id,
    generation_mode: manifest.generation_mode,
    status,
    canonical: { safe_area: safe, max_primitives: maxPrimitives },
    family_span_ratio: Math.round(familySpanRatio * 1000) / 1000,
    family_issues: familyIssues,
    icons,
    summary: { count: icons.length, failing },
  };
  await fs.mkdir(path.dirname(reportPath), { recursive: true });
  await fs.writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify({ status, icons: icons.length, failing, familyIssues }));
  process.exit(status === "pass" ? 0 : 1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
