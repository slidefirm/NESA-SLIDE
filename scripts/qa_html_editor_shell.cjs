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
  const browserCandidates = [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  const executablePath = browserCandidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  try {
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "commit", timeout: 30000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true"
      && Boolean(window.EditMode)
      && Boolean(window.SlidePlayer)
    ), null, { timeout: 120000 });
    await page.waitForTimeout(450);

    const shellState = () => page.evaluate(() => {
      const player = document.getElementById("player");
      const rail = document.getElementById("slideRail");
      const bar = document.getElementById("bar");
      const hint = document.getElementById("hint");
      const badge = document.getElementById("edit-selection-badge");
      const barRect = bar.getBoundingClientRect();
      const slides = [...document.querySelectorAll("#stage > .slide")];
      const thumbnailCorrespondence = [...document.querySelectorAll(".slide-thumb")].map((thumb, index) => {
        const slide = slides[index];
        const host = thumb.querySelector('.slide-thumb-canvas[data-thumbnail-clone="true"]');
        const mirror = host?.shadowRoot?.querySelector("#stage > .slide");
        const originalSlideStyle = slide?.getAttribute("style");
        const temporarilyReveal = Boolean(slide && !slide.classList.contains("active"));
        if (temporarilyReveal) {
          slide.style.setProperty("display", "block", "important");
        }
        const normalize = (value) => (value || "").replace(/\s+/g, "").trim();
        const visualStyleKeys = [
          "display", "visibility", "overflow",
          "color", "backgroundColor", "backgroundImage", "border", "borderRadius",
          "boxShadow", "opacity", "fontFamily", "fontSize", "fontWeight",
          "lineHeight", "letterSpacing", "transform",
        ];
        const isRenderableNode = (node) => !/^(SCRIPT|STYLE|LINK|DEFS|MARKER|CLIPPATH|MASK|PATTERN)$/.test(node.tagName)
          && !node.closest("defs,marker,clipPath,mask,pattern");
        const sourceNodes = slide ? [...slide.querySelectorAll("*")].filter(isRenderableNode) : [];
        const mirrorNodes = mirror ? [...mirror.querySelectorAll("*")].filter(isRenderableNode) : [];
        const visualStylesMatch = sourceNodes.length === mirrorNodes.length && sourceNodes.every((node, nodeIndex) => {
          const sourceStyle = getComputedStyle(node);
          const mirrorStyle = getComputedStyle(mirrorNodes[nodeIndex]);
          const sourceAlign = sourceStyle.textAlign === "start" ? "left"
            : sourceStyle.textAlign === "end" ? "right"
              : sourceStyle.textAlign;
          const mirrorAlign = mirrorStyle.textAlign === "start" ? "left"
            : mirrorStyle.textAlign === "end" ? "right"
              : mirrorStyle.textAlign;
          return sourceAlign === mirrorAlign
            && visualStyleKeys.every((key) => sourceStyle[key] === mirrorStyle[key]);
        });
        const geometryOf = (node, rootRect) => {
          const rect = node.getBoundingClientRect();
          return [
            (rect.left - rootRect.left) / rootRect.width * 1920,
            (rect.top - rootRect.top) / rootRect.height * 1080,
            rect.width / rootRect.width * 1920,
            rect.height / rootRect.height * 1080,
          ];
        };
        const sourceRootRect = slide?.getBoundingClientRect();
        const mirrorRootRect = mirror?.getBoundingClientRect();
        const geometryMatches = Boolean(sourceRootRect?.width && sourceRootRect?.height
          && mirrorRootRect?.width && mirrorRootRect?.height)
          && sourceNodes.length === mirrorNodes.length
          && sourceNodes.every((node, nodeIndex) => {
            const sourceGeometry = geometryOf(node, sourceRootRect);
            const mirrorGeometry = geometryOf(mirrorNodes[nodeIndex], mirrorRootRect);
            return sourceGeometry.every((value, geometryIndex) => (
              Math.abs(value - mirrorGeometry[geometryIndex]) <= 0.75
            ));
          });
        const sourceRootStyle = slide ? getComputedStyle(slide) : null;
        const mirrorRootStyle = mirror ? getComputedStyle(mirror) : null;
        const rootAppearanceMatches = Boolean(sourceRootStyle && mirrorRootStyle)
          && ["backgroundColor", "backgroundImage", "color", "borderRadius", "opacity"]
            .every((key) => sourceRootStyle[key] === mirrorRootStyle[key]);
        const result = {
          slideId: slide?.id || "",
          thumbSlideId: thumb.dataset.slideId || "",
          clonePresent: Boolean(host),
          mirrorPresent: Boolean(mirror),
          cloneLayoutId: mirror?.dataset.layoutId || "",
          slideLayoutId: slide?.dataset.layoutId || "",
          textMatches: normalize(mirror?.textContent) === normalize(slide?.textContent),
          editableObjectCountMatches: mirror?.querySelectorAll(".el").length === slide?.querySelectorAll(".el").length,
          visualStylesMatch,
          geometryMatches,
          rootAppearanceMatches,
        };
        if (temporarilyReveal) {
          if (originalSlideStyle === null) slide.removeAttribute("style");
          else slide.setAttribute("style", originalSlideStyle);
        }
        return result;
      });
      return {
        editorShell: player.classList.contains("editor-shell"),
        documentSlideCount: document.querySelectorAll(".slide").length,
        railVisible: getComputedStyle(rail).display !== "none",
        topbarDocked: Math.abs(barRect.top) <= 1,
        hintVisible: getComputedStyle(hint).display !== "none",
        frameVisible: getComputedStyle(document.getElementById("edit-selection-frame")).display !== "none",
        badgeVisible: getComputedStyle(badge).display !== "none",
        badgeFloating: badge.parentElement === document.body
          && getComputedStyle(badge).position === "fixed"
          && badge.getBoundingClientRect().top >= barRect.bottom - 1,
        visibleHandles: [...document.querySelectorAll(".edit-resize-handle")]
          .filter((handle) => getComputedStyle(handle).display !== "none").length,
        order: slides.map((slide) => slide.id),
        thumbOrder: [...document.querySelectorAll(".slide-thumb")].map((thumb) => thumb.dataset.slideId),
        thumbnailCorrespondence,
        counter: document.querySelector("#barInner .counter")?.textContent || "",
      };
    });

    const initial = await shellState();
    const target = page.locator("#stage > .slide.active .el").filter({ hasText: /\S/ }).first();
    await target.click();
    await page.waitForTimeout(80);
    const selected = await shellState();

    const thumbs = page.locator(".slide-thumb");
    const firstBox = await thumbs.nth(0).boundingBox();
    const secondBox = await thumbs.nth(1).boundingBox();
    if (!firstBox || !secondBox) throw new Error("Unable to measure slide thumbnails");
    await page.mouse.move(firstBox.x + firstBox.width / 2, firstBox.y + firstBox.height / 2);
    await page.mouse.down();
    await page.mouse.move(secondBox.x + secondBox.width / 2, secondBox.y + secondBox.height * 0.8, { steps: 8 });
    await page.mouse.up();
    await page.waitForTimeout(120);
    const reordered = await shellState();
    await page.keyboard.press("Control+z");
    await page.waitForTimeout(100);
    const undo = await shellState();
    await page.keyboard.press("Control+y");
    await page.waitForTimeout(100);
    const redo = await shellState();
    await page.keyboard.press("Control+z");

    await page.evaluate(() => window.EditMode.toggle(false));
    await page.waitForTimeout(360);
    const presentation = await shellState();
    await page.evaluate(() => window.EditMode.toggle(true));
    await page.waitForTimeout(200);
    const restoredEdit = await shellState();

    const originalOrder = initial.order.join("|");
    const movedOrder = reordered.order.join("|");
    const result = {
      initial,
      selected,
      reordered,
      undo,
      redo,
      presentation,
      restoredEdit,
      checks: {
        editorChrome: initial.editorShell && initial.railVisible && initial.topbarDocked,
        realThumbnailCorrespondence: initial.thumbnailCorrespondence.length === initial.order.length
          && initial.thumbnailCorrespondence.every((item) => item.clonePresent
            && item.slideId === item.thumbSlideId
            && item.mirrorPresent
            && item.cloneLayoutId === item.slideLayoutId
            && item.textMatches
            && item.editableObjectCountMatches
            && item.visualStylesMatch
            && item.geometryMatches
            && item.rootAppearanceMatches)
          && initial.documentSlideCount === initial.order.length,
        noCornerReadout: !initial.hintVisible && !selected.hintVisible && !presentation.hintVisible,
        selectionPanelStartsHidden: !initial.badgeVisible,
        selectionVisible: selected.frameVisible && selected.badgeVisible
          && selected.badgeFloating && selected.visibleHandles === 8,
        reorderApplied: movedOrder !== originalOrder
          && reordered.order.join("|") === reordered.thumbOrder.join("|")
          && reordered.counter.startsWith("02 /"),
        reorderUndo: undo.order.join("|") === originalOrder,
        reorderRedo: redo.order.join("|") === movedOrder,
        projectionSeparated: !presentation.editorShell && !presentation.railVisible
          && !presentation.frameVisible && !presentation.badgeVisible,
        editorRestored: restoredEdit.editorShell && restoredEdit.railVisible && restoredEdit.topbarDocked,
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
