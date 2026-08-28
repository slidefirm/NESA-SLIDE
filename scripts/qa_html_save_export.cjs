const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--url") out.url = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
  }
  if (!out.url || !out.report) throw new Error("--url and --report are required");
  return out;
}

function hasPersistedEditorChrome(markup) {
  const staticMarkup = String(markup || "").replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "");
  return /id=["']edit-(?:insert-panel|save-menu|slide-style-panel)["']|<input\b[^>]*type=["']file["'][^>]*data-editor-chrome=["']true["']/i.test(staticMarkup);
}

async function main() {
  const options = argsOf(process.argv);
  const candidates = [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  const executablePath = candidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath, acceptDownloads: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  try {
    const parsedUrl = new URL(options.url);
    const localServerMode = ["http:", "https:"].includes(parsedUrl.protocol)
      && ["127.0.0.1", "localhost"].includes(parsedUrl.hostname);
    const pickerMode = !localServerMode;
    if (localServerMode) {
      // The bound server-save path remains native. This QA's export assertion
      // specifically covers the documented browser-download fallback, so do
      // not let Chromium's File System Access picker consume a non-gesture
      // page.evaluate export call and leave the download waiter unresolved.
      await page.addInitScript(() => {
        Object.defineProperty(window, "showSaveFilePicker", {
          value: undefined,
          writable: false,
          configurable: true,
        });
        window.__qaBrowserDownloadExportHarness = true;
      });
    }
    if (pickerMode) {
      await page.addInitScript(() => {
        window.__qaSavedHtml = "";
        window.showSaveFilePicker = async () => ({
          name: "composition-first-html-qa-20260723.html",
          createWritable: async () => ({
            write: async (payload) => {
              window.__qaSavedHtml = typeof payload === "string" ? payload : await payload.text();
            },
            close: async () => {},
          }),
        });
      });
    }
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(options.url, { waitUntil: "commit", timeout: 120000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
    ), null, { timeout: 120000 });
    console.error("[qa-save-export] framework-ready");
    const exportDownloadHarness = localServerMode
      ? await page.evaluate(() => ({
        forcedBrowserDownload: window.__qaBrowserDownloadExportHarness === true,
        pickerUnavailable: typeof window.showSaveFilePicker === "undefined",
        pass: window.__qaBrowserDownloadExportHarness === true
          && typeof window.showSaveFilePicker === "undefined",
      }))
      : { filePickerStub: true, pass: true };
    if (!exportDownloadHarness.pass) {
      throw new Error("Save/export QA did not force the browser-download fallback");
    }
    if (pickerMode) {
      await page.evaluate(() => {
        window.__qaSavedHtml = "";
        window.showSaveFilePicker = async () => ({
          name: "composition-first-html-qa-20260723.html",
          createWritable: async () => ({
            write: async (payload) => {
              window.__qaSavedHtml = typeof payload === "string" ? payload : await payload.text();
            },
            close: async () => {},
          }),
        });
      });
    }

    const marker = `SAVE-EXPORT-QA-${Date.now()}`;
    await page.evaluate((value) => {
      const target = document.querySelector('#stage > .slide.active [data-edit-fit="text"],#stage > .slide.active .el');
      if (!target) throw new Error("No editable target found");
      target.innerHTML += ` ${value}`;
      target.dataset.manualFontQa = "true";
      target.style.setProperty("font-size", "20px", "important");
      target.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: value }));
    }, marker);
    await page.evaluate(() => window.SlidePlayer?.setRailCollapsed(true));

    const saveControl = page.locator('button[data-save-binding-state]');
    const saveControlCount = await saveControl.count();
    const saveControlBefore = saveControlCount === 1
      ? await saveControl.evaluate((button) => ({
        label: button.textContent.trim(),
        state: button.dataset.saveBindingState,
        method: button.dataset.saveBindingMethod,
      }))
      : null;

    const saveResponsePromise = localServerMode
      ? page.waitForResponse((response) => response.url().endsWith("/__save"))
      : null;
    await saveControl.click();
    const saveResponse = localServerMode ? await saveResponsePromise : null;
    if (pickerMode) {
      await page.waitForFunction((value) => window.__qaSavedHtml.includes(value), marker, { timeout: 30000 });
    }
    console.error("[qa-save-export] save-response", saveResponse?.status() || "file-picker");
    await page.waitForTimeout(250);
    const saveControlAfter = await saveControl.evaluate((button) => ({
      label: button.textContent.trim(),
      state: button.dataset.saveBindingState,
      method: button.dataset.saveBindingMethod,
    }));
    const saveStatus = await page.locator("#edit-action-status").textContent();
    const savedHtml = pickerMode
      ? await page.evaluate(() => window.__qaSavedHtml)
      : await (await page.request.get(options.url, { headers: { "Cache-Control": "no-cache" } })).text();
    console.error("[qa-save-export] saved-file-read");

    const saveMenuToggle = page.locator("#edit-save-menu-toggle");
    if (await saveMenuToggle.count()) {
      await saveMenuToggle.click();
      await page.waitForFunction(
        () => getComputedStyle(document.getElementById("edit-save-menu")).display !== "none",
        null,
        { timeout: 30000 },
      );
    }
    const saveAsButton = page.getByRole("menuitem", { name: /另存新檔 HTML|HTML/ }).first();
    let exportedHtml = "";
    let suggestedFilename = "";
    if (pickerMode) {
      await page.evaluate(() => { window.__qaSavedHtml = ""; });
      if (await saveAsButton.count()) await saveAsButton.click();
      else await page.getByRole("button", { name: /HTML/ }).click();
      await page.waitForFunction(() => window.__qaSavedHtml.length > 0, null, { timeout: 30000 });
      exportedHtml = await page.evaluate(() => window.__qaSavedHtml);
      suggestedFilename = "file-picker.html";
      console.error("[qa-save-export] file-picker-read");
    } else {
      const downloadPromise = page.waitForEvent("download");
      if (await saveAsButton.count()) await saveAsButton.click();
      else await page.getByRole("button", { name: /HTML/ }).click();
      const download = await downloadPromise;
      suggestedFilename = download.suggestedFilename();
      console.error("[qa-save-export] download-started", suggestedFilename);
      await page.waitForTimeout(50);
      const stream = await download.createReadStream();
      const chunks = [];
      for await (const chunk of stream) chunks.push(chunk);
      exportedHtml = Buffer.concat(chunks).toString("utf8");
      console.error("[qa-save-export] download-read");
    }
    await page.waitForTimeout(50);
    const exportStatus = await page.locator("#edit-action-status").textContent();

    const result = {
      url: options.url,
      saveStatusCode: saveResponse?.status() || "file-picker",
      saveStatus,
      saveControlBefore,
      saveControlAfter,
      exportStatus,
      suggestedFilename,
      exportDownloadHarness,
      checks: {
        oneSharedSaveButton: saveControlCount === 1,
        initialSaveStateMatchesEnvironment: localServerMode
          ? saveControlBefore?.state === "bound" && saveControlBefore?.label === "儲存進度"
          : saveControlBefore?.state === "unbound" && saveControlBefore?.label === "開始存檔",
        saveButtonBecomesProgress: saveControlAfter.state === "bound"
          && saveControlAfter.label === "儲存進度",
        saveRequestSucceeded: pickerMode ? savedHtml.length > 0 : saveResponse.ok(),
        savedFileContainsEdit: savedHtml.includes(marker),
        savedManualFontBelowFloor: savedHtml.includes('data-manual-font-qa="true"')
          && /font-size:\s*20px/i.test(savedHtml)
          && savedHtml.includes('data-ai-font-floor-applied="true"'),
        savedRailDefaultsExpanded: !/<div\s+id="player"[^>]*class="[^"]*\brail-collapsed\b/i.test(savedHtml),
        saveFeedbackVisible: /已存檔|已儲存|已覆寫|Saved/i.test(saveStatus || ""),
        savedEditorChromeExcluded: !hasPersistedEditorChrome(savedHtml),
        exportDownloadFallbackForced: exportDownloadHarness.pass,
        exportDownloaded: exportedHtml.length > 0 && (pickerMode || /\.html$/i.test(suggestedFilename)),
        exportedFileContainsEdit: exportedHtml.includes(marker),
        exportedManualFontBelowFloor: exportedHtml.includes('data-manual-font-qa="true"')
          && /font-size:\s*20px/i.test(exportedHtml)
          && exportedHtml.includes('data-ai-font-floor-applied="true"'),
        exportedRailDefaultsExpanded: !/<div\s+id="player"[^>]*class="[^"]*\brail-collapsed\b/i.test(exportedHtml),
        exportedEditorChromeExcluded: !hasPersistedEditorChrome(exportedHtml),
        exportFeedbackNonEmpty: String(exportStatus || "").trim().length > 0,
        exportFeedbackVisible: /已匯出|已(?:下載)?另存|Exported/i.test(exportStatus || ""),
      },
    };
    result.pass = Object.values(result.checks).every(Boolean);
    await fs.mkdir(path.dirname(path.resolve(options.report)), { recursive: true });
    await fs.writeFile(path.resolve(options.report), JSON.stringify(result, null, 2) + "\n", "utf8");
    console.log(JSON.stringify(result));
    if (!result.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
