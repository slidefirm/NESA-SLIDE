const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

function argsOf(argv) {
  const out = {
    selector: '.slide.active [data-edit-kind="text"][data-edit-fit="text"]',
    slide: 0,
    panelOnly: false,
    ungroup: false,
  };
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--url") out.url = argv[++index];
    else if (argv[index] === "--selector") out.selector = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
    else if (argv[index] === "--slide") out.slide = Number.parseInt(argv[++index], 10);
    else if (argv[index] === "--panel-only") out.panelOnly = true;
    else if (argv[index] === "--ungroup") out.ungroup = true;
  }
  if (!out.url || !out.report) throw new Error("--url and --report are required");
  if (!Number.isInteger(out.slide) || out.slide < 0) throw new Error("--slide must be a non-negative integer");
  return out;
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
    await page.goto(options.url, { waitUntil: "commit", timeout: 120000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
    ), null, { timeout: 120000 });
    if (await page.evaluate(() => typeof window.setSlide === "function")) {
      await page.evaluate((slide) => window.setSlide(slide), options.slide);
      await page.waitForTimeout(120);
    }
    const target = page.locator(options.selector).first();
    await target.waitFor({ state: "visible" });
    const box = await target.boundingBox();
    if (!box) throw new Error("Target has no visible bounding box");
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
    await page.waitForTimeout(120);
    if (options.ungroup) {
      await page.evaluate(() => window.EditMode.ungroup());
      await page.waitForTimeout(120);
      const memberBox = await target.boundingBox();
      if (!memberBox) throw new Error("Target disappeared after ungroup");
      await page.mouse.click(memberBox.x + memberBox.width / 2, memberBox.y + memberBox.height / 2);
      await page.waitForTimeout(120);
    }

    const before = await page.evaluate((selector) => {
      const target = document.querySelector(selector);
      const badge = document.getElementById("edit-selection-badge");
      const frame = document.getElementById("edit-selection-frame");
      const bar = document.getElementById("bar");
      const fontInput = document.getElementById("edit-font-size-input");
      const frameWidthInput = document.getElementById("edit-frame-width-input");
      const badgeRect = badge?.getBoundingClientRect();
      const frameRect = frame?.getBoundingClientRect();
      const workspaceRect = document.getElementById("canvasBox")?.getBoundingClientRect();
      const expectedCenter = badgeRect && frameRect && workspaceRect
        ? Math.min(
            Math.max(
              (frameRect.left + frameRect.right) / 2,
              workspaceRect.left + 12 + badgeRect.width / 2
            ),
            workspaceRect.right - 12 - badgeRect.width / 2
          )
        : null;
      const relation = badgeRect && frameRect
        ? {
            placement: badge.dataset.placement || "",
            above: badgeRect.bottom <= frameRect.top + 1,
            below: badgeRect.top >= frameRect.bottom - 1,
            horizontalCenterDelta: expectedCenter === null ? null : Math.abs(
              (badgeRect.left + badgeRect.right) / 2 - expectedCenter
            ),
          }
        : null;
      return {
        targetText: target?.textContent?.trim() || "",
        fontSize: target ? parseFloat(getComputedStyle(target).fontSize) : 0,
        badgeRect: badgeRect ? {
          left: badgeRect.left,
          top: badgeRect.top,
          right: badgeRect.right,
          bottom: badgeRect.bottom,
          width: badgeRect.width,
          height: badgeRect.height,
        } : null,
        frameRect: frameRect ? {
          left: frameRect.left,
          top: frameRect.top,
          right: frameRect.right,
          bottom: frameRect.bottom,
          width: frameRect.width,
          height: frameRect.height,
          mode: frame.dataset.selectionMode || "",
        } : null,
        badgeVisible: Boolean(badge && getComputedStyle(badge).display !== "none"),
        badgeFloating: Boolean(badge
          && bar
          && badge.parentElement === document.body
          && getComputedStyle(badge).position === "fixed"
          && badge.getBoundingClientRect().top >= bar.getBoundingClientRect().bottom - 1),
        badgeRelation: relation,
        frameVisible: Boolean(frame && getComputedStyle(frame).display !== "none"),
        handlesVisible: [...document.querySelectorAll(".edit-resize-handle")]
          .filter((handle) => getComputedStyle(handle).display !== "none").length,
        fontControlVisible: Boolean(fontInput && getComputedStyle(fontInput.parentElement).display !== "none"),
        frameWidthControlAbsent: !frameWidthInput,
        fontInputDisabled: Boolean(fontInput?.disabled),
      };
    }, options.selector);

    await page.evaluate(() => {
      const input = document.getElementById("edit-font-size-input");
      const plus = input?.parentElement?.querySelector("button:last-of-type");
      plus?.click();
    });
    await page.waitForTimeout(120);
    const after = await page.evaluate((selector) => {
      const target = document.querySelector(selector);
      const input = document.getElementById("edit-font-size-input");
      const buttons = [...(input?.parentElement?.querySelectorAll("button") || [])].map((button) => ({
        text: button.textContent,
        title: button.title,
        disabled: button.disabled,
      }));
      return {
        fontSize: target ? parseFloat(getComputedStyle(target).fontSize) : 0,
        inlineFontSize: target?.style.fontSize || "",
        inputValue: input?.value || "",
        buttons,
      };
    }, options.selector);
    await page.evaluate(() => window.EditMode.undo());
    await page.waitForTimeout(120);
    const undoFont = await page.evaluate((selector) => {
      const target = document.querySelector(selector);
      return target ? parseFloat(getComputedStyle(target).fontSize) : 0;
    }, options.selector);

    const result = {
      url: options.url,
      selector: options.selector,
      slide: options.slide,
      panelOnly: options.panelOnly,
      ungroup: options.ungroup,
      before,
      after,
      undoFont,
      checks: {
        targetMatched: Boolean(before.targetText),
        badgeVisible: before.badgeVisible,
        floatingSelectionPanel: before.badgeFloating,
        selectionAnchoredPanel: Boolean(
          before.badgeRelation
          && ["above", "below"].includes(before.badgeRelation.placement)
          && (before.badgeRelation.above || before.badgeRelation.below)
          && before.badgeRelation.horizontalCenterDelta <= 2
        ),
        frameVisible: before.frameVisible,
        eightHandlesVisible: before.handlesVisible === 8,
        frameWidthControlRemoved: before.frameWidthControlAbsent,
      },
    };
    if (!options.panelOnly) {
      Object.assign(result.checks, {
        fontControlVisible: before.fontControlVisible && !before.fontInputDisabled,
        fontControlUsable: after.fontSize > before.fontSize,
        undoRestoresFont: Math.abs(undoFont - before.fontSize) <= 0.1,
      });
    }
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
  process.exitCode = 1;
});
