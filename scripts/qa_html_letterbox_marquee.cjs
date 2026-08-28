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
    else if (argv[index] === "--slide") out.slide = Number(argv[++index]);
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
  if (!executablePath) throw new Error("No Chrome or Edge executable found for HTML QA");

  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
  await page.route("https://fonts.gstatic.com/**", (route) => route.abort());

  let report;
  try {
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "commit", timeout: 30000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
    ), null, { timeout: 120000 });
    if (Number.isInteger(options.slide)) {
      await page.evaluate((index) => window.setSlide(index), options.slide);
    }

    const geometry = await page.evaluate(() => {
      const player = document.getElementById("player");
      const stage = document.getElementById("stage");
      const slide = document.querySelector("#stage > .slide.active");
      const playerRect = player.getBoundingClientRect();
      const stageRect = stage.getBoundingClientRect();
      const slideRect = slide.getBoundingClientRect();
      const centerY = Math.max(playerRect.top + 8, Math.min(
        playerRect.bottom - 8,
        stageRect.top + stageRect.height / 2,
      ));
      let start = null;
      if (playerRect.right - stageRect.right >= 12) {
        start = { x: (stageRect.right + playerRect.right) / 2, y: centerY, side: "right" };
      } else if (stageRect.left - playerRect.left >= 12) {
        start = { x: (playerRect.left + stageRect.left) / 2, y: centerY, side: "left" };
      } else if (playerRect.bottom - stageRect.bottom >= 12) {
        start = {
          x: stageRect.left + stageRect.width / 2,
          y: (stageRect.bottom + playerRect.bottom) / 2,
          side: "bottom",
        };
      } else if (stageRect.top - playerRect.top >= 12) {
        start = {
          x: stageRect.left + stageRect.width / 2,
          y: (playerRect.top + stageRect.top) / 2,
          side: "top",
        };
      }
      if (!start) throw new Error("No #player letterbox band is available at this viewport");
      return {
        start,
        end: {
          x: slideRect.left + slideRect.width * 0.46,
          y: slideRect.top + slideRect.height * 0.72,
        },
        player: {
          left: playerRect.left,
          top: playerRect.top,
          right: playerRect.right,
          bottom: playerRect.bottom,
        },
        slide: {
          left: slideRect.left,
          top: slideRect.top,
          right: slideRect.right,
          bottom: slideRect.bottom,
        },
      };
    });

    await page.mouse.move(geometry.start.x, geometry.start.y);
    await page.mouse.down();
    await page.mouse.move(geometry.end.x, geometry.end.y, { steps: 8 });
    await page.mouse.up();

    const result = await page.evaluate(() => {
      const visible = (element) => (
        element && getComputedStyle(element).display !== "none"
      );
      return {
        selectionFrameVisible: visible(document.getElementById("edit-selection-frame")),
        selectionBadgeVisible: visible(document.getElementById("edit-selection-badge")),
        memberFramesVisible: Array.from(
          document.querySelectorAll(".edit-selection-member-frame"),
        ).filter(visible).length,
        marqueeStillVisible: Array.from(
          document.querySelectorAll(".edit-marquee-box"),
        ).filter(visible).length,
      };
    });
    const startInsidePlayer = (
      geometry.start.x >= geometry.player.left
      && geometry.start.x <= geometry.player.right
      && geometry.start.y >= geometry.player.top
      && geometry.start.y <= geometry.player.bottom
    );
    const startOutsideSlide = !(
      geometry.start.x >= geometry.slide.left
      && geometry.start.x <= geometry.slide.right
      && geometry.start.y >= geometry.slide.top
      && geometry.start.y <= geometry.slide.bottom
    );
    report = {
      html: htmlPath,
      viewport: { width: 1280, height: 720 },
      geometry,
      startInsidePlayer,
      startOutsideSlide,
      ...result,
    };
    report.pass = (
      startInsidePlayer
      && startOutsideSlide
      && result.selectionFrameVisible
      && result.selectionBadgeVisible
      && result.memberFramesVisible > 0
      && result.marqueeStillVisible === 0
    );
  } finally {
    await browser.close();
  }

  await fs.mkdir(path.dirname(path.resolve(options.report)), { recursive: true });
  await fs.writeFile(path.resolve(options.report), JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report));
  if (!report.pass) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
