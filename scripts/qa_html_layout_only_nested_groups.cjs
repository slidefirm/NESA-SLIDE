const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");
const { selectAllBySelector } = require("./html_qa_selection.cjs");

function parseArgs(argv) {
  const options = {};
  for (let index = 2; index < argv.length; index += 1) {
    const key = argv[index];
    if (key === "--url") options.url = argv[++index];
    else if (key === "--report") options.report = argv[++index];
    else if (key === "--shot-dir") options.shotDir = argv[++index];
  }
  if (!options.url || !options.report) throw new Error("--url and --report are required");
  return options;
}

function browserExecutable() {
  return [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean).find((candidate) => fsSync.existsSync(candidate));
}

async function waitForEditor(page) {
  await page.waitForFunction(() => (
    document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
  ), null, { timeout: 120000 });
}

async function activateLayout(page, layoutId) {
  await page.evaluate(async (wantedLayoutId) => {
    const slide = document.querySelector(`.slide[data-layout-id="${wantedLayoutId}"]`);
    if (!slide) throw new Error(`${wantedLayoutId} slide missing`);
    window.setSlide(Number(slide.dataset.index));
    if (!document.documentElement.classList.contains("edit-mode")) window.EditMode.toggle(true);
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }, layoutId);
}

async function selectionState(page) {
  return page.evaluate(() => {
    const frame = document.getElementById("edit-selection-frame");
    const visible = frame && getComputedStyle(frame).display !== "none";
    const rect = visible ? frame.getBoundingClientRect() : null;
    return {
      visible: Boolean(visible),
      mode: frame?.dataset.selectionMode || "",
      label: document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent?.trim() || "",
      rect: rect ? {
        left: rect.left,
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom,
        width: rect.width,
        height: rect.height,
      } : null,
    };
  });
}

async function pageStructure(page, rootSelector, slotSelector, moduleSelector) {
  return page.evaluate(({ rootSelector, slotSelector, moduleSelector }) => {
    const root = document.querySelector(rootSelector);
    const layoutContainers = root ? [
      ...(root.matches('[data-edit-layout-only="true"]') ? [root] : []),
      ...root.querySelectorAll('[data-edit-layout-only="true"]'),
    ] : [];
    const slots = root ? [...root.querySelectorAll(slotSelector)] : [];
    const modules = root ? [...root.querySelectorAll(moduleSelector)] : [];
    const rectOf = (node) => {
      const rect = node.getBoundingClientRect();
      return {
        left: rect.left,
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom,
        width: rect.width,
        height: rect.height,
      };
    };
    const unionOf = (nodes) => {
      const rects = nodes.map((node) => node.getBoundingClientRect()).filter((rect) => rect.width > 0.5 && rect.height > 0.5);
      const left = Math.min(...rects.map((rect) => rect.left));
      const top = Math.min(...rects.map((rect) => rect.top));
      const right = Math.max(...rects.map((rect) => rect.right));
      const bottom = Math.max(...rects.map((rect) => rect.bottom));
      return { left, top, right, bottom, width: right - left, height: bottom - top };
    };    const visibleSelectionRect = (node) => {
      const root = node.classList?.contains("el") ? node : node.closest?.(".el");
      if (node === root && root?.dataset?.editComposite && root.dataset.editGroupState !== "ungrouped") {
        const nestedRoots = [...root.querySelectorAll(".el")].filter((item) => (
          item.parentElement?.closest(".el") === root && getComputedStyle(item).display !== "none"
        ));
        const directLayers = [...root.querySelectorAll("[data-edit-layer]")].filter((item) => (
          item.closest(".el") === root && getComputedStyle(item).display !== "none"
        ));
        const members = nestedRoots.length ? nestedRoots.concat(directLayers) : directLayers;
        if (members.length) {
          const rects = members.map(visibleSelectionRect);
          const left = Math.min(...rects.map((rect) => rect.left));
          const top = Math.min(...rects.map((rect) => rect.top));
          const right = Math.max(...rects.map((rect) => rect.right));
          const bottom = Math.max(...rects.map((rect) => rect.bottom));
          return { left, top, right, bottom, width: right - left, height: bottom - top };
        }
      }
      const elementRect = node.getBoundingClientRect();
      const layer = node.dataset?.editLayer || "";
      const tightText = !(node.dataset?.editFrameWidth === "manual" || node.dataset?.editFrameHeight === "manual")
        && (node.dataset?.editFit === "text" || layer === "text" || layer === "metric");
      if (!tightText || !(node.textContent || "").trim()) return rectOf(node);
      const range = document.createRange();
      range.selectNodeContents(node);
      const textRect = range.getBoundingClientRect();
      return textRect.width > 0.5 && textRect.height > 0.5
        ? { left: textRect.left, top: textRect.top, right: textRect.right, bottom: textRect.bottom, width: textRect.width, height: textRect.height }
        : { left: elementRect.left, top: elementRect.top, right: elementRect.right, bottom: elementRect.bottom, width: elementRect.width, height: elementRect.height };
    };
    return {
      rootRect: rectOf(root),
      rootVisualRect: visibleSelectionRect(root),
      moduleUnion: unionOf(modules),
      moduleVisualRects: modules.map(visibleSelectionRect),
      layoutOnlyCount: layoutContainers.length,
      layoutOnlyEditableCount: layoutContainers.filter((node) => (
        node.matches(".el,[data-edit-layer],[data-edit-composite]")
      )).length,
      slotRects: slots.map(rectOf),
      moduleRects: modules.map(rectOf),
      moduleCount: modules.length,
      modulesNestedDirectlyUnderRoot: modules.every((module) => module.parentElement === root),
      moduleLayerCounts: modules.map((module) => module.querySelectorAll(":scope > [data-edit-layer]").length),
      moduleBackgroundFirst: modules.every((module) => module.firstElementChild?.dataset.editLayer === "background"),
      textVerticalCenter: [...root.querySelectorAll('[data-edit-layer="text"]')].every((node) => (
        node.dataset.editVerticalAlign === "center"
      )),
      fitMaterialized: root.dataset.editFitMaterialized || "",
      fitVersion: root.dataset.editFitVersion || "",
      fitGroupsCount: document.documentElement.dataset.editFitGroups || "",
      rootState: root.dataset.editGroupState || "",
      moduleStates: modules.map((module) => module.dataset.editGroupState || ""),
    };
  }, { rootSelector, slotSelector, moduleSelector });
}

async function blankLayoutPoint(page, slotSelector, moduleSelector) {
  return page.evaluate(({ slotSelector, moduleSelector }) => {
    const slot = document.querySelector(slotSelector);
    const modules = [...document.querySelectorAll(moduleSelector)];
    if (!slot || !modules.length) throw new Error("layout frame or semantic module missing");
    const slotRect = slot.getBoundingClientRect();
    const moduleRects = modules.map((module) => module.getBoundingClientRect());
    for (let row = 1; row < 12; row += 1) {
      for (let column = 1; column < 24; column += 1) {
        const x = slotRect.left + slotRect.width * column / 24;
        const y = slotRect.top + slotRect.height * row / 12;
        if (moduleRects.every((rect) => x < rect.left || x > rect.right || y < rect.top || y > rect.bottom)) {
          return { x, y };
        }
      }
    }
    return null;
  }, { slotSelector, moduleSelector });
}

async function modulePoint(page, moduleSelector) {
  return page.evaluate((selector) => {
    const module = document.querySelector(selector);
    if (!module) throw new Error("semantic module missing");
    const rect = module.getBoundingClientRect();
    return { x: rect.right - 12, y: rect.bottom - 12 };
  }, moduleSelector);
}

function close(a, b, tolerance = 4) {
  return Math.abs(a - b) <= tolerance;
}

function rectMatches(a, b, tolerance = 4) {
  return Boolean(a && b
    && close(a.left, b.left, tolerance)
    && close(a.top, b.top, tolerance)
    && close(a.width, b.width, tolerance)
    && close(a.height, b.height, tolerance));
}

async function main() {
  const options = parseArgs(process.argv);
  const executablePath = browserExecutable();
  if (!executablePath) throw new Error("No Chrome or Edge executable found");
  const browser = await chromium.launch({ headless: true, executablePath });
  const result = { checks: {} };
  try {
    const page = await browser.newPage({ viewport: { width: 1800, height: 1000 } });
    await page.addInitScript(() => localStorage.clear());
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(options.url, { waitUntil: "domcontentloaded", timeout: 60000 });
    await waitForEditor(page);

    await activateLayout(page, "brave-learner-columns");
    const columnsBefore = await pageStructure(
      page,
      ".slide.active .column-grid",
      ".column-slot",
      ".column-item",
    );
    const blankPoint = await blankLayoutPoint(page, ".slide.active .column-grid", ".slide.active .column-item:first-child");
    if (blankPoint) {
      await page.mouse.click(blankPoint.x, blankPoint.y);
      await page.waitForTimeout(120);
    }
    const blankSelection = await selectionState(page);

    const firstColumnPoint = await modulePoint(page, ".slide.active .column-item:first-child");
    const firstColumnHitStack = await page.evaluate(({ x, y }) => (
      document.elementsFromPoint(x, y).slice(0, 12).map((node) => ({
        tag: node.tagName,
        cls: node.className || "",
        layer: node.dataset?.editLayer || "",
        layoutOnly: node.dataset?.editLayoutOnly || "",
        root: node.closest?.(".el")?.className || "",
      }))
    ), firstColumnPoint);
    await page.mouse.click(firstColumnPoint.x, firstColumnPoint.y);
    await page.waitForTimeout(120);
    const outerSelection = await selectionState(page);
    const columnsAtOuterSelection = await pageStructure(
      page,
      ".slide.active .column-grid",
      ".column-slot",
      ".column-item",
    );
    const secondColumnPoint = await modulePoint(page, ".slide.active .column-item:first-child");
    await page.mouse.click(secondColumnPoint.x, secondColumnPoint.y);
    await page.waitForTimeout(120);
    const moduleSelection = await selectionState(page);
    const columnsAtModuleSelection = await pageStructure(
      page,
      ".slide.active .column-grid",
      ".column-slot",
      ".column-item",
    );
    const multiSelectProbe = await selectAllBySelector(page, ".slide.active .column-item");
    const multiSelection = await selectionState(page);
    const multiMemberFrames = multiSelectProbe.memberFrameCount;

    await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await waitForEditor(page);
    await activateLayout(page, "brave-learner-columns");
    const ungroupPoint = await modulePoint(page, ".slide.active .column-item:first-child");
    await page.mouse.click(ungroupPoint.x, ungroupPoint.y);
    await page.waitForTimeout(100);
    await page.evaluate(() => window.EditMode.ungroup());
    await page.waitForTimeout(120);
    const columnsAfterModuleUngroup = await pageStructure(
      page,
      ".slide.active .column-grid",
      ".column-slot",
      ".column-item",
    );
    const selectionAfterModuleUngroup = await selectionState(page);

    const columnsCheck = {
      layoutContainersNotEditable: columnsBefore.layoutOnlyCount >= 1 && columnsBefore.layoutOnlyEditableCount === 0,
      fourSemanticSmallGroups: columnsBefore.moduleCount === 4
        && columnsBefore.modulesNestedDirectlyUnderRoot
        && columnsBefore.moduleLayerCounts.every((count) => count === 4)
        && columnsBefore.moduleBackgroundFirst,
      centeringFrameContainsSemanticModules: columnsBefore.moduleRects.every((rect) => (
        rect.left >= columnsBefore.rootRect.left - 2 && rect.right <= columnsBefore.rootRect.right + 2
        && rect.top >= columnsBefore.rootRect.top - 2 && rect.bottom <= columnsBefore.rootRect.bottom + 2
      )),
      blankLayoutSpaceDoesNotSelect: !blankSelection.visible,
      firstClickSelectsSemanticModule: outerSelection.mode === "group"
        && rectMatches(outerSelection.rect, columnsAtOuterSelection.moduleVisualRects[0]),
      repeatedClickKeepsSemanticModule: moduleSelection.mode === "group"
        && rectMatches(moduleSelection.rect, columnsAtModuleSelection.moduleVisualRects[0]),
      explicitMultiSelectionSelectsAllModules: multiSelection.mode === "multi"
        && multiMemberFrames === 4,
      oneUngroupAffectsOnlySelectedModule: columnsAfterModuleUngroup.moduleStates[0] === "ungrouped"
        && columnsAfterModuleUngroup.moduleStates.slice(1).every((state) => state !== "ungrouped"),
      textDefaultsToVerticalCenter: columnsBefore.textVerticalCenter,
    };
    result.columns = {
      before: columnsBefore,
      blankPoint,
      blankSelection,
      firstColumnHitStack,
      outerSelection,
      columnsAtOuterSelection,
      moduleSelection,
      columnsAtModuleSelection,
      multiSelection,
      multiMemberFrames,
      afterModuleUngroup: columnsAfterModuleUngroup,
      selectionAfterModuleUngroup,
      checks: columnsCheck,
      pass: Object.values(columnsCheck).every(Boolean),
    };

    await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await waitForEditor(page);
    await activateLayout(page, "brave-learning-metrics");
    const metricsBefore = await pageStructure(
      page,
      ".slide.active .metric-grid",
      ".metric-slot",
      ".metric-item",
    );
    const metricsBalance = await page.evaluate(() => {
      const area = document.querySelector(".slide.active [data-content-area]");
      const modules = [...document.querySelectorAll(".slide.active .metric-item")];
      const textNodes = [...document.querySelectorAll('.slide.active .metric-item [data-edit-layer="text"]')];
      const areaRect = area.getBoundingClientRect();
      const glyphRects = textNodes.map((node) => {
        const range = document.createRange();
        range.selectNodeContents(node);
        const rangeRect = range.getBoundingClientRect();
        return rangeRect.width > 0.5 && rangeRect.height > 0.5 ? rangeRect : node.getBoundingClientRect();
      });
      const left = Math.min(...glyphRects.map((rect) => rect.left));
      const right = Math.max(...glyphRects.map((rect) => rect.right));
      const moduleRects = modules.map((node) => node.getBoundingClientRect());
      const nonOverlappingRows = moduleRects.every((rect, index) => (
        index === 0 || moduleRects[index - 1].bottom <= rect.top + 2
      ));
      return {
        areaWidth: areaRect.width,
        textUnionWidth: right - left,
        horizontalUseRatio: (right - left) / areaRect.width,
        nonOverlappingRows,
        textAlignValues: textNodes.map((node) => getComputedStyle(node).textAlign),
      };
    });
    const metricsCheck = {
      layoutContainersNotEditable: metricsBefore.layoutOnlyCount >= 1 && metricsBefore.layoutOnlyEditableCount === 0,
      fourSemanticSmallGroups: metricsBefore.moduleCount === 4
        && metricsBefore.modulesNestedDirectlyUnderRoot
        && metricsBefore.moduleLayerCounts.every((count) => count === 4)
        && metricsBefore.moduleBackgroundFirst,
      centeringFrameContainsSemanticModules: metricsBefore.moduleRects.every((rect) => (
        rect.left >= metricsBefore.rootRect.left - 2 && rect.right <= metricsBefore.rootRect.right + 2
        && rect.top >= metricsBefore.rootRect.top - 2 && rect.bottom <= metricsBefore.rootRect.bottom + 2
      )),
      contentUsesEnoughWidth: metricsBalance.horizontalUseRatio >= 0.68,
      rowsDoNotOverlap: metricsBalance.nonOverlappingRows,
      textDefaultsToVerticalCenter: metricsBefore.textVerticalCenter,
    };
    result.metrics = {
      structure: metricsBefore,
      balance: metricsBalance,
      checks: metricsCheck,
      pass: Object.values(metricsCheck).every(Boolean),
    };

    if (options.shotDir) {
      const shotDir = path.resolve(options.shotDir);
      await fs.mkdir(shotDir, { recursive: true });
      await page.evaluate(() => window.EditMode.toggle(false));
      await page.waitForTimeout(120);
      await page.locator(".slide.active").screenshot({ path: path.join(shotDir, "brave-learning-metrics.png") });
      await activateLayout(page, "brave-learner-columns");
      await page.locator(".slide.active").screenshot({ path: path.join(shotDir, "brave-learner-columns-edit.png") });
    }

    result.pass = result.columns.pass && result.metrics.pass;
    result.checks = { columns: result.columns.pass, metrics: result.metrics.pass };
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
