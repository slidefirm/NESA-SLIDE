const fs = require('node:fs/promises');
const fsSync = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

function argsOf(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--url') out.url = argv[++i];
    else if (argv[i] === '--file') out.file = argv[++i];
    else if (argv[i] === '--report') out.report = argv[++i];
  }
  if (!out.url || !out.file || !out.report) throw new Error('missing args');
  return out;
}

function serveRootFor(sourcePath, sourceUrl) {
  const relativeParts = decodeURIComponent(new URL(sourceUrl).pathname)
    .replace(/^\/+/, '')
    .split('/')
    .filter(Boolean);
  let candidate = sourcePath;
  for (const _part of relativeParts) candidate = path.dirname(candidate);
  const reconstructed = path.resolve(candidate, ...relativeParts);
  if (reconstructed.toLowerCase() !== sourcePath.toLowerCase()) {
    throw new Error('URL path does not match --file inside the served directory');
  }
  return candidate;
}

async function main() {
  const options = argsOf(process.argv);
  const candidates = [
    process.env.BROWSER_EXECUTABLE,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  ].filter(Boolean);
  const executablePath = candidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath, acceptDownloads: true });
  const sourcePath = path.resolve(options.file);
  const sourceHtml = await fs.readFile(sourcePath, 'utf8');
  const qaFileName = `.direct-save-qa-${process.pid}-${Date.now()}.html`;
  const qaFilePath = path.join(path.dirname(sourcePath), qaFileName);
  const serveRoot = serveRootFor(sourcePath, options.url);
  const historyRoot = path.join(serveRoot, '.history');
  const qaHistoryPath = path.join(historyRoot, qaFileName);
  const qaUrl = new URL(options.url);
  qaUrl.pathname = qaUrl.pathname.replace(/[^/]*$/, encodeURIComponent(qaFileName));
  qaUrl.search = '';
  await fs.writeFile(qaFilePath, sourceHtml, 'utf8');
  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
    await page.route('https://fonts.googleapis.com/**', (route) => route.abort());
    await page.route('https://fonts.gstatic.com/**', (route) => route.abort());
    await page.goto(qaUrl.href, { waitUntil: 'commit', timeout: 120000 });
    await page.waitForFunction(() => Boolean(window.EditMode), null, { timeout: 120000 });
    await page.waitForFunction(() => document.querySelector('button[data-save-binding-state]')?.dataset.saveBindingState === 'bound');
    const serverSaveButtonBefore = await page.locator('button[data-save-binding-state]').evaluate((button) => ({
      label: button.textContent.trim(),
      state: button.dataset.saveBindingState,
      method: button.dataset.saveBindingMethod,
      background: getComputedStyle(button).backgroundColor,
      color: getComputedStyle(button).color,
    }));
    const marker = `DIRECT-OVERWRITE-QA-${Date.now()}`;
    await page.evaluate((value) => {
      const target = document.querySelector('#stage .slide.active [data-edit-layer="text"],#stage .slide.active .el');
      const root = target?.closest('.el');
      if (!target || !root) throw new Error('editable target missing');
      const fireClick = (el) => {
        ['mousedown', 'mouseup', 'click'].forEach((type) => el.dispatchEvent(new MouseEvent(type, {
          bubbles: true, clientX: 360, clientY: 240, button: 0,
        })));
      };
      fireClick(root);
      fireClick(target);
      fireClick(target);
      target.innerHTML += ` ${value}`;
      target.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: value }));
    }, marker);
    const responsePromise = page.waitForResponse((response) => response.url().endsWith('/__save'));
    const saveResultPromise = page.evaluate(() => window.EditMode.save());
    const response = await responsePromise;
    const saveResult = await saveResultPromise;
    const serverSaveButtonAfter = await page.locator('button[data-save-binding-state]').evaluate((button) => ({
      label: button.textContent.trim(),
      state: button.dataset.saveBindingState,
      method: button.dataset.saveBindingMethod,
    }));
    const savedHtml = await fs.readFile(qaFilePath, 'utf8');
    const statusText = await page.locator('#edit-action-status').textContent();
    await page.waitForTimeout(1800);
    const postSaveDraftKey = await page.evaluate(() => window.EditMode.diagnostics().draftKey);
    const draftRecreatedAfterSave = await page.evaluate((key) => localStorage.getItem(key) !== null, postSaveDraftKey);
    await page.reload({ waitUntil: 'load' });
    await page.waitForFunction(() => Boolean(window.EditMode), null, { timeout: 120000 });
    const draftPromptAfterSave = await page.locator('#edit-draft-prompt').count() === 1;

    await page.evaluate(() => {
      window.__qaPickerCalls = 0;
      window.__qaPickerSuggestedName = '';
      window.__qaPickerWrites = [];
      window.showSaveFilePicker = async (options) => {
        window.__qaPickerCalls += 1;
        window.__qaPickerSuggestedName = options?.suggestedName || '';
        return {
          name: window.__qaPickerSuggestedName,
          createWritable: async () => ({
            write: async (html) => { window.__qaPickerWrites.push(html); },
            close: async () => {},
          }),
        };
      };
    });
    await page.route('**/__save', (route) => route.fulfill({ status: 500, contentType: 'application/json', body: '{"error":"forced failure"}' }));
    const fallbackResult = await page.evaluate(() => window.EditMode.save());
    const fallbackSaveButton = await page.locator('button[data-save-binding-state]').evaluate((button) => ({
      label: button.textContent.trim(),
      state: button.dataset.saveBindingState,
      method: button.dataset.saveBindingMethod,
    }));
    const pickerState = await page.evaluate(() => ({
      calls: window.__qaPickerCalls,
      suggestedName: window.__qaPickerSuggestedName,
      writes: window.__qaPickerWrites,
    }));
    const fallbackStatus = await page.locator('#edit-action-status').textContent();

    const pickerPage = await browser.newPage({ viewport: { width: 1600, height: 900 } });
    await pickerPage.route('https://fonts.googleapis.com/**', (route) => route.abort());
    await pickerPage.route('https://fonts.gstatic.com/**', (route) => route.abort());
    await pickerPage.setContent(savedHtml, { waitUntil: 'load' });
    await pickerPage.waitForFunction(() => Boolean(window.EditMode), null, { timeout: 120000 });
    await pickerPage.evaluate(() => {
      window.__qaNoServerPickerCalls = 0;
      window.__qaNoServerWrites = [];
      window.showSaveFilePicker = async (options) => {
        window.__qaNoServerPickerCalls += 1;
        return {
          name: options?.suggestedName || 'presentation.html',
          createWritable: async () => ({
            write: async (html) => { window.__qaNoServerWrites.push(html); },
            close: async () => {},
          }),
        };
      };
    });
    await pickerPage.waitForFunction(() => document.querySelector('button[data-save-binding-state]')?.dataset.saveBindingState === 'unbound');
    const pickerSaveButtonBefore = await pickerPage.locator('button[data-save-binding-state]').evaluate((button) => ({
      label: button.textContent.trim(),
      state: button.dataset.saveBindingState,
      background: getComputedStyle(button).backgroundColor,
      color: getComputedStyle(button).color,
    }));
    const noServerResult = await pickerPage.evaluate(() => window.EditMode.save());
    const pickerSaveButtonAfter = await pickerPage.locator('button[data-save-binding-state]').evaluate((button) => ({
      label: button.textContent.trim(),
      state: button.dataset.saveBindingState,
      method: button.dataset.saveBindingMethod,
      background: getComputedStyle(button).backgroundColor,
      color: getComputedStyle(button).color,
    }));
    const noServerState = await pickerPage.evaluate(() => ({
      calls: window.__qaNoServerPickerCalls,
      writes: window.__qaNoServerWrites,
    }));
    await pickerPage.close();

    const downloadPage = await browser.newPage({ viewport: { width: 1600, height: 900 } });
    await downloadPage.route('https://fonts.googleapis.com/**', (route) => route.abort());
    await downloadPage.route('https://fonts.gstatic.com/**', (route) => route.abort());
    await downloadPage.setContent(savedHtml, { waitUntil: 'load' });
    await downloadPage.waitForFunction(() => Boolean(window.EditMode), null, { timeout: 120000 });
    await downloadPage.evaluate(() => {
      window.showSaveFilePicker = undefined;
      window.__qaDownloadClicks = [];
      HTMLAnchorElement.prototype.click = function () {
        window.__qaDownloadClicks.push({ download: this.download, href: this.href });
      };
    });
    const browserSaveAsResult = await downloadPage.evaluate(() => window.EditMode.save());
    const unsupportedSaveButton = await downloadPage.locator('button[data-save-binding-state]').evaluate((button) => ({
      label: button.textContent.trim(),
      state: button.dataset.saveBindingState,
    }));
    const browserSaveAsState = await downloadPage.evaluate(() => window.__qaDownloadClicks);
    await downloadPage.close();

    const previewPage = await browser.newPage({ viewport: { width: 1600, height: 900 } });
    let previewSaveRequests = 0;
    await previewPage.route('https://fonts.googleapis.com/**', (route) => route.abort());
    await previewPage.route('https://fonts.gstatic.com/**', (route) => route.abort());
    await previewPage.route('**/__save', (route) => {
      previewSaveRequests += 1;
      return route.fulfill({ status: 500, contentType: 'application/json', body: '{"error":"preview must not save"}' });
    });
    const previewUrl = new URL(qaUrl.href);
    previewUrl.searchParams.set('preview', '1');
    const previewFileBefore = await fs.readFile(qaFilePath, 'utf8');
    await previewPage.goto(previewUrl.href, { waitUntil: 'load', timeout: 120000 });
    await previewPage.waitForFunction(() => Boolean(window.EditMode), null, { timeout: 120000 });
    await previewPage.waitForFunction(
      () => document.querySelector('button[data-save-binding-method]')?.dataset.saveBindingMethod === 'read-only-preview',
    );
    const previewSaveButton = await previewPage.locator('button[data-save-binding-state]').evaluate((button) => ({
      label: button.textContent.trim(),
      state: button.dataset.saveBindingState,
      method: button.dataset.saveBindingMethod,
      ariaDisabled: button.getAttribute('aria-disabled'),
    }));
    const previewSaveResult = await previewPage.evaluate(() => window.EditMode.save());
    const previewStatus = await previewPage.locator('#edit-action-status').textContent();
    const previewFileAfter = await fs.readFile(qaFilePath, 'utf8');
    await previewPage.close();

    const expectedPath = decodeURIComponent(qaUrl.pathname).replace(/^\/+/, '');
    const sourceArtifactAfter = await fs.readFile(sourcePath, 'utf8');
    const result = {
      sourceUrl: options.url,
      url: qaUrl.href,
      expectedPath,
      saveResult,
      fallbackResult,
      noServerResult,
      previewSaveResult,
      saveButtons: {
        serverBefore: serverSaveButtonBefore,
        serverAfter: serverSaveButtonAfter,
        fallback: fallbackSaveButton,
        pickerBefore: pickerSaveButtonBefore,
        pickerAfter: pickerSaveButtonAfter,
        unsupported: unsupportedSaveButton,
        preview: previewSaveButton,
      },
      statusText,
      fallbackStatus,
      previewStatus,
      checks: {
        serverStartsBound: serverSaveButtonBefore.state === 'bound'
          && serverSaveButtonBefore.label === '儲存進度'
          && serverSaveButtonBefore.method === 'dev-server',
        serverStaysBoundAfterSave: serverSaveButtonAfter.state === 'bound'
          && serverSaveButtonAfter.label === '儲存進度',
        saveRequestSucceeded: response.ok(),
        currentFileOverwritten: savedHtml.includes(marker),
        exactUrlPathUsed: saveResult.path === expectedPath,
        methodIsOverwrite: saveResult.saved === true && saveResult.method === 'overwrite',
        overwriteFeedbackVisible: (statusText || '').includes('已覆寫目前 HTML'),
        draftNotRecreatedAfterSave: !draftRecreatedAfterSave,
        noDraftPromptAfterSave: !draftPromptAfterSave,
        serverFailureFallsBackToPicker: fallbackResult.saved === true && fallbackResult.method === 'file-picker',
        serverFailureOpensPicker: pickerState.calls === 1,
        pickerSuggestsCurrentFile: pickerState.suggestedName === path.basename(expectedPath),
        pickerWritesFullHtml: pickerState.writes.length === 1 && pickerState.writes[0].includes('<!DOCTYPE html>'),
        fallbackFeedbackVisible: (fallbackStatus || '').includes('已儲存 HTML 檔案'),
        fallbackPickerEndsBound: fallbackSaveButton.state === 'bound'
          && fallbackSaveButton.label === '儲存進度',
        staticStartsUnbound: pickerSaveButtonBefore.state === 'unbound'
          && pickerSaveButtonBefore.label === '開始存檔',
        unboundUsesWarningTone: pickerSaveButtonBefore.background.includes('245, 158, 11')
          && pickerSaveButtonBefore.color.includes('255, 208, 138'),
        noServerUsesFilePicker: noServerResult.saved === true && noServerResult.method === 'file-picker',
        noServerOpensPicker: noServerState.calls === 1,
        noServerWritesFullHtml: noServerState.writes.length === 1 && noServerState.writes[0].includes('<!DOCTYPE html>'),
        staticBecomesBoundAfterPicker: pickerSaveButtonAfter.state === 'bound'
          && pickerSaveButtonAfter.label === '儲存進度',
        boundUsesSuccessTone: pickerSaveButtonAfter.background.includes('34, 197, 94')
          && pickerSaveButtonAfter.color.includes('167, 243, 208'),
        bindingVisiblyChangesSameControl: pickerSaveButtonBefore.background !== pickerSaveButtonAfter.background
          && pickerSaveButtonBefore.color !== pickerSaveButtonAfter.color,
        unsupportedPickerUsesBrowserSaveAs: browserSaveAsResult.pending === true && browserSaveAsResult.method === 'browser-save-as',
        unsupportedBrowserStaysUnbound: unsupportedSaveButton.state === 'unbound'
          && unsupportedSaveButton.label === '開始存檔',
        browserSaveAsUsesCurrentName: browserSaveAsState.length === 1 && browserSaveAsState[0].download === 'blank.html',
        browserSaveAsBuildsBlob: browserSaveAsState.length === 1 && browserSaveAsState[0].href.startsWith('blob:'),
        sourceArtifactUnchanged: sourceArtifactAfter === sourceHtml,
        previewStartsReadOnly: previewSaveButton.state === 'unbound'
          && previewSaveButton.label === '開始存檔'
          && previewSaveButton.method === 'read-only-preview'
          && previewSaveButton.ariaDisabled === 'true',
        previewSaveShortCircuits: previewSaveResult.saved === false
          && previewSaveResult.method === 'read-only-preview',
        previewDoesNotRequestServer: previewSaveRequests === 0,
        previewDoesNotModifyFile: previewFileAfter === previewFileBefore,
        previewFeedbackVisible: (previewStatus || '').includes('預覽模式不會修改檔案'),
      },
    };
    result.pass = Object.values(result.checks).every(Boolean);
    await fs.mkdir(path.dirname(path.resolve(options.report)), { recursive: true });
    await fs.writeFile(path.resolve(options.report), JSON.stringify(result, null, 2) + '\n', 'utf8');
    console.log(JSON.stringify(result));
    if (!result.pass) process.exitCode = 1;
  } finally {
    try {
      await browser.close();
    } finally {
      await fs.rm(qaFilePath, { force: true });
      await fs.rm(qaHistoryPath, { recursive: true, force: true });
      try {
        await fs.rmdir(historyRoot);
      } catch (error) {
        if (!['ENOENT', 'ENOTEMPTY'].includes(error?.code)) throw error;
      }
    }
  }
}

main().catch((error) => { console.error(error); process.exit(1); });
