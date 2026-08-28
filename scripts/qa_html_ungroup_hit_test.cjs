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

async function clickCenter(page, selector) {
  const box = await page.locator(selector).first().boundingBox();
  if (!box) throw new Error(`No visible target for ${selector}`);
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await page.waitForTimeout(100);
}

async function inspectCase(page, testCase) {
  await page.evaluate((index) => window.setSlide(index), testCase.slideIndex);
  await page.waitForTimeout(120);
  await clickCenter(page, testCase.layerSelector);
  const grouped = await page.evaluate((rootSelector) => {
    const root = document.querySelector(rootSelector);
    return {
      label: document.querySelector('#edit-selection-badge [data-role=label]')?.textContent?.trim() || '',
      state: root?.dataset.editGroupState || '',
    };
  }, testCase.rootSelector);

  await page.evaluate(() => window.EditMode.ungroup());
  await page.waitForTimeout(100);
  const afterUngroup = await page.evaluate((rootSelector) => {
    const root = document.querySelector(rootSelector);
    const frame = document.getElementById('edit-selection-frame');
    return {
      state: root?.dataset.editGroupState || '',
      mode: frame?.dataset.selectionMode || '',
      memberFrames: Number(frame?.dataset.memberFrameCount || 0),
    };
  }, testCase.rootSelector);

  await clickCenter(page, testCase.layerSelector);
  const samePlaceClick = await page.evaluate(({ rootSelector, layerSelector }) => {
    const root = document.querySelector(rootSelector);
    const layer = document.querySelector(layerSelector);
    const frame = document.getElementById('edit-selection-frame');
    const rootRect = root?.getBoundingClientRect();
    const frameRect = frame?.getBoundingClientRect();
    const frameMatchesRoot = Boolean(rootRect && frameRect
      && Math.abs(rootRect.left - frameRect.left) < 2
      && Math.abs(rootRect.top - frameRect.top) < 2
      && Math.abs(rootRect.width - frameRect.width) < 2
      && Math.abs(rootRect.height - frameRect.height) < 2);
    return {
      label: document.querySelector('#edit-selection-badge [data-role=label]')?.textContent?.trim() || '',
      rootStillUngrouped: root?.dataset.editGroupState === 'ungrouped',
      layerVisible: Boolean(layer && layer.getClientRects().length),
      frameMatchesRoot,
    };
  }, testCase);

  const pass = /^已選取群組/.test(grouped.label)
    && afterUngroup.state === 'ungrouped'
    && afterUngroup.mode === 'single'
    && afterUngroup.memberFrames === 0
    && samePlaceClick.label === testCase.expectedLabel
    && samePlaceClick.rootStillUngrouped
    && samePlaceClick.layerVisible
    && !samePlaceClick.frameMatchesRoot;
  return { ...testCase, grouped, afterUngroup, samePlaceClick, pass };
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
    const cases = [
      {
        id: 'route-map-main-text',
        slideIndex: 8,
        rootSelector: '.slide.active .scene-content[data-edit-composite]',
        layerSelector: '.slide.active .flow-label[data-edit-layer=text]',
        expectedLabel: '已選取文字',
      },
      {
        id: 'route-service-blueprint-cell',
        slideIndex: 4,
        rootSelector: '.slide.active .scene-content[data-edit-composite]',
        layerSelector: '.slide.active .ledger-cell[data-edit-layer=text]',
        expectedLabel: '已選取文字',
      },
    ];
    const results = [];
    for (const testCase of cases) results.push(await inspectCase(page, testCase));
    const report = { url: options.url, results, pass: results.every((item) => item.pass) };
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
