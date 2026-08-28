const crypto = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const { browserExecutable, loadPlaywright } = require('./playwright_runtime.cjs');

const { chromium } = loadPlaywright();

function argsOf(argv) {
  const options = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === '--url') options.url = argv[++index];
    else if (argv[index] === '--html') options.html = argv[++index];
    else if (argv[index] === '--report') options.report = argv[++index];
    else if (argv[index] === '--toc-screenshot') options.tocScreenshot = argv[++index];
    else if (argv[index] === '--compare-screenshot') options.compareScreenshot = argv[++index];
  }
  if (!options.url || !options.report) throw new Error('--url and --report are required');
  return options;
}

async function sha256(file) {
  if (!file) return null;
  return crypto.createHash('sha256').update(await fs.readFile(file)).digest('hex');
}

function portable(file) {
  return file ? path.relative(process.cwd(), file).replaceAll('\\', '/') : null;
}

async function main() {
  const options = argsOf(process.argv);
  const sourceBefore = await sha256(options.html);
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  let result;

  try {
    await page.route('https://fonts.googleapis.com/**', (route) => route.abort());
    await page.route('https://fonts.gstatic.com/**', (route) => route.abort());
    await page.goto(options.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === 'true'
      && Boolean(window.EditMode)
      && (!document.fonts || document.fonts.status === 'loaded')
    ), null, { timeout: 120000 });

    const compare = await page.evaluate(async () => {
      const settle = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const near = (first, second, tolerance = 1.2) => Math.abs(first - second) <= tolerance;
      const rectOf = (rect) => ({
        left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom,
        width: rect.width, height: rect.height,
      });
      const paintState = (el, rootRect) => {
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
          box: { left: fallback.left - rootRect.left, top: fallback.top - rootRect.top, right: fallback.right - rootRect.left, bottom: fallback.bottom - rootRect.top },
          paint: { left: left - rootRect.left, top: top - rootRect.top, right: right - rootRect.left, bottom: bottom - rootRect.top },
          inline: {
            left: el.style.left || '', width: el.style.width || '', height: el.style.height || '',
            maxWidth: el.style.maxWidth || '', whiteSpace: el.style.whiteSpace || '',
          },
        };
      };
      const click = (el) => {
        const rect = el.getBoundingClientRect();
        const init = { bubbles: true, button: 0, clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 };
        ['mousedown', 'mouseup', 'click'].forEach((type) => el.dispatchEvent(new MouseEvent(type, init)));
      };

      window.setSlide(3);
      await settle();
      const root = document.querySelector('#s4 .compare-panel.before');
      if (!root) return { error: 'before panel missing' };
      click(root);
      await settle();

      const snapshot = () => {
        const rootRect = root.getBoundingClientRect();
        const nodes = {
          kicker: root.querySelector('.compare-kicker'),
          title: root.querySelector('.compare-title'),
          subtitle: root.querySelector('.compare-subtitle'),
        };
        const text = Object.fromEntries(Object.entries(nodes).map(([key, el]) => [key, paintState(el, rootRect)]));
        const order = ['kicker', 'title', 'subtitle'];
        const paintGaps = order.slice(1).map((key, index) => text[key].paint.top - text[order[index]].paint.bottom);
        const boxGaps = order.slice(1).map((key, index) => text[key].box.top - text[order[index]].box.bottom);
        return {
          root: rectOf(rootRect),
          rootInline: { left: root.style.left || '', width: root.style.width || '' },
          text,
          paintGaps,
          boxGaps,
          textInside: Object.values(text).every((item) => (
            item.paint.left >= -1 && item.paint.right <= rootRect.width + 1
            && item.paint.top >= -1 && item.paint.bottom <= rootRect.height + 1
          )),
        };
      };
      const drag = async (ratio) => {
        const selection = document.querySelector('#edit-selection-frame').getBoundingClientRect();
        const handle = document.querySelector('.edit-resize-handle[data-handle="s"]');
        const rect = handle.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        const nextY = y - selection.height * (1 - ratio);
        handle.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, button: 0, clientX: x, clientY: y }));
        window.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, button: 0, clientX: x, clientY: nextY }));
        window.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, button: 0, clientX: x, clientY: nextY }));
        await settle();
      };

      const initial = snapshot();
      await drag(0.78);
      const first = snapshot();
      window.EditMode.undo();
      await settle();
      const afterUndo = snapshot();
      window.EditMode.redo();
      await settle();
      const afterRedo = snapshot();
      window.EditMode.undo();
      await settle();
      await drag(0.66);
      const repeated = snapshot();

      const modes = (state) => Object.fromEntries(Object.entries(state.text).map(([key, item]) => [key, item.inline]));
      const lines = (state) => Object.fromEntries(Object.entries(state.text).map(([key, item]) => [key, item.lineCount]));
      return {
        initial, first, afterUndo, afterRedo, repeated,
        checks: {
          firstResizeOccurred: first.root.height < initial.root.height - 20,
          undoRestoresHeight: near(afterUndo.root.height, initial.root.height),
          redoRestoresHeight: near(afterRedo.root.height, first.root.height),
          repeatResizeOccurred: repeated.root.height < initial.root.height - 40,
          rootWidthStable: [first, afterUndo, afterRedo, repeated].every((state) => near(state.root.width, initial.root.width)),
          intrinsicModesPreservedAfterUndo: JSON.stringify(modes(afterUndo)) === JSON.stringify(modes(initial)),
          intrinsicModesPreservedAfterRedo: JSON.stringify(modes(afterRedo)) === JSON.stringify(modes(initial)),
          intrinsicModesPreservedAfterRepeat: JSON.stringify(modes(repeated)) === JSON.stringify(modes(initial)),
          lineCountsStable: JSON.stringify(lines(repeated)) === JSON.stringify(lines(initial)),
          noTextCollision: repeated.boxGaps.every((gap) => gap >= -1),
          textInsideFrame: repeated.textInside,
        },
      };
    });

    if (options.compareScreenshot) {
      await fs.mkdir(path.dirname(options.compareScreenshot), { recursive: true });
      await page.screenshot({ path: options.compareScreenshot, fullPage: false });
    }

    const toc = await page.evaluate(async () => {
      const settle = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const near = (first, second, tolerance = 1.2) => Math.abs(first - second) <= tolerance;
      const rectOf = (rect) => ({
        left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom,
        width: rect.width, height: rect.height,
      });
      const paintState = (el, rowRect) => {
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
          paint: { left: left - rowRect.left, top: top - rowRect.top, right: right - rowRect.left, bottom: bottom - rowRect.top },
          inline: {
            left: el.style.left || '', width: el.style.width || '', height: el.style.height || '',
            maxWidth: el.style.maxWidth || '', whiteSpace: el.style.whiteSpace || '',
          },
        };
      };
      const click = (el, shiftKey = false) => {
        const rect = el.getBoundingClientRect();
        const init = {
          bubbles: true, button: 0, shiftKey,
          clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2,
        };
        ['mousedown', 'mouseup', 'click'].forEach((type) => el.dispatchEvent(new MouseEvent(type, init)));
      };

      window.setSlide(1);
      await settle();
      const rows = Array.from(document.querySelectorAll('#s2 .toc-vertical-row'));
      if (rows.length !== 6) return { error: `expected 6 TOC rows, got ${rows.length}` };
      click(rows[0]);
      rows.slice(1).forEach((row) => click(row, true));
      await settle();
      window.EditMode.group();
      await settle();

      const snapshot = () => {
        const frame = document.querySelector('#edit-selection-frame').getBoundingClientRect();
        const rowStates = rows.map((row) => {
          const rowRect = row.getBoundingClientRect();
          const number = paintState(row.querySelector(':scope > span'), rowRect);
          const title = paintState(row.querySelector(':scope > b'), rowRect);
          const description = paintState(row.querySelector(':scope > p'), rowRect);
          return {
            row: rectOf(rowRect), number, title, description,
            numberTitleGap: title.paint.left - number.paint.right,
            titleDescriptionGap: description.paint.left - title.paint.right,
            inside: [number, title, description].every((item) => (
              item.paint.left >= -1 && item.paint.right <= rowRect.width + 1
              && item.paint.top >= -1 && item.paint.bottom <= rowRect.height + 1
            )),
          };
        });
        return { frame: rectOf(frame), rows: rowStates };
      };
      const drag = async (ratio) => {
        const selection = document.querySelector('#edit-selection-frame').getBoundingClientRect();
        const handle = document.querySelector('.edit-resize-handle[data-handle="s"]');
        const rect = handle.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        const nextY = y - selection.height * (1 - ratio);
        handle.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, button: 0, clientX: x, clientY: y }));
        window.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, button: 0, clientX: x, clientY: nextY }));
        window.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, button: 0, clientX: x, clientY: nextY }));
        await settle();
      };

      const initial = snapshot();
      await drag(0.76);
      const first = snapshot();
      window.EditMode.undo();
      await settle();
      const afterUndo = snapshot();
      window.EditMode.redo();
      await settle();
      const afterRedo = snapshot();
      window.EditMode.undo();
      await settle();
      await drag(0.62);
      const repeated = snapshot();

      const modes = (state) => state.rows.map((row) => ({
        number: row.number.inline, title: row.title.inline, description: row.description.inline,
      }));
      const lineCounts = (state, key) => state.rows.map((row) => row[key].lineCount);
      return {
        selectedMembers: rows.length,
        initial, first, afterUndo, afterRedo, repeated,
        checks: {
          firstResizeOccurred: first.frame.height < initial.frame.height - 20,
          undoRestoresHeight: near(afterUndo.frame.height, initial.frame.height),
          redoRestoresHeight: near(afterRedo.frame.height, first.frame.height),
          repeatResizeOccurred: repeated.frame.height < initial.frame.height - 40,
          groupWidthStable: [first, afterUndo, afterRedo, repeated].every((state) => near(state.frame.width, initial.frame.width)),
          intrinsicModesPreservedAfterUndo: JSON.stringify(modes(afterUndo)) === JSON.stringify(modes(initial)),
          intrinsicModesPreservedAfterRedo: JSON.stringify(modes(afterRedo)) === JSON.stringify(modes(initial)),
          intrinsicModesPreservedAfterRepeat: JSON.stringify(modes(repeated)) === JSON.stringify(modes(initial)),
          titleLineCountsStable: JSON.stringify(lineCounts(repeated, 'title')) === JSON.stringify(lineCounts(initial, 'title')),
          descriptionLineCountsStable: JSON.stringify(lineCounts(repeated, 'description')) === JSON.stringify(lineCounts(initial, 'description')),
          numberTitleSeparated: repeated.rows.every((row) => row.numberTitleGap >= -1),
          titleDescriptionSeparated: repeated.rows.every((row) => row.titleDescriptionGap >= -1),
          textInsideRows: repeated.rows.every((row) => row.inside),
        },
      };
    });

    if (options.tocScreenshot) {
      await fs.mkdir(path.dirname(options.tocScreenshot), { recursive: true });
      await page.screenshot({ path: options.tocScreenshot, fullPage: false });
    }

    const sourceAfter = await sha256(options.html);
    const comparePass = !compare.error && Object.values(compare.checks).every(Boolean);
    const tocPass = !toc.error && Object.values(toc.checks).every(Boolean);
    result = {
      pass: comparePass && tocPass && (!options.html || sourceBefore === sourceAfter),
      contract: 'vertical resize history preserves intrinsic horizontal geometry through repeated resize and Undo/Redo',
      url: options.url,
      source: options.html ? {
        file: portable(options.html), sha256Before: sourceBefore, sha256After: sourceAfter,
        stable: sourceBefore === sourceAfter,
      } : null,
      cases: { beforeAfterPanel: compare, tocRows: toc },
      screenshots: {
        beforeAfterPanel: portable(options.compareScreenshot),
        tocRows: portable(options.tocScreenshot),
      },
    };
  } finally {
    await browser.close();
  }

  await fs.mkdir(path.dirname(options.report), { recursive: true });
  await fs.writeFile(options.report, JSON.stringify(result, null, 2) + '\n', 'utf8');
  console.log(JSON.stringify({
    pass: result.pass,
    beforeAfterPanel: result.cases.beforeAfterPanel.checks,
    tocRows: result.cases.tocRows.checks,
  }, null, 2));
  return result.pass ? 0 : 1;
}

main().then((code) => process.exit(code)).catch((error) => {
  console.error(error);
  process.exit(1);
});
