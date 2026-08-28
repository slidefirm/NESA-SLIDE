const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

function argsOf(argv) {
  const args = {};
  for (let index = 2; index < argv.length; index += 2) {
    args[argv[index].replace(/^--/, "")] = argv[index + 1];
  }
  if (!args.url || !args.report) throw new Error("--url and --report are required");
  return args;
}

async function main() {
  const args = argsOf(process.argv);
  const executablePath = [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean).find((candidate) => fsSync.existsSync(candidate));
  if (!executablePath) throw new Error("No Chrome or Edge executable found");

  const browser = await chromium.launch({ headless: true, executablePath });
  try {
    const page = await browser.newPage({ viewport: { width: 1800, height: 1000 } });
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(args.url, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForFunction(
      () => document.documentElement.dataset.layoutReady === "true",
      null,
      { timeout: 60000 },
    );
    await page.evaluate(() => document.fonts?.ready || Promise.resolve());

    const slideCount = await page.locator(".slide").count();
    const slides = [];
    for (let index = 0; index < slideCount; index += 1) {
      await page.evaluate((slideIndex) => window.setSlide(slideIndex), index);
      const result = await page.evaluate(() => {
        const slide = document.querySelector(".slide.active");
        const slideRect = slide.getBoundingClientRect();
        const scale = slide.offsetWidth ? slideRect.width / slide.offsetWidth : 1;
        const round = (value) => Math.round(value / scale * 100) / 100;
        const visible = (node) => {
          const style = getComputedStyle(node);
          const rect = node.getBoundingClientRect();
          return style.display !== "none" && style.visibility !== "hidden"
            && rect.width > 0.5 && rect.height > 0.5;
        };
        const textRect = (node) => {
          const range = document.createRange();
          range.selectNodeContents(node);
          const measured = range.getBoundingClientRect();
          return measured.width > 0.5 && measured.height > 0.5
            ? measured
            : node.getBoundingClientRect();
        };
        const overlaps = (a, b, tolerance = 0.5 * scale) => (
          a.left < b.right - tolerance
          && a.right > b.left + tolerance
          && a.top < b.bottom - tolerance
          && a.bottom > b.top + tolerance
        );
        const issues = [];

        for (const layer of slide.querySelectorAll("[data-edit-layer]")) {
          const position = layer.dataset.editPosition;
          if (!["absolute", "flow"].includes(position)) {
            issues.push({
              type: "missing-edit-position",
              element: layer.className || layer.tagName.toLowerCase(),
              position: position || null,
            });
          }
        }

        for (const layer of slide.querySelectorAll('[data-edit-position="flow"]')) {
          if (!visible(layer)) continue;
          const style = getComputedStyle(layer);
          const rect = textRect(layer);
          if (["absolute", "fixed"].includes(style.position)) {
            issues.push({
              type: "flow-became-absolute",
              element: layer.className || layer.tagName.toLowerCase(),
              computedPosition: style.position,
            });
          }
          const parent = layer.parentElement;
          if (parent && parent.tagName === "LI") {
            const parentRect = parent.getBoundingClientRect();
            if (rect.top < parentRect.top - scale || rect.bottom > parentRect.bottom + scale) {
              issues.push({
                type: "flow-does-not-size-list-row",
                element: layer.className || layer.tagName.toLowerCase(),
                rowHeight: round(parentRect.height),
                textHeight: round(rect.height),
              });
            }
          }

          let ancestor = parent;
          while (ancestor && ancestor !== slide) {
            if (visible(ancestor)) {
              const ancestorRect = ancestor.getBoundingClientRect();
              const ancestorStyle = getComputedStyle(ancestor);
              const borders = [
                {
                  edge: "top",
                  width: parseFloat(ancestorStyle.borderTopWidth) || 0,
                  rect: {
                    left: ancestorRect.left,
                    right: ancestorRect.right,
                    top: ancestorRect.top,
                    bottom: ancestorRect.top + (parseFloat(ancestorStyle.borderTopWidth) || 0),
                  },
                },
                {
                  edge: "bottom",
                  width: parseFloat(ancestorStyle.borderBottomWidth) || 0,
                  rect: {
                    left: ancestorRect.left,
                    right: ancestorRect.right,
                    top: ancestorRect.bottom - (parseFloat(ancestorStyle.borderBottomWidth) || 0),
                    bottom: ancestorRect.bottom,
                  },
                },
                {
                  edge: "left",
                  width: parseFloat(ancestorStyle.borderLeftWidth) || 0,
                  rect: {
                    left: ancestorRect.left,
                    right: ancestorRect.left + (parseFloat(ancestorStyle.borderLeftWidth) || 0),
                    top: ancestorRect.top,
                    bottom: ancestorRect.bottom,
                  },
                },
                {
                  edge: "right",
                  width: parseFloat(ancestorStyle.borderRightWidth) || 0,
                  rect: {
                    left: ancestorRect.right - (parseFloat(ancestorStyle.borderRightWidth) || 0),
                    right: ancestorRect.right,
                    top: ancestorRect.top,
                    bottom: ancestorRect.bottom,
                  },
                },
              ];
              for (const border of borders) {
                if (border.width > 0 && overlaps(rect, border.rect)) {
                  issues.push({
                    type: "rule-crosses-flow-text",
                    element: layer.className || layer.tagName.toLowerCase(),
                    ancestor: ancestor.className || ancestor.tagName.toLowerCase(),
                    edge: border.edge,
                  });
                }
              }
            }
            ancestor = ancestor.parentElement;
          }
        }
        return {
          index: Number(slide.dataset.index),
          layoutId: slide.dataset.layoutId,
          flowLayers: slide.querySelectorAll('[data-edit-position="flow"]').length,
          issues,
          pass: issues.length === 0,
        };
      });
      slides.push(result);
    }

    const focusIndex = Math.max(0, Math.min(
      slideCount - 1,
      Number.parseInt(args.slide || "7", 10),
    ));
    await page.evaluate((slideIndex) => window.setSlide(slideIndex), focusIndex);
    if (args.screenshot) {
      await fs.mkdir(path.dirname(path.resolve(args.screenshot)), { recursive: true });
      await page.locator(".slide.active").screenshot({ path: path.resolve(args.screenshot) });
    }

    await page.evaluate((slideIndex) => {
      window.setSlide(slideIndex);
      window.EditMode.toggle(true);
    }, focusIndex);
    const flowTarget = page.locator(
      '.slide.active [data-edit-position="flow"][data-edit-layer="text"]',
    ).first();
    const flowTargetBox = await flowTarget.evaluate((layer) => {
      const range = document.createRange();
      range.selectNodeContents(layer);
      const textRect = range.getBoundingClientRect();
      const rect = textRect.width > 0.5 && textRect.height > 0.5
        ? textRect
        : layer.getBoundingClientRect();
      return { x: rect.left, y: rect.top, width: rect.width, height: rect.height };
    });
    if (!flowTargetBox) throw new Error("No visible flow text layer on focus slide");
    await page.mouse.click(
      flowTargetBox.x + flowTargetBox.width / 2,
      flowTargetBox.y + flowTargetBox.height / 2,
    );
    await page.waitForTimeout(100);
    const groupedSelection = await page.evaluate(() => ({
      label: document.querySelector('#edit-selection-badge [data-role="label"]')
        ?.textContent?.trim() || "",
    }));
    await page.evaluate(() => window.EditMode.ungroup());
    await page.waitForTimeout(100);
    await page.mouse.click(
      flowTargetBox.x + flowTargetBox.width / 2,
      flowTargetBox.y + flowTargetBox.height / 2,
    );
    await page.waitForTimeout(100);
    const ungroupedSelection = await page.evaluate(() => {
      const layer = document.querySelector(
        '.slide.active [data-edit-position="flow"][data-edit-layer="text"]',
      );
      const root = layer?.closest(".el");
       const contentRoot = layer?.closest('.scene-content[data-edit-layout-only="true"]');
      const frame = document.getElementById("edit-selection-frame");
      const layerRect = layer?.getBoundingClientRect();
      const range = document.createRange();
      if (layer) range.selectNodeContents(layer);
      const textRect = layer ? range.getBoundingClientRect() : null;
      const rootRect = root?.getBoundingClientRect();
      const frameRect = frame?.getBoundingClientRect();
      const close = (a, b, tolerance = 2) => Math.abs(a - b) <= tolerance;
      return {
        label: document.querySelector('#edit-selection-badge [data-role="label"]')
          ?.textContent?.trim() || "",
        rootState: root?.dataset.editGroupState || "",
         contentRootEditable: Boolean(contentRoot?.matches('.el,[data-edit-layer],[data-edit-composite]')),
        computedPosition: layer ? getComputedStyle(layer).position : "",
        frameMatchesText: Boolean(textRect && frameRect
          && close(textRect.left, frameRect.left)
          && close(textRect.top, frameRect.top)
          && close(textRect.width, frameRect.width)
          && close(textRect.height, frameRect.height)),
        frameMatchesRoot: Boolean(rootRect && frameRect
          && close(rootRect.left, frameRect.left)
          && close(rootRect.top, frameRect.top)
          && close(rootRect.width, frameRect.width)
          && close(rootRect.height, frameRect.height)),
      };
    });
    const editorFlowSelection = {
      groupedSelection,
      ungroupedSelection,
      pass: /^已選取群組/.test(groupedSelection.label)
        && ungroupedSelection.rootState === "ungrouped"
        && !ungroupedSelection.contentRootEditable
        && ungroupedSelection.label === "已選取文字"
        && ungroupedSelection.computedPosition !== "absolute"
        && ungroupedSelection.frameMatchesText
        && !ungroupedSelection.frameMatchesRoot,
    };

    const report = {
      url: args.url,
      slideCount,
      slides,
      editorFlowSelection,
      issueCount: slides.reduce((sum, slide) => sum + slide.issues.length, 0),
      pass: slides.every((slide) => slide.pass) && editorFlowSelection.pass,
    };
    await fs.mkdir(path.dirname(path.resolve(args.report)), { recursive: true });
    await fs.writeFile(path.resolve(args.report), `${JSON.stringify(report, null, 2)}\n`, "utf8");
    process.stdout.write(`${JSON.stringify(report)}\n`);
    if (!report.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
