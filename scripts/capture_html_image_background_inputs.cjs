#!/usr/bin/env node
"use strict";

const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");

function parseArgs(argv) {
  const options = {};
  for (let index = 2; index < argv.length; index += 1) {
    const key = argv[index];
    const value = argv[index + 1];
    if (key === "--run-dir") {
      options.runDir = value;
      index += 1;
    } else if (key === "--quality") {
      options.quality = Number(value);
      index += 1;
    }
  }
  if (!options.runDir) throw new Error("--run-dir is required");
  options.quality = Number.isFinite(options.quality) ? options.quality : 92;
  return options;
}

function parseMaskConsole(text) {
  try {
    const value = JSON.parse(text);
    if (value?.type === "html-image-background-mask" && value.payload) return value.payload;
  } catch (_) {
    // Editor diagnostics and browser warnings are unrelated to mask capture.
  }
  return null;
}

async function settleNativeStage(page) {
  await page.evaluate(() => {
    window.EditMode?.toggle(false);
    window.MotionPreview?.setEnabled(false, false);
    const style = document.createElement("style");
    style.id = "html-image-background-native-capture";
    style.textContent = `
      html, body { width:1920px !important; height:1080px !important; margin:0 !important; overflow:hidden !important; }
      #player, .editor-shell { position:fixed !important; inset:0 !important; width:1920px !important; height:1080px !important; }
      #slideRail, #slideRailHeader, #slideThumbList, #bar, #barInner, #hint,
      #editSelectionFrame, #editMultiSelectionFrame, #editContextMenu,
      #editTextFormatPanel, [data-edit-ui], [data-editor-chrome] { visibility:hidden !important; pointer-events:none !important; }
      #canvasBox { position:absolute !important; left:0 !important; top:0 !important; width:1920px !important; height:1080px !important; overflow:hidden !important; }
      #stage { position:absolute !important; left:0 !important; top:0 !important; width:1920px !important; height:1080px !important; transform:none !important; transform-origin:top left !important; }
    `;
    document.head.appendChild(style);
  });
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const geometry = await page.locator("#canvasBox > #stage").evaluate((stage) => {
    const rect = stage.getBoundingClientRect();
    const visibleSlides = [...stage.querySelectorAll(":scope > .slide")].filter((slide) => {
      const style = getComputedStyle(slide);
      const box = slide.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && box.width > 0 && box.height > 0;
    });
    return {
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      visibleSlides: visibleSlides.length,
      visibleSlideId: visibleSlides[0]?.id || null,
    };
  });
  if (geometry.width !== 1920 || geometry.height !== 1080 || geometry.visibleSlides !== 1) {
    throw new Error(`Native stage invariant failed: ${JSON.stringify(geometry)}`);
  }
  return geometry;
}

async function main() {
  const options = parseArgs(process.argv);
  const runDir = path.resolve(options.runDir);
  const manifestPath = path.join(runDir, "run.json");
  const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
  if (manifest.mode !== "html-image-background-per-slide-experiment") {
    throw new Error("run.json is not a prepared per-slide background run");
  }
  const maskPages = Array.isArray(manifest.mask_pages) ? manifest.mask_pages : [];
  if (!maskPages.length || maskPages.length !== manifest.slide_count) {
    throw new Error("run.json mask_pages must match slide_count");
  }

  const referenceDir = path.join(runDir, "references");
  await fs.mkdir(referenceDir, { recursive: true });
  const { chromium } = loadPlaywright();
  const executablePath = browserExecutable();
  if (!process.env.BROWSER_CDP_URL && !executablePath) throw new Error("No Chrome or Edge executable found");
  const browser = process.env.BROWSER_CDP_URL
    ? await chromium.connectOverCDP(process.env.BROWSER_CDP_URL)
    : await chromium.launch({ headless: true, executablePath });
  const records = [];
  try {
    for (let index = 0; index < maskPages.length; index += 1) {
      const sourcePath = path.resolve(maskPages[index]);
      const markup = await fs.readFile(sourcePath, "utf8");
      const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
      await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
      await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
      let maskRecord = null;
      page.on("console", (message) => {
        const parsed = parseMaskConsole(message.text());
        if (parsed) maskRecord = parsed;
      });
      const baseHref = pathToFileURL(`${path.dirname(sourcePath)}${path.sep}`).href;
      const withBase = markup.replace(/<head>/i, `<head><base href="${baseHref}">`);
      await page.setContent(withBase, { waitUntil: "load", timeout: 120000 });
      await Promise.race([
        page.waitForFunction(() => document.fonts?.status === "loaded", null, { timeout: 5000 }),
        page.waitForTimeout(5000),
      ]);
      await page.waitForFunction(() => document.querySelector("#canvasBox > #stage"), null, { timeout: 120000 });
      for (let attempt = 0; attempt < 100 && !maskRecord; attempt += 1) await page.waitForTimeout(25);
      if (!maskRecord) throw new Error(`Mask payload was not emitted: ${sourcePath}`);
      const geometry = await settleNativeStage(page);
      if (geometry.visibleSlideId !== maskRecord.id) {
        throw new Error(`Visible slide ${geometry.visibleSlideId} does not match mask record ${maskRecord.id}`);
      }
      const number = String(index + 1).padStart(3, "0");
      const referencePath = path.join(referenceDir, `slide-${number}-clean-foreground.png`);
      await page.locator("#canvasBox > #stage").screenshot({ path: referencePath, type: "png" });
      records.push({
        ...maskRecord,
        source_reference: referencePath,
        reference_screenshot: referencePath,
        capture_contract: {
          slide_only: true,
          editor_chrome_hidden: true,
          native_width: geometry.width,
          native_height: geometry.height,
        },
      });
      await page.close();
      process.stdout.write(`${JSON.stringify({ slide: index + 1, id: maskRecord.id, reference: referencePath })}\n`);
    }
  } finally {
    await browser.close();
  }
  const outputPath = path.join(runDir, "masks.json");
  await fs.writeFile(outputPath, `${JSON.stringify(records, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify({ slides: records.length, masks: outputPath })}\n`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
