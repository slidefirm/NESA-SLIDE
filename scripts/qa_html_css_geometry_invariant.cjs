const fs = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");
const { pathToFileURL } = require("node:url");
const { loadPlaywright, browserExecutable } = require("./playwright_runtime.cjs");

const PROJECT_ROOT = path.resolve(__dirname, "..");

function portableReportPath(value) {
  const resolved = path.resolve(value);
  const relative = path.relative(PROJECT_ROOT, resolved);
  if (relative === "") return ".";
  if (relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative)) {
    return relative.split(path.sep).join("/");
  }
  return resolved.split(path.sep).join("/");
}

function argsOf(argv) {
  const out = { tolerance: 0.5 };
  for (let index = 2; index < argv.length; index += 1) {
    const key = argv[index];
    const value = argv[index + 1];
    if (key === "--file") { out.file = value; index += 1; }
    else if (key === "--report") { out.report = value; index += 1; }
    else if (key === "--tolerance") { out.tolerance = Number(value); index += 1; }
  }
  if (!out.file || !out.report) throw new Error("--file and --report are required");
  if (!Number.isFinite(out.tolerance) || out.tolerance < 0) throw new Error("--tolerance must be non-negative");
  return out;
}

async function main() {
  const options = argsOf(process.argv);
  const htmlPath = path.resolve(options.file);
  const markup = await fs.readFile(htmlPath, "utf8");
  const baseHref = pathToFileURL(`${path.dirname(htmlPath)}${path.sep}`).href;
  const markupWithBase = markup.replace(/<head>/i, `<head><base href="${baseHref}">`);
  const { chromium } = loadPlaywright();
  const executablePath = browserExecutable();
  if (!process.env.BROWSER_CDP_URL && !executablePath) {
    throw new Error("No Chrome or Edge executable found for CSS geometry QA");
  }
  const browser = process.env.BROWSER_CDP_URL
    ? await chromium.connectOverCDP(process.env.BROWSER_CDP_URL)
    : await chromium.launch({ headless: true, executablePath });
  const report = {
    file: portableReportPath(htmlPath),
    fileSha256: crypto.createHash("sha256").update(markup).digest("hex"),
    contract: "references/html-css-ownership-contract.md",
    tolerancePx: options.tolerance,
    status: "fail",
    slides: 0,
    targets: 0,
    appearanceOwners: [],
    issues: [],
  };
  try {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.setContent(markupWithBase, { waitUntil: "domcontentloaded", timeout: 120000 });
    await Promise.race([page.evaluate(() => document.fonts?.ready), page.waitForTimeout(5000)]);
    await page.waitForFunction(
      () => document.documentElement.dataset.layoutReady === "true",
      null,
      { timeout: 120000 },
    );

    const result = await page.evaluate(async ({ tolerance }) => {
      const appearance = [...document.querySelectorAll(
        'style[data-css-owner="theme-appearance"],style[data-css-owner="preset-appearance"]',
      )];
      const owners = [...new Set(appearance.map((style) => style.dataset.cssOwner))];
      const issues = [];
      const slides = [...document.querySelectorAll("#stage > .slide")];
      const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const round = (value) => Math.round(value * 1000) / 1000;
      const geometryProperties = [
        "position", "left", "top", "right", "bottom", "width", "height",
        "minWidth", "maxWidth", "minHeight", "maxHeight", "display", "overflow",
        "paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
        "marginTop", "marginRight", "marginBottom", "marginLeft",
        "gridTemplateColumns", "gridTemplateRows", "gap", "alignItems", "justifyContent",
        "transform", "translate", "rotate", "scale", "writingMode", "textAlign",
        "fontSize", "lineHeight", "whiteSpace",
      ];
      const snapshot = (slide) => {
        const stage = document.querySelector("#stage");
        const stageRect = stage.getBoundingClientRect();
        const scale = stageRect.width / 1920 || 1;
        const targets = [...slide.querySelectorAll('.content[data-content-area],.el')];
        return targets.map((element, index) => {
          const style = getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          const properties = Object.fromEntries(geometryProperties.map((property) => [property, style[property]]));
          return {
            index,
            label: element.id || element.getAttribute("data-edit-id") || String(element.className || element.tagName),
            rect: {
              x: round((rect.left - stageRect.left) / scale),
              y: round((rect.top - stageRect.top) / scale),
              width: round(rect.width / scale),
              height: round(rect.height / scale),
            },
            properties,
          };
        });
      };

      if (!appearance.length) {
        issues.push({ code: "missing-appearance-styles", detail: "No owned appearance style blocks found" });
      }
      let targetCount = 0;
      for (let slideIndex = 0; slideIndex < slides.length; slideIndex += 1) {
        slides.forEach((slide, index) => slide.classList.toggle("active", index === slideIndex));
        await nextFrame();
        const before = snapshot(slides[slideIndex]);
        targetCount += before.length;
        appearance.forEach((style) => { style.disabled = true; });
        await nextFrame();
        const after = snapshot(slides[slideIndex]);
        appearance.forEach((style) => { style.disabled = false; });
        await nextFrame();

        for (let index = 0; index < before.length; index += 1) {
          const left = before[index];
          const right = after[index];
          if (!right) {
            issues.push({ slide: slideIndex + 1, code: "target-disappeared", target: left.label });
            continue;
          }
          const drift = Object.fromEntries(
            Object.keys(left.rect).map((key) => [key, round(Math.abs(left.rect[key] - right.rect[key]))]),
          );
          if (Object.values(drift).some((value) => value > tolerance)) {
            issues.push({
              slide: slideIndex + 1,
              code: "appearance-mutates-geometry",
              target: left.label,
              drift,
              appearanceOn: left.rect,
              appearanceOff: right.rect,
            });
          }
          for (const property of geometryProperties) {
            if (left.properties[property] !== right.properties[property]) {
              issues.push({
                slide: slideIndex + 1,
                code: "appearance-owns-layout-property",
                target: left.label,
                property,
                appearanceOn: left.properties[property],
                appearanceOff: right.properties[property],
              });
            }
          }
        }
      }
      appearance.forEach((style) => { style.disabled = false; });
      slides.forEach((slide, index) => slide.classList.toggle("active", index === 0));
      return { owners, issues, slides: slides.length, targets: targetCount };
    }, { tolerance: options.tolerance });

    report.slides = result.slides;
    report.targets = result.targets;
    report.appearanceOwners = result.owners;
    report.issues = result.issues;
    report.status = result.issues.length ? "fail" : "pass";
    await fs.mkdir(path.dirname(path.resolve(options.report)), { recursive: true });
    await fs.writeFile(path.resolve(options.report), `${JSON.stringify(report, null, 2)}\n`, "utf8");
    console.log(JSON.stringify(report, null, 2));
    process.exitCode = report.status === "pass" ? 0 : 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});
