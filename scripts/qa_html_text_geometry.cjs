const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");

const PROJECT_ROOT = path.resolve(__dirname, "..");
const THRESHOLD_PX = 2;

function parseArgs(argv) {
  const options = {};
  for (let index = 2; index < argv.length; index += 1) {
    const key = argv[index];
    const value = argv[index + 1];
    if (key === "--file") {
      options.file = value;
      index += 1;
    } else if (key === "--report") {
      options.report = value;
      index += 1;
    } else {
      throw new Error(`Unknown argument: ${key}`);
    }
  }
  if (!options.file || !options.report) {
    throw new Error("--file and --report are required");
  }
  options.file = path.resolve(options.file);
  options.report = path.resolve(options.report);
  if (options.file === options.report) {
    throw new Error("--report must not overwrite --file");
  }
  return options;
}

function portablePath(value) {
  const resolved = path.resolve(value);
  const relative = path.relative(PROJECT_ROOT, resolved);
  if (relative === "") return ".";
  if (relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative)) {
    return relative.split(path.sep).join("/");
  }
  return resolved.split(path.sep).join("/");
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

async function writeReport(reportPath, report) {
  await fs.mkdir(path.dirname(reportPath), { recursive: true });
  await fs.writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
}

function markupWithBase(markup, htmlPath) {
  const baseHref = pathToFileURL(`${path.dirname(htmlPath)}${path.sep}`).href;
  const baseTag = `<base href="${baseHref}">`;
  if (/<head\b[^>]*>/i.test(markup)) {
    return markup.replace(/<head\b[^>]*>/i, (head) => `${head}${baseTag}`);
  }
  return `${baseTag}${markup}`;
}

async function evaluateGeometry(page) {
  return page.evaluate(({ thresholdPx }) => {
    const REQUIRED_MODULE_CLASSES = [
      "cycle-callout",
      "cycle-hub",
      "toc-panel-grid-card",
      "toc-panel-row",
      "metric-chart-panel",
      "metric-insight",
      "metric-kpi-card",
    ];
    const TEXT_LAYER_SELECTOR = '[data-edit-layer="text"],[data-edit-layer="metric"]';
    const round = (value) => Math.round(value * 100) / 100;

    const rectObject = (rect) => ({
      left: round(rect.left),
      top: round(rect.top),
      right: round(rect.right),
      bottom: round(rect.bottom),
      width: round(rect.width),
      height: round(rect.height),
    });

    const isVisible = (element, stopAt = null) => {
      if (!(element instanceof Element)) return false;
      let current = element;
      while (current) {
        const style = getComputedStyle(current);
        if (
          style.display === "none"
          || style.visibility === "hidden"
          || style.visibility === "collapse"
          || Number(style.opacity) <= 0.001
        ) {
          return false;
        }
        if (current === stopAt) break;
        current = current.parentElement;
      }
      return [...element.getClientRects()].some((rect) => rect.width > 0.1 && rect.height > 0.1);
    };

    const hasIntentionalGeometryOptOut = (layer, module) => {
      let current = layer;
      while (current) {
        const classTokens = [...current.classList].map((token) => token.toLowerCase());
        const role = (current.getAttribute("data-edit-role") || "").toLowerCase();
        const overlap = (current.getAttribute("data-edit-overlap") || "").toLowerCase();
        const qaMode = (current.getAttribute("data-qa-text-geometry") || "").toLowerCase();
        if (
          current.getAttribute("aria-hidden") === "true"
          || current.getAttribute("data-text-geometry-ignore") === "true"
          || current.getAttribute("data-qa-allow-overlap") === "true"
          || qaMode === "ignore"
          || overlap === "intentional"
          || ["decorative", "overprint", "watermark"].includes(role)
          || classTokens.some((token) => /(^|[-_])(overprint|watermark)([-_]|$)/.test(token))
        ) {
          return true;
        }
        if (current === module) break;
        current = current.parentElement;
      }
      return false;
    };

    const selectorFor = (element, slide) => {
      const parts = [];
      let current = element;
      while (current && current !== slide) {
        const parent = current.parentElement;
        if (!parent) break;
        const childIndex = [...parent.children].indexOf(current) + 1;
        parts.unshift(`${current.tagName.toLowerCase()}:nth-child(${childIndex})`);
        current = parent;
      }
      const slideIndex = [...slide.parentElement.children].indexOf(slide) + 1;
      return `#stage > .slide:nth-child(${slideIndex})${parts.length ? ` > ${parts.join(" > ")}` : ""}`;
    };

    const textSummary = (element) => {
      const summary = (element.textContent || "").replace(/\s+/g, " ").trim();
      return summary.length > 120 ? `${summary.slice(0, 117)}...` : summary;
    };

    const metricsFor = (slide) => {
      const slideRect = slide.getBoundingClientRect();
      const width = slide.offsetWidth || slideRect.width || 1;
      const height = slide.offsetHeight || slideRect.height || 1;
      return {
        slideRect,
        scaleX: slideRect.width / width || 1,
        scaleY: slideRect.height / height || 1,
      };
    };

    const normalizeRect = (rect, metrics) => {
      const left = (rect.left - metrics.slideRect.left) / metrics.scaleX;
      const top = (rect.top - metrics.slideRect.top) / metrics.scaleY;
      const right = (rect.right - metrics.slideRect.left) / metrics.scaleX;
      const bottom = (rect.bottom - metrics.slideRect.top) / metrics.scaleY;
      return rectObject({
        left,
        top,
        right,
        bottom,
        width: right - left,
        height: bottom - top,
      });
    };

    const glyphRectsFor = (layer, metrics) => {
      const rects = [];
      const walker = document.createTreeWalker(layer, NodeFilter.SHOW_TEXT);
      let textNode = walker.nextNode();
      while (textNode) {
        const raw = textNode.data || "";
        const leading = raw.search(/\S/);
        if (leading >= 0) {
          let trailing = raw.length;
          while (trailing > leading && /\s/.test(raw[trailing - 1])) trailing -= 1;
          const parent = textNode.parentElement;
          const owner = parent && parent.closest(TEXT_LAYER_SELECTOR);
          if (owner === layer && isVisible(parent, layer)) {
            const range = document.createRange();
            range.setStart(textNode, leading);
            range.setEnd(textNode, trailing);
            for (const rect of range.getClientRects()) {
              if (rect.width > 0.1 && rect.height > 0.1) {
                rects.push(normalizeRect(rect, metrics));
              }
            }
            range.detach();
          }
        }
        textNode = walker.nextNode();
      }
      return rects;
    };

    const overflowOf = (glyph, moduleRect) => {
      const overflow = {
        left: Math.max(0, moduleRect.left - glyph.left),
        top: Math.max(0, moduleRect.top - glyph.top),
        right: Math.max(0, glyph.right - moduleRect.right),
        bottom: Math.max(0, glyph.bottom - moduleRect.bottom),
      };
      overflow.max = Math.max(overflow.left, overflow.top, overflow.right, overflow.bottom);
      return Object.fromEntries(Object.entries(overflow).map(([key, value]) => [key, round(value)]));
    };

    const intersectionOf = (left, right) => ({
      x: round(Math.max(0, Math.min(left.right, right.right) - Math.max(left.left, right.left))),
      y: round(Math.max(0, Math.min(left.bottom, right.bottom) - Math.max(left.top, right.top))),
    });

    const slides = [...document.querySelectorAll("#stage > .slide")];
    const issues = [];
    const checks = {
      slides: slides.length,
      modules: 0,
      textLayers: 0,
      glyphRects: 0,
      ignoredIntentionalLayers: 0,
      textOutsideModule: 0,
      textLayerOverlap: 0,
    };

    for (let slideIndex = 0; slideIndex < slides.length; slideIndex += 1) {
      const slide = slides[slideIndex];
      const pageNumber = slide.dataset.pageNumber || String(slideIndex + 1);
      const layoutId = slide.dataset.layoutId || null;
      const metrics = metricsFor(slide);
      const candidates = [...slide.querySelectorAll(`[data-edit-composite],.${REQUIRED_MODULE_CLASSES.join(",.")}`)];
      const modules = [...new Set(candidates)].filter((module) => {
        if (!isVisible(module, slide)) return false;
        const namedModule = REQUIRED_MODULE_CLASSES.some((className) => module.classList.contains(className));
        const directBackground = [...module.children].some((child) => child.getAttribute("data-edit-layer") === "background");
        return namedModule || (module.hasAttribute("data-edit-composite") && directBackground);
      });
      const moduleSet = new Set(modules);
      const owningModule = (element) => {
        let current = element.parentElement;
        while (current && current !== slide) {
          if (moduleSet.has(current)) return current;
          current = current.parentElement;
        }
        return null;
      };

      for (const module of modules) {
        checks.modules += 1;
        const directBackground = [...module.children].find((child) => child.getAttribute("data-edit-layer") === "background");
        const boundaryElement = directBackground && isVisible(directBackground, module) ? directBackground : module;
        const moduleRect = normalizeRect(boundaryElement.getBoundingClientRect(), metrics);
        const moduleSelector = selectorFor(module, slide);
        const composite = module.getAttribute("data-edit-composite") || REQUIRED_MODULE_CLASSES.find((className) => module.classList.contains(className)) || null;
        const layers = [...module.querySelectorAll(TEXT_LAYER_SELECTOR)]
          .filter((layer) => owningModule(layer) === module)
          .filter((layer) => isVisible(layer, module));
        const measuredLayers = [];

        for (const layer of layers) {
          if (hasIntentionalGeometryOptOut(layer, module)) {
            checks.ignoredIntentionalLayers += 1;
            continue;
          }
          const glyphRects = glyphRectsFor(layer, metrics);
          if (!glyphRects.length) continue;
          checks.textLayers += 1;
          checks.glyphRects += glyphRects.length;
          const measurement = {
            element: layer,
            selector: selectorFor(layer, slide),
            summary: textSummary(layer),
            glyphRects,
          };
          measuredLayers.push(measurement);

          let worst = null;
          for (const glyphRect of glyphRects) {
            const overflow = overflowOf(glyphRect, moduleRect);
            if (overflow.max > thresholdPx && (!worst || overflow.max > worst.overflow.max)) {
              worst = { glyphRect, overflow };
            }
          }
          if (worst) {
            checks.textOutsideModule += 1;
            issues.push({
              contract: "text-outside-module",
              page: pageNumber,
              layout: layoutId,
              composite,
              selectors: { module: moduleSelector, primary: measurement.selector, secondary: null },
              summaries: { primary: measurement.summary, secondary: null },
              rects: { module: moduleRect, primaryGlyph: worst.glyphRect, secondaryGlyph: null },
              overlap: null,
              overflow: worst.overflow,
              thresholdPx,
            });
          }
        }

        for (let leftIndex = 0; leftIndex < measuredLayers.length; leftIndex += 1) {
          const left = measuredLayers[leftIndex];
          for (let rightIndex = leftIndex + 1; rightIndex < measuredLayers.length; rightIndex += 1) {
            const right = measuredLayers[rightIndex];
            if (left.element.contains(right.element) || right.element.contains(left.element)) continue;
            let worst = null;
            for (const leftRect of left.glyphRects) {
              for (const rightRect of right.glyphRects) {
                const overlap = intersectionOf(leftRect, rightRect);
                if (overlap.x <= thresholdPx || overlap.y <= thresholdPx) continue;
                const area = overlap.x * overlap.y;
                if (!worst || area > worst.area) {
                  worst = { leftRect, rightRect, overlap, area };
                }
              }
            }
            if (worst) {
              checks.textLayerOverlap += 1;
              issues.push({
                contract: "text-layer-overlap",
                page: pageNumber,
                layout: layoutId,
                composite,
                selectors: { module: moduleSelector, primary: left.selector, secondary: right.selector },
                summaries: { primary: left.summary, secondary: right.summary },
                rects: { module: moduleRect, primaryGlyph: worst.leftRect, secondaryGlyph: worst.rightRect },
                overlap: worst.overlap,
                overflow: null,
                thresholdPx,
              });
            }
          }
        }
      }
    }

    return { checks, issues };
  }, { thresholdPx: THRESHOLD_PX });
}

async function run(options) {
  const markup = await fs.readFile(options.file, "utf8");
  const inputSha256 = sha256(markup);
  const executablePath = browserExecutable();
  if (!process.env.BROWSER_CDP_URL && !executablePath) {
    throw new Error("No Chrome or Edge executable found for text geometry QA");
  }
  const { chromium } = loadPlaywright();
  const browser = process.env.BROWSER_CDP_URL
    ? await chromium.connectOverCDP(process.env.BROWSER_CDP_URL)
    : await chromium.launch({ headless: true, executablePath });
  try {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.setContent(markupWithBase(markup, options.file), { waitUntil: "domcontentloaded", timeout: 120000 });
    await page.evaluate(async () => {
      if (document.fonts && document.fonts.ready) await document.fonts.ready;
    });
    await page.waitForFunction(
      () => (
        document.documentElement.dataset.layoutReady === "true"
        || document.body?.dataset.layoutReady === "true"
        || document.querySelector("#stage")?.dataset.layoutReady === "true"
      ),
      null,
      { timeout: 120000 },
    );
    await page.addStyleTag({
      content: "#stage > .slide { display:block !important; visibility:visible !important; opacity:1 !important; }",
    });
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const result = await evaluateGeometry(page);
    const markupAfter = await fs.readFile(options.file, "utf8");
    const outputSha256 = sha256(markupAfter);
    if (inputSha256 !== outputSha256) {
      throw new Error("Input HTML changed while the report-only geometry QA was running");
    }
    return {
      schemaVersion: "html-text-geometry-v1",
      file: portablePath(options.file),
      fileSha256: inputSha256,
      fileSha256After: outputSha256,
      inputUnchanged: true,
      thresholdPx: THRESHOLD_PX,
      status: result.issues.length ? "fail" : "pass",
      checks: result.checks,
      issues: result.issues,
    };
  } finally {
    await browser.close();
  }
}

async function main() {
  let options;
  try {
    options = parseArgs(process.argv);
    const report = await run(options);
    await writeReport(options.report, report);
    console.log(JSON.stringify(report, null, 2));
    process.exitCode = report.status === "pass" ? 0 : 1;
  } catch (error) {
    const message = error && (error.stack || error.message) ? (error.stack || error.message) : String(error);
    const report = {
      schemaVersion: "html-text-geometry-v1",
      file: options?.file ? portablePath(options.file) : null,
      status: "runtime-error",
      error: message,
    };
    if (options?.report) {
      try {
        await writeReport(options.report, report);
      } catch (writeError) {
        console.error(writeError.stack || writeError.message || String(writeError));
      }
    }
    console.error(message);
    process.exitCode = 2;
  }
}

main();
