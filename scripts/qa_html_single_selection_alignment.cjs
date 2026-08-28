const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

function argsOf(argv) {
  const out = {
    selector: '.slide.active [data-edit-kind="text"][data-edit-fit="text"]',
  };
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--url") out.url = argv[++index];
    else if (argv[index] === "--selector") out.selector = argv[++index];
    else if (argv[index] === "--multi-selector") out.multiSelector = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
  }
  if (!out.url || !out.report) throw new Error("--url and --report are required");
  return out;
}

function closeEnough(actual, expected, tolerance = 0.35) {
  return Math.abs(actual - expected) <= tolerance;
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
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });

  async function logicalBox(selector) {
    return page.evaluate((targetSelector) => {
      const target = document.querySelector(targetSelector);
      const stage = document.getElementById("stage");
      if (!target || !stage) return null;
      const rect = target.getBoundingClientRect();
      const stageRect = stage.getBoundingClientRect();
      const scale = stageRect.width / 1920;
      return {
        left: (rect.left - stageRect.left) / scale,
        top: (rect.top - stageRect.top) / scale,
        right: (rect.right - stageRect.left) / scale,
        bottom: (rect.bottom - stageRect.top) / scale,
        width: rect.width / scale,
        height: rect.height / scale,
      };
    }, selector);
  }

  async function clickAlignment(mode) {
    await page.evaluate((alignmentMode) => {
      document.querySelector(`[data-align-selection-mode="${alignmentMode}"]`)?.click();
    }, mode);
    await page.waitForTimeout(100);
    return logicalBox(options.selector);
  }

  try {
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(options.url, { waitUntil: "commit", timeout: 120000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
    ), null, { timeout: 120000 });

    const target = page.locator(options.selector).first();
    await target.waitFor({ state: "visible" });
    const targetBox = await target.boundingBox();
    if (!targetBox) throw new Error("Target has no visible bounding box");
    await page.mouse.click(targetBox.x + targetBox.width / 2, targetBox.y + targetBox.height / 2);
    await page.waitForTimeout(120);

    const initial = await logicalBox(options.selector);
    const controls = await page.evaluate(() => {
      const align = [...document.querySelectorAll("[data-align-selection-mode]")].map((button) => ({
        mode: button.dataset.alignSelectionMode,
        disabled: button.disabled,
        title: button.title,
      }));
      const distribute = [...document.querySelectorAll("[data-distribute-selection-axis]")].map((button) => ({
        axis: button.dataset.distributeSelectionAxis,
        disabled: button.disabled,
      }));
      return { align, distribute };
    });

    const left = await clickAlignment("left");
    const centerX = await clickAlignment("centerX");
    const right = await clickAlignment("right");
    const top = await clickAlignment("top");
    const middle = await clickAlignment("middle");
    const bottom = await clickAlignment("bottom");

    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(100);
    const undo = await logicalBox(options.selector);

    let multiSelection = null;
    if (options.multiSelector) {
      const secondTarget = page.locator(options.multiSelector).first();
      await secondTarget.waitFor({ state: "visible" });
      const secondBox = await secondTarget.boundingBox();
      if (!secondBox) throw new Error("Multi-selection target has no visible bounding box");
      await page.keyboard.down("Shift");
      await page.mouse.click(secondBox.x + secondBox.width / 2, secondBox.y + secondBox.height / 2);
      await page.keyboard.up("Shift");
      await page.waitForTimeout(120);

      const before = await page.evaluate((selectors) => {
        const stage = document.getElementById("stage");
        const stageRect = stage.getBoundingClientRect();
        const scale = stageRect.width / 1920;
        return selectors.map((selector) => {
          const rect = document.querySelector(selector).getBoundingClientRect();
          return {
            left: (rect.left - stageRect.left) / scale,
            top: (rect.top - stageRect.top) / scale,
            width: rect.width / scale,
            height: rect.height / scale,
          };
        });
      }, [options.selector, options.multiSelector]);
      const multiControls = await page.evaluate(() => ({
        selectedCount: [...document.querySelectorAll(".edit-selection-member-frame")]
          .filter((frame) => getComputedStyle(frame).display !== "none").length,
        align: [...document.querySelectorAll("[data-align-selection-mode]")].map((button) => ({
          mode: button.dataset.alignSelectionMode,
          disabled: button.disabled,
          title: button.title,
        })),
        distribute: [...document.querySelectorAll("[data-distribute-selection-axis]")].map((button) => ({
          axis: button.dataset.distributeSelectionAxis,
          disabled: button.disabled,
        })),
      }));
      await page.evaluate(() => {
        document.querySelector('[data-align-selection-mode="left"]')?.click();
      });
      await page.waitForTimeout(100);
      const after = await page.evaluate((selectors) => {
        const stage = document.getElementById("stage");
        const stageRect = stage.getBoundingClientRect();
        const scale = stageRect.width / 1920;
        return selectors.map((selector) => {
          const rect = document.querySelector(selector).getBoundingClientRect();
          return {
            left: (rect.left - stageRect.left) / scale,
            top: (rect.top - stageRect.top) / scale,
            width: rect.width / scale,
            height: rect.height / scale,
          };
        });
      }, [options.selector, options.multiSelector]);
      const expectedLeft = Math.min(...before.map((box) => box.left));
      multiSelection = {
        selectors: [options.selector, options.multiSelector],
        before,
        after,
        controls: multiControls,
        checks: {
          twoTargetsSelected: multiControls.selectedCount === 2,
          alignmentButtonsEnabled: multiControls.align.length === 6
            && multiControls.align.every((button) => !button.disabled),
          tooltipsDescribeObjectAlignment: multiControls.align.every((button) => !button.title.includes("投影片")),
          distributionDisabledForTwo: multiControls.distribute.length === 2
            && multiControls.distribute.every((button) => button.disabled),
          leftUsesSelectionBounds: after.every((box) => closeEnough(box.left, expectedLeft)),
          sizesPreserved: after.every((box, index) => (
            closeEnough(box.width, before[index].width)
            && closeEnough(box.height, before[index].height)
          )),
        },
      };
      multiSelection.pass = Object.values(multiSelection.checks).every(Boolean);
    }

    const boxes = [left, centerX, right, top, middle, bottom];
    const sizePreserved = boxes.every((box) => (
      box
      && closeEnough(box.width, initial.width)
      && closeEnough(box.height, initial.height)
    ));
    const checks = {
      singleAlignmentButtonsEnabled: controls.align.length === 6
        && controls.align.every((button) => !button.disabled),
      singleAlignmentTooltipsNameSlide: controls.align.every((button) => button.title.includes("投影片")),
      distributionDisabledForSingle: controls.distribute.length === 2
        && controls.distribute.every((button) => button.disabled),
      leftUsesSlideEdge: closeEnough(left.left, 0),
      horizontalCenterUsesSlideCenter: closeEnough(centerX.left + centerX.width / 2, 960),
      rightUsesSlideEdge: closeEnough(right.right, 1920),
      topUsesSlideEdge: closeEnough(top.top, 0),
      verticalCenterUsesSlideCenter: closeEnough(middle.top + middle.height / 2, 540),
      bottomUsesSlideEdge: closeEnough(bottom.bottom, 1080),
      alignmentPreservesSize: sizePreserved,
      undoRestoresPreviousPosition: closeEnough(undo.top + undo.height / 2, 540),
    };
    const result = {
      url: options.url,
      selector: options.selector,
      initial,
      controls,
      positions: { left, centerX, right, top, middle, bottom, undo },
      multiSelection,
      checks,
      pass: Object.values(checks).every(Boolean) && (!multiSelection || multiSelection.pass),
    };
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
  process.exitCode = 1;
});
