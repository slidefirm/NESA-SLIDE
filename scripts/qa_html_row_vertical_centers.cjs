const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

function argsOf(argv) {
  const args = {};
  for (let index = 2; index < argv.length; index += 2) {
    args[argv[index].replace(/^--/, "")] = argv[index + 1];
  }
  if ((!args.html && !args.url) || !args.report) throw new Error("--html or --url, plus --report, are required");
  return args;
}

async function main() {
  const args = argsOf(process.argv);
  const candidates = [
    process.env.BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  const executablePath = candidates.find((candidate) => fsSync.existsSync(candidate));
  if (!executablePath) throw new Error("No Chrome or Edge executable found");

  const browser = await chromium.launch({ headless: true, executablePath });
  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    if (args.url) {
      await page.goto(args.url, { waitUntil: "domcontentloaded", timeout: 60000 });
    } else {
      const markup = await fs.readFile(path.resolve(args.html), "utf8");
      await page.setContent(markup, { waitUntil: "domcontentloaded", timeout: 60000 });
    }
    await page.waitForFunction(
      () => document.documentElement.dataset.layoutReady === "true",
      null,
      { timeout: 60000 },
    );
    await page.evaluate(() => window.setSlide(1));
    const result = await page.evaluate(() => {
      const slide = document.querySelector(".slide.active");
      const slideRect = slide.getBoundingClientRect();
      const scale = slide.offsetWidth ? slideRect.width / slide.offsetWidth : 1;
      const rows = [...slide.querySelectorAll('[data-row-align="center"]')].map((row) => {
        const rowRect = row.getBoundingClientRect();
        const rowCenter = (rowRect.top + rowRect.bottom) / 2;
        const children = [...row.querySelectorAll(":scope > [data-edit-layer]")]
          .filter((node) => !node.classList.contains("diagram-node-bg"))
          .map((node) => {
            const rect = node.getBoundingClientRect();
            return {
              layer: node.dataset.editLayer,
              tag: node.tagName.toLowerCase(),
              deltaFromRowCenter: Math.round(Math.abs((rect.top + rect.bottom) / 2 - rowCenter) / scale * 100) / 100,
            };
          });
        return {
          className: row.className,
          children,
          maxDelta: Math.max(...children.map((item) => item.deltaFromRowCenter), 0),
        };
      });
      const maxDelta = Math.max(...rows.map((row) => row.maxDelta), 0);
      return {
        layoutId: slide.dataset.layoutId,
        rows,
        maxDelta,
        pass: rows.length > 0 && maxDelta <= 1,
      };
    });
    await fs.mkdir(path.dirname(path.resolve(args.report)), { recursive: true });
    await fs.writeFile(path.resolve(args.report), `${JSON.stringify(result, null, 2)}\n`, "utf8");
    process.stdout.write(`${JSON.stringify(result)}\n`);
    if (!result.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
