const fs = require("node:fs/promises");
const path = require("node:path");
const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");
const { selectAllBySelector } = require("./html_qa_selection.cjs");
const { chromium } = loadPlaywright();

function args(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === "--url") out.url = argv[++i];
    else if (argv[i] === "--report") out.report = argv[++i];
    else if (argv[i] === "--screenshot") out.screenshot = argv[++i];
    else if (argv[i] === "--slide-index") out.slideIndex = Number(argv[++i]);
    else if (argv[i] === "--expected-modules") out.expectedModules = Number(argv[++i]);
    else if (argv[i] === "--grid-selector") out.gridSelector = argv[++i];
    else if (argv[i] === "--module-selector") out.moduleSelector = argv[++i];
  }
  if (!out.url || !out.report) throw new Error("--url and --report are required");
  return out;
}
function near(a, b, tolerance = 3) { return Math.abs(a - b) <= tolerance; }
async function snapshot(page, moduleSelector) {
  return page.evaluate((selector) => {
    const frame = document.getElementById("edit-selection-frame");
    const rect = (node) => {
      const r = node.getBoundingClientRect();
      return { left:r.left, top:r.top, width:r.width, height:r.height, right:r.right, bottom:r.bottom };
    };
    const cards = [...document.querySelectorAll(`.slide.active ${selector}`)];
    return {
      label: document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent?.trim() || "",
      mode: frame?.dataset.selectionMode || "",
      frame: rect(frame),
      cards: cards.map((card) => ({
        rect: rect(card),
        inlineHeight: card.style.height || "",
        transform: card.style.transform || "",
        parentClass: card.parentElement?.className || "",
        parentLayoutOnly: card.parentElement?.dataset?.editLayoutOnly || "",
        groupPath: card.dataset?.editGroup || "",
        text: [...card.querySelectorAll('[data-edit-layer="text"]')].map((node) => ({ rect:rect(node), transform:node.style.transform || "" }))
      }))
    };
  }, moduleSelector);
}
async function dragHandle(page, handle, dx, dy) {
  const h = page.locator(`.edit-resize-handle[data-handle="${handle}"]`);
  const box = await h.boundingBox();
  if (!box) throw new Error(`${handle} resize handle missing`);
  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + dx, y + dy, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(180);
}
async function main() {
  const options = args(process.argv);
  const browser = await chromium.launch({ headless:true, executablePath:browserExecutable() });
  const report = { checks:{} };
  try {
    const page = await browser.newPage({ viewport:{ width:1800, height:1000 } });
    await page.addInitScript(() => localStorage.clear());
    await page.route("https://fonts.googleapis.com/**", r => r.abort());
    await page.route("https://fonts.gstatic.com/**", r => r.abort());
    await page.goto(options.url, { waitUntil:"domcontentloaded", timeout:60000 });
    await page.waitForFunction(() => document.documentElement.dataset.layoutReady === "true" && window.EditMode);
    const slideIndex = Number.isInteger(options.slideIndex) ? options.slideIndex : 3;
    const expectedModules = Number.isInteger(options.expectedModules) ? options.expectedModules : 4;
    const gridSelector = options.gridSelector || ".column-grid";
    const moduleSelector = options.moduleSelector || ".column-item";
    await page.evaluate(async (index) => {
      window.setSlide(index);
      if (!document.documentElement.classList.contains("edit-mode")) window.EditMode.toggle(true);
      await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    }, slideIndex);
    const structure = await page.evaluate(({ gridSelector, moduleSelector }) => {
      const grid = document.querySelector(`.slide.active ${gridSelector}`);
      if (!grid) throw new Error(`grid missing: ${gridSelector}`);
      const cards = [...document.querySelectorAll(`.slide.active ${moduleSelector}`)];
      return {
        count:cards.length,
        direct:cards.every(card => card.parentElement === grid),
        slotCount:grid.querySelectorAll(':scope > [data-edit-layout-only="true"]').length,
        complete:cards.every(card => card.matches('.el[data-edit-structure="module"][data-edit-composite]') && card.firstElementChild?.dataset?.editLayer === "background")
      };
    }, { gridSelector, moduleSelector });
    await selectAllBySelector(page, `.slide.active ${moduleSelector}`);
    await page.evaluate(() => window.EditMode.group());
    await page.waitForTimeout(120);
    const before = await snapshot(page, moduleSelector);
    await dragHandle(page, "s", 0, 110);
    const after = await snapshot(page, moduleSelector);
    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(150);
    const undone = await snapshot(page, moduleSelector);
    await page.evaluate(() => window.EditMode.redo());
    await page.waitForTimeout(150);
    const redone = await snapshot(page, moduleSelector);
    if (options.screenshot) {
      await fs.mkdir(path.dirname(options.screenshot), { recursive:true });
      await page.screenshot({ path:options.screenshot, fullPage:true });
    }

    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(120);
    const horizontalBefore = await snapshot(page, moduleSelector);
    await dragHandle(page, "e", 90, 0);
    const horizontalAfter = await snapshot(page, moduleSelector);
    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(120);
    const horizontalUndone = await snapshot(page, moduleSelector);

    const cornerBefore = await snapshot(page, moduleSelector);
    await dragHandle(page, "se", 85, 60);
    const cornerAfter = await snapshot(page, moduleSelector);
    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(120);
    const cornerUndone = await snapshot(page, moduleSelector);

    const allCardsExtended = after.cards.every((card, i) => card.rect.height > before.cards[i].rect.height + 25);
    const textParticipates = after.cards.every((card, i) => card.text.some((text, j) => (
      Math.abs(text.rect.top - before.cards[i].text[j].rect.top) > 2 || text.transform !== before.cards[i].text[j].transform
    )));
    const restored = undone.cards.every((card, i) => near(card.rect.top, before.cards[i].rect.top) && near(card.rect.height, before.cards[i].rect.height));
    const replayed = redone.cards.every((card, i) => near(card.rect.top, after.cards[i].rect.top) && near(card.rect.height, after.cards[i].rect.height));
    report.structure = structure;
    report.expectedModules = expectedModules;
    report.selectors = { gridSelector, moduleSelector };
    report.before = before;
    report.after = after;
    report.undone = undone;
    report.redone = redone;
    report.horizontal = { before:horizontalBefore, after:horizontalAfter, undone:horizontalUndone };
    report.corner = { before:cornerBefore, after:cornerAfter, undone:cornerUndone };
    const horizontalExtended = horizontalAfter.frame.width > horizontalBefore.frame.width + 25
      && horizontalAfter.cards.every((card, i) => card.rect.width > horizontalBefore.cards[i].rect.width + 10);
    const horizontalRestored = horizontalUndone.cards.every((card, i) => near(card.rect.left, horizontalBefore.cards[i].rect.left) && near(card.rect.width, horizontalBefore.cards[i].rect.width));
    const cornerScaleX = cornerAfter.frame.width / cornerBefore.frame.width;
    const cornerScaleY = cornerAfter.frame.height / cornerBefore.frame.height;
    const cornerScaled = cornerScaleX > 1.03 && cornerScaleY > 1.03 && Math.abs(cornerScaleX - cornerScaleY) < 0.04;
    const cornerRestored = cornerUndone.cards.every((card, i) => near(card.rect.left, cornerBefore.cards[i].rect.left) && near(card.rect.top, cornerBefore.cards[i].rect.top) && near(card.rect.width, cornerBefore.cards[i].rect.width) && near(card.rect.height, cornerBefore.cards[i].rect.height));
    report.checks = {
      expectedCompleteDirectGridModules: structure.count === expectedModules && structure.direct && structure.slotCount === 0 && structure.complete,
      formalGroupSelected: before.mode === "group" && before.cards.every((card) => card.groupPath && card.groupPath === before.cards[0].groupPath),
      selectionFrameExtended: after.frame.height > before.frame.height + 25,
      allCardsExtended,
      textAndSpacingParticipate: textParticipates,
      undoRestoresGeometry: restored,
      redoReplaysGeometry: replayed,
      horizontalExtensionWorks: horizontalExtended,
      horizontalUndoRestoresGeometry: horizontalRestored,
      cornerProportionalScaleWorks: cornerScaled,
      cornerUndoRestoresGeometry: cornerRestored
    };
    report.pass = Object.values(report.checks).every(Boolean);
    await fs.mkdir(path.dirname(options.report), { recursive:true });
    await fs.writeFile(options.report, JSON.stringify(report, null, 2) + "\n", "utf8");
    if (!report.pass) throw new Error(`group resize ownership QA failed: ${JSON.stringify(report.checks)}`);
  } finally { await browser.close(); }
}
main().catch(err => { console.error(err.stack || err); process.exitCode = 1; });
