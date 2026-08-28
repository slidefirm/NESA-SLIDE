const fs = require('node:fs/promises');
const fsSync = require('node:fs');
const { chromium } = require('playwright');

function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--url') out.url = argv[++i];
    else if (argv[i] === '--report') out.report = argv[++i];
  }
  if (!out.url || !out.report) throw new Error('--url and --report are required');
  return out;
}

function browserExecutable() {
  return [
    process.env.BROWSER_EXECUTABLE,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
  ].filter(Boolean).find(fsSync.existsSync);
}

async function ready(page, url, slide) {
  await page.addInitScript(() => localStorage.clear());
  await page.route('https://fonts.googleapis.com/**', route => route.abort());
  await page.route('https://fonts.gstatic.com/**', route => route.abort());
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForFunction(() => document.documentElement.dataset.layoutReady === 'true' && window.EditMode, null, { timeout: 120000 });
  await page.evaluate(async index => {
    window.setSlide(index);
    if (!document.documentElement.classList.contains('edit-mode')) window.EditMode.toggle(true);
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }, slide);
}

async function clickBlank(page, selector, xRatio, yRatio) {
  const box = await page.locator(selector).first().boundingBox();
  if (!box) throw new Error(`missing ${selector}`);
  await page.mouse.click(box.x + box.width * xRatio, box.y + box.height * yRatio);
  await page.waitForTimeout(120);
}

async function clearSelection(page) {
  await page.evaluate(() => window.EditMode.deselect());
  await page.waitForTimeout(80);
}

async function selectedState(page, backgroundSelector) {
  return page.evaluate(selector => {
    const frame = document.getElementById('edit-selection-frame');
    const bg = document.querySelector(selector);
    const rect = node => {
      const r = node.getBoundingClientRect();
      return { left:r.left, top:r.top, width:r.width, height:r.height };
    };
    const style = bg ? getComputedStyle(bg) : null;
    return {
      label: document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent?.trim() || '',
      mode: frame?.dataset.selectionMode || '',
      frame: frame ? rect(frame) : null,
      background: bg ? rect(bg) : null,
      fill: style?.backgroundColor || '',
      borderTop: style?.borderTopWidth || '',
      shadow: style?.boxShadow || ''
    };
  }, backgroundSelector);
}

const near = (a, b, tolerance = 4) => Math.abs(a - b) <= tolerance;
function selectedRealBackground(state) {
  return state.label.includes('背景')
    && state.background && state.background.width > 40 && state.background.height > 40
    && near(state.frame.left, state.background.left)
    && near(state.frame.top, state.background.top)
    && near(state.frame.width, state.background.width)
    && near(state.frame.height, state.background.height)
    && state.fill !== 'rgba(0, 0, 0, 0)';
}

async function thesisBackgroundCase(browser, options) {
  const page = await browser.newPage({ viewport:{ width:1800, height:1000 } });
  try {
    await ready(page, options.url, 1);
    await clickBlank(page, '.slide.active .thesis-note', .88, .78);
    await page.evaluate(() => window.EditMode.ungroup());
    await page.waitForTimeout(120);
    await clearSelection(page);
    await clickBlank(page, '.slide.active .thesis-note', .88, .78);
    await page.evaluate(() => window.EditMode.ungroup());
    await page.waitForTimeout(120);
    await clearSelection(page);
    await clickBlank(page, '.slide.active .thesis-note', .88, .78);
    const state = await selectedState(page, '.slide.active .thesis-note .thesis-note-bg');
    return { pass:selectedRealBackground(state), state };
  } finally { await page.close(); }
}

async function ledgerBackgroundCase(browser, options) {
  const page = await browser.newPage({ viewport:{ width:1800, height:1000 } });
  try {
    await ready(page, options.url, 8);
    await clickBlank(page, '.slide.active .ledger-row', .5, .5);
    await page.evaluate(() => window.EditMode.ungroup());
    await page.waitForTimeout(120);
    await clearSelection(page);
    const sheet = await page.locator('.slide.active .ledger-sheet-bg').boundingBox();
    const header = await page.locator('.slide.active .ledger-header').boundingBox();
    if (!sheet || !header) throw new Error('ledger sheet/header missing');
    const exposedTop = Math.max(1, (header.y - sheet.y) / 2);
    await page.mouse.click(sheet.x + sheet.width / 2, sheet.y + exposedTop);
    await page.waitForTimeout(120);
    const state = await selectedState(page, '.slide.active .ledger-sheet-bg');
    return { pass:selectedRealBackground(state), state };
  } finally { await page.close(); }
}

async function groupTextCase(browser, options) {
  const page = await browser.newPage({ viewport:{ width:1800, height:1000 } });
  try {
    await ready(page, options.url, 8);
    await clickBlank(page, '.slide.active .scene-footer', .5, .5);
    const before = await page.evaluate(() => {
      const root = document.querySelector('.slide.active .scene-content');
      const nodes = [...root.querySelectorAll('[data-edit-layer="text"],[data-edit-layer="metric"]')]
        .filter(node => getComputedStyle(node).display !== 'none' && node.getClientRects().length);
      return {
        mode: document.getElementById('edit-selection-frame')?.dataset.selectionMode || '',
        values: nodes.map(node => ({ cls:node.className, size:parseFloat(getComputedStyle(node).fontSize) }))
      };
    });
    await page.keyboard.press(']');
    await page.waitForTimeout(180);
    const after = await page.evaluate(() => [...document.querySelectorAll('.slide.active .scene-content [data-edit-layer="text"],.slide.active .scene-content [data-edit-layer="metric"]')]
      .filter(node => getComputedStyle(node).display !== 'none' && node.getClientRects().length)
      .map(node => ({ cls:node.className, size:parseFloat(getComputedStyle(node).fontSize) })));
    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(150);
    const undone = await page.evaluate(() => [...document.querySelectorAll('.slide.active .scene-content [data-edit-layer="text"],.slide.active .scene-content [data-edit-layer="metric"]')]
      .filter(node => getComputedStyle(node).display !== 'none' && node.getClientRects().length)
      .map(node => parseFloat(getComputedStyle(node).fontSize)));
    await page.evaluate(() => window.EditMode.redo());
    await page.waitForTimeout(150);
    const redone = await page.evaluate(() => [...document.querySelectorAll('.slide.active .scene-content [data-edit-layer="text"],.slide.active .scene-content [data-edit-layer="metric"]')]
      .filter(node => getComputedStyle(node).display !== 'none' && node.getClientRects().length)
      .map(node => parseFloat(getComputedStyle(node).fontSize)));
    const footerIndex = before.values.findIndex(item => String(item.cls).includes('scene-footer'));
    const everyTextChanged = before.values.length === after.length && before.values.every((item, index) => near(after[index].size, item.size + 1, .25));
    const footerChanged = footerIndex >= 0 && near(after[footerIndex].size, before.values[footerIndex].size + 1, .25);
    const undoRestored = before.values.every((item, index) => near(undone[index], item.size, .25));
    const redoRestored = after.every((item, index) => near(redone[index], item.size, .25));
    const checks = { selectedAsGroup:before.mode === 'group', everyGroupTextChanged:everyTextChanged, groupedFooterChanged:footerChanged, undoRestoresAllText:undoRestored, redoReappliesAllText:redoRestored };
    return { pass:Object.values(checks).every(Boolean), checks, before, after };
  } finally { await page.close(); }
}

async function main() {
  const options = parseArgs(process.argv);
  const browser = await chromium.launch({ headless:true, executablePath:browserExecutable() });
  try {
    const report = {
      thesisBackground: await thesisBackgroundCase(browser, options),
      ledgerBackground: await ledgerBackgroundCase(browser, options),
      groupText: await groupTextCase(browser, options)
    };
    report.pass = Object.values(report).filter(value => value && typeof value === 'object' && 'pass' in value).every(value => value.pass);
    await fs.mkdir(require('node:path').dirname(options.report), { recursive:true });
    await fs.writeFile(options.report, JSON.stringify(report, null, 2) + '\n', 'utf8');
    console.log(JSON.stringify({ pass:report.pass, report:options.report }, null, 2));
    if (!report.pass) process.exitCode = 1;
  } finally { await browser.close(); }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
