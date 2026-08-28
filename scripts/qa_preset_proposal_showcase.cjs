const fs = require('node:fs/promises');
const fsSync = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

function argsOf(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--url') out.url = argv[++i];
    else if (argv[i] === '--report') out.report = argv[++i];
    else if (argv[i] === '--screenshots') out.screenshots = argv[++i];
  }
  if (!out.url || !out.report || !out.screenshots) throw new Error('missing args');
  return out;
}

async function main() {
  const options = argsOf(process.argv);
  const candidates = [
    process.env.BROWSER_EXECUTABLE,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  ].filter(Boolean);
  const executablePath = candidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1800, height: 1100 }, deviceScaleFactor: 1 });
  try {
    await page.goto(options.url, { waitUntil: 'networkidle', timeout: 120000 });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(300);
    await fs.mkdir(path.resolve(options.screenshots), { recursive: true });
    const result = await page.evaluate(() => {
      const presets = [...document.querySelectorAll('.preset')];
      const previews = [...document.querySelectorAll('.preview')];
      const textNodes = [...document.querySelectorAll('.canvas h1,.canvas h2,.canvas h3,.canvas p,.canvas b,.canvas span,.canvas strong')]
        .filter((node) => (node.textContent || '').trim());
      const belowFloor = textNodes.map((node) => ({
        text: (node.textContent || '').trim().slice(0, 32),
        size: parseFloat(getComputedStyle(node).fontSize),
      })).filter((row) => row.size < 36);
      const pairCounts = presets.map((preset) => preset.querySelectorAll('.preview').length);
      const scaled = previews.every((preview) => {
        const canvas = preview.querySelector('.canvas');
        const previewRect = preview.getBoundingClientRect();
        const canvasRect = canvas.getBoundingClientRect();
        return Math.abs(previewRect.width - canvasRect.width) < 1
          && Math.abs(previewRect.height - canvasRect.height) < 1;
      });
      return { presetCount: presets.length, previewCount: previews.length, pairCounts, belowFloor, scaled };
    });
    const presetLocators = page.locator('.preset');
    for (let i = 0; i < 10; i += 1) {
      await presetLocators.nth(i).screenshot({ path: path.resolve(options.screenshots, `preset-${String(i + 1).padStart(2, '0')}.png`) });
    }
    await page.locator('.preview').first().click();
    const viewerOpen = await page.locator('.viewer.open').count() === 1;
    const firstCounter = await page.locator('.viewer .counter').textContent();
    await page.keyboard.press('ArrowRight');
    const secondCounter = await page.locator('.viewer .counter').textContent();
    await page.keyboard.press('Escape');
    const viewerClosed = await page.locator('.viewer.open').count() === 0;
    result.checks = {
      tenPresets: result.presetCount === 10,
      twoPagesEach: result.previewCount === 20 && result.pairCounts.every((count) => count === 2),
      minimumSlideFont36: result.belowFloor.length === 0,
      previewsScaleToFrame: result.scaled,
      viewerOpen,
      viewerNavigation: /封面/.test(firstCounter || '') && /內容頁/.test(secondCounter || ''),
      escapeClosesViewer: viewerClosed,
    };
    result.pass = Object.values(result.checks).every(Boolean);
    result.url = options.url;
    await fs.mkdir(path.dirname(path.resolve(options.report)), { recursive: true });
    await fs.writeFile(path.resolve(options.report), JSON.stringify(result, null, 2) + '\n', 'utf8');
    console.log(JSON.stringify(result));
    if (!result.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error); process.exit(1); });
