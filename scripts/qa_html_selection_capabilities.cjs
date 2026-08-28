const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { fileURLToPath } = require("node:url");
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

async function visible(page, selector) {
  return page.evaluate((value) => {
    const node = document.querySelector(value);
    if (!node || !node.getClientRects().length) return false;
    const style = getComputedStyle(node);
    return style.display !== "none" && style.visibility !== "hidden";
  }, selector);
}

async function visibleCount(page, selector) {
  return page.evaluate((value) => {
    return [...document.querySelectorAll(value)].filter((node) => {
      if (!node.getClientRects().length) return false;
      const style = getComputedStyle(node);
      return style.display !== "none" && style.visibility !== "hidden";
    }).length;
  }, selector);
}

async function badgeLabel(page) {
  return page.evaluate(() => {
    return document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent?.trim() || "";
  });
}

async function allControlsDisabled(page, selector) {
  return page.evaluate((value) => {
    const roots = [...document.querySelectorAll(value)];
    const controls = roots.flatMap((root) => (
      root.matches("button,input,select")
        ? [root]
        : [...root.querySelectorAll("button,input,select")]
    ));
    return controls.length > 0 && controls.every((control) => control.disabled || control.getAttribute("aria-disabled") === "true");
  }, selector);
}

async function clickCenter(page, selector) {
  const box = await page.evaluate((value) => {
    const node = [...document.querySelectorAll(value)].find((candidate) => {
      const rect = candidate.getBoundingClientRect();
      const style = getComputedStyle(candidate);
      return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
    });
    if (!node) return null;
    const rect = node.getBoundingClientRect();
    return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
  }, selector);
  if (!box) throw new Error(`No visible box for ${selector}`);
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await page.waitForTimeout(100);
}

async function clickExact(page, selector) {
  const clicked = await page.evaluate((value) => {
    const node = [...document.querySelectorAll(value)].find((candidate) => {
      const rect = candidate.getBoundingClientRect();
      const style = getComputedStyle(candidate);
      return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
    });
    if (!node) return false;
    const rect = node.getBoundingClientRect();
    for (const type of ["mousedown", "mouseup", "click"]) {
      node.dispatchEvent(new MouseEvent(type, {
        bubbles: true,
        button: 0,
        clientX: rect.left + rect.width / 2,
        clientY: rect.top + rect.height / 2,
      }));
    }
    return true;
  }, selector);
  if (!clicked) throw new Error(`No visible exact target for ${selector}`);
  await page.waitForTimeout(100);
}

async function activateSlideWith(page, selector) {
  const count = await page.locator("#stage > .slide").count();
  for (let index = 0; index < count; index += 1) {
    await page.evaluate((value) => window.setSlide(value), index);
    await page.waitForTimeout(80);
    const found = await page.evaluate((value) => {
      return [...document.querySelectorAll(`#stage > .slide.active ${value}`)].some((node) => {
        const rect = node.getBoundingClientRect();
        const style = getComputedStyle(node);
        return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
      });
    }, selector);
    if (found) return index;
  }
  throw new Error(`No slide has a visible ${selector}`);
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
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  try {
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    if (options.url.startsWith("file:")) {
      await page.goto(options.url, { waitUntil: "commit", timeout: 120000 });
    } else {
      await page.goto(options.url, { waitUntil: "commit", timeout: 120000 });
    }
    await Promise.race([page.evaluate(() => document.fonts?.ready), page.waitForTimeout(3000)]);
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
    ), null, { timeout: 120000 });

    const textSelector = '.slide.active [data-edit-layer="text"]';
    const visualSelector = '.slide.active [data-edit-layer="visual"]';
    const compositeSelector = '.slide.active .el[data-edit-composite]';

    // AI-generated composite roots are exposed as ordinary groups: first
    // click selects the group, then authors may ungroup/regroup or drill into a layer.
    await activateSlideWith(page, '[data-edit-layer="text"]');
    await clickCenter(page, textSelector);
    await clickCenter(page, textSelector);
    const textSelection = {
      label: await badgeLabel(page),
      font: await visible(page, "#edit-font-size-input"),
      frameWidth: await visible(page, "#edit-frame-width-input"),
      textTools: await visible(page, "#edit-text-tools"),
      colorTools: await visible(page, "#edit-color-tools"),
      objectTools: await visible(page, "#edit-object-tools"),
      fontDisabled: await allControlsDisabled(page, "#edit-font-size-input"),
      textToolsDisabled: await allControlsDisabled(page, "#edit-text-tools"),
      colorToolsDisabled: await allControlsDisabled(page, "#edit-color-tools"),
    };

    await activateSlideWith(page, '[data-edit-layer="visual"]');
    await clickExact(page, visualSelector);
    await clickExact(page, visualSelector);
    const visualBeforeCount = await visibleCount(page, visualSelector);
    const visualSelection = {
      label: await badgeLabel(page),
      font: await visible(page, "#edit-font-size-input"),
      frameWidth: await visible(page, "#edit-frame-width-input"),
      textTools: await visible(page, "#edit-text-tools"),
      colorTools: await visible(page, "#edit-color-tools"),
      objectTools: await visible(page, "#edit-object-tools"),
      fontDisabled: await allControlsDisabled(page, "#edit-font-size-input"),
      textToolsDisabled: await allControlsDisabled(page, "#edit-text-tools"),
      colorToolsDisabled: await allControlsDisabled(page, "#edit-color-tools"),
    };
    await page.locator('#edit-object-tools button[title="\u8907\u88fd"]').click();
    await page.waitForTimeout(100);
    const visualAfterDuplicateCount = await visibleCount(page, visualSelector);
    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(100);
    const visualAfterUndoCount = await visibleCount(page, visualSelector);

    await activateSlideWith(page, '.el[data-edit-composite]');
    await clickCenter(page, `${compositeSelector} [data-edit-layer="text"]`);
    const compositeSelection = {
      label: await badgeLabel(page),
      font: await visible(page, "#edit-font-size-input"),
      textTools: await visible(page, "#edit-text-tools"),
      colorTools: await visible(page, "#edit-color-tools"),
      objectTools: await visible(page, "#edit-object-tools"),
      groupTools: await visible(page, "#edit-group-tools"),
      memberFrames: await visibleCount(page, ".edit-selection-member-frame"),
      fontDisabled: await allControlsDisabled(page, "#edit-font-size-input"),
      textToolsDisabled: await allControlsDisabled(page, "#edit-text-tools"),
      colorToolsDisabled: await allControlsDisabled(page, "#edit-color-tools"),
    };
    const generatedGroupRoundTrip = await page.evaluate(() => {
      const root = document.querySelector('.slide.active .el[data-edit-composite]');
      window.EditMode.ungroup();
      const ungrouped = root?.dataset.editGroupState === 'ungrouped';
      window.EditMode.group();
      const regrouped = root && !root.dataset.editGroupState;
      const label = document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent?.trim() || '';
      return { ungrouped, regrouped, label };
    });
    await page.waitForTimeout(100);
    await clickCenter(page, `${compositeSelector} [data-edit-layer="text"]`);
    const layerSelection = {
      label: await badgeLabel(page),
      font: await visible(page, "#edit-font-size-input"),
      frameWidth: await visible(page, "#edit-frame-width-input"),
      textTools: await visible(page, "#edit-text-tools"),
      colorTools: await visible(page, "#edit-color-tools"),
      objectTools: await visible(page, "#edit-object-tools"),
      fontDisabled: await allControlsDisabled(page, "#edit-font-size-input"),
      textToolsDisabled: await allControlsDisabled(page, "#edit-text-tools"),
      colorToolsDisabled: await allControlsDisabled(page, "#edit-color-tools"),
    };

    const checks = {
      textSelectionUsable: textSelection.label === "\u5df2\u9078\u53d6\u6587\u5b57"
        && textSelection.font && textSelection.frameWidth && textSelection.textTools
        && textSelection.colorTools && textSelection.objectTools
        && !textSelection.fontDisabled && !textSelection.textToolsDisabled && !textSelection.colorToolsDisabled,
      visualSelectionHonest: visualSelection.objectTools && (
        (visualSelection.label === "\u5df2\u9078\u53d6\u5716\u5f62"
          && visualSelection.font && visualSelection.frameWidth
          && visualSelection.textTools && visualSelection.colorTools
          && visualSelection.fontDisabled && visualSelection.textToolsDisabled && visualSelection.colorToolsDisabled)
        || (visualSelection.label === "\u5df2\u9078\u53d6\u6587\u5b57"
          && !visualSelection.fontDisabled && !visualSelection.textToolsDisabled && !visualSelection.colorToolsDisabled)
      ),
      visualObjectActionUsable: visualAfterDuplicateCount === visualBeforeCount + 1
        && visualAfterUndoCount === visualBeforeCount,
      generatedGroupSelectionHonest: /^\u7fa4\u7d44\s*\u00d7\s*\d+$/.test(compositeSelection.label)
        && compositeSelection.font && compositeSelection.textTools
        && compositeSelection.colorTools && compositeSelection.objectTools
        && compositeSelection.fontDisabled && compositeSelection.textToolsDisabled && compositeSelection.colorToolsDisabled
        && compositeSelection.groupTools && compositeSelection.memberFrames > 0,
      generatedGroupRoundTrip: generatedGroupRoundTrip.ungrouped
        && generatedGroupRoundTrip.regrouped
        && /^\u7fa4\u7d44\s*\u00d7\s*\d+$/.test(generatedGroupRoundTrip.label),
      compositeTextLayerUsable: layerSelection.label === "\u5df2\u9078\u53d6\u6587\u5b57"
        && layerSelection.font && layerSelection.frameWidth && layerSelection.textTools
        && layerSelection.colorTools && layerSelection.objectTools
        && !layerSelection.fontDisabled && !layerSelection.textToolsDisabled && !layerSelection.colorToolsDisabled,
    };
    const result = {
      url: options.url,
      textSelection,
      visualSelection,
      visualBeforeCount,
      visualAfterDuplicateCount,
      visualAfterUndoCount,
      compositeSelection,
      generatedGroupRoundTrip,
      layerSelection,
      checks,
      pass: Object.values(checks).every(Boolean),
    };
    await fs.mkdir(path.dirname(path.resolve(options.report)), { recursive: true });
    await fs.writeFile(path.resolve(options.report), JSON.stringify(result, null, 2) + "\n", "utf8");
    console.log(JSON.stringify(result));
    if (!result.pass) process.exitCode = 1;
  } finally {
    await Promise.race([browser.close(), new Promise((resolve) => setTimeout(resolve, 2000))]);
  }
}

main()
  .then(() => process.exit(process.exitCode || 0))
  .catch((error) => { console.error(error); process.exit(1); });
