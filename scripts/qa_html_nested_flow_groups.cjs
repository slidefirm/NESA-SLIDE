const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--url") out.url = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
    else if (argv[index] === "--screenshot") out.screenshot = argv[++index];
  }
  if (!out.url || !out.report) throw new Error("--url and --report are required");
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

async function waitForFlow(page) {
  await page.waitForFunction(() => (
    document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
  ), null, { timeout: 120000 });
  await page.evaluate(async () => {
    const slide = document.querySelector('.slide[data-layout-id="brave-lesson-flow"]');
    if (!slide) throw new Error("brave-lesson-flow slide missing");
    window.setSlide(Number(slide.dataset.index));
    if (!document.documentElement.classList.contains("edit-mode")) window.EditMode.toggle(true);
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
}

async function backgroundPoint(page) {
  return page.evaluate(() => {
    const bg = document.querySelector('.slide.active .flow-item:first-child > [data-edit-layer="background"]');
    if (!bg) throw new Error("first flow background missing");
    const rect = bg.getBoundingClientRect();
    const candidates = [[0.84, 0.84], [0.16, 0.84], [0.88, 0.52], [0.12, 0.52]];
    for (const [rx, ry] of candidates) {
      const x = rect.left + rect.width * rx;
      const y = rect.top + rect.height * ry;
      const competing = document.elementsFromPoint(x, y).find((node) => {
        const layer = node.closest && node.closest("[data-edit-layer]");
        return layer && layer !== bg && bg.parentElement.contains(layer);
      });
      if (!competing) return { x, y };
    }
    return { x: rect.right - 10, y: rect.bottom - 10 };
  });
}

async function selectionState(page) {
  return page.evaluate(() => {
    const frame = document.getElementById("edit-selection-frame");
    const rect = frame?.getBoundingClientRect();
    return {
      mode: frame?.dataset.selectionMode || "",
      label: document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent?.trim() || "",
      rect: rect ? { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height } : null,
    };
  });
}

async function main() {
  const options = argsOf(process.argv);
  const executablePath = browserExecutable();
  if (!executablePath) throw new Error("No Chrome or Edge executable found");
  const browser = await chromium.launch({ headless: true, executablePath });
  let result;
  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(options.url, { waitUntil: "domcontentloaded", timeout: 60000 });
    await waitForFlow(page);

    const structure = await page.evaluate(() => {
      const slide = document.querySelector(".slide.active");
      const content = slide?.querySelector('.scene-content[data-edit-layout-only="true"]');
      const footer = slide?.querySelector('.scene-footer-object[data-edit-role="footer-note"]');
      const line = content?.querySelector(':scope > .el[data-edit-layer="visual"].flow-line');
      const list = content?.querySelector(":scope > .flow-list");
      const nodes = [...(list?.querySelectorAll(":scope > .flow-item") || [])];
      const rectOf = (node) => {
        const rect = node.getBoundingClientRect();
        return { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height };
      };
      const backgroundStyle = (node) => {
        const style = getComputedStyle(node);
        return `${style.backgroundColor}|${style.backgroundImage}`;
      };
      return {
        forbiddenAggregateGroups: slide?.querySelectorAll('.el[data-edit-structure="group"],.el[data-edit-role="title-group"],.el[data-edit-role="content-group"],.el[data-edit-role="extra-group"]').length || 0,
        layoutOnlyEditableCount: slide ? [...slide.querySelectorAll('[data-edit-layout-only="true"]')].filter((node) => node.matches('.el,[data-edit-layer],[data-edit-composite]')).length : 0,
        nodeCount: nodes.length,
        moduleCount: nodes.filter((node) => node.dataset.editStructure === "module").length,
        compositeCount: nodes.filter((node) => Boolean(node.dataset.editComposite)).length,
        firstChildBackgroundCount: nodes.filter((node) => node.firstElementChild?.dataset.editLayer === "background").length,
        nodeLayerCounts: nodes.map((node) => node.querySelectorAll(":scope > [data-edit-layer]").length),
        nestedUnderContent: nodes.every((node) => content?.contains(node)),
        lineInsideContent: Boolean(line && content?.contains(line)),
        footerIsIndependentSibling: Boolean(footer && footer.parentElement === content?.parentElement && !content.contains(footer)),
        footerIsEditableRoot: Boolean(footer?.classList.contains("el")),
        listMaterialized: list?.dataset.layoutMaterialized || "",
        nodePositions: nodes.map((node) => getComputedStyle(node).position),
        nodeStyles: nodes.map((node) => node.getAttribute("style") || ""),
        nodeSourceStyles: nodes.map((node) => node.dataset.layoutSourceStyle || ""),
        listStyle: list?.getAttribute("style") || "",
        listDisplay: list ? getComputedStyle(list).display : "",
        nodeBackgrounds: nodes.map((node) => backgroundStyle(node.firstElementChild)),
        nodeContainerBackgrounds: nodes.map(backgroundStyle),
        nodeRects: nodes.map(rectOf),
        contentRect: content ? rectOf(content) : null,
        footerRect: footer ? rectOf(footer) : null,
        lineRect: line ? rectOf(line) : null,
      };
    });

    if (options.screenshot) {
      await fs.mkdir(path.dirname(path.resolve(options.screenshot)), { recursive: true });
      await page.locator(".slide.active").screenshot({ path: path.resolve(options.screenshot) });
    }

    const point = await backgroundPoint(page);
    await page.mouse.click(point.x, point.y);
    await page.waitForTimeout(140);
    const node = await selectionState(page);
    await page.mouse.click(point.x, point.y);
    await page.waitForTimeout(140);
    const repeatedNode = await selectionState(page);
    await page.locator('[data-action="edit-group-member"]').click();
    await page.waitForTimeout(120);
    await page.mouse.click(point.x, point.y);
    await page.waitForTimeout(140);
    const background = await selectionState(page);

    await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await waitForFlow(page);
    const ungroupPoint = await backgroundPoint(page);
    await page.mouse.click(ungroupPoint.x, ungroupPoint.y);
    await page.waitForTimeout(100);
    await page.evaluate(() => window.EditMode.ungroup());
    await page.waitForTimeout(140);
    const afterNodeUngroup = await page.evaluate(() => ({
      firstNodeState: document.querySelector(".slide.active .flow-item")?.dataset.editGroupState || "",
      mode: document.getElementById("edit-selection-frame")?.dataset.selectionMode || "",
    }));
    await page.mouse.click(ungroupPoint.x, ungroupPoint.y);
    await page.waitForTimeout(120);
    const afterLayerClick = await selectionState(page);

    const close = (a, b, tolerance = 4) => Math.abs(a - b) <= tolerance;
    const rectMatches = (a, b) => Boolean(a && b
      && close(a.left, b.left) && close(a.top, b.top)
      && close(a.width, b.width) && close(a.height, b.height));
    const nodeUnion = structure.nodeRects.length ? {
      left: Math.min(...structure.nodeRects.map((rect) => rect.left), structure.lineRect?.left ?? Infinity),
      top: Math.min(...structure.nodeRects.map((rect) => rect.top), structure.lineRect?.top ?? Infinity),
      right: Math.max(...structure.nodeRects.map((rect) => rect.right), structure.lineRect?.right ?? -Infinity),
      bottom: Math.max(...structure.nodeRects.map((rect) => rect.bottom), structure.lineRect?.bottom ?? -Infinity),
    } : null;
    if (nodeUnion) {
      nodeUnion.width = nodeUnion.right - nodeUnion.left;
      nodeUnion.height = nodeUnion.bottom - nodeUnion.top;
    }

    const nonOverlapping = structure.nodeRects.every((rect, index, all) => (
      index === 0 || all[index - 1].right <= rect.left + 2
    ));
    const alignedRow = structure.nodeRects.every((rect, index, all) => (
      index === 0 || (close(rect.top, all[0].top) && close(rect.bottom, all[0].bottom))
    ));
    const nodesInsideContent = Boolean(structure.contentRect) && structure.nodeRects.every((rect) => (
      rect.left >= structure.contentRect.left - 4
      && rect.right <= structure.contentRect.right + 4
      && rect.top >= structure.contentRect.top - 4
      && rect.bottom <= structure.contentRect.bottom + 4
    ));
    const pass = structure.forbiddenAggregateGroups === 0
      && structure.layoutOnlyEditableCount === 0
      && structure.nodeCount === 5
      && structure.moduleCount === 5
      && structure.compositeCount === 5
      && structure.firstChildBackgroundCount === 5
      && structure.nodeLayerCounts.every((count) => count === 4)
      && structure.nestedUnderContent
      && structure.lineInsideContent
      && structure.footerIsIndependentSibling
      && structure.footerIsEditableRoot
      && structure.listMaterialized === ""
      && structure.nodePositions.every((value) => value === "relative")
      && structure.nodeBackgrounds.every((value) => value && !value.startsWith("rgba(0, 0, 0, 0)|none") && !value.startsWith("transparent|none"))
      && structure.nodeContainerBackgrounds.every((value) => value.startsWith("rgba(0, 0, 0, 0)|none"))
      && nonOverlapping
      && alignedRow
      && nodesInsideContent
      && Boolean(structure.contentRect && structure.footerRect && structure.contentRect.bottom < structure.footerRect.top + 4)
      && node.mode === "group"
      && rectMatches(node.rect, structure.nodeRects[0])
      && repeatedNode.mode === "group"
      && rectMatches(repeatedNode.rect, structure.nodeRects[0])
      && background.mode === "single"
      && rectMatches(background.rect, structure.nodeRects[0])
      && afterNodeUngroup.firstNodeState === "ungrouped"
      && afterLayerClick.mode === "single";

    result = {
      pass,
      structure,
      drill: { node, repeatedNode, background, nodeUnion },
      ungroup: { afterNodeUngroup, afterLayerClick },
    };
  } finally {
    await Promise.race([browser.close(), new Promise((resolve) => setTimeout(resolve, 2000))]);
  }

  const reportPath = path.resolve(options.report);
  await fs.mkdir(path.dirname(reportPath), { recursive: true });
  await fs.writeFile(reportPath, `${JSON.stringify({ url: options.url, ...result }, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(result));
  if (!result.pass) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
