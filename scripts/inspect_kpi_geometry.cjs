const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");

const htmlPath = path.resolve(process.argv[2]);
if (!htmlPath) throw new Error("HTML path is required");

async function main() {
  const markup = await fs.readFile(htmlPath, "utf8");
  const baseHref = pathToFileURL(`${path.dirname(htmlPath)}${path.sep}`).href;
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
  const page = await browser.newPage({ viewport: { width: 960, height: 540 }, deviceScaleFactor: 1 });
  await page.setContent(markup.replace(/<head>/i, `<head><base href="${baseHref}">`), {
    waitUntil: "domcontentloaded",
    timeout: 120000,
  });
  await Promise.race([page.evaluate(() => document.fonts?.ready), page.waitForTimeout(3000)]);
  await page.waitForFunction(() => document.documentElement.dataset.layoutReady === "true", null, { timeout: 120000 });
  await page.evaluate(() => window.setSlide(4));
  await page.waitForTimeout(120);
  const result = await page.evaluate(() => {
    const rect = (el) => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return {
        className: el.className || el.tagName,
        styleTop: el.style.top,
        position: s.position,
        transform: s.transform,
        left: Math.round(r.left * 10) / 10,
        top: Math.round(r.top * 10) / 10,
        right: Math.round(r.right * 10) / 10,
        bottom: Math.round(r.bottom * 10) / 10,
        width: Math.round(r.width * 10) / 10,
        height: Math.round(r.height * 10) / 10,
      };
    };
    const slide = document.querySelector("#stage > .slide.active");
    const frame = slide?.querySelector(".prod-frame");
    const source = slide?.querySelector('[data-layout-flow-id="kpi-header"]');
    const follower = slide?.querySelector('[data-layout-follow="kpi-header"]');
    return {
      layoutReady: document.documentElement.dataset.layoutReady,
      slide: rect(slide),
      frame: rect(frame),
      source: rect(source),
      sourceRoots: source ? [...source.children].map(rect) : [],
      follower: follower ? {
        ...rect(follower),
        datasetTop: follower.dataset.layoutFollowSourceTop,
        resolved: follower.dataset.layoutFollowResolved,
        shift: follower.dataset.layoutFollowShift,
      } : null,
      followerRoots: follower ? [...follower.children].map(rect) : [],
      cards: slide ? [...slide.querySelectorAll(".metric-kpi-card")].map(rect) : [],
      takeaway: rect(slide?.querySelector(".metric-takeaway")),
      matchingRules: [...document.styleSheets].flatMap((sheet) => {
        try {
          return [...sheet.cssRules]
            .filter((rule) => rule.selectorText && /metric-kpi-card|layout-flow-follow-region|\.el\s*\{/.test(rule.selectorText))
            .map((rule) => ({ selector: rule.selectorText, cssText: rule.cssText }));
        } catch {
          return [];
        }
      }),
    };
  });
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
