const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");
const { selectAllBySelector } = require("./html_qa_selection.cjs");

function args(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === "--url") out.url = argv[++i];
    else if (argv[i] === "--report") out.report = argv[++i];
    else if (argv[i] === "--screenshot") out.screenshot = argv[++i];
    else if (argv[i] === "--slide-index") out.slideIndex = Number(argv[++i]);
    else if (argv[i] === "--toolbar-clearance") out.toolbarClearance = true;
  }
  if (!out.url || !out.report) throw new Error("--url and --report are required");
  if (!Number.isInteger(out.slideIndex) || out.slideIndex < 0) out.slideIndex = 3;
  return out;
}
function executable() {
  return [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean).find(fsSync.existsSync);
}
function near(a, b, tolerance = 3) { return Math.abs(a - b) <= tolerance; }
async function dragHandle(page, handle, dx, dy) {
  const box = await page.locator(`.edit-resize-handle[data-handle="${handle}"]`).boundingBox();
  if (!box) throw new Error(`missing ${handle} resize handle`);
  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + dx, y + dy, { steps: 14 });
  await page.mouse.up();
  await page.waitForTimeout(220);
}
async function snapshot(page, includeHeader = false) {
  return page.evaluate((includeHeaderValue) => {
    const rect = node => {
      const r = node.getBoundingClientRect();
      return { left:r.left, top:r.top, right:r.right, bottom:r.bottom, width:r.width, height:r.height };
    };
    const glyphRect = node => {
      const range = document.createRange();
      range.selectNodeContents(node);
      return rect(range);
    };
    const frame = document.getElementById("edit-selection-frame");
    const toolbar = document.getElementById("edit-selection-badge");
    const canvas = document.getElementById("canvasBox");
    const toolbarVisible = toolbar && getComputedStyle(toolbar).display !== "none";
    const rows = [...document.querySelectorAll(includeHeaderValue
      ? ".slide.active .ledger-row"
      : ".slide.active .ledger-row:not(.ledger-header)")];
    const footer = document.querySelector(".slide.active .scene-footer");
    const members = [...rows, footer];
    return {
      frame: frame ? rect(frame) : null,
      label: document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent?.trim() || "",
      toolbar: toolbarVisible ? {
        ...rect(toolbar),
        placement: toolbar.dataset.placement || "",
        chromeDock: toolbar.dataset.chromeDock === "true",
      } : null,
      canvas: canvas ? rect(canvas) : null,
      members: members.map(member => {
        const memberRect = rect(member);
        const texts = [...member.querySelectorAll('[data-edit-layer="text"]')].map(node => {
          const glyph = glyphRect(node);
          return {
            text: node.textContent.trim(),
            fontSize: parseFloat(getComputedStyle(node).fontSize) || 0,
            glyph,
            fits: glyph.left >= memberRect.left - 1
              && glyph.right <= memberRect.right + 1
              && glyph.top >= memberRect.top - 1
              && glyph.bottom <= memberRect.bottom + 1,
          };
        });
        return {
          className: member.className,
          rect: memberRect,
          groupPath: member.dataset.editGroup || "",
          texts,
        };
      }),
      footerBackground: rect(footer.querySelector('[data-edit-layer="background"]')),
    };
  }, includeHeader);
}

function moduleClearances(snapshotValue) {
  const members = snapshotValue.members.map((member, index) => ({ index, rect:member.rect }));
  const pairs = [];
  for (let i = 0; i < members.length; i += 1) {
    for (let j = i + 1; j < members.length; j += 1) {
      const first = members[i];
      const second = members[j];
      const overlapX = Math.min(first.rect.right, second.rect.right) - Math.max(first.rect.left, second.rect.left);
      if (overlapX <= 1) continue;
      const upper = first.rect.top <= second.rect.top ? first : second;
      const lower = upper === first ? second : first;
      pairs.push({ upper:upper.index, lower:lower.index, gap:lower.rect.top - upper.rect.bottom });
    }
  }
  return pairs;
}
function rectsIntersect(a, b) {
  if (!a || !b) return false;
  return Math.min(a.right, b.right) > Math.max(a.left, b.left)
    && Math.min(a.bottom, b.bottom) > Math.max(a.top, b.top);
}
async function main() {
  const options = args(process.argv);
  const browser = await chromium.launch({ headless:true, executablePath:executable() });
  const report = { url:options.url, checks:{} };
  try {
    const page = await browser.newPage({ viewport:{ width:1800, height:1000 }, deviceScaleFactor:1 });
    await page.addInitScript(() => localStorage.clear());
    await page.route("https://fonts.googleapis.com/**", route => route.abort());
    await page.route("https://fonts.gstatic.com/**", route => route.abort());
    const response = await page.goto(options.url, { waitUntil:"domcontentloaded", timeout:60000 });
    await page.waitForFunction(() => document.documentElement.dataset.layoutReady === "true" && window.EditMode, null, { timeout:120000 });
    await page.evaluate(async (slideIndex) => {
      window.setSlide(slideIndex);
      if (!document.documentElement.classList.contains("edit-mode")) window.EditMode.toggle(true);
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    }, options.slideIndex);
    report.structure = await page.evaluate(httpStatus => {
      const content = document.querySelector(".slide.active > .content");
      const footer = document.querySelector(".slide.active .scene-footer");
      const rows = [...document.querySelectorAll(".slide.active .ledger-row:not(.ledger-header)")];
      return {
        httpStatus,
        footerIsDirectSiblingModule: footer?.parentElement === content
          && footer.matches('.el[data-edit-structure="module"][data-edit-composite]'),
        footerBackgroundFirst: footer?.firstElementChild?.dataset?.editLayer === "background",
        rowCount: rows.length,
        rowsComplete: rows.every(row => row.matches('.el[data-edit-structure="module"][data-edit-composite]')
          && row.firstElementChild?.dataset?.editLayer === "background"),
      };
    }, response.status());
    const authored = await snapshot(page);

    const rowSelection = await selectAllBySelector(page, ".slide.active .ledger-row:not(.ledger-header)");
    if (rowSelection.memberFrameCount < 4) throw new Error(`ledger rows were not multi-selected; member frames=${rowSelection.memberFrameCount}`);
    const footerBox = await page.locator(".slide.active .scene-footer").boundingBox();
    if (!footerBox) throw new Error("footer missing");
    await page.keyboard.down("Shift");
    await page.mouse.click(footerBox.x + 10, footerBox.y + footerBox.height / 2);
    await page.keyboard.up("Shift");
    await page.waitForTimeout(120);
    const combinedFrameCount = await page.evaluate(() => [...document.querySelectorAll(".edit-selection-member-frame")]
      .filter(frame => getComputedStyle(frame).display !== "none").length);
    report.selectionProbe = { rowFrameCount:rowSelection.memberFrameCount, combinedFrameCount };

    await page.evaluate(() => window.EditMode.group());
    await page.waitForTimeout(150);

    let toolbarProbe = null;
    if (options.toolbarClearance) {
      await page.setViewportSize({ width:1560, height:420 });
      await page.waitForTimeout(220);
      toolbarProbe = await snapshot(page);
      await page.setViewportSize({ width:1800, height:1000 });
      await page.waitForTimeout(220);
    }
    report.toolbarProbe = toolbarProbe;
    const before = await snapshot(page);
    await dragHandle(page, "s", 0, -620);
    const after = await snapshot(page);
    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(180);
    const undone = await snapshot(page);
    await page.evaluate(() => window.EditMode.redo());
    await page.waitForTimeout(180);
    const redone = await snapshot(page);

    if (options.screenshot) {
      await fs.mkdir(path.dirname(options.screenshot), { recursive:true });
      await page.screenshot({ path:options.screenshot, fullPage:true });
    }

    const ratios = after.members.flatMap((member, memberIndex) => member.texts.map((text, textIndex) => {
      const original = before.members[memberIndex].texts[textIndex]?.fontSize || text.fontSize;
      return original > 0 ? text.fontSize / original : 1;
    }));
    const groupPath = before.members[0]?.groupPath || "";
    const footerIndex = before.members.length - 1;
    const restored = undone.members.every((member, index) => near(member.rect.top, before.members[index].rect.top)
      && near(member.rect.height, before.members[index].rect.height));
    const replayed = redone.members.every((member, index) => near(member.rect.top, after.members[index].rect.top)
      && near(member.rect.height, after.members[index].rect.height));
    const bg = after.footerBackground;
    const footer = after.members[footerIndex].rect;
    const authoredClearances = moduleClearances(authored);
    const clearances = moduleClearances(after);
    const redoneClearances = moduleClearances(redone);
    const toolbarDockedSafely = !options.toolbarClearance || (
      toolbarProbe?.toolbar?.chromeDock
      && toolbarProbe.toolbar.placement === "chrome-dock"
      && toolbarProbe.canvas
      && toolbarProbe.toolbar.bottom <= toolbarProbe.canvas.top + 1
      && !rectsIntersect(toolbarProbe.toolbar, toolbarProbe.frame)
    );

    report.authored = authored;
    report.before = before;
    report.after = after;
    report.undone = undone;
    report.redone = redone;
    report.minimumObservedFontRatio = Math.min(...ratios);
    report.authoredModuleClearances = authoredClearances;
    report.moduleClearances = clearances;
    report.redoneModuleClearances = redoneClearances;
    report.toolbarDockedSafely = toolbarDockedSafely;
    report.checks = {
      semanticFooterStructure: report.structure.httpStatus === 200
        && report.structure.footerIsDirectSiblingModule
        && report.structure.footerBackgroundFirst,
      completeLedgerRows: report.structure.rowCount === 4 && report.structure.rowsComplete,
      manualGroupIncludesRowsAndFooter: !!groupPath
        && before.members.every(member => member.groupPath === groupPath),
      selectionActuallyShrinks: after.frame.height < before.frame.height - 120,
      everyRowResizesTogether: after.members.slice(0, footerIndex).every((member, index) => (
        member.rect.height < before.members[index].rect.height - 8
      )),
      footerResizesWithGroup: after.members[footerIndex].rect.height < before.members[footerIndex].rect.height - 5,
      automaticTypographyKeepsHierarchy: ratios.every(ratio => ratio >= 0.615),
      glyphsRemainInsideModules: after.members.every(member => member.texts.every(text => text.fits)),
      authoredSemanticModulesDoNotOverlap: authoredClearances.length > 0 && authoredClearances.every(pair => pair.gap >= 2),
      semanticModulesDoNotOverlap: clearances.length > 0 && clearances.every(pair => pair.gap >= 2),
      redoPreservesModuleClearance: redoneClearances.length === clearances.length
        && redoneClearances.every(pair => pair.gap >= 2),
      footerBackgroundFollowsModule: near(bg.left, footer.left, 2)
        && near(bg.top, footer.top, 2)
        && near(bg.width, footer.width, 2)
        && near(bg.height, footer.height, 2),
      undoRestoresWholeGroup: restored,
      redoReplaysWholeGroup: replayed,
      toolbarAvoidsCanvasAndSelection: toolbarDockedSafely,
    };
    report.pass = Object.values(report.checks).every(Boolean);
    await fs.mkdir(path.dirname(options.report), { recursive:true });
    await fs.writeFile(options.report, JSON.stringify(report, null, 2) + "\n", "utf8");
    console.log(JSON.stringify({ pass:report.pass, checks:report.checks, minimumObservedFontRatio:report.minimumObservedFontRatio }));
    if (!report.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error.stack || error); process.exit(1); });
