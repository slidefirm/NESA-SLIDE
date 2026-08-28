const fs = require('node:fs/promises');
const fsSync = require('node:fs');
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

function assert(checks, id, value) {
  checks[id] = Boolean(value);
}

async function main() {
  const options = argsOf(process.argv);
  const browserCandidates = [
    process.env.BROWSER_EXECUTABLE,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  ].filter(Boolean);
  const executablePath = browserCandidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  // This QA exercises the browser-download export fallback. File System
  // Access is covered by file-binding/direct-overwrite harnesses instead.
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
  const checks = {};
  const evidence = {};
  try {
    await page.goto(options.url, { waitUntil: 'commit', timeout: 120000 });
    await page.waitForFunction(() => Boolean(window.EditMode), null, { timeout: 120000 });
    await page.evaluate(() => {
      const key = window.EditMode.diagnostics().draftKey;
      localStorage.removeItem(key);
      document.getElementById('edit-draft-prompt')?.remove();
      if (!document.documentElement.classList.contains('edit-mode')) window.EditMode.toggle(true);
    });

    const target = page.locator('#s1 .cover-center-title').first();
    await target.click({ position: { x: 60, y: 30 } });
    await page.waitForTimeout(120);

    evidence.initial = await page.evaluate(() => {
      const target = document.querySelector('#s1 .cover-center-title');
      const styleButton = document.getElementById('edit-slide-style-button');
      const panel = document.getElementById('edit-slide-style-panel');
      const backgroundTools = document.getElementById('edit-text-background-tools');
      const bar = document.getElementById('bar');
      const buttonRect = styleButton?.getBoundingClientRect();
      const panelRect = panel?.getBoundingClientRect();
      return {
        targetFound: Boolean(target),
        backgroundToolsFound: Boolean(backgroundTools),
        backgroundInputFound: Boolean(document.getElementById('edit-slide-background-input')),
        toolbarTop: bar?.getBoundingClientRect().top || 0,
        styleButtonRect: buttonRect ? { left: buttonRect.left, bottom: buttonRect.bottom } : null,
        panelRect: panelRect ? { left: panelRect.left, top: panelRect.top, width: panelRect.width } : null,
      };
    });
    assert(checks, 'textBoxBackgroundControlExists', evidence.initial.backgroundToolsFound);
    assert(checks, 'slideBackgroundControlRemoved', !evidence.initial.backgroundInputFound);

    await page.click('#edit-slide-style-button');
    await page.waitForFunction(() => getComputedStyle(document.getElementById('edit-slide-style-panel')).display !== 'none');
    evidence.dropdown = await page.evaluate(() => {
      const button = document.getElementById('edit-slide-style-button').getBoundingClientRect();
      const panel = document.getElementById('edit-slide-style-panel').getBoundingClientRect();
      return { button, panel, ariaExpanded: document.getElementById('edit-slide-style-button').getAttribute('aria-expanded') };
    });
    assert(checks, 'stylePanelOpensAsDropdown', evidence.dropdown.ariaExpanded === 'true');
    assert(checks, 'stylePanelAnchoredBelowToolbar', evidence.dropdown.panel.top >= evidence.dropdown.button.bottom - 2);
    assert(checks, 'stylePanelNearTrigger', Math.abs(evidence.dropdown.panel.left - evidence.dropdown.button.left) < 80);
    await page.click('#edit-slide-style-button');

    const backgroundInput = page.locator('#edit-text-background-tools input[type="color"]').first();
    await backgroundInput.evaluate((input) => {
      input.value = '#315579';
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await page.waitForTimeout(120);
    evidence.applied = await page.evaluate(() => ({
      inline: document.querySelector('#s1 .cover-center-title').style.background,
      computed: getComputedStyle(document.querySelector('#s1 .cover-center-title')).backgroundColor,
    }));
    assert(checks, 'textBoxBackgroundApplied', evidence.applied.computed === 'rgb(49, 85, 121)');

    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(80);
    evidence.undo = await page.evaluate(() => document.querySelector('#s1 .cover-center-title').style.background);
    assert(checks, 'textBoxBackgroundUndo', evidence.undo === '');
    await page.evaluate(() => window.EditMode.redo());
    await page.waitForTimeout(80);
    evidence.redo = await page.evaluate(() => document.querySelector('#s1 .cover-center-title').style.background);
    assert(checks, 'textBoxBackgroundRedo', evidence.redo === 'rgb(49, 85, 121)');

    await page.waitForTimeout(1750);
    evidence.draft = await page.evaluate(() => {
      const key = window.EditMode.diagnostics().draftKey;
      const payload = JSON.parse(localStorage.getItem(key) || 'null');
      return { exists: Boolean(payload), entries: payload?.entries?.length || 0 };
    });
    assert(checks, 'draftSaved', evidence.draft.exists && evidence.draft.entries > 0);

    const downloadPromise = page.waitForEvent('download');
    await page.evaluate(() => window.EditMode.export());
    const exportDownloadHarness = await page.evaluate(() => ({
      forcedBrowserDownload: window.__qaBrowserDownloadExportHarness === true,
      pickerUnavailable: typeof window.showSaveFilePicker === 'undefined',
      pass: window.__qaBrowserDownloadExportHarness === true
        && typeof window.showSaveFilePicker === 'undefined',
    }));
    if (!exportDownloadHarness.pass) {
      throw new Error('Textbox background QA did not force browser-download export fallback');
    }
    const download = await downloadPromise;
    const stream = await download.createReadStream();
    const chunks = [];
    for await (const chunk of stream) chunks.push(chunk);
    const exportedHtml = Buffer.concat(chunks).toString('utf8');
    evidence.export = await page.evaluate((html) => {
      const copy = new DOMParser().parseFromString(html, 'text/html');
      const target = copy.querySelector('#s1 .cover-center-title');
      return {
        editorPanelRemoved: !copy.getElementById('edit-slide-style-panel'),
        background: target?.style.background || '',
        slideBackgroundInputRemoved: !copy.getElementById('edit-slide-background-input'),
      };
    }, exportedHtml);
    assert(checks, 'exportRemovesEditorPanel', evidence.export.editorPanelRemoved);
    assert(checks, 'exportDownloadFallbackForced', exportDownloadHarness.pass);
    assert(checks, 'exportPreservesTextBoxBackground', evidence.export.background === 'rgb(49, 85, 121)');
    assert(checks, 'exportRemovesSlideBackgroundControl', evidence.export.slideBackgroundInputRemoved);

    evidence.exportDownloadHarness = exportDownloadHarness;
    const report = { qa: 'html-textbox-background-dropdown', url: options.url, pass: Object.values(checks).every(Boolean), checks, evidence };
    const reportPath = path.resolve(options.report);
    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
    process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
    if (!report.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});
