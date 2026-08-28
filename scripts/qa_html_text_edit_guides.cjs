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
    else if (argv[index] === "--screenshot") out.screenshot = argv[++index];
  }
  if (!out.html || !out.report) throw new Error("--html and --report are required");
  return out;
}

async function main() {
  const options = argsOf(process.argv);
  const htmlPath = path.resolve(options.html);
  const reportPath = path.resolve(options.report);
  const candidates = [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  const executablePath = candidates.find((candidate) => fsSync.existsSync(candidate));
  if (!executablePath) throw new Error("No Chrome or Edge executable found");

  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
  await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
  try {
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForFunction(() => document.documentElement.dataset.layoutReady === "true", null, { timeout: 60000 });
    await page.evaluate(() => {
      const active = document.querySelector(".slide.active");
      const probe = document.createElement("div");
      probe.className = "el qa-text-guide-probe";
      probe.dataset.editLayer = "text";
      probe.dataset.editFit = "text";
      probe.textContent = "GUIDE";
      probe.style.cssText = [
        "position:absolute", "left:760px", "top:420px", "width:400px", "height:90px",
        "z-index:999", "display:flex", "align-items:center", "justify-content:center",
        "padding:0", "border:0", "background:transparent", "font:700 36px/1 sans-serif",
        "text-align:center", "color:#111827",
      ].join(";");
      active.appendChild(probe);
    });

    const probe = page.locator(".qa-text-guide-probe");
    await probe.click();
    await probe.click();
    await page.waitForTimeout(100);

    const during = await page.evaluate(() => {
      const guide = document.querySelector('.edit-guide-line[data-guide-axis="x"]');
      const stage = document.getElementById("stage");
      const frame = document.getElementById("edit-selection-frame");
      const guideRect = guide?.getBoundingClientRect();
      const stageRect = stage?.getBoundingClientRect();
      return {
        textEditing: document.querySelector(".qa-text-guide-probe")?.getAttribute("contenteditable") === "true",
        guideVisible: Boolean(guide && getComputedStyle(guide).display !== "none"),
        guideAxis: guide?.dataset.guideAxis || "",
        guideSource: guide?.dataset.guideSource || "",
        centered: Boolean(guideRect && stageRect && Math.abs(guideRect.left - (stageRect.left + stageRect.width / 2)) <= 1.5),
        spansStage: Boolean(guideRect && stageRect && Math.abs(guideRect.top - stageRect.top) <= 1.5
          && Math.abs(guideRect.height - stageRect.height) <= 2),
        textFrameVisible: Boolean(frame && getComputedStyle(frame).display !== "none"
          && frame.dataset.selectionMode === "text-edit"),
      };
    });

    if (options.screenshot) {
      const screenshotPath = path.resolve(options.screenshot);
      await fs.mkdir(path.dirname(screenshotPath), { recursive: true });
      await page.screenshot({ path: screenshotPath, fullPage: false });
    }

    await page.evaluate(() => window.EditMode.toggle(false));
    await page.waitForTimeout(80);
    const hiddenInProjection = await page.evaluate(() => {
      const guides = [...document.querySelectorAll(".edit-guide-line")];
      return guides.every((guide) => getComputedStyle(guide).display === "none");
    });

    const report = {
      html: htmlPath,
      ...during,
      hiddenInProjection,
      pass: during.textEditing && during.guideVisible && during.guideAxis === "x"
        && during.centered && during.spansStage && during.textFrameVisible && hiddenInProjection,
    };
    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + "\n", "utf8");
    console.log(JSON.stringify(report));
    if (!report.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
