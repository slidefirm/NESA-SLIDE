const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--html") out.html = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
    else if (argv[index] === "--screenshot") out.screenshot = argv[++index];
  }
  if (!out.html || !out.report) throw new Error("--html and --report are required");
  return out;
}

function browserExecutable() {
  return [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean).find((candidate) => fsSync.existsSync(candidate));
}

async function waitForDeck(page) {
  await page.waitForFunction(() => (
    document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
  ), null, { timeout: 120000 });
  await page.evaluate(async () => {
    const slide = document.querySelector('.slide[data-composition="contrast"]');
    if (!slide) throw new Error("contrast slide missing");
    window.setSlide(Number(slide.dataset.index));
    if (!document.documentElement.classList.contains("edit-mode")) window.EditMode.toggle(true);
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
}

async function backgroundPoint(page) {
  return page.evaluate(() => {
    const bg = document.querySelector('.slide.active .contrast-left > [data-edit-layer="background"]');
    if (!bg) throw new Error("left background layer missing");
    const rect = bg.getBoundingClientRect();
    const candidates = [
      [0.86, 0.88], [0.88, 0.55], [0.54, 0.88], [0.12, 0.88], [0.92, 0.24],
    ];
    for (const [rx, ry] of candidates) {
      const x = rect.left + rect.width * rx;
      const y = rect.top + rect.height * ry;
      const competing = document.elementsFromPoint(x, y).find((node) => {
        const layer = node.closest && node.closest("[data-edit-layer]");
        return layer && layer !== bg && bg.parentElement.contains(layer);
      });
      if (!competing) return { x, y };
    }
    return { x: rect.right - 12, y: rect.bottom - 12 };
  });
}

async function selectionState(page) {
  return page.evaluate(() => {
    const frame = document.getElementById("edit-selection-frame");
    return {
      label: document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent?.trim() || "",
      mode: frame?.dataset.selectionMode || "",
      memberFrames: Number(frame?.dataset.memberFrameCount || 0),
    };
  });
}

async function main() {
  const options = argsOf(process.argv);
  const htmlPath = path.resolve(options.html);
  const reportPath = path.resolve(options.report);
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  let result;

  try {
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "commit", timeout: 30000 });
    await waitForDeck(page);

    if (options.screenshot) {
      await fs.mkdir(path.dirname(path.resolve(options.screenshot)), { recursive: true });
      await page.locator(".slide.active").screenshot({ path: path.resolve(options.screenshot) });
    }
    const structure = await page.evaluate(() => {
      const slide = document.querySelector(".slide.active");
      const content = slide?.querySelector('.scene-content[data-edit-layout-only="true"]');
      const grid = content?.querySelector(":scope > .contrast-grid");
      const panels = [...(grid?.querySelectorAll(":scope > .contrast-panel") || [])];
      const backgrounds = panels.map((panel) => panel.querySelector(':scope > [data-edit-layer="background"]'));
      const computedBackground = (node) => {
        if (!node) return "";
        const style = getComputedStyle(node);
        return `${style.backgroundColor}|${style.backgroundImage}|${style.borderRightWidth}`;
      };
      return {
        forbiddenAggregateGroups: slide?.querySelectorAll('.el[data-edit-structure="group"],.el[data-edit-role="title-group"],.el[data-edit-role="content-group"],.el[data-edit-role="extra-group"]').length || 0,
        layoutOnlyEditableCount: slide ? [...slide.querySelectorAll('[data-edit-layout-only="true"]')].filter((node) => node.matches('.el,[data-edit-layer],[data-edit-composite]')).length : 0,
        panelCount: panels.length,
        moduleCount: panels.filter((panel) => panel.dataset.editStructure === "module").length,
        compositeCount: panels.filter((panel) => Boolean(panel.dataset.editComposite)).length,
        firstChildBackgroundCount: panels.filter((panel) => panel.firstElementChild?.dataset.editLayer === "background").length,
        backgroundCount: backgrounds.filter(Boolean).length,
        backgroundStyles: backgrounds.map(computedBackground),
        panelBackgrounds: panels.map(computedBackground),
        layerCounts: panels.map((panel) => panel.querySelectorAll(":scope > [data-edit-layer]").length),
        nestedUnderContent: panels.every((panel) => content?.contains(panel)),
        gridMaterialized: grid?.dataset.layoutMaterialized || "",
        panelPositions: panels.map((panel) => getComputedStyle(panel).position),
        slideRect: (() => {
          const rect = slide.getBoundingClientRect();
          return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, width: rect.width, height: rect.height };
        })(),
        panelRects: panels.map((panel) => {
          const rect = panel.getBoundingClientRect();
          return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, width: rect.width, height: rect.height };
        }),
      };
    });

    const point = await backgroundPoint(page);
    await page.mouse.click(point.x, point.y);
    await page.waitForTimeout(120);
    const drillPanel = await selectionState(page);
    await page.mouse.click(point.x, point.y);
    await page.waitForTimeout(120);
    const repeatedPanel = await selectionState(page);
    await page.locator('[data-action="edit-group-member"]').click();
    await page.waitForTimeout(120);
    await page.mouse.click(point.x, point.y);
    await page.waitForTimeout(120);
    const drillBackground = await selectionState(page);

    await page.reload({ waitUntil: "commit", timeout: 30000 });
    await waitForDeck(page);
    const ungroupPoint = await backgroundPoint(page);
    await page.mouse.click(ungroupPoint.x, ungroupPoint.y);
    await page.waitForTimeout(100);
    await page.evaluate(() => window.EditMode.ungroup());
    await page.waitForTimeout(120);
    const afterPanelUngroup = await page.evaluate(() => ({
      leftState: document.querySelector(".slide.active .contrast-left")?.dataset.editGroupState || "",
      label: document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent?.trim() || "",
    }));
    await page.mouse.click(ungroupPoint.x, ungroupPoint.y);
    await page.waitForTimeout(120);
    const backgroundAfterUngroup = await selectionState(page);

    const pass = structure.forbiddenAggregateGroups === 0
      && structure.layoutOnlyEditableCount === 0
      && structure.panelCount === 2
      && structure.moduleCount === 2
      && structure.compositeCount === 2
      && structure.firstChildBackgroundCount === 2
      && structure.backgroundCount === 2
      && structure.backgroundStyles.every((value) => value && !value.startsWith("rgba(0, 0, 0, 0)|none") && !value.startsWith("transparent|none"))
      && structure.panelBackgrounds.every((value) => value.startsWith("rgba(0, 0, 0, 0)|none"))
      && structure.layerCounts.every((count) => count >= 4)
      && structure.nestedUnderContent
      && structure.gridMaterialized === "true"
      && structure.panelPositions.every((value) => value === "absolute")
      && structure.panelRects.length === 2
      && structure.panelRects.every((rect) => rect.width > 300 && rect.height > 250)
      && structure.panelRects[0].right <= structure.panelRects[1].left + 2
      && Math.abs(structure.panelRects[0].top - structure.panelRects[1].top) <= 2
      && Math.abs(structure.panelRects[0].bottom - structure.panelRects[1].bottom) <= 2
      && structure.panelRects.every((rect) => rect.left >= structure.slideRect.left - 2 && rect.right <= structure.slideRect.right + 2 && rect.top >= structure.slideRect.top - 2 && rect.bottom <= structure.slideRect.bottom + 2)
      && /^已選取群組 · \d+ 個物件$/.test(drillPanel.label)
      && drillPanel.mode === "group"
      && repeatedPanel.mode === "group"
      && drillBackground.label === "已選取背景"
      && afterPanelUngroup.leftState === "ungrouped"
      && backgroundAfterUngroup.label === "已選取背景";

    result = {
      pass,
      structure,
      drill: { panel: drillPanel, repeatedPanel, background: drillBackground },
      ungroup: { afterPanelUngroup, backgroundAfterUngroup },
    };
  } finally {
    await Promise.race([browser.close(), new Promise((resolve) => setTimeout(resolve, 2000))]);
  }

  await fs.mkdir(path.dirname(reportPath), { recursive: true });
  await fs.writeFile(reportPath, JSON.stringify({ html: htmlPath, ...result }, null, 2) + "\n", "utf8");
  console.log(JSON.stringify(result));
  if (!result.pass) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
