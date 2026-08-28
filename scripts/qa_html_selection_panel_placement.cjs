const fs = require("node:fs/promises");
const crypto = require("node:crypto");
const os = require("node:os");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--html") out.html = argv[++index];
    else if (argv[index] === "--url") out.url = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
    else if (argv[index] === "--selector") out.selector = argv[++index];
    else if (argv[index] === "--editor") out.editor = argv[++index];
    else if (argv[index] === "--fixture-output") out.fixtureOutput = argv[++index];
  }
  if ((!out.html && !out.url) || !out.report) {
    throw new Error("--html or --url, plus --report, are required");
  }
  return out;
}

async function canonicalFixture(htmlPath, editorPath, fixtureOutput) {
  const markup = await fs.readFile(htmlPath, "utf8");
  const editorSource = await fs.readFile(editorPath, "utf8");
  const editModeMarker = markup.indexOf("window.EditMode = {");
  if (editModeMarker < 0) throw new Error("Embedded EditMode source was not found in the HTML fixture");
  const scriptStart = markup.lastIndexOf("<script", editModeMarker);
  const scriptOpenEnd = markup.indexOf(">", scriptStart);
  const scriptEnd = markup.indexOf("</script>", editModeMarker);
  if (scriptStart < 0 || scriptOpenEnd < 0 || scriptEnd < 0) {
    throw new Error("Unable to isolate the embedded EditMode script");
  }
  const sourceBase = pathToFileURL(`${path.dirname(htmlPath)}${path.sep}`).href;
  const withBase = markup.includes("<base ")
    ? markup
    : markup.replace(/<head(\s[^>]*)?>/i, (head) => `${head}<base href="${sourceBase}">`);
  const adjustedMarker = withBase.indexOf("window.EditMode = {");
  const adjustedStart = withBase.lastIndexOf("<script", adjustedMarker);
  const adjustedEnd = withBase.indexOf("</script>", adjustedMarker) + "</script>".length;
  const materialized = `${withBase.slice(0, adjustedStart)}<script data-edit-mode-embedded="true" data-qa-canonical-editor="true">\n${editorSource}\n</script>${withBase.slice(adjustedEnd)}`;
  const temporaryDirectory = fixtureOutput ? null : await fs.mkdtemp(path.join(os.tmpdir(), "qa-html-selection-panel-"));
  const temporaryHtml = fixtureOutput
    ? path.resolve(fixtureOutput)
    : path.join(temporaryDirectory, path.basename(htmlPath));
  await fs.mkdir(path.dirname(temporaryHtml), { recursive: true });
  await fs.writeFile(temporaryHtml, materialized, "utf8");
  return {
    pageUrl: pathToFileURL(temporaryHtml).href,
    temporaryDirectory,
    editorSha256: crypto.createHash("sha256").update(editorSource).digest("hex"),
  };
}

function portablePath(value) {
  if (!value) return null;
  return path.relative(process.cwd(), value).split(path.sep).join("/");
}

function roundedRect(rect) {
  if (!rect) return null;
  return Object.fromEntries(
    ["left", "top", "right", "bottom", "width", "height"]
      .map((key) => [key, Math.round(rect[key] * 10) / 10]),
  );
}

async function runViewport(browser, pageUrl, selector, viewport, verticalPosition) {
  const page = await browser.newPage({ viewport });
  try {
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(pageUrl, { waitUntil: "commit", timeout: 30000 });
    await page.waitForLoadState("domcontentloaded");
    await Promise.race([page.evaluate(() => document.fonts?.ready), page.waitForTimeout(3000)]);
    await page.waitForFunction(() => Boolean(window.EditMode));
    await page.evaluate(() => window.EditMode.toggle(true));
    await page.waitForTimeout(180);

    const targetInfo = await page.evaluate(({ targetSelector, verticalPosition: position }) => {
      window.EditMode.deselect();
      const target = document.querySelector(targetSelector);
      if (!target) throw new Error(`Selection target not found: ${targetSelector}`);
      const slide = target.closest(".slide.active");
      if (!slide) throw new Error("Selection target is not inside the active slide");
      slide.appendChild(target);
      target.style.setProperty("position", "absolute", "important");
      target.style.setProperty("left", "256px");
      target.style.setProperty("top", position === "bottom" ? "852px" : "48px");
      target.style.setProperty("width", "1408px");
      target.style.setProperty("height", "180px");
      target.style.setProperty("z-index", "20");
      target.dataset.qaSelectionPanelTarget = "true";
      const rect = target.getBoundingClientRect();
      return {
        x: rect.left + rect.width / 2,
        y: rect.top + Math.min(rect.height / 2, 24),
      };
    }, { targetSelector: selector, verticalPosition });

    await page.mouse.click(targetInfo.x, targetInfo.y);
    await page.waitForFunction(() => {
      const badge = document.getElementById("edit-selection-badge");
      return badge && getComputedStyle(badge).display !== "none";
    });
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));

    return await page.evaluate((position) => {
      const target = document.querySelector('[data-qa-selection-panel-target="true"]');
      const panel = document.getElementById("edit-selection-badge");
      const frame = document.getElementById("edit-selection-frame");
      const bar = document.getElementById("bar");
      const canvas = document.getElementById("canvasBox");
      if (!target || !panel || !frame || !bar || !canvas) {
        throw new Error("Editor selection geometry is incomplete");
      }
      const targetRect = target.getBoundingClientRect();
      const panelRect = panel.getBoundingClientRect();
      const frameRect = frame.getBoundingClientRect();
      const barRect = bar.getBoundingClientRect();
      const canvasRect = canvas.getBoundingClientRect();
      const overlapWidth = Math.max(0, Math.min(frameRect.right, panelRect.right) - Math.max(frameRect.left, panelRect.left));
      const overlapHeight = Math.max(0, Math.min(frameRect.bottom, panelRect.bottom) - Math.max(frameRect.top, panelRect.top));
      const overlapArea = overlapWidth * overlapHeight;
      const clearance = panelRect.bottom <= frameRect.top
        ? frameRect.top - panelRect.bottom
        : (panelRect.top >= frameRect.bottom ? panelRect.top - frameRect.bottom : -Math.min(overlapWidth, overlapHeight));
      const panelInsideViewport = panelRect.left >= -0.5
        && panelRect.top >= -0.5
        && panelRect.right <= window.innerWidth + 0.5
        && panelRect.bottom <= window.innerHeight + 0.5;
      return {
        verticalPosition: position,
        viewport: { width: window.innerWidth, height: window.innerHeight },
        placement: panel.dataset.placement || null,
        chromeDock: panel.dataset.chromeDock === "true",
        target: {
          left: targetRect.left,
          top: targetRect.top,
          right: targetRect.right,
          bottom: targetRect.bottom,
          width: targetRect.width,
          height: targetRect.height,
        },
        panel: {
          left: panelRect.left,
          top: panelRect.top,
          right: panelRect.right,
          bottom: panelRect.bottom,
          width: panelRect.width,
          height: panelRect.height,
        },
        frame: {
          left: frameRect.left,
          top: frameRect.top,
          right: frameRect.right,
          bottom: frameRect.bottom,
          width: frameRect.width,
          height: frameRect.height,
        },
        bar: {
          left: barRect.left,
          top: barRect.top,
          right: barRect.right,
          bottom: barRect.bottom,
          width: barRect.width,
          height: barRect.height,
        },
        canvas: {
          left: canvasRect.left,
          top: canvasRect.top,
          right: canvasRect.right,
          bottom: canvasRect.bottom,
          width: canvasRect.width,
          height: canvasRect.height,
        },
        overlapArea,
        clearance,
        checks: {
          panelVisible: getComputedStyle(panel).display !== "none",
          panelInsideViewport,
          selectedObjectUncovered: overlapArea <= 0.5,
          selectionFrameVisible: getComputedStyle(frame).display !== "none",
          panelBelowTopbar: panelRect.top >= barRect.bottom - 0.5,
        },
      };
    }, verticalPosition);
  } finally {
    await page.close();
  }
}

async function runEditorCompatibility(browser, pageUrl) {
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  try {
    // This compatibility case asserts browser-download export. File System
    // Access behavior is deliberately covered by file-binding/direct-overwrite
    // QA, so force this page's fallback before scripts initialize.
    await page.addInitScript(() => {
      Object.defineProperty(window, "showSaveFilePicker", {
        value: undefined,
        writable: false,
        configurable: true,
      });
      window.__qaBrowserDownloadExportHarness = true;
    });
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(pageUrl, { waitUntil: "commit", timeout: 30000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
    ), null, { timeout: 120000 });
    await page.evaluate(() => Promise.race([
      document.fonts?.ready || Promise.resolve(),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]));

    const interaction = await page.evaluate(async () => {
      const nextFrame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const fireClick = (element) => {
        ["mousedown", "mouseup", "click"].forEach((type) => element.dispatchEvent(new MouseEvent(type, {
          bubbles: true,
          clientX: 360,
          clientY: 240,
          button: 0,
        })));
      };
      localStorage.clear();
      window.EditMode.toggle(true);
      const target = document.querySelector('#stage > .slide .page-title[data-edit-fit="text"]');
      if (!target) throw new Error("Editable page-title target was not found");
      const slide = target.closest(".slide");
      window.setSlide(Number(slide.dataset.index));
      await nextFrame();
      fireClick(target);
      await nextFrame();
      const fontInput = document.getElementById("edit-font-size-input");
      const plusButton = fontInput?.parentElement?.querySelector("button:last-of-type");
      if (!plusButton) throw new Error("Font-size increment control was not found");
      const beforeFont = parseFloat(getComputedStyle(target).fontSize);
      plusButton.click();
      await nextFrame();
      const afterFont = parseFloat(getComputedStyle(target).fontSize);
      window.EditMode.undo();
      await nextFrame();
      const undoFont = parseFloat(getComputedStyle(target).fontSize);
      window.EditMode.redo();
      await nextFrame();
      const redoFont = parseFloat(getComputedStyle(target).fontSize);
      fireClick(slide.querySelector(".meta") || slide);
      await new Promise((resolve) => setTimeout(resolve, 1800));
      const apiAvailable = ["toggle", "export", "undo", "redo", "save"]
        .every((key) => typeof window.EditMode[key] === "function");
      const undoRedoPass = afterFont > beforeFont
        && Math.abs(undoFont - beforeFont) <= 0.1
        && Math.abs(redoFont - afterFont) <= 0.1;
      const draftSaved = Object.keys(localStorage).some((key) => key.startsWith("edit-draft:"));
      return {
        apiAvailable,
        historyLimit: window.EditMode.historyLimit,
        beforeFont,
        afterFont,
        undoFont,
        redoFont,
        undoRedoPass,
        draftSaved,
        pass: apiAvailable && window.EditMode.historyLimit === 100 && undoRedoPass && draftSaved,
      };
    });

    const exportDownloadHarness = await page.evaluate(() => ({
      forcedBrowserDownload: window.__qaBrowserDownloadExportHarness === true,
      pickerUnavailable: typeof window.showSaveFilePicker === "undefined",
      pass: window.__qaBrowserDownloadExportHarness === true
        && typeof window.showSaveFilePicker === "undefined",
    }));
    if (!exportDownloadHarness.pass) {
      throw new Error("Selection-panel QA did not force browser-download export fallback");
    }
    const downloadPromise = page.waitForEvent("download", { timeout: 60000 });
    const [download, exportResult] = await Promise.all([
      downloadPromise,
      page.evaluate(() => window.EditMode.export()),
    ]);
    const stream = await download.createReadStream();
    const chunks = [];
    for await (const chunk of stream) chunks.push(chunk);
    const exportedHtml = Buffer.concat(chunks).toString("utf8");
    const exportChecks = await page.evaluate((markup) => {
      const doc = new DOMParser().parseFromString(markup, "text/html");
      const checks = {
        contenteditableRemoved: doc.querySelectorAll("[contenteditable]").length === 0,
        transientPanelRemoved: !doc.querySelector("#edit-selection-badge"),
        selectionChromeRemoved: !doc.querySelector("#edit-selection-frame,.edit-resize-handle"),
        editorEmbedded: Boolean(doc.querySelector('script[data-edit-mode-embedded="true"]')),
        browserDownloadFallbackForced: exportDownloadHarness.pass,
      };
      return { ...checks, pass: Object.values(checks).every(Boolean) };
    }, exportedHtml);
    await page.evaluate(() => localStorage.clear());
    return {
      interaction,
      export: {
        method: exportResult?.method || null,
        fileName: exportResult?.fileName || download.suggestedFilename(),
        browserDownloadHarness: exportDownloadHarness,
        ...exportChecks,
      },
      pass: interaction.pass && exportChecks.pass,
    };
  } finally {
    await page.close();
  }
}

async function main() {
  const options = argsOf(process.argv);
  const htmlPath = options.html ? path.resolve(options.html) : null;
  const editorPath = path.resolve(options.editor || path.join("src", "html-editor", "edit-mode.js"));
  const fixture = htmlPath ? await canonicalFixture(htmlPath, editorPath, options.fixtureOutput) : null;
  const pageUrl = options.url || fixture.pageUrl;
  const selector = options.selector || ".slide.active .el.cover-title";
  const { chromium } = loadPlaywright();
  let browser = null;
  try {
    browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
    const viewports = [
      { width: 1600, height: 900 },
      { width: 1366, height: 768 },
    ];
    const cases = [];
    for (const viewport of viewports) {
      for (const verticalPosition of ["top", "bottom"]) {
        cases.push(await runViewport(browser, pageUrl, selector, viewport, verticalPosition));
      }
    }
    const compatibility = await runEditorCompatibility(browser, pageUrl);
    cases.forEach((testCase) => {
      testCase.target = roundedRect(testCase.target);
      testCase.panel = roundedRect(testCase.panel);
      testCase.frame = roundedRect(testCase.frame);
      testCase.bar = roundedRect(testCase.bar);
      testCase.canvas = roundedRect(testCase.canvas);
      testCase.overlapArea = Math.round(testCase.overlapArea * 10) / 10;
      testCase.clearance = Math.round(testCase.clearance * 10) / 10;
      testCase.pass = Object.values(testCase.checks).every(Boolean);
    });
    const result = {
      html: portablePath(htmlPath),
      url: options.url || pathToFileURL(htmlPath).href,
      editor: portablePath(editorPath),
      editorSha256: fixture ? fixture.editorSha256 : null,
      selector,
      cases,
      compatibility,
      pass: cases.every((testCase) => testCase.pass) && compatibility.pass,
    };
    await fs.mkdir(path.dirname(path.resolve(options.report)), { recursive: true });
    await fs.writeFile(path.resolve(options.report), `${JSON.stringify(result, null, 2)}\n`, "utf8");
    console.log(JSON.stringify(result));
    if (!result.pass) process.exitCode = 1;
  } finally {
    if (browser) await Promise.race([browser.close(), new Promise((resolve) => setTimeout(resolve, 2000))]);
    if (fixture?.temporaryDirectory) await fs.rm(fixture.temporaryDirectory, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
