const crypto = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const { browserExecutable, loadPlaywright } = require('./playwright_runtime.cjs');

const { chromium } = loadPlaywright();

function parseArgs(argv) {
  const options = {};
  for (let index = 2; index < argv.length; index += 1) {
    const key = argv[index];
    if (key === '--url') options.url = argv[++index];
    else if (key === '--html') options.html = argv[++index];
    else if (key === '--report') options.report = argv[++index];
    else if (key === '--export') options.exported = argv[++index];
    else if (key === '--toc-screenshot') options.tocScreenshot = argv[++index];
    else if (key === '--reopen-screenshot') options.reopenScreenshot = argv[++index];
    else if (key === '--compare-screenshot') options.compareScreenshot = argv[++index];
  }
  if (!options.url || !options.html || !options.report || !options.exported) {
    throw new Error('--url, --html, --report and --export are required');
  }
  return options;
}

function portable(file) {
  return file ? path.relative(process.cwd(), file).replaceAll('\\', '/') : null;
}

async function sha256(file) {
  return crypto.createHash('sha256').update(await fs.readFile(file)).digest('hex');
}

async function settle(page) {
  await page.evaluate(() => new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  }));
}

async function waitReady(page) {
  await page.waitForFunction(() => (
    document.documentElement.dataset.layoutReady === 'true'
    && Boolean(window.EditMode)
    && (!document.fonts || document.fonts.status === 'loaded')
  ), null, { timeout: 120000 });
}

async function openDeck(browser, url) {
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();
  // This harness asserts the browser-download HTML export fallback. Disable
  // File System Access before load so page.evaluate export does not open a
  // native picker that Playwright cannot complete without a user gesture.
  await page.addInitScript(() => {
    Object.defineProperty(window, 'showSaveFilePicker', {
      value: undefined,
      writable: false,
      configurable: true,
    });
    window.__qaBrowserDownloadExportHarness = true;
  });
  await page.route('https://fonts.googleapis.com/**', (route) => route.abort());
  await page.route('https://fonts.gstatic.com/**', (route) => route.abort());
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await waitReady(page);
  return { context, page };
}

async function setSlide(page, index) {
  await page.evaluate((next) => window.setSlide(next), index);
  await settle(page);
}

async function selectTocRows(page) {
  await setSlide(page, 1);
  const count = await page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll('#s2 .toc-vertical-row'));
    const click = (el, shiftKey) => {
      const rect = el.getBoundingClientRect();
      const init = {
        bubbles: true,
        button: 0,
        shiftKey,
        clientX: rect.left + rect.width / 2,
        clientY: rect.top + rect.height / 2,
      };
      ['mousedown', 'mouseup', 'click'].forEach((type) => {
        el.dispatchEvent(new MouseEvent(type, init));
      });
    };
    rows.forEach((row, index) => click(row, index > 0));
    return rows.length;
  });
  await settle(page);
  if (count !== 6) throw new Error(`expected six TOC rows, got ${count}`);
}

async function selectElement(page, selector, slideIndex) {
  await setSlide(page, slideIndex);
  const found = await page.evaluate((target) => {
    const el = document.querySelector(target);
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const init = {
      bubbles: true,
      button: 0,
      clientX: rect.left + rect.width / 2,
      clientY: rect.top + rect.height / 2,
    };
    ['mousedown', 'mouseup', 'click'].forEach((type) => {
      el.dispatchEvent(new MouseEvent(type, init));
    });
    return true;
  }, selector);
  await settle(page);
  if (!found) throw new Error(`selection target missing: ${selector}`);
}

async function selectionBox(page) {
  const box = await page.locator('#edit-selection-frame').boundingBox();
  if (!box) throw new Error('selection frame missing');
  return box;
}

async function dragHandleBy(page, handleName, deltaX, deltaY) {
  const handle = page.locator(`.edit-resize-handle[data-handle="${handleName}"]`);
  const box = await handle.boundingBox();
  if (!box) throw new Error(`resize handle missing: ${handleName}`);
  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + deltaX, y + deltaY, { steps: 12 });
  await page.mouse.up();
  await settle(page);
}

async function dragHandleRatio(page, handleName, ratio) {
  const box = await selectionBox(page);
  if (handleName === 'e') await dragHandleBy(page, handleName, box.width * (ratio - 1), 0);
  else if (handleName === 'w') await dragHandleBy(page, handleName, box.width * (1 - ratio), 0);
  else if (handleName === 's') await dragHandleBy(page, handleName, 0, box.height * (ratio - 1));
  else if (handleName === 'n') await dragHandleBy(page, handleName, 0, box.height * (1 - ratio));
  else throw new Error(`unsupported handle: ${handleName}`);
}

async function restoreVerticalSize(page, handleName, targetHeight) {
  const box = await selectionBox(page);
  const missing = targetHeight - box.height;
  if (handleName === 's') await dragHandleBy(page, handleName, 0, missing);
  else if (handleName === 'n') await dragHandleBy(page, handleName, 0, -missing);
  else throw new Error(`unsupported vertical handle: ${handleName}`);
}

async function tocSnapshot(page, includeFrame = true) {
  return page.evaluate((withFrame) => {
    const rounded = (value) => Math.round(value * 1000) / 1000;
    const rectState = (rect) => ({
      left: rounded(rect.left), top: rounded(rect.top), right: rounded(rect.right), bottom: rounded(rect.bottom),
      width: rounded(rect.width), height: rounded(rect.height),
    });
    const textState = (el, rowRect) => {
      const style = getComputedStyle(el);
      const range = document.createRange();
      range.selectNodeContents(el);
      const fragments = Array.from(range.getClientRects()).filter((rect) => rect.width > 0.1 && rect.height > 0.1);
      const fallback = el.getBoundingClientRect();
      const left = fragments.length ? Math.min(...fragments.map((rect) => rect.left)) : fallback.left;
      const top = fragments.length ? Math.min(...fragments.map((rect) => rect.top)) : fallback.top;
      const right = fragments.length ? Math.max(...fragments.map((rect) => rect.right)) : fallback.right;
      const bottom = fragments.length ? Math.max(...fragments.map((rect) => rect.bottom)) : fallback.bottom;
      const lineTops = Array.from(new Set(fragments.map((rect) => Math.round(rect.top * 2) / 2)));
      return {
        text: (el.textContent || '').trim(),
        lineCount: Math.max(1, lineTops.length),
        fontSize: rounded(parseFloat(style.fontSize) || 0),
        lineHeight: rounded(parseFloat(style.lineHeight) || 0),
        paint: {
          left: rounded(left - rowRect.left), top: rounded(top - rowRect.top),
          right: rounded(right - rowRect.left), bottom: rounded(bottom - rowRect.top),
        },
        inline: {
          left: el.style.left || '', top: el.style.top || '', width: el.style.width || '', height: el.style.height || '',
          transform: el.style.transform || '', whiteSpace: el.style.whiteSpace || '', maxWidth: el.style.maxWidth || '',
        },
      };
    };
    const rows = Array.from(document.querySelectorAll('#s2 .toc-vertical-row'));
    const rowRects = rows.map((row) => row.getBoundingClientRect());
    const groupTop = Math.min(...rowRects.map((rect) => rect.top));
    const groupLeft = Math.min(...rowRects.map((rect) => rect.left));
    const groupRight = Math.max(...rowRects.map((rect) => rect.right));
    const groupBottom = Math.max(...rowRects.map((rect) => rect.bottom));
    const rowStates = rows.map((row, index) => {
      const rect = rowRects[index];
      const number = textState(row.querySelector(':scope > span'), rect);
      const title = textState(row.querySelector(':scope > b'), rect);
      const description = textState(row.querySelector(':scope > p'), rect);
      const arrow = textState(row.querySelector(':scope > i'), rect);
      const text = [number, title, description, arrow];
      return {
        row: {
          left: rounded(rect.left - groupLeft), top: rounded(rect.top - groupTop),
          width: rounded(rect.width), height: rounded(rect.height),
        },
        number,
        title,
        description,
        arrow,
        numberTitleGap: rounded(title.paint.left - number.paint.right),
        titleDescriptionGap: rounded(description.paint.left - title.paint.right),
        descriptionArrowGap: rounded(arrow.paint.left - description.paint.right),
        inside: text.every((item) => (
          item.paint.left >= -1.5 && item.paint.right <= rect.width + 1.5
          && item.paint.top >= -1.5 && item.paint.bottom <= rect.height + 1.5
        )),
      };
    });
    const gaps = rowStates.slice(1).map((row, index) => rounded(
      row.row.top - (rowStates[index].row.top + rowStates[index].row.height)
    ));
    const frameEl = withFrame ? document.querySelector('#edit-selection-frame') : null;
    const frameRect = frameEl ? frameEl.getBoundingClientRect() : null;
    return {
      frame: frameRect ? rectState(frameRect) : null,
      group: { left: 0, top: 0, width: rounded(groupRight - groupLeft), height: rounded(groupBottom - groupTop) },
      rows: rowStates,
      gaps,
    };
  }, includeFrame);
}

async function comparePanelSnapshot(page) {
  return page.evaluate(() => {
    const root = document.querySelector('#s4 .compare-panel.before');
    const rootRect = root.getBoundingClientRect();
    const textState = (selector) => {
      const el = root.querySelector(selector);
      const range = document.createRange();
      range.selectNodeContents(el);
      const rects = Array.from(range.getClientRects()).filter((rect) => rect.width > 0.1 && rect.height > 0.1);
      const left = Math.min(...rects.map((rect) => rect.left));
      const right = Math.max(...rects.map((rect) => rect.right));
      const top = Math.min(...rects.map((rect) => rect.top));
      const bottom = Math.max(...rects.map((rect) => rect.bottom));
      const lines = new Set(rects.map((rect) => Math.round(rect.top * 2) / 2));
      return {
        text: (el.textContent || '').trim(),
        lineCount: Math.max(1, lines.size),
        paint: { left: left - rootRect.left, right: right - rootRect.left, top: top - rootRect.top, bottom: bottom - rootRect.top },
      };
    };
    const kicker = textState('.compare-kicker');
    const title = textState('.compare-title');
    const subtitle = textState('.compare-subtitle');
    return {
      root: { width: rootRect.width, height: rootRect.height },
      kicker,
      title,
      subtitle,
      gaps: [title.paint.top - kicker.paint.bottom, subtitle.paint.top - title.paint.bottom],
      inside: [kicker, title, subtitle].every((item) => (
        item.paint.left >= -1.5 && item.paint.right <= rootRect.width + 1.5
        && item.paint.top >= -1.5 && item.paint.bottom <= rootRect.height + 1.5
      )),
    };
  });
}

function near(first, second, tolerance = 1.5) {
  return Math.abs(first - second) <= tolerance;
}

function typographyMatches(state, reference, tolerance = 0.6) {
  return state.rows.every((row, rowIndex) => (
    ['number', 'title', 'description', 'arrow'].every((key) => (
      near(row[key].fontSize, reference.rows[rowIndex][key].fontSize, tolerance)
      && near(row[key].lineHeight, reference.rows[rowIndex][key].lineHeight, tolerance)
    ))
  ));
}

function verticalGeometryMatches(state, reference, tolerance = 1.8) {
  return near(state.group.height, reference.group.height, tolerance)
    && state.rows.every((row, index) => (
      near(row.row.top, reference.rows[index].row.top, tolerance)
      && near(row.row.height, reference.rows[index].row.height, tolerance)
      && near(row.title.paint.top, reference.rows[index].title.paint.top, tolerance)
      && near(row.description.paint.top, reference.rows[index].description.paint.top, tolerance)
    ));
}

function safeRows(state) {
  return state.rows.every((row) => (
    row.inside
    && row.title.lineCount === 1
    && row.numberTitleGap >= 0
    && row.titleDescriptionGap >= 0
    && row.descriptionArrowGap >= 0
  ));
}

function reopenedMatches(state, reference) {
  return near(state.group.width, reference.group.width, 1.8)
    && near(state.group.height, reference.group.height, 1.8)
    && state.rows.every((row, index) => (
      near(row.row.left, reference.rows[index].row.left, 1.8)
      && near(row.row.top, reference.rows[index].row.top, 1.8)
      && near(row.row.width, reference.rows[index].row.width, 1.8)
      && near(row.row.height, reference.rows[index].row.height, 1.8)
      && row.title.lineCount === reference.rows[index].title.lineCount
      && row.description.lineCount === reference.rows[index].description.lineCount
      && near(row.number.paint.left, reference.rows[index].number.paint.left, 2)
      && near(row.title.paint.left, reference.rows[index].title.paint.left, 2)
      && near(row.description.paint.left, reference.rows[index].description.paint.left, 2)
      && typographyMatches({ rows: [row] }, { rows: [reference.rows[index]] }, 0.6)
    ));
}

async function main() {
  const options = parseArgs(process.argv);
  const htmlPath = path.resolve(options.html);
  const reportPath = path.resolve(options.report);
  const exportPath = path.resolve(options.exported);
  const sourceHashBefore = await sha256(htmlPath);
  await fs.mkdir(path.dirname(reportPath), { recursive: true });
  await fs.mkdir(path.dirname(exportPath), { recursive: true });

  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
  let result;
  try {
    const mainDeck = await openDeck(browser, options.url);
    const page = mainDeck.page;
    await selectTocRows(page);
    const initial = await tocSnapshot(page);

    await dragHandleRatio(page, 'e', 974 / initial.frame.width);
    const horizontal = await tocSnapshot(page);

    await dragHandleRatio(page, 's', 0.6);
    const southShrink = await tocSnapshot(page);
    await restoreVerticalSize(page, 's', horizontal.frame.height);
    const southExpanded = await tocSnapshot(page);

    await page.evaluate(() => window.EditMode.undo());
    await settle(page);
    const afterUndo = await tocSnapshot(page);
    await page.evaluate(() => window.EditMode.redo());
    await settle(page);
    const afterRedo = await tocSnapshot(page);

    await dragHandleRatio(page, 's', 0.6);
    await restoreVerticalSize(page, 's', horizontal.frame.height);
    const repeatedRoundTrip = await tocSnapshot(page);

    if (options.tocScreenshot) {
      await fs.mkdir(path.dirname(path.resolve(options.tocScreenshot)), { recursive: true });
      await page.screenshot({ path: path.resolve(options.tocScreenshot), fullPage: false });
    }

    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 30000 }),
      page.evaluate(() => window.EditMode.export()),
    ]);
    const exportDownloadHarness = await page.evaluate(() => ({
      forcedBrowserDownload: window.__qaBrowserDownloadExportHarness === true,
      pickerUnavailable: typeof window.showSaveFilePicker === 'undefined',
      pass: window.__qaBrowserDownloadExportHarness === true
        && typeof window.showSaveFilePicker === 'undefined',
    }));
    if (!exportDownloadHarness.pass) {
      throw new Error('Adaptive-axis QA did not force browser-download export fallback');
    }
    await download.saveAs(exportPath);
    const exportSize = (await fs.stat(exportPath)).size;
    const exportHash = await sha256(exportPath);

    const exportUrl = new URL(`/${portable(exportPath)}`, options.url).href;
    const reopenedDeck = await openDeck(browser, exportUrl);
    await setSlide(reopenedDeck.page, 1);
    const reopened = await tocSnapshot(reopenedDeck.page, false);
    if (options.reopenScreenshot) {
      await fs.mkdir(path.dirname(path.resolve(options.reopenScreenshot)), { recursive: true });
      await reopenedDeck.page.screenshot({ path: path.resolve(options.reopenScreenshot), fullPage: false });
    }

    const northDeck = await openDeck(browser, options.url);
    await selectTocRows(northDeck.page);
    const northInitial = await tocSnapshot(northDeck.page);
    await dragHandleRatio(northDeck.page, 'e', 974 / northInitial.frame.width);
    const northHorizontal = await tocSnapshot(northDeck.page);
    await dragHandleRatio(northDeck.page, 'n', 0.65);
    const northShrink = await tocSnapshot(northDeck.page);
    await restoreVerticalSize(northDeck.page, 'n', northHorizontal.frame.height);
    const northExpanded = await tocSnapshot(northDeck.page);

    const compareDeck = await openDeck(browser, options.url);
    await selectElement(compareDeck.page, '#s4 .compare-panel.before', 3);
    const compareInitial = await comparePanelSnapshot(compareDeck.page);
    await dragHandleRatio(compareDeck.page, 'e', 0.78);
    const compareHorizontal = await comparePanelSnapshot(compareDeck.page);
    if (options.compareScreenshot) {
      await fs.mkdir(path.dirname(path.resolve(options.compareScreenshot)), { recursive: true });
      await compareDeck.page.screenshot({ path: path.resolve(options.compareScreenshot), fullPage: false });
    }

    const sourceHashAfter = await sha256(htmlPath);
    const checks = {
      exactHorizontalTargetReached: near(horizontal.frame.width, 974, 3),
      horizontalResizeKeepsRowsSafe: safeRows(horizontal),
      horizontalResizeKeepsGroupHeight: near(horizontal.frame.height, initial.frame.height, 1.8),
      southShrinkOccurred: southShrink.frame.height < horizontal.frame.height * 0.64,
      southShrinkKeepsWidth: near(southShrink.frame.width, horizontal.frame.width, 1.8),
      southShrinkKeepsTextInside: southShrink.rows.every((row) => row.inside),
      southExpansionRestoresGeometry: verticalGeometryMatches(southExpanded, horizontal),
      southExpansionRestoresTypography: typographyMatches(southExpanded, horizontal),
      southExpansionKeepsRowsSafe: safeRows(southExpanded),
      undoReturnsToShrunkState: verticalGeometryMatches(afterUndo, southShrink, 2.2),
      redoReturnsToExpandedState: verticalGeometryMatches(afterRedo, southExpanded, 2.2)
        && typographyMatches(afterRedo, southExpanded),
      repeatedRoundTripDoesNotAccumulate: verticalGeometryMatches(repeatedRoundTrip, horizontal, 2.2)
        && typographyMatches(repeatedRoundTrip, horizontal)
        && safeRows(repeatedRoundTrip),
      northShrinkOccurred: northShrink.frame.height < northHorizontal.frame.height * 0.69,
      northShrinkKeepsWidth: near(northShrink.frame.width, northHorizontal.frame.width, 1.8),
      northExpansionRestoresGeometry: verticalGeometryMatches(northExpanded, northHorizontal, 2.2),
      northExpansionRestoresTypography: typographyMatches(northExpanded, northHorizontal),
      northExpansionKeepsRowsSafe: safeRows(northExpanded),
      comparePanelShrinksHorizontally: compareHorizontal.root.width < compareInitial.root.width * 0.82,
      compareKickerAndTitleStayOnOneLine: compareHorizontal.kicker.lineCount === 1
        && compareHorizontal.title.lineCount === 1,
      compareTextSpacingDoesNotWorsen: compareHorizontal.gaps.every((gap, index) => (
        gap >= compareInitial.gaps[index] - 1
      )),
      compareTextStaysInside: compareHorizontal.inside,
      exportCreated: exportSize > 100000,
      exportDownloadFallbackForced: exportDownloadHarness.pass,
      exportedReopenMatchesLive: reopenedMatches(reopened, repeatedRoundTrip),
      exportedReopenKeepsRowsSafe: safeRows(reopened),
      sourceHashStable: sourceHashBefore === sourceHashAfter,
    };

    result = {
      pass: Object.values(checks).every(Boolean),
      contract: 'mixed-axis multi-selection resize is lane-aware, reversible, non-cumulative and export-stable',
      url: options.url,
      checks,
      source: {
        file: portable(htmlPath),
        sha256Before: sourceHashBefore,
        sha256After: sourceHashAfter,
      },
      export: {
        file: portable(exportPath),
        url: exportUrl,
        bytes: exportSize,
        sha256: exportHash,
        browserDownloadHarness: exportDownloadHarness,
      },
      cases: {
        tocSouth: { initial, horizontal, shrink: southShrink, expanded: southExpanded, afterUndo, afterRedo, repeatedRoundTrip },
        tocNorth: { initial: northInitial, horizontal: northHorizontal, shrink: northShrink, expanded: northExpanded },
        compareHorizontal: { initial: compareInitial, resized: compareHorizontal },
        exportedReopen: reopened,
      },
      screenshots: {
        tocRoundTrip: portable(options.tocScreenshot),
        exportedReopen: portable(options.reopenScreenshot),
        compareHorizontal: portable(options.compareScreenshot),
      },
    };

    await Promise.all([
      mainDeck.context.close(),
      reopenedDeck.context.close(),
      northDeck.context.close(),
      compareDeck.context.close(),
    ]);
  } finally {
    await browser.close();
  }

  await fs.writeFile(reportPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({ pass: result.pass, checks: result.checks }, null, 2));
  if (!result.pass) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error.stack || String(error));
  process.exitCode = 1;
});
