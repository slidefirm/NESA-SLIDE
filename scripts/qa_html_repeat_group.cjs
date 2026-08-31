const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { browserExecutable, loadPlaywright } = require("./playwright_runtime.cjs");
const { chromium } = loadPlaywright();

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

function sha256(text) {
  return crypto.createHash("sha256").update(text, "utf8").digest("hex");
}

function portablePath(filePath) {
  const relative = path.relative(process.cwd(), filePath);
  return relative && !relative.startsWith("..") && !path.isAbsolute(relative)
    ? relative.split(path.sep).join("/")
    : `<external>/${path.basename(filePath)}`;
}

async function main() {
  const options = argsOf(process.argv);
  const htmlPath = path.resolve(options.html);
  const reportPath = path.resolve(options.report);
  const beforeMarkup = await fs.readFile(htmlPath, "utf8");
  const beforeSha256 = sha256(beforeMarkup);
  const staticChecks = {
    repeatAttributesAbsent: !/\bdata-edit-repeat-[\w-]+\s*=/i.test(beforeMarkup),
    repeatEditorApiAbsent: !/\brepeat(?:SelectAll|Add|Remove)\b/.test(beforeMarkup),
    aggregateRolesAbsent: !/data-edit-role=["'](?:title-group|content-group|extra-group)["']/i.test(beforeMarkup),
    generatedAggregateStructureAbsent: !/data-edit-structure=["']group["']/i.test(beforeMarkup),
  };

  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable() });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  let browserChecks;
  try {
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.route("https://fonts.gstatic.com/**", (route) => route.abort());
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "commit", timeout: 60000 });
    await page.waitForFunction(() => (
      document.documentElement.dataset.layoutReady === "true" && Boolean(window.EditMode)
    ), null, { timeout: 120000 });
    browserChecks = await page.evaluate(() => {
      window.EditMode.toggle(true);
      const repeatNodes = document.querySelectorAll(
        "[data-edit-repeat-group],[data-edit-repeat-layout],[data-edit-repeat-connectors]"
      );
      const aggregateGroups = document.querySelectorAll(
        '.el[data-edit-role="title-group"],.el[data-edit-role="content-group"],.el[data-edit-role="extra-group"],.el[data-edit-structure="group"]'
      );
      const centeringFrames = [...document.querySelectorAll('[data-visual-balance="content-bounds"]')];
      const invalidCenteringFrames = centeringFrames.filter((frame) => (
        frame.dataset.editLayoutOnly !== "true"
        || frame.matches(".el,[data-edit-composite],[data-edit-layer]")
      ));
      const offCenterFrames = centeringFrames.filter((frame) => {
        const left = Number.parseFloat(frame.dataset.visualLeftGap);
        const right = Number.parseFloat(frame.dataset.visualRightGap);
        const top = Number.parseFloat(frame.dataset.visualTopGap);
        const bottom = Number.parseFloat(frame.dataset.visualBottomGap);
        return frame.dataset.visualBalanced !== "true"
          || ![left, right, top, bottom].every(Number.isFinite)
          || Math.abs(left - right) > 0.2
          || Math.abs(top - bottom) > 0.2;
      });
      const modules = [...document.querySelectorAll('.el[data-edit-structure="module"][data-edit-composite]')];
      const invalidModules = modules.filter((module) => {
        const first = module.firstElementChild;
        return !first
          || first.dataset.editLayer !== "background"
          || first.dataset.editPosition !== "absolute";
      });
      const looseObjects = [...document.querySelectorAll(".el")].filter((object) => (
        !object.matches('[data-edit-structure="module"]')
        && !object.closest('.el[data-edit-structure="module"]')
        && !object.matches('[data-edit-structure="group"]')
      ));
      const positioningFrames = [...document.querySelectorAll(
        '.title-flow-stack,.layout-flow-follow-region'
      )];
      const invalidPositioningFrames = positioningFrames.filter((frame) => (
        frame.dataset.editLayoutOnly !== "true"
        || frame.matches('.el,[data-edit-composite],[data-edit-layer]')
      ));
      const visibleRect = (node) => {
        const style = getComputedStyle(node);
        const layoutRect = node.getBoundingClientRect();
        if (style.display === "none" || layoutRect.width <= 0.5 || layoutRect.height <= 0.5) return null;
        if (node.dataset.editFit !== "text" || !(node.textContent || "").trim()) return layoutRect;
        const range = document.createRange();
        range.selectNodeContents(node);
        const glyphRect = range.getBoundingClientRect();
        return glyphRect.width > 0.5 && glyphRect.height > 0.5 ? glyphRect : layoutRect;
      };
      const headerCollisions = [];
      [...document.querySelectorAll('.title-flow-stack')].forEach((stack) => {
        const slide = stack.closest('.slide');
        const previousDisplay = slide?.style.display || "";
        const previousVisibility = slide?.style.visibility || "";
        if (slide && getComputedStyle(slide).display === "none") {
          slide.style.display = "block";
          slide.style.visibility = "hidden";
        }
        const rects = [...stack.children]
          .filter((node) => node.matches('.el'))
          .map((node) => ({ node, rect: visibleRect(node) }))
          .filter((entry) => entry.rect && entry.rect.width > 0.5 && entry.rect.height > 0.5)
          .sort((a, b) => a.rect.top - b.rect.top);
        for (let index = 1; index < rects.length; index += 1) {
          if (rects[index - 1].rect.bottom > rects[index].rect.top - 0.5) {
            headerCollisions.push({
              slide: stack.closest('.slide')?.dataset.index || "",
              before: rects[index - 1].node.className,
              after: rects[index].node.className,
              beforeBottom: Math.round(rects[index - 1].rect.bottom * 10) / 10,
              afterTop: Math.round(rects[index].rect.top * 10) / 10,
              beforeBox: Math.round(rects[index - 1].node.getBoundingClientRect().bottom * 10) / 10,
              afterBox: Math.round(rects[index].node.getBoundingClientRect().top * 10) / 10,
              beforeStyle: rects[index - 1].node.getAttribute('style') || "",
              afterStyle: rects[index].node.getAttribute('style') || "",
              beforeSourceStyle: rects[index - 1].node.dataset.layoutSourceStyle || "",
              afterSourceStyle: rects[index].node.dataset.layoutSourceStyle || "",
            });
          }
        }
        if (slide) {
          slide.style.display = previousDisplay;
          slide.style.visibility = previousVisibility;
        }
      });
      const followerCollisions = [];
      [...document.querySelectorAll('[data-layout-follow]')].forEach((follower) => {
        const slide = follower.closest('.slide');
        const previousDisplay = slide?.style.display || "";
        const previousVisibility = slide?.style.visibility || "";
        if (slide && getComputedStyle(slide).display === "none") {
          slide.style.display = "block";
          slide.style.visibility = "hidden";
        }
        const source = [...(slide?.querySelectorAll('[data-layout-flow-id]') || [])]
          .find((candidate) => candidate.dataset.layoutFlowId === follower.dataset.layoutFollow);
        const sourceRects = source
          ? [...source.children].filter((node) => node.matches('.el')).map(visibleRect).filter(Boolean)
          : [];
        const followerRects = [...follower.children]
          .filter((node) => node.matches('.el')).map(visibleRect).filter(Boolean);
        if (!sourceRects.length || !followerRects.length) {
          if (slide) {
            slide.style.display = previousDisplay;
            slide.style.visibility = previousVisibility;
          }
          return;
        }
        const frame = follower.closest('.prod-frame,[data-content-area="true"]');
        const frameRect = frame?.getBoundingClientRect();
        const scaleY = frame && frameRect && frame.offsetHeight
          ? frameRect.height / frame.offsetHeight
          : 1;
        const sourceBottom = Math.max(...sourceRects.map((rect) => rect.bottom));
        const followerTop = Math.min(...followerRects.map((rect) => rect.top));
        const gap = Math.max(0, Number.parseFloat(follower.dataset.layoutFollowGap) || 0) * scaleY;
        if (sourceBottom + gap > followerTop + 0.5) {
          followerCollisions.push({
            slide: slide?.dataset.index || "",
            deficit: Math.round((sourceBottom + gap - followerTop) * 10) / 10,
            sourceBottom: Math.round(sourceBottom * 10) / 10,
            followerTop: Math.round(followerTop * 10) / 10,
            requestedGap: Math.round(gap * 10) / 10,
            resolvedShift: follower.dataset.layoutFollowShift || "",
          });
        }
        if (slide) {
          slide.style.display = previousDisplay;
          slide.style.visibility = previousVisibility;
        }
      });
      const repeatControls = [...document.querySelectorAll('[data-action^="repeat"],button')].filter((node) => (
        /^repeat/i.test(node.dataset?.action || "") || (node.textContent || "").includes("重複群組")
      ));
      return {
        repeatNodes: repeatNodes.length,
        repeatApiAbsent: !["repeatSelectAll", "repeatAdd", "repeatRemove"]
          .some((name) => Object.prototype.hasOwnProperty.call(window.EditMode, name)),
        repeatToolbarAbsent: repeatControls.length === 0,
        aggregateGroups: aggregateGroups.length,
        centeringFrames: centeringFrames.length,
        invalidCenteringFrames: invalidCenteringFrames.length,
        offCenterFrames: offCenterFrames.length,
        semanticModules: modules.length,
        invalidModules: invalidModules.length,
        looseObjects: looseObjects.length,
        positioningFrames: positioningFrames.length,
        invalidPositioningFrames: invalidPositioningFrames.length,
        headerCollisions,
        followerCollisions,
      };
    });
    browserChecks.flowStressCases = await page.evaluate(async () => {
      const originalIndex = Number(document.querySelector('.slide.active')?.dataset.index || 0);
      const cases = [];
      const nextFrames = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const rectOf = (node) => {
        const range = document.createRange();
        range.selectNodeContents(node);
        const glyph = range.getBoundingClientRect();
        return glyph.width > 0.5 && glyph.height > 0.5 ? glyph : node.getBoundingClientRect();
      };
      const overlapCount = (stack) => {
        const rects = [...stack.children].filter((node) => node.matches('.el'))
          .map(rectOf).sort((a, b) => a.top - b.top);
        let overlaps = 0;
        for (let index = 1; index < rects.length; index += 1) {
          if (rects[index - 1].bottom > rects[index].top - 0.5) overlaps += 1;
        }
        return overlaps;
      };
      const followerDeficit = (stack) => {
        const slide = stack.closest('.slide');
        const flowId = stack.dataset.layoutFlowId || '';
        const follower = [...slide.querySelectorAll('[data-layout-follow]')]
          .find((candidate) => candidate.dataset.layoutFollow === flowId);
        if (!follower) return 0;
        const sourceRects = [...stack.children].filter((node) => node.matches('.el')).map(rectOf);
        const followerRects = [...follower.children].filter((node) => node.matches('.el')).map(rectOf);
        const frame = follower.closest('.prod-frame,[data-content-area="true"]');
        const frameRect = frame.getBoundingClientRect();
        const scaleY = frame.offsetHeight ? frameRect.height / frame.offsetHeight : 1;
        const gap = Math.max(0, Number.parseFloat(follower.dataset.layoutFollowGap) || 0) * scaleY;
        return Math.max(0,
          Math.max(...sourceRects.map((rect) => rect.bottom)) + gap
          - Math.min(...followerRects.map((rect) => rect.top))
        );
      };
      const stressTitles = [
        '港灣燈節',
        '讓三天的港灣燈節，成為一整年的文化引擎',
        '讓三天的港灣燈節，成為居民共同創作、地方餐飲與全年回訪內容持續運轉的文化引擎',
      ];
      for (const stack of document.querySelectorAll('.title-flow-stack')) {
        const title = [...stack.children].find((node) => node.matches('.prod-title,.cover-center-title'));
        const slide = stack.closest('.slide');
        if (!title || !slide) continue;
        const originalText = title.textContent;
        const titles = stack.matches('.cover-center-area') ? stressTitles : [stressTitles[2]];
        window.setSlide(Number(slide.dataset.index));
        await nextFrames();
        for (const stressTitle of titles) {
          title.textContent = stressTitle;
          window.reapplyAutoLayout(slide);
          await nextFrames();
          cases.push({
            slide: slide.dataset.index || '',
            layout: slide.dataset.layoutId || '',
            titleLength: stressTitle.length,
            overlaps: overlapCount(stack),
            followerDeficit: Math.round(followerDeficit(stack) * 10) / 10,
          });
        }
        title.textContent = originalText;
        window.reapplyAutoLayout(slide);
        await nextFrames();
      }
      window.setSlide(originalIndex);
      await nextFrames();
      return cases;
    });
    await page.evaluate(async () => {
      const target = [...document.querySelectorAll(".slide")].find((slide) => (
        slide.querySelectorAll('.el[data-edit-structure="module"][data-edit-composite]').length > 1
        && [...slide.querySelectorAll('.el[data-edit-kind="text"],.el[data-edit-layer="text"]')]
          .some((node) => !node.closest('.el[data-edit-structure="module"]'))
      ));
      if (!target) return;
      window.setSlide(Number(target.dataset.index));
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    });
    const loosePoint = await page.evaluate(() => {
      const object = [...document.querySelectorAll('.slide.active .el[data-edit-kind="text"],.slide.active .el[data-edit-layer="text"]')]
        .find((node) => !node.closest('.el[data-edit-structure="module"]'));
      if (!object) return null;
      const range = document.createRange();
      range.selectNodeContents(object);
      const glyph = range.getBoundingClientRect();
      const rect = glyph.width > 0.5 && glyph.height > 0.5 ? glyph : object.getBoundingClientRect();
      return { x:rect.left + rect.width / 2, y:rect.top + rect.height / 2 };
    });
    if (loosePoint) await page.mouse.click(loosePoint.x, loosePoint.y);
    await page.waitForTimeout(120);
    Object.assign(browserChecks, await page.evaluate(() => ({
      looseSelectionMode: document.getElementById("edit-selection-frame")?.dataset?.selectionMode || "",
      looseSelectionLabel: document.querySelector('#edit-selection-badge [data-role="label"]')?.textContent?.trim() || "",
    })));
    await page.evaluate(() => window.EditMode.deselect());
    const moduleBox = await page.locator('.slide.active .el[data-edit-structure="module"][data-edit-composite]').first().boundingBox();
    if (moduleBox) await page.mouse.click(moduleBox.x + moduleBox.width / 2, moduleBox.y + moduleBox.height / 2);
    await page.waitForTimeout(120);
    browserChecks.moduleSelectionMode = await page.evaluate(() => (
      document.getElementById("edit-selection-frame")?.dataset?.selectionMode || ""
    ));
    if (options.screenshot) {
      const screenshotPath = path.resolve(options.screenshot);
      await fs.mkdir(path.dirname(screenshotPath), { recursive: true });
      await page.screenshot({ path:screenshotPath, fullPage:true });
    }
  } finally {
    await browser.close();
  }

  const afterMarkup = await fs.readFile(htmlPath, "utf8");
  const afterSha256 = sha256(afterMarkup);
  const sourceUnchanged = beforeSha256 === afterSha256;
  const checks = {
    ...staticChecks,
    repeatNodesAbsent: browserChecks.repeatNodes === 0,
    repeatApiAbsent: browserChecks.repeatApiAbsent,
    repeatToolbarAbsent: browserChecks.repeatToolbarAbsent,
    aggregateGroupsAbsent: browserChecks.aggregateGroups === 0,
    centeringFramesPresent: browserChecks.centeringFrames > 0,
    centeringFramesNonSelectable: browserChecks.invalidCenteringFrames === 0,
    visibleContentAbsolutelyCentered: browserChecks.offCenterFrames === 0,
    semanticModulesPresent: browserChecks.semanticModules > 0,
    semanticModulesComplete: browserChecks.invalidModules === 0,
    looseObjectsPresent: browserChecks.looseObjects > 0,
    positioningFramesPresent: browserChecks.positioningFrames > 0,
    positioningFramesNonSelectable: browserChecks.invalidPositioningFrames === 0,
    dependentHeadersDoNotOverlap: browserChecks.headerCollisions.length === 0,
    dependentBodiesFollowHeaders: browserChecks.followerCollisions.length === 0,
    flowStressCasesPass: browserChecks.flowStressCases.length > 0
      && browserChecks.flowStressCases.every((item) => item.overlaps === 0 && item.followerDeficit <= 0.5),
    looseObjectsSelectIndividually: browserChecks.looseSelectionMode === "single"
      || /^已選取(?:文字|物件)$/.test(browserChecks.looseSelectionLabel),
    semanticModulesSelectAsGroups: browserChecks.moduleSelectionMode === "group",
    sourceUnchanged,
  };
  const report = {
    html: portablePath(htmlPath),
    screenshot: options.screenshot ? portablePath(path.resolve(options.screenshot)) : null,
    qaMode: "report-only",
    retiredFeature: "Repeat Group",
    beforeSha256,
    afterSha256,
    browser: browserChecks,
    checks,
    pass: Object.values(checks).every(Boolean),
  };
  await fs.mkdir(path.dirname(reportPath), { recursive: true });
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + "\n", "utf8");
  console.log(JSON.stringify(report));
  if (!report.pass) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
