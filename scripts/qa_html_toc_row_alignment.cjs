const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
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

async function main() {
  const options = argsOf(process.argv);
  const browserCandidates = [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  const executablePath = browserCandidates.find((candidate) => fsSync.existsSync(candidate));
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  try {
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(options.url, { waitUntil: "commit", timeout: 120000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true"
      && Boolean(window.SlidePlayer)
    ), null, { timeout: 120000 });
    await page.evaluate(() => {
      const slides = [...document.querySelectorAll("#stage > .slide")];
      const index = slides.findIndex((slide) => slide.querySelector(".toc-panel-row"));
      if (index >= 0) window.setSlide(index);
    });
    const rows = await page.evaluate(() => (
      [...document.querySelectorAll(".slide.active .toc-panel-row")].map((row) => {
        const rowRect = row.getBoundingClientRect();
        const rowCenter = rowRect.top + rowRect.height / 2;
        const members = [...row.children]
          .filter((member) => member.matches("span,b,p,i"))
          .map((member) => {
            const rect = member.getBoundingClientRect();
            return {
              tag: member.tagName.toLowerCase(),
              text: (member.textContent || "").trim(),
              centerOffset: Math.round(((rect.top + rect.height / 2) - rowCenter) * 1000) / 1000,
              top: getComputedStyle(member).top,
              transform: getComputedStyle(member).transform,
            };
          });
        return {
          className: row.className,
          members,
          maximumCenterOffset: Math.max(...members.map((member) => Math.abs(member.centerOffset))),
        };
      })
    ));
    const checks = {
      rowsFound: rows.length > 0,
      fourMembersPerRow: rows.every((row) => row.members.length === 4),
      commonVerticalCenterline: rows.every((row) => row.maximumCenterOffset <= 0.5),
      relativeCenteringUsed: rows.every((row) => row.members.every((member) => (
        member.top === "89px" && member.transform !== "none"
      ))),
    };
    const result = {
      url: options.url,
      tolerancePx: 0.5,
      rows,
      checks,
      pass: Object.values(checks).every(Boolean),
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
