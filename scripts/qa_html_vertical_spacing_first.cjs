const crypto = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const { browserExecutable, loadPlaywright } = require('./playwright_runtime.cjs');

const { chromium } = loadPlaywright();

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === '--url') out.url = argv[++index];
    else if (argv[index] === '--html') out.html = argv[++index];
    else if (argv[index] === '--report') out.report = argv[++index];
    else if (argv[index] === '--screenshot') out.screenshot = argv[++index];
  }
  if (!out.url || !out.report) throw new Error('--url and --report are required');
  return out;
}

async function sha256(file) {
  if (!file) return null;
  const content = await fs.readFile(file);
  return crypto.createHash('sha256').update(content).digest('hex');
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
      document.documentElement.dataset.layoutReady === 'true' && Boolean(window.EditMode)
    ), null, { timeout: 120000 });

    const moderate = await page.evaluate(async () => {
      const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      window.setSlide(3);
      await frame();
      const root = document.querySelector('#s4 .compare-panel.after');
      if (!root) return { error: 'before-after fixture missing' };

      const click = (el) => {
        const rect = el.getBoundingClientRect();
        const init = { bubbles: true, button: 0,
          clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2 };
        ['mousedown', 'mouseup', 'click'].forEach((type) => el.dispatchEvent(new MouseEvent(type, init)));
      };
      const snapshot = () => {
        const rootRect = root.getBoundingClientRect();
        const direct = Array.from(root.children).filter((el) => el.dataset.editLayer !== 'background');
        const blocks = direct.map((el) => {
          const rect = el.getBoundingClientRect();
          const transform = getComputedStyle(el).transform;
          const matrix = transform === 'none' ? new DOMMatrixReadOnly() : new DOMMatrixReadOnly(transform);
          return {
            name: el.className || el.tagName,
            top: rect.top - rootRect.top,
            bottom: rect.bottom - rootRect.top,
            height: rect.height,
            transform: el.style.transform || '',
            scaleX: matrix.a,
            scaleY: matrix.d,
          };
        });
        const gaps = [blocks[0].top];
        for (let index = 1; index < blocks.length; index += 1) {
          gaps.push(blocks[index].top - blocks[index - 1].bottom);
        }
        gaps.push(rootRect.height - blocks[blocks.length - 1].bottom);
        const fonts = Array.from(root.querySelectorAll('[data-edit-layer="text"],[data-edit-layer="metric"]')).map((el) => {
          const style = getComputedStyle(el);
          const range = document.createRange();
          range.selectNodeContents(el);
          const paint = range.getBoundingClientRect();
          const transform = style.transform;
          const matrix = transform === 'none' ? new DOMMatrixReadOnly() : new DOMMatrixReadOnly(transform);
          return {
            text: (el.textContent || '').trim(),
            fontSize: parseFloat(style.fontSize),
            lineHeight: parseFloat(style.lineHeight),
            paintTop: paint.top - rootRect.top,
            paintBottom: paint.bottom - rootRect.top,
            scaleX: matrix.a,
            scaleY: matrix.d,
          };
        });
        return {
          root: { width: rootRect.width, height: rootRect.height },
          blocks,
          gaps,
          fonts,
          signalHeight: root.querySelector('.compare-signal').getBoundingClientRect().height,
          listHeight: root.querySelector('ul').getBoundingClientRect().height,
          rowHeights: Array.from(root.querySelectorAll('li')).map((el) => el.getBoundingClientRect().height),
        };
      };
      const drag = async (ratio) => {
        const before = root.getBoundingClientRect();
        const handle = document.querySelector('.edit-resize-handle[data-handle="s"]');
        const rect = handle.getBoundingClientRect();
        const startX = rect.left + rect.width / 2;
        const startY = rect.top + rect.height / 2;
        const deltaY = -before.height * (1 - ratio);
        handle.dispatchEvent(new MouseEvent('mousedown', {
          bubbles: true, button: 0, clientX: startX, clientY: startY,
        }));
        window.dispatchEvent(new MouseEvent('mousemove', {
          bubbles: true, button: 0, clientX: startX, clientY: startY + deltaY,
        }));
        window.dispatchEvent(new MouseEvent('mouseup', {
          bubbles: true, button: 0, clientX: startX, clientY: startY + deltaY,
        }));
        await frame();
      };

      click(root);
      await frame();
      const before = snapshot();
      await drag(0.8);
      return { before, after: snapshot() };
    });

    if (options.screenshot) {
      await fs.mkdir(path.dirname(options.screenshot), { recursive: true });
      await page.screenshot({ path: options.screenshot, fullPage: false });
    }

    const deepAndUndo = await page.evaluate(async () => {
      const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const root = document.querySelector('#s4 .compare-panel.after');
      const snapshot = () => {
        const rootRect = root.getBoundingClientRect();
        const blocks = Array.from(root.children).filter((el) => el.dataset.editLayer !== 'background').map((el) => {
          const rect = el.getBoundingClientRect();
          const transform = getComputedStyle(el).transform;
          const matrix = transform === 'none' ? new DOMMatrixReadOnly() : new DOMMatrixReadOnly(transform);
          return {
            name: el.className || el.tagName,
            top: rect.top - rootRect.top,
            bottom: rect.bottom - rootRect.top,
            height: rect.height,
            transform: el.style.transform || '',
            scaleX: matrix.a,
            scaleY: matrix.d,
          };
        });
        const gaps = [blocks[0].top];
        for (let index = 1; index < blocks.length; index += 1) gaps.push(blocks[index].top - blocks[index - 1].bottom);
        gaps.push(rootRect.height - blocks[blocks.length - 1].bottom);
        const fonts = Array.from(root.querySelectorAll('[data-edit-layer="text"],[data-edit-layer="metric"]')).map((el) => {
          const style = getComputedStyle(el);
          const range = document.createRange();
          range.selectNodeContents(el);
          const paint = range.getBoundingClientRect();
          const transform = style.transform;
          const matrix = transform === 'none' ? new DOMMatrixReadOnly() : new DOMMatrixReadOnly(transform);
          return {
            text: (el.textContent || '').trim(),
            fontSize: parseFloat(style.fontSize),
            lineHeight: parseFloat(style.lineHeight),
            paintTop: paint.top - rootRect.top,
            paintBottom: paint.bottom - rootRect.top,
            scaleX: matrix.a,
            scaleY: matrix.d,
          };
        });
        return {
          root: { width: rootRect.width, height: rootRect.height }, blocks, gaps, fonts,
          signalHeight: root.querySelector('.compare-signal').getBoundingClientRect().height,
          listHeight: root.querySelector('ul').getBoundingClientRect().height,
          rowHeights: Array.from(root.querySelectorAll('li')).map((el) => el.getBoundingClientRect().height),
        };
      };
      const drag = async (ratio) => {
        const before = root.getBoundingClientRect();
        const handle = document.querySelector('.edit-resize-handle[data-handle="s"]');
        const rect = handle.getBoundingClientRect();
        const startX = rect.left + rect.width / 2;
        const startY = rect.top + rect.height / 2;
        const deltaY = -before.height * (1 - ratio);
        handle.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, button: 0, clientX: startX, clientY: startY }));
        window.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, button: 0, clientX: startX, clientY: startY + deltaY }));
        window.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, button: 0, clientX: startX, clientY: startY + deltaY }));
        await frame();
      };

      window.EditMode.undo();
      await frame();
      const moderateUndo = snapshot();
      await drag(0.6);
      const deep = snapshot();
      window.EditMode.undo();
      await frame();
      return { moderateUndo, deep, deepUndo: snapshot() };
    });

    const sourceAfter = await sha256(options.html);
    const before = moderate.before;
    const stageOne = moderate.after;
    const deep = deepAndUndo.deep;
    const near = (first, second, tolerance = 1.2) => Math.abs(first - second) <= tolerance;
    const sum = (items) => items.reduce((total, value) => total + value, 0);
    const noBlockOverlap = (state) => state.gaps.every((gap) => gap >= -0.8);
    const textInside = (state) => state.fonts.every((font) => (
      font.paintTop >= -0.8 && font.paintBottom <= state.root.height + 0.8
    ));
    const noScaleTransform = (state) => state.blocks.concat(state.fonts).every((item) => (
      near(item.scaleX, 1, 0.01) && near(item.scaleY, 1, 0.01)
    ));
    const fontsMatch = (state, reference) => state.fonts.every((font, index) => (
      near(font.fontSize, reference.fonts[index].fontSize, 0.2)
      && near(font.lineHeight, reference.fonts[index].lineHeight, 0.2)
    ));
    const geometryRestored = (state) => (
      near(state.root.width, before.root.width)
      && near(state.root.height, before.root.height)
      && state.blocks.every((block, index) => (
        near(block.top, before.blocks[index].top)
        && near(block.height, before.blocks[index].height)
        && block.transform === before.blocks[index].transform
      ))
      && state.rowHeights.every((height, index) => near(height, before.rowHeights[index]))
      && fontsMatch(state, before)
    );

    const checks = {
      stageOneHeightAtEightyPercent: near(stageOne.root.height, before.root.height * 0.8, 2),
      stageOneWidthStable: near(stageOne.root.width, before.root.width),
      stageOneFontsStable: fontsMatch(stageOne, before),
      stageOneSpacingCompressed: sum(stageOne.gaps) < sum(before.gaps) - 20,
      stageOneNoOverlap: noBlockOverlap(stageOne) && textInside(stageOne),
      stageOneNoScaleY: noScaleTransform(stageOne),
      stageOneUndoRestores: geometryRestored(deepAndUndo.moderateUndo),
      stageTwoHeightAtSixtyPercent: near(deep.root.height, before.root.height * 0.6, 2),
      stageTwoFontsReduced: deep.fonts.every((font, index) => font.fontSize < before.fonts[index].fontSize - 0.5),
      stageTwoContentBlocksReduced: deep.signalHeight < before.signalHeight - 10 && deep.listHeight < before.listHeight - 10,
      stageTwoSpacingAtFloor: sum(deep.gaps) < sum(stageOne.gaps),
      stageTwoNoOverlap: noBlockOverlap(deep) && textInside(deep),
      stageTwoNoScaleY: noScaleTransform(deep),
      stageTwoUndoRestores: geometryRestored(deepAndUndo.deepUndo),
      sourceHashStable: !options.html || sourceBefore === sourceAfter,
    };
    result = {
      pass: Object.values(checks).every(Boolean),
      contract: 'vertical side-handle shrink consumes inter-block spacing first, then reduces content after spacing floors',
      url: options.url,
      checks,
      source: options.html ? {
        file: path.relative(process.cwd(), options.html).replaceAll('\\', '/'),
        sha256Before: sourceBefore,
        sha256After: sourceAfter,
      } : null,
      measurements: { before, stageOneEightyPercent: stageOne, stageTwoSixtyPercent: deep },
      screenshot: options.screenshot ? path.relative(process.cwd(), options.screenshot).replaceAll('\\', '/') : null,
    };
  } finally {
    await browser.close();
  }

  await fs.mkdir(path.dirname(options.report), { recursive: true });
  await fs.writeFile(options.report, JSON.stringify(result, null, 2) + '\n', 'utf8');
  console.log(JSON.stringify({ pass: result.pass, checks: result.checks }, null, 2));
  return result.pass ? 0 : 1;
}

main().then((code) => process.exit(code)).catch((error) => {
  console.error(error);
  process.exit(1);
});
