const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--url") out.url = argv[++index];
    else if (argv[index] === "--file") out.file = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
  }
  if (!out.url || !out.file || !out.report) {
    throw new Error("--url, --file and --report are required");
  }
  return out;
}

function serveRootFor(sourcePath, sourceUrl) {
  const relativeParts = decodeURIComponent(new URL(sourceUrl).pathname)
    .replace(/^\/+/, "")
    .split("/")
    .filter(Boolean);
  let candidate = sourcePath;
  for (const _part of relativeParts) candidate = path.dirname(candidate);
  const reconstructed = path.resolve(candidate, ...relativeParts);
  if (reconstructed.toLowerCase() !== sourcePath.toLowerCase()) {
    throw new Error("URL path does not match --file inside the served directory");
  }
  return candidate;
}

async function main() {
  const options = argsOf(process.argv);
  const sourcePath = path.resolve(options.file);
  const sourceHtml = await fs.readFile(sourcePath, "utf8");
  const qaFileName = `.autosave-qa-${process.pid}-${Date.now()}.html`;
  const qaFilePath = path.join(path.dirname(sourcePath), qaFileName);
  const serveRoot = serveRootFor(sourcePath, options.url);
  const historyPath = path.join(serveRoot, ".history", qaFileName);
  const qaUrl = new URL(options.url);
  qaUrl.pathname = qaUrl.pathname.replace(/[^/]*$/, encodeURIComponent(qaFileName));
  qaUrl.search = "";
  const candidates = [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  const executablePath = candidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });

  await fs.writeFile(qaFilePath, sourceHtml, "utf8");
  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(qaUrl.href, { waitUntil: "commit", timeout: 120000 });
    await page.waitForFunction(() => Boolean(window.EditMode), null, { timeout: 120000 });
    await page.waitForFunction(
      () => document.querySelector("button[data-save-binding-state]")?.dataset.saveBindingState === "bound",
      null,
      { timeout: 120000 },
    );

    const pickerCalls = await page.evaluate(() => {
      window.__qaPickerCalls = 0;
      window.showSaveFilePicker = async () => {
        window.__qaPickerCalls += 1;
        throw new Error("autosave must not open a file picker");
      };
      return window.__qaPickerCalls;
    });

    const marker = `AUTOSAVE-QA-${Date.now()}`;
    const saveResponsePromise = page.waitForResponse(
      (response) => response.url().endsWith("/__save"),
      { timeout: 30000 },
    );
    const target = page.locator(
      "#stage .slide.active [data-edit-layer=\"text\"],#stage .slide.active [data-edit-kind=\"text\"],#stage .slide.active [data-edit-fit=\"text\"],#stage .slide.active .el:not(.scrim)",
    ).first();
    await target.scrollIntoViewIfNeeded();
    await target.dblclick({ force: true });
    const originalText = await target.innerText();
    await target.fill(`${originalText} ${marker}`);

    const response = await saveResponsePromise;
    await page.waitForFunction(() => {
      const autoSave = window.EditMode?.diagnostics?.().autoSave;
      return autoSave?.state === "saved" && autoSave.pending === false && autoSave.inFlight === false;
    }, null, { timeout: 30000 });

    const savedHtml = await fs.readFile(qaFilePath, "utf8");
    let historyEntries = [];
    try {
      historyEntries = (await fs.readdir(historyPath)).filter((name) => name.endsWith(".html"));
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
    const evidence = await page.evaluate(() => ({
      pickerCalls: window.__qaPickerCalls,
      diagnostics: window.EditMode.diagnostics(),
      saveButton: (() => {
        const button = document.querySelector("button[data-save-binding-state]");
        return button ? {
          autoSaveEnabled: button.dataset.autoSaveEnabled,
          autoSaveState: button.dataset.autoSaveState,
          bindingMethod: button.dataset.saveBindingMethod,
        } : null;
      })(),
      actionStatus: document.querySelector("#edit-action-status")?.textContent || "",
    }));

    const draftKey = evidence.diagnostics.draftKey;
    const draftStillPresent = await page.evaluate((key) => Boolean(localStorage.getItem(key)), draftKey);
    const reportPath = (filePath) => path.relative(process.cwd(), filePath).split(path.sep).join("/");
    const result = {
      url: qaUrl.href,
      sourceFile: reportPath(sourcePath),
      file: reportPath(qaFilePath),
      responseStatus: response.status(),
      marker,
      historyEntries,
      evidence,
      checks: {
        autosaveRequestSucceeded: response.ok(),
        currentFileOverwritten: savedHtml.includes(marker),
        historySnapshotCreated: historyEntries.length >= 1,
        noFilePickerOpened: pickerCalls === 0 && evidence.pickerCalls === 0,
        autosaveEnabledOnDevServer: evidence.saveButton?.autoSaveEnabled === "true",
        autosaveReachedSavedState: evidence.saveButton?.autoSaveState === "saved",
        autosaveFeedbackVisible: /自動存檔|auto/i.test(evidence.actionStatus || ""),
        draftClearedAfterAutosave: !draftStillPresent,
      },
    };
    result.pass = Object.values(result.checks).every(Boolean);
    await fs.mkdir(path.dirname(path.resolve(options.report)), { recursive: true });
    await fs.writeFile(path.resolve(options.report), JSON.stringify(result, null, 2) + "\n", "utf8");
    console.log(JSON.stringify(result));
    if (!result.pass) process.exitCode = 1;
  } finally {
    await browser.close();
    await fs.rm(qaFilePath, { force: true });
    await fs.rm(historyPath, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
