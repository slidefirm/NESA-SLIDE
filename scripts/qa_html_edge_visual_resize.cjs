const fs = require("node:fs/promises");
const path = require("node:path");
const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");
const { selectAllBySelector } = require("./html_qa_selection.cjs");
const { chromium } = loadPlaywright();

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === "--url") out.url = argv[++i];
    else if (argv[i] === "--report") out.report = argv[++i];
    else if (argv[i] === "--screenshot") out.screenshot = argv[++i];
    else if (argv[i] === "--slide-index") out.slideIndex = Number(argv[++i]);
    else if (argv[i] === "--module-selector") out.moduleSelector = argv[++i];
  }
  if (!out.url || !out.report) throw new Error("--url and --report are required");
  return out;
}

function inside(child, parent, tolerance = 1.5) {
  return child.left >= parent.left - tolerance
    && child.right <= parent.right + tolerance
    && child.top >= parent.top - tolerance
    && child.bottom <= parent.bottom + tolerance;
}

async function main() {
  const options = parseArgs(process.argv);
  const moduleSelector = options.moduleSelector || ".module-card";
  const slideIndex = Number.isInteger(options.slideIndex) ? options.slideIndex : 1;
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
  const report = { checks: {} };

  try {
    const page = await browser.newPage({ viewport: { width: 1800, height: 1000 } });
    await page.addInitScript(() => localStorage.clear());
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(options.url, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForFunction(() => document.documentElement.dataset.layoutReady === "true" && window.EditMode);
    await page.evaluate(async (index) => {
      window.setSlide(index);
      if (!document.documentElement.classList.contains("edit-mode")) window.EditMode.toggle(true);
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    }, slideIndex);

    await selectAllBySelector(page, `.slide.active ${moduleSelector}`);
    await page.evaluate(() => window.EditMode.group());
    await page.waitForTimeout(100);

    // Simulate the stale transform left by the bug reported in the editor.
    await page.evaluate((selector) => {
      document.querySelectorAll(`.slide.active ${selector} > [data-edit-layer="visual"][data-edit-anchor="bottom"]`)
        .forEach((node) => node.style.setProperty("transform", "translateY(180px)", "important"));
    }, moduleSelector);

    const snapshot = () => page.evaluate((selector) => {
      const rect = (node) => {
        const value = node.getBoundingClientRect();
        return {
          left: value.left,
          top: value.top,
          right: value.right,
          bottom: value.bottom,
          width: value.width,
          height: value.height,
          transform: node.style.transform || ""
        };
      };
      return [...document.querySelectorAll(`.slide.active ${selector}`)].map((module) => ({
        module: rect(module),
        visuals: [...module.querySelectorAll(':scope > [data-edit-layer="visual"][data-edit-anchor="bottom"]')].map(rect)
      }));
    }, moduleSelector);

    const before = await snapshot();
    const handle = await page.locator('.edit-resize-handle[data-handle="s"]').boundingBox();
    if (!handle) throw new Error("south resize handle missing");
    const x = handle.x + handle.width / 2;
    const y = handle.y + handle.height / 2;
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x, y + 110, { steps: 10 });
    await page.mouse.up();
    await page.waitForTimeout(220);
    const after = await snapshot();

    const visualCount = after.reduce((sum, item) => sum + item.visuals.length, 0);
    const anchorMetadataPresent = visualCount > 0;
    const insideModules = after.every((item) => item.visuals.every((visual) => inside(visual, item.module)));
    const staleTransformsCleared = after.every((item) => item.visuals.every((visual) => visual.transform === ""));
    report.before = before;
    report.after = after;
    report.checks = {
      edgeAnchorMetadataPresent: anchorMetadataPresent,
      visualLayersFound: visualCount > 0,
      visualLayersStayInsideModule: insideModules,
      staleVisualTransformsCleared: staleTransformsCleared
    };
    report.pass = Object.values(report.checks).every(Boolean);
    if (options.screenshot) {
      await fs.mkdir(path.dirname(options.screenshot), { recursive: true });
      await page.screenshot({ path: options.screenshot, fullPage: false });
      report.screenshot = options.screenshot;
    }
    await fs.mkdir(path.dirname(options.report), { recursive: true });
    await fs.writeFile(options.report, JSON.stringify(report, null, 2) + "\n", "utf8");
    if (!report.pass) throw new Error(`edge visual resize QA failed: ${JSON.stringify(report.checks)}`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
