const fs = require("node:fs/promises");
const path = require("node:path");
const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");
const { selectAllBySelector } = require("./html_qa_selection.cjs");

function parseArgs(argv) {
  const options = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--url") options.url = argv[++index];
    else if (argv[index] === "--report") options.report = argv[++index];
    else if (argv[index] === "--screenshots") options.screenshots = argv[++index];
  }
  if (!options.url) throw new Error("--url is required");
  if (!options.report) throw new Error("--report is required");
  return options;
}

const near = (first, second, tolerance = 2) => Math.abs(first - second) <= tolerance;

async function ready(page, url, slideIndex) {
  await page.addInitScript(() => localStorage.clear());
  await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
  await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForFunction(
    () => document.documentElement.dataset.layoutReady === "true" && window.EditMode,
    null,
    { timeout: 120000 }
  );
  await page.evaluate(async (index) => {
    window.setSlide(index);
    if (!document.documentElement.classList.contains("edit-mode")) window.EditMode.toggle(true);
    await document.fonts.ready;
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }, slideIndex);
}

async function clickCenter(page, selector) {
  const box = await page.locator(`.slide.active ${selector}`).boundingBox();
  if (!box) throw new Error(`Missing selectable element: ${selector}`);
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await page.waitForTimeout(90);
}

async function dragSelection(page, deltaX, deltaY) {
  const box = await page.locator("#edit-selection-frame").boundingBox();
  if (!box) throw new Error("Selection frame is not visible");
  const startX = box.x + box.width / 2;
  const startY = box.y + box.height / 2;
  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(startX + deltaX, startY + deltaY, { steps: 10 });
  await page.mouse.up();
  await page.waitForTimeout(150);
}

async function dragHandle(page, handle, deltaX, deltaY) {
  const box = await page.locator(`.edit-resize-handle[data-handle="${handle}"]`).boundingBox();
  if (!box) throw new Error(`Missing ${handle} resize handle`);
  const startX = box.x + box.width / 2;
  const startY = box.y + box.height / 2;
  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(startX + deltaX, startY + deltaY, { steps: 12 });
  await page.mouse.up();
  await page.waitForTimeout(180);
}

async function captureTitle(page) {
  return page.evaluate(() => {
    const title = document.querySelector(".slide.active .cover-center-title");
    const frame = document.getElementById("edit-selection-frame");
    if (!title || !frame) throw new Error("Cover title fixture is missing");
    const rect = (node) => {
      const value = node.getBoundingClientRect();
      return {
        left: value.left,
        top: value.top,
        right: value.right,
        bottom: value.bottom,
        width: value.width,
        height: value.height,
      };
    };
    const range = document.createRange();
    range.selectNodeContents(title);
    const lineTops = [];
    Array.from(range.getClientRects()).forEach((value) => {
      if (value.width <= 0.5 || value.height <= 0.5) return;
      if (!lineTops.some((top) => Math.abs(top - value.top) <= 1)) lineTops.push(value.top);
    });
    const style = getComputedStyle(title);
    return {
      rect: rect(title),
      frame: rect(frame),
      lineCount: lineTops.length,
      inlineStyle: title.getAttribute("style") || "",
      inlineWidth: title.style.width,
      inlineHeight: title.style.height,
      computedWidth: style.width,
      computedHeight: style.height,
      transform: title.style.transform,
      translate: title.style.translate,
      frameWidthMode: title.dataset.editFrameWidth || "",
      frameHeightMode: title.dataset.editFrameHeight || "",
    };
  });
}

async function titleMoveUndoCase(browser, options) {
  const page = await browser.newPage({ viewport: { width: 1800, height: 1000 } });
  try {
    await ready(page, options.url, 0);
    await clickCenter(page, ".cover-center-title");
    const editMember = page.locator('[data-action="edit-group-member"]');
    if (await editMember.isEnabled()) {
      await editMember.click();
      await page.waitForTimeout(90);
      await clickCenter(page, ".cover-center-title");
    }
    const before = await captureTitle(page);
    await dragSelection(page, 72, 28);
    const moved = await captureTitle(page);
    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(150);
    const undone = await captureTitle(page);
    await page.evaluate(() => window.EditMode.redo());
    await page.waitForTimeout(150);
    const redone = await captureTitle(page);
    const checks = {
      dragMovesTitle: !near(moved.rect.left, before.rect.left, 4) || !near(moved.rect.top, before.rect.top, 4),
      dragKeepsLineCount: moved.lineCount === before.lineCount,
      undoRestoresPosition: near(undone.rect.left, before.rect.left) && near(undone.rect.top, before.rect.top),
      undoKeepsIntrinsicWidth: undone.inlineWidth === before.inlineWidth && undone.inlineHeight === before.inlineHeight,
      undoKeepsLineCount: undone.lineCount === before.lineCount,
      redoRestoresPosition: near(redone.rect.left, moved.rect.left) && near(redone.rect.top, moved.rect.top),
      redoKeepsIntrinsicWidth: redone.inlineWidth === moved.inlineWidth && redone.inlineHeight === moved.inlineHeight,
      redoKeepsLineCount: redone.lineCount === before.lineCount,
    };
    if (options.screenshots) {
      await fs.mkdir(options.screenshots, { recursive: true });
      await page.screenshot({ path: path.join(options.screenshots, "title-move-redo.png"), fullPage: true });
    }
    return { pass: Object.values(checks).every(Boolean), checks, before, moved, undone, redone };
  } finally {
    await page.close();
  }
}

async function captureMetricsGroup(page) {
  return page.evaluate(() => {
    const root = document.querySelector('.slide.active [data-edit-layout-only="true"][data-visual-balance="content-bounds"]');
    const frame = document.getElementById("edit-selection-frame");
    const cards = Array.from(document.querySelectorAll(".slide.active .metric-stat-card"));
    if (!root || !frame || cards.length !== 3) throw new Error("Metrics module fixture is missing");
    const rect = (node) => {
      const value = node.getBoundingClientRect();
      return {
        left: value.left,
        top: value.top,
        right: value.right,
        bottom: value.bottom,
        width: value.width,
        height: value.height,
      };
    };
    const paintRect = (node) => {
      const range = document.createRange();
      range.selectNodeContents(node);
      const value = range.getBoundingClientRect();
      return value.width > 0.5 && value.height > 0.5 ? {
        left: value.left,
        top: value.top,
        right: value.right,
        bottom: value.bottom,
        width: value.width,
        height: value.height,
      } : rect(node);
    };
    return {
      root: { rect: rect(root), inlineStyle: root.getAttribute("style") || "" },
      frame: rect(frame),
      cards: cards.map((card) => {
        const cardRect = rect(card);
        const textLayers = Array.from(card.querySelectorAll('[data-edit-layer="text"],[data-edit-layer="metric"]'));
        return {
          rect: cardRect,
          inlineStyle: card.getAttribute("style") || "",
          background: rect(card.querySelector('[data-edit-layer="background"]')),
          text: textLayers.map((layer) => {
            const value = paintRect(layer);
            return {
              text: (layer.textContent || "").trim(),
              rect: value,
              relativeTop: value.top - cardRect.top,
              relativeBottom: value.bottom - cardRect.top,
              fontSize: parseFloat(getComputedStyle(layer).fontSize),
            };
          }),
        };
      }),
    };
  });
}

function everyCardTextFits(snapshot, tolerance = 1) {
  return snapshot.cards.every((card) => card.text.every((item) => (
    item.rect.top >= card.rect.top - tolerance && item.rect.bottom <= card.rect.bottom + tolerance
  )));
}

function cardsKeepWidth(first, second, tolerance = 2) {
  return second.cards.every((card, index) => near(card.rect.width, first.cards[index].rect.width, tolerance));
}

function cardsKeepRelativeText(first, second, tolerance = 3) {
  return second.cards.every((card, cardIndex) => card.text.every((item, textIndex) => (
    near(item.relativeTop, first.cards[cardIndex].text[textIndex].relativeTop, tolerance)
    && near(item.relativeBottom, first.cards[cardIndex].text[textIndex].relativeBottom, tolerance)
  )));
}

async function metricsGroupCase(browser, options) {
  const page = await browser.newPage({ viewport: { width: 1800, height: 1000 } });
  try {
    await ready(page, options.url, 4);
    await selectAllBySelector(page, ".slide.active .metric-stat-card");
    await page.evaluate(() => window.EditMode.group());
    await page.waitForTimeout(120);
    const before = await captureMetricsGroup(page);
    await dragSelection(page, 0, 90);
    const moved = await captureMetricsGroup(page);
    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(150);
    const moveUndone = await captureMetricsGroup(page);
    await page.evaluate(() => window.EditMode.redo());
    await page.waitForTimeout(150);
    const moveRedone = await captureMetricsGroup(page);
    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(150);

    const northDelta = Math.min(210, Math.max(80, before.frame.height * 0.42));
    await dragHandle(page, "n", 0, northDelta);
    const compressed = await captureMetricsGroup(page);
    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(150);
    const resizeUndone = await captureMetricsGroup(page);
    await page.evaluate(() => window.EditMode.redo());
    await page.waitForTimeout(150);
    const resizeRedone = await captureMetricsGroup(page);

    const checks = {
      groupMoveChangesOnlyPosition: !near(moved.frame.top, before.frame.top, 4)
        && near(moved.frame.width, before.frame.width)
        && near(moved.frame.height, before.frame.height),
      groupMoveKeepsCardWidths: cardsKeepWidth(before, moved),
      groupMoveKeepsRelativeText: cardsKeepRelativeText(before, moved),
      groupMoveUndoRestores: near(moveUndone.frame.left, before.frame.left)
        && near(moveUndone.frame.top, before.frame.top)
        && near(moveUndone.frame.width, before.frame.width)
        && near(moveUndone.frame.height, before.frame.height)
        && cardsKeepWidth(before, moveUndone),
      groupMoveRedoReplays: near(moveRedone.frame.left, moved.frame.left)
        && near(moveRedone.frame.top, moved.frame.top)
        && near(moveRedone.frame.width, moved.frame.width)
        && near(moveRedone.frame.height, moved.frame.height)
        && cardsKeepWidth(moved, moveRedone),
      northResizeChangesHeightOnly: compressed.frame.height < before.frame.height - 40
        && near(compressed.frame.width, before.frame.width, 3),
      northResizeKeepsTextInsideCards: everyCardTextFits(compressed),
      northResizeUndoRestores: near(resizeUndone.frame.left, before.frame.left)
        && near(resizeUndone.frame.top, before.frame.top)
        && near(resizeUndone.frame.width, before.frame.width)
        && near(resizeUndone.frame.height, before.frame.height),
      northResizeRedoReplays: near(resizeRedone.frame.left, compressed.frame.left)
        && near(resizeRedone.frame.top, compressed.frame.top)
        && near(resizeRedone.frame.width, compressed.frame.width)
        && near(resizeRedone.frame.height, compressed.frame.height)
        && everyCardTextFits(resizeRedone),
    };
    if (options.screenshots) {
      await fs.mkdir(options.screenshots, { recursive: true });
      await page.screenshot({ path: path.join(options.screenshots, "metrics-north-resize-redo.png"), fullPage: true });
    }
    return {
      pass: Object.values(checks).every(Boolean),
      checks,
      before,
      moved,
      moveUndone,
      moveRedone,
      compressed,
      resizeUndone,
      resizeRedone,
    };
  } finally {
    await page.close();
  }
}

async function main() {
  const options = parseArgs(process.argv);
  const { chromium } = loadPlaywright();
  const executablePath = browserExecutable();
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
  const report = { url: options.url, pass: false };
  try {
    report.titleMoveUndo = await titleMoveUndoCase(browser, options);
    report.metricsGroup = await metricsGroupCase(browser, options);
    report.pass = report.titleMoveUndo.pass && report.metricsGroup.pass;
  } finally {
    await browser.close();
  }
  await fs.mkdir(path.dirname(options.report), { recursive: true });
  await fs.writeFile(options.report, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify({
    pass: report.pass,
    titleMoveUndo: report.titleMoveUndo.checks,
    metricsGroup: report.metricsGroup.checks,
  }));
  if (!report.pass) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error.stack || error);
  process.exit(1);
});
