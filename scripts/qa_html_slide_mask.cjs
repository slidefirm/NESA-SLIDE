const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--file") out.file = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
  }
  if (!out.file || !out.report) throw new Error("--file and --report are required");
  return out;
}

function portablePath(value) {
  return path.relative(process.cwd(), value).split(path.sep).join("/");
}

async function setMask(page, color, opacity) {
  await page.locator("#edit-slide-mask-color").evaluate((input, value) => {
    input.value = value;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }, color);
  await page.locator("#edit-slide-mask-opacity").evaluate((input, value) => {
    input.value = String(value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }, opacity);
  await page.waitForTimeout(100);
}

async function readMask(page) {
  return page.evaluate(() => {
    const slide = document.querySelector("#stage > .slide.active");
    const color = document.getElementById("edit-slide-mask-color");
    const opacity = document.getElementById("edit-slide-mask-opacity");
    const pseudo = slide ? getComputedStyle(slide, "::before") : null;
    return {
      id: slide?.id || null,
      color: slide?.dataset.editorSlideMaskColor || null,
      opacity: slide?.dataset.editorSlideMaskOpacity || null,
      enabled: slide?.dataset.editorSlideMask || null,
      colorControl: color?.value || null,
      opacityControl: opacity?.value || null,
      pseudoBackground: pseudo?.backgroundColor || null,
      pseudoOpacity: pseudo?.opacity || null,
    };
  });
}

async function main() {
  const options = argsOf(process.argv);
  const sourcePath = path.resolve(options.file);
  await fs.access(sourcePath);
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  try {
    // This harness verifies browser-download HTML export, not File System
    // Access. Install the fallback override before the document loads.
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
    await page.goto(pathToFileURL(sourcePath).href, { waitUntil: "commit", timeout: 120000 });
    await page.waitForFunction(() => Boolean(window.EditMode), null, { timeout: 120000 });
    await page.evaluate(() => {
      const key = window.EditMode.diagnostics().draftKey;
      localStorage.removeItem(key);
      document.getElementById("edit-draft-prompt")?.remove();
    });
    await page.waitForSelector("#edit-slide-style-button");
    await page.click("#edit-slide-style-button");
    await page.waitForFunction(
      () => getComputedStyle(document.getElementById("edit-slide-style-panel")).display !== "none",
      null,
      { timeout: 30000 },
    );

    let slideIds = await page.evaluate(() => [...document.querySelectorAll("#stage > .slide")].map((slide) => slide.id));
    let syntheticSecondSlide = false;
    if (slideIds.length < 2) {
      const secondSlideId = `${slideIds[0] || "s1"}-qa-second`;
      await page.evaluate((id) => {
        const stage = document.getElementById("stage");
        const first = stage?.querySelector(":scope > .slide");
        if (!stage || !first) throw new Error("Unable to create the one-slide QA companion");
        const clone = first.cloneNode(true);
        clone.id = id;
        clone.classList.remove("active");
        clone.dataset.index = "1";
        clone.dataset.pageNumber = "2";
        clone.dataset.pageCount = "2";
        stage.appendChild(clone);
        window.SlidePlayer.refreshSlides(first.id);
      }, secondSlideId);
      slideIds = await page.evaluate(() => [...document.querySelectorAll("#stage > .slide")].map((slide) => slide.id));
      syntheticSecondSlide = true;
    }
    const firstSlideId = slideIds[0];
    const secondSlideId = slideIds[1];

    const visualBefore = await page.evaluate((slideId) => {
      const node = document.querySelector(`#${slideId} .cover-center-rule`);
      if (!node) return null;
      const style = getComputedStyle(node);
      return {
        backgroundColor: style.backgroundColor,
        opacity: style.opacity,
        transform: style.transform,
        width: style.width,
        height: style.height,
      };
    }, firstSlideId);

    await setMask(page, "#112233", 25);
    const first = await readMask(page);

    await page.keyboard.press("ArrowRight");
    await page.waitForFunction((previousId) => document.querySelector("#stage > .slide.active")?.id !== previousId, firstSlideId);
    await page.waitForTimeout(100);
    await setMask(page, "#334455", 55);
    const second = await readMask(page);

    await page.keyboard.press("ArrowLeft");
    await page.waitForFunction((slideId) => document.querySelector("#stage > .slide.active")?.id === slideId, firstSlideId);
    await page.waitForTimeout(100);
    const firstRestored = await readMask(page);

    const visualAfter = await page.evaluate((slideId) => {
      const node = document.querySelector(`#${slideId} .cover-center-rule`);
      if (!node) return null;
      const style = getComputedStyle(node);
      return {
        backgroundColor: style.backgroundColor,
        opacity: style.opacity,
        transform: style.transform,
        width: style.width,
        height: style.height,
      };
    }, firstSlideId);

    await setMask(page, "#112233", 35);
    const maskChanged = await readMask(page);
    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(100);
    const maskUndo = await readMask(page);
    await page.evaluate(() => window.EditMode.redo());
    await page.waitForTimeout(100);
    const maskRedo = await readMask(page);

    await page.waitForTimeout(1800);
    const draft = await page.evaluate(() => {
      const key = window.EditMode.diagnostics().draftKey;
      const payload = JSON.parse(localStorage.getItem(key) || "null");
      return payload?.slideMasks || null;
    });

    const exportDownloadHarness = await page.evaluate(() => ({
      forcedBrowserDownload: window.__qaBrowserDownloadExportHarness === true,
      pickerUnavailable: typeof window.showSaveFilePicker === "undefined",
      pass: window.__qaBrowserDownloadExportHarness === true
        && typeof window.showSaveFilePicker === "undefined",
    }));
    if (!exportDownloadHarness.pass) {
      throw new Error("Slide-mask QA did not force browser-download export fallback");
    }
    const downloadPromise = page.waitForEvent("download");
    await page.evaluate(() => window.EditMode.export());
    const download = await downloadPromise;
    const stream = await download.createReadStream();
    const exportChunks = [];
    for await (const chunk of stream) exportChunks.push(chunk);
    const exportedHtml = Buffer.concat(exportChunks).toString("utf8");
    const exportState = await page.evaluate(({ html, slideId }) => {
      const documentCopy = new DOMParser().parseFromString(html, "text/html");
      const slide = documentCopy.getElementById(slideId);
      return {
        stylePresent: Boolean(documentCopy.getElementById("edit-slide-mask-style")),
        color: slide?.getAttribute("data-editor-slide-mask-color") || "",
        opacity: slide?.getAttribute("data-editor-slide-mask-opacity") || "",
        maskEnabled: slide?.getAttribute("data-editor-slide-mask") || "",
        cssOpacity: slide?.style.getPropertyValue("--editor-slide-mask-opacity") || "",
      };
    }, { html: exportedHtml, slideId: firstSlideId });

    const mixedGroupBefore = await page.evaluate(() => {
      const root = document.querySelector("#s1 .cover-logo");
      const shape = root?.querySelector('[data-edit-layer="background"]');
      const style = shape ? getComputedStyle(shape) : null;
      return {
        hasMixedGroup: Boolean(root && shape && root.querySelector('[data-edit-layer="text"]')),
        shape: style ? {
          backgroundColor: style.backgroundColor,
          borderColor: style.borderColor,
          opacity: style.opacity,
          transform: style.transform,
        } : null,
      };
    });

    await page.locator("#canvasBox > #stage > #s1 .cover-logo").click({ position: { x: 20, y: 20 }, force: true });
    await page.waitForTimeout(120);
    const mixedGroupControls = await page.evaluate(() => ({
      fontFamilyEnabled: document.getElementById("edit-font-family-select")?.disabled === false,
      fontSizeEnabled: document.getElementById("edit-font-size-input")?.disabled === false,
      textColorEnabled: [...document.querySelectorAll("#edit-color-tools button")].some((button) => !button.disabled),
    }));

    const shapeBeforeTextEdit = await page.evaluate(() => {
      const shape = document.querySelector("#s1 .cover-logo [data-edit-layer=\"background\"]");
      if (!shape) return null;
      const style = getComputedStyle(shape);
      return { backgroundColor: style.backgroundColor, borderColor: style.borderColor, opacity: style.opacity, transform: style.transform };
    });

    if (mixedGroupControls.fontSizeEnabled) {
      await page.locator("#edit-font-size-input").evaluate((input) => {
        const current = Number.parseFloat(input.value) || 36;
        input.value = String(current + 1);
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("blur", { bubbles: true }));
      });
      await page.waitForTimeout(100);
    }

    const shapeAfterTextEdit = await page.evaluate(() => {
      const shape = document.querySelector("#s1 .cover-logo [data-edit-layer=\"background\"]");
      if (!shape) return null;
      const style = getComputedStyle(shape);
      return { backgroundColor: style.backgroundColor, borderColor: style.borderColor, opacity: style.opacity, transform: style.transform };
    });

    const checks = {
      controlsReachable: first.colorControl === "#112233" && first.opacityControl === "25",
      firstSlideMaskApplied: first.id === firstSlideId && first.color === "#112233" && first.opacity === "0.25" && first.enabled === "true",
      secondSlideMaskApplied: second.id === secondSlideId && second.color === "#334455" && second.opacity === "0.55" && second.enabled === "true",
      perSlideValuesRestore: firstRestored.id === firstSlideId && firstRestored.color === "#112233" && firstRestored.opacity === "0.25" && firstRestored.opacityControl === "25",
      maskOnlyBackgroundLayer: first.pseudoBackground === "rgb(17, 34, 51)" && first.pseudoOpacity === "0.25",
      maskUndoRedo: maskChanged.opacity === "0.35" && maskUndo.opacity === "0.25" && maskRedo.opacity === "0.35",
      draftPersistsPerSlideMasks: Array.isArray(draft)
        && draft.some((entry) => entry.slideId === firstSlideId && entry.color === "#112233" && entry.opacity === 0.35)
        && draft.some((entry) => entry.slideId === secondSlideId && entry.color === "#334455" && entry.opacity === 0.55),
      exportPersistsMask: exportState.stylePresent
        && exportState.color === "#112233"
        && exportState.opacity === "0.35"
        && exportState.maskEnabled === "true"
        && exportState.cssOpacity === "0.35",
      exportDownloadFallbackForced: exportDownloadHarness.pass,
      existingVisualStyleUnchanged: JSON.stringify(visualBefore) === JSON.stringify(visualAfter),
      mixedGroupDetected: mixedGroupBefore.hasMixedGroup,
      mixedGroupTextControlsEnabled: mixedGroupControls.fontFamilyEnabled && mixedGroupControls.fontSizeEnabled,
      mixedGroupShapeUntouched: JSON.stringify(shapeBeforeTextEdit) === JSON.stringify(shapeAfterTextEdit),
    };
    const result = {
      qa: "html-slide-mask",
      sourceFile: portablePath(sourcePath),
      slideIds: [firstSlideId, secondSlideId],
      syntheticSecondSlide,
      first,
      second,
      firstRestored,
      maskChanged,
      maskUndo,
      maskRedo,
      draft,
      exportState,
      exportDownloadHarness,
      visualBefore,
      visualAfter,
      mixedGroupBefore,
      mixedGroupControls,
      shapeBeforeTextEdit,
      shapeAfterTextEdit,
      checks,
    };
    result.pass = Object.values(checks).every(Boolean);
    const reportPath = path.resolve(options.report);
    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
    console.log(JSON.stringify(result, null, 2));
    if (!result.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});
