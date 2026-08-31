const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--file") out.file = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
  }
  if (!out.file || !out.report) throw new Error("--file and --report are required");
  return out;
}

function reportPath(filePath) {
  return path.relative(process.cwd(), filePath).split(path.sep).join("/");
}

async function main() {
  const options = argsOf(process.argv);
  const sourcePath = path.resolve(options.file);
  await fs.access(sourcePath);
  const candidates = [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  const executablePath = candidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
    await page.addInitScript(() => {
      window.__qaFilePicker = { calls: 0, suggestedName: "", writes: [] };
      window.showSaveFilePicker = async (options) => {
        window.__qaFilePicker.calls += 1;
        window.__qaFilePicker.suggestedName = options?.suggestedName || "qa-bound.html";
        return {
          name: window.__qaFilePicker.suggestedName,
          queryPermission: async () => "granted",
          requestPermission: async () => "granted",
          createWritable: async () => ({
            write: async (html) => window.__qaFilePicker.writes.push(String(html)),
            close: async () => {},
          }),
        };
      };
    });
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(pathToFileURL(sourcePath).href, { waitUntil: "commit", timeout: 120000 });
    await page.waitForFunction(() => Boolean(window.EditMode), null, { timeout: 120000 });
    const saveControl = page.locator("button[data-save-binding-state]");
    await saveControl.waitFor({ state: "visible", timeout: 120000 });
    const initial = await saveControl.evaluate((button) => ({
      label: button.textContent.trim(),
      state: button.dataset.saveBindingState,
      method: button.dataset.saveBindingMethod,
    }));

    const marker = `FILE-BINDING-QA-${Date.now()}`;
    const target = page.locator(
      "#stage .slide.active [data-edit-layer=\"text\"],#stage .slide.active [data-edit-kind=\"text\"],#stage .slide.active [data-edit-fit=\"text\"],#stage .slide.active .el:not(.scrim)",
    ).first();
    await target.scrollIntoViewIfNeeded();
    await target.dblclick({ force: true });
    const originalText = await target.innerText();
    await target.fill(`${originalText} ${marker}`);

    await saveControl.click();
    await page.waitForFunction(() => window.__qaFilePicker.writes.length > 0, null, { timeout: 30000 });
    await page.waitForFunction(
      () => document.querySelector("button[data-save-binding-state]")?.dataset.saveBindingState === "bound",
      null,
      { timeout: 30000 },
    );

    const secondMarker = `FILE-BINDING-QA-SECOND-${Date.now()}`;
    await target.dblclick({ force: true });
    const secondText = await target.innerText();
    await target.fill(`${secondText} ${secondMarker}`);
    await saveControl.click();
    await page.waitForFunction(() => window.__qaFilePicker.writes.length >= 2, null, { timeout: 30000 });

    const evidence = await page.evaluate(({ marker: firstMarker, secondMarker: finalMarker }) => {
      const button = document.querySelector("button[data-save-binding-state]");
      const writes = window.__qaFilePicker.writes.map(String);
      return {
        picker: {
          calls: window.__qaFilePicker.calls,
          suggestedName: window.__qaFilePicker.suggestedName,
          writeCount: writes.length,
          writeSizes: writes.map((html) => html.length),
          firstMarkerInWrites: writes.map((html) => html.includes(firstMarker)),
          secondMarkerInWrites: writes.map((html) => html.includes(finalMarker)),
        },
        saveButton: button ? {
          label: button.textContent.trim(),
          state: button.dataset.saveBindingState,
          method: button.dataset.saveBindingMethod,
          boundFile: button.dataset.saveBoundFile || "",
        } : null,
        fileHandleId: document.documentElement.getAttribute("data-editor-file-handle-id") || "",
        actionStatus: document.querySelector("#edit-action-status")?.textContent || "",
        diagnostics: window.EditMode.diagnostics(),
      };
    }, { marker, secondMarker });
    const result = {
      sourceFile: reportPath(sourcePath),
      protocol: "file:",
      marker,
      secondMarker,
      initial,
      evidence,
      checks: {
        initialButtonExplainsBinding: initial.state === "unbound" && initial.label === "綁定並存檔",
        onePickerAction: evidence.picker.calls === 1,
        firstWriteCompleted: evidence.picker.firstMarkerInWrites[0] === true,
        secondWriteCompleted: evidence.picker.secondMarkerInWrites.at(-1) === true,
        bindingIdWritten: Boolean(evidence.fileHandleId),
        boundAfterWrite: evidence.saveButton?.state === "bound" && evidence.saveButton?.method === "file-handle",
        secondSaveReusesBinding: evidence.picker.calls === 1 && evidence.picker.writeCount === 2 && evidence.saveButton?.method === "file-handle",
        rememberedFileNameShown: Boolean(evidence.saveButton?.boundFile),
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
