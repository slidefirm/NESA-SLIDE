const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--html") out.html = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
  }
  if (!out.html || !out.report) throw new Error("--html and --report are required");
  return out;
}

async function main() {
  const options = argsOf(process.argv);
  const htmlPath = path.resolve(options.html);
  const reportPath = path.resolve(options.report);
  const browserCandidates = [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  const executablePath = browserCandidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  let result;

  try {
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "commit", timeout: 30000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
    ), null, { timeout: 120000 });

    result = await page.evaluate(async () => {
      const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const click = (el) => {
        if (!el) return;
        const rect = el.getBoundingClientRect();
        const eventInit = {
          bubbles: true,
          button: 0,
          clientX: rect.left + Math.max(2, Math.min(12, rect.width / 2)),
          clientY: rect.top + Math.max(2, Math.min(12, rect.height / 2)),
        };
        ["mousedown", "mouseup", "click"].forEach((type) => {
          el.dispatchEvent(new MouseEvent(type, eventInit));
        });
      };
      const slide = document.querySelector("#stage > .slide .column-grid")?.closest(".slide");
      if (!slide) return { pass: false, error: "column slide missing" };
      window.setSlide(Number(slide.dataset.index));
      window.EditMode.toggle(true);
      await frame();

      const centeringFrames = [...slide.querySelectorAll('[data-edit-layout-only="true"]')];
      const cards = [...slide.querySelectorAll(".column-grid > .el.column-item")];
      const title = slide.querySelector(".el.scene-title");
      const subtitle = slide.querySelector(".el.scene-intro");
      const titleRect = title?.getBoundingClientRect();
      const titleHit = titleRect
        ? document.elementFromPoint(titleRect.left + Math.min(24, titleRect.width / 2), titleRect.top + Math.min(20, titleRect.height / 2))
        : null;
      const structure = {
        centeringFrameCount: centeringFrames.length,
        centeringFramesSelectable: centeringFrames.filter((node) => node.matches('.el,[data-edit-layer],[data-edit-composite]')).length,
        generatedAggregateGroupCount: slide.querySelectorAll('.el[data-edit-structure="group"],.el[data-edit-role="title-group"],.el[data-edit-role="content-group"],.el[data-edit-role="extra-group"]').length,
        titleIsLooseText: Boolean(title?.matches('.el[data-edit-layer="text"]')),
        subtitleIsLooseText: Boolean(subtitle?.matches('.el[data-edit-layer="text"]')),
        cardCount: cards.length,
        cardCompositeCount: cards.filter((card) => card.matches('.el[data-edit-structure="module"][data-edit-composite]')).length,
        retiredAttributeCount: slide.querySelectorAll('[data-edit-repeat-group],[data-edit-repeat-layout],[data-edit-repeat-connectors]').length,
        backgroundLayerCount: cards.filter((card) =>
          Boolean(card.querySelector(':scope > [data-edit-layer="background"]'))).length,
        textLayerCounts: cards.map((card) =>
          card.querySelectorAll(':scope > [data-edit-layer="text"]').length),
      };

      click(titleHit);
      await frame();
      const titleSelection = {
        selectedClass: titleHit?.closest(".el")?.className || "",
        selectionMode: document.getElementById("edit-selection-frame")?.dataset.selectionMode || "",
        label: document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent || "",
      };

      click(cards[0]);
      await frame();
      const moduleSelection = {
        composite: cards[0].dataset.editComposite || "",
        selectionMode: document.getElementById("edit-selection-frame")?.dataset.selectionMode || "",
        label: document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent || "",
        ungroupDisabled: document.querySelector('#edit-group-tools [data-action="ungroup"]')?.getAttribute("aria-disabled") || "",
      };
      window.EditMode.ungroup();
      await frame();
      const firstBackground = cards[0].querySelector(':scope > [data-edit-layer="background"]');
      click(firstBackground);
      await frame();
      const cardUngroup = {
        state: cards[0].dataset.editGroupState || "",
        selectionMode: document.getElementById("edit-selection-frame")?.dataset.selectionMode || "",
        backgroundLayers: cards[0].querySelectorAll(':scope > [data-edit-layer="background"]').length,
        textLayers: cards[0].querySelectorAll(':scope > [data-edit-layer="text"]').length,
      };

      const pass = structure.centeringFrameCount >= 1
        && structure.centeringFramesSelectable === 0
        && structure.generatedAggregateGroupCount === 0
        && structure.titleIsLooseText
        && structure.subtitleIsLooseText
        && structure.cardCount === 4
        && structure.cardCompositeCount === 4
        && structure.retiredAttributeCount === 0
        && structure.backgroundLayerCount === 4
        && structure.textLayerCounts.every((count) => count === 3)
        && titleSelection.selectedClass.includes("scene-title")
        && titleSelection.selectionMode === "single"
        && moduleSelection.selectionMode === "group"
        && cardUngroup.state === "ungrouped"
        && cardUngroup.selectionMode === "single"
        && cardUngroup.backgroundLayers === 1
        && cardUngroup.textLayers === 3;

      return {
        pass,
        structure,
        titleSelection,
        moduleSelection,
        cardUngroup,
      };
    });
  } finally {
    await Promise.race([browser.close(), new Promise((resolve) => setTimeout(resolve, 2000))]);
  }

  await fs.mkdir(path.dirname(reportPath), { recursive: true });
  await fs.writeFile(reportPath, JSON.stringify({ html: htmlPath, ...result }, null, 2), "utf8");
  console.log(JSON.stringify(result));
  if (!result.pass) process.exitCode = 1;
}

main()
  .then(() => process.exit(process.exitCode || 0))
  .catch((error) => {
    console.error(error.stack || error.message || String(error));
    process.exit(1);
  });
