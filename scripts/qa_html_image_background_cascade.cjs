#!/usr/bin/env node
"use strict";

const fsp = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");

function argsOf(argv) {
  const options = {};
  for (let index = 2; index < argv.length; index += 1) {
    const key = argv[index];
    if (!key.startsWith("--")) continue;
    options[key.slice(2)] = argv[index + 1];
    index += 1;
  }
  return options;
}

async function main() {
  const options = argsOf(process.argv);
  if (!options.html) throw new Error("--html is required");
  const htmlPath = path.resolve(options.html);
  await fsp.access(htmlPath);

  const { chromium } = loadPlaywright();
  const executablePath = browserExecutable();
  if (!process.env.BROWSER_CDP_URL && !executablePath) {
    throw new Error("No Chrome or Edge executable found for background cascade QA");
  }
  const browser = process.env.BROWSER_CDP_URL
    ? await chromium.connectOverCDP(process.env.BROWSER_CDP_URL)
    : await chromium.launch({ headless: true, executablePath });
  const launchedLocally = !process.env.BROWSER_CDP_URL;
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

  let report;
  try {
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "domcontentloaded", timeout: 120000 });
    report = await page.evaluate(async () => {
      const liveSlide = document.querySelector("#stage > section.slide");
      if (!liveSlide) throw new Error("Missing top-level slide");
      const liveStyle = getComputedStyle(liveSlide);
      const live = {
        id: liveSlide.id,
        backgroundImage: liveStyle.backgroundImage,
        pptxBackground: liveSlide.getAttribute("data-pptx-background-image"),
        pptxEmbedded: liveSlide.getAttribute("data-pptx-background-image-embedded"),
        pptxSource: liveSlide.getAttribute("data-pptx-background-image-src"),
      };

      const host = document.createElement("span");
      host.dataset.thumbnailClone = "cascade-qa";
      const shadow = host.attachShadow({ mode: "open" });
      document.querySelectorAll("style,link[rel=\"stylesheet\"]").forEach((node) => {
        shadow.appendChild(node.cloneNode(true));
      });
      const clone = liveSlide.cloneNode(true);
      clone.classList.remove("active");
      const mirrorStage = document.createElement("main");
      mirrorStage.id = "stage";
      mirrorStage.appendChild(clone);
      const contextRoot = document.createElement("html");
      Array.from(document.documentElement.attributes).forEach((attribute) => {
        contextRoot.setAttribute(attribute.name, attribute.value);
      });
      const contextBody = document.createElement("body");
      Array.from(document.body.attributes).forEach((attribute) => {
        contextBody.setAttribute(attribute.name, attribute.value);
      });
      contextBody.appendChild(mirrorStage);
      contextRoot.appendChild(contextBody);
      shadow.appendChild(contextRoot);
      document.body.appendChild(host);
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const cloneStyle = getComputedStyle(clone);
      const thumbnailClone = {
        id: clone.id,
        backgroundImage: cloneStyle.backgroundImage,
      };
      host.remove();

      const finalStyle = document.getElementById("html-image-background-per-slide-experiment-final")
        || document.getElementById("html-image-background-experiment-final");
      const finalCss = finalStyle ? finalStyle.textContent : "";
      const liveUsesEmbeddedRaster = /^url\(["']?data:image\//i.test(live.backgroundImage);
      const thumbnailCloneUsesSameEmbeddedRaster = (
        /^url\(["']?data:image\//i.test(thumbnailClone.backgroundImage)
        && thumbnailClone.backgroundImage === live.backgroundImage
      );
      const checks = {
        finalStylePresent: Boolean(finalStyle),
        finalStyleHasNoImportant: !/!important/i.test(finalCss),
        liveSlideUsesEmbeddedRaster: liveUsesEmbeddedRaster,
        thumbnailCloneUsesSameEmbeddedRaster,
        pptxAttributesPreserved: (
          live.pptxBackground === "true"
          && live.pptxEmbedded === "true"
          && Boolean(live.pptxSource)
        ),
      };
      return {
        status: Object.values(checks).every(Boolean) ? "pass" : "fail",
        checks,
        live,
        thumbnailClone,
        finalSelectorText: finalCss.split("{")[0].trim(),
      };
    });
  } finally {
    await page.close();
    if (launchedLocally) await browser.close();
  }

  report.html = htmlPath;
  if (options.report) {
    const reportPath = path.resolve(options.report);
    await fsp.mkdir(path.dirname(reportPath), { recursive: true });
    await fsp.writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  }
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  if (report.status !== "pass") process.exitCode = 1;
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || String(error)}\n`);
  process.exitCode = 1;
});
