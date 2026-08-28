const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { chromium } = require("playwright");

function portablePath(value) {
  if (!value) return null;
  return path.relative(process.cwd(), value).split(path.sep).join("/");
}

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--html") out.html = argv[++index];
    else if (argv[index] === "--url") out.url = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
    else if (argv[index] === "--screenshot") out.screenshot = argv[++index];
    else if (argv[index] === "--profile") out.profile = argv[++index];
    else if (argv[index] === "--selector") out.selector = argv[++index];
  }
  if ((!out.html && !out.url) || !out.report || !out.screenshot) {
    throw new Error("--html or --url, plus --report and --screenshot, are required");
  }
  return out;
}

async function main() {
  const options = argsOf(process.argv);
  const htmlPath = options.html ? path.resolve(options.html) : null;
  const pageUrl = options.url || pathToFileURL(htmlPath).href;
  const reportPath = path.resolve(options.report);
  const screenshotPath = path.resolve(options.screenshot);
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
    await page.goto(pageUrl, { waitUntil: "commit", timeout: 30000 });
    if (options.selector) await page.waitForSelector(options.selector);
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true"
      && Boolean(window.EditMode)
      && Boolean(window.SlidePlayer)
      && document.querySelectorAll(".slide-thumb").length > 0
    ));

    const snapshot = () => page.evaluate(() => {
      const player = document.getElementById("player");
      const rail = document.getElementById("slideRail");
      const header = document.getElementById("slideRailHeader");
      const list = document.getElementById("slideThumbList");
      const toggle = document.getElementById("slideRailToggle");
      const bar = document.getElementById("bar");
      const canvas = document.getElementById("canvasBox");
      const stage = document.getElementById("stage");
      const railRect = rail.getBoundingClientRect();
      const headerRect = header.getBoundingClientRect();
      const listRect = list.getBoundingClientRect();
      const barRect = bar.getBoundingClientRect();
      const canvasRect = canvas.getBoundingClientRect();
      const stageRect = stage.getBoundingClientRect();
      const thumbnailFit = Array.from(list.querySelectorAll(".slide-thumb-preview")).map((preview) => {
        const canvas = preview.querySelector(".slide-thumb-canvas");
        const previewRect = preview.getBoundingClientRect();
        const canvasRect = canvas ? canvas.getBoundingClientRect() : { width: 0, height: 0, right: 0, bottom: 0 };
        return {
          rightOverflow: Math.max(0, canvasRect.right - previewRect.right),
          bottomOverflow: Math.max(0, canvasRect.bottom - previewRect.bottom),
          aspectDelta: canvasRect.height > 0 ? Math.abs(canvasRect.width / canvasRect.height - 16 / 9) : 0,
        };
      });
      return {
        collapsed: player.classList.contains("rail-collapsed"),
        apiCollapsed: window.SlidePlayer.isRailCollapsed(),
        viewportHeight: window.innerHeight,
        railTop: railRect.top,
        railBottom: railRect.bottom,
        railWidth: railRect.width,
        headerTop: headerRect.top,
        headerBottom: headerRect.bottom,
        listTop: listRect.top,
        listBottom: listRect.bottom,
        barLeft: barRect.left,
        canvasLeft: canvasRect.left,
        canvasWidth: canvasRect.width,
        canvasHeight: canvasRect.height,
        stageWidth: stageRect.width,
        stageHeight: stageRect.height,
        slideCount: document.querySelectorAll("#stage .slide").length,
        thumbCount: list.querySelectorAll(".slide-thumb").length,
        thumbDisplay: getComputedStyle(list).display,
        thumbnailCanvasCount: thumbnailFit.length,
        thumbnailMaxRightOverflow: Math.max(0, ...thumbnailFit.map((item) => item.rightOverflow)),
        thumbnailMaxBottomOverflow: Math.max(0, ...thumbnailFit.map((item) => item.bottomOverflow)),
        thumbnailMaxAspectDelta: Math.max(0, ...thumbnailFit.map((item) => item.aspectDelta)),
        ariaExpanded: toggle.getAttribute("aria-expanded"),
        ariaLabel: toggle.getAttribute("aria-label"),
      };
    });

    const expanded = await snapshot();
    await page.click("#slideRailToggle");
    await page.waitForTimeout(80);
    const collapsed = await snapshot();
    await fs.mkdir(path.dirname(screenshotPath), { recursive: true });
    await page.screenshot({ path: screenshotPath });
    await page.click("#slideRailToggle");
    await page.waitForTimeout(80);
    const restored = await snapshot();

    const near = (left, right, tolerance = 1) => Math.abs(left - right) <= tolerance;
    const checks = {
      initialExpanded: !expanded.collapsed && !expanded.apiCollapsed,
      hasThumbnails: expanded.slideCount > 0
        && expanded.thumbCount === expanded.slideCount
        && expanded.thumbDisplay !== "none",
      expandedWidth: near(expanded.railWidth, 232),
      railUsesFullHeight: near(expanded.railTop, 0)
        && near(expanded.railBottom, expanded.viewportHeight),
      headerUsesTopSpace: near(expanded.headerTop, 0),
      thumbnailListFillsRemainingHeight: near(expanded.listTop, expanded.headerBottom)
        && near(expanded.listBottom, expanded.viewportHeight),
      thumbnailsShowCompleteSlides: expanded.thumbnailCanvasCount === expanded.slideCount
        && expanded.thumbnailMaxRightOverflow <= 0.5
        && expanded.thumbnailMaxBottomOverflow <= 0.5
        && expanded.thumbnailMaxAspectDelta <= 0.001,
      collapsedState: collapsed.collapsed && collapsed.apiCollapsed,
      collapsedWidth: near(collapsed.railWidth, 44),
      collapsedTopbar: near(collapsed.barLeft, 44),
      collapsedThumbsHidden: collapsed.thumbDisplay === "none",
      collapsedAccessibility: collapsed.ariaExpanded === "false" && collapsed.ariaLabel === "展開投影片縮圖",
      canvasRefit: collapsed.canvasLeft < expanded.canvasLeft - 20,
      canvasAspect: near(collapsed.stageWidth / collapsed.stageHeight, 16 / 9, 0.005),
      restoredState: !restored.collapsed && !restored.apiCollapsed && restored.thumbDisplay !== "none",
      restoredGeometry: near(restored.railWidth, expanded.railWidth) && near(restored.canvasLeft, expanded.canvasLeft),
      restoredFullHeight: near(restored.railTop, 0)
        && near(restored.railBottom, restored.viewportHeight)
        && near(restored.headerTop, 0)
        && near(restored.listTop, restored.headerBottom)
        && near(restored.listBottom, restored.viewportHeight),
      restoredAccessibility: restored.ariaExpanded === "true" && restored.ariaLabel === "收合投影片縮圖",
    };
    const report = {
      html: portablePath(htmlPath),
      url: pageUrl,
      profile: options.profile || null,
      selector: options.selector || null,
      screenshot: portablePath(screenshotPath),
      expanded,
      collapsed,
      restored,
      checks,
      pass: Object.values(checks).every(Boolean),
    };
    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
    process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
    if (!report.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
