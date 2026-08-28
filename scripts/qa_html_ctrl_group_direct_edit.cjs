const fs = require('node:fs/promises');
const fsSync = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === '--html') out.html = argv[++index];
    else if (argv[index] === '--report') out.report = argv[++index];
  }
  if (!out.html || !out.report) throw new Error('--html and --report are required');
  return out;
}

async function main() {
  const options = argsOf(process.argv);
  const htmlPath = path.resolve(options.html);
  const reportPath = path.resolve(options.report);
  const browserCandidates = [
    process.env.BROWSER_EXECUTABLE,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  ].filter(Boolean);
  const executablePath = browserCandidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  await page.route('https://fonts.googleapis.com/**', (route) => route.abort());
  await page.route('https://fonts.gstatic.com/**', (route) => route.abort());

  const settle = async () => {
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  };
  const activate = async (selector) => {
    const index = await page.locator(selector).first().evaluate((el) => Number(el.closest('.slide').dataset.index));
    await page.evaluate((slideIndex) => window.setSlide(slideIndex), index);
    await settle();
  };
  const pointFor = async (selector, textGlyph) => page.locator(selector).first().evaluate((el, useTextGlyph) => {
    let rect = el.getBoundingClientRect();
    if (useTextGlyph) {
      const range = document.createRange();
      range.selectNodeContents(el);
      const glyphRects = [...range.getClientRects()].filter((item) => item.width > 1 && item.height > 1);
      if (glyphRects.length) rect = glyphRects[0];
    }
    return {
      x: rect.left + Math.max(1, Math.min(rect.width - 1, rect.width / 2)),
      y: rect.top + Math.max(1, Math.min(rect.height - 1, rect.height / 2)),
    };
  }, textGlyph);
  const ctrlClick = async (point) => {
    await page.keyboard.down('Control');
    await page.mouse.click(point.x, point.y);
    await page.keyboard.up('Control');
    await settle();
  };
  const click = async (point, shiftKey = false) => {
    if (shiftKey) await page.keyboard.down('Shift');
    await page.mouse.click(point.x, point.y);
    if (shiftKey) await page.keyboard.up('Shift');
    await settle();
  };
  const stateFor = async (targetSelector, rootSelector) => page.evaluate(({ targetSelector: target, rootSelector: root }) => {
    const targetEl = document.querySelector(target);
    const rootEl = document.querySelector(root);
    const frame = document.getElementById('edit-selection-frame');
    const memberFrames = [...document.querySelectorAll('.edit-selection-member-frame')]
      .filter((item) => getComputedStyle(item).display !== 'none');
    return {
      selectionMode: frame?.dataset.selectionMode || '',
      selectionVisible: Boolean(frame && getComputedStyle(frame).display !== 'none'),
      memberFrameCount: memberFrames.length,
      contenteditable: targetEl?.getAttribute('contenteditable') || '',
      activeElementMatches: document.activeElement === targetEl,
      groupState: rootEl?.dataset.editGroupState || '',
      groupPath: rootEl?.dataset.editGroup || '',
    };
  }, { targetSelector, rootSelector });

  let result = { pass: false };
  try {
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'commit', timeout: 30000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === 'true' && Boolean(window.EditMode)
    ), null, { timeout: 120000 });
    await page.evaluate(() => Promise.race([
      document.fonts?.ready || Promise.resolve(),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]));

    const rootSelector = '#stage > .slide .demo-card';
    const backgroundSelector = `${rootSelector} [data-edit-layer="background"]`;
    const textSelector = `${rootSelector} [data-edit-layer="text"].card-title`;
    await activate(rootSelector);
    const backgroundPoint = await pointFor(rootSelector, false);
    const textPoint = await pointFor(textSelector, true);

    await click(backgroundPoint);
    const ordinaryGeneratedBefore = await stateFor(backgroundSelector, rootSelector);
    await ctrlClick(backgroundPoint);
    const directGeneratedBackground = await stateFor(backgroundSelector, rootSelector);
    await click(backgroundPoint);
    const ordinaryGeneratedAfterBackground = await stateFor(backgroundSelector, rootSelector);
    await ctrlClick(textPoint);
    const directGeneratedText = await stateFor(textSelector, rootSelector);
    await page.keyboard.press('Escape');
    await settle();
    await click(textPoint);
    const ordinaryGeneratedRestored = await stateFor(textSelector, rootSelector);

    const generated = {
      ordinaryBefore: ordinaryGeneratedBefore,
      directBackground: directGeneratedBackground,
      ordinaryAfterBackground: ordinaryGeneratedAfterBackground,
      directText: directGeneratedText,
      ordinaryRestored: ordinaryGeneratedRestored,
      pass: ordinaryGeneratedBefore.selectionMode === 'group'
        && ordinaryGeneratedBefore.memberFrameCount === 0
        && directGeneratedBackground.selectionMode === 'single'
        && directGeneratedBackground.groupState !== 'ungrouped'
        && ordinaryGeneratedAfterBackground.selectionMode === 'group'
        && directGeneratedText.selectionMode === 'text-edit'
        && directGeneratedText.contenteditable === 'true'
        && directGeneratedText.activeElementMatches
        && directGeneratedText.groupState !== 'ungrouped'
        && ordinaryGeneratedRestored.selectionMode === 'group'
        && ordinaryGeneratedRestored.contenteditable !== 'true',
    };

    const manualRootSelectors = [
      '#stage > .slide .toc-card[data-card-no="01"]',
      '#stage > .slide .toc-card[data-card-no="02"]',
    ];
    const manualTextSelector = `${manualRootSelectors[0]} [data-edit-layer="text"].card-title`;
    await activate(manualRootSelectors[0]);
    await page.evaluate((selectors) => selectors.forEach((selector) => {
      const el = document.querySelector(selector);
      if (el) delete el.dataset.editGroup;
    }), manualRootSelectors);
    await page.evaluate(() => window.EditMode.deselect());
    await settle();
    const manualPoints = await Promise.all(manualRootSelectors.map((selector) => pointFor(selector, false)));
    await click(manualPoints[0]);
    await click(manualPoints[1], true);
    await page.keyboard.press('Control+g');
    await settle();
    const manualGroupCreated = await page.evaluate((selectors) => {
      const roots = selectors.map((selector) => document.querySelector(selector));
      const paths = roots.map((root) => (root?.dataset.editGroup || '').split('>').filter(Boolean));
      const groupId = paths[0]?.[paths[0].length - 1] || '';
      return {
        groupId,
        paths,
        selectionMode: document.getElementById('edit-selection-frame')?.dataset.selectionMode || '',
        pass: Boolean(groupId) && paths.every((pathItems) => pathItems.includes(groupId)),
      };
    }, manualRootSelectors);
    const manualTextPoint = await pointFor(manualTextSelector, true);
    await ctrlClick(manualTextPoint);
    const directManualText = await stateFor(manualTextSelector, manualRootSelectors[0]);
    const manualPathPreserved = directManualText.groupPath.split('>').includes(manualGroupCreated.groupId);
    await page.keyboard.press('Escape');
    await settle();
    await click(manualTextPoint);
    const ordinaryManualRestored = await stateFor(manualTextSelector, manualRootSelectors[0]);
    await page.keyboard.press('Control+Shift+g');
    await settle();

    const manual = {
      created: manualGroupCreated,
      directText: directManualText,
      groupPathPreserved: manualPathPreserved,
      ordinaryRestored: ordinaryManualRestored,
      pass: manualGroupCreated.pass
        && manualGroupCreated.selectionMode === 'group'
        && directManualText.selectionMode === 'text-edit'
        && directManualText.contenteditable === 'true'
        && directManualText.activeElementMatches
        && manualPathPreserved
        && ordinaryManualRestored.selectionMode === 'group'
        && ordinaryManualRestored.contenteditable !== 'true',
    };

    result = {
      html: path.relative(process.cwd(), htmlPath).replaceAll('\\', '/'),
      generated,
      manual,
      pass: generated.pass && manual.pass,
    };
  } catch (error) {
    result = { ...result, error: String(error && error.stack ? error.stack : error), pass: false };
  } finally {
    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, JSON.stringify(result, null, 2) + '\n', 'utf8');
    console.log(JSON.stringify(result));
    await browser.close();
  }
  if (!result.pass) process.exitCode = 1;
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
