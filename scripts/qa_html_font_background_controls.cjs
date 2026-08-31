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

function primaryFamily(value) {
  return String(value || "").split(",")[0].trim().replace(/^[\"']|[\"']$/g, "").toLowerCase();
}

async function main() {
  const options = argsOf(process.argv);
  const browserCandidates = [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  const executablePath = browserCandidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
  await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
  try {
    await page.goto(options.url, { waitUntil: "commit", timeout: 120000 });
    await page.waitForFunction(() => Boolean(window.EditMode), null, { timeout: 120000 });
    await page.evaluate(() => {
      localStorage.removeItem(window.EditMode.diagnostics().draftKey);
      document.getElementById("edit-draft-prompt")?.remove();
    });
    await page.evaluate(() => {
      const root = document.documentElement;
      root.dataset.presetTheme = "qa-dark-preset";
      root.dataset.themeKind = "html-preset";
      root.style.setProperty("--bg", "#102030");
      root.style.setProperty("--surface", "#203448");
      root.style.setProperty("--text", "#F5F7FA");
      root.style.setProperty("--muted", "#A7B4C2");
      root.style.setProperty("--accent", "#E06C3B");
      root.style.setProperty("--support-accent", "#4FC3B3");
      root.style.setProperty("--surface-text", "#F5F7FA");
    });
    await page.waitForTimeout(100);

    const target = page.locator("#s1 .title").first();
    await target.waitFor({ state: "visible" });
    await target.click({ position: { x: 40, y: 30 } });
    await page.waitForTimeout(100);

    const before = await page.evaluate(() => {
      const target = document.querySelector("#s1 .title");
      const select = document.getElementById("edit-font-family-select");
      const badge = document.getElementById("edit-selection-badge");
      const bar = document.getElementById("bar");
      const badgeRect = badge.getBoundingClientRect();
      const barRect = bar.getBoundingClientRect();
      const swatches = [...document.querySelectorAll("#edit-color-tools [data-color-swatch]")];
      return {
        computedFamily: getComputedStyle(target).fontFamily,
        inlineFamily: target.style.fontFamily,
        selectorVisible: Boolean(select && getComputedStyle(select).display !== "none" && !select.disabled),
        selectorOptions: [...(select?.options || [])].map((option) => option.textContent),
        swatchColors: swatches.map((swatch) => getComputedStyle(swatch).backgroundColor),
        badgeBackground: getComputedStyle(badge).backgroundColor,
        badgeColor: getComputedStyle(badge).color,
        badgeBorder: getComputedStyle(badge).borderColor,
        selectionPanelAvoidsToolbar: barRect.top < innerHeight / 2
          ? badgeRect.top >= barRect.bottom
          : badgeRect.bottom <= barRect.top,
      };
    });

    const selectedFontValue = await page.evaluate(() => {
      const select = document.getElementById("edit-font-family-select");
      return [...select.options].find((option) => option.textContent === "Noto Sans TC")?.value || "";
    });
    await page.selectOption("#edit-font-family-select", selectedFontValue);
    await page.waitForTimeout(100);
    const afterElementFont = await page.evaluate(() => ({
      inline: document.querySelector("#s1 .title").style.fontFamily,
      computed: getComputedStyle(document.querySelector("#s1 .title")).fontFamily,
    }));
    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(80);
    const undoElementFont = await page.evaluate(() => document.querySelector("#s1 .title").style.fontFamily);
    await page.evaluate(() => window.EditMode.redo());
    await page.waitForTimeout(80);
    const redoElementFont = await page.evaluate(() => document.querySelector("#s1 .title").style.fontFamily);

    await page.click("#edit-slide-style-button");
    await page.waitForFunction(() => getComputedStyle(document.getElementById("edit-slide-style-panel")).display !== "none");
    const deckFontValue = await page.evaluate(() => {
      const select = document.getElementById("edit-deck-font-family-select");
      return [...select.options].find((option) => option.textContent === "Arial")?.value || "";
    });
    await page.selectOption("#edit-deck-font-family-select", deckFontValue);
    await page.waitForTimeout(100);
    const afterDeckFont = await page.evaluate(() => {
      const style = document.documentElement.style;
      const target = document.querySelector("#s1 .title");
      return {
        display: style.getPropertyValue("--font-display").trim(),
        heading: style.getPropertyValue("--font-heading").trim(),
        body: style.getPropertyValue("--font-body").trim(),
        mono: getComputedStyle(document.documentElement).getPropertyValue("--font-mono").trim(),
        selectedInline: target.style.fontFamily,
        selectedComputed: getComputedStyle(target).fontFamily,
      };
    });
    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(80);
    const undoDeckFont = await page.evaluate(() => document.documentElement.style.getPropertyValue("--font-body").trim());
    await page.evaluate(() => window.EditMode.redo());
    await page.waitForTimeout(80);
    const redoDeckFont = await page.evaluate(() => document.documentElement.style.getPropertyValue("--font-body").trim());

    const beforeBackground = await page.evaluate(() => {
      const slide = document.querySelector(".slide.active");
      const style = getComputedStyle(slide);
      return { image: style.backgroundImage, inlineColor: slide.style.backgroundColor };
    });
    await page.evaluate(() => {
      const input = document.getElementById("edit-slide-background-input");
      input.value = "#315579";
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await page.waitForTimeout(100);
    const afterBackground = await page.evaluate(() => {
      const slide = document.querySelector(".slide.active");
      const style = getComputedStyle(slide);
      return { image: style.backgroundImage, inlineColor: slide.style.backgroundColor, computedColor: style.backgroundColor };
    });
    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(80);
    const undoBackground = await page.evaluate(() => document.querySelector(".slide.active").style.backgroundColor);
    await page.evaluate(() => window.EditMode.redo());
    await page.waitForTimeout(80);
    const redoBackground = await page.evaluate(() => document.querySelector(".slide.active").style.backgroundColor);

    await page.waitForTimeout(1750);
    const draft = await page.evaluate(() => {
      const key = window.EditMode.diagnostics().draftKey;
      const payload = JSON.parse(localStorage.getItem(key) || "null");
      return {
        exists: Boolean(payload),
        hasElementFont: Boolean(payload?.entries?.some((entry) => Object.prototype.hasOwnProperty.call(entry, "fontFamily") && entry.fontFamily)),
        deckFont: payload?.deckFont || null,
        slideBackgrounds: payload?.slideBackgrounds || null,
      };
    });

    const downloadPromise = page.waitForEvent("download");
    await page.evaluate(() => window.EditMode.export());
    const download = await downloadPromise;
    const stream = await download.createReadStream();
    const exportChunks = [];
    for await (const chunk of stream) exportChunks.push(chunk);
    const exportedHtml = Buffer.concat(exportChunks).toString("utf8");
    const exportState = await page.evaluate((html) => {
      const documentCopy = new DOMParser().parseFromString(html, "text/html");
      const rootStyle = documentCopy.documentElement.style;
      const slide = documentCopy.getElementById("s1");
      const title = slide?.querySelector(".title");
      return {
        editorPanelRemoved: !documentCopy.getElementById("edit-slide-style-panel"),
        deckFont: rootStyle.getPropertyValue("--font-body").trim(),
        slideBackground: slide?.style.backgroundColor || "",
        elementFont: title?.style.fontFamily || "",
      };
    }, exportedHtml);

    await page.reload({ waitUntil: "commit", timeout: 120000 });
    await page.waitForFunction(() => Boolean(window.EditMode), null, { timeout: 120000 });
    await page.waitForSelector("#edit-draft-prompt");
    await page.click("#edit-draft-prompt button");
    await page.waitForTimeout(150);
    const restoredDraft = await page.evaluate(() => {
      const rootStyle = document.documentElement.style;
      const slide = document.getElementById("s1");
      const title = slide.querySelector(".title");
      return {
        deckFont: rootStyle.getPropertyValue("--font-body").trim(),
        slideBackground: slide.style.backgroundColor,
        elementFont: title.style.fontFamily,
      };
    });

    const expectedPalette = ["rgb(245, 247, 250)", "rgb(167, 180, 194)", "rgb(224, 108, 59)", "rgb(79, 195, 179)", "rgb(32, 52, 72)", "rgb(16, 32, 48)"];
    const checks = {
      familySelectorVisible: before.selectorVisible,
      familyOptionsPresent: ["Noto Sans TC", "Noto Serif TC", "Roboto Mono"].every((name) => before.selectorOptions.includes(name)),
      presetPaletteProjected: expectedPalette.every((color) => before.swatchColors.includes(color)),
      pickerChromeUsesPresetSurface: before.badgeBackground === "rgb(32, 52, 72)",
      pickerChromeUsesPresetAccent: before.badgeBorder === "rgb(224, 108, 59)",
      selectionPanelAvoidsToolbar: before.selectionPanelAvoidsToolbar,
      elementFontApplied: primaryFamily(afterElementFont.computed) === "noto sans tc" && Boolean(afterElementFont.inline),
      elementFontUndo: undoElementFont === "",
      elementFontRedo: redoElementFont === afterElementFont.inline,
      deckRoleFontsApplied: [afterDeckFont.display, afterDeckFont.heading, afterDeckFont.body].every((value) => primaryFamily(value) === "arial"),
      monoRolePreserved: primaryFamily(afterDeckFont.mono) === "roboto mono",
      elementOverridePreserved: primaryFamily(afterDeckFont.selectedComputed) === "noto sans tc" && afterDeckFont.selectedInline === redoElementFont,
      deckFontUndo: undoDeckFont === "",
      deckFontRedo: primaryFamily(redoDeckFont) === "arial",
      slideBackgroundApplied: afterBackground.inlineColor === "rgb(49, 85, 121)",
      backgroundImagePreserved: afterBackground.image === beforeBackground.image && afterBackground.image !== "none",
      slideBackgroundUndo: undoBackground === beforeBackground.inlineColor,
      slideBackgroundRedo: redoBackground === afterBackground.inlineColor,
      draftPersistsElementFont: draft.hasElementFont,
      draftPersistsDeckFont: Boolean(draft.deckFont) && primaryFamily(draft.deckFont["--font-body"]) === "arial",
      draftPersistsSlideBackground: Boolean(draft.slideBackgrounds?.some((entry) => entry.slideId === "s1" && entry.backgroundColor === afterBackground.inlineColor)),
      exportRemovesEditorPanel: exportState.editorPanelRemoved,
      exportPersistsElementFont: exportState.elementFont === afterElementFont.inline,
      exportPersistsDeckFont: primaryFamily(exportState.deckFont) === "arial",
      exportPersistsSlideBackground: exportState.slideBackground === afterBackground.inlineColor,
      draftRestoreElementFont: restoredDraft.elementFont === afterElementFont.inline,
      draftRestoreDeckFont: primaryFamily(restoredDraft.deckFont) === "arial",
      draftRestoreSlideBackground: restoredDraft.slideBackground === afterBackground.inlineColor,
    };
    const pass = Object.values(checks).every(Boolean);
    const report = {
      qa: "html-font-background-controls",
      url: options.url,
      pass,
      checks,
      evidence: {
        before,
        afterElementFont,
        undoElementFont,
        redoElementFont,
        afterDeckFont,
        undoDeckFont,
        redoDeckFont,
        beforeBackground,
        afterBackground,
        undoBackground,
        redoBackground,
        draft,
        exportState,
        restoredDraft,
      },
    };
    const reportPath = path.resolve(options.report);
    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
    process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
    if (!pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});
