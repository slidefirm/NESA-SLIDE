const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === '--url') out.url = argv[++index];
    else if (argv[index] === '--report') out.report = argv[++index];
  }
  if (!out.url || !out.report) throw new Error('--url and --report are required');
  return out;
}

function closeEnough(first, second, tolerance = 0.015) {
  return Math.abs(first - second) <= tolerance;
}

async function nextFrame(page) {
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

async function snapshot(page) {
  return page.evaluate(() => {
    const root = document.querySelector('.slide.active .scene-content[data-edit-composite]');
    const card = document.querySelector('.slide.active .metric-item.item-1');
    const text = document.querySelector('.slide.active .metric-value[data-edit-layer=text]');
    const rootRect = root.getBoundingClientRect();
    const cardRect = card.getBoundingClientRect();
    const textRect = text.getBoundingClientRect();
    const normalized = (rect) => ({
      left: (rect.left - rootRect.left) / rootRect.width,
      top: (rect.top - rootRect.top) / rootRect.height,
      width: rect.width / rootRect.width,
      height: rect.height / rootRect.height,
    });
    return {
      root: {
        left: rootRect.left,
        top: rootRect.top,
        width: rootRect.width,
        height: rootRect.height,
        ratio: rootRect.width / rootRect.height,
        transform: getComputedStyle(root).transform,
      },
      card: {
        ...normalized(cardRect),
        background: getComputedStyle(card).backgroundColor,
        borderTopWidth: getComputedStyle(card).borderTopWidth,
      },
      text: normalized(textRect),
    };
  });
}

async function main() {
  const options = argsOf(process.argv);
  const executablePath = [
    process.env.BROWSER_EXECUTABLE,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  ].filter(Boolean).find((candidate) => fs.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  try {
    await page.route('https://fonts.googleapis.com/**', (route) => route.abort());
    await page.route('https://fonts.gstatic.com/**', (route) => route.abort());
    await page.goto(options.url, { waitUntil: 'commit', timeout: 120000 });
    await page.waitForFunction(() => document.documentElement.dataset.layoutReady === 'true' && Boolean(window.EditMode));
    await page.evaluate(() => window.setSlide(10));
    await nextFrame(page);

    const text = page.locator('.slide.active .metric-value[data-edit-layer=text]').first();
    const textBox = await text.boundingBox();
    await page.mouse.click(textBox.x + textBox.width / 2, textBox.y + textBox.height / 2);
    await nextFrame(page);

    const before = await snapshot(page);
    const handle = page.locator('.edit-resize-handle[data-handle=e]');
    await handle.waitFor({ state: 'visible' });
    const handleBox = await handle.boundingBox();
    const stageScale = await page.evaluate(() => {
      const stage = document.getElementById('stage');
      return stage.getBoundingClientRect().width / stage.offsetWidth;
    });
    const x = handleBox.x + handleBox.width / 2;
    const y = handleBox.y + handleBox.height / 2;
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x - 320 * stageScale, y, { steps: 10 });
    await page.mouse.up();
    await nextFrame(page);

    const after = await snapshot(page);
    const normalizedStable = (first, second) => ['left', 'top', 'width', 'height']
      .every((key) => closeEnough(first[key], second[key]));
    const checks = {
      wholeGroupShrank: after.root.width < before.root.width * 0.9
        && after.root.height < before.root.height * 0.9,
      aspectRatioPreserved: closeEnough(before.root.ratio, after.root.ratio, 0.01),
      rootTransformChanged: before.root.transform !== after.root.transform,
      cardScaledWithGroup: normalizedStable(before.card, after.card),
      textScaledWithGroup: normalizedStable(before.text, after.text),
      cardStylingPreserved: before.card.background === after.card.background
        && before.card.borderTopWidth === after.card.borderTopWidth,
    };

    await page.evaluate(() => window.EditMode.undo());
    await nextFrame(page);
    const undo = await snapshot(page);
    await page.evaluate(() => window.EditMode.redo());
    await nextFrame(page);
    const redo = await snapshot(page);
    checks.undoRestored = closeEnough(undo.root.width, before.root.width, 1)
      && closeEnough(undo.root.height, before.root.height, 1)
      && undo.root.transform === before.root.transform;
    checks.redoRestored = closeEnough(redo.root.width, after.root.width, 1)
      && closeEnough(redo.root.height, after.root.height, 1)
      && redo.root.transform === after.root.transform;

    const report = { url: options.url, before, after, undo, redo, checks, pass: Object.values(checks).every(Boolean) };
    fs.mkdirSync(path.dirname(path.resolve(options.report)), { recursive: true });
    fs.writeFileSync(path.resolve(options.report), JSON.stringify(report, null, 2) + '\n', 'utf8');
    console.log(JSON.stringify(report));
    if (!report.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
