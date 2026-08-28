const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

function argsOf(argv) {
  const out = {};
  for (let index = 2; index < argv.length; index += 1) {
    if (argv[index] === "--url") out.url = argv[++index];
    else if (argv[index] === "--output") out.output = argv[++index];
    else if (argv[index] === "--report") out.report = argv[++index];
  }
  if (!out.url || !out.output || !out.report) {
    throw new Error("--url, --output and --report are required");
  }
  return out;
}

async function main() {
  const options = argsOf(process.argv);
  const outputPath = path.resolve(options.output);
  const reportPath = path.resolve(options.report);
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
      document.documentElement.dataset.layoutReady === "true"
      && Boolean(window.EditMode?.exportPptx)
    ), null, { timeout: 120000 });

    const framework = await page.evaluate(() => {
      const visibleButtons = [...document.querySelectorAll("#barInner button")]
        .filter((button) => getComputedStyle(button).display !== "none")
        .map((button) => ({
          label: button.getAttribute("aria-label") || "",
          text: (button.textContent || "").trim(),
        }));
      return {
        title: document.title,
        slides: document.querySelectorAll("#stage > .slide").length,
        pptxButtonVisible: visibleButtons.some((button) => (
          /PPTX/i.test(button.label) || /PPTX/i.test(button.text)
        )),
      };
    });

    const manifestStartedAt = Date.now();
    const manifest = await page.evaluate(() => window.EditMode.buildPptxManifest());
    const manifestMs = Date.now() - manifestStartedAt;
    const endpoint = new URL("/__export-pptx", options.url);
    const exportStartedAt = Date.now();
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(manifest),
      signal: AbortSignal.timeout(240000),
    });
    const responseBytes = Buffer.from(await response.arrayBuffer());
    const exportMs = Date.now() - exportStartedAt;
    if (!response.ok) {
      throw new Error(`PPTX endpoint returned ${response.status}: ${responseBytes.toString("utf8")}`);
    }
    await fs.mkdir(path.dirname(outputPath), { recursive: true });
    await fs.writeFile(outputPath, responseBytes);
    const file = await fs.stat(outputPath);
    const signature = Buffer.alloc(4);
    const handle = await fs.open(outputPath, "r");
    await handle.read(signature, 0, 4, 0);
    await handle.close();

    const checks = {
      frameworkReady: Boolean(framework.title),
      slideCount: framework.slides > 0,
      pptxButtonVisible: framework.pptxButtonVisible,
      publicApi: typeof manifest?.schemaVersion === "number"
        && manifest?.slides?.length === framework.slides,
      endpointStatus: response.status === 200,
      contentType: /presentationml\.presentation/.test(response.headers.get("content-type") || ""),
      slideHeader: Number(response.headers.get("x-pptx-slides")) === framework.slides,
      zipSignature: signature.equals(Buffer.from([0x50, 0x4b, 0x03, 0x04])),
      outputBytes: file.size > 10000,
    };
    const report = {
      url: options.url,
      output: outputPath,
      suggestedFileName: manifest.fileName,
      bytes: file.size,
      timings: { manifestMs, exportMs },
      framework,
      response: {
        status: response.status,
        contentType: response.headers.get("content-type") || "",
        slides: response.headers.get("x-pptx-slides") || "",
        layouts: response.headers.get("x-pptx-layouts") || "",
      },
      manifest: {
        schemaVersion: manifest.schemaVersion,
        title: manifest.title,
        fileName: manifest.fileName,
        slides: manifest.slides.length,
        elements: manifest.slides.reduce((sum, slide) => sum + slide.elements.length, 0),
      },
      checks,
      pass: Object.values(checks).every(Boolean),
    };
    await fs.mkdir(path.dirname(reportPath), { recursive: true });
    await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + "\n", "utf8");
    process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
    if (!report.pass) process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
